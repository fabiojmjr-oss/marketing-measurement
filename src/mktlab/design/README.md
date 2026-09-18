# `mktlab.design` — deciding what a test can find, before anybody pays for it

*[Português](#mktlabdesign--decidir-o-que-um-teste-consegue-achar-antes-de-alguém-pagar-por-ele)*

Two documents, because they answer two different objections to the same test.

| Document | The question it settles |
| --- | --- |
| [`README-sizing.md`](README-sizing.md) | **Is this test worth running?** The precision it will have before any data exists, the smallest *return* it can establish, what it costs if the channel works, and what a null result already ruled out. |
| [`README-sequential.md`](README-sequential.md) | **And what happens because nobody reads it once?** A thirteen-week holdout glanced at every Monday has a false-positive rate of 21.4%, not 5%. Two boundaries fix that, at prices computed rather than assumed — and neither fixes the flattering estimate that early stopping produces. |

The short version of both: a geo holdout's precision is a function of the design and not of the
data, so every complaint anybody will have about the result is available in advance. The two
complaints that matter are that the test could never have resolved the return the budget cares
about, and that the test was not read the way it was sized.

## Assumptions and limitations

These apply to both documents; each one also carries the limitations specific to it.

- **Every number comes from a seeded synthetic generator**, including the true lifts the predictions
  are checked against. No advertiser, agency, platform or client data is used anywhere. See
  [`DISCLAIMER.md`](../../../DISCLAIMER.md).
- **The variance model is a floor on the noise, not an estimate of it.** Real regions carry
  autocorrelation, region-specific seasonality and variance that grows with the level. A design
  sized from the closed form here is therefore optimistic, and the gap between it and a spread
  measured from the account's own pre-period is the number a real sizing would look at.
- **The two documents use different distributional conventions**, and the composition between them
  is accurate to the difference. The sizing uses the t distribution, as a two-sample comparison of
  forty regions should; the sequential boundaries are normal-theory, as group-sequential boundaries
  conventionally are. At thirty-eight degrees of freedom the critical values differ by 3.3%.
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

A versão curta dos dois: a precisão de um holdout geográfico é função do desenho e não dos dados,
então toda reclamação que alguém vai ter sobre o resultado já está disponível antes. As duas que
importam são que o teste nunca conseguiria resolver o retorno que o orçamento quer saber, e que o
teste não foi lido do jeito para o qual foi dimensionado.

## Premissas e limitações

Valem para os dois documentos; cada um traz também as limitações específicas dele.

- **Todo número vem de um gerador sintético com semente**, inclusive os lifts verdadeiros contra os
  quais as previsões são conferidas. Nenhum dado de anunciante, agência, plataforma ou cliente é
  usado em lugar algum. Ver [`DISCLAIMER.md`](../../../DISCLAIMER.md).
- **O modelo de variância é um piso do ruído, não uma estimativa dele.** Regiões reais carregam
  autocorrelação, sazonalidade específica e variância que cresce com o nível. Um desenho dimensionado
  pela forma fechada daqui é, portanto, otimista — e a distância entre ela e uma dispersão medida no
  próprio pré-período da conta é o número que um dimensionamento real olharia.
- **Os dois documentos usam convenções distribucionais diferentes**, e a composição entre eles é
  precisa até essa diferença. O dimensionamento usa a distribuição t, como deve fazer uma comparação
  de duas amostras de quarenta regiões; as fronteiras sequenciais são de teoria normal, como
  convencionalmente são as fronteiras de grupos sequenciais. Com trinta e oito graus de liberdade os
  valores críticos diferem em 3,3%.
- **Nada aqui estima um efeito.** São ferramentas para decidir o que um teste consegue sustentar, o
  que é um trabalho diferente de ler um — isso é o
  [`mktlab.attribution`](../attribution/README.md).
