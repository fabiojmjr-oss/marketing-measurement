# Disclaimer

*[Português abaixo](#aviso)*

**No data from any employer, client, advertiser, agency, ad platform or third party is used
anywhere in this repository.**

Every table in every example, test and README figure is produced by `mktlab.synth`, a seeded
generator whose parameters are written down in `src/mktlab/synth/config.py`. Running
`generate_dataset()` on the default seed reproduces every published number exactly. No advertising
account was read, exported, queried or approximated to build it, and no platform API is called
anywhere in the codebase.

The channel names (`social-pago`, `email`, `busca-generica`, `retargeting`, `busca-marca`) are
**invented Portuguese labels for generic marketing functions**, not the structure of any real
account. So are every spend figure, the value per conversion, the base conversion rate, the number
of users, the region labels of the geo panels (`UF-01` to `UF-40`, which are not Brazilian states
or any other real geography), and the true effects themselves — the zero effects on `retargeting` and `busca-marca` included. None of these are measurements of, or
references to, any real campaign, channel, market, region, brand, agency, vendor or platform, and
any resemblance to one is coincidental.

One column deserves naming on its own. The `intent` column — how likely each user was to convert
before any marketing happened — is **invented, and is the reason this repository can say anything
at all.** No real advertising account has it, which is precisely why attribution cannot be checked
against the truth in practice. Here it is drawn from a declared Beta distribution, exposure is
drawn as a declared function of it, and conversion as a declared function of both. Every claim in
the READMEs about a model getting the wrong answer is a claim against that declared truth, not
against an observed one.

The weekly panel the media mix model is fitted on is invented in the same way, and carries a
second column no real account has: `baseline`, the conversions the account would have recorded in
that week with no marketing at all. The budget swing, the per-channel swing, the trend, the seasonal
amplitude, the carryover and the saturation point are all declared parameters in
`src/mktlab/synth/config.py`, and every statement about what a model recovered is measured against
them.

Everything in the generator was designed to make a particular measurement situation visible — two
channels whose entire performance is selection on intent, one channel that creates demand it does
not get credited for, conversions with no touch at all, a holdout large enough to resolve some
effects and not others — not to represent any real account. The effects, exposure rates, spreads
and sample sizes were chosen for what they demonstrate.

No market statistic, industry benchmark or third-party figure is quoted as fact anywhere in this
repository. Where the literature is referenced, it is cited by name in the module's **Sources**
section as the origin of a *method* or of a published field experiment, never as a source of
numbers appearing in these tables.

This repository is a portfolio of methods. It is not a report about any account, brand or market.

---

# Aviso

*[English above](#disclaimer)*

**Nenhum dado de empregador, cliente, anunciante, agência, plataforma de mídia ou terceiro é
utilizado em qualquer parte deste repositório.**

Toda tabela em todo exemplo, teste e figura de README é produzida pelo `mktlab.synth`, um gerador
com semente cujos parâmetros estão escritos em `src/mktlab/synth/config.py`. Rodar
`generate_dataset()` na semente padrão reproduz exatamente todo número publicado. Nenhuma conta de
mídia foi lida, exportada, consultada ou aproximada para construí-lo, e nenhuma API de plataforma é
chamada em lugar algum do código.

Os nomes de canal (`social-pago`, `email`, `busca-generica`, `retargeting`, `busca-marca`) são
**rótulos inventados em português para funções genéricas de marketing**, não a estrutura de nenhuma
conta real. Também são inventados todos os valores de investimento, o valor por conversão, a
taxa-base de conversão, o número de usuários, os rótulos de região dos painéis geográficos (`UF-01`
a `UF-40`, que não são unidades federativas nem qualquer outra geografia real), e os próprios
efeitos verdadeiros — inclusive os efeitos zero de `retargeting` e
`busca-marca`. Nada disso é medição de, ou referência a, nenhuma campanha, canal, mercado, região,
marca, agência, fornecedor ou plataforma real, e qualquer semelhança é coincidência.

Uma coluna merece ser nomeada à parte. A coluna `intent` — a probabilidade de cada usuário converter
antes de qualquer marketing acontecer — é **inventada, e é a razão pela qual este repositório
consegue afirmar qualquer coisa.** Nenhuma conta de mídia real a possui, e é exatamente por isso que
na prática a atribuição não pode ser confrontada com a verdade. Aqui ela é sorteada de uma
distribuição Beta declarada, a exposição é sorteada como função declarada dela, e a conversão como
função declarada de ambas. Toda afirmação nos READMEs sobre um modelo chegar à resposta errada é uma
afirmação contra essa verdade declarada, não contra uma verdade observada.

O painel semanal sobre o qual o modelo de mix de mídia é ajustado é inventado do mesmo jeito, e
carrega uma segunda coluna que nenhuma conta real tem: `baseline`, as conversões que a conta teria
registrado naquela semana sem marketing algum. A oscilação de orçamento, a oscilação por canal, a
tendência, a amplitude sazonal, o carryover e o ponto de saturação são todos parâmetros declarados em
`src/mktlab/synth/config.py`, e toda afirmação sobre o que um modelo recuperou é medida contra eles.

Tudo no gerador foi desenhado para tornar visível uma situação de medição específica — dois canais
cujo desempenho inteiro é seleção por intenção, um canal que cria demanda pela qual não é creditado,
conversões sem toque algum, um holdout grande o bastante para resolver alguns efeitos e não outros —
e não para representar conta real alguma. Os efeitos, as taxas de exposição, as dispersões e os
tamanhos de amostra foram escolhidos pelo que demonstram.

Nenhuma estatística de mercado, benchmark de indústria ou número de terceiro é citado como fato em
qualquer parte deste repositório. Onde a literatura é referenciada, ela é citada nominalmente na
seção **Fontes** do módulo como origem de um *método* ou de um experimento de campo publicado, nunca
como fonte de números que aparecem nestas tabelas.

Este repositório é um portfólio de métodos. Não é um relatório sobre conta, marca ou mercado algum.
