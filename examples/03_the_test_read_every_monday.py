"""What thirteen weekly glances at a thirteen-week holdout actually cost.

Run:
    python examples/03_the_test_read_every_monday.py

Wave 2 sized the holdout on an assumption it never stated: that the test is read once, at the end.
The test in question runs for thirteen weeks after the switch and sits on a dashboard. This example
prices the difference between the test that was designed and the test that is actually being run.
"""

from __future__ import annotations

import pandas as pd

from mktlab.design import (
    DEFAULT_POWER,
    RULES,
    GeoDesign,
    exaggeration,
    inflated_alpha,
    information_inflation,
    ncp_for_power,
    peeking_table,
    plan,
    regions_for,
)
from mktlab.synth import AUDIENCE, CHANNELS, GEO, mean_rate, true_rate_lift


def main() -> None:
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)
    rate = mean_rate(AUDIENCE, tuple(CHANNELS))
    design = GeoDesign(
        geos=GEO.geos,
        weeks=GEO.weeks,
        split=GEO.split,
        users_per_geo_week=GEO.users_per_geo_week,
        base_rate=rate,
    )
    looks = design.weeks_after
    email = next(profile for profile in CHANNELS if profile.channel == "email")
    reach = float(AUDIENCE.users)
    value = AUDIENCE.value_per_conversion

    print("THE TEST THAT WAS DESIGNED, AND THE TEST THAT IS RUN")
    print(f"   Designed: {design.geos} regions, read once after {looks} weeks, alpha 0.05.")
    print(f"   Run: the same test, on a dashboard, read every Monday for {looks} weeks.")
    print()
    print(f"   Real false-positive rate of the second one: {inflated_alpha(looks):.4f}")
    print("   A channel that does nothing is declared a winner about one time in five.")

    print("\n" + "=" * 100)
    print("THE ERROR RATE AGAINST THE NUMBER OF GLANCES")
    print("=" * 100)
    print("   Computed by the Armitage-McPherson-Rowe recursion, not simulated: the looks are not")
    print("   independent, because each one contains all the data of the ones before it.")
    print()
    rows = [
        {
            "looks": count,
            "true_alpha": inflated_alpha(count),
            "times_the_nominal": inflated_alpha(count) / 0.05,
        }
        for count in (1, 2, 3, 5, 10, looks, 26, 52)
    ]
    print(pd.DataFrame(rows).round(6).to_string(index=False))
    print()
    print(
        "   Note what the curve does: it is steepest at the start. Two looks already cost 66% more"
    )
    print("   error than one. The difference between weekly and daily matters less than the")
    print("   difference between once and twice.")

    print("\n" + "=" * 100)
    print("THE FOUR RULES, PRICED")
    print("=" * 100)
    table = peeking_table(looks)
    print(table.round(6).to_string(index=False))
    print()
    for rule in RULES:
        print(f"   {plan(rule, looks).verdict()}")
    print()
    print("   Read the naive row as the diagnosis and the other two as the prescriptions. Both")
    print("   prescriptions hold the error rate at exactly 0.05, and they are different trades:")
    print(
        "   Pocock lets you stop from week one and needs a 32% bigger test; O'Brien-Fleming needs"
    )
    print("   4% more and will not stop you in the first weeks however good the numbers look.")
    print()
    print(
        "   The first O'Brien-Fleming boundary is 7.58 standard errors. That is not a typo: it is"
    )
    print("   the design saying that nothing observable in week one should stop a thirteen-week")
    print("   test, which is also the honest answer to most requests to end a test early.")

    print("\n" + "=" * 100)
    print("WHAT THE HONEST VERSION COSTS THE ACTUAL HOLDOUT")
    print("=" * 100)
    print("   More information means either a worse detectable return at the same size, or more")
    print("   regions to hold the return where it was. Both, for email, whose floor wave 2 showed")
    print("   was already the binding constraint:")
    print()
    floor = design.detectable_iroas(email.spend, reach, value)
    truth = true_rate_lift(email)
    base_regions = regions_for(truth, design)
    rows = []
    for rule in RULES:
        built = plan(rule, looks)
        if not built.valid:
            rows.append(
                {
                    "rule": rule,
                    "true_alpha": built.true_alpha,
                    "information": float("nan"),
                    "detectable_iroas": float("nan"),
                    "regions_for_the_same_floor": float("nan"),
                }
            )
            continue
        inflation = information_inflation(built.boundary, DEFAULT_POWER)
        # Information scales with regions, so holding the detectable effect where it was means
        # multiplying the region count by the inflation and rounding up to an even number, so that
        # the two arms stay equal.
        needed = -(-int(base_regions * inflation) // 2) * 2
        rows.append(
            {
                "rule": rule,
                "true_alpha": built.true_alpha,
                "information": inflation,
                "detectable_iroas": floor * inflation**0.5,
                "regions_for_the_same_floor": needed,
            }
        )
    print(pd.DataFrame(rows).round(6).to_string(index=False))
    print()
    print(
        f"   The base is {base_regions} regions, which is what email needed when the test was read"
    )
    print("   once. O'Brien-Fleming costs 2.1% of the detectable return - 4.25 becomes 4.34 - or")
    print("   two extra regions to hold the return where it was. That is the whole bill for a test")
    print("   that may legitimately be read every week for thirteen weeks, and nobody pays it")
    print("   because nobody has seen it written down. Pocock's bill is eight regions, and it buys")
    print("   the right to stop in week one.")
    print()
    print("   One approximation to name: the boundaries are normal-theory, as group-sequential")
    print(
        "   boundaries are, while the sizing in wave 2 uses the t distribution - at 38 degrees of"
    )
    print(
        "   freedom the critical values differ by 3.3%, which is the accuracy of this composition."
    )

    print("\n" + "=" * 100)
    print("AND THE HALF THAT A CORRECT BOUNDARY DOES NOT FIX")
    print("=" * 100)
    print("   A test stops early because the data came in favourably, so the estimate at the")
    print(
        "   stopping point is drawn from the favourable tail. Each rule below is evaluated at the"
    )
    print("   effect that gives that rule 80% power, so the comparison is at equal power:")
    print()
    rows = []
    for rule in RULES:
        built = plan(rule, looks)
        ncp = (
            ncp_for_power(built.boundary, DEFAULT_POWER)
            if built.valid
            else ncp_for_power(plan("naive", looks).boundary, DEFAULT_POWER)
        )
        measured = exaggeration(built.boundary, ncp)
        rows.append(
            {
                "rule": rule,
                "power": measured["power"],
                "reported_over_true": measured["ratio"],
                "expected_looks": measured["expected_looks"],
                "same_sign": measured["same_sign"],
            }
        )
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    print()
    print("   Reading once and publishing only the significant result already overstates a real")
    print("   effect by 12%, because publication is conditional on significance. Stopping early")
    print("   makes it worse in proportion to how early you are allowed to stop: 27% under")
    print("   O'Brien-Fleming, 48% under Pocock, 72% under the rule that is actually in use.")
    print()
    print("   So the ordering is not 'valid rules are clean and the naive rule is dirty'. Every")
    print("   rule that can stop early reports a flattering number, and a correct boundary fixes")
    print("   the false-positive rate only. Fixing the estimate needs a different instrument, and")
    print("   the cheapest version of it is not stopping early.")

    print("\n" + "=" * 100)
    print("THE UNDERPOWERED CASE, WHICH IS THE COMMON ONE")
    print("=" * 100)
    print("   Wave 2 showed the holdout could establish nothing below a return of 4.25 on email,")
    print("   against a truth of 5.76. That is a test near the edge of its own power. Peeking on a")
    print("   test like that does not exaggerate by 72%:")
    print()
    weak = ncp_for_power(plan("read-once", looks).boundary, 0.30)
    rows = []
    for rule in ("read-once", "naive"):
        built = plan(rule, looks)
        measured = exaggeration(built.boundary, weak)
        rows.append(
            {
                "rule": rule,
                "power": measured["power"],
                "reported_over_true": measured["ratio"],
                "expected_looks": measured["expected_looks"],
                "same_sign": measured["same_sign"],
            }
        )
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    print()
    print("   At 30% power, read once, the published effect is already 1.80 times the truth. Read")
    print("   weekly, it is 2.62 times - and 4% of the results that clear the line point the wrong")
    print("   way entirely. An underpowered test is not a weak test. It is a test whose successes")
    print("   are mostly noise, and peeking is how the noise gets declared.")


if __name__ == "__main__":
    main()
