#!/usr/bin/env python3
"""Record the author's decisions in the graph (invariant I-3: approval is human; the session only transcribes).

Reads docs/especificacoes/ESP-ONT-02/decisoes.json, where each decision has the date and the exact message in
which the author decided, and writes one hrai:ApprovalDecision per decision, attributed to the author
(hrai:ReviewActor). Each candidate of the batches the decision covers gets hrai:hasReviewDecision; each
provision correspondence covered gets hrai:correspondenceReview, which lets rule R26 infer transposition.

Output: ontologies/regulatory/decisoes/decisoes_autor.ttl

Usage:
  python3 scripts/ontologia/registrar_decisoes.py           # regenerate
  python3 scripts/ontologia/registrar_decisoes.py --check   # fail if the output differs
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import rdflib
from rdflib import Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, PROV, RDF, RDFS, XSD

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "docs/especificacoes/ESP-ONT-02/decisoes.json"
OUT = ROOT / "ontologies/regulatory/decisoes/decisoes_autor.ttl"
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
DEC = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/decisoes#")


def graph_of_batches() -> rdflib.Graph:
    g = rdflib.Graph()
    for f in sorted(glob.glob(str(ROOT / "ontologies/regulatory/**/*.ttl"), recursive=True)):
        if not Path(f).name.startswith("._") and "/decisoes/" not in f:
            g.parse(f)
    return g


def build() -> rdflib.Graph:
    log = json.loads(LOG.read_text(encoding="utf-8"))
    src = graph_of_batches()
    g = rdflib.Graph()
    g.bind("hrai", H); g.bind("dec", DEC)
    onto = URIRef(str(DEC)[:-1])
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal("Decisões humanas do autor (transcritas de decisoes.json)", lang="pt")))
    author = DEC.Autor
    g.add((author, RDF.type, H.ReviewActor))
    g.add((author, RDFS.label, Literal(log["autor"] + " (autor do trabalho)", lang="pt")))
    for d in log["decisoes"]:
        x = DEC[d["id"].replace("-", "_")]
        g.add((x, RDF.type, H.ApprovalDecision))
        g.add((x, RDFS.label, Literal(f"{d['id']}: {d['decisao']}", lang="pt")))
        g.add((x, H.reviewDecisionBy, author))
        g.add((x, H.approvalRecordedAt, Literal(d["data"], datatype=XSD.dateTime)))
        g.add((x, H.approvedReason, Literal(f"Mensagem do autor: \"{d['mensagem']}\"")))
        g.add((x, PROV.wasAttributedTo, author))
        for v in d.get("valores", []):   # values the author set (for example an alert threshold)
            g.add((URIRef(v["sujeito"]), URIRef(v["propriedade"]), Literal(v["valor"], datatype=XSD.decimal)))
            g.add((URIRef(v["sujeito"]), rdflib.namespace.DCTERMS.isReferencedBy, x))
        for target in d.get("aprovados", []):   # individuals approved directly (alignments, links)
            g.add((URIRef(target), rdflib.namespace.DCTERMS.isReferencedBy, x))
        for batch in d.get("lotes", []):
            for cand in src.objects(URIRef(batch), H.extractionContainsCandidate):
                g.add((cand, H.hasReviewDecision, x))
                if d.get("correspondencias"):
                    subject = src.value(cand, rdflib.namespace.DCTERMS.subject)
                    if subject is not None and (subject, RDF.type, H.ProvisionCorrespondence) in src:
                        g.add((subject, H.correspondenceReview, x))
    return g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    g = build()
    if args.check:
        ok = OUT.exists() and isomorphic(g, rdflib.Graph().parse(OUT))
        print("decisões:", "atualizadas" if ok else "DESATUALIZADAS: rode python3 scripts/ontologia/registrar_decisoes.py")
        return 0 if ok else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("# Gerado por scripts/ontologia/registrar_decisoes.py a partir de decisoes.json. Decisões do autor.\n"
                   + g.serialize(format="turtle"), encoding="utf-8")
    n = len(list(g.subject_objects(H.hasReviewDecision)))
    print(f"{OUT.relative_to(ROOT)}: {len(list(g.subjects(RDF.type, H.ApprovalDecision)))} decisões, {n} candidatos revisados, "
          f"{len(list(g.subject_objects(H.correspondenceReview)))} correspondências revisadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
