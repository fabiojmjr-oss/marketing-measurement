# `mktlab.design.sequential` — the test that is read every Monday

*[Português](#mktlabdesignsequential--o-teste-que-é-lido-toda-segunda-feira)*

## The business problem

Wave 2 sized a geo holdout carefully and rested the whole calculation on an assumption it never
wrote down: that the test is read **once**, at the end of thirteen weeks. Nobody does that. The test
sits on a dashboard that refreshes weekly, somebody looks at it every Monday, and it is declared the
first time it clears the line.

Reading a fixed 1.96 boundary thirteen times takes the false-positive rate from 5% to **21.4%**. A
channel that does absolutely nothing is declared a winner about **one time in five**. Every
individual look is arithmetically correct. What is wrong is that the decision rule in force is not
the one the 1.96 was computed for — and the person taking the decision usually does not know that a
decision rule exists.

## The decision it enables

1. **What is the error rate of the test we are actually running**, as opposed to the one we designed?
2. **What does it cost to be allowed to look?** Because it is a real cost and it is smaller than
   people fear — for one of the two standard answers.
3. **And by how much is the number we report inflated?** Which is the part a correct boundary does
   not fix, and nobody mentions.

## Usage

```python
from mktlab.design import exaggeration, inflated_alpha, peeking_table, plan

inflated_alpha(13)  # 0.213814 - thirteen weekly looks at the usual 1.96

peeking_table(13)  # the four rules, priced side by side
plan("obrien-fleming", 13).verdict()
# "obrien-fleming: 13 looks holding alpha at 0.0500, +4.3% information, stops after 9.79 looks..."

exaggeration(plan("naive", 13).boundary, ncp=2.477)["ratio"]  # 1.7308
```

## Result 1: the error rate against the number of glances

Computed with the Armitage-McPherson-Rowe recursion — the density of the running sum carried forward
through the continuation region, look by look. Not simulated, and not a Bonferroni-style bound: the
looks are heavily dependent, because each one contains all the data of the ones before it, and
treating them as independent would give a wildly wrong answer in the other direction.

| Looks | True false-positive rate | Times the nominal 5% |
| --- | --- | --- |
| 1 | 0.050000 | 1.00× |
| 2 | **0.083118** | 1.66× |
| 3 | 0.107256 | 2.15× |
| 5 | 0.141689 | 2.83× |
| 10 | 0.193357 | 3.87× |
| **13** | **0.213814** | **4.28×** |
| 26 | 0.268788 | 5.38× |
| 52 | 0.323512 | 6.47× |

**The curve is steepest at the start.** Looking twice instead of once already costs 66% more error
than the design allows for. The difference between weekly and daily monitoring matters much less
than the difference between once and twice — which inverts the usual intuition that occasional
glances are harmless and only obsessive monitoring is a problem.

## Result 2: two honest boundaries, and they are different trades

| Rule | Looks | First boundary | Last boundary | Nominal α (first / last) | True α | Valid | Information | Stops after |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| read once | 1 | 1.9600 | 1.9600 | 0.0500 / 0.0500 | 0.0500 | yes | 1.0000 | 1.00 looks |
| **naive weekly** | 13 | 1.9600 | 1.9600 | 0.0500 / 0.0500 | **0.2138** | **no** | — | 6.20 looks |
| Pocock | 13 | 2.6019 | 2.6019 | 0.0093 / 0.0093 | 0.0500 | yes | **1.3247** | 7.83 looks |
| O'Brien-Fleming | 13 | **7.5799** | 2.1023 | 3.5e-14 / 0.0355 | 0.0500 | yes | **1.0432** | 9.79 looks |

Read the naive row as the diagnosis and the other two as prescriptions. Both hold the error rate at
exactly 5% across thirteen weekly readings, and they buy different things:

- **Pocock** applies the same higher bar every week — a p-value under **0.0093** at any look. It can
  end the test in week one, and it needs a **32% bigger** test to keep 80% power.
- **O'Brien-Fleming** starts almost closed and opens up: the first week's bar is **7.58 standard
  errors**, and the last week's is 2.10, barely above the fixed-sample 1.96. It costs only **4.3%**
  more information, and it will not stop the test early in the first half however good the numbers
  look.

That first boundary of 7.58 is not a numerical accident and it is the most useful sentence in this
document: **the design is saying that nothing observable in week one should end a thirteen-week
test.** Which is also the honest answer to most requests to call a test early.

## Result 3: the honest version costs about 2% of the holdout

More information means either a worse detectable return at the same size, or more regions to hold the
return where it was. For email — the channel wave 2 showed was already at the edge of what the test
could resolve:

| Rule | True α | Information | Detectable iROAS | Regions for the same floor |
| --- | --- | --- | --- | --- |
| read once | 0.0500 | 1.0000 | 4.2498 | 24 |
| naive weekly | **0.2138** | — | — | — |
| O'Brien-Fleming | 0.0500 | 1.0432 | **4.3406** | **26** |
| Pocock | 0.0500 | 1.3247 | 4.8913 | 32 |

**O'Brien-Fleming costs 2.1% of the detectable return, or two extra regions out of twenty-four.**
That is the entire bill for the right to read the test every week for thirteen weeks without lying
about the error rate. It is not paid, because it has never been written down where the person
designing the test could see it. Pocock's bill is eight regions, and what it buys is the right to
stop in week one — which is worth having when the downside of continuing is real, and not otherwise.

## Result 4: the half a correct boundary does not fix

A test stops early because the data came in favourably. So the estimate at the stopping point is
drawn from the favourable tail, and the effect you report is larger than the effect you measured.
Each rule below is evaluated at the effect that gives **that rule** 80% power, so the comparison is
at equal power rather than at equal design:

| Rule | Power | Reported ÷ true | Stops after | Right direction |
| --- | --- | --- | --- | --- |
| read once | 0.8011 | **1.1250** | 1.00 | 1.0000 |
| O'Brien-Fleming | 0.8006 | 1.2695 | 9.79 | 1.0000 |
| Pocock | 0.8011 | 1.4815 | 7.82 | 0.9997 |
| naive weekly | 0.8007 | **1.7308** | 7.01 | 0.9926 |

**Reading once already overstates a real effect by 13%**, because what gets published is conditional
on significance and significance selects the favourable draws. Early stopping makes it worse in
proportion to how early you are allowed to stop: 27% under O'Brien-Fleming, 48% under Pocock, **73%
under the rule actually in use.**

So the ordering is not "the valid rules are clean and the naive one is dirty". Every rule that can
stop early reports a flattering number, and a valid boundary repairs the false-positive rate **only**.
Repairing the estimate is a different instrument, and the cheapest version of it is not stopping
early. Note the direction, too: it is the same direction as every other finding in this repository.

## Result 5: and on an underpowered test it is not 73%, it is 163%

Wave 2 showed the holdout could establish nothing below a return of 4.25 on email, against a truth
of 5.76 — a test close to the edge of its own power. At 30% power:

| Rule | Power | Reported ÷ true | Stops after | Right direction |
| --- | --- | --- | --- | --- |
| read once | 0.3008 | **1.8036** | 1.00 | 0.9987 |
| naive weekly | 0.4780 | **2.6344** | 9.55 | **0.9614** |

Read once, the published effect is already **1.80 times** the truth. Read weekly, **2.63 times** —
and **3.9%** of the results that clear the line point the wrong way entirely, so the report does not
merely exaggerate the channel, it occasionally reverses it.

**An underpowered test is not a weak test. It is a test whose successes are mostly noise**, and
peeking is the mechanism by which the noise gets declared. That is why this document sits next to
[`README-sizing.md`](README-sizing.md) rather than on its own: peeking and under-sizing are not two
problems, they are one problem measured from two ends.

## Assumptions and limitations

The package-level assumptions are in [`README.md`](README.md). Specific to this document:

- **Equal information between looks.** The recursion assumes each look adds the same amount of
  information, which is what weekly reads of a steady-traffic test approximate. Unequal spacing
  changes the boundaries; the standard treatment is an alpha-spending function, which is the natural
  next thing to build here and is not built.
- **Normal increments, so normal-theory boundaries.** Group-sequential boundaries conventionally
  work in information units with normal increments. Wave 2's sizing uses the t distribution; at
  thirty-eight degrees of freedom the critical values differ by 3.3%, which is the accuracy of
  composing the two.
- **The recursion is deterministic and its convergence is asserted, not assumed.** The figures are
  identical to six decimal places at 100, 300 and 600 quadrature nodes, and are checked against a
  four-million-draw simulation: 0.141689 against 0.141656 ± 0.00034 at five looks, 0.193357 against
  0.193018 ± 0.00039 at ten, 0.247911 against 0.247841 ± 0.00042 at twenty. A closed form that only
  agrees with itself has been verified against nothing.
- **The boundaries reproduce the classical published ones**, which is the other external check: at
  five looks the O'Brien-Fleming nominal levels come out 0.000005, 0.001257, 0.008445, 0.022556 and
  0.041343, and the Pocock constants at one, two, three, four, five and twenty looks come out 1.9600,
  2.1783, 2.2895, 2.3613, 2.4132 and 2.6720. Those are facts about a recursion rather than statistics about a market, which
  is why they can be checked at all.
- **The exaggeration ratios are simulated**, on a declared seed, because the conditional expectation
  of an estimate at a random stopping time has no closed form worth the algebra. They are
  reproducible to the same standard as everything else here, and the control case — reading once, at
  high power — drives the ratio to one.
- **Only two-sided symmetric boundaries, and only for efficacy.** No futility boundary, so nothing
  here can stop a test for being hopeless — which is the other half of a real monitoring plan and
  the thing that would actually save the forgone conversions wave 2 priced.
- **No estimate correction.** The module measures the exaggeration; it does not repair it. A
  median-unbiased or bias-adjusted estimate at the stopping time exists and is not implemented, so
  the honest use of Result 4 is as an argument against stopping early rather than as a correction
  factor to multiply by.

## Sources

- Armitage, P., McPherson, C. K., Rowe, B. C. (1969). *Repeated Significance Tests on Accumulating
  Data.* Journal of the Royal Statistical Society A 132(2). — the recursion implemented here.
- Pocock, S. J. (1977). *Group Sequential Methods in the Design and Analysis of Clinical Trials.*
  Biometrika 64(2).
- O'Brien, P. C., Fleming, T. R. (1979). *A Multiple Testing Procedure for Clinical Trials.*
  Biometrics 35(3).
- Lan, K. K. G., DeMets, D. L. (1983). *Discrete Sequential Boundaries for Clinical Trials.*
  Biometrika 70(3). — the alpha-spending generalisation this module deliberately stops short of.
- Johari, R., Koomen, P., Pekelis, L., Walsh, D. (2017). *Peeking at A/B Tests: Why It Matters, and
  What to Do About It.* KDD.
- Gelman, A., Carlin, J. (2014). *Beyond Power Calculations: Assessing Type S and Type M Errors.*
  Perspectives on Psychological Science 9(6). — the exaggeration ratio in Results 4 and 5.

---

# `mktlab.design.sequential` — o teste que é lido toda segunda-feira

*[English](#mktlabdesignsequential--the-test-that-is-read-every-monday)*

## O problema de negócio

A onda 2 dimensionou um holdout geográfico com cuidado e apoiou todo o cálculo numa premissa que
nunca escreveu: que o teste é lido **uma vez**, no fim de treze semanas. Ninguém faz isso. O teste
fica num painel que atualiza toda semana, alguém olha toda segunda-feira, e ele é declarado na
primeira vez que cruza a linha.

Ler uma fronteira fixa de 1,96 treze vezes leva a taxa de falso-positivo de 5% para **21,4%**. Um
canal que não faz absolutamente nada é declarado vencedor cerca de **uma vez em cinco**. Cada olhada
individual está aritmeticamente correta. O que está errado é que a regra de decisão em vigor não é
aquela para a qual o 1,96 foi calculado — e quem toma a decisão normalmente não sabe que existe uma
regra de decisão.

## A decisão que habilita

1. **Qual é a taxa de erro do teste que estamos de fato rodando**, em oposição ao que desenhamos?
2. **Quanto custa ter o direito de olhar?** Porque é um custo real e é menor do que se teme — para
   uma das duas respostas padrão.
3. **E quanto o número que reportamos está inflado?** Que é a parte que uma fronteira correta não
   corrige, e que ninguém menciona.

## Uso

```python
from mktlab.design import exaggeration, inflated_alpha, peeking_table, plan

inflated_alpha(13)  # 0,213814 - treze olhadas semanais no 1,96 de sempre

peeking_table(13)  # as quatro regras, precificadas lado a lado
plan("obrien-fleming", 13).verdict()
# "obrien-fleming: 13 looks holding alpha at 0.0500, +4.3% information, stops after 9.79 looks..."

exaggeration(plan("naive", 13).boundary, ncp=2.477)["ratio"]  # 1,7308
```

## Resultado 1: a taxa de erro contra o número de olhadas

Calculada pela recursão de Armitage-McPherson-Rowe — a densidade da soma acumulada levada adiante
pela região de continuação, olhada por olhada. Não simulada, e não um limite tipo Bonferroni: as
olhadas são fortemente dependentes, porque cada uma contém todos os dados das anteriores, e
tratá-las como independentes daria uma resposta muito errada na outra direção.

| Olhadas | Taxa real de falso-positivo | Vezes o 5% nominal |
| --- | --- | --- |
| 1 | 0,050000 | 1,00× |
| 2 | **0,083118** | 1,66× |
| 3 | 0,107256 | 2,15× |
| 5 | 0,141689 | 2,83× |
| 10 | 0,193357 | 3,87× |
| **13** | **0,213814** | **4,28×** |
| 26 | 0,268788 | 5,38× |
| 52 | 0,323512 | 6,47× |

**A curva é mais inclinada no começo.** Olhar duas vezes em vez de uma já custa 66% mais erro do que
o desenho admite. A diferença entre monitorar semanalmente e diariamente importa muito menos que a
diferença entre uma e duas vezes — o que inverte a intuição usual de que olhadas ocasionais são
inofensivas e só o monitoramento obsessivo é problema.

## Resultado 2: duas fronteiras honestas, e são trocas diferentes

| Regra | Olhadas | Primeira fronteira | Última fronteira | α nominal (1ª / última) | α real | Válida | Informação | Para após |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ler uma vez | 1 | 1,9600 | 1,9600 | 0,0500 / 0,0500 | 0,0500 | sim | 1,0000 | 1,00 olhada |
| **ingênua semanal** | 13 | 1,9600 | 1,9600 | 0,0500 / 0,0500 | **0,2138** | **não** | — | 6,20 olhadas |
| Pocock | 13 | 2,6019 | 2,6019 | 0,0093 / 0,0093 | 0,0500 | sim | **1,3247** | 7,83 olhadas |
| O'Brien-Fleming | 13 | **7,5799** | 2,1023 | 3,5e-14 / 0,0355 | 0,0500 | sim | **1,0432** | 9,79 olhadas |

Leia a linha ingênua como o diagnóstico e as outras duas como prescrições. As duas mantêm a taxa de
erro em exatamente 5% ao longo de treze leituras semanais, e compram coisas diferentes:

- **Pocock** aplica a mesma barra mais alta toda semana — p-valor abaixo de **0,0093** em qualquer
  olhada. Pode encerrar o teste na semana um, e precisa de um teste **32% maior** para manter 80% de
  poder.
- **O'Brien-Fleming** começa quase fechada e vai abrindo: a barra da primeira semana é **7,58
  erros-padrão**, e a da última é 2,10, pouco acima do 1,96 de amostra fixa. Custa apenas **4,3%**
  mais informação, e não encerra o teste na primeira metade por melhores que os números pareçam.

Essa primeira fronteira de 7,58 não é um acidente numérico e é a frase mais útil deste documento:
**o desenho está dizendo que nada observável na semana um deveria encerrar um teste de treze
semanas.** Que é também a resposta honesta à maioria dos pedidos de encerrar um teste antes.

## Resultado 3: a versão honesta custa cerca de 2% do holdout

Mais informação significa ou um retorno detectável pior no mesmo tamanho, ou mais regiões para manter
o retorno onde estava. Para o email — o canal que a onda 2 mostrou já estar no limite do que o teste
conseguia resolver:

| Regra | α real | Informação | iROAS detectável | Regiões para o mesmo piso |
| --- | --- | --- | --- | --- |
| ler uma vez | 0,0500 | 1,0000 | 4,2498 | 24 |
| ingênua semanal | **0,2138** | — | — | — |
| O'Brien-Fleming | 0,0500 | 1,0432 | **4,3406** | **26** |
| Pocock | 0,0500 | 1,3247 | 4,8913 | 32 |

**O'Brien-Fleming custa 2,1% do retorno detectável, ou duas regiões extras em vinte e quatro.** É a
conta inteira pelo direito de ler o teste toda semana durante treze semanas sem mentir sobre a taxa
de erro. Não é paga porque nunca foi escrita onde quem desenha o teste pudesse ver. A conta do Pocock
é oito regiões, e o que ela compra é o direito de parar na semana um — o que vale ter quando o
prejuízo de continuar é real, e não vale nos outros casos.

## Resultado 4: a metade que uma fronteira correta não corrige

Um teste para antes porque os dados vieram favoráveis. Então a estimativa no ponto de parada é
sorteada da cauda favorável, e o efeito reportado é maior que o efeito medido. Cada regra abaixo é
avaliada no efeito que dá **àquela regra** 80% de poder, então a comparação é a poder igual e não a
desenho igual:

| Regra | Poder | Reportado ÷ real | Para após | Direção certa |
| --- | --- | --- | --- | --- |
| ler uma vez | 0,8011 | **1,1250** | 1,00 | 1,0000 |
| O'Brien-Fleming | 0,8006 | 1,2695 | 9,79 | 1,0000 |
| Pocock | 0,8011 | 1,4815 | 7,82 | 0,9997 |
| ingênua semanal | 0,8007 | **1,7308** | 7,01 | 0,9926 |

**Ler uma vez já superestima um efeito real em 13%**, porque o que é publicado é condicionado à
significância e a significância seleciona os sorteios favoráveis. Parar antes piora isso na proporção
de quão antes se pode parar: 27% com O'Brien-Fleming, 48% com Pocock, **73% com a regra efetivamente
em uso.**

Portanto a ordenação não é "as regras válidas são limpas e a ingênua é suja". Toda regra que permite
parar antes reporta um número lisonjeiro, e uma fronteira válida corrige **apenas** a taxa de
falso-positivo. Corrigir a estimativa é outro instrumento, e a versão mais barata dele é não parar
antes. Repare também na direção: é a mesma direção de todo outro achado deste repositório.

## Resultado 5: e num teste com pouco poder não é 73%, é 163%

A onda 2 mostrou que o holdout não conseguia estabelecer nada abaixo de um retorno de 4,25 no email,
contra uma verdade de 5,76 — um teste perto do limite do próprio poder. A 30% de poder:

| Regra | Poder | Reportado ÷ real | Para após | Direção certa |
| --- | --- | --- | --- | --- |
| ler uma vez | 0,3008 | **1,8036** | 1,00 | 0,9987 |
| ingênua semanal | 0,4780 | **2,6344** | 9,55 | **0,9614** |

Lido uma vez, o efeito publicado já é **1,80 vez** a verdade. Lido semanalmente, **2,63 vezes** — e
**3,9%** dos resultados que cruzam a linha apontam para o lado errado, então o relatório não apenas
exagera o canal, ele ocasionalmente inverte o canal.

**Um teste com pouco poder não é um teste fraco. É um teste cujos sucessos são em boa parte ruído**,
e espiar é o mecanismo pelo qual o ruído é declarado. É por isso que este documento fica ao lado do
[`README-sizing.md`](README-sizing.md) e não sozinho: espiar e subdimensionar não são dois problemas,
são um problema medido por duas pontas.

## Premissas e limitações

As premissas do pacote estão em [`README.md`](README.md). Específicas deste documento:

- **Informação igual entre olhadas.** A recursão supõe que cada olhada adiciona a mesma quantidade de
  informação, o que leituras semanais de um teste com tráfego estável aproximam. Espaçamento desigual
  muda as fronteiras; o tratamento padrão é uma função de gasto de alfa, que é a coisa natural a
  construir em seguida aqui e não está construída.
- **Incrementos normais, então fronteiras de teoria normal.** Fronteiras de grupos sequenciais
  trabalham convencionalmente em unidades de informação com incrementos normais. O dimensionamento da
  onda 2 usa a distribuição t; com trinta e oito graus de liberdade os valores críticos diferem em
  3,3%, que é a precisão de compor as duas coisas.
- **A recursão é determinística e sua convergência é asserida, não suposta.** As cifras são idênticas
  até a sexta casa decimal com 100, 300 e 600 nós de quadratura, e são conferidas contra uma
  simulação de quatro milhões de sorteios: 0,141689 contra 0,141656 ± 0,00034 em cinco olhadas,
  0,193357 contra 0,193018 ± 0,00039 em dez, 0,247911 contra 0,247841 ± 0,00042 em vinte. Uma forma
  fechada que só concorda consigo mesma não foi verificada contra nada.
- **As fronteiras reproduzem as clássicas publicadas**, que é a outra verificação externa: em cinco
  olhadas os níveis nominais de O'Brien-Fleming saem 0,000005, 0,001257, 0,008445, 0,022556 e
  0,041343, e as constantes de Pocock com uma, duas, três, quatro, cinco e vinte olhadas saem 1,9600,
  2,1783, 2,2895, 2,3613, 2,4132 e 2,6720. São fatos sobre uma recursão e não estatísticas sobre um mercado, e é por isso que
  podem ser conferidas.
- **As razões de exageração são simuladas**, com semente declarada, porque a esperança condicional de
  uma estimativa num tempo de parada aleatório não tem forma fechada que compense a álgebra. São
  reprodutíveis pelo mesmo padrão de tudo aqui, e o caso de controle — ler uma vez, com poder alto —
  leva a razão a um.
- **Só fronteiras bilaterais simétricas, e só de eficácia.** Não há fronteira de futilidade, então
  nada aqui consegue encerrar um teste por ser inútil — que é a outra metade de um plano de
  monitoramento real e a coisa que de fato economizaria as conversões abdicadas que a onda 2
  precificou.
- **Nenhuma correção da estimativa.** O módulo mede a exageração; não a corrige. Uma estimativa
  mediana-não-viesada ou ajustada no tempo de parada existe e não está implementada, então o uso
  honesto do Resultado 4 é como argumento contra parar antes, não como fator de correção para
  multiplicar.

## Fontes

- Armitage, P., McPherson, C. K., Rowe, B. C. (1969). *Repeated Significance Tests on Accumulating
  Data.* Journal of the Royal Statistical Society A 132(2). — a recursão implementada aqui.
- Pocock, S. J. (1977). *Group Sequential Methods in the Design and Analysis of Clinical Trials.*
  Biometrika 64(2).
- O'Brien, P. C., Fleming, T. R. (1979). *A Multiple Testing Procedure for Clinical Trials.*
  Biometrics 35(3).
- Lan, K. K. G., DeMets, D. L. (1983). *Discrete Sequential Boundaries for Clinical Trials.*
  Biometrika 70(3). — a generalização por gasto de alfa da qual este módulo deliberadamente para
  antes.
- Johari, R., Koomen, P., Pekelis, L., Walsh, D. (2017). *Peeking at A/B Tests: Why It Matters, and
  What to Do About It.* KDD.
- Gelman, A., Carlin, J. (2014). *Beyond Power Calculations: Assessing Type S and Type M Errors.*
  Perspectives on Psychological Science 9(6). — a razão de exageração dos Resultados 4 e 5.
