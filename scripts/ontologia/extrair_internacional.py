#!/usr/bin/env python3
"""Extract the EU, UK and US instruments of the corpus into the graph (ESP-ONT-02, RF-04, RF-14; V-02).

Primary-source extraction (METODO_EXTRACAO.md, section 3), deterministic (pdftotext + regular expressions,
no language model). Each document becomes a SourceSnapshot with the SHA-256 of the PDF and enters as a
pending CandidateAssertion; no review decision is created (invariant I-3).

  EU  AI Act, Regulation (EU) 2024/1689 (OJ L, 12.7.2024): EnactedLegalInstrument, one version, the 113
      articles with title, chapter, section and full text.
  UK  "A pro-innovation approach to AI regulation" (white paper, 2023): PolicyInstrument (non-statutory,
      E1), the five cross-sectoral principles with their definition as written; the impact assessment is
      captured as a snapshot.
  US  NIST AI RMF 1.0 (NIST AI 100-1, 2023): PolicyInstrument (voluntary guide, E1), the four functions with
      their definition as written.

Output: ontologies/regulatory/instances/{eu,uk,us}/HRAI_GO_Regulatory_*.ttl (+ .owl twins via
scripts/build_regulatory_instances.py).

Usage:
  python3 scripts/ontologia/extrair_internacional.py           # regenerate (needs pdftotext)
  python3 scripts/ontologia/extrair_internacional.py --check   # fail if outputs differ (skips without pdftotext)
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

import rdflib
from rdflib import Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS, SKOS, XSD

ROOT = Path(__file__).resolve().parents[2]
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
PBIA = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/br/pbia#")
REPO = "https://github.com/aeonbridge/ab-hrai-go-platform/blob/main/"
DATA = "https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/"

EU_PDF = "docs/ai-regulations/eu/OJ_L_202401689_EN_TXT.pdf"
UK_PDF = "docs/ai-regulations/uk/a-pro-innovation-approach-to-ai-regulation-amended-web-ready.pdf"
UK_IA_PDF = "docs/ai-regulations/uk/uk_ai_regulation_impact_assessment.pdf"
US_PDF = "docs/ai-regulations/us/NIST.AI.100-1.pdf"
UK_PRINCIPLES = ["Safety, security and robustness", "Appropriate transparency and explainability", "Fairness",
                 "Accountability and governance", "Contestability and redress"]
NIST_FUNCTIONS = {"Govern": "GOVERN is a cross-cutting function", "Map": "The MAP function establishes",
                  "Measure": "The MEASURE function employs", "Manage": "The MANAGE function entails"}


def text(pdf: str, layout: bool = False) -> str:
    args = ["pdftotext"] + (["-layout"] if layout else []) + [str(ROOT / pdf), "-"]
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def flat(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def sentences(s: str, n: int) -> str:
    """First n sentences of a passage (definitions are quoted, never paraphrased)."""
    parts = re.split(r"(?<=[.!?])\s+", s)
    return " ".join(parts[:n])


def base(g: rdflib.Graph, ns: rdflib.Namespace, label: str) -> tuple[URIRef, URIRef]:
    for p, n in (("hrai", H), ("pbia", PBIA), ("prov", PROV), ("dcterms", DCTERMS), ("skos", SKOS)):
        g.bind(p, n)
    onto = URIRef(str(ns)[:-1])
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal(label, lang="pt")))
    g.add((onto, RDFS.comment, Literal("Gerado por scripts/ontologia/extrair_internacional.py (pdftotext + expressões regulares, "
                                       "sem LLM). Candidato pendente de revisão humana. Método: METODO_EXTRACAO.md.", lang="pt")))
    agent, batch = ns.ExtratorDeTexto, ns.Lote_Extracao
    g.add((agent, RDF.type, H.MonitoringAgent))
    g.add((agent, RDFS.label, Literal("Extrator de texto (scripts/ontologia/extrair_internacional.py, determinístico)", lang="pt")))
    g.add((batch, RDF.type, H.ExtractionBatch))
    g.add((batch, RDFS.label, Literal("Lote de extração: " + label, lang="pt")))
    return agent, batch


def snapshot(g, ns, key, pdf, label, source_label, source_uri) -> URIRef:
    src, snap = ns["Fonte_" + key], ns["Snapshot_" + key]
    g.add((src, RDF.type, H.LegalSource))
    g.add((src, RDFS.label, Literal(source_label)))
    g.add((src, H.sourceURI, Literal(source_uri, datatype=XSD.anyURI)))
    g.add((snap, RDF.type, H.SourceSnapshot))
    g.add((snap, RDFS.label, Literal(label)))
    g.add((snap, H.snapshotOfSource, src))
    g.add((snap, H.snapshotURI, Literal(REPO + pdf.replace(" ", "%20"), datatype=XSD.anyURI)))
    g.add((snap, H.snapshotSHA256, Literal(hashlib.sha256((ROOT / pdf).read_bytes()).hexdigest())))
    return snap


def candidate(g, ns, agent, batch, snap, subject, label):
    c = ns["Candidate_" + str(subject).split("#")[-1]]
    g.add((c, RDF.type, H.CandidateAssertion))
    g.add((c, RDFS.label, Literal("Candidato: " + label, lang="pt")))
    g.add((c, H.candidateFromSnapshot, snap))
    g.add((c, H.candidateProducedBy, agent))
    g.add((c, DCTERMS.subject, subject))
    g.add((batch, H.extractionContainsCandidate, c))


NOISE_EU = re.compile(r"^\s*\d+/144\s|ELI: http|^OJ L, 12\.7\.2024|^\s*EN\s*$|^\s*L series\s*$")


def aiact_articles(raw: str) -> list[dict]:
    lines = [l for l in raw.splitlines() if not NOISE_EU.search(l)]
    out, cur, chapter, section, skip = [], None, "", "", set()
    for i, l in enumerate(lines):
        s = l.strip()
        if re.fullmatch(r"ANNEX I", s):
            break
        if i in skip:
            continue
        m_ch, m_se, m_ar = re.fullmatch(r"CHAPTER ([IVX]+)", s), re.fullmatch(r"SECTION (\d+)", s), re.fullmatch(r"Article (\d+)", s)
        if m_ch or m_se or m_ar:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            parts = []
            while j < len(lines) and lines[j].strip() and len(parts) < 3 \
                    and not re.fullmatch(r"(CHAPTER [IVX]+|SECTION \d+|Article \d+)", lines[j].strip()):
                nxt = lines[j].strip()
                if parts and not (nxt[0].islower() or nxt.isupper()):
                    break  # continuation of a heading starts lowercase (or is all caps); otherwise the text began
                parts.append(nxt); skip.add(j); j += 1
            title = " ".join(parts)
            if m_ch:
                chapter, section = f"Chapter {m_ch.group(1)} · {title}", ""
            elif m_se:
                section = f"Section {m_se.group(1)} · {title}"
            else:
                cur = {"n": int(m_ar.group(1)), "title": title, "chapter": chapter, "section": section, "lines": []}
                out.append(cur)
            continue
        if cur is not None and s:
            cur["lines"].append(s)
    for a in out:
        a["text"] = flat(" ".join(a["lines"]))
    return out


def build_eu() -> rdflib.Graph:
    g, ns = rdflib.Graph(), rdflib.Namespace(DATA + "eu/aiact#")
    g.bind("eu", ns)
    agent, batch = base(g, ns, "UE: AI Act, Regulamento (UE) 2024/1689, com os artigos (extração de fonte primária)")
    snap = snapshot(g, ns, "AIAct", EU_PDF, "Regulation (EU) 2024/1689 (AI Act), OJ L, 12.7.2024",
                    "Official Journal of the European Union, L series, 2024/1689", "http://data.europa.eu/eli/reg/2024/1689/oj")
    eu, act, ver = PBIA.EuropeanUnion, ns.AIAct, ns.AIAct_2024
    g.add((eu, RDF.type, H.Jurisdiction))
    g.add((act, RDF.type, H.EnactedLegalInstrument))
    g.add((act, RDFS.label, Literal("Regulamento (UE) 2024/1689 (AI Act)", lang="pt")))
    g.add((act, H.instrumentIdentifier, Literal("Regulation (EU) 2024/1689")))
    g.add((act, H.instrumentInJurisdiction, eu))
    g.add((act, H.hasVersion, ver))
    g.add((ver, RDF.type, H.LegalInstrumentVersion))
    g.add((ver, RDFS.label, Literal("AI Act, texto publicado no Jornal Oficial em 12/07/2024", lang="pt")))
    g.add((ver, H.versionOfInstrument, act))
    g.add((ver, H.publishedAtSource, snap))
    g.add((ver, DCTERMS.date, Literal("2024-07-12", datatype=XSD.date)))
    arts = aiact_articles(text(EU_PDF, layout=True))
    for a in arts:
        x = ns[f"Art_{a['n']:03d}"]
        g.add((x, RDF.type, H.LegalProvision))
        g.add((x, RDFS.label, Literal(f"Article {a['n']} · {a['title']}", lang="en")))
        g.add((x, H.legalCitation, Literal(f"Regulation (EU) 2024/1689, Article {a['n']}")))
        g.add((x, H.provisionOfVersion, ver))
        g.add((ver, H.versionContainsProvision, x))
        g.add((x, H.provisionDocumentedIn, snap))
        g.add((x, DCTERMS.description, Literal(a["text"], lang="en")))
        g.add((x, SKOS.notation, Literal(str(a["n"]))))
        g.add((x, SKOS.scopeNote, Literal(a["chapter"] + (f" · {a['section']}" if a["section"] else ""), lang="en")))
    g.add((ver, RDFS.comment, Literal(f"{len(arts)} artigos extraídos (anexos não incluídos).", lang="pt")))
    candidate(g, ns, agent, batch, snap, ver, f"artigos do AI Act ({len(arts)})")
    return g


def build_uk() -> rdflib.Graph:
    g, ns = rdflib.Graph(), rdflib.Namespace(DATA + "uk/whitepaper#")
    g.bind("uk", ns)
    agent, batch = base(g, ns, "Reino Unido: white paper 'A pro-innovation approach to AI regulation' e os cinco princípios")
    snap = snapshot(g, ns, "WhitePaper", UK_PDF, "A pro-innovation approach to AI regulation (white paper, March 2023, amended web version)",
                    "UK Department for Science, Innovation and Technology", "https://www.gov.uk/government/publications/ai-regulation-a-pro-innovation-approach")
    snap_ia = snapshot(g, ns, "ImpactAssessment", UK_IA_PDF, "UK Artificial Intelligence Regulation Impact Assessment (2023)",
                       "UK Department for Science, Innovation and Technology", "https://www.gov.uk/government/publications/ai-regulation-a-pro-innovation-approach")
    uk, wp = ns.UnitedKingdom, ns.WhitePaper2023
    g.add((uk, RDF.type, H.Jurisdiction))
    g.add((uk, RDFS.label, Literal("Reino Unido", lang="pt")))
    g.add((wp, RDF.type, H.PolicyInstrument))
    g.add((wp, RDFS.label, Literal("A pro-innovation approach to AI regulation (white paper, 2023)", lang="en")))
    g.add((wp, H.policyInstrumentInJurisdiction, uk))
    g.add((wp, PROV.wasDerivedFrom, snap))
    g.add((wp, DCTERMS.references, snap_ia))
    raw = flat(text(UK_PDF))
    stat = re.search(r"We will not put these principles on a statutory footing initially\.[^.]*\.", raw)
    g.add((wp, SKOS.scopeNote, Literal("Princípios não estatutários (E1): " + (stat.group(0) if stat else ""), lang="en")))
    for i, name in enumerate(UK_PRINCIPLES, start=1):
        m = re.search(re.escape(name) + r"\s+(?:Definition and explanation\s+)?(AI systems should[^.]*\.|Governance measures should[^.]*\.|Where appropriate[^.]*\.)",
                      raw, re.I)
        x = ns[f"Principio_{i}"]
        g.add((x, RDF.type, H.PolicyInstrument))
        g.add((x, RDFS.label, Literal(name, lang="en")))
        g.add((x, DCTERMS.isPartOf, wp))
        g.add((x, H.policyInstrumentInJurisdiction, uk))
        g.add((x, PROV.wasDerivedFrom, snap))
        if m:
            g.add((x, DCTERMS.description, Literal(m.group(1), lang="en")))
        g.add((x, SKOS.notation, Literal(str(i))))
        candidate(g, ns, agent, batch, snap, x, f"princípio '{name}'")
    candidate(g, ns, agent, batch, snap, wp, "white paper do Reino Unido")
    return g


def build_us() -> rdflib.Graph:
    g, ns = rdflib.Graph(), rdflib.Namespace(DATA + "us/nist#")
    g.bind("us", ns)
    agent, batch = base(g, ns, "EUA: NIST AI Risk Management Framework 1.0 e as quatro funções")
    snap = snapshot(g, ns, "AIRMF", US_PDF, "NIST AI 100-1, Artificial Intelligence Risk Management Framework (AI RMF 1.0), January 2023",
                    "National Institute of Standards and Technology", "https://doi.org/10.6028/NIST.AI.100-1")
    us, rmf = ns.UnitedStates, ns.AIRMF_1_0
    g.add((us, RDF.type, H.Jurisdiction))
    g.add((us, RDFS.label, Literal("Estados Unidos da América", lang="pt")))
    g.add((rmf, RDF.type, H.PolicyInstrument))
    g.add((rmf, RDFS.label, Literal("NIST AI Risk Management Framework (AI RMF 1.0)", lang="en")))
    g.add((rmf, H.policyInstrumentInJurisdiction, us))
    g.add((rmf, PROV.wasDerivedFrom, snap))
    raw = flat(text(US_PDF))
    vol = re.search(r"[^.]*\bvoluntary, rights-preserving[^.]*\.", raw)
    g.add((rmf, SKOS.scopeNote, Literal("Guia voluntário (E1). " + (vol.group(0) if vol else ""), lang="en")))
    for name, start in NIST_FUNCTIONS.items():
        i = raw.find(start)
        x = ns["Function_" + name]
        g.add((x, RDF.type, H.PolicyInstrument))
        g.add((x, RDFS.label, Literal(name.upper(), lang="en")))
        g.add((x, DCTERMS.isPartOf, rmf))
        g.add((x, H.policyInstrumentInJurisdiction, us))
        g.add((x, PROV.wasDerivedFrom, snap))
        if i >= 0:
            g.add((x, DCTERMS.description, Literal(sentences(raw[i:i + 900], 2), lang="en")))
        g.add((x, SKOS.closeMatch, URIRef("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/comparativo#NIST_" + name)))
        candidate(g, ns, agent, batch, snap, x, f"função {name.upper()}")
    candidate(g, ns, agent, batch, snap, rmf, "NIST AI RMF 1.0")
    return g


OUTPUTS = {"eu": (ROOT / "ontologies/regulatory/instances/eu/HRAI_GO_Regulatory_EU_AIAct.ttl", build_eu),
           "uk": (ROOT / "ontologies/regulatory/instances/uk/HRAI_GO_Regulatory_UK_WhitePaper.ttl", build_uk),
           "us": (ROOT / "ontologies/regulatory/instances/us/HRAI_GO_Regulatory_US_NIST.ttl", build_us)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if shutil.which("pdftotext") is None:
        print("pdftotext ausente: extração não verificada")
        return 0 if args.check else 1
    bad = []
    for key, (out, fn) in OUTPUTS.items():
        g = fn()
        if args.check:
            if not (out.exists() and isomorphic(g, rdflib.Graph().parse(out))):
                bad.append(key)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("# Gerado por scripts/ontologia/extrair_internacional.py. Não editar à mão.\n" + g.serialize(format="turtle"), encoding="utf-8")
        print(f"{out.relative_to(ROOT)}: {len(g)} triplas")
    if args.check:
        print("internacional:", "atualizado" if not bad else f"DESATUALIZADO ({', '.join(bad)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
