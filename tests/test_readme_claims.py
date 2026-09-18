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
from scipy import optimize, stats

from mktlab.attribution import (
    credit,
    credit_table,
    geo_lift,
    journey_sets,
    returns,
    shapley,
    unattributable,
)
from mktlab.calibration import average_to_marginal, calibrate, prior_from_holdout
from mktlab.design import (
    DEFAULT_POWER,
    RULES,
    UNREACHABLE,
    GeoDesign,
    alpha_spent,
    crossing_probability,
    equal_information,
    exaggeration,
    fixed_boundary,
    holdout_cost,
    inflated_alpha,
    information_inflation,
    monitoring_plan,
    ncp_for_power,
    nominal_alpha,
    obrien_fleming,
    peeking_table,
    plan,
    pocock,
    regions_for,
    retrospective,
    schedule,
    spending_boundary,
)
from mktlab.mmm import fit as mmm_fit
from mktlab.mmm import transform_grid as mmm_transform_grid
from mktlab.synth import (
    AUDIENCE,
    CHANNELS,
    GEO,
    MEDIA_MIX,
    Dataset,
    mean_rate,
    true_rate_lift,
)

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.slow


def test_the_dataset_is_the_size_both_readmes_quote(full: Dataset) -> None:
    assert len(full.audience) == 200_000
    assert len(full.journeys) == 278_062
    assert int(full.audience["converted"].sum()) == 19_418


def test_the_credit_shares_are_what_the_table_publishes(full: Dataset) -> None:
    table = credit_table(full.journeys)
    published = {
        "social-pago": (0.2015, 0.6684, 0.4012, 0.4168, 0.3191, 0.4012),
        "email": (0.1717, 0.1596, 0.1983, 0.1837, 0.1916, 0.1983),
        "busca-generica": (0.2145, 0.0942, 0.1743, 0.1645, 0.1933, 0.1743),
        "retargeting": (0.1800, 0.0447, 0.1150, 0.1134, 0.1420, 0.1150),
        "busca-marca": (0.2322, 0.0331, 0.1112, 0.1216, 0.1540, 0.1112),
    }
    for channel, shares in published.items():
        row = table.loc[channel]
        for model, expected in zip(table.columns, shares, strict=True):
            assert float(row[model]) == pytest.approx(expected, abs=5e-5), f"{channel} {model}"


def test_last_click_gives_the_two_zero_effect_channels_the_published_share(full: Dataset) -> None:
    table = credit_table(full.journeys, models=("last-click",))
    zero = [profile.channel for profile in CHANNELS if profile.true_effect == 0.0]
    assert zero == ["retargeting", "busca-marca"]
    assert float(table.loc[zero, "last-click"].sum()) == pytest.approx(0.4122, abs=5e-5)
    assert str(table["last-click"].idxmax()) == "busca-marca"


def test_the_two_ends_of_the_journey_disagree_by_the_published_multiples(full: Dataset) -> None:
    table = credit_table(full.journeys, models=("first-click", "last-click"))
    social = table.loc["social-pago"]
    brand = table.loc["busca-marca"]
    assert float(social["first-click"] / social["last-click"]) == pytest.approx(3.32, abs=5e-3)
    assert float(brand["last-click"] / brand["first-click"]) == pytest.approx(7.01, abs=5e-3)


def test_the_shapley_value_equals_linear_attribution_on_the_whole_dataset(full: Dataset) -> None:
    """The identity the README calls a result. Computed over all 2^5 coalitions, not asserted."""
    sets = journey_sets(full.journeys)
    channels = tuple(sorted({item for key in sets for item in key}))
    assert len(channels) == 5
    allocation = shapley(sets, channels)
    linear = credit(full.journeys, "linear").set_index("channel")["credited"]

    published = {
        "social-pago": 6998.533333,
        "email": 3459.366667,
        "busca-generica": 3040.783333,
        "retargeting": 2006.866667,
        "busca-marca": 1940.450000,
    }
    largest = 0.0
    for channel, expected in published.items():
        assert allocation[channel] == pytest.approx(expected, abs=5e-6), channel
        largest = max(largest, abs(allocation[channel] - float(linear[channel])))
    # Two bounds, and only the first is the claim: the allocations agree to floating point. The
    # second pins the figure the README quotes, loosely, because the exact accumulation over 2^5
    # coalitions is summation order and a different numpy build may reorder it.
    assert largest < 1e-11, f"largest difference {largest:.3e} is not floating point"
    assert largest == pytest.approx(1.8e-12, rel=0.5), f"quoted figure moved: {largest:.3e}"

    shares_difference = credit_table(full.journeys, models=("shapley", "linear")).pipe(
        lambda frame: (frame["shapley"] - frame["linear"]).abs().max()
    )
    assert float(shares_difference) < 1e-15
    assert float(shares_difference) == pytest.approx(1.1e-16, rel=0.5)


def test_the_untouched_conversions_are_the_published_share(full: Dataset) -> None:
    missing = unattributable(full.audience, full.journeys)
    assert missing["conversions"] == 19_418.0
    assert missing["attributable"] == 17_446.0
    assert missing["untouched"] == 1_972.0
    assert missing["untouched_share"] == pytest.approx(0.1016, abs=5e-5)


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
        "social-pago": (0.029087, 0.027398, 0.030775, 0.0000, True),
        "busca-generica": (0.007088, 0.005338, 0.008839, 0.0000, True),
        "email": (0.004606, 0.002843, 0.006368, 0.0000, True),
        "retargeting": (0.000396, -0.000999, 0.001791, 0.5687, False),
        "busca-marca": (0.001342, -0.000636, 0.003320, 0.1759, False),
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


def test_four_holdout_intervals_of_five_cover_the_lift_the_generator_declared(
    full: Dataset,
) -> None:
    """Four of five, which is the claim - and the fifth is published rather than hidden.

    A 95% interval is wrong one time in twenty by construction. Five were computed and one missed,
    on the channel with the largest effect, by 2.6 predicted standard errors. An estimator whose
    intervals never missed across five tests would be one whose intervals were too wide.
    """
    designs = full.geo_designs.set_index("channel")
    design = _published_design()
    covered = []
    missed = []
    for channel, result in _holdouts(full).items():
        truth = float(designs.loc[channel, "true_rate_lift"])
        low, high = result.interval  # type: ignore[attr-defined]
        (covered if low <= truth <= high else missed).append(channel)
    assert sorted(covered) == ["busca-generica", "busca-marca", "email", "retargeting"]
    assert missed == ["social-pago"]

    social = _holdouts(full)["social-pago"]
    truth = float(designs.loc["social-pago", "true_rate_lift"])
    distance = (social.lift - truth) / design.standard_error(truth)  # type: ignore[attr-defined]
    assert distance == pytest.approx(2.6, abs=0.05)


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
        "email": (20_000.0, 2_996.0, 26.964, 921.1538, 8.2904, True, 3.2524),
        "retargeting": (60_000.0, 3_140.0, 9.420, 79.2308, 0.2377, False, None),
        "busca-marca": (90_000.0, 4_051.0, 8.102, 268.4615, 0.5369, False, None),
        "busca-generica": (120_000.0, 3_743.0, 5.6145, 1_417.6923, 2.1265, True, 2.6402),
        "social-pago": (180_000.0, 3_516.0, 3.516, 5_817.3077, 5.8173, True, 0.6044),
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
    assert blended_roas == pytest.approx(6.6814, abs=5e-5)
    assert blended_iroas == pytest.approx(3.2568, abs=5e-5)
    assert blended_roas / blended_iroas == pytest.approx(2.05, abs=0.01)

    unestablished = float(priced.loc[~priced["established"], "spend"].sum())
    assert unestablished == 150_000.0
    assert unestablished / total_spend == pytest.approx(0.319, abs=5e-4)


def test_roas_understates_the_one_channel_that_creates_demand(full: Dataset) -> None:
    """The half of the finding that gets missed: the error runs both ways.

    social-pago is last by ROAS and second by incremental return, and it is the only channel whose
    credited figure understates it. Which channel tops the incremental ranking is not the claim -
    that the ROAS ranking inverts for the demand-creating channel is.
    """
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
    established = priced.loc[priced["established"], "iroas"].sort_values(ascending=False)
    assert list(established.index) == ["email", "social-pago", "busca-generica"]
    assert float(understated.loc["social-pago", "ratio"]) == pytest.approx(0.6044, abs=5e-5)


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
        "social-pago": (0.000797, 0.000834, 1.0461, 1.0000),
        "email": (0.000820, 0.000870, 1.0608, 0.9671),
        "busca-generica": (0.000816, 0.000865, 1.0590, 1.0000),
        "retargeting": (0.000823, 0.000689, 0.8366, 0.0500),
        "busca-marca": (0.000823, 0.000968, 1.1754, 0.0500),
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
        "retargeting": (0.2377, -0.5991, 1.0745, 1.4166, False),
        "busca-marca": (0.5369, -0.2543, 1.3282, 0.9444, True),
    }
    for channel, (iroas, low, high, floor, big_enough) in published.items():
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
        # The pair the README turns on: one null the design could resolve, one it could not.
        assert read.was_big_enough is big_enough, channel


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
        "read-once": (0.8011, 1.1250, 1.0000, 1.0000),
        "obrien-fleming": (0.8006, 1.2695, 9.79, 1.0000),
        "pocock": (0.8011, 1.4815, 7.82, 0.9997),
        "naive": (0.8007, 1.7308, 7.01, 0.9926),
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
        "read-once": (0.3008, 1.8036, 1.0000, 0.9987),
        "naive": (0.4780, 2.6344, 9.55, 0.9614),
    }
    for rule, (achieved, ratio, looks, same_sign) in published.items():
        measured = exaggeration(plan(rule, LOOKS).boundary, weak)
        assert measured["power"] == pytest.approx(achieved, abs=5e-4), rule
        assert measured["ratio"] == pytest.approx(ratio, abs=5e-4), rule
        assert measured["expected_looks"] == pytest.approx(looks, abs=5e-3), rule
        assert measured["same_sign"] == pytest.approx(same_sign, abs=5e-5), rule
    assert 1.0 - published["naive"][3] == pytest.approx(0.039, abs=5e-4)


def test_the_t_against_z_gap_the_readme_quotes_is_right() -> None:
    """The accuracy of composing normal-theory boundaries with a t-based sizing."""
    design = _published_design()
    critical = float(stats.t.ppf(0.975, design.df))
    normal = float(stats.norm.ppf(0.975))
    assert critical / normal - 1.0 == pytest.approx(0.033, abs=5e-4)


# --- Wave 4: monitoring, from src/mktlab/design/README-monitoring.md ---------------------------

ONE_SIDED = 0.025


def _shares() -> tuple[float, ...]:
    return equal_information(LOOKS)


def _never() -> tuple[float, ...]:
    return (-UNREACHABLE,) * LOOKS


def _design_effect() -> float:
    """The alternative the published plan is powered for, re-derived rather than copied."""
    efficacy = spending_boundary(_shares(), ONE_SIDED)
    return float(
        optimize.brentq(
            lambda ncp: (
                crossing_probability(
                    efficacy, drift=ncp / LOOKS**0.5, fractions=_shares(), futility=_never()
                )[-1]
                - DEFAULT_POWER
            ),
            0.5,
            20.0,
            xtol=1e-12,
        )
    )


def test_the_design_effect_the_monitoring_readme_quotes_is_right() -> None:
    assert _design_effect() == pytest.approx(2.8591, abs=5e-5)


def test_every_reading_schedule_spends_exactly_the_published_error_rate() -> None:
    published = {
        "weekly": (_shares(), 7.9965, 2.0981),
        "monthly": ((4 / 13, 8 / 13, 1.0), 3.8751, 1.9835),
        "late start": ((0.5, 0.75, 0.9, 1.0), 2.9626, 2.0731),
        "read once": ((1.0,), 1.9600, 1.9600),
    }
    for label, (shares, first, last) in published.items():
        boundary = spending_boundary(shares, ONE_SIDED)
        assert boundary[0] == pytest.approx(first, abs=5e-5), label
        assert boundary[-1] == pytest.approx(last, abs=5e-5), label
        spent = crossing_probability(
            boundary, fractions=shares, futility=(-UNREACHABLE,) * len(shares)
        )[-1]
        assert spent == pytest.approx(ONE_SIDED, abs=1e-9), label


def test_the_approximation_table_against_the_exact_boundary_is_published_correctly() -> None:
    approximate = spending_boundary(_shares(), ONE_SIDED)
    exact = obrien_fleming(LOOKS, 2.0 * ONE_SIDED)
    published = {
        1: (7.9965, 7.5799, 1.0550),
        2: (5.5954, 5.3598, 1.0440),
        4: (3.8801, 3.7900, 1.0238),
        7: (2.8881, 2.8649, 1.0081),
        10: (2.4005, 2.3970, 1.0015),
        12: (2.1858, 2.1881, 0.9990),
        13: (2.0981, 2.1023, 0.9980),
    }
    for look, (spending, classical, ratio) in published.items():
        index = look - 1
        assert approximate[index] == pytest.approx(spending, abs=5e-5), look
        assert exact[index] == pytest.approx(classical, abs=5e-5), look
        assert approximate[index] / exact[index] == pytest.approx(ratio, abs=5e-5), look
    ratios = [a / b for a, b in zip(approximate, exact, strict=True)]
    assert ratios == sorted(ratios, reverse=True)


def test_the_pocock_spending_gap_is_what_is_published() -> None:
    assert pocock(LOOKS, 2.0 * ONE_SIDED)[0] == pytest.approx(2.6019, abs=5e-5)
    loose = spending_boundary(_shares(), ONE_SIDED, "pocock")[0]
    assert loose == pytest.approx(2.7366, abs=5e-5)
    assert loose / pocock(LOOKS, 2.0 * ONE_SIDED)[0] - 1.0 == pytest.approx(0.052, abs=5e-4)


def test_the_published_schedule_is_row_for_row_what_the_readme_prints() -> None:
    built = monitoring_plan(_shares(), _design_effect(), alpha=ONE_SIDED)
    table = schedule(built).set_index("look")
    published = {
        1: (0.0769, 0.000000, 7.9965, -3.6818, 0.000004),
        3: (0.2308, 0.000003, 4.5216, -1.0694, 0.007636),
        5: (0.3846, 0.000301, 3.4467, -0.0768, 0.038787),
        6: (0.4615, 0.000969, 3.1308, 0.2630, 0.059242),
        9: (0.6923, 0.007064, 2.5347, 1.0200, 0.123503),
        13: (1.0000, 0.025000, 2.0981, 2.0981, 0.200000),
    }
    for look, (information, spent, efficacy, futility, beta) in published.items():
        row = table.loc[look]
        assert float(row["information"]) == pytest.approx(information, abs=5e-5), look
        assert float(row["alpha_spent"]) == pytest.approx(spent, abs=5e-7), look
        assert float(row["efficacy"]) == pytest.approx(efficacy, abs=5e-5), look
        assert float(row["futility"]) == pytest.approx(futility, abs=5e-5), look
        assert float(row["beta_spent"]) == pytest.approx(beta, abs=5e-7), look
    # The two claims the table is read for: nothing ends the test in week one, and the last look
    # ends it either way.
    assert float(table.loc[1, "futility"]) < -3.0
    assert float(table.loc[6, "futility"]) > 0.0
    assert float(table.loc[13, "futility"]) == pytest.approx(float(table.loc[13, "efficacy"]))


def test_the_cost_and_benefit_of_futility_are_published_correctly() -> None:
    powered_for = _design_effect()
    open_ended = monitoring_plan(_shares(), powered_for, alpha=ONE_SIDED, beta=None)
    with_futility = monitoring_plan(_shares(), powered_for, alpha=ONE_SIDED)

    assert open_ended.true_alpha == pytest.approx(0.025000, abs=5e-7)
    assert with_futility.true_alpha == pytest.approx(0.022421, abs=5e-7)
    assert open_ended.power == pytest.approx(0.800000, abs=5e-7)
    assert with_futility.power == pytest.approx(0.765575, abs=5e-7)
    assert open_ended.information_to_restore_power() == pytest.approx(1.000000, abs=5e-7)
    assert with_futility.information_to_restore_power() == pytest.approx(1.088761, abs=5e-6)
    assert open_ended.expected_looks_under(0.0) == pytest.approx(12.94, abs=5e-3)
    assert with_futility.expected_looks_under(0.0) == pytest.approx(6.09, abs=5e-3)
    assert open_ended.expected_looks_under(powered_for) == pytest.approx(9.83, abs=5e-3)
    assert with_futility.expected_looks_under(powered_for) == pytest.approx(8.94, abs=5e-3)
    assert with_futility.abandoned_under_null == pytest.approx(0.977579, abs=5e-7)
    assert with_futility.abandoned_under_alternative == pytest.approx(0.234425, abs=5e-7)

    # The prose figures: 8.9% more information, and the test cut in half on a dead channel.
    assert with_futility.information_to_restore_power() - 1.0 == pytest.approx(0.089, abs=5e-4)
    halved = with_futility.expected_looks_under(0.0) / open_ended.expected_looks_under(0.0)
    assert halved == pytest.approx(0.47, abs=5e-3)


def test_futility_saves_calendar_and_not_conversions() -> None:
    """The claim that corrects this repository's own roadmap, as arithmetic.

    A channel doing nothing costs nothing to hold out, so the case futility fires on is the case
    where there was no conversion cost to save. What it saves there is weeks.
    """
    powered_for = _design_effect()
    open_ended = monitoring_plan(_shares(), powered_for, alpha=ONE_SIDED, beta=None)
    with_futility = monitoring_plan(_shares(), powered_for, alpha=ONE_SIDED)
    design = _published_design()
    per_week = design.holdout_geos * design.users_per_geo_week
    email = next(profile for profile in CHANNELS if profile.channel == "email")

    dead_without = open_ended.expected_looks_under(0.0)
    dead_with = with_futility.expected_looks_under(0.0)
    assert per_week * dead_without * 0.0 == 0.0
    assert per_week * dead_with * 0.0 == 0.0
    assert dead_without - dead_with == pytest.approx(6.85, abs=5e-3)

    lift = true_rate_lift(email)
    live_without = per_week * open_ended.expected_looks_under(powered_for) * lift
    live_with = per_week * with_futility.expected_looks_under(powered_for) * lift
    assert live_without == pytest.approx(1258.85, abs=5e-2)
    assert live_with == pytest.approx(1143.81, abs=5e-2)
    assert live_without - live_with == pytest.approx(115.0, abs=0.5)
    assert holdout_cost(design, lift, AUDIENCE.value_per_conversion)[
        "forgone_conversions"
    ] == pytest.approx(1664.0)


def test_the_spending_family_trades_power_for_calendar_monotonically() -> None:
    powered_for = _design_effect()
    published = {
        ("obrien-fleming", 3.0): (0.000053, 7.9965, 0.765575, 6.09, 0.234425),
        ("power", 3.0): (0.000728, 4.2360, 0.783266, 7.12, 0.216734),
        ("power", 1.0): (0.007692, 2.8905, 0.713910, 5.27, 0.286090),
        ("pocock", 3.0): (0.010610, 2.7366, 0.681486, 4.91, 0.318514),
    }
    for (family, rho), values in published.items():
        spent, first, power_value, looks, abandoned = values
        boundary = spending_boundary(_shares(), ONE_SIDED, family, rho)
        built = monitoring_plan(_shares(), powered_for, alpha=ONE_SIDED, family=family, rho=rho)
        assert alpha_spent(_shares()[3], ONE_SIDED, family, rho) == pytest.approx(
            spent, abs=5e-7
        ), family
        assert boundary[0] == pytest.approx(first, abs=5e-5), family
        assert built.power == pytest.approx(power_value, abs=5e-7), family
        assert built.expected_looks_under(0.0) == pytest.approx(looks, abs=5e-3), family
        assert built.abandoned_under_alternative == pytest.approx(abandoned, abs=5e-7), family

    # Ordered by how early each schedule spends: sooner off a dead channel, less power, more
    # winners abandoned. The ordering is the claim, not the individual figures.
    order = [("pocock", 3.0), ("power", 1.0), ("obrien-fleming", 3.0), ("power", 3.0)]
    plans = [
        monitoring_plan(_shares(), powered_for, alpha=ONE_SIDED, family=family, rho=rho)
        for family, rho in order
    ]
    assert [built.expected_looks_under(0.0) for built in plans] == sorted(
        built.expected_looks_under(0.0) for built in plans
    )
    assert [built.power for built in plans] == sorted(built.power for built in plans)
    assert [built.abandoned_under_alternative for built in plans] == sorted(
        (built.abandoned_under_alternative for built in plans), reverse=True
    )


# --- Wave 5: the media mix model, from src/mktlab/mmm/README.md --------------------------------


def test_the_panel_is_the_size_the_mmm_readme_quotes(full: Dataset) -> None:
    assert len(full.spend_panel) == 104
    assert MEDIA_MIX.adstock == 0.45
    assert MEDIA_MIX.saturation_at == 1.30
    assert MEDIA_MIX.budget_swing == 0.30
    assert MEDIA_MIX.idiosyncratic_swing == 0.12
    assert MEDIA_MIX.noise_sd == 9.0


def test_the_declared_returns_are_what_is_published(full: Dataset) -> None:
    published = {
        "social-pago": (0.0300, 0.016957),
        "email": (0.0320, 0.018087),
        "busca-generica": (0.0125, 0.007065),
        "retargeting": (0.0000, 0.000000),
        "busca-marca": (0.0000, 0.000000),
    }
    truth = full.media_truth.set_index("channel")
    for channel, (average, marginal) in published.items():
        assert float(truth.loc[channel, "conversions_per_unit_spend"]) == pytest.approx(
            average, abs=5e-5
        ), channel
        assert float(truth.loc[channel, "marginal_conversions_per_unit_spend"]) == pytest.approx(
            marginal, abs=5e-7
        ), channel
    # The ratio between the two, which the README quotes as 1.77 and identical across channels.
    for channel, (average, marginal) in published.items():
        if marginal:
            assert average / marginal == pytest.approx(1.77, abs=5e-3), channel


def test_the_spend_correlations_are_what_is_published(full: Dataset) -> None:
    columns = [f"spend_{profile.channel}" for profile in CHANNELS]
    correlations = full.spend_panel[columns].corr()
    published = {
        ("busca-generica", "busca-marca"): 0.8305,
        ("busca-generica", "email"): 0.8412,
        ("busca-generica", "retargeting"): 0.8388,
        ("busca-generica", "social-pago"): 0.8387,
        ("busca-marca", "email"): 0.8771,
        ("email", "social-pago"): 0.8789,
        ("retargeting", "social-pago"): 0.8584,
    }
    for (first, second), value in published.items():
        assert float(correlations.loc[f"spend_{first}", f"spend_{second}"]) == pytest.approx(
            value, abs=5e-5
        ), (first, second)
    off_diagonal = correlations.to_numpy()[correlations.to_numpy() < 1.0]
    assert off_diagonal.min() == pytest.approx(0.8305, abs=5e-5)


def test_the_variance_inflation_table_is_what_is_published(full: Dataset) -> None:
    published = {
        "email": (8.5249, 2.9197),
        "busca-generica": (6.8811, 2.6232),
        "busca-marca": (6.4804, 2.5457),
        "social-pago": (6.3857, 2.5270),
        "retargeting": (5.7315, 2.3940),
    }
    fitted = mmm_fit(full.spend_panel)
    factors = dict(zip(fitted.channels, fitted.vif, strict=True))
    for channel, (inflation, multiple) in published.items():
        assert float(factors[channel]) == pytest.approx(inflation, abs=5e-5), channel
        assert float(factors[channel]) ** 0.5 == pytest.approx(multiple, abs=5e-5), channel


def test_the_fitted_model_is_what_the_mmm_readme_publishes(full: Dataset) -> None:
    fitted = mmm_fit(full.spend_panel)
    assert fitted.r_squared == pytest.approx(0.8364, abs=5e-5)
    assert fitted.residual_sd == pytest.approx(8.718, abs=5e-4)
    assert fitted.df == 95.0
    assert fitted.condition_number == pytest.approx(7.01, abs=5e-3)

    published = {
        "social-pago": (139.3700, 47.7410, 2.9193, 0.0044, 44.59, 234.15),
        "busca-generica": (18.5883, 44.3302, 0.4193, 0.6759, -69.42, 106.59),
        "email": (5.7788, 49.9995, 0.1156, 0.9082, -93.48, 105.04),
        "retargeting": (2.7547, 42.4445, 0.0649, 0.9484, -81.51, 87.02),
        "busca-marca": (-16.6503, 46.6161, -0.3572, 0.7217, -109.20, 75.89),
    }
    table = fitted.table().set_index("channel")
    for channel, values in published.items():
        coefficient, error, statistic, p_value, low, high = values
        row = table.loc[channel]
        assert float(row["coefficient"]) == pytest.approx(coefficient, abs=5e-4), channel
        assert float(row["standard_error"]) == pytest.approx(error, abs=5e-4), channel
        assert float(row["t"]) == pytest.approx(statistic, abs=5e-4), channel
        assert float(row["p_value"]) == pytest.approx(p_value, abs=5e-4), channel
        assert float(row["low"]) == pytest.approx(low, abs=5e-2), channel
        assert float(row["high"]) == pytest.approx(high, abs=5e-2), channel


def test_the_model_resolves_one_channel_and_covers_every_truth(full: Dataset) -> None:
    fitted = mmm_fit(full.spend_panel)
    published = {
        "social-pago": (0.020475, 0.006551, 0.034398, 1.21, 1.64),
        "busca-generica": (0.004013, -0.014985, 0.023011, 0.57, 5.38),
        "email": (0.007425, -0.120121, 0.134972, 0.41, 14.10),
        "retargeting": (0.001194, -0.035331, 0.037719, None, None),
        "busca-marca": (-0.004758, -0.031202, 0.021687, None, None),
    }
    returns = fitted.returns(full.media_truth).set_index("channel")
    for channel, values in published.items():
        estimate, low, high, times, width = values
        row = returns.loc[channel]
        assert float(row["marginal_return"]) == pytest.approx(estimate, abs=5e-7), channel
        assert float(row["low"]) == pytest.approx(low, abs=5e-7), channel
        assert float(row["high"]) == pytest.approx(high, abs=5e-7), channel
        assert bool(row["covers_truth"]), channel
        if times is not None:
            assert float(row["times_the_truth"]) == pytest.approx(times, abs=5e-3), channel
            assert float(row["interval_width_over_truth"]) == pytest.approx(width, abs=5e-3), (
                channel
            )

    resolved = [
        channel
        for index, channel in enumerate(fitted.channels)
        if not fitted.interval(index)[0] <= 0.0 <= fitted.interval(index)[1]
    ]
    assert resolved == ["social-pago"]
    assert bool(returns["covers_truth"].all())


def test_the_equivalent_range_table_is_what_is_published(full: Dataset) -> None:
    fitted = mmm_fit(full.spend_panel)
    index = fitted.channels.index("social-pago")
    published = {
        0.001: (102.99, 175.75, 72.77),
        0.005: (58.02, 220.72, 162.71),
        0.010: (24.32, 254.42, 230.10),
    }
    for loss, (low, high, width) in published.items():
        got_low, got_high = fitted.equivalent_range(index, loss)
        assert got_low == pytest.approx(low, abs=5e-3), loss
        assert got_high == pytest.approx(high, abs=5e-3), loss
        assert got_high - got_low == pytest.approx(width, abs=5e-3), loss

    low, high = fitted.interval(index)
    assert low == pytest.approx(44.59, abs=5e-3)
    assert high == pytest.approx(234.15, abs=5e-3)
    assert high - low == pytest.approx(189.56, abs=5e-3)

    # The loss of fit the 95% interval corresponds to, which the README quotes as 0.0068.
    total = fitted.residual_sd**2 * fitted.df / (1.0 - fitted.r_squared)
    implied = fitted.critical_value**2 * fitted.residual_sd**2 / total
    assert implied == pytest.approx(0.0068, abs=5e-5)
    matched = fitted.equivalent_range(index, implied)
    assert matched[0] == pytest.approx(low, rel=1e-9)
    assert matched[1] == pytest.approx(high, rel=1e-9)


def test_the_transform_grid_is_what_is_published(full: Dataset) -> None:
    grid = mmm_transform_grid(
        full.spend_panel,
        carryovers=(0.0, 0.2, 0.45, 0.6, 0.8),
        saturations=(0.5, 1.3, 3.0, 10.0),
        truth=full.media_truth,
    )
    published = [
        (0.45, 3.0, 0.836444, 0.000000, 0.020463, 1.21),
        (0.45, 1.3, 0.836425, 0.000019, 0.020475, 1.21),
        (0.45, 10.0, 0.836148, 0.000295, 0.020174, 1.19),
        (0.45, 0.5, 0.835689, 0.000754, 0.019968, 1.18),
        (0.60, 1.3, 0.831749, 0.004695, 0.025993, 1.53),
        (0.60, 0.5, 0.831276, 0.005167, 0.026049, 1.54),
        (0.20, 10.0, 0.823651, 0.012793, 0.014909, 0.88),
        (0.20, 0.5, 0.819866, 0.016578, 0.014342, 0.85),
    ]
    indexed = grid.set_index(["adstock", "saturation_at"])
    for carryover, saturation, r_squared, loss, estimate, times in published:
        row = indexed.loc[(carryover, saturation)]
        assert float(row["r_squared"]) == pytest.approx(r_squared, abs=5e-7), (
            carryover,
            saturation,
        )
        assert float(row["fit_loss"]) == pytest.approx(loss, abs=5e-7), (carryover, saturation)
        assert float(row["social_pago_return"]) == pytest.approx(estimate, abs=5e-7)
        assert float(row["times_the_truth"]) == pytest.approx(times, abs=5e-3)

    near = grid[grid["fit_loss"] <= 0.01]
    assert len(near) == 8
    assert len(grid) == 20
    assert float(near["times_the_truth"].min()) == pytest.approx(1.18, abs=5e-3)
    assert float(near["times_the_truth"].max()) == pytest.approx(1.54, abs=5e-3)

    # The claim that corrects the lazy version: the carryover is identified, the saturation is not.
    right = indexed.xs(0.45, level="adstock")
    assert float(right["fit_loss"].max()) == pytest.approx(0.000754, abs=5e-7)
    assert float(right["social_pago_return"].max() / right["social_pago_return"].min()) == (
        pytest.approx(1.0254, abs=5e-4)
    )
    assert float(indexed.loc[(0.60, 1.3), "fit_loss"]) == pytest.approx(0.004695, abs=5e-7)


def test_the_misspecified_model_is_what_is_published(full: Dataset) -> None:
    good = mmm_fit(full.spend_panel)
    bare = mmm_fit(full.spend_panel, trend=False, seasonality=False)
    assert good.r_squared == pytest.approx(0.8364, abs=5e-5)
    assert bare.r_squared == pytest.approx(0.2371, abs=5e-5)

    published = {
        "social-pago": (0.031340, 0.003280, 0.059400, 1.85),
        "busca-generica": (-0.014840, -0.054512, 0.024831, -2.10),
        "email": (-0.093731, -0.355965, 0.168503, -5.18),
        "busca-marca": (0.049819, -0.004444, 0.104082, None),
        "retargeting": (-0.016337, -0.089660, 0.056986, None),
    }
    returns = bare.returns(full.media_truth).set_index("channel")
    for channel, values in published.items():
        estimate, low, high, times = values
        row = returns.loc[channel]
        assert float(row["marginal_return"]) == pytest.approx(estimate, abs=5e-7), channel
        assert float(row["low"]) == pytest.approx(low, abs=5e-7), channel
        assert float(row["high"]) == pytest.approx(high, abs=5e-7), channel
        if times is not None:
            assert float(row["times_the_truth"]) == pytest.approx(times, abs=5e-3), channel
    assert bool(returns["covers_truth"].all()), "coverage never catches this"


def test_the_model_against_the_holdout_is_what_is_published(full: Dataset) -> None:
    """The comparison of precision relative to what each instrument estimates."""
    fitted = mmm_fit(full.spend_panel)
    returns = fitted.returns(full.media_truth).set_index("channel")
    declared = full.media_truth.set_index("channel")
    published = {
        "social-pago": (0.1251, 1.6423, 13.13),
        "email": (1.1015, 14.1037, 12.80),
        "busca-generica": (0.4668, 5.3779, 11.52),
    }
    for channel, (holdout_width, model_width, ratio) in published.items():
        profile = next(item for item in CHANNELS if item.channel == channel)
        panel = full.geo_experiments[full.geo_experiments["channel"] == channel]
        lift = geo_lift(panel, split=GEO.split, channel=channel)
        scale = AUDIENCE.users / profile.spend
        low, high = lift.interval
        average = float(declared.loc[channel, "conversions_per_unit_spend"])
        measured_holdout = (high - low) * scale / average
        measured_model = float(returns.loc[channel, "interval_width_over_truth"])
        assert measured_holdout == pytest.approx(holdout_width, abs=5e-5), channel
        assert measured_model == pytest.approx(model_width, abs=5e-5), channel
        assert measured_model / measured_holdout == pytest.approx(ratio, abs=5e-3), channel

    resolved_by_holdout = sum(
        geo_lift(
            full.geo_experiments[full.geo_experiments["channel"] == profile.channel],
            split=GEO.split,
            channel=profile.channel,
        ).significant
        for profile in CHANNELS
    )
    resolved_by_model = sum(
        1
        for index in range(len(fitted.channels))
        if not fitted.interval(index)[0] <= 0.0 <= fitted.interval(index)[1]
    )
    assert resolved_by_holdout == 3
    assert resolved_by_model == 1


# --- Wave 6: the calibration, from src/mktlab/calibration/README.md ----------------------------


def wave_six_priors(
    full: Dataset, channels: list[str], convert: bool = True
) -> tuple[object, dict]:
    """The fit and the priors the wave 6 document is built on."""
    baseline = mmm_fit(full.spend_panel)
    priors = {}
    for channel in channels:
        profile = next(item for item in CHANNELS if item.channel == channel)
        panel = full.geo_experiments[full.geo_experiments["channel"] == channel]
        lift = geo_lift(panel, split=GEO.split, channel=channel)
        priors[channel] = prior_from_holdout(
            lift,
            baseline,
            channel,
            reach=float(AUDIENCE.users),
            spend=profile.spend,
            convert=convert,
        )
    return baseline, priors


WAVE_SIX_RESOLVED = ["social-pago", "email", "busca-generica"]


def test_the_average_to_marginal_factors_are_what_is_published(full: Dataset) -> None:
    """Result 1: the closed form, the four rows of its table, and the generator's own ratio."""
    published = {0.5: 3.0000, 1.3: 1.7692, 3.0: 1.3333, 10.0: 1.1000}
    for multiple, factor in published.items():
        assert average_to_marginal(multiple) == pytest.approx(factor, abs=5e-5), multiple
    assert average_to_marginal(MEDIA_MIX.saturation_at) == pytest.approx(1.7692307692, abs=5e-11)
    truth = full.media_truth.set_index("channel")
    for channel in WAVE_SIX_RESOLVED:
        ratio = float(truth.loc[channel, "conversions_per_unit_spend"]) / float(
            truth.loc[channel, "marginal_conversions_per_unit_spend"]
        )
        # To the ten digits the document prints. The closed form and the generator agree far past
        # that - the identity is checked exactly in tests/test_calibration.py - but a published
        # constant can only be asserted to the precision it was published at.
        assert ratio == pytest.approx(1.7692307692, abs=5e-11), channel


def test_the_published_priors_are_what_the_holdouts_produce(full: Dataset) -> None:
    """Result 2, first table: every column of the three priors the document quotes."""
    published = {
        "social-pago": (0.032318, 0.018267, 1.0773, 124.3418, 3.5633),
        "email": (0.046058, 0.026033, 1.4393, 20.2596, 3.8282),
        "busca-generica": (0.011814, 0.006678, 0.9451, 30.9328, 3.7726),
    }
    _, priors = wave_six_priors(full, WAVE_SIX_RESOLVED)
    truth = full.media_truth.set_index("channel")
    for channel, (average, marginal, times, mean, error) in published.items():
        prior = priors[channel]
        assert prior.average_return == pytest.approx(average, abs=5e-7), channel
        assert prior.marginal_return == pytest.approx(marginal, abs=5e-7), channel
        assert prior.conversion_factor == pytest.approx(1.769231, abs=5e-7), channel
        real = float(truth.loc[channel, "marginal_conversions_per_unit_spend"])
        assert prior.marginal_return / real == pytest.approx(times, abs=5e-5), channel
        assert prior.mean == pytest.approx(mean, abs=5e-5), channel
        assert prior.standard_error == pytest.approx(error, abs=5e-5), channel


def test_the_calibration_table_is_what_is_published(full: Dataset) -> None:
    """Result 2, second table: the prior, the model, the posterior and the width kept."""
    published = {
        "social-pago": (124.3418, 14.1479, 139.3700, 189.5556, 124.3782, 14.0984, 0.0744),
        "email": (20.2596, 15.2000, 5.7788, 198.5230, 20.1673, 15.1464, 0.0763),
        "busca-generica": (30.9328, 14.9793, 18.5883, 176.0132, 30.8354, 14.9135, 0.0847),
    }
    unpriored = {
        "busca-marca": (-16.6503, 185.0894, -25.2209, 139.2410, 0.7523),
        "retargeting": (2.7547, 168.5260, -1.1745, 136.3520, 0.8091),
    }
    _, priors = wave_six_priors(full, WAVE_SIX_RESOLVED)
    table = calibrate(full.spend_panel, priors).table().set_index("channel")
    for channel, values in published.items():
        prior_mean, prior_width, model, model_width, posterior, width, kept = values
        row = table.loc[channel]
        assert float(row["prior_mean"]) == pytest.approx(prior_mean, abs=5e-5), channel
        assert float(row["prior_width"]) == pytest.approx(prior_width, abs=5e-5), channel
        assert float(row["model_mean"]) == pytest.approx(model, abs=5e-5), channel
        assert float(row["model_width"]) == pytest.approx(model_width, abs=5e-5), channel
        assert float(row["posterior_mean"]) == pytest.approx(posterior, abs=5e-5), channel
        assert float(row["posterior_width"]) == pytest.approx(width, abs=5e-5), channel
        assert float(row["width_kept"]) == pytest.approx(kept, abs=5e-5), channel
        # The document's claim that the model's own contribution rounds to nothing on these three.
        assert abs(posterior - prior_mean) / abs(prior_mean) < 0.005, channel
    for channel, values in unpriored.items():
        model, model_width, posterior, width, kept = values
        row = table.loc[channel]
        assert np.isnan(float(row["prior_mean"])), channel
        assert float(row["model_mean"]) == pytest.approx(model, abs=5e-5), channel
        assert float(row["model_width"]) == pytest.approx(model_width, abs=5e-5), channel
        assert float(row["posterior_mean"]) == pytest.approx(posterior, abs=5e-5), channel
        assert float(row["posterior_width"]) == pytest.approx(width, abs=5e-5), channel
        assert float(row["width_kept"]) == pytest.approx(kept, abs=5e-5), channel


def test_the_transfer_resolves_three_of_five_and_covers_four(full: Dataset) -> None:
    """Result 2 and Result 3: the counts, the returns, and the fit the transfer costs."""
    published = {
        "social-pago": (0.018272, 0.017237, 0.019308, False, 1.0776, 0.1221, True),
        "email": (0.025914, 0.016183, 0.035645, True, 1.4327, 1.0760, True),
        "busca-generica": (0.006657, 0.005047, 0.008266, True, 0.9422, 0.4557, True),
    }
    baseline, priors = wave_six_priors(full, WAVE_SIX_RESOLVED)
    calibrated = calibrate(full.spend_panel, priors)
    table = calibrated.transfer(full.media_truth).set_index("channel")
    for channel, values in published.items():
        estimate, low, high, covers, times, width, resolved = values
        row = table.loc[channel]
        assert float(row["posterior_return"]) == pytest.approx(estimate, abs=5e-7), channel
        assert float(row["low"]) == pytest.approx(low, abs=5e-7), channel
        assert float(row["high"]) == pytest.approx(high, abs=5e-7), channel
        assert bool(row["covers_truth"]) is covers, channel
        assert float(row["times_the_truth"]) == pytest.approx(times, abs=5e-5), channel
        assert float(row["interval_width_over_truth"]) == pytest.approx(width, abs=5e-5), channel
        assert bool(row["resolved"]) is resolved, channel
    for channel, low, high in (
        ("busca-marca", -0.027101, 0.012687),
        ("retargeting", -0.030061, 0.029043),
    ):
        row = table.loc[channel]
        assert float(row["low"]) == pytest.approx(low, abs=5e-7), channel
        assert float(row["high"]) == pytest.approx(high, abs=5e-7), channel
        assert bool(row["covers_truth"]), channel
        assert not bool(row["resolved"]), channel

    assert int(table["resolved"].sum()) == 3
    assert int(table["covers_truth"].sum()) == 4
    before = baseline.returns(full.media_truth)
    resolved_before = sum(
        1 for low, high in zip(before["low"], before["high"], strict=True) if low > 0 or high < 0
    )
    assert resolved_before == 1
    assert int(before["covers_truth"].sum()) == 5
    assert baseline.r_squared == pytest.approx(0.836425, abs=5e-7)
    assert calibrated.posterior.r_squared == pytest.approx(0.836050, abs=5e-7)
    assert baseline.r_squared - calibrated.posterior.r_squared == pytest.approx(0.000374, abs=5e-7)


def test_the_lost_coverage_was_inherited_from_the_holdout(full: Dataset) -> None:
    """Result 3: the holdout's own interval on the average return, and the weight it carried."""
    published = {
        "social-pago": (0.030442, 0.034194, 0.030000, False),
        "email": (0.028433, 0.063682, 0.032000, True),
        "busca-generica": (0.008897, 0.014731, 0.012500, True),
    }
    baseline, priors = wave_six_priors(full, WAVE_SIX_RESOLVED)
    for channel, (low, high, average_truth, covers) in published.items():
        profile = next(item for item in CHANNELS if item.channel == channel)
        panel = full.geo_experiments[full.geo_experiments["channel"] == channel]
        lift = geo_lift(panel, split=GEO.split, channel=channel)
        scale = AUDIENCE.users / profile.spend
        interval = (lift.interval[0] * scale, lift.interval[1] * scale)
        assert interval[0] == pytest.approx(low, abs=5e-7), channel
        assert interval[1] == pytest.approx(high, abs=5e-7), channel
        assert bool(interval[0] <= average_truth <= interval[1]) is covers, channel

    index = baseline.channels.index("social-pago")
    model_precision = 1.0 / float(baseline.standard_errors[index]) ** 2
    prior_precision = 1.0 / priors["social-pago"].standard_error ** 2
    weight = model_precision / (model_precision + prior_precision)
    assert weight == pytest.approx(0.0055, abs=5e-5)
    # And the model's own interval did cover the truth it was overruled about.
    low, high = (
        baseline.returns(full.media_truth).set_index("channel").loc["social-pago", ["low", "high"]]
    )
    assert float(low) <= 0.016957 <= float(high)


def test_the_naive_calibration_is_what_is_published(full: Dataset) -> None:
    """Result 4: one skipped division, four channels resolved and one covering interval."""
    published = {
        "social-pago": (0.031988, 1.8865, False, True),
        "email": (0.044009, 2.4332, False, True),
        "busca-generica": (0.011393, 1.6126, False, True),
    }
    _, priors = wave_six_priors(full, WAVE_SIX_RESOLVED, convert=False)
    calibrated = calibrate(full.spend_panel, priors)
    table = calibrated.transfer(full.media_truth).set_index("channel")
    for channel, (estimate, times, covers, resolved) in published.items():
        row = table.loc[channel]
        assert float(row["posterior_return"]) == pytest.approx(estimate, abs=5e-7), channel
        assert float(row["times_the_truth"]) == pytest.approx(times, abs=5e-5), channel
        assert bool(row["covers_truth"]) is covers, channel
        assert bool(row["resolved"]) is resolved, channel
    # The manufactured finding: a confident negative return on a channel whose truth is zero.
    marca = table.loc["busca-marca"]
    assert float(marca["low"]) == pytest.approx(-0.045283, abs=5e-7)
    assert float(marca["high"]) == pytest.approx(-0.005099, abs=5e-7)
    assert float(marca["high"]) < 0.0
    assert bool(marca["resolved"])
    assert not bool(marca["covers_truth"])
    assert int(table["resolved"].sum()) == 4
    assert int(table["covers_truth"].sum()) == 1
    assert calibrated.posterior.r_squared == pytest.approx(0.824520, abs=5e-7)


def test_a_null_holdout_buys_what_is_published(full: Dataset) -> None:
    """Result 5: the two channels the holdout could not resolve, used as priors anyway."""
    published = {
        "retargeting": (168.5260, 11.8594, 0.0704, 0.000742, -0.001828, 0.003313),
        "busca-marca": (185.0894, 16.8217, 0.0909, 0.001632, -0.000771, 0.004035),
    }
    _, priors = wave_six_priors(full, ["retargeting", "busca-marca"])
    calibrated = calibrate(full.spend_panel, priors)
    table = calibrated.table().set_index("channel")
    transferred = calibrated.transfer(full.media_truth).set_index("channel")
    for channel, (model_width, width, kept, estimate, low, high) in published.items():
        assert float(table.loc[channel, "model_width"]) == pytest.approx(model_width, abs=5e-5), (
            channel
        )
        assert float(table.loc[channel, "posterior_width"]) == pytest.approx(width, abs=5e-5), (
            channel
        )
        assert float(table.loc[channel, "width_kept"]) == pytest.approx(kept, abs=5e-5), channel
        assert float(transferred.loc[channel, "posterior_return"]) == pytest.approx(
            estimate, abs=5e-7
        ), channel
        assert float(transferred.loc[channel, "low"]) == pytest.approx(low, abs=5e-7), channel
        assert float(transferred.loc[channel, "high"]) == pytest.approx(high, abs=5e-7), channel
        assert bool(transferred.loc[channel, "covers_truth"]), channel
        assert not bool(transferred.loc[channel, "resolved"]), channel
        assert 11.0 <= 1.0 / kept <= 14.5, channel


def test_one_prior_moves_every_other_channel_by_what_is_published(full: Dataset) -> None:
    """Result 6: the spillover table, and that the widths moved by less than five per cent."""
    published = {
        "social-pago": (0.020475, 0.018279, 0.8928, 0.0744),
        "email": (0.007425, 0.013037, 1.7558, 0.9605),
        "retargeting": (0.001194, 0.002780, 2.3282, 0.9616),
        "busca-generica": (0.004013, 0.004895, 1.2199, 0.9559),
        "busca-marca": (-0.004758, -0.004224, 0.8878, 0.9918),
    }
    baseline, priors = wave_six_priors(full, ["social-pago"])
    calibrated = calibrate(full.spend_panel, priors)
    before = baseline.returns(full.media_truth).set_index("channel")
    after = calibrated.transfer(full.media_truth).set_index("channel")
    widths = calibrated.table().set_index("channel")
    for channel, (ols, posterior, moved, kept) in published.items():
        assert float(before.loc[channel, "marginal_return"]) == pytest.approx(ols, abs=5e-7), (
            channel
        )
        assert float(after.loc[channel, "posterior_return"]) == pytest.approx(
            posterior, abs=5e-7
        ), channel
        ratio = float(after.loc[channel, "posterior_return"]) / float(
            before.loc[channel, "marginal_return"]
        )
        assert ratio == pytest.approx(moved, abs=5e-5), channel
        assert float(widths.loc[channel, "width_kept"]) == pytest.approx(kept, abs=5e-5), channel
        if channel != "social-pago":
            assert float(widths.loc[channel, "width_kept"]) > 0.95, channel


def test_the_single_prior_identity_is_exact_and_several_are_bounded(full: Dataset) -> None:
    """Result 6's closed form: Sherman-Morrison exactly, and under two per cent of leak."""
    _, one = wave_six_priors(full, ["social-pago"])
    single = calibrate(full.spend_panel, one)
    table = single.table().set_index("channel")
    assert float(table.loc["social-pago", "posterior_width"]) == pytest.approx(
        single.independent_widths["social-pago"], rel=1e-12
    )
    _, five = wave_six_priors(full, [profile.channel for profile in CHANNELS])
    everything = calibrate(full.spend_panel, five)
    widths = everything.table().set_index("channel")
    for channel in everything.posterior.channels:
        actual = float(widths.loc[channel, "posterior_width"])
        identity = everything.independent_widths[channel]
        assert actual <= identity
        assert (identity - actual) / identity < 0.02, channel


def test_the_saturation_grid_is_what_is_published(full: Dataset) -> None:
    """Result 7: the four rows, and the two claims the wave ends on."""
    published = {
        0.5: (3.0000, 0.835689, 0.000754, 0.010796, 0.64, 0.0722),
        1.3: (1.7692, 0.836425, 0.000019, 0.018272, 1.08, 0.1221),
        3.0: (1.3333, 0.836444, 0.000000, 0.024157, 1.42, 0.1616),
        10.0: (1.1000, 0.836148, 0.000295, 0.029132, 1.72, 0.1953),
    }
    measured = {}
    for multiple in published:
        fitted = mmm_fit(full.spend_panel, saturation_at=multiple)
        priors = {}
        for channel in WAVE_SIX_RESOLVED:
            profile = next(item for item in CHANNELS if item.channel == channel)
            panel = full.geo_experiments[full.geo_experiments["channel"] == channel]
            priors[channel] = prior_from_holdout(
                geo_lift(panel, split=GEO.split, channel=channel),
                fitted,
                channel,
                reach=float(AUDIENCE.users),
                spend=profile.spend,
            )
        row = (
            calibrate(full.spend_panel, priors, saturation_at=multiple)
            .transfer(full.media_truth)
            .set_index("channel")
            .loc["social-pago"]
        )
        measured[multiple] = (fitted.r_squared, row)

    best = max(value[0] for value in measured.values())
    for multiple, values in published.items():
        factor, r_squared, loss, estimate, times, width = values
        fitted_r, row = measured[multiple]
        assert average_to_marginal(multiple) == pytest.approx(factor, abs=5e-5), multiple
        assert fitted_r == pytest.approx(r_squared, abs=5e-7), multiple
        assert best - fitted_r == pytest.approx(loss, abs=5e-7), multiple
        assert float(row["posterior_return"]) == pytest.approx(estimate, abs=5e-7), multiple
        assert float(row["times_the_truth"]) == pytest.approx(times, abs=5e-3), multiple
        assert float(row["interval_width_over_truth"]) == pytest.approx(width, abs=5e-5), multiple
        assert not bool(row["covers_truth"]), multiple

    # The two claims the document ends on: the best fit is not the true one, and the spread in the
    # answer is the spread in the conversion factor.
    best_multiple = max(measured, key=lambda key: measured[key][0])
    assert best_multiple == 3.0
    # The spread in the answer is nearly the spread in the conversion factor, and not exactly it:
    # changing the saturation point also changes the model's own design. The document says "nearly
    # all of it" because of this line, which is what the first draft claimed was an equality.
    times = [float(row["times_the_truth"]) for _, row in measured.values()]
    factor_spread = average_to_marginal(0.5) / average_to_marginal(10.0)
    assert max(times) / min(times) == pytest.approx(2.70, abs=5e-3)
    assert factor_spread == pytest.approx(2.73, abs=5e-3)
    assert max(times) / min(times) < factor_spread
    assert max(value[0] for value in measured.values()) - min(
        value[0] for value in measured.values()
    ) == pytest.approx(0.000754, abs=5e-7)
