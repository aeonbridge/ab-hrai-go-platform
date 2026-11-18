# Método de extração e de lastro do HRAI-GO

Como cada elemento que o HRAI-GO (Human-centred Regulatory AI, Governance Observatory) exibe ganha um indivíduo na
ontologia, de onde ele vem e em que estado de revisão está. Complementa o passo M2 do RT-VIS-03 ("Extração candidata e
revisão humana") e a regra de transição da ESP-ONT-02 (capítulo "Fonte única").

## 1. Três tipos de origem

| Origem | O que é | Exemplos no repositório | Como entra no grafo |
|---|---|---|---|
| **Fonte primária** | Texto oficial, capturado com hash | PBIA (PDF VN 8), PL 2338 (2023 e texto do Senado), AI Act, LGPD, white paper do Reino Unido, NIST AI RMF (`docs/ai-regulations/`) | Extração candidata por documento, com dispositivo ou página (seção 3) |
| **Documento-semente** | Documento escrito pelo projeto para dar partida à plataforma; resume e organiza fontes, mas não é fonte oficial | modelo da câmara `scenarios/governanca-brasil/model/brasil-governanca-v0.json`; contexto `scenarios/governanca-brasil/context/2026-11-14.json`; cenário `scenarios/governanca-brasil/GOV-BR-001.json` (registro de fontes); alinhamento `ontologies/regulatory/alinhamentos/camara_GM_para_PBIA.ttl`; conselho `ontologies/scse/conselho/GOV-BR-001.ttl` | Semeadura automática e determinística (seção 2) |
| **Análise externa** | Documento de terceiros com teses | "Análise Comparativa e Diretrizes Estratégicas"; Alanoca et al. (2025) | Teses como `PolicyClaim`, nunca como fato (RF-11) |

## 2. Semeadura a partir de documentos-semente

**Decisão do autor (17/11/2026):** elementos que vêm de documentos-semente são criados automaticamente no grafo e
contam como "com lastro". Eles levam o estado **semente**, visível na ficha, e ficam na fila de revisão. A revisão
humana pode confirmar (ligando ao indivíduo de fonte primária), corrigir ou retirar.

**Ferramenta:** `scripts/ontologia/semear.py`. Determinística, sem modelo de linguagem: o mesmo documento-semente gera
sempre as mesmas triplas. Saída: `ontologies/regulatory/sementes/GOV-BR-001_sementes.ttl` (fora de `instances/`, que
só recebe extração de fonte primária; invariante I-2).

**Passos**

1. **Captura do documento-semente.** Cada arquivo vira um `hrai:SourceSnapshot` com o SHA-256 do arquivo e o caminho no
   repositório. Mudou o arquivo, muda o hash, e a semeadura é refeita (o CI acusa se o `.ttl` estiver desatualizado).
2. **Seleção.** Todos os componentes e traços de contexto exibidos. Componentes com correspondência exata a um
   indivíduo de fonte primária também são semeados, mas o indivíduo semeado só guarda os atributos de apresentação e
   aponta para o de fonte primária (`skos:exactMatch`); o selo mostra o estado "exato".
3. **Mapeamento de campos** (tabela abaixo). Nenhum valor é inventado: título, descrição, notas, ids de fonte e estado
   de verificação são copiados do documento-semente.
4. **Proveniência.** Cada indivíduo leva `prov:wasDerivedFrom` (o snapshot do documento-semente), `dcterms:references`
   (as fontes que o documento-semente cita, com URI quando o registro de fontes a tem) e `hrai:displayKey` (o elemento
   da câmara que ele sustenta).
5. **Registro de extração.** Para cada indivíduo há um `hrai:CandidateAssertion` num `hrai:ExtractionBatch`, produzido
   pelo agente `ExtratorDeSementes` (`hrai:MonitoringAgent`). Nenhuma `ReviewDecision` é criada (invariante I-3).

**Mapeamento de campos do modelo da câmara (componentes GM-xx)**

| Campo no documento-semente | No grafo |
|---|---|
| `kind = institution` | `hrai:Stakeholder` |
| `kind = instrument, mechanism, resource, metric` | `hrai:PolicyInstrument` |
| `legalStatus = proposed` | `dcterms:isPartOf` o PL 2338 e anotação "proposta, sem força vinculante" |
| `legalStatus = policy` com fonte do PBIA | `dcterms:isPartOf` o PBIA |
| `title`, `description`, `notes` | `rdfs:label`, `rdfs:comment`, `skos:editorialNote` |
| `sourceIds` | `dcterms:references` (URI) ou `hrai:seedSourceId` (id sem URI registrada) |
| `verification` | `hrai:seedVerification` |
| alinhamento `skos:closeMatch` | copiado: o componente "próximo" aponta para os indivíduos parecidos |

**Mapeamento dos traços de contexto (CF-xx)**

| Campo | No grafo |
|---|---|
| traço | `hrai:ContextIndicator` qualitativo, `hrai:indicatorRelevantToJurisdiction` Brasil, sem valor numérico nem ano-base (ficam para o RF-07) |
| `kind` (asset, capability, constraint) | `hrai:hasIndicatorMethod` |
| `basis = assertion` | marcado como **hipótese de trabalho** |
| fontes só do "Brasil fictício" (`BRF-*`) ou sem fonte | marcado como **sem fonte real**: não pode sustentar especificidade da QN1 até ganhar fonte primária |

## 3. Extração de fonte primária

Usada para dispositivos, requisitos, correspondências, codificações e indicadores (itens 9 a 12 do loop).

1. **Captura**: `SourceSnapshot` com URI, data e SHA-256; a captura anterior não é apagada.
2. **Extração**: o agente propõe indivíduos citando dispositivo (artigo, parágrafo) ou página. Tudo entra como
   `CandidateAssertion` num lote, com o agente que extraiu.
3. **Revisão humana**: `ReviewDecision` aprova ou rejeita; só a pessoa decide (I-3).
4. **Publicação**: ato explícito num `KnowledgeGraphRelease`; nenhuma regra publica (I-1).

Quando a extração primária confirma um elemento semeado, o indivíduo semeado recebe `skos:exactMatch` para o
indivíduo de fonte primária e o selo passa a mostrar a fonte primária.

## 4. Estados de lastro de um elemento exibido

| Estado | Significado | Selo na ficha | Conta no contador |
|---|---|---|---|
| sem lastro | só existe em `web/assets/modelo.js` | "Sem lastro na ontologia" | sem lastro |
| semente | indivíduo derivado de documento-semente, pendente de revisão | "Semente: derivado de <documento>, pendente de revisão" | com lastro |
| próximo | só correspondência aproximada (`closeMatch`), sem indivíduo próprio | "Próximo de ..., pendente de revisão" | sem lastro |
| exato | correspondência exata com indivíduo de fonte primária | "Na ontologia: <indivíduo>" | com lastro |

O contador (`scripts/ontologia/lastro.py`, `web/assets/lastro.js`) publica o total e quantos ainda são sementes. O CI
falha se o número sem lastro subir. O slide da apresentação só diz "cada peça é um indivíduo da ontologia" com zero sem
lastro, e então informa quantas peças ainda são sementes.

## 5. Da ontologia para a interface

`scripts/ontologia/build_modelo.py` gera `web/assets/modelo.js` (o que a câmara, a apresentação e o painel exibem) e
`web/assets/grafo.js` (a proveniência de cada elemento) a partir do grafo. Nada é editado à mão; o CI falha se os
arquivos divergirem do grafo. A força de cada área da cúpula é derivada dos componentes, com regra explícita mostrada
no "Por quê?" da ficha: vigente se há componente documentado vigente ou de política pública; senão proposta se há
componente documentado proposto; senão inferida; lacuna sem componentes. Atributos só de apresentação (tipo, situação
legal declarada, ordem de exibição) são anotações copiadas do documento-semente.

## 6. O que este método não faz

- Não transforma documento-semente em fonte oficial: o selo e a proveniência dizem de onde veio.
- Não usa traço sem fonte real como evidência de especificidade (QN1) nem de lacuna (QN3).
- Não aprova nada: semente, candidato e alinhamento ficam na fila "Aguardando decisão" do `PROGRESSO.md`.

## 7. Como verificar

```
python3 scripts/ontologia/semear.py --check     # sementes atualizadas em relação aos documentos-semente
python3 scripts/ontologia/lastro.py --check     # contador atualizado e sem regressão
python3 scripts/ontologia/build_modelo.py --check  # modelo.js e grafo.js iguais ao que o grafo gera
python3 -m pytest -q tests/test_sementes.py     # proveniência, marcação de hipóteses, nenhuma ReviewDecision
```
