# 4. Componentes

Esta é uma especificação agnóstica de plataforma. Cada componente tem propósito, anatomia,
API (props com nome e tipo, para traduzir a React, React Native, SwiftUI ou Compose),
estados, diferenças entre web e mobile e acessibilidade. A organização segue o atomic
design.

Convenções de API:

- `tone`, `variant` e `size` têm nomes iguais em todos os componentes.
- `size`: `sm | md | lg`, com padrão `md`.
- Componentes de estado recebem **o valor de domínio**, nunca uma cor:
  `<StatusBadge group="obligationStatus" value="insufficientEvidence" />`.
- Nenhum componente aceita `color` livre.

---

## 4.1 Átomos

### Button
- **Variantes:** `primary` · `secondary` · `ghost` · `danger`. Tamanhos `sm` (32), `md` (40)
  e `lg` (48). No mobile o padrão é `lg`.
- **Props:** `variant`, `size`, `icon?`, `iconPosition: start|end`, `loading`, `disabled`,
  `as` (botão ou link).
- **Estados:** repouso, hover, pressionado, foco (anel `border.focus` de 3px com afastamento
  de 2px), desabilitado (`text.disabled` + `bg.muted`), carregando (spinner + texto
  "Processando…" e largura mantida).
- **Acessibilidade:** usar o elemento nativo de botão. `aria-busy` durante o carregamento.
  Botão só com ícone exige `aria-label`.
- **Regra de domínio:** a ação que publica algo no grafo validado ("Publicar interpretação",
  "Aceitar contribuição") sempre abre confirmação mostrando o efeito e o nível de autoridade
  exigido.

### Icon
- Lucide, tamanhos `sm`/`md`/`lg`. É decorativo por padrão (`aria-hidden`). Recebe
  `label` quando é o único portador de sentido.

### Text / Heading / LegalText / Code
- `LegalText` usa serif, `font.size.400`, `lineHeight.reading` e largura máxima de 68ch.
  Preserva a numeração original (art., §, inciso). Trechos destacados como evidência usam
  `<mark>` com `tone.civic.bg` e sublinhado. No modo de alto contraste (`forced-colors`),
  o sublinhado é o que permanece.
- `Code` em mono para IRI, versão, hash e snapshot, com botão de copiar ao lado.

### Input / Select / Checkbox / Radio / Switch / DatePicker
- Borda `border.control` (≥ 3:1). Na web: altura 40, fonte 16 e rótulo sempre visível acima
  (placeholder não substitui rótulo). No mobile: altura 48 e teclado adequado ao tipo.
- Erro: borda `tone.crimson.border`, ícone `circle-x` e mensagem abaixo, ligada por
  `aria-describedby`. A cor não é o único sinal.
- `DatePicker` aceita data parcial ("2026", "2026-08") quando o contexto é jurídico.

### Badge (base)
- É o átomo neutro sobre o qual os badges de domínio são construídos.
- **Anatomia:** [ícone 16] [rótulo] dentro de borda `border.width.regular` com o `stroke` do
  token.
- **Variantes:** `soft` (fundo `bg`, texto `fg`, borda `border`), `solid` (`solid` +
  `solidFg`) e `outline` (sem fundo).
- Altura de 24 na web e 28 no mobile. O rótulo quebra linha e nunca usa reticências.

### ConfidenceMeter
- Três segmentos de 6×12px em `tone.neutral`: os segmentos preenchidos são `solid` e os
  vazios são `border` com traço. O rótulo vem ao lado ("Confiança média").
- `role="meter"`, com `aria-valuenow` de 1 a 3 e `aria-valuetext` igual ao rótulo.

### Avatar / IdentityGlyph
- Para pessoa e instituição verificadas: avatar ou brasão de 24/32/40.
- Para perspectiva sintética e agente: **somente o ícone** (`bot`/`cpu`) num quadrado
  neutro. É proibido usar foto, ilustração humana ou iniciais que sugiram pessoa.

---

## 4.2 Moléculas de domínio

### EpistemicTag
- Mostra o `epistemicKind` de uma afirmação. Badge `soft` com o traço do token.
- **Props:** `kind`, `compact?`. Com `compact`, mostra só o ícone e o rótulo curto. No modo
  compacto o rótulo continua obrigatório; ele só fica mais curto.
- **Posição fixa:** canto superior esquerdo do cartão ou primeira célula da linha.

### StatusBadge
- É o badge genérico para qualquer grupo de domínio.
- **Props:** `group` (`normativeState`, `obligationStatus`, `reviewStatus`, `coverageState`,
  `bindingness`…), `value`, `variant`, `size`.
- O mesmo componente atende todos os grupos, e o token define tudo. Isso garante a
  consistência entre os módulos.

### BindingMarker
- É um `StatusBadge group="bindingness"` em `outline`. Fica sempre à direita do estado da
  obrigação.

### ProvenanceChip
- **Propósito:** levar à origem de qualquer afirmação em um toque.
- **Anatomia:** [ícone do `knowledgeGraph.provenance`] [fonte curta] · [versão] · [data].
  O clique abre o `ProvenancePanel`.
- **Props:** `sourceId`, `sourceLabel`, `version`, `recordTime`, `agentId?`, `confidence?`.
- **Mobile:** fica no rodapé do cartão. Um toque abre a sheet.

### CitationLink
- É o link para um dispositivo normativo ("LGPD, art. 20, §1º"). O hover ou foco mostra um
  preview com `LegalText`, o `normativeState` e o snapshot. Usa `text.link` sublinhado.
- Se o dispositivo estiver `repealed` ou `superseded` na data avaliada, o link mostra o badge
  ao lado. **Nunca** omite essa informação.

### AsOfBar
- **Propósito:** deixar explícita a data de qualquer tela que filtre por tempo (spec §6.2).
- **Anatomia:** `Retrato jurídico: legal-snapshot-br-2026-11-11` · `Vigência considerada:
  11/11/2026` · `Registrado em: 11/11/2026 14:02` · [Alterar].
- **Web:** barra fixa abaixo do cabeçalho da página. **Mobile:** chip recolhido no topo, que
  abre uma sheet ao ser tocado.
- Ao alterar, a tela pergunta qual eixo mudar: "o que valia em junho" (`validTime`) ou "o que
  se sabia em junho" (`recordTime`).

### AgentIdentity
- **Anatomia:** [IdentityGlyph] [nome canônico em mono, p. ex. `ComplianceAssessmentAgent`]
  [badge de voz] [versão do modelo · parâmetros, sob "detalhes"].
- Para `perspectiveAgent`: estrato, link para o `PerspectiveCharter` e contagem de fontes.

### ContributorIdentity
- [Avatar] [nome] [badge `authorityLevel`] [badge `voice`] [declaração de conflito de
  interesse, se houver: ícone `flag` e "Declara vínculo com…"].

### SyntheticBanner
- É uma faixa fixa no topo de qualquer contêiner com conteúdo sintético ou fictício.
  Usa o fundo hachurado, o ícone e o rótulo completo, e não pode ser dispensada.
- Para Shadow Council: "Perspectivas sintéticas baseadas em fontes documentais. Não é
  consulta pública, amostra de opinião nem mandato" (spec §10).

### TensionChip
- Chip neutro com o ícone de `tensionType` e o rótulo ("Proteção × inovação").

### EquivalenceBadge
- Badge de `equivalence`. Na biblioteca comparativa, aparece sempre entre os dois
  requisitos comparados.

### Stepper (ControversyStepper / CouncilRoundStepper)
- Passos numerados com ícone e rótulo. O estado de cada passo é dado por forma (círculo
  preenchido, anel ou vazio) e por texto ("concluído", "em andamento", "não iniciado").
- **Web:** horizontal. **Mobile:** vertical, ou horizontal com rolagem quando houver mais de 4
  passos.

---

## 4.3 Organismos

### NormCard
- É a ficha de um instrumento ou dispositivo.
- **Anatomia:** overline com jurisdição e tipo ("BR · Lei") · título · `StatusBadge`
  (`normativeState`) · `VersionTimeline` compacto · trecho em `LegalText` · rodapé com
  `ProvenanceChip` e "Comparar com outras jurisdições".

### VersionTimeline
- Eixo do tempo com marcos: proposta → tramitação → aprovação → promulgação → vigência →
  aplicação → (suspensão, revogação, substituição).
- Cada marco tem o ícone e o traço do estado. **Vigência e aplicação são marcos separados.**
  A data avaliada (do `AsOfBar`) aparece como uma linha vertical rotulada.
- **Mobile:** vertical. Toque num marco abre o diff do texto daquela versão.

### ObligationMatrix
- É o resultado de uma `ComplianceAssessment`.
- **Web:** tabela com as colunas Requisito (`CitationLink`) · Estado (`StatusBadge`) ·
  Vinculação (`BindingMarker`) · Evidências (contagem + link) · Confiança · Revisão. Linhas
  podem ser agrupadas por estado ou por norma. Os requisitos `nonBinding` ficam em grupo
  separado e recolhido.
- **Cabeçalho:** `AssessmentSummary` com a distribuição dos seis estados em barra empilhada.
  Cada segmento tem rótulo e número, e o padrão do traço também aparece na barra.
  `insufficientEvidence` nunca é somado a `notSatisfied`.
- **Mobile:** lista de cartões de obrigação, com filtro por estado em chips roláveis e o
  resumo fixo no topo.

### EvidenceItem
- Mostra o tipo de evidência, a origem, o período, o método, a confiança, o vínculo com
  obrigações ("sustenta 3 obrigações") e o acesso. O acesso é público ou restrito: na camada
  organizacional restrita (spec §10) aparece um cadeado e "visível só para a organização".

### ClaimCard (PolicyClaim / argumento)
- **Anatomia:** `EpistemicTag` · `ContributorIdentity` ou `AgentIdentity` · tese · evidências
  (`EvidenceItem` compacto) · relações (contagem por `argumentRelation`) · ações
  ("Apoiar com evidência", "Contestar", "Qualificar").
- "Apoiar" exige anexar evidência, porque a credibilidade vem da evidência e não de votos.
  **Não existe** botão de curtir nem contador de apoio por popularidade.

### ArgumentGraph
- É a visão em grafo do `RegulatoryArgumentGraph`. Os nós têm forma por `knowledgeGraph` e as
  arestas seguem `argumentRelation`.
- **Equivalente obrigatório:** a mesma informação existe numa lista indentada (árvore de
  argumentos) acessível por teclado e leitor de tela. O grafo é uma visão adicional, não a
  única.
- **Mobile:** abre na lista. O grafo fica disponível em tela cheia, opcionalmente.

### TensionCaseCard
- Mostra o `RegulatoryTensionCase`: tipo (`TensionChip`), questão, `ControversyStepper`,
  objetivos em tensão (lado a lado, sem "vencedor"), evidências dos dois lados e link para
  a sessão do Shadow Council.

### CouncilSessionHeader
- Contém `SyntheticBanner` · questão (`CouncilQuestion`) · jurisdição · `councilMode` ·
  `LegalSnapshot` · `CouncilRoundStepper` · metadados (modelos e versões, parâmetros,
  `SamplingFrame` com `populationRepresentative: false` dito em texto:
  "Moldura documental · não representativa da população").

### CoverageMatrix
- Grade de estratos (linhas) × perspectivas ou teses (colunas). As células usam
  `coverageState`, com ícone em cada uma. As células `unrepresented` são tracejadas e
  vazias, com o texto "sem fonte".
- Rodapé com as métricas `StratumCoverage` e `ViewpointCoverage`, em número e barra.
- **Mobile:** lista por estrato. Cada estrato é expansível e mostra suas perspectivas.

### CouncilSeatGrid
- Um cartão por `CouncilSeat` com: ícone do estrato, `AgentIdentity` sintético, número de
  fontes, `coverageState` e posição atual na rodada.
- **Não** mostra contagem de "a favor × contra" como placar. Se houver experimento com
  pesos, eles aparecem como "parâmetros de cenário", com link para a análise de
  sensibilidade (spec §10.7).

### MinorityReport
- Seção **fixa** de todo `ShadowCouncilReport` e de toda síntese. Tem o mesmo nível de
  título e o mesmo peso tipográfico da síntese principal, e nunca fica recolhida por padrão.
- Ícone `file-warning`, título "Relatório de minoria" e a lista de argumentos com
  `ClaimCard`.

### CouncilQualityPanel
- São as métricas da spec §10.9: StratumCoverage, ViewpointCoverage, EvidenceTraceability,
  UnsupportedClaimRate, DissentRetention, ModelSensitivity, ExpertAgreement,
  AffectedGroupReview e ConflictOfInterestDisclosure.
- Cada métrica é um `MetricTile`: nome, valor, o que mede (uma frase) e tendência com seta e
  texto. **Não** há nota composta.

### ComparisonTable (biblioteca comparativa)
- Colunas por jurisdição e linhas por **função regulatória** (não por rótulo nacional, spec
  §9.1). Cada célula tem: `NormativeRequirement` resumido, `CitationLink`, intervalo de
  vigência (`effectiveInterval`), confiança da interpretação e `EquivalenceBadge` em relação
  à coluna de referência.
- **Mobile:** escolher duas jurisdições e comparar lado a lado, com as funções empilhadas.

### PolicyAlternativeCard (FORESIGHT)
- Mostra o nome da alternativa (p. ex. "Controles graduados por exposição a risco"), as
  hipóteses explícitas, os indicadores separados (custo administrativo, dano potencial,
  capacidade de fiscalização, distribuição de impactos) com incerteza, o estado
  (`deliberationOutcome`, incluindo "Inconclusivo por falta de dados") e o
  `SyntheticBanner` quando os dados forem simulados.
- **Proibido:** nota, estrela, ranking ou rótulo de "melhor alternativa".

### TradeoffChart
- Small multiples, com um indicador por painel, ou um gráfico de dispersão com fronteira de
  Pareto rotulada. As alternativas são codificadas por **forma + rótulo direto**, com cor
  apenas de reforço. A incerteza aparece como intervalo (barra de erro ou faixa), nunca é
  omitida.
- Paleta: as tônicas `civic`, `lagoon`, `ochre` e `iris` no valor `border`, que tem 3:1 ou
  mais sobre a superfície, cada uma com marcador distinto (círculo, quadrado, triângulo,
  losango).

### ReviewQueueItem
- É a contribuição externa à espera de revisão (spec §10).
- **Anatomia:** `ContributorIdentity` · tipo de mudança · diff · `StatusBadge`
  (`reviewStatus`) · aviso de segurança quando houver sinal de injeção de instrução ou fonte
  suspeita (ícone `shield-alert`, tom crimson, "Conteúdo retido para verificação").
- As ações "Aceitar" e "Pedir ajustes" estão sempre disponíveis. Em mobile, também por
  deslizar, com botões equivalentes visíveis.

### ProvenancePanel
- Linhagem completa: fonte → extração → regra (versão) → ontologia (versão) → agente ou
  modelo → revisão humana → publicação. É uma lista vertical de passos com `recordTime` em
  cada um.
- **Web:** painel lateral à direita (fixo em `xlarge`). **Mobile:** sheet em altura cheia.

---

## 4.4 Componentes de aplicação

- **AppShell:** cabeçalho (marca, busca global, `AsOfBar`, conta), navegação por módulo e
  área de conteúdo. Detalhe em `05-padroes-e-layouts.md`.
- **ModuleNav:** NORM · VERIFY · DEBATE (com SHADOW COUNCIL como subitem) · FORESIGHT. O
  item ativo tem indicador no tom do módulo (2px) e `action.selected`.
- **EmptyState:** diz por que está vazio e o que fazer. Em contexto de evidência, "Nenhuma
  evidência anexada" é um **estado de domínio** (leva a `insufficientEvidence`) e não um
  vazio genérico.
- **Toast / InlineAlert:** usam a tônica do estado, com ícone e texto. Toast some sozinho
  só quando for informativo. Erro fica até ser dispensado.
- **Modal / Sheet:** com foco preso no conteúdo, Esc ou botão para fechar, foco devolvido ao
  gatilho e `bg.scrim` ao fundo.
