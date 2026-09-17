"""Allocating credit for a conversion among the channels that touched the user.

Every model here is a rule for splitting something that already happened. None of them contains a
counterfactual, so none of them can distinguish a channel that caused a conversion from a channel
that was present when one was going to happen anyway. That is not a criticism of the arithmetic -
the arithmetic is trivial and correct - it is a statement about what the arithmetic is *of*.

Two things worth knowing before reading a report built on any of them:

**The models disagree with each other by more than most budget decisions.** On the same journeys,
the share a channel receives moves by a factor of several between first-click and last-click,
because the order of touches is a fact about the funnel's shape rather than about cause.

**And the "data-driven" one is not a different answer.** The Shapley value of the standard journey
coverage game - the game whose worth is the conversions whose channel set is contained in a
coalition - is **exactly** linear attribution. Not approximately: each journey splits equally
among its channels, provably, and :func:`shapley` computes it the long way round so the identity
can be checked rather than asserted. A model sold as principled and a rule anybody could write on
a napkin return the same numbers.

What none of them can do is in :mod:`mktlab.attribution.incrementality`, which needs an experiment.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter

import numpy as np
import pandas as pd

#: The models, in the order the published table lists them.
MODELS = ("last-click", "first-click", "linear", "position-based", "time-decay", "shapley")

#: Share given to the first and last touch by the position-based model, with the remainder split
#: among the middle. The 40/20/40 convention, exposed because it is a convention.
POSITION_FIRST = 0.40
POSITION_LAST = 0.40

#: Weight halving per step back from the last touch, for the time-decay model. Also a convention.
DECAY_RATIO = 0.5

CREDIT_COLUMNS = ("channel", "credited", "share")


def _converting(journeys: pd.DataFrame, converted: str, user: str, position: str) -> pd.DataFrame:
    """The touches of converting users, in order. What an attribution tool actually reads."""
    frame = journeys[journeys[converted].astype(bool)]
    if frame.empty:
        raise ValueError("no converting journeys, so there is nothing to allocate")
    return frame.sort_values([user, position])


def _weights(frame: pd.DataFrame, model: str, user: str, position: str) -> np.ndarray:
    """The share of its conversion each touch receives under a model."""
    length = frame.groupby(user, observed=True)[position].transform("size").to_numpy()
    order = frame.groupby(user, observed=True)[position].transform("cumcount").to_numpy()
    first = order == 0
    last = order == length - 1

    if model == "last-click":
        return last.astype(float)
    if model == "first-click":
        return first.astype(float)
    if model in {"linear", "shapley"}:
        # Identical by construction: see the module docstring and :func:`shapley`, which computes
        # the Shapley value from the game rather than from this shortcut.
        return 1.0 / length
    if model == "position-based":
        weights = np.full(length.shape, 0.0)
        single = length == 1
        pair = length == 2
        longer = length >= 3
        weights[single] = 1.0
        weights[pair & (first | last)] = 0.5
        middle = longer & ~first & ~last
        weights[longer & first] = POSITION_FIRST
        weights[longer & last] = POSITION_LAST
        remainder = 1.0 - POSITION_FIRST - POSITION_LAST
        weights[middle] = remainder / (length[middle] - 2)
        return weights
    if model == "time-decay":
        steps = (length - 1 - order).astype(float)
        raw = DECAY_RATIO**steps
        total = pd.Series(raw).groupby(frame[user].to_numpy(), observed=True).transform("sum")
        return (raw / total.to_numpy()).astype(float)
    raise ValueError(f"unknown model {model!r}; the models are {MODELS}")


def journey_sets(
    journeys: pd.DataFrame,
    user: str = "user",
    channel: str = "channel",
    converted: str = "converted",
) -> Counter[frozenset[str]]:
    """How many conversions each distinct set of channels produced.

    The coalition game the Shapley model is defined on, and the only thing it needs: the order of
    the touches does not enter it, which is itself worth noticing about a model that is often sold
    as understanding the journey.

    Args:
        journeys: One row per touch.
        user: Column identifying the user.
        channel: Column holding the channel.
        converted: Boolean column marking a converting journey.

    Returns:
        A counter from channel set to number of conversions.
    """
    frame = journeys[journeys[converted].astype(bool)]
    grouped = frame.groupby(user, observed=True)[channel].agg(frozenset)
    return Counter(grouped.tolist())


def coverage_value(sets: Counter[frozenset[str]], coalition: frozenset[str] | set[str]) -> float:
    """The worth of a coalition: conversions whose whole journey sits inside it.

    This is the standard definition, and it is the one that makes the Shapley value computable: a
    journey is "explained" by a coalition only when every channel it used is in the coalition.

    Args:
        sets: Output of :func:`journey_sets`.
        coalition: The channels in the coalition.

    Returns:
        Conversions attributable to the coalition.
    """
    chosen = frozenset(coalition)
    return float(sum(count for touched, count in sets.items() if touched <= chosen))


def shapley(sets: Counter[frozenset[str]], channels: tuple[str, ...]) -> dict[str, float]:
    """The Shapley value of the coverage game, computed from the definition.

    Deliberately the long way round - every coalition, every marginal contribution, the factorial
    weights - so that its equality with linear attribution is a result rather than an assumption.
    The cost is exponential in the number of channels, which is why :data:`MAX_CHANNELS` exists.

    Args:
        sets: Output of :func:`journey_sets`.
        channels: The channels to allocate among.

    Returns:
        Credited conversions per channel.

    Raises:
        ValueError: If there are more channels than :data:`MAX_CHANNELS`.
    """
    if len(channels) > MAX_CHANNELS:
        raise ValueError(
            f"the Shapley value over {len(channels)} channels needs 2^{len(channels)} coalitions; "
            f"the limit here is {MAX_CHANNELS}, and linear attribution gives the same answer"
        )
    total = len(channels)
    allocation = dict.fromkeys(channels, 0.0)
    for channel in channels:
        others = [other for other in channels if other != channel]
        for size in range(len(others) + 1):
            weight = math.factorial(size) * math.factorial(total - size - 1) / math.factorial(total)
            for coalition in itertools.combinations(others, size):
                marginal = coverage_value(sets, frozenset(coalition) | {channel}) - coverage_value(
                    sets, frozenset(coalition)
                )
                allocation[channel] += weight * marginal
    return allocation


#: Channels the exact Shapley computation is allowed. Every extra channel doubles the work, and the
#: identity with linear attribution means there is nothing to gain by pushing it.
MAX_CHANNELS = 12


def credit(
    journeys: pd.DataFrame,
    model: str,
    user: str = "user",
    position: str = "position",
    channel: str = "channel",
    converted: str = "converted",
) -> pd.DataFrame:
    """Allocate the conversions among the channels under one model.

    Args:
        journeys: One row per touch, with a position and a conversion flag.
        model: One of :data:`MODELS`.
        user: Column identifying the user.
        position: Column holding the touch's order within the journey.
        channel: Column holding the channel.
        converted: Boolean column marking a converting journey.

    Returns:
        A frame with the columns in :data:`CREDIT_COLUMNS`, one row per channel. ``share`` is of
        the conversions the model can see, which is not all of them - see
        :func:`unattributable`.

    Raises:
        ValueError: If the model is unknown or no journey converted.
    """
    if model not in MODELS:
        raise ValueError(f"unknown model {model!r}; the models are {MODELS}")
    frame = _converting(journeys, converted, user, position)

    if model == "shapley":
        sets = journey_sets(journeys, user=user, channel=channel, converted=converted)
        allocation = shapley(sets, tuple(sorted({item for key in sets for item in key})))
        credited = pd.Series(allocation, dtype=float)
    else:
        weights = _weights(frame, model, user, position)
        credited = (
            pd.Series(weights, index=frame[channel].to_numpy())
            .groupby(level=0, observed=True)
            .sum()
        )
    credited = credited.sort_index()
    return pd.DataFrame(
        {
            "channel": credited.index,
            "credited": credited.to_numpy(),
            "share": credited.to_numpy() / credited.sum(),
        }
    )[list(CREDIT_COLUMNS)]


def credit_table(
    journeys: pd.DataFrame,
    models: tuple[str, ...] = MODELS,
    **columns: str,
) -> pd.DataFrame:
    """Every model side by side, as shares, which is how a report is read.

    Args:
        journeys: One row per touch.
        models: The models to run.
        **columns: Column names, forwarded to :func:`credit`.

    Returns:
        A frame indexed by channel with one column per model.
    """
    shares = {
        model: credit(journeys, model, **columns).set_index("channel")["share"] for model in models
    }
    return pd.DataFrame(shares)


def unattributable(
    audience: pd.DataFrame,
    journeys: pd.DataFrame,
    converted: str = "converted",
    touches: str = "touches",
) -> dict[str, float]:
    """The conversions no attribution model can see, because nobody touched them.

    Every model above divides the conversions it *can* see, and a report that rescales those
    shares to one hundred per cent has quietly given the untouched conversions away to the
    channels - in proportion to how much credit they already had.

    Args:
        audience: One row per user, with a touch count and a conversion flag.
        journeys: One row per touch, used only to cross-check the count.
        converted: Boolean conversion column.
        touches: Column holding how many touches the user received.

    Returns:
        ``conversions``, ``attributable``, ``untouched`` and ``untouched_share``.
    """
    converting = audience[audience[converted].astype(bool)]
    total = float(len(converting))
    untouched = float((converting[touches] == 0).sum())
    seen = float(journeys[journeys[converted].astype(bool)]["user"].nunique())
    return {
        "conversions": total,
        "attributable": seen,
        "untouched": untouched,
        "untouched_share": untouched / total if total else float("nan"),
    }
