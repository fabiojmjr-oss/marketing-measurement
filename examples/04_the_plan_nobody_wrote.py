"""The monitoring plan a thirteen-week holdout should have been handed before it started.

Run:
    python examples/04_the_plan_nobody_wrote.py

Wave 3 priced what weekly glances cost and offered two boundaries that fix the error rate. Both of
them assume the looks are evenly spaced and known in advance, and neither can end a test that is
going nowhere. This example builds the plan without those assumptions: an alpha-spending schedule,
so the looks do not have to be known when the test starts, and a futility bound, so a channel doing
nothing stops consuming the calendar.
"""

from __future__ import annotations

import pandas as pd
from scipy import optimize

from mktlab.design import (
    DEFAULT_POWER,
    UNREACHABLE,
    GeoDesign,
    alpha_spent,
    crossing_probability,
    equal_information,
    holdout_cost,
    monitoring_plan,
    obrien_fleming,
    pocock,
    schedule,
    spending_boundary,
)
from mktlab.synth import AUDIENCE, CHANNELS, GEO, mean_rate, true_rate_lift

ONE_SIDED = 0.025


def main() -> None:
    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", 30)
    looks = GEO.weeks - GEO.split
    fractions = equal_information(looks)
    efficacy = spending_boundary(fractions, ONE_SIDED)
    never = (-UNREACHABLE,) * looks

    print("THE ASSUMPTION WAVE 3 LEFT IN PLACE")
    print(f"   Its boundaries are built for {looks} looks, evenly spaced, known in advance. A real")
    print(
        "   test is read when somebody opens the dashboard. An alpha-spending function commits to"
    )
    print("   how much error may be spent by each *point in the accumulation of information*, and")
    print(
        "   the boundary follows - so the schedule does not have to be known when the test starts."
    )
    print()
    print("   The same 0.025 of error, spent under four different reading schedules:")
    print()
    rows = []
    for label, shares in (
        (f"weekly, {looks} looks", fractions),
        ("monthly, 3 looks", (4 / 13, 8 / 13, 1.0)),
        ("late start, 4 looks", (0.5, 0.75, 0.9, 1.0)),
        ("read once at the end", (1.0,)),
    ):
        boundary = spending_boundary(shares, ONE_SIDED)
        spent = crossing_probability(
            boundary, fractions=shares, futility=(-UNREACHABLE,) * len(shares)
        )[-1]
        rows.append(
            {
                "schedule": label,
                "looks": len(shares),
                "first_boundary": boundary[0],
                "last_boundary": boundary[-1],
                "alpha_spent": spent,
            }
        )
    print(pd.DataFrame(rows).round(8).to_string(index=False))
    print()
    print(
        "   Every row spends exactly 0.025, and the last one returns 1.96 - reading a test once is"
    )
    print(
        "   the degenerate case of monitoring it, which is the control this whole machinery has to"
    )
    print("   pass before any of its other numbers mean anything.")

    print("\n" + "=" * 100)
    print("THE SPENDING FUNCTION AGAINST THE EXACT BOUNDARY IT APPROXIMATES")
    print("=" * 100)
    approximation = spending_boundary(fractions, ONE_SIDED, "obrien-fleming")
    exact = obrien_fleming(looks, 2.0 * ONE_SIDED)
    comparison = pd.DataFrame(
        {
            "look": range(1, looks + 1),
            "spending_function": approximation,
            "exact_obrien_fleming": exact,
            "ratio": [a / b for a, b in zip(approximation, exact, strict=True)],
        }
    )
    print(comparison.round(4).to_string(index=False))
    print()
    print(f"   Pocock's exact constant is {pocock(looks, 2.0 * ONE_SIDED)[0]:.4f}, against")
    print(
        f"   {spending_boundary(fractions, ONE_SIDED, 'pocock')[0]:.4f} from its spending function."
    )
    print(
        "   The approximation is worst at the first look and nearly exact at the last, which is the"
    )
    print("   trade: a few per cent of shape, in exchange for not having to know the schedule.")

    print("\n" + "=" * 100)
    print("THE PLAN, WITH AND WITHOUT THE RIGHT TO GIVE UP")
    print("=" * 100)
    powered_for = float(
        optimize.brentq(
            lambda ncp: (
                crossing_probability(
                    efficacy, drift=ncp / looks**0.5, fractions=fractions, futility=never
                )[-1]
                - DEFAULT_POWER
            ),
            0.5,
            20.0,
            xtol=1e-12,
        )
    )
    print(f"   Powered for an effect whose final statistic has noncentrality {powered_for:.4f},")
    print(f"   which is {DEFAULT_POWER:.0%} power without a futility bound.")
    print()
    open_ended = monitoring_plan(fractions, powered_for, alpha=ONE_SIDED, beta=None)
    with_futility = monitoring_plan(fractions, powered_for, alpha=ONE_SIDED)
    print(f"   {open_ended.verdict()}")
    print(f"   {with_futility.verdict()}")
    print()
    print(schedule(with_futility).round(6).to_string(index=False))
    print()
    print("   Read the futility column downwards. In week one it is -3.68: nothing observable then")
    print("   should end the test. By week six it has risen above zero, which says that a channel")
    print("   not yet ahead by then is not going to get there. In the last week it equals the")
    print("   efficacy bound, because a test that reaches its end without rejecting has failed.")

    print("\n" + "=" * 100)
    print("WHAT THE RIGHT TO GIVE UP COSTS AND WHAT IT BUYS")
    print("=" * 100)
    rows = [
        {
            "quantity": "one-sided error rate",
            "without_futility": open_ended.true_alpha,
            "with_futility": with_futility.true_alpha,
        },
        {
            "quantity": "power at the design effect",
            "without_futility": open_ended.power,
            "with_futility": with_futility.power,
        },
        {
            "quantity": "information for 80% power",
            "without_futility": open_ended.information_to_restore_power(),
            "with_futility": with_futility.information_to_restore_power(),
        },
        {
            "quantity": "looks used, channel doing nothing",
            "without_futility": open_ended.expected_looks_under(0.0),
            "with_futility": with_futility.expected_looks_under(0.0),
        },
        {
            "quantity": "looks used, channel that works",
            "without_futility": open_ended.expected_looks_under(powered_for),
            "with_futility": with_futility.expected_looks_under(powered_for),
        },
        {
            "quantity": "chance of abandoning, nothing happening",
            "without_futility": open_ended.abandoned_under_null,
            "with_futility": with_futility.abandoned_under_null,
        },
        {
            "quantity": "chance of abandoning a test that would work",
            "without_futility": open_ended.abandoned_under_alternative,
            "with_futility": with_futility.abandoned_under_alternative,
        },
    ]
    print(pd.DataFrame(rows).round(6).to_string(index=False))
    print()
    print(
        "   The headline: on a channel doing nothing the test ends after 6.09 weekly reads instead"
    )
    print(
        "   of 12.94 - it is cut in half - and the bill is 8.9% more information to hold the same"
    )
    print("   80% power, plus a 23.4% chance of abandoning a test that would have succeeded.")
    print()
    print("   The error rate falls from 0.0250 to 0.0224 rather than staying put, and that is the")
    print(
        "   futility bound being *non-binding*: the efficacy boundary is solved as though the test"
    )
    print(
        "   could never be abandoned, so a team that overrules the futility signal and keeps going"
    )
    print("   has not broken anything. The gap between those two numbers is what that insurance")
    print("   costs.")

    print("\n" + "=" * 100)
    print("AND WHAT IT DOES NOT SAVE, WHICH THIS REPOSITORY GOT WRONG FIRST")
    print("=" * 100)
    rate = mean_rate(AUDIENCE, tuple(CHANNELS))
    design = GeoDesign(
        geos=GEO.geos,
        weeks=GEO.weeks,
        split=GEO.split,
        users_per_geo_week=GEO.users_per_geo_week,
        base_rate=rate,
    )
    held_out_per_week = design.holdout_geos * design.users_per_geo_week
    email = next(profile for profile in CHANNELS if profile.channel == "email")
    rows = []
    for label, lift, ncp in (
        ("email, which works", true_rate_lift(email), powered_for),
        ("retargeting, which does nothing", 0.0, 0.0),
    ):
        without = open_ended.expected_looks_under(ncp)
        within = with_futility.expected_looks_under(ncp)
        rows.append(
            {
                "channel": label,
                "weeks_held_without": without,
                "weeks_held_with": within,
                "conversions_forgone_without": held_out_per_week * without * lift,
                "conversions_forgone_with": held_out_per_week * within * lift,
            }
        )
    print(pd.DataFrame(rows).round(2).to_string(index=False))
    print()
    full_run = holdout_cost(design, true_rate_lift(email), AUDIENCE.value_per_conversion)
    print(f"   A holdout run to its full {design.weeks_after} weeks would give up")
    print(f"   {full_run['forgone_conversions']:.0f} of email's conversions. The roadmap of this")
    print(
        "   repository claimed a futility bound was what would save them. It is not, and wave 2's"
    )
    print("   own arithmetic says so: the cost is the held-out population times the channel's real")
    print("   lift, so a channel doing nothing costs nothing to hold out - and that is exactly the")
    print("   case futility fires on. The retargeting row gives up nothing either way.")
    print()
    print(
        "   What futility saves there is seven weeks of calendar, twenty regions kept away from a"
    )
    print("   channel nobody can act on yet, and a decision that cannot be taken while the test")
    print("   runs. Those are real and they are not conversions. Stopping early on a channel that")
    print(
        "   *works* does save conversions - 115 of them here - and that is the efficacy boundary's"
    )
    print("   doing, not the futility bound's.")

    print("\n" + "=" * 100)
    print("THE SPENDING FUNCTION IS A DIAL, NOT A NAME")
    print("=" * 100)
    rows = []
    for family, rho in (("obrien-fleming", 3.0), ("power", 3.0), ("power", 1.0), ("pocock", 3.0)):
        boundary = spending_boundary(fractions, ONE_SIDED, family, rho)
        built = monitoring_plan(fractions, powered_for, alpha=ONE_SIDED, family=family, rho=rho)
        rows.append(
            {
                "family": family if family != "power" else f"power, rho={rho:g}",
                "spent_by_week_4": alpha_spent(fractions[3], ONE_SIDED, family, rho),
                "first_boundary": boundary[0],
                "last_boundary": boundary[-1],
                "power": built.power,
                "looks_if_nothing": built.expected_looks_under(0.0),
                "abandon_a_winner": built.abandoned_under_alternative,
            }
        )
    print(pd.DataFrame(rows).round(6).to_string(index=False))
    print()
    print(
        "   A schedule that spends early can stop sooner and pays for it in power; one that spends"
    )
    print("   late keeps the power and reads the test longer. Both are defensible and neither is a")
    print("   default worth inheriting without looking at these two columns.")


if __name__ == "__main__":
    main()
