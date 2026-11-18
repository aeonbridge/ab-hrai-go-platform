"""RF-03: rules R24-R26 (core) and R29-R30 (SCSE), invariants I-1 to I-4, reasoning time (RNF-02)."""

import glob
import sys
import time
from pathlib import Path

import rdflib
from rdflib.collection import Collection
from rdflib.namespace import OWL, PROV, RDF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/ontologia"))
import raciocinar  # noqa: E402

CORE = ROOT / "ontologies/regulatory/HRAI_GO_Regulatory_General.ttl"
SCSE = ROOT / "ontologies/scse/SCSE_Shadow_Council_Ontology.ttl"
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
S = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/scse#")
SW = rdflib.Namespace("http://www.w3.org/2003/11/swrl#")
EX = "http://example.test/fixture#"

FIXTURE = f"""
@prefix hrai: <{H}> . @prefix scse: <{S}> . @prefix ex: <{EX}> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:BR a hrai:Jurisdiction . ex:EU a hrai:Jurisdiction .
ex:Lei a hrai:EnactedLegalInstrument ; hrai:instrumentInJurisdiction ex:BR .
ex:LeiV a hrai:LegalInstrumentVersion ; hrai:versionOfInstrument ex:Lei .
ex:art1 a hrai:LegalProvision ; hrai:provisionOfVersion ex:LeiV ; hrai:provisionAddressesFunction ex:Saude ;
        hrai:provisionInJurisdiction ex:BR .
ex:PL a hrai:LegislativeProposal ; hrai:proposalInJurisdiction ex:BR .
ex:PLV a hrai:LegalInstrumentVersion ; hrai:versionOfInstrument ex:PL .
ex:art9 a hrai:LegalProvision ; hrai:provisionOfVersion ex:PLV ; hrai:provisionAddressesFunction ex:Energia ;
        hrai:provisionInJurisdiction ex:BR .
ex:Plano a hrai:PolicyInstrument ; hrai:policyInstrumentInJurisdiction ex:BR ; hrai:provisionAddressesFunction ex:Computacao .
ex:Saude a hrai:SubstantiveArea . ex:Energia a hrai:SubstantiveArea . ex:Computacao a hrai:SubstantiveArea .
ex:orcamento a hrai:ContextIndicator ; hrai:hasNumericValue "10"^^xsd:decimal ; hrai:hasLowerAlertThreshold "50"^^xsd:decimal .
ex:cap a hrai:CapacityRequirement ; hrai:capacityMeasuredBy ex:orcamento .
ex:req a hrai:NormativeRequirement ; hrai:requirementAssumesCapacity ex:cap .
ex:art6EU a hrai:LegalProvision ; hrai:provisionInJurisdiction ex:EU .
ex:aprov a hrai:ApprovalDecision .
ex:corr a hrai:ProvisionCorrespondence ; hrai:correspondenceFrom ex:art6EU ; hrai:correspondenceTo ex:art9 ;
        hrai:correspondenceHasType hrai:AdaptedCorrespondence ; hrai:correspondenceReview ex:aprov .
ex:corrSemRevisao a hrai:ProvisionCorrespondence ; hrai:correspondenceFrom ex:art6EU ; hrai:correspondenceTo ex:art1 ;
        hrai:correspondenceHasType hrai:EquivalentCorrespondence .
ex:assento a hrai:SyntheticStakeholderPerspective ; scse:stakeholderInStratum ex:reguladores .
ex:pessoa a hrai:IdentifiedStakeholder ; scse:stakeholderInStratum ex:trabalhadores .
ex:tese a hrai:PolicyClaim .
ex:posSint a hrai:StakeholderPosition ; hrai:positionExpressedBy ex:assento ; hrai:positionSupportsClaim ex:tese .
ex:alt a hrai:PolicyAlternative .
ex:pA a hrai:StakeholderPosition ; hrai:positionExpressedBy ex:assento ; scse:positionSupportsAlternative ex:alt .
ex:pB a hrai:StakeholderPosition ; hrai:positionExpressedBy ex:pessoa ; scse:positionChallengesAlternative ex:alt .
ex:altMesmoEstrato a hrai:PolicyAlternative .
ex:pC a hrai:StakeholderPosition ; hrai:positionExpressedBy ex:pessoa ; scse:positionSupportsAlternative ex:altMesmoEstrato .
ex:pD a hrai:StakeholderPosition ; hrai:positionExpressedBy ex:pessoa ; scse:positionChallengesAlternative ex:altMesmoEstrato .
"""


def reason_fixture(tmp_path):
    fx = tmp_path / "fixture.ttl"
    fx.write_text(FIXTURE, encoding="utf-8")
    rz = raciocinar.Raciocinador(CORE, SCSE, fx)
    rz.executar()
    return rz.g


def ex(name):
    return rdflib.URIRef(EX + name)


def test_new_core_rules(tmp_path):
    g = reason_fixture(tmp_path)
    # R24a/b/c: legal force of the coverage comes from the instrument class.
    assert (ex("BR"), H.jurisdictionAddressesFunction, ex("Saude")) in g
    assert (ex("BR"), H.jurisdictionProposesFunction, ex("Energia")) in g
    assert (ex("BR"), H.jurisdictionAddressesFunction, ex("Energia")) not in g
    assert (ex("BR"), H.jurisdictionPlansFunction, ex("Computacao")) in g
    # R25a/b: capacity shortfall is a signal on the requirement.
    assert (ex("orcamento"), RDF.type, H.CapacityShortfallIndicator) in g
    assert (ex("req"), H.requirementHasCapacityRisk, ex("orcamento")) in g
    # R26: only reviewed, transposing, cross-jurisdiction correspondences.
    assert (ex("art9"), H.provisionTransposedFrom, ex("art6EU")) in g
    assert (ex("art1"), H.provisionTransposedFrom, ex("art6EU")) not in g


def test_synthetic_never_counts_as_human_and_divergence(tmp_path):
    g = reason_fixture(tmp_path)
    # R21 + R29a: synthetic support is recorded as synthetic only.
    assert (ex("posSint"), RDF.type, H.SyntheticStakeholderPosition) in g
    assert (ex("tese"), S.hasSyntheticSupport, ex("posSint")) in g
    assert (ex("pB"), RDF.type, H.SyntheticStakeholderPosition) not in g
    # R30: disagreement across strata, not within one stratum.
    assert (ex("alt"), RDF.type, S.DivergentAlternative) in g
    assert (ex("altMesmoEstrato"), RDF.type, S.DivergentAlternative) not in g


def all_rules():
    g = rdflib.Graph().parse(CORE)
    g.parse(SCSE)
    return g, sorted(set(g.subjects(RDF.type, SW.Imp)))


def test_i1_no_rule_asserts_status_compliance_publication_or_decision():
    g, rules = all_rules()
    forbidden = {H.assessmentHasStatus, H.hasLegalStatus, H.releasePublishesCandidate, H.hasReviewDecision,
                 H.ReviewDecision, H.ApprovalDecision, H.NationalSpecificity, S.DecisionRecord, S.provisionStateHasStatus,
                 S.decisionSelects, S.decisionCitesClaim, H.codingReview, H.correspondenceReview, H.specificityReview}
    for r in rules:
        for atom in Collection(g, g.value(r, SW.head)):
            pred = g.value(atom, SW.propertyPredicate) or g.value(atom, SW.classPredicate)
            assert pred not in forbidden, f"{r} infers {pred}"


def test_i2_scenarios_and_claims_never_mix_with_source_instances():
    inst = ROOT / "ontologies/regulatory/instances"
    files = [Path(f) for f in glob.glob(str(inst / "**/*.ttl"), recursive=True)]
    assert files and not any("cenario" in f.name.lower() or "afirmac" in f.name.lower() for f in files)
    side = rdflib.Graph()
    for f in glob.glob(str(ROOT / "ontologies/regulatory/cenarios/*.ttl")) + glob.glob(str(ROOT / "ontologies/regulatory/afirmacoes/*.ttl")):
        side.parse(f)
    side_subjects = {s for s in side.subjects(RDF.type, None)}
    for f in files:
        g = rdflib.Graph().parse(f)
        assert not (side_subjects & set(g.subjects(RDF.type, None))), f"{f.name} redeclares scenario or claim individuals"


def test_i3_no_agent_creates_review_decision():
    g = rdflib.Graph()
    for f in glob.glob(str(ROOT / "ontologies/regulatory/**/*.ttl"), recursive=True):
        g.parse(f)
    agents = set(g.subjects(RDF.type, H.MonitoringAgent)) | set(g.subjects(RDF.type, PROV.SoftwareAgent))
    for d in set(g.subjects(RDF.type, H.ReviewDecision)) | set(g.subjects(RDF.type, H.ApprovalDecision)):
        assert not (set(g.objects(d, H.reviewDecisionBy)) & agents), f"{d} decided by an agent"


def test_i4_synthetic_and_identified_are_disjoint():
    g = rdflib.Graph().parse(CORE)
    assert (H.SyntheticStakeholderPerspective, OWL.disjointWith, H.IdentifiedStakeholder) in g
    sg = rdflib.Graph().parse(SCSE)
    for prop in (S.hasSyntheticSupport, S.hasSyntheticChallenge):
        assert (prop, rdflib.RDFS.subPropertyOf, None) not in sg, "synthetic support must not specialize human support"


def test_rnf02_full_graph_reasons_under_five_seconds():
    files = [CORE, SCSE] + [Path(f) for pattern in ("ontologies/regulatory/instances/**/*.ttl", "ontologies/regulatory/cenarios/*.ttl",
                                                     "ontologies/regulatory/afirmacoes/*.ttl", "ontologies/regulatory/alinhamentos/*.ttl")
                            for f in sorted(glob.glob(str(ROOT / pattern), recursive=True))]
    t0 = time.perf_counter()
    rz = raciocinar.Raciocinador(*files)
    rz.executar()
    elapsed = time.perf_counter() - t0
    print(f"full graph: {len(rz.g)} triples reasoned in {elapsed:.2f} s")
    assert elapsed < 5.0, elapsed
