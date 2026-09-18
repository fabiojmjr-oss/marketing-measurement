"""Using the experiment and the model together, and pricing what that costs.

:mod:`~mktlab.calibration.transfer` puts a geo holdout's estimate into a media mix model as a prior
on the coefficient and reports what the transfer did. Three things it is built to make visible.

**The two instruments estimate different quantities.** A holdout measures the average return over
the period; a coefficient is the marginal return at current spend. The factor between them is
``1 + 1/k`` in the saturation point ``k`` - a closed form, and an uncomfortable one, because wave 5
established that the fit is nearly blind to ``k``.

**Precision and bias transfer with equal efficiency.** The posterior narrows whether or not the
prior is centred correctly, so a skipped conversion buys a tighter interval around a wrong
number.

**And a prior on one channel is not a claim about one channel.** The spend columns correlate above
0.83, so pinning one coefficient moves the others - which is how an experiment covering three
channels of five reaches all five.

The holdout is in :mod:`mktlab.attribution`, the model in :mod:`mktlab.mmm`, and the truth both are
judged against in :mod:`mktlab.synth`.
"""

from .transfer import (
    CALIBRATION_COLUMNS,
    TRANSFER_COLUMNS,
    Calibrated,
    Prior,
    average_to_marginal,
    calibrate,
    prior_from_holdout,
    saturation_multiple,
)

__all__ = [
    "CALIBRATION_COLUMNS",
    "TRANSFER_COLUMNS",
    "Calibrated",
    "Prior",
    "average_to_marginal",
    "calibrate",
    "prior_from_holdout",
    "saturation_multiple",
]
