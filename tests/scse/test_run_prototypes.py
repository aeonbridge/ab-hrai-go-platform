"""Checks for the run-backed prototype pages built by scripts/build_run_prototypes.py."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LATEST = ROOT / "runs/GOV-BR-001/latest.json"

pytestmark = pytest.mark.skipif(not LATEST.exists(), reason="no real run recorded for GOV-BR-001")


def _builder():
    spec = importlib.util.spec_from_file_location("build_run_prototypes", ROOT / "scripts/build_run_prototypes.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tour_uses_real_run_data_and_drops_example_markers():
    builder = _builder()
    run = builder.load_run("GOV-BR-001")
    html = builder.build_tour(run)

    assert run["index"]["runId"] in html
    assert "Preencher exemplo" not in html
    assert "propostas de exemplo" not in html
    assert "arcos de exemplo" not in html
    assert "claude.ai/artifact" not in html
    for proposal in run["packet"]["proposals"]:
        assert f'"id":"{proposal["proposalId"]}"' in html
    # Seats and providers come from the roster, not from the illustrative 20-seat council.
    for seat in run["roster"]["seats"]:
        assert seat["model"] in html


def test_tour_arcs_reflect_claim_graph():
    builder = _builder()
    run = builder.load_run("GOV-BR-001")
    stratum_ids = [s["stratumId"] for s in run["packet"]["strata"]]
    facts = builder.tour_run_object(run, stratum_ids)

    challenges = sum(1 for c in run["claims"] if c["kind"] == "challenge")
    amendments = sum(1 for c in run["claims"] if c["kind"] == "amendment")
    assert facts["arcCounts"].get(2, 0) == amendments
    assert 0 < facts["arcCounts"].get(0, 0) <= challenges
    assert facts["httpPairs"] > 0


def test_mural_feed_embeds_run_without_fetching():
    builder = _builder()
    run = builder.load_run("GOV-BR-001")
    html = builder.build_mural(run)

    assert "/*__RUN__*/" not in html
    assert "latest.json\", {cache" not in html and "loadLatestRun" not in html  # run data is embedded, not fetched
    assert "/api/health" in html  # live layer turns on only under `scse mural serve`
    start = html.index("const RUN = ") + len("const RUN = ")
    end = html.index(";\n", start)
    payload = json.loads(html[start:end].replace("<\\/", "</"))
    assert payload["index"]["runId"] == run["index"]["runId"]
    assert len(payload["packet"]["proposals"]) == len(run["packet"]["proposals"])
    assert {s["stratumId"] for s in payload["seats"]} == {s["stratumId"] for s in run["packet"]["strata"]}
    # Every stratum statement survives the slimming.
    original = sum(len(r["statements"]) for p in run["packet"]["proposals"] for r in p["stratumPositions"])
    kept = sum(len(r["statements"]) for p in payload["packet"]["proposals"] for r in p["stratumPositions"])
    assert kept == original
