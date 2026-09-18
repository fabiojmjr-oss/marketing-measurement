"""Reading a test more than once, and what it costs.

Wave 2 sized a geo holdout on one assumption it never stated: that the test is read **once**, at the
end. Nobody does that. A thirteen-week holdout sits on a dashboard that updates weekly, somebody
looks at it every Monday, and the test is declared the first time it clears the line.

That is not a small liberty. Reading a fixed-boundary test thirteen times takes its false-positive
rate from 5% to **21.4%** - so a channel that does nothing is declared a winner about one time in
five. The arithmetic of each individual look is correct. What is wrong is that the decision rule is
not the one the 1.96 was computed for, and the person taking it usually does not know a decision
rule is being used at all.

Three things this module does.

**It computes the real error rate exactly, rather than simulating it.** The recursion is
Armitage-McPherson-Rowe: propagate the density of the running sum forward through the continuation
region with Gauss-Legendre quadrature, look by look. It is deterministic, agrees with itself to six
decimal places at 100, 300 and 600 nodes, and reproduces the classical published boundaries. It is
also checked against a four-million-draw simulation, because a closed form that only agrees with
itself has been verified against nothing.

**It prices the two honest alternatives.** A boundary that holds the error rate at 5% across
thirteen weekly looks exists - two of them do, and they are different trades. Pocock's constant
boundary stops earlier and needs a **32%** bigger test; O'Brien and Fleming's declining boundary
needs only **4%** more but hardly ever stops in the first half. Neither is free and neither is
expensive in the way people assume.

**And it measures the part that a correct boundary does not fix.** Stopping early inflates the
effect you report, because you stopped on a favourable draw. At equal power, reading once overstates
a real effect by 12%, O'Brien-Fleming by 26%, Pocock by 48%, and peeking weekly at 1.96 by **72%**.
Repairing the error rate repairs the error rate. The estimate is still flattering, and it is
flattering in the same direction as everything else this repository measures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy import optimize, stats

from ..synth._draws import normal as normal_draws
from .geo import DEFAULT_ALPHA, DEFAULT_POWER

#: Quadrature nodes per look. The answer is stable to six decimals from 100 upwards; 300 is used so
#: that a figure published from this module does not depend on the setting, and the invariance is
#: asserted rather than assumed.
NODES = 300

#: Looks past this are refused. Not a numerical limit - a design with more than this many decision
#: points is a continuous monitoring problem, which needs a different tool than a boundary table.
MAX_LOOKS = 200

RULES = ("read-once", "naive", "pocock", "obrien-fleming")

PEEKING_COLUMNS = (
    "rule",
    "looks",
    "first_boundary",
    "last_boundary",
    "nominal_alpha_first",
    "nominal_alpha_last",
    "true_alpha",
    "valid",
    "information_inflation",
    "expected_looks",
)


def _validate(looks: int) -> None:
    if looks < 1:
        raise ValueError(f"a test is read at least once, got {looks}")
    if looks > MAX_LOOKS:
        raise ValueError(
            f"{looks} looks is continuous monitoring, not a boundary table; the limit here is "
            f"{MAX_LOOKS}"
        )


#: Cached results kept for the recursion and the two boundary solvers. They are pure functions of
#: hashable arguments, and the same boundary gets asked about several times over - its own size, its
#: validity, its power, its information cost. Without the cache the solvers dominate every run; with
#: it, nothing recomputes an answer it already has. The bound is generous rather than unlimited,
#: because a caller sweeping designs should not grow a cache without end. The boundary solvers are
#: cached for the same reason and it matters more for them: each runs a root finder per look, and
#: every evaluation inside that root finder runs the whole recursion.
CACHE_SIZE = 4_096


def equal_information(looks: int) -> tuple[float, ...]:
    """The information fractions of a test read at evenly spaced points.

    The assumption wave 3's boundaries are built on, written down so that departing from it is a
    choice rather than an oversight.
    """
    _validate(looks)
    return tuple((index + 1) / looks for index in range(looks))


def _checked_fractions(fractions: tuple[float, ...] | None, looks: int) -> tuple[float, ...]:
    """Validate information fractions, or supply the evenly spaced ones."""
    if fractions is None:
        return equal_information(looks)
    if len(fractions) != looks:
        raise ValueError(
            f"one information fraction per look: {len(fractions)} fractions for {looks} looks"
        )
    if any(later <= earlier for earlier, later in zip(fractions, fractions[1:], strict=False)):
        raise ValueError(f"information fractions must increase, got {fractions}")
    if fractions[0] <= 0.0:
        raise ValueError(f"the first information fraction must be positive, got {fractions[0]}")
    if fractions[-1] != 1.0:
        raise ValueError(f"the last look has all the information, got {fractions[-1]}")
    increments = [
        later - earlier for earlier, later in zip((0.0, *fractions), fractions, strict=False)
    ]
    smallest = min(increments)
    if smallest < MIN_INCREMENT:
        raise ValueError(
            f"look {increments.index(smallest) + 1} adds {smallest:.2e} of the information, below "
            f"the {MIN_INCREMENT:.0e} this recursion can resolve; two reads that close together "
            f"are one read"
        )
    return fractions


def _recursion(
    boundary: tuple[float, ...],
    drift: float,
    nodes: int,
    fractions: tuple[float, ...] | None,
    futility: tuple[float, ...] | None,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """The Armitage-McPherson-Rowe recursion, returning both ways out of the test.

    Information accumulates to ``looks`` by the last read, so the running sum at look ``k`` is
    normal with variance ``t_k`` and mean ``drift * t_k``, and the test continues while the
    standardised statistic stays inside its boundaries. The density of the sum restricted to the
    continuation region is carried forward look by look, which is the only way to get the joint
    probability right: the looks are not independent, because each one contains all the data of the
    ones before it.

    Returns:
        ``(rejected, stopped_for_futility)``, each cumulative by look. Without a futility boundary
        the second is all zeros and the first counts both tails, which is the two-sided test wave 3
        is built on. With one, the test is one-sided in the efficacy direction and the two together
        say how the probability left the continuation region.
    """
    _validate(len(boundary))
    if any(limit <= 0.0 for limit in boundary):
        raise ValueError("every critical value must be positive")
    looks = len(boundary)
    shares = _checked_fractions(fractions, looks)
    if futility is not None and len(futility) != looks:
        raise ValueError(f"one futility bound per look: {len(futility)} bounds for {looks} looks")

    information = [share * looks for share in shares]
    upper = [boundary[index] * np.sqrt(information[index]) for index in range(looks)]
    # The futility bound is a floor on the same statistic, so it scales the same way. Without one,
    # the floor is the mirror of the efficacy bound and leaving through it is a rejection.
    lower = (
        [futility[index] * np.sqrt(information[index]) for index in range(looks)]
        if futility is not None
        else [-value for value in upper]
    )
    for index in range(looks):
        # Equality is legitimate at the last look and nowhere else: a futility bound meeting the
        # efficacy bound there is what "the test ends, one way or the other" means, and the
        # recursion handles it - the continuation region collapses and all the surviving mass leaves
        # through one side or the other. Before the last look it would mean a test with nowhere to
        # continue to, which is a design error rather than a number to return.
        if lower[index] > upper[index] or (lower[index] == upper[index] and index != looks - 1):
            raise ValueError(
                f"the futility bound at look {index + 1} leaves no continuation region: "
                f"{futility[index] if futility else 0.0} against {boundary[index]}"
            )

    abscissa, quadrature = np.polynomial.legendre.leggauss(nodes)

    def region(index: int) -> tuple[np.ndarray, np.ndarray]:
        """Quadrature grid and weights over the continuation region at one look."""
        half = (upper[index] - lower[index]) / 2.0
        middle = (upper[index] + lower[index]) / 2.0
        return middle + half * abscissa, half * quadrature

    step = information[0]
    root = np.sqrt(step)
    grid, weights = region(0)
    density = stats.norm.pdf((grid - drift * step) / root) / root
    if futility is None:
        rejected = [1.0 - float(weights @ density)]
        futile = [0.0]
    else:
        rejected = [float(stats.norm.sf((upper[0] - drift * step) / root))]
        futile = [float(stats.norm.cdf((lower[0] - drift * step) / root))]

    for index in range(1, looks):
        step = information[index] - information[index - 1]
        root = np.sqrt(step)
        new_grid, new_weights = region(index)
        kernel = stats.norm.pdf((new_grid[:, None] - grid[None, :] - drift * step) / root) / root
        surviving = weights * density
        density = kernel @ surviving
        if futility is None:
            grid, weights = new_grid, new_weights
            rejected.append(1.0 - float(weights @ density))
            futile.append(0.0)
            continue
        # With a futility bound the mass leaving upwards has to be counted rather than inferred from
        # what is left, because mass also leaves downwards and that is not a rejection.
        standardised_up = (upper[index] - grid - drift * step) / root
        standardised_down = (lower[index] - grid - drift * step) / root
        rejected.append(rejected[-1] + float((stats.norm.sf(standardised_up) * surviving).sum()))
        futile.append(futile[-1] + float((stats.norm.cdf(standardised_down) * surviving).sum()))
        grid, weights = new_grid, new_weights

    return tuple(rejected), tuple(futile)


@lru_cache(maxsize=CACHE_SIZE)
def crossing_probability(
    boundary: tuple[float, ...],
    drift: float = 0.0,
    nodes: int = NODES,
    fractions: tuple[float, ...] | None = None,
    futility: tuple[float, ...] | None = None,
) -> tuple[float, ...]:
    """Cumulative probability of having rejected by each look.

    Args:
        boundary: Critical value on the standardised statistic at each look, one per look.
        drift: Mean increment per unit of information. Zero is the null; ``ncp / sqrt(looks)`` is an
            alternative whose final statistic has noncentrality ``ncp``.
        nodes: Gauss-Legendre nodes per look.
        fractions: Share of the total information available at each look, increasing and ending at
            one. ``None`` means evenly spaced, which is what wave 3's boundaries assume.
        futility: Optional lower boundary. Supplying one makes the test one-sided in the efficacy
            direction - see :func:`spending_boundary` for why that is the right pairing.

    Returns:
        The cumulative rejection probability after each look. The last entry is the overall size of
        the procedure under ``drift``: its false-positive rate when ``drift`` is zero, its power
        otherwise. With a futility boundary it is the probability of rejecting *and not having
        stopped for futility first*, which is what a procedure with both boundaries delivers.

    Raises:
        ValueError: If the boundary is empty, longer than :data:`MAX_LOOKS`, non-positive anywhere,
            or if the fractions or the futility boundary do not match it.
    """
    return _recursion(boundary, drift, nodes, fractions, futility)[0]


@lru_cache(maxsize=CACHE_SIZE)
def futility_probability(
    boundary: tuple[float, ...],
    futility: tuple[float, ...],
    drift: float = 0.0,
    nodes: int = NODES,
    fractions: tuple[float, ...] | None = None,
) -> tuple[float, ...]:
    """Cumulative probability of having stopped for futility by each look.

    Under the null this is mostly good news - the test ends early on a channel that is doing
    nothing. Under the alternative it is the power the futility bound costs, which is the number
    that decides whether the bound is worth having.

    Args:
        boundary: The efficacy boundary.
        futility: The futility boundary, one bound per look.
        drift: Mean increment per unit of information.
        nodes: Gauss-Legendre nodes per look.
        fractions: Information fraction at each look.

    Returns:
        The cumulative probability of having stopped for futility after each look.
    """
    return _recursion(boundary, drift, nodes, fractions, futility)[1]


def fixed_boundary(looks: int, alpha: float = DEFAULT_ALPHA) -> tuple[float, ...]:
    """The boundary somebody is using when they read the same test every week.

    It is the fixed-sample critical value, applied at every look, which is what a dashboard showing
    a p-value does whether or not anybody chose it.
    """
    _validate(looks)
    return (float(stats.norm.ppf(1.0 - alpha / 2.0)),) * looks


def inflated_alpha(looks: int, alpha: float = DEFAULT_ALPHA) -> float:
    """The real false-positive rate of a fixed boundary read ``looks`` times.

    Args:
        looks: Number of times the test is read.
        alpha: The significance level each individual look is judged at.

    Returns:
        The probability of rejecting at least once when nothing is happening.
    """
    return crossing_probability(fixed_boundary(looks, alpha))[-1]


@lru_cache(maxsize=CACHE_SIZE)
def pocock(looks: int, alpha: float = DEFAULT_ALPHA) -> tuple[float, ...]:
    """A constant boundary whose overall error rate is ``alpha``.

    The honest version of what the weekly reader is doing: the same critical value at every look,
    but the value that accounts for there being several. Every look has the same nominal level, so
    the test can stop as early as the first one.
    """
    _validate(looks)
    if looks == 1:
        return fixed_boundary(1, alpha)
    constant = float(
        optimize.brentq(
            lambda value: crossing_probability((value,) * looks)[-1] - alpha,
            stats.norm.ppf(1.0 - alpha / 2.0),
            10.0,
            xtol=1e-10,
        )
    )
    return (constant,) * looks


@lru_cache(maxsize=CACHE_SIZE)
def obrien_fleming(looks: int, alpha: float = DEFAULT_ALPHA) -> tuple[float, ...]:
    """A declining boundary whose overall error rate is ``alpha``.

    The critical value falls as the square root of the information accumulated, so the early looks
    are nearly impossible to cross and the final one is close to the fixed-sample value. It spends
    almost none of the error rate early, which is why it costs almost nothing in size - and why it
    will not stop a test in its first weeks however good the numbers look.
    """
    _validate(looks)
    if looks == 1:
        return fixed_boundary(1, alpha)
    constant = float(
        optimize.brentq(
            lambda value: (
                crossing_probability(
                    tuple(value * np.sqrt(looks / (index + 1)) for index in range(looks))
                )[-1]
                - alpha
            ),
            0.5,
            10.0,
            xtol=1e-10,
        )
    )
    return tuple(constant * float(np.sqrt(looks / (index + 1))) for index in range(looks))


#: Spending functions available to :func:`spending_boundary`. ``"obrien-fleming"`` and ``"pocock"``
#: are the Lan-DeMets functions whose boundaries approximate the two classical shapes; ``"power"``
#: is the family ``alpha * t ** rho``, which interpolates between them and is exposed so that the
#: shape is a dial rather than a choice between two names.
SPENDING = ("obrien-fleming", "pocock", "power")

#: A bound standing in for "this look cannot stop the test". Large enough that no path reaches it,
#: small enough to keep the quadrature grid sane.
UNREACHABLE = 50.0

#: Smallest share of the total information a single look may add.
#:
#: Not a convention - a measured limit of the method. The convolution kernel between two looks has
#: standard deviation equal to the square root of the information they are apart, so as that gap
#: shrinks the kernel narrows towards a spike that quadrature over a wide continuation region cannot
#: represent. Measured on a two-look test at the default node count, the error rate is smooth and
#: correct down to a gap of 2e-04 of the information and then collapses: at 1e-04 it is wrong by
#: 9e-03 and in the wrong direction, and at 1e-05 it returns -1.17, which is not a probability. The
#: floor here sits five times above the last good value, and it is generous in practice - reading a
#: thirteen-week test daily puts each look 0.011 apart, eleven times the floor.
MIN_INCREMENT = 1e-3

SCHEDULE_COLUMNS = (
    "look",
    "information",
    "alpha_spent",
    "alpha_this_look",
    "efficacy",
    "nominal_alpha",
    "futility",
    "beta_spent",
)


def alpha_spent(
    fraction: float,
    alpha: float = DEFAULT_ALPHA,
    family: str = "obrien-fleming",
    rho: float = 3.0,
) -> float:
    """How much of the error rate a spending function has committed by information ``fraction``.

    The Lan-DeMets insight, which is what makes a real monitoring plan possible: a boundary does not
    have to be chosen in advance for a fixed number of equally spaced looks. Commit instead to a
    function saying how much of the error rate may be spent by each point in the accumulation of
    information, and the boundary at each look follows from what has already been spent. The number
    and timing of the looks then do not have to be known when the test starts - which is the
    situation everybody is actually in.

    Args:
        fraction: Share of the total information, in ``(0, 1]``.
        alpha: Total error rate to spend.
        family: One of :data:`SPENDING`.
        rho: Exponent for the power family. Three is roughly O'Brien-Fleming-like, one is a linear
            spend that is more aggressive than Pocock.

    Returns:
        Cumulative error rate spent by ``fraction``.

    Raises:
        ValueError: If the fraction is outside ``(0, 1]``, or the family is unknown.
    """
    if not 0.0 < fraction <= 1.0:
        raise ValueError(f"an information fraction lies in (0, 1], got {fraction}")
    if family == "obrien-fleming":
        # The Lan-DeMets function whose boundary approximates O'Brien and Fleming's: it spends
        # almost nothing early and nearly everything at the end.
        return float(2.0 * stats.norm.sf(stats.norm.isf(alpha / 2.0) / math.sqrt(fraction)))
    if family == "pocock":
        return float(alpha * math.log(1.0 + (math.e - 1.0) * fraction))
    if family == "power":
        if rho <= 0:
            raise ValueError(f"the power family needs a positive exponent, got {rho}")
        return float(alpha * fraction**rho)
    raise ValueError(f"unknown spending function {family!r}; the families are {SPENDING}")


@lru_cache(maxsize=CACHE_SIZE)
def spending_boundary(
    fractions: tuple[float, ...],
    alpha: float = DEFAULT_ALPHA,
    family: str = "obrien-fleming",
    rho: float = 3.0,
) -> tuple[float, ...]:
    """The one-sided efficacy boundary implied by a spending function.

    Solved look by look: at each one, the critical value is whatever makes the cumulative
    probability of having rejected equal the error rate the function says may have been spent by
    then, *given the boundaries already fixed at the earlier looks*. That sequential construction is
    what lets the looks be unequally spaced.

    One-sided, unlike wave 3's boundaries, because this is the form that pairs with a futility
    bound: a holdout asks whether the channel helps, and the region where it appears to hurt is
    where futility belongs rather than where a rejection belongs. A one-sided ``alpha`` of 0.025 is
    the comparable setting to a two-sided 0.05.

    Args:
        fractions: Information fraction at each look, increasing and ending at one.
        alpha: One-sided error rate.
        family: One of :data:`SPENDING`.
        rho: Exponent for the power family.

    Returns:
        The critical value at each look.
    """
    looks = len(fractions)
    shares = _checked_fractions(fractions, looks)
    boundary: list[float] = []
    for index in range(looks):
        target = alpha_spent(shares[index], alpha, family, rho)

        def spent_with(value: float, index: int = index) -> float:
            candidate = tuple([*boundary, value] + [UNREACHABLE] * (looks - index - 1))
            futility = (-UNREACHABLE,) * looks
            return crossing_probability(candidate, fractions=shares, futility=futility)[index]

        # The bracket runs from a bound nothing can fail to cross to one nothing can reach. The
        # lower end is a small positive number rather than zero, because a critical value of zero
        # rejects half the paths at the first look and is not a boundary.
        def shortfall(value: float, target: float = target) -> float:
            return spent_with(value) - target

        boundary.append(
            float(optimize.brentq(shortfall, 1e-9, UNREACHABLE)) if target > 0.0 else UNREACHABLE
        )
    return tuple(boundary)


def nominal_alpha(boundary: tuple[float, ...]) -> tuple[float, ...]:
    """The two-sided p-value threshold each look corresponds to.

    The translation a practitioner needs: a boundary is abstract, "you may declare this on week
    three at p below 0.0084" is not.
    """
    return tuple(float(2.0 * stats.norm.sf(limit)) for limit in boundary)


def power(boundary: tuple[float, ...], ncp: float) -> float:
    """Probability of rejecting under an effect that a single final reading would see at ``ncp``.

    Args:
        boundary: The boundary.
        ncp: Noncentrality of the statistic at the **last** look - that is, the effect expressed the
            way a fixed-sample power calculation expresses it, so the two are comparable.

    Returns:
        The probability of crossing at some look.
    """
    return crossing_probability(boundary, drift=ncp / float(np.sqrt(len(boundary))))[-1]


def ncp_for_power(
    boundary: tuple[float, ...],
    target: float = DEFAULT_POWER,
) -> float:
    """The effect this boundary needs in order to reach ``target`` power.

    Raises:
        ValueError: If the target is not between the boundary's own size and one.
    """
    size = crossing_probability(boundary)[-1]
    if not size < target < 1.0:
        raise ValueError(
            f"power must be above this boundary's own size ({size:.4f}) and below one, got {target}"
        )
    return float(
        optimize.brentq(lambda value: power(boundary, value) - target, 1e-9, 40.0, xtol=1e-9)
    )


def information_inflation(
    boundary: tuple[float, ...],
    target: float = DEFAULT_POWER,
    alpha: float = DEFAULT_ALPHA,
) -> float:
    """How much bigger the test has to be, against reading it once.

    The price of being allowed to stop early, in the only currency a test has: information. Sample
    size scales with the square of the noncentrality, so this is the squared ratio of what the
    sequential boundary needs to what a single final reading needs.

    The single reading in the denominator is solved through the same recursion rather than taken
    from ``z_{1-a/2} + z_{power}``, so that a one-look boundary returns exactly one. Those two are
    not quite the same number: the textbook formula ignores the probability of rejecting in the
    *opposite* tail, which at 80% power and a 5% level is about one in a million, so it asks for a
    noncentrality 3.4e-06 too large. Nothing depends on that difference, and it is only worth
    knowing because a control case that returns 0.9999975 instead of 1 looks like a defect - and
    the fix for looking like a defect is to compute the reference the same way as the thing being
    compared to it, not to round the output.

    Args:
        boundary: The boundary.
        target: Power both designs are held to.
        alpha: Significance level the fixed-sample comparison is held to.

    Returns:
        A multiplier on the maximum information, at or above one.
    """
    fixed = ncp_for_power(fixed_boundary(1, alpha), target)
    return (ncp_for_power(boundary, target) / fixed) ** 2


def expected_looks(
    boundary: tuple[float, ...],
    ncp: float,
    futility: tuple[float, ...] | None = None,
    fractions: tuple[float, ...] | None = None,
) -> float:
    """Average number of looks before the test stops, counting the last one if it never does.

    The other half of the trade: a boundary that costs more information can still run for less time,
    because most of the time it stops before using all of it. With a futility boundary the test can
    also end by giving up, which is what shortens it when the channel is doing nothing.
    """
    drift = ncp / float(np.sqrt(len(boundary)))
    rejected = crossing_probability(boundary, drift=drift, fractions=fractions, futility=futility)
    abandoned = (
        futility_probability(boundary, futility, drift=drift, fractions=fractions)
        if futility is not None
        else (0.0,) * len(boundary)
    )
    total = 0.0
    previous = 0.0
    for index, (up, down) in enumerate(zip(rejected, abandoned, strict=True)):
        stopped = up + down
        total += (index + 1) * (stopped - previous)
        previous = stopped
    return total + len(boundary) * (1.0 - previous)


def beta_spent(
    fraction: float,
    beta: float,
    family: str = "obrien-fleming",
    rho: float = 3.0,
) -> float:
    """How much of the type II error a futility schedule has committed by ``fraction``.

    The same spending idea pointed at the other error. A conservative family spends almost none of
    it early, which means the test is not abandoned in week two on a bad first draw.
    """
    return alpha_spent(fraction, beta, family, rho)


@lru_cache(maxsize=CACHE_SIZE)
def futility_boundary(
    boundary: tuple[float, ...],
    ncp: float,
    fractions: tuple[float, ...] | None = None,
    beta: float = 1.0 - DEFAULT_POWER,
    family: str = "obrien-fleming",
    rho: float = 3.0,
) -> tuple[float, ...]:
    """A lower boundary that ends a test which is not going to succeed.

    Solved by beta spending under the alternative ``ncp``: at each look, the bound is whatever makes
    the cumulative probability of having abandoned the test equal the type II error the schedule
    says may have been spent by then. The final bound is set equal to the efficacy bound, because a
    test that reaches its last look without rejecting has failed and there is nothing left to
    continue into.

    What this buys is calendar, not conversions - and that is worth stating plainly, because the
    roadmap of this repository once claimed the opposite. Wave 2 showed the holdout's cost in
    conversions is the held-out population times the channel's real lift, so a channel doing
    nothing costs nothing to hold out. A futility bound fires precisely when the effect looks
    small, which is where the conversion cost is already near zero. What it saves is the weeks, the
    regions held back from a channel nobody can act on yet, and the decision that cannot be taken
    while the test runs.

    Args:
        boundary: The efficacy boundary this pairs with.
        ncp: Noncentrality of the alternative the test is powered for, at the final look.
        fractions: Information fraction at each look.
        beta: Total type II error to spend. The default is one minus :data:`DEFAULT_POWER`.
        family: One of :data:`SPENDING`.
        rho: Exponent for the power family.

    Returns:
        The futility bound at each look, on the standardised statistic. Values are typically
        negative early - no plausible first look should end a test - and rise to meet the efficacy
        bound.

    Raises:
        ValueError: If the alternative is not positive, since a futility bound is defined against an
            effect worth detecting.
    """
    if ncp <= 0:
        raise ValueError(f"a futility bound is defined against a real alternative, got ncp {ncp}")
    looks = len(boundary)
    shares = _checked_fractions(fractions, looks)
    drift = ncp / math.sqrt(looks)
    bounds: list[float] = []
    for index in range(looks - 1):
        target = beta_spent(shares[index], beta, family, rho)

        def abandoned(value: float, index: int = index) -> float:
            candidate = tuple([*bounds, value] + [-UNREACHABLE] * (looks - index - 1))
            return futility_probability(boundary, candidate, drift=drift, fractions=shares)[index]

        def shortfall(value: float, target: float = target) -> float:
            return abandoned(value) - target

        # The bracket spans a bound nothing can fall below up to just under the efficacy bound.
        # Just under, not at: a futility bound equal to the efficacy bound leaves no continuation
        # region at all, which is a design error rather than a root.
        ceiling = boundary[index] - 1e-6
        bounds.append(
            float(optimize.brentq(shortfall, -UNREACHABLE, ceiling))
            if target > 0.0
            else -UNREACHABLE
        )
    bounds.append(boundary[-1])
    return tuple(bounds)


@dataclass(frozen=True)
class SequentialPlan:
    """A rule for reading a test several times, and what it costs.

    Attributes:
        rule: Which boundary this is.
        boundary: Critical value at each look.
        alpha: The overall error rate the plan was built for.
        target_power: The power the costs are quoted at.
    """

    rule: str
    boundary: tuple[float, ...]
    alpha: float = DEFAULT_ALPHA
    target_power: float = DEFAULT_POWER

    @property
    def looks(self) -> int:
        """How many times the test is read."""
        return len(self.boundary)

    @property
    def true_alpha(self) -> float:
        """The plan's actual false-positive rate, whatever it was meant to be."""
        return crossing_probability(self.boundary)[-1]

    @property
    def valid(self) -> bool:
        """Whether the plan holds the error rate it claims.

        The naive rule does not, and this is the property that says so in one word.
        """
        return self.true_alpha <= self.alpha * (1.0 + 1e-6)

    @property
    def nominal_alphas(self) -> tuple[float, ...]:
        """The p-value threshold at each look."""
        return nominal_alpha(self.boundary)

    def verdict(self) -> str:
        """One line: what the plan really costs, or that it is not a plan."""
        if not self.valid:
            return (
                f"{self.rule}: {self.looks} looks at a fixed boundary gives a false-positive rate "
                f"of {self.true_alpha:.4f}, not {self.alpha:.4f}"
            )
        inflation = information_inflation(self.boundary, self.target_power, self.alpha)
        needed = ncp_for_power(self.boundary, self.target_power)
        return (
            f"{self.rule}: {self.looks} looks holding alpha at {self.true_alpha:.4f}, "
            f"{inflation - 1.0:+.1%} information, stops after "
            f"{expected_looks(self.boundary, needed):.2f} looks on average"
        )


@dataclass(frozen=True)
class MonitoringPlan:
    """A full monitoring plan: when to look, when to stop for success, when to give up.

    Every plan here is one-sided in the efficacy direction, and a plan that cannot give up carries
    a futility bound of ``-UNREACHABLE`` rather than ``None``. That is not decoration. In
    :func:`crossing_probability`, ``futility=None`` means the two-sided test wave 3 is built on, so
    a plan storing ``None`` for "no futility" reported an error rate of 0.0500 for a boundary solved
    to spend 0.025 - which is what the first version of this class did, and what
    :attr:`can_abandon` now exists to express instead.

    Attributes:
        fractions: Information fraction at each look.
        efficacy: Critical value at each look, one-sided.
        futility: Lower bound at each look. Unreachable bounds mean the test can only stop for
            success.
        alpha: One-sided error rate the efficacy boundary was built to spend.
        ncp: The alternative the plan is powered against, at the final look.
    """

    fractions: tuple[float, ...]
    efficacy: tuple[float, ...]
    futility: tuple[float, ...]
    alpha: float
    ncp: float

    @property
    def can_abandon(self) -> bool:
        """Whether any look in this plan can end the test for futility."""
        return any(bound > -UNREACHABLE for bound in self.futility)

    @property
    def looks(self) -> int:
        """How many times the test is read."""
        return len(self.efficacy)

    @property
    def drift(self) -> float:
        """Mean increment per unit of information under the alternative."""
        return self.ncp / math.sqrt(self.looks)

    @property
    def true_alpha(self) -> float:
        """The plan's actual one-sided error rate.

        Below :attr:`alpha` whenever a futility boundary is present, because the efficacy boundary
        is solved as though the test could never be abandoned. That is the **non-binding**
        convention and it is the point: a team that ignores the futility signal and keeps the test
        running has not broken the error rate, because the error rate never counted on them obeying
        it. The price of that insurance is the gap between the two numbers.
        """
        return crossing_probability(
            self.efficacy, drift=0.0, fractions=self.fractions, futility=self.futility
        )[-1]

    @property
    def power(self) -> float:
        """Probability of rejecting under the alternative, with the plan as it stands."""
        return crossing_probability(
            self.efficacy, drift=self.drift, fractions=self.fractions, futility=self.futility
        )[-1]

    @property
    def power_without_futility(self) -> float:
        """What the power would be if the test were never abandoned."""
        return crossing_probability(
            self.efficacy,
            drift=self.drift,
            fractions=self.fractions,
            futility=(-UNREACHABLE,) * self.looks,
        )[-1]

    @property
    def abandoned_under_null(self) -> float:
        """Probability of stopping for futility when nothing is happening.

        The plan working: a channel with no effect should not consume the whole calendar. A plan
        that cannot abandon returns essentially zero here without needing a special case, because
        its bound is unreachable rather than absent.
        """
        return futility_probability(
            self.efficacy, self.futility, drift=0.0, fractions=self.fractions
        )[-1]

    @property
    def abandoned_under_alternative(self) -> float:
        """Probability of abandoning a test that was going to succeed. The risk being bought."""
        return futility_probability(
            self.efficacy, self.futility, drift=self.drift, fractions=self.fractions
        )[-1]

    def expected_looks_under(self, ncp: float) -> float:
        """Average number of looks before this plan stops, at a given effect."""
        return expected_looks(self.efficacy, ncp, futility=self.futility, fractions=self.fractions)

    def information_to_restore_power(self, target: float = DEFAULT_POWER) -> float:
        """How much bigger the test must be to reach ``target`` power under this plan.

        A multiplier on information, comparable with :func:`information_inflation`. One means the
        plan already reaches the target; above one is what the futility bound costs in size, which
        is the honest price to put next to the calendar it saves.

        Raises:
            ValueError: If the target is not above the plan's own size and below one.
        """
        if not self.true_alpha < target < 1.0:
            raise ValueError(
                f"power must be above this plan's own size ({self.true_alpha:.4f}) and below one, "
                f"got {target}"
            )

        def achieved(ncp: float) -> float:
            return crossing_probability(
                self.efficacy,
                drift=ncp / math.sqrt(self.looks),
                fractions=self.fractions,
                futility=self.futility,
            )[-1]

        needed = float(optimize.brentq(lambda ncp: achieved(ncp) - target, 1e-9, 40.0, xtol=1e-9))
        return (needed / self.ncp) ** 2

    def verdict(self) -> str:
        """One line: what the plan costs and what it buys."""
        if not self.can_abandon:
            return (
                f"{self.looks} looks, alpha {self.true_alpha:.4f}, power {self.power:.4f}, "
                f"stops after {self.expected_looks_under(self.ncp):.2f} looks"
            )
        return (
            f"{self.looks} looks with futility: alpha {self.true_alpha:.4f}, power "
            f"{self.power:.4f} against {self.power_without_futility:.4f}, "
            f"{self.expected_looks_under(0.0):.2f} looks on a channel doing nothing against "
            f"{self.expected_looks_under(self.ncp):.2f} on one that works"
        )


def monitoring_plan(
    fractions: tuple[float, ...],
    ncp: float,
    alpha: float = DEFAULT_ALPHA,
    beta: float | None = 1.0 - DEFAULT_POWER,
    family: str = "obrien-fleming",
    rho: float = 3.0,
) -> MonitoringPlan:
    """Build a monitoring plan from a spending function and, optionally, a futility schedule.

    Args:
        fractions: Information fraction at each look, increasing and ending at one.
        ncp: The alternative to power against, at the final look.
        alpha: One-sided error rate.
        beta: Type II error to spend on futility, or ``None`` for a plan that can only stop for
            success.
        family: One of :data:`SPENDING`, for both schedules.
        rho: Exponent for the power family.

    Returns:
        A :class:`MonitoringPlan`.
    """
    efficacy = spending_boundary(fractions, alpha, family, rho)
    futility = (
        futility_boundary(efficacy, ncp, fractions, beta, family, rho)
        if beta is not None
        else (-UNREACHABLE,) * len(efficacy)
    )
    return MonitoringPlan(
        fractions=_checked_fractions(fractions, len(efficacy)),
        efficacy=efficacy,
        futility=futility,
        alpha=alpha,
        ncp=ncp,
    )


def schedule(built: MonitoringPlan) -> pd.DataFrame:
    """The plan as the table somebody has to be handed before the test starts.

    Every row is a decision the team agreed to in advance: at this much information, reject above
    this, give up below that. A monitoring plan that is not written down this way is not a plan - it
    is a dashboard and a habit.

    Args:
        built: The plan.

    Returns:
        A frame with the columns in :data:`SCHEDULE_COLUMNS`.
    """
    nominals = nominal_alpha(built.efficacy)
    spent = [alpha_spent(share, built.alpha) for share in built.fractions]
    rows = []
    for index, share in enumerate(built.fractions):
        rows.append(
            {
                "look": index + 1,
                "information": share,
                "alpha_spent": spent[index],
                "alpha_this_look": spent[index] - (spent[index - 1] if index else 0.0),
                "efficacy": built.efficacy[index],
                "nominal_alpha": nominals[index],
                "futility": built.futility[index] if built.can_abandon else float("nan"),
                "beta_spent": (
                    beta_spent(share, 1.0 - DEFAULT_POWER) if built.can_abandon else float("nan")
                ),
            }
        )
    return pd.DataFrame(rows)[list(SCHEDULE_COLUMNS)]


def plan(
    rule: str, looks: int, alpha: float = DEFAULT_ALPHA, power: float = DEFAULT_POWER
) -> SequentialPlan:
    """Build one of the plans in :data:`RULES`.

    Args:
        rule: One of :data:`RULES`. ``"read-once"`` is the single final reading, ``"naive"`` is the
            fixed boundary applied at every look - which is not a valid plan and is included
            because it is the one in use.
        looks: Number of readings.
        alpha: Overall error rate intended.
        power: Power the costs are quoted at.

    Returns:
        A :class:`SequentialPlan`.

    Raises:
        ValueError: If the rule is unknown.
    """
    if rule == "read-once":
        boundary = fixed_boundary(1, alpha)
    elif rule == "naive":
        boundary = fixed_boundary(looks, alpha)
    elif rule == "pocock":
        boundary = pocock(looks, alpha)
    elif rule == "obrien-fleming":
        boundary = obrien_fleming(looks, alpha)
    else:
        raise ValueError(f"unknown rule {rule!r}; the rules are {RULES}")
    return SequentialPlan(rule=rule, boundary=boundary, alpha=alpha, target_power=power)


def peeking_table(
    looks: int,
    alpha: float = DEFAULT_ALPHA,
    target_power: float = DEFAULT_POWER,
    rules: tuple[str, ...] = RULES,
) -> pd.DataFrame:
    """The four rules side by side: what each one costs and whether it is valid.

    Args:
        looks: Number of readings the sequential rules are built for.
        alpha: Overall error rate intended.
        target_power: Power the costs are quoted at.
        rules: Which rules to include.

    Returns:
        A frame with the columns in :data:`PEEKING_COLUMNS`.
    """
    rows = []
    for rule in rules:
        built = plan(rule, looks, alpha, target_power)
        nominals = built.nominal_alphas
        valid = built.valid
        rows.append(
            {
                "rule": rule,
                "looks": built.looks,
                "first_boundary": built.boundary[0],
                "last_boundary": built.boundary[-1],
                "nominal_alpha_first": nominals[0],
                "nominal_alpha_last": nominals[-1],
                "true_alpha": built.true_alpha,
                "valid": valid,
                "information_inflation": (
                    information_inflation(built.boundary, target_power, alpha)
                    if valid
                    else float("nan")
                ),
                "expected_looks": (
                    expected_looks(built.boundary, ncp_for_power(built.boundary, target_power))
                    if valid
                    else expected_looks(
                        built.boundary,
                        ncp_for_power(fixed_boundary(1, alpha), target_power),
                    )
                ),
            }
        )
    return pd.DataFrame(rows)[list(PEEKING_COLUMNS)]


def exaggeration(
    boundary: tuple[float, ...],
    ncp: float,
    draws: int = 200_000,
    seed: int = 11,
) -> dict[str, float]:
    """How much bigger the reported effect is than the real one, when the test is stopped.

    The part a correct boundary does not repair. A test stops early because the data came in
    favourably, so the estimate at the stopping point is drawn from the favourable tail. Reading
    once and publishing only the significant result does this too, in smaller measure: the estimate
    is unbiased, the *published* estimate is not.

    Simulated rather than integrated: the conditional expectation of the estimate at a random
    stopping time has no closed form worth the algebra, and a seeded simulation of it is
    reproducible to the same standard as everything else here - which means through
    :mod:`mktlab.synth._draws`, so that the figure does not move with a library version.

    Args:
        boundary: The boundary.
        ncp: Noncentrality at the last look, as in :func:`power`.
        draws: Simulated tests.
        seed: Seed, so the figure is reproducible.

    Returns:
        ``power``, ``ratio`` (reported effect over true effect, given rejection),
        ``expected_looks`` and ``same_sign`` (the share of rejections that get the direction right).

    Raises:
        ValueError: If the effect is not positive, since the ratio divides by it.
    """
    if ncp <= 0:
        raise ValueError(f"the exaggeration ratio is relative to a real effect, got ncp {ncp}")
    looks = len(boundary)
    drift = ncp / float(np.sqrt(looks))
    rng = np.random.default_rng(seed)
    # Inverse transform rather than the library's normal, for the reason in mktlab.synth._draws: a
    # rejection sampler makes a published figure depend on the library version.
    increments = drift + normal_draws(rng, (draws, looks))
    running = np.cumsum(increments, axis=1)
    index = np.arange(1, looks + 1)
    limits = np.asarray(boundary) * np.sqrt(index)

    crossed = np.abs(running) >= limits
    rejected = crossed.any(axis=1)
    stopped_at = np.where(rejected, crossed.argmax(axis=1), looks - 1)
    estimate = (running / index)[np.arange(draws), stopped_at]
    reported = estimate[rejected]
    return {
        "power": float(rejected.mean()),
        "ratio": float(reported.mean() / drift),
        "expected_looks": float((stopped_at + 1).mean()),
        "same_sign": float(np.mean(np.sign(reported) == np.sign(drift))),
    }
