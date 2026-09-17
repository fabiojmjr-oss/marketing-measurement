"""Sizing a geo holdout before it is run, and reading the one that already ran.

Wave 1 ran a holdout on five channels and resolved three of them. The two it could not separate
from zero happen to be the two whose true effect is zero, which is the estimator working - but
nothing in the output says so. **A non-significant holdout looks identical whether the channel does
nothing or the test was too small to see what it does**, and that is decidable in advance.

This module decides it. Three things it does that a sizing spreadsheet does not.

**The precision of a geo test closes analytically, so it is known before any money is spent.** The
permanent differences between regions - the thing everybody worries about - cancel exactly in a
difference of changes, and so does any trend common to the regions. What is left is sampling noise
in each region's two phase means, which is a binomial variance on a known number of users. The
predicted standard error is therefore a function of the design alone, and :func:`sizing_table`
prints it against the number of regions and weeks before anybody has to choose.

**The minimum detectable effect is restated as a minimum detectable return.** A rate point is not a
decision. :meth:`GeoDesign.detectable_iroas` divides the minimum detectable lift by the channel's
spend, and the answer is often the whole finding: a test on a small channel can be incapable of
establishing any return the business would care about, and that is knowable on the day the test is
designed rather than thirteen weeks later.

**The holdout has a price, and it is paid in conversions.** Every held-out region loses the channel
for the weeks after the switch, and if the channel works those conversions do not happen.
:func:`holdout_cost` prices that, so the trade is between two numbers in the same units instead of
between a statistical quantity and a vague discomfort.

One thing to keep straight, because getting it wrong is the same class of error as everything else
this repository is about: **the geo panel and the audience are two different populations.** The
panel's size is regions times weeks times users per region-week; the ``reach`` that turns a rate
into a return is the population the channel runs against, and it is passed in rather than inferred.
A cost figure from one and a return figure from the other cannot be subtracted, which is why
:func:`holdout_cost` also reports ``forgone_share`` - the fraction of the held-out regions' own
conversions given up, which is ``lift / base_rate`` and carries no population in it at all.

And for the test that already ran, :func:`retrospective` answers the question a non-result actually
raises: what *was* ruled out. "Not significant" carries an upper bound, that bound is a return, and
quoting the non-result without it is throwing away most of what thirteen weeks bought.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd
from scipy import optimize, stats

from mktlab.attribution.incrementality import GeoLift

#: Conventional power target. A convention, not a property of anything.
DEFAULT_POWER = 0.80
DEFAULT_ALPHA = 0.05

#: Below this, a test reports the absence of evidence and not evidence of absence.
UNDERPOWERED = 0.50

#: Largest number of regions :func:`regions_for` will search to. A design past this is not a design.
MAX_GEOS = 5_000

SIZING_COLUMNS = (
    "geos",
    "weeks",
    "standard_error",
    "detectable_lift",
    "detectable_iroas",
    "forgone_conversions",
    "forgone_revenue",
    "region_weeks_held_out",
)

CURVE_COLUMNS = ("lift", "power", "detectable", "iroas")


def _power_from_noncentral_t(ncp: float, df: float, alpha: float) -> float:
    """Power of a two-sided t-test with noncentrality ``ncp``.

    The noncentral t is the exact null-to-alternative shift for a t statistic; substituting a
    normal is the approximation that understates the size of the test.

    One tail is replaced by its limit: scipy returns ``nan``, rather than a small number, for the
    lower tail of a large positive noncentrality at few degrees of freedom. At two degrees of
    freedom and a noncentrality of 25 the lower tail comes back ``nan`` while the upper is
    0.9999999999999444. What it replaces is the probability of rejecting in the direction opposite
    a large true effect, which is negligible, so the limit is an error no larger than the value it
    stands in for - and without it the whole calculation is ``nan`` for an effect large enough that
    the answer is obvious. It is reached by the root finder walking its bracket outwards, not by
    anybody asking for it.

    Only that tail and only that direction are guarded, because that is the only case scipy
    produces. Which of the four it produces is asserted in the tests rather than assumed here, so a
    scipy that starts failing on a different tail breaks the build instead of quietly returning
    ``nan``.
    """
    if df <= 0:
        raise ValueError("not enough degrees of freedom to compute power")
    critical = float(stats.t.ppf(1.0 - alpha / 2.0, df))
    upper = float(stats.nct.sf(critical, df, ncp))
    lower = float(stats.nct.cdf(-critical, df, ncp))
    if not math.isfinite(lower):
        lower = 0.0
    return upper + lower


@dataclass(frozen=True)
class GeoDesign:
    """A holdout design, and what it can detect before it is run.

    Attributes:
        geos: Regions in the test. Half of them, rounded down, are held out.
        weeks: Weeks the test runs for.
        split: Last week before the channel is switched off.
        users_per_geo_week: Users reached in each region each week.
        base_rate: Conversion rate with the channel running. The binomial variance depends on it,
            so a design cannot be sized without it - which is the one input people leave out.
        alpha: Significance level the test will be read at.
    """

    geos: int
    weeks: int
    split: int
    users_per_geo_week: int
    base_rate: float
    alpha: float = DEFAULT_ALPHA

    def __post_init__(self) -> None:
        if self.geos < 4:
            raise ValueError(
                f"a holdout needs at least two regions a side to have any spread to compare, "
                f"got {self.geos}"
            )
        if not 1 <= self.split < self.weeks:
            raise ValueError(
                f"the split must leave weeks on both sides, got split {self.split} of "
                f"{self.weeks} weeks"
            )
        if not 0.0 < self.base_rate < 1.0:
            raise ValueError(f"the base rate must be a probability, got {self.base_rate}")
        if self.users_per_geo_week <= 0:
            raise ValueError(f"a region-week needs users, got {self.users_per_geo_week}")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError(f"alpha must be a probability, got {self.alpha}")

    @property
    def holdout_geos(self) -> int:
        """Regions that lose the channel."""
        return self.geos // 2

    @property
    def treated_geos(self) -> int:
        """Regions that keep it."""
        return self.geos - self.holdout_geos

    @property
    def weeks_before(self) -> int:
        """Weeks before the switch."""
        return self.split

    @property
    def weeks_after(self) -> int:
        """Weeks after it."""
        return self.weeks - self.split

    @property
    def df(self) -> float:
        """Degrees of freedom of the comparison of region-level changes.

        One observation per region, not one per region-week: a panel of forty regions over
        twenty-six weeks is not one thousand and forty independent observations of a change, and
        treating it as such is how a geo test arrives at an interval ten times too narrow.
        """
        return float(self.treated_geos - 1 + self.holdout_geos - 1)

    def change_sd(self, rate_after: float | None = None) -> float:
        """Standard deviation of one region's change in conversion rate.

        Both quantities that make regions differ from each other drop out of a change: a permanent
        level difference cancels because it is in both phases, and a trend common to the regions
        cancels because it is in both arms. What is left is the binomial noise of the two phase
        means.

        Args:
            rate_after: The region's rate after the switch, when it differs from
                :attr:`base_rate` - which is the case for a held-out region if the channel works.
                Defaults to :attr:`base_rate`.

        Returns:
            The standard deviation of the change.
        """
        after = self.base_rate if rate_after is None else rate_after
        before_variance = (
            self.base_rate * (1.0 - self.base_rate) / (self.users_per_geo_week * self.weeks_before)
        )
        after_variance = after * (1.0 - after) / (self.users_per_geo_week * self.weeks_after)
        return math.sqrt(before_variance + after_variance)

    def standard_error(self, lift: float = 0.0) -> float:
        """Predicted standard error of the estimated lift.

        Args:
            lift: The true lift, which lowers the held-out regions' rate after the switch and so
                slightly lowers their variance. Passing zero is the conservative choice and is the
                default, because a design is sized before the lift is known.

        Returns:
            The standard error of the difference of the two arms' mean changes.
        """
        treated = self.change_sd() ** 2
        held_out = self.change_sd(self.base_rate - lift) ** 2
        return math.sqrt(treated / self.treated_geos + held_out / self.holdout_geos)

    def power(self, lift: float) -> float:
        """Probability this design detects a lift of ``lift``.

        At a lift of exactly zero this returns :attr:`alpha`, which is the definition of the
        significance level rather than a coincidence, and is asserted as an exact control case.

        The rejection region is two-sided and symmetric, but the power is very slightly not: a
        channel that *hurts* raises the held-out regions' rate after the switch rather than
        lowering it, and a rate nearer one half varies more. So this design has about 0.3% less
        power against harm of a given size than against help of the same size. It is a property of
        the binomial variance rather than an asymmetry in the test, and it is asserted in the
        tests so that nobody later "fixes" it.
        """
        error = self.standard_error(lift)
        return _power_from_noncentral_t(lift / error, self.df, self.alpha)

    def detectable_lift(self, power: float = DEFAULT_POWER) -> float:
        """The smallest lift this design detects with probability ``power``.

        The question a non-significant holdout actually raises. Anything below this was never in
        reach, and reporting "no incremental return" for it is a statement about the test.

        Args:
            power: Target power.

        Returns:
            The minimum detectable lift, in conversion-rate points.

        Raises:
            ValueError: If the power asked for is not between alpha and one. Power below alpha is
                not achievable by a smaller effect - alpha is the floor - and power of one needs an
                infinite effect.
        """
        if not self.alpha < power < 1.0:
            raise ValueError(f"power must be above alpha ({self.alpha}) and below one, got {power}")
        ceiling = self.base_rate
        if self.power(ceiling) < power:
            raise ValueError(
                f"this design cannot reach {power:.0%} power for any lift up to the base rate "
                f"itself ({self.base_rate}), which means it cannot detect the channel being "
                f"switched off at all"
            )
        solved = float(
            optimize.brentq(lambda lift: self.power(lift) - power, 1e-12, ceiling, xtol=1e-12)
        )
        # The root finder lands within its tolerance of the target, which can be a hair below it:
        # the first version of this printed a detectable lift of 0.002361 next to a power of
        # 0.799992 in a table headed "detects at 80% power", and a table that contradicts its own
        # heading by eight parts in a million reads as a defect whether or not it is one. The
        # returned lift is therefore nudged up until the power is at or above what was asked for,
        # the same way a sample size is rounded up rather than to the nearest integer.
        while self.power(solved) < power and solved < ceiling:
            solved = min(solved * (1.0 + 1e-9) + 1e-15, ceiling)
        return solved

    def return_precision(
        self,
        spend: float,
        reach: float,
        value_per_conversion: float,
    ) -> float:
        """Half-width of the confidence interval this design will produce, in return terms.

        More useful than the minimum detectable return and less often computed, because the
        question a budget asks is rarely "is it above zero" - it is "is it above three". That is
        answerable only if the interval is narrower than the distance between the two candidate
        answers, and this is that width, known in advance.

        Args:
            spend: The channel's spend over the period.
            reach: Users the channel runs against.
            value_per_conversion: Revenue per conversion.

        Returns:
            The half-width of the interval on the incremental return.

        Raises:
            ValueError: If the spend is not positive.
        """
        if spend <= 0:
            raise ValueError(f"spend must be positive, got {spend}")
        critical = float(stats.t.ppf(1.0 - self.alpha / 2.0, self.df))
        return critical * self.standard_error() * reach * value_per_conversion / spend

    def detectable_iroas(
        self,
        spend: float,
        reach: float,
        value_per_conversion: float,
        power: float = DEFAULT_POWER,
    ) -> float:
        """The smallest incremental return this design can establish.

        The figure that decides whether the test is worth running: a rate point is not a decision,
        and a test whose detectable return sits above what the business would act on cannot answer
        the question it is being run for, however long it runs.

        Args:
            spend: The channel's spend over the period.
            reach: Users the channel runs against over the period.
            value_per_conversion: Revenue per conversion.
            power: Target power.

        Returns:
            The minimum detectable return on ad spend, incremental.

        Raises:
            ValueError: If the spend is not positive.
        """
        if spend <= 0:
            raise ValueError(f"spend must be positive, got {spend}")
        return self.detectable_lift(power) * reach * value_per_conversion / spend

    def verdict(self, power: float = DEFAULT_POWER) -> str:
        """What this design can and cannot find, in one line."""
        detectable = self.detectable_lift(power)
        return (
            f"{self.geos} regions, {self.weeks} weeks: standard error "
            f"{self.standard_error():.6f}, detects {detectable:+.6f} rate points at "
            f"{power:.0%} power"
        )


def power_curve(
    design: GeoDesign,
    lifts: tuple[float, ...],
    spend: float | None = None,
    reach: float = 0.0,
    value_per_conversion: float = 0.0,
    power: float = DEFAULT_POWER,
) -> pd.DataFrame:
    """Power against the size of the effect, with the return each lift corresponds to.

    Args:
        design: The design.
        lifts: Lifts to evaluate, in rate points.
        spend: The channel's spend, to express each lift as a return. Omitted leaves the column
            empty rather than inventing a spend.
        reach: Users the channel runs against.
        value_per_conversion: Revenue per conversion.
        power: The target the ``detectable`` column is judged against.

    Returns:
        A frame with the columns in :data:`CURVE_COLUMNS`.
    """
    rows = []
    for lift in lifts:
        achieved = design.power(lift)
        rows.append(
            {
                "lift": lift,
                "power": achieved,
                "detectable": achieved >= power,
                "iroas": (
                    lift * reach * value_per_conversion / spend
                    if spend is not None and spend > 0
                    else float("nan")
                ),
            }
        )
    return pd.DataFrame(rows)[list(CURVE_COLUMNS)]


def regions_for(
    lift: float,
    design: GeoDesign,
    power: float = DEFAULT_POWER,
) -> int:
    """The smallest even number of regions that detects ``lift`` at ``power``.

    Args:
        lift: The lift to detect, in rate points.
        design: A design supplying the weeks, the users and the base rate. Its own region count is
            replaced by the answer.
        power: Target power.

    Returns:
        Regions needed, always even, so the two arms are equal.

    Raises:
        ValueError: If the lift is not positive, or if no design up to :data:`MAX_GEOS` reaches the
            target - which is a real answer and not a failure: it says this lift is not detectable
            by adding regions, and the weeks or the base rate have to change instead.
    """
    if lift <= 0:
        raise ValueError(f"the lift to detect must be positive, got {lift}")
    count = 4
    while count <= MAX_GEOS:
        candidate = GeoDesign(
            geos=count,
            weeks=design.weeks,
            split=design.split,
            users_per_geo_week=design.users_per_geo_week,
            base_rate=design.base_rate,
            alpha=design.alpha,
        )
        if candidate.power(lift) >= power:
            return count
        count += 2
    raise ValueError(
        f"no design up to {MAX_GEOS} regions reaches {power:.0%} power for a lift of {lift}; "
        f"more weeks or more users per region-week are needed, not more regions"
    )


def holdout_cost(
    design: GeoDesign,
    lift: float,
    value_per_conversion: float,
) -> dict[str, float]:
    """What the test costs if the channel works, in conversions and in money.

    The held-out regions lose the channel for the weeks after the switch. If the channel does
    nothing this costs nothing, which is the asymmetry worth stating: **the test is expensive
    exactly when its answer is that the channel was worth keeping.**

    Args:
        design: The design.
        lift: The lift the channel really has, in rate points.
        value_per_conversion: Revenue per conversion.

    Returns:
        ``region_weeks_held_out``, ``users_held_out``, ``forgone_conversions``,
        ``forgone_revenue`` and ``forgone_share``. The share is of the conversions the held-out
        regions would have produced, and is the only one of the five that can be compared across
        populations: it is ``lift / base_rate`` exactly, so it does not depend on how many users
        the panel happens to contain.
    """
    region_weeks = float(design.holdout_geos * design.weeks_after)
    users = region_weeks * design.users_per_geo_week
    conversions = users * lift
    return {
        "region_weeks_held_out": region_weeks,
        "users_held_out": users,
        "forgone_conversions": conversions,
        "forgone_revenue": conversions * value_per_conversion,
        "forgone_share": lift / design.base_rate,
    }


def sizing_table(
    design: GeoDesign,
    geos: tuple[int, ...],
    weeks: tuple[int, ...],
    spend: float,
    reach: float,
    value_per_conversion: float,
    expected_lift: float,
    power: float = DEFAULT_POWER,
) -> pd.DataFrame:
    """The trade, as one table: precision against what the test costs.

    Every row is a design that could be run. The left half is what it can find, the right half is
    what it gives up to find it - both in conversions, so the choice is between comparable numbers.

    Args:
        design: A design supplying the users per region-week, the base rate and alpha.
        geos: Region counts to consider.
        weeks: Total test lengths to consider. The switch is placed halfway.
        spend: The channel's spend, for the detectable return.
        reach: Users the channel runs against.
        value_per_conversion: Revenue per conversion.
        expected_lift: The lift used to price the holdout. Pricing the cost at the lift the channel
            is believed to have is deliberate: the cost of the test is unknown for the same reason
            the test is being run, and using zero would price every test at nothing.
        power: Target power.

    Returns:
        A frame with the columns in :data:`SIZING_COLUMNS`.
    """
    rows = []
    for count in geos:
        for length in weeks:
            candidate = GeoDesign(
                geos=count,
                weeks=length,
                split=length // 2,
                users_per_geo_week=design.users_per_geo_week,
                base_rate=design.base_rate,
                alpha=design.alpha,
            )
            cost = holdout_cost(candidate, expected_lift, value_per_conversion)
            rows.append(
                {
                    "geos": count,
                    "weeks": length,
                    "standard_error": candidate.standard_error(),
                    "detectable_lift": candidate.detectable_lift(power),
                    "detectable_iroas": candidate.detectable_iroas(
                        spend, reach, value_per_conversion, power
                    ),
                    "forgone_conversions": cost["forgone_conversions"],
                    "forgone_revenue": cost["forgone_revenue"],
                    "region_weeks_held_out": cost["region_weeks_held_out"],
                }
            )
    return pd.DataFrame(rows)[list(SIZING_COLUMNS)]


@dataclass(frozen=True)
class Retrospective:
    """What a holdout that already ran actually established.

    Attributes:
        channel: The channel.
        lift: The estimated lift.
        significant: Whether the test separated it from zero.
        iroas: The point estimate as an incremental return.
        iroas_interval: The confidence interval on that return.
        detectable_iroas: The smallest return the design could have established.
        untested_because: Empty unless the design could not be read at all.
    """

    channel: str
    lift: float
    significant: bool
    iroas: float
    iroas_interval: tuple[float, float]
    detectable_iroas: float
    untested_because: str = ""

    @property
    def excludes(self) -> float:
        """The return this test rules out, being the top of its interval.

        The half of a non-result nobody quotes. "We could not establish a return" and "the return
        is below 1.41" are the same test read twice, and only the second one is a fact about the
        channel.
        """
        return self.iroas_interval[1]

    @property
    def was_big_enough(self) -> bool:
        """Whether the design could have found a return worth acting on.

        True when the smallest return the design could establish sits below the top of the interval
        the test produced: the test was capable of resolving the range the answer turned out to be
        in. False means the non-result is about the test's size.
        """
        return self.detectable_iroas <= self.excludes

    def verdict(self) -> str:
        """One line, and the one a report should carry instead of the p-value alone."""
        if self.untested_because:
            return f"{self.channel}: untested - {self.untested_because}"
        low, high = self.iroas_interval
        if self.significant:
            return (
                f"{self.channel}: incremental return {self.iroas:.4f}, "
                f"interval {low:.4f} to {high:.4f}"
            )
        capable = (
            "the design could resolve that range"
            if self.was_big_enough
            else (
                f"and the design could not establish any return below "
                f"{self.detectable_iroas:.4f} anyway"
            )
        )
        return (
            f"{self.channel}: no return established, but returns above {high:.4f} are ruled "
            f"out - {capable}"
        )


def retrospective(
    result: GeoLift,
    design: GeoDesign,
    spend: float,
    reach: float,
    value_per_conversion: float,
    power: float = DEFAULT_POWER,
) -> Retrospective:
    """Read a holdout that already ran as a statement about returns.

    Args:
        result: The holdout's result.
        design: The design it was run under, for what it could have detected.
        spend: The channel's spend over the period.
        reach: Users the channel ran against.
        value_per_conversion: Revenue per conversion.
        power: The power the detectable return is quoted at.

    Returns:
        A :class:`Retrospective`.

    Raises:
        ValueError: If the spend is not positive.
    """
    if spend <= 0:
        raise ValueError(f"spend must be positive, got {spend}")
    scale = reach * value_per_conversion / spend
    low, high = result.interval
    return Retrospective(
        channel=result.channel,
        lift=result.lift,
        significant=result.significant,
        iroas=result.lift * scale,
        iroas_interval=(low * scale, high * scale),
        detectable_iroas=design.detectable_iroas(spend, reach, value_per_conversion, power),
        untested_because=result.untested_because,
    )
