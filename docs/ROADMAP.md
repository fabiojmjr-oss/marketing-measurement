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

- **Sizing the test before running it.** The holdout in wave 1 resolved three effects out of five.
  Which of those two failures was the design's fault is answerable in advance, and a test run
  without that answer is a thirteen-week bet nobody priced.
- **Peeking.** A test declared on the first favourable day, and the error rate that costs, against
  a sequential rule that keeps it.
- **Media mix modelling and collinearity.** Channels whose spend moves together, and what a model
  reports about a coefficient it cannot identify.
- **Lifetime value and survivorship.** Cohorts measured on the customers who are still there.
- **Consent and the missing rows.** Measurement bias when the users who refuse tracking are not the
  users who convert.
