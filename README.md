# HRAI-GO Platform

Repositório de artefatos da plataforma de inteligência regulatória HRAI-GO e do **Shadow Council Simulation Environment (SCSE)**.

## Estrutura

- `docs/hrai-go/`: documento pedagógico da plataforma, em LaTeX.
- `docs/scse/`: especificação pedagógica do ambiente de simulação, em LaTeX.
- `ontologies/scse/`: serializações equivalentes Turtle (.ttl) e RDF/XML (.owl), incluindo regras SWRL.
- `schemas/scse/`: contratos de entrada e saída JSON Schema e exemplos.
- `assets/scse/`: diagramas SVG.
- `src/scse/`: runtime executável do Shadow Council (Python), multi-provider (Anthropic, OpenAI, xAI, Gemini), via OpenRouter por padrão ou APIs diretas. Guia: `docs/scse/SCSE_RUNTIME.md`.
- `config/scse/models.toml`: transporte, modelos por provider e perfil, e distribuição percentual de provider/modelo por estrato.
- `scenarios/brasil-ficticio/`: mundo fictício e cenários do PBIA (2026–2033).
- `experiments/scse/`: matriz experimental para comparar a prática de cada provider.
- `artifacts/`: PDFs e pacotes de distribuição, quando publicados.

## Runtime SCSE

```bash
pip install -e '.[all,dev]'
export OPENROUTER_API_KEY=...
scse run scenarios/brasil-ficticio/BR-PBIA-001.json --dry-run
scse experiment experiments/scse/provider-practice.toml --plan
```

## Modelagem e uso

Classes, propriedades, regras e identificadores canônicos em **inglês**; explicações em **português brasileiro**. O projeto separa inferência semântica, verificação de dados, avaliação jurídica e deliberação multiagente. As simulações não constituem certificação de conformidade nem consulta pública representativa.

Fontes normativas e materiais usados como referência não são automaticamente tratados como obrigações vigentes. O estado legislativo, a jurisdição e a data de aplicação devem ser verificados.

## Origem

Consolidação de artefatos criados nas discussões HRAI-GO e SCSE de novembro de 2026.
