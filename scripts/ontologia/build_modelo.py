#!/usr/bin/env python3
"""Generate web/assets/modelo.js from the graph (ESP-ONT-02, RF-09; RT-VIS-03 "Fonte única").

Everything the chamber, the presentation and the panel display comes from this file, and this file
comes from the graph: nothing is edited by hand. Sources in the graph:

  components   seeded components (ontologies/regulatory/sementes), one per GM-xx
  topics       substantive areas with displayKey "topics:*" (comparative module); strength and comps
               are DERIVED from the components, with the same rule the chamber always used:
               inForce if a documented component is effective or policy, else proposedOnly if a
               documented component is proposed, else inferredOnly; none without components
  features     seeded context traits (CF-xx)
  strata, seeds, branches, unrep   SCSE council of the scenario (ontologies/scse/conselho)

Also writes web/assets/grafo.js (window.HRAIGO_GRAFO): for every displayed element, its IRI, backing
state, origin snapshot (URI and SHA-256), cited sources and review state, which the fichas show
under "De onde vem" and "Por quê?".

Usage:
  python3 scripts/ontologia/build_modelo.py           # regenerate both files
  python3 scripts/ontologia/build_modelo.py --check   # fail if either file differs from the graph
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import rdflib
from rdflib.namespace import DCTERMS, PROV, RDF, RDFS, SKOS

ROOT = Path(__file__).resolve().parents[2]
MODELO = ROOT / "web/assets/modelo.js"
GRAFO = ROOT / "web/assets/grafo.js"
SOURCES = ["ontologies/regulatory/HRAI_GO_Regulatory_General.ttl", "ontologies/regulatory/sementes/*.ttl",
           "ontologies/comparativo/HRAI_GO_Comparativo.ttl", "ontologies/scse/SCSE_Shadow_Council_Ontology.ttl",
           "ontologies/scse/conselho/*.ttl", "ontologies/regulatory/instances/**/*.ttl",
           "ontologies/regulatory/afirmacoes/*.ttl"]
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
S = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/scse#")
SEED_NS = "https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/br/sementes#"
HEADER = ("/* Gerado por scripts/ontologia/build_modelo.py a partir do grafo. Não editar à mão (RF-09).\n"
          "   Componentes e traços: sementes (ontologies/regulatory/sementes); áreas: módulo comparativo;\n"
          "   estratos, tensões, ramos e cadeiras vazias: SCSE (ontologies/scse/conselho). */\n")


def load() -> rdflib.Graph:
    g = rdflib.Graph()
    for pattern in SOURCES:
        for f in sorted(glob.glob(str(ROOT / pattern), recursive=True)):
            if not Path(f).name.startswith("._"):
                g.parse(f)
    return g


def keyed(g: rdflib.Graph, prefix: str) -> list[tuple[str, rdflib.URIRef]]:
    """(id, individual) for every displayKey '<prefix>:<id>', in display order, then by id."""
    out = []
    for s, o in g.subject_objects(H.displayKey):
        if str(o).startswith(prefix + ":") and (str(s).startswith(SEED_NS) or prefix not in ("components", "features")):
            order = g.value(s, H.displayOrder)
            out.append((int(order) if order is not None else 10**6, str(o).split(":", 1)[1], s))
    return [(i, s) for _, i, s in sorted(out)]


def text(g, s, p, default=""):
    v = g.value(s, p)
    return str(v) if v is not None else default


def build(g: rdflib.Graph) -> tuple[dict, dict]:
    area_key = {s: str(o).split(":", 1)[1] for s, o in g.subject_objects(H.displayKey) if str(o).startswith("topics:")}
    components = []
    for cid, s in keyed(g, "components"):
        topics = sorted((area_key[a] for a in g.objects(s, H.seedArea) if a in area_key),
                        key=lambda t: int(g.value(next(k for k, v in area_key.items() if v == t), H.displayOrder) or 0))
        components.append({"id": cid, "kind": text(g, s, H.seedKind), "title": text(g, s, RDFS.label),
                           "status": text(g, s, H.seedLegalStatus), "basis": text(g, s, H.seedTopicsBasis),
                           "topics": topics, "desc": text(g, s, RDFS.comment), "note": text(g, s, SKOS.editorialNote)})
    topics = []
    for tid, s in keyed(g, "topics"):
        cs = [c for c in components if tid in c["topics"]]
        documented = [c for c in cs if c["basis"] == "documented"]
        strength = ("none" if not cs else "inForce" if any(c["status"] in ("effective", "policy") for c in documented)
                    else "proposedOnly" if any(c["status"] == "proposed" for c in documented) else "inferredOnly")
        topics.append({"id": tid, "label": text(g, s, SKOS.prefLabel), "strength": strength, "comps": [c["id"] for c in cs]})
    features = [{"id": fid, "kind": text(g, s, H.seedKind), "title": text(g, s, RDFS.label)} for fid, s in keyed(g, "features")]
    strata = []
    for sid, s in keyed(g, "strata"):
        seats = sum(1 for seat in g.subjects(S.hasStratum, s))
        strata.append({"id": sid, "label": text(g, s, RDFS.label), "seats": seats})
    strata_id = {s: i for i, s in keyed(g, "strata")}
    seeds = [{"id": tid, "title": text(g, s, RDFS.label), "desc": text(g, s, S.tensionDescription),
              "strata": [strata_id[x] for x in sorted(g.objects(s, S.tensionBetweenStrata), key=lambda x: int(g.value(x, H.displayOrder) or 0))]}
             for tid, s in keyed(g, "seeds")]
    branches = [{"id": bid, "h": text(g, s, S.assumption)} for bid, s in keyed(g, "branches")]
    unrep = [uid for uid, _ in keyed(g, "unrep")]
    modelo = {"components": components, "topics": topics, "features": features, "strata": strata,
              "seeds": seeds, "branches": branches, "unrep": unrep}

    # Provenance per displayed element ("De onde vem" / "Por quê?" in the fichas).
    grafo = {}
    for setname in ("components", "topics", "features", "strata", "seeds", "branches", "unrep"):
        for eid, s in keyed(g, setname):
            snap = g.value(s, PROV.wasDerivedFrom)
            entry = {"iri": str(s), "estado": "semente" if str(s).startswith(SEED_NS) else "ontologia",
                     "revisao": "pendente"}
            same = sorted(str(x) for x in g.objects(s, SKOS.exactMatch))
            if same:
                entry["fontePrimaria"] = same
            if snap is not None:
                entry["origem"] = {"rotulo": text(g, snap, RDFS.label), "uri": text(g, snap, H.snapshotURI),
                                   "sha256": text(g, snap, H.snapshotSHA256)}
            refs = sorted(str(x) for x in g.objects(s, DCTERMS.references))
            if refs:
                entry["fontes"] = refs
            claims = sorted(str(x) for x in g.objects(s, H.hasPolicyClaim))
            if claims:
                entry["afirmacoes"] = [{"iri": c, "rotulo": text(g, rdflib.URIRef(c), RDFS.label)} for c in claims]
            grafo[f"{setname}:{eid}"] = entry
    return modelo, grafo


def render(modelo: dict, grafo: dict) -> tuple[str, str]:
    m = HEADER + "window.HRAIGO_MODELO = " + json.dumps(modelo, ensure_ascii=False) + ";\n"
    gj = ("/* Gerado por scripts/ontologia/build_modelo.py. Proveniência de cada elemento exibido (fichas). */\n"
          "window.HRAIGO_GRAFO = " + json.dumps(grafo, ensure_ascii=False, indent=1, sort_keys=True) + ";\n")
    return m, gj


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    m, gj = render(*build(load()))
    if args.check:
        ok = MODELO.read_text(encoding="utf-8") == m and GRAFO.exists() and GRAFO.read_text(encoding="utf-8") == gj
        print("modelo.js:", "gerado do grafo" if ok else "DIFERENTE DO GRAFO: rode python3 scripts/ontologia/build_modelo.py (não edite à mão)")
        return 0 if ok else 1
    MODELO.write_text(m, encoding="utf-8")
    GRAFO.write_text(gj, encoding="utf-8")
    print(f"{MODELO.relative_to(ROOT)} e {GRAFO.relative_to(ROOT)} gerados do grafo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
