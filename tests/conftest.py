"""Shared fixtures. The dataset is built once per session because it is deterministic."""

from __future__ import annotations

import pandas as pd
import pytest

from mktlab.synth import Dataset, generate_dataset


@pytest.fixture(scope="session")
def full() -> Dataset:
    """The published dataset, from the default seed."""
    return generate_dataset()


@pytest.fixture
def hand_journeys() -> pd.DataFrame:
    """Three journeys whose every model can be worked out on paper.

    User 1 converted after A, B, C in that order. User 2 converted after A alone. User 3 saw B and
    C and did not convert, so no model may give it any weight.

    The allocations, in conversions: last-click A 1, C 1; first-click A 2; linear A 4/3, B 1/3,
    C 1/3; position-based A 1.4, B 0.2, C 0.4; time-decay A 1 + 1/7, B 2/7, C 4/7.
    """
    rows = [
        {"user": 1, "position": 1, "channel": "A", "converted": True},
        {"user": 1, "position": 2, "channel": "B", "converted": True},
        {"user": 1, "position": 3, "channel": "C", "converted": True},
        {"user": 2, "position": 1, "channel": "A", "converted": True},
        {"user": 3, "position": 1, "channel": "B", "converted": False},
        {"user": 3, "position": 2, "channel": "C", "converted": False},
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def noiseless_panel() -> pd.DataFrame:
    """A holdout with no noise at all, whose lift is exact.

    Four regions, four weeks, the switch after week 2. Every region converts at 0.10 before; after
    the switch the two treated regions stay at 0.10 and the two holdout regions drop to 0.06. The
    difference in differences is therefore exactly +0.04, with no spread between regions on either
    side - which is the case an estimator has to get exactly right before its answer on noisy data
    means anything.
    """
    rows = []
    for geo in range(4):
        holdout = geo >= 2
        for week in range(1, 5):
            rate = 0.06 if (holdout and week > 2) else 0.10
            rows.append(
                {
                    "geo": f"G{geo}",
                    "week": week,
                    "holdout": holdout,
                    "users": 1_000,
                    "conversions": int(round(1_000 * rate)),
                }
            )
    return pd.DataFrame(rows)
