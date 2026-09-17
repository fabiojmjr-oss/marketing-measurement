"""Seeded synthetic data for every module in the toolkit.

No data from any advertiser, agency, platform or client is used anywhere in this repository. See
``DISCLAIMER.md``.
"""

from .config import (
    AUDIENCE,
    CHANNELS,
    GEO,
    SEED,
    STAGE_NOISE,
    AudienceProfile,
    ChannelProfile,
    GeoProfile,
)
from .dataset import Dataset, generate_dataset
from .geo import (
    DESIGN_COLUMNS,
    GEO_COLUMNS,
    geo_designs,
    geo_experiments,
    mean_rate,
    true_rate_lift,
)
from .journeys import (
    AUDIENCE_COLUMNS,
    JOURNEY_COLUMNS,
    TRUTH_COLUMNS,
    audience_and_journeys,
    channel_truth,
    conversion_probability,
    exposure_probability,
)

__all__ = [
    "AUDIENCE",
    "AUDIENCE_COLUMNS",
    "CHANNELS",
    "DESIGN_COLUMNS",
    "GEO",
    "GEO_COLUMNS",
    "JOURNEY_COLUMNS",
    "SEED",
    "STAGE_NOISE",
    "TRUTH_COLUMNS",
    "AudienceProfile",
    "ChannelProfile",
    "Dataset",
    "GeoProfile",
    "audience_and_journeys",
    "channel_truth",
    "conversion_probability",
    "exposure_probability",
    "generate_dataset",
    "geo_designs",
    "geo_experiments",
    "mean_rate",
    "true_rate_lift",
]
