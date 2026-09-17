"""What a channel actually caused, which needs an experiment rather than a model.

A geo holdout switches a channel off in half the regions and leaves it running in the other half.
The difference between what happens to the two halves is the channel's incremental effect, and the
subtraction removes anything the two halves had in common - seasonality, a price change, a
competitor, the trend that a before-and-after reading of the same data would have credited to the
channel.

It is the same difference in differences an operational pilot uses, and the unit of analysis is the
same too: the region, not the region-week. Forty regions over twenty-six weeks are forty
observations of a change, not one thousand and forty, and treating them as the latter is how a geo
test arrives at a confidence interval several times too narrow.

The output the money hangs on is :func:`returns`, which puts return on ad spend next to the
incremental version of it. They are not two views of one number: one of them counts revenue that
was coming anyway.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

#: Significance level the intervals use.
DEFAULT_ALPHA = 0.05

RETURN_COLUMNS = (
    "channel",
    "spend",
    "credited_conversions",
    "roas",
    "incremental_conversions",
    "iroas",
    "established",
    "ratio",
)


def _standard_error(kept: np.ndarray, lost: np.ndarray) -> float:
    """Standard error of the difference of two region-level means, unequal variances."""
    return float(np.sqrt(kept.var(ddof=1) / kept.size + lost.var(ddof=1) / lost.size))


def _welch_df(kept: np.ndarray, lost: np.ndarray) -> float:
    """Welch-Satterthwaite degrees of freedom, in closed form.

    Computed here rather than taken from ``scipy.stats.ttest_ind`` because of the case a holdout
    with no noise in it produces: when both arms have zero variance the ratio is 0/0, and scipy
    answers it with a precision-loss warning and an unreliable number. A noiseless panel is a
    legitimate input - it is the control case every test of this estimator starts from - so the
    limit is taken explicitly. The value returned there is the pooled count, which is never used:
    both the interval and the p-value short-circuit on a standard error of zero before the degrees
    of freedom enter. It is returned so the field is a number rather than a nan nobody expects.
    """
    first = kept.var(ddof=1) / kept.size
    second = lost.var(ddof=1) / lost.size
    denominator = first**2 / (kept.size - 1) + second**2 / (lost.size - 1)
    if denominator == 0.0:
        return float(kept.size + lost.size - 2)
    return float((first + second) ** 2 / denominator)


@dataclass(frozen=True)
class GeoLift:
    """The result of one holdout, with what it can and cannot support.

    Attributes:
        channel: The channel switched off.
        treated_geos: Regions that kept it.
        holdout_geos: Regions that lost it.
        split: Last week before it was switched off.
        lift: The estimated effect on the conversion rate, in rate points, signed so that a
            positive number means the channel helps.
        standard_error: Standard error of that estimate, from the spread between regions.
        df: Degrees of freedom of the Welch comparison behind it.
        alpha: Significance level of the interval.
        untested_because: Empty when the design could be tested. Otherwise the reason it could
            not, which is not the same thing as a result of nothing - see :meth:`verdict`.
    """

    channel: str
    treated_geos: int
    holdout_geos: int
    split: int
    lift: float
    standard_error: float
    df: float
    alpha: float = DEFAULT_ALPHA
    untested_because: str = ""

    @property
    def interval(self) -> tuple[float, float]:
        """Confidence interval on the lift, from the region-level spread."""
        if self.untested_because:
            return (float("nan"), float("nan"))
        if self.standard_error == 0.0 or not np.isfinite(self.df):
            return (self.lift, self.lift)
        half = float(stats.t.ppf(1.0 - self.alpha / 2.0, self.df)) * self.standard_error
        return (self.lift - half, self.lift + half)

    @property
    def p_value(self) -> float:
        """Two-sided p-value against a lift of zero, or ``nan`` where there was no test."""
        if self.untested_because:
            return float("nan")
        if self.standard_error == 0.0:
            return 0.0 if self.lift != 0.0 else 1.0
        return float(2.0 * stats.t.sf(abs(self.lift / self.standard_error), self.df))

    @property
    def significant(self) -> bool:
        """Whether the test can distinguish this channel's effect from nothing.

        False for a design that could not be tested at all, which is why
        :attr:`untested_because` exists next to it: a design with nothing to compare against
        reads, through this property alone, exactly like a channel that was measured and found to
        do nothing.
        """
        if self.untested_because:
            return False
        return self.p_value < self.alpha

    def incremental_conversions(self, reach: float) -> float:
        """The lift scaled to a population.

        The test measures a rate; a budget decision needs conversions. ``reach`` is passed in
        rather than inferred, because the population the campaign runs against is a business fact
        and guessing it silently is how a geo result becomes a number nobody can reproduce.

        Args:
            reach: Users the channel runs against over the period.

        Returns:
            Incremental conversions.
        """
        if reach < 0:
            raise ValueError(f"reach cannot be negative, got {reach}")
        return self.lift * reach

    def verdict(self) -> str:
        """What this holdout established, in one line."""
        if self.untested_because:
            return (
                f"{self.channel}: lift {self.lift:+.6f} points, untested - {self.untested_because}"
            )
        low, high = self.interval
        if not self.significant:
            return (
                f"{self.channel}: lift {self.lift:+.6f} points, interval {low:+.6f} to "
                f"{high:+.6f} - not distinguishable from nothing"
            )
        return f"{self.channel}: lift {self.lift:+.6f} points, interval {low:+.6f} to {high:+.6f}"


def geo_lift(
    panel: pd.DataFrame,
    split: int,
    channel: str = "",
    geo: str = "geo",
    week: str = "week",
    holdout: str = "holdout",
    users: str = "users",
    conversions: str = "conversions",
    alpha: float = DEFAULT_ALPHA,
) -> GeoLift:
    """Read a holdout panel as a difference in differences on region-level rates.

    Each region contributes one number: how much its conversion rate changed from before the switch
    to after. The treated regions' average change minus the holdout regions' is the lift, and the
    comparison behind it is Welch's on those region-level changes.

    Args:
        panel: One row per region-week, with users, conversions and a holdout flag.
        split: Last week before the channel was switched off.
        channel: Label carried into the result.
        geo: Column identifying the region.
        week: Column holding the week.
        holdout: Boolean column marking the regions that lost the channel.
        users: Column holding users reached.
        conversions: Column holding conversions.
        alpha: Significance level for the interval.

    Returns:
        A :class:`GeoLift`.

    Raises:
        ValueError: If either arm is empty, or the split leaves one phase with no weeks.
    """
    frame = panel.copy()
    frame["rate"] = frame[conversions] / frame[users]
    weeks = np.asarray(frame[week], dtype=int)
    before = frame[weeks <= split]
    after = frame[weeks > split]
    if before.empty or after.empty:
        raise ValueError(f"the split at week {split} leaves one side of the test with no weeks")

    changes = (
        after.groupby([geo, holdout], observed=True)["rate"].mean()
        - before.groupby([geo, holdout], observed=True)["rate"].mean()
    ).reset_index()
    flags = changes[holdout].astype(bool).to_numpy()
    kept = changes.loc[~flags, "rate"].to_numpy()
    lost = changes.loc[flags, "rate"].to_numpy()
    if kept.size == 0 or lost.size == 0:
        raise ValueError("a holdout needs regions on both sides of the switch")

    # One region on a side gives a mean and no spread, so the difference is computable and its
    # error is not. Returning it with a reason rather than raising is deliberate: a two-region
    # test is a real design somebody runs, and a function that raises here would send them looking
    # for a bug instead of for more regions. What must not happen is the number arriving with a
    # nan standard error attached and being read as "not significant", which is what this said
    # before the reason existed.
    if kept.size < 2 or lost.size < 2:
        return GeoLift(
            channel=channel or str(panel[geo].iloc[0]),
            treated_geos=int(kept.size),
            holdout_geos=int(lost.size),
            split=split,
            lift=float(kept.mean() - lost.mean()),
            standard_error=float("nan"),
            df=float("nan"),
            alpha=alpha,
            untested_because=(
                f"the spread between regions needs at least two on each side, and this test has "
                f"{kept.size} treated and {lost.size} held out"
            ),
        )

    # Signed so that a positive lift means the channel helps: the regions that kept it should have
    # done better than the ones that lost it.
    lift = float(kept.mean() - lost.mean())
    pooled = _standard_error(kept, lost)
    return GeoLift(
        channel=channel or str(panel[geo].iloc[0]),
        treated_geos=int(kept.size),
        holdout_geos=int(lost.size),
        split=split,
        lift=lift,
        standard_error=pooled,
        df=_welch_df(kept, lost),
        alpha=alpha,
    )


def roas(credited_conversions: float, spend: float, value_per_conversion: float) -> float:
    """Revenue the channel was credited with, over what it cost.

    The figure every platform reports, and it counts revenue from conversions the channel was
    merely present for. It is not wrong about the revenue; it is wrong about the *because*.

    Raises:
        ValueError: If the spend is not positive.
    """
    if spend <= 0:
        raise ValueError(f"spend must be positive, got {spend}")
    return credited_conversions * value_per_conversion / spend


def iroas(incremental_conversions: float, spend: float, value_per_conversion: float) -> float:
    """Revenue that would not have happened, over what it cost.

    The same arithmetic as :func:`roas` on a different numerator, and the difference between the
    two numerators is the whole subject of this module.

    Raises:
        ValueError: If the spend is not positive.
    """
    if spend <= 0:
        raise ValueError(f"spend must be positive, got {spend}")
    return incremental_conversions * value_per_conversion / spend


def returns(
    credited: pd.DataFrame,
    lifts: dict[str, GeoLift],
    truth: pd.DataFrame,
    reach: float,
    value_per_conversion: float,
    channel: str = "channel",
    credited_column: str = "credited",
) -> pd.DataFrame:
    """Return on ad spend next to the incremental version, one row per channel.

    The credited conversions are read from the model's own ``credited`` column rather than
    reconstructed from its share. That is deliberate and it was a defect here first: multiplying a
    share by the *total* conversions spreads the untouched ones across the channels, which is
    precisely the rescaling :func:`mktlab.attribution.credit.unattributable` exists to warn about.

    Args:
        credited: Output of :func:`mktlab.attribution.credit.credit` for the model whose credit is
            being priced - usually last-click, because that is what the report shows.
        lifts: One :class:`GeoLift` per channel.
        truth: The channel table, for the spend.
        reach: Users each channel runs against over the period.
        value_per_conversion: Revenue per conversion.
        channel: Column identifying the channel.
        credited_column: Column holding credited conversions in absolute terms.

    Returns:
        A frame with the columns in :data:`RETURN_COLUMNS`. ``established`` says whether the
        holdout could distinguish the channel's effect from nothing; where it could not, ``ratio``
        is ``nan`` rather than a number, because a ratio against an unmeasured denominator reads as
        evidence and is not.

    Raises:
        KeyError: If a channel in ``credited`` has no holdout.
    """
    spend = truth.set_index(channel)["spend"]
    conversions = credited.set_index(channel)[credited_column]
    rows = []
    for name in conversions.index:
        if name not in lifts:
            raise KeyError(f"no holdout for {name!r}, so its incremental return is unknown")
        lift = lifts[name]
        credited_conversions = float(conversions[name])
        incremental = lift.incremental_conversions(reach)
        on_spend = roas(credited_conversions, float(spend[name]), value_per_conversion)
        incremental_return = iroas(incremental, float(spend[name]), value_per_conversion)
        established = bool(lift.significant and incremental_return > 0)
        rows.append(
            {
                "channel": name,
                "spend": float(spend[name]),
                "credited_conversions": credited_conversions,
                "roas": on_spend,
                "incremental_conversions": incremental,
                "iroas": incremental_return,
                "established": established,
                "ratio": on_spend / incremental_return if established else float("nan"),
            }
        )
    return pd.DataFrame(rows)[list(RETURN_COLUMNS)]
