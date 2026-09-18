# `mktlab.design` — what the test can find, decided before anybody pays for it

*[Português](#mktlabdesign--o-que-o-teste-consegue-achar-decidido-antes-de-alguém-pagar-por-ele)*

## The business problem

Wave 1 ran a geo holdout on five channels and came back with "no incremental return established"
for two of them. That sentence has two completely different meanings and the output does not say
which: **the channel does nothing**, or **the test was too small to see what it does**. A budget
that cuts on the first reading and a budget that cuts on the second are making different decisions,
one of them informed.

Here the answer happens to be the first — the two channels really do have a true effect of zero —
but nothing in the holdout's output establishes that, and in a real account nothing ever would. What
*is* available, in both cases and before a single region is switched off, is the size of the effect
the test would have been able to see.

## The decision it enables

1. **Is this test worth running at all?** Which is answered by comparing the smallest return it
   could establish against the return the business would act on. If the first is above the second,
   thirteen weeks buys nothing.
2. **How big does it have to be?** Regions, weeks, and which of the two is cheaper.
3. **What does the test cost if the channel works?** Because that is the case where a holdout is
   expensive, and it is the case nobody prices.
4. **And for the test that already ran: what did the null result rule out?** An interval has a top.

## Usage

```python
from mktlab.design import GeoDesign, holdout_cost, regions_for, retrospective
from mktlab.synth import AUDIENCE, CHANNELS, GEO, mean_rate

design = GeoDesign(
    geos=GEO.geos,
    weeks=GEO.weeks,
    split=GEO.split,
    users_per_geo_week=GEO.users_per_geo_week,
    base_rate=mean_rate(AUDIENCE, CHANNELS),
)

design.standard_error()  # 0.000823, before any data exists
design.power(0.0)  # 0.05 - the significance level, exactly
design.detectable_lift()  # 0.002361 rate points at 80% power
design.detectable_iroas(spend=20_000, reach=200_000, value_per_conversion=180)  # 4.2498
design.return_precision(spend=20_000, reach=200_000, value_per_conversion=180)  # 3.0007

regions_for(0.0032, design)  # 24 - the design used 40
holdout_cost(design, lift=0.0270, value_per_conversion=180)["forgone_share"]  # 0.2764
```

## Result 1: the precision of a geo test is known before it runs

A region contributes one number to a difference in differences: how much its conversion rate changed.
Both things that make regions differ from each other drop out of that. A permanent level difference
cancels because it is in both phases; a trend common to the regions cancels because it is in both
arms. What is left is the sampling noise of two phase means on a known number of users, which is a
binomial variance.

So the standard error closes analytically. Against the five panels wave 1 actually ran:

| Channel | True lift | Predicted SE | Observed SE | Ratio | Power at the truth | Resolved |
| --- | --- | --- | --- | --- | --- | --- |
| social-pago | 0.0270 | 0.000797 | 0.000834 | 1.0461 | 1.0000 | yes |
| email | 0.0032 | 0.000820 | 0.000870 | 1.0608 | 0.9671 | yes |
| busca-generica | 0.0075 | 0.000816 | 0.000865 | 1.0590 | 1.0000 | yes |
| retargeting | 0.0000 | 0.000823 | 0.000689 | **0.8366** | 0.0500 | no |
| busca-marca | 0.0000 | 0.000823 | 0.000968 | **1.1754** | 0.0500 | no |

A standard error estimated from forty regions is itself noisy by about 11.5%, so every ratio here is
within a standard deviation and a half of the prediction — the two extremes, 0.84 and 1.18, are the
sampling noise of a variance estimate rather than a failure of the algebra. **The precision of a geo
test is a design decision, not something discovered afterwards.**

The control case matters more than the table: `design.power(0.0)` returns **0.05000000**, the
significance level, exactly. A power function that does not return alpha when nothing is happening
is not measuring power.

## Result 2: the design resolved three channels and was sized for none of them

Minimum detectable lift at 80% power: **0.002361** rate points. At 50% power 0.001653, at 95%
0.003036.

| Channel | True lift | Power at that lift | Regions actually needed | Regions used |
| --- | --- | --- | --- | --- |
| social-pago | 0.0270 | 1.0000 | **4** | 40 |
| busca-generica | 0.0075 | 1.0000 | **8** | 40 |
| email | 0.0032 | 0.9671 | **24** | 40 |
| retargeting | 0.0000 | 0.0500 | — nothing to detect | 40 |
| busca-marca | 0.0000 | 0.0500 | — nothing to detect | 40 |

All three real effects were detectable at 96% power or better, and the hardest of them needed
twenty-four regions. Forty were used, which is not a free surplus: every held-out region gives up
conversions for thirteen weeks.

## Result 3: the figure nobody computes is the detectable *return*

The minimum detectable lift is the same 0.0024 for all five channels, because it depends on the
design and not on the channel. A budget does not decide on rate points. Dividing by the channel's
spend gives the smallest **return** the test could establish, and that is not the same for anybody:

| Channel | Spend | Detectable lift | Detectable iROAS | Interval half-width | True iROAS |
| --- | --- | --- | --- | --- | --- |
| social-pago | 180,000 | 0.0024 | **0.4722** | 0.3334 | 5.40 |
| busca-generica | 120,000 | 0.0024 | 0.7083 | 0.5001 | 2.25 |
| busca-marca | 90,000 | 0.0024 | 0.9444 | 0.6668 | 0.00 |
| retargeting | 60,000 | 0.0024 | 1.4166 | 1.0002 | 0.00 |
| email | 20,000 | 0.0024 | **4.2498** | **3.0007** | 5.76 |

**The same test, run the same way in the same weeks, is a precision instrument on the largest
channel and nearly blind on the smallest.** On social-pago it resolves returns down to 0.47. On
email it can establish nothing below 4.25, and the interval it produces is 3.00 wide either side —
so email's true return of 5.76 comes back as *somewhere between 2.8 and 8.8*. The test can confirm
that email is good. It can never say how good, which is the question the budget was asking.

Nobody notices this because the statistical figure — the detectable lift — is identical across the
five rows. The decision-relevant figure differs by a factor of nine.

## Result 4: what the two null results actually established

| Channel | iROAS | Interval | Rules out returns above | Design's detectable floor | Design big enough? |
| --- | --- | --- | --- | --- | --- |
| retargeting | 0.2377 | −0.5991 to 1.0745 | **1.0745** | 1.4166 | **no** |
| busca-marca | 0.5369 | −0.2543 to 1.3282 | **1.3282** | 0.9444 | **yes** |

**"Not significant" is not the end of the sentence.** The retargeting holdout rules out any return
above 1.07 — that is a fact about the channel, it cost thirteen weeks, and a report that quotes the
p-value alone throws it away.

But the two channels differ in a way no p-value shows, and it is in the last two columns.
**busca-marca's null is informative**: the design could establish returns down to 0.94, and the test
came back ruling out everything above 1.33, so the range the answer sits in is a range this test
could resolve. **retargeting's null is not**: the test ruled out returns above 1.07 while the design
could not have established any return below 1.42. There was no return this test could both miss and
detect — the bound it produced is the only thing it was ever going to produce.

Those two numbers are always of the same size, which is why the comparison is so close: the
interval's ceiling is the estimate plus *t* times the standard error, and the detectable floor is
*t* plus the power quantile times the same standard error. **A null holdout on a small channel buys
an upper bound and little else** — so if the upper bound is not itself the decision, the test was
the wrong instrument before it started.

## Result 5: the holdout is expensive exactly when the answer is "keep spending"

Twenty regions lose the channel for thirteen weeks: **260 region-weeks, 520,000 user-weeks**.

| Channel | True lift | Conversions given up | Share of those regions' conversions |
| --- | --- | --- | --- |
| social-pago | 0.0270 | **14,040** | **27.64%** |
| busca-generica | 0.0075 | 3,900 | 7.68% |
| email | 0.0032 | 1,664 | 3.28% |
| retargeting | 0.0000 | 0 | 0.00% |
| busca-marca | 0.0000 | 0 | 0.00% |

The asymmetry is the finding. **A holdout costs nothing on the channels that do nothing, and costs
the most on the channel it is most important to keep.** The share column is `lift / base_rate`
exactly, so it carries no population in it and survives being quoted somewhere else — unlike the
conversion count, which belongs to the panel's population and not to the audience the return figures
are scaled against.

## Result 6: half of the design is free, and it is the half nobody extends

The cost is paid entirely in the weeks *after* the switch. The weeks *before* it hold nothing out —
and they enter the standard error in exactly the same way. Forty regions, thirteen weeks after the
switch in every row:

| Weeks before | Standard error | Detectable iROAS (email) | Half-width | Region-weeks held out | Conversions given up |
| --- | --- | --- | --- | --- | --- |
| 4 | 0.001200 | 6.2004 | 4.3742 | 260 | 1,664 |
| 8 | 0.000943 | 4.8705 | 3.4377 | 260 | 1,664 |
| **13** | **0.000823** | **4.2498** | **3.0007** | **260** | **1,664** |
| 26 | 0.000713 | 3.6789 | 2.5987 | 260 | 1,664 |
| 52 | 0.000651 | 3.3574 | 2.3722 | 260 | 1,664 |

Every row costs the same. Extending the history from thirteen weeks to fifty-two takes the
detectable return from 4.25 to 3.36 and the interval half-width from 3.00 to 2.37, **for nothing.**

And there is an exact limit to it, which is the cleanest statement in the module. An infinitely long
pre-period reaches a standard error of **0.000582** — which is exactly what **eighty** regions over
the same twenty-six weeks give. Equal, not close: both halve the same variance, because with equal
phases the before term and the after term are the same size. So **a long enough history is worth
precisely as much as doubling the size of the test, and only one of the two is free.** Most accounts
already have the history and run the short pre-period anyway.

## Assumptions and limitations

- **Every number here comes from a seeded synthetic generator**, including the true lifts the
  predictions are checked against. No advertiser, agency, platform or client data is used anywhere.
  See [`DISCLAIMER.md`](../../../DISCLAIMER.md).
- **The variance model is binomial noise around a common rate.** That is the generator's own
  structure, which makes this a check that the algebra is right rather than a claim about real
  panels. Real regions carry autocorrelation week to week, seasonality that is not common across
  them, and variance that grows with the level; each would widen the predicted standard error. The
  closed form is therefore a **floor** on the noise, and a design sized from it is optimistic.
  Estimating the spread from the account's own pre-period, and comparing it against this floor, is
  what a real sizing would do — and the gap between them is itself the interesting number.
- **A permanent between-region difference cancels; a *changing* one does not.** The cancellation is
  exact only for level differences and trends common to the arms. A region-specific change in trend
  after the split — a competitor entering one market, a promotion in another — survives the
  difference in differences and is not in this variance.
- **The base rate has to be supplied, and the answer depends on it.** It is the input people leave
  out of a sizing, and the binomial variance cannot be computed without it.
- **`reach` is an argument, never inferred.** The geo panel and the audience are two different
  populations: the panel's size is regions times weeks times users per region-week, while the reach
  that turns a rate into a return is the population the channel runs against. Mixing a cost figure
  from one with a return figure from the other is the same class of error as everything else this
  repository is about, so `holdout_cost` also reports the population-free share.
- **Power comes from the noncentral t, not from a normal approximation**, which would understate
  every design in this document. The detectable lift is nudged up until the achieved power is at or
  above the target, the way a sample size is rounded up: the first version returned a lift whose
  power was 0.799992 and printed it under a heading that said 80%.
- **80% power is a convention**, exposed as `DEFAULT_POWER` rather than built in, so a design
  reporting it is reporting a choice.
- **Nothing here covers peeking.** Every figure assumes the test is read once, at the end. Reading
  it weekly spends the error rate several times over, and that is a wave of its own.
- **Interference between regions is ignored**, as it is in wave 1: people move between markets and
  platforms optimise across them, which contaminates the holdout in the direction of finding no
  effect.

## Sources

- Vaver, J., Koehler, J. (2011). *Measuring Ad Effectiveness Using Geo Experiments.* Google
  Research.
- Vaver, J., Koehler, J. (2012). *Periodic Measurement of Advertising Effectiveness Using
  Multiple-Test-Period Geo Experiments.* Google Research.
- Kerman, J., Wang, P., Vaver, J. (2017). *Estimating Ad Effectiveness Using Geo Experiments in a
  Time-Based Regression Framework.* Google Research.
- Lewis, R. A., Rao, J. M. (2015). *The Unfavorable Economics of Measuring the Returns to
  Advertising.* Quarterly Journal of Economics 130(4). — the paper this module is an implementation
  of the central complaint of: the sample sizes needed to measure advertising returns are far larger
  than the ones people run.
- Gelman, A., Carlin, J. (2014). *Beyond Power Calculations: Assessing Type S and Type M Errors.*
  Perspectives on Psychological Science 9(6).

---

# `mktlab.design` — o que o teste consegue achar, decidido antes de alguém pagar por ele

*[English](#mktlabdesign--what-the-test-can-find-decided-before-anybody-pays-for-it)*

## O problema de negócio

A onda 1 rodou um holdout geográfico em cinco canais e voltou com "nenhum retorno incremental
estabelecido" para dois deles. Essa frase tem dois significados completamente diferentes e a saída
não diz qual: **o canal não faz nada**, ou **o teste era pequeno demais para ver o que ele faz**. Um
orçamento que corta pela primeira leitura e um orçamento que corta pela segunda estão tomando
decisões diferentes — e só uma delas é informada.

Aqui a resposta é a primeira — os dois canais realmente têm efeito verdadeiro zero — mas nada na
saída do holdout estabelece isso, e numa conta real nada estabeleceria. O que **está** disponível,
nos dois casos e antes de desligar uma única região, é o tamanho do efeito que o teste seria capaz
de enxergar.

## A decisão que habilita

1. **Vale a pena rodar este teste?** Responde-se comparando o menor retorno que ele consegue
   estabelecer com o retorno sobre o qual o negócio agiria. Se o primeiro está acima do segundo,
   treze semanas não compram nada.
2. **Qual tamanho ele precisa ter?** Regiões, semanas, e qual das duas é mais barata.
3. **Quanto o teste custa se o canal funcionar?** Porque é nesse caso que um holdout é caro, e é
   esse caso que ninguém precifica.
4. **E para o teste que já rodou: o que o resultado nulo descartou?** Um intervalo tem um teto.

## Uso

```python
from mktlab.design import GeoDesign, holdout_cost, regions_for, retrospective
from mktlab.synth import AUDIENCE, CHANNELS, GEO, mean_rate

design = GeoDesign(
    geos=GEO.geos,
    weeks=GEO.weeks,
    split=GEO.split,
    users_per_geo_week=GEO.users_per_geo_week,
    base_rate=mean_rate(AUDIENCE, CHANNELS),
)

design.standard_error()  # 0,000823, antes de existir qualquer dado
design.power(0.0)  # 0,05 - o nível de significância, exatamente
design.detectable_lift()  # 0,002361 pontos de taxa a 80% de poder
design.detectable_iroas(spend=20_000, reach=200_000, value_per_conversion=180)  # 4,2498
design.return_precision(spend=20_000, reach=200_000, value_per_conversion=180)  # 3,0007

regions_for(0.0032, design)  # 24 - o desenho usou 40
holdout_cost(design, lift=0.0270, value_per_conversion=180)["forgone_share"]  # 0,2764
```

## Resultado 1: a precisão de um teste geográfico é conhecida antes de ele rodar

Uma região contribui com um número para uma diferença em diferenças: quanto sua taxa de conversão
mudou. As duas coisas que fazem as regiões diferirem entre si saem dessa conta. Uma diferença
permanente de nível cancela porque está nas duas fases; uma tendência comum às regiões cancela
porque está nos dois braços. Sobra o ruído amostral de duas médias de fase sobre um número conhecido
de usuários — uma variância binomial.

Então o erro-padrão fecha analiticamente. Contra os cinco painéis que a onda 1 de fato rodou:

| Canal | Lift real | EP previsto | EP observado | Razão | Poder na verdade | Resolvido |
| --- | --- | --- | --- | --- | --- | --- |
| social-pago | 0,0270 | 0,000797 | 0,000834 | 1,0461 | 1,0000 | sim |
| email | 0,0032 | 0,000820 | 0,000870 | 1,0608 | 0,9671 | sim |
| busca-generica | 0,0075 | 0,000816 | 0,000865 | 1,0590 | 1,0000 | sim |
| retargeting | 0,0000 | 0,000823 | 0,000689 | **0,8366** | 0,0500 | não |
| busca-marca | 0,0000 | 0,000823 | 0,000968 | **1,1754** | 0,0500 | não |

Um erro-padrão estimado a partir de quarenta regiões é ele mesmo ruidoso em cerca de 11,5%, então
toda razão aqui está dentro de um desvio e meio da previsão — os dois extremos, 0,84 e 1,18, são o
ruído amostral de uma estimativa de variância, não uma falha da álgebra. **A precisão de um teste
geográfico é uma decisão de desenho, não algo descoberto depois.**

O caso de controle importa mais que a tabela: `design.power(0.0)` devolve **0,05000000**, o nível de
significância, exatamente. Uma função de poder que não devolve alfa quando nada está acontecendo não
está medindo poder.

## Resultado 2: o desenho resolveu três canais e não foi dimensionado para nenhum

Lift mínimo detectável a 80% de poder: **0,002361** pontos de taxa. A 50% de poder, 0,001653; a 95%,
0,003036.

| Canal | Lift real | Poder nesse lift | Regiões de fato necessárias | Regiões usadas |
| --- | --- | --- | --- | --- |
| social-pago | 0,0270 | 1,0000 | **4** | 40 |
| busca-generica | 0,0075 | 1,0000 | **8** | 40 |
| email | 0,0032 | 0,9671 | **24** | 40 |
| retargeting | 0,0000 | 0,0500 | — nada a detectar | 40 |
| busca-marca | 0,0000 | 0,0500 | — nada a detectar | 40 |

Os três efeitos reais eram detectáveis com 96% de poder ou mais, e o mais difícil deles precisava de
vinte e quatro regiões. Foram usadas quarenta, e esse excedente não é grátis: cada região em holdout
abre mão de conversões por treze semanas.

## Resultado 3: a cifra que ninguém calcula é o *retorno* detectável

O lift mínimo detectável é o mesmo 0,0024 para os cinco canais, porque depende do desenho e não do
canal. Um orçamento não decide em pontos de taxa. Dividir pelo investimento do canal dá o menor
**retorno** que o teste conseguiria estabelecer — e esse não é igual para ninguém:

| Canal | Investimento | Lift detectável | iROAS detectável | Semi-amplitude do intervalo | iROAS real |
| --- | --- | --- | --- | --- | --- |
| social-pago | 180.000 | 0,0024 | **0,4722** | 0,3334 | 5,40 |
| busca-generica | 120.000 | 0,0024 | 0,7083 | 0,5001 | 2,25 |
| busca-marca | 90.000 | 0,0024 | 0,9444 | 0,6668 | 0,00 |
| retargeting | 60.000 | 0,0024 | 1,4166 | 1,0002 | 0,00 |
| email | 20.000 | 0,0024 | **4,2498** | **3,0007** | 5,76 |

**O mesmo teste, rodado da mesma forma nas mesmas semanas, é um instrumento de precisão no maior
canal e quase cego no menor.** No social-pago resolve retornos até 0,47. No email não consegue
estabelecer nada abaixo de 4,25, e o intervalo que produz tem 3,00 de cada lado — então o retorno
real do email, 5,76, volta como *algo entre 2,8 e 8,8*. O teste consegue confirmar que o email é
bom. Nunca consegue dizer quão bom, que era a pergunta do orçamento.

Ninguém percebe isso porque a cifra estatística — o lift detectável — é idêntica nas cinco linhas. A
cifra relevante para a decisão difere por um fator de nove.

## Resultado 4: o que os dois resultados nulos de fato estabeleceram

| Canal | iROAS | Intervalo | Descarta retornos acima de | Piso detectável do desenho | Desenho suficiente? |
| --- | --- | --- | --- | --- | --- |
| retargeting | 0,2377 | −0,5991 a 1,0745 | **1,0745** | 1,4166 | **não** |
| busca-marca | 0,5369 | −0,2543 a 1,3282 | **1,3282** | 0,9444 | **sim** |

**"Não significante" não é o fim da frase.** O holdout de retargeting descarta qualquer retorno acima
de 1,07 — isso é um fato sobre o canal, custou treze semanas, e um relatório que cita só o p-valor
joga fora esse fato.

Mas os dois canais diferem de um jeito que nenhum p-valor mostra, e está nas duas últimas colunas.
**O nulo da busca de marca é informativo**: o desenho conseguia estabelecer retornos até 0,94, e o
teste voltou descartando tudo acima de 1,33 — ou seja, a faixa onde a resposta está é uma faixa que
este teste conseguia resolver. **O nulo do retargeting não é**: o teste descartou retornos acima de
1,07 enquanto o desenho não conseguiria estabelecer nenhum retorno abaixo de 1,42. Não havia retorno
que este teste pudesse ao mesmo tempo perder e detectar — o limite que ele produziu era a única coisa
que ele iria produzir.

Esses dois números têm sempre o mesmo tamanho, e é por isso que a comparação fica tão próxima: o teto
do intervalo é a estimativa mais *t* vezes o erro-padrão, e o piso detectável é *t* mais o quantil de
poder vezes o mesmo erro-padrão. **Um holdout nulo num canal pequeno compra um limite superior e
pouco mais** — então, se o limite superior não é em si a decisão, o teste era o instrumento errado
antes de começar.

## Resultado 5: o holdout é caro exatamente quando a resposta é "continue investindo"

Vinte regiões perdem o canal por treze semanas: **260 região-semanas, 520.000 usuário-semanas**.

| Canal | Lift real | Conversões abdicadas | Fração das conversões daquelas regiões |
| --- | --- | --- | --- |
| social-pago | 0,0270 | **14.040** | **27,64%** |
| busca-generica | 0,0075 | 3.900 | 7,68% |
| email | 0,0032 | 1.664 | 3,28% |
| retargeting | 0,0000 | 0 | 0,00% |
| busca-marca | 0,0000 | 0 | 0,00% |

A assimetria é o achado. **Um holdout não custa nada nos canais que não fazem nada, e custa o máximo
no canal que é mais importante manter.** A coluna de fração é `lift / taxa-base` exatamente, então
não carrega população alguma e sobrevive a ser citada em outro lugar — diferente da contagem de
conversões, que pertence à população do painel e não à audiência contra a qual as cifras de retorno
são escaladas.

## Resultado 6: metade do desenho é grátis, e é a metade que ninguém estende

O custo é pago inteiramente nas semanas *depois* do corte. As semanas *antes* dele não colocam
ninguém em holdout — e entram no erro-padrão exatamente da mesma forma. Quarenta regiões, treze
semanas depois do corte em todas as linhas:

| Semanas antes | Erro-padrão | iROAS detectável (email) | Semi-amplitude | Região-semanas em holdout | Conversões abdicadas |
| --- | --- | --- | --- | --- | --- |
| 4 | 0,001200 | 6,2004 | 4,3742 | 260 | 1.664 |
| 8 | 0,000943 | 4,8705 | 3,4377 | 260 | 1.664 |
| **13** | **0,000823** | **4,2498** | **3,0007** | **260** | **1.664** |
| 26 | 0,000713 | 3,6789 | 2,5987 | 260 | 1.664 |
| 52 | 0,000651 | 3,3574 | 2,3722 | 260 | 1.664 |

Todas as linhas custam o mesmo. Estender o histórico de treze para cinquenta e duas semanas leva o
retorno detectável de 4,25 para 3,36 e a semi-amplitude de 3,00 para 2,37, **de graça.**

E há um limite exato para isso, que é a afirmação mais limpa do módulo. Um pré-período
infinitamente longo chega a um erro-padrão de **0,000582** — exatamente o que **oitenta** regiões nas
mesmas vinte e seis semanas dão. Igual, não próximo: as duas coisas cortam a mesma variância pela
metade, porque com fases iguais o termo de antes e o de depois têm o mesmo tamanho. Portanto **um
histórico suficientemente longo vale precisamente o mesmo que dobrar o tamanho do teste, e só um dos
dois é grátis.** A maioria das contas já tem o histórico e roda o pré-período curto do mesmo jeito.

## Premissas e limitações

- **Todo número aqui vem de um gerador sintético com semente**, inclusive os lifts verdadeiros
  contra os quais as previsões são conferidas. Nenhum dado de anunciante, agência, plataforma ou
  cliente é usado em lugar algum. Ver [`DISCLAIMER.md`](../../../DISCLAIMER.md).
- **O modelo de variância é ruído binomial em torno de uma taxa comum.** Essa é a própria estrutura
  do gerador, o que torna isto uma verificação de que a álgebra está certa, e não uma afirmação sobre
  painéis reais. Regiões reais carregam autocorrelação semana a semana, sazonalidade que não é comum
  a todas, e variância que cresce com o nível; cada uma alargaria o erro-padrão previsto. A forma
  fechada é portanto um **piso** do ruído, e um desenho dimensionado por ela é otimista. Estimar a
  dispersão do próprio pré-período da conta e compará-la com esse piso é o que um dimensionamento
  real faria — e a distância entre os dois é, ela mesma, o número interessante.
- **Uma diferença permanente entre regiões cancela; uma diferença que *muda* não.** O cancelamento é
  exato apenas para diferenças de nível e tendências comuns aos braços. Uma mudança de tendência
  específica de uma região depois do corte — um concorrente entrando num mercado, uma promoção em
  outro — sobrevive à diferença em diferenças e não está nesta variância.
- **A taxa-base precisa ser informada, e a resposta depende dela.** É o insumo que as pessoas deixam
  de fora de um dimensionamento, e a variância binomial não pode ser calculada sem ele.
- **`reach` é argumento, nunca inferido.** O painel geográfico e a audiência são duas populações
  diferentes: o tamanho do painel é regiões vezes semanas vezes usuários por região-semana, enquanto
  o alcance que transforma uma taxa em retorno é a população contra a qual o canal roda. Misturar uma
  cifra de custo de uma com uma cifra de retorno da outra é a mesma classe de erro que todo o resto
  deste repositório denuncia, então o `holdout_cost` também reporta a fração livre de população.
- **O poder vem da t não-central, não de uma aproximação normal**, que subestimaria todo desenho
  deste documento. O lift detectável é empurrado para cima até que o poder alcançado esteja no alvo
  ou acima dele, do mesmo jeito que um tamanho de amostra é arredondado para cima: a primeira versão
  devolvia um lift cujo poder era 0,799992 e o imprimia sob um título que dizia 80%.
- **80% de poder é uma convenção**, exposta como `DEFAULT_POWER` em vez de embutida, para que um
  desenho que reporte isso esteja reportando uma escolha.
- **Nada aqui trata de espiar o teste em andamento.** Toda cifra assume que o teste é lido uma vez,
  no fim. Lê-lo semanalmente gasta a taxa de erro várias vezes, e isso é uma onda à parte.
- **Interferência entre regiões é ignorada**, como na onda 1: pessoas circulam entre mercados e as
  plataformas otimizam através deles, o que contamina o holdout na direção de não achar efeito.

## Fontes

- Vaver, J., Koehler, J. (2011). *Measuring Ad Effectiveness Using Geo Experiments.* Google
  Research.
- Vaver, J., Koehler, J. (2012). *Periodic Measurement of Advertising Effectiveness Using
  Multiple-Test-Period Geo Experiments.* Google Research.
- Kerman, J., Wang, P., Vaver, J. (2017). *Estimating Ad Effectiveness Using Geo Experiments in a
  Time-Based Regression Framework.* Google Research.
- Lewis, R. A., Rao, J. M. (2015). *The Unfavorable Economics of Measuring the Returns to
  Advertising.* Quarterly Journal of Economics 130(4). — o artigo cuja queixa central este módulo
  implementa: os tamanhos de amostra necessários para medir retorno de publicidade são muito maiores
  do que os que as pessoas rodam.
- Gelman, A., Carlin, J. (2014). *Beyond Power Calculations: Assessing Type S and Type M Errors.*
  Perspectives on Psychological Science 9(6).
