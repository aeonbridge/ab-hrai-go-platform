# 7. Câmara: a linguagem espacial do HRAI-GO

Desde o DS v2, a referência de experiência é o protótipo 3D do Shadow Council
(`docs/scse/prototipo/shadow-council-tour.html`). O design system se adapta a ele. O tema
`camara` (`tokens/semantic.camara.tokens.json`) é o padrão; os temas `light` e `dark`
continuam para documentos, impressão e telas densas de texto jurídico.

O que muda é a superfície. O que **não** muda é a camada semântica: os 108 valores de
`domain.tokens.json`, com rótulo, ícone, traço e tom, valem dentro e fora da câmara.

## 7.1 Por que um espaço, e não um painel

Governança de IA é um arranjo de peças que se apoiam umas nas outras, observado por
perspectivas que não concordam. Um painel achata isso em linhas e colunas. A câmara mostra
três coisas que a tabela esconde:

- **O que sustenta o quê**: componentes empilhados por tipo, com a força jurídica visível.
- **Quem olha de onde**: assentos em anel, cada um numa posição física distinta, nenhum no
  centro.
- **O que falta**: lacunas como espaço vazio e cadeira vazia, não como linha omitida.

## 7.2 Elementos espaciais e sua semântica

| Elemento | O que representa | Codificação obrigatória |
|---|---|---|
| **Torre** | O modelo de governança em exame. Cada bloco é um componente (`GM-xx`); os andares agrupam o tipo: instrumento, instituição, mecanismo, recurso, métrica | Cor do bloco = tom do estado normativo (`inForce` → civic/teal, política pública → ochre/brass, proposta → iris/violet). Conteúdo inferido ou a confirmar: bloco vazado com aresta tracejada |
| **Anel de assentos** | Os 20 assentos sintéticos em 8 estratos | Marcador de estrato (`color.stratum.*`) só como identidade; família de modelo (`color.provider.*`) alternável. Todo assento leva rótulo de estrato e a marca "sintético" |
| **Cadeira vazia** | Perspectiva sem fonte documental (`Unrepresented`) | Anel tracejado neutro, sem cor de estrato, com rótulo do grupo ausente. Nunca é preenchida com posição plausível |
| **Véu** | Rodada R1 às cegas: os assentos não veem o modelo | Névoa sobre a torre enquanto durar a rodada; texto explícito "às cegas" |
| **Feixes** | Expectativas de cada assento viajando até as áreas da taxonomia | Partícula na cor de identidade do estrato; intensidade de uma área = número de assentos que a esperam, nunca "importância" |
| **Cúpula de áreas** | As 28 áreas da taxonomia e sua cobertura | Força de cobertura: `inForce` sólido, `proposedOnly` tracejado iris, `inferredOnly` pontilhado neutro, `none` vazio com contorno crimson/coral e rótulo "sem componente" |
| **Lentes Q1/Q2/Q3** | Omissão, excesso e vantagem contextual | Etiqueta com código e nome sempre visíveis ("Q1 · Omissão"); a cor é secundária |
| **Faixa de posições** | Posição de cada estrato sobre uma proposta | Glifo + rótulo: ✓ a favor, ✕ contra, ± ajuste, ⇄ dividido, · sem posição. Sem soma, sem barra de placar |
| **Decisão** | Aceitar, modificar, rejeitar, adiar | Sempre humana, com nome do revisor e justificativa; o agente nunca pré-seleciona |

## 7.3 Vidro, luz e movimento

O DS v1 proibia vidro, brilho e gradiente. Na câmara eles são permitidos **como espaço**, não
como enfeite:

- **Vidro** (`bg.glass`, `bg.glassStrong`) só sobre a cena 3D. O contraste é medido com o
  painel composto sobre `bg.canvas` (`scripts/contrast_check.py`). Texto jurídico longo usa
  `bg.glassStrong` ou sai da cena para uma superfície opaca.
- **Luz (bloom)** marca foco de atenção: o assento falando, a área acendendo. Nunca é usada
  para indicar estado jurídico, que continua dependendo de rótulo e traço.
- **Gradiente** só na marca e na cena, nunca em componente de estado.
- **Movimento** conta a sequência do protocolo (R1 → cobertura → lentes → decisão). Com
  `prefers-reduced-motion`, as transições viram cortes, e todo o conteúdo continua acessível.
- **Sem 3D**: se WebGL falhar ou o dispositivo for fraco, o mesmo tour roda em painéis
  (`body.no3d`). Nenhuma informação existe só na cena.

## 7.4 Estratos com cor: a regra que substitui a proibição

O DS v1 negava cor aos estratos porque cor cria hierarquia de confiança. No espaço 3D, sem
cor não há como seguir um assento no anel nem um feixe até a cúpula. A regra nova:

1. Cor de estrato é **identidade de posição**, nunca valor: proibida em barras, rankings,
   totais, mapas de calor e resumos.
2. Sempre acompanhada do rótulo do estrato.
3. Nenhum estrato usa tom do domínio como identidade principal. A semelhança visual entre
   cores de estrato e tons normativos é conhecida e mitigada pelo rótulo; ver §7.6.
4. Na interface 2D (formulários, listas, relatórios), os estratos voltam a ser neutros.

## 7.5 Tipografia na câmara

- `font.family.display` (Bricolage Grotesque) para título de cena, marca e números de
  palco. Nunca em texto jurídico, rótulo de estado ou identificador.
- IBM Plex Sans para interface, Serif para norma, Mono para identificadores: inalterados.

## 7.6 Divergências conhecidas entre o 3D atual e a semântica

O protótipo é a referência de experiência, mas três pontos dele contrariam a camada
semântica e devem ser ajustados no próximo ciclo:

| Ponto no protótipo | Conflito | Ajuste proposto |
|---|---|---|
| Lente Q1 (Omissão) em teal | Teal é o tom de norma em vigor; na mesma cena da torre, "falta" e "vigente" ficam com a mesma cor | Q1 em coral (lacuna), Q2 em brass, Q3 em verdant |
| Posição "dividido" em violeta | Violeta é exclusivo do que não vincula (proposta, hipótese) | "Dividido" em neutro com glifo ⇄ |
| three.js r128 e fontes por CDN | Dependência externa e versão de 2021 | Vendorizar no site; atualizar o three.js num ciclo próprio, com teste visual |

## 7.7 Aceite específico da câmara

Além de `checklists/aceite.md`:

- [ ] A tela funciona com WebGL desligado e com movimento reduzido.
- [ ] Nenhum estado jurídico depende de luz, brilho ou posição no espaço.
- [ ] Toda cor de estrato aparece com rótulo, e nenhuma aparece em agregado numérico.
- [ ] A cadeira vazia está presente sempre que houver `Unrepresented`.
- [ ] Texto sobre vidro passa no `contrast_check.py` (tema `camara`).

## 7.8 Câmara ao vivo (`web/ao-vivo/`)

Evolução nascida da demo com público: a mesma câmara, agora habitada por quem está na sala.

| Elemento | O que representa | Regra |
|---|---|---|
| **Anel humano** (externo) | Cada pessoa que entrou pelo QR code | Luz latão (`brass.200`), em arcos por setor. Entra pelo lado da plateia e voa até a vaga. Simulada: luz mais fosca e contagem separada ("12 simuladas"), nunca misturada sem aviso |
| **Feixe de escolha** | Uma resposta saindo da pessoa até o objeto escolhido | Latão para tensão, coral para lacuna, latão claro para contribuição escrita. Dura o tempo do voo; não deixa rastro permanente |
| **Arcos de tensão** | As 6 tensões-semente do modelo, sobre a câmara | A opacidade cresce com os votos da sala. Rótulo só para as duas mais votadas na visão geral; todas no modo Tensões |
| **Anéis de lacuna** | Áreas sem componente na cúpula | O diâmetro cresce com os votos; o selo mostra quantos estratos sintéticos esperavam a área (R1), lado a lado com a sala |
| **Núcleo da torre** | Destino das contribuições escritas | Pulsa quando uma contribuição chega; o texto aparece no telão com setor e movimento |

Regras de leitura:

- Contagens da sala são da sala. O telão nunca diz "o Brasil acha" nem soma sala com conselho.
- Toda posição de estrato sintético mostrada como exemplo leva o selo "ilustrativa".
- O apresentador pode ocultar textos. A câmara funciona sem WebGL pelo painel 2D (`../#ao-vivo`).
