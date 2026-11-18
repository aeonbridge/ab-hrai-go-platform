"""RF-13: seed tensions, strata, seats, empty seats and scenario branches in SCSE, linked to the core."""

import glob
import json
import re
from pathlib import Path

import rdflib
from rdflib.namespace import RDF, SKOS

ROOT = Path(__file__).resolve().parents[1]
CONSELHO = ROOT / "ontologies/scse/conselho/GOV-BR-001.ttl"
S = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/scse#")
H = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/regulatory#")
MODELO = json.loads(re.search(r"window\.HRAIGO_MODELO\s*=\s*(\{.*\})\s*;?\s*$",
                              (ROOT / "web/assets/modelo.js").read_text(encoding="utf-8"), re.S).group(1))


def graph():
    g = rdflib.Graph()
    for f in [CONSELHO, ROOT / "ontologies/scse/SCSE_Shadow_Council_Ontology.ttl",
              ROOT / "ontologies/regulatory/HRAI_GO_Regulatory_General.ttl"] + \
             glob.glob(str(ROOT / "ontologies/regulatory/afirmacoes/*.ttl")) + \
             glob.glob(str(ROOT / "ontologies/regulatory/instances/**/*.ttl"), recursive=True):
        g.parse(f)
    return g


def test_v16_no_seed_without_claim():
    g = graph()
    rows = list(g.query((ROOT / "ontologies/consultas/V16_sementes_sem_ligacao.rq").read_text(encoding="utf-8")))
    assert rows == []
    assert len(set(g.subjects(RDF.type, S.PolicyTension))) == len(MODELO["seeds"]) == 6


def test_council_matches_what_the_chamber_shows():
    g = graph()
    gov = "https://hrai-go.aeonbridge.io/data/scse/gov-br-001#"
    by = lambda cls: {str(g.value(x, SKOS.notation) or g.value(x, rdflib.RDFS.label))  # noqa: E731
                      for x in g.subjects(RDF.type, cls) if str(x).startswith(gov)}
    assert by(S.StakeholderStratum) == {s["id"] for s in MODELO["strata"]}
    assert by(S.ScenarioBranch) == {b["id"] for b in MODELO["branches"]}
    assert by(S.CoverageGap) == set(MODELO["unrep"])
    seats = [x for x in g.subjects(RDF.type, S.CouncilSeat) if str(x).startswith(gov)]
    assert len(seats) == sum(s["seats"] for s in MODELO["strata"])
    assert all(g.value(seat, S.hasStratum) is not None for seat in seats)


def test_branches_point_to_existing_instruments_and_layer_is_separate():
    g = graph()
    for b in g.subjects(RDF.type, S.ScenarioBranch):
        target = g.value(b, S.branchConcernsInstrument)
        assert target is not None and (target, RDF.type, None) in g, b
    assert "regulatory/instances" not in str(CONSELHO)
