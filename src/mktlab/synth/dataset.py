"""One seeded dataset feeding every module, so no example needs its own fixture."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import SEED
from .geo import geo_designs, geo_experiments
from .journeys import audience_and_journeys, channel_truth


@dataclass(frozen=True)
class Dataset:
    """Every table the toolkit's examples and tests are built on.

    Attributes:
        audience: One row per user, including the intent no real account has.
        journeys: One row per touch: who was reached, in what order, and whether they converted.
        channel_truth: One row per channel, with its real effect and how selected its audience is.
        geo_experiments: One row per region-week of a holdout panel, one panel per channel.
        geo_designs: One row per panel, with the lift the test should recover.
    """

    audience: pd.DataFrame
    journeys: pd.DataFrame
    channel_truth: pd.DataFrame
    geo_experiments: pd.DataFrame
    geo_designs: pd.DataFrame


def generate_dataset(seed: int = SEED) -> Dataset:
    """Build the whole dataset from one seed.

    New tables are appended at the end of this function rather than inserted, because the
    generator is consumed in stream order: inserting a draw shifts every later table and every
    published figure with it.

    Args:
        seed: Seed for the shared generator. The published figures all use the default.

    Returns:
        A :class:`Dataset`.
    """
    rng = np.random.default_rng(seed)
    audience, journeys = audience_and_journeys(rng)
    return Dataset(
        audience=audience,
        journeys=journeys,
        channel_truth=channel_truth(),
        # Appended after the journeys, so the attribution figures are untouched by a change here.
        geo_experiments=geo_experiments(rng),
        geo_designs=geo_designs(),
    )
