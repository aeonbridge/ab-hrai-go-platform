# HRAI-GO Design System

Design system do **HRAI-GO (Human-centred Regulatory AI, Governance Observatory)**, plataforma de inteligência regulatória
humano–IA (ver `docs/NOMENCLATURA.md`), para web e mobile. **DS v2 (17/11/2026):** a referência de experiência passa a ser a câmara 3D do Shadow
Council (`docs/07-camara.md`). O tema `camara` é o padrão; os temas claro e escuro
institucionais continuam para documentos e leitura jurídica. A camada semântica de domínio
não mudou.

O entregável é **tokens + especificação**, sem código de plataforma. Os tokens seguem o
formato W3C DTCG e podem ser convertidos para CSS variables, Tailwind, React Native,
SwiftUI, Compose ou Flutter.

Fonte de domínio: *HRAI-GO — Plataforma Aberta de Inteligência Regulatória e Governança de
IA*, documento pedagógico de consolidação (11/11/2026). Os nomes canônicos dos estados
(`InForce`, `InsufficientEvidence`, `PerspectiveAgent`…) vêm desse documento.

## Por que este design system existe

A plataforma junta, na mesma tela, lei vigente, interpretação, evidência, hipótese de
agente, posição de stakeholder e proposta de reforma. O erro mais grave que a interface
pode cometer é deixar uma dessas coisas parecer outra: um projeto de lei parecer
obrigação, uma perspectiva sintética parecer consulta pública, ou falta de prova parecer
descumprimento. Por isso, cada valor controlado da ontologia tem **assinatura visual
própria**, formada por rótulo, ícone, traço e tom. Ela continua legível em escala de cinza
e com daltonismo.

## Estrutura

```
design-system/
├── tokens/
│   ├── primitives.tokens.json      escalas de cor, fonte, espaço, raio, borda, movimento, breakpoints
│   ├── semantic.light.tokens.json  papéis (bg, text, border, action, tone.*) — tema claro
│   ├── semantic.dark.tokens.json   mesmas chaves — tema escuro
│   ├── semantic.camara.tokens.json mesmas chaves — tema câmara 3D (padrão desde o v2)
│   └── domain.tokens.json          108 valores de domínio: tipo epistêmico, estado normativo,
│                                    estado de obrigação, vinculação, voz, autoridade, Shadow
│                                    Council, argumentação, equivalência, módulos…
├── docs/
│   ├── 01-principios.md            separação epistemológica, evidência antes de inferência, voz
│   ├── 02-fundamentos.md           cor, tipografia, espaço, elevação, movimento, ícones, layout
│   ├── 03-semantica-de-dominio.md  como cada estado do domínio é desenhado (núcleo do sistema)
│   ├── 04-componentes.md           átomos, moléculas e organismos, com API e diferenças web/mobile
│   ├── 05-padroes-e-layouts.md     estrutura do app, templates por módulo, padrões transversais
│   ├── 06-acessibilidade.md        WCAG 2.2 AA, contraste medido, teclado, leitor de tela, mobile
│   ├── 07-camara.md                linguagem espacial 3D: torre, anel, cadeira vazia, véu, cúpula
│   └── contrast-report.md          GERADO — contraste de todos os pares, nos dois temas
├── checklists/aceite.md            o que conferir antes de dar uma tela por pronta
└── scripts/
    ├── contrast_check.py           mede contraste WCAG de todos os pares; exit 1 se falhar
    └── validate_domain.py          valida tokens de domínio (rótulos, tons, traços, unicidade)
```

## Verificação

```bash
python3 scripts/contrast_check.py    # → 0 failures (câmara, claro e escuro, incluindo vidro)
python3 scripts/validate_domain.py   # → 108 domain values, 0 errors
```

Os dois scripts usam só a biblioteca padrão e servem para CI. Estado em 11/11/2026: os dois
passam. O texto de corpo mais baixo é 5,59:1, o texto de estado tem 7,01:1 ou mais e os
contornos têm 4,1:1 ou mais. Os 86 ícones foram conferidos contra o lucide-react 1.25.

## Como consumir

1. Transformar os tokens com Style Dictionary 4 (que suporta DTCG) ou Terrazzo, gerando:
   - **web:** CSS custom properties, com `:root` = claro e `[data-theme="dark"]` = escuro,
     mais um `@theme` do Tailwind v4 que aponta para elas;
   - **mobile:** um objeto de tema por plataforma (React Native, SwiftUI `Color` assets,
     Compose `ColorScheme`).
2. Os tokens de domínio não viram cor diretamente. Viram uma **tabela de lookup**
   `grupo → valor → {tone, stroke, icon, label}`, consumida por um único `StatusBadge`. Ver
   `docs/03` §3.1.
3. Fontes: IBM Plex Sans, Serif e Mono, e Bricolage Grotesque para cena e marca (todas OFL). Ícones: Lucide (ISC).

## Decisões de design registradas

| Decisão | Por quê |
|---|---|
| `iris` reservado para o que não vincula | Garante à primeira vista o critério de aceite §15.3 da spec ("nenhuma proposição pendente é apresentada como obrigação"). O `validate_domain.py` impõe isso |
| Traço codifica força jurídica (tracejado → sólido → duplo) | Distingue proposta, vigência e aplicabilidade sem depender de cor, inclusive em impressão P&B |
| Estratos sem cor na interface 2D; cor só como identidade na câmara 3D | Cor em agregado criaria hierarquia de confiança; no espaço 3D, sem cor não se segue um assento até a área que ele espera (v2) |
| Vidro, luz e gradiente permitidos só como espaço | A câmara precisa de profundidade; o estado jurídico continua em rótulo, ícone e traço (v2) |
| Tons de domínio mantidos, rampas trocadas no tema câmara | civic→teal, ochre→brass, iris→violet, crimson→coral, lagoon→sky: muda a cor, não o significado (v2) |
| Confiança em tom neutro | Confiança não é boa nem ruim, então semáforo induziria leitura errada |
| Sem placar no Shadow Council | Doze agentes contra oito não representam vontade social (spec §10.7) |
| Cor de módulo só na navegação | Um estado (p. ex. "Atendida") precisa ter a mesma aparência em todos os módulos |
| Sem ícone de "brilhos" para IA | Agente é identificado como agente, com identidade e versão, não como mágica |

## Em aberto

- Marca (logotipo, símbolo). O nome está fechado: HRAI-GO (Human-centred Regulatory AI, Governance Observatory), ver
  `docs/NOMENCLATURA.md`. Falta só a identidade gráfica.
- Quais estratos e eixos de estratificação (spec §10.3) são parametrizáveis por sessão.
  Isso afeta a `CoverageMatrix`.
- Biblioteca de gráficos e grafo por plataforma (decisão de implementação).
- Validação com usuários reais: reguladores, juristas, sociedade civil. Os testes do cinza e
  de contraste não substituem teste com pessoas.
