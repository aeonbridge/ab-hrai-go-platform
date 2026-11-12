# 2. Fundamentos

Os tokens estão em três camadas, no formato W3C DTCG:

| Camada | Arquivo | Quem usa |
|---|---|---|
| Primitivos | `tokens/primitives.tokens.json` | Somente as camadas semânticas. Nenhum componente aponta para um primitivo. |
| Semânticos | `tokens/semantic.light.tokens.json` e `tokens/semantic.dark.tokens.json` (mesmas chaves) | Todos os componentes. |
| Domínio | `tokens/domain.tokens.json` | Componentes de estado regulatório (ver `03-semantica-de-dominio.md`). |

**Regra:** cor escrita à mão num componente é defeito. Se faltar um token, ele é criado nos
dois temas e o `scripts/contrast_check.py` é rodado de novo.

## 2.1 Cor

### Primitivos

Há sete escalas de 50 a 950: `ink` (neutro com viés quente, de papel e tinta), `civic`
(azul institucional), `verdant`, `crimson`, `ochre`, `iris` e `lagoon`. Cada matiz tem um
papel fixo e não é reaproveitado para outro sentido:

| Escala | Papel | Nunca usar para |
|---|---|---|
| `civic` | Marca, ação primária, registro normativo (texto oficial, obrigação, vigência) | Proposta, hipótese |
| `lagoon` | Evidência empírica, contexto nacional, cobertura documental | Conformidade |
| `ochre` | Posição de stakeholder, evidência insuficiente, alerta, dissenso | Erro |
| `iris` | Proposta normativa, hipótese de agente, incerteza jurídica | **Nada vinculante** |
| `verdant` | Obrigação atendida, convergência, revisão humana concluída | Decoração |
| `crimson` | Obrigação não atendida, erro, ação destrutiva, contestação | Destaque de marca |
| `ink` | Texto, superfícies, bordas, estados neutros (não aplicável, revogada, sintético) | — |

### Semânticos: as "tônicas"

Cada matiz vira uma tônica `color.tone.<tom>` com cinco papéis. Todos os estados de domínio
são renderizados por essas cinco cores:

| Papel | Uso | Piso medido |
|---|---|---|
| `fg` | Texto e ícone do estado, sobre `bg` ou sobre qualquer superfície | ≥ 4.5:1 |
| `bg` | Fundo tingido (badge suave, faixa de linha) | — |
| `border` | Contorno do badge ou cartão | ≥ 3:1 sobre a superfície e sobre `bg` |
| `solid` | Preenchimento forte (badge sólido, barra de status) | — |
| `solidFg` | Texto sobre `solid` | ≥ 4.5:1 |

Os outros grupos semânticos são `bg.*` (canvas, surface, subtle, muted, inverse, scrim),
`text.*`, `border.*` (subtle, default, control, strong, focus), `action.*` (primary,
secondary, ghost, danger, selected) e `simulation.*` (fundo hachurado do conteúdo fictício).

`border.subtle` é decorativo. A borda de um controle interativo usa `border.control`, que
tem contraste de 3:1 ou mais.

Os valores de contraste estão medidos em `docs/contrast-report.md`, gerado por
`scripts/contrast_check.py`: 0 falhas nos dois temas, e o texto de corpo tem no mínimo
5,59:1 (link no tema escuro sobre `bg.subtle`), e todo texto de estado tem no mínimo 7,01:1.

### Tema escuro

As chaves são as mesmas e as tônicas se invertem: `fg` vira o tom 200, `bg` vira o 950 e
`solid` vira o 300 com texto escuro. A profundidade vem de superfícies mais claras, não de
sombra. O tema escuro é opção da pessoa (`prefers-color-scheme` como valor inicial, com
preferência salva). Ele não é um "modo analista" com outra linguagem visual.

## 2.2 Tipografia

A família IBM Plex é aberta (OFL), multilíngue e tem as três vozes de que a plataforma
precisa:

| Família | Token | Uso |
|---|---|---|
| IBM Plex Sans | `font.family.sans` | Interface, navegação, rótulos, dados |
| IBM Plex Serif | `font.family.serif` | Texto normativo: artigo, inciso, trecho citado |
| IBM Plex Mono | `font.family.mono` | IRI, `LegalSnapshot`, versão, hash, data e hora ISO, nome canônico |

Escala (`font.size`, base 16px):

| Estilo | Tamanho / altura de linha / peso | Uso |
|---|---|---|
| `display` | 900 (48) / tight / semibold | Somente em página institucional pública |
| `h1` | 700 (30) / tight / semibold | Título de página |
| `h2` | 600 (24) / snug / semibold | Seção |
| `h3` | 500 (20) / snug / semibold | Cartão, painel |
| `h4` | 400 (18) / snug / semibold | Subseção |
| `body` | 300 (16) / normal / regular | Texto corrido de interface |
| `legal` | 400 (18) serif / reading / regular | Texto da norma, largura máxima de `size.measure.reading` (68ch) |
| `body-sm` | 200 (14) / normal / regular | Tabela densa, metadado |
| `caption` | 100 (12) / normal / medium | Rótulo de eixo, nota de rodapé. **Nunca** para conteúdo jurídico |
| `overline` | 100 (12) / normal / semibold / caps | Módulo (NORM, VERIFY…), rótulo de seção curto |
| `code` | 200 (14) mono / normal / regular | Identificadores |

Regras:

- Corpo de texto nunca abaixo de 14px. Texto jurídico nunca abaixo de 16px.
- No mobile, os tamanhos acompanham a configuração de texto do sistema (Dynamic Type no iOS,
  `fontScale` no Android) até 200%, sem truncar o rótulo de estado. Badges quebram linha;
  não usam reticências.
- Números em tabela usam `font-variant-numeric: tabular-nums`.

## 2.3 Espaço, raio, borda

- **Grade de 4px** (`space.*`). Em mobile, o padding lateral é `space.4` (16); em desktop,
  `space.6` (24).
- **Raio contido**, porque a plataforma é documental, não lúdica: `radius.md` (4) em
  controles, `radius.lg` (8) em cartões, `radius.full` só em avatar e chip de filtro.
- **Borda é informação.** `border.width.regular` (1.5px) é o padrão dos badges de estado,
  porque precisa ser legível também quando tracejada ou pontilhada. `strong` (2px) marca
  seleção. `focus` (3px) é o anel de foco, com afastamento de 2px.

## 2.4 Elevação

São três níveis (`shadow.sm/md/lg`) e só no tema claro. Usos: `sm` em cartão sobre canvas,
`md` em popover e menu, `lg` em modal e sheet. Elevação não é usada para indicar
importância.

## 2.5 Movimento

- `duration.fast` (120ms) para hover e feedback de toque. `duration.base` (200ms) para abrir
  painel. `duration.slow` (320ms) para sheet e modal.
- Com `prefers-reduced-motion` (ou "reduzir movimento" no sistema), toda transição vira um
  `opacity` de no máximo 120ms ou é cortada.
- Nenhuma animação comunica estado sozinha. Um "carregando" infinito tem texto ("Avaliando
  12 obrigações…").

## 2.6 Iconografia

- Biblioteca: **Lucide** (ISC), disponível para web e React Native. Os nomes estão
  verificados contra o lucide-react 1.25.
- Tamanhos: `size.icon.sm` (16) inline, `md` (20) em controles, `lg` (24) em navegação.
  Traço de 1.75px.
- Ícone de estado vem sempre acompanhado de rótulo. Ícone sem rótulo só é aceito em botão
  de barra de ferramentas, com `aria-label` e tooltip.
- **Proibidos:** emoji, e os ícones `sparkles`/`wand`/`stars` para IA.

## 2.7 Layout e pontos de quebra

| Classe | Largura | Colunas | Margem | Navegação |
|---|---|---|---|---|
| `compact` | 0–599 | 4 | 16 | Barra inferior (5 destinos) |
| `medium` | 600–904 | 8 | 24 | Rail lateral |
| `expanded` | 905–1239 | 12 | 24 | Rail ou barra lateral recolhível |
| `large` | 1240–1599 | 12 | 32 | Barra lateral fixa de 280px |
| `xlarge` | 1600+ | 12 (+ painel de detalhe) | 32 | Barra lateral + painel de evidência fixo à direita |

## 2.8 Toque e entrada

- Alvo de toque com `size.touchTarget.recommended` (48) por padrão e
  `size.touchTarget.min` (44) como piso absoluto.
- No mobile, campo de entrada tem fonte de 16px ou mais, para o iOS não dar zoom.
- Todo gesto (deslizar para revisar, segurar para comparar) tem equivalente clicável.
