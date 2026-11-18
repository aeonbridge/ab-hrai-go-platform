#!/usr/bin/env python3
"""Make every HRAI-GO IRI resolvable in the browser (RNF-01, V-24; decisions D-05 and D-05a).

IRIs live under https://hrai-go.aeonbridge.io/ (GitHub Pages of this repository, custom domain). An IRI such as
https://hrai-go.aeonbridge.io/ontology/regulatory#LegalProvision is requested by the browser as
/ontology/regulatory/, so this script writes one HTML page per namespace (web/<path>/index.html) with one anchored
section per term or individual: label, types, description, asserted properties (links resolve too) and the
triples inferred by the reasoner, each with the rule that inferred it ("por quê?").

Generated from the graph; never edited by hand.

Usage:
  python3 scripts/ontologia/publicar_iris.py           # regenerate web/ontology/** and web/data/**
  python3 scripts/ontologia/publicar_iris.py --check   # fail if any page differs from the graph
"""

from __future__ import annotations

import argparse
import html
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import rdflib
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consultas  # noqa: E402
import raciocinar  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
BASE = "https://hrai-go.aeonbridge.io/"
ROOTS = ("ontology", "data")
DESCRIPTIVE = (RDFS.comment, SKOS.definition, DCTERMS.description)
PREFIXES = {"https://hrai-go.aeonbridge.io/ontology/regulatory#": "hrai:", "https://hrai-go.aeonbridge.io/ontology/scse#": "scse:",
            "https://hrai-go.aeonbridge.io/ontology/comparativo#": "comp:", str(RDF): "rdf:", str(RDFS): "rdfs:", str(OWL): "owl:",
            str(SKOS): "skos:", str(DCTERMS): "dcterms:", "http://www.w3.org/ns/prov#": "prov:", "http://www.w3.org/2003/11/swrl#": "swrl:"}
CSS = """body{margin:0;background:#0B1220;color:#EAF0F7;font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:980px;margin:0 auto;padding:28px 20px 60px}a{color:#7CC4FF}h1{font-size:26px;margin:0 0 6px}
header p,.nota{color:#93A3BC;font-size:14px}section{border-top:1px solid rgba(214,226,240,.15);padding:16px 0}
section:target{background:rgba(232,163,61,.08);outline:1px solid rgba(232,163,61,.45);padding-left:10px}
h2{font-size:18px;margin:0 0 4px}code{font-size:13px;color:#C9D3E0;overflow-wrap:anywhere}
dl{display:grid;grid-template-columns:minmax(150px,auto) 1fr;gap:4px 14px;margin:8px 0 0;font-size:14px}
dt{color:#93A3BC}dd{margin:0;overflow-wrap:anywhere}.inf{color:#F5C571}.desc{white-space:pre-wrap;margin:6px 0 0}"""


def short(u) -> str:
    s = str(u)
    for base, p in sorted(PREFIXES.items(), key=lambda kv: -len(kv[0])):
        if s.startswith(base):
            return p + s[len(base):]
    return s


def href(u) -> str:
    s = str(u)
    if s.startswith(BASE):
        ns, _, frag = s.partition("#")
        return "/" + ns[len(BASE):].strip("/") + "/" + ("#" + frag if frag else "")
    return s


def value(o) -> str:
    if isinstance(o, Literal):
        text = str(o)
        return html.escape(text if len(text) <= 900 else text[:900] + "…")
    if isinstance(o, BNode):
        return "<span class='nota'>(nó anônimo)</span>"
    return f"<a href='{html.escape(href(o))}'>{html.escape(short(o))}</a>"


def page_path(ns: str) -> Path:
    return WEB / ns[len(BASE):].strip("/") / "index.html"


def build() -> dict[Path, str]:
    rz = raciocinar.Raciocinador(*consultas.files())
    rz.executar()
    g, asserted = rz.g, rz.declaradas
    by_ns: dict[str, list] = defaultdict(list)
    for s in set(g.subjects()):
        if isinstance(s, URIRef) and str(s).startswith(BASE) and str(s)[len(BASE):].split("/")[0] in ROOTS:
            ns = str(s).split("#")[0] if "#" in str(s) else str(s)
            by_ns[ns].append(s)
    pages = {}
    for ns, subjects in sorted(by_ns.items()):
        body = []
        onto = URIRef(ns)
        title = str(g.value(onto, DCTERMS.title) or g.value(onto, RDFS.label) or ns[len(BASE):])
        for s in sorted(subjects, key=lambda x: str(x)):
            if s == onto:
                continue
            frag = str(s).split("#", 1)[1] if "#" in str(s) else ""
            label = g.value(s, RDFS.label) or g.value(s, SKOS.prefLabel) or frag
            types = sorted({o for o in g.objects(s, RDF.type) if isinstance(o, URIRef)}, key=str)
            rows = []
            for p, o in sorted(g.predicate_objects(s), key=lambda po: (str(po[0]), str(po[1]))):
                if p in (RDF.type, RDFS.label, SKOS.prefLabel) + DESCRIPTIVE:
                    continue
                if isinstance(o, BNode):
                    continue
                if (s, p, o) in asserted:
                    rows.append(f"<dt>{html.escape(short(p))}</dt><dd>{value(o)}</dd>")
                else:
                    rule = rz.justificativa.get((s, p, o), {}).get("regra", "fechamento OWL/RDFS")
                    rows.append(f"<dt class='inf'>{html.escape(short(p))}</dt><dd>{value(o)} <span class='inf'>inferido por {html.escape(str(rule).split('#')[-1])}</span></dd>")
            desc = "".join(f"<p class='desc'>{value(d)}</p>" for p in DESCRIPTIVE for d in g.objects(s, p))
            def type_note(t):
                if (s, RDF.type, t) in asserted:
                    return ""
                rule = rz.justificativa.get((s, RDF.type, t), {}).get("regra", "fechamento OWL/RDFS")
                return f" <span class='inf'>inferido por {html.escape(str(rule).split('#')[-1])}</span>"
            type_html = ", ".join(value(t) + type_note(t) for t in types)
            body.append(f"<section id='{html.escape(frag)}'><h2>{html.escape(str(label))}</h2><code>{html.escape(str(s))}</code>"
                        f"<dl><dt>tipo</dt><dd>{type_html or '—'}</dd>{''.join(rows)}</dl>{desc}</section>")
        meta = "".join(f"<p>{value(d)}</p>" for p in (DCTERMS.description, RDFS.comment) for d in g.objects(onto, p))
        doc = (f"<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
               f"<title>{html.escape(title)} · HRAI-GO</title><style>{CSS}</style></head><body><main><header>"
               f"<p><a href='/'>HRAI-GO: Human-centred Regulatory AI, Governance Observatory</a></p><h1>{html.escape(title)}</h1>"
               f"<p><code>{html.escape(ns)}</code></p>{meta}<p class='nota'>Página gerada do grafo (scripts/ontologia/publicar_iris.py). "
               f"Em amarelo, o que o raciocinador inferiu, com a regra. {len(subjects)} termos e indivíduos.</p></header>"
               + "".join(body) + "</main></body></html>\n")
        pages[page_path(ns)] = doc
    return pages


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    pages = build()
    existing = {p for r in ROOTS for p in (WEB / r).rglob("index.html") if not p.name.startswith("._")} if any((WEB / r).exists() for r in ROOTS) else set()
    if args.check:
        bad = [str(p.relative_to(ROOT)) for p, text in pages.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        bad += [str(p.relative_to(ROOT)) + " (sobra)" for p in existing - set(pages)]
        print("páginas de IRI:", "atualizadas" if not bad else "DESATUALIZADAS: " + ", ".join(bad[:5]))
        return 1 if bad else 0
    for r in ROOTS:
        shutil.rmtree(WEB / r, ignore_errors=True)
    for p, text in pages.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(f"{len(pages)} páginas de IRI em web/ontology e web/data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
