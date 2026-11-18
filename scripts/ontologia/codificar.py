#!/usr/bin/env python3
"""Code Brazil (PL 2338, Senate text 2024) and the EU (AI Act) on the 25 criteria plus E1 (ESP-ONT-02, RF-16; V-08, V-09).

Scales: approved by the author (decision D-02, ontologies/comparativo/escalas-E4.json). Every value of the loop
session cites the article(s) of the primary text that justify it (codingJustifiedBy); a value 0 cites the
article whose scope shows the absence, with a note. Codings enter as pending candidates (I-3).

Next to them, the codings of the paper's authors (Alanoca et al., 2025, Tables 3-4 and 9-10) are recorded as
written, with the value mapped by the session onto the same scale, so that agreement can be published per
criterion (V-09). Each divergence states how it was resolved against the primary text.

The judgment of each value is the session's (LLM-assisted reading of the articles in the graph); the rows
below are the record of that reading.

Outputs:
  ontologies/comparativo/codificacoes/BR_UE_codificacoes.ttl
  docs/especificacoes/ESP-ONT-02/concordancia-codificacoes.md

Usage:
  python3 scripts/ontologia/codificar.py           # regenerate
  python3 scripts/ontologia/codificar.py --check   # fail if outputs differ
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import rdflib
from rdflib import Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, XSD

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ontologies/comparativo/codificacoes/BR_UE_codificacoes.ttl"
REPORT = ROOT / "docs/especificacoes/ESP-ONT-02/concordancia-codificacoes.md"
SCALES = json.loads((ROOT / "ontologies/comparativo/escalas-E4.json").read_text(encoding="utf-8"))["escalas"]
H = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/regulatory#")
C = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/comparativo#")
K = rdflib.Namespace("https://hrai-go.aeonbridge.io/data/comparativo/codificacoes#")
PL = rdflib.Namespace("https://hrai-go.aeonbridge.io/data/regulatory/br/pl2338#")
EU = rdflib.Namespace("https://hrai-go.aeonbridge.io/data/regulatory/eu/aiact#")
DOI = URIRef("https://doi.org/10.1145/3715275.3732059")
SUBJECT = {"BR": PL.Versao_2024, "UE": EU.AIAct_2024}
ART = {"BR": lambda n: PL[f"Art_2024_{n:03d}"], "UE": lambda n: EU[f"Art_{n:03d}"]}
CRIT = {k.split("_")[0]: k for k in SCALES}

# Session codings: (jurisdiction, criterion, value, articles, note)
OURS = [
    ("BR", "C01", 2, [1], "Aprovado pelo Senado (10/12/2024), em tramitação na Câmara; o status vem da versão, não de um artigo."),
    ("BR", "C02", 2, [1], "Lei nova dedicada à governança de sistemas de IA."),
    ("BR", "C03", 1, [1], "O art. 1 articula a lei com a LGPD, a Política Nacional do Meio Ambiente e a Lei de Direitos Autorais; ecossistema digital ainda em formação."),
    ("BR", "C04", 2, [29, 30, 32], "Seção própria para IA de propósito geral e generativa."),
    ("BR", "C05", 2, [17, 18], "Obrigações dos agentes de IA (desenvolvedores e aplicadores)."),
    ("BR", "C06", 2, [22, 23, 24], "Seção própria de medidas de governança aplicadas pelo poder público."),
    ("BR", "C07", 0, [1], "O art. 1, § 1º, I, exclui o uso por pessoa natural para fim exclusivamente particular e não econômico."),
    ("BR", "C08", 2, [42], "Comunicação de incidente grave à autoridade setorial."),
    ("BR", "C09", 1, [34], "Acreditação de organismos de avaliação de conformidade, como faculdade, sem regra operacional na lei."),
    ("BR", "C10", 1, [45, 46], "SIA coordenado pela ANPD com as autoridades setoriais existentes."),
    ("BR", "C11", 2, [35, 36, 37], "Responsabilidade civil pelo CDC e pelo Código Civil, com inversão do ônus da prova."),
    ("BR", "C12", 2, [55, 56, 57], "Ambiente regulatório experimental (sandbox) com regras de funcionamento."),
    ("BR", "C13", 0, [50], "Só sanções administrativas no art. 50; nenhuma sanção penal."),
    ("BR", "C14", 2, [50], "Multa limitada a R$ 50 milhões por infração ou 2% do faturamento."),
    ("BR", "C15", 2, [50], "Suspensão parcial ou total, temporária ou definitiva, do desenvolvimento, fornecimento ou operação (art. 50, V)."),
    ("BR", "C16", 1, [24], "Padrões mínimos de transparência para o setor público federal, a cargo do Executivo; sem regime geral de normas técnicas."),
    ("BR", "C17", 2, [49], "A autoridade competente realiza ou determina auditorias de sistemas de alto risco (art. 49, VII)."),
    ("BR", "C18", 1, [54], "Comitê de Especialistas e Cientistas de IA (Cecia), com composição e funcionamento definidos por regulamento."),
    ("BR", "C19", 1, [4, 68], "Definições alinhadas a referências internacionais e diretriz de cooperação internacional (art. 68, VII)."),
    ("BR", "C20", 2, [53], "Indicador indireto: o critério mede a consulta no processo legislativo, que não está no texto; o Cria prevê cooperação com a sociedade civil."),
    ("BR", "C21", 2, [40, 41, 53], "Indicador indireto: códigos de boas práticas e autorregulação pelos agentes; Cria."),
    ("BR", "C22", 3, [12, 25, 26], "Avaliação preliminar e avaliação de impacto algorítmico antes da introdução no mercado."),
    ("BR", "C23", 3, [6, 35, 36, 37], "Direitos de explicação, contestação e revisão humana, mais regime de responsabilidade civil."),
    ("BR", "C24", 1, [29, 30], "IA de propósito geral como camada secundária, numa seção de três artigos."),
    ("BR", "C25", 2, [14], "Classificação de alto risco por finalidade e contexto de uso."),
    ("BR", "E1", 3, [1], "Projeto de lei."),
    ("UE", "C01", 3, [113], "Regulamento publicado e em vigor, com aplicação escalonada."),
    ("UE", "C02", 2, [1], "Regulamento novo dedicado à IA."),
    ("UE", "C03", 3, [2], "O art. 2 articula o regulamento com o RGPD e outros atos do mercado digital; ecossistema maduro."),
    ("UE", "C04", 2, [51, 53, 55], "Capítulo próprio para modelos de propósito geral, inclusive com risco sistêmico."),
    ("UE", "C05", 2, [16], "Obrigações dos fornecedores de sistemas de alto risco."),
    ("UE", "C06", 2, [2, 27], "Autoridades públicas como responsáveis pela implantação; avaliação de impacto sobre direitos fundamentais para organismos públicos."),
    ("UE", "C07", 0, [2], "O art. 2, n.º 10, exclui pessoas singulares em atividade puramente pessoal e não profissional."),
    ("UE", "C08", 2, [72, 73], "Acompanhamento pós-comercialização e comunicação de incidentes graves."),
    ("UE", "C09", 2, [43], "Avaliação da conformidade com intervenção de organismo notificado (terceiro) nos casos do Anexo VII."),
    ("UE", "C10", 2, [64, 70], "Serviço para a IA (AI Office) criado na Comissão, ao lado das autoridades nacionais."),
    ("UE", "C11", 0, [2], "O regulamento não trata de responsabilidade civil; ausência verificada nos 113 artigos extraídos."),
    ("UE", "C12", 2, [57], "Cada Estado-membro cria ao menos um sandbox regulatório."),
    ("UE", "C13", 0, [99], "Sanções administrativas; nenhuma sanção penal prevista no regulamento."),
    ("UE", "C14", 2, [99], "Coimas até 35 milhões de euros ou 7% do volume de negócios mundial."),
    ("UE", "C15", 2, [79], "A autoridade de fiscalização pode exigir retirada ou recolha do sistema, com prazo definido."),
    ("UE", "C16", 2, [40], "Normas harmonizadas publicadas no Jornal Oficial, com presunção de conformidade."),
    ("UE", "C17", 2, [74], "Acesso da autoridade de fiscalização ao código-fonte sob condições definidas."),
    ("UE", "C18", 2, [68], "Painel científico de peritos independentes."),
    ("UE", "C19", 1, [3], "Definição de sistema de IA alinhada à da OCDE."),
    ("UE", "C20", 2, [67], "Indicador indireto: fórum consultivo com sociedade civil, indústria e academia."),
    ("UE", "C21", 2, [67], "Indicador indireto: fórum consultivo com indústria, startups e PME."),
    ("UE", "C22", 3, [6, 43], "Classificação de alto risco e avaliação da conformidade antes da colocação no mercado."),
    ("UE", "C23", 2, [85, 86], "Direito de apresentar reclamação e direito a explicação de decisões individuais."),
    ("UE", "C24", 2, [51, 53, 55], "Capítulo próprio para modelos de propósito geral e risco sistêmico."),
    ("UE", "C25", 2, [6], "Classificação por uso, com o Anexo III."),
    ("UE", "E1", 3, [113], "Regulamento (lei vinculante)."),
]
# Paper authors' codings, as written (abridged), with the value mapped onto the approved scale.
AUTHORS = {
    "BR": {"C01": ("approved by the Brazilian Senate", 2), "C02": ("New law.", 2), "C03": ("Complementing an emerging digital regulatory environment", 1),
           "C04": ("Applies to GPAI systems and generative AI systems.", 2), "C05": ("Law targets industry.", 2),
           "C06": ("Not primarily targeting government or federal agencies.", 1), "C07": ("Not primarily targeting individuals.", 1),
           "C08": ("registration and documentation of the preliminary assessment", 2), "C09": ("Audit to be completed by a competent authority", 1),
           "C10": ("Leveraging existing agencies; SIA", 1), "C11": ("Includes a liability regime.", 2), "C12": ("Includes regulatory sandboxes.", 2),
           "C13": ("Not included.", 0), "C14": ("up to BRL 50 million or 2% of turnover", 2), "C15": ("Included.", 1),
           "C16": ("Not directly included within the law.", 0), "C17": ("Audit to be completed by a competent authority", 1),
           "C18": ("No new center of expertise", 0), "C19": ("Aligned with some definitions set by international stakeholders", 1),
           "C20": ("higher level of inclusion of civil society", 3), "C21": ("Inclusion of private stakeholders", 2),
           "C22": ("High level of ex ante requirements.", 3), "C23": ("Medium level of ex post remedies.", 2),
           "C24": ("Targets, as a secondary regulatory layer, GPAI", 1), "C25": ("Primarily targets context or application based AI", 2)},
    "UE": {"C01": ("adopted by the EU in July 2024", 3), "C02": ("New law.", 2), "C03": ("Very mature landscape (GDPR, DMA, DSA, Chips Act)", 3),
           "C04": ("Applies to GPAI systems, models, and models with systemic risk.", 2), "C05": ("Law targets industry.", 2),
           "C06": ("Includes government and federal agencies.", 2), "C07": ("Does not directly target individuals.", 0),
           "C08": ("Serious AI incidents need to be reported", 2), "C09": ("does not explicitly mention third-party audits", 1),
           "C10": ("new EU level regulator, the EU AI Office", 2), "C11": ("Not directly covered in the EU AI Act", 0),
           "C12": ("Art. 57: at least one AI regulatory sandbox", 2), "C13": ("No mention of charges", 0),
           "C14": ("up to 35 000 000 EUR or 7%", 2), "C15": ("Included.", 1), "C16": ("CEN, CENELEC and ETSI standards", 2),
           "C17": ("access to source code; periodic audits by notified bodies", 2), "C18": ("JRC, AI Office, scientific panel", 2),
           "C19": ("definition aligned with that of the OECD", 1), "C20": ("Inclusion of civil society through the AI HLG", 2),
           "C21": ("Inclusion of private sector through the AI HLG", 2), "C22": ("High level of ex ante requirements.", 3),
           "C23": ("Medium level of ex post remedies.", 2), "C24": ("Targeting GPAI systems, models, and models with systemic risk.", 2),
           "C25": ("Risk classification takes into account most sensitive applications.", 2)},
}


def build() -> tuple[rdflib.Graph, str]:
    g = rdflib.Graph()
    for p, ns in (("hrai", H), ("comp", C), ("cod", K), ("pl", PL), ("eu", EU), ("dcterms", DCTERMS)):
        g.bind(p, ns)
    onto = URIRef(str(K)[:-1])
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal("Codificações de Brasil e UE nos 25 critérios e na E1, com as dos autores do paper", lang="pt")))
    g.add((onto, OWL.imports, URIRef("https://hrai-go.aeonbridge.io/ontology/comparativo")))
    session, authors, batch = K.SessaoLoop, K.AutoresAlanoca2025, K.Lote_Codificacoes
    g.add((session, RDF.type, H.MonitoringAgent))
    g.add((session, RDFS.label, Literal("Sessão do loop ESP-ONT-02 (Claude Code, leitura assistida por LLM dos artigos no grafo)", lang="pt")))
    g.add((authors, RDFS.label, Literal("Alanoca, Gur-Arieh, Zick e Klyman (2025), Tabelas 3-4 (UE) e 9-10 (Brasil)", lang="pt")))
    g.add((authors, DCTERMS.source, DOI))
    g.add((batch, RDF.type, H.ExtractionBatch))
    g.add((batch, RDFS.label, Literal("Lote: codificações de Brasil e UE (escalas aprovadas, D-02)", lang="pt")))
    rows = []
    for jur, code, value, arts, note in OURS:
        crit = CRIT[code]
        x = K[f"Cod_{jur}_{code}"]
        g.add((x, RDF.type, H.CriterionCoding))
        g.add((x, RDFS.label, Literal(f"{jur} · {code} = {value} ({SCALES[crit][value]})", lang="pt")))
        g.add((x, H.codingSubject, SUBJECT[jur]))
        g.add((x, H.codingCriterion, C[crit]))
        g.add((x, H.codingScaleValue, Literal(f"{value}.0", datatype=XSD.decimal)))
        g.add((x, H.codingValueLabel, Literal(SCALES[crit][value], lang="pt")))
        g.add((x, H.codingCoder, session))
        g.add((x, RDFS.comment, Literal(note, lang="pt")))
        for n in arts:
            g.add((x, H.codingJustifiedBy, ART[jur](n)))
        cand = K["Candidate_" + str(x).split("#")[-1]]
        g.add((cand, RDF.type, H.CandidateAssertion))
        g.add((cand, RDFS.label, Literal("Candidato: codificação " + str(x).split("#")[-1], lang="pt")))
        g.add((cand, H.candidateProducedBy, session))
        g.add((cand, DCTERMS.subject, x))
        g.add((batch, H.extractionContainsCandidate, cand))
        if code in AUTHORS.get(jur, {}):
            text, mapped = AUTHORS[jur][code]
            a = K[f"Cod_{jur}_{code}_Autores"]
            g.add((a, RDF.type, H.CriterionCoding))
            g.add((a, RDFS.label, Literal(f"{jur} · {code} segundo os autores do paper", lang="pt")))
            g.add((a, H.codingSubject, SUBJECT[jur]))
            g.add((a, H.codingCriterion, C[crit]))
            g.add((a, H.codingScaleValue, Literal(f"{mapped}.0", datatype=XSD.decimal)))
            g.add((a, H.codingValueLabel, Literal(text, lang="en")))
            g.add((a, H.codingCoder, authors))
            g.add((a, DCTERMS.source, DOI))
            g.add((a, RDFS.comment, Literal("Valor descritivo dos autores; conversão para a escala aprovada feita pela sessão.", lang="pt")))
            rows.append((jur, code, value, mapped, text, arts, note))
    return g, report(rows)


def report(rows) -> str:
    L = ["# Concordância das codificações com os autores do paper (V-09)", "",
         "Brasil: PL 2338, texto aprovado pelo Senado (2024). UE: AI Act. Escalas aprovadas pelo autor (D-02). Os valores dos autores "
         "(Alanoca et al., 2025, Tabelas 3-4 e 9-10) são descritivos; a conversão para a escala é da sessão. Cada divergência foi "
         "resolvida contra o texto primário: vale o valor da sessão, com o artigo citado. Gerado por `scripts/ontologia/codificar.py`.", ""]
    for jur in ("BR", "UE"):
        mine = [r for r in rows if r[0] == jur]
        agree = sum(1 for r in mine if r[2] == r[3])
        L += [f"## {jur}: {agree} de {len(mine)} critérios concordantes ({100 * agree // len(mine)}%)", "",
              "| Critério | Sessão | Autores | Resolução |", "|---|---|---|---|"]
        for _, code, value, mapped, text, arts, note in mine:
            res = "concorda" if value == mapped else f"divergência resolvida contra o texto primário (art. {', '.join(map(str, arts))}): {note}"
            L.append(f"| {code} | {value} | {mapped} ({text}) | {res} |")
        L.append("")
    return "\n".join(L).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    g, md = build()
    if args.check:
        ok = OUT.exists() and isomorphic(g, rdflib.Graph().parse(OUT)) and REPORT.exists() and REPORT.read_text(encoding="utf-8") == md
        print("codificações:", "atualizadas" if ok else "DESATUALIZADAS: rode python3 scripts/ontologia/codificar.py")
        return 0 if ok else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("# Gerado por scripts/ontologia/codificar.py. Não editar à mão. Candidatos pendentes de revisão.\n" + g.serialize(format="turtle"), encoding="utf-8")
    REPORT.write_text(md, encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(OURS)} codificações da sessão; relatório em {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
