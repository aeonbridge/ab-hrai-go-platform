# Execução da ESP-ONT-02 em sessão autônoma (loop)

Roteiro para uma sessão que implementa a especificação `docs/especificacoes/ESP-ONT-02/especificacao.pdf`
(fonte: `especificacao.tex`) em iterações curtas, até estabilizar. Ler antes de cada iteração.

## Leitura obrigatória antes da 1ª iteração

1. `docs/especificacoes/ESP-ONT-02/especificacao.pdf`: requisitos RF-01 a RF-17 e RNF-01/02 (seção 8).
2. `docs/relatorios/ontologia/relatorio.pdf` (RT-ONT-01): motor de raciocínio e resultados de base.
3. `ontologies/regulatory/README.md` e `ontologies/scse/`: as duas ontologias que serão separadas (RF-17).
4. `scripts/ontologia/raciocinar.py`, `experimentos.py`, `afirmacoes.py`: ferramentas já prontas.

## Ordem de execução (dependências)

| Ordem | Requisito | Depende de | Autônomo? |
|---|---|---|---|
| 1 | RF-15 slide da apresentação + selo "sem lastro" nas fichas (início do RF-12) | — | sim |
| 2 | RF-17 separar núcleo e SCSE (SCSE importa o núcleo; classes de deliberação migram com equivalência) | — | sim |
| 3 | RF-03 TBox v1.2.0 + regras R24–R30 + testes de invariantes | 2 | sim |
| 4 | RF-16 (formalização) módulo comparativo: 25 critérios de Alanoca et al. + E1–E7, `CriterionCoding` | 3 | sim, **exceto as escalas da E4** (ver abaixo) |
| 5 | RF-05 esquema `SubstantiveArea` (28 áreas + IA generativa/GPAI) | 4 | sim |
| 6 | RF-13 tensões, estratos, assentos e cenários na SCSE com ligação ao núcleo | 2 | sim |
| 7 | RF-08 consultas SPARQL PC1–PC8 versionadas + teste de regressão no CI | 3–6 | sim |
| 8 | RF-09 + RF-12 build gera `web/assets/modelo.js` do grafo; contador "sem lastro" no CI | 5–7 | sim |
| 9 | RF-01 substitutivo do Senado (dez/2024) no corpus como nova versão do PL | — | **não**: obter o texto oficial (ver bloqueios) |
| 10 | RF-04 / RF-06 / RF-16 (codificação) / RF-14 instâncias UE, Reino Unido, EUA; correspondências; codificações | 9 | extração sim, **aprovação não** |
| 11 | RF-07 indicadores de capacidade e exposição com fonte e ano-base | 10 | extração sim, **aprovação não** |
| 12 | RF-10 Mesa grava posições sobre afirmações; registro de decisão; métricas | 6 | sim |

## Protocolo de cada iteração

1. Escolher o próximo item não concluído da tabela, respeitando dependências.
2. Implementar o menor incremento verificável.
3. Rodar sempre:
   - `python3 tests/verify_regulatory_ontology.py`
   - `python3 tests/verify_regulatory_instances.py`
   - `python3 scripts/ontologia/experimentos.py`
   - `python3 scripts/ontologia/afirmacoes.py`
   - os testes novos do próprio item.
4. Conferir o critério de aceite do requisito na tabela da seção 8 da especificação. Só marcar como concluído se ele passar.
5. Registrar o resultado em `docs/especificacoes/ESP-ONT-02/PROGRESSO.md`: item, o que mudou, comandos rodados com saída resumida e o que ficou pendente.
6. Commit pequeno, com mensagem descrevendo o requisito (ex.: `RF-17: SCSE importa o núcleo`).

## Invariantes (violação = parar e reportar)

- Nenhuma regra afirma `hasLegalStatus`, `assessmentHasStatus`, `releasePublishesCandidate` ou decisão humana.
- Cenários (`ontologies/regulatory/cenarios/`) e afirmações (`ontologies/regulatory/afirmacoes/`) nunca vão para `instances/`.
- Todo conteúdo extraído entra como `CandidateAssertion`. **A sessão nunca cria `ApprovalDecision` nem `ReviewDecision`**: aprovação é humana.
- Nenhuma jurisdição exibida sem `SourceSnapshot` com SHA-256.
- O contador de elementos "sem lastro" nunca sobe em relação ao `main`.
- Taxonomia de Alanoca et al.: definições originais intactas; extensões apenas como E1–E7, com crédito e DOI.

## Decisões humanas: a sessão prepara, não decide

- **RF-02, China:** incluir fontes primárias ou retirar da comparação.
- **E4, escalas:** propor escala para cada um dos 25 critérios com exemplos de codificação e deixar para aprovação.
- **Revisão das extrações** (F2): dispositivos, correspondências BR↔UE, codificações, indicadores.
- **Alinhamento A1** dos 5 componentes "próximos" e das teses do anexo.

A sessão deve abrir esses itens em `PROGRESSO.md`, numa seção "Aguardando decisão", e seguir com o que não depende deles.

## Bloqueios conhecidos

- **Texto do Senado (RF-01):** baixar do site do Senado ou da Câmara exige rede liberada para esses domínios. Sem rede, registrar como bloqueio e pedir o PDF ao usuário. Não usar fonte secundária como texto primário.
- **PDF da "Análise Comparativa":** não está no repositório. As teses vieram de resumo do usuário.
- **IRIs resolvíveis (RNF-01):** depende de decisão sobre domínio (w3id.org ou GitHub Pages).

## Critério de parada (plataforma estabilizada)

A sessão encerra o loop quando:
1. os itens 1–8 e 12 estão concluídos com critério de aceite verde;
2. CI verde com consultas PC1–PC8 respondendo e contador "sem lastro" publicado;
3. os itens 9–11 estão implementados até onde não dependem de decisão humana, com a fila "Aguardando decisão" atualizada.

Também deve parar e pedir orientação se o mesmo item falhar em três iterações seguidas.
