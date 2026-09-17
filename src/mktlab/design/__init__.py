"""Deciding what a test can find, before anybody pays for it.

:mod:`~mktlab.design.geo` sizes a geo holdout. The precision of one closes analytically - the
permanent differences between regions cancel in a difference of changes - so the standard error,
the minimum detectable lift and, more usefully, the **minimum detectable return** are all functions
of the design rather than of the data. Next to them sits what the test costs if the channel works,
in the same units, so the trade is between two comparable numbers.

It also reads a test that already ran: a non-significant holdout carries an upper bound, that bound
is a return, and a report that quotes the p-value without it throws away most of what the test
bought.
"""

from .geo import (
    CURVE_COLUMNS,
    DEFAULT_ALPHA,
    DEFAULT_POWER,
    MAX_GEOS,
    SIZING_COLUMNS,
    UNDERPOWERED,
    GeoDesign,
    Retrospective,
    holdout_cost,
    power_curve,
    regions_for,
    retrospective,
    sizing_table,
)

__all__ = [
    "CURVE_COLUMNS",
    "DEFAULT_ALPHA",
    "DEFAULT_POWER",
    "MAX_GEOS",
    "SIZING_COLUMNS",
    "UNDERPOWERED",
    "GeoDesign",
    "Retrospective",
    "holdout_cost",
    "power_curve",
    "regions_for",
    "retrospective",
    "sizing_table",
]
