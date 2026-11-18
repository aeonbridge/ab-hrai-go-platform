"""RF-17: the SCSE module imports the regulatory core instead of redeclaring its classes."""

import sys
from pathlib import Path

import rdflib
from rdflib.namespace import OWL, RDF

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "ontologies/regulatory/HRAI_GO_Regulatory_General.ttl"
SCSE = ROOT / "ontologies/scse/SCSE_Shadow_Council_Ontology.ttl"
CORE_IRI = "https://hrai-go.aeonbridge.io/ontology/regulatory"
SCSE_NS = "https://hrai-go.aeonbridge.io/ontology/scse#"
CORE_NS = CORE_IRI + "#"
DECLARED = (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty)


def declared(g):
    return {s for t in DECLARED for s in g.subjects(RDF.type, t) if isinstance(s, rdflib.URIRef)}


def test_no_term_declared_in_both_modules():
    core, scse = rdflib.Graph().parse(CORE), rdflib.Graph().parse(SCSE)
    both = declared(core) & declared(scse)
    assert not both, sorted(map(str, both))
    # SCSE declares only its own namespace; core terms are used, never redeclared.
    assert all(str(t).startswith(SCSE_NS) for t in declared(scse))
    assert not any(str(s).startswith(CORE_NS) for s in scse.subjects())


def test_scse_imports_core_and_has_no_placeholder_namespace():
    scse = rdflib.Graph().parse(SCSE)
    assert (rdflib.URIRef(SCSE_NS[:-1]), OWL.imports, rdflib.URIRef(CORE_IRI)) in scse
    terms = {str(x) for t in scse for x in t if isinstance(x, rdflib.URIRef)}
    assert not any("example.org/hrai-go" in t for t in terms)


def test_deliberation_classes_live_in_scse_with_equivalence():
    scse = rdflib.Graph().parse(SCSE)
    for name in ("Deliberation", "StakeholderPosition", "SyntheticStakeholderPerspective", "SyntheticStakeholderPosition"):
        assert (rdflib.URIRef(SCSE_NS + name), OWL.equivalentClass, rdflib.URIRef(CORE_NS + name)) in scse, name


def test_every_term_used_by_scse_rules_is_declared_and_rules_fire():
    sys.path.insert(0, str(ROOT / "scripts/ontologia"))
    import raciocinar

    rz = raciocinar.Raciocinador(CORE, SCSE)
    known = declared(rz.g)
    used = {o for p in (rdflib.URIRef("http://www.w3.org/2003/11/swrl#classPredicate"),
                        rdflib.URIRef("http://www.w3.org/2003/11/swrl#propertyPredicate")) for o in rz.g.objects(None, p)}
    missing = {u for u in used if u not in known}
    assert not missing, sorted(map(str, missing))
    rz.executar()
    fired = {k.split("#")[-1] for k, v in rz.disparos.items() if v and ":" not in k}
    # The SCSE rules that fired before the separation still fire on the illustration individuals.
    for rule in ("R01_CouncilAgent", "R02_CouncilCoversStratum", "R03_AgentEvidenceGrounding", "R04_RunProducesClaim",
                 "R05_AssessmentRequiresEvidenceReview", "R06_FindingRequiresEvidenceReview",
                 "R07_ProposedProvisionNeedsProspectiveReview", "R09_ProjectRegulation"):
        assert rule in fired, rule
