"""Geo holdouts: the only table here that contains a counterfactual.

One panel per channel. Half the regions keep the channel and half lose it from a known week, so
the difference between what happened to the two halves is the channel's incremental effect - and
it is the same difference-in-differences a well-run operational pilot uses, applied to media.

The panel is aggregated rather than simulated user by user: conversions in a region-week are drawn
from a binomial around the exact mean rate the audience model implies. Exact for the mean, and
slightly generous with the variance, because a binomial treats users as identical when they differ
in intent. Overstating the noise makes every interval computed from this panel conservative.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AUDIENCE, CHANNELS, GEO, AudienceProfile, ChannelProfile, GeoProfile

GEO_COLUMNS = ("channel", "geo", "week", "holdout", "users", "conversions")
DESIGN_COLUMNS = (
    "channel",
    "geos",
    "weeks",
    "split",
    "users_per_geo_week",
    "weekly_trend",
    "true_effect",
    "true_rate_lift",
    "spend",
)


def mean_rate(audience: AudienceProfile, live: tuple[ChannelProfile, ...]) -> float:
    """The exact average conversion rate when these channels are running.

    Exposure is linear in intent and the effects are additive, so the expectation closes: each live
    channel contributes its effect times its expected exposure, and nothing has to be simulated to
    get the mean right.

    Args:
        audience: The population's parameters.
        live: The channels switched on.

    Returns:
        The mean probability of converting.
    """
    mean_intent = audience.intent_alpha / (audience.intent_alpha + audience.intent_beta)
    rate = audience.base_conversion + audience.intent_slope * mean_intent
    for profile in live:
        rate += profile.true_effect * (
            profile.exposure_base + profile.exposure_intent_slope * mean_intent
        )
    return float(rate)


def true_rate_lift(profile: ChannelProfile, audience: AudienceProfile = AUDIENCE) -> float:
    """What switching this channel off actually costs, in conversion-rate points.

    The figure a geo test is trying to recover, and the one the attribution models are checked
    against. It is the channel's effect times the share of users it reaches - not the effect alone,
    because a channel only helps the people who see it.
    """
    mean_intent = audience.intent_alpha / (audience.intent_alpha + audience.intent_beta)
    return float(
        profile.true_effect * (profile.exposure_base + profile.exposure_intent_slope * mean_intent)
    )


def _one_panel(
    profile: ChannelProfile,
    rng: np.random.Generator,
    audience: AudienceProfile,
    design: GeoProfile,
) -> pd.DataFrame:
    holdout = np.zeros(design.geos, dtype=bool)
    holdout[rng.choice(design.geos, size=design.geos // 2, replace=False)] = True
    level = rng.normal(0.0, design.geo_sd, size=design.geos)

    live = tuple(CHANNELS)
    without = tuple(other for other in CHANNELS if other.channel != profile.channel)
    with_channel = mean_rate(audience, live)
    without_channel = mean_rate(audience, without)

    rows: list[dict[str, object]] = []
    for geo in range(design.geos):
        for week in range(1, design.weeks + 1):
            switched_off = holdout[geo] and week > design.split
            base = without_channel if switched_off else with_channel
            rate = float(np.clip(base + level[geo] + design.weekly_trend * (week - 1), 1e-6, 1.0))
            rows.append(
                {
                    "channel": profile.channel,
                    "geo": f"UF-{geo + 1:02d}",
                    "week": week,
                    "holdout": bool(holdout[geo]),
                    "users": design.users_per_geo_week,
                    "conversions": int(rng.binomial(design.users_per_geo_week, rate)),
                }
            )
    return pd.DataFrame(rows)


def geo_experiments(
    rng: np.random.Generator,
    audience: AudienceProfile = AUDIENCE,
    design: GeoProfile = GEO,
) -> pd.DataFrame:
    """One holdout panel per channel, stacked.

    Args:
        rng: The shared generator, consumed in a fixed order.
        audience: The population's parameters.
        design: The test's shape.

    Returns:
        A frame with the columns in :data:`GEO_COLUMNS`.
    """
    frame = pd.concat(
        [_one_panel(profile, rng, audience, design) for profile in CHANNELS], ignore_index=True
    )
    for column in ("channel", "geo"):
        frame[column] = frame[column].astype("category")
    return frame[list(GEO_COLUMNS)]


def geo_designs(audience: AudienceProfile = AUDIENCE, design: GeoProfile = GEO) -> pd.DataFrame:
    """What each test was built to measure, including the lift it should recover."""
    return pd.DataFrame(
        [
            {
                "channel": profile.channel,
                "geos": design.geos,
                "weeks": design.weeks,
                "split": design.split,
                "users_per_geo_week": design.users_per_geo_week,
                "weekly_trend": design.weekly_trend,
                "true_effect": profile.true_effect,
                "true_rate_lift": true_rate_lift(profile, audience),
                "spend": profile.spend,
            }
            for profile in CHANNELS
        ]
    )[list(DESIGN_COLUMNS)]
