"""RF-08: competency questions PC1-PC9 are versioned, answer on the real graph and work on a fixture."""

import subprocess
import sys
from pathlib import Path

import rdflib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/ontologia"))
import raciocinar  # noqa: E402

Q = ROOT / "ontologies/consultas"
H = "https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#"
S = "https://github.com/aeonbridge/ab-hrai-go-platform/ontology/scse#"
C = "https://github.com/aeonbridge/ab-hrai-go-platform/ontology/comparativo#"

FIXTURE = f"""
@prefix hrai: <{H}> . @prefix scse: <{S}> . @prefix comp: <{C}> . @prefix ex: <http://example.test/q#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
ex:BR a hrai:Jurisdiction . ex:EU a hrai:Jurisdiction .
ex:Lei a hrai:EnactedLegalInstrument ; hrai:instrumentInJurisdiction ex:BR . ex:LeiV a hrai:LegalInstrumentVersion ; hrai:versionOfInstrument ex:Lei .
ex:art1 a hrai:LegalProvision ; hrai:provisionOfVersion ex:LeiV ; hrai:provisionAddressesFunction ex:Saude ; hrai:provisionInJurisdiction ex:BR .
ex:PL a hrai:LegislativeProposal ; hrai:proposalInJurisdiction ex:BR . ex:PLV a hrai:LegalInstrumentVersion ; hrai:versionOfInstrument ex:PL .
ex:art9 a hrai:LegalProvision ; hrai:provisionOfVersion ex:PLV ; hrai:provisionAddressesFunction ex:Energia ; hrai:provisionInJurisdiction ex:BR .
ex:Plano a hrai:PolicyInstrument ; hrai:policyInstrumentInJurisdiction ex:BR ; hrai:provisionAddressesFunction ex:Computacao .
ex:Saude a hrai:SubstantiveArea . ex:Energia a hrai:SubstantiveArea . ex:Computacao a hrai:SubstantiveArea . ex:Criancas a hrai:SubstantiveArea .
ex:orc a hrai:ContextIndicator ; hrai:hasNumericValue "10"^^xsd:decimal ; hrai:hasLowerAlertThreshold "50"^^xsd:decimal .
ex:cap a hrai:CapacityRequirement ; hrai:capacityMeasuredBy ex:orc . ex:req a hrai:NormativeRequirement ; hrai:requirementAssumesCapacity ex:cap .
ex:capSemInd a hrai:CapacityRequirement . ex:req2 a hrai:NormativeRequirement ; hrai:requirementAssumesCapacity ex:capSemInd .
ex:art6EU a hrai:LegalProvision ; hrai:provisionInJurisdiction ex:EU . ex:ok a hrai:ApprovalDecision .
ex:corr a hrai:ProvisionCorrespondence ; hrai:correspondenceFrom ex:art6EU ; hrai:correspondenceTo ex:art9 ;
        hrai:correspondenceHasType hrai:AdaptedCorrespondence ; hrai:correspondenceReview ex:ok ; hrai:groundedInSpecificity ex:esp .
ex:expo a hrai:RiskExposureIndicator ; hrai:exposureConcernsFunction ex:Criancas .
ex:cov a hrai:CoverageAssessment ; hrai:coverageOfFunction ex:Criancas ; hrai:coverageForJurisdiction ex:BR .
ex:cod a hrai:CriterionCoding ; hrai:codingSubject ex:PLV ; hrai:codingCriterion comp:C22_ExAnte ; hrai:codingScaleValue "3"^^xsd:decimal ; hrai:codingJustifiedBy ex:art9 .
ex:esp a hrai:NationalSpecificity ; rdfs:label "Soberania computacional com orçamento" ; hrai:specificityDimension hrai:StrategicObjectiveDimension ;
       hrai:differenceType hrai:BrazilOnlyDifference ; hrai:specificityGroundedIn ex:Plano ; hrai:specificityComparison ex:cmpEU .
ex:cmpEU hrai:comparisonJurisdiction ex:EU ; hrai:comparisonNotCoded true .
ex:assento a hrai:SyntheticStakeholderPerspective . ex:pessoa a hrai:IdentifiedStakeholder . ex:tese a hrai:PolicyClaim . ex:alt a hrai:PolicyAlternative .
ex:p1 a hrai:StakeholderPosition ; hrai:positionExpressedBy ex:assento ; hrai:positionSupportsClaim ex:tese .
ex:p2 a hrai:StakeholderPosition ; hrai:positionExpressedBy ex:pessoa ; scse:positionChallengesAlternative ex:alt .
"""


def fixture_graph(tmp_path):
    fx = tmp_path / "q.ttl"
    fx.write_text(FIXTURE, encoding="utf-8")
    rz = raciocinar.Raciocinador(ROOT / "ontologies/regulatory/HRAI_GO_Regulatory_General.ttl",
                                 ROOT / "ontologies/scse/SCSE_Shadow_Council_Ontology.ttl",
                                 ROOT / "ontologies/comparativo/HRAI_GO_Comparativo.ttl", fx)
    rz.executar()
    return rz.g


def rows(g, name):
    q = next(p for p in Q.glob(name + "_*.rq") if not p.name.startswith("._"))
    return [{k: (str(v) if v is not None else None) for k, v in r.asdict().items()} for r in g.query(q.read_text(encoding="utf-8"))]


def test_all_nine_questions_are_versioned():
    names = {p.stem.split("_")[0] for p in Q.glob("PC*.rq") if not p.name.startswith("._")}
    assert names == {f"PC{i}" for i in range(1, 10)}


def test_regression_on_the_real_graph():
    assert subprocess.run([sys.executable, str(ROOT / "scripts/ontologia/consultas.py"), "--check"]).returncode == 0


def test_each_question_answers_on_fixture(tmp_path):
    g = fixture_graph(tmp_path)
    pc1 = {(r["area"].split("#")[-1], r["forca"]) for r in rows(g, "PC1")}
    assert pc1 == {("Saude", "vigente"), ("Energia", "proposta"), ("Computacao", "plano")}
    pc2 = rows(g, "PC2")
    assert len(pc2) == 1 and pc2[0]["transposto"] == "true" and pc2[0]["especificidade"].endswith("#esp")
    assert {r["situacao"] for r in rows(g, "PC3")} == {"abaixo do limiar", "sem indicador"}
    pc4 = rows(g, "PC4")
    assert len(pc4) == 1 and pc4[0]["area"].endswith("#Criancas")
    assert rows(g, "PC5")[0]["notacao"] == "C22"
    pc8 = {(r["posicao"].split("#")[-1], r["origem"]) for r in rows(g, "PC8")}
    assert pc8 == {("p1", "sintética"), ("p2", "humana")}
    pc9 = rows(g, "PC9")
    assert len(pc9) == 1 and pc9[0]["naoCodificado"] == "true" and pc9[0]["tipo"].endswith("BrazilOnlyDifference")
