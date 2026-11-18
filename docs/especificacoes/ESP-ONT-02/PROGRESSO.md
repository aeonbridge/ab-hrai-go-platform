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

## Aguardando decisão

| Id | Decisão | Quem | Bloqueia |
|---|---|---|---|
| D-01 | RF-02, China: incluir fontes primárias ou retirar da comparação | autor | V-03, item 11 (parte) |
| D-02 | E4: aprovar as escalas dos 25 critérios (a sessão propõe) | autor | V-07, codificações (item 11) |
| D-03 | Revisão das extrações (dispositivos, correspondências BR↔UE, codificações, indicadores) | revisor humano | V-08 a V-11 |
| D-04 | Alinhamento A1: os 5 componentes "próximos" (GM-15, GM-17, GM-19, GM-20, GM-22) e as teses do anexo | autor | contador sem lastro |
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
| V-05 | 🟡 | TBox 1.2.0, R24–R26, R29–R30, I-1 a I-4 testadas (`tests/test_invariantes.py`); falta R28 (item 4) |
| V-06 | ⬜ | item 4 |
| V-07 | ⏸ | D-02 |
| V-08 | ⬜ | item 11 |
| V-09 | ⬜ | item 11 |
| V-10 | ⬜ | item 11 |
| V-11 | ⬜ | item 12 |
| V-12 | ⬜ | item 7 |
| V-13 | ✅ | `test_rnf02_full_graph_reasons_under_five_seconds` no CI: 0,12 s para 5105 triplas |
| V-14 | ⬜ | item 8 |
| V-15 | 🟡 | contador publicado e protegido no CI (item 1): 83 sem lastro de 88; meta zero no item 8 |
| V-16 | ⬜ | item 6 |
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
