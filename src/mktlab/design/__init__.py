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

It also builds the plan a real test needs rather than the one a textbook assumes: an alpha-spending
schedule, so the looks do not have to be evenly spaced or even known in advance, and a futility
boundary, so a test that cannot succeed ends instead of running to the calendar. What that saves is
weeks rather than conversions, and the module is explicit about it - the arithmetic of wave 2 says a
channel doing nothing costs nothing to hold out, which is exactly the case futility fires on.
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
    SCHEDULE_COLUMNS,
    SPENDING,
    UNREACHABLE,
    MonitoringPlan,
    SequentialPlan,
    alpha_spent,
    beta_spent,
    crossing_probability,
    equal_information,
    exaggeration,
    expected_looks,
    fixed_boundary,
    futility_boundary,
    futility_probability,
    inflated_alpha,
    information_inflation,
    monitoring_plan,
    ncp_for_power,
    nominal_alpha,
    obrien_fleming,
    peeking_table,
    plan,
    pocock,
    power,
    schedule,
    spending_boundary,
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
    "SCHEDULE_COLUMNS",
    "SIZING_COLUMNS",
    "SPENDING",
    "UNDERPOWERED",
    "UNREACHABLE",
    "GeoDesign",
    "MonitoringPlan",
    "Retrospective",
    "SequentialPlan",
    "alpha_spent",
    "beta_spent",
    "crossing_probability",
    "equal_information",
    "exaggeration",
    "expected_looks",
    "fixed_boundary",
    "futility_boundary",
    "futility_probability",
    "holdout_cost",
    "inflated_alpha",
    "information_inflation",
    "monitoring_plan",
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
    "schedule",
    "sizing_table",
    "spending_boundary",
]
