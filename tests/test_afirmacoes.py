"""RF-11: external theses are claims whose state is recalculated from the graph at each corpus version (V-17)."""

import json
import subprocess
import sys
from pathlib import Path

import rdflib
from rdflib.namespace import DCTERMS

ROOT = Path(__file__).resolve().parents[1]
A1 = ROOT / "ontologies/regulatory/afirmacoes/A1_analise_comparativa_BR_AIAct.ttl"
PL = ROOT / "ontologies/regulatory/instances/br/HRAI_GO_Regulatory_BR_PL2338.ttl"
COMMITTED = ROOT / "docs/especificacoes/ESP-ONT-02/afirmacoes.json"


def test_committed_states_match_a_fresh_recalculation(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "scripts/ontologia/afirmacoes.py"), str(A1), str(tmp_path)], check=True,
                   capture_output=True)
    fresh = json.loads((tmp_path / "afirmacoes.json").read_text(encoding="utf-8"))
    assert fresh == json.loads(COMMITTED.read_text(encoding="utf-8"))
    states = {d["id"]: d["status"] for d in fresh}
    assert sorted(states.values()).count("contestada") == 4 and len(states) == 12


def test_c04_reevaluated_against_the_senate_text():
    d = {x["id"]: x for x in json.loads(COMMITTED.read_text(encoding="utf-8"))}
    c04 = d["C04"]
    assert c04["status"] == "contestada"
    assert any("art. 54" in e for k in c04["contestada_por"] for e in k["evidencias"])
    assert "Reavaliada em 17/11/2026" in c04["nota"]


def test_evidence_points_to_existing_articles():
    a1, pl = rdflib.Graph().parse(A1), rdflib.Graph().parse(PL)
    targets = [o for o in a1.objects(None, DCTERMS.references) if "/pl2338#" in str(o)]
    assert targets and all((t, None, None) in pl for t in targets)
