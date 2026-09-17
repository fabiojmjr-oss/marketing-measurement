"""Attribution models against allocations worked out on paper.

The hand journeys in ``conftest`` are small enough that every model's answer is an exact fraction,
which is the only way to tell a model that is wrong from a model that merely disagrees.
"""

from __future__ import annotations

from collections import Counter

import pandas as pd
import pytest

from mktlab.attribution import (
    MODELS,
    coverage_value,
    credit,
    credit_table,
    journey_sets,
    shapley,
    unattributable,
)
from mktlab.attribution.credit import CREDIT_COLUMNS, MAX_CHANNELS

EXPECTED = {
    "last-click": {"A": 1.0, "C": 1.0},
    "first-click": {"A": 2.0},
    "linear": {"A": 4.0 / 3.0, "B": 1.0 / 3.0, "C": 1.0 / 3.0},
    "position-based": {"A": 1.4, "B": 0.2, "C": 0.4},
    "time-decay": {"A": 1.0 + 1.0 / 7.0, "B": 2.0 / 7.0, "C": 4.0 / 7.0},
    "shapley": {"A": 4.0 / 3.0, "B": 1.0 / 3.0, "C": 1.0 / 3.0},
}


@pytest.mark.parametrize("model", MODELS)
def test_each_model_allocates_what_it_says_on_paper(
    model: str, hand_journeys: pd.DataFrame
) -> None:
    allocated = credit(hand_journeys, model).set_index("channel")["credited"]
    for channel, expected in EXPECTED[model].items():
        assert float(allocated[channel]) == pytest.approx(expected), channel


@pytest.mark.parametrize("model", MODELS)
def test_every_model_allocates_exactly_the_conversions_it_can_see(
    model: str, hand_journeys: pd.DataFrame
) -> None:
    """Two conversions in, two conversions out. A model that does not conserve them is broken."""
    allocated = credit(hand_journeys, model)
    assert float(allocated["credited"].sum()) == pytest.approx(2.0)
    assert float(allocated["share"].sum()) == pytest.approx(1.0)
    assert tuple(allocated.columns) == CREDIT_COLUMNS


def test_a_journey_that_did_not_convert_receives_nothing(hand_journeys: pd.DataFrame) -> None:
    """User 3 saw B and C. Under last-click, C gets credit only from user 1."""
    allocated = credit(hand_journeys, "last-click").set_index("channel")["credited"]
    assert float(allocated["C"]) == pytest.approx(1.0)


def test_an_unknown_model_is_refused(hand_journeys: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="unknown model"):
        credit(hand_journeys, "data-driven")


def test_nothing_to_allocate_is_refused_rather_than_returned_as_zeros() -> None:
    frame = pd.DataFrame(
        [{"user": 1, "position": 1, "channel": "A", "converted": False}],
    )
    with pytest.raises(ValueError, match="no converting journeys"):
        credit(frame, "linear")


def test_journey_sets_ignores_order_and_counts_conversions(hand_journeys: pd.DataFrame) -> None:
    sets = journey_sets(hand_journeys)
    assert sets == Counter({frozenset({"A", "B", "C"}): 1, frozenset({"A"}): 1})


def test_coverage_value_counts_only_journeys_wholly_inside_the_coalition(
    hand_journeys: pd.DataFrame,
) -> None:
    sets = journey_sets(hand_journeys)
    assert coverage_value(sets, set()) == 0.0
    assert coverage_value(sets, {"A"}) == 1.0
    assert coverage_value(sets, {"B", "C"}) == 0.0
    assert coverage_value(sets, {"A", "B"}) == 1.0
    assert coverage_value(sets, {"A", "B", "C"}) == 2.0


def test_the_shapley_value_of_the_coverage_game_is_linear_attribution(
    hand_journeys: pd.DataFrame,
) -> None:
    """The identity the module exists to demonstrate, on journeys that can be checked by hand.

    Each journey's value appears only when all of its channels are present, so its Shapley value
    splits equally among them: 1/3 each for the three-channel journey and 1 for the one-channel
    journey.
    """
    sets = journey_sets(hand_journeys)
    allocation = shapley(sets, ("A", "B", "C"))
    assert allocation["A"] == pytest.approx(4.0 / 3.0)
    assert allocation["B"] == pytest.approx(1.0 / 3.0)
    assert allocation["C"] == pytest.approx(1.0 / 3.0)


def test_the_shapley_value_is_efficient(hand_journeys: pd.DataFrame) -> None:
    """The axiom worth checking: the allocation sums to the worth of the whole coalition."""
    sets = journey_sets(hand_journeys)
    allocation = shapley(sets, ("A", "B", "C"))
    assert sum(allocation.values()) == pytest.approx(coverage_value(sets, {"A", "B", "C"}))


def test_a_channel_in_no_journey_gets_nothing_from_the_shapley_value(
    hand_journeys: pd.DataFrame,
) -> None:
    """The null-player axiom, which is also the sanity check on the coalition enumeration."""
    sets = journey_sets(hand_journeys)
    allocation = shapley(sets, ("A", "B", "C", "Z"))
    assert allocation["Z"] == pytest.approx(0.0)
    assert allocation["A"] == pytest.approx(4.0 / 3.0)


def test_too_many_channels_is_refused_with_the_reason(hand_journeys: pd.DataFrame) -> None:
    """Exponential in the channel count, and pointless, since linear gives the same answer."""
    channels = tuple(f"C{index}" for index in range(MAX_CHANNELS + 1))
    with pytest.raises(ValueError, match="linear attribution gives the same answer"):
        shapley(journey_sets(hand_journeys), channels)


def test_credit_table_puts_every_model_in_one_frame(hand_journeys: pd.DataFrame) -> None:
    table = credit_table(hand_journeys)
    assert list(table.columns) == list(MODELS)
    assert table.sum().round(10).eq(1.0).all()


def test_the_models_disagree_on_the_same_journeys(hand_journeys: pd.DataFrame) -> None:
    """If they agreed there would be nothing to report, so the disagreement is asserted."""
    table = credit_table(hand_journeys)
    assert table.loc["A", "first-click"] > table.loc["A", "last-click"]
    assert table.loc["C", "last-click"] > table.loc["C", "first-click"]


def test_unattributable_separates_the_conversions_nobody_touched() -> None:
    audience = pd.DataFrame(
        [
            {"user": 1, "touches": 2, "converted": True},
            {"user": 2, "touches": 0, "converted": True},
            {"user": 3, "touches": 1, "converted": False},
            {"user": 4, "touches": 0, "converted": False},
        ]
    )
    journeys = pd.DataFrame(
        [
            {"user": 1, "position": 1, "channel": "A", "converted": True},
            {"user": 1, "position": 2, "channel": "B", "converted": True},
            {"user": 3, "position": 1, "channel": "A", "converted": False},
        ]
    )
    missing = unattributable(audience, journeys)
    assert missing == {
        "conversions": 2.0,
        "attributable": 1.0,
        "untouched": 1.0,
        "untouched_share": 0.5,
    }


def test_unattributable_with_no_conversions_at_all_returns_a_nan_share() -> None:
    audience = pd.DataFrame([{"user": 1, "touches": 1, "converted": False}])
    journeys = pd.DataFrame(
        [{"user": 1, "position": 1, "channel": "A", "converted": False}],
    )
    missing = unattributable(audience, journeys)
    assert missing["conversions"] == 0.0
    assert pd.isna(missing["untouched_share"])


def test_a_single_touch_journey_gets_all_of_it_under_every_model() -> None:
    """The degenerate journey, where the six rules have to collapse to the same answer."""
    frame = pd.DataFrame([{"user": 1, "position": 1, "channel": "A", "converted": True}])
    for model in MODELS:
        allocated = credit(frame, model).set_index("channel")["credited"]
        assert float(allocated["A"]) == pytest.approx(1.0), model


def test_a_two_touch_journey_splits_the_position_model_in_half() -> None:
    """With no middle to give the remainder to, 40-20-40 has to become 50-50."""
    frame = pd.DataFrame(
        [
            {"user": 1, "position": 1, "channel": "A", "converted": True},
            {"user": 1, "position": 2, "channel": "B", "converted": True},
        ]
    )
    allocated = credit(frame, "position-based").set_index("channel")["credited"]
    assert float(allocated["A"]) == pytest.approx(0.5)
    assert float(allocated["B"]) == pytest.approx(0.5)


def test_position_based_gives_the_remainder_to_the_middle_touches() -> None:
    """Four touches: 0.40, 0.10, 0.10, 0.40."""
    frame = pd.DataFrame(
        [
            {"user": 1, "position": index, "channel": name, "converted": True}
            for index, name in enumerate("ABCD", start=1)
        ]
    )
    allocated = credit(frame, "position-based").set_index("channel")["credited"]
    assert float(allocated["A"]) == pytest.approx(0.40)
    assert float(allocated["B"]) == pytest.approx(0.10)
    assert float(allocated["C"]) == pytest.approx(0.10)
    assert float(allocated["D"]) == pytest.approx(0.40)


def test_credit_reads_the_touches_in_position_order_not_row_order() -> None:
    """A frame arriving out of order is normal, and last-click must not read the last row."""
    frame = pd.DataFrame(
        [
            {"user": 1, "position": 3, "channel": "C", "converted": True},
            {"user": 1, "position": 1, "channel": "A", "converted": True},
            {"user": 1, "position": 2, "channel": "B", "converted": True},
        ]
    )
    allocated = credit(frame, "last-click").set_index("channel")["credited"]
    assert float(allocated["C"]) == pytest.approx(1.0)
    assert "A" not in allocated.index or float(allocated["A"]) == pytest.approx(0.0)


def test_the_weight_function_refuses_an_unknown_model_too(hand_journeys: pd.DataFrame) -> None:
    """Two guards on the same mistake, on purpose.

    :func:`credit` validates the model name before doing any work, so this branch is unreachable
    through the public API today. It is tested rather than deleted because the next model added
    here will be added to ``MODELS`` first, and this is what catches a name that got into the
    tuple before it got a weighting rule.
    """
    from mktlab.attribution.credit import _weights

    with pytest.raises(ValueError, match="unknown model"):
        _weights(hand_journeys, "mmm", "user", "position")
