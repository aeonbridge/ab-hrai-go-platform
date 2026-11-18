#!/usr/bin/env python3
"""Extract the PL 2338/2023 texts into the graph as two versions with their articles (ESP-ONT-02, RF-01).

Primary-source extraction (METODO_EXTRACAO.md, section 3), deterministic: ``pdftotext -layout`` plus
regular expressions, no language model. For each text it records:

  - the LegalSource and a SourceSnapshot with the SHA-256 of the PDF in docs/ai-regulations/br;
  - a LegalInstrumentVersion of pbia:PL_2338_2023 (the 2024 Senate text has previousLegalVersion the 2023 text);
  - one LegalProvision per article: citation, caput as label, full text (page headers removed),
    chapter and section, documented in the snapshot;
  - a RegulatoryChangeEvent for the arrival of the Senate text (rules R10-R13 propagate potential impact);
  - an ExtractionBatch with one CandidateAssertion per version. No review decision (invariant I-3).

Observed in the Senate text (PDF of the Chamber, codteor 2868197): articles are numbered up to 80 and
art. 31 does not appear anywhere in the document, so there are 79 articles. Recorded, not corrected.

Output: ontologies/regulatory/instances/br/HRAI_GO_Regulatory_BR_PL2338.ttl (+ .owl twin via
scripts/build_regulatory_instances.py).

Usage:
  python3 scripts/ontologia/extrair_pl2338.py           # regenerate (needs pdftotext)
  python3 scripts/ontologia/extrair_pl2338.py --check   # fail if the output differs (skips without pdftotext)
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
from rdflib.namespace import DCTERMS, PROV, RDF, RDFS, SKOS, XSD

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ontologies/regulatory/instances/br/HRAI_GO_Regulatory_BR_PL2338.ttl"
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
PL = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/br/pl2338#")
PBIA = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/br/pbia#")
REPO = "https://github.com/aeonbridge/ab-hrai-go-platform/blob/main/"

VERSIONS = [
    {"key": "2023", "pdf": "docs/ai-regulations/br/DOC-SF238339076816-20230503.pdf",
     "rotulo": "PL 2338/2023, texto inicial (Senado Federal, 03/05/2023)", "id": "texto inicial",
     "citacao": "PL 2338/2023 (texto inicial, 2023)", "data": "2023-05-03", "fonte": "Fonte_SenadoTextoInicial",
     "fonteRotulo": "Senado Federal: PL 2338/2023, texto inicial (documento SF/23833.90768-16)",
     "fonteUri": "https://www25.senado.leg.br/web/atividade/materias/-/materia/157233"},
    {"key": "2024", "pdf": "docs/ai-regulations/br/PL2338-2023_texto-aprovado-Senado-2024_Camara-20250317.pdf",
     "rotulo": "PL 2338/2023, texto aprovado pelo Senado em 10/12/2024 (inteiro teor na Câmara, 17/03/2025)",
     "id": "texto aprovado pelo Senado (2024)", "citacao": "PL 2338/2023 (texto do Senado, 2024)", "data": "2024-12-10",
     "fonte": "Fonte_CamaraInteiroTeor", "fonteRotulo": "Câmara dos Deputados: inteiro teor do PL 2338/2023 (codteor 2868197)",
     "fonteUri": "https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2868197"},
]
NOISE = re.compile(r"Apresentação: \d|PL n\.2338/2023|Autenticado Eletronicamente|SF/\d{5}\.\d{5}-\d{2}|PROJETO DE LEI Nº|\*CD\d+\*|ivb/pl")
# The bill ends where the justification (2023) or the signature block (2024) starts.
END = re.compile(r"^\s*(JUSTIFICAÇÃO|Senado Federal, em \d)")
ART = re.compile(r"^\s*Art\. ?(\d+)(?:º|°|\.)?\s*(.*)$")


def pdf_text(path: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True).stdout


def articles(text: str) -> list[dict]:
    """Split the bill into articles, carrying the current chapter and section headings."""
    lines = [l for l in text.splitlines() if not NOISE.search(l) and not re.fullmatch(r"\s*\d{1,3}\s*", l)]
    out, cur, chapter, section, skip = [], None, "", "", set()
    for i, raw in enumerate(lines):
        if END.match(raw):
            break
        line = raw.strip()
        if i in skip:
            continue
        m_ch, m_se = re.fullmatch(r"CAPÍTULO ([IVXL]+)", line), re.fullmatch(r"Seção ([IVXL]+)", line)
        if m_ch or m_se:
            # Heading title: the following non-empty lines up to the first blank line or article (max 3 lines).
            j, parts = i + 1, []
            while j < len(lines) and not lines[j].strip():
                j += 1
            while (j < len(lines) and lines[j].strip() and not ART.match(lines[j]) and len(parts) < 3
                   and not re.fullmatch(r"(CAPÍTULO|Seção) [IVXL]+", lines[j].strip())):
                parts.append(lines[j].strip()); skip.add(j); j += 1
            title = " ".join(parts)
            if m_ch:
                chapter, section = f"Capítulo {m_ch.group(1)} · {title}", ""
            else:
                section = f"Seção {m_se.group(1)} · {title}"
            continue
        m = ART.match(raw)
        if m:
            cur = {"n": int(m.group(1)), "chapter": chapter, "section": section, "lines": [m.group(2).strip()]}
            out.append(cur)
        elif cur is not None and line:
            cur["lines"].append(line)
    for a in out:
        a["text"] = re.sub(r"\s+", " ", " ".join(a["lines"])).strip()
        caput = re.split(r"\s(?:§ ?\d|Parágrafo único|I – |I - )", a["text"], maxsplit=1)[0]
        a["caput"] = caput if len(caput) <= 220 else caput[:217].rsplit(" ", 1)[0] + "…"
    return out


def build() -> rdflib.Graph:
    g = rdflib.Graph()
    for p, ns in (("hrai", H), ("pl", PL), ("pbia", PBIA), ("prov", PROV), ("dcterms", DCTERMS), ("skos", SKOS)):
        g.bind(p, ns)
    onto = URIRef(str(PL)[:-1])
    g.add((onto, RDF.type, rdflib.OWL.Ontology))
    g.add((onto, RDFS.label, Literal("PL 2338/2023: textos de 2023 e de 2024 com os artigos (extração de fonte primária)", lang="pt")))
    g.add((onto, RDFS.comment, Literal("Gerado por scripts/ontologia/extrair_pl2338.py (pdftotext + expressões regulares, sem LLM). "
                                       "Candidato pendente de revisão humana. Método: docs/especificacoes/ESP-ONT-02/METODO_EXTRACAO.md.", lang="pt")))
    agent, batch = PL.ExtratorDeTexto, PL.Lote_PL2338_Textos
    g.add((agent, RDF.type, H.MonitoringAgent))
    g.add((agent, RDFS.label, Literal("Extrator de texto legislativo (scripts/ontologia/extrair_pl2338.py, determinístico)", lang="pt")))
    g.add((batch, RDF.type, H.ExtractionBatch))
    g.add((batch, RDFS.label, Literal("Lote de extração: PL 2338/2023, textos de 2023 e 2024", lang="pt")))
    # Same typing as the PBIA instance, repeated so this file validates on its own.
    g.add((PBIA.PL_2338_2023, RDF.type, H.LegislativeProposal))
    g.add((PBIA.Brazil, RDF.type, H.Jurisdiction))
    previous = None
    for v in VERSIONS:
        pdf = ROOT / v["pdf"]
        src, snap, ver = PL[v["fonte"]], PL["Snapshot_" + v["key"]], PL["Versao_" + v["key"]]
        g.add((src, RDF.type, H.LegalSource))
        g.add((src, RDFS.label, Literal(v["fonteRotulo"], lang="pt")))
        g.add((src, H.sourceURI, Literal(v["fonteUri"], datatype=XSD.anyURI)))
        g.add((snap, RDF.type, H.SourceSnapshot))
        g.add((snap, RDFS.label, Literal(v["rotulo"], lang="pt")))
        g.add((snap, H.snapshotOfSource, src))
        g.add((snap, H.snapshotURI, Literal(REPO + v["pdf"].replace(" ", "%20"), datatype=XSD.anyURI)))
        g.add((snap, H.snapshotSHA256, Literal(hashlib.sha256(pdf.read_bytes()).hexdigest())))
        g.add((ver, RDF.type, H.LegalInstrumentVersion))
        g.add((ver, RDFS.label, Literal(v["rotulo"], lang="pt")))
        g.add((ver, H.versionIdentifier, Literal(v["id"])))
        g.add((ver, H.versionOfInstrument, PBIA.PL_2338_2023))
        g.add((PBIA.PL_2338_2023, H.hasVersion, ver))
        g.add((ver, H.publishedAtSource, snap))
        g.add((ver, DCTERMS.date, Literal(v["data"], datatype=XSD.date)))
        if previous is not None:
            g.add((ver, H.previousLegalVersion, previous))
        arts = articles(pdf_text(pdf))
        numbers = [a["n"] for a in arts]
        missing = sorted(set(range(1, max(numbers) + 1)) - set(numbers))
        g.add((ver, RDFS.comment, Literal(f"{len(arts)} artigos extraídos, numerados até {max(numbers)}"
                                          + (f"; ausentes no documento: art. {', '.join(map(str, missing))}" if missing else "") + ".", lang="pt")))
        for a in arts:
            x = PL[f"Art_{v['key']}_{a['n']:03d}"]
            g.add((x, RDF.type, H.LegalProvision))
            g.add((x, RDFS.label, Literal(f"Art. {a['n']} · {a['caput']}", lang="pt")))
            g.add((x, H.legalCitation, Literal(f"{v['citacao']}, art. {a['n']}")))
            g.add((x, H.provisionOfVersion, ver))
            g.add((ver, H.versionContainsProvision, x))
            g.add((x, H.provisionDocumentedIn, snap))
            g.add((x, DCTERMS.description, Literal(a["text"], lang="pt")))
            g.add((x, SKOS.notation, Literal(str(a["n"]))))
            if a["chapter"]:
                g.add((x, SKOS.scopeNote, Literal(a["chapter"] + (f" · {a['section']}" if a["section"] else ""), lang="pt")))
        cand = PL["Candidate_" + v["key"]]
        g.add((cand, RDF.type, H.CandidateAssertion))
        g.add((cand, RDFS.label, Literal(f"Candidato: artigos do {v['rotulo']} ({len(arts)} artigos)", lang="pt")))
        g.add((cand, H.candidateFromSnapshot, snap))
        g.add((cand, H.candidateProducedBy, agent))
        g.add((cand, DCTERMS.subject, ver))
        g.add((batch, H.extractionContainsCandidate, cand))
        previous = ver
    ev = PL.Mudanca_TextoSenado2024
    g.add((ev, RDF.type, H.RegulatoryChangeEvent))
    g.add((ev, RDFS.label, Literal("Chega ao corpus o texto do PL 2338/2023 aprovado pelo Senado (2024)", lang="pt")))
    g.add((ev, H.changeAffectsVersion, PL.Versao_2024))
    g.add((ev, H.changeObservedInSnapshot, PL.Snapshot_2024))
    g.add((ev, H.changeHasSource, PL.Fonte_CamaraInteiroTeor))
    g.add((ev, H.changeDescription, Literal("Nova versão do mesmo instrumento; continua proposta. Codificações e teses ligadas à versão de 2023 devem ser revistas (E5).", lang="pt")))
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
        print("PL 2338:", "atualizado" if ok else "DESATUALIZADO: rode python3 scripts/ontologia/extrair_pl2338.py")
        return 0 if ok else 1
    OUT.write_text("# Gerado por scripts/ontologia/extrair_pl2338.py. Não editar à mão.\n" + g.serialize(format="turtle"), encoding="utf-8")
    for v in VERSIONS:
        n = len(list(g.objects(PL["Versao_" + v["key"]], H.versionContainsProvision)))
        print(f"{v['key']}: {n} artigos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
