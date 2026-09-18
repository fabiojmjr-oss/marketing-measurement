"""The model people use when nobody will pay for the experiment.

:mod:`~mktlab.mmm.model` fits weekly conversions on transformed weekly spend and reports, beside
every coefficient, the width the data actually supports. Three things it is built to make visible.

**The channels move together**, because media plans are written as shares of a budget, so the
columns of the design matrix are nearly the same column. The regression returns a coefficient
anyway - it always does - and the standard error beside it is the model saying it could not tell
them apart.

**The two transforms are guesses.** How much of a week's spend carries over, and where returns bend,
are not observed. A grid of very different guesses fits almost identically and implies returns that
differ by a factor of several.

**And the coefficient is a local slope**, not a return on the whole spend. Pushing it through the
chain rule is the difference between a number a budget can use and a number that sounds like one.

The same account's holdout is in :mod:`mktlab.attribution`, and both are measured against the same
declared truth, so the two instruments can be put side by side.
"""

from .model import (
    DEFAULT_ALPHA,
    FIT_COLUMNS,
    GRID_COLUMNS,
    RETURN_COLUMNS,
    Fit,
    channel_names,
    channel_of,
    design_matrix,
    fit,
    spend_columns,
    transform_grid,
    variance_inflation,
)

__all__ = [
    "DEFAULT_ALPHA",
    "FIT_COLUMNS",
    "GRID_COLUMNS",
    "RETURN_COLUMNS",
    "Fit",
    "channel_names",
    "channel_of",
    "design_matrix",
    "fit",
    "spend_columns",
    "transform_grid",
    "variance_inflation",
]
