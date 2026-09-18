"""Putting the holdout into the model, and pricing everything the transfer carries with it.

Run:
    python examples/06_the_experiment_the_model_believes.py

Wave 5 ended in a choice: the holdout is narrow and expensive, the model is free and eleven to
thirteen times wider. The construction that refuses the choice is to use both - the experiment's
estimate enters the model as a prior on the coefficient. It works. This example measures what else
it does: the unit conversion between the two instruments, what a skipped conversion buys, what the
experiment's own sampling error becomes once the model believes it, and what happens to the four
channels the experiment never touched.
"""

from __future__ import annotations

import pandas as pd

from mktlab.attribution import geo_lift
from mktlab.calibration import average_to_marginal, calibrate, prior_from_holdout
from mktlab.mmm import fit
from mktlab.synth import AUDIENCE, CHANNELS, GEO, MEDIA_MIX, generate_dataset

#: Saturation points spanning the range wave 5 established the fit cannot distinguish.
SATURATIONS = (0.5, 1.3, 3.0, 10.0)


def main() -> None:
    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", 30)
    data = generate_dataset()
    panel = data.spend_panel
    truth = data.media_truth
    spend = {profile.channel: profile.spend for profile in CHANNELS}
    reach = float(AUDIENCE.users)
    baseline = fit(panel)

    lifts = {}
    for profile in CHANNELS:
        name = profile.channel
        experiment = data.geo_experiments[data.geo_experiments["channel"] == name]
        lifts[name] = geo_lift(experiment, split=GEO.split, channel=name)
    resolved = [name for name, lift in lifts.items() if lift.significant]

    def priors(names: list[str], convert: bool = True) -> dict:
        return {
            name: prior_from_holdout(
                lifts[name], baseline, name, reach=reach, spend=spend[name], convert=convert
            )
            for name in names
        }

    print("THE BRIDGE BETWEEN THE TWO INSTRUMENTS")
    print("   A holdout switches a channel off, so it measures the average return over the period.")
    print("   A coefficient is a local slope, so it estimates the marginal return at the current")
    print("   spend.")
    print("   Where the response bends those are different numbers, and the factor is closed form:")
    print("   with a half point at k times the spend level, average / marginal = 1 + 1/k.")
    print()
    rows = []
    for multiple in SATURATIONS:
        rows.append({"saturation_at": multiple, "factor": average_to_marginal(multiple)})
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    declared = average_to_marginal(MEDIA_MIX.saturation_at)
    print()
    print(f"   At the generator's {MEDIA_MIX.saturation_at:.2f} the factor is {declared:.10f}, and")
    print("   the generator's own ratio of its two return columns is the same number to twelve")
    print("   digits - two derivations that share no code. The uncomfortable part is the column")
    print("   above: the factor is set by the saturation point, which wave 5 established the fit")
    print("   is nearly blind to.")

    print("\n" + "=" * 98)
    print("WHAT THE EXPERIMENT SAYS, ONCE IT IS ON THE COEFFICIENT'S SCALE")
    print("=" * 98)
    print(f"   The holdout resolved {len(resolved)} channels of {len(lifts)}:")
    print(f"   {', '.join(resolved)}.")
    print("   Each estimate is a rate per user, so it becomes conversions when multiplied by the")
    print("   population, a return when divided by the spend, a marginal return when divided by")
    print("   the factor above, and a coefficient when divided by the model's own chain rule. The")
    print("   experiment's clean number passes through two of the model's guesses before it lands.")
    print()
    built = priors(resolved)
    rows = []
    for name, prior in built.items():
        real = float(
            truth.loc[truth["channel"] == name, "marginal_conversions_per_unit_spend"].iloc[0]
        )
        rows.append(
            {
                "channel": name,
                "average_return": prior.average_return,
                "conversion_factor": prior.conversion_factor,
                "marginal_return": prior.marginal_return,
                "truth": real,
                "times_the_truth": prior.marginal_return / real,
                "coefficient": prior.mean,
                "standard_error": prior.standard_error,
            }
        )
    print(pd.DataFrame(rows).round(6).to_string(index=False))

    print("\n" + "=" * 98)
    print("THE MODEL BEFORE AND AFTER IT BELIEVES THE EXPERIMENT")
    print("=" * 98)
    good = calibrate(panel, built)
    print(good.table().round(4).to_string(index=False))
    print()
    print("   Read width_kept: the three channels the experiment covered keep under a tenth of the")
    print("   width least squares gave them. The two it did not cover keep three quarters and four")
    print("   fifths of theirs, having had no prior at all - that is the correlation between the")
    print("   spend columns, and it is the subject of the last section.")
    print()
    print(good.transfer(truth).round(6).to_string(index=False))
    before = int(
        sum(
            1
            for low, high in zip(
                baseline.returns(truth)["low"], baseline.returns(truth)["high"], strict=True
            )
            if low > 0 or high < 0
        )
    )
    after = int(good.transfer(truth)["resolved"].sum())
    covered_before = int(baseline.returns(truth)["covers_truth"].sum())
    covered_after = int(good.transfer(truth)["covers_truth"].sum())
    # Over the channels the experiment covered, not over every channel: the two with no prior also
    # narrow, through the correlation, and including them puts a 1.2 in a range about the transfer.
    covered = good.table().set_index("channel").loc[resolved, "width_kept"]
    tightest, loosest = 1.0 / float(covered.min()), 1.0 / float(covered.max())
    loss = baseline.r_squared - good.posterior.r_squared
    print()
    print(f"   Channels resolved: {before} of 5 before, {after} of 5 after.")
    print(
        f"   Intervals covering the truth: {covered_before} of 5 before,"
        f" {covered_after} of 5 after."
    )
    print("   That is the trade nobody writes down. On the channels the experiment covered the")
    print(
        f"   transfer bought between {loosest:.0f} and {tightest:.0f} times the precision, and it"
    )
    print("   gave up a covering interval.")
    print(
        f"   In-sample fit: R-squared {baseline.r_squared:.6f} before,"
        f" {good.posterior.r_squared:.6f}"
    )
    print(f"   after - a loss of {loss:.6f}. The data is almost indifferent between the two")
    print("   answers, which is why in-sample fit cannot adjudicate a calibration.")

    print("\n" + "=" * 98)
    print("WHERE THE LOST COVERAGE CAME FROM")
    print("=" * 98)
    print("   It was not manufactured by the update. It was inherited, and the holdout's own")
    print("   interval says so: a 95% interval is wrong one time in twenty by construction, five")
    print("   were computed in wave 1, and this is the one.")
    print()
    rows = []
    for name in resolved:
        lift = lifts[name]
        low, high = lift.interval
        average_truth = float(
            truth.loc[truth["channel"] == name, "conversions_per_unit_spend"].iloc[0]
        )
        rows.append(
            {
                "channel": name,
                "holdout_low": low * reach / spend[name],
                "holdout_high": high * reach / spend[name],
                "average_truth": average_truth,
                "holdout_covers": bool(
                    low * reach / spend[name] <= average_truth <= high * reach / spend[name]
                ),
            }
        )
    print(pd.DataFrame(rows).round(6).to_string(index=False))
    print()
    index = baseline.channels.index("social-pago")
    model_precision = 1.0 / float(baseline.standard_errors[index]) ** 2
    prior_precision = 1.0 / built["social-pago"].standard_error ** 2
    weight = model_precision / (model_precision + prior_precision)
    print("   The model's own interval on social-pago did cover the truth, and it carried")
    print(f"   {weight:.2%} of the weight in the average that overruled it. Calibration is not a")
    print("   way to be right more often than the experiment. It is a way to be as right as")
    print("   the experiment, cheaply.")

    print("\n" + "=" * 98)
    print("THE SAME TRANSFER, WITH THE CONVERSION SKIPPED")
    print("=" * 98)
    naive = calibrate(panel, priors(resolved, convert=False))
    print(naive.transfer(truth).round(6).to_string(index=False))
    print()
    print(f"   Channels resolved: {int(naive.transfer(truth)['resolved'].sum())} of 5.")
    print(
        f"   Intervals covering the truth: {int(naive.transfer(truth)['covers_truth'].sum())} of 5."
    )
    print(f"   R-squared {naive.posterior.r_squared:.6f}.")
    print("   One unit conversion, skipped. The intervals are tighter than the honest ones, every")
    print("   estimate is inflated by about the factor that was left out, and busca-marca - a")
    print("   channel whose true effect is exactly zero - now has an interval that excludes zero")
    print("   from below. A confident negative return, manufactured by arithmetic.")

    print("\n" + "=" * 98)
    print("WHAT A NULL RESULT IS WORTH")
    print("=" * 98)
    print("   The two channels the holdout could not resolve are usually reported as inconclusive")
    print("   and then dropped. They are not absences: each is an estimate with a standard error,")
    print("   and on this account it is a far tighter one than the model can produce.")
    print()
    nulls = [name for name in lifts if name not in resolved]
    # The two null priors and nothing else, so that nothing but them is doing the work.
    from_nulls = calibrate(panel, priors(nulls))
    table = from_nulls.table().set_index("channel")
    transferred = from_nulls.transfer(truth).set_index("channel")
    rows = []
    for name in nulls:
        rows.append(
            {
                "channel": name,
                "model_width": float(table.loc[name, "model_width"]),
                "posterior_width": float(table.loc[name, "posterior_width"]),
                "width_kept": float(table.loc[name, "width_kept"]),
                "posterior_return": float(transferred.loc[name, "posterior_return"]),
                "low": float(transferred.loc[name, "low"]),
                "high": float(transferred.loc[name, "high"]),
                "covers_truth": bool(transferred.loc[name, "covers_truth"]),
                "resolved": bool(transferred.loc[name, "resolved"]),
            }
        )
    print(pd.DataFrame(rows).round(6).to_string(index=False))
    print()
    print("   Both keep under a tenth of their width, both intervals cover the truth of zero, and")
    print("   neither is resolved - which is the correct answer for a channel that does nothing.")
    print("   The null result was the most precise thing anybody knew about these two channels.")

    print("\n" + "=" * 98)
    print("A PRIOR ON ONE CHANNEL IS NOT A CLAIM ABOUT ONE CHANNEL")
    print("=" * 98)
    one = calibrate(panel, priors(["social-pago"]))
    ols = baseline.returns(truth).set_index("channel")
    posterior = one.transfer(truth).set_index("channel")
    widths = one.table().set_index("channel")
    rows = []
    for name in baseline.channels:
        estimate = float(ols.loc[name, "marginal_return"])
        rows.append(
            {
                "channel": name,
                "ols_return": estimate,
                "posterior_return": float(posterior.loc[name, "posterior_return"]),
                "return_moved_by": float(posterior.loc[name, "posterior_return"]) / estimate,
                "width_kept": float(widths.loc[name, "width_kept"]),
            }
        )
    print(pd.DataFrame(rows).round(6).to_string(index=False))
    print()
    print("   One experiment, on one channel. Every other channel's reported return moved, two of")
    print("   them by more than half again, while their widths moved by less than five per cent.")
    print("   The spend columns correlate above 0.83, so a prior on one of them is information")
    print("   about all of them - and the transfer arrives as a shift in location that nothing on")
    print("   the chart marks, because the interval beside it looks the same as it did before.")

    print("\n" + "=" * 98)
    print("AND THE BRIDGE RESTS ON THE PARAMETER THE FIT CANNOT SEE")
    print("=" * 98)
    rows = []
    for multiple in SATURATIONS:
        fitted = fit(panel, saturation_at=multiple)
        transfer = calibrate(
            panel,
            {
                name: prior_from_holdout(lifts[name], fitted, name, reach=reach, spend=spend[name])
                for name in resolved
            },
            saturation_at=multiple,
        ).transfer(truth)
        row = transfer.set_index("channel").loc["social-pago"]
        rows.append(
            {
                "saturation_at": multiple,
                "factor": average_to_marginal(multiple),
                "r_squared": fitted.r_squared,
                "posterior_return": float(row["posterior_return"]),
                "times_the_truth": float(row["times_the_truth"]),
                "width_over_truth": float(row["interval_width_over_truth"]),
                "covers_truth": bool(row["covers_truth"]),
            }
        )
    grid = pd.DataFrame(rows)
    grid["fit_loss"] = grid["r_squared"].max() - grid["r_squared"]
    print(grid.round(6).to_string(index=False))
    print()
    best = grid.loc[grid["r_squared"].idxmax()]
    print(f"   Every row fits within {grid['fit_loss'].max():.6f} of R-squared of every other, and")
    print("   across them the calibrated answer for social-pago runs from")
    print(
        f"   {grid['times_the_truth'].min():.2f} to {grid['times_the_truth'].max():.2f} times the"
        f" truth."
    )
    print(f"   The best-fitting row is not the true one: it is k = {best['saturation_at']:.1f},")
    print(f"   which returns {best['times_the_truth']:.2f} times the truth in an interval")
    print(f"   {best['width_over_truth']:.2f} times the size of the quantity it estimates. A")
    print("   practitioner choosing the saturation point by fit, which is the only way it can be")
    print("   chosen, lands on that row.")
    print()
    print(
        f"   These four widths run {grid['width_over_truth'].min():.2f} to"
        f" {grid['width_over_truth'].max():.2f} times the truth, against 1.64 for this same model"
    )
    print("   uncalibrated and 0.13 for the holdout itself. The transfer puts the model in the")
    print("   experiment's precision class - and where inside that class it lands, along with how")
    print("   far the answer sits from the truth, is settled by a parameter the fit cannot see.")
    print()
    print("   That is the whole wave in one table. Calibration transfers precision faithfully, and")
    print("   it transfers everything else just as faithfully: the experiment's own sampling")
    print("   error, and the modeller's choice of a parameter the data cannot see.")


if __name__ == "__main__":
    main()
