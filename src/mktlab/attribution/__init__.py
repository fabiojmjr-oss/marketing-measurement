"""Attribution: who gets the credit, and what a holdout says instead.

:mod:`~mktlab.attribution.credit` allocates conversions among the channels that touched the user.
Every model in it is a rule for splitting something that already happened, so none of them can tell
a channel that caused a conversion from a channel that was present when one was going to happen
anyway - and the "data-driven" Shapley model turns out to be *exactly* linear attribution, which
the module proves rather than asserts.

:mod:`~mktlab.attribution.incrementality` runs the experiment that can tell them apart: a geo
holdout, read as a difference in differences on region-level rates, and the return on ad spend put
next to the incremental version of it.
"""

from .credit import (
    CREDIT_COLUMNS,
    DECAY_RATIO,
    MAX_CHANNELS,
    MODELS,
    POSITION_FIRST,
    POSITION_LAST,
    coverage_value,
    credit,
    credit_table,
    journey_sets,
    shapley,
    unattributable,
)
from .incrementality import (
    DEFAULT_ALPHA,
    RETURN_COLUMNS,
    GeoLift,
    geo_lift,
    iroas,
    returns,
    roas,
)

__all__ = [
    "CREDIT_COLUMNS",
    "DECAY_RATIO",
    "DEFAULT_ALPHA",
    "MAX_CHANNELS",
    "MODELS",
    "POSITION_FIRST",
    "POSITION_LAST",
    "RETURN_COLUMNS",
    "GeoLift",
    "coverage_value",
    "credit",
    "credit_table",
    "geo_lift",
    "iroas",
    "journey_sets",
    "returns",
    "roas",
    "shapley",
    "unattributable",
]
