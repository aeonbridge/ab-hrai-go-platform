"""RF-18 / V-26 to V-30: initial answer to QN1, QN2 and QN3 generated from the graph, pending human decision."""

import json
import subprocess
import sys
from pathlib import Path

import rdflib
from rdflib.namespace import RDF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/ontologia"))
import consultas  # noqa: E402

H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
MD = ROOT / "docs/relatorios/perguntas-norteadoras/relatorio-QN.md"


def test_answers_and_report_are_generated_from_the_graph():
    for script in ("responder_qn.py", "relatorio_qn.py"):
        assert subprocess.run([sys.executable, str(ROOT / "scripts/ontologia" / script), "--check"]).returncode == 0


def test_acceptance_queries_return_nothing():
    g = consultas.reasoned_graph()
    for name in ("V27", "V28", "V30"):
        q = next(p for p in consultas.QUERIES.glob(name + "_*.rq") if not p.name.startswith("._"))
        assert list(g.query(q.read_text(encoding="utf-8"))) == [], name
    assert len(set(g.subjects(RDF.type, H.NationalSpecificity))) >= 1   # PC9 answers


def test_report_order_and_initial_mark():
    md = MD.read_text(encoding="utf-8")
    assert md.index("## QN1.") < md.index("## QN2.") < md.index("## QN3.")
    assert "Resposta inicial" in md and "aguardam decisão humana" in md
    assert "não codificado" in md


def test_nothing_is_decided_and_no_fictional_trait_grounds_a_specificity():
    g = consultas.reasoned_graph()
    assert not list(g.subject_objects(H.specificityReview))
    for s in g.subjects(RDF.type, H.NationalSpecificity):
        for e in g.objects(s, H.specificityGroundedIn):
            real = g.value(e, H.seedHasRealSource)
            assert real is None or real.toPython() is True, (s, e)
