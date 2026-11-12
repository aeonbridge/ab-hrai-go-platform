from pathlib import Path
from rdflib import Graph, Namespace, RDF, OWL
from rdflib.compare import isomorphic
root = Path(__file__).resolve().parents[1] / "ontologies" / "regulatory"
ttl = Graph().parse(root / "HRAI_GO_Regulatory_General.ttl", format="turtle")
owl = Graph().parse(root / "HRAI_GO_Regulatory_General.owl", format="xml")
assert isomorphic(ttl, owl), "Turtle and RDF/XML graphs differ"
H = Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
SW = Namespace("http://www.w3.org/2003/11/swrl#")
mandatory = ["Jurisdiction","LegalInstrument","LegislativeProposal","LegalProvision","NormativeRequirement","RegulatoryModel","NationalContext","ContextIndicator","PolicyObjective","PolicyInstrument","RegulatoryTension","RegulatoryGap","PolicyClaim","PolicyAlternative","Stakeholder","StakeholderPosition","Deliberation","PolicyImpactAssessment"]
for name in mandatory:
    assert (H[name], RDF.type, OWL.Class) in ttl, name
rules = list(ttl.subjects(RDF.type, SW.Imp))
assert len(rules) == 18, (len(rules), "SWRL rule count")
assert len(set(rules)) == len(rules)
for r in rules:
    assert ttl.value(r, SW.body) is not None
    assert ttl.value(r, SW.head) is not None
    assert (r, SW.head, None) in ttl
print(f"OK: {len(ttl)} RDF triples, {len(mandatory)} canonical classes and {len(rules)} SWRL rules")
