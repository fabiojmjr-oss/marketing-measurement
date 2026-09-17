# marketing-measurement

*[English](README.md)*

**Quase toda cifra de um relatório de marketing é o cálculo correto da quantidade errada.**

A atribuição distribui crédito sem contrafactual. O retorno sobre investimento em mídia conta
receita que viria de qualquer forma. Um teste declarado na primeira segunda-feira favorável já
gastou sua taxa de erro várias vezes. Nenhum desses é um erro de aritmética — cada um é a aritmética
certa aplicada a uma quantidade que ninguém escolheu deliberadamente, e cada um fica visível no
momento em que a quantidade é escrita como aritmética em vez de como slide.

Este repositório é esse exercício. O `mktlab` é um pacote Python cujas ferramentas respondem, cada
uma, a uma decisão que um orçamento precisa tomar, e que **se recusam a devolver um número quando a
premissa por trás dele não se sustenta** — uma razão contra um denominador não medido volta como
`nan` com uma justificativa anexa, em vez de como uma cifra que se lê como evidência.

Toda tabela vem do `mktlab.synth`, um gerador com semente cujos parâmetros estão escritos, inclusive
a única coluna que nenhuma conta de mídia real possui: **a probabilidade de cada usuário converter
antes de qualquer marketing acontecer.** É essa coluna que permite confrontar as afirmações daqui
com a verdade em vez de com outro modelo. Nenhum dado de anunciante, agência, plataforma ou cliente
é usado em lugar algum — ver [`DISCLAIMER.md`](DISCLAIMER.md).

## O achado, em uma tabela

Cinco canais. Dois deles têm efeito verdadeiro exatamente zero, porque são exibidos a quem já ia
converter. Crédito de last-click contra o que um holdout geográfico estabelece:

| Canal | Efeito real | Participação last-click | ROAS | iROAS | O holdout estabeleceu? |
| --- | --- | --- | --- | --- | --- |
| email | +0,010 | 0,1605 | **25,16** | 5,2165 | sim |
| retargeting | **0,000** | 0,1805 | **9,43** | 0,3773 | **não** |
| busca-marca | **0,000** | 0,2311 | **8,05** | −0,2892 | **não** |
| busca-generica | +0,030 | 0,2213 | 5,78 | 1,8398 | sim |
| social-pago | +0,060 | 0,2067 | **3,60** | **5,6981** | sim |

Lido de cima para baixo, esse é o ranking que o relatório mostra. Os dois canais em segundo e
terceiro lugar não têm retorno incremental estabelecido algum — **31,9% de um orçamento de
470.000** — e o canal em último é o único que cria demanda em vez de colhê-la. Agregado, a conta
reporta **ROAS 6,6711 contra iROAS 2,8667**.

Mais três resultados do mesmo conjunto de dados:

- **O last-click entrega aos dois canais sem efeito 41,16% do crédito** e faz daquele com a
  segmentação mais inclinada pela intenção a maior linha isolada da conta.
- **First-click e last-click divergem até 7,67×** sobre as mesmas jornadas. Só a regra mudou.
- **O valor de Shapley do jogo de cobertura da jornada é exatamente a atribuição linear.** Calculado
  pelo caminho longo, sobre todas as coalizões: a maior diferença é 9,09e-13 conversões em 17.419. O
  modelo "data-driven" é dividir por n — e é comprovadamente indiferente à ordem dos toques que ele
  é vendido como entendendo.

## E o teste que produziu as colunas da direita nunca foi dimensionado

O holdout acima resolveu três canais de cinco. Cada parte disso era calculável antes de desligar uma
única região — inclusive a parte que ninguém calcula:

- **O lift mínimo detectável é idêntico para os cinco canais, e o *retorno* mínimo detectável difere
  por um fator de nove.** Mesmo teste, mesmas semanas: resolve retornos até 0,47 no maior canal e não
  consegue estabelecer nada abaixo de **4,25** no menor. O retorno real do email, 5,76, volta como
  "algo entre 2,8 e 8,8".
- **Um resultado nulo num canal pequeno compra um limite superior e nada mais.** O holdout de
  retargeting descartou retornos acima de 1,4085 — um fato real, treze semanas dele — e o desenho não
  conseguiria estabelecer nenhum retorno abaixo de 1,4166. Esses dois números têm o mesmo tamanho por
  construção.
- **O holdout não custa nada nos canais que não fazem nada** e abdica de 27,64% das conversões das
  regiões em holdout no canal que mais importa manter.
- **Metade do desenho é grátis, e é a metade que ninguém estende.** Um pré-período mais longo não
  coloca ninguém em holdout e entra no erro-padrão exatamente como o pós-período. Um pré-período
  ilimitado vale *exatamente* o mesmo que dobrar o número de regiões — 0,000582 nos dois casos,
  igual e não próximo, porque os dois cortam a mesma variância pela metade.

## Módulos

| Módulo | O que decide |
| --- | --- |
| [`mktlab.attribution`](src/mktlab/attribution/README.md) | Quem leva o crédito sob seis modelos, o que um holdout geográfico diz em vez disso, e a diferença entre o ROAS e sua versão incremental. |
| [`mktlab.design`](src/mktlab/design/README.md) | Se o teste vale ser rodado: a precisão que ele terá, o menor **retorno** que consegue estabelecer, quanto custa se o canal funcionar, e o que um resultado nulo já descartou. |

Todo README de módulo é bilíngue e traz uma seção **Premissas e limitações**, porque uma cifra sem
suas premissas não é um resultado.

## Exemplos

| Exemplo | O que mostra |
| --- | --- |
| [`examples/01_who_gets_the_credit.py`](examples/01_who_gets_the_credit.py) | Seis modelos de atribuição sobre uma mesma base de jornadas, a identidade de Shapley, as conversões que ninguém tocou, e o holdout que derruba os seis. |
| [`examples/02_the_test_nobody_sized.py`](examples/02_the_test_nobody_sized.py) | O mesmo holdout, precificado antes de rodar: sua precisão, quais canais ele sempre iria resolver, o retorno que ele nunca conseguiria estabelecer, e quanto custou. |

## Instalar e rodar

```bash
python -m pip install -e ".[dev]"
make check       # lint, tipos e a suíte rápida - o que libera um push
make check-all   # o acima mais toda cifra documentada re-derivada
python examples/01_who_gets_the_credit.py
python examples/02_the_test_nobody_sized.py
```

## Como as afirmações são mantidas honestas

**167 testes, 100% de cobertura de linhas e de ramos.** 140 deles rodam em segundos e liberam cada
push. Os 27 restantes re-derivam, a partir do gerador, toda cifra citada em todo README deste
repositório, e rodam todo script de exemplo. Uma mudança que mova um número publicado quebra o build
em vez de deixar o texto silenciosamente errado.

Três disciplinas, cada uma adotada depois de ter pegado algo:

1. **Verificação contra formas fechadas e casos de controle, nunca contra a saída do próprio
   código.** Os modelos de atribuição são conferidos contra alocações resolvidas no papel como
   frações exatas; o estimador geográfico contra um painel sem ruído cuja diferença em diferenças é
   exatamente +0,04, com uma tendência comum e uma diferença permanente entre regiões adicionadas
   para confirmar que nenhuma das duas chega à estimativa; as taxas médias do gerador contra a
   expectativa analítica para a qual elas fecham; a função de poder contra seu próprio caso de
   controle, em que um lift exatamente zero tem de devolver alfa com doze casas decimais; e o
   erro-padrão previsto contra os cinco painéis efetivamente simulados.
2. **Cifras são asseridas, não citadas.** Inclusive as que o repositório faz sobre si mesmo: a
   contagem de testes acima, a tabela de módulos correspondendo ao pacote, as duas edições de idioma
   existindo, e todo exemplo estando linkado de algum lugar.
3. **Conectar os módulos encontra defeitos que escrever mais módulos não encontra.** Cinco dos seis
   defeitos registrados até aqui foram achados escrevendo um exemplo ou um caso de controle, não
   lendo código. Eles estão registrados na documentação do módulo em vez de corrigidos em silêncio — a
   função de retorno um dia multiplicou a *participação* de um canal pelo total de conversões, o que
   espalha as conversões sem toque entre os canais e é precisamente o erro que o módulo existe para
   denunciar.

Ver [`docs/ROADMAP.md`](docs/ROADMAP.md) para o que está construído, o que está deliberadamente
ausente, e o que continua aberto.

## Licença

MIT. Ver [`LICENSE`](LICENSE).
