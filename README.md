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

## Modules

| Module | What it decides |
| --- | --- |
| [`mktlab.attribution`](src/mktlab/attribution/README.md) | Who gets the credit under six models, what a geo holdout says instead, and the difference between ROAS and its incremental version. |
| [`mktlab.design`](src/mktlab/design/README.md) | Whether the test is worth running, whether it is being read the way it was sized, and what the plan for reading it should say. Three documents: [sizing](src/mktlab/design/README-sizing.md) — the precision it will have, the smallest **return** it can establish, what it costs if the channel works, and what a null result already ruled out; [repeated looks](src/mktlab/design/README-sequential.md) — what a weekly glance does to the error rate, what the two honest boundaries cost, and by how much an early stop inflates the number you report; and [monitoring](src/mktlab/design/README-monitoring.md) — an alpha-spending schedule for looks nobody agreed in advance, and a futility bound that ends a test going nowhere. |

Every module README is bilingual and carries an **Assumptions and limitations** section, because a
figure without its assumptions is not a result.

## Examples

| Example | What it shows |
| --- | --- |
| [`examples/01_who_gets_the_credit.py`](examples/01_who_gets_the_credit.py) | Six attribution models on one set of journeys, the Shapley identity, the conversions nobody touched, and the holdout that overrules all six. |
| [`examples/02_the_test_nobody_sized.py`](examples/02_the_test_nobody_sized.py) | The same holdout, priced before it ran: its precision, which channels it was always going to resolve, the return it could never have established, and what it cost. |
| [`examples/03_the_test_read_every_monday.py`](examples/03_the_test_read_every_monday.py) | The same holdout again, read weekly instead of once: the error rate that costs, the two boundaries that fix it, what they cost in regions, and the flattering estimate neither of them fixes. |
| [`examples/04_the_plan_nobody_wrote.py`](examples/04_the_plan_nobody_wrote.py) | The monitoring plan the holdout should have arrived with: the same error rate spent on four different reading schedules, the futility bound written down week by week, and what the right to give up costs. |

## Install and run

```bash
python -m pip install -e ".[dev]"
make check       # lint, types and the fast suite - what gates a push
make check-all   # the above plus every documented figure re-derived
python examples/01_who_gets_the_credit.py
python examples/02_the_test_nobody_sized.py
python examples/03_the_test_read_every_monday.py
python examples/04_the_plan_nobody_wrote.py
```

## How the claims are kept honest

**281 tests, 100% statement and branch coverage.** 232 of them run in seconds and gate every push.
The remaining 49 re-derive, from the generator, every figure quoted in every README on this
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
3. **Connecting the modules finds defects that writing more modules does not.** Seven of the eight
   defects recorded so far were found by writing an example, a control case or a sentence — not by
   reading code.
   They are recorded in the module documentation rather than quietly fixed — the return function
   once multiplied a channel's *share* by total conversions, which spreads the untouched
   conversions across the channels and is precisely the error the module exists to warn about.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for what is built, what is deliberately absent, and what is
still open.

## Licence

MIT. See [`LICENSE`](LICENSE).
