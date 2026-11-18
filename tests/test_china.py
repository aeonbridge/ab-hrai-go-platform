"""RF-02 / D-01: China enters the corpus with secondary sources, flagged as such (V-03)."""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import rdflib
from rdflib.namespace import DCTERMS, PROV, RDF, SKOS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ontologies/regulatory/instances/cn/HRAI_GO_Regulatory_CN.ttl"
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
CN = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/cn/china#")


@pytest.fixture(scope="module")
def g():
    return rdflib.Graph().parse(OUT)


def test_china_has_hashed_snapshots_and_every_instrument_is_flagged_secondary(g):
    snaps = list(g.subjects(RDF.type, H.SourceSnapshot))
    assert len(snaps) == 2
    for s in snaps:
        path = ROOT / str(g.value(s, H.snapshotURI)).split("/blob/main/", 1)[1]
        assert str(g.value(s, H.snapshotSHA256)) == hashlib.sha256(path.read_bytes()).hexdigest()
    instruments = [x for x in g.subjects(PROV.wasDerivedFrom, CN.Snapshot_Overview) if (x, RDF.type, H.Stakeholder) not in g]
    assert len(instruments) == 14
    assert all("Fonte secundária" in str(g.value(x, SKOS.scopeNote)) for x in instruments)
    assert len(set(g.subjects(DCTERMS.references, CN.Snapshot_LawLibrary))) == 7


def test_non_binding_and_draft_instruments_are_not_shown_as_law(g):
    assert (CN.EthicsSafetyGuidelines, RDF.type, H.PolicyInstrument) in g
    assert (CN.DigitalVirtualHumanDraft, RDF.type, H.LegislativeProposal) in g
    assert (CN.GenerativeAIMeasures, RDF.type, H.EnactedLegalInstrument) in g
    assert not set(g.subjects(RDF.type, H.ReviewDecision))


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext not installed")
def test_extraction_is_reproducible():
    assert subprocess.run([sys.executable, str(ROOT / "scripts/ontologia/extrair_china.py"), "--check"]).returncode == 0
