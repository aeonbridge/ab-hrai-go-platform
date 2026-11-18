#!/usr/bin/env python3
"""Initial answers to the guiding questions (ESP-ONT-02, RF-18; RT-VIS-03, step M5 and section 7.5).

QN1  specificities of Brazil versus the other jurisdictions of the corpus (NationalSpecificity), each with
     a QN1 dimension, a difference type, Brazilian evidence and one comparison per other jurisdiction.
QN2  what is considered and should not be: incorporated requirements that presuppose capacity the
     context lacks, each grounded in a QN1 specificity (groundedInSpecificity).
QN3  what is not considered and should be, each grounded in a specificity and with its scope stated.

How this first answer is produced (bootstrap). Step M5 needs every jurisdiction coded on the same
yardstick; the codings wait for the approved E4 scales (decision D-02). So, in this first run, the
detection of differences was done by the loop session over the graph, item by item (LLM-assisted
analysis), and every row below cites the individuals of the graph it rests on. Comparisons for which the
corpus has no equivalent value are recorded as "não codificado", never as "não tem". When codings exist,
a detection query replaces this table. Everything is a candidate pending human decision (V-29).

Output: ontologies/regulatory/respostas/QN_respostas.ttl

Usage:
  python3 scripts/ontologia/responder_qn.py           # regenerate
  python3 scripts/ontologia/responder_qn.py --check   # fail if the output differs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import rdflib
from rdflib import Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ontologies/regulatory/respostas/QN_respostas.ttl"
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
R = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/respostas#")
D = "https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/"
PBIA, PL, CAP = rdflib.Namespace(D + "br/pbia#"), rdflib.Namespace(D + "br/pl2338#"), rdflib.Namespace(D + "br/capacidade#")
EU, UK, US = rdflib.Namespace(D + "eu/aiact#"), rdflib.Namespace(D + "uk/whitepaper#"), rdflib.Namespace(D + "us/nist#")
SEM = rdflib.Namespace(D + "br/sementes#")
COR = rdflib.Namespace(D + "correspondencias/br-ue#")
COMP = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/comparativo#")

DIM = {"contexto": H.NationalContextDimension, "capacidade": H.InstalledCapacityDimension,
       "exposicao": H.RiskExposureDimension, "objetivo": H.StrategicObjectiveDimension}
DIF = {"exclusiva": H.BrazilOnlyDifference, "ausente": H.AbsentInBrazilDifference,
       "intensidade": H.IntensityDifference, "contexto": H.ContextDifference}
JUR = {"UE": (PBIA.EuropeanUnion, EU.Snapshot_AIAct), "Reino Unido": (UK.UnitedKingdom, UK.Snapshot_WhitePaper),
       "EUA": (US.UnitedStates, US.Snapshot_AIRMF)}
NOT_A_PLAN = "não codificado: o instrumento da jurisdição no corpus não é plano de investimento (E1) e o plano equivalente não está no corpus"
NO_INDICATOR = "não codificado: o corpus não traz indicador equivalente para esta jurisdição"

# QN1: id, label, dimension, difference type, Brazilian evidence, {jurisdiction: (value, coded?)}
SPECIFICITIES = [
    ("S1_SoberaniaComputacional", "Soberania computacional com orçamento público: Nuvem Soberana (R$ 1 bilhão) e supercomputador de IA no PBIA",
     "objetivo", "exclusiva", [PBIA.Action27_SovereignCloud, PBIA.Action01_AISupercomputer],
     {j: (NOT_A_PLAN, False) for j in JUR}),
    ("S2_LinguaPortuguesa", "Modelos de linguagem em português com dados nacionais, para o português do Brasil em escala continental",
     "objetivo", "exclusiva", [PBIA.Action09_PortugueseLLM, SEM.Traco_CF_03],
     {j: (NOT_A_PLAN, False) for j in JUR}),
    ("S3_MatrizRenovavel", "Matriz elétrica majoritariamente renovável: 89,2% em 2023, segundo o PBIA (citando a EPE)",
     "contexto", "contexto", [PBIA.Ind_RenewableShareElectricityMatrix2023],
     {j: (NO_INDICATOR, False) for j in JUR}),
    ("S4_OrcamentoGovernanca", "Orçamento de governança pequeno: 0,45% do PBIA (R$ 103,25 milhões de R$ 23,03 bilhões) no Eixo 5",
     "capacidade", "contexto", [CAP.Ind_GovernanceBudgetShare],
     {j: (NO_INDICATOR, False) for j in JUR}),
    ("S5_ProfissionaisTIC", "Déficit estimado de 530 mil profissionais de TIC entre 2021 e 2025, segundo o PBIA",
     "capacidade", "contexto", [PBIA.Ind_ICTTalentDeficit2021_2025],
     {j: (NO_INDICATOR, False) for j in JUR}),
    ("S6_DadosSaudeSUS", "Dados de saúde em escala sob guarda do Estado (SUS): ativo e exposição de dados sensíveis",
     "exposicao", "contexto", [CAP.Exp_HealthDataSUS, SEM.Traco_CF_05],
     {j: (NO_INDICATOR, False) for j in JUR}),
    ("S7_SupervisaoPorSistema", "Supervisão por um sistema que coordena reguladores existentes (SIA, coordenado pela ANPD), com orçamento de governança pequeno",
     "capacidade", "intensidade", [PL.Art_2024_045, CAP.Ind_GovernanceBudgetShare],
     {"UE": ("art. 70 do AI Act: cada Estado-membro designa autoridades nacionais competentes, sob coordenação europeia", True),
      "Reino Unido": ("princípios não estatutários aplicados pelos reguladores existentes, sem autoridade nova", True),
      "EUA": ("não codificado: o NIST AI RMF é guia voluntário e não cria autoridade", False)}),
    ("S8_ResponsabilidadeCivil", "Responsabilidade civil por danos de IA pelas regras do Código de Defesa do Consumidor e do Código Civil, com inversão do ônus da prova",
     "contexto", "exclusiva", [PL.Art_2024_035, PL.Art_2024_036, PL.Art_2024_037],
     {"UE": ("não codificado: o AI Act não trata de responsabilidade civil e a diretiva de responsabilidade não está no corpus; ausência exige avaliação de cobertura (D-10)", False),
      "Reino Unido": ("não codificado: o white paper deixa a responsabilidade ao direito existente; sem avaliação de cobertura", False),
      "EUA": ("não codificado: guia voluntário", False)}),
]

# QN2 and QN3: id, question, label, specificities it rests on, graph individuals it cites, scope
ITEMS = [
    ("Q2_AvaliacaoImpactoSemProfissionais", "QN2",
     "A avaliação de impacto algorítmico obrigatória (art. 25 do texto do Senado, adaptada do art. 27 do AI Act) pressupõe profissionais técnicos que o déficit estimado de TIC indica faltar",
     ["S5_ProfissionaisTIC"], [CAP.Req_AlgorithmicImpactAssessment, COR.Corr_BR025_EU027], "texto do Senado de 2024 e indicador do PBIA; sem limiar aprovado (D-09)"),
    ("Q2_SupervisaoSemOrcamento", "QN2",
     "A supervisão, a fiscalização e a acreditação pela autoridade competente (arts. 34 e 49) pressupõem orçamento que o Eixo 5 do PBIA não prevê em escala",
     ["S4_OrcamentoGovernanca", "S7_SupervisaoPorSistema"], [CAP.Req_CompetentAuthoritySupervision, CAP.Req_ConformityAccreditation],
     "texto do Senado de 2024 e Tabela 2 do PBIA; sem limiar aprovado (D-09)"),
    ("Q3_DadosSUSTreinamento", "QN3",
     "Uso de dados públicos sensíveis, como os do SUS, para treinar modelos: o texto do Senado não tem regra específica; a escala desses dados pede salvaguarda própria",
     ["S6_DadosSaudeSUS"], [CAP.Exp_HealthDataSUS],
     "busca no texto do Senado de 2024: 'treinamento' aparece só em definições, IA de propósito geral, Cade e direitos autorais; sem avaliação de cobertura aprovada (D-10)"),
    ("Q3_AutoridadeComOrcamentoProprio", "QN3",
     "Fonte de financiamento própria e estável para o sistema de supervisão (SIA): o texto do Senado cria o sistema, mas nenhum artigo vincula orçamento a ele",
     ["S4_OrcamentoGovernanca", "S7_SupervisaoPorSistema"], [PL.Art_2024_045, CAP.Ind_GovernanceBudgetShare],
     "leitura dos arts. 45 a 49 do texto do Senado de 2024; sem avaliação de cobertura aprovada (D-10)"),
]
# Findings about the seed model, found while answering (they correct the chamber, not the law).
FINDINGS = [
    ("A_EnergiaNoTextoDoSenado",
     "A lacuna 'Energia e meio ambiente' da cúpula vem do modelo-semente; o texto do Senado trata o tema: eficiência energética de IA de propósito geral (art. 30), data centers sustentáveis (art. 59), uso eficiente de recursos (art. 60) e certificação ambiental com o Ministério do Meio Ambiente (art. 61)",
     [COMP.Area_EnergyEnvironment, PL.Art_2024_030, PL.Art_2024_059, PL.Art_2024_060, PL.Art_2024_061],
     "modelo da câmara (documento-semente) frente ao texto do Senado de 2024; corrigir o modelo na revisão das sementes (D-07)"),
]
# Correspondences explained or contradicted by a specificity (PC2).
CORRESPONDENCE_LINKS = [(COR.Corr_BR045_EU070, "S7_SupervisaoPorSistema"), (COR.Corr_BR025_EU027, "S5_ProfissionaisTIC")]


def build() -> rdflib.Graph:
    g = rdflib.Graph()
    for p, ns in (("hrai", H), ("resp", R), ("pbia", PBIA), ("pl", PL), ("cap", CAP), ("cor", COR), ("dcterms", DCTERMS), ("prov", PROV)):
        g.bind(p, ns)
    onto = URIRef(str(R)[:-1])
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal("Resposta inicial às perguntas norteadoras QN1, QN2 e QN3 (candidata)", lang="pt")))
    g.add((onto, RDFS.comment, Literal("Gerado por scripts/ontologia/responder_qn.py. Detecção feita pela sessão do loop sobre o grafo "
                                       "(análise assistida por LLM), por falta de codificações aprovadas (D-02). Tudo pendente de decisão humana.", lang="pt")))
    agent, batch = R.SessaoLoop, R.Lote_Respostas
    g.add((agent, RDF.type, H.MonitoringAgent))
    g.add((agent, RDFS.label, Literal("Sessão do loop ESP-ONT-02 (Claude Code, análise assistida por LLM)", lang="pt")))
    g.add((batch, RDF.type, H.ExtractionBatch))
    g.add((batch, RDFS.label, Literal("Lote: resposta inicial às perguntas norteadoras", lang="pt")))

    for sid, label, dim, dif, evidence, comps in SPECIFICITIES:
        s = R[sid]
        g.add((s, RDF.type, H.NationalSpecificity))
        g.add((s, RDFS.label, Literal(label, lang="pt")))
        g.add((s, H.answersGuidingQuestion, Literal("QN1")))
        g.add((s, H.specificityDimension, DIM[dim]))
        g.add((s, H.differenceType, DIF[dif]))
        for e in evidence:
            g.add((s, H.specificityGroundedIn, e))
        for jname, (value, coded) in comps.items():
            jur, snap = JUR[jname]
            c = R[f"{sid}_vs_{jname.replace(' ', '')}"]
            g.add((s, H.specificityComparison, c))
            g.add((c, RDF.type, H.JurisdictionComparison))
            g.add((c, H.comparisonJurisdiction, jur))
            g.add((c, H.comparisonValue, Literal(value, lang="pt")))
            g.add((c, H.comparisonNotCoded, Literal(not coded)))
            if coded:
                g.add((c, H.comparisonSource, snap))
        cand = R["Candidate_" + sid]
        g.add((cand, RDF.type, H.CandidateAssertion))
        g.add((cand, RDFS.label, Literal("Candidato QN1: " + label, lang="pt")))
        g.add((cand, H.candidateProducedBy, agent))
        g.add((cand, DCTERMS.subject, s))
        g.add((batch, H.extractionContainsCandidate, cand))

    for iid, qn, label, specs, cites, scope in ITEMS:
        x = R[iid]
        g.add((x, RDF.type, H.PolicyClaim))
        g.add((x, RDFS.label, Literal(label, lang="pt")))
        g.add((x, H.answersGuidingQuestion, Literal(qn)))
        g.add((x, H.answerScope, Literal(scope, lang="pt")))
        for sid in specs:
            g.add((x, H.groundedInSpecificity, R[sid]))
        ev = R["Ev_" + iid]
        g.add((ev, RDF.type, H.Evidence))
        g.add((ev, RDFS.label, Literal("Evidência do grafo para " + iid, lang="pt")))
        for c in cites:
            g.add((ev, DCTERMS.references, c))
        g.add((x, H.claimSupportedByEvidence, ev))
        cand = R["Candidate_" + iid]
        g.add((cand, RDF.type, H.CandidateAssertion))
        g.add((cand, RDFS.label, Literal(f"Candidato {qn}: " + label, lang="pt")))
        g.add((cand, H.candidateProducedBy, agent))
        g.add((cand, DCTERMS.subject, x))
        g.add((batch, H.extractionContainsCandidate, cand))

    for fid, label, cites, scope in FINDINGS:
        x = R[fid]
        g.add((x, RDF.type, H.PolicyClaim))
        g.add((x, RDFS.label, Literal(label, lang="pt")))
        g.add((x, H.answersGuidingQuestion, Literal("achado")))
        g.add((x, H.answerScope, Literal(scope, lang="pt")))
        ev = R["Ev_" + fid]
        g.add((ev, RDF.type, H.Evidence))
        g.add((ev, RDFS.label, Literal("Evidência do grafo para " + fid, lang="pt")))
        for c in cites:
            g.add((ev, DCTERMS.references, c))
        g.add((x, H.claimSupportedByEvidence, ev))

    for corr, sid in CORRESPONDENCE_LINKS:
        g.add((corr, H.groundedInSpecificity, R[sid]))
    return g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    g = build()
    if args.check:
        ok = OUT.exists() and isomorphic(g, rdflib.Graph().parse(OUT))
        print("respostas QN:", "atualizadas" if ok else "DESATUALIZADAS: rode python3 scripts/ontologia/responder_qn.py")
        return 0 if ok else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("# Gerado por scripts/ontologia/responder_qn.py. Não editar à mão. Candidato pendente de decisão humana.\n"
                   + g.serialize(format="turtle"), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(SPECIFICITIES)} especificidades, {len(ITEMS)} itens QN2/QN3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
