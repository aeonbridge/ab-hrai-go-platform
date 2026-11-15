# Conceito Stitch · Biblioteca comparativa HRAI-GO

Esta pasta contém um protótipo HTML da biblioteca comparativa por jurisdição e função regulatória. O arquivo mostra um recorte de NORM; ele não define outro design system.

## Fonte canônica

A única fonte de tokens, semântica e padrões é o diretório `design-system/` do projeto em `/Volumes/T9/projects/aeon-bridge/repos/public/ab-hrai-go-platform/ab-hrai-go-platform/design-system/`:

- `tokens/primitives.tokens.json`: paletas, tipografia, espaçamento, raios, bordas, ícones e breakpoints.
- `tokens/semantic.light.tokens.json` e `tokens/semantic.dark.tokens.json`: papéis semânticos para os dois temas.
- `tokens/domain.tokens.json`: ícone, rótulo, tom e traço para cada estado de domínio.
- `docs/01-principios.md` a `docs/06-acessibilidade.md`: princípios, componentes, padrões e acessibilidade.
- `checklists/aceite.md`: critérios de aceite.

Os valores CSS de `code.html` são a camada web de consumo desses tokens. Ao alterar o design system, atualize essa camada a partir dos arquivos canônicos; não acrescente uma paleta ou escala paralela neste manifesto.

## Padrões representados

- Interface clara por padrão, tema escuro com os mesmos papéis semânticos e preferência persistida.
- IBM Plex Sans para interface, IBM Plex Serif para passagens jurídicas e IBM Plex Mono para identificadores e datas técnicas.
- `AsOfBar` bitemporal com snapshot, `EpistemicTag`, `StatusBadge`, `BindingMarker` e links de proveniência.
- Proposta normativa em íris tracejada; norma em vigor em civic sólido; aplicabilidade em civic duplo; orientações não vinculantes em tom neutro pontilhado.
- Métricas do recorte identificadas como demonstrativas até a conexão com corpus e cálculo reproduzível; confiança interpretativa permanece separada da similaridade e de qualquer juízo de qualidade regulatória.
- Navegação por seções em desktop, rail acessível em larguras médias e barra inferior com cinco destinos em mobile; posição atual anunciada como localização.
- Conteúdo jurídico em IBM Plex Serif, 18 px e largura máxima de 68ch; corpo de interface a partir de 14 px; controles móveis com alvo mínimo de 44 px e recomendado de 48 px.
- Comparação funcional como primeiro bloco de conteúdo, com filtro funcional acessível e opção para exibir todas as unidades; métricas demonstrativas identificadas como não conectadas a uma base.
- Foco visível, texto e estado redundantes, comportamento de movimento reduzido e proveniência navegável.

## Arquivos

- `code.html`: protótipo responsivo e interativo.
- `screen.png`: captura de página inteira do protótipo em desktop.
