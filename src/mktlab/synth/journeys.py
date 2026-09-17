"""Users, their journeys, and the intent that decided both.

The table a real attribution tool sees is the journeys one: which channels touched which user, in
what order, and whether that user converted. What it does not see is ``intent`` - how likely the
user was to convert before any marketing happened - and every distortion this repository measures
comes from that one missing column.

The generator draws intent first, then exposure *as a function of it*, then conversion. That order
is the causal order, and reversing it in analysis is the mistake the whole package is about.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AUDIENCE, CHANNELS, STAGE_NOISE, AudienceProfile, ChannelProfile

AUDIENCE_COLUMNS = ("user", "intent", "touches", "converted")
JOURNEY_COLUMNS = ("user", "position", "channel", "converted")
TRUTH_COLUMNS = (
    "channel",
    "stage",
    "exposure_rate",
    "exposure_intent_slope",
    "true_effect",
    "spend",
)


def exposure_probability(profile: ChannelProfile, intent: np.ndarray) -> np.ndarray:
    """Chance of being exposed to a channel, given how much intent a user has.

    Args:
        profile: The channel.
        intent: Intent per user, in ``[0, 1]``.

    Returns:
        A probability per user, clipped to ``[0, 1]``.
    """
    return np.clip(profile.exposure_base + profile.exposure_intent_slope * intent, 0.0, 1.0)


def conversion_probability(
    audience: AudienceProfile,
    intent: np.ndarray,
    exposed: dict[str, np.ndarray],
) -> np.ndarray:
    """Chance of converting: a baseline, the user's own intent, and what marketing added.

    The channels enter additively and only through their ``true_effect``, so the effect of a
    channel is the same for everybody exposed to it. That is a simplification and it is the
    conservative one: a channel whose effect varied with intent would be even harder to read off a
    journey than what is measured here.

    Args:
        audience: The population's parameters.
        intent: Intent per user.
        exposed: Exposure mask per channel.

    Returns:
        A probability per user, clipped to ``[0, 1]``.
    """
    lift = np.zeros_like(intent)
    for profile in CHANNELS:
        lift = lift + profile.true_effect * exposed[profile.channel]
    return np.clip(audience.base_conversion + audience.intent_slope * intent + lift, 0.0, 1.0)


def _draw(
    rng: np.random.Generator, audience: AudienceProfile
) -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray]:
    """Intent, exposure and conversion, drawn in the causal order."""
    intent = rng.beta(audience.intent_alpha, audience.intent_beta, size=audience.users)
    exposed = {
        profile.channel: rng.random(audience.users) < exposure_probability(profile, intent)
        for profile in CHANNELS
    }
    converted = rng.random(audience.users) < conversion_probability(audience, intent, exposed)
    return intent, exposed, converted


def _ordered_touches(
    rng: np.random.Generator, exposed: dict[str, np.ndarray], users: int
) -> list[list[str]]:
    """Each user's channels, ordered by funnel stage with noise.

    The order matters because last-click and first-click read it as evidence. It is drawn from the
    stage rather than at random, so a late-funnel channel is usually - not always - the last touch.
    """
    stages = {profile.channel: profile.stage for profile in CHANNELS}
    noise = {profile.channel: rng.normal(0.0, STAGE_NOISE, size=users) for profile in CHANNELS}
    journeys: list[list[str]] = []
    for index in range(users):
        touched = [profile.channel for profile in CHANNELS if exposed[profile.channel][index]]
        journeys.append(
            sorted(touched, key=lambda channel: stages[channel] + noise[channel][index])
        )
    return journeys


def audience_and_journeys(
    rng: np.random.Generator, audience: AudienceProfile = AUDIENCE
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One table of users and one of touches, drawn from the same pass.

    They are returned together because they are one draw: generating them separately would need
    the intent to be drawn twice, and the second draw would not be the first one.

    Args:
        rng: The shared generator, consumed in a fixed order.
        audience: The population's parameters.

    Returns:
        ``(audience, journeys)`` with the columns in :data:`AUDIENCE_COLUMNS` and
        :data:`JOURNEY_COLUMNS`.
    """
    intent, exposed, converted = _draw(rng, audience)
    ordered = _ordered_touches(rng, exposed, audience.users)

    users = pd.DataFrame(
        {
            "user": np.arange(1, audience.users + 1),
            "intent": intent,
            "touches": [len(touches) for touches in ordered],
            "converted": converted,
        }
    )

    rows: list[dict[str, object]] = []
    for index, touches in enumerate(ordered):
        for position, channel in enumerate(touches, start=1):
            rows.append(
                {
                    "user": index + 1,
                    "position": position,
                    "channel": channel,
                    "converted": bool(converted[index]),
                }
            )
    journeys = pd.DataFrame(rows)
    journeys["channel"] = journeys["channel"].astype("category")
    return users[list(AUDIENCE_COLUMNS)], journeys[list(JOURNEY_COLUMNS)]


def channel_truth(audience: AudienceProfile = AUDIENCE) -> pd.DataFrame:
    """What each channel really does, next to how selected its audience is.

    ``exposure_rate`` is computed rather than drawn: with exposure linear in intent, the expected
    rate is the base plus the slope times the mean intent, which is exact.
    """
    mean_intent = audience.intent_alpha / (audience.intent_alpha + audience.intent_beta)
    return pd.DataFrame(
        [
            {
                "channel": profile.channel,
                "stage": profile.stage,
                "exposure_rate": profile.exposure_base
                + profile.exposure_intent_slope * mean_intent,
                "exposure_intent_slope": profile.exposure_intent_slope,
                "true_effect": profile.true_effect,
                "spend": profile.spend,
            }
            for profile in CHANNELS
        ]
    )[list(TRUTH_COLUMNS)]
