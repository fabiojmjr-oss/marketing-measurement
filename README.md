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
| email | +0.010 | 0.1605 | **25.16** | 5.2165 | yes |
| retargeting | **0.000** | 0.1805 | **9.43** | 0.3773 | **no** |
| busca-marca | **0.000** | 0.2311 | **8.05** | −0.2892 | **no** |
| busca-generica | +0.030 | 0.2213 | 5.78 | 1.8398 | yes |
| social-pago | +0.060 | 0.2067 | **3.60** | **5.6981** | yes |

Read top to bottom, that is the ranking the report shows. The two channels in second and third
place have no established incremental return at all — **31.9% of a 470,000 budget** — and the
channel ranked last is the only one that creates demand rather than harvesting it. Blended, the
account reports **ROAS 6.6711 against iROAS 2.8667**.

Three more results from the same dataset:

- **Last-click gives the two channels with no effect 41.16% of the credit**, and makes the one with
  the steepest intent-based targeting the single largest line in the account.
- **First-click and last-click disagree by up to 7.67×** on the same journeys. Only the rule
  changed.
- **The Shapley value of the journey coverage game is exactly linear attribution.** Computed the
  long way, over every coalition: the largest difference is 9.09e-13 conversions out of 17,419. The
  "data-driven" model is divide-by-n, and it is provably indifferent to the order of the touches it
  is sold as understanding.

## Modules

| Module | What it decides |
| --- | --- |
| [`mktlab.attribution`](src/mktlab/attribution/README.md) | Who gets the credit under six models, what a geo holdout says instead, and the difference between ROAS and its incremental version. |

Every module README is bilingual and carries an **Assumptions and limitations** section, because a
figure without its assumptions is not a result.

## Examples

| Example | What it shows |
| --- | --- |
| [`examples/01_who_gets_the_credit.py`](examples/01_who_gets_the_credit.py) | Six attribution models on one set of journeys, the Shapley identity, the conversions nobody touched, and the holdout that overrules all six. |

## Install and run

```bash
python -m pip install -e ".[dev]"
make check       # lint, types and the fast suite - what gates a push
make check-all   # the above plus every documented figure re-derived
python examples/01_who_gets_the_credit.py
```

## How the claims are kept honest

**100 tests, 100% statement and branch coverage.** 85 of them run in seconds and gate every push.
The remaining 15 re-derive, from the generator, every figure quoted in every README on this
repository, and run every example script. A change that moves a published number breaks the build
instead of leaving the text quietly wrong.

Three disciplines, each of which was adopted after it caught something:

1. **Verification against closed forms and control cases, never against the code's own output.**
   The attribution models are checked against allocations worked out on paper as exact fractions;
   the geo estimator against a noiseless panel whose difference in differences is exactly +0.04,
   with a common trend and a permanent between-region difference added to confirm neither reaches
   the estimate; the generator's mean rates against the analytic expectation they close to.
2. **Figures are asserted, not quoted.** Including the ones about the repository itself: the test
   count above, the module table matching the package, both language editions existing, and every
   example being linked from somewhere.
3. **Connecting the modules finds defects that writing more modules does not.** Two of this wave's
   three defects were found by writing the example and the control cases, not by reading the code.
   They are recorded in the module documentation rather than quietly fixed — the return function
   once multiplied a channel's *share* by total conversions, which spreads the untouched
   conversions across the channels and is precisely the error the module exists to warn about.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for what is built, what is deliberately absent, and what is
still open.

## Licence

MIT. See [`LICENSE`](LICENSE).
