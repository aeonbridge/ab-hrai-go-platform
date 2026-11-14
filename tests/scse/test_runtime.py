import json
from pathlib import Path

import pytest

from scse.config import ModelConfig
from scse.council import compose
from scse.deliberation import DeliberationEngine, extract_json, round_plan
from scse.experiment import load_experiment, plan, run_experiment
from scse.report import compile_run
from scse.runner import RunOptions, preflight, run_scenario
from scse.world import ScenarioError, load_scenario, prepare, validate

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = sorted((ROOT / "scenarios/brasil-ficticio").glob("BR-PBIA-*.json"))


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda p: p.stem)
def test_scenarios_valid(path):
    assert validate(load_scenario(path), "scenario") == []


def test_invalid_scenario_reports_fields():
    sc = load_scenario(SCENARIOS[0])
    sc["mode"] = "solutionCompliance"  # requires solution
    with pytest.raises(ScenarioError, match="solution"):
        prepare(sc)


def test_round_plan():
    assert round_plan(6) == ["R1", "R2", "R3", "R4", "R5", "R6"]
    assert round_plan(3) == ["R1", "R2", "R3"]
    assert round_plan(8) == ["R1", "R2", "R3", "R4", "R3", "R4", "R5", "R6"]


def test_extract_json_tolerates_fences():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('texto {"a": 2} fim') == {"a": 2}


def _engine(seats=8, **kw):
    cfg = ModelConfig.load()
    snap = prepare(load_scenario(SCENARIOS[0]), scenario_path=SCENARIOS[0], seats_override=seats)
    roster = compose(snap, cfg, seed=7)
    return DeliberationEngine(snap, roster, cfg, run_id="t", seed=7, dry_run=True, **kw)


def test_dry_run_full_protocol(tmp_path):
    eng = _engine(critic=True, synthesize=True)
    eng.run()
    rounds = [e["roundId"] for e in eng.ledger.events if e["type"] == "round.started"]
    assert rounds == ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    assert eng.ledger.verify()
    # R1 drafts stay private
    assert all(c.visibility == "private" for c in eng.claims.values() if c.roundId == "R1")
    # council output never carries legal-fact classifications
    assert {c.classification for c in eng.claims.values()} <= {"syntheticPerspective", "hypothesis", "unknown"}
    # unknown citations are stripped and downgraded
    bad = [c for c in eng.claims.values() if c.invalidSourceIds]
    assert all(c.insufficientGrounding and c.classification != "syntheticPerspective" for c in bad)
    out = compile_run(eng, tmp_path)
    assert validate(out["report"], "report") == []
    for name in ("run-manifest.json", "world-snapshot.jsonld", "council-roster.json", "deliberation-events.jsonl",
                 "compliance-matrix.json", "tensions.json", "minority-report.md", "provider-scorecard.json"):
        assert (tmp_path / name).exists(), name
    assert set(out["scorecard"]) == {"anthropic", "openai", "xai", "gemini"}


def test_determinism_same_seed():
    a, b = _engine(), _engine()
    a.run(); b.run()
    assert [(c.id, c.text) for c in a.claims.values()] == [(c.id, c.text) for c in b.claims.values()]


def test_ledger_tamper_detected():
    eng = _engine(seats=8)
    eng.run()
    eng.ledger.events[3]["payload"]["text"] = "adulterado"
    assert not eng.ledger.verify()


def test_rule_enforcement_rejects_bad_actions():
    eng = _engine(seats=8)
    seat = eng.roster.seats[0]
    payload = {"actions": [
        {"action": "withdraw", "targetClaimId": "C9999-R2", "branchId": None, "text": "x", "sourceIds": [],
         "classification": "unknown", "confidence": "low"},
        {"action": "challenge", "targetClaimId": None, "branchId": None, "text": "x", "sourceIds": [],
         "classification": "unknown", "confidence": "low"}],
        "insufficientGrounding": False, "notes": ""}
    accepted, rejected = eng._apply(seat, "R2", payload)
    assert accepted == [] and rejected == 2


def test_budget_stop():
    eng = _engine(seats=8)
    eng.token_budget = 1000
    eng.run()
    assert eng.stopped_reason and "tokenBudget" in eng.stopped_reason


def test_solution_mode_findings(tmp_path):
    path = ROOT / "scenarios/brasil-ficticio/BR-PBIA-005.json"
    res = run_scenario(path, ModelConfig.load(), RunOptions(dry_run=True, seats=8, replicates=2), out_root=tmp_path)
    rep = json.loads(next(Path(res["outDir"]).glob("rep-01/report.json")).read_text())
    status = {f["legalSourceIds"][0]: f["status"] for f in rep["findings"]}
    assert status == {"LGPD": "insufficientEvidence", "PL2338": "proposalOnly"}
    assert res["sensitivity"]["replicates"] == 2


def test_preflight_requires_keys(monkeypatch):
    for env in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(env, raising=False)
    problems = preflight(ModelConfig.load(), ["anthropic", "openai", "xai", "gemini"], dry_run=False)
    assert len(problems) == 4
    assert preflight(ModelConfig.load(), ["anthropic"], dry_run=True) == []


def test_experiment_plan_and_dry_run(tmp_path):
    exp_path = ROOT / "experiments/scse/provider-practice.toml"
    exp = load_experiment(exp_path)
    ids = {a["id"] for a in exp["arms"]}
    for p in ("anthropic", "openai", "xai", "gemini"):
        assert f"solo-{p}" in ids and f"B1-single-agent-{p}" in ids
    assert plan(exp)["maxModelCalls"] > 0
    small = tmp_path / "small.toml"
    small.write_text(exp_path.read_text(encoding="utf-8").replace("replicates = 3", "replicates = 1")
                     , encoding="utf-8")
    text = small.read_text(encoding="utf-8")
    first = text.index("scenarios = [")
    end = text.index("]", first)
    small.write_text(text[:first] + 'scenarios = ["scenarios/brasil-ficticio/BR-PBIA-004.json"]' + text[end + 1:],
                     encoding="utf-8")
    import os
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        summary = run_experiment(small, dry_run=True, out_root=tmp_path / "out")
    finally:
        os.chdir(cwd)
    assert "mixed-rotate" in summary["arms"]
    assert (Path(summary["outDir"]) / "experiment-summary.md").exists()
