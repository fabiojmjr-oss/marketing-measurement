"""Seeded synthetic data for every module in the toolkit.

No data from any advertiser, agency, platform or client is used anywhere in this repository. See
``DISCLAIMER.md``.
"""

from .config import (
    AUDIENCE,
    CHANNELS,
    GEO,
    MEDIA_MIX,
    SEED,
    STAGE_NOISE,
    AudienceProfile,
    ChannelProfile,
    GeoProfile,
    MediaMixProfile,
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
from .spend import (
    MEDIA_TRUTH_COLUMNS,
    SPEND_COLUMNS,
    adstock,
    conversions_per_unit_spend,
    media_truth,
    saturate,
    spend_panel,
)

__all__ = [
    "AUDIENCE",
    "AUDIENCE_COLUMNS",
    "CHANNELS",
    "DESIGN_COLUMNS",
    "GEO",
    "GEO_COLUMNS",
    "JOURNEY_COLUMNS",
    "MEDIA_MIX",
    "MEDIA_TRUTH_COLUMNS",
    "SEED",
    "SPEND_COLUMNS",
    "STAGE_NOISE",
    "TRUTH_COLUMNS",
    "AudienceProfile",
    "ChannelProfile",
    "Dataset",
    "GeoProfile",
    "MediaMixProfile",
    "adstock",
    "audience_and_journeys",
    "channel_truth",
    "conversion_probability",
    "conversions_per_unit_spend",
    "exposure_probability",
    "generate_dataset",
    "geo_designs",
    "geo_experiments",
    "mean_rate",
    "media_truth",
    "saturate",
    "spend_panel",
    "true_rate_lift",
]
