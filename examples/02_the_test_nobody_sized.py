"""What the holdout could have found, decided before it ran rather than after.

Run:
    python examples/02_the_test_nobody_sized.py

Wave 1's holdout resolved three channels out of five. This example shows that every part of that
outcome was computable in advance: the precision of the test, which channels it would resolve, how
many regions it actually needed, what it would cost, and - the figure nobody computes - the smallest
incremental return it was capable of establishing on each channel.
"""

from __future__ import annotations

import pandas as pd

from mktlab.attribution import geo_lift
from mktlab.design import (
    DEFAULT_POWER,
    GeoDesign,
    holdout_cost,
    power_curve,
    regions_for,
    retrospective,
    sizing_table,
)
from mktlab.synth import AUDIENCE, CHANNELS, GEO, generate_dataset, mean_rate, true_rate_lift


def main() -> None:
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)
    data = generate_dataset()
    rate = mean_rate(AUDIENCE, tuple(CHANNELS))
    design = GeoDesign(
        geos=GEO.geos,
        weeks=GEO.weeks,
        split=GEO.split,
        users_per_geo_week=GEO.users_per_geo_week,
        base_rate=rate,
    )

    print("THE DESIGN THAT WAS RUN, PRICED BEFORE IT RAN")
    print(f"   {design.geos} regions ({design.treated_geos} treated, {design.holdout_geos} held")
    print(f"   out), {design.weeks_before} weeks before the switch and {design.weeks_after} after,")
    print(
        f"   {design.users_per_geo_week:,} users a region-week, base rate {design.base_rate:.4f}."
    )
    print(f"   Degrees of freedom: {design.df:.0f} - one per region, not one per region-week.")
    print()
    print(f"   Predicted standard error: {design.standard_error():.6f}")
    print(f"   Power at a lift of exactly zero: {design.power(0.0):.6f}")
    print("   That last line is the significance level, and it is the control case: a test that")
    print("   does not return alpha when nothing is happening is not a test.")

    print("\n" + "=" * 100)
    print("THE PRECISION WAS KNOWN BEFORE ANY MONEY WAS SPENT")
    print("=" * 100)
    print("   The permanent differences between regions cancel in a difference of changes, and so")
    print("   does any trend common to them. What is left is binomial noise on a known number of")
    print("   users, so the standard error closes analytically - no data required.")
    print()
    rows = []
    lifts = {}
    for profile in CHANNELS:
        panel = data.geo_experiments[data.geo_experiments["channel"] == profile.channel]
        observed = geo_lift(panel, split=GEO.split, channel=profile.channel)
        lifts[profile.channel] = observed
        truth = true_rate_lift(profile)
        predicted = design.standard_error(truth)
        rows.append(
            {
                "channel": profile.channel,
                "true_lift": truth,
                "predicted_se": predicted,
                "observed_se": observed.standard_error,
                "ratio": observed.standard_error / predicted,
                "power_at_truth": design.power(truth),
                "resolved": observed.significant,
            }
        )
    precision = pd.DataFrame(rows)
    print(precision.round(6).to_string(index=False))
    print()
    print("   An estimated standard error on 38 degrees of freedom is itself noisy by about 11.5%,")
    print("   so ratios in this range are the prediction working rather than failing. The test's")
    print("   precision is a design decision, not something discovered afterwards.")

    print("\n" + "=" * 100)
    print("WHICH CHANNELS THIS DESIGN WAS ALWAYS GOING TO RESOLVE")
    print("=" * 100)
    detectable = design.detectable_lift()
    print(f"   Minimum detectable lift at {DEFAULT_POWER:.0%} power: {detectable:.6f} rate points.")
    print(
        f"   At 50% power: {design.detectable_lift(0.50):.6f}."
        f" At 95%: {design.detectable_lift(0.95):.6f}."
    )
    print()
    for profile in CHANNELS:
        truth = true_rate_lift(profile)
        if truth == 0.0:
            print(
                f"   {profile.channel:<16} true lift 0 - correctly unresolvable, nothing to detect"
            )
            continue
        needed = regions_for(truth, design)
        print(
            f"   {profile.channel:<16} true lift {truth:.4f}"
            f"  power {design.power(truth):.4f}"
            f"  regions actually needed {needed:>4} of {design.geos}"
        )
    print()
    print("   All three real effects were detectable with at least 96% power, and the hardest of")
    print("   them needed 24 regions. Forty were used. The surplus is not free - see the cost.")

    print("\n" + "=" * 100)
    print("THE FIGURE NOBODY COMPUTES: THE SMALLEST RETURN THE TEST COULD ESTABLISH")
    print("=" * 100)
    print("   The detectable lift above is the same for every channel, because it depends on the")
    print("   design and not on the channel. The detectable *return* is not, because it divides")
    print("   that lift by the channel's spend - and a budget decides on returns.")
    print()
    rows = []
    for profile in CHANNELS:
        truth = true_rate_lift(profile)
        rows.append(
            {
                "channel": profile.channel,
                "spend": profile.spend,
                "detectable_lift": detectable,
                "detectable_iroas": design.detectable_iroas(
                    profile.spend, float(AUDIENCE.users), AUDIENCE.value_per_conversion
                ),
                "interval_half_width": design.return_precision(
                    profile.spend, float(AUDIENCE.users), AUDIENCE.value_per_conversion
                ),
                "true_iroas": truth
                * AUDIENCE.users
                * AUDIENCE.value_per_conversion
                / profile.spend,
            }
        )
    floors = pd.DataFrame(rows)
    print(floors.round(4).to_string(index=False))
    print()
    print("   The same test, run the same way, is a precision instrument on the largest channel")
    print("   and nearly blind on the smallest. On email it can establish nothing below a return")
    print("   of 4.25, and the interval it will produce is 3.00 wide either side - so email's true")
    print("   return of 5.76 arrives as 'somewhere between 2.8 and 8.8'. The test can confirm the")
    print("   channel is good and can never say how good, which is the question being asked.")

    print("\n" + "=" * 100)
    print("WHAT A NON-RESULT ACTUALLY ESTABLISHED")
    print("=" * 100)
    print("   Two channels came back not significant. That is not the end of the sentence: an")
    print("   interval has a top, the top is a return, and ruling out returns above it is a fact")
    print("   about the channel rather than about the test.")
    print()
    rows = []
    for profile in CHANNELS:
        read = retrospective(
            lifts[profile.channel],
            design,
            spend=profile.spend,
            reach=float(AUDIENCE.users),
            value_per_conversion=AUDIENCE.value_per_conversion,
        )
        rows.append(
            {
                "channel": read.channel,
                "iroas": read.iroas,
                "low": read.iroas_interval[0],
                "excludes_above": read.excludes,
                "detectable_floor": read.detectable_iroas,
                "significant": read.significant,
                "design_was_big_enough": read.was_big_enough,
            }
        )
        if not read.significant:
            print(f"   {read.verdict()}")
    print()
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    print()
    print("   The two null rows differ in a way no p-value shows, and it is in the last two")
    print("   columns. busca-marca's null is informative: the design could establish returns down")
    print("   to 0.94 and the test ruled out everything above 1.33, so the answer sits in a range")
    print("   this test could resolve. retargeting's null is not: it ruled out returns above 1.07")
    print("   while the design could not have established any return below 1.42, so there was no")
    print("   return it could both miss and detect.")
    print()
    print("   Those two numbers are always of the same size - the ceiling is the estimate plus t")
    print("   times the standard error, the floor is t plus the power quantile times the same")
    print("   standard error - which is the general statement: a null holdout on a small channel")
    print("   buys an upper bound and little else.")

    print("\n" + "=" * 100)
    print("WHAT THE TEST COST")
    print("=" * 100)
    print("   The held-out regions lose the channel for the weeks after the switch. If the channel")
    print("   works, those conversions do not happen.")
    print()
    rows = []
    for profile in CHANNELS:
        truth = true_rate_lift(profile)
        cost = holdout_cost(design, truth, AUDIENCE.value_per_conversion)
        rows.append(
            {
                "channel": profile.channel,
                "true_lift": truth,
                "region_weeks": cost["region_weeks_held_out"],
                "forgone_conversions": cost["forgone_conversions"],
                "forgone_share": cost["forgone_share"],
            }
        )
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    print()
    print("   The asymmetry is the point: the test is expensive exactly when its answer is that")
    print("   the channel was worth keeping, and free on the channels that do nothing. Holding")
    print("   out the best channel gives up 27.6% of the conversions those regions would have")
    print("   produced - and that figure is lift over base rate, which carries no population in")
    print("   it and so survives being quoted.")

    print("\n" + "=" * 100)
    print("THE TRADE, AS ONE TABLE")
    print("=" * 100)
    print("   Every row is a design somebody could run, for the channel where the trade actually")
    print("   bites: email, where the detectable return starts above what the business would act")
    print("   on. Left half is what it finds, right half is what it gives up to find it.")
    print()
    email = next(profile for profile in CHANNELS if profile.channel == "email")
    table = sizing_table(
        design,
        geos=(20, 40, 80, 160),
        weeks=(13, 26, 52),
        spend=email.spend,
        reach=float(AUDIENCE.users),
        value_per_conversion=AUDIENCE.value_per_conversion,
        expected_lift=true_rate_lift(email),
    )
    print(
        table.assign(
            forgone_conversions=table["forgone_conversions"].round(0),
            forgone_revenue=table["forgone_revenue"].round(0),
        )
        .round(6)
        .to_string(index=False)
    )
    print()
    print("   Doubling the regions cuts the detectable return by about 30% and doubles what the")
    print("   test gives up. And the design that ran is the row that cannot answer the question:")
    for geos, weeks in ((40, 26), (80, 26), (160, 26), (40, 52)):
        candidate = GeoDesign(
            geos=geos,
            weeks=weeks,
            split=weeks // 2,
            users_per_geo_week=GEO.users_per_geo_week,
            base_rate=rate,
        )
        half = candidate.return_precision(
            email.spend, float(AUDIENCE.users), AUDIENCE.value_per_conversion
        )
        truth = true_rate_lift(email) * AUDIENCE.users * AUDIENCE.value_per_conversion / email.spend
        print(
            f"   {geos:>3} regions, {weeks:>2} weeks: interval half-width {half:.4f}"
            f"  ->  email's {truth:.2f} arrives as {truth - half:.2f} to {truth + half:.2f}"
        )
    print()
    print("   Telling a return of 3 from a return of 8 needs the half-width under 2.76, which")
    print("   means 80 regions rather than 40, or the same 40 for a year. That is the honest")
    print(
        "   answer to 'should we run a holdout on email', and it is available before running one."
    )

    print("\n" + "=" * 100)
    print("THE HALF OF THE DESIGN THAT IS FREE")
    print("=" * 100)
    print("   The cost of a holdout is paid entirely in the weeks *after* the switch: that is when")
    print("   the held-out regions lose the channel. The weeks before it hold nothing out and cost")
    print("   nothing - and they enter the standard error exactly as the weeks after do.")
    print()
    rows = []
    for before in (4, 8, 13, 26, 52):
        candidate = GeoDesign(
            geos=design.geos,
            weeks=before + design.weeks_after,
            split=before,
            users_per_geo_week=GEO.users_per_geo_week,
            base_rate=rate,
        )
        cost = holdout_cost(candidate, true_rate_lift(email), AUDIENCE.value_per_conversion)
        rows.append(
            {
                "weeks_before": before,
                "weeks_after": candidate.weeks_after,
                "standard_error": candidate.standard_error(),
                "detectable_iroas": candidate.detectable_iroas(
                    email.spend, float(AUDIENCE.users), AUDIENCE.value_per_conversion
                ),
                "half_width": candidate.return_precision(
                    email.spend, float(AUDIENCE.users), AUDIENCE.value_per_conversion
                ),
                "region_weeks_held_out": cost["region_weeks_held_out"],
                "forgone_conversions": cost["forgone_conversions"],
            }
        )
    print(pd.DataFrame(rows).round(6).to_string(index=False))
    print()
    print("   Every row costs the same 260 region-weeks and the same 1,664 conversions. Extending")
    print("   the history from 13 weeks to 52 takes the detectable return from 4.25 to 3.36 and")
    print("   the interval half-width from 3.00 to 2.37, for nothing.")
    print()
    doubled = GeoDesign(
        geos=design.geos * 2,
        weeks=design.weeks,
        split=design.split,
        users_per_geo_week=GEO.users_per_geo_week,
        base_rate=rate,
    )
    floor = design.standard_error() / 2.0**0.5
    print("   And there is an exact limit to it. An infinitely long pre-period reaches a standard")
    print(
        f"   error of {floor:.6f}, which is exactly what {doubled.geos} regions over the same"
        f" {doubled.weeks} weeks"
    )
    print(f"   give: {doubled.standard_error():.6f}. Equal, not close - both halve the same")
    print("   variance. A long enough history is worth as much as doubling the size of the test,")
    print("   and only one of the two is free.")

    print("\n" + "=" * 100)
    print("POWER AGAINST THE EFFECT, FOR THE DESIGN THAT RAN")
    print("=" * 100)
    curve = power_curve(
        design,
        lifts=(
            0.0,
            0.0005,
            0.0010,
            design.detectable_lift(0.50),
            design.detectable_lift(),
            0.0032,
            0.0075,
            0.0270,
        ),
        spend=email.spend,
        reach=float(AUDIENCE.users),
        value_per_conversion=AUDIENCE.value_per_conversion,
    )
    print(curve.round(6).to_string(index=False))
    print()
    print("   The first row is the control: nothing happening, and the test rejects at exactly")
    print("   alpha. The iroas column prices each lift against email's spend, which is how a")
    print("   power curve becomes a budget conversation instead of a statistics one.")


if __name__ == "__main__":
    main()
