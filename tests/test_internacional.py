"""RF-04 / RF-14 / RF-06: EU, UK and US instruments extracted from the corpus, and BR x EU correspondences."""

import glob
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest
import rdflib
from rdflib.namespace import DCTERMS, RDF, SKOS

ROOT = Path(__file__).resolve().parents[1]
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
INST = ROOT / "ontologies/regulatory/instances"
COR = ROOT / "ontologies/regulatory/correspondencias/BR_UE_PL2338_AIAct.ttl"


def graph(*rel):
    g = rdflib.Graph()
    for r in rel:
        g.parse(INST / r)
    return g


def test_aiact_has_its_113_articles_and_is_in_force():
    g = graph("eu/HRAI_GO_Regulatory_EU_AIAct.ttl")
    arts = [s for s in g.subjects(RDF.type, H.LegalProvision)]
    assert len(arts) == 113
    assert len(set(g.subjects(RDF.type, H.EnactedLegalInstrument))) == 1


def test_uk_principles_and_nist_functions_are_non_binding_instruments():
    uk = graph("uk/HRAI_GO_Regulatory_UK_WhitePaper.ttl")
    principles = [s for s in uk.subjects(SKOS.notation, None)]
    assert len(principles) == 5 and all(uk.value(p, DCTERMS.description) for p in principles)
    assert not set(uk.subjects(RDF.type, H.EnactedLegalInstrument))
    assert any("statutory footing" in str(o) for o in uk.objects(None, SKOS.scopeNote))
    us = graph("us/HRAI_GO_Regulatory_US_NIST.ttl")
    funcs = [s for s in us.subjects(DCTERMS.isPartOf, None)]
    assert len(funcs) == 4 and all(us.value(f, DCTERMS.description) for f in funcs)
    assert any("voluntary" in str(o) for o in us.objects(None, SKOS.scopeNote))


def test_every_jurisdiction_has_a_hashed_snapshot():
    """V-02 / V-03: no jurisdiction without a SourceSnapshot with SHA-256."""
    g = rdflib.Graph()
    for f in glob.glob(str(INST / "**/*.ttl"), recursive=True):
        g.parse(f)
    snaps = list(g.subjects(RDF.type, H.SourceSnapshot))
    for s in snaps:
        uri = str(g.value(s, H.snapshotURI) or "")
        if "/blob/main/" in uri:
            path = ROOT / unquote(uri.split("/blob/main/", 1)[1])
            assert str(g.value(s, H.snapshotSHA256)) == hashlib.sha256(path.read_bytes()).hexdigest(), s
    labels = " ".join(str(g.value(s, rdflib.RDFS.label)) for s in snaps)
    for needle in ("PBIA", "PL 2338/2023, texto inicial", "aprovado pelo Senado", "2024/1689", "pro-innovation", "AI RMF"):
        assert needle in labels, needle


def test_correspondences_are_pending_and_infer_no_transposition():
    g = rdflib.Graph().parse(COR)
    corrs = list(g.subjects(RDF.type, H.ProvisionCorrespondence))
    assert len(corrs) == 18
    assert all(g.value(c, H.correspondenceAnalyst) is not None and g.value(c, rdflib.RDFS.comment) for c in corrs)
    assert not list(g.objects(None, H.correspondenceReview))
    sys.path.insert(0, str(ROOT / "scripts/ontologia"))
    import consultas
    rg = consultas.reasoned_graph()
    assert not list(rg.subject_objects(H.provisionTransposedFrom)), "R26 must wait for human approval"


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext not installed")
def test_extraction_and_correspondences_are_reproducible():
    for script in ("extrair_internacional.py", "correspondencias.py"):
        assert subprocess.run([sys.executable, str(ROOT / "scripts/ontologia" / script), "--check"]).returncode == 0
