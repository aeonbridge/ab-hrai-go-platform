#!/usr/bin/env python3
"""Generate the comparator page from the graph (RT-VIS-03, section 7.2; V-25; PC2, PC3, PC4, PC5, PC9).

web/comparador/index.html shows, for Brazil (PL 2338, Senate text 2024) and the EU (AI Act):
  - the declared limits of the observatory (RT-VIS-03, chapter 9), at the top;
  - the matrix of the 25 criteria plus E1: value and label on the approved scale, the justifying articles
    (linked to their resolvable IRI pages) and the agreement with the paper's authors (PC5, V-09);
  - the provisions side by side, with correspondence type and transposition (PC2);
  - what was incorporated without capacity (PC3) and exposure without coverage (PC4, with its scope);
  - what is specific to Brazil (QN1 specificities, PC9).

Generated from the graph; never edited by hand.

Usage:
  python3 scripts/ontologia/build_comparador.py           # regenerate
  python3 scripts/ontologia/build_comparador.py --check   # fail if the page differs from the graph
"""

from __future__ import annotations

import argparse
import html
import sys
from collections import defaultdict
from pathlib import Path

import rdflib
from rdflib.namespace import DCTERMS, RDF, RDFS, SKOS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consultas  # noqa: E402
import publicar_iris  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web/comparador/index.html"
H = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/regulatory#")
C = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/comparativo#")
SUBJECT = {"Brasil": rdflib.URIRef("https://hrai-go.aeonbridge.io/data/regulatory/br/pl2338#Versao_2024"),
           "UE": rdflib.URIRef("https://hrai-go.aeonbridge.io/data/regulatory/eu/aiact#AIAct_2024")}
LIMITS = [
    ("Não é aconselhamento jurídico.", "Marcar algo como potencialmente afetado não diz se há conformidade ou violação."),
    ("Perspectivas sintéticas não são representativas da população.", "Elas ampliam o que é considerado; não substituem consulta pública."),
    ("Lacunas valem dentro do escopo declarado.", "Uma ausência só vale dentro do escopo da avaliação de cobertura que a produziu."),
    ("Validade das codificações.", "As codificações dependem das escalas aprovadas e da revisão humana; a concordância com os autores do paper é publicada para tornar isso visível."),
]
CSS = """body{margin:0;background:#0B1220;color:#EAF0F7;font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding:28px 20px 60px}a{color:#7CC4FF}h1{font-size:28px;margin:0 0 6px}h2{font-size:21px;margin:34px 0 8px}
.nota{color:#93A3BC;font-size:14px}.limites{border:1px dashed rgba(214,226,240,.35);border-radius:10px;padding:12px 16px;margin:16px 0}
.limites li{margin:4px 0}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;vertical-align:top;padding:7px 8px;border-top:1px solid rgba(214,226,240,.14)}
th{color:#93A3BC;font-weight:600}.ok{color:#9FE3D9}.div{color:#F5C571}.v{font-weight:700}
.card{border-top:1px solid rgba(214,226,240,.14);padding:10px 0}nav a{display:inline-block;margin-right:14px;min-height:44px;line-height:44px}"""


def label(g, x) -> str:
    return str(g.value(x, RDFS.label) or g.value(x, SKOS.prefLabel) or str(x).split("#")[-1])


def link(g, x, text=None) -> str:
    return f"<a href='{html.escape(publicar_iris.href(x))}'>{html.escape(text or label(g, x))}</a>"


def build() -> str:
    g = consultas.reasoned_graph()
    authors = rdflib.URIRef("https://hrai-go.aeonbridge.io/data/comparativo/codificacoes#AutoresAlanoca2025")
    codings = defaultdict(dict)   # criterion -> {(jur, who): coding}
    for c in g.subjects(RDF.type, H.CriterionCoding):
        subj = g.value(c, H.codingSubject)
        jur = next((j for j, s in SUBJECT.items() if s == subj), None)
        if jur:
            who = "autores" if g.value(c, H.codingCoder) == authors else "sessao"
            codings[g.value(c, H.codingCriterion)][(jur, who)] = c
    crits = sorted(codings, key=lambda k: (str(g.value(k, SKOS.notation)).startswith("E"), int(str(g.value(k, SKOS.notation))[1:])))
    rows = []
    for k in crits:
        cells = [f"<td><b>{html.escape(str(g.value(k, SKOS.notation)))}</b> {html.escape(str(g.value(k, SKOS.altLabel) or label(g, k)))}</td>"]
        for jur in ("Brasil", "UE"):
            c, a = codings[k].get((jur, "sessao")), codings[k].get((jur, "autores"))
            if c is None:
                cells.append("<td>—</td>"); continue
            v = int(float(g.value(c, H.codingScaleValue)))
            arts = ", ".join(link(g, d, str(g.value(d, SKOS.notation) or "")) for d in sorted(g.objects(c, H.codingJustifiedBy), key=lambda d: int(str(g.value(d, SKOS.notation) or 0))))
            agree = ""
            if a is not None:
                av = int(float(g.value(a, H.codingScaleValue)))
                agree = f"<br><span class='{'ok' if av == v else 'div'}'>autores: {av}{' (concorda)' if av == v else ' (diverge)'}</span>"
            reviewed = any((cand, H.hasReviewDecision, None) in g for cand in g.subjects(DCTERMS.subject, c))
            cells.append(f"<td><span class='v'>{v}</span> {html.escape(str(g.value(c, H.codingValueLabel)))}<br><span class='nota'>art. {arts}"
                         f" · {'revisada' if reviewed else 'candidata'}</span>{agree}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    corr = []
    for c in sorted(g.subjects(RDF.type, H.ProvisionCorrespondence), key=str):
        src, dst, t = g.value(c, H.correspondenceFrom), g.value(c, H.correspondenceTo), g.value(c, H.correspondenceHasType)
        transposed = (dst, H.provisionTransposedFrom, src) in g
        corr.append(f"<tr><td>{link(g, dst)}</td><td>{link(g, src)}</td><td>{html.escape(label(g, t).replace('Correspondence', ''))}"
                    f"{' · transposição (R26)' if transposed else ''}</td><td class='nota'>{html.escape(str(g.value(c, RDFS.comment) or ''))}</td></tr>")
    q = lambda name: next(p for p in consultas.QUERIES.glob(name + "_*.rq") if not p.name.startswith("._")).read_text(encoding="utf-8")  # noqa: E731
    pc3 = [f"<li>{link(g, r.requisito)}: {html.escape(str(r.situacao))}" + (f" ({link(g, r.indicador)})" if r.indicador else "") + "</li>"
           for r in g.query(q("PC3"))]
    pc4 = list(g.query(q("PC4")))
    specs = []
    for s in sorted(g.subjects(RDF.type, H.NationalSpecificity), key=str):
        comps = "".join(f"<li>{html.escape(label(g, g.value(c, H.comparisonJurisdiction)))}: {html.escape(str(g.value(c, H.comparisonValue)))}</li>"
                        for c in sorted(g.objects(s, H.specificityComparison), key=lambda c: label(g, g.value(c, H.comparisonJurisdiction))))
        specs.append(f"<div class='card'><b>{link(g, s)}</b><br><span class='nota'>{html.escape(label(g, g.value(s, H.specificityDimension)))} · "
                     f"{html.escape(label(g, g.value(s, H.differenceType)))}</span><ul>{comps}</ul></div>")
    return (f"<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Comparador Brasil × UE · HRAI-GO</title><style>{CSS}</style></head><body><main>"
            f"<nav><a href='/'>HRAI-GO</a><a href='/#conhecimento'>Conhecimento</a><a href='/ontology/regulatory/'>Ontologia</a><a href='/ao-vivo/'>Câmara ao vivo</a></nav>"
            f"<h1>Comparador Brasil × União Europeia</h1><p class='nota'>Brasil: PL 2338, texto aprovado pelo Senado (2024). UE: AI Act (2024). "
            f"Gerado do grafo (scripts/ontologia/build_comparador.py); cada valor abre o artigo que o justifica.</p>"
            f"<div class='limites'><b>Limites declarados</b><ul>" + "".join(f"<li><b>{html.escape(a)}</b> {html.escape(b)}</li>" for a, b in LIMITS) + "</ul></div>"
            f"<h2>Critérios da taxonomia (25 + E1)</h2><p class='nota'>Escalas aprovadas (D-02). Ao lado, o valor dos autores do paper convertido para a mesma escala.</p>"
            f"<table><thead><tr><th>Critério</th><th>Brasil</th><th>UE</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
            f"<h2>Dispositivos lado a lado</h2><table><thead><tr><th>Brasil</th><th>AI Act</th><th>Tipo</th><th>Por quê</th></tr></thead><tbody>{''.join(corr)}</tbody></table>"
            f"<h2>Incorporado sem capacidade</h2><ul>{''.join(pc3)}</ul>"
            f"<h2>Exposição sem cobertura</h2><p class='nota'>" + (f"{len(pc4)} exposições" if pc4 else
              "Nenhuma lacuna afirmada: falta declarar o escopo da avaliação de cobertura (premissa P-03); sem escopo, uma ausência não vale.") + "</p>"
            f"<h2>O que é próprio do Brasil</h2>{''.join(specs)}</main></body></html>\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    page = build()
    if args.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == page
        print("comparador:", "atualizado" if ok else "DESATUALIZADO: rode python3 scripts/ontologia/build_comparador.py")
        return 0 if ok else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)} gerado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
