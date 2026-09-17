# `mktlab.attribution` — who gets the credit, and who actually earned it

*[Português](#mktlabattribution--quem-leva-o-crédito-e-quem-de-fato-o-mereceu)*

## The business problem

A monthly report says retargeting returned 9.43 on every unit spent and branded search 8.05. They
rank second and third in the account. Both figures are arithmetically correct, both come straight
out of the platform, and in this dataset **both channels have a true effect of exactly zero**.

Nothing was faked to produce that. The two channels are shown to people who were already going to
convert — retargeting to users who visited, branded search to users who typed the brand name — and
a rule that divides completed conversions among the channels that were present cannot tell presence
from cause. The report is not a bad estimate of the channel's contribution. It is a correct estimate
of a different quantity: how often the channel was standing nearby when something good happened.

## The decision it enables

1. **If this channel were switched off, what would we lose?** Which is the only question a budget
   asks, and the only one no attribution model answers.
2. **How much does the answer depend on the rule we picked?** Because the rules disagree by
   multiples, not by margins, on data that has not changed.
3. **Which channels have we established anything about?** Not "which scored well" — which ones
   survived a test that could have said no.

## Usage

```python
from mktlab.attribution import credit, credit_table, geo_lift, returns, unattributable
from mktlab.synth import AUDIENCE, GEO, generate_dataset

data = generate_dataset()

credit_table(data.journeys)  # six models side by side, as shares
unattributable(data.audience, data.journeys)  # the conversions no model can see

panel = data.geo_experiments[data.geo_experiments["channel"] == "busca-marca"]
lift = geo_lift(panel, split=GEO.split, channel="busca-marca")
lift.lift, lift.p_value, lift.significant  # -0.000723, 0.4044, False
lift.verdict()  # "... not distinguishable from nothing"
```

## Result 1: six models, one set of journeys

200,000 users, 277,849 touches, 19,393 conversions. The shares below are of the conversions each
model can see.

| Channel | True effect | last-click | first-click | linear | position 40-20-40 | time-decay | Shapley |
| --- | --- | --- | --- | --- | --- | --- | --- |
| social-pago | **+0.060** | 0.2067 | 0.6662 | 0.4027 | 0.4184 | 0.3219 | 0.4027 |
| email | +0.010 | 0.1605 | 0.1594 | 0.1925 | 0.1780 | 0.1840 | 0.1925 |
| busca-generica | +0.030 | 0.2213 | 0.1004 | 0.1811 | 0.1711 | 0.2001 | 0.1811 |
| retargeting | **0.000** | 0.1805 | 0.0439 | 0.1144 | 0.1130 | 0.1416 | 0.1144 |
| busca-marca | **0.000** | 0.2311 | 0.0301 | 0.1093 | 0.1195 | 0.1524 | 0.1093 |

**Last-click gives the two channels with no effect 41.16% of the credit**, and makes busca-marca —
whose true effect is zero — the single largest line in the account at 23.11%. This is not a flaw in
last-click's arithmetic. It is what "last touch before the conversion" means when a channel's whole
targeting rule is *people who are about to convert*: its exposure rises with intent at a slope of
0.80, the steepest in the account, and the conversion arrives right after it by construction.

**The two ends of the same journey disagree by up to 7.67×.** social-pago gets 3.22 times more
credit from first-click than from last-click; busca-marca gets 7.67 times more from last-click than
from first-click. Same users, same touches, same order. Only the rule changed, and the rule was
chosen by whoever configured the dashboard.

## Result 2: the "data-driven" model is divide-by-n

The Shapley value is the standard defence: it is not an arbitrary rule, it comes from cooperative
game theory, it accounts for interactions. On the coverage game — where a coalition's worth is the
conversions whose whole journey sits inside it — it is computed here from the definition, over all
2⁵ coalitions, with the factorial weights:

| Channel | Shapley | Linear | Difference |
| --- | --- | --- | --- |
| social-pago | 7015.233333 | 7015.233333 | 0 |
| email | 3353.483333 | 3353.483333 | 0 |
| busca-generica | 3153.983333 | 3153.983333 | 0 |
| retargeting | 1992.066667 | 1992.066667 | 0 |
| busca-marca | 1904.233333 | 1904.233333 | 0 |

**They are the same allocation.** The largest absolute difference is 9.09e-13 conversions out of
17,419, and 2.8e-17 as a share — floating point, not disagreement. The reason is structural rather
than numerical: in the coverage game a journey's value is indivisible and appears only when every
one of its channels is present, so each of its *k* channels has the same marginal contribution in
the same number of orderings, and the Shapley value of that journey is 1/*k* to each. Summed over
journeys, that is exactly linear attribution.

Two consequences worth stating plainly. The order of the touches never enters the coverage game at
all, so a model marketed as understanding the customer journey is provably indifferent to it. And a
vendor charging for the algorithmic model, on this game, is charging for dividing by the number of
channels. Any *actual* difference a platform's data-driven model shows against linear attribution
comes from a different game definition, which is the thing to ask them for — not from the Shapley
value itself.

## Result 3: 10.18% of the conversions belong to nobody

| | Conversions |
| --- | --- |
| In the period | 19,393 |
| With at least one touch | 17,419 |
| **Touched by nothing at all** | **1,974 (10.18%)** |

Every share in the tables above divides the 17,419. The 1,974 are users who converted with no
marketing contact — in this generator, high-intent users the channels happened to miss. A report
that presents channel shares as adding to one hundred per cent of the business has silently handed
those 1,974 conversions to the channels **in proportion to the credit they already had**, which
means the channel that over-credits itself most also absorbs the most of what it never touched.

That error was in this module's own code first: `returns` originally multiplied each channel's
*share* by total conversions. The fix is that it reads the model's absolute `credited` column, and
the API no longer takes a total to rescale against.

## Result 4: the holdout, which can say no

40 regions, 26 weeks, one panel per channel, the channel switched off in half the regions after
week 13. Each region contributes one number — how much its conversion rate changed — and the lift
is the treated regions' mean change minus the holdout regions', compared with Welch's test on those
40 region-level observations. A panel of 40 regions over 26 weeks is not 1,040 independent
observations of a change.

| Channel | Lift (rate points) | 95% interval | p | Significant | True lift | Interval covers truth |
| --- | --- | --- | --- | --- | --- | --- |
| social-pago | +0.028490 | +0.026890 to +0.030091 | 0.0000 | yes | 0.0270 | yes |
| busca-generica | +0.006133 | +0.004620 to +0.007645 | 0.0000 | yes | 0.0075 | yes |
| email | +0.002898 | +0.000650 to +0.005146 | 0.0131 | yes | 0.0032 | yes |
| retargeting | +0.000629 | −0.001090 to +0.002348 | 0.4633 | no | 0.0000 | yes |
| busca-marca | −0.000723 | −0.002461 to +0.001015 | 0.4044 | no | 0.0000 | yes |

**Five intervals out of five contain the truth, and the two channels with no effect are exactly
the two the test refuses to separate from zero.** The estimator is not smarter than attribution; it
is aimed at the right quantity. Note what "not significant" buys here: busca-marca's point estimate
is *negative*, and the honest reading is not "branded search hurts" but "this test cannot tell, and
its interval is ±0.0017 rate points wide."

## Result 5: the ranking inverts

Last-click credit priced at 180.00 per conversion, against the same channels' incremental
conversions from the holdout, over 200,000 users:

| Channel | Spend | Credited | ROAS | Incremental | iROAS | Established | ROAS ÷ iROAS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| email | 20,000 | 2,796 | **25.16** | 579.6 | 5.2165 | yes | 4.82 |
| retargeting | 60,000 | 3,144 | **9.43** | 125.8 | 0.3773 | **no** | — |
| busca-marca | 90,000 | 4,025 | **8.05** | −144.6 | −0.2892 | **no** | — |
| busca-generica | 120,000 | 3,854 | 5.78 | 1,226.5 | 1.8398 | yes | 3.14 |
| social-pago | 180,000 | 3,600 | **3.60** | 5,698.1 | **5.6981** | yes | **0.63** |

Read top to bottom, that is the report's ranking. Three things in it are wrong in three different
ways.

**The two channels ranked second and third have no established return.** 150,000 of 470,000 —
**31.9% of the budget** — is spent where the holdout cannot distinguish the effect from nothing.
Note that this is not the same claim as "wasted": a test that fails to reject is not proof of zero.
It is the weaker and more useful claim that after running a 13-week holdout across 20 regions, the
account still has no evidence for a third of its spend.

**The ratio is deliberately `nan` where nothing was established.** busca-marca's iROAS of −0.2892
would read as a finding, and it is not one: it is a point estimate whose interval covers zero,
divided into a spend. Publishing a ratio against an unmeasured denominator is how a non-result
becomes a slide, so `returns` returns `nan` and an `established` column instead.

**And the error runs the other way too, which is the part that gets missed.** social-pago is the
*worst* channel by ROAS at 3.60 and the best by iROAS at 5.70 — a ratio of **0.63**. It is the only
channel that creates demand rather than harvesting it, so the conversions it starts are closed
weeks later by somebody standing closer to the sale. An account optimised on ROAS does not merely
overspend on branded search; it defunds the channel that fills the funnel, and then watches branded
search volume fall for reasons the dashboard cannot explain.

Blended, the account reports **ROAS 6.6711 against iROAS 2.8667** — the same spend and the same
period, 2.3 times apart.

## Assumptions and limitations

- **Every number here comes from a seeded synthetic generator**, including the intent column that
  makes the comparison possible. No advertiser, agency or platform data is used anywhere. See
  [`DISCLAIMER.md`](../../../DISCLAIMER.md). The channel names are invented Portuguese labels for
  generic functions, not any real account's structure.
- **The generator's selection mechanism is the whole result.** Exposure is drawn as a linear
  function of intent, and conversion as a base rate plus intent plus the true effects of the
  channels that reached the user. Real accounts are selected on more than one latent variable, with
  feedback from the campaign to the targeting, and both would widen the gaps below rather than
  close them.
- **The Shapley identity is a property of the coverage game**, not of every conceivable data-driven
  model. A game whose value function splits partial journeys, or weights order, gives a different
  answer. The claim proved here is that the coverage game — the standard formulation — is linear
  attribution.
- **The holdout estimates a rate effect for a period, not a demand curve.** It says what switching
  the channel off did at this spend level in these regions over 13 weeks. It does not give the
  marginal return on the next unit of spend, which is a different experiment.
- **`incremental_conversions(reach)` takes the population as an argument on purpose.** Scaling a
  rate to conversions needs a business fact, and inferring it silently is how a geo result becomes
  a number nobody can reproduce.
- **Geo tests carry interference and a real cost.** Regions are treated as independent here; in
  practice people move between them and platforms optimise across them. And the test is not free:
  half the regions lose the channel for 13 weeks, which is the trade-off the next wave sizes.
- **Non-significant is not zero.** Two channels here are truly zero and the test says "cannot
  tell". Those are different statements, and the module's `verdict()` is worded to keep them apart.
- **And "untested" is a third statement again.** A holdout with one region on a side gives a
  difference and no spread, so `geo_lift` returns the lift with `untested_because` filled in rather
  than a `nan` standard error that reads downstream as "not significant". That was a defect here:
  a two-region design — which people do run — arrived looking exactly like a channel that had been
  measured and found to do nothing. The Welch degrees of freedom are computed in closed form for
  the same reason, so a noiseless control panel returns a number instead of a warning.

## Sources

- Shapley, L. S. (1953). *A Value for n-Person Games.* Contributions to the Theory of Games II.
- Dalessandro, B., Perlich, C., Stitelman, O., Provost, F. (2012). *Causally Motivated Attribution
  for Online Advertising.* ADKDD.
- Lewis, R. A., Rao, J. M. (2015). *The Unfavorable Economics of Measuring the Returns to
  Advertising.* Quarterly Journal of Economics 130(4).
- Blake, T., Nosko, C., Tadelis, S. (2015). *Consumer Heterogeneity and Paid Search Effectiveness:
  A Large-Scale Field Experiment.* Econometrica 83(1). — the branded-search holdout this module's
  busca-marca channel is modelled on.
- Gordon, B. R., Zettelmeyer, F., Bhargava, N., Chapsky, D. (2019). *A Comparison of Approaches to
  Advertising Measurement.* Marketing Science 38(2).
- Vaver, J., Koehler, J. (2011). *Measuring Ad Effectiveness Using Geo Experiments.* Google
  Research.

---

# `mktlab.attribution` — quem leva o crédito, e quem de fato o mereceu

*[English](#mktlabattribution--who-gets-the-credit-and-who-actually-earned-it)*

## O problema de negócio

Um relatório mensal diz que retargeting devolveu 9,43 por unidade investida e a busca de marca
8,05. São o segundo e o terceiro colocados da conta. As duas cifras estão aritmeticamente corretas,
as duas saem direto da plataforma, e neste conjunto de dados **os dois canais têm efeito verdadeiro
exatamente zero**.

Nada foi forjado para chegar a isso. Os dois canais são exibidos a quem já ia converter —
retargeting a quem visitou, busca de marca a quem digitou o nome da marca — e uma regra que divide
conversões concluídas entre os canais presentes não distingue presença de causa. O relatório não é
uma estimativa ruim da contribuição do canal. É uma estimativa correta de outra quantidade: com que
frequência o canal estava por perto quando algo bom aconteceu.

## A decisão que habilita

1. **Se este canal fosse desligado, o que perderíamos?** É a única pergunta que um orçamento faz, e
   a única que nenhum modelo de atribuição responde.
2. **Quanto a resposta depende da regra escolhida?** Porque as regras divergem por múltiplos, não
   por margens, sobre dados que não mudaram.
3. **Sobre quais canais nós estabelecemos algo?** Não "quais pontuaram bem" — quais sobreviveram a
   um teste que podia ter dito não.

## Uso

```python
from mktlab.attribution import credit, credit_table, geo_lift, returns, unattributable
from mktlab.synth import AUDIENCE, GEO, generate_dataset

data = generate_dataset()

credit_table(data.journeys)  # seis modelos lado a lado, em participação
unattributable(data.audience, data.journeys)  # as conversões que nenhum modelo vê

panel = data.geo_experiments[data.geo_experiments["channel"] == "busca-marca"]
lift = geo_lift(panel, split=GEO.split, channel="busca-marca")
lift.lift, lift.p_value, lift.significant  # -0,000723, 0,4044, False
lift.verdict()  # "... not distinguishable from nothing"
```

## Resultado 1: seis modelos, uma mesma base de jornadas

200.000 usuários, 277.849 toques, 19.393 conversões. As participações abaixo são sobre as
conversões que cada modelo consegue ver.

| Canal | Efeito real | last-click | first-click | linear | posição 40-20-40 | time-decay | Shapley |
| --- | --- | --- | --- | --- | --- | --- | --- |
| social-pago | **+0,060** | 0,2067 | 0,6662 | 0,4027 | 0,4184 | 0,3219 | 0,4027 |
| email | +0,010 | 0,1605 | 0,1594 | 0,1925 | 0,1780 | 0,1840 | 0,1925 |
| busca-generica | +0,030 | 0,2213 | 0,1004 | 0,1811 | 0,1711 | 0,2001 | 0,1811 |
| retargeting | **0,000** | 0,1805 | 0,0439 | 0,1144 | 0,1130 | 0,1416 | 0,1144 |
| busca-marca | **0,000** | 0,2311 | 0,0301 | 0,1093 | 0,1195 | 0,1524 | 0,1093 |

**O last-click entrega aos dois canais sem efeito 41,16% do crédito** e faz da busca de marca —
cujo efeito real é zero — a maior linha isolada da conta, com 23,11%. Isso não é uma falha da
aritmética do last-click. É o que "último toque antes da conversão" significa quando toda a regra de
segmentação do canal é *pessoas que estão a ponto de converter*: sua exposição cresce com a intenção
a uma inclinação de 0,80, a mais inclinada da conta, e a conversão chega logo depois dele por
construção.

**As duas pontas da mesma jornada divergem até 7,67×.** O social-pago recebe 3,22 vezes mais
crédito do first-click que do last-click; a busca de marca recebe 7,67 vezes mais do last-click que
do first-click. Mesmos usuários, mesmos toques, mesma ordem. Só a regra mudou — e a regra foi
escolhida por quem configurou o painel.

## Resultado 2: o modelo "data-driven" é dividir por n

O valor de Shapley é a defesa padrão: não é uma regra arbitrária, vem da teoria dos jogos
cooperativos, considera interações. No jogo de cobertura — em que o valor de uma coalizão são as
conversões cuja jornada inteira está dentro dela — ele é calculado aqui a partir da definição, sobre
todas as 2⁵ coalizões, com os pesos fatoriais:

| Canal | Shapley | Linear | Diferença |
| --- | --- | --- | --- |
| social-pago | 7015,233333 | 7015,233333 | 0 |
| email | 3353,483333 | 3353,483333 | 0 |
| busca-generica | 3153,983333 | 3153,983333 | 0 |
| retargeting | 1992,066667 | 1992,066667 | 0 |
| busca-marca | 1904,233333 | 1904,233333 | 0 |

**É a mesma alocação.** A maior diferença absoluta é 9,09e-13 conversões em 17.419, e 2,8e-17 em
participação — ponto flutuante, não discordância. A razão é estrutural, não numérica: no jogo de
cobertura o valor de uma jornada é indivisível e só aparece quando todos os seus canais estão
presentes, então cada um dos seus *k* canais tem a mesma contribuição marginal no mesmo número de
ordenações, e o valor de Shapley daquela jornada é 1/*k* para cada. Somado sobre as jornadas, isso é
exatamente a atribuição linear.

Duas consequências que vale dizer sem rodeios. A ordem dos toques não entra no jogo de cobertura em
momento nenhum — ou seja, um modelo vendido como "entende a jornada do cliente" é comprovadamente
indiferente a ela. E um fornecedor que cobra pelo modelo algorítmico, neste jogo, está cobrando por
uma divisão pelo número de canais. Qualquer diferença *real* que o modelo data-driven de uma
plataforma mostre contra a atribuição linear vem de outra definição de jogo — e é justamente isso
que se deve pedir a ele — não do valor de Shapley.

## Resultado 3: 10,18% das conversões não são de ninguém

| | Conversões |
| --- | --- |
| No período | 19.393 |
| Com ao menos um toque | 17.419 |
| **Sem nenhum toque** | **1.974 (10,18%)** |

Toda participação das tabelas acima divide as 17.419. As 1.974 são usuários que converteram sem
nenhum contato de marketing — neste gerador, usuários de alta intenção que os canais não alcançaram.
Um relatório que apresenta participações de canal somando cem por cento do negócio entregou em
silêncio essas 1.974 conversões aos canais **na proporção do crédito que eles já tinham**, o que
significa que o canal que mais se supercredita é também o que mais absorve do que nunca tocou.

Esse erro esteve primeiro no código deste próprio módulo: `returns` originalmente multiplicava a
*participação* de cada canal pelo total de conversões. A correção é ler a coluna absoluta `credited`
do modelo, e a API não recebe mais um total para reescalar.

## Resultado 4: o holdout, que sabe dizer não

40 regiões, 26 semanas, um painel por canal, o canal desligado em metade das regiões depois da
semana 13. Cada região contribui com um número — quanto sua taxa de conversão mudou — e o lift é a
mudança média das regiões tratadas menos a das regiões em holdout, comparada pelo teste de Welch
sobre essas 40 observações regionais. Um painel de 40 regiões por 26 semanas não são 1.040
observações independentes de uma mudança.

| Canal | Lift (pontos de taxa) | Intervalo 95% | p | Significante | Lift real | Intervalo cobre a verdade |
| --- | --- | --- | --- | --- | --- | --- |
| social-pago | +0,028490 | +0,026890 a +0,030091 | 0,0000 | sim | 0,0270 | sim |
| busca-generica | +0,006133 | +0,004620 a +0,007645 | 0,0000 | sim | 0,0075 | sim |
| email | +0,002898 | +0,000650 a +0,005146 | 0,0131 | sim | 0,0032 | sim |
| retargeting | +0,000629 | −0,001090 a +0,002348 | 0,4633 | não | 0,0000 | sim |
| busca-marca | −0,000723 | −0,002461 a +0,001015 | 0,4044 | não | 0,0000 | sim |

**Cinco intervalos de cinco contêm a verdade, e os dois canais sem efeito são exatamente os dois
que o teste se recusa a separar de zero.** O estimador não é mais inteligente que a atribuição; ele
está apontado para a quantidade certa. Repare no que "não significante" compra aqui: a estimativa
pontual da busca de marca é *negativa*, e a leitura honesta não é "a busca de marca prejudica", mas
"este teste não consegue dizer, e seu intervalo tem ±0,0017 pontos de taxa de largura".

## Resultado 5: o ranking se inverte

Crédito de last-click precificado a 180,00 por conversão, contra as conversões incrementais dos
mesmos canais no holdout, sobre 200.000 usuários:

| Canal | Investimento | Creditadas | ROAS | Incrementais | iROAS | Estabelecido | ROAS ÷ iROAS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| email | 20.000 | 2.796 | **25,16** | 579,6 | 5,2165 | sim | 4,82 |
| retargeting | 60.000 | 3.144 | **9,43** | 125,8 | 0,3773 | **não** | — |
| busca-marca | 90.000 | 4.025 | **8,05** | −144,6 | −0,2892 | **não** | — |
| busca-generica | 120.000 | 3.854 | 5,78 | 1.226,5 | 1,8398 | sim | 3,14 |
| social-pago | 180.000 | 3.600 | **3,60** | 5.698,1 | **5,6981** | sim | **0,63** |

Lido de cima para baixo, esse é o ranking do relatório. Três coisas nele estão erradas de três
maneiras diferentes.

**Os dois canais em segundo e terceiro não têm retorno estabelecido.** 150.000 de 470.000 —
**31,9% do orçamento** — está onde o holdout não consegue distinguir o efeito de nada. E isso não é
a mesma afirmação que "desperdiçado": um teste que não rejeita não é prova de zero. É a afirmação
mais fraca e mais útil de que, depois de rodar um holdout de 13 semanas em 20 regiões, a conta
continua sem evidência para um terço do que investe.

**A razão é deliberadamente `nan` onde nada foi estabelecido.** O iROAS de −0,2892 da busca de marca
se leria como um achado, e não é: é uma estimativa pontual cujo intervalo cobre zero, dividida por
um investimento. Publicar uma razão contra um denominador não medido é como um não-resultado vira
slide, então `returns` devolve `nan` e uma coluna `established` no lugar.

**E o erro corre também na outra direção, que é a parte que passa batido.** O social-pago é o
*pior* canal por ROAS, com 3,60, e o melhor por iROAS, com 5,70 — uma razão de **0,63**. É o único
canal que cria demanda em vez de colhê-la, então as conversões que ele inicia são fechadas semanas
depois por alguém mais próximo da venda. Uma conta otimizada por ROAS não apenas investe demais em
busca de marca; ela desfinancia o canal que enche o funil, e depois assiste ao volume da busca de
marca cair por razões que o painel não explica.

Agregado, a conta reporta **ROAS 6,6711 contra iROAS 2,8667** — mesmo investimento, mesmo período,
2,3 vezes de distância.

## Premissas e limitações

- **Todo número aqui vem de um gerador sintético com semente**, inclusive a coluna de intenção que
  torna a comparação possível. Nenhum dado de anunciante, agência ou plataforma é usado em lugar
  algum. Ver [`DISCLAIMER.md`](../../../DISCLAIMER.md). Os nomes de canal são rótulos inventados em
  português para funções genéricas, não a estrutura de nenhuma conta real.
- **O mecanismo de seleção do gerador é o resultado inteiro.** A exposição é sorteada como função
  linear da intenção, e a conversão como taxa-base mais intenção mais os efeitos reais dos canais
  que alcançaram o usuário. Contas reais são selecionadas por mais de uma variável latente, com
  retroalimentação da campanha para a segmentação, e as duas coisas alargariam as distâncias acima
  em vez de fechá-las.
- **A identidade de Shapley é uma propriedade do jogo de cobertura**, não de todo modelo
  data-driven concebível. Um jogo cuja função de valor reparta jornadas parciais, ou pese a ordem,
  dá outra resposta. O que se prova aqui é que o jogo de cobertura — a formulação padrão — é a
  atribuição linear.
- **O holdout estima um efeito de taxa para um período, não uma curva de demanda.** Ele diz o que
  desligar o canal fez neste nível de investimento, nestas regiões, em 13 semanas. Não dá o retorno
  marginal da próxima unidade investida, que é outro experimento.
- **`incremental_conversions(reach)` recebe a população como argumento de propósito.** Escalar uma
  taxa para conversões exige um fato de negócio, e inferi-lo em silêncio é como um resultado de geo
  se transforma num número que ninguém reproduz.
- **Testes geográficos carregam interferência e um custo real.** As regiões são tratadas como
  independentes aqui; na prática as pessoas circulam entre elas e as plataformas otimizam através
  delas. E o teste não é grátis: metade das regiões perde o canal por 13 semanas, que é o
  trade-off que a próxima onda dimensiona.
- **Não significante não é zero.** Dois canais aqui são verdadeiramente zero e o teste diz "não
  consigo dizer". São afirmações diferentes, e o `verdict()` do módulo é redigido para mantê-las
  separadas.
- **E "não testado" é uma terceira afirmação.** Um holdout com uma região de um lado dá uma
  diferença e nenhuma dispersão, então o `geo_lift` devolve o lift com `untested_because` preenchido
  em vez de um erro-padrão `nan` que, adiante, se lê como "não significante". Esse foi um defeito
  aqui: um desenho de duas regiões — que gente de fato roda — chegava com a aparência exata de um
  canal que havia sido medido e não fazia nada. Os graus de liberdade de Welch são calculados em
  forma fechada pela mesma razão, para que um painel-controle sem ruído devolva um número em vez de
  um aviso.

## Fontes

- Shapley, L. S. (1953). *A Value for n-Person Games.* Contributions to the Theory of Games II.
- Dalessandro, B., Perlich, C., Stitelman, O., Provost, F. (2012). *Causally Motivated Attribution
  for Online Advertising.* ADKDD.
- Lewis, R. A., Rao, J. M. (2015). *The Unfavorable Economics of Measuring the Returns to
  Advertising.* Quarterly Journal of Economics 130(4).
- Blake, T., Nosko, C., Tadelis, S. (2015). *Consumer Heterogeneity and Paid Search Effectiveness:
  A Large-Scale Field Experiment.* Econometrica 83(1). — o holdout de busca de marca no qual o canal
  busca-marca deste módulo é modelado.
- Gordon, B. R., Zettelmeyer, F., Bhargava, N., Chapsky, D. (2019). *A Comparison of Approaches to
  Advertising Measurement.* Marketing Science 38(2).
- Vaver, J., Koehler, J. (2011). *Measuring Ad Effectiveness Using Geo Experiments.* Google
  Research.
