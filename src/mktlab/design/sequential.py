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

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy import optimize, stats

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
#: because a caller sweeping designs should not grow a cache without end.
CACHE_SIZE = 4_096


@lru_cache(maxsize=CACHE_SIZE)
def crossing_probability(
    boundary: tuple[float, ...],
    drift: float = 0.0,
    nodes: int = NODES,
) -> tuple[float, ...]:
    """Cumulative probability of having crossed the boundary by each look.

    The Armitage-McPherson-Rowe recursion. Increments are independent with mean ``drift`` and unit
    variance, so the running sum after ``k`` looks is normal with mean ``k * drift`` and variance
    ``k``, and the test continues while the standardised statistic stays inside ``boundary[k]``. The
    density of the sum restricted to the continuation region is carried forward look by look, which
    is the only way to get the joint probability right: the looks are not independent, because each
    one contains all the data of the ones before it.

    Args:
        boundary: Critical value on the standardised statistic at each look, one per look. Equal
            information between looks is assumed.
        drift: Mean of each increment, in standard errors of a single look. Zero is the null.
        nodes: Gauss-Legendre nodes per look.

    Returns:
        The cumulative rejection probability after each look. The last entry is the overall size of
        the procedure under ``drift``, which is its false-positive rate when ``drift`` is zero and
        its power otherwise.

    Raises:
        ValueError: If the boundary is empty, longer than :data:`MAX_LOOKS`, or non-positive
            anywhere.
    """
    _validate(len(boundary))
    if any(limit <= 0.0 for limit in boundary):
        raise ValueError("every critical value must be positive")

    limits = [boundary[index] * np.sqrt(index + 1) for index in range(len(boundary))]
    abscissa, quadrature = np.polynomial.legendre.leggauss(nodes)

    grid = limits[0] * abscissa
    weights = limits[0] * quadrature
    density = stats.norm.pdf(grid - drift)
    cumulative = [1.0 - float(weights @ density)]

    for index in range(1, len(boundary)):
        new_grid = limits[index] * abscissa
        new_weights = limits[index] * quadrature
        # The density of the sum at this look is the previous one convolved with a single increment,
        # integrated only over the region where the test had not already stopped.
        kernel = stats.norm.pdf(new_grid[:, None] - grid[None, :] - drift)
        density = kernel @ (weights * density)
        grid, weights = new_grid, new_weights
        cumulative.append(1.0 - float(weights @ density))

    return tuple(cumulative)


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


def expected_looks(boundary: tuple[float, ...], ncp: float) -> float:
    """Average number of looks before the test stops, counting the last one if it never does.

    The other half of the trade: a boundary that costs more information can still run for less time,
    because most of the time it stops before using all of it.
    """
    cumulative = crossing_probability(boundary, drift=ncp / float(np.sqrt(len(boundary))))
    total = 0.0
    previous = 0.0
    for index, value in enumerate(cumulative):
        total += (index + 1) * (value - previous)
        previous = value
    return total + len(boundary) * (1.0 - previous)


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
    reproducible to the same standard as everything else here.

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
    increments = drift + rng.standard_normal((draws, looks))
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
