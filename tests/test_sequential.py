"""Repeated looks, against closed forms, control cases and a simulation.

The recursion is the load-bearing piece, so it is checked three ways: a single look must reduce to
the fixed-sample test exactly, the answer must not move with the quadrature, and the classical
published boundaries must come out of it. The simulation check lives in the slow suite, because a
closed form that only agrees with itself has been verified against nothing.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from mktlab.design import (
    DEFAULT_POWER,
    MAX_LOOKS,
    RULES,
    SequentialPlan,
    crossing_probability,
    exaggeration,
    expected_looks,
    fixed_boundary,
    inflated_alpha,
    information_inflation,
    ncp_for_power,
    nominal_alpha,
    obrien_fleming,
    peeking_table,
    plan,
    pocock,
    power,
)
from mktlab.design.sequential import PEEKING_COLUMNS

ALPHA = 0.05
FIXED = float(stats.norm.ppf(1.0 - ALPHA / 2.0))


def test_one_look_is_the_fixed_sample_test_exactly() -> None:
    """The control case for the whole recursion."""
    assert crossing_probability((FIXED,))[-1] == pytest.approx(ALPHA, abs=1e-12)
    assert inflated_alpha(1) == pytest.approx(ALPHA, abs=1e-12)


def test_one_look_power_is_the_two_sided_normal_power() -> None:
    """Including the far tail, which the textbook formula drops."""
    ncp = 2.8
    expected = float(stats.norm.sf(FIXED - ncp) + stats.norm.cdf(-FIXED - ncp))
    assert power((FIXED,), ncp) == pytest.approx(expected, abs=1e-10)


def test_the_answer_does_not_depend_on_the_quadrature() -> None:
    """If it moved with the node count the published figures would be an artefact of a setting."""
    for looks in (2, 5, 13):
        boundary = fixed_boundary(looks)
        coarse = crossing_probability(boundary, nodes=100)[-1]
        fine = crossing_probability(boundary, nodes=600)[-1]
        assert coarse == pytest.approx(fine, abs=1e-9), looks


def test_the_error_rate_rises_with_every_extra_look() -> None:
    rates = [inflated_alpha(looks) for looks in range(1, 15)]
    assert rates == sorted(rates)
    assert rates[0] == pytest.approx(ALPHA, abs=1e-12)
    assert rates[-1] > 0.21


def test_the_error_rate_is_steepest_at_the_first_extra_look() -> None:
    """The counter-intuitive shape: twice is most of the damage, not daily monitoring."""
    steps = [inflated_alpha(looks + 1) - inflated_alpha(looks) for looks in range(1, 10)]
    assert steps == sorted(steps, reverse=True)


def test_drift_of_zero_is_the_size_and_positive_drift_is_the_power() -> None:
    boundary = pocock(5)
    assert crossing_probability(boundary, drift=0.0)[-1] == pytest.approx(ALPHA, abs=1e-9)
    assert power(boundary, 3.0) > ALPHA


def test_the_cumulative_probabilities_only_ever_rise() -> None:
    cumulative = crossing_probability(obrien_fleming(8), drift=0.5)
    assert list(cumulative) == sorted(cumulative)
    assert all(0.0 <= value <= 1.0 for value in cumulative)


def test_pocock_holds_the_error_rate_it_was_built_for() -> None:
    """The round trip that makes the boundary meaningful."""
    for looks in (2, 3, 5, 13, 20):
        boundary = pocock(looks, ALPHA)
        assert len(set(boundary)) == 1, "Pocock's boundary is constant"
        assert crossing_probability(boundary)[-1] == pytest.approx(ALPHA, abs=1e-9), looks


def test_obrien_fleming_holds_the_error_rate_it_was_built_for() -> None:
    for looks in (2, 3, 5, 13, 20):
        boundary = obrien_fleming(looks, ALPHA)
        assert crossing_probability(boundary)[-1] == pytest.approx(ALPHA, abs=1e-9), looks


def test_obrien_fleming_declines_as_the_root_of_the_information() -> None:
    looks = 13
    boundary = obrien_fleming(looks)
    for index in range(1, looks):
        ratio = boundary[index] / boundary[0]
        assert ratio == pytest.approx(np.sqrt(1.0 / (index + 1)), rel=1e-12)
    assert boundary[0] > boundary[-1]


def test_obrien_fleming_ends_near_the_fixed_sample_value_and_pocock_does_not() -> None:
    """Which is the whole difference between the two trades."""
    ends = obrien_fleming(13)[-1]
    constant = pocock(13)[0]
    assert FIXED < ends < constant
    assert ends == pytest.approx(2.1023, abs=5e-5)


def test_both_boundaries_are_above_the_fixed_sample_value_everywhere() -> None:
    """A valid boundary can never be easier to cross than the single-look one."""
    for boundary in (pocock(13), obrien_fleming(13)):
        assert all(limit >= FIXED for limit in boundary)


def test_a_single_look_boundary_is_the_fixed_value_under_either_rule() -> None:
    assert pocock(1) == fixed_boundary(1)
    assert obrien_fleming(1) == fixed_boundary(1)


def test_a_tighter_alpha_gives_a_higher_boundary() -> None:
    assert pocock(5, 0.01)[0] > pocock(5, 0.05)[0]
    assert obrien_fleming(5, 0.01)[0] > obrien_fleming(5, 0.05)[0]


def test_nominal_alpha_is_the_two_sided_tail_of_each_limit() -> None:
    boundary = pocock(5)
    assert nominal_alpha(boundary)[0] == pytest.approx(2.0 * stats.norm.sf(boundary[0]))
    assert nominal_alpha(fixed_boundary(1))[0] == pytest.approx(ALPHA)


def test_reading_once_needs_no_extra_information() -> None:
    """The control case: the reference and the thing compared to it are computed the same way."""
    assert information_inflation(fixed_boundary(1), DEFAULT_POWER, ALPHA) == 1.0


def test_the_textbook_noncentrality_is_slightly_too_large() -> None:
    """Worth knowing, because it is why the control case above had to be made self-consistent.

    ``z + z_power`` ignores the probability of rejecting in the tail opposite the true effect. At
    80% power and a 5% level that is about one in a million, so the formula asks for a shade more
    effect than 80% power actually needs.
    """
    textbook = float(stats.norm.ppf(0.975) + stats.norm.ppf(DEFAULT_POWER))
    solved = ncp_for_power(fixed_boundary(1), DEFAULT_POWER)
    assert solved < textbook
    assert textbook - solved == pytest.approx(3.4e-06, rel=0.2)
    assert power(fixed_boundary(1), textbook) > DEFAULT_POWER


def test_stopping_early_costs_information_and_obrien_fleming_costs_least() -> None:
    pocock_cost = information_inflation(pocock(13), DEFAULT_POWER, ALPHA)
    obf_cost = information_inflation(obrien_fleming(13), DEFAULT_POWER, ALPHA)
    assert 1.0 < obf_cost < pocock_cost
    assert obf_cost == pytest.approx(1.0432, abs=5e-4)
    assert pocock_cost == pytest.approx(1.3247, abs=5e-4)


def test_the_information_cost_rises_with_the_number_of_looks() -> None:
    assert information_inflation(pocock(3)) < information_inflation(pocock(13))


def test_the_power_target_must_be_above_the_boundary_own_size() -> None:
    with pytest.raises(ValueError, match="above this boundary's own size"):
        ncp_for_power(pocock(5), 0.04)
    with pytest.raises(ValueError, match="above this boundary's own size"):
        ncp_for_power(pocock(5), 1.0)


def test_the_effect_needed_for_a_target_is_the_effect_that_achieves_it() -> None:
    for target in (0.50, 0.80, 0.95):
        boundary = pocock(13)
        assert power(boundary, ncp_for_power(boundary, target)) == pytest.approx(target, abs=1e-6)


def test_expected_looks_is_one_for_a_single_look_and_at_most_the_number_of_looks() -> None:
    assert expected_looks(fixed_boundary(1), 2.8) == pytest.approx(1.0)
    for boundary in (pocock(13), obrien_fleming(13)):
        assert 1.0 < expected_looks(boundary, 3.0) <= 13.0


def test_a_boundary_that_cannot_be_crossed_early_runs_to_the_end() -> None:
    """The control case for the stopping-time calculation."""
    boundary = (50.0, 50.0, 50.0, 50.0, 3.0)
    assert expected_looks(boundary, 3.0) == pytest.approx(5.0, abs=1e-6)


def test_a_bigger_effect_stops_the_test_sooner() -> None:
    boundary = pocock(13)
    assert expected_looks(boundary, 6.0) < expected_looks(boundary, 3.0)


def test_pocock_stops_sooner_than_obrien_fleming_at_its_own_power() -> None:
    """The trade stated as an assertion: Pocock buys time, O'Brien-Fleming buys size."""
    pocock_boundary = pocock(13)
    obf_boundary = obrien_fleming(13)
    pocock_looks = expected_looks(pocock_boundary, ncp_for_power(pocock_boundary))
    obf_looks = expected_looks(obf_boundary, ncp_for_power(obf_boundary))
    assert pocock_looks < obf_looks


def test_an_empty_or_over_long_boundary_is_refused() -> None:
    with pytest.raises(ValueError, match="read at least once"):
        crossing_probability(())
    with pytest.raises(ValueError, match="continuous monitoring"):
        crossing_probability((2.0,) * (MAX_LOOKS + 1))
    with pytest.raises(ValueError, match="continuous monitoring"):
        pocock(MAX_LOOKS + 1)


def test_a_non_positive_critical_value_is_refused() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        crossing_probability((2.0, 0.0, 2.0))


def test_the_plan_knows_whether_it_holds_its_own_error_rate() -> None:
    assert plan("read-once", 13).valid
    assert plan("pocock", 13).valid
    assert plan("obrien-fleming", 13).valid
    assert not plan("naive", 13).valid


def test_the_naive_plan_is_one_look_long_when_there_is_only_one_look() -> None:
    """Reading a test once is not peeking, whatever the rule is called."""
    assert plan("naive", 1).valid
    assert plan("naive", 1).true_alpha == pytest.approx(ALPHA, abs=1e-12)


def test_the_read_once_plan_ignores_the_number_of_looks() -> None:
    assert plan("read-once", 13).looks == 1


def test_an_unknown_rule_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown rule"):
        plan("bayesian", 13)


def test_the_verdict_of_an_invalid_plan_names_the_real_error_rate() -> None:
    line = plan("naive", 13).verdict()
    assert "0.2138" in line
    assert "not 0.0500" in line


def test_the_verdict_of_a_valid_plan_names_its_price() -> None:
    line = plan("obrien-fleming", 13).verdict()
    assert "holding alpha at 0.0500" in line
    assert "+4.3%" in line
    assert "9.79 looks" in line


def test_the_peeking_table_has_one_row_per_rule_and_flags_the_invalid_one() -> None:
    table = peeking_table(13)
    assert tuple(table.columns) == PEEKING_COLUMNS
    assert list(table["rule"]) == list(RULES)
    assert list(table["valid"]) == [True, False, True, True]
    naive = table[table["rule"] == "naive"].iloc[0]
    assert str(naive["information_inflation"]) == "nan"
    assert float(naive["true_alpha"]) == pytest.approx(0.213814, abs=5e-6)


def test_a_custom_plan_can_be_built_directly() -> None:
    built = SequentialPlan(rule="mine", boundary=(3.0, 2.5, 2.2), alpha=ALPHA)
    assert built.looks == 3
    assert built.valid == (built.true_alpha <= ALPHA * (1 + 1e-6))
    assert len(built.nominal_alphas) == 3


def test_the_exaggeration_of_a_single_look_at_high_power_goes_to_one() -> None:
    """The control case: with essentially no chance of missing, nothing is selected on."""
    measured = exaggeration(fixed_boundary(1), ncp=12.0, draws=50_000)
    assert measured["power"] == pytest.approx(1.0)
    assert measured["ratio"] == pytest.approx(1.0, abs=0.01)
    assert measured["expected_looks"] == 1.0
    assert measured["same_sign"] == 1.0


def test_a_single_look_at_modest_power_already_exaggerates() -> None:
    """Publication is conditional on significance, which selects the favourable draws."""
    measured = exaggeration(fixed_boundary(1), ncp=2.8, draws=100_000)
    assert 1.10 < measured["ratio"] < 1.15


def test_peeking_exaggerates_more_than_reading_once_at_equal_power() -> None:
    naive = plan("naive", 13).boundary
    once = fixed_boundary(1)
    peeked = exaggeration(naive, ncp=ncp_for_power(naive, DEFAULT_POWER), draws=100_000)
    read_once = exaggeration(once, ncp=ncp_for_power(once, DEFAULT_POWER), draws=100_000)
    assert peeked["power"] == pytest.approx(read_once["power"], abs=0.01)
    assert peeked["ratio"] > read_once["ratio"]


def test_a_valid_boundary_reduces_the_exaggeration_without_removing_it() -> None:
    """The point of Result 4: fixing the error rate does not fix the estimate."""
    obf = obrien_fleming(13)
    naive = plan("naive", 13).boundary
    corrected = exaggeration(obf, ncp=ncp_for_power(obf, DEFAULT_POWER), draws=100_000)
    peeked = exaggeration(naive, ncp=ncp_for_power(naive, DEFAULT_POWER), draws=100_000)
    assert 1.0 < corrected["ratio"] < peeked["ratio"]


def test_the_exaggeration_is_worse_on_an_underpowered_test() -> None:
    boundary = plan("naive", 13).boundary
    weak = exaggeration(boundary, ncp=ncp_for_power(fixed_boundary(1), 0.30), draws=100_000)
    strong = exaggeration(boundary, ncp=ncp_for_power(fixed_boundary(1), 0.80), draws=100_000)
    assert weak["ratio"] > strong["ratio"]
    assert weak["same_sign"] < strong["same_sign"]


def test_the_exaggeration_is_reproducible_and_seed_dependent() -> None:
    boundary = plan("naive", 13).boundary
    first = exaggeration(boundary, ncp=2.5, draws=20_000, seed=3)
    again = exaggeration(boundary, ncp=2.5, draws=20_000, seed=3)
    other = exaggeration(boundary, ncp=2.5, draws=20_000, seed=4)
    assert first == again
    assert first["ratio"] != other["ratio"]


def test_the_exaggeration_ratio_needs_a_real_effect_to_be_relative_to() -> None:
    with pytest.raises(ValueError, match="relative to a real effect"):
        exaggeration(fixed_boundary(1), ncp=0.0)


def test_the_recursion_is_cached_and_the_cache_is_keyed_on_every_argument() -> None:
    """The cache is safe only because the results are immutable, so that is asserted.

    A cached function handing out a mutable object lets one caller's change reach the next one. These
    return tuples, which is why the same object can be handed out twice, and the node count and the
    drift are part of the key rather than ignored.
    """
    boundary = fixed_boundary(4)
    first = crossing_probability(boundary)
    assert crossing_probability(boundary) is first
    assert isinstance(first, tuple)
    assert crossing_probability(boundary, nodes=100) is not first
    assert crossing_probability(boundary, drift=0.5) is not first
    assert pocock(4) is pocock(4)
    assert obrien_fleming(4) is obrien_fleming(4)
    assert pocock(4, 0.01) is not pocock(4, 0.05)
