"""Human decisions: transcribed from decisoes.json, attributed to the author, never to an agent (invariant I-3)."""

import json
import subprocess
import sys
from pathlib import Path

import rdflib
from rdflib.namespace import RDF

ROOT = Path(__file__).resolve().parents[1]
H = rdflib.Namespace("https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#")
OUT = ROOT / "ontologies/regulatory/decisoes/decisoes_autor.ttl"
LOG = json.loads((ROOT / "docs/especificacoes/ESP-ONT-02/decisoes.json").read_text(encoding="utf-8"))


def test_decisions_match_the_log_and_quote_the_message():
    assert subprocess.run([sys.executable, str(ROOT / "scripts/ontologia/registrar_decisoes.py"), "--check"]).returncode == 0
    g = rdflib.Graph().parse(OUT)
    decisions = list(g.subjects(RDF.type, H.ApprovalDecision))
    assert len(decisions) == len(LOG["decisoes"])
    for d in decisions:
        actor = g.value(d, H.reviewDecisionBy)
        assert (actor, RDF.type, H.ReviewActor) in g and (actor, RDF.type, H.MonitoringAgent) not in g
        assert "Mensagem do autor" in str(g.value(d, H.approvedReason))


def test_only_logged_batches_are_reviewed():
    g = rdflib.Graph().parse(OUT)
    reviewed = {str(c) for c in g.subjects(H.hasReviewDecision, None)}
    assert not any("/sementes#" in c or "/respostas#" in c or "/cn/china#" in c for c in reviewed)  # D-07, D-11, D-12 pending
