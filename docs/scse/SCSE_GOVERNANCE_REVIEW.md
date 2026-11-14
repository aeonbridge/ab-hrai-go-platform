# SCSE v2: o conselho questiona o modelo de governança de IA

Modo `governanceReview`. O conselho examina um **modelo de governança nacional de IA** diante do país em uma **data**, e produz propostas de revisão que **pessoas** aceitam, modificam, rejeitam ou adiam. O modelo só muda por decisão humana, e cada mudança fica no histórico do próprio modelo.

> O conselho é sintético. Suas propostas são hipóteses fundamentadas em fontes declaradas, não achados, não parecer jurídico e não opinião pública.

## Relação com a versão inicial (v1)

A v1 continua intacta e funcionando: runtime multi-provedor, modos `regulatoryPolicy` e `solutionCompliance`, cenários `BR-PBIA-001..005`, experimento `provider-practice` e a apresentação. Ela está nos commits `b6ac950` (runtime) e `29e4e83` (OpenRouter e pesos por estrato).

A v2 é aditiva: reaproveita provedores, OpenRouter, composição do conselho, registro de eventos e relatórios, e acrescenta um modo novo com motor, prompts, contratos e ciclo de revisão próprios (`governance.py`, `governance_engine.py`, `gov_prompts.py`).

## O ciclo

```
modelo v0.1.0 ─┐
contexto do país na data ─┼─▶ conselho (R1..R7, réplicas) ─▶ pacote de revisão ─▶ folha de revisão
tensões iniciais ─┘                                                                      │
                                                                                         ▼
modelo v0.2.0 ◀── scse govern apply ◀── DECISÕES HUMANAS (nome do revisor, justificativa) ┘
     │
     └─▶ nova rodada sobre v0.2.0 ─▶ scse govern compare (o que persiste, o que sumiu, o que é novo)
```

## As três perguntas (lentes)

| Lente | Pergunta | O que o achado precisa ter |
|---|---|---|
| `omission` (Q1) | O que deveria estar sendo considerado e não está | `topic` da taxonomia (ou `other` com título), `change` = `add` (ou `modify` se a cobertura é parcial), por que importa **nesta data**, fontes |
| `excess` (Q2) | O que está sendo considerado e não deveria | `componentId` existente, `change` = `remove` ou `modify`, o risco de manter |
| `advantage` (Q3) | Que especificidades do contexto deveriam orientar o desenho para uma vantagem competitiva distintiva | `contextFeatureIds` (CF-xx), o desenho proposto, por que é **distintiva** (difícil de copiar) e o custo |

O motor rejeita, em código, achado que não cumpre esses requisitos, e registra o motivo no log de eventos. Um verificador de outro provedor marca cada achado como `specific` ou `generic`: recomendação que serviria a qualquer país não conta como vantagem distintiva.

## Rodadas

| Rodada | Nome | O que acontece |
|---|---|---|
| R0 | Prepare | Valida o contrato, carrega modelo, taxonomia e **contexto vigente na data** (falha fechada se não há), congela tudo com hash |
| R1 | BlindExpectations | Cada assento lista o que um modelo nacional **deve** considerar, **sem ver o modelo**. Privado |
| (código) | Agregação | Expectativas viram uma matriz de cobertura: tópico esperado × componentes que o cobrem |
| R2 | ModelReview | O modelo é revelado. Achados nas três lentes, com a matriz e as expectativas agregadas (anônimas) à vista |
| R3 | CrossExamination | Contestar, apoiar, pedir evidência |
| R4 | EvidenceRevision | Manter, revisar ou retirar |
| R5 | ChangeProposals | Mudanças concretas: `add`, `modify`, `remove` ou `keep`, com redação |
| R6 | ContextStress | Cada achado sobrevive aos ramos de contexto? (PL aprovado, PL parado, corte do PBIA, novo governo) |
| R7 | MinorityAndAudit | Dissenso preservado, fundamentação auditada, genericidade verificada |

**Por que a R1 é cega.** Um modelo de linguagem que vê o modelo antes de opinar tende a criticar dentro da moldura dele e a achar menos omissões. Pedir as expectativas antes e cruzá-las com o modelo em código mede a lacuna sem essa ancoragem.

## Entradas

| Arquivo | Papel |
|---|---|
| `scenarios/governanca-brasil/model/brasil-governanca-v0.json` | O modelo em exame: 22 componentes (EBIA, PBIA, LGPD, PL 2338 e seus mecanismos, instituições, recursos), cada um com tipo, status legal, tópicos, fontes e `verification` |
| `scenarios/governanca-brasil/taxonomy.json` | 28 áreas de governança. Define o que "omissão" pode ser. Revisável por humanos |
| `scenarios/governanca-brasil/context/2026-11-14.json` | O Brasil na data: fatos (CTX), 14 traços de contexto (CF), evidências e perspectivas sem fonte. Um diretório de snapshots datados serve a várias datas |
| `scenarios/governanca-brasil/GOV-BR-001.json` | Cenário: pergunta, lentes, as tensões T1 a T6 como sementes, ramos de contexto |
| `scenarios/brasil-ficticio/world.json` | Os 8 estratos e 20 assentos, com posições documentadas |

As tensões iniciais são **sementes**: o conselho confirma, refuta ou reformula. O relatório mostra quantos achados e quantos assentos (na R1) citaram cada uma.

## Saídas por execução

`report.json` (seção `governanceReview`), `revision-packet.json`, `coverage-matrix.json`, `review-sheet.md`, mais os artefatos de sempre (manifesto, registro de eventos encadeado por hash, snapshot). Por cenário, com as réplicas consolidadas: `merged-packet.json`, `review-sheet.md` e `decisions.template.json`.

**Matriz de cobertura** (calculada em código): para cada tópico, quantos assentos o esperavam e como o modelo o cobre: `documentedInForce`, `documentedProposedOnly`, `inferredOnly` ou `none`. **Lacuna** = esperado e sem cobertura. **Frágil** = coberto só por projeto de lei ou só por tópicos que são leitura do autor do modelo.

## Sem falso consenso: a posição de cada estrato

O conselho **não delibera uma resposta única**. Uma proposta é levantada por um assento e cada estrato reage a ela, ou não. O pacote de revisão mostra essas reações lado a lado, sem somá-las num veredito.

Cada proposta traz `stratumPositions`, uma linha para cada estrato do *world pack* (os 8, inclusive os que não disseram nada):

| Posição | Quando |
|---|---|
| `for` (a favor) | todos os assentos do estrato que se pronunciaram são autores ou apoiadores |
| `against` (contra) | todos contestaram |
| `amend` (propõe ajuste) | todos propuseram emenda |
| `split` (dividido) | os assentos do estrato divergem entre si |
| `silent` (sem posição) | nenhum assento do estrato se pronunciou. **Não significa concordância** |
| `notSeated` (sem assento) | o estrato não teve assento nesta execução |

A posição de um assento é a última que ele tomou na rodada. Cada linha guarda os argumentos no texto original (`statements`: autoria, apoio, contestação, emenda, opinião minoritária), com rodada, modelo e a marca `onEarlierVersion` quando o argumento se referia a uma versão anterior da tese, revisada na R4. O apoio agora registra a justificativa de quem apoiou (`supportNotes`), que antes se perdia.

`positionSpread` resume quem está em cada posição, se a proposta foi contestada e se só o estrato autor se pronunciou.

O pacote também traz `strataPerspectives`, a leitura de cada estrato sobre a rodada inteira: o que esperava às cegas na R1, o que levantou, o que apoiou, contestou ou quis ajustar, onde ficou sozinho (`aloneFor`, `aloneAgainst`) e suas opiniões minoritárias. Não há síntese entre estratos.

No merge de réplicas, achados com a mesma chave numa réplica têm as posições somadas por assento. Um estrato só mantém a posição se a teve em todas as réplicas em que a proposta apareceu; senão fica `variesAcrossReplicates`, com a posição de cada réplica em `byReplicate`. Posição instável entre réplicas é sinal de que ela depende do sorteio de modelo e ordem de fala, não do estrato.

A folha de revisão abre com a seção **Cada estrato, sua leitura** e mostra, em cada proposta, uma tabela estrato × posição × argumento.

### Mural de tensões

`docs/scse/prototipo/mural-de-tensoes.html` lê um `revision-packet.json` ou `merged-packet.json` (botão "Carregar pacote") e organiza as propostas por tensão semeada (T1 a T6), mais um mural "Fora das tensões iniciais" para propostas sem tensão.

- **Galeria:** cada tensão é um post. As reações somam as posições dos estratos sobre as propostas da tensão. Um mapa de calor em miniatura e um resumo acompanham o post.
- **Mural da tensão:** mapa de calor estrato × proposta (toque na célula para ler o argumento), barras por estrato, visão **Conversa** (cada proposta como post, argumentos como comentários) e visão **Quadro** (colunas a favor, ajuste, dividido, contra e sem posição).
- **Cards humanos:** quem tem acesso de contribuidor acrescenta um card com posição, proposta e argumento. Os cards ficam no armazenamento compartilhado da página, ligados ao `packetId`.
- **Facilitador:** sob pedido, um modelo lê posições, argumentos e cards e devolve panorama, leitura por estrato, convergências explícitas (com os estratos que as sustentam), disputas com os dois lados, silêncios e perguntas para quem decide. O prompt proíbe veredito e consenso inventado. O resumo fica salvo e é marcado como desatualizado quando entram cards novos.

O mural não grava decisões. Decisão continua em `scse govern apply`.

## Revisão humana

```bash
# 1. rodar o conselho (offline para ensaiar; sem --dry-run usa os modelos reais)
scse run scenarios/governanca-brasil/GOV-BR-001.json --critic --seats 8 --replicates 3

# 2. gerar a folha e o modelo de decisões (se não vieram da execução)
scse govern sheet <dir-da-execução> --model scenarios/governanca-brasil/model/brasil-governanca-v0.json --out revisao/

# 3. pessoas leem revisao/review-sheet.md e preenchem revisao/decisions.template.json

# 4. aplicar as decisões e gravar a próxima versão
scse govern apply --model scenarios/governanca-brasil/model/brasil-governanca-v0.json \
  --packet revisao/merged-packet.json --decisions revisao/decisions.json \
  --out scenarios/governanca-brasil/model/brasil-governanca-v0.2.json \
  --taxonomy scenarios/governanca-brasil/taxonomy.json

# 5. nova rodada sobre a versão revisada (aponte governance.modelPath do cenário) e comparar
scse govern compare <execução-anterior> <execução-nova>
scse govern diff <modelo-v1> <modelo-v2>
```

Cada decisão tem `decision` (`accept`, `modify`, `reject`, `defer` ou `null` para pendente), `rationale`, `edited` (campos corrigidos) e, quando exigido, `legalReview`.

**Salvaguardas em código (`scse govern apply`)**
- exige pelo menos um **revisor humano nomeado**;
- só aplica o que foi decidido: proposta sem decisão fica pendente, nada é aplicado por padrão;
- justificativa de 20 ou mais caracteres para `accept` e `modify`;
- as decisões têm de referir o mesmo pacote e a mesma versão do modelo;
- remover ou alterar componente **em vigor** (`effective`, `enactedNotEffective`) exige `legalReview {reviewer, note}`;
- remoção move o componente para `retiredComponents`, com motivo, e não apaga;
- `modify` rebaixa o componente para `verification: pending` e `origin: humanAuthored`;
- o histórico (`history`) registra revisores, pacote, execuções, cada mudança e a justificativa.

## Como ler uma proposta

1. **Réplicas.** Proposta presente em 3 de 3 execuções é mais robusta; em 1 de 3 pode ser ruído. É o filtro mais barato que há.
2. **Tabela de estratos.** Leia quem defendeu, quem contestou, quem pediu ajuste e quem ficou calado. Proposta que só o estrato autor defendeu não teve teste. Estrato `split` merece ler os dois argumentos. Apoio de um só provedor sugere viés de modelo.
3. **Apoio não é voto.** Contagem de assentos sintéticos mede procedência do argumento. Não substitui evidência.
4. **Evidência fraca.** Citação fora do pacote foi removida e a tese rebaixada a hipótese.
5. **Genérica.** Achado Q3 que serviria a qualquer país não é vantagem distintiva.
6. **Dissenso.** Posição minoritária fundamentada fica registrada; não é descartada por ser minoria.

## Limites que importam

- **O modelo v0 é uma leitura, não o texto oficial.** Foi montado a partir de fontes secundárias. Três componentes (`GM-10` avaliação de impacto, `GM-11` responsabilização civil, `GM-12` sandbox) **não foram confirmados** nas fontes consultadas e estão marcados `inferred`. Conferir no texto do PL 2338 antes de decidir sobre eles. Um erro aqui contamina a matriz de cobertura.
- **A taxonomia molda as omissões.** Só se acha lacuna em área que ela nomeia (ou que o conselho sugira como `other`). Humanos devem revisá-la.
- **Os traços de contexto (CF-xx) são hipóteses.** Todos estão `pending`. Achados Q3 só valem tanto quanto eles.
- **Expectativas vêm de modelos de linguagem.** A matriz mede concordância entre assentos sintéticos, não necessidade real.
- **Perspectivas sem fonte não foram simuladas:** povos indígenas e comunidades tradicionais, Judiciário, Ministério Público e TCU, Congresso, segurança e defesa, setores regulados, agronegócio. O relatório as lista como ausentes. Para essas, é preciso ouvir pessoas.
- **Transição de governo.** O contexto registra que as eleições de 2026 ocorreram e que o resultado não consta do pacote. O ramo `new-government-priorities` é só um teste de estresse.
- **Rodar de novo não prova nada sozinho.** Em `govern compare`, "resolvida" significa que o conselho deixou de levantar o ponto, não que o problema esteja resolvido.

## Custo

O modelo e o contexto vão em todo turno: o prompt de sistema passa de 7 mil tokens a partir da R2, e uma réplica de 20 assentos consome cerca de 1,7 M de tokens de entrada (estimativa do modo simulado, sem tokens de raciocínio). Três réplicas dão cerca de 5 M. Use `--seats 8` e uma réplica para ensaiar, e `maxCostUsd` e `tokenBudget` do cenário como teto. Cache de prompt não está implementado nos adaptadores e reduziria o custo.

## Experimento

`experiments/scse/governance-sensitivity.toml` compara o conselho estratificado e misto com conselhos de um só provedor, debate sem estratos (B2) e agente único (B1), para medir se o resultado depende de quem opina e se a complexidade do conselho se paga.
