"""RF-02 / D-01c: China in the comparison, with the official CAC text of the generative AI measures and flagged secondary sources."""

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
H = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/regulatory#")
CN = rdflib.Namespace("https://hrai-go.aeonbridge.io/data/regulatory/cn/china#")


@pytest.fixture(scope="module")
def g():
    return rdflib.Graph().parse(OUT)


def test_china_snapshots_are_hashed_and_sources_are_honest(g):
    snaps = list(g.subjects(RDF.type, H.SourceSnapshot))
    assert len(snaps) == 4
    for s in snaps:
        path = ROOT / str(g.value(s, H.snapshotURI)).split("/blob/main/", 1)[1]
        assert str(g.value(s, H.snapshotSHA256)) == hashlib.sha256(path.read_bytes()).hexdigest()
    instruments = [x for x in g.subjects(PROV.wasDerivedFrom, CN.Snapshot_Overview) if (x, RDF.type, H.Stakeholder) not in g]
    assert len(instruments) == 14
    official = {CN.GenerativeAIMeasures}
    assert all("Fonte secundária" in str(g.value(x, SKOS.scopeNote)) for x in instruments if x not in official | {CN.DeepSynthesis})
    assert "Texto oficial da CAC" in str(g.value(CN.GenerativeAIMeasures, SKOS.scopeNote))


def test_official_generative_ai_measures_have_their_24_articles(g):
    arts = list(g.objects(CN.GenerativeAIMeasures_2023, H.versionContainsProvision))
    assert len(arts) == 24
    assert all(g.value(a, H.provisionDocumentedIn) == CN.Snapshot_CAC_GenerativeAI for a in arts)


def test_non_binding_and_draft_instruments_are_not_shown_as_law(g):
    assert (CN.EthicsSafetyGuidelines, RDF.type, H.PolicyInstrument) in g
    assert (CN.DigitalVirtualHumanDraft, RDF.type, H.LegislativeProposal) in g
    assert (CN.GenerativeAIMeasures, RDF.type, H.EnactedLegalInstrument) in g
    assert not set(g.subjects(RDF.type, H.ReviewDecision))


def test_every_specificity_compares_with_china():
    """Adding a jurisdiction: V30 flags missing comparisons until each QN1 specificity has one (D-01c impact)."""
    answers = rdflib.Graph().parse(ROOT / "ontologies/regulatory/respostas/QN_respostas.ttl")
    specs = set(answers.subjects(RDF.type, H.NationalSpecificity))
    with_cn = {s for s in specs for c in answers.objects(s, H.specificityComparison) if answers.value(c, H.comparisonJurisdiction) == CN.China}
    assert specs and with_cn == specs


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext not installed")
def test_extraction_is_reproducible():
    assert subprocess.run([sys.executable, str(ROOT / "scripts/ontologia/extrair_china.py"), "--check"]).returncode == 0
