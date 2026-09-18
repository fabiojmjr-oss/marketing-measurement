# Roadmap

What is built, what is deliberately absent, and what is still open. One wave at a time, each one
ending in a state where every published figure is asserted by a test.

## Wave 1 — attribution against incrementality *(complete)*

The dataset, the six credit models, the Shapley identity, the conversions nobody touched, the geo
holdout, and ROAS next to iROAS.

| Delivered | Where |
| --- | --- |
| Seeded generator with a declared `intent` column, five channels, two of them with a true effect of zero | `src/mktlab/synth/` |
| Six attribution models, including the exact Shapley value of the coverage game | `src/mktlab/attribution/credit.py` |
| The conversions no model can see, and the rescaling that hides them | `credit.unattributable` |
| Geo holdout as a difference in differences on region-level rates, with Welch | `src/mktlab/attribution/incrementality.py` |
| ROAS, iROAS, and the refusal to publish a ratio against an unmeasured denominator | `incrementality.returns` |

**The one thread running through it:** at every step the figure a report shows is inflated in the
flattering direction for the channels that select on intent, and deflated for the channel that
creates demand — by an amount that is computable and that nobody computes.

### Defects found and recorded

Each was found by connecting the modules or by a control case, not by reading code. They are
documented in the module and the README rather than quietly fixed, because the class of mistake is
the point.

1. **`returns` rescaled a share instead of reading absolute credit.** It multiplied each channel's
   share by *total* conversions, which spreads the 1,974 untouched conversions across the channels
   — precisely the error `unattributable` exists to warn about, committed inside the module that
   warns about it. Found by checking the credited total against the attributable count.
2. **A two-region holdout arrived looking like a measured zero.** With one region on a side there
   is a mean and no spread, so the standard error was `nan` and `significant` was `False` — which
   reads downstream exactly like a channel that was measured and found to do nothing. Now the lift
   comes back with `untested_because` filled in. Found by running the estimator on the smallest
   design somebody might actually run.
3. **A noiseless control panel produced a warning instead of a number.** The Welch degrees of
   freedom came from scipy, whose ratio is 0/0 when both arms have zero variance. Now computed in
   closed form with the limit taken explicitly, and checked against scipy everywhere scipy is
   defined. Found because the noiseless panel is the first control case the geo tests use.

## Wave 2 — the test nobody sized *(complete)*

Wave 1 ran a holdout and read it. This wave asks what it was capable of finding, in advance, and
what its null results already established.

| Delivered | Where |
| --- | --- |
| The predicted standard error of a geo holdout, in closed form, before any data exists | `design.GeoDesign.standard_error` |
| Power from the noncentral t, with a lift of exactly zero returning alpha as a control case | `design.GeoDesign.power` |
| Minimum detectable lift, nudged up so the achieved power is never below the target | `design.GeoDesign.detectable_lift` |
| Minimum detectable **return**, and the width of the interval the test will produce | `detectable_iroas`, `return_precision` |
| Regions needed for a given lift, and the named refusal when regions are the wrong lever | `design.regions_for` |
| What the holdout costs if the channel works, including a population-free share | `design.holdout_cost` |
| The trade as one table, and the free precision of a longer pre-period | `design.sizing_table` |
| A null result read as a bound on the return, next to what the design could reach | `design.retrospective` |

**The thread from wave 1 continues, one level up.** Wave 1 showed that the figure a report shows is
a correct calculation of the wrong quantity. Wave 2 shows that the *test* meant to fix that is also
sized against the wrong quantity: everybody computes the minimum detectable lift, which is the same
for every channel in the account, and nobody computes the minimum detectable return, which differs
between them by a factor of nine and is the only one a budget can act on.

### Defects found and recorded

1. **A detectable lift printed under an "80% power" heading whose power was 0.799992.** The root
   finder lands within its tolerance, which can be a hair below the target. The lift is now nudged
   up until the achieved power is at or above what was asked for, the way a sample size is rounded
   up rather than to the nearest integer. Found by reading the example's own output table.
2. **A guard covering three cases that cannot happen.** The non-finite tail guard was written
   symmetrically, for both tails and both signs, when scipy fails on exactly one of the four. It is
   now narrowed to that case, and which case it is has become an assertion about scipy rather than
   an assumption inside the module. Found by a coverage report showing a branch no test could reach.
3. **A prose claim that did not follow from the numbers.** A draft of the module README said no
   design in its table could establish email's return as distinct from 3.00. Eighty regions can,
   which is why `return_precision` now exists: the claim needed the half-width of the interval, not
   the minimum detectable effect, and computing the right quantity was the fix. Found by checking a
   sentence I had already written.

## Wave 3 — the test read every Monday *(complete)*

Wave 2's sizing rests on an assumption it never states: that the test is read once, at the end. This
wave removes it.

| Delivered | Where |
| --- | --- |
| The Armitage-McPherson-Rowe recursion: the exact error rate of a boundary read several times | `sequential.crossing_probability` |
| The real false-positive rate of a fixed boundary read K times — 21.4% at thirteen weekly looks | `sequential.inflated_alpha` |
| Pocock's constant boundary and O'Brien and Fleming's declining one, solved to hold alpha exactly | `sequential.pocock`, `sequential.obrien_fleming` |
| Power, the effect a boundary needs, and the information that costs against reading once | `power`, `ncp_for_power`, `information_inflation` |
| How long the test runs on average under each rule | `sequential.expected_looks` |
| The four rules priced side by side, with the invalid one marked invalid | `sequential.peeking_table` |
| How much an early stop inflates the effect that gets reported | `sequential.exaggeration` |

**The thread, at its third level.** Wave 1: the figure a report shows is a correct calculation of the
wrong quantity. Wave 2: the test meant to fix that is sized against the wrong quantity. Wave 3: the
test is not even read the way it was sized — and when the reading is repaired, the *estimate* is still
flattering, in the same direction as everything else. Nothing here is a mistake anybody made. Each is
a decision rule nobody knew was in force.

### Defects found and recorded

1. **A column in the example that ran backwards.** "Regions needed to hold the same floor" showed
   *fewer* regions for the more expensive boundary, because the lift to detect had been inflated
   instead of the information. Information scales with regions; the effect does not. Found by reading
   the printed table and noticing the ordering was impossible.
2. **A control case returning 0.9999975 instead of 1.** The information cost of reading once has to
   be exactly one, and it was not, because the reference was the textbook ``z + z_power`` while the
   thing compared to it came out of the recursion. Those two differ by 3.4e-06 — the textbook formula
   ignores the probability of rejecting in the tail opposite the true effect. The fix was to compute
   the reference the same way as the thing being compared to it, rather than to round the output.
3. **A published nominal level off by three orders of magnitude.** A draft of the module README wrote
   O'Brien-Fleming's first nominal level as 1e-13 where it is 3.5e-14. It changes no argument, which
   is exactly why it would have survived: the claim tests now assert it.

## Wave 4 — the plan nobody wrote *(complete)*

Wave 3's boundaries hold the error rate, and both of them assume the looks are evenly spaced and known
before the test starts. Neither can end a test that is going nowhere. This wave removes both
limitations.

| Delivered | Where |
| --- | --- |
| The recursion generalised to unequal information, and to a lower boundary as well as an upper one | `sequential._recursion` |
| Alpha spending: O'Brien-Fleming-like, Pocock-like, and the power family as a dial between them | `alpha_spent`, `spending_boundary` |
| Futility by beta spending, solved against a declared alternative | `beta_spent`, `futility_boundary` |
| The probability of abandoning a test, which under the alternative is the power it costs | `futility_probability` |
| A monitoring plan as an object, and the schedule table a team has to be handed | `MonitoringPlan`, `monitoring_plan`, `schedule` |
| A measured floor on how close two reads may be before the quadrature fails | `MIN_INCREMENT` |

**The thread, at its fourth level.** Wave 1: the figure a report shows is a correct calculation of the
wrong quantity. Wave 2: the test meant to fix that is sized against the wrong quantity. Wave 3: the
test is not read the way it was sized. Wave 4: the boundary that fixes the reading assumes a schedule
nobody keeps, and the plan that fixes *that* has a price — 8.9% more information and a 23.4% chance of
abandoning a winner — which is the first honest cost in the whole arc that is small enough to simply
pay.

### Defects found and recorded

1. **This roadmap claimed futility would save the conversions wave 2 priced. It does not, and wave
   2's own arithmetic says so.** The cost of a holdout is the held-out population times the channel's
   *real* lift, so a channel doing nothing costs nothing to hold out — which is exactly the case a
   futility bound fires on. What it saves there is calendar: about seven weeks, twenty regions kept
   from a channel nobody can act on, and a decision that cannot be taken while the test runs. The 115
   conversions that early stopping does save on a channel that works are the *efficacy* boundary's
   doing. The claim had the mechanism backwards and is corrected in
   [`README-monitoring.md`](../src/mktlab/design/README-monitoring.md) rather than deleted.
2. **A plan with no futility bound reported twice the error rate it was built for.** Storing "nothing"
   for "cannot give up" collided with the recursion's convention, where an absent futility bound means
   the two-sided test wave 3 is built on — so a boundary solved to spend a one-sided 0.025 reported
   0.0500. A plan that cannot abandon now carries an unreachable bound rather than a missing one, and
   `can_abandon` says which kind it is. Found by reading the verdict line of the very first plan built.
3. **A control case returned −1.17 as a probability.** Two looks taken an instant apart in information
   should change nothing, and instead the convolution kernel narrowed to a spike the quadrature could
   not represent. The behaviour is now measured rather than guessed — smooth and correct down to a gap
   of 2e-04 of the information, wrong at 1e-04, nonsense at 1e-05 — and gaps below a floor five times
   above the last good value are refused by name. Found by writing the control case, not by reading
   code.

## The reproducibility fix *(after wave 3)*

The repository's central promise is that the default seed reproduces every published number. It did
not. The first three waves were published from a machine whose figures a clean install did not
reproduce: the attribution tables matched to the last decimal while every figure downstream of the
geo panel's binomial moved.

**What changed.** Every draw now goes through `src/mktlab/synth/_draws.py`, and nothing there samples
by rejection: intent comes from a beta quantile, region levels and stage noise from a normal
quantile, the holdout split from sorted uniform keys, and each region-week's conversions from one
Bernoulli trial per user — about ten million uniforms for the whole panel, which costs a second. The
number of uniforms consumed now depends only on how many values are asked for, so the stream position
cannot drift with a library version. A test reads the package and fails if any module calls a
distribution method other than `random`, and it immediately caught a second instance nobody had
looked for: the exaggeration simulation in `design.sequential` was using `standard_normal`, which is
the ziggurat algorithm and rejects.

**What is honest about the diagnosis.** The mechanism fits the evidence and was not observed. The
two environments differed in their numpy version, and the newer one could not be installed on the
interpreter available for testing, so the divergence was never reproduced side by side. The fix
removes the class rather than the instance, which is the right response to a defect whose exact
cause cannot be pinned down.

**What it cost.** Every data-dependent figure in waves 1 to 3 moved and was rewritten — four module
documents, two root READMEs, three examples and the claim tests. Two of the rewrites changed what the
documents *say*, not just what they quote, and both are better for it:

- One holdout interval of five no longer covers the truth. A 95% interval is wrong one time in twenty
  by construction, five were computed, and the miss is 2.6 predicted standard errors out on the
  channel with the largest effect. The document now publishes the miss and says why an estimator that
  never missed would be one whose intervals were too wide.
- The two null results are no longer the same kind of null. busca-marca's design could resolve the
  range its answer turned out to sit in; retargeting's could not. That pair says more about sizing
  than the old coincidence did.

**What the pins are now.** The first uniform of the stream is asserted directly, and both the first
values and the sums of the generated tables are pinned — because a first row can match by coincidence
while everything after it has moved, which is exactly what happened here and is why the original pin
did not catch it.

## Wave 5 — the model that replaces the experiment *(complete)*

Waves 2 to 4 priced the holdout honestly, and every one of those prices is a reason somebody refuses
to run it. This wave fits what gets built instead, on the same account, and asks what it can support.

| Delivered | Where |
| --- | --- |
| A weekly spend panel with a declared `baseline`, a shared budget swing and a per-channel one | `synth.spend_panel` |
| The truth the panel was built from, as average *and* marginal return per unit of spend | `synth.media_truth` |
| Adstock and Hill saturation as the generator applies them, so a model can be handed the right ones | `synth.adstock`, `synth.saturate` |
| Variance inflation per channel, and the condition number of the **centred** design | `mmm.variance_inflation`, `mmm.design_matrix` |
| The fit with coefficients, standard errors, p-values, intervals and the returns they imply | `mmm.fit`, `Fit.table`, `Fit.returns` |
| The range of coefficients that fits within a tolerated loss, and its closed form | `Fit.equivalent_range` |
| A grid over the two unobservable transforms, ranked by fit and by the return each implies | `mmm.transform_grid` |

**The thread, at its fifth level.** Wave 1: the figure a report shows is a correct calculation of the
wrong quantity. Wave 2: the test meant to fix that is sized against the wrong quantity. Wave 3: it is
not read the way it was sized. Wave 4: the plan that repairs the reading has a price. Wave 5: the
instrument built to avoid paying that price is, on this account and under the best conditions it will
ever get, **eleven to thirteen times wider than the test it replaces** — and it is the one usually
presented without its width.

The result that surprised me is the one about the transforms. The complaint that "the carryover and
the saturation are guesses, so the answer is a guess" is half wrong: the fit identifies the carryover
well enough to matter, and is nearly blind to the saturation point — which in this panel is the
parameter that barely moves the answer. The grid says which half of the slogan is true.

### Defects found and recorded

1. **A condition number of 69.1 that was an artefact of not centring.** Computed on the raw
   transformed columns it reads as most of the way to the conventional warning line, and essentially
   all of it is the columns' common mean rather than any relationship between the channels. Centred,
   it is **7.01** — and the honest reading is the uncomfortable one: the alarm everybody checks does
   not go off here, while the diagnostic that does bite, the variance inflation, says every interval
   is two and a half to three times wider than it would have been on independent spend. Found by
   trying to write the sentence that interpreted the number.
2. **A variance inflation of 2.7e+30 for a column duplicated exactly.** The right answer is
   infinity. A regression of one column on its own copy leaves a residual sum of squares that is
   floating-point noise rather than zero, and 1/(1−R²) obediently returns a very large finite number
   — which reads as a very high but finite diagnostic rather than as the refusal it should be.
   Perfect collinearity is now detected by a declared tolerance and reported as infinite. Found by
   the control case, which is the only place the answer is known in advance.
3. **Two of my own test helpers were wrong, and the module was right.** One checked the recovery of a
   marginal return against an absolute half point per channel, which called a 1.4% error a failure;
   the other compared two independent draws as though one should be ten times the other. Both were
   demands the mathematics does not make, written while looking at the module instead of at the
   quantity. A test that fails for the wrong reason costs the same as one that passes for the wrong
   reason, and it is the more flattering failure because fixing it feels like progress.
4. **Four sentences in the example that the tables did not support.** Written in the same pass as the
   tables they described: a correlation range quoted wider than the matrix, a count of sign flips that
   included a channel whose truth is zero, a fit-loss figure attached to the wrong comparison, and
   "answers about one channel" where the model answers about five and *resolves* one. None changes a
   conclusion, which is precisely why each would have survived; all four are now quoted from the
   claim tests instead of from memory.

## What is deliberately not here

- **No market statistics, industry benchmarks or third-party figures.** Every number in this
  repository comes from the seeded generator. A benchmark quoted from memory cannot be put under
  test, and this repository's only real discipline is that its figures are asserted.
- **No platform API clients.** Nothing here reads an advertising account, and nothing is designed
  to. See [`DISCLAIMER.md`](../DISCLAIMER.md).
- **No Bayesian media mix model, and no priors.** Wave 5's model is ordinary least squares on
  purpose: a prior narrows an interval, and the point of the wave is how wide the interval honestly
  is before anybody narrows it. A prior that does the narrowing is the next wave's subject, not a
  way to improve this one's figures.
- **No budget optimiser.** An optimiser on top of wave 5's coefficients would return a confident
  allocation from a model that distinguishes one channel of five from zero, which is the failure the
  wave documents rather than a feature to build on it.
- **No dashboards.** The output is tables and a decision, which is what survives being pasted into
  a document.

## Still open

- **Estimating the spread from the account's own history rather than assuming it.** Wave 2's closed
  form is a floor on the noise, because real regions carry autocorrelation and region-specific
  seasonality. The distance between that floor and a spread measured from the pre-period is itself
  the interesting number, and it is how a sizing stops being optimistic.
- **A bias-adjusted estimate at the stopping time.** Wave 3 measures the exaggeration and does not
  repair it, so its honest use is as an argument against stopping early rather than as a correction
  factor.
- **Binding futility, which recovers the error rate the non-binding version gives back.** Wave 4's
  plans spend 0.0224 of an intended 0.025 because the efficacy boundary is solved as though the test
  could never be abandoned. Re-solving it against the futility bound is more efficient and only holds
  if the bound is obeyed, which is a governance question before it is a statistical one.
- **Information time estimated rather than assumed.** A spending function evaluated at a mis-stated
  information fraction spends the wrong amount of error, and in a geo test the fraction has to be
  inferred from the same accumulation that drives the statistic.
- **Calibrating the model with the experiment instead of choosing between them.** Wave 5 compares
  the two instruments and stops there. The interesting construction is the holdout's average return
  entering the model as information about the coefficient — which is what an informative prior is
  for, and is the honest use of a test that resolved three channels of five.
- **Out-of-sample validation, because every fit figure in wave 5 is in-sample.** A fit loss of
  0.0047 between two carryover values says the data prefers one; it does not say the preference
  would survive on weeks the model has not seen, and a rolling-origin evaluation is how that is
  settled.
- **Spend that was set by the answer.** The panel's budget swings for reasons unrelated to how the
  channels perform. Real plans move spend towards what last quarter's report credited, which puts
  the model's own output on the right-hand side of its next fit.
- **Lifetime value and survivorship.** Cohorts measured on the customers who are still there.
- **Consent and the missing rows.** Measurement bias when the users who refuse tracking are not the
  users who convert.
