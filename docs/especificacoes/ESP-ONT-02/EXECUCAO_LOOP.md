# Execução da ESP-ONT-02 em sessão autônoma (loop)

Roteiro para uma sessão que implementa a especificação `docs/especificacoes/ESP-ONT-02/especificacao.pdf`
(fonte: `especificacao.tex`) em iterações curtas, até estabilizar. Ler antes de cada iteração.

A referência de aceite é o relatório de visão RT-VIS-03 (`docs/relatorios/visao/hrai-go-visao.pdf`): ele descreve a
plataforma pronta, e o checklist do apêndice A (V-01 a V-31) é o critério de "pronto". Este roteiro leva até o fim
do *bootstrap*; a plataforma só está pronta quando todos os V-xx estiverem marcados com evidência.

## Objetivo do trabalho (ler primeiro)

Todo o desenvolvimento serve a um fim. Ao terminar o *bootstrap*, a plataforma, usada sobre o próprio corpus, deve
responder, ainda que de forma inicial, às três perguntas norteadoras (ESP-ONT-02, Introdução; RT-VIS-03, cap. 2):

1. **QN1 (âncora):** quais as especificidades do Brasil em relação às demais jurisdições analisadas que devem nortear
   um modelo de governança de IA com foco estratégico para o Brasil como nação, e não apenas uma proposta regulatória
   baseada em princípios e valores afins?
2. **QN2:** o que está sendo considerado e não deveria?
3. **QN3:** o que não está sendo considerado e deveria?

A QN2 e a QN3 são respondidas **à luz da QN1**. Todo item delas cita a especificidade brasileira em que se apoia. Uma
divergência em relação ao AI Act, sozinha, não é achado. Antes de implementar um item, confira a qual pergunta ele
serve. Se ele não servir a nenhuma, pergunte antes de seguir.

## Leitura obrigatória antes da 1ª iteração

1. `docs/relatorios/visao/hrai-go-visao.pdf` (RT-VIS-03): estado-alvo, método M1–M10 e checklist V-01 a V-31.
   Cada item da tabela abaixo indica os V-xx que fecha.
2. `docs/especificacoes/ESP-ONT-02/especificacao.pdf`: requisitos RF-01 a RF-18 e RNF-01/02 (capítulo de especificação de implementação).
3. `docs/relatorios/ontologia/relatorio.pdf` (RT-ONT-01): motor de raciocínio e resultados de base.
4. `ontologies/regulatory/README.md` e `ontologies/scse/`: as duas ontologias que serão separadas (RF-17).
5. `scripts/ontologia/raciocinar.py`, `experimentos.py`, `afirmacoes.py`: ferramentas já prontas.

## Ordem de execução (dependências)

| Ordem | Requisito | Depende de | Fecha | Autônomo? |
|---|---|---|---|---|
| 1 | RF-15 slide da apresentação + selo "sem lastro" nas fichas (início do RF-12) | — | — | sim |
| 2 | RF-17 separar núcleo e SCSE (SCSE importa o núcleo; classes de deliberação migram com equivalência) | — | V-04 | sim |
| 3 | RF-03 TBox v1.2.0 + regras R24–R30 + testes das invariantes I-1 a I-4 + tempo de raciocínio medido no CI (RNF-02) | 2 | V-05, V-13 | sim |
| 4 | RF-16 (formalização) módulo comparativo: 25 critérios de Alanoca et al. + E1–E7, `CriterionCoding` | 3 | V-06 | sim, **exceto as escalas da E4** (ver abaixo) |
| 5 | RF-05 esquema `SubstantiveArea` (28 áreas + IA generativa/GPAI) | 4 | — | sim |
| 6 | RF-13 tensões, estratos, assentos e cenários na SCSE com ligação ao núcleo | 2 | V-16 | sim |
| 7 | RF-08 consultas SPARQL PC1–PC9 versionadas + teste de regressão no CI (PC9 = QN1) | 3–6 | V-12 | sim |
| 8 | RF-09 + RF-12 build gera `web/assets/modelo.js` do grafo; contador "sem lastro" no CI, com meta zero; fichas "por quê?" em todos os elementos da câmara, até a captura da fonte | 5–7 | V-14, V-15, V-19 | sim |
| 9 | RF-01 texto aprovado pelo Senado (dez/2024) como nova versão do PL: arquivo já no corpus (`docs/ai-regulations/br/PL2338-2023_texto-aprovado-Senado-2024_Camara-20250317.pdf`) | — | V-02 | sim (extração); aprovação humana |
| 10 | RF-11 teses externas como `PolicyClaim` com estado recalculado a cada versão do corpus; reavaliar a tese C04 contra o texto do Senado | 9 | V-17 | sim (cálculo); aprovação humana |
| 11 | RF-04 / RF-06 / RF-16 (codificação) / RF-14 instâncias UE, Reino Unido, EUA; correspondências; codificações | 9 | V-08 a V-10 | extração sim, **aprovação não** |
| 12 | RF-07 indicadores de capacidade e exposição com fonte e ano-base, os mesmos para todas as jurisdições | 11 | V-11 | extração sim, **aprovação não** |
| 13 | M10 monitoramento: `RegulatoryChangeEvent`, R10–R13, fila do que foi reaberto, codificações e especificidades marcadas para refazer (PC7) | 3, 9 | V-23 | sim |
| 14 | RF-10 Mesa grava posições sobre afirmações; protocolo de cinco rodadas com posição cega antes do conselho; registro de decisão; relatório com as quatro métricas | 6 | V-20 a V-22 | sim (ensaio e decisão são humanos) |
| 15 | Interfaces do RT-VIS-03 cap. 7: celular participante (Minhas escolhas, Mesa, Agora; alvos ≥ 44 px; identificação opcional), comparador, base de conhecimento, limites declarados na interface | 7, 8, 14 | V-18, V-25, V-31 | sim |
| 16 | RF-18 (a) especificidades do Brasil frente às demais jurisdições, passo M5 do RT-VIS-03 (ver seção abaixo) | 4, 5, 7, 11, 12 | V-27, V-30 | geração sim, **aceite não** |
| 17 | RF-18 (b) `NationalSpecificity` + `groundedInSpecificity`; relatório das perguntas norteadoras (QN1 → QN2 → QN3) gerado no build | 7, 16 | V-26, V-28, V-29 | geração sim, **publicação não** (decisão humana por item) |

## Como as diferenciações do Brasil são produzidas (item 16, passo M5)

Este é o passo que responde à QN1. Uma especificidade é uma diferença do Brasil em relação às demais jurisdições
do corpus que se explica pelo contexto nacional. Não é qualquer diferença, e não é divergência em relação ao AI Act.

1. **Mesma régua para todas as jurisdições.** Brasil, UE, Reino Unido, EUA e as jurisdições decididas no RF-02 são
   codificados pelos mesmos 25 critérios e E1–E7, na mesma matriz de áreas (E3) e pelos mesmos indicadores, com fonte
   e ano-base. Critério sem codificação aparece como *não codificado*, nunca como "não tem".
2. **Detectar diferenças.** Uma consulta versionada compara o Brasil com cada jurisdição e com o conjunto e classifica
   cada diferença em um de quatro tipos: *exclusiva do Brasil* (sem par), *ausente no Brasil*, *de intensidade*
   (valor diferente na escala E4 ou força jurídica diferente, E1) e *de contexto* (indicador de capacidade ou de
   exposição). Só se compara o comparável: mesmo tipo de instrumento (E1) ou tipo declarado ao lado; ausência só
   vale dentro do escopo do `CoverageAssessment` da jurisdição.
3. **Explicar pelo contexto nacional.** A diferença vira `NationalSpecificity` candidata só quando ligada a pelo
   menos uma das quatro dimensões da QN1 (contexto nacional, capacidades instaladas, exposições a risco, objetivos
   estratégicos), com evidência: dispositivo, indicador com fonte e ano-base, ou objetivo do PBIA. A ficha registra a
   dimensão, o tipo de diferença, a evidência brasileira, o valor de cada uma das demais jurisdições com a fonte, o
   escopo e o estado. Diferença sem explicação fica registrada como diferença, não como especificidade.
4. **Revisar e usar.** Agentes e Shadow Council propõem e contestam; só `ReviewDecision` humana aceita. As aceitas
   são o critério da QN2 e da QN3 (`groundedInSpecificity`). Nova versão ou nova jurisdição recalcula as afetadas
   (item 13).

Aceite: PC9 responde; especificidades sem dimensão, sem tipo, sem evidência ou sem o valor das demais jurisdições = 0.
Enquanto os indicadores do item 12 não forem aprovados, a evidência de contexto fica como "sem indicador" e a
especificidade se apoia em dispositivo ou objetivo do PBIA; isso permite fechar o item 16 sem decisão pendente.

## Protocolo de cada iteração

1. Escolher o próximo item não concluído da tabela, respeitando dependências.
2. Implementar o menor incremento verificável.
3. Rodar sempre:
   - `python3 tests/verify_regulatory_ontology.py`
   - `python3 tests/verify_regulatory_instances.py`
   - `python3 scripts/ontologia/experimentos.py`
   - `python3 scripts/ontologia/afirmacoes.py`
   - os testes novos do próprio item.
4. Conferir o critério de aceite do requisito na tabela da seção 8 da especificação **e** a verificação dos V-xx que
   o item fecha (coluna "Fecha"; RT-VIS-03, apêndice A). Só marcar como concluído se os dois passarem.
5. Registrar o resultado em `docs/especificacoes/ESP-ONT-02/PROGRESSO.md` (criar na 1ª iteração, com as seções
   "Concluído", "Aguardando decisão" e "Checklist V-01 a V-31"): item, o que mudou, comandos rodados com saída
   resumida, evidência de cada V-xx (link do CI, captura de tela ou commit) e o que ficou pendente.
6. Commit pequeno, com mensagem descrevendo o requisito (ex.: `RF-17: SCSE importa o núcleo`).

## Invariantes (violação = parar e reportar)

- I-1: nenhuma regra afirma `hasLegalStatus`, `assessmentHasStatus`, `releasePublishesCandidate` ou decisão humana.
- I-4: sintético nunca é contado como humano (disjunção na TBox, regra R21; cor e rótulo distintos na interface).
- Cenários (`ontologies/regulatory/cenarios/`) e afirmações (`ontologies/regulatory/afirmacoes/`) nunca vão para `instances/`.
- Todo conteúdo extraído entra como `CandidateAssertion`. **A sessão nunca cria `ApprovalDecision` nem `ReviewDecision`**: aprovação é humana.
- Nenhuma jurisdição exibida sem `SourceSnapshot` com SHA-256.
- O contador de elementos "sem lastro" nunca sobe em relação ao `main`; a meta final é zero (V-15).
- Participação humana anônima por padrão: apelido e avatar vêm do identificador anônimo. A identificação é opcional,
  a qualquer momento e reversível, e nunca muda apelido nem avatar (V-31).
- Uma diferença em relação a outra jurisdição só vira especificidade com dimensão da QN1 e evidência (item 16).
- Taxonomia de Alanoca et al.: definições originais intactas; extensões apenas como E1–E7, com crédito e DOI.

## Decisões humanas: a sessão prepara, não decide

- **RF-02, China:** incluir fontes primárias ou retirar da comparação.
- **E4, escalas:** propor escala para cada um dos 25 critérios com exemplos de codificação e deixar para aprovação.
- **Revisão das extrações** (F2): dispositivos, correspondências BR↔UE, codificações, indicadores.
- **Alinhamento A1** dos 5 componentes "próximos" e das teses do anexo.

A sessão deve abrir esses itens em `PROGRESSO.md`, numa seção "Aguardando decisão", e seguir com o que não depende deles.

## Bloqueios conhecidos

- ~~**Texto do Senado (RF-01)**~~ resolvido em 17/11/2026: inteiro teor da Câmara (codteor 2868197, texto aprovado pelo Senado em 10/12/2024, 80 artigos, SHA-256 `82e264056ab6622a58ce7cbb66e02d0c79c5d85ff76639841421ca415892c8ca`). Em 17/11/2026 a Câmara não tem parecer nem substitutivo; reconsultar a ficha de tramitação antes de cada release e, se surgir substitutivo, incorporá-lo como nova versão.
- **PDF da "Análise Comparativa":** não está no repositório. As teses vieram de resumo do usuário.
- **IRIs resolvíveis (RNF-01):** depende de decisão sobre domínio (w3id.org ou GitHub Pages).

## Critério de parada (plataforma estabilizada)

A sessão encerra o loop quando:
1. os itens 1–8, 10 e 13–17 estão concluídos com critério de aceite verde, até onde não dependem de decisão humana;
2. CI verde com consultas PC1–PC9 respondendo e contador "sem lastro" publicado;
3. o relatório das perguntas norteadoras foi gerado pela plataforma, com a resposta inicial à QN1 e, à luz dela, à QN2 e à QN3, e está na fila "Aguardando decisão" para revisão humana;
4. os itens 9, 11 e 12 estão implementados até onde não dependem de decisão humana, com a fila "Aguardando decisão" atualizada;
5. `PROGRESSO.md` lista o estado de cada V-01 a V-31.

Parar o loop é o fim do *bootstrap*, não o aceite. A plataforma está pronta quando todos os V-xx do RT-VIS-03 estiverem
marcados com evidência, o que inclui as decisões humanas (escalas da E4, revisões, ensaio da sessão ao vivo).

Também deve parar e pedir orientação se o mesmo item falhar em três iterações seguidas.
