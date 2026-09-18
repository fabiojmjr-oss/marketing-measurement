# `mktlab.calibration` — the experiment the model believes

*[Português](#mktlabcalibration--o-experimento-em-que-o-modelo-acredita)*

## The business problem

Wave 5 ended in a choice nobody wants to make. The holdout answers narrowly about the channels it
covered, costs conversions, and takes thirteen weeks. The model answers about every channel, costs
nothing, and on this account under the most favourable conditions it will ever get is eleven to
thirteen times wider.

The construction that refuses the choice is to use both: the experiment's estimate enters the model
as a prior on the coefficient, and the panel updates it. This is what a commercial media mix model
does when it is done well, and **it works** — three channels of five resolved instead of one, with
intervals twelve to thirteen times tighter on the channels the experiment covered.

This document measures what else the transfer carries. One unit conversion stands between the two
instruments and it is worth a factor of 1.77 here; the experiment's own sampling error becomes the
model's error, including the one interval in twenty that misses; and the conversion depends on the
saturation point, which wave 5 established the fit is nearly blind to.

## The decision it enables

1. **Can the experiment we already ran make the model usable?** Yes, and by a measurable factor.
2. **What did we inherit along with the precision?** The experiment's error, and it can no longer be
   overruled by the data.
3. **And what still has to be assumed?** The parameter that converts one instrument's answer into the
   other's, which the fit cannot settle.

## Usage

```python
from mktlab.attribution import geo_lift
from mktlab.calibration import calibrate, prior_from_holdout
from mktlab.mmm import fit
from mktlab.synth import AUDIENCE, generate_dataset

data = generate_dataset()
baseline = fit(data.spend_panel)
lift = geo_lift(experiment_panel, split=13, channel="social-pago")

prior = prior_from_holdout(
    lift, baseline, "social-pago", reach=float(AUDIENCE.users), spend=180_000.0
)
prior.conversion_factor  # 1.7692 - the average-to-marginal bridge
prior.mean  # the same experiment, on the coefficient's scale

calibrated = calibrate(data.spend_panel, {"social-pago": prior})
calibrated.table()  # the two claims in, the one claim out
calibrated.transfer(data.media_truth)  # the posterior as returns, against the truth
```

## Result 1: the bridge between the two instruments has a closed form

A holdout switches a channel off, so it measures the **average** return over the period. A regression
coefficient is a local slope, so it estimates the **marginal** return at the spend the channel is
running at. Where the response bends, those are different numbers.

With a Michaelis-Menten response `f(x) = x / (x + h)`, the average return per unit of spend at level
`x` is `f(x)/x = 1/(x + h)` and the marginal return is `f'(x) = h/(x + h)²`. Their ratio is
`(x + h)/h`, so writing the half point as a multiple `k` of the spend level gives

> **average / marginal = 1 + 1/k**

which depends on nothing else at all.

| Saturation point `k` | Factor |
| --- | --- |
| 0.5 | 3.0000 |
| **1.3** (the generator's) | **1.7692** |
| 3.0 | 1.3333 |
| 10.0 | 1.1000 |

At the generator's 1.30 the formula gives **1.7692307692**, and the generator's own ratio of its two
declared return columns is the same number to twelve digits on all three channels with a real effect
— two derivations that share no code. It is also why that ratio is identical across channels here:
they were all given the same multiple, not because anything general says they should be.

**And the table above is the problem, not a parameter table.** Wave 5 established that every
saturation point from 0.5 to 10.0 fits within 0.0008 of R-squared of the best. Across that range this
factor runs from 3.0 to 1.1 — a spread of 2.7× in the bridge between the two instruments, chosen by a
parameter the data cannot settle. Result 7 prices that.

## Result 2: the transfer works

The holdout resolved three channels of five. Each estimate is a rate per user, so it becomes
conversions when multiplied by the population, a return when divided by the spend, a marginal return
when divided by the factor above, and a coefficient when divided by the model's own chain rule.

| Channel | Average return | ÷ factor | Marginal return | Truth | Times the truth | Coefficient | Standard error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| social-pago | 0.032318 | 1.769231 | 0.018267 | 0.016957 | 1.0773 | 124.3418 | 3.5633 |
| email | 0.046058 | 1.769231 | 0.026033 | 0.018087 | 1.4393 | 20.2596 | 3.8282 |
| busca-generica | 0.011814 | 1.769231 | 0.006678 | 0.007065 | 0.9451 | 30.9328 | 3.7726 |

Note what has already happened: **the experiment's clean number passed through two of the model's
guesses before it landed.** A coefficient means nothing until the carryover and the saturation point
have been assumed, so there is no way to put an experiment into a model that does not route it
through the model's assumptions.

Then the update, which is the conjugate normal one with the residual variance held at its least
squares estimate:

| Channel | Prior | Prior width | Model | Model width | Posterior | Posterior width | Width kept |
| --- | --- | --- | --- | --- | --- | --- | --- |
| social-pago | 124.3418 | 14.1479 | 139.3700 | 189.5556 | **124.3782** | **14.0984** | **0.0744** |
| email | 20.2596 | 15.2000 | 5.7788 | 198.5230 | **20.1673** | **15.1464** | **0.0763** |
| busca-generica | 30.9328 | 14.9793 | 18.5883 | 176.0132 | **30.8354** | **14.9135** | **0.0847** |
| busca-marca | — | — | −16.6503 | 185.0894 | −25.2209 | 139.2410 | 0.7523 |
| retargeting | — | — | 2.7547 | 168.5260 | −1.1745 | 136.3520 | 0.8091 |

As the returns a budget acts on:

| Channel | Posterior return | 95% interval | Truth | Covers | Times the truth | Width ÷ truth | Resolved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| social-pago | 0.018272 | 0.017237 to 0.019308 | 0.016957 | **no** | 1.0776 | **0.1221** | yes |
| email | 0.025914 | 0.016183 to 0.035645 | 0.018087 | yes | 1.4327 | 1.0760 | yes |
| busca-generica | 0.006657 | 0.005047 to 0.008266 | 0.007065 | yes | 0.9422 | 0.4557 | yes |
| busca-marca | −0.007207 | −0.027101 to 0.012687 | 0.000000 | yes | — | — | no |
| retargeting | −0.000509 | −0.030061 to 0.029043 | 0.000000 | yes | — | — | no |

**Channels resolved: one of five before, three of five after.** On the channels the experiment
covered the posterior keeps under a tenth of the width least squares gave them, and the posterior
means sit within half a per cent of the priors — the model's own contribution to those three
channels rounds to nothing.

And the in-sample fit barely moves: R-squared **0.836425 before, 0.836050 after**, a loss of
**0.000374**. The data is nearly indifferent between a coefficient of 139.37 and one of 124.38 on
social-pago, which is wave 5's equivalent-range result arriving from the other direction. **In-sample
fit cannot adjudicate a calibration**, in either direction, which is worth saying because the fit
statistic is what usually gets shown to defend the model.

## Result 3: and it gave up a covering interval

Before the transfer, five of five intervals covered the truth. After it, four of five: social-pago's
posterior interval, 0.017237 to 0.019308, does not contain 0.016957.

That was not manufactured by the update. It was **inherited**, and the holdout's own interval says so:

| Channel | Holdout interval on the average return | Truth | Covers |
| --- | --- | --- | --- |
| social-pago | 0.030442 to 0.034194 | 0.030000 | **no** |
| email | 0.028433 to 0.063682 | 0.032000 | yes |
| busca-generica | 0.008897 to 0.014731 | 0.012500 | yes |

A 95% interval is wrong one time in twenty by construction. Wave 1 computed five of them and this is
the one — the repository has published that miss since the reproducibility fix, and here is what it
costs downstream. The model's own interval on social-pago **did** cover the truth and was overruled
anyway, because it carried **0.55%** of the weight in the precision-weighted average.

That is the honest statement of what calibration is. It is not a way to be right more often than the
experiment. It is a way to be **as right as the experiment, cheaply** — and to be exactly as wrong as
it, without the data retaining any ability to say so.

## Result 4: skip the unit conversion and the same machinery manufactures a confident wrong answer

The naive calibration is the one that uses the holdout's number as though a coefficient estimated it.
It is one division away from the honest one.

| Channel | Posterior return | 95% interval | Truth | Covers | Times the truth | Resolved |
| --- | --- | --- | --- | --- | --- | --- |
| social-pago | 0.031988 | 0.030170 to 0.033807 | 0.016957 | no | **1.8865** | yes |
| email | 0.044009 | 0.026919 to 0.061098 | 0.018087 | no | **2.4332** | yes |
| busca-generica | 0.011393 | 0.008572 to 0.014215 | 0.007065 | no | **1.6126** | yes |
| busca-marca | −0.025191 | **−0.045283 to −0.005099** | 0.000000 | no | — | **yes** |
| retargeting | −0.026414 | −0.056167 to 0.003339 | 0.000000 | yes | — | no |

**Four channels resolved, one interval of five covering the truth.** Every estimate is inflated by
about the factor that was left out, and busca-marca — a channel whose true effect is exactly zero —
now carries an interval that excludes zero **from below**: a confident negative return, manufactured
by arithmetic, on a channel nobody measured.

R-squared falls to **0.824520**, a loss of 0.0119 against the honest calibration's 0.000374. So the
error is visible in the fit, thirty times more visible than the correct transfer's cost — but 0.0119
of R-squared is not what anybody notices on a slide, and the intervals got *tighter*, which is what
does get noticed.

**Precision and bias transfer with equal efficiency.** The update narrows the posterior around
whatever the prior says, and it has no way to know whether the prior is centred correctly.

## Result 5: a null result was the most precise thing anybody knew

The two channels the holdout could not distinguish from zero are usually reported as inconclusive and
then dropped. They are not absences. Each is an estimate with a standard error, and on this account a
far tighter one than the model can produce.

| Channel | Model width | Posterior width | Width kept | Posterior return | 95% interval | Covers zero | Resolved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| retargeting | 168.5260 | 11.8594 | **0.0704** | 0.000742 | −0.001828 to 0.003313 | yes | no |
| busca-marca | 185.0894 | 16.8217 | **0.0909** | 0.001632 | −0.000771 to 0.004035 | yes | no |

These are the only two priors in the fit, so nothing else is doing the work. Both keep under a
tenth of their width, both intervals cover the truth of zero, and **neither is resolved** — which is
the correct answer for a channel that does nothing, arrived at with eleven to fourteen times the
precision the model had on its own. Wave 2 showed that a null result buys an upper bound;
this is where that bound gets spent.

## Result 6: a prior on one channel is not a claim about one channel

One experiment, on social-pago only, and then read the whole account:

| Channel | Least squares return | Posterior return | Moved by | Width kept |
| --- | --- | --- | --- | --- |
| social-pago | 0.020475 | 0.018279 | 0.89× | **0.0744** |
| email | 0.007425 | 0.013037 | **1.76×** | 0.9605 |
| retargeting | 0.001194 | 0.002780 | **2.33×** | 0.9616 |
| busca-generica | 0.004013 | 0.004895 | 1.22× | 0.9559 |
| busca-marca | −0.004758 | −0.004224 | 0.89× | 0.9918 |

The spend columns correlate above 0.83, so information about one of them is information about all of
them. Every channel's reported return moved, two of them by more than half again — **and their widths
moved by less than five per cent.** The transfer arrives as a shift in location that nothing on the
chart marks, because the interval beside the number looks the same as it did before.

The width transfer is the small one and it has a closed form: with a prior on exactly one
coefficient, the posterior standard error is the precision sum *exactly*, by Sherman-Morrison, no
matter how collinear the design is. With priors on several channels it becomes an upper bound, and the
gap — under two per cent here — is the precision that arrives through the correlation.

## Result 7: the same transfer at four saturation points the fit cannot distinguish

Everything above assumed the generator's saturation point. A practitioner does not have it, and picks
one by fit.

| Saturation `k` | Factor | R-squared | Fit loss | Posterior return | Times the truth | Width ÷ truth | Covers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.5 | 3.0000 | 0.835689 | 0.000754 | 0.010796 | **0.64** | 0.0722 | no |
| **1.3** (true) | 1.7692 | 0.836425 | 0.000019 | 0.018272 | 1.08 | 0.1221 | no |
| **3.0** (best fit) | 1.3333 | 0.836444 | 0.000000 | 0.024157 | **1.42** | 0.1616 | no |
| 10.0 | 1.1000 | 0.836148 | 0.000295 | 0.029132 | **1.72** | 0.1953 | no |

Every row fits within **0.000754** of R-squared of every other, and across them the calibrated answer
runs from **0.64 to 1.72 times the truth** — a spread of 2.70×, against 2.73× in the conversion
factor. Nearly all of it is the bridge; the remainder is the model's own design changing with `k`. The best-fitting row is not the true one: it is `k = 3.0`, which returns 1.42 times
the truth. **A practitioner choosing the saturation point by fit — the only way it can be chosen —
lands there.**

The four widths run 0.07 to 0.20 times the truth, against 1.64 for this same model uncalibrated and
0.13 for the holdout itself. The transfer puts the model in the experiment's precision class. Where
inside that class it lands, and how far from the truth it lands, is settled by a parameter the fit
cannot see.

**That is the wave in one table.** Calibration transfers the experiment's precision faithfully, and it
transfers everything else just as faithfully: the experiment's own sampling error, and the modeller's
choice of a parameter the data cannot settle. What it does not transfer is the data's ability to
object.

## Assumptions and limitations

- **Every number here comes from a seeded synthetic generator**, including the returns the transfer is
  judged against and the truth of exactly zero on two channels. No advertiser, agency, platform or
  client data is used anywhere. See [`DISCLAIMER.md`](../../../DISCLAIMER.md).
- **Wave 6 adds no draws to the generator.** It reads the panel and the holdouts waves 1 and 5 already
  published, so no figure in any earlier document can move because this module exists. That is
  deliberate and it is asserted by a test.
- **The residual variance is plugged in from the least squares fit and its uncertainty is not
  propagated.** This is the empirical-Bayes step, and a fully Bayesian treatment would put a prior on
  the variance too and report slightly wider intervals. The construction here is the smallest one that
  makes the transfer visible, not the most complete one.
- **The intervals use the least squares degrees of freedom.** With a prior the effective degrees of
  freedom are larger than `n − p`, so the critical value is mildly conservative. It is the same
  critical value on both sides of every comparison in this document, which is what the comparisons
  need.
- **The prior is independent per channel — a diagonal precision.** A real experiment programme
  measuring several channels at once would produce a covariance between them, and using it would
  change the transfer. Nothing here estimates that covariance, because nothing here ran that
  programme.
- **The experiment and the model are measured on the same declared truth but on different synthetic
  populations** — the journey dataset and the weekly panel. Both are built from the same channel
  effects, which is what makes the returns comparable; neither is a sample from the other.
- **The average-to-marginal factor assumes the generator's response shape.** `1 + 1/k` is exact for a
  Michaelis-Menten curve. A different saturation family gives a different factor, and the point of
  Result 7 survives that unchanged: whatever the family, the bridge is a function of a parameter the
  fit cannot settle.
- **A prior is not a fix for an unidentified model, and this module is not an argument for one.** What
  the transfer does is import information from a design that did identify the quantity. Where no such
  design was run, a prior narrows the interval without anything having been learned — which is the
  case Result 4 measures.

## Sources

Cited as the origin of a *method*, never as a source of any number in these tables.

- Sherman, J., Morrison, W. J. (1950). *Adjustment of an Inverse Matrix Corresponding to a Change in
  One Element of a Given Matrix.* Annals of Mathematical Statistics 21(1). — why the single-prior
  precision identity is exact on any design.
- Hoerl, A. E., Kennard, R. W. (1970). *Ridge Regression: Biased Estimation for Nonorthogonal
  Problems.* Technometrics 12(1). — the generalised ridge this update is, read as a normal prior.
- Gelman, A., Carlin, J. B., Stern, H. S., Dunson, D. B., Vehtari, A., Rubin, D. B. *Bayesian Data
  Analysis*, 3rd ed. — the conjugate normal update and the empirical-Bayes plug-in this module uses.
- Chan, D., Perry, M. (2017). *Challenges and Opportunities in Media Mix Modeling.* Google Research. —
  the identification problem the transfer is proposed as an answer to.
- Jin, Y., Wang, Y., Sun, Y., Chan, D., Koehler, J. (2017). *Bayesian Methods for Media Mix Modeling
  with Carryover and Shape Effects.* Google Research. — the Hill response whose derivative gives the
  closed form in Result 1, and the Bayesian treatment this is the smallest version of.
- Gordon, B. R., Zettelmeyer, F., Bhargava, N., Chapsky, D. (2019). *A Comparison of Approaches to
  Advertising Measurement.* Marketing Science 38(2). — experiments and observational models on the
  same campaigns, which is the comparison Result 7 ends in.

---

# `mktlab.calibration` — o experimento em que o modelo acredita

*[English](#mktlabcalibration--the-experiment-the-model-believes)*

## O problema de negócio

A onda 5 termina numa escolha que ninguém quer fazer. O holdout responde de forma estreita sobre os
canais que cobriu, custa conversões e leva treze semanas. O modelo responde sobre todos os canais, não
custa nada, e nesta conta, nas condições mais favoráveis que jamais terá, é onze a treze vezes mais
largo.

A construção que recusa a escolha é usar os dois: a estimativa do experimento entra no modelo como
uma priori sobre o coeficiente, e o painel a atualiza. É o que um modelo de mix de mídia comercial faz
quando é bem feito, e **funciona** — três canais em cinco resolvidos em vez de um, com intervalos doze
a treze vezes mais estreitos nos canais que o experimento cobriu.

Este documento mede o que mais a transferência carrega. Uma conversão de unidade separa os dois
instrumentos e vale um fator de 1,77 aqui; o erro amostral do próprio experimento passa a ser o erro
do modelo, inclusive o intervalo em vinte que erra; e a conversão depende do ponto de saturação, ao
qual a onda 5 estabeleceu que o ajuste é quase cego.

## A decisão que habilita

1. **O experimento que já rodamos torna o modelo utilizável?** Sim, e por um fator mensurável.
2. **O que herdamos junto com a precisão?** O erro do experimento, e ele não pode mais ser derrubado
   pelos dados.
3. **E o que ainda tem de ser suposto?** O parâmetro que converte a resposta de um instrumento na do
   outro, que o ajuste não consegue resolver.

## Uso

```python
from mktlab.attribution import geo_lift
from mktlab.calibration import calibrate, prior_from_holdout
from mktlab.mmm import fit
from mktlab.synth import AUDIENCE, generate_dataset

data = generate_dataset()
baseline = fit(data.spend_panel)
lift = geo_lift(painel_do_experimento, split=13, channel="social-pago")

prior = prior_from_holdout(
    lift, baseline, "social-pago", reach=float(AUDIENCE.users), spend=180_000.0
)
prior.conversion_factor  # 1,7692 - a ponte entre o médio e o marginal
prior.mean  # o mesmo experimento, na escala do coeficiente

calibrated = calibrate(data.spend_panel, {"social-pago": prior})
calibrated.table()  # as duas afirmações que entram, a que sai
calibrated.transfer(data.media_truth)  # a posteriori como retornos, contra a verdade
```

## Resultado 1: a ponte entre os dois instrumentos tem forma fechada

Um holdout desliga o canal, então mede o retorno **médio** no período. Um coeficiente de regressão é
uma inclinação local, então estima o retorno **marginal** no nível de investimento em que o canal
está. Onde a resposta dobra, esses são números diferentes.

Com uma resposta de Michaelis-Menten `f(x) = x / (x + h)`, o retorno médio por unidade de
investimento no nível `x` é `f(x)/x = 1/(x + h)` e o marginal é `f'(x) = h/(x + h)²`. A razão é
`(x + h)/h`, então escrever o meio-ponto como um múltiplo `k` do próprio nível de investimento dá

> **médio / marginal = 1 + 1/k**

que não depende de mais nada.

| Ponto de saturação `k` | Fator |
| --- | --- |
| 0,5 | 3,0000 |
| **1,3** (do gerador) | **1,7692** |
| 3,0 | 1,3333 |
| 10,0 | 1,1000 |

No 1,30 do gerador a fórmula dá **1,7692307692**, e a razão entre as duas colunas de retorno
declaradas do próprio gerador é o mesmo número com doze dígitos nos três canais com efeito real —
duas derivações que não compartilham código. É também por isso que essa razão é idêntica entre canais
aqui: todos receberam o mesmo múltiplo, não porque algo geral diga que deveriam.

**E a tabela acima é o problema, não uma tabela de parâmetros.** A onda 5 estabeleceu que todo ponto
de saturação de 0,5 a 10,0 ajusta dentro de 0,0008 de R-quadrado do melhor. Nessa faixa este fator vai
de 3,0 a 1,1 — uma dispersão de 2,7× na ponte entre os dois instrumentos, escolhida por um parâmetro
que os dados não resolvem. O Resultado 7 precifica isso.

## Resultado 2: a transferência funciona

O holdout resolveu três canais em cinco. Cada estimativa é uma taxa por usuário, então vira
conversões quando multiplicada pela população, retorno quando dividida pelo investimento, retorno
marginal quando dividida pelo fator acima, e coeficiente quando dividida pela regra da cadeia do
próprio modelo.

| Canal | Retorno médio | ÷ fator | Retorno marginal | Verdade | Vezes a verdade | Coeficiente | Erro-padrão |
| --- | --- | --- | --- | --- | --- | --- | --- |
| social-pago | 0,032318 | 1,769231 | 0,018267 | 0,016957 | 1,0773 | 124,3418 | 3,5633 |
| email | 0,046058 | 1,769231 | 0,026033 | 0,018087 | 1,4393 | 20,2596 | 3,8282 |
| busca-generica | 0,011814 | 1,769231 | 0,006678 | 0,007065 | 0,9451 | 30,9328 | 3,7726 |

Note o que já aconteceu: **o número limpo do experimento passou por dois palpites do modelo antes de
aterrissar.** Um coeficiente não significa nada até que o carryover e o ponto de saturação tenham sido
supostos, então não existe forma de colocar um experimento num modelo que não o faça atravessar as
premissas do modelo.

Então a atualização, que é a normal conjugada com a variância residual mantida em sua estimativa de
mínimos quadrados:

| Canal | Priori | Largura da priori | Modelo | Largura do modelo | Posteriori | Largura da posteriori | Largura mantida |
| --- | --- | --- | --- | --- | --- | --- | --- |
| social-pago | 124,3418 | 14,1479 | 139,3700 | 189,5556 | **124,3782** | **14,0984** | **0,0744** |
| email | 20,2596 | 15,2000 | 5,7788 | 198,5230 | **20,1673** | **15,1464** | **0,0763** |
| busca-generica | 30,9328 | 14,9793 | 18,5883 | 176,0132 | **30,8354** | **14,9135** | **0,0847** |
| busca-marca | — | — | −16,6503 | 185,0894 | −25,2209 | 139,2410 | 0,7523 |
| retargeting | — | — | 2,7547 | 168,5260 | −1,1745 | 136,3520 | 0,8091 |

Como os retornos sobre os quais um orçamento age:

| Canal | Retorno posteriori | Intervalo de 95% | Verdade | Cobre | Vezes a verdade | Largura ÷ verdade | Resolvido |
| --- | --- | --- | --- | --- | --- | --- | --- |
| social-pago | 0,018272 | 0,017237 a 0,019308 | 0,016957 | **não** | 1,0776 | **0,1221** | sim |
| email | 0,025914 | 0,016183 a 0,035645 | 0,018087 | sim | 1,4327 | 1,0760 | sim |
| busca-generica | 0,006657 | 0,005047 a 0,008266 | 0,007065 | sim | 0,9422 | 0,4557 | sim |
| busca-marca | −0,007207 | −0,027101 a 0,012687 | 0,000000 | sim | — | — | não |
| retargeting | −0,000509 | −0,030061 a 0,029043 | 0,000000 | sim | — | — | não |

**Canais resolvidos: um em cinco antes, três em cinco depois.** Nos canais que o experimento cobriu a
posteriori mantém menos de um décimo da largura que os mínimos quadrados lhes davam, e as médias da
posteriori ficam a menos de meio por cento das prioris — a contribuição do próprio modelo para esses
três canais arredonda para nada.

E o ajuste dentro da amostra quase não se move: R-quadrado **0,836425 antes, 0,836050 depois**, uma
perda de **0,000374**. Os dados são quase indiferentes entre um coeficiente de 139,37 e um de 124,38
em social-pago, o que é o resultado da faixa equivalente da onda 5 chegando pelo outro lado. **O
ajuste dentro da amostra não consegue julgar uma calibração**, em nenhuma direção — o que vale dizer,
porque a estatística de ajuste é o que costuma ser mostrado para defender o modelo.

## Resultado 3: e ela abriu mão de um intervalo que cobria

Antes da transferência, cinco de cinco intervalos cobriam a verdade. Depois, quatro de cinco: o
intervalo posteriori de social-pago, 0,017237 a 0,019308, não contém 0,016957.

Isso não foi fabricado pela atualização. Foi **herdado**, e o intervalo do próprio holdout diz isso:

| Canal | Intervalo do holdout sobre o retorno médio | Verdade | Cobre |
| --- | --- | --- | --- |
| social-pago | 0,030442 a 0,034194 | 0,030000 | **não** |
| email | 0,028433 a 0,063682 | 0,032000 | sim |
| busca-generica | 0,008897 a 0,014731 | 0,012500 | sim |

Um intervalo de 95% está errado uma vez em vinte por construção. A onda 1 calculou cinco deles e este
é o tal — o repositório publica esse erro desde a correção de reprodutibilidade, e aqui está o que ele
custa adiante. O intervalo do próprio modelo em social-pago **cobria** a verdade e foi derrubado
mesmo assim, porque carregava **0,55%** do peso na média ponderada por precisão.

Essa é a afirmação honesta do que a calibração é. Não é uma forma de acertar mais vezes que o
experimento. É uma forma de acertar **tanto quanto o experimento, barato** — e de errar exatamente
tanto quanto ele, sem que os dados retenham qualquer capacidade de dizer isso.

## Resultado 4: pule a conversão de unidade e a mesma maquinaria fabrica uma resposta errada e confiante

A calibração ingênua é a que usa o número do holdout como se um coeficiente o estimasse. Está a uma
divisão da honesta.

| Canal | Retorno posteriori | Intervalo de 95% | Verdade | Cobre | Vezes a verdade | Resolvido |
| --- | --- | --- | --- | --- | --- | --- |
| social-pago | 0,031988 | 0,030170 a 0,033807 | 0,016957 | não | **1,8865** | sim |
| email | 0,044009 | 0,026919 a 0,061098 | 0,018087 | não | **2,4332** | sim |
| busca-generica | 0,011393 | 0,008572 a 0,014215 | 0,007065 | não | **1,6126** | sim |
| busca-marca | −0,025191 | **−0,045283 a −0,005099** | 0,000000 | não | — | **sim** |
| retargeting | −0,026414 | −0,056167 a 0,003339 | 0,000000 | sim | — | não |

**Quatro canais resolvidos, um intervalo em cinco cobrindo a verdade.** Toda estimativa está inflada
por cerca do fator que foi deixado de fora, e busca-marca — um canal cujo efeito verdadeiro é
exatamente zero — agora carrega um intervalo que exclui o zero **por baixo**: um retorno negativo
confiante, fabricado por aritmética, num canal que ninguém mediu.

O R-quadrado cai para **0,824520**, uma perda de 0,0119 contra os 0,000374 da calibração honesta.
Então o erro é visível no ajuste, trinta vezes mais visível que o custo da transferência correta — mas
0,0119 de R-quadrado não é o que alguém nota num slide, e os intervalos ficaram *mais estreitos*, o
que é o que se nota.

**Precisão e viés se transferem com a mesma eficiência.** A atualização estreita a posteriori em torno
do que a priori diz, e não tem como saber se a priori está centrada no lugar certo.

## Resultado 5: um resultado nulo era a coisa mais precisa que alguém sabia

Os dois canais que o holdout não conseguiu distinguir de zero costumam ser reportados como
inconclusivos e depois descartados. Não são ausências. Cada um é uma estimativa com erro-padrão, e
nesta conta um bem mais estreito do que o modelo consegue produzir.

| Canal | Largura do modelo | Largura da posteriori | Largura mantida | Retorno posteriori | Intervalo de 95% | Cobre o zero | Resolvido |
| --- | --- | --- | --- | --- | --- | --- | --- |
| retargeting | 168,5260 | 11,8594 | **0,0704** | 0,000742 | −0,001828 a 0,003313 | sim | não |
| busca-marca | 185,0894 | 16,8217 | **0,0909** | 0,001632 | −0,000771 a 0,004035 | sim | não |

Essas são as duas únicas prioris do ajuste, então nada mais está fazendo o trabalho. Os dois
mantêm menos de um décimo da largura, os dois intervalos cobrem a verdade de zero, e **nenhum é
resolvido** — que é a resposta correta para um canal que não faz nada, obtida com onze a catorze
vezes a precisão que o modelo tinha sozinho. A onda 2 mostrou que um resultado nulo compra um limite
superior; é aqui que esse limite é gasto.

## Resultado 6: uma priori sobre um canal não é uma afirmação sobre um canal

Um experimento, só em social-pago, e então leia a conta inteira:

| Canal | Retorno por mínimos quadrados | Retorno posteriori | Moveu | Largura mantida |
| --- | --- | --- | --- | --- |
| social-pago | 0,020475 | 0,018279 | 0,89× | **0,0744** |
| email | 0,007425 | 0,013037 | **1,76×** | 0,9605 |
| retargeting | 0,001194 | 0,002780 | **2,33×** | 0,9616 |
| busca-generica | 0,004013 | 0,004895 | 1,22× | 0,9559 |
| busca-marca | −0,004758 | −0,004224 | 0,89× | 0,9918 |

As colunas de investimento correlacionam acima de 0,83, então informação sobre uma é informação sobre
todas. O retorno reportado de todo canal se moveu, dois deles em mais de metade a mais — **e as
larguras se moveram menos de cinco por cento.** A transferência chega como um deslocamento de posição
que nada no gráfico marca, porque o intervalo ao lado do número parece o mesmo de antes.

A transferência de largura é a pequena e tem forma fechada: com uma priori sobre exatamente um
coeficiente, o erro-padrão posteriori é a soma de precisões *exatamente*, por Sherman-Morrison, não
importa quão colinear seja o desenho. Com prioris em vários canais vira um limite superior, e a
diferença — menos de dois por cento aqui — é a precisão que chega pela correlação.

## Resultado 7: a mesma transferência em quatro pontos de saturação que o ajuste não distingue

Tudo acima supôs o ponto de saturação do gerador. Um praticante não o tem, e escolhe um pelo ajuste.

| Saturação `k` | Fator | R-quadrado | Perda de ajuste | Retorno posteriori | Vezes a verdade | Largura ÷ verdade | Cobre |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0,5 | 3,0000 | 0,835689 | 0,000754 | 0,010796 | **0,64** | 0,0722 | não |
| **1,3** (verdadeiro) | 1,7692 | 0,836425 | 0,000019 | 0,018272 | 1,08 | 0,1221 | não |
| **3,0** (melhor ajuste) | 1,3333 | 0,836444 | 0,000000 | 0,024157 | **1,42** | 0,1616 | não |
| 10,0 | 1,1000 | 0,836148 | 0,000295 | 0,029132 | **1,72** | 0,1953 | não |

Toda linha ajusta dentro de **0,000754** de R-quadrado de todas as outras, e entre elas a resposta
calibrada vai de **0,64 a 1,72 vezes a verdade** — uma dispersão de 2,70×, contra 2,73× no fator de
conversão. Quase tudo é a ponte; o restante é o próprio desenho do modelo mudando com `k`. A linha de melhor ajuste não é a verdadeira: é `k = 3,0`, que devolve 1,42
vezes a verdade. **Um praticante que escolhe o ponto de saturação pelo ajuste — a única forma de
escolher — aterrissa ali.**

As quatro larguras vão de 0,07 a 0,20 vezes a verdade, contra 1,64 para este mesmo modelo não
calibrado e 0,13 para o próprio holdout. A transferência coloca o modelo na classe de precisão do
experimento. Onde dentro dessa classe ele cai, e a que distância da verdade, é decidido por um
parâmetro que o ajuste não vê.

**Essa é a onda numa tabela.** A calibração transfere a precisão do experimento fielmente, e transfere
tudo o mais com a mesma fidelidade: o erro amostral do próprio experimento e a escolha do modelador
por um parâmetro que os dados não resolvem. O que ela não transfere é a capacidade de os dados
objetarem.

## Premissas e limitações

- **Todo número aqui vem de um gerador sintético com semente**, inclusive os retornos contra os quais
  a transferência é julgada e a verdade de exatamente zero em dois canais. Nenhum dado de anunciante,
  agência, plataforma ou cliente é usado em qualquer parte. Ver
  [`DISCLAIMER.md`](../../../DISCLAIMER.md).
- **A onda 6 não adiciona sorteios ao gerador.** Ela lê o painel e os holdouts que as ondas 1 e 5 já
  publicaram, então nenhuma cifra de nenhum documento anterior pode se mover porque este módulo
  existe. Isso é deliberado e está asserido por um teste.
- **A variância residual é plugada a partir do ajuste de mínimos quadrados e sua incerteza não é
  propagada.** Este é o passo empírico-bayesiano; um tratamento totalmente bayesiano colocaria uma
  priori também sobre a variância e reportaria intervalos ligeiramente mais largos. A construção aqui
  é a menor que torna a transferência visível, não a mais completa.
- **Os intervalos usam os graus de liberdade dos mínimos quadrados.** Com uma priori os graus de
  liberdade efetivos são maiores que `n − p`, então o valor crítico é levemente conservador. É o mesmo
  valor crítico nos dois lados de toda comparação deste documento, que é o que as comparações
  precisam.
- **A priori é independente por canal — uma precisão diagonal.** Um programa real de experimentos
  medindo vários canais ao mesmo tempo produziria uma covariância entre eles, e usá-la mudaria a
  transferência. Nada aqui estima essa covariância, porque nada aqui rodou esse programa.
- **O experimento e o modelo são medidos contra a mesma verdade declarada, mas em populações
  sintéticas diferentes** — a base de jornadas e o painel semanal. Os dois são construídos dos mesmos
  efeitos de canal, o que é o que torna os retornos comparáveis; nenhum é amostra do outro.
- **O fator médio-para-marginal supõe a forma de resposta do gerador.** `1 + 1/k` é exato para uma
  curva de Michaelis-Menten. Uma família de saturação diferente dá um fator diferente, e o ponto do
  Resultado 7 sobrevive intacto: qualquer que seja a família, a ponte é função de um parâmetro que o
  ajuste não resolve.
- **Uma priori não é conserto para um modelo não identificado, e este módulo não é argumento a favor
  de um.** O que a transferência faz é importar informação de um desenho que identificou a
  quantidade. Onde tal desenho não foi rodado, uma priori estreita o intervalo sem que nada tenha sido
  aprendido — que é o caso que o Resultado 4 mede.

## Fontes

Citadas como origem de um *método*, nunca como fonte de qualquer número destas tabelas.

- Sherman, J., Morrison, W. J. (1950). *Adjustment of an Inverse Matrix Corresponding to a Change in
  One Element of a Given Matrix.* Annals of Mathematical Statistics 21(1). — por que a identidade de
  precisão com uma única priori é exata em qualquer desenho.
- Hoerl, A. E., Kennard, R. W. (1970). *Ridge Regression: Biased Estimation for Nonorthogonal
  Problems.* Technometrics 12(1). — a ridge generalizada que esta atualização é, lida como priori
  normal.
- Gelman, A., Carlin, J. B., Stern, H. S., Dunson, D. B., Vehtari, A., Rubin, D. B. *Bayesian Data
  Analysis*, 3ª ed. — a atualização normal conjugada e o plug-in empírico-bayesiano usado aqui.
- Chan, D., Perry, M. (2017). *Challenges and Opportunities in Media Mix Modeling.* Google Research. —
  o problema de identificação para o qual a transferência é proposta como resposta.
- Jin, Y., Wang, Y., Sun, Y., Chan, D., Koehler, J. (2017). *Bayesian Methods for Media Mix Modeling
  with Carryover and Shape Effects.* Google Research. — a resposta de Hill cuja derivada dá a forma
  fechada do Resultado 1, e o tratamento bayesiano do qual este é a menor versão.
- Gordon, B. R., Zettelmeyer, F., Bhargava, N., Chapsky, D. (2019). *A Comparison of Approaches to
  Advertising Measurement.* Marketing Science 38(2). — experimentos e modelos observacionais nas
  mesmas campanhas, que é a comparação em que o Resultado 7 termina.
