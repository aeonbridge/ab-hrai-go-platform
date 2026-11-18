#!/usr/bin/env python3
"""China in the corpus (ESP-ONT-02, RF-02, decision D-01 by the author on 17/11/2026: include China).

The corpus has two SECONDARY sources on China and no official Chinese text:
  - Regulations.AI, "China AI Regulation Overview" (RAI-CN-NA-SUMMARY-2026, generated 17/11/2026): 4 pages
    of images, no extractable text. The instrument list below was TRANSCRIBED from those images by the
    loop session (LLM reading the page images), not parsed.
  - Law Library of Congress, "China: Regulation of Artificial Intelligence" (June 2023, LL File No.
    2023-022300): text. Every instrument whose name appears in it is also referenced to it, checked
    automatically here.

Everything enters as a pending candidate flagged as secondary-source; an instrument is never shown as
verified against an official text. Adding the official texts (CAC, NPC) is recorded as pending.

Output: ontologies/regulatory/em-espera/cn/HRAI_GO_Regulatory_CN.ttl

ON HOLD (decision D-01b, 17/11/2026): China stays OUT of the comparison for now, so that adding a new
jurisdiction, and measuring its impact, can be validated later. The file is generated in em-espera/,
which no pipeline loads. To add China: move it to ontologies/regulatory/instances/cn/, run
scripts/build_regulatory_instances.py and the CI; acceptance query V30 then lists every QN1
specificity that needs a comparison with China, and the monitoring shows what is reopened.

Usage:
  python3 scripts/ontologia/extrair_china.py           # regenerate (needs pdftotext)
  python3 scripts/ontologia/extrair_china.py --check   # fail if the output differs (skips without pdftotext)
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
OUT = ROOT / "ontologies/regulatory/em-espera/cn/HRAI_GO_Regulatory_CN.ttl"
H = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/regulatory#")
CN = rdflib.Namespace("https://hrai-go.aeonbridge.io/data/regulatory/cn/china#")
REPO = "https://github.com/aeonbridge/ab-hrai-go-platform/blob/main/"
OVERVIEW = "docs/ai-regulations/ch/China-china-ai-regulation-overview.pdf"
LOC = "docs/ai-regulations/ch/service-ll-llglrd-2023555933-2023555933.pdf"
SECONDARY = "Fonte secundária: não há texto oficial chinês no corpus."

# (id, name as written in the overview, year, kind, name to look for in the LoC report or None)
#   kind: law = statute of the NPC Standing Committee; regulation = binding administrative or departmental rule;
#         standard = non-binding technical standard or guideline; plan = strategic plan; draft = proposal
INSTRUMENTS = [
    ("CybersecurityLaw", "Cybersecurity Law of the PRC (2016, amended 2025)", "2016", "law", "Cybersecurity Law"),
    ("DataSecurityLaw", "Data Security Law of the PRC (2021)", "2021", "law", "Data Security Law"),
    ("PIPL", "Personal Information Protection Law of the PRC (PIPL) (2021)", "2021", "law", "Personal Information Protection Law"),
    ("AlgorithmicRecommendation", "Provisions on the Administration of Algorithmic Recommendation in Internet Information Services (2021)", "2021", "regulation", "Algorithmic Recommendation"),
    ("DeepSynthesis", "Provisions on the Administration of Deep Synthesis of Internet-based Information Services (2022)", "2022", "regulation", "Deep Synthesis"),
    ("GenerativeAIMeasures", "Interim Measures for the Administration of Generative AI Services (2023)", "2023", "regulation", "Generative AI Measures"),
    ("NetworkDataSecurity", "Regulations on Network Data Security Management (2024)", "2024", "regulation", None),
    ("AIContentLabeling", "Administrative Measures for the Labeling of AI-Generated Content / Measures for Identification (2025)", "2025", "regulation", None),
    ("AnthropomorphicAI", "Interim Measures for the Administration of Anthropomorphic AI Interaction Services (2025/2026)", "2025", "regulation", None),
    ("AgentInterconnection", "Artificial Intelligence - Agent Interconnection (GB/Z 185-2026)", "2026", "standard", None),
    ("AIMeasurementGuidelines", "Guidelines for AI Measurement System and Capability Building (2026 Edition)", "2026", "standard", None),
    ("EthicsSafetyGuidelines", "Ethics-Safety Guidelines for Artificial Intelligence Applications 1.0 (2026)", "2026", "standard", None),
    ("DigitalVirtualHumanDraft", "Administrative Measures for Digital Virtual Human Information Services (Draft 2026)", "2026", "draft", None),
    ("DevelopmentPlan2017", "New Generation Artificial Intelligence Development Plan (2017)", "2017", "plan", "New Generation Artificial Intelligence Development Plan"),
]
# Enforcement bodies, from the table on page 4 of the overview.
AUTHORITIES = [("CAC", "Cyberspace Administration of China (CAC)"), ("MIIT", "Ministry of Industry and Information Technology (MIIT)"),
               ("MPS", "Ministry of Public Security (MPS)"), ("SAMR", "State Administration for Market Regulation (SAMR)"),
               ("MOST", "Ministry of Science and Technology (MOST)"), ("NDRC", "National Development and Reform Commission (NDRC)"),
               ("TC260", "National Technical Committee 260 on Cybersecurity (TC260)")]
KIND_CLASS = {"law": H.EnactedLegalInstrument, "regulation": H.EnactedLegalInstrument, "standard": H.PolicyInstrument,
              "plan": H.PolicyInstrument, "draft": H.LegislativeProposal}
KIND_NOTE = {"law": "lei aprovada pelo Comitê Permanente da Assembleia Popular Nacional, segundo a fonte",
             "regulation": "regra administrativa ou departamental vinculante, segundo a fonte",
             "standard": "norma técnica ou guia não vinculante (E1), segundo a fonte",
             "plan": "plano estratégico (E1), segundo a fonte", "draft": "minuta, ainda não promulgada, segundo a fonte"}


def snapshot(g, key, pdf, label, publisher) -> URIRef:
    src, snap = CN["Fonte_" + key], CN["Snapshot_" + key]
    g.add((src, RDF.type, H.LegalSource))
    g.add((src, RDFS.label, Literal(publisher)))
    g.add((snap, RDF.type, H.SourceSnapshot))
    g.add((snap, RDFS.label, Literal(label)))
    g.add((snap, H.snapshotOfSource, src))
    g.add((snap, H.snapshotURI, Literal(REPO + pdf, datatype=XSD.anyURI)))
    g.add((snap, H.snapshotSHA256, Literal(hashlib.sha256((ROOT / pdf).read_bytes()).hexdigest())))
    g.add((snap, RDFS.comment, Literal(SECONDARY, lang="pt")))
    return snap


def build() -> rdflib.Graph:
    g = rdflib.Graph()
    for p, ns in (("hrai", H), ("cn", CN), ("prov", PROV), ("dcterms", DCTERMS), ("skos", SKOS)):
        g.bind(p, ns)
    onto = URIRef(str(CN)[:-1])
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal("China: instrumentos e autoridades de governança de IA, segundo fontes secundárias", lang="pt")))
    g.add((onto, RDFS.comment, Literal("Gerado por scripts/ontologia/extrair_china.py. Decisão D-01 (autor, 17/11/2026): incluir a China. "
                                       + SECONDARY + " Lista transcrita das imagens do overview pela sessão do loop (LLM); "
                                       "presença no relatório da Law Library of Congress conferida automaticamente.", lang="pt")))
    agent, batch = CN.SessaoLoop, CN.Lote_China
    g.add((agent, RDF.type, H.MonitoringAgent))
    g.add((agent, RDFS.label, Literal("Sessão do loop ESP-ONT-02 (Claude Code; transcrição de PDF em imagem assistida por LLM)", lang="pt")))
    g.add((batch, RDF.type, H.ExtractionBatch))
    g.add((batch, RDFS.label, Literal("Lote: China, fontes secundárias", lang="pt")))
    s_ov = snapshot(g, "Overview", OVERVIEW, "Regulations.AI, China AI Regulation Overview (RAI-CN-NA-SUMMARY-2026), gerado em 17/11/2026", "Regulations.AI")
    s_loc = snapshot(g, "LawLibrary", LOC, "Law Library of Congress, China: Regulation of Artificial Intelligence (June 2023)", "Law Library of Congress")
    loc_text = re.sub(r"\s+", " ", subprocess.run(["pdftotext", str(ROOT / LOC), "-"], capture_output=True, text=True, check=True).stdout)
    cn = CN.China
    g.add((cn, RDF.type, H.Jurisdiction))
    g.add((cn, RDFS.label, Literal("China", lang="pt")))
    g.add((cn, RDFS.comment, Literal(SECONDARY + " Incluir os textos oficiais (CAC, Assembleia Popular Nacional) é pendência.", lang="pt")))
    for key, name, year, kind, loc_name in INSTRUMENTS:
        x = CN[key]
        g.add((x, RDF.type, KIND_CLASS[kind]))
        g.add((x, RDFS.label, Literal(name, lang="en")))
        g.add((x, DCTERMS.date, Literal(year, datatype=XSD.gYear)))
        g.add((x, SKOS.scopeNote, Literal(f"{KIND_NOTE[kind].capitalize()}. {SECONDARY}", lang="pt")))
        g.add((x, PROV.wasDerivedFrom, s_ov))
        if kind == "draft":
            g.add((x, H.proposalInJurisdiction, cn))
            g.add((x, H.instrumentInJurisdiction, cn))
        elif kind in ("law", "regulation"):
            g.add((x, H.instrumentInJurisdiction, cn))
        else:
            g.add((x, H.policyInstrumentInJurisdiction, cn))
        if loc_name and loc_name in loc_text:
            g.add((x, DCTERMS.references, s_loc))  # also described in the Law Library of Congress report (2023)
        c = CN["Candidate_" + key]
        g.add((c, RDF.type, H.CandidateAssertion))
        g.add((c, RDFS.label, Literal("Candidato (fonte secundária): " + name, lang="pt")))
        g.add((c, H.candidateFromSnapshot, s_ov))
        g.add((c, H.candidateProducedBy, agent))
        g.add((c, DCTERMS.subject, x))
        g.add((batch, H.extractionContainsCandidate, c))
    for key, name in AUTHORITIES:
        a = CN["Autoridade_" + key]
        g.add((a, RDF.type, H.Stakeholder))
        g.add((a, RDFS.label, Literal(name, lang="en")))
        g.add((a, PROV.wasDerivedFrom, s_ov))
        g.add((a, DCTERMS.spatial, cn))
    return g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if shutil.which("pdftotext") is None:
        print("pdftotext ausente: extração não verificada")
        return 0 if args.check else 1
    g = build()
    if args.check:
        ok = OUT.exists() and isomorphic(g, rdflib.Graph().parse(OUT))
        print("China:", "atualizado" if ok else "DESATUALIZADO: rode python3 scripts/ontologia/extrair_china.py")
        return 0 if ok else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("# Gerado por scripts/ontologia/extrair_china.py. Não editar à mão. Fontes secundárias.\n" + g.serialize(format="turtle"), encoding="utf-8")
    confirmed = len(list(g.subject_objects(DCTERMS.references)))
    print(f"{OUT.relative_to(ROOT)}: {len(INSTRUMENTS)} instrumentos ({confirmed} também no relatório da LoC), {len(AUTHORITIES)} autoridades")
    return 0


if __name__ == "__main__":
    sys.exit(main())
