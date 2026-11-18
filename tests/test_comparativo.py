"""RF-16 (formalization): comparative module with the base taxonomy, extensions E1-E7 and rule R28."""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import rdflib
from rdflib.namespace import OWL, RDF, RDFS, SKOS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/ontologia"))
import raciocinar  # noqa: E402

spec = importlib.util.spec_from_file_location("build_comparativo", ROOT / "scripts/ontologia/build_comparativo.py")
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)

H, C = bc.H, bc.C
DEFS = json.loads(bc.DEFS.read_text(encoding="utf-8"))
CORE = ROOT / "ontologies/regulatory/HRAI_GO_Regulatory_General.ttl"
SCSE = ROOT / "ontologies/scse/SCSE_Shadow_Council_Ontology.ttl"


@pytest.fixture(scope="module")
def g():
    return rdflib.Graph().parse(bc.TTL)


def test_published_files_are_current():
    assert subprocess.run([sys.executable, str(ROOT / "scripts/ontologia/build_comparativo.py"), "--check"]).returncode == 0


def test_twelve_categories_twenty_five_criteria_seven_extensions(g):
    base = set(g.subjects(SKOS.inScheme, C.TaxonomiaAlanoca2025)) & set(g.subjects(RDF.type, H.RegulatoryDesignCriterion))
    cats = set(g.subjects(SKOS.topConceptOf, C.TaxonomiaAlanoca2025))
    ext = set(g.subjects(SKOS.inScheme, C.ExtensoesHRAIGO))
    assert (len(cats), len(base), len(ext)) == (12, 25, 7)
    assert {str(x).split("#")[-1].split("_")[0] for x in ext} == {f"E{i}" for i in range(1, 8)}


def test_original_definitions_intact(g):
    for cat in DEFS["categorias"]:
        for cr in cat["criterios"]:
            assert str(g.value(C[cr["id"]], SKOS.definition)) == cr["definicao"], cr["id"]
            assert (C[cr["id"]], rdflib.namespace.DCTERMS.source, bc.DOI) in g


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext not installed")
def test_frozen_definitions_match_the_paper():
    text = subprocess.run(["pdftotext", str(ROOT / DEFS["arquivo"]), "-"], capture_output=True, text=True).stdout
    norm = lambda s: re.sub(r"\s+", " ", s.replace("-\n", "").replace("’", "'")).replace("- ", "").strip()  # noqa: E731
    paper = norm(text)
    for cat in DEFS["categorias"]:
        for item in [cat] + cat["criterios"]:
            if item.get("definicao"):
                assert norm(item["definicao"]) in paper, item["id"]


def test_extensions_carry_credit_and_doi(g):
    for ext in g.subjects(SKOS.inScheme, C.ExtensoesHRAIGO):
        assert "doi:10.1145/3715275.3732059" in str(g.value(ext, SKOS.scopeNote)), ext
        assert (ext, RDFS.seeAlso, bc.DOI) in g


def test_module_imports_core_and_declares_nothing_from_other_modules(g):
    assert (rdflib.URIRef(bc.BASE + "/comparativo"), OWL.imports, rdflib.URIRef(bc.BASE + "/regulatory")) in g
    decl = lambda gr: {s for t in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty) for s in gr.subjects(RDF.type, t)}  # noqa: E731
    others = decl(rdflib.Graph().parse(CORE)) | decl(rdflib.Graph().parse(SCSE))
    assert not (decl(g) & others)


FIXTURE = """
@prefix hrai: <{H}> . @prefix comp: <{C}> . @prefix ex: <http://example.test/c#> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:ok a hrai:ApprovalDecision . ex:art a hrai:LegalProvision .
ex:PLv a hrai:LegalInstrumentVersion . ex:SoV a hrai:LegalInstrumentVersion .
ex:c1 a hrai:CriterionCoding ; hrai:codingSubject ex:PLv ; hrai:codingCriterion comp:E1_LegalForm ; hrai:codingScaleValue "3"^^xsd:decimal ; hrai:codingJustifiedBy ex:art ; hrai:codingReview ex:ok .
ex:c2 a hrai:CriterionCoding ; hrai:codingSubject ex:PLv ; hrai:codingCriterion comp:C22_ExAnte ; hrai:codingScaleValue "3"^^xsd:decimal ; hrai:codingJustifiedBy ex:art ; hrai:codingReview ex:ok .
ex:c3 a hrai:CriterionCoding ; hrai:codingSubject ex:PLv ; hrai:codingCriterion comp:C25_ApplicationFocused ; hrai:codingScaleValue "2"^^xsd:decimal ; hrai:codingJustifiedBy ex:art ; hrai:codingReview ex:ok .
ex:d1 a hrai:CriterionCoding ; hrai:codingSubject ex:SoV ; hrai:codingCriterion comp:E1_LegalForm ; hrai:codingScaleValue "3"^^xsd:decimal ; hrai:codingJustifiedBy ex:art ; hrai:codingReview ex:ok .
ex:d2 a hrai:CriterionCoding ; hrai:codingSubject ex:SoV ; hrai:codingCriterion comp:C22_ExAnte ; hrai:codingScaleValue "3"^^xsd:decimal ; hrai:codingJustifiedBy ex:art .
ex:d3 a hrai:CriterionCoding ; hrai:codingSubject ex:SoV ; hrai:codingCriterion comp:C25_ApplicationFocused ; hrai:codingScaleValue "2"^^xsd:decimal ; hrai:codingJustifiedBy ex:art ; hrai:codingReview ex:ok .
"""


def test_r28_needs_justified_and_approved_codings(tmp_path):
    fx = tmp_path / "f.ttl"
    fx.write_text(FIXTURE.format(H=H, C=C), encoding="utf-8")
    rz = raciocinar.Raciocinador(CORE, bc.TTL, fx)
    rz.executar()
    ex = rdflib.Namespace("http://example.test/c#")
    assert (ex.PLv, C.hasDesignProfile, C.HorizontalRiskBasedRegulation) in rz.g
    # ex:d2 has no review decision: the profile is not derived.
    assert (ex.SoV, C.hasDesignProfile, C.HorizontalRiskBasedRegulation) not in rz.g
