"""RF-07: capacity and exposure indicators with source and base year; requirements that presuppose capacity."""

import glob
from pathlib import Path

import rdflib
from rdflib.namespace import RDF

ROOT = Path(__file__).resolve().parents[1]
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
CAP = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/br/capacidade#")


def instances():
    g = rdflib.Graph()
    for f in glob.glob(str(ROOT / "ontologies/regulatory/instances/**/*.ttl"), recursive=True):
        g.parse(f)
    return g


def test_every_indicator_has_source_and_base_year():
    g = instances()
    inds = set(g.subjects(RDF.type, H.ContextIndicator)) | set(g.subjects(RDF.type, H.RiskExposureIndicator))
    assert len(inds) >= 19
    for i in inds:
        assert g.value(i, H.indicatorSource) is not None, i
        assert g.value(i, H.baseYear) is not None, i   # base year as stated, or "não informado na fonte"


def test_governance_budget_share_matches_the_pbia_table():
    g = instances()
    share = float(g.value(CAP.Ind_GovernanceBudgetShare, H.hasNumericValue))
    amount = float(g.value(CAP.Ind_GovernanceBudgetAmount, H.hasNumericValue))
    assert abs(amount / 23030 * 100 - share) < 0.01   # R$ 103,25 mi of R$ 23,03 bi


def test_no_threshold_is_set_by_the_session():
    """Thresholds are normative: the session sets none in the instances; the author's comes from decisoes (D-09)."""
    g = instances()
    assert not list(g.subject_objects(H.hasLowerAlertThreshold))
    reqs = list(g.subjects(H.requirementAssumesCapacity, None))
    assert len(set(reqs)) == 3 and all(g.value(r, H.derivedFromProvision) is not None for r in reqs)


def test_author_threshold_flags_the_budget_dependent_requirements():
    import sys
    sys.path.insert(0, str(ROOT / "scripts/ontologia"))
    import consultas
    g = consultas.reasoned_graph()
    assert float(g.value(CAP.Ind_GovernanceBudgetShare, H.hasLowerAlertThreshold)) == 5.0
    assert (CAP.Ind_GovernanceBudgetShare, RDF.type, H.CapacityShortfallIndicator) in g
    flagged = set(g.subjects(H.requirementHasCapacityRisk, CAP.Ind_GovernanceBudgetShare))
    assert flagged == {CAP.Req_CompetentAuthoritySupervision, CAP.Req_ConformityAccreditation}
