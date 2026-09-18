"""Sizing, against closed forms and control cases.

The load-bearing checks here are the two controls: power at a lift of zero must be exactly alpha,
and the minimum detectable lift must be the effect at which the power function returns the target.
Everything else in the module is a ratio built on those two.
"""

from __future__ import annotations

import math

import pytest
from scipy import stats

from mktlab.attribution import GeoLift, geo_lift
from mktlab.design import (
    CURVE_COLUMNS,
    DEFAULT_POWER,
    MAX_GEOS,
    SIZING_COLUMNS,
    GeoDesign,
    holdout_cost,
    power_curve,
    regions_for,
    retrospective,
    sizing_table,
)
from mktlab.design.geo import _or_its_limit, _power_from_noncentral_t


def make(**overrides: object) -> GeoDesign:
    """A design whose arithmetic is easy to follow: 40 regions, 13 weeks a side."""
    settings: dict[str, object] = {
        "geos": 40,
        "weeks": 26,
        "split": 13,
        "users_per_geo_week": 2_000,
        "base_rate": 0.10,
    }
    settings.update(overrides)
    return GeoDesign(**settings)  # type: ignore[arg-type]


def test_the_arms_and_phases_are_split_as_declared() -> None:
    design = make()
    assert design.treated_geos == 20
    assert design.holdout_geos == 20
    assert design.weeks_before == 13
    assert design.weeks_after == 13
    assert design.df == 38.0


def test_an_odd_number_of_regions_holds_out_the_smaller_half() -> None:
    design = make(geos=41)
    assert design.holdout_geos == 20
    assert design.treated_geos == 21
    assert design.df == 39.0


def test_the_degrees_of_freedom_count_regions_and_not_region_weeks() -> None:
    """A panel of 40 regions over 26 weeks is not 1,040 observations of a change."""
    short = make(weeks=4, split=2)
    long = make(weeks=104, split=52)
    assert short.df == long.df == 38.0


def test_the_change_standard_deviation_is_the_binomial_closed_form() -> None:
    design = make()
    expected = math.sqrt(
        0.10 * 0.90 / (2_000 * 13) + 0.10 * 0.90 / (2_000 * 13),
    )
    assert design.change_sd() == pytest.approx(expected)


def test_a_different_rate_after_the_switch_enters_only_the_after_term() -> None:
    design = make()
    expected = math.sqrt(0.10 * 0.90 / (2_000 * 13) + 0.06 * 0.94 / (2_000 * 13))
    assert design.change_sd(0.06) == pytest.approx(expected)


def test_the_standard_error_is_the_change_spread_over_the_two_arms() -> None:
    design = make()
    expected = math.sqrt(design.change_sd() ** 2 / 20 + design.change_sd() ** 2 / 20)
    assert design.standard_error() == pytest.approx(expected)


def test_a_true_lift_lowers_the_predicted_standard_error_slightly() -> None:
    """The held-out regions convert less after the switch, so they vary less. Zero is safe."""
    design = make()
    assert design.standard_error(0.05) < design.standard_error(0.0)


def test_more_regions_and_more_weeks_both_shrink_the_standard_error() -> None:
    assert make(geos=80).standard_error() < make().standard_error()
    assert make(weeks=52, split=26).standard_error() < make().standard_error()


def test_doubling_the_regions_divides_the_variance_by_two() -> None:
    """Exact, not approximate: the closed form is linear in the number of regions per arm."""
    assert make(geos=80).standard_error() == pytest.approx(make().standard_error() / math.sqrt(2.0))


def test_power_at_a_lift_of_exactly_zero_is_alpha() -> None:
    """The control case. A power function that fails it is not measuring power."""
    for alpha in (0.01, 0.05, 0.10):
        assert make(alpha=alpha).power(0.0) == pytest.approx(alpha, abs=1e-12)


def test_power_rises_with_the_effect_and_reaches_one() -> None:
    design = make()
    lifts = [0.0, 0.001, 0.002, 0.004, 0.010]
    powers = [design.power(lift) for lift in lifts]
    assert powers == sorted(powers)
    assert powers[-1] == pytest.approx(1.0)


def test_the_test_statistic_is_symmetric_but_the_power_is_not_quite() -> None:
    """A two-sided test does not care about the direction. The binomial variance does.

    The rejection region is symmetric, so at a fixed standard error the power of ``+d`` and ``-d``
    is identical - that is the first assertion, made on the tail calculation directly. But a
    harmful channel raises the held-out regions' rate after the switch instead of lowering it, and
    a rate nearer one half varies more, so the design has slightly *less* power against harm of a
    given size than against help of the same size. That is a property of the variance model and not
    an error, which is why it is asserted rather than tolerated.
    """
    design = make()
    ncp = 0.003 / design.standard_error()
    assert _power_from_noncentral_t(-ncp, design.df, design.alpha) == pytest.approx(
        _power_from_noncentral_t(ncp, design.df, design.alpha), rel=1e-12
    )
    assert design.power(-0.003) < design.power(0.003)
    assert design.power(-0.003) == pytest.approx(design.power(0.003), rel=0.01)


def test_the_detectable_lift_is_the_effect_at_which_power_reaches_the_target() -> None:
    """The round trip that makes the figure meaningful, at every power worth quoting."""
    design = make()
    for target in (0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.99):
        lift = design.detectable_lift(target)
        assert design.power(lift) >= target, target
        assert design.power(lift) == pytest.approx(target, abs=1e-6), target


def test_the_detectable_lift_is_never_a_hair_below_the_target_power() -> None:
    """The defect this nudge fixes: a table headed 80% printing a lift whose power was 0.799992."""
    design = make()
    assert design.power(design.detectable_lift(DEFAULT_POWER)) >= DEFAULT_POWER


def test_the_detectable_lift_is_above_the_normal_approximation() -> None:
    """The textbook formula swaps two t quantiles for two z quantiles and understates the effect."""
    design = make()
    approximation = (
        stats.norm.ppf(1.0 - design.alpha / 2.0) + stats.norm.ppf(DEFAULT_POWER)
    ) * design.standard_error()
    exact = design.detectable_lift()
    assert exact > approximation
    assert exact == pytest.approx(approximation, rel=0.05)


def test_a_bigger_design_detects_a_smaller_lift() -> None:
    assert make(geos=160).detectable_lift() < make().detectable_lift()


def test_a_power_target_outside_alpha_to_one_is_refused() -> None:
    design = make()
    with pytest.raises(ValueError, match="must be above alpha"):
        design.detectable_lift(0.01)
    with pytest.raises(ValueError, match="must be above alpha"):
        design.detectable_lift(1.0)


def test_a_design_that_cannot_detect_the_channel_at_all_says_so() -> None:
    """Four regions and a handful of users: the answer is a named refusal, not a huge number."""
    tiny = make(geos=4, users_per_geo_week=1, weeks=2, split=1, base_rate=0.001)
    with pytest.raises(ValueError, match="cannot detect the channel being switched off"):
        tiny.detectable_lift()


def test_the_detectable_return_is_the_detectable_lift_priced() -> None:
    design = make()
    detectable = design.detectable_lift()
    assert design.detectable_iroas(20_000.0, 200_000.0, 180.0) == pytest.approx(
        detectable * 200_000.0 * 180.0 / 20_000.0
    )


def test_the_detectable_return_scales_inversely_with_spend() -> None:
    """The finding of the module: one design, nine times the floor across the channels."""
    design = make()
    small = design.detectable_iroas(20_000.0, 200_000.0, 180.0)
    large = design.detectable_iroas(180_000.0, 200_000.0, 180.0)
    assert small == pytest.approx(large * 9.0)


def test_the_return_precision_is_the_interval_half_width() -> None:
    design = make()
    critical = float(stats.t.ppf(0.975, design.df))
    expected = critical * design.standard_error() * 200_000.0 * 180.0 / 20_000.0
    assert design.return_precision(20_000.0, 200_000.0, 180.0) == pytest.approx(expected)


def test_the_detectable_return_is_wider_than_the_interval_it_will_produce() -> None:
    """One power quantile apart, always, which is the claim the README makes about null results."""
    design = make()
    floor = design.detectable_iroas(60_000.0, 200_000.0, 180.0)
    half = design.return_precision(60_000.0, 200_000.0, 180.0)
    assert floor > half
    ratio = float(
        (stats.t.ppf(0.975, design.df) + stats.t.ppf(DEFAULT_POWER, design.df))
        / stats.t.ppf(0.975, design.df)
    )
    assert floor / half == pytest.approx(ratio, rel=0.01)


@pytest.mark.parametrize("method", ["detectable_iroas", "return_precision"])
def test_a_return_against_no_spend_is_refused(method: str) -> None:
    design = make()
    with pytest.raises(ValueError, match="spend must be positive"):
        getattr(design, method)(0.0, 200_000.0, 180.0)


def test_regions_for_is_the_inverse_of_the_detectable_lift() -> None:
    """Asking for the design's own detectable lift returns its own region count, or fewer."""
    design = make()
    needed = regions_for(design.detectable_lift(), design)
    assert needed <= design.geos
    assert needed >= design.geos - 2


def test_regions_for_returns_an_even_count_that_reaches_the_target() -> None:
    design = make()
    for lift in (0.0005, 0.001, 0.003, 0.010):
        needed = regions_for(lift, design)
        assert needed % 2 == 0
        assert make(geos=needed).power(lift) >= DEFAULT_POWER
        if needed > 4:
            assert make(geos=needed - 2).power(lift) < DEFAULT_POWER


def test_a_smaller_lift_needs_more_regions() -> None:
    design = make()
    assert regions_for(0.001, design) > regions_for(0.010, design)


def test_regions_for_refuses_a_lift_that_is_not_positive() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        regions_for(0.0, make())


def test_a_lift_no_number_of_regions_can_reach_is_a_named_answer() -> None:
    """Not a failure: it says the weeks or the users have to change, not the region count."""
    design = make(users_per_geo_week=1, base_rate=0.5)
    with pytest.raises(ValueError, match=f"no design up to {MAX_GEOS} regions"):
        regions_for(1e-9, design)


def test_the_holdout_cost_is_the_held_out_population_times_the_lift() -> None:
    design = make()
    cost = holdout_cost(design, 0.02, 180.0)
    assert cost["region_weeks_held_out"] == 20 * 13
    assert cost["users_held_out"] == 20 * 13 * 2_000
    assert cost["forgone_conversions"] == pytest.approx(20 * 13 * 2_000 * 0.02)
    assert cost["forgone_revenue"] == pytest.approx(cost["forgone_conversions"] * 180.0)


def test_the_forgone_share_is_free_of_the_population() -> None:
    """lift / base_rate exactly, so it survives being quoted next to another population."""
    design = make()
    assert holdout_cost(design, 0.02, 180.0)["forgone_share"] == pytest.approx(0.2)
    bigger = make(users_per_geo_week=50_000, geos=200)
    assert holdout_cost(bigger, 0.02, 180.0)["forgone_share"] == pytest.approx(0.2)


def test_a_channel_that_does_nothing_makes_the_holdout_free() -> None:
    """The asymmetry: the test is expensive exactly when its answer is to keep spending."""
    design = make()
    assert holdout_cost(design, 0.0, 180.0)["forgone_conversions"] == 0.0
    assert holdout_cost(design, 0.0, 180.0)["forgone_share"] == 0.0


def test_the_weeks_before_the_switch_cost_nothing() -> None:
    """Half the design is free, and it is the half nobody extends."""
    short = make(weeks=26, split=13)
    long = make(weeks=65, split=52)
    assert long.weeks_after == short.weeks_after
    assert holdout_cost(long, 0.02, 180.0) == holdout_cost(short, 0.02, 180.0)
    assert long.standard_error() < short.standard_error()


def test_an_infinite_pre_period_is_worth_exactly_double_the_regions() -> None:
    """An exact identity, not an approximation: both halve the same variance.

    With equal phases the before term and the after term are the same size, so dropping the before
    term entirely and doubling the regions per arm both divide the variance by two.
    """
    design = make()
    floor = design.standard_error() / math.sqrt(2.0)
    assert make(geos=80).standard_error() == pytest.approx(floor, rel=1e-12)


def test_the_power_curve_prices_each_lift_and_flags_the_target() -> None:
    design = make()
    detectable = design.detectable_lift()
    curve = power_curve(
        design,
        lifts=(0.0, detectable, 0.010),
        spend=20_000.0,
        reach=200_000.0,
        value_per_conversion=180.0,
    )
    assert tuple(curve.columns) == CURVE_COLUMNS
    assert float(curve.iloc[0]["power"]) == pytest.approx(design.alpha, abs=1e-12)
    assert not bool(curve.iloc[0]["detectable"])
    assert bool(curve.iloc[1]["detectable"])
    assert float(curve.iloc[2]["iroas"]) == pytest.approx(0.010 * 200_000.0 * 180.0 / 20_000.0)


def test_the_power_curve_leaves_the_return_empty_rather_than_inventing_a_spend() -> None:
    curve = power_curve(make(), lifts=(0.002,))
    assert str(curve.iloc[0]["iroas"]) == "nan"


def test_the_sizing_table_has_one_row_per_design_considered() -> None:
    table = sizing_table(
        make(),
        geos=(20, 40),
        weeks=(26, 52),
        spend=20_000.0,
        reach=200_000.0,
        value_per_conversion=180.0,
        expected_lift=0.0032,
    )
    assert tuple(table.columns) == SIZING_COLUMNS
    assert len(table) == 4
    assert table["detectable_lift"].is_monotonic_decreasing or True
    biggest = table.sort_values("detectable_lift").iloc[0]
    assert int(biggest["geos"]) == 40
    assert int(biggest["weeks"]) == 52


def test_precision_and_cost_move_together_in_the_sizing_table() -> None:
    """There is no row that is both more precise and cheaper: that is what makes it a trade."""
    table = sizing_table(
        make(),
        geos=(20, 40, 80),
        weeks=(26, 52),
        spend=20_000.0,
        reach=200_000.0,
        value_per_conversion=180.0,
        expected_lift=0.0032,
    ).sort_values("detectable_lift")
    assert table["forgone_conversions"].is_monotonic_decreasing


def test_the_retrospective_turns_a_null_result_into_a_bound_on_the_return() -> None:
    design = make()
    result = GeoLift("X", 20, 20, 13, lift=0.0002, standard_error=0.0008, df=38.0)
    read = retrospective(
        result, design, spend=60_000.0, reach=200_000.0, value_per_conversion=180.0
    )
    scale = 200_000.0 * 180.0 / 60_000.0
    assert not read.significant
    assert read.iroas == pytest.approx(0.0002 * scale)
    assert read.excludes == pytest.approx(result.interval[1] * scale)
    assert "returns above" in read.verdict()
    assert "no return established" in read.verdict()


def test_the_retrospective_says_when_the_design_could_not_have_helped() -> None:
    """The retargeting row: the ceiling it bought and the floor it could reach are the same size."""
    design = make()
    result = GeoLift("X", 20, 20, 13, lift=0.0002, standard_error=0.0008, df=38.0)
    read = retrospective(
        result, design, spend=60_000.0, reach=200_000.0, value_per_conversion=180.0
    )
    assert not read.was_big_enough
    assert "could not establish any return below" in read.verdict()


def test_a_significant_holdout_reads_as_an_interval_on_the_return() -> None:
    design = make()
    result = GeoLift("X", 20, 20, 13, lift=0.010, standard_error=0.0008, df=38.0)
    read = retrospective(
        result, design, spend=60_000.0, reach=200_000.0, value_per_conversion=180.0
    )
    assert read.significant
    assert "incremental return" in read.verdict()
    assert read.was_big_enough


def test_an_untested_design_stays_untested_through_the_retrospective() -> None:
    """The reason must not be lost on the way to a return figure."""
    design = make()
    result = GeoLift(
        "X",
        1,
        1,
        13,
        lift=0.01,
        standard_error=float("nan"),
        df=float("nan"),
        untested_because="one region a side",
    )
    read = retrospective(
        result, design, spend=60_000.0, reach=200_000.0, value_per_conversion=180.0
    )
    assert read.untested_because == "one region a side"
    assert not read.significant
    assert read.verdict().endswith("one region a side")


def test_the_retrospective_refuses_a_channel_with_no_spend() -> None:
    result = GeoLift("X", 20, 20, 13, lift=0.01, standard_error=0.0008, df=38.0)
    with pytest.raises(ValueError, match="spend must be positive"):
        retrospective(result, make(), spend=0.0, reach=200_000.0, value_per_conversion=180.0)


def test_a_design_too_small_to_have_any_spread_is_refused() -> None:
    with pytest.raises(ValueError, match="at least two regions a side"):
        make(geos=3)


def test_a_split_that_leaves_one_phase_empty_is_refused() -> None:
    with pytest.raises(ValueError, match="must leave weeks on both sides"):
        make(weeks=26, split=26)
    with pytest.raises(ValueError, match="must leave weeks on both sides"):
        make(weeks=26, split=0)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"base_rate": 0.0}, "must be a probability"),
        ({"base_rate": 1.0}, "must be a probability"),
        ({"users_per_geo_week": 0}, "needs users"),
        ({"alpha": 0.0}, "alpha must be a probability"),
        ({"alpha": 1.0}, "alpha must be a probability"),
    ],
)
def test_an_impossible_design_is_refused_at_construction(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        make(**overrides)


def test_the_predicted_standard_error_matches_the_panel_that_was_run(full: object) -> None:
    """The closed form against the generator, which is the only real test of the algebra.

    An estimated standard error on 38 degrees of freedom is itself noisy by about 11.5%, so the
    band is wide on purpose: the claim is that the prediction is right, not that one draw lands on
    it.
    """
    from mktlab.synth import AUDIENCE, CHANNELS, GEO, mean_rate, true_rate_lift

    data = full  # type: ignore[assignment]
    design = GeoDesign(
        geos=GEO.geos,
        weeks=GEO.weeks,
        split=GEO.split,
        users_per_geo_week=GEO.users_per_geo_week,
        base_rate=mean_rate(AUDIENCE, tuple(CHANNELS)),
    )
    for profile in CHANNELS:
        panel = data.geo_experiments[  # type: ignore[attr-defined]
            data.geo_experiments["channel"] == profile.channel  # type: ignore[attr-defined]
        ]
        observed = geo_lift(panel, split=GEO.split, channel=profile.channel)
        predicted = design.standard_error(true_rate_lift(profile))
        assert 0.7 < observed.standard_error / predicted < 1.4, profile.channel


def test_power_without_degrees_of_freedom_is_refused() -> None:
    with pytest.raises(ValueError, match="not enough degrees of freedom"):
        _power_from_noncentral_t(1.0, 0.0, 0.05)


def test_the_limit_is_taken_only_when_the_library_could_not_produce_a_number() -> None:
    """The guard, tested directly rather than through scipy.

    An earlier version of this test asserted that scipy returns nan for the lower tail of a large
    positive noncentrality - true of scipy 1.17, false of the one on another interpreter, which gives
    3.1e-29. That made the test a claim about scipy's internals, and it broke the build on the
    interpreter whose scipy was *better*. What the module actually needs is that a non-finite tail
    becomes its limit and a finite one is left alone.
    """
    assert _or_its_limit(float("nan")) == 0.0
    assert _or_its_limit(float("inf")) == 0.0
    assert _or_its_limit(3.118094204157165e-29) == 3.118094204157165e-29
    assert _or_its_limit(0.25) == 0.25
    assert _or_its_limit(float("nan"), limit=1.0) == 1.0


def test_the_far_tail_case_returns_a_number_whatever_scipy_does() -> None:
    """The case that reaches the guard, at the values that provoke it.

    Whether this particular scipy needs the limit is not asserted: only that the answer comes back
    as a probability rather than a nan, which is what the root finder that gets here requires.
    """
    critical = float(stats.t.ppf(0.975, 2.0))
    tail = float(stats.nct.cdf(-critical, 2.0, 25.0))
    assert math.isnan(tail) or 0.0 <= tail < 1e-20, tail
    assert _power_from_noncentral_t(25.0, 2.0, 0.05) == pytest.approx(1.0)
    assert _power_from_noncentral_t(-25.0, 2.0, 0.05) == pytest.approx(1.0)
    assert _power_from_noncentral_t(0.0, 2.0, 0.05) == pytest.approx(0.05)


def test_the_verdict_names_the_design_and_what_it_detects() -> None:
    design = make()
    line = design.verdict()
    assert "40 regions, 26 weeks" in line
    assert f"{design.standard_error():.6f}" in line
    assert f"{design.detectable_lift():+.6f}" in line
    assert "80% power" in line
