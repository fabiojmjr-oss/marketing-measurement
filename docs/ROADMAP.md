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

## What is deliberately not here

- **No market statistics, industry benchmarks or third-party figures.** Every number in this
  repository comes from the seeded generator. A benchmark quoted from memory cannot be put under
  test, and this repository's only real discipline is that its figures are asserted.
- **No platform API clients.** Nothing here reads an advertising account, and nothing is designed
  to. See [`DISCLAIMER.md`](../DISCLAIMER.md).
- **No media mix model yet.** Not because it is uninteresting — because it is the easiest place in
  marketing measurement to produce a confident wrong number, and it deserves a wave of its own with
  its collinearity made visible rather than a module bolted on here.
- **No dashboards.** The output is tables and a decision, which is what survives being pasted into
  a document.

## Still open

- **Estimating the spread from the account's own history rather than assuming it.** Wave 2's closed
  form is a floor on the noise, because real regions carry autocorrelation and region-specific
  seasonality. The distance between that floor and a spread measured from the pre-period is itself
  the interesting number, and it is how a sizing stops being optimistic.
- **Alpha spending, and futility.** Wave 3's boundaries assume equal information between looks and
  can only stop a test for succeeding. A Lan-DeMets spending function handles unequal spacing, and a
  futility boundary is what would actually save the forgone conversions wave 2 priced — a test that
  cannot win should end early, and nothing here can end it.
- **A bias-adjusted estimate at the stopping time.** Wave 3 measures the exaggeration and does not
  repair it, so its honest use is as an argument against stopping early rather than as a correction
  factor.
- **Media mix modelling and collinearity.** Channels whose spend moves together, and what a model
  reports about a coefficient it cannot identify.
- **Lifetime value and survivorship.** Cohorts measured on the customers who are still there.
- **Consent and the missing rows.** Measurement bias when the users who refuse tracking are not the
  users who convert.
