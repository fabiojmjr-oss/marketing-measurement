"""Every figure quoted in a README, re-derived.

Marked slow because they build the full dataset, run the exact Shapley computation over every
coalition and execute every example script. The point is not coverage: it is that a change which
moves a published number breaks the build instead of leaving the text quietly wrong.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from mktlab.attribution import (
    credit,
    credit_table,
    geo_lift,
    journey_sets,
    returns,
    shapley,
    unattributable,
)
from mktlab.synth import AUDIENCE, CHANNELS, GEO, Dataset

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.slow


def test_the_dataset_is_the_size_both_readmes_quote(full: Dataset) -> None:
    assert len(full.audience) == 200_000
    assert len(full.journeys) == 277_849
    assert int(full.audience["converted"].sum()) == 19_393


def test_the_credit_shares_are_what_the_table_publishes(full: Dataset) -> None:
    table = credit_table(full.journeys)
    published = {
        "social-pago": (0.2067, 0.6662, 0.4027, 0.4184, 0.3219, 0.4027),
        "email": (0.1605, 0.1594, 0.1925, 0.1780, 0.1840, 0.1925),
        "busca-generica": (0.2213, 0.1004, 0.1811, 0.1711, 0.2001, 0.1811),
        "retargeting": (0.1805, 0.0439, 0.1144, 0.1130, 0.1416, 0.1144),
        "busca-marca": (0.2311, 0.0301, 0.1093, 0.1195, 0.1524, 0.1093),
    }
    for channel, shares in published.items():
        row = table.loc[channel]
        for model, expected in zip(table.columns, shares, strict=True):
            assert float(row[model]) == pytest.approx(expected, abs=5e-5), f"{channel} {model}"


def test_last_click_gives_the_two_zero_effect_channels_the_published_share(full: Dataset) -> None:
    table = credit_table(full.journeys, models=("last-click",))
    zero = [profile.channel for profile in CHANNELS if profile.true_effect == 0.0]
    assert zero == ["retargeting", "busca-marca"]
    assert float(table.loc[zero, "last-click"].sum()) == pytest.approx(0.4116, abs=5e-5)
    assert str(table["last-click"].idxmax()) == "busca-marca"


def test_the_two_ends_of_the_journey_disagree_by_the_published_multiples(full: Dataset) -> None:
    table = credit_table(full.journeys, models=("first-click", "last-click"))
    social = table.loc["social-pago"]
    brand = table.loc["busca-marca"]
    assert float(social["first-click"] / social["last-click"]) == pytest.approx(3.22, abs=5e-3)
    assert float(brand["last-click"] / brand["first-click"]) == pytest.approx(7.67, abs=5e-3)


def test_the_shapley_value_equals_linear_attribution_on_the_whole_dataset(full: Dataset) -> None:
    """The identity the README calls a result. Computed over all 2^5 coalitions, not asserted."""
    sets = journey_sets(full.journeys)
    channels = tuple(sorted({item for key in sets for item in key}))
    assert len(channels) == 5
    allocation = shapley(sets, channels)
    linear = credit(full.journeys, "linear").set_index("channel")["credited"]

    published = {
        "social-pago": 7015.233333,
        "email": 3353.483333,
        "busca-generica": 3153.983333,
        "retargeting": 1992.066667,
        "busca-marca": 1904.233333,
    }
    largest = 0.0
    for channel, expected in published.items():
        assert allocation[channel] == pytest.approx(expected, abs=5e-6), channel
        largest = max(largest, abs(allocation[channel] - float(linear[channel])))
    # Two bounds, and only the first is the claim: the allocations agree to floating point. The
    # second pins the figure the README quotes, loosely, because the exact accumulation over 2^5
    # coalitions is summation order and a different numpy build may reorder it.
    assert largest < 1e-11, f"largest difference {largest:.3e} is not floating point"
    assert largest == pytest.approx(9.09e-13, rel=0.5), f"quoted figure moved: {largest:.3e}"

    shares_difference = credit_table(full.journeys, models=("shapley", "linear")).pipe(
        lambda frame: (frame["shapley"] - frame["linear"]).abs().max()
    )
    assert float(shares_difference) < 1e-15
    assert float(shares_difference) == pytest.approx(2.8e-17, rel=0.5)


def test_the_untouched_conversions_are_the_published_share(full: Dataset) -> None:
    missing = unattributable(full.audience, full.journeys)
    assert missing["conversions"] == 19_393.0
    assert missing["attributable"] == 17_419.0
    assert missing["untouched"] == 1_974.0
    assert missing["untouched_share"] == pytest.approx(0.1018, abs=5e-5)


def _holdouts(full: Dataset) -> dict[str, object]:
    return {
        str(channel): geo_lift(
            full.geo_experiments[full.geo_experiments["channel"] == channel],
            split=GEO.split,
            channel=str(channel),
        )
        for channel in full.geo_experiments["channel"].unique()
    }


def test_the_holdout_table_is_what_the_readme_publishes(full: Dataset) -> None:
    published = {
        "social-pago": (0.028490, 0.026890, 0.030091, 0.0000, True),
        "busca-generica": (0.006133, 0.004620, 0.007645, 0.0000, True),
        "email": (0.002898, 0.000650, 0.005146, 0.0131, True),
        "retargeting": (0.000629, -0.001090, 0.002348, 0.4633, False),
        "busca-marca": (-0.000723, -0.002461, 0.001015, 0.4044, False),
    }
    lifts = _holdouts(full)
    for channel, (lift, low, high, p_value, significant) in published.items():
        result = lifts[channel]
        assert result.lift == pytest.approx(lift, abs=5e-7), channel  # type: ignore[attr-defined]
        assert result.interval[0] == pytest.approx(low, abs=5e-7), channel  # type: ignore[attr-defined]
        assert result.interval[1] == pytest.approx(high, abs=5e-7), channel  # type: ignore[attr-defined]
        assert result.p_value == pytest.approx(p_value, abs=5e-5), channel  # type: ignore[attr-defined]
        assert result.significant is significant, channel  # type: ignore[attr-defined]
        assert result.untested_because == "", channel  # type: ignore[attr-defined]


def test_every_holdout_interval_covers_the_lift_the_generator_declared(full: Dataset) -> None:
    """Five of five, which is the claim. The estimator is aimed at the right quantity."""
    designs = full.geo_designs.set_index("channel")
    covered = 0
    for channel, result in _holdouts(full).items():
        truth = float(designs.loc[channel, "true_rate_lift"])
        low, high = result.interval  # type: ignore[attr-defined]
        assert low <= truth <= high, channel
        covered += 1
    assert covered == 5


def test_the_two_channels_the_test_cannot_resolve_are_the_two_with_no_effect(
    full: Dataset,
) -> None:
    zero = {profile.channel for profile in CHANNELS if profile.true_effect == 0.0}
    silent = {
        channel
        for channel, result in _holdouts(full).items()
        if not result.significant  # type: ignore[attr-defined]
    }
    assert silent == zero


def test_the_returns_table_is_what_the_readme_publishes(full: Dataset) -> None:
    priced = returns(
        credited=credit(full.journeys, "last-click"),
        lifts=_holdouts(full),  # type: ignore[arg-type]
        truth=full.channel_truth,
        reach=float(AUDIENCE.users),
        value_per_conversion=AUDIENCE.value_per_conversion,
    ).set_index("channel")

    published = {
        "email": (20_000.0, 2_796.0, 25.164, 579.6154, 5.2165, True, 4.8239),
        "retargeting": (60_000.0, 3_144.0, 9.432, 125.7692, 0.3773, False, None),
        "busca-marca": (90_000.0, 4_025.0, 8.050, -144.6154, -0.2892, False, None),
        "busca-generica": (120_000.0, 3_854.0, 5.781, 1_226.5385, 1.8398, True, 3.1422),
        "social-pago": (180_000.0, 3_600.0, 3.600, 5_698.0769, 5.6981, True, 0.6318),
    }
    for channel, values in published.items():
        spend, credited, on_spend, incremental, incremental_return, established, ratio = values
        row = priced.loc[channel]
        assert float(row["spend"]) == pytest.approx(spend), channel
        assert float(row["credited_conversions"]) == pytest.approx(credited), channel
        assert float(row["roas"]) == pytest.approx(on_spend, abs=5e-4), channel
        assert float(row["incremental_conversions"]) == pytest.approx(incremental, abs=5e-4)
        assert float(row["iroas"]) == pytest.approx(incremental_return, abs=5e-5), channel
        assert bool(row["established"]) is established, channel
        if ratio is None:
            assert str(row["ratio"]) == "nan", channel
        else:
            assert float(row["ratio"]) == pytest.approx(ratio, abs=5e-5), channel


def test_the_credited_conversions_sum_to_the_attributable_ones(full: Dataset) -> None:
    """The defect the returns function had, as a claim: no rescaling may happen inside it."""
    priced = returns(
        credited=credit(full.journeys, "last-click"),
        lifts=_holdouts(full),  # type: ignore[arg-type]
        truth=full.channel_truth,
        reach=float(AUDIENCE.users),
        value_per_conversion=AUDIENCE.value_per_conversion,
    )
    missing = unattributable(full.audience, full.journeys)
    assert float(priced["credited_conversions"].sum()) == pytest.approx(missing["attributable"])


def test_the_blended_figures_and_the_unestablished_spend_are_published_correctly(
    full: Dataset,
) -> None:
    priced = returns(
        credited=credit(full.journeys, "last-click"),
        lifts=_holdouts(full),  # type: ignore[arg-type]
        truth=full.channel_truth,
        reach=float(AUDIENCE.users),
        value_per_conversion=AUDIENCE.value_per_conversion,
    )
    total_spend = float(priced["spend"].sum())
    value = AUDIENCE.value_per_conversion
    blended_roas = float(priced["credited_conversions"].sum()) * value / total_spend
    blended_iroas = float(priced["incremental_conversions"].sum()) * value / total_spend

    assert total_spend == 470_000.0
    assert blended_roas == pytest.approx(6.6711, abs=5e-5)
    assert blended_iroas == pytest.approx(2.8667, abs=5e-5)
    assert blended_roas / blended_iroas == pytest.approx(2.3, abs=0.05)

    unestablished = float(priced.loc[~priced["established"], "spend"].sum())
    assert unestablished == 150_000.0
    assert unestablished / total_spend == pytest.approx(0.319, abs=5e-4)


def test_roas_understates_the_one_channel_that_creates_demand(full: Dataset) -> None:
    """The half of the finding that gets missed: the error runs both ways."""
    priced = returns(
        credited=credit(full.journeys, "last-click"),
        lifts=_holdouts(full),  # type: ignore[arg-type]
        truth=full.channel_truth,
        reach=float(AUDIENCE.users),
        value_per_conversion=AUDIENCE.value_per_conversion,
    ).set_index("channel")
    understated = priced[priced["ratio"] < 1.0]
    assert list(understated.index) == ["social-pago"]
    assert str(priced["roas"].idxmin()) == "social-pago"
    assert str(priced.loc[priced["established"], "iroas"].idxmax()) == "social-pago"
    assert float(understated.loc["social-pago", "ratio"]) == pytest.approx(0.6318, abs=5e-5)


def test_the_geo_design_is_the_one_the_readme_describes() -> None:
    assert GEO.geos == 40
    assert GEO.weeks == 26
    assert GEO.split == 13
    assert AUDIENCE.value_per_conversion == 180.0


@pytest.mark.parametrize("script", sorted(path.name for path in (ROOT / "examples").glob("*.py")))
def test_the_example_runs(script: str) -> None:
    """An example that no longer runs is a broken promise in the README that links it."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / script)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
