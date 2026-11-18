#!/usr/bin/env python3
"""Build the comparative module of HRAI-GO (ESP-ONT-02, RF-16).

Sources:
  ontologies/comparativo/alanoca2025-definicoes.json  12 categories and 25 criteria of Alanoca et al.
                                                      (FAccT '25), definitions copied verbatim.
  EXTENSIONS below                                    declared extensions E1-E7, with credit and DOI.
  ontologies/comparativo/areas.json                   substantive areas (E3, RF-05): the 28 chamber areas
                                                      plus generative AI/GPAI, with PROPOSED mappings to
                                                      NIST AI RMF functions, AI Act chapters and criteria.

Output: ontologies/comparativo/HRAI_GO_Comparativo.ttl (+ .owl twin). The module imports the core
(``hrai:RegulatoryDesignCriterion``, ``hrai:CriterionCoding``) and holds rule R28 (design profile),
which combines coded values. Scales of the criteria (E4) are NOT here: they are a proposal awaiting
human approval (docs/especificacoes/ESP-ONT-02/escalas-E4-proposta.md, decision D-02).

Usage:
  python3 scripts/ontologia/build_comparativo.py           # regenerate
  python3 scripts/ontologia/build_comparativo.py --check   # fail if the files are out of date
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import rdflib
from rdflib import Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))
import swrl_texto  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "ontologies/comparativo"
DEFS = DIR / "alanoca2025-definicoes.json"
AREAS = DIR / "areas.json"
SCALES = DIR / "escalas-E4.json"
D02 = URIRef("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/decisoes#D_02")
D03 = URIRef("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/decisoes#D_03")
TTL = DIR / "HRAI_GO_Comparativo.ttl"
OWL_FILE = DIR / "HRAI_GO_Comparativo.owl"
BASE = "https://github.com/aeonbridge/ab-hrai-go-platform/ontology"
C = rdflib.Namespace(BASE + "/comparativo#")
H = rdflib.Namespace(BASE + "/regulatory#")
DOI = URIRef("https://doi.org/10.1145/3715275.3732059")
CREDIT = ("Extensão declarada da taxonomia de Alanoca, Gur-Arieh, Zick e Klyman (2025), Comparing Apples to Oranges, "
          "FAccT '25, doi:10.1145/3715275.3732059. Não altera as definições originais.")

# Declared extensions (ESP-ONT-02, chapter on the base taxonomy; RT-VIS-03, Tabela 3).
EXTENSIONS = [
    ("E1_LegalForm", "Forma jurídica", "Legal form",
     "Amplia o critério Status para instrumentos não vinculantes: lei, projeto de lei, plano, princípios não estatutários e guia voluntário.",
     "PBIA (plano), Reino Unido (princípios não estatutários), NIST AI RMF (guia voluntário)."),
    ("E2_PrimaryObjective", "Objetivo primário", "Primary objective",
     "Objetivo que o instrumento declara como principal: direitos, inovação, desenvolvimento e soberania, ou segurança.",
     "O caráter desenvolvimentista e de soberania do modelo brasileiro (PBIA)."),
    ("E3_SubstantiveCoverage", "Cobertura substantiva", "Substantive coverage",
     "Áreas substantivas cobertas (as 28 áreas da câmara mais IA generativa e modelos de propósito geral), ligadas aos critérios quando houver relação.",
     "Lacunas de conteúdo: energia, crianças, desigualdade regional, participação."),
    ("E4_ScaledCoding", "Codificação em escala, com evidência por valor", "Scaled coding with evidence per value",
     "Cada valor é registrado numa escala aprovada e ligado ao dispositivo que o justifica.",
     "Valores comparáveis e rastreáveis, em vez de descrições."),
    ("E5_VersionedCoding", "Codificação por versão do instrumento", "Coding per instrument version",
     "A codificação pertence a uma versão do instrumento; mudou o texto, a codificação é refeita.",
     "PL 2338 de 2023 e de 2024; instrumentos revogados (EO 14110)."),
    ("E6_ImplementationCapacity", "Capacidade de implementação", "Implementation capacity",
     "Orçamento e pessoal disponíveis para supervisionar e implementar o instrumento.",
     "Orçamento e pessoal de supervisão (Eixo 5 do PBIA)."),
    ("E7_ImplementationParticipation", "Participação na implementação", "Participation in implementation",
     "Participação de pessoas e grupos na implementação e na padronização, além da consulta no processo legislativo.",
     "Deliberação pública ao vivo e Shadow Council."),
]

# R28: combinations of coded values with evidence => derived reading label. The thresholds use the
# scales PROPOSED for E4 (0 to 3 for ex ante and E1, 0 to 2 for the application layer); the rule only
# fires on codings that have a justifying provision and an approved review, so it stays inactive
# until the scales and the codings are approved by a human.
R28 = ("R28_HorizontalRiskBasedProfile",
       "Reading label derived from coded values; the criteria stay visible. Depends on approved E4 scales and reviewed codings.",
       "hrai:CriterionCoding(?c1) ^ hrai:codingSubject(?c1,?v) ^ hrai:codingCriterion(?c1,comp:E1_LegalForm) ^ hrai:codingScaleValue(?c1,?x1) ^ swrlb:equal(?x1,3) ^ hrai:codingJustifiedBy(?c1,?p1) ^ hrai:codingReview(?c1,?d1) ^ hrai:ApprovalDecision(?d1)"
       " ^ hrai:CriterionCoding(?c2) ^ hrai:codingSubject(?c2,?v) ^ hrai:codingCriterion(?c2,comp:C22_ExAnte) ^ hrai:codingScaleValue(?c2,?x2) ^ swrlb:greaterThanOrEqual(?x2,3) ^ hrai:codingJustifiedBy(?c2,?p2) ^ hrai:codingReview(?c2,?d2) ^ hrai:ApprovalDecision(?d2)"
       " ^ hrai:CriterionCoding(?c3) ^ hrai:codingSubject(?c3,?v) ^ hrai:codingCriterion(?c3,comp:C25_ApplicationFocused) ^ hrai:codingScaleValue(?c3,?x3) ^ swrlb:greaterThanOrEqual(?x3,2) ^ hrai:codingJustifiedBy(?c3,?p3) ^ hrai:codingReview(?c3,?d3) ^ hrai:ApprovalDecision(?d3)"
       " -> comp:hasDesignProfile(?v,comp:HorizontalRiskBasedRegulation)")


def build() -> rdflib.Graph:
    data = json.loads(DEFS.read_text(encoding="utf-8"))
    g = rdflib.Graph()
    for p, ns in (("comp", C), ("hrai", H), ("skos", SKOS), ("dcterms", DCTERMS), ("owl", OWL),
                  ("swrl", swrl_texto.SWRL), ("swrlb", swrl_texto.SWRLB)):
        g.bind(p, ns)
    ont = URIRef(BASE + "/comparativo")
    g.add((ont, RDF.type, OWL.Ontology))
    g.add((ont, OWL.imports, URIRef(BASE + "/regulatory")))
    g.add((ont, OWL.versionInfo, Literal("1.0.0")))
    g.add((ont, OWL.versionIRI, URIRef(BASE + "/comparativo/1.0.0")))
    g.add((ont, DCTERMS.title, Literal("HRAI-GO comparative module: base taxonomy and declared extensions", lang="en")))
    g.add((ont, DCTERMS.description, Literal(
        "Módulo comparativo do HRAI-GO (Human-centred Regulatory AI, Governance Observatory): as 12 categorias e os 25 "
        "critérios de Alanoca et al. (2025), com as definições originais, e as extensões declaradas E1 a E7 (ESP-ONT-02, RF-16). "
        "As escalas dos critérios (E4) aguardam aprovação humana.", lang="pt")))
    g.add((ont, DCTERMS.source, DOI))

    base_scheme, ext_scheme = C.TaxonomiaAlanoca2025, C.ExtensoesHRAIGO
    g.add((base_scheme, RDF.type, SKOS.ConceptScheme))
    g.add((base_scheme, SKOS.prefLabel, Literal("Taxonomy of AI regulation (Alanoca et al., 2025)", lang="en")))
    g.add((base_scheme, DCTERMS.source, DOI))
    g.add((base_scheme, DCTERMS.bibliographicCitation, Literal(data["fonte"])))
    g.add((ext_scheme, RDF.type, SKOS.ConceptScheme))
    g.add((ext_scheme, SKOS.prefLabel, Literal("Extensões declaradas E1 a E7 do HRAI-GO", lang="pt")))
    g.add((ext_scheme, SKOS.scopeNote, Literal(CREDIT, lang="pt")))
    g.add((ext_scheme, RDFS.seeAlso, DOI))

    for cat in data["categorias"]:
        k = C["Cat_" + cat["id"]]
        g.add((k, RDF.type, SKOS.Concept))
        g.add((k, SKOS.inScheme, base_scheme))
        g.add((k, SKOS.topConceptOf, base_scheme))
        g.add((k, SKOS.prefLabel, Literal(cat["rotulo"], lang="en")))
        g.add((k, SKOS.altLabel, Literal(cat["rotuloPt"], lang="pt")))
        if cat["definicao"]:
            g.add((k, SKOS.definition, Literal(cat["definicao"], lang="en")))
        g.add((k, DCTERMS.source, DOI))
        for cr in cat["criterios"]:
            x = C[cr["id"]]
            g.add((x, RDF.type, SKOS.Concept))
            g.add((x, RDF.type, H.RegulatoryDesignCriterion))
            g.add((x, SKOS.inScheme, base_scheme))
            g.add((x, SKOS.broader, k))
            g.add((x, SKOS.notation, Literal(cr["id"].split("_")[0])))
            g.add((x, SKOS.prefLabel, Literal(cr["rotulo"], lang="en")))
            g.add((x, SKOS.altLabel, Literal(cr["rotuloPt"], lang="pt")))
            g.add((x, SKOS.definition, Literal(cr["definicao"], lang="en")))
            g.add((x, DCTERMS.source, DOI))
            if cr.get("origem"):
                g.add((x, SKOS.editorialNote, Literal(cr["origem"], lang="pt")))

    for eid, pt, en, definition, case in EXTENSIONS:
        x = C[eid]
        g.add((x, RDF.type, SKOS.Concept))
        g.add((x, RDF.type, H.RegulatoryDesignCriterion))
        g.add((x, SKOS.inScheme, ext_scheme))
        g.add((x, SKOS.topConceptOf, ext_scheme))
        g.add((x, SKOS.notation, Literal(eid.split("_")[0])))
        g.add((x, SKOS.prefLabel, Literal(pt, lang="pt")))
        g.add((x, SKOS.altLabel, Literal(en, lang="en")))
        g.add((x, SKOS.definition, Literal(definition, lang="pt")))
        g.add((x, SKOS.example, Literal(case, lang="pt")))
        g.add((x, SKOS.scopeNote, Literal(CREDIT, lang="pt")))
        g.add((x, RDFS.seeAlso, DOI))

    # Design profiles (R28): reading labels, never verdicts.
    g.add((C.DesignProfile, RDF.type, OWL.Class))
    g.add((C.DesignProfile, RDFS.label, Literal("DesignProfile", lang="en")))
    g.add((C.DesignProfile, RDFS.comment, Literal("Reading label derived from a combination of coded criteria (R28); the criteria stay visible.", lang="en")))
    g.add((C.hasDesignProfile, RDF.type, OWL.ObjectProperty))
    g.add((C.hasDesignProfile, RDFS.label, Literal("hasDesignProfile", lang="en")))
    g.add((C.hasDesignProfile, RDFS.comment, Literal("Inferred (R28): the coded instrument version reads as this design profile.", lang="en")))
    g.add((C.hasDesignProfile, RDFS.range, C.DesignProfile))
    g.add((C.HorizontalRiskBasedRegulation, RDF.type, OWL.NamedIndividual))
    g.add((C.HorizontalRiskBasedRegulation, RDF.type, C.DesignProfile))
    g.add((C.HorizontalRiskBasedRegulation, RDFS.label, Literal("Regulação horizontal por risco", lang="pt")))
    g.add((C.HorizontalRiskBasedRegulation, RDFS.comment, Literal(
        "Lei ou projeto de lei (E1), com requisitos ex ante altos (C22) e foco em aplicações (C25).", lang="pt")))

    add_areas(g)
    add_scales(g)

    name, comment, text = R28
    g += swrl_texto.to_graph(name, comment, text, {"hrai": str(H), "comp": str(C)}, str(C),
                             {str(H.codingScaleValue)})
    return g


def add_scales(g: rdflib.Graph) -> None:
    """E4 scales approved by the author (decision D-02): one SKOS level per value, linked to its criterion."""
    data = json.loads(SCALES.read_text(encoding="utf-8"))
    g.add((C.scaleLevelOf, RDF.type, OWL.ObjectProperty))
    g.add((C.scaleLevelOf, RDFS.label, Literal("scaleLevelOf", lang="en")))
    g.add((C.scaleLevelOf, RDFS.comment, Literal("Criterion whose approved E4 scale this level belongs to.", lang="en")))
    g.add((C.scaleLevelOf, RDFS.range, H.RegulatoryDesignCriterion))
    g.add((C.ScaleLevel, RDF.type, OWL.Class))
    g.add((C.ScaleLevel, RDFS.label, Literal("ScaleLevel", lang="en")))
    g.add((C.ScaleLevel, RDFS.comment, Literal("Level of an approved E4 scale: numeric value (skos:notation) and label. Approved by the author (D-02).", lang="en")))
    for crit, labels in data["escalas"].items():
        g.add((C[crit], SKOS.editorialNote, Literal("Escala E4 aprovada pelo autor (D-02, 17/11/2026).", lang="pt")))
        g.add((C[crit], DCTERMS.isReferencedBy, D02))
        for value, label in enumerate(labels):
            lv = C[f"Nivel_{crit.split('_')[0]}_{value}"]
            g.add((lv, RDF.type, C.ScaleLevel))
            g.add((lv, RDF.type, SKOS.Concept))
            g.add((lv, C.scaleLevelOf, C[crit]))
            g.add((lv, SKOS.notation, Literal(str(value))))
            g.add((lv, SKOS.prefLabel, Literal(label, lang="pt")))
    for crit, labels in data.get("categoricas", {}).items():
        g.add((C[crit], DCTERMS.isReferencedBy, D02))
        for label in labels:
            lv = C[f"Valor_{crit.split('_')[0]}_{_camel(label.replace(' ', '-'))}"]
            g.add((lv, RDF.type, C.ScaleLevel)); g.add((lv, RDF.type, SKOS.Concept))
            g.add((lv, C.scaleLevelOf, C[crit])); g.add((lv, SKOS.prefLabel, Literal(label, lang="pt")))


def _camel(key: str) -> str:
    return "".join(part.capitalize() for part in key.split("-"))


def add_areas(g: rdflib.Graph) -> None:
    """Substantive areas (E3) as SKOS concepts and hrai:SubstantiveArea individuals, with proposed mappings."""
    data = json.loads(AREAS.read_text(encoding="utf-8"))
    scheme = C.AreasSubstantivas
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, SKOS.prefLabel, Literal("Áreas substantivas do HRAI-GO (extensão E3)", lang="pt")))
    g.add((scheme, SKOS.scopeNote, Literal(data["nota"], lang="pt")))
    for prop, label, comment, rng in (
        ("areaNistFunction", "areaNistFunction", "NIST AI RMF 1.0 function related to the area (proposed mapping, pending review).", C.NistFunction),
        ("areaAIActChapter", "areaAIActChapter", "AI Act chapter that addresses the area (proposed mapping, pending review).", C.AIActChapter),
    ):
        g.add((C[prop], RDF.type, OWL.ObjectProperty))
        g.add((C[prop], RDFS.label, Literal(label, lang="en")))
        g.add((C[prop], RDFS.comment, Literal(comment, lang="en")))
        g.add((C[prop], RDFS.domain, H.SubstantiveArea))
        g.add((C[prop], RDFS.range, rng))
    for cls, comment in ((C.NistFunction, "Function of the NIST AI Risk Management Framework 1.0 (govern, map, measure, manage)."),
                         (C.AIActChapter, "Chapter of Regulation (EU) 2024/1689 (AI Act).")):
        g.add((cls, RDF.type, OWL.Class))
        g.add((cls, RDFS.label, Literal(str(cls).split("#")[-1], lang="en")))
        g.add((cls, RDFS.comment, Literal(comment, lang="en")))
    for key, label in data["nist"].items():
        n = C["NIST_" + key]
        g.add((n, RDF.type, OWL.NamedIndividual)); g.add((n, RDF.type, C.NistFunction))
        g.add((n, RDFS.label, Literal(label, lang="en")))
    for key, label in data["aiact"].items():
        ch = C["AIAct_Chapter" + key]
        g.add((ch, RDF.type, OWL.NamedIndividual)); g.add((ch, RDF.type, C.AIActChapter))
        g.add((ch, RDFS.label, Literal(label, lang="en")))
    for order, area in enumerate(data["areas"], start=1):
        a = C["Area_" + _camel(area["id"])]
        g.add((a, H.displayOrder, Literal(order)))
        g.add((a, RDF.type, OWL.NamedIndividual))
        g.add((a, RDF.type, H.SubstantiveArea))
        g.add((a, RDF.type, SKOS.Concept))
        g.add((a, SKOS.inScheme, scheme))
        g.add((a, SKOS.prefLabel, Literal(area["rotulo"], lang="pt")))
        g.add((a, SKOS.notation, Literal(area["id"])))
        if area.get("naCamara", True):
            g.add((a, H.displayKey, Literal("topics:" + area["id"])))
        else:
            g.add((a, SKOS.scopeNote, Literal("Área acrescentada pela extensão E3; ainda não aparece na cúpula da câmara.", lang="pt")))
        for f in area["nist"]:
            g.add((a, C.areaNistFunction, C["NIST_" + f]))
        for ch in area["aiact"]:
            g.add((a, C.areaAIActChapter, C["AIAct_Chapter" + ch]))
        for cr in area["criterios"]:
            g.add((a, SKOS.related, C[cr]))
        g.add((a, SKOS.editorialNote, Literal("Mapeamentos para NIST, AI Act e critérios: revisados pelo autor (D-03, 17/11/2026).", lang="pt")))
        g.add((a, DCTERMS.isReferencedBy, D03))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    g = build()
    if args.check:
        ok = TTL.exists() and OWL_FILE.exists() and isomorphic(g, rdflib.Graph().parse(TTL)) and isomorphic(g, rdflib.Graph().parse(OWL_FILE))
        print("comparativo:", "atualizado" if ok else "DESATUALIZADO: rode python3 scripts/ontologia/build_comparativo.py")
        return 0 if ok else 1
    g.serialize(TTL, format="turtle")
    g.serialize(OWL_FILE, format="xml")
    crit = len(set(g.subjects(RDF.type, H.RegulatoryDesignCriterion)))
    print(f"{TTL.relative_to(ROOT)}: {len(g)} triplas, {crit} critérios (25 de base + 7 extensões)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
