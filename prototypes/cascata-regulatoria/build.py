"""Gera index.html embutindo a TBox e as regras SWRL de ontologies/regulatory.
Uso: python3 prototypes/cascata-regulatoria/build.py (a partir da raiz do repositório)."""
import json, re
from pathlib import Path
root = Path(__file__).resolve().parents[2]
ttl = (root / "ontologies/regulatory/HRAI_GO_Regulatory_General.ttl").read_text()
swrl = (root / "ontologies/regulatory/HRAI_GO_Regulatory_General.swrl").read_text()
props = {}
for m in re.finditer(r'^hrai:(\w+) rdf:type owl:(ObjectProperty|DatatypeProperty) \.', ttl, re.M):
    props[m.group(1)] = {"k": "o" if m.group(2) == "ObjectProperty" else "d"}
for m in re.finditer(r'^hrai:(\w+) rdfs:(domain|range) (\S+) \.', ttl, re.M):
    if m.group(1) in props:
        props[m.group(1)][m.group(2)[0]] = m.group(3).replace("hrai:", "")
onto = {"C": re.findall(r'^hrai:(\w+) rdf:type owl:Class \.', ttl, re.M), "P": props,
        "SUB": dict(re.findall(r'^hrai:(\w+) rdfs:subClassOf hrai:(\w+) \.', ttl, re.M))}
here = Path(__file__).parent
tpl = (here / "cascata.tpl.html").read_text()
out = tpl.replace("__ONTO__", json.dumps(onto, separators=(",", ":"), ensure_ascii=False)).replace("__SWRL__", json.dumps(swrl, ensure_ascii=False))
(here / "index.html").write_text(out)
print("index.html:", len(out), "bytes;", len(onto["C"]), "classes;", len(props), "propriedades")
