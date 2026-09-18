"""Putting the experiment's answer into the model, and pricing what that does.

Waves 2 to 5 end in a choice nobody wants to make. The holdout answers narrowly about the channels
it covered and costs conversions; the model answers about every channel and, on this account under
the best conditions it will ever get, eleven to thirteen times more widely. The construction that
avoids the choice is to use both: the experiment's estimate enters the model as a prior on the
coefficient, and the data updates it.

That is what a commercial media mix model does when it is done well, and it works. The three things
this module exists to make arithmetic are the three that get left out of the sentence describing it.

**The two instruments do not estimate the same quantity.** A holdout switches a channel off, so it
measures the *average* return over the period. A regression coefficient is a local slope, so it
estimates the *marginal* return at current spend. Where the response bends, those differ by a factor
this module derives in closed form - and the factor depends on the saturation point, which wave 5
established the fit is nearly blind to. **The bridge between the experiment and the model is a
parameter the data cannot identify.**

**The experiment cannot enter the model except through the model's assumptions.** The prior is on a
coefficient, and a coefficient only means a return after the carryover and the saturation point have
been assumed. So the experiment's clean number is converted by two guesses before it lands.

**And precision and bias transfer with equal efficiency.** A prior tightens the posterior whether or
not it is centred in the right place. Skip the average-to-marginal conversion and the interval
narrows around a value that is wrong by the factor that was skipped, which reads on a chart exactly
like a better model.

What this module is not: a Bayesian hierarchical media mix model. It is the conjugate normal update
with the residual variance plugged in from the least squares fit - the smallest construction that
makes the transfer visible. The uncertainty in that plug-in is not propagated, and that limitation
is stated in the README rather than hidden here.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from mktlab.attribution import GeoLift
from mktlab.mmm import DEFAULT_ALPHA, Fit, design_matrix, fit
from mktlab.synth import MEDIA_MIX, MediaMixProfile

#: Columns of the table that compares an estimate before and after the experiment enters it.
CALIBRATION_COLUMNS = (
    "channel",
    "prior_mean",
    "prior_width",
    "model_mean",
    "model_width",
    "posterior_mean",
    "posterior_width",
    "width_kept",
)

#: Columns of the table that prices what the transfer did to the answers a budget acts on.
TRANSFER_COLUMNS = (
    "channel",
    "posterior_return",
    "low",
    "high",
    "truth",
    "covers_truth",
    "times_the_truth",
    "interval_width_over_truth",
    "resolved",
)


def average_to_marginal(saturation_multiple: float) -> float:
    """How many times the average return over a period exceeds the marginal return at that spend.

    The bridge between the two instruments, and it has a closed form. With a Michaelis-Menten
    response ``f(x) = x / (x + h)``, the average return per unit of spend at level ``x`` is
    ``f(x) / x = 1 / (x + h)`` and the marginal return is ``f'(x) = h / (x + h)**2``. Their ratio is
    ``(x + h) / h``, so writing the half point as a multiple ``k`` of the spend level itself gives

        average / marginal = (x + k*x) / (k*x) = 1 + 1/k

    which depends on nothing but ``k``. Two consequences worth stating in the same breath. It is why
    the ratio is identical for every channel in this generator - they were all given the same
    multiple - and it is why the conversion is not free: ``k`` is the saturation point, which wave 5
    established sits within 0.0008 of the best fit anywhere between 0.5 and 10.0. Over that range
    this factor runs from 3.0 to 1.1.

    Args:
        saturation_multiple: The half point as a multiple of the spend level, ``k``.

    Returns:
        The factor, always above one, by which the average return exceeds the marginal one.

    Raises:
        ValueError: If the multiple is not positive. A half point at or below zero is not a bending
            response, and returning a number for it would be inventing one.
    """
    if saturation_multiple <= 0:
        raise ValueError(
            f"the saturation multiple must be positive, got {saturation_multiple}; a half point at "
            f"zero is not a response curve"
        )
    return 1.0 + 1.0 / saturation_multiple


def saturation_multiple(fitted: Fit, index: int) -> float:
    """The saturation point one fit assumed, as a multiple of steady-state spend.

    Recovered from the fit rather than passed in again, because the conversion has to use the
    model's own assumption. An experiment's number converted with a different saturation point than
    the model was fitted with is two models' worth of assumptions in one estimate.
    """
    steady = fitted.spend_per_week[index] / (1.0 - fitted.carryover)
    return fitted.half_points[index] / steady


@dataclass(frozen=True)
class Prior:
    """What the experiment says about one coefficient, on the coefficient's own scale.

    Attributes:
        channel: The channel.
        mean: Prior mean for the coefficient.
        standard_error: Prior standard error. Larger is a weaker claim; infinity is no claim at all
            and leaves the coefficient at its least squares value.
        average_return: The average return the experiment measured, before any conversion.
        marginal_return: The marginal return that was converted from it, which is what the
            coefficient is about.
        conversion_factor: The factor the conversion used, or 1.0 where none was applied.
        source: One line naming where the number came from and what was assumed to move it.
        refused_because: Empty when the prior is usable. Otherwise the reason it is not, in which
            case the mean and error are ``nan`` and :func:`calibrate` leaves the channel alone.
    """

    channel: str
    mean: float
    standard_error: float
    average_return: float
    marginal_return: float
    conversion_factor: float
    source: str
    refused_because: str = ""

    @property
    def usable(self) -> bool:
        """Whether this prior carries a claim a posterior can use."""
        return not self.refused_because and math.isfinite(self.mean)


def prior_from_holdout(
    lift: GeoLift,
    fitted: Fit,
    channel: str,
    reach: float,
    spend: float,
    convert: bool = True,
) -> Prior:
    """Turn one geo holdout into a prior on one channel's coefficient.

    The whole chain, with every step named: the holdout's lift is a rate per user, so it becomes
    conversions when multiplied by the population and a return when divided by the spend. That
    return is an average over the period, so it is divided by :func:`average_to_marginal` to become
    the marginal return a coefficient estimates. And a marginal return is a coefficient only after
    division by the model's chain-rule factor, which depends on the two transforms the model
    guessed.

    Args:
        lift: The holdout result.
        fitted: The fit whose coefficient this prior is about, for the transforms it assumed.
        channel: Which channel, which must be one the fit has a column for.
        reach: Users the channel runs against over the period.
        spend: Money put into the channel over the same period.
        convert: Whether to apply the average-to-marginal conversion. ``False`` is the naive
            calibration - the experiment's number used as though a coefficient estimated it - and it
            exists here so that its cost can be measured rather than asserted.

    Returns:
        A :class:`Prior`. Where the holdout could not be tested at all, or the spend is zero, the
        prior is refused with the reason attached instead of carrying a number that reads like one.

    Raises:
        ValueError: If the channel is not one of the fit's columns, or the spend is negative.
    """
    if channel not in fitted.channels:
        raise ValueError(f"{channel!r} is not a channel of this fit: {fitted.channels}")
    if spend < 0:
        raise ValueError(f"spend cannot be negative, got {spend}")
    index = fitted.channels.index(channel)
    nothing = float("nan")

    if lift.untested_because:
        return Prior(
            channel=channel,
            mean=nothing,
            standard_error=nothing,
            average_return=nothing,
            marginal_return=nothing,
            conversion_factor=nothing,
            source="geo holdout",
            refused_because=f"the holdout was not a test: {lift.untested_because}",
        )
    if spend == 0:
        return Prior(
            channel=channel,
            mean=nothing,
            standard_error=nothing,
            average_return=nothing,
            marginal_return=nothing,
            conversion_factor=nothing,
            source="geo holdout",
            refused_because="a return needs a denominator and this channel's spend is zero",
        )

    average = lift.incremental_conversions(reach) / spend
    average_error = lift.standard_error * reach / spend
    factor = average_to_marginal(saturation_multiple(fitted, index)) if convert else 1.0
    marginal = average / factor
    marginal_error = average_error / factor
    chain = fitted.marginal_factor(index)
    source = (
        f"geo holdout on {lift.holdout_geos} of {lift.holdout_geos + lift.treated_geos} regions; "
        f"average return divided by {factor:.4f} to reach the marginal one"
        if convert
        else f"geo holdout on {lift.holdout_geos} of {lift.holdout_geos + lift.treated_geos} "
        f"regions; average return used as the marginal one, unconverted"
    )
    return Prior(
        channel=channel,
        mean=marginal / chain,
        standard_error=marginal_error / chain,
        average_return=average,
        marginal_return=marginal,
        conversion_factor=factor,
        source=source,
    )


@dataclass(frozen=True)
class Calibrated:
    """A model after the experiment entered it, next to the same model before.

    Attributes:
        baseline: The least squares fit the priors were applied to.
        posterior: The same fit with the posterior coefficients, errors and in-sample fit, so every
            table the least squares fit can produce is available for the calibrated one on the same
            terms.
        priors: The priors that were used, by channel. A channel absent from this mapping, or
            present with a refusal, kept its least squares estimate exactly.
        independent_widths: What each posterior interval would have been had precisions simply
            added, channel by channel. It is not a loose comparison: with a prior on exactly one
            channel it equals that channel's posterior width **exactly**, by Sherman-Morrison, no
            matter how collinear the design is. With priors on several channels it is an upper bound
            on every width, because adding prior precision to the information matrix can only
            shrink the diagonal of its inverse. The gap is precision arriving through the
            correlation between channels, which is small here - and the same correlation moves the
            other channels' point estimates a great deal, which is the part nobody checks.
    """

    baseline: Fit
    posterior: Fit
    priors: Mapping[str, Prior]
    independent_widths: Mapping[str, float]

    def table(self) -> pd.DataFrame:
        """One row per channel: the two claims that went in and the one that came out.

        Widths are full interval widths on the coefficient scale, so they are comparable down the
        column. ``width_kept`` is the posterior width as a share of the least squares width, which
        is the number to read: 1.00 is a prior that changed nothing and 0.10 is one doing nine
        tenths of the work.
        """
        critical = self.baseline.critical_value
        rows = []
        for index, channel in enumerate(self.baseline.channels):
            prior = self.priors.get(channel)
            model_width = 2.0 * critical * float(self.baseline.standard_errors[index])
            posterior_width = 2.0 * critical * float(self.posterior.standard_errors[index])
            usable = prior.usable if prior is not None else False
            rows.append(
                {
                    "channel": channel,
                    "prior_mean": prior.mean if prior is not None and usable else float("nan"),
                    "prior_width": (
                        2.0 * critical * prior.standard_error
                        if prior is not None and usable
                        else float("nan")
                    ),
                    "model_mean": float(self.baseline.coefficients[index]),
                    "model_width": model_width,
                    "posterior_mean": float(self.posterior.coefficients[index]),
                    "posterior_width": posterior_width,
                    "width_kept": posterior_width / model_width,
                }
            )
        return pd.DataFrame(rows)[list(CALIBRATION_COLUMNS)]

    def transfer(self, truth: pd.DataFrame) -> pd.DataFrame:
        """The posterior as the returns a budget acts on, judged against the declared truth.

        Args:
            truth: Frame with ``channel`` and ``marginal_conversions_per_unit_spend``.

        Returns:
            A frame with the columns in :data:`TRANSFER_COLUMNS`. ``resolved`` is whether the
            interval excludes zero, which is the only column a budget can act on without a truth
            column beside it.
        """
        returns = self.posterior.returns(truth)
        resolved = [
            bool(low > 0 or high < 0)
            for low, high in zip(returns["low"], returns["high"], strict=True)
        ]
        out = returns.rename(columns={"marginal_return": "posterior_return"}).copy()
        out["resolved"] = resolved
        return out[list(TRANSFER_COLUMNS)]


def _prior_precision(
    fitted: Fit, priors: Mapping[str, Prior], columns: int
) -> tuple[np.ndarray, np.ndarray]:
    """Prior precision and prior mean for every column of the design, intercept first.

    Columns with no usable prior get a precision of exactly zero, which is a flat prior and leaves
    them to the data. Returning the precision rather than the variance is what makes that
    expressible: there is no variance that means "no claim", but there is a precision.
    """
    precision = np.zeros(columns, dtype=float)
    means = np.zeros(columns, dtype=float)
    for index, channel in enumerate(fitted.channels):
        prior = priors.get(channel)
        if prior is None or not prior.usable:
            continue
        if prior.standard_error <= 0:
            raise ValueError(
                f"the prior on {channel} has a standard error of {prior.standard_error}, which "
                f"claims the experiment measured the coefficient exactly"
            )
        precision[index + 1] = 1.0 / prior.standard_error**2
        means[index + 1] = prior.mean
    return precision, means


def calibrate(
    panel: pd.DataFrame,
    priors: Mapping[str, Prior],
    carryover: float = MEDIA_MIX.adstock,
    saturation_at: float = MEDIA_MIX.saturation_at,
    design: MediaMixProfile = MEDIA_MIX,
    trend: bool = True,
    seasonality: bool = True,
    alpha: float = DEFAULT_ALPHA,
    response: str = "conversions",
) -> Calibrated:
    """Fit the model, then update it with what the experiment established.

    The conjugate normal update, in the form that makes the arithmetic legible: with the residual
    variance held at its least squares estimate, the posterior precision is the sum of the model's
    precision and the prior's, and the posterior mean is the precision-weighted average of the two
    claims,

        V = (X'X / s2 + P)^-1,   b = V (X'y / s2 + P m)

    where ``P`` is diagonal and zero for every column the experiment says nothing about. Two things
    follow that the wave exists to show. The posterior is narrower than least squares whether or not
    the prior is right, because precision adds without regard to location. And because the channels
    are correlated, a prior on one of them narrows and moves the others - so an experiment covering
    three channels of five is not an answer about three channels.

    Args:
        panel: The weekly panel.
        priors: Priors by channel. Channels absent from it keep their least squares estimate.
        carryover: Adstock the model assumes.
        saturation_at: Saturation half point the model assumes.
        design: The panel's declared shape.
        trend: Whether to include a linear trend.
        seasonality: Whether to include the seasonal pair.
        alpha: Significance level of the intervals.
        response: Column holding conversions.

    Returns:
        A :class:`Calibrated`.

    Raises:
        ValueError: If a prior claims a standard error of zero, which is an experiment claiming to
            have measured a coefficient exactly.
    """
    baseline = fit(
        panel,
        carryover=carryover,
        saturation_at=saturation_at,
        design=design,
        trend=trend,
        seasonality=seasonality,
        alpha=alpha,
        response=response,
    )
    matrix, _, _, _ = design_matrix(panel, carryover, saturation_at, design, trend, seasonality)
    target = np.asarray(panel[response], dtype=float)
    full = np.column_stack([np.ones(matrix.shape[0]), matrix])

    variance = baseline.residual_sd**2
    precision, means = _prior_precision(baseline, priors, full.shape[1])
    information = full.T @ full / variance + np.diag(precision)
    covariance = np.linalg.inv(information)
    coefficients = covariance @ (full.T @ target / variance + precision * means)
    errors = np.sqrt(np.diag(covariance))

    residuals = target - full @ coefficients
    residual_ss = float(residuals @ residuals)
    centred = target - target.mean()
    channels = len(baseline.channels)
    posterior = Fit(
        names=baseline.names,
        channels=baseline.channels,
        coefficients=coefficients[1 : channels + 1],
        intercept=float(coefficients[0]),
        standard_errors=errors[1 : channels + 1],
        df=baseline.df,
        r_squared=1.0 - residual_ss / float(centred @ centred),
        residual_sd=math.sqrt(residual_ss / baseline.df),
        condition_number=baseline.condition_number,
        vif=baseline.vif,
        carryover=baseline.carryover,
        half_points=baseline.half_points,
        spend_per_week=baseline.spend_per_week,
        alpha=baseline.alpha,
    )

    # What each interval would have been had the channels been uncorrelated: precisions add, so the
    # width follows from the two standard errors alone. Where the posterior comes back narrower than
    # this, the extra came through the correlation with a channel that did get a prior.
    critical = baseline.critical_value
    independent: dict[str, float] = {}
    for index, channel in enumerate(baseline.channels):
        own = 1.0 / float(baseline.standard_errors[index]) ** 2
        prior = priors.get(channel)
        if prior is not None and prior.usable:
            own += 1.0 / prior.standard_error**2
        independent[channel] = 2.0 * critical / math.sqrt(own)
    return Calibrated(
        baseline=baseline, posterior=posterior, priors=priors, independent_widths=independent
    )
