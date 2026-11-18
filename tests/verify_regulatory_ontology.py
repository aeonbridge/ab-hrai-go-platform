from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal
from rdflib.collection import Collection
from rdflib.compare import isomorphic

root = Path(__file__).resolve().parents[1] / "ontologies" / "regulatory"
ttl = Graph().parse(root / "HRAI_GO_Regulatory_General.ttl", format="turtle")
owl = Graph().parse(root / "HRAI_GO_Regulatory_General.owl", format="xml")
assert isomorphic(ttl, owl), "Turtle and RDF/XML graphs differ"

H = Namespace("https://hrai-go.aeonbridge.io/ontology/regulatory#")
SW = Namespace("http://www.w3.org/2003/11/swrl#")

mandatory = ["Jurisdiction", "LegalInstrument", "LegislativeProposal", "LegalProvision", "NormativeRequirement",
             "RegulatoryModel", "NationalContext", "ContextIndicator", "PolicyObjective", "PolicyInstrument",
             "RegulatoryTension", "RegulatoryGap", "PolicyClaim", "PolicyAlternative", "Stakeholder",
             "StakeholderPosition", "Deliberation", "PolicyImpactAssessment"]
for name in mandatory:
    assert (H[name], RDF.type, OWL.Class) in ttl, name

# v1.1.0: extensões aditivas
v110_classes = {"PublicPolicyPlan": "PolicyInstrument", "PolicyPlanAxis": "PolicyInstrument", "BudgetAllocation": None,
                "ExecutionRecord": None, "ExecutionBelowAlertRatioRecord": "ExecutionRecord", "ImpactReviewOutcome": None,
                "SyntheticStakeholderPerspective": "Stakeholder", "IdentifiedStakeholder": "Stakeholder",
                "SyntheticStakeholderPosition": "StakeholderPosition", "ProposedProvision": "LegalProvision",
                "ProspectiveRequirement": "NormativeRequirement"}
for name, sup in v110_classes.items():
    assert (H[name], RDF.type, OWL.Class) in ttl, name
    if sup:
        assert (H[name], RDFS.subClassOf, H[sup]) in ttl, (name, sup)
assert (H.SyntheticStakeholderPerspective, OWL.disjointWith, H.IdentifiedStakeholder) in ttl
assert (H.LegislativeProposal, OWL.disjointWith, H.EnactedLegalInstrument) in ttl
assert (H.impactReviewStatus, OWL.deprecated, Literal(True)) in ttl

# v1.2.0 (ESP-ONT-02, RF-03): extensões aditivas da comparação, cobertura, capacidade e especificidade
v120_classes = {"RegulatoryDesignCriterion": None, "CriterionCoding": None, "SubstantiveArea": None,
                "ProvisionCorrespondence": None, "CorrespondenceType": None, "TransposingCorrespondenceType": "CorrespondenceType",
                "CapacityRequirement": None, "CapacityShortfallIndicator": "ContextIndicator",
                "RiskExposureIndicator": "ContextIndicator", "CoverageAssessment": None, "NationalSpecificity": None,
                "SpecificityDimension": None, "DifferenceType": None, "JurisdictionComparison": None}
for name, sup in v120_classes.items():
    assert (H[name], RDF.type, OWL.Class) in ttl, name
    assert ttl.value(H[name], RDFS.comment) is not None, f"{name}: classe sem comentário"
    if sup:
        assert (H[name], RDFS.subClassOf, H[sup]) in ttl, (name, sup)
for prop in ("provisionAddressesFunction", "jurisdictionAddressesFunction", "jurisdictionProposesFunction",
             "jurisdictionPlansFunction", "provisionTransposedFrom", "requirementHasCapacityRisk", "claimQualifies",
             "claimComplements", "groundedInSpecificity", "specificityComparison", "hasLowerAlertThreshold"):
    assert ttl.value(H[prop], RDFS.comment) is not None, f"{prop}: propriedade ausente ou sem comentário"
assert (None, None, Literal("1.2.0")) in ttl

# Regras SWRL: contagem, estrutura e segurança
rules = sorted(set(ttl.subjects(RDF.type, SW.Imp)))
assert len(rules) == 29, (len(rules), "SWRL rule count")
# I-1: nenhuma regra afirma status jurídico, conformidade, publicação ou decisão (humana ou de revisão).
forbidden_heads = {H.assessmentHasStatus, H.hasLegalStatus, H.releasePublishesCandidate, H.hasReviewDecision,
                   H.ReviewDecision, H.ApprovalDecision, H.codingReview, H.correspondenceReview, H.specificityReview,
                   H.NationalSpecificity}
VAR_PROPS = (SW.argument1, SW.argument2)


def atom_vars(atom):
    vs = {ttl.value(atom, p) for p in VAR_PROPS} - {None}
    args = ttl.value(atom, SW.arguments)
    if args is not None:
        vs |= set(Collection(ttl, args))
    return {v for v in vs if (v, RDF.type, SW.Variable) in ttl}


for r in rules:
    body, head = ttl.value(r, SW.body), ttl.value(r, SW.head)
    assert body is not None and head is not None, r
    assert ttl.value(r, RDFS.comment) is not None, f"{r}: regra sem ressalva (rdfs:comment)"
    body_atoms, head_atoms = list(Collection(ttl, body)), list(Collection(ttl, head))
    assert len(head_atoms) == 1, r
    for a in head_atoms:
        pred = ttl.value(a, SW.propertyPredicate) or ttl.value(a, SW.classPredicate)
        assert pred not in forbidden_heads, f"{r} afirma {pred} automaticamente"
    body_vars = set().union(*(atom_vars(a) for a in body_atoms))
    head_vars = set().union(*(atom_vars(a) for a in head_atoms))
    assert head_vars <= body_vars, f"{r}: variável da cabeça ausente do corpo (regra insegura)"

print(f"OK: {len(ttl)} RDF triples, {len(mandatory)} canonical classes, {len(v110_classes)} v1.1.0 classes, "
      f"{len(v120_classes)} v1.2.0 classes "
      f"and {len(rules)} safe SWRL rules")
