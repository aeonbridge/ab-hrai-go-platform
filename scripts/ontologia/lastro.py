#!/usr/bin/env python3
"""Counter of displayed elements without ontology backing ("sem lastro") — RF-12, RF-15.

Every element the chamber, the presentation and the panel display comes from
``web/assets/modelo.js``. An element has backing ("lastro") only when an alignment file in
``ontologies/regulatory/alinhamentos/`` maps it by ``skos:exactMatch`` to an individual that
exists in the instance graph, or when a typed individual of the ontologies declares
``hrai:displayKey "<set>:<id>"`` for it. Individuals seeded from the project's seed documents
(``ontologies/regulatory/sementes/``, METODO_EXTRACAO.md) count as backed with state "semente". ``skos:closeMatch`` is recorded as "próximo" (pending human review)
and still counts as without backing. Anything not aligned is "sem lastro".

Output: ``web/assets/lastro.js`` (``window.HRAIGO_LASTRO``), read by the chamber fichas (seal)
and by the presentation slide, so the slide says what is true in each published version.
The file has no timestamp, so the build is reproducible and CI can compare it.

Usage:
  python3 scripts/ontologia/lastro.py            # regenerate web/assets/lastro.js
  python3 scripts/ontologia/lastro.py --check    # fail if the file is stale or the counter
                                                 # rose against --base-ref (default origin/main) or --base FILE
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

import rdflib
from rdflib.namespace import RDF, SKOS

ROOT = Path(__file__).resolve().parents[2]
MODELO = ROOT / "web/assets/modelo.js"
OUT = ROOT / "web/assets/lastro.js"
ALIGNMENTS = ROOT / "ontologies/regulatory/alinhamentos"
INSTANCES = ["ontologies/regulatory/instances/**/*.ttl", "ontologies/scse/**/*.ttl", "ontologies/comparativo/*.ttl",
             "ontologies/regulatory/afirmacoes/*.ttl", "ontologies/regulatory/sementes/*.ttl"]
SEED_NS = "https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/br/sementes#"
DISPLAY_KEY = rdflib.URIRef("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#displayKey")
GM_NS = "https://github.com/aeonbridge/ab-hrai-go-platform/data/governance/br#"

# The seven displayed sets (ESP-ONT-02, chapter "Fonte única") and how each element is keyed.
SETS = {
    "components": ("Componentes do modelo", lambda e: e["id"]),
    "topics": ("Áreas da taxonomia (cúpula)", lambda e: e["id"]),
    "features": ("Traços de contexto", lambda e: e["id"]),
    "strata": ("Estratos do conselho", lambda e: e["id"]),
    "seeds": ("Tensões-semente", lambda e: e["id"]),
    "branches": ("Ramos de cenário", lambda e: e["id"]),
    "unrep": ("Cadeiras vazias", lambda e: e if isinstance(e, str) else e.get("id") or e.get("label")),
}


def load_modelo(path: Path = MODELO) -> dict:
    """Parse the JSON object assigned to window.HRAIGO_MODELO."""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"window\.HRAIGO_MODELO\s*=\s*(\{.*\})\s*;?\s*$", text, re.S)
    if not m:
        raise SystemExit(f"{path}: window.HRAIGO_MODELO not found")
    return json.loads(m.group(1))


def load_alignments() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """exactMatch and closeMatch targets per GM id, from every alignment file."""
    g = rdflib.Graph()
    for f in sorted(x for x in ALIGNMENTS.glob("*.ttl") if not x.name.startswith("._")):
        g.parse(f)
    exact: dict[str, list[str]] = {}
    close: dict[str, list[str]] = {}
    for prop, bucket in ((SKOS.exactMatch, exact), (SKOS.closeMatch, close)):
        for s, o in g.subject_objects(prop):
            if str(s).startswith(GM_NS):
                bucket.setdefault(str(s)[len(GM_NS):], []).append(str(o))
    return exact, close


def instance_graph() -> rdflib.Graph:
    g = rdflib.Graph()
    for pattern in INSTANCES:
        for f in sorted(glob.glob(str(ROOT / pattern), recursive=True)):
            if not Path(f).name.startswith("._"):  # skip macOS AppleDouble files
                g.parse(f)
    return g


def known_individuals(g: rdflib.Graph | None = None) -> set[str]:
    """IRIs typed in the instance graphs; an alignment only counts if its target exists."""
    g = g if g is not None else instance_graph()
    return {str(s) for s in g.subjects(RDF.type, None)}


def display_keys(g: rdflib.Graph) -> dict[str, list[str]]:
    """'<set>:<id>' -> typed individuals that declare hrai:displayKey for that displayed element."""
    keys: dict[str, list[str]] = {}
    for s, o in g.subject_objects(DISPLAY_KEY):
        if (s, RDF.type, None) in g:
            keys.setdefault(str(o), []).append(str(s))
    return keys


def build() -> dict:
    """Counter per set plus the state of every backed or near element."""
    modelo = load_modelo()
    exact, close = load_alignments()
    graph = instance_graph()
    known = known_individuals(graph)
    keyed = display_keys(graph)
    sets, items = {}, {}
    for key, (label, ident) in SETS.items():
        elements = modelo.get(key, [])
        backed = 0
        for e in elements:
            eid = ident(e)
            hits = sorted(i for i in exact.get(eid, []) if i in known) if key == "components" else []
            hits = sorted(set(hits) | set(keyed.get(f"{key}:{eid}", [])))
            near = sorted(i for i in close.get(eid, []) if i in known) if key == "components" else []
            if hits:
                backed += 1
                # Seeded individuals (METODO_EXTRACAO.md) count as backed but keep their own state on the seal.
                seeded = [i for i in hits if i.startswith(SEED_NS)]
                if seeded and len(seeded) == len(hits):
                    near_seed = sorted(i for i in close.get(eid, []) if i in known) if key == "components" else []
                    items[f"{key}:{eid}"] = {"estado": "semente", "iris": seeded, **({"proximo": near_seed} if near_seed else {})}
                else:
                    items[f"{key}:{eid}"] = {"estado": "exato", "iris": hits}
            elif near:
                items[f"{key}:{eid}"] = {"estado": "proximo", "iris": near}
        sets[key] = {"rotulo": label, "total": len(elements), "comLastro": backed, "semLastro": len(elements) - backed}
    total = sum(s["total"] for s in sets.values())
    com = sum(s["comLastro"] for s in sets.values())
    seeds = sum(1 for v in items.values() if v["estado"] == "semente")
    return {"total": total, "comLastro": com, "semLastro": total - com, "sementes": seeds, "conjuntos": sets, "itens": items}


def render(data: dict) -> str:
    body = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
    return ("/* Gerado por scripts/ontologia/lastro.py. Não editar à mão.\n"
            "   Elementos exibidos com e sem lastro na ontologia (RF-12); usado no selo das fichas e no slide (RF-15). */\n"
            f"window.HRAIGO_LASTRO = {body};\n")


def parse_js(text: str) -> dict:
    m = re.search(r"window\.HRAIGO_LASTRO\s*=\s*(\{.*\})\s*;", text, re.S)
    return json.loads(m.group(1)) if m else {}


def baseline(base: str | None, ref: str = "origin/main") -> dict | None:
    """Counter published at ``ref`` (or in a given file); None when there is none yet."""
    if base:
        return parse_js(Path(base).read_text(encoding="utf-8"))
    try:
        text = subprocess.run(["git", "show", f"{ref}:web/assets/lastro.js"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return parse_js(text)


def check(data: dict, base: str | None, ref: str = "origin/main") -> list[str]:
    problems = []
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != render(data):
        problems.append("web/assets/lastro.js desatualizado: rode python3 scripts/ontologia/lastro.py")
    prev = baseline(base, ref)
    if prev:
        if data["semLastro"] > prev.get("semLastro", data["semLastro"]):
            problems.append(f"contador sem lastro subiu: {prev['semLastro']} -> {data['semLastro']}")
        for key, s in data["conjuntos"].items():
            old = prev.get("conjuntos", {}).get(key)
            if old and s["semLastro"] > old["semLastro"]:
                problems.append(f"{key}: sem lastro subiu {old['semLastro']} -> {s['semLastro']} (elemento novo fora do grafo?)")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="fail if stale or if the counter rose")
    ap.add_argument("--base", help="baseline lastro.js file")
    ap.add_argument("--base-ref", default="origin/main", help="git ref holding the baseline (default: origin/main)")
    args = ap.parse_args()
    data = build()
    if args.check:
        problems = check(data, args.base, args.base_ref)
        for p in problems:
            print("ERRO:", p)
        print(f"sem lastro: {data['semLastro']} de {data['total']}")
        return 1 if problems else 0
    OUT.write_text(render(data), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {data['comLastro']} com lastro ({data['sementes']} sementes), {data['semLastro']} sem lastro, de {data['total']}")
    for key, s in data["conjuntos"].items():
        print(f"  {key:11s} {s['comLastro']:3d}/{s['total']:3d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
