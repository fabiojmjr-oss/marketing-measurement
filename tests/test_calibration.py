"""Putting the experiment into the model, against cases where the answer is known in advance.

Four controls carry this file. The average-to-marginal factor has a closed form, so it is checked
against the generator's own ratio of the two return columns - two derivations that share no code. A
flat prior has to return least squares exactly, and a prior with no width has to return its own mean,
because those are the two ends of the update. And with a prior on exactly one coefficient the
posterior standard error has a closed form by Sherman-Morrison, however collinear the design is,
which pins the arithmetic in the middle of the range rather than only at its ends.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from mktlab.attribution import GeoLift, geo_lift
from mktlab.calibration import (
    CALIBRATION_COLUMNS,
    TRANSFER_COLUMNS,
    Prior,
    average_to_marginal,
    calibrate,
    prior_from_holdout,
    saturation_multiple,
)
from mktlab.mmm import fit
from mktlab.synth import AUDIENCE, CHANNELS, GEO, MEDIA_MIX, Dataset


def control_prior(channel: str, mean: float, standard_error: float) -> Prior:
    """A prior with a declared mean and width, for the control cases."""
    return Prior(
        channel=channel,
        mean=mean,
        standard_error=standard_error,
        average_return=float("nan"),
        marginal_return=float("nan"),
        conversion_factor=1.0,
        source="control case",
    )


def holdout_of(full: Dataset, channel: str) -> GeoLift:
    """The holdout for one channel, as the examples read it."""
    panel = full.geo_experiments[full.geo_experiments["channel"] == channel]
    return geo_lift(panel, split=GEO.split, channel=channel)


def spend_of(channel: str) -> float:
    """The declared spend for one channel."""
    return next(profile.spend for profile in CHANNELS if profile.channel == channel)


def real_prior(full: Dataset, channel: str, convert: bool = True) -> Prior:
    """The prior the wave actually publishes: this channel's holdout, converted."""
    fitted = fit(full.spend_panel)
    return prior_from_holdout(
        holdout_of(full, channel),
        fitted,
        channel,
        reach=float(AUDIENCE.users),
        spend=spend_of(channel),
        convert=convert,
    )


class TestTheBridgeBetweenTheInstruments:
    def test_the_factor_is_one_plus_the_reciprocal_of_the_saturation_multiple(self) -> None:
        """The closed form, at four points spanning the range the fit cannot distinguish."""
        for multiple in (0.5, 1.3, 3.0, 10.0):
            assert average_to_marginal(multiple) == pytest.approx(1.0 + 1.0 / multiple, rel=1e-15)

    def test_the_factor_matches_the_generators_own_ratio_of_the_two_return_columns(
        self, full: Dataset
    ) -> None:
        """The control that matters: the closed form against a number derived from other code.

        The generator builds the average return from the declared effect and the marginal one by
        differentiating the response, with no reference to this formula. That they agree to twelve
        digits on every channel with a real effect is the evidence that the bridge is the right one.
        """
        expected = average_to_marginal(MEDIA_MIX.saturation_at)
        truth = full.media_truth
        working = truth[truth["marginal_conversions_per_unit_spend"] > 0]
        assert len(working) == 3, "the panel should have three channels with a real effect"
        for _, row in working.iterrows():
            ratio = row["conversions_per_unit_spend"] / row["marginal_conversions_per_unit_spend"]
            assert ratio == pytest.approx(expected, rel=1e-12), row["channel"]

    def test_a_saturation_point_at_or_below_zero_is_refused_rather_than_answered(self) -> None:
        for multiple in (0.0, -1.3):
            with pytest.raises(ValueError, match="must be positive"):
                average_to_marginal(multiple)

    def test_the_fit_reports_back_the_saturation_point_it_was_given(self, full: Dataset) -> None:
        """The conversion has to use the model's own assumption, so it is read off the model."""
        for multiple in (0.5, 1.3, 4.0):
            fitted = fit(full.spend_panel, saturation_at=multiple)
            for index in range(len(fitted.channels)):
                assert saturation_multiple(fitted, index) == pytest.approx(multiple, rel=1e-12)


class TestTheEndsOfTheUpdate:
    def test_no_priors_at_all_returns_least_squares(self, full: Dataset) -> None:
        """The first thing a Bayesian update has to do is nothing when it is told nothing."""
        baseline = fit(full.spend_panel)
        calibrated = calibrate(full.spend_panel, {})
        assert calibrated.posterior.coefficients == pytest.approx(baseline.coefficients, rel=1e-9)
        assert calibrated.posterior.standard_errors == pytest.approx(
            baseline.standard_errors, rel=1e-9
        )
        assert calibrated.posterior.r_squared == pytest.approx(baseline.r_squared, rel=1e-12)

    def test_a_refused_prior_leaves_the_channel_exactly_where_it_was(self, full: Dataset) -> None:
        """A holdout that was not a test must not enter the model as though it were."""
        baseline = fit(full.spend_panel)
        untested = GeoLift(
            channel="social-pago",
            treated_geos=1,
            holdout_geos=1,
            split=GEO.split,
            lift=0.05,
            standard_error=float("nan"),
            df=float("nan"),
            untested_because="one region a side leaves nothing to compare",
        )
        prior = prior_from_holdout(
            untested, baseline, "social-pago", reach=float(AUDIENCE.users), spend=180_000.0
        )
        assert not prior.usable
        assert "not a test" in prior.refused_because
        calibrated = calibrate(full.spend_panel, {"social-pago": prior})
        assert calibrated.posterior.coefficients == pytest.approx(baseline.coefficients, rel=1e-9)

    def test_a_prior_with_no_width_returns_its_own_mean(self, full: Dataset) -> None:
        """The other end: an experiment claiming certainty overrides the data entirely."""
        calibrated = calibrate(
            full.spend_panel, {"social-pago": control_prior("social-pago", 100.0, 1e-6)}
        )
        index = calibrated.posterior.channels.index("social-pago")
        assert float(calibrated.posterior.coefficients[index]) == pytest.approx(100.0, rel=1e-12)

    def test_a_prior_claiming_exactness_is_refused_by_name(self, full: Dataset) -> None:
        """Zero width is not a strong claim, it is an impossible one."""
        with pytest.raises(ValueError, match="measured the coefficient exactly"):
            calibrate(full.spend_panel, {"social-pago": control_prior("social-pago", 100.0, 0.0)})

    def test_the_posterior_lies_between_the_two_claims_it_averages(self, full: Dataset) -> None:
        """A precision-weighted average cannot land outside the two numbers it weighs."""
        baseline = fit(full.spend_panel)
        index = baseline.channels.index("social-pago")
        least_squares = float(baseline.coefficients[index])
        for mean in (0.0, 60.0, 400.0):
            calibrated = calibrate(
                full.spend_panel, {"social-pago": control_prior("social-pago", mean, 20.0)}
            )
            posterior = float(calibrated.posterior.coefficients[index])
            assert min(mean, least_squares) <= posterior <= max(mean, least_squares)


class TestTheArithmeticOfTheTransfer:
    def test_one_prior_makes_the_precision_identity_exact(self, full: Dataset) -> None:
        """Sherman-Morrison, and it holds however correlated the columns are.

        Adding ``c`` to one diagonal entry of the information matrix changes that entry of the
        inverse to ``v / (1 + c v)``, which is ``1 / (1/v + c)``. So the posterior standard error of
        the one coefficient that got a prior is the precision sum exactly - not approximately, and
        not only on an orthogonal design.
        """
        baseline = fit(full.spend_panel)
        index = baseline.channels.index("email")
        own = float(baseline.standard_errors[index])
        for width in (5.0, 40.0, 500.0):
            calibrated = calibrate(full.spend_panel, {"email": control_prior("email", 30.0, width)})
            expected = 1.0 / math.sqrt(1.0 / own**2 + 1.0 / width**2)
            assert float(calibrated.posterior.standard_errors[index]) == pytest.approx(
                expected, rel=1e-12
            )
            assert calibrated.independent_widths["email"] == pytest.approx(
                2.0 * baseline.critical_value * expected, rel=1e-12
            )

    def test_several_priors_never_leave_an_interval_wider_than_the_identity(
        self, full: Dataset
    ) -> None:
        """Adding prior precision can only shrink the diagonal of the inverse, so it is a bound.

        The gap is the precision that arrives through the correlation between channels. Asserting
        the direction rather than a figure is deliberate: the direction is a theorem, and the size
        is a property of this spend plan.
        """
        priors = {
            name: control_prior(name, 50.0, 25.0)
            for name in ("social-pago", "email", "busca-generica")
        }
        calibrated = calibrate(full.spend_panel, priors)
        table = calibrated.table().set_index("channel")
        for name in calibrated.posterior.channels:
            assert (
                float(table.loc[name, "posterior_width"])
                <= calibrated.independent_widths[name] + 1e-9
            )

    def test_a_prior_on_the_least_squares_estimate_narrows_without_moving(
        self, full: Dataset
    ) -> None:
        """Location and width are separate transfers, and this is the case that separates them.

        The identity is exact in algebra: with the prior mean at the least squares estimate, the
        weighted average collapses to ``V (X'X/s2 + P) b`` and the two factors cancel. It is checked
        to 1e-9 rather than to the last bit because the two sides reach that estimate by different
        routes - one through a least squares solve, the other through an explicit inverse - and they
        agree to the twelfth digit. Demanding more would be testing the linear algebra library.
        """
        baseline = fit(full.spend_panel)
        index = baseline.channels.index("busca-generica")
        estimate = float(baseline.coefficients[index])
        calibrated = calibrate(
            full.spend_panel, {"busca-generica": control_prior("busca-generica", estimate, 30.0)}
        )
        assert float(calibrated.posterior.coefficients[index]) == pytest.approx(estimate, rel=1e-9)
        assert float(calibrated.posterior.standard_errors[index]) < float(
            baseline.standard_errors[index]
        )

    def test_believing_the_experiment_can_only_cost_in_sample_fit(self, full: Dataset) -> None:
        """Least squares is the best in-sample fit by construction, so a prior cannot improve it.

        Which is the reason in-sample fit cannot adjudicate a calibration: the calibrated model is
        always the worse fit, including when it is the closer answer.
        """
        baseline = fit(full.spend_panel)
        priors = {
            name: control_prior(name, 50.0, 15.0)
            for name in ("social-pago", "email", "busca-generica")
        }
        calibrated = calibrate(full.spend_panel, priors)
        assert calibrated.posterior.r_squared <= baseline.r_squared
        assert calibrated.posterior.residual_sd >= baseline.residual_sd


class TestBuildingThePriorFromAHoldout:
    def test_the_conversion_is_exactly_the_factor_it_reports(self, full: Dataset) -> None:
        prior = real_prior(full, "social-pago")
        assert prior.marginal_return * prior.conversion_factor == pytest.approx(
            prior.average_return, rel=1e-12
        )
        assert prior.conversion_factor == pytest.approx(
            average_to_marginal(MEDIA_MIX.saturation_at), rel=1e-12
        )

    def test_skipping_the_conversion_is_recorded_rather_than_silent(self, full: Dataset) -> None:
        """The naive calibration has to be identifiable from the object it produces."""
        naive = real_prior(full, "social-pago", convert=False)
        assert naive.conversion_factor == 1.0
        assert naive.marginal_return == pytest.approx(naive.average_return, rel=1e-15)
        assert "unconverted" in naive.source
        converted = real_prior(full, "social-pago")
        assert naive.mean == pytest.approx(
            converted.mean * average_to_marginal(MEDIA_MIX.saturation_at), rel=1e-12
        )

    def test_a_channel_with_no_spend_gets_a_refusal_and_not_a_ratio(self, full: Dataset) -> None:
        fitted = fit(full.spend_panel)
        prior = prior_from_holdout(
            holdout_of(full, "email"),
            fitted,
            "email",
            reach=float(AUDIENCE.users),
            spend=0.0,
        )
        assert not prior.usable
        assert "denominator" in prior.refused_because
        assert math.isnan(prior.mean)

    def test_a_channel_the_model_does_not_have_is_an_error_not_a_guess(self, full: Dataset) -> None:
        fitted = fit(full.spend_panel)
        with pytest.raises(ValueError, match="is not a channel of this fit"):
            prior_from_holdout(
                holdout_of(full, "email"),
                fitted,
                "tv",
                reach=float(AUDIENCE.users),
                spend=1_000.0,
            )

    def test_negative_spend_is_an_error(self, full: Dataset) -> None:
        fitted = fit(full.spend_panel)
        with pytest.raises(ValueError, match="spend cannot be negative"):
            prior_from_holdout(
                holdout_of(full, "email"),
                fitted,
                "email",
                reach=float(AUDIENCE.users),
                spend=-1.0,
            )


class TestTheTables:
    def test_the_calibration_table_has_its_columns_and_one_row_per_channel(
        self, full: Dataset
    ) -> None:
        calibrated = calibrate(full.spend_panel, {"email": control_prior("email", 30.0, 10.0)})
        table = calibrated.table()
        assert tuple(table.columns) == CALIBRATION_COLUMNS
        assert len(table) == len(calibrated.posterior.channels)
        row = table.set_index("channel").loc["email"]
        assert float(row["width_kept"]) < 1.0
        untouched = table.set_index("channel").loc["busca-marca"]
        assert math.isnan(float(untouched["prior_mean"]))
        assert float(untouched["width_kept"]) <= 1.0

    def test_the_transfer_table_marks_resolved_by_whether_the_interval_excludes_zero(
        self, full: Dataset
    ) -> None:
        calibrated = calibrate(full.spend_panel, {"email": control_prior("email", 30.0, 10.0)})
        table = calibrated.transfer(full.media_truth)
        assert tuple(table.columns) == TRANSFER_COLUMNS
        for _, row in table.iterrows():
            excludes = bool(row["low"] > 0 or row["high"] < 0)
            assert bool(row["resolved"]) is excludes

    def test_a_negative_interval_counts_as_resolved(self, full: Dataset) -> None:
        """Resolved means the data settled the sign, not that the answer is good news."""
        calibrated = calibrate(full.spend_panel, {"email": control_prior("email", -400.0, 5.0)})
        table = calibrated.transfer(full.media_truth).set_index("channel")
        assert float(table.loc["email", "high"]) < 0
        assert bool(table.loc["email", "resolved"])


class TestWhatTheTransferDoesOnThisAccount:
    def test_the_experiment_dominates_the_channels_it_covered(self, full: Dataset) -> None:
        """Not a published figure - the direction, which is the claim the wave rests on."""
        resolved = ["social-pago", "email", "busca-generica"]
        priors = {name: real_prior(full, name) for name in resolved}
        calibrated = calibrate(full.spend_panel, priors)
        table = calibrated.table().set_index("channel")
        for name in resolved:
            assert float(table.loc[name, "width_kept"]) < 0.10
            assert float(table.loc[name, "posterior_mean"]) == pytest.approx(
                priors[name].mean, rel=0.05
            )

    def test_the_naive_calibration_is_tighter_and_less_often_right(self, full: Dataset) -> None:
        """The wave's central claim, as a comparison rather than as a quoted figure."""
        resolved = ["social-pago", "email", "busca-generica"]
        good = calibrate(full.spend_panel, {n: real_prior(full, n) for n in resolved})
        naive = calibrate(
            full.spend_panel, {n: real_prior(full, n, convert=False) for n in resolved}
        )
        covered_good = int(good.transfer(full.media_truth)["covers_truth"].sum())
        covered_naive = int(naive.transfer(full.media_truth)["covers_truth"].sum())
        assert covered_naive < covered_good
        assert naive.posterior.r_squared < good.posterior.r_squared

    def test_a_null_holdout_is_information_rather_than_an_absence(self, full: Dataset) -> None:
        """The two channels the holdout could not resolve still carry a standard error."""
        baseline = fit(full.spend_panel)
        priors = {name: real_prior(full, name) for name in ("retargeting", "busca-marca")}
        for prior in priors.values():
            assert prior.usable
        calibrated = calibrate(full.spend_panel, priors)
        table = calibrated.table().set_index("channel")
        truth = calibrated.transfer(full.media_truth).set_index("channel")
        for name in priors:
            assert float(table.loc[name, "width_kept"]) < 0.20
            assert bool(truth.loc[name, "covers_truth"])
            assert not bool(truth.loc[name, "resolved"])
        assert baseline.channels == calibrated.posterior.channels

    def test_a_prior_on_one_channel_moves_the_others_more_than_it_narrows_them(
        self, full: Dataset
    ) -> None:
        """The spillover, as a direction: correlated spend spreads a prior's location, not its width.

        Asserting the ordering rather than the sizes, because the sizes are published figures and
        belong in the claims suite. What belongs here is that the effect exists and which way round
        it is - a deck can change materially on channels the experiment never touched, while the
        widths beside them barely move.
        """
        baseline = fit(full.spend_panel)
        calibrated = calibrate(full.spend_panel, {"social-pago": real_prior(full, "social-pago")})
        table = calibrated.table().set_index("channel")
        for name in ("email", "retargeting"):
            index = baseline.channels.index(name)
            before = float(baseline.coefficients[index])
            after = float(calibrated.posterior.coefficients[index])
            moved = abs(after - before) / abs(before)
            narrowed = 1.0 - float(table.loc[name, "width_kept"])
            assert moved > narrowed


def test_the_module_exports_what_the_examples_import() -> None:
    """A rename that breaks an example should break a fast test first."""
    import mktlab.calibration as module

    for name in (
        "CALIBRATION_COLUMNS",
        "TRANSFER_COLUMNS",
        "Calibrated",
        "Prior",
        "average_to_marginal",
        "calibrate",
        "prior_from_holdout",
        "saturation_multiple",
    ):
        assert hasattr(module, name), name
    assert set(module.__all__) == {
        "CALIBRATION_COLUMNS",
        "TRANSFER_COLUMNS",
        "Calibrated",
        "Prior",
        "average_to_marginal",
        "calibrate",
        "prior_from_holdout",
        "saturation_multiple",
    }


def test_the_posterior_is_not_a_new_dataset(full: Dataset) -> None:
    """Wave 6 adds no draws, so the panel it reads must be the one waves 1 to 5 published."""
    assert isinstance(full.spend_panel, pd.DataFrame)
    assert float(full.spend_panel["conversions"].iloc[0]) == pytest.approx(
        176.23144880744616, rel=1e-12
    )
    assert float(full.spend_panel["conversions"].sum()) == pytest.approx(
        21657.22859822624, rel=1e-12
    )
    assert not np.isnan(full.spend_panel.to_numpy(dtype=float)).any()
