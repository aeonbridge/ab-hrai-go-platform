# 5. Padrões e layouts: web e mobile

O mesmo sistema atende dois usos diferentes:

- **Web** é a estação de análise. Mostra densidade, comparação lado a lado e o painel de
  evidência sempre aberto.
- **Mobile** é para acompanhar e revisar: alertas de mudança normativa, fila de revisão,
  leitura de avaliações e de relatórios do council, e contribuições.

O mobile não é uma versão menor da web. Ele prioriza ver o que mudou, entender a
situação e agir sobre a revisão.

## 5.1 Estrutura do app

### Web (`expanded` em diante)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ HRAI-GO   [Busca global ⌘K]                        [Conta · nível]         │
├────────────────────────────────────────────────────────────────────────────┤
│ Retrato jurídico: legal-snapshot-br-2026-11-11 · Vigência: 11/11/2026 [Alterar] │  ← AsOfBar
├──────────────┬───────────────────────────────────────────┬─────────────────┤
│ NORM         │ VERIFY · overline                          │ Proveniência    │
│ VERIFY  ▌    │ Título da página                           │ (xlarge: fixo;  │
│ DEBATE       │                                            │  menores: abre  │
│  └ Shadow    │ Conteúdo                                   │  sob demanda)   │
│    Council   │                                            │                 │
│ FORESIGHT    │                                            │                 │
│ ──────────   │                                            │                 │
│ Revisão (3)  │                                            │                 │
│ Fontes       │                                            │                 │
└──────────────┴───────────────────────────────────────────┴─────────────────┘
```

- A barra lateral tem 280px e pode ser recolhida para um rail de 72px.
- O painel de proveniência tem 360px. Em `xlarge` fica fixo à direita; em `large` e abaixo
  abre por cima do conteúdo.

### Mobile (`compact`)

```
┌──────────────────────────┐
│ VERIFY        [busca][⋯] │
│ ◷ 11/11/2026 · snapshot ▾│  ← AsOfBar recolhido
├──────────────────────────┤
│                          │
│  Conteúdo em cartões     │
│                          │
├──────────────────────────┤
│ Início  Normas  Avaliar  │
│ Debate  Revisão(3)       │  ← barra inferior, 5 destinos
└──────────────────────────┘
```

- Destinos da barra inferior: **Início** (mudanças e alertas), **Normas** (NORM),
  **Avaliações** (VERIFY), **Debate** (DEBATE, Shadow Council e FORESIGHT) e **Revisão**
  (fila, com contador).
- O FORESIGHT entra pelo Debate no mobile, porque a análise de alternativas é uso de
  estação de trabalho e o mobile só permite consultá-la.
- Detalhes (proveniência, versão, evidência) abrem em sheet. Os níveis de altura são
  médio e cheio.

## 5.2 Templates por módulo

### NORM: monitor normativo
- **Web:** à esquerda, lista de mudanças detectadas (feed por data, com filtros de
  jurisdição, órgão, tipo e estado); à direita, o `NormCard` com o `VersionTimeline`, o diff
  textual da versão e a lista "Avaliações afetadas (propagação)", que indica o que precisa
  ser reavaliado (spec §6.1, passo 6).
- **Mobile:** feed de mudanças. Cada item mostra o estado anterior → o novo (dois
  `StatusBadge` com seta, mais o texto "passou de Em tramitação para Aprovada · não
  promulgada") e o número de avaliações afetadas.

### VERIFY: avaliação de aplicação
- **Web:** cabeçalho da aplicação (dossiê: finalidade, jurisdição, autonomia decisória,
  dados pessoais) · `AsOfBar` · `AssessmentSummary` · `ObligationMatrix` · painel de
  evidência.
- O fluxo segue as quatro perguntas da spec §7.2 numa barra de abas fixa: **Aplicabilidade
  → Evidências → Avaliação → Impacto de mudanças**.
- **Mobile:** resumo no topo e cartões de obrigação embaixo. Pedido de evidência num toque
  ("Solicitar evidência ao responsável").

### DEBATE: tensões e argumentos
- **Web:** `TensionCaseCard` em destaque, `ControversyStepper` e duas colunas de argumentos
  com o mesmo peso visual. A posição das colunas é sorteada por sessão, para que nenhum
  lado fique fixo na posição de leitura privilegiada. O `ArgumentGraph` fica numa aba.
- **Mobile:** lista de `ClaimCard` agrupada por relação, com filtro "apoios · contestações ·
  qualificações".

### SHADOW COUNCIL: sessão
- **Web:** `CouncilSessionHeader` (com `SyntheticBanner`) e as abas **Composição**
  (`CoverageMatrix` + `CouncilSeatGrid`), **Rodadas** (linha do tempo das seis rodadas, com
  as contribuições de cada assento), **Relatório** (síntese, `MinorityReport` e matriz de
  divergências, todos no mesmo nível) e **Qualidade** (`CouncilQualityPanel`).
- **Mobile:** somente leitura do relatório e da composição. A criação e a configuração de
  sessão são exclusivas da web.

### FORESIGHT: alternativas
- **Web:** `PolicyAlternativeCard` lado a lado (até 3) e `TradeoffChart`; as hipóteses
  ficam sempre visíveis acima dos gráficos.
- O aviso "Explorador conceitual · não é resultado econométrico" aparece quando aplicável.

### Revisão (todos os módulos)
- **Web:** fila com filtros por tipo e por nível de autoridade exigido, diff à direita e
  ações abaixo.
- **Mobile:** um item por tela. Há ações por botão e também por deslizar.

## 5.3 Padrões transversais

**Mudança de estado é sempre "de → para".** Nunca se mostra só o estado novo. Os dois
badges aparecem com seta e texto.

**Detalhe progressivo.** O nível 1 mostra o rótulo e o estado. O nível 2 (hover, foco ou
toque) mostra o preview, a fonte e a data. O nível 3 (painel ou sheet) mostra a linhagem
completa. Nenhuma informação jurídica crítica (vinculação, data, sintético) fica só no
nível 2 ou 3.

**Tabelas densas na web.** Cabeçalho fixo, primeira coluna fixa, densidade alternável
(confortável 48px / compacta 36px) e números tabulares. Na versão compacta os badges
continuam com rótulo.

**Carregamento e processamento.** Avaliações e sessões são longas e acontecem em segundo
plano. O status aparece em texto e em progresso real ("Rodada 2 de 5 · 14 de 20 assentos"),
nunca só como spinner. Ao terminar, há notificação, que no mobile é push.

**Erros de fonte.** Quando a fonte oficial está indisponível, a tela diz isso e mostra a
última versão conhecida, com o `recordTime`. A plataforma nunca inventa nem completa o
texto.

**Camadas de acesso** (spec §10). O conteúdo restrito à organização tem o ícone `lock` e o
rótulo "Restrito à organização". O público tem `globe` e "Público". Um conteúdo nunca muda
de camada sem confirmação explícita.

## 5.4 Internacionalização

- Os rótulos estão em `pt-BR` e `en` nos tokens. A plataforma é multinacional.
- Datas: formato local na interface (11/11/2026) e ISO 8601 em mono no detalhe técnico.
- Nomes de jurisdição e de instrumento mantêm a grafia oficial do país ("EU AI Act",
  "LGPD").
- Deixar margem de cerca de 30% para expansão de texto em badges e botões.
