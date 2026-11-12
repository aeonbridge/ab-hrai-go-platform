#!/usr/bin/env bash
# Build all SCSE/HRAI-GO publications from version-controlled source files.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts/hrai-go artifacts/scse artifacts/previews/scse
latex_run() {
  local source="$1" destination="$2"
  for pass in 1 2; do
    xelatex -interaction=nonstopmode -halt-on-error -file-line-error \
      -output-directory="$destination" "$source" >/tmp/hrai-tex-build.log 2>&1 || {
        tail -n 100 /tmp/hrai-tex-build.log >&2
        return 1
      }
  done
}
latex_run docs/hrai-go/HRAI-GO_Plataforma_Inteligencia_Regulatoria_Shadow_Council.tex artifacts/hrai-go
latex_run docs/scse/SCSE_Shadow_Council_Simulation_Spec.tex artifacts/scse
find artifacts/hrai-go artifacts/scse -maxdepth 1 -type f \
  ! -name '*.pdf' ! -name '*.zip' ! -name 'SCSE_REENVIO.tex' -delete
cp artifacts/scse/SCSE_Shadow_Council_Simulation_Spec.pdf artifacts/scse/SCSE_REENVIO.pdf
cp docs/scse/SCSE_Shadow_Council_Simulation_Spec.tex artifacts/scse/SCSE_REENVIO.tex
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root = Path.cwd()
plans = {
    'artifacts/hrai-go/HRAI-GO_Documento_Pedagogico_Completo.zip': [
        ('docs/hrai-go/HRAI-GO_Plataforma_Inteligencia_Regulatoria_Shadow_Council.tex', 'HRAI-GO_Plataforma_Inteligencia_Regulatoria_Shadow_Council.tex'),
        ('artifacts/hrai-go/HRAI-GO_Plataforma_Inteligencia_Regulatoria_Shadow_Council.pdf', 'HRAI-GO_Plataforma_Inteligencia_Regulatoria_Shadow_Council.pdf'),
    ],
    'artifacts/scse/SCSE_Ontology_TTL_OWL.zip': [
        ('ontologies/scse/SCSE_Shadow_Council_Ontology.ttl', 'SCSE_Shadow_Council_Ontology.ttl'),
        ('ontologies/scse/SCSE_Shadow_Council_Ontology.owl', 'SCSE_Shadow_Council_Ontology.owl'),
    ],
    'artifacts/scse/SCSE_Shadow_Council_Especificacao_Completa.zip': [
        ('artifacts/scse/SCSE_Shadow_Council_Simulation_Spec.pdf', 'SCSE_Shadow_Council_Simulation_Spec.pdf'),
        ('docs/scse/SCSE_Shadow_Council_Simulation_Spec.tex', 'SCSE_Shadow_Council_Simulation_Spec.tex'),
        ('docs/scse/SCSE_README.md', 'SCSE_README.md'),
        *[(f'schemas/scse/{f}', f) for f in ('scenario.schema.json','report.schema.json')],
        *[(f'examples/scse/{f}', f) for f in ('example_policy_request.json','example_solution_request.json','example_solution_report.json')],
    ],
    'artifacts/scse/SCSE_REENVIO_COMPLETO.zip': [
        ('artifacts/scse/SCSE_REENVIO.pdf', 'SCSE_REENVIO.pdf'),
        ('artifacts/scse/SCSE_REENVIO.tex', 'SCSE_REENVIO.tex'),
        ('assets/scse/SCSE_Capa_Diagrama.svg', 'SCSE_Capa_Diagrama.svg'),
        ('docs/scse/SCSE_README.md', 'SCSE_README.md'),
        *[(f'schemas/scse/{f}', f) for f in ('scenario.schema.json','report.schema.json')],
        *[(f'examples/scse/{f}', f) for f in ('example_policy_request.json','example_solution_request.json','example_solution_report.json')],
    ],
}
for outfile, members in plans.items():
    with ZipFile(root / outfile, 'w', compression=ZIP_DEFLATED, compresslevel=9) as z:
        for path, name in members:
            src = root / path
            if not src.is_file(): raise FileNotFoundError(src)
            z.write(src, name)
        assert z.testzip() is None, outfile
    print(outfile)
PY
if command -v pdftoppm >/dev/null 2>&1; then
  pdftoppm -f 1 -l 16 -r 80 -png \
    artifacts/scse/SCSE_Shadow_Council_Simulation_Spec.pdf \
    artifacts/previews/scse/page >/dev/null 2>&1
fi
pdfinfo artifacts/scse/SCSE_Shadow_Council_Simulation_Spec.pdf | grep Pages:
pdfinfo artifacts/hrai-go/HRAI-GO_Plataforma_Inteligencia_Regulatoria_Shadow_Council.pdf | grep Pages:
