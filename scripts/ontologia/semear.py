#!/usr/bin/env python3
"""Seed the graph from the project's seed documents (method: docs/especificacoes/ESP-ONT-02/METODO_EXTRACAO.md).

Deterministic, no language model. For every element the chamber shows that has no backing yet, it
creates an individual derived from the seed document, with provenance (snapshot with SHA-256 of the
seed file, cited sources, displayKey) and a CandidateAssertion in an extraction batch. No review
decision is ever created (invariant I-3): seeds stay pending human review.

Seed documents read:
  scenarios/governanca-brasil/model/brasil-governanca-v0.json   components GM-01..GM-22
  scenarios/governanca-brasil/context/2026-11-14.json           context traits CF-01..CF-14, evidence
  scenarios/governanca-brasil/GOV-BR-001.json                   source registry (ids -> URIs)
  ontologies/regulatory/alinhamentos/camara_GM_para_PBIA.ttl    exact/close matches (exact ones are skipped)

Output: ontologies/regulatory/sementes/GOV-BR-001_sementes.ttl

Usage:
  python3 scripts/ontologia/semear.py           # regenerate
  python3 scripts/ontologia/semear.py --check   # fail if the output is out of date
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import rdflib
from rdflib import Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS, SKOS, XSD

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "scenarios/governanca-brasil/model/brasil-governanca-v0.json"
CONTEXT = ROOT / "scenarios/governanca-brasil/context/2026-11-14.json"
SCENARIO = ROOT / "scenarios/governanca-brasil/GOV-BR-001.json"
ALIGN = ROOT / "ontologies/regulatory/alinhamentos/camara_GM_para_PBIA.ttl"
OUT = ROOT / "ontologies/regulatory/sementes/GOV-BR-001_sementes.ttl"

H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
SEM = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/br/sementes#")
PBIA = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/br/pbia#")
GM = "https://github.com/aeonbridge/ab-hrai-go-platform/data/governance/br#"
REPO = "https://github.com/aeonbridge/ab-hrai-go-platform/blob/main/"
FICTIONAL_PREFIX = "BRF-"  # "Brasil fictício" world pack: not a real source

CLASS_BY_KIND = {"institution": H.Stakeholder, "instrument": H.PolicyInstrument, "mechanism": H.PolicyInstrument,
                 "resource": H.PolicyInstrument, "metric": H.PolicyInstrument}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_registry() -> dict[str, dict]:
    """Source ids cited by the seed documents -> title and URI, when registered."""
    reg = {s["id"]: s for s in json.loads(SCENARIO.read_text(encoding="utf-8"))["regulatorySources"]}
    for e in json.loads(CONTEXT.read_text(encoding="utf-8"))["evidence"]:
        reg.setdefault(e["id"], e)
    return reg


def snapshot(g: rdflib.Graph, key: str, path: Path, label: str) -> URIRef:
    s = SEM["Snapshot_" + key]
    g.add((s, RDF.type, H.SourceSnapshot))
    g.add((s, RDFS.label, Literal(label, lang="pt")))
    g.add((s, H.snapshotURI, Literal(REPO + str(path.relative_to(ROOT)), datatype=XSD.anyURI)))
    g.add((s, H.snapshotSHA256, Literal(sha256(path))))
    g.add((s, RDFS.comment, Literal("Documento-semente do projeto (não é fonte oficial): ver METODO_EXTRACAO.md.", lang="pt")))
    return s


def add_sources(g: rdflib.Graph, x: URIRef, ids: list[str], reg: dict[str, dict]) -> None:
    for sid in ids:
        uri = (reg.get(sid) or {}).get("uri", "")
        if uri.startswith("http"):
            g.add((x, DCTERMS.references, URIRef(uri)))
        g.add((x, H.seedSourceId, Literal(sid)))


def candidate(g: rdflib.Graph, batch: URIRef, snap: URIRef, x: URIRef, key: str, label: str) -> None:
    c = SEM["Candidate_" + key]
    g.add((c, RDF.type, H.CandidateAssertion))
    g.add((c, RDFS.label, Literal("Semente: " + label, lang="pt")))
    g.add((c, H.candidateFromSnapshot, snap))
    g.add((c, H.candidateProducedBy, SEM.ExtratorDeSementes))
    g.add((c, DCTERMS.subject, x))
    g.add((batch, H.extractionContainsCandidate, c))


def build() -> rdflib.Graph:
    g = rdflib.Graph()
    for p, ns in (("hrai", H), ("sem", SEM), ("pbia", PBIA), ("prov", PROV), ("dcterms", DCTERMS), ("skos", SKOS)):
        g.bind(p, ns)
    onto = URIRef(str(SEM)[:-1])
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal("Sementes do cenário GOV-BR-001: elementos da câmara derivados de documentos-semente", lang="pt")))
    g.add((onto, RDFS.comment, Literal(
        "Gerado por scripts/ontologia/semear.py (determinístico). Método: docs/especificacoes/ESP-ONT-02/METODO_EXTRACAO.md. "
        "Tudo aqui é semente pendente de revisão humana; nada é fonte primária.", lang="pt")))

    # Provenance annotations (seedSourceId, seedVerification, seedBasis, seedHasRealSource) are declared in the core.
    agent = SEM.ExtratorDeSementes
    g.add((agent, RDF.type, H.MonitoringAgent))
    g.add((agent, RDFS.label, Literal("Extrator de sementes (scripts/ontologia/semear.py, determinístico, sem modelo de linguagem)", lang="pt")))
    batch = SEM.Lote_Sementes_GOV_BR_001
    g.add((batch, RDF.type, H.ExtractionBatch))
    g.add((batch, RDFS.label, Literal("Lote de sementes do cenário GOV-BR-001", lang="pt")))

    snap_model = snapshot(g, "ModeloCamara", MODEL, "Modelo da câmara brasil-governanca-v0 (documento-semente)")
    snap_ctx = snapshot(g, "Contexto", CONTEXT, "Contexto nacional de 14/11/2026 (documento-semente)")
    reg = source_registry()

    align = rdflib.Graph().parse(ALIGN)
    exact = {str(s)[len(GM):] for s in align.subjects(SKOS.exactMatch, None)}
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    for c in model["components"]:
        if c["id"] in exact:
            continue  # already backed by a primary-source individual
        key = c["id"].replace("-", "_")
        x = SEM["Componente_" + key]
        g.add((x, RDF.type, OWL.NamedIndividual))
        g.add((x, RDF.type, CLASS_BY_KIND[c["kind"]]))
        g.add((x, RDFS.label, Literal(c["title"], lang="pt")))
        g.add((x, RDFS.comment, Literal(c["description"], lang="pt")))
        if c.get("notes"):
            g.add((x, SKOS.editorialNote, Literal(c["notes"], lang="pt")))
        g.add((x, SKOS.notation, Literal(c["id"])))
        g.add((x, H.displayKey, Literal("components:" + c["id"])))
        g.add((x, PROV.wasDerivedFrom, snap_model))
        g.add((x, H.seedVerification, Literal(c.get("verification", "unknown"))))
        g.add((x, H.seedBasis, Literal("documentado" if c.get("origin") == "documented" else "hipótese de trabalho")))
        if c.get("legalStatus") == "proposed":
            g.add((x, DCTERMS.isPartOf, PBIA.PL_2338_2023))
            g.add((x, SKOS.scopeNote, Literal("Previsto em proposta legislativa: sem força vinculante.", lang="pt")))
        elif c.get("legalStatus") == "policy" and any(s.startswith("PBIA") for s in c["sourceIds"]):
            g.add((x, DCTERMS.isPartOf, PBIA.PBIA_Plan))
        add_sources(g, x, c["sourceIds"], reg)
        for near in align.objects(URIRef(GM + c["id"]), SKOS.closeMatch):
            g.add((x, SKOS.closeMatch, near))
        candidate(g, batch, snap_model, x, key, c["title"])

    ctx = json.loads(CONTEXT.read_text(encoding="utf-8"))
    for f in ctx["features"]:
        key = f["id"].replace("-", "_")
        x = SEM["Traco_" + key]
        real = [s for s in f["sourceIds"] if not s.startswith(FICTIONAL_PREFIX)]
        g.add((x, RDF.type, OWL.NamedIndividual))
        g.add((x, RDF.type, H.ContextIndicator))
        g.add((x, RDFS.label, Literal(f["title"], lang="pt")))
        g.add((x, RDFS.comment, Literal(f.get("description", ""), lang="pt")))
        g.add((x, SKOS.notation, Literal(f["id"])))
        g.add((x, H.displayKey, Literal("features:" + f["id"])))
        g.add((x, H.indicatorRelevantToJurisdiction, PBIA.Brazil))
        g.add((x, H.hasIndicatorMethod, Literal(f"traço qualitativo ({f['kind']}) do documento de contexto; sem valor numérico nem ano-base")))
        g.add((x, PROV.wasDerivedFrom, snap_ctx))
        g.add((x, H.seedVerification, Literal(f.get("verification", "unknown"))))
        g.add((x, H.seedBasis, Literal("documentado" if f.get("basis") == "documented" else "hipótese de trabalho")))
        g.add((x, H.seedHasRealSource, Literal(bool(real))))
        add_sources(g, x, f["sourceIds"], reg)
        candidate(g, batch, snap_ctx, x, key, f["title"])
    return g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    g = build()
    if args.check:
        ok = OUT.exists() and isomorphic(g, rdflib.Graph().parse(OUT))
        print("sementes:", "atualizadas" if ok else "DESATUALIZADAS: rode python3 scripts/ontologia/semear.py")
        return 0 if ok else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    header = ("# Gerado por scripts/ontologia/semear.py. Não editar à mão.\n"
              "# Método: docs/especificacoes/ESP-ONT-02/METODO_EXTRACAO.md. Sementes pendentes de revisão humana.\n")
    OUT.write_text(header + g.serialize(format="turtle"), encoding="utf-8")
    comps = len(set(g.subjects(SKOS.notation, None)) & set(g.subjects(H.displayKey, None)))
    print(f"{OUT.relative_to(ROOT)}: {len(g)} triplas, {comps} elementos semeados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
