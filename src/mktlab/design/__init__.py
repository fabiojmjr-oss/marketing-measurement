"""Deciding what a test can find, before anybody pays for it.

:mod:`~mktlab.design.geo` sizes a geo holdout. The precision of one closes analytically - the
permanent differences between regions cancel in a difference of changes - so the standard error,
the minimum detectable lift and, more usefully, the **minimum detectable return** are all functions
of the design rather than of the data. Next to them sits what the test costs if the channel works,
in the same units, so the trade is between two comparable numbers.

It also reads a test that already ran: a non-significant holdout carries an upper bound, that bound
is a return, and a report that quotes the p-value without it throws away most of what the test
bought.

:mod:`~mktlab.design.sequential` removes the assumption the sizing never states: that the test is
read once, at the end. Reading a thirteen-week holdout every Monday against the usual 1.96 takes its
false-positive rate from 5% to 21.4%. Two boundaries hold it at 5% instead, at prices that are
computed here rather than assumed - and neither of them repairs the other half of the damage, which
is that a test stopped early reports an effect larger than the one it measured.
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
from .sequential import (
    MAX_LOOKS,
    NODES,
    PEEKING_COLUMNS,
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

__all__ = [
    "CURVE_COLUMNS",
    "DEFAULT_ALPHA",
    "DEFAULT_POWER",
    "MAX_GEOS",
    "MAX_LOOKS",
    "NODES",
    "PEEKING_COLUMNS",
    "RULES",
    "SIZING_COLUMNS",
    "UNDERPOWERED",
    "GeoDesign",
    "Retrospective",
    "SequentialPlan",
    "crossing_probability",
    "exaggeration",
    "expected_looks",
    "fixed_boundary",
    "holdout_cost",
    "inflated_alpha",
    "information_inflation",
    "ncp_for_power",
    "nominal_alpha",
    "obrien_fleming",
    "peeking_table",
    "plan",
    "pocock",
    "power",
    "power_curve",
    "regions_for",
    "retrospective",
    "sizing_table",
]
