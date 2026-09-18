"""The spend panel, against the closed forms it was built from.

The load-bearing check is that the panel's declared returns are derived from wave 1's truth rather
than invented beside it: a channel's conversions per unit of spend has to be its rate lift times the
audience it reaches, divided by its spend, or the comparison between the model and the holdout is
between two different accounts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mktlab.synth import (
    AUDIENCE,
    CHANNELS,
    MEDIA_MIX,
    MEDIA_TRUTH_COLUMNS,
    SEED,
    Dataset,
    MediaMixProfile,
    adstock,
    conversions_per_unit_spend,
    generate_dataset,
    media_truth,
    saturate,
    spend_panel,
    true_rate_lift,
)


def test_the_declared_return_is_wave_ones_truth_divided_by_spend() -> None:
    """The identity that makes the model and the holdout comparable."""
    for profile in CHANNELS:
        expected = true_rate_lift(profile) * AUDIENCE.users / profile.spend
        assert conversions_per_unit_spend(profile) == pytest.approx(expected)


def test_the_declared_return_times_value_is_the_true_iroas_from_wave_two() -> None:
    """Checked against the figure the sizing document publishes, not against this module."""
    published = {"social-pago": 5.40, "email": 5.76, "busca-generica": 2.25}
    for profile in CHANNELS:
        if profile.channel not in published:
            continue
        iroas = conversions_per_unit_spend(profile) * AUDIENCE.value_per_conversion
        assert iroas == pytest.approx(published[profile.channel], abs=5e-3), profile.channel


def test_a_channel_with_no_effect_has_no_return() -> None:
    for profile in CHANNELS:
        if profile.true_effect == 0.0:
            assert conversions_per_unit_spend(profile) == 0.0


def test_adstock_with_no_carryover_is_the_series_itself() -> None:
    spend = np.array([1.0, 2.0, 3.0])
    assert adstock(spend, 0.0).tolist() == [1.0, 2.0, 3.0]


def test_adstock_carries_a_geometric_share_forward() -> None:
    """Worked out by hand: 1, then 2 + 0.5, then 3 + 0.5 * 2.5."""
    assert adstock(np.array([1.0, 2.0, 3.0]), 0.5).tolist() == [1.0, 2.5, 4.25]


def test_adstock_reaches_the_declared_steady_state() -> None:
    """Constant spend accumulates to spend over one minus the carryover, which is the closed form."""
    for carryover in (0.0, 0.3, 0.45, 0.9):
        series = adstock(np.full(400, 10.0), carryover)
        assert series[-1] == pytest.approx(10.0 / (1.0 - carryover), rel=1e-9)


def test_a_carryover_outside_the_unit_interval_is_refused() -> None:
    with pytest.raises(ValueError, match=r"must be in \[0, 1\)"):
        adstock(np.array([1.0]), 1.0)
    with pytest.raises(ValueError, match=r"must be in \[0, 1\)"):
        adstock(np.array([1.0]), -0.1)


def test_saturation_is_zero_at_zero_and_a_half_at_the_half_point() -> None:
    assert saturate(np.array([0.0]), 5.0)[0] == 0.0
    assert saturate(np.array([5.0]), 5.0)[0] == pytest.approx(0.5)
    assert saturate(np.array([1e12]), 5.0)[0] == pytest.approx(1.0, abs=1e-9)


def test_saturation_rises_with_a_falling_slope() -> None:
    """The minimum a response curve has to do to be one."""
    spend = np.linspace(0.1, 100.0, 200)
    response = saturate(spend, 10.0)
    assert np.all(np.diff(response) > 0.0)
    slopes = np.diff(response) / np.diff(spend)
    assert np.all(np.diff(slopes) < 0.0)


def test_a_non_positive_half_point_is_refused() -> None:
    with pytest.raises(ValueError, match="half point must be positive"):
        saturate(np.array([1.0]), 0.0)


def test_the_marginal_return_is_below_the_average_where_the_response_bends() -> None:
    truth = media_truth().set_index("channel")
    for profile in CHANNELS:
        if profile.true_effect == 0.0:
            continue
        row = truth.loc[profile.channel]
        assert (
            0.0
            < float(row["marginal_conversions_per_unit_spend"])
            < float(row["conversions_per_unit_spend"])
        ), profile.channel


def test_the_marginal_return_matches_a_numerical_derivative() -> None:
    """The chain rule, checked against a difference quotient rather than against itself."""
    design = MEDIA_MIX
    truth = media_truth().set_index("channel")
    for profile in CHANNELS:
        if profile.true_effect == 0.0:
            continue
        weekly = profile.spend / design.weeks
        half_point = design.saturation_at * weekly / (1.0 - design.adstock)
        steady = weekly / (1.0 - design.adstock)
        average = float(truth.loc[profile.channel, "conversions_per_unit_spend"])
        ceiling = average * weekly / saturate(np.array([steady]), half_point)[0]

        step = weekly * 1e-6
        higher = (weekly + step) / (1.0 - design.adstock)
        lower = (weekly - step) / (1.0 - design.adstock)
        numerical = (
            ceiling
            * (
                saturate(np.array([higher]), half_point)[0]
                - saturate(np.array([lower]), half_point)[0]
            )
            / (2.0 * step)
        )
        assert float(truth.loc[profile.channel, "marginal_conversions_per_unit_spend"]) == (
            pytest.approx(numerical, rel=1e-6)
        ), profile.channel


def test_the_media_truth_table_has_one_row_per_channel() -> None:
    truth = media_truth()
    assert tuple(truth.columns) == MEDIA_TRUTH_COLUMNS
    assert len(truth) == len(CHANNELS)
    assert set(truth["channel"]) == {profile.channel for profile in CHANNELS}
    assert truth["spend_per_week"].sum() == pytest.approx(
        sum(profile.spend for profile in CHANNELS) / MEDIA_MIX.weeks
    )


def test_the_panel_has_a_row_per_week_and_a_column_per_channel(full: Dataset) -> None:
    panel = full.spend_panel
    assert len(panel) == MEDIA_MIX.weeks
    assert list(panel["week"]) == list(range(1, MEDIA_MIX.weeks + 1))
    for profile in CHANNELS:
        assert f"spend_{profile.channel}" in panel.columns
    assert "conversions" in panel.columns
    assert "baseline" in panel.columns


def test_every_week_spends_something_on_every_channel(full: Dataset) -> None:
    for profile in CHANNELS:
        assert (full.spend_panel[f"spend_{profile.channel}"] > 0.0).all(), profile.channel


def test_the_average_weekly_spend_is_near_the_declared_level(full: Dataset) -> None:
    """The plan's level, recovered from the draw: within 5% over a hundred and four weeks."""
    for profile in CHANNELS:
        mean = float(full.spend_panel[f"spend_{profile.channel}"].mean())
        assert mean == pytest.approx(profile.spend / MEDIA_MIX.weeks, rel=0.05), profile.channel


def test_the_channels_move_together_because_the_budget_does(full: Dataset) -> None:
    """The panel is built to be collinear, so the collinearity is asserted rather than hoped for."""
    columns = [f"spend_{profile.channel}" for profile in CHANNELS]
    correlations = full.spend_panel[columns].corr().to_numpy()
    off_diagonal = correlations[~np.eye(len(columns), dtype=bool)]
    assert off_diagonal.min() > 0.8
    assert off_diagonal.max() < 1.0


def test_the_baseline_is_the_declared_level_trend_and_season(full: Dataset) -> None:
    """No marketing in it at all, which is what makes it the baseline."""
    weeks = np.arange(MEDIA_MIX.weeks, dtype=float)
    seasonal = (
        MEDIA_MIX.seasonal_amplitude
        * MEDIA_MIX.base_conversions
        * np.sin(2.0 * np.pi * weeks / MEDIA_MIX.seasonal_period)
    )
    expected = MEDIA_MIX.base_conversions + MEDIA_MIX.weekly_trend * weeks + seasonal
    assert np.allclose(full.spend_panel["baseline"].to_numpy(), expected)


def test_conversions_sit_above_the_baseline_on_average(full: Dataset) -> None:
    """Marketing adds something, so the response has to be positive on average."""
    panel = full.spend_panel
    residual = (panel["conversions"] - panel["baseline"]).to_numpy()
    assert residual.mean() > 0.0
    assert residual.std() > 0.0


def test_the_response_is_the_declared_sum_of_saturated_adstocked_spend(full: Dataset) -> None:
    """Rebuilt from the config and compared with the panel, which is the only real check of it."""
    panel = full.spend_panel
    truth = media_truth().set_index("channel")
    response = np.zeros(MEDIA_MIX.weeks)
    for profile in CHANNELS:
        weekly = profile.spend / MEDIA_MIX.weeks
        half_point = MEDIA_MIX.saturation_at * weekly / (1.0 - MEDIA_MIX.adstock)
        steady = weekly / (1.0 - MEDIA_MIX.adstock)
        average = float(truth.loc[profile.channel, "conversions_per_unit_spend"])
        ceiling = average * weekly / saturate(np.array([steady]), half_point)[0]
        spend = panel[f"spend_{profile.channel}"].to_numpy()
        response = response + ceiling * saturate(adstock(spend, MEDIA_MIX.adstock), half_point)
    noise = panel["conversions"].to_numpy() - panel["baseline"].to_numpy() - response
    assert noise.std() == pytest.approx(MEDIA_MIX.noise_sd, rel=0.2)
    assert abs(noise.mean()) < MEDIA_MIX.noise_sd


def test_the_panel_is_appended_after_everything_wave_one_to_four_published() -> None:
    """The stream-order contract: adding this table moved no earlier figure.

    The pins are the ones waves 1 to 4 were measured with. If the panel had been generated before
    any of them, every one of these would have changed.
    """
    data = generate_dataset()
    assert float(data.audience.iloc[0]["intent"]) == pytest.approx(0.2839801037362014)
    assert int(data.audience["converted"].sum()) == 19_418
    assert len(data.journeys) == 278_062
    assert int(data.geo_experiments.iloc[0]["conversions"]) == 203
    assert int(data.geo_experiments["conversions"].sum()) == 1_059_224


def test_the_panel_pins_are_unchanged(full: Dataset) -> None:
    assert float(full.spend_panel.iloc[0]["conversions"]) == pytest.approx(176.2314492)
    assert float(full.spend_panel["conversions"].sum()) == pytest.approx(21_657.2286, abs=5e-4)


def test_the_seed_reproduces_the_panel() -> None:
    first = generate_dataset(SEED)
    second = generate_dataset(SEED)
    pd.testing.assert_frame_equal(first.spend_panel, second.spend_panel)
    pd.testing.assert_frame_equal(first.media_truth, second.media_truth)


def test_a_different_seed_moves_the_panel_and_not_its_declared_truth() -> None:
    other = generate_dataset(seed=7)
    published = generate_dataset()
    assert not other.spend_panel["conversions"].equals(published.spend_panel["conversions"])
    pd.testing.assert_frame_equal(other.media_truth, published.media_truth)


def test_a_panel_with_no_budget_swing_is_perfectly_collinear() -> None:
    """The control case at the edge: with no idiosyncratic movement the channels are one variable."""
    rigid = MediaMixProfile(
        weeks=52,
        base_conversions=100.0,
        weekly_trend=0.0,
        seasonal_amplitude=0.0,
        seasonal_period=52.0,
        noise_sd=1.0,
        budget_swing=0.30,
        idiosyncratic_swing=0.0,
        adstock=0.0,
        saturation_at=1.0,
    )
    panel = spend_panel(np.random.default_rng(0), AUDIENCE, rigid)
    columns = [f"spend_{profile.channel}" for profile in CHANNELS]
    correlations = panel[columns].corr().to_numpy()
    off_diagonal = correlations[~np.eye(len(columns), dtype=bool)]
    assert off_diagonal.min() == pytest.approx(1.0, abs=1e-9)
