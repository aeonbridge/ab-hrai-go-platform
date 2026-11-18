#!/usr/bin/env python3
"""Run the competency questions PC1-PC9 (ESP-ONT-02, RF-08) over the full reasoned graph.

The graph is every ontology module and data file (core, SCSE with the council, comparative module,
source instances, scenarios, claims, alignments). The forward-chaining reasoner runs first, because
some answers are inferred (for example PC1 uses coverage inferred by R24a/b/c).

Output: docs/especificacoes/ESP-ONT-02/consultas-resultado.json, with one entry per query: guiding
question it serves, number of rows and columns. No timestamps, so the file is reproducible.

Regression (``--check``): every query must parse and run, and must return at least as many rows as
the committed result. A query that stops answering, or loses rows, fails CI.

Usage:
  python3 scripts/ontologia/consultas.py           # run and write the result file
  python3 scripts/ontologia/consultas.py --check   # regression check against the committed file
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import raciocinar  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
QUERIES = ROOT / "ontologies/consultas"
RESULT = ROOT / "docs/especificacoes/ESP-ONT-02/consultas-resultado.json"
SOURCES = ["ontologies/regulatory/HRAI_GO_Regulatory_General.ttl", "ontologies/scse/**/*.ttl",
           "ontologies/comparativo/*.ttl", "ontologies/regulatory/instances/**/*.ttl",
           "ontologies/regulatory/cenarios/*.ttl", "ontologies/regulatory/afirmacoes/*.ttl",
           "ontologies/regulatory/alinhamentos/*.ttl", "ontologies/regulatory/sementes/*.ttl",
           "ontologies/regulatory/correspondencias/*.ttl", "ontologies/regulatory/respostas/*.ttl"]
QN = {"PC1": "QN1", "PC5": "QN1", "PC9": "QN1", "PC2": "QN2", "PC3": "QN2", "PC6": "QN2/QN3", "PC4": "QN3",
      "PC7": "transversal", "PC8": "transversal", "V16": "aceite V-16", "V27": "aceite V-27",
      "V28": "aceite V-28", "V30": "aceite V-30"}


def files() -> list[Path]:
    out: list[Path] = []
    for pattern in SOURCES:
        out += [Path(f) for f in sorted(glob.glob(str(ROOT / pattern), recursive=True)) if not Path(f).name.startswith("._")]
    return out


def reasoned_graph():
    rz = raciocinar.Raciocinador(*files())
    rz.executar()
    return rz.g


def run(g=None) -> dict:
    g = g if g is not None else reasoned_graph()
    results = {}
    for q in sorted(x for x in QUERIES.glob("*.rq") if not x.name.startswith("._")):  # skip macOS AppleDouble files
        key = q.stem.split("_")[0]
        rows = list(g.query(q.read_text(encoding="utf-8")))
        results[q.stem] = {"pergunta": QN.get(key, "—"), "linhas": len(rows),
                           "colunas": [str(v) for v in (rows[0].labels if rows else re.findall(r"\?(\w+)", q.read_text(encoding="utf-8").split("WHERE")[0]))]}
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    results = run()
    if args.check:
        base = json.loads(RESULT.read_text(encoding="utf-8")) if RESULT.exists() else {}
        problems = [f"{k}: não existe mais" for k in base if k not in results]
        problems += [f"{k}: {base[k]['linhas']} -> {v['linhas']} linhas" for k, v in results.items()
                     if k in base and v["linhas"] < base[k]["linhas"]]
        for k, v in results.items():
            print(f"{k:34s} {v['pergunta']:12s} {v['linhas']:4d} linhas")
        for p in problems:
            print("ERRO:", p)
        return 1 if problems else 0
    RESULT.write_text(json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for k, v in results.items():
        print(f"{k:34s} {v['pergunta']:12s} {v['linhas']:4d} linhas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
