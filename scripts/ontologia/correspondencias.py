#!/usr/bin/env python3
"""Provision correspondences between the PL 2338 Senate text (2024) and the AI Act (ESP-ONT-02, RF-06; PC2).

Unlike the text extraction, a correspondence is a JUDGMENT: two provisions are read side by side and
classified as equivalent, adapted, partial or divergent. The table below was written by the loop
session (Claude Code, LLM-assisted analysis) after reading both articles in the graph; every row
carries its reasoning. All rows enter as pending CandidateAssertions with the analyst recorded; no
review decision is created (I-3), so rule R26 infers no transposition until a human approves.

Output: ontologies/regulatory/correspondencias/BR_UE_PL2338_AIAct.ttl

Usage:
  python3 scripts/ontologia/correspondencias.py           # regenerate
  python3 scripts/ontologia/correspondencias.py --check   # fail if the output differs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import rdflib
from rdflib import Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ontologies/regulatory/correspondencias/BR_UE_PL2338_AIAct.ttl"
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
COR = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/correspondencias/br-ue#")
PL = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/br/pl2338#")
EU = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/data/regulatory/eu/aiact#")
COMP = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/comparativo#")
TYPE = {"equivalente": H.EquivalentCorrespondence, "adaptado": H.AdaptedCorrespondence,
        "parcial": H.PartialCorrespondence, "divergente": H.DivergentCorrespondence}

# (BR art. of the 2024 text, EU Article, type, area, reasoning)
TABLE = [
    (13, 5, "adaptado", "RiskClassification", "Ambos vedam práticas de risco inaceitável; a lista brasileira de risco excessivo segue a lógica do art. 5 com recortes próprios (por exemplo, sistemas de armas autônomas)."),
    (14, 6, "adaptado", "RiskClassification", "Ambos definem o alto risco por finalidade e contexto de uso; o PL enumera os usos no corpo da lei, o AI Act remete ao Anexo III e a produtos regulados."),
    (12, 6, "parcial", "RiskClassification", "A avaliação preliminar do PL é a autoavaliação de enquadramento; o art. 6 do AI Act prevê a autoavaliação só na derrogação do art. 6(3)."),
    (17, 9, "parcial", "ImpactAssessment", "Medidas gerais de governança e segurança do PL cobrem parte do sistema de gestão de riscos exigido pelo art. 9, sem o mesmo detalhamento de ciclo de vida."),
    (8, 14, "adaptado", "RightsRedress", "Supervisão humana de sistemas de alto risco nos dois textos, com finalidade de prevenir riscos a direitos; o AI Act detalha medidas técnicas do fornecedor."),
    (25, 27, "adaptado", "ImpactAssessment", "Avaliação de impacto algorítmico (PL) e avaliação de impacto sobre direitos fundamentais (AI Act); no PL a obrigação alcança desenvolvedor ou aplicador de alto risco, no AI Act só certos aplicadores."),
    (19, 50, "adaptado", "InfoIntegrity", "Identificação de conteúdo sintético gerado por IA nos dois textos, considerando o estado da arte."),
    (29, 53, "adaptado", "GenerativeGpai", "Obrigações do desenvolvedor de IA de propósito geral e generativa (PL) e do fornecedor de modelos de propósito geral (AI Act): documentação e avaliação."),
    (30, 55, "adaptado", "GenerativeGpai", "Obrigações adicionais para IA de propósito geral com risco sistêmico nos dois textos."),
    (54, 68, "parcial", "OversightInstitutions", "O Cecia orienta e supervisiona técnica e cientificamente; o art. 68 exige peritos independentes de fornecedores. O PL não declara a independência: ver tese C04."),
    (55, 57, "adaptado", "InnovationSandbox", "Ambiente regulatório experimental (sandbox) promovido pelas autoridades nos dois textos."),
    (67, 62, "adaptado", "SmeCompetition", "Critérios diferenciados para microempresas, pequenas empresas e startups (PL) e medidas para PME e startups (AI Act)."),
    (42, 73, "adaptado", "MonitoringLearning", "Comunicação de incidente grave à autoridade nos dois textos; prazos e conteúdo definidos de modo diferente."),
    (44, 71, "adaptado", "Transparency", "Base de dados pública de sistemas de alto risco (PL) e base de dados da UE para sistemas do Anexo III (AI Act)."),
    (45, 70, "divergente", "OversightInstitutions", "O PL cria um sistema nacional (SIA) coordenado pela autoridade competente com as autoridades setoriais; o AI Act exige que cada Estado-membro designe autoridades nacionais competentes, sob coordenação europeia."),
    (50, 99, "adaptado", "EnforcementCapacity", "Sanções administrativas com multa limitada por valor e por faturamento nos dois textos; os tetos são diferentes (R$ 50 milhões ou 2% no PL)."),
    (6, 86, "adaptado", "RightsRedress", "Direito à explicação de decisões de sistemas de alto risco nos dois textos; o PL soma o direito de contestar e de pedir revisão humana."),
    (62, 53, "parcial", "CopyrightIp", "O PL dedica uma seção a direitos de autor (informação sobre conteúdos usados, exceções e remuneração); no AI Act o tema aparece só nas obrigações de modelos de propósito geral (política de direitos autorais e resumo dos dados de treinamento)."),
]


def build() -> rdflib.Graph:
    g = rdflib.Graph()
    for p, ns in (("hrai", H), ("cor", COR), ("pl", PL), ("eu", EU), ("comp", COMP), ("dcterms", DCTERMS)):
        g.bind(p, ns)
    onto = URIRef(str(COR)[:-1])
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal("Correspondências BR (PL 2338, texto do Senado) × UE (AI Act): candidatas", lang="pt")))
    g.add((onto, RDFS.comment, Literal("Gerado por scripts/ontologia/correspondencias.py. Julgamento de leitura (análise assistida por LLM), "
                                       "pendente de revisão humana; sem revisão, R26 não infere transposição.", lang="pt")))
    agent, batch = COR.AnalistaSessaoLoop, COR.Lote_Correspondencias
    g.add((agent, RDF.type, H.MonitoringAgent))
    g.add((agent, RDFS.label, Literal("Sessão do loop ESP-ONT-02 (Claude Code, análise assistida por LLM)", lang="pt")))
    g.add((batch, RDF.type, H.ExtractionBatch))
    g.add((batch, RDFS.label, Literal("Lote de correspondências BR × UE", lang="pt")))
    for br, eu, kind, area, why in TABLE:
        c = COR[f"Corr_BR{br:03d}_EU{eu:03d}"]
        g.add((c, RDF.type, H.ProvisionCorrespondence))
        g.add((c, RDFS.label, Literal(f"PL 2338 (Senado, 2024) art. {br} × AI Act art. {eu}: {kind}", lang="pt")))
        g.add((c, H.correspondenceFrom, EU[f"Art_{eu:03d}"]))
        g.add((c, H.correspondenceTo, PL[f"Art_2024_{br:03d}"]))
        g.add((c, H.correspondenceHasType, TYPE[kind]))
        g.add((c, H.correspondenceAnalyst, agent))
        g.add((c, RDFS.comment, Literal(why, lang="pt")))
        g.add((c, DCTERMS.subject, COMP["Area_" + area]))
        cand = COR["Candidate_" + str(c).split("#")[-1]]
        g.add((cand, RDF.type, H.CandidateAssertion))
        g.add((cand, RDFS.label, Literal("Candidato: " + f"art. {br} × art. {eu} ({kind})", lang="pt")))
        g.add((cand, H.candidateProducedBy, agent))
        g.add((cand, DCTERMS.subject, c))
        g.add((batch, H.extractionContainsCandidate, cand))
    return g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    g = build()
    if args.check:
        ok = OUT.exists() and isomorphic(g, rdflib.Graph().parse(OUT))
        print("correspondências:", "atualizadas" if ok else "DESATUALIZADAS: rode python3 scripts/ontologia/correspondencias.py")
        return 0 if ok else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("# Gerado por scripts/ontologia/correspondencias.py. Não editar à mão.\n" + g.serialize(format="turtle"), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(TABLE)} correspondências candidatas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
