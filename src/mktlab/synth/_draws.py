"""Every random draw in the package, and the one rule they all follow.

**Nothing here samples by rejection.** Each draw is an inverse transform of the uniform stream, so
the number of uniforms consumed depends only on how many values are asked for - never on the values
themselves.

That is not a stylistic preference, it is the repository's central promise made true. A rejection
sampler - which is what a library's ``binomial`` or ``beta`` method usually is - consumes a variable
number of uniforms per draw, so the *position* in the stream after it depends on the sampler's
internal details. Change library version, change the internals, and every draw after that point is
different. The published figures then hold only for the exact library the author happened to have.

This was not hypothetical, and the evidence is worth stating precisely because the conclusion is
inferred rather than demonstrated. The first version of this generator drew the geo panels with
``Generator.binomial``. Its published figures held on the author's machine and failed on a clean
install: the attribution tables, which touch no rejection sampler, matched to the last decimal
while every figure downstream of the binomial moved. The two environments differed in one relevant
way, the numpy version, and the newer one could not be installed on the interpreter available for
testing, so the divergence was never reproduced side by side. A rejection sampler's stream
consumption is the mechanism that fits the evidence; it is not a mechanism that was observed.

Which is reason enough. The fix removes the whole class rather than the one instance, and it is
cheap: what remains is the bit generator's uniform stream, which numpy guarantees, and the
accuracy of two quantile functions, where a difference of 1e-16 moves a rate by 1e-16 instead of
shifting every draw that follows. ``tests/test_synth.py`` enforces the rule against the source,
because a rule nothing checks is a rule that lasts until the next module.
"""

from __future__ import annotations

import numpy as np
from scipy import stats


def uniform(rng: np.random.Generator, size: int | tuple[int, ...]) -> np.ndarray:
    """Uniforms in the shape asked for - the only primitive anything here may consume."""
    return rng.random(size)


def normal(rng: np.random.Generator, size: int | tuple[int, ...], sd: float = 1.0) -> np.ndarray:
    """Normal draws by inverse transform, in place of ``Generator.normal``.

    ``Generator.standard_normal`` is the ziggurat algorithm, which rejects, so it belongs to the
    same class of hazard as the binomial this module was written for.
    """
    return np.asarray(stats.norm.ppf(uniform(rng, size)) * sd, dtype=float)


def beta(rng: np.random.Generator, size: int, alpha: float, beta_shape: float) -> np.ndarray:
    """Beta draws by inverse transform, in place of ``Generator.beta``."""
    return np.asarray(stats.beta.ppf(uniform(rng, size), alpha, beta_shape), dtype=float)


def bernoulli(rng: np.random.Generator, probability: np.ndarray) -> np.ndarray:
    """One Bernoulli trial per element of ``probability``."""
    return uniform(rng, probability.size) < probability


def binomial(rng: np.random.Generator, trials: int, probability: float) -> int:
    """Successes in ``trials`` trials, counted from ``trials`` uniforms.

    Deliberately the expensive way round. A library binomial draws this in roughly constant time by
    rejection; this one spends one uniform per trial so that the stream position afterwards is
    ``trials``, always. The whole geo panel costs about ten million uniforms, which takes under a
    second - a price worth paying for figures that reproduce on somebody else's machine.
    """
    return int(np.count_nonzero(uniform(rng, trials) < probability))


def order_of(rng: np.random.Generator, size: int) -> np.ndarray:
    """A random permutation of ``range(size)``, in place of ``Generator.permutation``.

    Sorting uniform keys rather than shuffling in place: the keys are one uniform each, and
    ``argsort`` is deterministic.
    """
    return np.argsort(uniform(rng, size))
