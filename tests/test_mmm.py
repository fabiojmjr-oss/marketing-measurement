"""The media mix model, against controls where the answer is known.

Two controls carry this file. On a panel with independent spend and no noise the model must recover
the coefficients it was built from, because a regression that cannot do that on a noiseless
orthogonal panel is not evidence about anything. And the range of coefficients that fit within a given
loss of fit must equal the standard error rescaled, which is the identity the module's central claim
rests on.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mktlab.mmm import (
    FIT_COLUMNS,
    GRID_COLUMNS,
    RETURN_COLUMNS,
    channel_names,
    channel_of,
    design_matrix,
    fit,
    spend_columns,
    transform_grid,
    variance_inflation,
)
from mktlab.synth import CHANNELS, MEDIA_MIX, Dataset, adstock, saturate


def orthogonal_panel(
    coefficients: dict[str, float],
    weeks: int = 200,
    noise: float = 0.0,
    carryover: float = 0.0,
    saturation_at: float = 1e6,
    seed: int = 3,
) -> pd.DataFrame:
    """A panel whose columns are independent by construction and whose answer is declared.

    The half point is computed the way :func:`design_matrix` computes it - a multiple of the channel's
    own mean spend - so that a model fitted with the same multiple sees exactly the columns the panel
    was built from and must recover the coefficients. Building it any other way makes the control case
    fail for a reason that has nothing to do with the model: the first version of this helper used one
    absolute half point for every channel, and the recovered coefficients came back 1.4% out because
    each channel's mean spend differed from the others by that much.

    A large multiple makes the saturation curve linear over the range of the data, which is what makes
    the declared coefficient checkable directly.
    """
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame({"week": np.arange(1, weeks + 1)})
    response = np.zeros(weeks)
    for channel, coefficient in coefficients.items():
        spend = 1_000.0 + 300.0 * rng.standard_normal(weeks)
        frame[f"spend_{channel}"] = spend
        half_point = saturation_at * float(spend.mean()) / (1.0 - carryover)
        response = response + coefficient * saturate(adstock(spend, carryover), half_point)
    frame["conversions"] = 500.0 + response + noise * rng.standard_normal(weeks)
    frame["baseline"] = 500.0
    return frame


def test_spend_columns_are_found_and_named() -> None:
    panel = orthogonal_panel({"a": 1.0, "b": 2.0})
    assert spend_columns(panel) == ("spend_a", "spend_b")
    assert channel_of("spend_a") == "a"
    assert channel_names() == tuple(sorted(profile.channel for profile in CHANNELS))


def test_a_noiseless_orthogonal_panel_recovers_its_own_coefficients() -> None:
    """The control case. Without this, nothing else in the module is evidence."""
    declared = {"a": 4_000.0, "b": 9_000.0, "c": 1_500.0}
    panel = orthogonal_panel(declared, noise=0.0)
    fitted = fit(panel, carryover=0.0, saturation_at=1e6, trend=False, seasonality=False)
    recovered = dict(zip(fitted.channels, fitted.coefficients, strict=True))
    for channel, coefficient in declared.items():
        assert recovered[channel] == pytest.approx(coefficient, rel=1e-6), channel
    assert fitted.r_squared == pytest.approx(1.0, abs=1e-12)
    assert fitted.residual_sd == pytest.approx(0.0, abs=1e-6)


def test_independent_spend_has_no_variance_inflation() -> None:
    """The other end of the module's headline: inflation is a property of the plan, not the method."""
    panel = orthogonal_panel({"a": 1.0, "b": 1.0, "c": 1.0}, weeks=500)
    matrix, _, _, _ = design_matrix(panel, 0.0, 1e6, trend=False, seasonality=False)
    assert np.allclose(variance_inflation(matrix), 1.0, atol=0.05)


def test_a_duplicated_column_has_unbounded_variance_inflation() -> None:
    """The limit taken explicitly: two identical columns cannot be told apart at all."""
    panel = orthogonal_panel({"a": 1.0, "b": 1.0})
    panel["spend_b"] = panel["spend_a"]
    matrix, _, _, _ = design_matrix(panel, 0.0, 1e6, trend=False, seasonality=False)
    factors = variance_inflation(matrix)
    assert np.isinf(factors).all()


def test_variance_inflation_rises_with_correlation() -> None:
    rng = np.random.default_rng(11)
    base = rng.standard_normal(400)
    for share, previous in ((0.1, 0.0), (0.5, 0.0), (0.9, 0.0)):
        matrix = np.column_stack([base, share * base + (1.0 - share) * rng.standard_normal(400)])
        factors = variance_inflation(matrix)
        assert factors.min() > previous
        assert factors.min() > 1.0
        assert share > 0.0


def test_a_panel_with_fewer_weeks_than_parameters_is_refused() -> None:
    panel = orthogonal_panel({"a": 1.0, "b": 1.0, "c": 1.0}, weeks=6)
    with pytest.raises(ValueError, match="more rows than it has things to estimate"):
        fit(panel)


def test_the_design_matrix_carries_the_terms_it_was_asked_for() -> None:
    panel = orthogonal_panel({"a": 1.0, "b": 1.0})
    _, names, _, _ = design_matrix(panel, 0.45, 1.3)
    assert names == ("a", "b", "trend", "seasonal_sin", "seasonal_cos")
    _, bare, _, _ = design_matrix(panel, 0.45, 1.3, trend=False, seasonality=False)
    assert bare == ("a", "b")


def test_the_half_point_scales_with_each_channels_own_spend() -> None:
    """One saturation setting has to cover channels of very different sizes."""
    panel = orthogonal_panel({"small": 1.0, "large": 1.0})
    # Exactly ten times the other column, not a separate draw ten times larger: two independent
    # draws have means a per cent or so apart, which is enough to fail an assertion about a factor
    # of ten and has nothing to do with what is being tested.
    panel["spend_large"] = panel["spend_small"] * 10.0
    _, names, half_points, per_week = design_matrix(panel, 0.0, 2.0, trend=False, seasonality=False)
    lookup = dict(zip(names, half_points, strict=True))
    weekly = dict(zip(names, per_week, strict=True))
    assert lookup["large"] == pytest.approx(10.0 * lookup["small"], rel=1e-6)
    assert lookup["small"] == pytest.approx(2.0 * weekly["small"])


def test_the_fit_reports_the_noise_it_was_given() -> None:
    panel = orthogonal_panel({"a": 4_000.0, "b": 9_000.0}, noise=25.0, weeks=400)
    fitted = fit(panel, carryover=0.0, saturation_at=1e6, trend=False, seasonality=False)
    assert fitted.residual_sd == pytest.approx(25.0, rel=0.1)
    assert 0.0 < fitted.r_squared < 1.0


def test_the_interval_is_the_coefficient_plus_and_minus_t_times_the_error() -> None:
    panel = orthogonal_panel({"a": 4_000.0, "b": 9_000.0}, noise=25.0)
    fitted = fit(panel, carryover=0.0, saturation_at=1e6, trend=False, seasonality=False)
    low, high = fitted.interval(0)
    half = fitted.critical_value * float(fitted.standard_errors[0])
    assert low == pytest.approx(float(fitted.coefficients[0]) - half)
    assert high == pytest.approx(float(fitted.coefficients[0]) + half)
    assert (high - low) / 2.0 == pytest.approx(half)


def test_the_equivalent_range_is_the_standard_error_rescaled() -> None:
    """The identity the module's central claim rests on, asserted rather than described.

    The furthest a coefficient can travel while the residual sum of squares rises by delta is its
    standard error times the root of delta over the residual variance. So the 95% interval is the set
    of coefficients costing a particular, computable loss of fit - and there is no second diagnostic
    hiding behind the standard error.
    """
    panel = orthogonal_panel({"a": 4_000.0, "b": 9_000.0}, noise=25.0)
    fitted = fit(panel, carryover=0.0, saturation_at=1e6, trend=False, seasonality=False)
    total = fitted.residual_sd**2 * fitted.df / (1.0 - fitted.r_squared)

    loss = 0.004
    low, high = fitted.equivalent_range(0, loss)
    expected = float(fitted.standard_errors[0]) * np.sqrt(loss * total / fitted.residual_sd**2)
    assert (high - low) / 2.0 == pytest.approx(expected, rel=1e-9)

    # And the loss of fit that the 95% interval corresponds to, from the same algebra.
    implied = fitted.critical_value**2 * fitted.residual_sd**2 / total
    matched = fitted.equivalent_range(0, implied)
    assert matched[0] == pytest.approx(fitted.interval(0)[0], rel=1e-9)
    assert matched[1] == pytest.approx(fitted.interval(0)[1], rel=1e-9)


def test_a_wider_loss_of_fit_allows_a_wider_range() -> None:
    panel = orthogonal_panel({"a": 4_000.0}, noise=25.0)
    fitted = fit(panel, carryover=0.0, saturation_at=1e6, trend=False, seasonality=False)
    narrow = fitted.equivalent_range(0, 0.001)
    wide = fitted.equivalent_range(0, 0.01)
    assert wide[0] < narrow[0] < narrow[1] < wide[1]


def test_a_non_positive_loss_of_fit_is_refused() -> None:
    panel = orthogonal_panel({"a": 4_000.0}, noise=25.0)
    fitted = fit(panel, carryover=0.0, saturation_at=1e6, trend=False, seasonality=False)
    with pytest.raises(ValueError, match="loss of fit must be positive"):
        fitted.equivalent_range(0, 0.0)


def test_the_marginal_factor_is_the_chain_rule_at_the_operating_point() -> None:
    """Checked against a difference quotient on the transform the model actually used."""
    panel = orthogonal_panel({"a": 4_000.0}, carryover=0.4, saturation_at=2.0)
    fitted = fit(panel, carryover=0.4, saturation_at=2.0, trend=False, seasonality=False)
    weekly = fitted.spend_per_week[0]
    half_point = fitted.half_points[0]
    step = weekly * 1e-6
    steady = lambda value: value / (1.0 - fitted.carryover)  # noqa: E731
    numerical = (
        saturate(np.array([steady(weekly + step)]), half_point)[0]
        - saturate(np.array([steady(weekly - step)]), half_point)[0]
    ) / (2.0 * step)
    assert fitted.marginal_factor(0) == pytest.approx(numerical, rel=1e-6)


def test_the_table_has_a_row_per_channel_and_nothing_else(full: Dataset) -> None:
    fitted = fit(full.spend_panel)
    table = fitted.table()
    assert tuple(table.columns) == FIT_COLUMNS
    assert list(table["channel"]) == list(fitted.channels)
    assert len(table) == len(CHANNELS)
    assert "trend" not in list(table["channel"])


def test_the_returns_table_is_empty_of_comparisons_without_a_truth(full: Dataset) -> None:
    """A real account has no truth column, and the honest state of those columns is nan."""
    returns = fit(full.spend_panel).returns()
    assert tuple(returns.columns) == RETURN_COLUMNS
    assert returns["truth"].isna().all()
    assert returns["times_the_truth"].isna().all()
    assert not returns["covers_truth"].any()


def test_the_returns_are_the_coefficients_through_the_chain_rule(full: Dataset) -> None:
    fitted = fit(full.spend_panel)
    returns = fitted.returns(full.media_truth).set_index("channel")
    for index, channel in enumerate(fitted.channels):
        expected = float(fitted.coefficients[index]) * fitted.marginal_factor(index)
        assert float(returns.loc[channel, "marginal_return"]) == pytest.approx(expected), channel


def test_a_model_given_the_right_transforms_covers_every_truth(full: Dataset) -> None:
    """The model is honest on this panel. What it is not is informative."""
    returns = fit(full.spend_panel).returns(full.media_truth)
    assert bool(returns["covers_truth"].all())


def test_only_one_channel_of_five_is_distinguishable_from_zero(full: Dataset) -> None:
    """The headline, asserted: collinear spend leaves the model almost silent."""
    fitted = fit(full.spend_panel)
    resolved = [
        channel
        for index, channel in enumerate(fitted.channels)
        if not fitted.interval(index)[0] <= 0.0 <= fitted.interval(index)[1]
    ]
    assert resolved == ["social-pago"]


def test_omitting_the_trend_collapses_the_fit_and_flips_signs(full: Dataset) -> None:
    """Misspecification is visible in the fit and invisible in the coverage."""
    good = fit(full.spend_panel)
    bare = fit(full.spend_panel, trend=False, seasonality=False)
    assert bare.r_squared < good.r_squared / 3.0
    truth = full.media_truth.set_index("channel")
    flipped = [
        channel
        for index, channel in enumerate(bare.channels)
        if float(truth.loc[channel, "marginal_conversions_per_unit_spend"]) > 0.0
        and float(bare.coefficients[index]) < 0.0
    ]
    assert len(flipped) == 2
    assert bool(bare.returns(full.media_truth)["covers_truth"].all())


def test_the_transform_grid_is_ordered_by_fit_and_names_the_best(full: Dataset) -> None:
    grid = transform_grid(
        full.spend_panel,
        carryovers=(0.2, 0.45, 0.6),
        saturations=(0.5, 1.3, 3.0),
        truth=full.media_truth,
    )
    assert tuple(grid.columns) == GRID_COLUMNS
    assert len(grid) == 9
    assert list(grid["fit_loss"]) == sorted(grid["fit_loss"])
    assert float(grid["fit_loss"].iloc[0]) == pytest.approx(0.0)
    assert float(grid["adstock"].iloc[0]) == pytest.approx(MEDIA_MIX.adstock)


def test_the_grid_identifies_the_carryover_and_not_the_saturation(full: Dataset) -> None:
    """The finding that corrects the lazy version of the complaint about transforms."""
    grid = transform_grid(
        full.spend_panel,
        carryovers=(0.2, 0.45, 0.6),
        saturations=(0.5, 1.3, 3.0, 10.0),
        truth=full.media_truth,
    ).set_index(["adstock", "saturation_at"])
    right = grid.xs(MEDIA_MIX.adstock, level="adstock")
    assert float(right["fit_loss"].max()) < 0.001, "saturation barely moves the fit"
    assert float(right["times_the_truth"].max() - right["times_the_truth"].min()) < 0.05

    wrong = grid.xs(0.6, level="adstock")
    assert float(wrong["fit_loss"].min()) > 0.004, "the carryover does move the fit"
    assert float(wrong["times_the_truth"].min()) > float(right["times_the_truth"].max())
