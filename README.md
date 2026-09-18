# marketing-measurement

*[Português](README.pt-BR.md)*

**Almost every figure in a marketing report is a correct calculation of the wrong quantity.**

Attribution allocates credit without a counterfactual. Return on ad spend counts revenue that was
coming anyway. A test declared on the first favourable Monday has spent its error rate several
times over. None of those are arithmetic mistakes — each is the right arithmetic applied to a
quantity nobody chose deliberately, and each becomes visible the moment the quantity is written
down as arithmetic rather than as a slide.

This repository is that exercise. `mktlab` is a Python package whose tools each answer a decision a
budget has to take, and which **refuse to return a number when the assumption behind it does not
hold** — a ratio against an unmeasured denominator comes back as `nan` with a reason attached,
rather than as a figure that reads like evidence.

Every table comes from `mktlab.synth`, a seeded generator whose parameters are written down,
including the one column no real advertising account has: **how likely each user was to convert
before any marketing happened.** That column is why the claims here can be checked against the
truth instead of against another model. No advertiser, agency, platform or client data is used
anywhere — see [`DISCLAIMER.md`](DISCLAIMER.md).

## The finding, in one table

Five channels. Two of them have a true effect of exactly zero, because they are shown to people who
were already going to convert. Last-click credit against what a geo holdout establishes:

| Channel | True effect | Last-click share | ROAS | iROAS | Holdout established it? |
| --- | --- | --- | --- | --- | --- |
| email | +0.010 | 0.1717 | **26.96** | 8.2904 | yes |
| retargeting | **0.000** | 0.1800 | **9.42** | 0.2377 | **no** |
| busca-marca | **0.000** | 0.2322 | **8.10** | 0.5369 | **no** |
| busca-generica | +0.030 | 0.2145 | 5.61 | 2.1265 | yes |
| social-pago | +0.060 | 0.2015 | **3.52** | 5.8173 | yes |

Read top to bottom, that is the ranking the report shows. The two channels in second and third
place have no established incremental return at all — **31.9% of a 470,000 budget** — and the
channel ranked last is the only one that creates demand rather than harvesting it, with the only
ROAS-to-iROAS ratio below one. Blended, the account reports **ROAS 6.6814 against iROAS 3.2568**.

Three more results from the same dataset:

- **Last-click gives the two channels with no effect 41.22% of the credit**, and makes the one with
  the steepest intent-based targeting the single largest line in the account.
- **First-click and last-click disagree by up to 7.01×** on the same journeys. Only the rule
  changed.
- **The Shapley value of the journey coverage game is exactly linear attribution.** Computed the
  long way, over every coalition: the largest difference is 1.8e-12 conversions out of 17,446. The
  "data-driven" model is divide-by-n, and it is provably indifferent to the order of the touches it
  is sold as understanding.
- **10.16% of the conversions have no touch at all**, and every model silently drops or rescales
  them.

## And the test that produced the right-hand columns was never sized

The holdout above resolved three channels of five. Every part of that was computable before a single
region was switched off — including the part nobody computes:

- **The minimum detectable lift is identical for all five channels, and the minimum detectable
  *return* differs by a factor of nine.** The same test, the same weeks: it resolves returns down to
  0.47 on the largest channel and can establish nothing below **4.25** on the smallest. Email's true
  return of 5.76 comes back as "somewhere between 2.8 and 8.8".
- **A null result on a small channel buys an upper bound and little else.** The retargeting holdout
  ruled out returns above 1.0745 — a real fact, thirteen weeks of it — while the design could not
  have established any return below 1.4166: there was no return it could both miss and detect. Those
  two numbers are always of the same size, which is the general statement.
- **The holdout costs nothing on the channels that do nothing**, and gives up 27.64% of the held-out
  regions' conversions on the channel it matters most to keep.
- **Half the design is free and it is the half nobody extends.** A longer pre-period holds nobody
  out and enters the standard error exactly as the post-period does. An unlimited one is worth
  *exactly* as much as doubling the number of regions — 0.000582 either way, equal rather than
  close, because both halve the same variance.

## And nobody reads a test once

That sizing rests on an assumption it never states: that the holdout is read once, at the end. It
runs for thirteen weeks on a dashboard.

- **Thirteen weekly glances at the usual 1.96 make the false-positive rate 21.4%, not 5%** — a
  channel that does nothing is declared a winner about one time in five. The curve is steepest at the
  start: looking *twice* already costs 66% more error than the design allows.
- **The honest fix costs 2.1% of the detectable return.** An O'Brien-Fleming boundary holds the error
  rate at exactly 5% across all thirteen readings for 4.3% more information — two extra regions out
  of twenty-four. Pocock's version costs eight regions and buys the right to stop in week one.
- **Its first boundary is 7.58 standard errors**, which is the design saying that nothing observable
  in week one should end a thirteen-week test.
- **And a correct boundary fixes the error rate only.** At equal power, reading once overstates a
  real effect by 13% — publication is conditional on significance — O'Brien-Fleming by 27%, Pocock by
  48%, and weekly peeking by **73%**. On an underpowered test, read weekly, the reported effect is
  **2.63 times** the truth and 3.9% of the results that clear the line point the wrong way.

## And the plan for reading it can be written down

Both of those boundaries assume the looks are evenly spaced and known before the test starts, and
neither can end a test that is going nowhere.

- **An alpha-spending schedule fixes the first.** Commit to how much error may be spent by each point
  in the accumulation of information, and the boundary follows — so thirteen weekly reads, three
  monthly ones, four starting halfway through, or a single read at the end all spend **exactly
  0.025**, and the last of those returns 1.96.
- **A futility bound fixes the second, and its price is the first honest cost in this arc small
  enough to simply pay:** on a channel doing nothing the test ends after **six** weekly reads instead
  of thirteen, for **8.9% more information** and a **23.4% chance of abandoning a test that would
  have worked**.
- **And it saves calendar, not conversions** — which this repository's own roadmap got backwards. A
  channel doing nothing costs nothing to hold out, so the case futility fires on is the case with no
  conversion cost to save. What it saves is seven weeks and twenty regions.

## And the model built instead resolves one channel of five

Every one of those costs is a reason somebody says no to the experiment, and a media mix model is
what gets built instead: a regression of weekly conversions on weekly spend, no regions switched
off, no conversions given up, an answer for every channel at once. Fitted here on the same account
and handed **the generator's own carryover and saturation** — a favour no real model receives.

- **The panel decides the answer before the modelling starts.** The five spend series correlate
  0.8305 to 0.8789, because a media plan is written as shares of a budget and the channels move when
  the budget does. Variance inflation runs 5.7315 to 8.5249, which multiplies every standard error
  by 2.39 to 2.92. The condition number of the centred design is **7.01** — comfortably inside the
  conventional warning line, which is why the alarm that does not go off is not evidence.
- **With the right transforms it resolves one channel of five.** R-squared 0.8364 and a residual
  standard deviation of 8.718 against a generator noise of 9.0: the fit has recovered the noise
  floor. All five intervals contain the truth, one excludes zero, and on the three channels that
  work the interval is **1.64, 5.38 and 14.10 times** the return it is estimating.
- **The range of coefficients that fits equally well *is* the confidence interval.** The profile has
  a closed form — the furthest a coefficient travels while the residual sum of squares rises by δ is
  its standard error rescaled — so the 95% interval is exactly the set of values costing **0.0068 of
  R-squared**. There is no second diagnostic hiding behind the standard error.
- **One of the two unobservable transforms is recoverable and the other is not.** Eight of twenty
  designs fit within 0.01 of the best, implying returns from **1.18× to 1.54×** the truth. But the
  fit identifies the carryover: moving it from 0.45 to 0.60 costs 0.0047 of R-squared and moves the
  return by a quarter, while at the right carryover the whole saturation range 0.5 to 10.0 — a
  twentyfold span — sits within 0.0008 of the best fit and moves the return by **one per cent**.
- **Drop the trend and the seasonality and two of the three working channels come back negative.**
  R-squared falls from 0.8364 to **0.2371**, busca-generica returns −2.10× its truth and email
  −5.18×, and social-pago is confidently 1.85× — confidently, because that interval still excludes
  zero. **Every interval still covers the truth.** Coverage does not catch a model that is wrong
  about the sign of most of an account; intervals that wide cover almost anything.
- **Against the holdout, per unit of the quantity each one estimates, the model is 11.5 to 13.1
  times wider.** The holdout resolved three channels of five and cost 260 region-weeks per channel;
  the model resolved one and cost nothing. That is a trade, not a verdict — and only one of the two
  instruments is usually presented with its width attached.

## And the honest way to use both makes the model as right as the experiment, exactly

That leaves a choice nobody wants: the holdout is narrow, expensive and covers three channels; the
model is free, covers five and is thirteen times wider. The construction that refuses the choice is
to use both — the experiment's estimate enters the model as a prior on the coefficient. It works, and
what it carries in with the precision is the wave's subject.

- **The two instruments do not estimate the same quantity, and the bridge between them is a
  parameter the data cannot settle.** A holdout measures the average return over the period; a
  coefficient is the marginal return at current spend. For a bending response the ratio is exactly
  **1 + 1/k** in the saturation point — 1.7692307692 at the generator's 1.30, which is the
  generator's own ratio of its two declared return columns to twelve digits, from code that shares
  nothing with the formula. Across the saturation range wave 5 showed the fit cannot distinguish,
  that factor runs from **3.0 to 1.1**.
- **It works: three channels of five resolved instead of one, twelve to thirteen times tighter.** And
  the posterior means land within half a per cent of the priors, so the model's own contribution to
  those three channels rounds to nothing. In-sample fit moves by **0.000374** of R-squared, which is
  why fit cannot adjudicate a calibration in either direction.
- **And it gave up a covering interval.** Five of five intervals covered the truth before, four of
  five after. Nothing was manufactured: a 95% interval is wrong one time in twenty, wave 1 computed
  five, and social-pago's is the one. The model's own interval **did** cover the truth and was
  overruled anyway, carrying **0.55%** of the weight. Calibration is not a way to be right more often
  than the experiment — it is a way to be as right as the experiment, cheaply, and exactly as wrong.
- **Skip the unit conversion and the same machinery manufactures a confident wrong answer.** One
  division left out: four channels resolved instead of three, **one interval of five covering the
  truth**, every estimate inflated by about the factor that was skipped, and busca-marca — true
  effect exactly zero — carrying an interval that excludes zero *from below*. Precision and bias
  transfer with equal efficiency.
- **A null result was the most precise thing anybody knew about the two channels it "could not
  resolve".** Used as priors, retargeting and busca-marca keep **7.0% and 9.1%** of their width,
  both intervals cover the truth of zero, and neither is falsely resolved. The inconclusive result
  was never an absence; it was an estimate with a standard error eleven to fourteen times tighter
  than the model's.
- **And a prior on one channel is not a claim about one channel.** One experiment, on social-pago
  only: email's reported return moves **1.76×** and retargeting's **2.33×** — while every width
  beside them moves by less than five per cent. The transfer arrives as a shift in location that
  nothing on the chart marks.
- **Then the whole thing rests on the parameter the fit cannot see.** Repeat the transfer at four
  saturation points spanning **0.000754** of R-squared and the calibrated answer runs **0.64× to
  1.72×** the truth. The best-fitting point is not the true one: it is k = 3.0, returning 1.42× the
  truth. A practitioner choosing the saturation point by fit — the only way it can be chosen — lands
  there.

## Modules

| Module | What it decides |
| --- | --- |
| [`mktlab.attribution`](src/mktlab/attribution/README.md) | Who gets the credit under six models, what a geo holdout says instead, and the difference between ROAS and its incremental version. |
| [`mktlab.design`](src/mktlab/design/README.md) | Whether the test is worth running, whether it is being read the way it was sized, and what the plan for reading it should say. Three documents: [sizing](src/mktlab/design/README-sizing.md) — the precision it will have, the smallest **return** it can establish, what it costs if the channel works, and what a null result already ruled out; [repeated looks](src/mktlab/design/README-sequential.md) — what a weekly glance does to the error rate, what the two honest boundaries cost, and by how much an early stop inflates the number you report; and [monitoring](src/mktlab/design/README-monitoring.md) — an alpha-spending schedule for looks nobody agreed in advance, and a futility bound that ends a test going nowhere. |
| [`mktlab.mmm`](src/mktlab/mmm/README.md) | What a regression of conversions on spend can support when nobody will switch a region off: whether the spend plan permits an answer at all, how much of the answer came from the transforms that were guessed, and how the width compares with the experiment it replaces. |
| [`mktlab.calibration`](src/mktlab/calibration/README.md) | Whether the experiment already run can make the model usable, what the transfer carries in along with the precision, and what still has to be assumed to move an answer from one instrument to the other. |

Every module README is bilingual and carries an **Assumptions and limitations** section, because a
figure without its assumptions is not a result.

## Examples

| Example | What it shows |
| --- | --- |
| [`examples/01_who_gets_the_credit.py`](examples/01_who_gets_the_credit.py) | Six attribution models on one set of journeys, the Shapley identity, the conversions nobody touched, and the holdout that overrules all six. |
| [`examples/02_the_test_nobody_sized.py`](examples/02_the_test_nobody_sized.py) | The same holdout, priced before it ran: its precision, which channels it was always going to resolve, the return it could never have established, and what it cost. |
| [`examples/03_the_test_read_every_monday.py`](examples/03_the_test_read_every_monday.py) | The same holdout again, read weekly instead of once: the error rate that costs, the two boundaries that fix it, what they cost in regions, and the flattering estimate neither of them fixes. |
| [`examples/04_the_plan_nobody_wrote.py`](examples/04_the_plan_nobody_wrote.py) | The monitoring plan the holdout should have arrived with: the same error rate spent on four different reading schedules, the futility bound written down week by week, and what the right to give up costs. |
| [`examples/05_the_model_that_replaces_the_experiment.py`](examples/05_the_model_that_replaces_the_experiment.py) | The model built when the holdout is refused, on the same account and with the generator's own transforms handed to it: what the spend plan already decided, the one channel it resolves, the range that fits equally well, and what the misspecification every real model has does to the signs. |
| [`examples/06_the_experiment_the_model_believes.py`](examples/06_the_experiment_the_model_believes.py) | The holdout put into the model as a prior: the unit conversion between the two instruments, what a skipped conversion buys, the experiment's own error once the model believes it, and what one prior does to the four channels nobody measured. |

## Install and run

```bash
python -m pip install -e ".[dev]"
make check       # lint, types and the fast suite - what gates a push
make check-all   # the above plus every documented figure re-derived
python examples/01_who_gets_the_credit.py
python examples/02_the_test_nobody_sized.py
python examples/03_the_test_read_every_monday.py
python examples/04_the_plan_nobody_wrote.py
python examples/05_the_model_that_replaces_the_experiment.py
python examples/06_the_experiment_the_model_believes.py
```

## How the claims are kept honest

**377 tests, 100% statement and branch coverage.** 306 of them run in seconds and gate every push.
The remaining 71 re-derive, from the generator, every figure quoted in every README on this
repository, and run every example script. A change that moves a published number breaks the build
instead of leaving the text quietly wrong.

Three disciplines, each of which was adopted after it caught something:

1. **Verification against closed forms and control cases, never against the code's own output.**
   The attribution models are checked against allocations worked out on paper as exact fractions;
   the geo estimator against a noiseless panel whose difference in differences is exactly +0.04,
   with a common trend and a permanent between-region difference added to confirm neither reaches
   the estimate; the generator's mean rates against the analytic expectation they close to; the
   power function against its own control case, where a lift of exactly zero must return alpha to
   twelve decimal places; the predicted standard error against the five panels that were actually
   simulated; and the repeated-looks recursion against a single look reducing to the fixed-sample
   test, against its own convergence at 100, 300 and 600 quadrature nodes, against the classical
   published boundaries, and against a four-million-draw simulation.
2. **Figures are asserted, not quoted.** Including the ones about the repository itself: the test
   count above, the module table matching the package, both language editions existing, and every
   example being linked from somewhere. And including the claim that makes the rest possible:
   **every draw in the generator is an inverse transform of the uniform stream, never a rejection
   sampler**, so the stream position depends on how many values are asked for and not on which
   library version answers. That rule is enforced against the source, because the first version of
   this repository published figures that held on one machine and moved on a clean install.
3. **Connecting the modules finds defects that writing more modules does not.** Nineteen of the twenty-one
   defects recorded so far were found by writing an example, a control case or a sentence — not by
   reading code. The two exceptions were a coverage report showing a branch no test could reach, and
   a clean install that did not reproduce the published figures.
   They are recorded in the module documentation rather than quietly fixed — the return function
   once multiplied a channel's *share* by total conversions, which spreads the untouched
   conversions across the channels and is precisely the error the module exists to warn about.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for what is built, what is deliberately absent, and what is
still open.

## Licence

MIT. See [`LICENSE`](LICENSE).
