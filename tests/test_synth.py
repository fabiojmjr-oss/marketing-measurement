"""The generator, against the closed forms it was built from.

Nothing here is checked against the generator's own output. Every expectation is either an
analytic value or a property the construction guarantees.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mktlab.synth import (
    AUDIENCE,
    AUDIENCE_COLUMNS,
    CHANNELS,
    DESIGN_COLUMNS,
    GEO,
    GEO_COLUMNS,
    JOURNEY_COLUMNS,
    SEED,
    TRUTH_COLUMNS,
    AudienceProfile,
    ChannelProfile,
    Dataset,
    audience_and_journeys,
    channel_truth,
    conversion_probability,
    exposure_probability,
    generate_dataset,
    geo_designs,
    mean_rate,
    true_rate_lift,
)

MEAN_INTENT = AUDIENCE.intent_alpha / (AUDIENCE.intent_alpha + AUDIENCE.intent_beta)


def test_exposure_is_the_declared_line_in_intent() -> None:
    profile = ChannelProfile("X", 1.0, 0.20, 0.50, 0.0, 1.0)
    intent = np.array([0.0, 0.5, 1.0])
    assert exposure_probability(profile, intent) == pytest.approx([0.20, 0.45, 0.70])


def test_exposure_is_clipped_to_a_probability() -> None:
    """A base plus a slope can leave the unit interval, and a probability cannot."""
    profile = ChannelProfile("X", 1.0, 0.80, 0.90, 0.0, 1.0)
    assert exposure_probability(profile, np.array([1.0]))[0] == 1.0
    negative = ChannelProfile("X", 1.0, -0.20, 0.10, 0.0, 1.0)
    assert exposure_probability(negative, np.array([0.0]))[0] == 0.0


def test_conversion_probability_adds_the_effects_of_the_channels_that_reached_the_user() -> None:
    intent = np.array([0.0, 0.0])
    exposed = {profile.channel: np.array([False, True]) for profile in CHANNELS}
    probability = conversion_probability(AUDIENCE, intent, exposed)
    total_effect = sum(profile.true_effect for profile in CHANNELS)
    assert probability[0] == pytest.approx(AUDIENCE.base_conversion)
    assert probability[1] == pytest.approx(AUDIENCE.base_conversion + total_effect)


def test_intent_alone_moves_the_conversion_probability_by_the_declared_slope() -> None:
    exposed = {profile.channel: np.array([False, False]) for profile in CHANNELS}
    probability = conversion_probability(AUDIENCE, np.array([0.0, 1.0]), exposed)
    assert probability[1] - probability[0] == pytest.approx(AUDIENCE.intent_slope)


def test_channel_truth_exposure_rate_is_the_exact_expectation() -> None:
    truth = channel_truth().set_index("channel")
    for profile in CHANNELS:
        expected = profile.exposure_base + profile.exposure_intent_slope * MEAN_INTENT
        assert float(truth.loc[profile.channel, "exposure_rate"]) == pytest.approx(expected)
    assert tuple(channel_truth().columns) == TRUTH_COLUMNS


def test_mean_rate_with_no_channels_live_is_the_audience_on_its_own() -> None:
    assert mean_rate(AUDIENCE, ()) == pytest.approx(
        AUDIENCE.base_conversion + AUDIENCE.intent_slope * MEAN_INTENT
    )


def test_mean_rate_adds_effect_times_expected_exposure_per_live_channel() -> None:
    live = tuple(CHANNELS)
    expected = (
        AUDIENCE.base_conversion
        + AUDIENCE.intent_slope * MEAN_INTENT
        + sum(
            profile.true_effect
            * (profile.exposure_base + profile.exposure_intent_slope * MEAN_INTENT)
            for profile in live
        )
    )
    assert mean_rate(AUDIENCE, live) == pytest.approx(expected)


def test_switching_one_channel_off_moves_the_mean_rate_by_its_true_lift() -> None:
    """The identity the geo test is trying to recover, stated as arithmetic."""
    live = tuple(CHANNELS)
    for profile in CHANNELS:
        without = tuple(other for other in CHANNELS if other.channel != profile.channel)
        drop = mean_rate(AUDIENCE, live) - mean_rate(AUDIENCE, without)
        assert drop == pytest.approx(true_rate_lift(profile))


def test_a_channel_with_no_effect_has_no_true_lift_however_selected_its_audience() -> None:
    selected = ChannelProfile("X", 5.0, 0.02, 0.95, 0.0, 1.0)
    assert true_rate_lift(selected) == 0.0


def test_geo_designs_declares_one_row_per_channel_with_the_lift_to_recover() -> None:
    designs = geo_designs()
    assert tuple(designs.columns) == DESIGN_COLUMNS
    assert len(designs) == len(CHANNELS)
    for profile in CHANNELS:
        row = designs[designs["channel"] == profile.channel].iloc[0]
        assert float(row["true_rate_lift"]) == pytest.approx(true_rate_lift(profile))
        assert int(row["split"]) == GEO.split


def test_the_dataset_has_the_declared_shape(full: Dataset) -> None:
    assert isinstance(full, Dataset)
    assert tuple(full.audience.columns) == AUDIENCE_COLUMNS
    assert tuple(full.journeys.columns) == JOURNEY_COLUMNS
    assert tuple(full.geo_experiments.columns) == GEO_COLUMNS
    assert len(full.audience) == AUDIENCE.users
    assert len(full.geo_experiments) == len(CHANNELS) * GEO.geos * GEO.weeks


def test_every_geo_panel_splits_its_regions_in_half(full: Dataset) -> None:
    for channel in full.geo_experiments["channel"].unique():
        panel = full.geo_experiments[full.geo_experiments["channel"] == channel]
        held = panel[panel["holdout"]]["geo"].nunique()
        assert held == GEO.geos // 2, channel


def test_a_journey_row_exists_for_every_touch_the_audience_table_counts(full: Dataset) -> None:
    assert len(full.journeys) == int(full.audience["touches"].sum())


def test_journey_positions_run_from_one_with_no_gaps(full: Dataset) -> None:
    sizes = full.journeys.groupby("user", observed=True)["position"]
    assert sizes.min().min() == 1
    assert (sizes.max() == sizes.size()).all()


def test_the_conversion_flag_agrees_between_the_two_tables(full: Dataset) -> None:
    flags = full.audience.set_index("user")["converted"]
    joined = full.journeys.join(flags.rename("truth"), on="user")
    assert (joined["converted"] == joined["truth"]).all()


def test_the_seed_reproduces_the_dataset_byte_for_byte() -> None:
    first = generate_dataset()
    second = generate_dataset()
    pd.testing.assert_frame_equal(first.audience, second.audience)
    pd.testing.assert_frame_equal(first.journeys, second.journeys)
    pd.testing.assert_frame_equal(first.geo_experiments, second.geo_experiments)


def test_a_different_seed_gives_different_draws_and_the_same_declared_truth() -> None:
    other = generate_dataset(seed=7)
    published = generate_dataset()
    assert not other.audience["intent"].equals(published.audience["intent"])
    pd.testing.assert_frame_equal(other.channel_truth, published.channel_truth)
    pd.testing.assert_frame_equal(other.geo_designs, published.geo_designs)


def test_the_stream_order_pins_are_unchanged(full: Dataset) -> None:
    """The generator is consumed in stream order, so a draw inserted anywhere shifts these.

    They exist so that a change which silently moves every published figure fails here, in one
    line, rather than in thirty assertions about tables downstream of it. The sums are pinned as
    well as the first values, because a first row can match by coincidence while everything after it
    has moved - which is exactly what happened when the geo panel was drawn with a library binomial.
    """
    assert float(full.audience.iloc[0]["intent"]) == pytest.approx(0.2839801037362014)
    assert int(full.audience["converted"].sum()) == 19_418
    assert len(full.journeys) == 278_062
    assert int(full.geo_experiments.iloc[0]["conversions"]) == 203
    assert int(full.geo_experiments["conversions"].sum()) == 1_059_224


def test_the_uniform_stream_itself_is_what_it_has_always_been() -> None:
    """The one thing the whole dataset now rests on, asserted directly.

    Every draw is an inverse transform of this stream, so if these three numbers ever change, every
    figure in the repository changes with them - and this test says so in one line instead of
    leaving thirty tables to disagree with the documentation. They are a property of PCG64 and the
    seed, which numpy guarantees, rather than of any distribution implementation, which it does not.
    """
    assert np.random.default_rng(SEED).random(3).tolist() == [
        0.7739560485559633,
        0.4388784397520523,
        0.8585979199113825,
    ]


def test_the_generator_draws_nothing_but_uniforms() -> None:
    """The contract that keeps the figures reproducible, enforced against the source.

    A library's ``binomial``, ``beta``, ``choice`` or ``normal`` is usually a rejection sampler: it
    consumes a variable number of uniforms per draw, so the stream position after it depends on the
    sampler's internals rather than on how many values were asked for. Change library version,
    change the internals, and every figure downstream moves. That is not hypothetical - it is why
    ``_draws.py`` exists.

    So the rule is that only ``rng.random`` may be called, and only from that module. This test
    reads the package and enforces it, because a rule nothing checks is a rule that lasts until the
    next module.
    """
    package = Path(__file__).resolve().parents[1] / "src" / "mktlab"
    forbidden = (
        "binomial",
        "beta",
        "choice",
        "normal",
        "permutation",
        "shuffle",
        "poisson",
        "standard_normal",
        "integers",
        "uniform",
        "exponential",
        "gamma",
    )
    offenders = []
    for path in sorted(package.rglob("*.py")):
        if path.name == "_draws.py":
            continue
        text = path.read_text(encoding="utf-8")
        for name in forbidden:
            if f"rng.{name}(" in text:
                offenders.append(f"{path.relative_to(package)}: rng.{name}(")
    assert not offenders, (
        "these draws consume a variable number of uniforms, which makes the published figures "
        "depend on the library version: " + "; ".join(offenders)
    )


def test_a_tiny_audience_still_produces_both_tables() -> None:
    """The smallest population the generator is asked for anywhere, so it has to work."""
    small = AudienceProfile(
        users=10,
        intent_alpha=2.0,
        intent_beta=8.0,
        base_conversion=0.5,
        intent_slope=0.0,
        value_per_conversion=1.0,
    )
    rng = np.random.default_rng(0)
    users, journeys = audience_and_journeys(rng, small)
    assert len(users) == 10
    assert len(journeys) == int(users["touches"].sum())
