# Progresso da ESP-ONT-02 (loop de execução)

Registro de cada iteração do roteiro `EXECUCAO_LOOP.md`. Referência de aceite: RT-VIS-03, apêndice A (V-01 a V-31).

## Concluído

### Item 1 · RF-15 slide + selo "sem lastro" (início do RF-12) — 17/11/2026

- **O que mudou**
  - `scripts/ontologia/lastro.py`: contador dos sete conjuntos exibidos (`web/assets/modelo.js`). Só conta como lastro o
    `skos:exactMatch` (em `ontologies/regulatory/alinhamentos/`) para um indivíduo que existe no grafo; `closeMatch`
    fica como "próximo, pendente de revisão" e continua sem lastro. Gera `web/assets/lastro.js`, sem data, reprodutível.
  - Câmara (`web/ao-vivo`): selo na ficha de componente, área, estrato, tensão e cadeira vazia (exato, próximo ou sem lastro).
  - Apresentação (`web/apresentacao`): o slide "Por trás da imagem" lê o contador. Com contador > 0 diz "ontologia em
    construção" e quantas peças já são indivíduos; a frase "cada peça é um indivíduo da ontologia" só aparece com zero.
  - CI (`validate-regulatory.yml`): `lastro.py --check --base-ref HEAD~1` falha se `lastro.js` estiver desatualizado ou
    se o contador subir (no total ou em qualquer conjunto).
  - Teste: `tests/test_lastro.py` (4 testes).
- **Comandos**
  - `python3 tests/verify_regulatory_ontology.py` → OK, 1557 triplas, 23 regras SWRL seguras.
  - `python3 tests/verify_regulatory_instances.py` → OK, 1057 triplas.
  - `python3 scripts/ontologia/experimentos.py` → OK.
  - `python3 scripts/ontologia/afirmacoes.py` → 6 com evidência, 4 contestadas, 2 sem evidência.
  - `python3 scripts/ontologia/lastro.py` → 5 com lastro, 83 sem lastro, de 88.
  - `python3 -m pytest -q tests/test_lastro.py` → 4 passed.
- **Medido**: componentes 5/22, áreas 0/28, traços de contexto 0/14, estratos 0/8, tensões 0/6, ramos 0/4, cadeiras vazias 0/6.
- **Pendente**: zerar o contador é o item 8 (RF-09/RF-12); os 5 componentes "próximos" dependem da revisão A1.

### Item 2 · RF-17 separar núcleo e SCSE — 17/11/2026

- **O que mudou**
  - SCSE 1.1.0 com namespace próprio (`.../ontology/scse#`), sem `example.org`, com `owl:imports` do núcleo.
  - Deixou de redeclarar 8 classes e a propriedade `claimText`; passou a usar as do núcleo. Termos homônimos com sentido
    diferente ganharam nome próprio (`provisionStateHasStatus`, `positionGroundedInEvidence`).
  - Classes de deliberação com casa na SCSE e `owl:equivalentClass` para as do núcleo (compatibilidade com instâncias e
    regras R07/R21). Alinhamentos `PolicyTension ⊑ RegulatoryTension`, `ArgumentClaim ⊑ PolicyClaim`, `EvidenceRecord ⊑ Evidence`.
  - `ontologies/scse/README.md` novo; README do núcleo atualizado; CI roda `tests/test_modulos.py` e `tests/test_lastro.py`.
- **Comandos**: os quatro do protocolo com exit 0; `pytest tests/test_modulos.py` → 4 passed. As 8 regras da SCSE que
  disparavam antes disparam igual depois (mesma contagem por regra), agora com o núcleo importado (32 regras no total).
- **Aceite RF-17**: nenhum termo declarado nos dois módulos (teste); testes dos dois módulos passam.

### Item 3 · RF-03 TBox v1.2.0, regras R24–R30, invariantes, tempo no CI — 17/11/2026

- **O que mudou**
  - Núcleo 1.2.0: 14 classes, 34 propriedades de objeto e 5 de dados com comentário em cada uma; vocabulários
    controlados (tipos de correspondência, dimensões da QN1, tipos de diferença). Regras R24a/b/c, R25a/b e R26.
  - SCSE 1.2.0: `DecisionRecord`, revisão de posição, posições sobre alternativas, estrato do stakeholder; R29a/b e R30.
  - `scripts/ontologia/swrl_texto.py`: converte SWRL textual em `swrl:Imp`; `raciocinar.py` ganhou `swrlb:notEqual`.
  - Testes: `tests/verify_regulatory_ontology.py` estendido (29 regras, classes v1.2.0, cabeças proibidas);
    `tests/test_invariantes.py` (regras novas sobre fixture, I-1 a I-4, tempo do grafo completo).
- **Decisões de modelagem**: R27 não existe (sem negação em SWRL); R28 vai para o módulo comparativo no item 4, porque
  combina valores dos critérios; R29–R30 ficam no SCSE (casa da deliberação desde o RF-17).
- **Comandos**: os quatro do protocolo com exit 0; `build_regulatory_instances.py --check` OK; pytest dos módulos,
  lastro e invariantes → 27 passed. Grafo completo (núcleo, SCSE, instâncias, cenários, afirmações, alinhamentos):
  5105 triplas em 0,12 s (RNF-02 < 5 s).
- **Pendente**: R28 (item 4).

### Item 4 · RF-16 (formalização) módulo comparativo — 17/11/2026

- **O que mudou**
  - `ontologies/comparativo/` (novo módulo, importa o núcleo): 12 categorias e 25 critérios de Alanoca et al. com as
    definições originais (copiadas literalmente da seção 5.1; "Scope" a partir das Tabelas 1 a 10), E1 a E7 com crédito
    e DOI, perfil de desenho e regra R28.
  - `alanoca2025-definicoes.json`: definições congeladas; o teste confere cada uma contra o texto do PDF.
  - `scripts/ontologia/build_comparativo.py` gera o módulo (com `--check` no CI).
  - `docs/especificacoes/ESP-ONT-02/escalas-E4-proposta.md`: escala proposta para cada um dos 25 critérios e para as
    extensões, com exemplos tirados do que o paper registra para o Brasil. **Aguarda aprovação (D-02).**
- **Observação**: o paper divide "Existing agency" e "Dedicated new agency" nas tabelas por país; a seção 5.1 trata as
  duas como um critério ("Existing Agency or New Agency"). O módulo segue a seção 5.1, o que dá os 25 critérios.
- **Divergência registrada** para o item 11: C18 (Technical Expertise) está como ausente no paper para o Brasil, mas o
  texto do Senado cria o comitê de especialistas (CECIA); resolver contra o texto primário (tese C04).
- **Comandos**: os quatro do protocolo com exit 0; `pytest tests/test_comparativo.py` → 7 passed; R28 dispara só com
  codificações justificadas e aprovadas (fixture).

### Item 5 · RF-05 esquema `SubstantiveArea` — 17/11/2026

- **O que mudou**
  - `ontologies/comparativo/areas.json` + `build_comparativo.py`: 29 áreas (`hrai:SubstantiveArea` e `skos:Concept`),
    as 28 da cúpula e "IA generativa e modelos de propósito geral". Mapeamento proposto para funções do NIST AI RMF,
    capítulos do AI Act e critérios da taxonomia, marcado como pendente de revisão em cada área.
  - Núcleo: anotação `hrai:displayKey` liga um indivíduo ao elemento exibido (`topics:<id>`); o contador de lastro a usa.
  - Contador: áreas 28/28 com lastro; total 33 com lastro e 55 sem lastro, de 88 (antes 5 e 83).
- **Aceite RF-05**: parcial. As áreas da cúpula têm o mesmo id e rótulo no esquema e em `modelo.js` (teste), mas
  `modelo.js` ainda não é gerado do esquema; a geração é o item 8.
- **Comandos**: protocolo com exit 0; pytest (módulos, lastro, invariantes, comparativo, nomenclatura) → 35 passed.

### Item 6 · RF-13 tensões, estratos, assentos e cenários na SCSE — 17/11/2026

- **O que mudou**
  - `ontologies/scse/conselho/GOV-BR-001.ttl` (fonte nova): 8 estratos, 20 assentos, 6 cadeiras vazias com motivo,
    6 tensões-semente ligadas a afirmações do núcleo (T1→C07; T2→C08, C11, C12; T3→C03; T4→C01, K01, C02;
    T5→C04, C07; T6→C05, K05, K09) e 4 ramos ligados ao PL 2338 ou ao PBIA. Ligações marcadas como proposta.
  - SCSE: propriedades `tensionBetweenStrata` e `branchConcernsInstrument`.
  - `ontologies/consultas/V16_sementes_sem_ligacao.rq`: zero linhas.
  - Contador: 57 com lastro, 31 sem lastro, de 88 (estratos, tensões, ramos e cadeiras vazias completos).
- **Aceite RF-13**: parcial. Cada semente aponta para as afirmações (consulta V-16 = 0). "Câmara e mural leem tensões
  da SCSE" depende de gerar `modelo.js` do grafo (item 8).
- **Comandos**: protocolo com exit 0; pytest → 38 passed.

## Aguardando decisão

| Id | Decisão | Quem | Bloqueia |
|---|---|---|---|
| D-01 | RF-02, China: incluir fontes primárias ou retirar da comparação | autor | V-03, item 11 (parte) |
| D-02 | E4: aprovar as escalas dos 25 critérios; proposta pronta em `escalas-E4-proposta.md` | autor | V-07, codificações (item 11), R28 |
| D-03 | Revisão das extrações (dispositivos, correspondências BR↔UE, codificações, indicadores) e do mapeamento das 29 áreas para NIST, AI Act e critérios (`areas.json`) | revisor humano | V-08 a V-11 |
| D-04 | Alinhamento A1: os 5 componentes "próximos" (GM-15, GM-17, GM-19, GM-20, GM-22) e as teses do anexo; ligações semente→afirmação e ramo→instrumento (`conselho/GOV-BR-001.ttl`) | autor | contador sem lastro |
| D-05 | RNF-01: domínio dos IRIs (w3id.org ou GitHub Pages) | autor | V-24 |
| D-06 | PDF da "Análise Comparativa" no repositório (hoje as teses vêm de resumo) | autor | rastreabilidade das teses |

## Checklist V-01 a V-31

Legenda: ✅ verificado com evidência · 🟡 parcial · ⬜ não iniciado · ⏸ depende de decisão humana.

| Id | Estado | Evidência / observação |
|---|---|---|
| V-01 | 🟡 | nome completo no README e relatórios (`tests/test_nomenclatura.py`); conferir site e `dcterms:title` |
| V-02 | 🟡 | PBIA, PL 2023 e 2024 (SHA-256 no `EXECUCAO_LOOP.md`), UE, RU e EUA no corpus; falta `SourceSnapshot` de cada um no grafo |
| V-03 | ⏸ | D-01 |
| V-04 | ✅ | `tests/test_modulos.py` no CI (`validate-regulatory.yml`); item 2 |
| V-05 | ✅ | TBox 1.2.0, R24–R26 (núcleo), R28 (comparativo), R29–R30 (SCSE); I-1 a I-4 em `tests/test_invariantes.py` |
| V-06 | ✅ | `tests/test_comparativo.py`: 25 critérios com definições originais conferidas no PDF, E1–E7 com crédito e DOI |
| V-07 | ⏸ | D-02 |
| V-08 | ⬜ | item 11 |
| V-09 | ⬜ | item 11 |
| V-10 | ⬜ | item 11 |
| V-11 | ⬜ | item 12 |
| V-12 | ⬜ | item 7 |
| V-13 | ✅ | `test_rnf02_full_graph_reasons_under_five_seconds` no CI: 0,12 s para 5105 triplas |
| V-14 | ⬜ | item 8 |
| V-15 | 🟡 | contador publicado e protegido no CI: 31 sem lastro de 88 (faltam 17 componentes e 14 traços de contexto); meta zero no item 8 |
| V-16 | ✅ | `ontologies/consultas/V16_sementes_sem_ligacao.rq` = 0 linhas (`tests/test_conselho.py`, CI) |
| V-17 | 🟡 | `afirmacoes.py` classifica as 12 teses (6/4/2); falta recálculo no CI e C04 (item 10) |
| V-18 | 🟡 | celular participante com Minhas escolhas, Mesa e Agora já existe; falta teste de toque (item 15) |
| V-19 | 🟡 | ficha em torre, assento, arco, cúpula, pessoa e mesa; "por quê?" até a fonte no item 8 |
| V-20 | ⬜ | item 14 |
| V-21 | ⬜ | item 14 |
| V-22 | ⬜ | item 14 |
| V-23 | ⬜ | item 13 |
| V-24 | ⏸ | D-05 |
| V-25 | ⬜ | item 15 |
| V-26 | ⬜ | item 17 |
| V-27 | ⬜ | item 16 |
| V-28 | ⬜ | item 17 |
| V-29 | ⏸ | decisão humana por item (item 17) |
| V-30 | ⬜ | item 16 |
| V-31 | ✅ | `tests/test_identificacao_ao_vivo.py`; migração aplicada no Supabase em 17/11/2026 (rejeição por `respostas_nome_check` confirmada); commit 285407a |
