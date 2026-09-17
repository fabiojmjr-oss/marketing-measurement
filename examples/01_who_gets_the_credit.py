"""Six attribution models on one set of journeys, and the holdout that overrules all six.

Run:
    python examples/01_who_gets_the_credit.py

The dataset carries a column no real advertising account has: how likely each user was to convert
before any marketing happened. Two of the five channels have a true effect of exactly zero - they
are shown to people who were already going to convert. Everything below is the question of whether
a measurement can tell that, and the answer depends entirely on which measurement.
"""

from __future__ import annotations

import pandas as pd

from mktlab.attribution import (
    MODELS,
    credit,
    credit_table,
    geo_lift,
    journey_sets,
    returns,
    shapley,
    unattributable,
)
from mktlab.synth import AUDIENCE, GEO, generate_dataset


def main() -> None:
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    data = generate_dataset()
    truth = data.channel_truth
    designs = data.geo_designs.set_index("channel")

    print("WHAT IS ACTUALLY TRUE, WHICH NO ACCOUNT KNOWS")
    print("   true_effect is the rate points a channel adds to a user it reaches.")
    print("   exposure_intent_slope is how much of its targeting rides on intent the user had")
    print("   already. A channel can score well on either without the other.")
    print()
    print(truth.round(4).to_string(index=False))
    zero = truth[truth["true_effect"] == 0.0]["channel"].tolist()
    print(f"\n   Channels whose true effect is exactly zero: {', '.join(zero)}")

    print("\n" + "=" * 98)
    print("SIX MODELS, ONE SET OF JOURNEYS")
    print("=" * 98)
    table = credit_table(data.journeys)
    print(table.round(4).to_string())
    zero_share = float(table.loc[zero, "last-click"].sum())
    print(f"\n   Last-click hands the two zero-effect channels {zero_share:.1%} of the credit.")
    largest = str(table["last-click"].idxmax())
    print(
        f"   The single largest share under last-click is {largest} at"
        f" {table.loc[largest, 'last-click']:.2%}, which adds nothing."
    )

    first_vs_last = pd.DataFrame(
        {
            "first-click": table["first-click"],
            "last-click": table["last-click"],
            "ratio": table["first-click"] / table["last-click"],
        }
    )
    print("\n   The same journeys read from the other end:")
    print(first_vs_last.round(4).to_string())
    print("   Nothing in the data changed between those two columns. Only the rule did.")

    print("\n" + "=" * 98)
    print("THE DATA-DRIVEN MODEL IS THE NAPKIN RULE")
    print("=" * 98)
    sets = journey_sets(data.journeys)
    channels = tuple(sorted({item for key in sets for item in key}))
    allocation = shapley(sets, channels)
    linear = credit(data.journeys, "linear").set_index("channel")["credited"]
    comparison = pd.DataFrame(
        {
            "shapley": pd.Series(allocation),
            "linear": linear,
        }
    )
    comparison["difference"] = comparison["shapley"] - comparison["linear"]
    print(comparison.round(6).to_string())
    print(
        f"\n   Largest absolute difference: {comparison['difference'].abs().max():.2e}"
        " - floating point, not disagreement."
    )
    print("   The Shapley value of the journey coverage game IS linear attribution. Computed here")
    print(f"   the long way, over 2^{len(channels)} coalitions, so the identity is a result.")
    print("   A vendor charging for the 'algorithmic' model is charging for divide-by-n.")

    print("\n" + "=" * 98)
    print("THE CONVERSIONS NO MODEL CAN SEE")
    print("=" * 98)
    missing = unattributable(data.audience, data.journeys)
    print(f"   conversions in the period: {missing['conversions']:,.0f}")
    print(f"   conversions with at least one touch: {missing['attributable']:,.0f}")
    print(
        f"   conversions nobody touched: {missing['untouched']:,.0f}"
        f" ({missing['untouched_share']:.2%})"
    )
    print("\n   Every share in the table above divides the touched conversions only. A report that")
    print(
        "   rescales those shares to one hundred per cent of the business has given the untouched"
    )
    print("   conversions to the channels in proportion to the credit they already had.")

    print("\n" + "=" * 98)
    print("THE HOLDOUT")
    print("=" * 98)
    print(f"   {GEO.geos} regions, {GEO.weeks} weeks, the channel switched off in half of them")
    print(f"   after week {GEO.split}. Read as a difference in differences on region-level rate")
    print("   changes, compared with Welch's test, one panel per channel.")
    print()
    lifts = {}
    rows = []
    for name in sorted(designs.index):
        panel = data.geo_experiments[data.geo_experiments["channel"] == name]
        lift = geo_lift(panel, split=GEO.split, channel=str(name))
        lifts[name] = lift
        low, high = lift.interval
        rows.append(
            {
                "channel": name,
                "lift": lift.lift,
                "low": low,
                "high": high,
                "p_value": lift.p_value,
                "significant": lift.significant,
                "true_rate_lift": float(designs.loc[name, "true_rate_lift"]),
                "covers_truth": low <= float(designs.loc[name, "true_rate_lift"]) <= high,
            }
        )
    holdouts = pd.DataFrame(rows)
    print(holdouts.round(6).to_string(index=False))
    print(
        f"\n   Intervals covering the true lift: {int(holdouts['covers_truth'].sum())}"
        f" of {len(holdouts)}."
    )
    print("   The two channels with no true effect are the two the test cannot separate from zero.")

    print("\n" + "=" * 98)
    print("WHAT THE BUDGET WAS ACTUALLY BUYING")
    print("=" * 98)
    last_click = credit(data.journeys, "last-click")
    priced = returns(
        credited=last_click,
        lifts=lifts,
        truth=truth,
        reach=float(AUDIENCE.users),
        value_per_conversion=AUDIENCE.value_per_conversion,
    )
    print(priced.round(4).to_string(index=False))

    ranked = priced.sort_values("roas", ascending=False)
    unestablished = ranked[~ranked["established"]]["channel"].tolist()
    print("\n   Ranked by the figure the report shows:")
    for position, (_, row) in enumerate(ranked.iterrows(), start=1):
        verdict = "incremental return established" if row["established"] else "NOT established"
        print(f"   {position}. {row['channel']:<16} ROAS {row['roas']:6.2f}   {verdict}")
    print(
        f"\n   ROAS puts {' and '.join(unestablished)} high in that ranking while the holdout"
        " cannot"
    )
    print("   establish any incremental return for them at all.")

    wasted = float(priced.loc[~priced["established"], "spend"].sum())
    total_spend = float(priced["spend"].sum())
    print(
        f"   Spend with no established incremental return: {wasted:,.0f}"
        f" of {total_spend:,.0f} ({wasted / total_spend:.1%})."
    )

    credited_total = float(priced["credited_conversions"].sum())
    blended_roas = credited_total * AUDIENCE.value_per_conversion / total_spend
    incremental_total = float(priced["incremental_conversions"].sum())
    blended_iroas = incremental_total * AUDIENCE.value_per_conversion / total_spend
    print(
        f"\n   Blended ROAS {blended_roas:.4f} against blended iROAS {blended_iroas:.4f}."
        " Same spend, same period."
    )

    understated = priced[priced["ratio"] < 1.0]
    for _, row in understated.iterrows():
        print(
            f"   And it runs the other way too: {row['channel']} has ROAS"
            f" {row['roas']:.2f} against iROAS {row['iroas']:.2f}"
        )
        print(
            f"   (ratio {row['ratio']:.4f}) - the one channel that creates demand is the one the"
            " credited figure"
        )
        print("   understates, because the conversions it starts are closed by somebody else.")

    print("\n" + "=" * 98)
    print("THE DECISION STANDARD")
    print("=" * 98)
    print(f"   Six models ({', '.join(MODELS)})")
    print("   disagree with each other and none of them is measuring the quantity a budget needs.")
    print("   One holdout answers it, for one channel, at a cost: half the regions lose the")
    print("   channel for thirteen weeks. That trade is the subject of the next wave.")


if __name__ == "__main__":
    main()
