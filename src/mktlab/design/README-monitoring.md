# `mktlab.design` monitoring — the plan the test should have arrived with

*[Português](#mktlabdesign-monitoramento--o-plano-com-o-qual-o-teste-deveria-ter-chegado)*

## The business problem

[`README-sequential.md`](README-sequential.md) priced what weekly glances cost and offered two
boundaries that hold the error rate at its nominal value. Both of them assume something no real test
satisfies: that the looks are **evenly spaced and known before the test starts**. And neither of them
can do the thing a team most wants on week six — end a test that is going nowhere.

The first assumption is not a technicality. A boundary computed for thirteen weekly reads is not the
boundary for a test somebody happened to read in weeks two, five and nine, and a team that reads it
on a different schedule than the one the boundary was computed for is back to having no error rate at
all. The second is a standing cost: the regions in a holdout are held away from a channel nobody can
act on, and a test with no futility rule runs to the calendar whatever it has already shown.

## The decision it enables

1. **Can we monitor a test we have not scheduled?** Yes, if what is committed to in advance is a
   *spending function* rather than a boundary.
2. **When may we give up?** And what does the right to give up cost in power and size?
3. **What does giving up actually save?** Which is not what this repository first claimed.

## Usage

```python
from mktlab.design import equal_information, monitoring_plan, schedule, spending_boundary

# The looks do not have to be evenly spaced, and all three spend exactly 0.025.
spending_boundary((4 / 13, 8 / 13, 1.0), alpha=0.025)  # (3.8751, 2.6312, 1.9835)
spending_boundary((1.0,), alpha=0.025)  # (1.9600,) - reading once is the degenerate case

plan = monitoring_plan(equal_information(13), ncp=2.8591, alpha=0.025)
plan.verdict()
# "13 looks with futility: alpha 0.0224, power 0.7656 against 0.8000, 6.09 looks on a
#  channel doing nothing against 8.94 on one that works"
schedule(plan)  # the table the team has to be handed before the test starts
```

## Result 1: the same error rate, spent on any schedule

An alpha-spending function commits to how much of the error rate may have been spent by each point in
the **accumulation of information**, rather than at each of a fixed number of looks. The boundary at
every look then follows from what has already been spent, solved one look at a time — so the number
and timing of the reads do not have to be known when the test starts, which is the situation
everybody is actually in.

| Schedule | Looks | First boundary | Last boundary | Error rate spent |
| --- | --- | --- | --- | --- |
| weekly, 13 looks | 13 | 7.9965 | 2.0981 | **0.025000** |
| monthly, 3 looks | 3 | 3.8751 | 1.9835 | **0.025000** |
| late start, 4 looks | 4 | 2.9626 | 2.0731 | **0.025000** |
| read once at the end | 1 | **1.9600** | 1.9600 | **0.025000** |

The last row is the control the whole construction has to pass: **reading a test once is the
degenerate case of monitoring it**, and the spending function has to return 1.96 and spend exactly
0.025 there or none of its other numbers mean anything.

## Result 2: how close the approximation is, look by look

A spending function is not the exact boundary; it is a function whose boundary approximates one. The
Lan-DeMets O'Brien-Fleming-like function against the exact O'Brien-Fleming boundary from
[`README-sequential.md`](README-sequential.md), at thirteen evenly spaced looks:

| Look | Spending function | Exact O'Brien-Fleming | Ratio |
| --- | --- | --- | --- |
| 1 | 7.9965 | 7.5799 | **1.0550** |
| 2 | 5.5954 | 5.3598 | 1.0440 |
| 4 | 3.8801 | 3.7900 | 1.0238 |
| 7 | 2.8881 | 2.8649 | 1.0081 |
| 10 | 2.4005 | 2.3970 | 1.0015 |
| 12 | 2.1858 | 2.1881 | 0.9990 |
| 13 | 2.0981 | 2.1023 | **0.9980** |

**The gap closes monotonically, from 5.5% at the first look to 0.2% at the last.** That is the whole
trade: a few per cent of shape early, in exchange for a plan that survives the schedule changing.
Pocock's version is looser — its exact constant is 2.6019 and the spending function opens at 2.7366,
5.2% high, and does not stay constant.

## Result 3: the plan, written down

Powered for an effect whose final statistic has noncentrality 2.8591, which is 80% power with no
futility bound. Thirteen weekly reads, one-sided 0.025, O'Brien-Fleming-like spending on both
schedules:

| Look | Information | α spent | α this look | Efficacy | Nominal α | Futility | β spent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0769 | 0.000000 | 0.000000 | 7.9965 | 0.000000 | **−3.6818** | 0.000004 |
| 2 | 0.1538 | 0.000000 | 0.000000 | 5.5954 | 0.000000 | −1.9447 | 0.001086 |
| 3 | 0.2308 | 0.000003 | 0.000003 | 4.5216 | 0.000006 | −1.0694 | 0.007636 |
| 4 | 0.3077 | 0.000053 | 0.000050 | 3.8801 | 0.000104 | −0.5000 | 0.020869 |
| 5 | 0.3846 | 0.000301 | 0.000248 | 3.4467 | 0.000568 | −0.0768 | 0.038787 |
| 6 | 0.4615 | 0.000969 | 0.000668 | 3.1308 | 0.001743 | **+0.2630** | 0.059242 |
| 7 | 0.5385 | 0.002254 | 0.001285 | 2.8881 | 0.003876 | +0.5493 | 0.080731 |
| 8 | 0.6154 | 0.004273 | 0.002019 | 2.6942 | 0.007057 | +0.7983 | 0.102329 |
| 9 | 0.6923 | 0.007064 | 0.002790 | 2.5347 | 0.011256 | +1.0200 | 0.123503 |
| 10 | 0.7692 | 0.010601 | 0.003537 | 2.4005 | 0.016372 | +1.2208 | 0.143962 |
| 11 | 0.8462 | 0.014824 | 0.004223 | 2.2856 | 0.022275 | +1.4063 | 0.163561 |
| 12 | 0.9231 | 0.019652 | 0.004828 | 2.1858 | 0.028827 | +1.5840 | 0.182243 |
| 13 | 1.0000 | **0.025000** | 0.005348 | 2.0981 | 0.035898 | **+2.0981** | **0.200000** |

Read the futility column downwards, because it is the half of the plan nobody writes. In week one it
sits at **−3.68**: nothing observable that early should end a thirteen-week test. By week six it has
risen above zero, which says that a channel not yet ahead by then is not going to get there. In the
last week it **equals the efficacy bound**, because a test that reaches its end without rejecting has
failed and there is nothing left to continue into.

This table is the deliverable. A monitoring plan that is not written down this way is not a plan — it
is a dashboard and a habit.

## Result 4: what the right to give up costs, and what it buys

| | Without futility | With futility |
| --- | --- | --- |
| One-sided error rate | 0.025000 | **0.022421** |
| Power at the design effect | 0.800000 | **0.765575** |
| Information needed for 80% power | 1.000000 | **1.088761** |
| Looks used, channel doing nothing | **12.94** | **6.09** |
| Looks used, channel that works | 9.83 | 8.94 |
| Chance of abandoning when nothing is happening | 0.000000 | 0.977579 |
| Chance of abandoning a test that would have worked | 0.000000 | **0.234425** |

**On a channel doing nothing the test ends after six weekly reads instead of thirteen.** The bill is
**8.9% more information** to hold the same 80% power, and a **23.4% chance of abandoning a test that
would have succeeded**. Both halves of that belong in the same sentence, and a monitoring plan
presented without the second half is being sold rather than explained.

Note the error rate *falling* to 0.0224 rather than staying at 0.025. That is the futility bound being
**non-binding**: the efficacy boundary is solved as though the test could never be abandoned, so a
team that overrules the futility signal in week seven and keeps going has not broken the error rate,
because the error rate never counted on them obeying it. The gap between 0.0250 and 0.0224 is what
that insurance costs, and it is worth paying: the alternative is a plan that only works if nobody
changes their mind.

## Result 5: what futility does not save, which this repository got wrong first

The roadmap of this repository said a futility boundary "is what would actually save the forgone
conversions wave 2 priced". **That is wrong, and wave 2's own arithmetic says so.** The cost of a
holdout is the held-out population times the channel's *real* lift, so a channel doing nothing costs
nothing to hold out — and a futility bound fires precisely when the effect looks small, which is that
case. The claim had the mechanism backwards.

| Channel | Weeks held, no futility | With futility | Conversions given up, no futility | With futility |
| --- | --- | --- | --- | --- |
| email, which works | 9.83 | 8.94 | 1,258.8 | 1,143.8 |
| retargeting, which does nothing | 12.94 | 6.09 | **0.0** | **0.0** |

What futility saves on the retargeting row is **seven weeks of calendar**, twenty regions kept away
from a channel nobody can act on yet, and a decision that cannot be taken while the test runs. Those
are real costs and they are not conversions. The 115 conversions saved on the email row are the
*efficacy* boundary stopping early on a channel that works — which is the one case where stopping
early does save conversions, and it is not the futility bound's doing.

## Result 6: the spending function is a dial, not a name

| Family | α spent by week 4 | First boundary | Last boundary | Power | Looks if nothing is happening | Chance of abandoning a winner |
| --- | --- | --- | --- | --- | --- | --- |
| O'Brien-Fleming-like | 0.000053 | 7.9965 | 2.0981 | **0.7656** | 6.09 | 0.2344 |
| power, ρ = 3 | 0.000728 | 4.2360 | 2.1090 | 0.7833 | 7.12 | 0.2167 |
| power, ρ = 1 | 0.007692 | 2.8905 | 2.3745 | 0.7139 | 5.27 | 0.2861 |
| Pocock-like | 0.010610 | 2.7366 | 2.4971 | **0.6815** | **4.91** | **0.3185** |

The two right-hand columns move together and against the power column, monotonically: **a schedule
that spends its error early ends the test sooner and pays for it in power**, and one that spends late
keeps the power and reads the test for longer. Pocock-like spending finishes a dead channel in five
weeks instead of six, and buys that with eight points of power and a third of all winners abandoned.
Neither end of that range is a default worth inheriting without looking at those columns.

## Assumptions and limitations

The package-level assumptions are in [`README.md`](README.md). Specific to this document:

- **These plans are one-sided in the efficacy direction**, unlike wave 3's, because that is the form
  a futility bound pairs with: a holdout asks whether the channel helps, and the region where it
  appears to hurt is where giving up belongs rather than where a rejection belongs. A one-sided 0.025
  is the setting comparable to a two-sided 0.05.
- **A plan that cannot give up carries an unreachable futility bound, not a missing one.** In the
  recursion, an absent futility bound means the *two-sided* test wave 3 is built on — so a plan that
  stored "nothing" for "no futility" reported an error rate of 0.0500 for a boundary solved to spend
  0.025. It did, in the first version of this module.
- **Information is treated as known.** In a geo test it is proportional to region-weeks accumulated,
  which is observable, but a spending function evaluated at a *mis-stated* information fraction spends
  the wrong amount of error. Estimating the fraction from the data that also drives the statistic is a
  further subtlety this does not address.
- **The futility schedule is solved against one declared alternative.** A test whose true effect is
  smaller than the one the plan was powered for is abandoned more often than the beta schedule
  suggests, which is the correct behaviour but not what the 23.4% figure refers to.
- **Beta spending sets when the failures are declared, not how many there are.** The final futility
  bound is set equal to the efficacy bound, so the total type II error is whatever the design
  achieves — reported as the power — rather than exactly the beta that was asked for.
- **Nothing here re-solves the efficacy boundary to recover the alpha the futility bound gives back.**
  That is the binding-futility design, it is more efficient, and it only holds if the futility signal
  is actually obeyed. The conservative choice is deliberate.
- **The approximations of Result 2 are to the equal-information boundaries only.** For unequal looks
  there is no classical boundary to compare against, which is the reason spending functions exist and
  also the reason that column stops at thirteen weekly reads.

## Sources

- Lan, K. K. G., DeMets, D. L. (1983). *Discrete Sequential Boundaries for Clinical Trials.*
  Biometrika 70(3). — the spending function implemented here.
- Lan, K. K. G., DeMets, D. L. (1989). *Group Sequential Procedures: Calendar versus Information
  Time.* Statistics in Medicine 8(10). — why the fraction has to be information and not weeks.
- Pampallona, S., Tsiatis, A. A. (1994). *Group Sequential Designs for One-Sided and Two-Sided
  Hypothesis Testing with Provision for Early Stopping in Favor of the Null Hypothesis.* Journal of
  Statistical Planning and Inference 42(1). — beta spending and futility.
- Jennison, C., Turnbull, B. W. (2000). *Group Sequential Methods with Applications to Clinical
  Trials.* Chapman and Hall. — the standard treatment of everything in this document.
- Vaver, J., Koehler, J. (2011). *Measuring Ad Effectiveness Using Geo Experiments.* Google Research.

---

# `mktlab.design` monitoramento — o plano com o qual o teste deveria ter chegado

*[English](#mktlabdesign-monitoring--the-plan-the-test-should-have-arrived-with)*

## O problema de negócio

O [`README-sequential.md`](README-sequential.md) precificou o custo de olhadas semanais e ofereceu
duas fronteiras que mantêm a taxa de erro no valor nominal. As duas supõem algo que nenhum teste real
satisfaz: que as olhadas são **igualmente espaçadas e conhecidas antes de o teste começar**. E nenhuma
das duas consegue fazer o que um time mais quer na semana seis — encerrar um teste que não vai dar em
nada.

A primeira premissa não é detalhe técnico. Uma fronteira calculada para treze leituras semanais não é
a fronteira de um teste que alguém leu nas semanas dois, cinco e nove — e um time que lê num
calendário diferente daquele para o qual a fronteira foi calculada volta a não ter taxa de erro
alguma. A segunda é um custo permanente: as regiões de um holdout ficam afastadas de um canal sobre o
qual ninguém pode agir, e um teste sem regra de futilidade roda até o fim do calendário por mais que
já tenha mostrado.

## A decisão que habilita

1. **Podemos monitorar um teste que não agendamos?** Sim, se o que se compromete antes é uma *função
   de gasto* em vez de uma fronteira.
2. **Quando podemos desistir?** E quanto custa, em poder e em tamanho, o direito de desistir?
3. **O que desistir de fato economiza?** Que não é o que este repositório afirmou primeiro.

## Uso

```python
from mktlab.design import equal_information, monitoring_plan, schedule, spending_boundary

# As olhadas não precisam ser igualmente espaçadas, e as três gastam exatamente 0,025.
spending_boundary((4 / 13, 8 / 13, 1.0), alpha=0.025)  # (3,8751, 2,6312, 1,9835)
spending_boundary((1.0,), alpha=0.025)  # (1,9600,) - ler uma vez é o caso degenerado

plan = monitoring_plan(equal_information(13), ncp=2.8591, alpha=0.025)
plan.verdict()
# "13 looks with futility: alpha 0.0224, power 0.7656 against 0.8000, 6.09 looks on a
#  channel doing nothing against 8.94 on one that works"
schedule(plan)  # a tabela que o time precisa receber antes de o teste começar
```

## Resultado 1: a mesma taxa de erro, gasta em qualquer calendário

Uma função de gasto de alfa se compromete com quanto da taxa de erro pode ter sido gasto a cada ponto
da **acumulação de informação**, em vez de em cada uma de um número fixo de olhadas. A fronteira de
cada olhada então decorre do que já foi gasto, resolvida uma olhada por vez — de modo que o número e o
momento das leituras não precisam ser conhecidos quando o teste começa, que é a situação em que todo
mundo está de fato.

| Calendário | Olhadas | Primeira fronteira | Última fronteira | Taxa de erro gasta |
| --- | --- | --- | --- | --- |
| semanal, 13 olhadas | 13 | 7,9965 | 2,0981 | **0,025000** |
| mensal, 3 olhadas | 3 | 3,8751 | 1,9835 | **0,025000** |
| início tardio, 4 olhadas | 4 | 2,9626 | 2,0731 | **0,025000** |
| ler uma vez no fim | 1 | **1,9600** | 1,9600 | **0,025000** |

A última linha é o controle que toda a construção precisa passar: **ler um teste uma vez é o caso
degenerado de monitorá-lo**, e a função de gasto tem de devolver 1,96 e gastar exatamente 0,025 ali,
ou nenhum dos outros números dela significa coisa alguma.

## Resultado 2: quão perto a aproximação chega, olhada por olhada

Uma função de gasto não é a fronteira exata; é uma função cuja fronteira aproxima uma. A função tipo
O'Brien-Fleming de Lan-DeMets contra a fronteira exata de O'Brien-Fleming do
[`README-sequential.md`](README-sequential.md), com treze olhadas igualmente espaçadas:

| Olhada | Função de gasto | O'Brien-Fleming exata | Razão |
| --- | --- | --- | --- |
| 1 | 7,9965 | 7,5799 | **1,0550** |
| 2 | 5,5954 | 5,3598 | 1,0440 |
| 4 | 3,8801 | 3,7900 | 1,0238 |
| 7 | 2,8881 | 2,8649 | 1,0081 |
| 10 | 2,4005 | 2,3970 | 1,0015 |
| 12 | 2,1858 | 2,1881 | 0,9990 |
| 13 | 2,0981 | 2,1023 | **0,9980** |

**A distância fecha monotonicamente, de 5,5% na primeira olhada para 0,2% na última.** É toda a
troca: alguns por cento de forma no começo, em troca de um plano que sobrevive à mudança de
calendário. A versão de Pocock é mais frouxa — sua constante exata é 2,6019 e a função de gasto abre
em 2,7366, 5,2% acima, e não se mantém constante.

## Resultado 3: o plano, escrito

Dimensionado para um efeito cuja estatística final tem não-centralidade 2,8591, que é 80% de poder sem
fronteira de futilidade. Treze leituras semanais, 0,025 unilateral, gasto tipo O'Brien-Fleming nos
dois cronogramas:

| Olhada | Informação | α gasto | α nesta olhada | Eficácia | α nominal | Futilidade | β gasto |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0,0769 | 0,000000 | 0,000000 | 7,9965 | 0,000000 | **−3,6818** | 0,000004 |
| 2 | 0,1538 | 0,000000 | 0,000000 | 5,5954 | 0,000000 | −1,9447 | 0,001086 |
| 3 | 0,2308 | 0,000003 | 0,000003 | 4,5216 | 0,000006 | −1,0694 | 0,007636 |
| 4 | 0,3077 | 0,000053 | 0,000050 | 3,8801 | 0,000104 | −0,5000 | 0,020869 |
| 5 | 0,3846 | 0,000301 | 0,000248 | 3,4467 | 0,000568 | −0,0768 | 0,038787 |
| 6 | 0,4615 | 0,000969 | 0,000668 | 3,1308 | 0,001743 | **+0,2630** | 0,059242 |
| 7 | 0,5385 | 0,002254 | 0,001285 | 2,8881 | 0,003876 | +0,5493 | 0,080731 |
| 8 | 0,6154 | 0,004273 | 0,002019 | 2,6942 | 0,007057 | +0,7983 | 0,102329 |
| 9 | 0,6923 | 0,007064 | 0,002790 | 2,5347 | 0,011256 | +1,0200 | 0,123503 |
| 10 | 0,7692 | 0,010601 | 0,003537 | 2,4005 | 0,016372 | +1,2208 | 0,143962 |
| 11 | 0,8462 | 0,014824 | 0,004223 | 2,2856 | 0,022275 | +1,4063 | 0,163561 |
| 12 | 0,9231 | 0,019652 | 0,004828 | 2,1858 | 0,028827 | +1,5840 | 0,182243 |
| 13 | 1,0000 | **0,025000** | 0,005348 | 2,0981 | 0,035898 | **+2,0981** | **0,200000** |

Leia a coluna de futilidade de cima para baixo, porque é a metade do plano que ninguém escreve. Na
semana um ela está em **−3,68**: nada observável tão cedo deveria encerrar um teste de treze semanas.
Na semana seis já subiu acima de zero, o que diz que um canal que ainda não está à frente não vai
chegar. Na última semana ela **iguala a fronteira de eficácia**, porque um teste que chega ao fim sem
rejeitar falhou e não há para onde continuar.

Esta tabela é a entrega. Um plano de monitoramento que não está escrito assim não é um plano — é um
painel e um hábito.

## Resultado 4: quanto custa o direito de desistir, e o que ele compra

| | Sem futilidade | Com futilidade |
| --- | --- | --- |
| Taxa de erro unilateral | 0,025000 | **0,022421** |
| Poder no efeito de desenho | 0,800000 | **0,765575** |
| Informação necessária para 80% de poder | 1,000000 | **1,088761** |
| Olhadas usadas, canal que não faz nada | **12,94** | **6,09** |
| Olhadas usadas, canal que funciona | 9,83 | 8,94 |
| Chance de abandonar quando nada acontece | 0,000000 | 0,977579 |
| Chance de abandonar um teste que daria certo | 0,000000 | **0,234425** |

**Num canal que não faz nada o teste termina depois de seis leituras semanais em vez de treze.** A
conta é **8,9% mais informação** para manter os mesmos 80% de poder, e uma **chance de 23,4% de
abandonar um teste que teria dado certo**. As duas metades disso pertencem à mesma frase, e um plano
de monitoramento apresentado sem a segunda está sendo vendido, não explicado.

Repare na taxa de erro *caindo* para 0,0224 em vez de ficar em 0,025. Isso é a fronteira de futilidade
ser **não vinculante**: a fronteira de eficácia é resolvida como se o teste nunca pudesse ser
abandonado, então um time que derruba o sinal de futilidade na semana sete e continua não quebrou a
taxa de erro, porque a taxa de erro nunca contou com a obediência dele. A distância entre 0,0250 e
0,0224 é o que esse seguro custa, e vale pagar: a alternativa é um plano que só funciona se ninguém
mudar de ideia.

## Resultado 5: o que a futilidade não economiza, e o que este repositório errou primeiro

O roadmap deste repositório dizia que uma fronteira de futilidade "é o que de fato economizaria as
conversões abdicadas que a onda 2 precificou". **Isso está errado, e a própria aritmética da onda 2
diz.** O custo de um holdout é a população em holdout vezes o lift *real* do canal, então um canal que
não faz nada não custa nada para segurar — e uma fronteira de futilidade dispara exatamente quando o
efeito parece pequeno, que é esse caso. A afirmação tinha o mecanismo invertido.

| Canal | Semanas seguras, sem futilidade | Com futilidade | Conversões abdicadas, sem | Com |
| --- | --- | --- | --- | --- |
| email, que funciona | 9,83 | 8,94 | 1.258,8 | 1.143,8 |
| retargeting, que não faz nada | 12,94 | 6,09 | **0,0** | **0,0** |

O que a futilidade economiza na linha do retargeting são **sete semanas de calendário**, vinte regiões
mantidas longe de um canal sobre o qual ninguém pode agir, e uma decisão que não pode ser tomada
enquanto o teste roda. São custos reais e não são conversões. As 115 conversões economizadas na linha
do email são a fronteira de *eficácia* parando antes num canal que funciona — o único caso em que
parar antes economiza conversões, e não é obra da fronteira de futilidade.

## Resultado 6: a função de gasto é um dial, não um nome

| Família | α gasto até a semana 4 | Primeira fronteira | Última fronteira | Poder | Olhadas se nada acontece | Chance de abandonar um vencedor |
| --- | --- | --- | --- | --- | --- | --- |
| tipo O'Brien-Fleming | 0,000053 | 7,9965 | 2,0981 | **0,7656** | 6,09 | 0,2344 |
| potência, ρ = 3 | 0,000728 | 4,2360 | 2,1090 | 0,7833 | 7,12 | 0,2167 |
| potência, ρ = 1 | 0,007692 | 2,8905 | 2,3745 | 0,7139 | 5,27 | 0,2861 |
| tipo Pocock | 0,010610 | 2,7366 | 2,4971 | **0,6815** | **4,91** | **0,3185** |

As duas colunas da direita se movem juntas e contra a coluna de poder, monotonicamente: **um
cronograma que gasta o erro cedo termina o teste antes e paga em poder**, e um que gasta tarde
preserva o poder e lê o teste por mais tempo. O gasto tipo Pocock encerra um canal morto em cinco
semanas em vez de seis, e compra isso com oito pontos de poder e um terço de todos os vencedores
abandonados. Nenhuma das pontas dessa faixa é um padrão que valha herdar sem olhar essas colunas.

## Premissas e limitações

As premissas do pacote estão em [`README.md`](README.md). Específicas deste documento:

- **Estes planos são unilaterais na direção da eficácia**, ao contrário dos da onda 3, porque é a
  forma com que uma fronteira de futilidade se casa: um holdout pergunta se o canal ajuda, e a região
  em que ele parece prejudicar é onde cabe desistir, não onde cabe rejeitar. Um 0,025 unilateral é o
  ajuste comparável a um 0,05 bilateral.
- **Um plano que não pode desistir carrega uma fronteira de futilidade inalcançável, não ausente.** Na
  recursão, futilidade ausente significa o teste *bilateral* sobre o qual a onda 3 é construída — então
  um plano que guardava "nada" para "sem futilidade" reportava taxa de erro de 0,0500 para uma
  fronteira resolvida para gastar 0,025. E foi o que a primeira versão deste módulo fez.
- **A informação é tratada como conhecida.** Num teste geográfico ela é proporcional às região-semanas
  acumuladas, que é observável, mas uma função de gasto avaliada numa fração de informação *mal
  declarada* gasta a quantidade errada de erro. Estimar a fração a partir dos mesmos dados que movem a
  estatística é uma subtileza adicional que isto não trata.
- **O cronograma de futilidade é resolvido contra uma alternativa declarada.** Um teste cujo efeito
  real é menor que aquele para o qual o plano foi dimensionado é abandonado mais vezes do que o
  cronograma de beta sugere, o que é o comportamento correto mas não é a que a cifra de 23,4% se
  refere.
- **O gasto de beta define quando as falhas são declaradas, não quantas são.** A fronteira final de
  futilidade é igualada à de eficácia, então o erro tipo II total é o que o desenho alcança — reportado
  como o poder — e não exatamente o beta pedido.
- **Nada aqui re-resolve a fronteira de eficácia para recuperar o alfa que a futilidade devolve.** Esse
  é o desenho de futilidade vinculante, é mais eficiente, e só vale se o sinal de futilidade for de
  fato obedecido. A escolha conservadora é deliberada.
- **As aproximações do Resultado 2 são apenas contra as fronteiras de informação igual.** Para olhadas
  desiguais não existe fronteira clássica para comparar, o que é a razão pela qual funções de gasto
  existem e também a razão pela qual aquela coluna para em treze leituras semanais.

## Fontes

- Lan, K. K. G., DeMets, D. L. (1983). *Discrete Sequential Boundaries for Clinical Trials.*
  Biometrika 70(3). — a função de gasto implementada aqui.
- Lan, K. K. G., DeMets, D. L. (1989). *Group Sequential Procedures: Calendar versus Information
  Time.* Statistics in Medicine 8(10). — por que a fração tem de ser de informação e não de semanas.
- Pampallona, S., Tsiatis, A. A. (1994). *Group Sequential Designs for One-Sided and Two-Sided
  Hypothesis Testing with Provision for Early Stopping in Favor of the Null Hypothesis.* Journal of
  Statistical Planning and Inference 42(1). — gasto de beta e futilidade.
- Jennison, C., Turnbull, B. W. (2000). *Group Sequential Methods with Applications to Clinical
  Trials.* Chapman and Hall. — o tratamento padrão de tudo neste documento.
- Vaver, J., Koehler, J. (2011). *Measuring Ad Effectiveness Using Geo Experiments.* Google Research.
