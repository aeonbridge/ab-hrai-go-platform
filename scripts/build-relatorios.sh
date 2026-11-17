#!/usr/bin/env bash
# Build HRAI-GO technical reports (ABNT NBR 10719:2015 house style, docs/PADRAO_RELATORIOS.md).
# Usage: scripts/build-relatorios.sh [file.tex ...]   (no argument: every registered report)
# Engine: XeLaTeX + BibTeX through latexmk. The PDF is written next to its source.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
# Shared style (hraigo-abnt.sty) and bibliography (referencias.bib) live in docs/latex.
export TEXINPUTS="$ROOT/docs/latex//:${TEXINPUTS:-}"
export BIBINPUTS="$ROOT/docs/latex//:${BIBINPUTS:-}"

# Registry of reports that must follow the standard (keep in sync with tests/test_padrao_relatorios.py).
REPORTS=(
  docs/latex/modelo-relatorio-tecnico.tex
  docs/relatorios/ontologia/relatorio.tex
  docs/relatorios/visao/hrai-go-visao.tex
  docs/especificacoes/ESP-ONT-02/especificacao.tex
  docs/hrai-go/HRAI-GO_Plataforma_Inteligencia_Regulatoria_Shadow_Council.tex
  docs/scse/SCSE_Shadow_Council_Simulation_Spec.tex
)
[ "$#" -gt 0 ] && REPORTS=("$@")

for tex in "${REPORTS[@]}"; do
  dir="$(dirname "$tex")"; name="$(basename "$tex")"
  echo "==> $tex"
  ( cd "$dir" && latexmk -xelatex -bibtex -interaction=nonstopmode -halt-on-error -file-line-error \
      -silent "$name" >/dev/null ) || {
    log="$dir/${name%.tex}.log"; grep -nE '^!|Error|error:' "$log" | head -20 >&2; exit 1; }
  ( cd "$dir" && latexmk -c "$name" >/dev/null 2>&1 || true )
done
