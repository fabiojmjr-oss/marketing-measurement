"""The holdout and the return figures, against exact cases.

The noiseless panel in ``conftest`` has a difference in differences of exactly +0.04 with no
spread between regions. An estimator that cannot return that exactly has no business returning a
confidence interval on real data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from mktlab.attribution import (
    RETURN_COLUMNS,
    GeoLift,
    geo_lift,
    iroas,
    returns,
    roas,
)
from mktlab.attribution.incrementality import _welch_df


def test_a_noiseless_holdout_returns_the_exact_lift(noiseless_panel: pd.DataFrame) -> None:
    lift = geo_lift(noiseless_panel, split=2, channel="X")
    assert lift.lift == pytest.approx(0.04)
    assert lift.treated_geos == 2
    assert lift.holdout_geos == 2
    assert lift.standard_error == 0.0


def test_a_noiseless_holdout_has_a_degenerate_interval_rather_than_a_crash(
    noiseless_panel: pd.DataFrame,
) -> None:
    """Zero spread is a limit, not an error: the interval is the point and the p-value is zero."""
    lift = geo_lift(noiseless_panel, split=2, channel="X")
    assert lift.interval == (pytest.approx(0.04), pytest.approx(0.04))
    assert lift.p_value == 0.0
    assert lift.significant


def test_a_lift_of_exactly_zero_with_no_spread_is_not_significant() -> None:
    """The other side of the same limit: nothing happened, and the test must not claim it did."""
    lift = GeoLift(
        channel="X",
        treated_geos=2,
        holdout_geos=2,
        split=2,
        lift=0.0,
        standard_error=0.0,
        df=2.0,
    )
    assert lift.p_value == 1.0
    assert not lift.significant


def test_the_sign_is_set_so_that_a_positive_lift_means_the_channel_helps(
    noiseless_panel: pd.DataFrame,
) -> None:
    """Flipping which regions were held out has to flip the sign, and nothing else."""
    flipped = noiseless_panel.copy()
    flipped["holdout"] = ~flipped["holdout"].astype(bool)
    assert geo_lift(flipped, split=2).lift == pytest.approx(-0.04)


def test_a_common_trend_does_not_reach_the_estimate(noiseless_panel: pd.DataFrame) -> None:
    """The reason the difference in differences exists, as arithmetic.

    Adding 0.02 to every region's rate after the split - treated and holdout alike - is exactly
    what a before-and-after reading would credit to the channel. The estimate must not move.
    """
    trended = noiseless_panel.copy()
    after = trended["week"] > 2
    trended.loc[after, "conversions"] = trended.loc[after, "conversions"] + 20
    assert geo_lift(trended, split=2).lift == pytest.approx(0.04)


def test_a_permanent_difference_between_regions_does_not_reach_the_estimate(
    noiseless_panel: pd.DataFrame,
) -> None:
    """The other thing it removes: a region that always converts more, in both phases."""
    shifted = noiseless_panel.copy()
    always = shifted["geo"] == "G0"
    shifted.loc[always, "conversions"] = shifted.loc[always, "conversions"] + 50
    assert geo_lift(shifted, split=2).lift == pytest.approx(0.04)


def test_a_split_outside_the_test_is_refused(noiseless_panel: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="no weeks"):
        geo_lift(noiseless_panel, split=4)
    with pytest.raises(ValueError, match="no weeks"):
        geo_lift(noiseless_panel, split=0)


def test_a_test_with_no_holdout_is_refused(noiseless_panel: pd.DataFrame) -> None:
    """Without regions on both sides there is no counterfactual, which is the whole point."""
    one_sided = noiseless_panel.copy()
    one_sided["holdout"] = False
    with pytest.raises(ValueError, match="both sides of the switch"):
        geo_lift(one_sided, split=2)


def test_the_interval_widens_with_the_spread_between_regions() -> None:
    """Two panels, same lift, different region-level spread. Only the interval may differ."""
    rows = []
    for geo in range(8):
        holdout = geo >= 4
        for week in (1, 2):
            rows.append(
                {
                    "geo": f"G{geo}",
                    "week": week,
                    "holdout": holdout,
                    "users": 1_000,
                    "conversions": 100,
                }
            )
    tight = pd.DataFrame(rows)
    tight.loc[(tight["week"] == 2) & tight["holdout"], "conversions"] = 60
    tight.loc[(tight["week"] == 2) & ~tight["holdout"], "conversions"] = 100

    loose = tight.copy()
    noisy = (loose["week"] == 2) & (loose["geo"].isin(["G0", "G4"]))
    loose.loc[noisy, "conversions"] = loose.loc[noisy, "conversions"] + 30

    narrow = geo_lift(tight, split=1)
    wide = geo_lift(loose, split=1)
    assert narrow.lift == pytest.approx(wide.lift)
    assert wide.standard_error > narrow.standard_error
    assert (wide.interval[1] - wide.interval[0]) > (narrow.interval[1] - narrow.interval[0])


def test_incremental_conversions_is_the_rate_scaled_to_the_population() -> None:
    lift = GeoLift("X", 20, 20, 13, lift=0.01, standard_error=0.001, df=38.0)
    assert lift.incremental_conversions(100_000) == pytest.approx(1_000.0)
    assert lift.incremental_conversions(0) == 0.0


def test_a_negative_population_is_refused() -> None:
    lift = GeoLift("X", 20, 20, 13, lift=0.01, standard_error=0.001, df=38.0)
    with pytest.raises(ValueError, match="cannot be negative"):
        lift.incremental_conversions(-1)


def test_the_verdict_says_not_distinguishable_when_the_interval_covers_zero() -> None:
    established = GeoLift("X", 20, 20, 13, lift=0.01, standard_error=0.001, df=38.0)
    silent = GeoLift("Y", 20, 20, 13, lift=0.0005, standard_error=0.001, df=38.0)
    assert "not distinguishable" not in established.verdict()
    assert "not distinguishable from nothing" in silent.verdict()
    assert "Y" in silent.verdict()


def test_roas_and_iroas_are_the_same_arithmetic_on_different_numerators() -> None:
    assert roas(100.0, 1_000.0, 50.0) == pytest.approx(5.0)
    assert iroas(20.0, 1_000.0, 50.0) == pytest.approx(1.0)


@pytest.mark.parametrize("function", [roas, iroas])
def test_a_ratio_against_no_spend_is_refused(function: object) -> None:
    with pytest.raises(ValueError, match="spend must be positive"):
        function(100.0, 0.0, 50.0)  # type: ignore[operator]


def _lifts() -> dict[str, GeoLift]:
    return {
        "works": GeoLift("works", 20, 20, 13, lift=0.01, standard_error=0.001, df=38.0),
        "silent": GeoLift("silent", 20, 20, 13, lift=0.0002, standard_error=0.001, df=38.0),
    }


def test_returns_reads_absolute_credit_rather_than_rescaling_a_share() -> None:
    """The defect this function had: multiplying a share by total conversions.

    That spreads the untouched conversions across the channels, which is precisely the rescaling
    :func:`unattributable` exists to warn about. The credited column is absolute, and the ROAS
    below follows from it and from nothing else.
    """
    credited = pd.DataFrame(
        [
            {"channel": "works", "credited": 400.0, "share": 0.4},
            {"channel": "silent", "credited": 600.0, "share": 0.6},
        ]
    )
    truth = pd.DataFrame(
        [
            {"channel": "works", "spend": 10_000.0},
            {"channel": "silent", "spend": 10_000.0},
        ]
    )
    priced = returns(credited, _lifts(), truth, reach=100_000, value_per_conversion=50.0)
    assert tuple(priced.columns) == RETURN_COLUMNS
    row = priced.set_index("channel").loc["works"]
    assert float(row["credited_conversions"]) == pytest.approx(400.0)
    assert float(row["roas"]) == pytest.approx(400.0 * 50.0 / 10_000.0)
    assert float(row["incremental_conversions"]) == pytest.approx(1_000.0)
    assert float(row["iroas"]) == pytest.approx(5.0)
    assert bool(row["established"])
    assert float(row["ratio"]) == pytest.approx(2.0 / 5.0)


def test_returns_refuses_a_ratio_where_the_holdout_established_nothing() -> None:
    """A ratio against an unmeasured denominator reads as evidence and is not."""
    credited = pd.DataFrame([{"channel": "silent", "credited": 600.0, "share": 1.0}])
    truth = pd.DataFrame([{"channel": "silent", "spend": 10_000.0}])
    priced = returns(credited, _lifts(), truth, reach=100_000, value_per_conversion=50.0)
    row = priced.iloc[0]
    assert not bool(row["established"])
    assert np.isnan(float(row["ratio"]))
    assert float(row["roas"]) == pytest.approx(3.0)


def test_a_channel_with_no_holdout_is_named_rather_than_silently_dropped() -> None:
    credited = pd.DataFrame([{"channel": "untested", "credited": 100.0, "share": 1.0}])
    truth = pd.DataFrame([{"channel": "untested", "spend": 10_000.0}])
    with pytest.raises(KeyError, match="no holdout for 'untested'"):
        returns(credited, _lifts(), truth, reach=100_000, value_per_conversion=50.0)


def _two_region_panel() -> pd.DataFrame:
    """One region treated, one held out. A real design, and an untestable one."""
    rows = []
    for geo in range(2):
        for week in (1, 2):
            switched_off = geo == 1 and week == 2
            rows.append(
                {
                    "geo": f"G{geo}",
                    "week": week,
                    "holdout": geo == 1,
                    "users": 1_000,
                    "conversions": 60 if switched_off else 100,
                }
            )
    return pd.DataFrame(rows)


def test_a_test_with_one_region_a_side_returns_the_lift_and_says_why_it_is_untested() -> None:
    """The estimate exists; its error does not. Both facts have to survive to the caller."""
    lift = geo_lift(_two_region_panel(), split=1, channel="X")
    assert lift.lift == pytest.approx(0.04)
    assert lift.untested_because
    assert "two on each side" in lift.untested_because
    assert np.isnan(lift.standard_error)
    assert np.isnan(lift.p_value)
    assert all(np.isnan(bound) for bound in lift.interval)
    assert not lift.significant
    assert "untested" in lift.verdict()


def test_an_untestable_design_does_not_arrive_as_a_measured_zero() -> None:
    """The failure mode the reason field exists to prevent.

    Without it, a design with nothing to compare against reads through ``significant`` exactly
    like a channel that was measured and found to do nothing - which is the difference between
    "we need more regions" and "switch the channel off".
    """
    untested = geo_lift(_two_region_panel(), split=1, channel="X")
    measured = GeoLift("Y", 20, 20, 13, lift=0.0002, standard_error=0.001, df=38.0)
    assert not untested.significant
    assert not measured.significant
    assert untested.untested_because != ""
    assert measured.untested_because == ""
    assert "not distinguishable from nothing" in measured.verdict()
    assert "not distinguishable from nothing" not in untested.verdict()


def test_an_untested_design_is_never_priced_as_an_established_return() -> None:
    credited = pd.DataFrame([{"channel": "X", "credited": 100.0, "share": 1.0}])
    truth = pd.DataFrame([{"channel": "X", "spend": 1_000.0}])
    lifts = {"X": geo_lift(_two_region_panel(), split=1, channel="X")}
    row = returns(credited, lifts, truth, reach=100_000, value_per_conversion=50.0).iloc[0]
    assert not bool(row["established"])
    assert np.isnan(float(row["ratio"]))


def test_the_closed_form_welch_degrees_of_freedom_match_scipy_where_scipy_is_defined() -> None:
    """The df stopped coming from scipy to remove a warning, so it is checked against scipy."""
    rng = np.random.default_rng(11)
    for _ in range(20):
        kept = rng.normal(0.0, 1.0, size=rng.integers(3, 15))
        lost = rng.normal(0.0, 2.0, size=rng.integers(3, 15))
        expected = float(stats.ttest_ind(kept, lost, equal_var=False).df)
        assert _welch_df(kept, lost) == pytest.approx(expected)


def test_the_degrees_of_freedom_of_a_noiseless_panel_are_a_number_not_a_nan(
    noiseless_panel: pd.DataFrame,
) -> None:
    """Zero variance on both sides is 0/0. scipy answers it with a warning; this takes the limit."""
    lift = geo_lift(noiseless_panel, split=2)
    assert lift.df == pytest.approx(2.0)
    assert np.isfinite(lift.df)
