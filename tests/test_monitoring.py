"""Alpha spending, futility, and the plan they make, against controls.

Two controls carry this file. A single look must reduce to the fixed-sample one-sided test - boundary
1.96, error rate exactly the alpha asked for - and a plan that cannot give up must need exactly one
times the information. Everything else is a ratio resting on those.
"""

from __future__ import annotations

import math

import pytest
from scipy import optimize, stats

from mktlab.design import (
    DEFAULT_POWER,
    SPENDING,
    UNREACHABLE,
    MonitoringPlan,
    alpha_spent,
    beta_spent,
    crossing_probability,
    equal_information,
    expected_looks,
    fixed_boundary,
    futility_boundary,
    futility_probability,
    inflated_alpha,
    monitoring_plan,
    obrien_fleming,
    pocock,
    schedule,
    spending_boundary,
)
from mktlab.design.sequential import SCHEDULE_COLUMNS

ONE_SIDED = 0.025
LOOKS = 13


def fractions() -> tuple[float, ...]:
    return equal_information(LOOKS)


def never(looks: int = LOOKS) -> tuple[float, ...]:
    return (-UNREACHABLE,) * looks


# --- the recursion, generalised ------------------------------------------------------------------


def test_equal_information_is_evenly_spaced_and_ends_at_one() -> None:
    assert equal_information(4) == (0.25, 0.5, 0.75, 1.0)
    assert equal_information(1) == (1.0,)


def test_explicit_even_fractions_are_the_same_as_the_default() -> None:
    """The generalisation must not move a single one of wave 3's published figures."""
    boundary = fixed_boundary(LOOKS)
    assert crossing_probability(boundary) == crossing_probability(
        boundary, fractions=equal_information(LOOKS)
    )


def test_wave_three_figures_are_untouched_by_the_generalisation() -> None:
    """The refactor must not have changed the arithmetic, to twelve significant figures.

    Not bit-identical, which is what this asserted first and what broke the build on the other
    interpreter: ``inflated_alpha(13)`` came back 4.9e-15 apart there, in the fourteenth significant
    digit, because a different libm rounds a transcendental differently. Bit-identity across builds
    is not a property floating point offers, so asking for it tests the platform rather than the
    change. Agreement to 1e-12 is five orders of magnitude tighter than any figure this repository
    publishes and it establishes what the test is for.
    """
    assert inflated_alpha(13) == pytest.approx(0.2138142746188343, rel=1e-12)
    assert pocock(13)[0] == pytest.approx(2.6019105595011642, rel=1e-12)
    assert obrien_fleming(13)[0] == pytest.approx(7.579939928715328, rel=1e-12)


def test_fractions_that_are_not_a_schedule_are_refused() -> None:
    boundary = fixed_boundary(3)
    with pytest.raises(ValueError, match="one information fraction per look"):
        crossing_probability(boundary, fractions=(0.5, 1.0))
    with pytest.raises(ValueError, match="must increase"):
        crossing_probability(boundary, fractions=(0.5, 0.5, 1.0))
    with pytest.raises(ValueError, match="must increase"):
        crossing_probability(boundary, fractions=(0.5, 0.9, 0.8))
    with pytest.raises(ValueError, match="first information fraction must be positive"):
        crossing_probability(boundary, fractions=(0.0, 0.5, 1.0))
    with pytest.raises(ValueError, match="last look has all the information"):
        crossing_probability(boundary, fractions=(0.3, 0.6, 0.9))


def test_a_futility_bound_of_the_wrong_length_is_refused() -> None:
    with pytest.raises(ValueError, match="one futility bound per look"):
        crossing_probability(fixed_boundary(3), futility=(-1.0, -1.0))


def test_a_futility_bound_above_the_efficacy_bound_is_refused() -> None:
    """Except at the last look, where meeting it is what ending the test means."""
    with pytest.raises(ValueError, match="no continuation region"):
        crossing_probability((2.0, 2.0, 2.0), futility=(3.0, -1.0, 2.0))
    with pytest.raises(ValueError, match="no continuation region"):
        crossing_probability((2.0, 2.0, 2.0), futility=(2.0, -1.0, 2.0))
    # The same value at the final look is legitimate and resolves to everything having stopped.
    rejected = crossing_probability((2.0, 2.0, 2.0), futility=(-3.0, -1.0, 2.0))
    abandoned = futility_probability((2.0, 2.0, 2.0), (-3.0, -1.0, 2.0))
    assert rejected[-1] + abandoned[-1] == pytest.approx(1.0)


def test_a_far_away_futility_bound_leaves_a_one_sided_test() -> None:
    """The control that links the two worlds: one tail instead of two, so half the error rate."""
    for looks in (1, 5, 13):
        boundary = fixed_boundary(looks)
        two_sided = crossing_probability(boundary)[-1]
        one_sided = crossing_probability(boundary, futility=never(looks))[-1]
        assert one_sided == pytest.approx(two_sided / 2.0, rel=0.005), looks
    assert crossing_probability(fixed_boundary(1), futility=(-UNREACHABLE,))[-1] == pytest.approx(
        0.025, abs=1e-12
    )


def test_a_futility_bound_lowers_the_error_rate() -> None:
    """Paths that would have crossed later are removed, so the test becomes conservative."""
    boundary = fixed_boundary(5)
    assert (
        crossing_probability(boundary, futility=(-0.5,) * 5)[-1]
        < crossing_probability(boundary, futility=never(5))[-1]
    )


def test_unequal_looks_behave_like_the_equal_ones_they_reduce_to() -> None:
    """Splitting the information evenly in a different way must give the same answer."""
    boundary = fixed_boundary(2)
    assert crossing_probability(boundary, fractions=(0.5, 1.0))[-1] == pytest.approx(
        crossing_probability(boundary)[-1]
    )


def test_two_reads_too_close_together_are_refused_rather_than_answered() -> None:
    """A measured limit of the method, turned into a named refusal.

    The convolution kernel between two looks has standard deviation equal to the root of the
    information they are apart, so as that gap shrinks the kernel narrows towards a spike that
    quadrature over a wide region cannot represent. Below the floor the recursion does not merely
    lose accuracy: at a gap of 1e-05 it returned -1.17, which is not a probability. This test exists
    because a control case - a second look adding nothing should change nothing - produced that
    number instead of an answer.
    """
    boundary = fixed_boundary(2)
    with pytest.raises(ValueError, match="two reads that close together are one read"):
        crossing_probability(boundary, fractions=(1.0 - 1e-9, 1.0))
    with pytest.raises(ValueError, match="below the 1e-03 this recursion can resolve"):
        crossing_probability(boundary, fractions=(1.0 - 5e-4, 1.0))


def test_a_closer_second_look_costs_less_error_all_the_way_to_the_floor() -> None:
    """Inside the resolvable range the behaviour is the right one, and monotone.

    A second look taken later adds less new information, so it adds less error. The sequence has to
    fall towards the single-look value as the gap closes, and it does - which is what says the
    refusal above is a limit of the quadrature rather than of the mathematics.
    """
    boundary = fixed_boundary(2)
    one_look = crossing_probability((boundary[0],), fractions=(1.0,))[-1]
    extra = [
        crossing_probability(boundary, fractions=(1.0 - gap, 1.0))[-1] - one_look
        for gap in (0.5, 0.1, 0.01, 0.002, 0.001)
    ]
    assert extra == sorted(extra, reverse=True)
    assert all(value > 0.0 for value in extra)
    assert extra[-1] < 2e-3


# --- the spending functions ----------------------------------------------------------------------


@pytest.mark.parametrize("family", SPENDING)
def test_a_spending_function_spends_nothing_at_the_start_and_everything_at_the_end(
    family: str,
) -> None:
    assert alpha_spent(1.0, ONE_SIDED, family) == pytest.approx(ONE_SIDED)
    assert alpha_spent(1e-6, ONE_SIDED, family) < ONE_SIDED / 100.0


@pytest.mark.parametrize("family", SPENDING)
def test_a_spending_function_only_ever_rises(family: str) -> None:
    spent = [alpha_spent(share, ONE_SIDED, family) for share in equal_information(20)]
    assert spent == sorted(spent)


def test_the_families_are_ordered_by_how_early_they_spend() -> None:
    """The ordering that makes the family a dial rather than a name."""
    early = alpha_spent(0.3, ONE_SIDED, "pocock")
    middling = alpha_spent(0.3, ONE_SIDED, "power", rho=1.0)
    late = alpha_spent(0.3, ONE_SIDED, "obrien-fleming")
    assert late < middling < early


def test_the_power_family_is_the_declared_curve() -> None:
    assert alpha_spent(0.5, 0.025, "power", rho=2.0) == pytest.approx(0.025 * 0.25)
    assert alpha_spent(0.5, 0.025, "power", rho=1.0) == pytest.approx(0.0125)


def test_an_impossible_spending_request_is_refused() -> None:
    with pytest.raises(ValueError, match=r"lies in \(0, 1\]"):
        alpha_spent(0.0, ONE_SIDED)
    with pytest.raises(ValueError, match=r"lies in \(0, 1\]"):
        alpha_spent(1.5, ONE_SIDED)
    with pytest.raises(ValueError, match="positive exponent"):
        alpha_spent(0.5, ONE_SIDED, "power", rho=0.0)
    with pytest.raises(ValueError, match="unknown spending function"):
        alpha_spent(0.5, ONE_SIDED, "bayesian")


def test_beta_spending_is_the_same_shape_pointed_at_the_other_error() -> None:
    assert beta_spent(0.5, 0.2, "power", rho=1.0) == pytest.approx(0.1)
    assert beta_spent(1.0, 0.2) == pytest.approx(0.2)


# --- the boundaries the spending functions imply -------------------------------------------------


@pytest.mark.parametrize("family", SPENDING)
def test_a_spending_boundary_spends_exactly_the_error_rate_it_was_given(family: str) -> None:
    """The round trip. Anything else and the function is not a spending function."""
    for shares in (equal_information(5), (4 / 13, 8 / 13, 1.0), (0.5, 0.75, 0.9, 1.0)):
        boundary = spending_boundary(shares, ONE_SIDED, family)
        spent = crossing_probability(
            boundary, fractions=shares, futility=(-UNREACHABLE,) * len(shares)
        )[-1]
        assert spent == pytest.approx(ONE_SIDED, abs=1e-9), (family, shares)


@pytest.mark.parametrize("family", SPENDING)
def test_one_look_is_the_fixed_sample_one_sided_test(family: str) -> None:
    """The control case for the whole construction: reading once is monitoring, degenerately."""
    boundary = spending_boundary((1.0,), ONE_SIDED, family)
    assert boundary == (pytest.approx(float(stats.norm.isf(ONE_SIDED))),)
    assert boundary[0] == pytest.approx(1.959964, abs=5e-6)


def test_the_boundary_falls_as_information_accumulates_under_a_conservative_schedule() -> None:
    boundary = spending_boundary(fractions(), ONE_SIDED, "obrien-fleming")
    assert list(boundary) == sorted(boundary, reverse=True)
    assert boundary[0] > 7.0
    assert boundary[-1] < 2.2


def test_the_spending_boundary_approaches_the_exact_one_it_approximates() -> None:
    """The gap closes monotonically, which is the claim the monitoring README publishes."""
    approximate = spending_boundary(fractions(), ONE_SIDED, "obrien-fleming")
    exact = obrien_fleming(LOOKS, 2.0 * ONE_SIDED)
    ratios = [a / b for a, b in zip(approximate, exact, strict=True)]
    assert ratios == sorted(ratios, reverse=True)
    assert ratios[0] == pytest.approx(1.0550, abs=5e-4)
    assert ratios[-1] == pytest.approx(0.9980, abs=5e-4)


def test_a_tighter_error_rate_raises_the_whole_boundary() -> None:
    shares = equal_information(5)
    tight = spending_boundary(shares, 0.005)
    loose = spending_boundary(shares, 0.05)
    assert all(a > b for a, b in zip(tight, loose, strict=True))


# --- futility ------------------------------------------------------------------------------------


def test_the_futility_bound_rises_and_meets_the_efficacy_bound_at_the_end() -> None:
    efficacy = spending_boundary(fractions(), ONE_SIDED)
    bound = futility_boundary(efficacy, 2.8591, fractions())
    assert list(bound) == sorted(bound)
    assert bound[0] < -3.0, "nothing observable in week one should end a thirteen-week test"
    assert bound[-1] == efficacy[-1]


def test_the_futility_bound_needs_a_real_alternative() -> None:
    efficacy = spending_boundary(fractions(), ONE_SIDED)
    with pytest.raises(ValueError, match="defined against a real alternative"):
        futility_boundary(efficacy, 0.0, fractions())


def test_a_futility_bound_stops_most_dead_tests_and_some_live_ones() -> None:
    efficacy = spending_boundary(fractions(), ONE_SIDED)
    bound = futility_boundary(efficacy, 2.8591, fractions())
    under_null = futility_probability(efficacy, bound, drift=0.0, fractions=fractions())[-1]
    under_alternative = futility_probability(
        efficacy, bound, drift=2.8591 / math.sqrt(LOOKS), fractions=fractions()
    )[-1]
    assert under_null > 0.95
    assert 0.1 < under_alternative < 0.4
    assert under_alternative < under_null


def test_a_more_aggressive_futility_schedule_abandons_more_tests() -> None:
    efficacy = spending_boundary(fractions(), ONE_SIDED)
    patient = futility_boundary(efficacy, 2.8591, fractions(), family="obrien-fleming")
    hasty = futility_boundary(efficacy, 2.8591, fractions(), family="pocock")
    drift = 2.8591 / math.sqrt(LOOKS)
    assert (
        futility_probability(efficacy, hasty, drift=drift, fractions=fractions())[-1]
        > futility_probability(efficacy, patient, drift=drift, fractions=fractions())[-1]
    )


def test_expected_looks_falls_when_the_test_may_be_abandoned() -> None:
    efficacy = spending_boundary(fractions(), ONE_SIDED)
    bound = futility_boundary(efficacy, 2.8591, fractions())
    open_ended = expected_looks(efficacy, 1e-9, futility=never(), fractions=fractions())
    with_bound = expected_looks(efficacy, 1e-9, futility=bound, fractions=fractions())
    assert with_bound < open_ended / 1.5
    assert open_ended <= LOOKS


# --- the plan ------------------------------------------------------------------------------------


def test_a_plan_that_cannot_give_up_needs_exactly_the_information_it_has() -> None:
    """The second control case, and the defect it was written for.

    A plan with no futility bound is one-sided with an unreachable floor, not a two-sided test. When
    it stored "nothing" instead, it reported an error rate of 0.05 for a boundary solved to spend
    0.025, and this multiplier came out wrong with it.
    """
    built = monitoring_plan(fractions(), 2.8591, alpha=ONE_SIDED, beta=None)
    assert not built.can_abandon
    assert built.true_alpha == pytest.approx(ONE_SIDED, abs=1e-9)
    assert built.abandoned_under_null == pytest.approx(0.0, abs=1e-12)
    assert built.abandoned_under_alternative == pytest.approx(0.0, abs=1e-12)
    assert built.information_to_restore_power(built.power) == pytest.approx(1.0, abs=1e-6)


def test_a_plan_with_futility_trades_power_for_calendar() -> None:
    powered_for = 2.8591
    open_ended = monitoring_plan(fractions(), powered_for, alpha=ONE_SIDED, beta=None)
    with_futility = monitoring_plan(fractions(), powered_for, alpha=ONE_SIDED)
    assert with_futility.can_abandon
    assert with_futility.true_alpha < open_ended.true_alpha
    assert with_futility.power < open_ended.power
    assert with_futility.power_without_futility == pytest.approx(open_ended.power)
    assert with_futility.information_to_restore_power() > 1.0
    assert with_futility.expected_looks_under(0.0) < open_ended.expected_looks_under(0.0) / 1.5


def test_the_plan_reports_its_own_looks_and_drift() -> None:
    built = monitoring_plan(fractions(), 2.8591, alpha=ONE_SIDED)
    assert built.looks == LOOKS
    assert built.drift == pytest.approx(2.8591 / math.sqrt(LOOKS))


def test_an_unreachable_power_target_is_refused() -> None:
    built = monitoring_plan(fractions(), 2.8591, alpha=ONE_SIDED)
    with pytest.raises(ValueError, match="above this plan's own size"):
        built.information_to_restore_power(0.01)
    with pytest.raises(ValueError, match="above this plan's own size"):
        built.information_to_restore_power(1.0)


def test_the_verdict_says_which_kind_of_plan_it_is() -> None:
    open_ended = monitoring_plan(fractions(), 2.8591, alpha=ONE_SIDED, beta=None)
    with_futility = monitoring_plan(fractions(), 2.8591, alpha=ONE_SIDED)
    assert "with futility" not in open_ended.verdict()
    assert "alpha 0.0250" in open_ended.verdict()
    assert "with futility" in with_futility.verdict()
    assert "channel doing nothing" in with_futility.verdict()


def test_a_plan_can_be_built_by_hand() -> None:
    built = MonitoringPlan(
        fractions=(0.5, 1.0),
        efficacy=(2.8, 2.0),
        futility=(-1.0, 2.0),
        alpha=ONE_SIDED,
        ncp=2.8,
    )
    assert built.looks == 2
    assert built.can_abandon
    assert 0.0 < built.true_alpha < 0.05
    assert 0.0 < built.power < 1.0


def test_the_schedule_is_the_table_the_team_is_handed() -> None:
    built = monitoring_plan(fractions(), 2.8591, alpha=ONE_SIDED)
    table = schedule(built)
    assert tuple(table.columns) == SCHEDULE_COLUMNS
    assert len(table) == LOOKS
    assert list(table["look"]) == list(range(1, LOOKS + 1))
    assert float(table["alpha_spent"].iloc[-1]) == pytest.approx(ONE_SIDED)
    assert float(table["alpha_this_look"].sum()) == pytest.approx(ONE_SIDED)
    assert table["alpha_this_look"].min() >= 0.0
    assert float(table["futility"].iloc[-1]) == pytest.approx(float(table["efficacy"].iloc[-1]))
    assert float(table["beta_spent"].iloc[-1]) == pytest.approx(1.0 - DEFAULT_POWER)


def test_a_plan_without_futility_has_no_futility_column_to_read() -> None:
    table = schedule(monitoring_plan(fractions(), 2.8591, alpha=ONE_SIDED, beta=None))
    assert str(table["futility"].iloc[0]) == "nan"
    assert str(table["beta_spent"].iloc[0]) == "nan"


def test_the_plan_can_be_built_on_an_unequal_schedule() -> None:
    """The reason the whole thing exists: the looks were not agreed in advance."""
    shares = (0.3, 0.45, 0.8, 1.0)
    built = monitoring_plan(shares, 2.8591, alpha=ONE_SIDED)
    assert built.looks == 4
    assert built.true_alpha < ONE_SIDED
    assert built.power_without_futility == pytest.approx(
        crossing_probability(
            built.efficacy, drift=built.drift, fractions=shares, futility=never(4)
        )[-1]
    )


def test_more_looks_cost_power_for_the_same_error_rate() -> None:
    """Monitoring is not free even when it is done correctly.

    Three looks against thirteen rather than against twenty-six: solving a boundary runs a root
    finder per look and every evaluation inside it runs the whole recursion, so the cost grows with
    the square of the looks. The claim is no truer at twenty-six, and this suite gates every push.
    """
    ncp = 2.8591
    few = monitoring_plan(equal_information(3), ncp, alpha=ONE_SIDED, beta=None)
    many = monitoring_plan(equal_information(LOOKS), ncp, alpha=ONE_SIDED, beta=None)
    assert many.power < few.power


def test_the_solver_agrees_with_the_power_it_reports() -> None:
    """A round trip through the two directions of the same question."""
    built = monitoring_plan(fractions(), 2.8591, alpha=ONE_SIDED)
    multiplier = built.information_to_restore_power(0.80)
    restored = MonitoringPlan(
        fractions=built.fractions,
        efficacy=built.efficacy,
        futility=built.futility,
        alpha=built.alpha,
        ncp=built.ncp * math.sqrt(multiplier),
    )
    assert restored.power == pytest.approx(0.80, abs=1e-6)


def test_the_design_effect_is_recovered_from_the_boundary_it_was_solved_against() -> None:
    """The alternative quoted in the monitoring README, re-derived rather than copied."""
    efficacy = spending_boundary(fractions(), ONE_SIDED)
    solved = float(
        optimize.brentq(
            lambda ncp: (
                crossing_probability(
                    efficacy, drift=ncp / math.sqrt(LOOKS), fractions=fractions(), futility=never()
                )[-1]
                - DEFAULT_POWER
            ),
            0.5,
            20.0,
            xtol=1e-12,
        )
    )
    assert solved == pytest.approx(2.8591, abs=5e-5)
