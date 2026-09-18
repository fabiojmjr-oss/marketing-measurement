"""Every figure quoted in a README, re-derived.

Marked slow because they build the full dataset, run the exact Shapley computation over every
coalition and execute every example script. The point is not coverage: it is that a change which
moves a published number breaks the build instead of leaving the text quietly wrong.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from mktlab.attribution import (
    credit,
    credit_table,
    geo_lift,
    journey_sets,
    returns,
    shapley,
    unattributable,
)
from mktlab.design import (
    DEFAULT_POWER,
    RULES,
    GeoDesign,
    crossing_probability,
    exaggeration,
    fixed_boundary,
    holdout_cost,
    inflated_alpha,
    information_inflation,
    ncp_for_power,
    nominal_alpha,
    obrien_fleming,
    peeking_table,
    plan,
    pocock,
    regions_for,
    retrospective,
)
from mktlab.synth import AUDIENCE, CHANNELS, GEO, Dataset, mean_rate, true_rate_lift

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


# --- Wave 2: the sizing figures, from src/mktlab/design/README.md -----------------------------


def _published_design() -> GeoDesign:
    return GeoDesign(
        geos=GEO.geos,
        weeks=GEO.weeks,
        split=GEO.split,
        users_per_geo_week=GEO.users_per_geo_week,
        base_rate=mean_rate(AUDIENCE, tuple(CHANNELS)),
    )


def test_the_design_readme_quotes_the_right_base_rate_and_precision() -> None:
    design = _published_design()
    assert design.base_rate == pytest.approx(0.0977)
    assert design.df == 38.0
    assert design.standard_error() == pytest.approx(0.000823, abs=5e-7)
    assert design.power(0.0) == pytest.approx(0.05, abs=1e-12)


def test_the_detectable_lifts_are_what_the_design_readme_publishes() -> None:
    design = _published_design()
    assert design.detectable_lift() == pytest.approx(0.002361, abs=5e-7)
    assert design.detectable_lift(0.50) == pytest.approx(0.001653, abs=5e-7)
    assert design.detectable_lift(0.95) == pytest.approx(0.003036, abs=5e-7)


def test_the_predicted_against_observed_table_is_what_is_published(full: Dataset) -> None:
    design = _published_design()
    published = {
        "social-pago": (0.000797, 0.000786, 0.9868, 1.0000),
        "email": (0.000820, 0.001106, 1.3476, 0.9671),
        "busca-generica": (0.000816, 0.000745, 0.9125, 1.0000),
        "retargeting": (0.000823, 0.000849, 1.0307, 0.0500),
        "busca-marca": (0.000823, 0.000857, 1.0407, 0.0500),
    }
    for profile in CHANNELS:
        predicted, observed, ratio, power = published[profile.channel]
        truth = true_rate_lift(profile)
        panel = full.geo_experiments[full.geo_experiments["channel"] == profile.channel]
        result = geo_lift(panel, split=GEO.split, channel=profile.channel)
        assert design.standard_error(truth) == pytest.approx(predicted, abs=5e-7), profile.channel
        assert result.standard_error == pytest.approx(observed, abs=5e-7), profile.channel
        assert result.standard_error / design.standard_error(truth) == pytest.approx(
            ratio, abs=5e-5
        ), profile.channel
        assert design.power(truth) == pytest.approx(power, abs=5e-5), profile.channel


def test_the_regions_each_channel_actually_needed_are_published_correctly() -> None:
    design = _published_design()
    published = {"social-pago": 4, "busca-generica": 8, "email": 24}
    for profile in CHANNELS:
        truth = true_rate_lift(profile)
        if truth == 0.0:
            continue
        assert regions_for(truth, design) == published[profile.channel], profile.channel
        assert published[profile.channel] < design.geos


def test_the_detectable_return_table_is_what_is_published() -> None:
    design = _published_design()
    reach = float(AUDIENCE.users)
    value = AUDIENCE.value_per_conversion
    published = {
        "social-pago": (0.4722, 0.3334, 5.40),
        "busca-generica": (0.7083, 0.5001, 2.25),
        "busca-marca": (0.9444, 0.6668, 0.00),
        "retargeting": (1.4166, 1.0002, 0.00),
        "email": (4.2498, 3.0007, 5.76),
    }
    for profile in CHANNELS:
        floor, half_width, true_iroas = published[profile.channel]
        assert design.detectable_iroas(profile.spend, reach, value) == pytest.approx(
            floor, abs=5e-5
        ), profile.channel
        assert design.return_precision(profile.spend, reach, value) == pytest.approx(
            half_width, abs=5e-5
        ), profile.channel
        assert true_rate_lift(profile) * reach * value / profile.spend == pytest.approx(
            true_iroas, abs=5e-3
        ), profile.channel


def test_the_same_design_is_nine_times_blinder_on_the_smallest_channel() -> None:
    """The claim the README makes in words: the statistical figure is identical, the decision
    figure differs by a factor of nine."""
    design = _published_design()
    reach = float(AUDIENCE.users)
    value = AUDIENCE.value_per_conversion
    floors = {
        profile.channel: design.detectable_iroas(profile.spend, reach, value)
        for profile in CHANNELS
    }
    assert max(floors.values()) / min(floors.values()) == pytest.approx(9.0)
    assert max(floors, key=lambda name: floors[name]) == "email"
    assert min(floors, key=lambda name: floors[name]) == "social-pago"


def test_the_two_null_results_are_read_as_bounds_on_the_return(full: Dataset) -> None:
    design = _published_design()
    published = {
        "retargeting": (0.3773, -0.6539, 1.4085, 1.4166),
        "busca-marca": (-0.2892, -0.9844, 0.4060, 0.9444),
    }
    for channel, (iroas, low, high, floor) in published.items():
        profile = next(item for item in CHANNELS if item.channel == channel)
        panel = full.geo_experiments[full.geo_experiments["channel"] == channel]
        read = retrospective(
            geo_lift(panel, split=GEO.split, channel=channel),
            design,
            spend=profile.spend,
            reach=float(AUDIENCE.users),
            value_per_conversion=AUDIENCE.value_per_conversion,
        )
        assert not read.significant, channel
        assert read.iroas == pytest.approx(iroas, abs=5e-5), channel
        assert read.iroas_interval[0] == pytest.approx(low, abs=5e-5), channel
        assert read.excludes == pytest.approx(high, abs=5e-5), channel
        assert read.detectable_iroas == pytest.approx(floor, abs=5e-5), channel
        assert not read.was_big_enough, channel


def test_the_holdout_cost_table_is_what_is_published() -> None:
    design = _published_design()
    published = {
        "social-pago": (14_040.0, 0.2764),
        "busca-generica": (3_900.0, 0.0768),
        "email": (1_664.0, 0.0328),
        "retargeting": (0.0, 0.0),
        "busca-marca": (0.0, 0.0),
    }
    for profile in CHANNELS:
        conversions, share = published[profile.channel]
        cost = holdout_cost(design, true_rate_lift(profile), AUDIENCE.value_per_conversion)
        assert cost["region_weeks_held_out"] == 260.0
        assert cost["users_held_out"] == 520_000.0
        assert cost["forgone_conversions"] == pytest.approx(conversions, abs=5e-1), profile.channel
        assert cost["forgone_share"] == pytest.approx(share, abs=5e-5), profile.channel


def test_the_free_pre_period_table_is_what_is_published() -> None:
    design = _published_design()
    email = next(profile for profile in CHANNELS if profile.channel == "email")
    published = {
        4: (0.001200, 6.2004, 4.3742),
        8: (0.000943, 4.8705, 3.4377),
        13: (0.000823, 4.2498, 3.0007),
        26: (0.000713, 3.6789, 2.5987),
        52: (0.000651, 3.3574, 2.3722),
    }
    for before, (error, floor, half_width) in published.items():
        candidate = GeoDesign(
            geos=design.geos,
            weeks=before + design.weeks_after,
            split=before,
            users_per_geo_week=design.users_per_geo_week,
            base_rate=design.base_rate,
        )
        reach = float(AUDIENCE.users)
        value = AUDIENCE.value_per_conversion
        assert candidate.standard_error() == pytest.approx(error, abs=5e-7), before
        assert candidate.detectable_iroas(email.spend, reach, value) == pytest.approx(
            floor, abs=5e-5
        ), before
        assert candidate.return_precision(email.spend, reach, value) == pytest.approx(
            half_width, abs=5e-5
        ), before
        # Every row costs the same, which is the whole point of the table.
        cost = holdout_cost(candidate, true_rate_lift(email), value)
        assert cost["region_weeks_held_out"] == 260.0
        assert cost["forgone_conversions"] == pytest.approx(1_664.0)


def test_an_unlimited_pre_period_equals_double_the_regions_at_the_published_figure() -> None:
    """The exact identity the README calls the cleanest statement in the module."""
    design = _published_design()
    doubled = GeoDesign(
        geos=design.geos * 2,
        weeks=design.weeks,
        split=design.split,
        users_per_geo_week=design.users_per_geo_week,
        base_rate=design.base_rate,
    )
    floor = design.standard_error() / 2.0**0.5
    assert doubled.standard_error() == pytest.approx(floor, rel=1e-12)
    assert floor == pytest.approx(0.000582, abs=5e-7)


def test_email_needs_eighty_regions_to_tell_three_from_eight() -> None:
    """The claim behind 'the design that ran is the row that cannot answer the question'."""
    design = _published_design()
    email = next(profile for profile in CHANNELS if profile.channel == "email")
    reach = float(AUDIENCE.users)
    value = AUDIENCE.value_per_conversion
    truth = true_rate_lift(email) * reach * value / email.spend
    needed = truth - 3.0
    assert design.return_precision(email.spend, reach, value) > needed
    doubled = GeoDesign(
        geos=80,
        weeks=design.weeks,
        split=design.split,
        users_per_geo_week=design.users_per_geo_week,
        base_rate=design.base_rate,
    )
    assert doubled.return_precision(email.spend, reach, value) < needed


# --- Wave 3: repeated looks, from src/mktlab/design/README-sequential.md -----------------------

LOOKS = GEO.weeks - GEO.split


def test_the_holdout_is_read_for_thirteen_weeks() -> None:
    """The number every figure in the sequential README is built on."""
    assert LOOKS == 13


def test_the_inflated_alpha_table_is_what_is_published() -> None:
    published = {
        1: 0.050000,
        2: 0.083118,
        3: 0.107256,
        5: 0.141689,
        10: 0.193357,
        13: 0.213814,
        26: 0.268788,
        52: 0.323512,
    }
    for looks, expected in published.items():
        assert inflated_alpha(looks) == pytest.approx(expected, abs=5e-7), looks
    assert published[13] / 0.05 == pytest.approx(4.28, abs=5e-3)


def test_the_error_rate_is_steepest_at_the_second_look() -> None:
    """The claim in words: twice is 66% more error than once."""
    assert (inflated_alpha(2) - 0.05) / 0.05 == pytest.approx(0.66, abs=5e-3)


def test_the_peeking_table_is_what_is_published() -> None:
    table = peeking_table(LOOKS).set_index("rule")
    assert float(table.loc["naive", "true_alpha"]) == pytest.approx(0.213814, abs=5e-7)
    assert not bool(table.loc["naive", "valid"])
    assert float(table.loc["naive", "expected_looks"]) == pytest.approx(6.20, abs=5e-3)

    assert float(table.loc["pocock", "first_boundary"]) == pytest.approx(2.6019, abs=5e-5)
    assert float(table.loc["pocock", "nominal_alpha_first"]) == pytest.approx(0.0093, abs=5e-5)
    assert float(table.loc["pocock", "information_inflation"]) == pytest.approx(1.3247, abs=5e-5)
    assert float(table.loc["pocock", "expected_looks"]) == pytest.approx(7.83, abs=5e-3)

    assert float(table.loc["obrien-fleming", "first_boundary"]) == pytest.approx(7.5799, abs=5e-5)
    assert float(table.loc["obrien-fleming", "last_boundary"]) == pytest.approx(2.1023, abs=5e-5)
    assert float(table.loc["obrien-fleming", "nominal_alpha_first"]) == pytest.approx(
        3.5e-14, rel=0.05
    )
    assert float(table.loc["obrien-fleming", "nominal_alpha_last"]) == pytest.approx(
        0.0355, abs=5e-5
    )
    assert float(table.loc["obrien-fleming", "information_inflation"]) == pytest.approx(
        1.0432, abs=5e-5
    )
    assert float(table.loc["obrien-fleming", "expected_looks"]) == pytest.approx(9.79, abs=5e-3)

    for rule in ("read-once", "pocock", "obrien-fleming"):
        assert float(table.loc[rule, "true_alpha"]) == pytest.approx(0.05, abs=1e-9), rule


def test_the_published_boundaries_reproduce_the_classical_ones() -> None:
    """The external check: these are facts about a recursion, so they can be checked at all."""
    pocock_constants = {1: 1.9600, 2: 2.1783, 3: 2.2895, 4: 2.3613, 5: 2.4132, 20: 2.6720}
    for looks, constant in pocock_constants.items():
        assert pocock(looks)[0] == pytest.approx(constant, abs=5e-5), looks

    nominals = nominal_alpha(obrien_fleming(5))
    published = (0.000005, 0.001257, 0.008445, 0.022556, 0.041343)
    for index, expected in enumerate(published):
        assert nominals[index] == pytest.approx(expected, abs=5e-7), index


def test_the_recursion_agrees_with_a_four_million_draw_simulation() -> None:
    """A closed form that only agrees with itself has been verified against nothing."""
    rng = np.random.default_rng(7)
    draws = 4_000_000
    published = {5: 0.141689, 10: 0.193357, 20: 0.247911}
    for looks, expected in published.items():
        assert inflated_alpha(looks) == pytest.approx(expected, abs=5e-7), looks
        increments = rng.standard_normal((draws, looks))
        running = np.cumsum(increments, axis=1)
        limits = np.asarray(fixed_boundary(looks)) * np.sqrt(np.arange(1, looks + 1))
        simulated = float((np.abs(running) >= limits).any(axis=1).mean())
        error = 1.96 * (simulated * (1.0 - simulated) / draws) ** 0.5
        assert abs(simulated - expected) < error + 5e-7, (looks, simulated, expected)


def test_the_quadrature_does_not_move_the_published_figures() -> None:
    for looks in (5, 13, 20):
        boundary = fixed_boundary(looks)
        coarse = crossing_probability(boundary, nodes=100)[-1]
        fine = crossing_probability(boundary, nodes=600)[-1]
        assert coarse == pytest.approx(fine, abs=1e-9), looks
        assert crossing_probability(boundary)[-1] == pytest.approx(fine, abs=1e-9), looks


def test_the_cost_of_the_honest_boundaries_on_the_real_holdout_is_published_correctly() -> None:
    design = _published_design()
    email = next(profile for profile in CHANNELS if profile.channel == "email")
    reach = float(AUDIENCE.users)
    value = AUDIENCE.value_per_conversion
    floor = design.detectable_iroas(email.spend, reach, value)
    base = regions_for(true_rate_lift(email), design)
    assert base == 24
    assert floor == pytest.approx(4.2498, abs=5e-5)

    published = {"obrien-fleming": (1.0432, 4.3406, 26), "pocock": (1.3247, 4.8913, 32)}
    for rule, (inflation, detectable, regions) in published.items():
        built = plan(rule, LOOKS)
        measured = information_inflation(built.boundary, DEFAULT_POWER)
        assert measured == pytest.approx(inflation, abs=5e-5), rule
        assert floor * measured**0.5 == pytest.approx(detectable, abs=5e-4), rule
        assert -(-int(base * measured) // 2) * 2 == regions, rule

    assert published["obrien-fleming"][0] ** 0.5 - 1.0 == pytest.approx(0.021, abs=5e-4)


def test_the_exaggeration_table_is_what_is_published() -> None:
    published = {
        "read-once": (0.7991, 1.1241, 1.0000, 1.0000),
        "obrien-fleming": (0.8013, 1.2676, 9.79, 1.0000),
        "pocock": (0.8012, 1.4794, 7.82, 0.9996),
        "naive": (0.8006, 1.7273, 7.02, 0.9927),
    }
    for rule, (achieved, ratio, looks, same_sign) in published.items():
        built = plan(rule, LOOKS)
        ncp = ncp_for_power(
            built.boundary if built.valid else plan("naive", LOOKS).boundary, DEFAULT_POWER
        )
        measured = exaggeration(built.boundary, ncp)
        assert measured["power"] == pytest.approx(achieved, abs=5e-4), rule
        assert measured["ratio"] == pytest.approx(ratio, abs=5e-4), rule
        assert measured["expected_looks"] == pytest.approx(looks, abs=5e-3), rule
        assert measured["same_sign"] == pytest.approx(same_sign, abs=5e-5), rule


def test_reading_once_exaggerates_least_and_peeking_most() -> None:
    """The ordering the README states, as an assertion rather than a description."""
    ratios = {}
    for rule in RULES:
        built = plan(rule, LOOKS)
        ncp = ncp_for_power(
            built.boundary if built.valid else plan("naive", LOOKS).boundary, DEFAULT_POWER
        )
        ratios[rule] = exaggeration(built.boundary, ncp)["ratio"]
    assert ratios["read-once"] < ratios["obrien-fleming"] < ratios["pocock"] < ratios["naive"], (
        ratios
    )


def test_the_underpowered_exaggeration_is_what_is_published() -> None:
    weak = ncp_for_power(fixed_boundary(1), 0.30)
    published = {
        "read-once": (0.2982, 1.8053, 1.0000, 0.9989),
        "naive": (0.4769, 2.6352, 9.57, 0.9618),
    }
    for rule, (achieved, ratio, looks, same_sign) in published.items():
        measured = exaggeration(plan(rule, LOOKS).boundary, weak)
        assert measured["power"] == pytest.approx(achieved, abs=5e-4), rule
        assert measured["ratio"] == pytest.approx(ratio, abs=5e-4), rule
        assert measured["expected_looks"] == pytest.approx(looks, abs=5e-3), rule
        assert measured["same_sign"] == pytest.approx(same_sign, abs=5e-5), rule
    assert 1.0 - published["naive"][3] == pytest.approx(0.038, abs=5e-4)


def test_the_t_against_z_gap_the_readme_quotes_is_right() -> None:
    """The accuracy of composing normal-theory boundaries with a t-based sizing."""
    design = _published_design()
    critical = float(stats.t.ppf(0.975, design.df))
    normal = float(stats.norm.ppf(0.975))
    assert critical / normal - 1.0 == pytest.approx(0.033, abs=5e-4)
