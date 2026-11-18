#!/usr/bin/env python3
"""Monitoring queue (RT-VIS-03, M10; ESP-ONT-02 PC7): what each regulatory change reopens, for human review.

Runs PC7 over the full reasoned graph and groups the answer by change event: provisions, requirements,
assessments and applications potentially affected (rules R10-R13), and codings, QN1 specificities and
claims tied to the previous version of the changed instrument. Nothing is updated as fact: every item
goes to the review queue.

Output: web/assets/monitoramento.js (window.HRAIGO_MONITOR), shown on the site's "Monitoramento" page.

Usage:
  python3 scripts/ontologia/monitorar.py           # regenerate
  python3 scripts/ontologia/monitorar.py --check   # fail if the file differs from the graph
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import rdflib
from rdflib.namespace import RDFS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consultas  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web/assets/monitoramento.js"
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
ORDER = ["dispositivo", "requisito", "avaliação", "aplicação", "codificação", "especificidade", "afirmação"]


def build() -> dict:
    g = consultas.reasoned_graph()
    q = next(p for p in consultas.QUERIES.glob("PC7_*.rq") if not p.name.startswith("._"))
    by_event: dict[str, dict] = {}
    items = defaultdict(lambda: defaultdict(list))
    for row in g.query(q.read_text(encoding="utf-8")):
        ev, kind, target = row.evento, str(row.tipoAfetado), row.afetado
        label = str(g.value(target, RDFS.label) or g.value(target, H.legalCitation) or str(target).split("#")[-1])
        items[str(ev)][kind].append(label)
    for ev, kinds in items.items():
        e = rdflib.URIRef(ev)
        snap = g.value(e, H.changeObservedInSnapshot)
        by_event[ev] = {
            "rotulo": str(g.value(e, RDFS.label) or ev.split("#")[-1]),
            "descricao": str(g.value(e, H.changeDescription) or ""),
            "snapshot": str(g.value(snap, RDFS.label)) if snap is not None else "",
            "reaberto": {k: len(kinds[k]) for k in ORDER if kinds.get(k)},
            "itens": {k: sorted(set(kinds[k]))[:12] for k in ORDER if kinds.get(k)},
        }
    return {"eventos": [by_event[k] for k in sorted(by_event)], "revisao": "todos os itens aguardam revisão humana"}


def render(data: dict) -> str:
    return ("/* Gerado por scripts/ontologia/monitorar.py a partir do grafo (PC7). Fila de reabertura para revisão humana. */\n"
            "window.HRAIGO_MONITOR = " + json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + ";\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = render(build())
    if args.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("monitoramento:", "atualizado" if ok else "DESATUALIZADO: rode python3 scripts/ontologia/monitorar.py")
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8")
    data = json.loads(text.split("=", 1)[1].rstrip(";\n"))
    for e in data["eventos"]:
        print(e["rotulo"], e["reaberto"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
