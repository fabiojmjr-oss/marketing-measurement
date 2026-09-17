"""Every number the generator uses, in one place.

The values are invented. No data from any advertiser, agency, platform or client is used anywhere
in this repository - see ``DISCLAIMER.md`` - and the channel names are labels for the roles those
channels play, not references to any account.

Two conventions carry the whole repository:

**Exposure depends on intent, and that is the mechanism.** A user who is already going to buy
searches the brand name and gets retargeted; a user who has never heard of the product does not.
So the channels that appear in converting journeys are partly *consequences* of intent rather than
causes of it, and every model that allocates credit by co-occurrence inherits that. The
``exposure_intent_slope`` column is where that lives, and it is the single most important parameter
in the file.

**Two channels have a true incremental effect of exactly zero.** ``retargeting`` and
``busca-marca`` are the ones whose exposure is most intent-driven, and they cause nothing at all.
That is not a caricature: it is the case every geo holdout in the industry keeps rediscovering, and
a generator where every channel worked a little would let a wrong reading of an attribution report
pass unnoticed.
"""

from __future__ import annotations

from dataclasses import dataclass

SEED = 42


@dataclass(frozen=True)
class ChannelProfile:
    """One marketing channel, described by what it does and by who sees it.

    Attributes:
        channel: Label for the channel.
        stage: Where it sits in the journey, from 1 for the first touch upwards. Touches are
            ordered by this with noise, so a late-funnel channel is usually the last touch - which
            is what makes last-click attribution a statement about the funnel's shape rather than
            about cause.
        exposure_base: Probability of exposure for a user with no intent at all.
        exposure_intent_slope: How much that probability rises with intent. Zero is a channel that
            reaches everybody equally, which is what a broad prospecting buy does. Large is a
            channel that finds people who were already going to convert.
        true_effect: The channel's real effect on the probability of converting, as an absolute
            increase. This is the column a real account never has, and the one every figure in the
            repository is checked against.
        spend: Money put into the channel over the period, for the return figures.
    """

    channel: str
    stage: float
    exposure_base: float
    exposure_intent_slope: float
    true_effect: float
    spend: float


# Five channels, chosen so that the models disagree with each other and all of them disagree with
# the truth. The two at the bottom are the instructive ones: their exposure is almost entirely a
# consequence of intent, and their effect is zero.
CHANNELS = (
    # A broad prospecting buy. It reaches everybody equally - the slope is zero - and it is the
    # only channel here that creates demand rather than finding it.
    ChannelProfile(
        channel="social-pago",
        stage=1.0,
        exposure_base=0.45,
        exposure_intent_slope=0.00,
        true_effect=0.060,
        spend=180_000.0,
    ),
    # Owned audience. Cheap, mildly self-selected, and mildly effective.
    ChannelProfile(
        channel="email",
        stage=2.0,
        exposure_base=0.30,
        exposure_intent_slope=0.10,
        true_effect=0.010,
        spend=20_000.0,
    ),
    # Non-brand search. Half demand capture, half demand creation, and self-selected in between.
    ChannelProfile(
        channel="busca-generica",
        stage=3.0,
        exposure_base=0.20,
        exposure_intent_slope=0.25,
        true_effect=0.030,
        spend=120_000.0,
    ),
    # Retargeting. Seen almost only by people who already showed intent, and worth nothing on top
    # of it: the canonical case an attribution report cannot see and a holdout settles in a week.
    ChannelProfile(
        channel="retargeting",
        stage=4.0,
        exposure_base=0.05,
        exposure_intent_slope=0.70,
        true_effect=0.000,
        spend=60_000.0,
    ),
    # Branded search. The user typed the brand name, which means the decision was already made.
    # Bidding on it buys a click that was coming anyway.
    ChannelProfile(
        channel="busca-marca",
        stage=5.0,
        exposure_base=0.02,
        exposure_intent_slope=0.80,
        true_effect=0.000,
        spend=90_000.0,
    ),
)

#: Spread of the noise added to a channel's stage when a journey is ordered. Large enough that the
#: order is not deterministic - real journeys are not - and small enough that late-funnel channels
#: are usually late.
STAGE_NOISE = 0.35


@dataclass(frozen=True)
class AudienceProfile:
    """The population the campaign runs against.

    Attributes:
        users: How many users are observed.
        intent_alpha: First shape of the intent distribution.
        intent_beta: Second shape. With ``(2, 8)`` most users have little intent and a few have a
            lot, which is the shape that makes the selection problem bite.
        base_conversion: Probability of converting with no intent and no exposure at all.
        intent_slope: How much intent raises that probability on its own, with no marketing.
        value_per_conversion: Revenue booked per conversion, for the return figures.
    """

    users: int
    intent_alpha: float
    intent_beta: float
    base_conversion: float
    intent_slope: float
    value_per_conversion: float


AUDIENCE = AudienceProfile(
    users=200_000,
    intent_alpha=2.0,
    intent_beta=8.0,
    base_conversion=0.010,
    intent_slope=0.250,
    value_per_conversion=180.0,
)


@dataclass(frozen=True)
class GeoProfile:
    """A geo holdout: half the regions keep the channel, half lose it.

    The panel is aggregated rather than simulated user by user. Conversions in a region-week are
    drawn from a binomial around the exact mean rate the audience model implies, which is faster
    and - for the mean - exact. It slightly overstates the variance, because a binomial treats
    users as identical when they differ in intent, and overstating the noise makes every interval
    here conservative rather than flattering.

    Attributes:
        geos: Regions in the test. Half are held out, chosen at random.
        weeks: Weeks the test runs for.
        split: Last week before the channel is switched off in the holdout regions.
        users_per_geo_week: Users reached in each region each week.
        geo_sd: Permanent spread between regions, on the conversion rate.
        weekly_trend: Change in the conversion rate per week, common to every region. It is here
            because a before-and-after reading of a geo test credits it to the channel, and the
            difference in differences is what removes it.
    """

    geos: int
    weeks: int
    split: int
    users_per_geo_week: int
    geo_sd: float
    weekly_trend: float


GEO = GeoProfile(
    geos=40,
    weeks=26,
    split=13,
    users_per_geo_week=2_000,
    geo_sd=0.010,
    weekly_trend=0.0004,
)
