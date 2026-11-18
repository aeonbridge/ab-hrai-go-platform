#!/usr/bin/env python3
"""Generate the guiding-questions report from the graph (ESP-ONT-02, RF-18; RT-VIS-03, section 7.5; V-26 to V-30).

Reads only the reasoned graph: QN1 (PC9: specificities with dimension, difference type, evidence and the
comparison with every other jurisdiction), then QN2 and QN3 (items grounded in a specificity, with scope
and state), then the findings about the seed model. Sections in this order. Every item is marked as an
initial answer: nothing is published until a human decision is recorded (V-29).

State of each QN2/QN3 item, from the graph (same rule as the external theses): "contestado" if a
contrary claim challenges it (R05), "com evidência" if evidence is attached (R17), otherwise
"sem evidência no corpus".

Output: docs/relatorios/perguntas-norteadoras/relatorio-QN.md (+ web/assets/respostas.js for the site)

Usage:
  python3 scripts/ontologia/relatorio_qn.py           # regenerate
  python3 scripts/ontologia/relatorio_qn.py --check   # fail if the report differs from the graph
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import rdflib
from rdflib.namespace import DCTERMS, RDF, RDFS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consultas  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MD = ROOT / "docs/relatorios/perguntas-norteadoras/relatorio-QN.md"
JS = ROOT / "web/assets/respostas.js"
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
DIM = {"NationalContextDimension": "contexto nacional", "InstalledCapacityDimension": "capacidade instalada",
       "RiskExposureDimension": "exposição a risco", "StrategicObjectiveDimension": "objetivo estratégico"}
DIF = {"BrazilOnlyDifference": "exclusiva do Brasil", "AbsentInBrazilDifference": "ausente no Brasil",
       "IntensityDifference": "de intensidade", "ContextDifference": "de contexto"}


def label(g, x) -> str:
    return str(g.value(x, RDFS.label) or g.value(x, H.legalCitation) or str(x).split("#")[-1])


def state(g, x) -> str:
    if (x, RDF.type, H.ContestedPolicyClaim) in g:
        return "contestado"
    if (x, RDF.type, H.EvidencedPolicyClaim) in g:
        return "com evidência"
    return "sem evidência no corpus"


def collect(g) -> dict:
    out = {"QN1": [], "QN2": [], "QN3": [], "achados": []}
    for s in sorted(g.subjects(RDF.type, H.NationalSpecificity), key=str):
        comps = []
        for c in g.objects(s, H.specificityComparison):
            comps.append({"jurisdicao": label(g, g.value(c, H.comparisonJurisdiction)),
                          "valor": str(g.value(c, H.comparisonValue) or ""),
                          "naoCodificado": bool(g.value(c, H.comparisonNotCoded).toPython()) if g.value(c, H.comparisonNotCoded) is not None else True,
                          "fonte": label(g, g.value(c, H.comparisonSource)) if g.value(c, H.comparisonSource) is not None else ""})
        out["QN1"].append({"id": str(s).split("#")[-1], "especificidade": label(g, s),
                           "dimensao": DIM.get(str(g.value(s, H.specificityDimension)).split("#")[-1], ""),
                           "tipo": DIF.get(str(g.value(s, H.differenceType)).split("#")[-1], ""),
                           "evidencia": sorted(label(g, e) for e in g.objects(s, H.specificityGroundedIn)),
                           "comparacoes": sorted(comps, key=lambda c: c["jurisdicao"]),
                           "decisao": "pendente" if g.value(s, H.specificityReview) is None else "registrada"})
    for x in sorted(g.subjects(H.answersGuidingQuestion, None), key=str):
        qn = str(g.value(x, H.answersGuidingQuestion))
        if qn not in ("QN2", "QN3", "achado"):
            continue
        cites = sorted(label(g, c) for ev in g.objects(x, H.claimSupportedByEvidence) for c in g.objects(ev, DCTERMS.references))
        item = {"id": str(x).split("#")[-1], "item": label(g, x), "estado": state(g, x),
                "especificidades": sorted(label(g, s) for s in g.objects(x, H.groundedInSpecificity)),
                "escopo": str(g.value(x, H.answerScope) or ""), "cita": cites,
                "decisao": "pendente"}
        out["achados" if qn == "achado" else qn].append(item)
    return out


def render_md(d: dict) -> str:
    L = ["# Resposta inicial às perguntas norteadoras", "",
         "HRAI-GO (Human-centred Regulatory AI, Governance Observatory). Relatório gerado pela plataforma a partir do grafo "
         "(`scripts/ontologia/relatorio_qn.py`), seções na ordem QN1, QN2, QN3 (RT-VIS-03, seção 7.5).", "",
         "> **Resposta inicial.** Nenhum item está publicado: todos aguardam decisão humana registrada (V-29). A detecção desta "
         "primeira execução foi feita pela sessão do loop sobre o grafo, item a item, porque as codificações nos 25 critérios "
         "esperam as escalas aprovadas (D-02). Comparação sem valor equivalente no corpus aparece como \"não codificado\", "
         "nunca como \"não tem\". Método: `docs/especificacoes/ESP-ONT-02/METODO_EXTRACAO.md`; passo M5 do RT-VIS-03.", "",
         "## QN1. Especificidades do Brasil frente às demais jurisdições", ""]
    for i, s in enumerate(d["QN1"], 1):
        L += [f"### {i}. {s['especificidade']}", "",
              f"- **Dimensão da QN1:** {s['dimensao']} · **Tipo de diferença:** {s['tipo']} · **Decisão humana:** {s['decisao']}",
              f"- **Evidência brasileira:** {'; '.join(s['evidencia'])}", "",
              "| Jurisdição | Valor comparado | Fonte |", "|---|---|---|"]
        for c in s["comparacoes"]:
            L.append(f"| {c['jurisdicao']} | {c['valor']} | {c['fonte'] or '—'} |")
        L.append("")
    for qn, title in (("QN2", "QN2. O que está sendo considerado e não deveria (à luz da QN1)"),
                      ("QN3", "QN3. O que não está sendo considerado e deveria (à luz da QN1)")):
        L += [f"## {title}", ""]
        for i, x in enumerate(d[qn], 1):
            L += [f"### {i}. {x['item']}", "",
                  f"- **Estado:** {x['estado']} · **Decisão humana:** {x['decisao']}",
                  f"- **Apoia-se nas especificidades:** {'; '.join(x['especificidades'])}",
                  f"- **Escopo:** {x['escopo']}",
                  f"- **Cita no grafo:** {'; '.join(x['cita'])}", ""]
    if d["achados"]:
        L += ["## Achados sobre o modelo-semente", "", "Encontrados ao responder; corrigem a câmara, não a lei.", ""]
        for x in d["achados"]:
            L += [f"- {x['item']}. *Escopo:* {x['escopo']}.", ""]
    return "\n".join(L).rstrip() + "\n"


def render_js(d: dict) -> str:
    return ("/* Gerado por scripts/ontologia/relatorio_qn.py: resposta inicial às perguntas norteadoras (candidata). */\n"
            "window.HRAIGO_RESPOSTAS = " + json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True) + ";\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    d = collect(consultas.reasoned_graph())
    md, js = render_md(d), render_js(d)
    if args.check:
        ok = MD.exists() and MD.read_text(encoding="utf-8") == md and JS.exists() and JS.read_text(encoding="utf-8") == js
        print("relatório QN:", "atualizado" if ok else "DESATUALIZADO: rode python3 scripts/ontologia/relatorio_qn.py")
        return 0 if ok else 1
    MD.parent.mkdir(parents=True, exist_ok=True)
    MD.write_text(md, encoding="utf-8")
    JS.write_text(js, encoding="utf-8")
    print(f"{MD.relative_to(ROOT)}: QN1 {len(d['QN1'])}, QN2 {len(d['QN2'])}, QN3 {len(d['QN3'])}, achados {len(d['achados'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
