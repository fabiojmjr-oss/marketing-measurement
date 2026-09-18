# `mktlab.design` — deciding what a test can find, before anybody pays for it

*[Português](#mktlabdesign--decidir-o-que-um-teste-consegue-achar-antes-de-alguém-pagar-por-ele)*

Two documents, because they answer two different objections to the same test.

| Document | The question it settles |
| --- | --- |
| [`README-sizing.md`](README-sizing.md) | **Is this test worth running?** The precision it will have before any data exists, the smallest *return* it can establish, what it costs if the channel works, and what a null result already ruled out. |
| [`README-sequential.md`](README-sequential.md) | **And what happens because nobody reads it once?** A thirteen-week holdout glanced at every Monday has a false-positive rate of 21.4%, not 5%. Two boundaries fix that, at prices computed rather than assumed — and neither fixes the flattering estimate that early stopping produces. |
| [`README-monitoring.md`](README-monitoring.md) | **Then write the plan the test should have arrived with.** An alpha-spending schedule, so the looks need not be evenly spaced or even known in advance, and a futility bound, so a test going nowhere ends — for 8.9% more information and a 23.4% chance of abandoning a winner. |

The short version of all three: a geo holdout's precision is a function of the design and not of the
data, so every complaint anybody will have about the result is available in advance. The three
complaints that matter are that the test could never have resolved the return the budget cares
about, that the test was not read the way it was sized, and that nobody agreed in advance on when to
stop.

## Assumptions and limitations

These apply to all three documents; each one also carries the limitations specific to it.

- **Every number comes from a seeded synthetic generator**, including the true lifts the predictions
  are checked against. No advertiser, agency, platform or client data is used anywhere. See
  [`DISCLAIMER.md`](../../../DISCLAIMER.md).
- **The variance model is a floor on the noise, not an estimate of it.** Real regions carry
  autocorrelation, region-specific seasonality and variance that grows with the level. A design
  sized from the closed form here is therefore optimistic, and the gap between it and a spread
  measured from the account's own pre-period is the number a real sizing would look at.
- **The documents use different distributional conventions**, and the composition between them is
  accurate to the difference. The sizing uses the t distribution, as a two-sample comparison of forty
  regions should; the sequential and monitoring boundaries are normal-theory, as group-sequential
  boundaries conventionally are. At thirty-eight degrees of freedom the critical values differ by
  3.3%.
- **The two-sided and one-sided documents are not interchangeable.** Wave 3's boundaries are
  two-sided at 0.05; the monitoring plans are one-sided at 0.025, because that is the form a futility
  bound pairs with. Comparing a boundary from one against a boundary from the other without matching
  the convention is how a plan comes to report twice the error rate it was built for.
- **Nothing here estimates an effect.** These are tools for deciding what a test can support, which
  is a different job from reading one — that is
  [`mktlab.attribution`](../attribution/README.md).

---

# `mktlab.design` — decidir o que um teste consegue achar, antes de alguém pagar por ele

*[English](#mktlabdesign--deciding-what-a-test-can-find-before-anybody-pays-for-it)*

Dois documentos, porque respondem a duas objeções diferentes ao mesmo teste.

| Documento | A pergunta que resolve |
| --- | --- |
| [`README-sizing.md`](README-sizing.md) | **Vale a pena rodar este teste?** A precisão que ele terá antes de existir qualquer dado, o menor *retorno* que consegue estabelecer, quanto custa se o canal funcionar, e o que um resultado nulo já descartou. |
| [`README-sequential.md`](README-sequential.md) | **E o que acontece porque ninguém lê o teste uma única vez?** Um holdout de treze semanas olhado toda segunda-feira tem taxa de falso-positivo de 21,4%, não de 5%. Duas fronteiras corrigem isso, a preços calculados e não supostos — e nenhuma delas corrige a estimativa inflada que a parada antecipada produz. |
| [`README-monitoring.md`](README-monitoring.md) | **Então escreva o plano com o qual o teste deveria ter chegado.** Um cronograma de gasto de alfa, para que as olhadas não precisem ser igualmente espaçadas nem conhecidas de antemão, e uma fronteira de futilidade, para que um teste que não vai dar em nada termine — por 8,9% mais informação e uma chance de 23,4% de abandonar um vencedor. |

A versão curta dos três: a precisão de um holdout geográfico é função do desenho e não dos dados,
então toda reclamação que alguém vai ter sobre o resultado já está disponível antes. As três que
importam são que o teste nunca conseguiria resolver o retorno que o orçamento quer saber, que o teste
não foi lido do jeito para o qual foi dimensionado, e que ninguém combinou antes quando parar.

## Premissas e limitações

Valem para os três documentos; cada um traz também as limitações específicas dele.

- **Todo número vem de um gerador sintético com semente**, inclusive os lifts verdadeiros contra os
  quais as previsões são conferidas. Nenhum dado de anunciante, agência, plataforma ou cliente é
  usado em lugar algum. Ver [`DISCLAIMER.md`](../../../DISCLAIMER.md).
- **O modelo de variância é um piso do ruído, não uma estimativa dele.** Regiões reais carregam
  autocorrelação, sazonalidade específica e variância que cresce com o nível. Um desenho dimensionado
  pela forma fechada daqui é, portanto, otimista — e a distância entre ela e uma dispersão medida no
  próprio pré-período da conta é o número que um dimensionamento real olharia.
- **Os documentos usam convenções distribucionais diferentes**, e a composição entre eles é precisa
  até essa diferença. O dimensionamento usa a distribuição t, como deve fazer uma comparação de duas
  amostras de quarenta regiões; as fronteiras sequenciais e de monitoramento são de teoria normal,
  como convencionalmente são as fronteiras de grupos sequenciais. Com trinta e oito graus de liberdade
  os valores críticos diferem em 3,3%.
- **Os documentos bilateral e unilateral não são intercambiáveis.** As fronteiras da onda 3 são
  bilaterais a 0,05; os planos de monitoramento são unilaterais a 0,025, porque é a forma com que uma
  fronteira de futilidade se casa. Comparar uma fronteira de um com a do outro sem casar a convenção é
  como um plano passa a reportar o dobro da taxa de erro para a qual foi construído.
- **Nada aqui estima um efeito.** São ferramentas para decidir o que um teste consegue sustentar, o
  que é um trabalho diferente de ler um — isso é o
  [`mktlab.attribution`](../attribution/README.md).
