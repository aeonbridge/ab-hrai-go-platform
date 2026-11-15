"""Serialize every regulatory ABox Turtle file to an RDF/XML (.owl) twin.

The Turtle file is the editable source of truth. The .owl file is a generated
RDF/XML serialization of the same graph, kept in sync for OWL tooling
(Protégé, SWRLTab) that prefers RDF/XML.

Usage:
    python scripts/build_regulatory_instances.py          # write .owl files
    python scripts/build_regulatory_instances.py --check  # fail if out of date
"""
from __future__ import annotations

import sys
from pathlib import Path

from rdflib import Graph
from rdflib.compare import isomorphic

INSTANCES_DIR = Path(__file__).resolve().parents[1] / "ontologies" / "regulatory" / "instances"


def instance_files() -> list[Path]:
    """Return ABox Turtle files, skipping macOS AppleDouble metadata (._*)."""
    return sorted(p for p in INSTANCES_DIR.rglob("*.ttl") if not p.name.startswith("._"))


def main(check_only: bool) -> int:
    stale = []
    for ttl_path in instance_files():
        owl_path = ttl_path.with_suffix(".owl")
        graph = Graph().parse(ttl_path, format="turtle")
        if check_only:
            # Compare graphs, not bytes: RDF/XML serialization order is not stable.
            if not owl_path.exists() or not isomorphic(graph, Graph().parse(owl_path, format="xml")):
                stale.append(owl_path)
            continue
        owl_path.write_text(graph.serialize(format="pretty-xml"), encoding="utf-8")
        print(f"wrote {owl_path.relative_to(INSTANCES_DIR.parents[2])} ({len(graph)} triples)")
    if stale:
        print("Out-of-date RDF/XML files:", *map(str, stale), sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv[1:]))
