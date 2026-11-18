"""RF-01: the PL 2338/2023 texts of 2023 and 2024 as two versions of the same proposal, with their articles."""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import rdflib
from rdflib.namespace import DCTERMS, RDF, RDFS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ontologies/regulatory/instances/br/HRAI_GO_Regulatory_BR_PL2338.ttl"
H = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/regulatory#")
PL = rdflib.Namespace("https://hrai-go.aeonbridge.io/data/regulatory/br/pl2338#")
PBIA = rdflib.Namespace("https://hrai-go.aeonbridge.io/data/regulatory/br/pbia#")


@pytest.fixture(scope="module")
def g():
    return rdflib.Graph().parse(OUT)


def test_two_versions_of_the_same_proposal(g):
    assert (PL.Versao_2023, H.versionOfInstrument, PBIA.PL_2338_2023) in g
    assert (PL.Versao_2024, H.versionOfInstrument, PBIA.PL_2338_2023) in g
    assert (PL.Versao_2024, H.previousLegalVersion, PL.Versao_2023) in g
    assert (PBIA.PL_2338_2023, RDF.type, H.LegislativeProposal) in g


def test_articles_counted_and_gap_recorded(g):
    n = lambda v: len(list(g.objects(v, H.versionContainsProvision)))  # noqa: E731
    assert (n(PL.Versao_2023), n(PL.Versao_2024)) == (45, 79)
    assert "ausentes no documento: art. 31" in str(g.value(PL.Versao_2024, RDFS.comment))
    for x in g.subjects(RDF.type, H.LegalProvision):
        text = str(g.value(x, DCTERMS.description))
        assert text and not any(w in text for w in ("Apresentação:", "Autenticado", "JUSTIFICAÇÃO", "Senado Federal, em")), x
        assert g.value(x, H.provisionDocumentedIn) is not None and g.value(x, H.legalCitation) is not None


def test_snapshots_hash_the_pdfs_and_nothing_is_decided(g):
    for snap in g.subjects(RDF.type, H.SourceSnapshot):
        path = ROOT / str(g.value(snap, H.snapshotURI)).split("/blob/main/", 1)[1].replace("%20", " ")
        assert str(g.value(snap, H.snapshotSHA256)) == hashlib.sha256(path.read_bytes()).hexdigest()
    assert len(set(g.subjects(RDF.type, H.CandidateAssertion))) == 2
    assert not set(g.subjects(RDF.type, H.ReviewDecision))


def test_cecia_is_in_the_senate_text(g):
    """Basis for re-evaluating thesis C04 (item 10): the 2024 text has a section on the expert committee."""
    notes = [str(o) for s, o in g.subject_objects(rdflib.namespace.SKOS.scopeNote) if str(s).startswith(str(PL) + "Art_2024")]
    assert any("Comitê de Especialistas e Cientistas" in n for n in notes)


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext not installed")
def test_extraction_is_reproducible():
    assert subprocess.run([sys.executable, str(ROOT / "scripts/ontologia/extrair_pl2338.py"), "--check"]).returncode == 0
