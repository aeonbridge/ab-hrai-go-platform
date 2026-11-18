"""RF-10: a live session becomes human positions on claims, a report with the four metrics and a human decision record."""

import json
import sys
from pathlib import Path

import rdflib
from rdflib.namespace import RDF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/ontologia"))
import sessao  # noqa: E402

H, S = sessao.H, sessao.S
ROWS = json.loads((ROOT / "docs/sessoes/ensaio-simulado/respostas.json").read_text(encoding="utf-8"))


def test_reactions_become_positions_on_claims_and_people_stay_anonymous():
    g, m = sessao.build("ensaio-simulado", ROWS, None)
    claims = set(g.subjects(RDF.type, H.PolicyClaim))
    assert len(claims) == 6
    positions = list(g.subjects(H.positionSupportsClaim, None)) + list(g.subjects(H.positionChallengesClaim, None))
    assert positions and all(g.value(p, H.positionExpressedBy) is not None for p in positions)
    labels = [str(g.value(p, rdflib.RDFS.label)) for p in g.subjects(RDF.type, H.Stakeholder)]
    assert all("·" in lab for lab in labels)                      # nickname, never a name (P-12)
    assert not set(g.subjects(RDF.type, H.SyntheticStakeholderPosition))   # human positions only (I-4)


def test_four_metrics_and_round_revision():
    _, m = sessao.build("ensaio-simulado", ROWS, None)
    met = m["metricas"]
    assert met["amplitude"] >= 6 and 0 <= met["ancoragem"] <= 1
    assert met["revisaoDePosicao"]["comPosicaoNasDuasRodadas"] == 14 and 0 < met["revisaoDePosicao"]["revisaram"] < 14
    assert met["divergenciaPreservada"] >= 1


def test_decision_record_only_from_a_human_file():
    g, _ = sessao.build("ensaio-simulado", ROWS, None)
    assert not set(g.subjects(RDF.type, S.DecisionRecord))
    decision = {"registradoPor": "Coordenação do ensaio", "data": "2026-11-18", "texto": "Escalonar a auditoria por risco e porte.",
                "afirmacoesCitadas": [], "divergenciasPreservadas": []}
    g, _ = sessao.build("ensaio-simulado", ROWS, decision)
    assert len(set(g.subjects(RDF.type, S.DecisionRecord))) == 1
