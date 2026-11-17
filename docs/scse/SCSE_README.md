# SCSE - Shadow Council Simulation Environment (HRAI-GO)

Módulo do **HRAI-GO (Human-centred Regulatory AI, Governance Observatory)**; ver `docs/NOMENCLATURA.md`.

Especificacao independente (v1.0) de ambiente de simulacao deliberativa multiagente inspirado no fluxo conceitual do MiroFish. **Nao e uma implementacao** de um simulador e nao emite parecer juridico.

## Artefatos

- `SCSE_Shadow_Council_Simulation_Spec.pdf`: especificacao pedagogica de arquitetura, semantica, simulacao, APIs, avaliacao e criterios de aceite.
- `SCSE_Shadow_Council_Simulation_Spec.tex`: fonte LaTeX completo com diagramas TikZ embutidos.
- `scenario.schema.json`: contrato JSON Schema Draft 2020-12 de pedidos.
- `report.schema.json`: contrato JSON Schema Draft 2020-12 de relatorios.
- `example_policy_request.json`: cenario ilustrativo de analise de proposta regulatoria brasileira.
- `example_solution_request.json`: cenario ilustrativo de conformidade de solucao de triagem de candidatos.
- `example_solution_report.json`: resultado sintetico ilustrativo, **nao proveniente de uma execucao de IA ou avaliacao juridica real**.

## Modos

- `regulatoryPolicy`: avalia propostas ou regulamentos frente ao contexto e aos stakeholders de um pais.
- `solutionCompliance`: avalia o briefing/spec de uma solucao diante de regulacao e jurisdicao datadas.

## Validacao de contratos

Os dois schemas e tres exemplos foram validados com `jsonschema` no momento da geracao. Para repetir:

```python
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

for stem, examples in (
    ("scenario", ["example_policy_request.json", "example_solution_request.json"]),
    ("report", ["example_solution_report.json"]),
):
    schema = json.loads(Path(f"{stem}.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for example in examples:
        value = json.loads(Path(example).read_text())
        validator.validate(value)
        print("OK:", example)
```

## Compilar o documento

Requer XeLaTeX, `Noto Serif`, `Noto Sans`, `DejaVu Sans Mono`, `tikz`, `tcolorbox`, `hyperref` e pacotes LaTeX usuais.

```bash
xelatex -interaction=nonstopmode -halt-on-error SCSE_Shadow_Council_Simulation_Spec.tex
xelatex -interaction=nonstopmode -halt-on-error SCSE_Shadow_Council_Simulation_Spec.tex
```

## Rastreabilidade de origem

MiroFish (referencia de conceito): https://github.com/666ghj/MiroFish

OASIS (motor de simulacao social): https://github.com/camel-ai/oasis

Os demais documentos de base fornecidos pelo usuario estao identificados na bibliografia do PDF. O SCSE e uma especificacao proposta independente; o uso de codigo de terceiros requer verificacao de licencas e atribuicoes.
