"""The weekly spend panel: the table a media mix model is fitted on.

Wave 1's tables are user-level, which no marketing team has. This one is what they do have - weeks
down the side, spend per channel across the top, conversions in the last column - and it is the
input
to the model everybody reaches for when nobody will pay for a holdout.

Three things are built into it deliberately, because they are the three reasons such a model is
hard.

**The channels move together.** Media plans are written as shares of a budget, so when the budget
moves the channels move with it. The panel is generated that way: one common budget swing plus a
smaller independent swing per channel. Nothing pathological has been done - this is how plans are
written - and it is enough to make the channels nearly the same variable.

**Spend carries over.** A share of each week's effect lands in the following weeks, geometrically.
Nobody observes that share.

**Returns bend.** Response saturates, so a channel's coefficient is a local slope at the spend level
it happens to be running at, not a return that holds at twice the budget. Nobody observes where the
bend is either.

The effect each channel really has is not invented separately here. It is derived from the truth
wave
1 already declared: a channel's incremental conversions are its rate lift times the audience it runs
against, and dividing by its spend gives conversions per unit of spend. So the model in
:mod:`mktlab.mmm` can be asked the same question the geo holdout was asked, against the same truth,
and the two answers can be put side by side.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ._draws import normal
from .config import (
    AUDIENCE,
    CHANNELS,
    MEDIA_MIX,
    AudienceProfile,
    ChannelProfile,
    MediaMixProfile,
)

SPEND_COLUMNS = ("week", "conversions", "baseline")
MEDIA_TRUTH_COLUMNS = (
    "channel",
    "spend_per_week",
    "conversions_per_unit_spend",
    "marginal_conversions_per_unit_spend",
    "true_effect",
    "adstock",
    "saturation_at",
)


def conversions_per_unit_spend(
    profile: ChannelProfile,
    audience: AudienceProfile = AUDIENCE,
) -> float:
    """The channel's real return, in conversions per unit of spend.

    Derived rather than invented: wave 1 declared a rate lift and an audience, so the incremental
    conversions are their product, and dividing by the spend gives the return per unit. This is what
    ties the spend panel to the same truth the holdout is measured against.
    """
    mean_intent = audience.intent_alpha / (audience.intent_alpha + audience.intent_beta)
    exposure = profile.exposure_base + profile.exposure_intent_slope * mean_intent
    return float(profile.true_effect * exposure * audience.users / profile.spend)


def adstock(spend: np.ndarray, carryover: float) -> np.ndarray:
    """Spend with a geometric share of each week carried into the following ones.

    Args:
        spend: Weekly spend.
        carryover: Share of the previous week's adstock that persists. Zero is no carryover.

    Returns:
        The adstocked series, the same length as the input.

    Raises:
        ValueError: If the carryover is not in ``[0, 1)``. At one the series never decays and the
            transform has no finite steady state.
    """
    if not 0.0 <= carryover < 1.0:
        raise ValueError(f"carryover must be in [0, 1), got {carryover}")
    out = np.empty_like(spend, dtype=float)
    running = 0.0
    for index, value in enumerate(spend):
        running = float(value) + carryover * running
        out[index] = running
    return out


def saturate(spend: np.ndarray, half_point: float) -> np.ndarray:
    """Diminishing returns, as a Hill curve with exponent one.

    ``spend / (spend + half_point)`` - zero at zero spend, one half at ``half_point``, approaching
    one from below. Bounded, monotone, and with a derivative that falls everywhere, which is the
    minimum a response curve has to do to be a response curve.

    Args:
        spend: Spend, in whatever units ``half_point`` is in.
        half_point: Spend at which the response reaches half of its ceiling.

    Returns:
        The saturated response, between zero and one.

    Raises:
        ValueError: If the half point is not positive.
    """
    if half_point <= 0:
        raise ValueError(f"the half point must be positive, got {half_point}")
    return np.asarray(spend / (spend + half_point), dtype=float)


def media_truth(
    audience: AudienceProfile = AUDIENCE,
    design: MediaMixProfile = MEDIA_MIX,
) -> pd.DataFrame:
    """What each channel really does in the panel, including the two unobservable parameters.

    ``conversions_per_unit_spend`` is the average return at the channel's own spend level;
    ``marginal_conversions_per_unit_spend`` is the derivative there, which is what a regression
    coefficient estimates and is smaller whenever the response is bending. Reporting the first while
    estimating the second is a confusion this column exists to prevent.
    """
    rows = []
    for profile in CHANNELS:
        weekly = profile.spend / design.weeks
        half_point = design.saturation_at * weekly / (1.0 - design.adstock)
        steady = weekly / (1.0 - design.adstock)
        average = conversions_per_unit_spend(profile, audience)
        # The response is a ceiling times saturate(adstocked spend). At the steady state, the
        # derivative with respect to one week's spend is the ceiling times the Hill derivative,
        # divided by the same carryover factor that built the steady state.
        derivative = half_point / (steady + half_point) ** 2 / (1.0 - design.adstock)
        ceiling = (
            average * profile.spend / (design.weeks * saturate(np.array([steady]), half_point)[0])
        )
        rows.append(
            {
                "channel": profile.channel,
                "spend_per_week": weekly,
                "conversions_per_unit_spend": average,
                "marginal_conversions_per_unit_spend": float(ceiling * derivative),
                "true_effect": profile.true_effect,
                "adstock": design.adstock,
                "saturation_at": design.saturation_at,
            }
        )
    return pd.DataFrame(rows)[list(MEDIA_TRUTH_COLUMNS)]


def spend_panel(
    rng: np.random.Generator,
    audience: AudienceProfile = AUDIENCE,
    design: MediaMixProfile = MEDIA_MIX,
) -> pd.DataFrame:
    """One row per week: spend per channel, the conversions it produced, and the baseline.

    The ``baseline`` column is the part of the conversions marketing had nothing to do with - the
    level, the trend and the seasonal cycle. No real panel has it, and it is here for the same
    reason
    the intent column is: so that a model's answer can be compared with the truth rather than with
    another model.

    Args:
        rng: The shared generator, consumed in a fixed order.
        audience: The population's parameters.
        design: The panel's shape.

    Returns:
        A frame with the columns in :data:`SPEND_COLUMNS` plus one spend column per channel, named
        ``spend_<channel>``.
    """
    weeks = np.arange(design.weeks, dtype=float)
    # One budget swing shared by every channel, then one independent swing each. The first is what
    # media plans do and the second is what stops the panel being unidentifiable in principle.
    budget = 1.0 + design.budget_swing * normal(rng, design.weeks)
    truth = media_truth(audience, design)

    spends: dict[str, np.ndarray] = {}
    response = np.zeros(design.weeks, dtype=float)
    for profile in CHANNELS:
        weekly = profile.spend / design.weeks
        own = 1.0 + design.idiosyncratic_swing * normal(rng, design.weeks)
        spend = np.clip(weekly * budget * own, weekly * 0.05, None)
        spends[f"spend_{profile.channel}"] = spend

        half_point = design.saturation_at * weekly / (1.0 - design.adstock)
        steady = weekly / (1.0 - design.adstock)
        average = float(
            truth.loc[truth["channel"] == profile.channel, "conversions_per_unit_spend"].iloc[0]
        )
        ceiling = average * weekly / saturate(np.array([steady]), half_point)[0]
        response = response + ceiling * saturate(adstock(spend, design.adstock), half_point)

    seasonal = (
        design.seasonal_amplitude
        * design.base_conversions
        * np.sin(2.0 * np.pi * weeks / design.seasonal_period)
    )
    baseline = design.base_conversions + design.weekly_trend * weeks + seasonal
    noise = normal(rng, design.weeks, design.noise_sd)

    frame = pd.DataFrame({"week": np.arange(1, design.weeks + 1), **spends})
    frame["conversions"] = baseline + response + noise
    frame["baseline"] = baseline
    ordered = ["week", *sorted(spends), "conversions", "baseline"]
    return frame[ordered]
