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
| email | +0,010 | 0,1717 | **26,96** | 8,2904 | sim |
| retargeting | **0,000** | 0,1800 | **9,42** | 0,2377 | **não** |
| busca-marca | **0,000** | 0,2322 | **8,10** | 0,5369 | **não** |
| busca-generica | +0,030 | 0,2145 | 5,61 | 2,1265 | sim |
| social-pago | +0,060 | 0,2015 | **3,52** | 5,8173 | sim |

Lido de cima para baixo, esse é o ranking que o relatório mostra. Os dois canais em segundo e
terceiro lugar não têm retorno incremental estabelecido algum — **31,9% de um orçamento de
470.000** — e o canal em último é o único que cria demanda em vez de colhê-la, e o único com razão
ROAS/iROAS abaixo de um. Agregado, a conta reporta **ROAS 6,6814 contra iROAS 3,2568**.

Mais três resultados do mesmo conjunto de dados:

- **O last-click entrega aos dois canais sem efeito 41,22% do crédito** e faz daquele com a
  segmentação mais inclinada pela intenção a maior linha isolada da conta.
- **First-click e last-click divergem até 7,01×** sobre as mesmas jornadas. Só a regra mudou.
- **O valor de Shapley do jogo de cobertura da jornada é exatamente a atribuição linear.** Calculado
  pelo caminho longo, sobre todas as coalizões: a maior diferença é 1,8e-12 conversões em 17.446. O
  modelo "data-driven" é dividir por n — e é comprovadamente indiferente à ordem dos toques que ele
  é vendido como entendendo.
- **10,16% das conversões não têm toque algum**, e todo modelo as descarta ou reescala em silêncio.

## E o teste que produziu as colunas da direita nunca foi dimensionado

O holdout acima resolveu três canais de cinco. Cada parte disso era calculável antes de desligar uma
única região — inclusive a parte que ninguém calcula:

- **O lift mínimo detectável é idêntico para os cinco canais, e o *retorno* mínimo detectável difere
  por um fator de nove.** Mesmo teste, mesmas semanas: resolve retornos até 0,47 no maior canal e não
  consegue estabelecer nada abaixo de **4,25** no menor. O retorno real do email, 5,76, volta como
  "algo entre 2,8 e 8,8".
- **Um resultado nulo num canal pequeno compra um limite superior e pouco mais.** O holdout de
  retargeting descartou retornos acima de 1,0745 — um fato real, treze semanas dele — enquanto o
  desenho não conseguiria estabelecer nenhum retorno abaixo de 1,4166: não havia retorno que ele
  pudesse ao mesmo tempo perder e detectar. Esses dois números têm sempre o mesmo tamanho, que é a
  afirmação geral.
- **O holdout não custa nada nos canais que não fazem nada** e abdica de 27,64% das conversões das
  regiões em holdout no canal que mais importa manter.
- **Metade do desenho é grátis, e é a metade que ninguém estende.** Um pré-período mais longo não
  coloca ninguém em holdout e entra no erro-padrão exatamente como o pós-período. Um pré-período
  ilimitado vale *exatamente* o mesmo que dobrar o número de regiões — 0,000582 nos dois casos,
  igual e não próximo, porque os dois cortam a mesma variância pela metade.

## E ninguém lê um teste uma única vez

Esse dimensionamento se apoia numa premissa que nunca declara: que o holdout é lido uma vez, no fim.
Ele roda treze semanas num painel.

- **Treze olhadas semanais no 1,96 de sempre levam a taxa de falso-positivo a 21,4%, não 5%** — um
  canal que não faz nada é declarado vencedor cerca de uma vez em cinco. A curva é mais inclinada no
  começo: olhar *duas* vezes já custa 66% mais erro do que o desenho admite.
- **A correção honesta custa 2,1% do retorno detectável.** Uma fronteira de O'Brien-Fleming mantém a
  taxa de erro em exatamente 5% nas treze leituras por 4,3% mais informação — duas regiões extras em
  vinte e quatro. A versão de Pocock custa oito regiões e compra o direito de parar na semana um.
- **Sua primeira fronteira é 7,58 erros-padrão**, que é o desenho dizendo que nada observável na
  semana um deveria encerrar um teste de treze semanas.
- **E uma fronteira correta corrige apenas a taxa de erro.** A poder igual, ler uma vez superestima um
  efeito real em 13% — a publicação é condicionada à significância —, O'Brien-Fleming em 27%, Pocock
  em 48%, e espiar semanalmente em **73%**. Num teste com pouco poder, lido semanalmente, o efeito
  reportado é **2,63 vezes** a verdade e 3,9% dos resultados que cruzam a linha apontam para o lado
  errado.

## E o plano de leitura pode ser escrito

As duas fronteiras supõem que as olhadas são igualmente espaçadas e conhecidas antes de o teste
começar, e nenhuma consegue encerrar um teste que não vai dar em nada.

- **Um cronograma de gasto de alfa corrige a primeira coisa.** Comprometa-se com quanto erro pode ser
  gasto a cada ponto da acumulação de informação, e a fronteira decorre — de modo que treze leituras
  semanais, três mensais, quatro começando na metade ou uma única no fim gastam **exatamente 0,025**,
  e a última delas devolve 1,96.
- **Uma fronteira de futilidade corrige a segunda, e seu preço é o primeiro custo honesto deste arco
  pequeno o bastante para simplesmente pagar:** num canal que não faz nada o teste termina depois de
  **seis** leituras semanais em vez de treze, por **8,9% mais informação** e uma **chance de 23,4% de
  abandonar um teste que teria dado certo**.
- **E ela economiza calendário, não conversões** — o que o roadmap deste repositório inverteu. Um canal
  que não faz nada não custa nada para segurar, então o caso em que a futilidade dispara é o caso sem
  custo de conversão a economizar. O que ela economiza são sete semanas e vinte regiões.

## E o modelo construído no lugar resolve um canal em cinco

Cada um desses custos é um motivo para alguém dizer não ao experimento, e um modelo de mix de mídia é
o que se constrói no lugar: uma regressão de conversões semanais sobre investimento semanal, nenhuma
região desligada, nenhuma conversão abdicada, uma resposta para todos os canais ao mesmo tempo.
Ajustado aqui na mesma conta e recebendo **o carryover e a saturação do próprio gerador** — um favor
que nenhum modelo real recebe.

- **O painel decide a resposta antes de a modelagem começar.** As cinco séries de investimento
  correlacionam entre 0,8305 e 0,8789, porque um plano de mídia é escrito como participações de um
  orçamento e os canais se movem quando o orçamento se move. A inflação de variância vai de 5,7315 a
  8,5249, o que multiplica todo erro-padrão por 2,39 a 2,92. O número de condição do desenho
  centrado é **7,01** — confortavelmente dentro da linha de alerta convencional, e é por isso que o
  alarme que não toca não é evidência.
- **Com os transformes certos, ele resolve um canal em cinco.** R-quadrado 0,8364 e desvio-padrão
  residual de 8,718 contra um ruído de gerador de 9,0: o ajuste recuperou o piso de ruído. Os cinco
  intervalos contêm a verdade, um exclui o zero, e nos três canais que funcionam o intervalo é
  **1,64, 5,38 e 14,10 vezes** o retorno que está estimando.
- **A faixa de coeficientes que ajusta igualmente bem *é* o intervalo de confiança.** O perfil tem
  forma fechada — o mais longe que um coeficiente vai enquanto a soma de quadrados dos resíduos sobe
  δ é seu erro-padrão reescalado — de modo que o intervalo de 95% é exatamente o conjunto de valores
  que custa **0,0068 de R-quadrado**. Não há um segundo diagnóstico escondido atrás do erro-padrão.
- **Um dos dois transformes não observáveis é recuperável e o outro não é.** Oito de vinte desenhos
  ajustam dentro de 0,01 do melhor, implicando retornos de **1,18× a 1,54×** a verdade. Mas o ajuste
  identifica o carryover: movê-lo de 0,45 para 0,60 custa 0,0047 de R-quadrado e move o retorno em um
  quarto, enquanto no carryover certo toda a faixa de saturação de 0,5 a 10,0 — vinte vezes — fica
  dentro de 0,0008 do melhor ajuste e move o retorno em **um por cento**.
- **Tire a tendência e a sazonalidade e dois dos três canais que funcionam voltam negativos.** O
  R-quadrado cai de 0,8364 para **0,2371**, busca-generica volta a −2,10× sua verdade e email a
  −5,18×, e social-pago vem confiantemente a 1,85× — confiantemente, porque aquele intervalo ainda
  exclui o zero. **Todo intervalo ainda cobre a verdade.** Cobertura não pega um modelo que erra o
  sinal da maior parte de uma conta; intervalos tão largos cobrem quase qualquer coisa.
- **Contra o holdout, por unidade da quantidade que cada um estima, o modelo é 11,5 a 13,1 vezes mais
  largo.** O holdout resolveu três canais em cinco e custou 260 região-semanas por canal; o modelo
  resolveu um e não custou nada. Isso é uma troca, não um veredito — e só um dos dois instrumentos
  costuma ser apresentado com sua largura em anexo.

## E a forma honesta de usar os dois deixa o modelo tão certo quanto o experimento, exatamente

Sobra uma escolha que ninguém quer: o holdout é estreito, caro e cobre três canais; o modelo é
gratuito, cobre cinco e é treze vezes mais largo. A construção que recusa a escolha é usar os dois —
a estimativa do experimento entra no modelo como priori sobre o coeficiente. Funciona, e o que ela
traz junto com a precisão é o assunto da onda.

- **Os dois instrumentos não estimam a mesma quantidade, e a ponte entre eles é um parâmetro que os
  dados não resolvem.** Um holdout mede o retorno médio no período; um coeficiente é o retorno
  marginal no investimento atual. Para uma resposta que dobra, a razão é exatamente **1 + 1/k** no
  ponto de saturação — 1,7692307692 no 1,30 do gerador, que é a razão entre as duas colunas de
  retorno declaradas do próprio gerador com doze dígitos, vinda de código que não compartilha nada
  com a fórmula. Na faixa de saturação que a onda 5 mostrou que o ajuste não distingue, esse fator vai
  de **3,0 a 1,1**.
- **Funciona: três canais em cinco resolvidos em vez de um, doze a treze vezes mais estreitos.** E as
  médias da posteriori caem a menos de meio por cento das prioris, então a contribuição do próprio
  modelo para esses três canais arredonda para nada. O ajuste dentro da amostra se move **0,000374**
  de R-quadrado, e é por isso que ajuste não julga uma calibração em nenhuma direção.
- **E ela abriu mão de um intervalo que cobria.** Cinco de cinco intervalos cobriam a verdade antes,
  quatro de cinco depois. Nada foi fabricado: um intervalo de 95% erra uma vez em vinte, a onda 1
  calculou cinco, e o de social-pago é o tal. O intervalo do próprio modelo **cobria** a verdade e foi
  derrubado mesmo assim, carregando **0,55%** do peso. Calibração não é uma forma de acertar mais
  vezes que o experimento — é uma forma de acertar tanto quanto ele, barato, e de errar exatamente
  tanto.
- **Pule a conversão de unidade e a mesma maquinaria fabrica uma resposta errada e confiante.** Uma
  divisão de fora: quatro canais resolvidos em vez de três, **um intervalo em cinco cobrindo a
  verdade**, toda estimativa inflada por cerca do fator que ficou de fora, e busca-marca — efeito
  verdadeiro exatamente zero — com um intervalo que exclui o zero *por baixo*. Precisão e viés se
  transferem com a mesma eficiência.
- **Um resultado nulo era a coisa mais precisa que alguém sabia sobre os dois canais que ele "não
  conseguiu resolver".** Usados como prioris, retargeting e busca-marca mantêm **7,0% e 9,1%** de sua
  largura, os dois intervalos cobrem a verdade de zero, e nenhum é falsamente resolvido. O resultado
  inconclusivo nunca foi uma ausência; era uma estimativa com erro-padrão onze a catorze vezes mais
  estreito que o do modelo.
- **E uma priori sobre um canal não é uma afirmação sobre um canal.** Um experimento, só em
  social-pago: o retorno reportado de email se move **1,76×** e o de retargeting **2,33×** — enquanto
  toda largura ao lado se move menos de cinco por cento. A transferência chega como um deslocamento
  de posição que nada no gráfico marca.
- **E então tudo isso se apoia no parâmetro que o ajuste não vê.** Repita a transferência em quatro
  pontos de saturação que se distinguem por **0,000754** de R-quadrado e a resposta calibrada vai de
  **0,64× a 1,72×** a verdade. O ponto de melhor ajuste não é o verdadeiro: é k = 3,0, devolvendo
  1,42× a verdade. Um praticante que escolhe o ponto de saturação pelo ajuste — a única forma de
  escolher — aterrissa ali.

## Módulos

| Módulo | O que decide |
| --- | --- |
| [`mktlab.attribution`](src/mktlab/attribution/README.md) | Quem leva o crédito sob seis modelos, o que um holdout geográfico diz em vez disso, e a diferença entre o ROAS e sua versão incremental. |
| [`mktlab.design`](src/mktlab/design/README.md) | Se o teste vale ser rodado, se está sendo lido do jeito para o qual foi dimensionado, e o que o plano de leitura deveria dizer. Três documentos: [dimensionamento](src/mktlab/design/README-sizing.md) — a precisão que ele terá, o menor **retorno** que consegue estabelecer, quanto custa se o canal funcionar, e o que um resultado nulo já descartou; [leituras repetidas](src/mktlab/design/README-sequential.md) — o que uma olhada semanal faz com a taxa de erro, quanto custam as duas fronteiras honestas, e quanto uma parada antecipada infla o número que você reporta; e [monitoramento](src/mktlab/design/README-monitoring.md) — um cronograma de gasto de alfa para olhadas que ninguém combinou antes, e uma fronteira de futilidade que encerra um teste que não vai dar em nada. |
| [`mktlab.mmm`](src/mktlab/mmm/README.md) | O que uma regressão de conversões sobre investimento consegue sustentar quando ninguém aceita desligar uma região: se o plano de investimento permite alguma resposta, quanto da resposta veio dos transformes que foram adivinhados, e como a largura se compara com o experimento que ele substitui. |
| [`mktlab.calibration`](src/mktlab/calibration/README.md) | Se o experimento já rodado consegue tornar o modelo utilizável, o que a transferência traz junto com a precisão, e o que ainda tem de ser suposto para mover uma resposta de um instrumento para o outro. |

Todo README de módulo é bilíngue e traz uma seção **Premissas e limitações**, porque uma cifra sem
suas premissas não é um resultado.

## Exemplos

| Exemplo | O que mostra |
| --- | --- |
| [`examples/01_who_gets_the_credit.py`](examples/01_who_gets_the_credit.py) | Seis modelos de atribuição sobre uma mesma base de jornadas, a identidade de Shapley, as conversões que ninguém tocou, e o holdout que derruba os seis. |
| [`examples/02_the_test_nobody_sized.py`](examples/02_the_test_nobody_sized.py) | O mesmo holdout, precificado antes de rodar: sua precisão, quais canais ele sempre iria resolver, o retorno que ele nunca conseguiria estabelecer, e quanto custou. |
| [`examples/03_the_test_read_every_monday.py`](examples/03_the_test_read_every_monday.py) | O mesmo holdout outra vez, lido semanalmente em vez de uma só vez: a taxa de erro que isso custa, as duas fronteiras que corrigem, quanto custam em regiões, e a estimativa lisonjeira que nenhuma das duas corrige. |
| [`examples/04_the_plan_nobody_wrote.py`](examples/04_the_plan_nobody_wrote.py) | O plano de monitoramento com o qual o holdout deveria ter chegado: a mesma taxa de erro gasta em quatro calendários de leitura diferentes, a fronteira de futilidade escrita semana a semana, e quanto custa o direito de desistir. |
| [`examples/05_the_model_that_replaces_the_experiment.py`](examples/05_the_model_that_replaces_the_experiment.py) | O modelo construído quando o holdout é recusado, na mesma conta e recebendo os transformes do próprio gerador: o que o plano de investimento já decidiu, o único canal que ele resolve, a faixa que ajusta igualmente bem, e o que a má especificação que todo modelo real tem faz com os sinais. |
| [`examples/06_the_experiment_the_model_believes.py`](examples/06_the_experiment_the_model_believes.py) | O holdout colocado no modelo como priori: a conversão de unidade entre os dois instrumentos, o que uma conversão pulada compra, o erro do próprio experimento depois que o modelo acredita nele, e o que uma priori faz com os quatro canais que ninguém mediu. |

## Instalar e rodar

```bash
python -m pip install -e ".[dev]"
make check       # lint, tipos e a suíte rápida - o que libera um push
make check-all   # o acima mais toda cifra documentada re-derivada
python examples/01_who_gets_the_credit.py
python examples/02_the_test_nobody_sized.py
python examples/03_the_test_read_every_monday.py
python examples/04_the_plan_nobody_wrote.py
python examples/05_the_model_that_replaces_the_experiment.py
python examples/06_the_experiment_the_model_believes.py
```

## Como as afirmações são mantidas honestas

**377 testes, 100% de cobertura de linhas e de ramos.** 306 deles rodam em segundos e liberam cada
push. Os 71 restantes re-derivam, a partir do gerador, toda cifra citada em todo README deste
repositório, e rodam todo script de exemplo. Uma mudança que mova um número publicado quebra o build
em vez de deixar o texto silenciosamente errado.

Três disciplinas, cada uma adotada depois de ter pegado algo:

1. **Verificação contra formas fechadas e casos de controle, nunca contra a saída do próprio
   código.** Os modelos de atribuição são conferidos contra alocações resolvidas no papel como
   frações exatas; o estimador geográfico contra um painel sem ruído cuja diferença em diferenças é
   exatamente +0,04, com uma tendência comum e uma diferença permanente entre regiões adicionadas
   para confirmar que nenhuma das duas chega à estimativa; as taxas médias do gerador contra a
   expectativa analítica para a qual elas fecham; a função de poder contra seu próprio caso de
   controle, em que um lift exatamente zero tem de devolver alfa com doze casas decimais; o
   erro-padrão previsto contra os cinco painéis efetivamente simulados; e a recursão de leituras
   repetidas contra uma única olhada reduzindo-se ao teste de amostra fixa, contra sua própria
   convergência com 100, 300 e 600 nós de quadratura, contra as fronteiras clássicas publicadas, e
   contra uma simulação de quatro milhões de sorteios.
2. **Cifras são asseridas, não citadas.** Inclusive as que o repositório faz sobre si mesmo: a
   contagem de testes acima, a tabela de módulos correspondendo ao pacote, as duas edições de idioma
   existindo, e todo exemplo estando linkado de algum lugar. E inclusive a afirmação que torna o
   resto possível: **todo sorteio do gerador é uma transformada inversa do stream uniforme, nunca um
   amostrador por rejeição**, de modo que a posição no stream depende de quantos valores são pedidos
   e não de qual versão de biblioteca responde. Essa regra é verificada contra o código-fonte,
   porque a primeira versão deste repositório publicou cifras que valiam numa máquina e mudavam numa
   instalação limpa.
3. **Conectar os módulos encontra defeitos que escrever mais módulos não encontra.** Dezenove dos vinte e um
   defeitos registrados até aqui foram achados escrevendo um exemplo, um caso de controle ou uma
   frase — não lendo código. As duas exceções foram um relatório de cobertura mostrando um ramo que
   nenhum teste alcançava, e uma instalação limpa que não reproduziu as cifras publicadas. Eles estão registrados na documentação do módulo em vez de corrigidos em silêncio — a
   função de retorno um dia multiplicou a *participação* de um canal pelo total de conversões, o que
   espalha as conversões sem toque entre os canais e é precisamente o erro que o módulo existe para
   denunciar.

Ver [`docs/ROADMAP.md`](docs/ROADMAP.md) para o que está construído, o que está deliberadamente
ausente, e o que continua aberto.

## Licença

MIT. Ver [`LICENSE`](LICENSE).
