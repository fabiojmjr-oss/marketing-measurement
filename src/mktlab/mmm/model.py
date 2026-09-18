"""Fitting a media mix model, and reading what it can and cannot support.

A media mix model is the instrument people reach for when nobody will pay for a holdout. It is a
regression of weekly conversions on transformed weekly spend, and everything difficult about it is
already visible in that sentence.

**The channels move together, so the model cannot separate them.** Media plans are written as shares
of a budget, so the columns of the design matrix are nearly the same column. The regression still
returns a coefficient per channel - it always does - and the standard error beside it is the model
saying it could not tell them apart. That standard error is the whole finding and it is the column
that gets dropped when the chart is drawn.

**The transforms are guesses.** How much of a week's spend carries into the following weeks, and
where
returns start to bend, are not observed. They are chosen by whoever fits the model, usually by
picking
whatever fits best - and a grid of very different choices fits almost identically while implying
returns that differ by a factor of several.

**And the coefficient is a local slope.** Response saturates, so what the regression estimates is
the
derivative at the spend level the channel happens to be running at, not a return that holds at twice
the budget. Reporting it as a return on the whole spend is a category error that the arithmetic here
makes visible.

What this module is not: a Bayesian hierarchical model with priors, which is what a commercial media
mix model usually is. The pathologies are the same - collinearity that shows up as inflated standard
errors here shows up as posterior correlation there, and a prior that resolves it is an assumption
doing the work the data cannot - and ordinary least squares makes them arithmetic rather than
diagnostics. That choice is stated in the module's README rather than hidden.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from mktlab.synth import CHANNELS, MEDIA_MIX, MediaMixProfile, adstock, saturate

DEFAULT_ALPHA = 0.05

#: A column whose residual against the others falls below this share of its own variation is treated
#: as an exact combination of them. Perfect collinearity leaves a numerically tiny residual rather
#: than a zero, and reporting a variance inflation of 1e30 for it is arithmetic, not an answer.
COLLINEAR_TOLERANCE = 1e-12

#: Columns of the coefficient table.
FIT_COLUMNS = (
    "channel",
    "coefficient",
    "standard_error",
    "t",
    "p_value",
    "low",
    "high",
    "vif",
)

#: Columns of the table that turns coefficients into the returns a budget decides on.
RETURN_COLUMNS = (
    "channel",
    "spend_per_week",
    "marginal_return",
    "low",
    "high",
    "truth",
    "covers_truth",
    "times_the_truth",
    "interval_width_over_truth",
)

#: Columns of the transform grid.
GRID_COLUMNS = (
    "adstock",
    "saturation_at",
    "r_squared",
    "residual_sd",
    "fit_loss",
    "social_pago_return",
    "times_the_truth",
)


def spend_columns(panel: pd.DataFrame) -> tuple[str, ...]:
    """The spend columns of a panel, in the order they appear."""
    return tuple(name for name in panel.columns if str(name).startswith("spend_"))


def channel_of(column: str) -> str:
    """The channel a spend column belongs to."""
    return column.removeprefix("spend_")


def variance_inflation(matrix: np.ndarray) -> np.ndarray:
    """Variance inflation factor per column of a design matrix.

    How many times wider a coefficient's variance is than it would have been had that column been
    uncorrelated with the others. The square root is the factor on the standard error, which is the
    number worth quoting: a variance inflation of 25 is a confidence interval five times wider.

    Args:
        matrix: Design matrix, without an intercept column.

    Returns:
        One factor per column.
    """
    columns = matrix.shape[1]
    factors = np.empty(columns, dtype=float)
    for index in range(columns):
        target = matrix[:, index]
        others = np.delete(matrix, index, axis=1)
        design = np.column_stack([np.ones(matrix.shape[0]), others])
        fitted = design @ np.linalg.lstsq(design, target, rcond=None)[0]
        centred = target - target.mean()
        total = float(centred @ centred)
        residual = float((target - fitted) @ (target - fitted))
        # A column that is an exact combination of the others leaves a residual that is numerically
        # tiny rather than exactly zero, so a bare test against zero reports a variance inflation of
        # 1e30 where the honest answer is that the column carries no information of its own. The
        # threshold is relative to the column's own variation, which makes it scale-free.
        factors[index] = (
            float("inf") if residual <= total * COLLINEAR_TOLERANCE else total / residual
        )
    return factors


@dataclass(frozen=True)
class Fit:
    """A fitted media mix model, and the width of everything it claims.

    Attributes:
        names: Column names of the design matrix, in order, excluding the intercept.
        channels: The channels, in the order their columns appear.
        coefficients: Estimated coefficient per design column, excluding the intercept.
        intercept: Estimated intercept.
        standard_errors: Standard error per coefficient, excluding the intercept.
        df: Residual degrees of freedom.
        r_squared: Share of the variance in conversions the fit accounts for.
        residual_sd: Estimated standard deviation of the weekly noise.
        condition_number: Condition number of the channel block, centred and scaled. Above about
            thirty is the conventional warning line, and it is a statement about the spend plan
            rather than about the code.

            Centred deliberately, and it matters: the same matrix left uncentred scores 69.1 here
            against 7.0 centred, because the saturated spend columns are all positive with similar
            means and that near-constant direction dominates the decomposition. The intercept
            absorbs the common level, so the collinearity that actually widens the slopes is what
            is left after centring. Quoting the uncentred number would be inflating the alarm with
            an artefact - which is how the first version of this attribute read.
        vif: Variance inflation factor per channel column.
        carryover: The adstock the model was fitted with, which is a guess unless it came from the
            generator.
        half_points: The saturation half point per channel the model was fitted with.
        spend_per_week: Mean weekly spend per channel, for turning coefficients into returns.
        alpha: Significance level of the intervals.
    """

    names: tuple[str, ...]
    channels: tuple[str, ...]
    coefficients: np.ndarray
    intercept: float
    standard_errors: np.ndarray
    df: float
    r_squared: float
    residual_sd: float
    condition_number: float
    vif: np.ndarray
    carryover: float
    half_points: tuple[float, ...]
    spend_per_week: tuple[float, ...]
    alpha: float = DEFAULT_ALPHA

    @property
    def critical_value(self) -> float:
        """Two-sided t quantile at this fit's degrees of freedom."""
        return float(stats.t.ppf(1.0 - self.alpha / 2.0, self.df))

    def interval(self, index: int) -> tuple[float, float]:
        """Confidence interval on one coefficient."""
        half = self.critical_value * float(self.standard_errors[index])
        value = float(self.coefficients[index])
        return (value - half, value + half)

    def table(self) -> pd.DataFrame:
        """One row per channel: the coefficient, its width, and why it is that wide."""
        rows = []
        for index, channel in enumerate(self.channels):
            error = float(self.standard_errors[index])
            value = float(self.coefficients[index])
            statistic = value / error if error > 0 else float("inf")
            low, high = self.interval(index)
            rows.append(
                {
                    "channel": channel,
                    "coefficient": value,
                    "standard_error": error,
                    "t": statistic,
                    "p_value": float(2.0 * stats.t.sf(abs(statistic), self.df)),
                    "low": low,
                    "high": high,
                    "vif": float(self.vif[index]),
                }
            )
        return pd.DataFrame(rows)[list(FIT_COLUMNS)]

    def marginal_factor(self, index: int) -> float:
        """Conversions per unit of one week's spend, per unit of coefficient.

        The chain rule the coefficient has to be pushed through before it is a return: the
        derivative of the saturation curve at the channel's steady-state adstocked spend, divided by
        the carryover factor that built that steady state. It depends on the half point, which the
        model assumed - so a return quoted from a coefficient inherits the guess twice over.
        """
        weekly = self.spend_per_week[index]
        half_point = self.half_points[index]
        steady = weekly / (1.0 - self.carryover)
        return half_point / (steady + half_point) ** 2 / (1.0 - self.carryover)

    def returns(self, truth: pd.DataFrame | None = None) -> pd.DataFrame:
        """The coefficients as marginal returns, next to the truth when there is one.

        Args:
            truth: Optional frame with ``channel`` and ``marginal_conversions_per_unit_spend``.

        Returns:
            A frame with the columns in :data:`RETURN_COLUMNS`. Where no truth is supplied the last
            four columns are ``nan``, which is the honest state of a real account.
        """
        declared = (
            dict(
                zip(
                    truth["channel"].astype(str),
                    truth["marginal_conversions_per_unit_spend"].astype(float),
                    strict=True,
                )
            )
            if truth is not None
            else None
        )
        rows = []
        for index, channel in enumerate(self.channels):
            factor = self.marginal_factor(index)
            low, high = self.interval(index)
            estimate = float(self.coefficients[index]) * factor
            real = declared[channel] if declared is not None else float("nan")
            rows.append(
                {
                    "channel": channel,
                    "spend_per_week": self.spend_per_week[index],
                    "marginal_return": estimate,
                    "low": low * factor,
                    "high": high * factor,
                    "truth": real,
                    "covers_truth": (
                        bool(low * factor <= real <= high * factor)
                        if declared is not None
                        else False
                    ),
                    "times_the_truth": estimate / real if real else float("nan"),
                    "interval_width_over_truth": (
                        (high - low) * factor / real if real else float("nan")
                    ),
                }
            )
        return pd.DataFrame(rows)[list(RETURN_COLUMNS)]

    def equivalent_range(self, index: int, r_squared_loss: float) -> tuple[float, float]:
        """How far one coefficient can move while the fit gets no worse than ``r_squared_loss``.

        The demonstration everybody wants from a collinear model - "here is a completely different
        answer that fits the data just as well" - and the point of computing it is what comes out.
        The profile has a closed form: the furthest a coefficient can go while the residual sum of
        squares rises by ``delta`` is its standard error times the square root of ``delta`` over the
        residual variance. So the range **is** the confidence interval, rescaled. There is no
        second diagnostic hiding here: the standard error was already saying this, and it is the
        column that gets dropped when the chart is drawn.

        Args:
            index: Which coefficient.
            r_squared_loss: How much R-squared may fall.

        Returns:
            The lowest and highest value the coefficient can take within that loss of fit.

        Raises:
            ValueError: If the loss is not positive.
        """
        if r_squared_loss <= 0:
            raise ValueError(f"the loss of fit must be positive, got {r_squared_loss}")
        total = self.residual_sd**2 * self.df / (1.0 - self.r_squared)
        allowed = r_squared_loss * total
        half = float(self.standard_errors[index]) * math.sqrt(allowed / self.residual_sd**2)
        value = float(self.coefficients[index])
        return (value - half, value + half)


def design_matrix(
    panel: pd.DataFrame,
    carryover: float,
    saturation_at: float,
    design: MediaMixProfile = MEDIA_MIX,
    trend: bool = True,
    seasonality: bool = True,
) -> tuple[np.ndarray, tuple[str, ...], tuple[float, ...], tuple[float, ...]]:
    """Build the design matrix a media mix model is fitted on.

    Args:
        panel: The weekly panel.
        carryover: Adstock the model assumes.
        saturation_at: Saturation half point the model assumes, as a multiple of each channel's mean
            weekly spend - so one number covers channels of very different sizes, which is what a
            practitioner does.
        design: The panel's declared shape, for the seasonal period.
        trend: Whether to include a linear trend. Leaving it out is the omitted-variable case.
        seasonality: Whether to include the seasonal pair.

    Returns:
        ``(matrix, names, half_points, spend_per_week)``. The matrix has no intercept column.
    """
    columns = spend_columns(panel)
    weeks = np.asarray(panel["week"], dtype=float) - 1.0
    blocks: list[np.ndarray] = []
    names: list[str] = []
    half_points: list[float] = []
    per_week: list[float] = []
    for column in columns:
        spend = np.asarray(panel[column], dtype=float)
        weekly = float(spend.mean())
        half_point = saturation_at * weekly / (1.0 - carryover)
        blocks.append(saturate(adstock(spend, carryover), half_point))
        names.append(channel_of(str(column)))
        half_points.append(half_point)
        per_week.append(weekly)
    if trend:
        blocks.append(weeks)
        names.append("trend")
    if seasonality:
        angle = 2.0 * np.pi * weeks / design.seasonal_period
        blocks.append(np.sin(angle))
        blocks.append(np.cos(angle))
        names.extend(["seasonal_sin", "seasonal_cos"])
    return np.column_stack(blocks), tuple(names), tuple(half_points), tuple(per_week)


def fit(
    panel: pd.DataFrame,
    carryover: float = MEDIA_MIX.adstock,
    saturation_at: float = MEDIA_MIX.saturation_at,
    design: MediaMixProfile = MEDIA_MIX,
    trend: bool = True,
    seasonality: bool = True,
    alpha: float = DEFAULT_ALPHA,
    response: str = "conversions",
) -> Fit:
    """Ordinary least squares on transformed spend, with every width it implies.

    Args:
        panel: The weekly panel.
        carryover: Adstock the model assumes. The default is the generator's, which is the case no
            practitioner is in.
        saturation_at: Saturation half point the model assumes.
        design: The panel's declared shape.
        trend: Whether to include a linear trend.
        seasonality: Whether to include the seasonal pair.
        alpha: Significance level for the intervals.
        response: Column holding conversions.

    Returns:
        A :class:`Fit`.

    Raises:
        ValueError: If the panel has fewer weeks than the model has parameters.
    """
    matrix, names, half_points, per_week = design_matrix(
        panel, carryover, saturation_at, design, trend, seasonality
    )
    observations = matrix.shape[0]
    parameters = matrix.shape[1] + 1
    if observations <= parameters:
        raise ValueError(
            f"{observations} weeks cannot support {parameters} parameters; a media mix model needs "
            f"more rows than it has things to estimate"
        )

    target = np.asarray(panel[response], dtype=float)
    full = np.column_stack([np.ones(observations), matrix])
    coefficients, *_ = np.linalg.lstsq(full, target, rcond=None)
    fitted = full @ coefficients
    residuals = target - fitted
    residual_ss = float(residuals @ residuals)
    df = float(observations - parameters)
    variance = residual_ss / df
    covariance = variance * np.linalg.pinv(full.T @ full)
    errors = np.sqrt(np.diag(covariance))

    centred = target - target.mean()
    r_squared = 1.0 - residual_ss / float(centred @ centred)
    channels = tuple(
        name for name in names if name not in {"trend", "seasonal_sin", "seasonal_cos"}
    )
    block = matrix[:, : len(channels)]
    block = block - block.mean(axis=0)
    scaled = block / np.linalg.norm(block, axis=0)
    return Fit(
        names=names,
        channels=channels,
        coefficients=coefficients[1 : len(channels) + 1],
        intercept=float(coefficients[0]),
        standard_errors=errors[1 : len(channels) + 1],
        df=df,
        r_squared=r_squared,
        residual_sd=math.sqrt(variance),
        condition_number=float(np.linalg.cond(scaled)),
        vif=variance_inflation(matrix[:, : len(channels)]),
        carryover=carryover,
        half_points=half_points,
        spend_per_week=per_week,
        alpha=alpha,
    )


def transform_grid(
    panel: pd.DataFrame,
    carryovers: tuple[float, ...],
    saturations: tuple[float, ...],
    truth: pd.DataFrame,
    channel: str = "social-pago",
    design: MediaMixProfile = MEDIA_MIX,
) -> pd.DataFrame:
    """Fit quality against implied return, over a grid of the two parameters nobody observes.

    The table that decides whether a media mix model is identified in practice. If the fit is
    almost flat across the grid while the implied return moves by a factor of several, then the
    number the model reports was chosen by whoever picked the transforms.

    Args:
        panel: The weekly panel.
        carryovers: Adstock values to try.
        saturations: Saturation half points to try, as multiples of mean weekly spend.
        truth: The declared media truth, for the comparison column.
        channel: Which channel's return to follow across the grid.
        design: The panel's declared shape.

    Returns:
        A frame with the columns in :data:`GRID_COLUMNS`, ordered by fit, best first.
    """
    best = max(
        fit(panel, carryover, saturation, design).r_squared
        for carryover in carryovers
        for saturation in saturations
    )
    declared = dict(
        zip(
            truth["channel"].astype(str),
            truth["marginal_conversions_per_unit_spend"].astype(float),
            strict=True,
        )
    )
    real = declared[channel]
    rows = []
    for carryover in carryovers:
        for saturation in saturations:
            fitted = fit(panel, carryover, saturation, design)
            returns = fitted.returns(truth).set_index("channel")
            estimate = float(
                returns.loc[channel, "marginal_return"]  # type: ignore[arg-type]
            )
            rows.append(
                {
                    "adstock": carryover,
                    "saturation_at": saturation,
                    "r_squared": fitted.r_squared,
                    "residual_sd": fitted.residual_sd,
                    "fit_loss": best - fitted.r_squared,
                    "social_pago_return": estimate,
                    "times_the_truth": estimate / real if real else float("nan"),
                }
            )
    return pd.DataFrame(rows).sort_values("fit_loss")[list(GRID_COLUMNS)].reset_index(drop=True)


def channel_names() -> tuple[str, ...]:
    """The channels, in the order the panel's spend columns are sorted."""
    return tuple(sorted(profile.channel for profile in CHANNELS))
