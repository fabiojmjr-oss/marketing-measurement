"""What a media mix model can establish about an account, against what the holdout established.

Run:
    python examples/05_the_model_that_replaces_the_experiment.py

Waves 2 to 4 priced the holdout: what it can resolve, what it costs, how to monitor it. A media
mix model is what gets built when nobody will pay that. This example fits one on the same account,
with the generator's own transforms handed to it - the most favourable case any real model gets -
and asks what it can support.
"""

from __future__ import annotations

import pandas as pd

from mktlab.attribution import geo_lift
from mktlab.mmm import fit, transform_grid, variance_inflation
from mktlab.mmm.model import design_matrix
from mktlab.synth import AUDIENCE, CHANNELS, GEO, MEDIA_MIX, generate_dataset

FIT_LOSS = 0.01


def main() -> None:
    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", 30)
    data = generate_dataset()
    panel = data.spend_panel
    truth = data.media_truth

    print("THE PANEL, AND THE TWO THINGS NOBODY OBSERVES")
    print(
        f"   {MEDIA_MIX.weeks} weeks of weekly spend per channel and the conversions it produced."
    )
    print(f"   Built with a carryover of {MEDIA_MIX.adstock:.2f} and returns bending at")
    print(f"   {MEDIA_MIX.saturation_at:.2f} times each channel's average weekly spend. Neither of")
    print("   those is in the data, and a model has to guess both.")
    print()
    print(truth.round(6).to_string(index=False))
    print()
    print("   Read the two return columns apart, because conflating them is a category error. The")
    print("   average return is what switching the channel off would cost per unit of its spend -")
    print(
        "   which is what the holdout measures. The marginal return is the derivative at the spend"
    )
    print("   level it is running at - which is what a regression coefficient estimates. Where the")
    print("   response is bending the second is much smaller than the first.")

    print("\n" + "=" * 100)
    print("THE CHANNELS MOVE TOGETHER, BECAUSE THAT IS HOW PLANS ARE WRITTEN")
    print("=" * 100)
    spends = panel[[name for name in panel.columns if name.startswith("spend_")]]
    correlations = spends.corr()
    print(correlations.round(4).to_string())
    print()
    matrix, names, _, _ = design_matrix(panel, MEDIA_MIX.adstock, MEDIA_MIX.saturation_at)
    factors = variance_inflation(matrix[:, : len(CHANNELS)])
    inflation = pd.DataFrame(
        {
            "channel": sorted(profile.channel for profile in CHANNELS),
            "variance_inflation": factors,
            "standard_error_multiple": factors**0.5,
        }
    )
    print(inflation.round(4).to_string(index=False))
    print()
    print(f"   The budget swings {MEDIA_MIX.budget_swing:.0%} week to week and each channel moves")
    off_diagonal = correlations.to_numpy()[correlations.to_numpy() < 1.0].min()
    print(f"   only {MEDIA_MIX.idiosyncratic_swing:.0%} on its own, so every pair of spend")
    print(f"   columns correlates above {off_diagonal:.2f} and every confidence interval comes")
    print("   out two and a half to three times wider than it would have been on independent")
    print("   spend. Nothing pathological was done to the plan: it was written as shares of a")
    print("   budget, which is how plans are written.")

    print("\n" + "=" * 100)
    print("THE MODEL, FITTED WITH THE RIGHT TRANSFORMS - THE BEST CASE THERE IS")
    print("=" * 100)
    fitted = fit(panel)
    print(f"   R-squared {fitted.r_squared:.4f}, residual sd {fitted.residual_sd:.3f} against a")
    print(f"   generator noise of {MEDIA_MIX.noise_sd:.1f}, {fitted.df:.0f} degrees of freedom,")
    print(f"   condition number {fitted.condition_number:.2f} on the centred channel block.")
    print()
    print(fitted.table().round(4).to_string(index=False))
    print()
    resolved = [
        channel
        for index, channel in enumerate(fitted.channels)
        if not fitted.interval(index)[0] <= 0.0 <= fitted.interval(index)[1]
    ]
    print(f"   Channels the model can distinguish from zero: {len(resolved)} of {len(CHANNELS)}")
    print(f"   ({', '.join(resolved)}). Every other interval spans both signs.")

    print("\n" + "=" * 100)
    print("AS RETURNS, AGAINST THE TRUTH IT WAS BUILT FROM")
    print("=" * 100)
    returns = fitted.returns(truth)
    print(returns.round(6).to_string(index=False))
    print()
    covered = int(returns["covers_truth"].sum())
    print(f"   All {covered} of {len(returns)} intervals contain the truth, so the model is not")
    print("   lying. It is uninformative: the interval on email is fourteen times the size of the")
    print("   return it is estimating, and busca-marca's point estimate is negative for a channel")
    print(
        "   whose true effect is zero. The model is honest and the deck shows the point estimates."
    )

    print("\n" + "=" * 100)
    print("THE RANGE THAT FITS EQUALLY WELL IS THE CONFIDENCE INTERVAL")
    print("=" * 100)
    index = fitted.channels.index("social-pago")
    rows = []
    for loss in (0.001, 0.005, FIT_LOSS):
        low, high = fitted.equivalent_range(index, loss)
        rows.append({"r_squared_loss": loss, "low": low, "high": high, "width": high - low})
    low, high = fitted.interval(index)
    rows.append(
        {
            "r_squared_loss": float("nan"),
            "low": low,
            "high": high,
            "width": high - low,
        }
    )
    frame = pd.DataFrame(rows)
    frame.index = ["", "", "", "the 95% interval"]
    print(frame.round(4).to_string())
    print()
    print(
        "   This is the demonstration everybody asks a collinear model for - 'here is a completely"
    )
    print(
        "   different answer that fits just as well' - and what comes out of computing it properly"
    )
    print("   is that there is nothing new in it. The profile has a closed form, and it is the")
    print("   standard error rescaled. The 95% interval is the set of coefficients costing about")
    print("   0.0068 of R-squared. The model was already saying this in the column nobody prints.")

    print("\n" + "=" * 100)
    print("THE TRANSFORMS IT HAD TO GUESS")
    print("=" * 100)
    grid = transform_grid(
        panel,
        carryovers=(0.0, 0.2, 0.45, 0.6, 0.8),
        saturations=(0.5, 1.3, 3.0, 10.0),
        truth=truth,
    )
    print(grid.head(10).round(6).to_string(index=False))
    print("   ...")
    near = grid[grid["fit_loss"] <= FIT_LOSS]
    print()
    print(
        f"   {len(near)} of {len(grid)} designs fit within {FIT_LOSS} of the best, and across them"
    )
    print(f"   the implied social-pago return runs {near['times_the_truth'].min():.2f}x to")
    print(f"   {near['times_the_truth'].max():.2f}x the truth.")
    print()
    print("   But read the grid by column rather than as a lump, because the lazy version of this")
    print(
        "   claim is wrong. The fit does identify the carryover: moving it from 0.45 to 0.60 costs"
    )
    print("   0.0047 of R-squared and moves the return by a quarter. It is nearly blind to the")
    print("   saturation point: at the right carryover, every value from 0.5 to 10.0 - a")
    print("   twentyfold range - sits within 0.0008 of the best fit and moves the return by one")
    print("   per cent. One of the two guesses matters and is recoverable; the other barely")
    print("   matters here at all.")

    print("\n" + "=" * 100)
    print("AND WHAT HAPPENS WHEN THE MODEL OMITS SOMETHING")
    print("=" * 100)
    bare = fit(panel, trend=False, seasonality=False)
    print(f"   With the trend and seasonal terms: R-squared {fitted.r_squared:.4f}")
    print(f"   Without them:                      R-squared {bare.r_squared:.4f}")
    print()
    print(bare.returns(truth).round(6).to_string(index=False))
    print()
    print("   Of the three channels with a real effect, two come back negative - email at five")
    print("   times the truth in the wrong direction - and social-pago is confidently 1.85 times")
    print("   its real marginal return, confidently because that interval excludes zero. The")
    print("   reassuring part is that the fit collapses from 0.84 to 0.24, so this")
    print("   misspecification is visible. The unreassuring part is that the intervals still")
    print("   cover the truth, which means a model can be badly wrong about every channel and")
    print("   never be caught by its own coverage.")

    print("\n" + "=" * 100)
    print("THE SAME ACCOUNT, MEASURED BOTH WAYS")
    print("=" * 100)
    print("   The two instruments do not estimate the same quantity - the holdout measures the")
    print("   average return over the period, the coefficient measures the marginal return at the")
    print("   current spend - so comparing their point estimates would be a mistake. What compares")
    print("   is each one's precision relative to the quantity it is estimating.")
    print()
    model_view = returns.set_index("channel")
    declared = truth.set_index("channel")
    rows = []
    for profile in CHANNELS:
        arm = data.geo_experiments[data.geo_experiments["channel"] == profile.channel]
        lift = geo_lift(arm, split=GEO.split, channel=profile.channel)
        scale = AUDIENCE.users / profile.spend
        low, high = lift.interval
        average = float(declared.loc[profile.channel, "conversions_per_unit_spend"])
        rows.append(
            {
                "channel": profile.channel,
                "holdout_width_over_truth": (high - low) * scale / average
                if average
                else float("nan"),
                "model_width_over_truth": float(
                    model_view.loc[profile.channel, "interval_width_over_truth"]
                ),
                "holdout_resolved": bool(lift.significant),
                "model_resolved": profile.channel in resolved,
            }
        )
    comparison = pd.DataFrame(rows)
    comparison["model_times_wider"] = (
        comparison["model_width_over_truth"] / comparison["holdout_width_over_truth"]
    )
    print(comparison.round(4).to_string(index=False))
    print()
    print(
        f"   The holdout resolved {int(comparison['holdout_resolved'].sum())} channels of five and"
    )
    print(
        f"   the model resolved {int(comparison['model_resolved'].sum())}. Where both have a truth"
    )
    print(
        "   to be judged against, the model's interval is between eleven and thirteen times wider"
    )
    print("   relative to what it is estimating.")
    print()
    print("   That is the trade stated honestly. The holdout costs 260 region-weeks per channel")
    print("   and thirteen weeks of calendar, and across five of them it resolved three. The")
    print("   model costs nothing, answers about all five at once, and its answer on four of")
    print("   them is 'somewhere between a negative number and several times the truth'. Both")
    print("   are real instruments. Only one is usually presented with its width attached.")


if __name__ == "__main__":
    main()
