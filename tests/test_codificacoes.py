"""V-08 / V-09: Brazil and the EU coded on the 25 criteria with the approved scales; agreement with the paper's authors."""

import json
import subprocess
import sys
from pathlib import Path

import rdflib
from rdflib.namespace import DCTERMS, RDF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/ontologia"))
import consultas  # noqa: E402

H = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/regulatory#")
C = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/comparativo#")
OUT = ROOT / "ontologies/comparativo/codificacoes/BR_UE_codificacoes.ttl"


def test_generated_and_every_value_is_on_the_approved_scale():
    assert subprocess.run([sys.executable, str(ROOT / "scripts/ontologia/codificar.py"), "--check"]).returncode == 0
    scales = json.loads((ROOT / "ontologies/comparativo/escalas-E4.json").read_text(encoding="utf-8"))["escalas"]
    g = rdflib.Graph().parse(OUT)
    ours = [c for c in g.subjects(RDF.type, H.CriterionCoding) if (c, DCTERMS.source, None) not in g]
    assert len(ours) == 52   # 26 per jurisdiction: 25 criteria + E1
    for c in ours:
        crit = str(g.value(c, H.codingCriterion)).split("#")[-1]
        assert 0 <= int(float(g.value(c, H.codingScaleValue))) < len(scales[crit]), c


def test_v08_no_coding_without_a_justifying_provision():
    g = consultas.reasoned_graph()
    q = next(p for p in consultas.QUERIES.glob("V08_*.rq") if not p.name.startswith("._"))
    assert list(g.query(q.read_text(encoding="utf-8"))) == []
    assert len(list(g.query(next(consultas.QUERIES.glob("PC5_*.rq")).read_text(encoding="utf-8")))) >= 52


def test_v09_agreement_is_published_per_criterion():
    md = (ROOT / "docs/especificacoes/ESP-ONT-02/concordancia-codificacoes.md").read_text(encoding="utf-8")
    assert "## BR:" in md and "## UE:" in md
    assert md.count("| C") >= 50
    assert "divergência resolvida contra o texto primário" in md
