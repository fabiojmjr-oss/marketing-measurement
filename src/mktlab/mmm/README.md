# `mktlab.mmm` — the model that replaces the experiment

*[Português](#mktlabmmm--o-modelo-que-substitui-o-experimento)*

## The business problem

Waves 2 to 4 priced the holdout: what it can resolve, what it costs, and how to monitor it honestly.
Every one of those answers is a reason somebody will say no. A media mix model is what gets built
instead — a regression of weekly conversions on weekly spend, no regions switched off, no conversions
given up, an answer for every channel at once.

This document fits one on the same account, hands it **the generator's own carryover and saturation**
— a favour no real model receives — and asks what it can support. With an R-squared of 0.84 and no
misspecification whatever, it can distinguish **one channel out of five** from zero. The other four
intervals span both signs, and one of them is fourteen times the size of the return it is estimating.

The model is not lying: all five intervals contain the truth. It is uninformative, and the deck shows
the point estimates.

## The decision it enables

1. **Can this panel answer the budget question at all?** Which is decided by the spend plan, before
   any modelling, and is visible in the correlation matrix.
2. **How much of the answer came from the transforms we guessed?** One of the two guesses matters and
   is recoverable from the fit; the other is nearly invisible to it.
3. **And what would the experiment have bought instead?** Eleven to thirteen times the precision,
   relative to the quantity each instrument estimates.

## Usage

```python
from mktlab.mmm import fit, transform_grid, variance_inflation
from mktlab.synth import MEDIA_MIX, generate_dataset

data = generate_dataset()
fitted = fit(data.spend_panel)  # the generator's own transforms: the best case there is
fitted.r_squared  # 0.8364
fitted.table()  # coefficient, standard error, p-value, interval, variance inflation
fitted.returns(data.media_truth)  # the same thing as returns, against the truth

fitted.equivalent_range(4, r_squared_loss=0.005)  # (58.02, 220.72) - and see Result 4
transform_grid(data.spend_panel, (0.2, 0.45, 0.6), (0.5, 1.3, 3.0), data.media_truth)
```

## Result 1: the channels move together, because that is how plans are written

The panel's budget swings 30% week to week and each channel moves only 12% on its own. That is not a
pathological construction — a media plan is written as shares of a budget, so when the budget moves
the channels move with it.

| | busca-generica | busca-marca | email | retargeting | social-pago |
| --- | --- | --- | --- | --- | --- |
| **busca-generica** | 1.0000 | 0.8305 | 0.8412 | 0.8388 | 0.8387 |
| **busca-marca** | 0.8305 | 1.0000 | 0.8771 | 0.8363 | 0.8310 |
| **email** | 0.8412 | 0.8771 | 1.0000 | 0.8539 | 0.8789 |
| **retargeting** | 0.8388 | 0.8363 | 0.8539 | 1.0000 | 0.8584 |
| **social-pago** | 0.8387 | 0.8310 | 0.8789 | 0.8584 | 1.0000 |

Every pair correlates above 0.83, and the consequence is arithmetic:

| Channel | Variance inflation | Standard error multiple |
| --- | --- | --- |
| email | **8.5249** | **2.9197** |
| busca-generica | 6.8811 | 2.6232 |
| busca-marca | 6.4804 | 2.5457 |
| social-pago | 6.3857 | 2.5270 |
| retargeting | 5.7315 | 2.3940 |

**Every confidence interval is two and a half to three times wider than it would have been on
independent spend.** The condition number of the centred channel block is 7.01, comfortably under the
conventional warning line of thirty — which is worth knowing, because the alarm that does not go off
here is not evidence that the model is fine. The variance inflation is the diagnostic that bites.

## Result 2: with the right transforms, it resolves one channel of five

Fitted with the generator's own carryover of 0.45 and saturation at 1.30 times mean weekly spend, a
linear trend and a seasonal pair. R-squared 0.8364, residual standard deviation 8.718 against a
generator noise of 9.0 — the model has recovered the noise level almost exactly, which is the fit
working.

| Channel | Coefficient | Standard error | t | p | 95% interval | VIF |
| --- | --- | --- | --- | --- | --- | --- |
| social-pago | **139.3700** | 47.7410 | 2.9193 | **0.0044** | 44.59 to 234.15 | 6.3857 |
| busca-generica | 18.5883 | 44.3302 | 0.4193 | 0.6759 | −69.42 to 106.59 | 6.8811 |
| email | 5.7788 | 49.9995 | 0.1156 | 0.9082 | −93.48 to 105.04 | 8.5249 |
| retargeting | 2.7547 | 42.4445 | 0.0649 | 0.9484 | −81.51 to 87.02 | 5.7315 |
| busca-marca | **−16.6503** | 46.6161 | −0.3572 | 0.7217 | −109.20 to 75.89 | 6.4804 |

As the returns a budget decides on, against the truth the panel was built from:

| Channel | Marginal return | 95% interval | Truth | Covers | Times the truth | Interval ÷ truth |
| --- | --- | --- | --- | --- | --- | --- |
| social-pago | 0.020475 | 0.006551 to 0.034398 | 0.016957 | yes | 1.21 | **1.64** |
| busca-generica | 0.004013 | −0.014985 to 0.023011 | 0.007065 | yes | 0.57 | **5.38** |
| email | 0.007425 | −0.120121 to 0.134972 | 0.018087 | yes | 0.41 | **14.10** |
| retargeting | 0.001194 | −0.035331 to 0.037719 | 0.000000 | yes | — | — |
| busca-marca | −0.004758 | −0.031202 to 0.021687 | 0.000000 | yes | — | — |

**Five of five intervals contain the truth and one of five excludes zero.** The model is honest and
almost silent. busca-marca's point estimate is negative for a channel whose true effect is zero;
email's interval is fourteen times the size of the return it is estimating; busca-generica comes in at
0.57 times its truth. A slide showing those five point estimates as a budget recommendation would be
reporting noise with the shape of an answer.

## Result 3: read the two return columns apart

| Channel | Average return | Marginal return | Ratio |
| --- | --- | --- | --- |
| social-pago | 0.0300 | 0.016957 | 1.77 |
| email | 0.0320 | 0.018087 | 1.77 |
| busca-generica | 0.0125 | 0.007065 | 1.77 |

The **average** return is what switching the channel off would cost, per unit of its spend — which is
what a holdout measures. The **marginal** return is the derivative at the spend level the channel is
running at — which is what a regression coefficient estimates. Where the response is bending they
differ by a factor of 1.77 here, and the ratio is the same for every channel only because every
channel was given the same saturation point.

Quoting a coefficient as "the channel's ROAS" conflates them, in the flattering direction if you are
defending a cut and the unflattering one if you are defending an increase. The two columns exist so
that the confusion has to be deliberate.

## Result 4: the range that fits equally well *is* the confidence interval

The demonstration everybody asks a collinear model for: *here is a completely different answer that
fits the data just as well.* For social-pago's coefficient:

| Fit sacrificed | Coefficient may be | Width |
| --- | --- | --- |
| 0.001 of R-squared | 102.99 to 175.75 | 72.77 |
| 0.005 of R-squared | 58.02 to 220.72 | 162.71 |
| 0.010 of R-squared | 24.32 to 254.42 | 230.10 |
| **the 95% interval** | **44.59 to 234.15** | **189.56** |

**And what comes out of computing it properly is that there is nothing new in it.** The profile has a
closed form — the furthest a coefficient can travel while the residual sum of squares rises by δ is
its standard error times √(δ/σ̂²) — so the "range of equally good fits" is the standard error
rescaled. The 95% interval is exactly the set of coefficients costing about **0.0068 of R-squared**.

That is the useful version of the complaint about collinear models. There is no second diagnostic
hiding behind the standard error: the standard error *was* the diagnostic, and it is the column that
gets dropped when the chart is drawn.

## Result 5: one guess matters, the other barely registers

Neither the carryover nor the saturation point is observable. Twenty combinations, fitted:

| Adstock | Saturation at | R-squared | Fit loss | Implied social-pago return | Times the truth |
| --- | --- | --- | --- | --- | --- |
| **0.45** | 3.0 | 0.836444 | 0.000000 | 0.020463 | 1.21 |
| **0.45** | 1.3 | 0.836425 | 0.000019 | 0.020475 | 1.21 |
| **0.45** | 10.0 | 0.836148 | 0.000295 | 0.020174 | 1.19 |
| **0.45** | 0.5 | 0.835689 | 0.000754 | 0.019968 | 1.18 |
| 0.60 | 1.3 | 0.831749 | 0.004695 | 0.025993 | **1.53** |
| 0.60 | 0.5 | 0.831276 | 0.005167 | 0.026049 | **1.54** |
| 0.20 | 10.0 | 0.823651 | 0.012793 | 0.014909 | 0.88 |
| 0.20 | 0.5 | 0.819866 | 0.016578 | 0.014342 | 0.85 |

Eight of the twenty designs fit within 0.01 of the best, and across them the implied return runs
**1.18× to 1.54×** the truth. But read the grid by column, because the lazy version of this complaint
is wrong:

- **The fit identifies the carryover.** The generator's 0.45 wins, and moving to 0.60 costs 0.0047 of
  R-squared while moving the return by a quarter. That is a detectable difference.
- **The fit is nearly blind to the saturation point.** At the right carryover, every value from 0.5 to
  10.0 — a twentyfold range — sits within 0.0008 of the best fit and moves the return by one per cent.

So one of the two unobservable parameters is recoverable from the data and the other is not, and in
this panel the one that is not barely matters. "The transforms are arbitrary, so the answer is
arbitrary" is a slogan; the grid says which half of it is true.

## Result 6: what happens when the model leaves something out

Fitted without the trend and the seasonal pair, which a model has no way to know are there:

| Channel | Marginal return | 95% interval | Truth | Times the truth |
| --- | --- | --- | --- | --- |
| social-pago | 0.031340 | 0.003280 to 0.059400 | 0.016957 | **1.85** |
| busca-generica | **−0.014840** | −0.054512 to 0.024831 | 0.007065 | **−2.10** |
| email | **−0.093731** | −0.355965 to 0.168503 | 0.018087 | **−5.18** |
| busca-marca | 0.049819 | −0.004444 to 0.104082 | 0.000000 | — |
| retargeting | −0.016337 | −0.089660 to 0.056986 | 0.000000 | — |

R-squared falls from **0.8364 to 0.2371**. Of the three channels with a real effect, two come back
negative, and social-pago is confidently 1.85 times its real marginal return — confidently, because
that interval still excludes zero.

The reassuring half: this misspecification is visible. A fit that collapses by six tenths is not
subtle, and anybody comparing two specifications would keep the right one. The unreassuring half:
**every interval still covers the truth.** A model can be wrong about the sign of most of an account
and never be caught by its own coverage, because intervals that wide cover almost anything.

## Result 7: the same account, measured both ways

The two instruments do not estimate the same quantity — the holdout measures the average return over
the period, the coefficient the marginal return at current spend — so comparing their point estimates
would be a mistake. What compares is each one's precision **relative to the quantity it is
estimating**:

| Channel | Holdout interval ÷ truth | Model interval ÷ truth | Model is wider by | Holdout resolved | Model resolved |
| --- | --- | --- | --- | --- | --- |
| social-pago | 0.1251 | 1.6423 | **13.13×** | yes | yes |
| email | 1.1015 | 14.1037 | **12.80×** | yes | no |
| busca-generica | 0.4668 | 5.3779 | **11.52×** | yes | no |
| retargeting | — | — | — | no | no |
| busca-marca | — | — | — | no | no |

**The holdout resolved three channels of five; the model resolved one.** Where there is a truth to be
judged against, the model's interval is eleven to thirteen times wider.

That is the trade stated honestly, and it is a trade rather than a verdict. The holdout costs 260
region-weeks per channel and thirteen weeks of calendar, and across five of them it resolved three.
The model costs nothing, answers about all five channels at once, and its answer on four of them is
*somewhere between a negative number and several times the truth*. Both are real instruments. Only
one of them is usually presented with its width attached.

## Assumptions and limitations

- **Every number here comes from a seeded synthetic generator**, including the carryover, the
  saturation point and the returns the model is judged against. No advertiser, agency, platform or
  client data is used anywhere. See [`DISCLAIMER.md`](../../../DISCLAIMER.md).
- **This is ordinary least squares, not a Bayesian hierarchical model**, which is what a commercial
  media mix model usually is. The choice is deliberate: the pathologies are the same — collinearity
  that shows up as inflated standard errors here shows up as posterior correlation there — and least
  squares makes them arithmetic instead of diagnostics. What a prior adds is information the data does
  not contain, which is sometimes the right thing to do and is never free. A hierarchical model with a
  tight prior on the coefficients would report narrower intervals on this panel without the panel
  having become more informative.
- **The model is handed the true transforms in Results 1 to 4, and that is a favour.** A real
  practitioner picks them, usually by fit, and Result 5 is what that costs. Every width in Result 2 is
  therefore a floor.
- **The response is additive and the effects are constant.** No interaction between channels, no
  competitive response, no change in the effects over the two years. Each of those would widen
  everything and none would narrow it.
- **The saturation is a Hill curve with exponent one and a shared half point** as a multiple of each
  channel's own mean spend. That is why the ratio between average and marginal return in Result 3 is
  identical across channels — an artefact of the generator, not a fact about media.
- **A hundred and four weeks estimate nine parameters.** That ratio is generous by the standards of
  real practice, where two years and a dozen channels is normal, and the widths here are what the
  generous case looks like.
- **The condition number is computed on the centred channel block.** Left uncentred the same matrix
  scores 69.1 against 7.0, because the saturated spend columns are all positive with similar means and
  that near-constant direction dominates the decomposition. The intercept absorbs the level, so
  centring is what makes the number a statement about the slopes. Quoting the uncentred figure would
  be inflating the alarm with an artefact.
- **Nothing here searches over lag structures, spend caps, competitor variables or macro controls**,
  all of which a real model carries and each of which is another dimension of the grid in Result 5.
- **The holdout comparison in Result 7 is between one model and one experiment on one dataset.** It is
  an illustration of the mechanism, not an estimate of how much better experiments are in general.

## Sources

- Belsley, D. A., Kuh, E., Welsch, R. E. (1980). *Regression Diagnostics: Identifying Influential Data
  and Sources of Collinearity.* Wiley. — the condition number and why it is computed on centred,
  scaled columns.
- Chan, D., Perry, M. (2017). *Challenges and Opportunities in Media Mix Modeling.* Google Research. —
  the collinearity and identification problems this document measures.
- Jin, Y., Wang, Y., Sun, Y., Chan, D., Koehler, J. (2017). *Bayesian Methods for Media Mix Modeling
  with Carryover and Shape Effects.* Google Research. — the adstock and Hill transforms, and the
  Bayesian treatment this module deliberately is not.
- Gordon, B. R., Zettelmeyer, F., Bhargava, N., Chapsky, D. (2019). *A Comparison of Approaches to
  Advertising Measurement.* Marketing Science 38(2). — observational methods against experiments on
  the same campaigns.
- Lewis, R. A., Rao, J. M. (2015). *The Unfavorable Economics of Measuring the Returns to
  Advertising.* Quarterly Journal of Economics 130(4).

---

# `mktlab.mmm` — o modelo que substitui o experimento

*[English](#mktlabmmm--the-model-that-replaces-the-experiment)*

## O problema de negócio

As ondas 2 a 4 precificaram o holdout: o que ele resolve, quanto custa e como monitorá-lo
honestamente. Cada uma dessas respostas é um motivo para alguém dizer não. Um media mix model é o que
se constrói no lugar — uma regressão de conversões semanais sobre investimento semanal, nenhuma
região desligada, nenhuma conversão abdicada, uma resposta para todos os canais de uma vez.

Este documento ajusta um na mesma conta, entrega a ele **o carryover e a saturação do próprio
gerador** — um favor que nenhum modelo real recebe — e pergunta o que ele consegue sustentar. Com
R-quadrado de 0,84 e nenhuma especificação errada, ele distingue de zero **um canal em cinco**. Os
outros quatro intervalos cobrem os dois sinais, e um deles é quatorze vezes o tamanho do retorno que
está estimando.

O modelo não está mentindo: os cinco intervalos contêm a verdade. Ele é pouco informativo, e o slide
mostra as estimativas pontuais.

## A decisão que habilita

1. **Este painel consegue responder à pergunta do orçamento?** Isso é decidido pelo plano de mídia,
   antes de qualquer modelagem, e está visível na matriz de correlação.
2. **Quanto da resposta veio dos transformes que adivinhamos?** Um dos dois palpites importa e é
   recuperável do ajuste; o outro é quase invisível para ele.
3. **E o que o experimento teria comprado?** Onze a treze vezes a precisão, relativa à quantidade que
   cada instrumento estima.

## Uso

```python
from mktlab.mmm import fit, transform_grid, variance_inflation
from mktlab.synth import MEDIA_MIX, generate_dataset

data = generate_dataset()
fitted = fit(data.spend_panel)  # os transformes do próprio gerador: o melhor caso possível
fitted.r_squared  # 0,8364
fitted.table()  # coeficiente, erro-padrão, p-valor, intervalo, inflação de variância
fitted.returns(data.media_truth)  # o mesmo como retornos, contra a verdade

fitted.equivalent_range(4, r_squared_loss=0.005)  # (58,02, 220,72) - ver o Resultado 4
transform_grid(data.spend_panel, (0.2, 0.45, 0.6), (0.5, 1.3, 3.0), data.media_truth)
```

## Resultado 1: os canais se movem juntos, porque é assim que planos são escritos

O orçamento do painel oscila 30% de semana para semana e cada canal se move apenas 12% por conta
própria. Isso não é uma construção patológica — um plano de mídia é escrito como frações de um
orçamento, então quando o orçamento se move os canais se movem com ele.

| | busca-generica | busca-marca | email | retargeting | social-pago |
| --- | --- | --- | --- | --- | --- |
| **busca-generica** | 1,0000 | 0,8305 | 0,8412 | 0,8388 | 0,8387 |
| **busca-marca** | 0,8305 | 1,0000 | 0,8771 | 0,8363 | 0,8310 |
| **email** | 0,8412 | 0,8771 | 1,0000 | 0,8539 | 0,8789 |
| **retargeting** | 0,8388 | 0,8363 | 0,8539 | 1,0000 | 0,8584 |
| **social-pago** | 0,8387 | 0,8310 | 0,8789 | 0,8584 | 1,0000 |

Todo par correlaciona acima de 0,83, e a consequência é aritmética:

| Canal | Inflação de variância | Multiplicador do erro-padrão |
| --- | --- | --- |
| email | **8,5249** | **2,9197** |
| busca-generica | 6,8811 | 2,6232 |
| busca-marca | 6,4804 | 2,5457 |
| social-pago | 6,3857 | 2,5270 |
| retargeting | 5,7315 | 2,3940 |

**Todo intervalo de confiança é duas e meia a três vezes mais largo do que seria com investimento
independente.** O número de condição do bloco de canais centrado é 7,01, confortavelmente abaixo da
linha convencional de alerta de trinta — o que vale saber, porque o alarme que *não* soa aqui não é
evidência de que o modelo está bem. A inflação de variância é o diagnóstico que morde.

## Resultado 2: com os transformes certos, ele resolve um canal em cinco

Ajustado com o carryover de 0,45 do próprio gerador e saturação em 1,30 vez o investimento semanal
médio, mais tendência linear e par sazonal. R-quadrado 0,8364, desvio-padrão residual 8,718 contra um
ruído de gerador de 9,0 — o modelo recuperou o nível de ruído quase exatamente, que é o ajuste
funcionando.

| Canal | Coeficiente | Erro-padrão | t | p | Intervalo 95% | VIF |
| --- | --- | --- | --- | --- | --- | --- |
| social-pago | **139,3700** | 47,7410 | 2,9193 | **0,0044** | 44,59 a 234,15 | 6,3857 |
| busca-generica | 18,5883 | 44,3302 | 0,4193 | 0,6759 | −69,42 a 106,59 | 6,8811 |
| email | 5,7788 | 49,9995 | 0,1156 | 0,9082 | −93,48 a 105,04 | 8,5249 |
| retargeting | 2,7547 | 42,4445 | 0,0649 | 0,9484 | −81,51 a 87,02 | 5,7315 |
| busca-marca | **−16,6503** | 46,6161 | −0,3572 | 0,7217 | −109,20 a 75,89 | 6,4804 |

Como os retornos sobre os quais um orçamento decide, contra a verdade da qual o painel foi
construído:

| Canal | Retorno marginal | Intervalo 95% | Verdade | Cobre | Vezes a verdade | Intervalo ÷ verdade |
| --- | --- | --- | --- | --- | --- | --- |
| social-pago | 0,020475 | 0,006551 a 0,034398 | 0,016957 | sim | 1,21 | **1,64** |
| busca-generica | 0,004013 | −0,014985 a 0,023011 | 0,007065 | sim | 0,57 | **5,38** |
| email | 0,007425 | −0,120121 a 0,134972 | 0,018087 | sim | 0,41 | **14,10** |
| retargeting | 0,001194 | −0,035331 a 0,037719 | 0,000000 | sim | — | — |
| busca-marca | −0,004758 | −0,031202 a 0,021687 | 0,000000 | sim | — | — |

**Cinco intervalos de cinco contêm a verdade e um de cinco exclui zero.** O modelo é honesto e quase
silencioso. A estimativa pontual da busca de marca é negativa para um canal cujo efeito real é zero; o
intervalo do email é quatorze vezes o tamanho do retorno que estima; a busca genérica sai em 0,57 vez
sua verdade. Um slide mostrando essas cinco estimativas pontuais como recomendação de orçamento
estaria reportando ruído com a forma de uma resposta.

## Resultado 3: leia as duas colunas de retorno separadas

| Canal | Retorno médio | Retorno marginal | Razão |
| --- | --- | --- | --- |
| social-pago | 0,0300 | 0,016957 | 1,77 |
| email | 0,0320 | 0,018087 | 1,77 |
| busca-generica | 0,0125 | 0,007065 | 1,77 |

O retorno **médio** é quanto desligar o canal custaria, por unidade investida nele — que é o que um
holdout mede. O retorno **marginal** é a derivada no nível de investimento em que o canal está — que é
o que um coeficiente de regressão estima. Onde a resposta está dobrando, os dois diferem por um fator
de 1,77 aqui, e a razão é a mesma para todo canal apenas porque todos receberam o mesmo ponto de
saturação.

Citar um coeficiente como "o ROAS do canal" confunde os dois — na direção lisonjeira se você está
defendendo um corte e na desfavorável se está defendendo um aumento. As duas colunas existem para que
a confusão tenha de ser deliberada.

## Resultado 4: a faixa que ajusta igualmente bem *é* o intervalo de confiança

A demonstração que todo mundo pede a um modelo colinear: *aqui está uma resposta completamente
diferente que ajusta igualmente bem.* Para o coeficiente do social-pago:

| Ajuste sacrificado | O coeficiente pode ser | Amplitude |
| --- | --- | --- |
| 0,001 de R-quadrado | 102,99 a 175,75 | 72,77 |
| 0,005 de R-quadrado | 58,02 a 220,72 | 162,71 |
| 0,010 de R-quadrado | 24,32 a 254,42 | 230,10 |
| **o intervalo de 95%** | **44,59 a 234,15** | **189,56** |

**E o que sai de calcular isso corretamente é que não há nada de novo ali.** O perfil tem forma
fechada — o mais longe que um coeficiente consegue ir enquanto a soma dos quadrados dos resíduos sobe
δ é seu erro-padrão vezes √(δ/σ̂²) — então a "faixa de ajustes igualmente bons" é o erro-padrão
reescalado. O intervalo de 95% é exatamente o conjunto de coeficientes que custa cerca de **0,0068 de
R-quadrado**.

Essa é a versão útil da reclamação sobre modelos colineares. Não existe um segundo diagnóstico
escondido atrás do erro-padrão: o erro-padrão *era* o diagnóstico, e é a coluna que cai quando o
gráfico é desenhado.

## Resultado 5: um palpite importa, o outro quase não registra

Nem o carryover nem o ponto de saturação são observáveis. Vinte combinações, ajustadas:

| Adstock | Saturação em | R-quadrado | Perda de ajuste | Retorno implícito do social-pago | Vezes a verdade |
| --- | --- | --- | --- | --- | --- |
| **0,45** | 3,0 | 0,836444 | 0,000000 | 0,020463 | 1,21 |
| **0,45** | 1,3 | 0,836425 | 0,000019 | 0,020475 | 1,21 |
| **0,45** | 10,0 | 0,836148 | 0,000295 | 0,020174 | 1,19 |
| **0,45** | 0,5 | 0,835689 | 0,000754 | 0,019968 | 1,18 |
| 0,60 | 1,3 | 0,831749 | 0,004695 | 0,025993 | **1,53** |
| 0,60 | 0,5 | 0,831276 | 0,005167 | 0,026049 | **1,54** |
| 0,20 | 10,0 | 0,823651 | 0,012793 | 0,014909 | 0,88 |
| 0,20 | 0,5 | 0,819866 | 0,016578 | 0,014342 | 0,85 |

Oito dos vinte desenhos ajustam dentro de 0,01 do melhor, e entre eles o retorno implícito vai de
**1,18× a 1,54×** a verdade. Mas leia a grade por coluna, porque a versão preguiçosa desta reclamação
está errada:

- **O ajuste identifica o carryover.** O 0,45 do gerador ganha, e mover para 0,60 custa 0,0047 de
  R-quadrado enquanto move o retorno em um quarto. Essa é uma diferença detectável.
- **O ajuste é quase cego ao ponto de saturação.** No carryover correto, todo valor de 0,5 a 10,0 — uma
  faixa de vinte vezes — fica dentro de 0,0008 do melhor ajuste e move o retorno em um por cento.

Então um dos dois parâmetros não observáveis é recuperável dos dados e o outro não é — e neste painel o
que não é quase não importa. "Os transformes são arbitrários, então a resposta é arbitrária" é um
slogan; a grade diz qual metade dele é verdadeira.

## Resultado 6: o que acontece quando o modelo deixa algo de fora

Ajustado sem a tendência e sem o par sazonal, que um modelo não tem como saber que existem:

| Canal | Retorno marginal | Intervalo 95% | Verdade | Vezes a verdade |
| --- | --- | --- | --- | --- |
| social-pago | 0,031340 | 0,003280 a 0,059400 | 0,016957 | **1,85** |
| busca-generica | **−0,014840** | −0,054512 a 0,024831 | 0,007065 | **−2,10** |
| email | **−0,093731** | −0,355965 a 0,168503 | 0,018087 | **−5,18** |
| busca-marca | 0,049819 | −0,004444 a 0,104082 | 0,000000 | — |
| retargeting | −0,016337 | −0,089660 a 0,056986 | 0,000000 | — |

O R-quadrado cai de **0,8364 para 0,2371**. Dos três canais com efeito real, dois voltam negativos, e
o social-pago é confiantemente 1,85 vez seu retorno marginal real — confiantemente, porque aquele
intervalo ainda exclui zero.

A metade tranquilizadora: essa especificação errada é visível. Um ajuste que despenca seis décimos não
é subtil, e qualquer um comparando duas especificações manteria a certa. A metade não tranquilizadora:
**todo intervalo ainda cobre a verdade.** Um modelo pode errar o sinal da maior parte de uma conta e
nunca ser pego pela própria cobertura, porque intervalos tão largos cobrem quase qualquer coisa.

## Resultado 7: a mesma conta, medida das duas formas

Os dois instrumentos não estimam a mesma quantidade — o holdout mede o retorno médio do período, o
coeficiente o retorno marginal no investimento atual — então comparar suas estimativas pontuais seria
um erro. O que se compara é a precisão de cada um **relativa à quantidade que ele estima**:

| Canal | Intervalo do holdout ÷ verdade | Intervalo do modelo ÷ verdade | Modelo é mais largo em | Holdout resolveu | Modelo resolveu |
| --- | --- | --- | --- | --- | --- |
| social-pago | 0,1251 | 1,6423 | **13,13×** | sim | sim |
| email | 1,1015 | 14,1037 | **12,80×** | sim | não |
| busca-generica | 0,4668 | 5,3779 | **11,52×** | sim | não |
| retargeting | — | — | — | não | não |
| busca-marca | — | — | — | não | não |

**O holdout resolveu três canais de cinco; o modelo resolveu um.** Onde há verdade contra a qual
julgar, o intervalo do modelo é onze a treze vezes mais largo.

Essa é a troca dita honestamente, e é uma troca e não um veredito. O holdout custa 260 região-semanas
por canal e treze semanas de calendário, e em cinco deles resolveu três. O modelo não custa nada,
responde sobre os cinco canais de uma vez, e sua resposta sobre quatro deles é *algo entre um número
negativo e várias vezes a verdade*. Os dois são instrumentos reais. Só um deles costuma ser
apresentado com sua largura anexada.

## Premissas e limitações

- **Todo número aqui vem de um gerador sintético com semente**, inclusive o carryover, o ponto de
  saturação e os retornos contra os quais o modelo é julgado. Nenhum dado de anunciante, agência,
  plataforma ou cliente é usado em lugar algum. Ver [`DISCLAIMER.md`](../../../DISCLAIMER.md).
- **Isto é mínimos quadrados ordinários, não um modelo bayesiano hierárquico**, que é o que um media
  mix model comercial normalmente é. A escolha é deliberada: as patologias são as mesmas —
  colinearidade que aparece como erro-padrão inflado aqui aparece como correlação posterior lá — e
  mínimos quadrados as torna aritmética em vez de diagnóstico. O que uma priori acrescenta é informação
  que os dados não contêm, o que às vezes é a coisa certa a fazer e nunca é grátis. Um modelo
  hierárquico com priori apertada sobre os coeficientes reportaria intervalos mais estreitos neste
  painel sem que o painel tenha ficado mais informativo.
- **O modelo recebe os transformes verdadeiros nos Resultados 1 a 4, e isso é um favor.** Um
  praticante real os escolhe, normalmente por ajuste, e o Resultado 5 é o que isso custa. Toda largura
  do Resultado 2 é, portanto, um piso.
- **A resposta é aditiva e os efeitos são constantes.** Nenhuma interação entre canais, nenhuma
  resposta competitiva, nenhuma mudança dos efeitos ao longo dos dois anos. Cada uma dessas coisas
  alargaria tudo e nenhuma estreitaria.
- **A saturação é uma curva de Hill com expoente um e ponto de meia-resposta compartilhado** como
  múltiplo do investimento médio de cada canal. É por isso que a razão entre retorno médio e marginal
  no Resultado 3 é idêntica entre canais — artefato do gerador, não fato sobre mídia.
- **Cento e quatro semanas estimam nove parâmetros.** Essa razão é generosa pelos padrões da prática
  real, em que dois anos e uma dúzia de canais é o normal, e as larguras aqui são como o caso generoso
  se parece.
- **O número de condição é calculado no bloco de canais centrado.** Sem centrar, a mesma matriz marca
  69,1 contra 7,0, porque as colunas de investimento saturado são todas positivas com médias parecidas
  e essa direção quase constante domina a decomposição. O intercepto absorve o nível, então centrar é o
  que faz o número ser uma afirmação sobre as inclinações. Citar a cifra não centrada seria inflar o
  alarme com um artefato.
- **Nada aqui busca sobre estruturas de defasagem, tetos de investimento, variáveis de concorrência ou
  controles macro**, que um modelo real carrega e que são cada um outra dimensão da grade do Resultado
  5.
- **A comparação com o holdout no Resultado 7 é entre um modelo e um experimento num conjunto de
  dados.** É uma ilustração do mecanismo, não uma estimativa de quanto experimentos são melhores em
  geral.

## Fontes

- Belsley, D. A., Kuh, E., Welsch, R. E. (1980). *Regression Diagnostics: Identifying Influential Data
  and Sources of Collinearity.* Wiley. — o número de condição e por que é calculado em colunas
  centradas e escaladas.
- Chan, D., Perry, M. (2017). *Challenges and Opportunities in Media Mix Modeling.* Google Research. —
  os problemas de colinearidade e identificação que este documento mede.
- Jin, Y., Wang, Y., Sun, Y., Chan, D., Koehler, J. (2017). *Bayesian Methods for Media Mix Modeling
  with Carryover and Shape Effects.* Google Research. — os transformes de adstock e Hill, e o
  tratamento bayesiano que este módulo deliberadamente não é.
- Gordon, B. R., Zettelmeyer, F., Bhargava, N., Chapsky, D. (2019). *A Comparison of Approaches to
  Advertising Measurement.* Marketing Science 38(2). — métodos observacionais contra experimentos nas
  mesmas campanhas.
- Lewis, R. A., Rao, J. M. (2015). *The Unfavorable Economics of Measuring the Returns to
  Advertising.* Quarterly Journal of Economics 130(4).
