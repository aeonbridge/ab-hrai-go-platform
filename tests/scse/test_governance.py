import copy
import json
from pathlib import Path

import pytest

from scse import governance as gv
from scse.cli import main as cli_main
from scse.config import ModelConfig
from scse.council import compose
from scse.governance_engine import GovernanceEngine
from scse.report import compile_run
from scse.runner import RunOptions, run_scenario
from scse.world import ScenarioError, load_scenario, prepare, validate

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "scenarios/governanca-brasil/GOV-BR-001.json"
MODEL = ROOT / "scenarios/governanca-brasil/model/brasil-governanca-v0.json"
TAXO = ROOT / "scenarios/governanca-brasil/taxonomy.json"


def _engine(seats=8, scenario=None, **kw):
    cfg = ModelConfig.load()
    sc = scenario or GOV
    snap = prepare(load_scenario(sc), scenario_path=sc, seats_override=seats)
    roster = compose(snap, cfg, seed=3)
    return GovernanceEngine(snap, roster, cfg, run_id="g", seed=3, dry_run=True, **kw)


# ------------------------------------------------------------------ data integrity
def test_scenario_and_model_are_valid():
    assert validate(load_scenario(GOV), "scenario") == []
    taxonomy = gv.load_taxonomy(TAXO)
    assert gv.validate_model(json.loads(MODEL.read_text()), taxonomy) == []


def test_every_cited_source_resolves():
    snap = prepare(load_scenario(GOV), scenario_path=GOV)
    known = snap.evidence_ids
    b = snap.governance
    for c in b.model["components"]:
        assert set(c["sourceIds"]) <= known, c["id"]
    for f in b.context["features"] + b.context["facts"]:
        assert set(f["sourceIds"]) <= known, f["id"]
    for e in b.context["evidence"]:
        assert snap.evidence(e["id"])["excerpt"]


def test_unverified_claims_are_flagged_not_hidden():
    model = json.loads(MODEL.read_text())
    assert all(c["verification"] == "pending" for c in model["components"])
    inferred = [c["id"] for c in model["components"] if c.get("topicsBasis") == "inferred"]
    assert {"GM-10", "GM-11", "GM-12"} <= set(inferred)  # not confirmed in the sources consulted


def test_context_and_model_must_not_postdate_the_round():
    sc = load_scenario(GOV)
    sc["asOfDate"] = "2026-01-01"
    with pytest.raises(ScenarioError, match="after the round date|no context snapshot"):
        prepare(sc, scenario_path=GOV)


def test_governance_block_required_and_exclusive():
    sc = load_scenario(GOV)
    del sc["governance"]
    assert any("governance" in e for e in validate(sc, "scenario"))
    other = load_scenario(ROOT / "scenarios/brasil-ficticio/BR-PBIA-001.json")
    other["governance"] = load_scenario(GOV)["governance"]
    assert validate(other, "scenario")


# ---------------------------------------------------------------- blind-first design
def test_r1_is_blind_and_r2_reveals_the_model():
    eng = _engine()
    seat = eng.roster.seats[0]
    r1, r2 = eng._system_prompt(seat, "R1"), eng._system_prompt(seat, "R2")
    assert "NÃO tem acesso ao modelo" in r1 and "Componentes:" not in r1 and "GM-05" not in r1
    assert "Componentes:" in r2 and "GM-05" in r2
    assert "PL 2338" in r1  # the context itself is visible; only the model is hidden


def test_prompt_defines_the_three_lenses():
    eng = _engine()
    text = eng._system_prompt(eng.roster.seats[0], "R2")
    for needle in ("omission (Q1)", "excess (Q2)", "advantage (Q3)", "DISTINTIVA", "NÃO conta"):
        assert needle in text


# --------------------------------------------------------------------- lens rules
def _action(**kw):
    base = {"action": "assertClaim", "targetClaimId": None, "branchId": None, "text": "x" * 30, "sourceIds": ["PL2338"],
            "classification": "syntheticPerspective", "confidence": "medium", "lens": "none", "topic": "none",
            "componentId": None, "change": "none", "title": None, "contextFeatureIds": [], "tensionIds": []}
    base.update(kw)
    return base


@pytest.mark.parametrize("round_id,kw,why", [
    ("R1", dict(lens="omission", topic="participation", change="add"), "expectation"),
    ("R1", dict(lens="expectation", topic="none"), "topic"),
    ("R1", dict(lens="expectation", topic="participation", componentId="GM-01"), "blind"),
    ("R2", dict(lens="excess", change="remove"), "componentId"),
    ("R2", dict(lens="excess", componentId="GM-01", change="add"), "remove or modify"),
    ("R2", dict(lens="advantage", change="add", topic="language-culture"), "contextFeatureIds"),
    ("R2", dict(lens="advantage", change="keep", contextFeatureIds=["CF-03"]), "componentId"),
    ("R2", dict(lens="omission", change="remove", topic="participation"), "change=add"),
    ("R2", dict(lens="expectation", topic="participation"), "not enabled"),
    ("R2", dict(lens="omission", change="add", topic="not-a-topic"), "unknown topic"),
    ("R2", dict(lens="advantage", change="add", topic="language-culture", contextFeatureIds=["CF-99"]), "unknown contextFeatureIds"),
    ("R2", dict(lens="excess", componentId="GM-99", change="remove"), "unknown componentId"),
    ("R2", dict(lens="omission", change="add", topic="participation", tensionIds=["T9"]), "unknown tensionIds"),
])
def test_invalid_actions_are_rejected(round_id, kw, why):
    eng = _engine()
    seat = eng.roster.seats[0]
    accepted, rejected = eng._apply(seat, round_id, {"actions": [_action(**kw)], "insufficientGrounding": False, "notes": ""})
    assert (accepted, rejected) == ([], 1)
    ev = [e for e in eng.ledger.events if e["type"] == "action.rejected"][-1]
    assert why in ev["payload"]["reason"]


def test_valid_findings_are_accepted_and_structured():
    eng = _engine()
    seat = eng.roster.seats[0]
    ok = [
        ("R1", _action(lens="expectation", topic="participation", tensionIds=["T4"])),
        ("R2", _action(lens="omission", change="add", topic="participation", title="Participação social")),
        ("R2", _action(lens="excess", componentId="GM-12", change="remove")),
        ("R2", _action(lens="advantage", change="add", topic="language-culture", contextFeatureIds=["CF-03"])),
    ]
    for rnd, a in ok:
        accepted, rejected = eng._apply(seat, rnd, {"actions": [a], "insufficientGrounding": False, "notes": ""})
        assert (accepted, rejected) == (["assertClaim"], 0), (rnd, a)
    lenses = [c.lens for c in eng.claims.values()]
    assert lenses == ["expectation", "omission", "excess", "advantage"]
    adv = list(eng.claims.values())[-1]
    assert adv.contextFeatureIds == ["CF-03"] and adv.classification == "syntheticPerspective"
    assert eng.claims["C0001-R1"].visibility == "private"


def test_amendment_inherits_the_lens_of_its_finding():
    eng = _engine()
    seat, other = eng.roster.seats[0], eng.roster.seats[1]
    eng._apply(seat, "R2", {"actions": [_action(lens="omission", change="add", topic="participation")],
                            "insufficientGrounding": False, "notes": ""})
    fid = next(iter(eng.claims))
    eng._apply(other, "R5", {"actions": [_action(action="proposeAmendment", targetClaimId=fid, change="add",
                                                 topic="participation", title="Conselho de participação")],
                             "insufficientGrounding": False, "notes": ""})
    amend = [c for c in eng.claims.values() if c.kind == "amendment"][0]
    assert amend.lens == "omission" and amend.title == "Conselho de participação"
    assert eng.claims[fid].amendedBy == [amend.id]


# ---------------------------------------------------------- end to end (dry run)
def test_dry_run_produces_report_packet_and_matrix(tmp_path):
    eng = _engine(critic=True)
    eng.run()
    assert eng.ledger.verify()
    names = [e["payload"].get("name") for e in eng.ledger.events if e["type"] == "round.started"]
    assert names == ["BlindExpectations", "ModelReview", "CrossExamination", "EvidenceRevision",
                     "ChangeProposals", "ContextStress", "MinorityAndAudit"]
    assert any(e["type"] == "expectations.aggregated" for e in eng.ledger.events)
    out = compile_run(eng, tmp_path)
    assert validate(out["report"], "report") == []
    gr = out["report"]["governanceReview"]
    assert gr["status"] == "pendingHumanReview" and gr["packetFile"] == "revision-packet.json"
    for f in ("revision-packet.json", "coverage-matrix.json", "review-sheet.md"):
        assert (tmp_path / f).exists(), f
    packet = out["packet"]
    assert packet["councilNature"] == "synthetic" and packet["status"] == "pendingHumanReview"
    assert all(p["decision"] is None for p in packet["proposals"])  # the council never decides
    gaps = [r for r in packet["coverageMatrix"] if r["gap"]]
    assert gaps and all(r["coverageStrength"] == "none" and r["expectedBySeats"] > 0 for r in gaps)
    for p in packet["proposals"]:
        if p["lens"] == "excess":
            assert p["componentId"] and p["change"] in ("remove", "modify") and p["componentTitle"]
        if p["lens"] == "advantage":
            assert p["contextFeatureIds"]
    assert any(c.genericity for c in eng.claims.values())  # critic checked distinctiveness
    # blind round never carried a component reference
    assert all(c.componentId is None for c in eng.claims.values() if c.lens == "expectation")
    manifest = json.loads((tmp_path / "run-manifest.json").read_text())
    assert manifest["governance"]["blindFirstRound"] is True and manifest["governance"]["modelVersion"] == "0.1.0"


def test_coverage_matrix_semantics():
    b = prepare(load_scenario(GOV), scenario_path=GOV).governance
    exp = {t: {"seats": {"a", "b"}, "strata": {"workers"}, "titles": set()}
           for t in ("participation", "risk-classification", "impact-assessment", "compute-infrastructure")}
    rows = {r["topic"]: r for r in gv.coverage_matrix(b.model, b.taxonomy, exp)}
    assert rows["participation"]["gap"] and rows["participation"]["coverageStrength"] == "none"
    assert rows["risk-classification"]["coverageStrength"] == "documentedProposedOnly" and rows["risk-classification"]["fragile"]
    assert rows["impact-assessment"]["coverageStrength"] == "inferredOnly"
    assert rows["compute-infrastructure"]["coverageStrength"] == "documentedInForce" and not rows["compute-infrastructure"]["fragile"]
    assert not rows["energy-environment"]["gap"]  # not expected by anyone, so not a gap


# -------------------------------------------------------------- human review loop
def _packet(**over):
    base = {"packetId": "pk1", "kind": "revisionPacket", "runIds": ["r1"], "scenarioId": "S", "asOfDate": "2026-11-14",
            "modelId": "BR-AI-GOVERNANCE", "modelVersion": "0.1.0", "contextId": "c", "status": "pendingHumanReview",
            "notice": "n", "coverageMatrix": [], "seedTensions": [], "minorityOpinions": []}
    base.update(over)
    return base


def _prop(pid, lens, change, **kw):
    p = {"proposalId": pid, "claimId": "C1", "lens": lens, "change": change, "componentId": None, "topic": None,
         "title": "t " + pid, "text": "texto", "proposedTitle": "Novo mecanismo " + pid,
         "proposedDescription": "Descrição proposta com mais de dez caracteres.", "sourceIds": ["PL2338"],
         "invalidSourceIds": [], "contextFeatureIds": [], "tensionIds": [], "classification": "hypothesis",
         "confidence": "low", "author": {"agentId": "a", "stratumId": "workers", "provider": "mock"},
         "support": {"seats": 2, "strata": ["workers"], "providers": ["mock"]}, "challenges": [], "amendments": [],
         "branchAssessments": [], "criticVerdict": None, "genericity": None, "weakEvidence": False,
         "minorityOpinion": False, "requiresLegalReview": False, "decision": None}
    p.update(kw)
    return p


def _decisions(packet, model, items, reviewers=("Maria Souza",)):
    return {"packetId": packet["packetId"], "modelId": model["modelId"], "baseVersion": model["version"],
            "reviewers": list(reviewers), "decidedOn": "2026-12-01", "decisions": items}


RAT = "Justificativa humana com mais de vinte caracteres."


def test_apply_accepts_only_what_humans_decided():
    model = json.loads(MODEL.read_text())
    packet = _packet(proposals=[
        _prop("P1", "omission", "add", topic="participation"),
        _prop("P2", "excess", "remove", componentId="GM-16"),
        _prop("P3", "excess", "modify", componentId="GM-22"),
        _prop("P4", "advantage", "add", topic="language-culture"),
        _prop("P5", "omission", "add", topic="energy-environment")])
    d = _decisions(packet, model, [
        {"proposalId": "P1", "decision": "accept", "rationale": RAT},
        {"proposalId": "P2", "decision": "accept", "rationale": RAT},
        {"proposalId": "P3", "decision": "modify", "rationale": RAT, "edited": {"description": "Eixo de inovação revisado e detalhado."}},
        {"proposalId": "P4", "decision": "reject", "rationale": ""},
        {"proposalId": "P5", "decision": None}])
    new, log = gv.apply_decisions(model, packet, d, taxonomy=gv.load_taxonomy(TAXO))
    assert new["version"] == "0.2.0" and model["version"] == "0.1.0" and new["status"] == "draft"
    added = [c for c in new["components"] if c["origin"] == "councilProposed"]
    assert len(added) == 1 and added[0]["id"] == "GM-23" and added[0]["topics"] == ["participation"]
    assert "GM-16" not in {c["id"] for c in new["components"]}
    assert new["retiredComponents"][0]["component"]["id"] == "GM-16" and new["retiredComponents"][0]["proposalId"] == "P2"
    assert next(c for c in new["components"] if c["id"] == "GM-22")["description"].startswith("Eixo de inovação revisado")
    assert log["pending"] == ["P5"] and [c["proposalId"] for c in log["notApplied"]] == ["P4"]
    h = new["history"][-1]
    assert h["reviewers"] == ["Maria Souza"] and h["fromVersion"] == "0.1.0" and len(h["changes"]) == 4
    assert gv.validate_model(new, gv.load_taxonomy(TAXO)) == []
    diff = gv.diff_models(model, new)
    assert diff["added"] == ["GM-23"] and diff["removed"] == ["GM-16"] and "GM-22" in diff["modified"]


@pytest.mark.parametrize("mut,msg", [
    (lambda d: d.update(reviewers=[]), "named human reviewer"),
    (lambda d: d.update(reviewers=["  "]), "named human reviewer"),
    (lambda d: d.update(baseVersion="0.0.1"), "not on"),
    (lambda d: d.update(packetId="other"), "different packet"),
    (lambda d: d["decisions"][0].update(rationale="curto"), "at least 20"),
    (lambda d: d["decisions"][0].update(proposalId="P99"), "unknown proposal"),
    (lambda d: d["decisions"][0].update(decision="maybe"), "decision must be"),
    (lambda d: d["decisions"].append(dict(d["decisions"][0])), "decided twice"),
])
def test_apply_guards(mut, msg):
    model = json.loads(MODEL.read_text())
    packet = _packet(proposals=[_prop("P1", "omission", "add", topic="participation")])
    d = _decisions(packet, model, [{"proposalId": "P1", "decision": "accept", "rationale": RAT}])
    mut(d)
    with pytest.raises(gv.GovernanceError, match=msg):
        gv.apply_decisions(model, packet, d)


def test_components_in_force_need_a_recorded_legal_review():
    model = json.loads(MODEL.read_text())
    packet = _packet(proposals=[_prop("P1", "excess", "remove", componentId="GM-03", requiresLegalReview=True)])
    item = {"proposalId": "P1", "decision": "accept", "rationale": RAT}
    with pytest.raises(gv.GovernanceError, match="legalReview"):
        gv.apply_decisions(model, packet, _decisions(packet, model, [item]))
    item["legalReview"] = {"reviewer": "Dra. Ana Lima", "note": "Lei em vigor; remoção só como proposta ao Legislativo."}
    new, _ = gv.apply_decisions(model, packet, _decisions(packet, model, [item]))
    assert new["history"][-1]["changes"][0]["legalReview"]["reviewer"] == "Dra. Ana Lima"


def test_modify_and_add_need_content():
    model = json.loads(MODEL.read_text())
    packet = _packet(proposals=[_prop("P1", "excess", "modify", componentId="GM-22", proposedDescription=None),
                                _prop("P2", "omission", "add", topic="other", proposedTitle=None, title=None)])
    with pytest.raises(gv.GovernanceError, match="needs the corrected fields"):
        gv.apply_decisions(model, packet, _decisions(packet, model, [{"proposalId": "P1", "decision": "modify", "rationale": RAT}]))
    with pytest.raises(gv.GovernanceError, match="needs title, description and topics"):
        gv.apply_decisions(model, packet, _decisions(packet, model, [{"proposalId": "P2", "decision": "accept", "rationale": RAT}]))


def test_merge_ranks_by_replicate_stability_and_refuses_mixed_versions():
    a = _packet(packetId="a", proposals=[_prop("P1", "omission", "add", topic="participation"),
                                         _prop("P2", "omission", "add", topic="children-vulnerable")])
    b = _packet(packetId="b", runIds=["r2"], proposals=[_prop("P1", "omission", "add", topic="participation")])
    m = gv.merge_packets([a, b])
    assert m["merged"] and m["replicates"] == 2
    top = m["proposals"][0]
    assert top["topic"] == "participation" and top["replicateCount"] == 2 and top["of"] == 2 and top["proposalId"] == "M001"
    assert m["proposals"][1]["replicateCount"] == 1
    with pytest.raises(gv.GovernanceError, match="different models"):
        gv.merge_packets([a, _packet(packetId="c", modelVersion="0.2.0", proposals=[])])


def test_compare_packets_reports_resolved_persisting_new():
    a = _packet(packetId="a", proposals=[_prop("P1", "omission", "add", topic="participation"),
                                         _prop("P2", "omission", "add", topic="children-vulnerable")],
                coverageMatrix=[{"topic": "participation", "gap": True}, {"topic": "children-vulnerable", "gap": True}])
    b = _packet(packetId="b", modelVersion="0.2.0", proposals=[_prop("P1", "omission", "add", topic="children-vulnerable"),
                                                              _prop("P2", "excess", "remove", componentId="GM-12")],
                coverageMatrix=[{"topic": "children-vulnerable", "gap": True}])
    cmp = gv.compare_packets(a, b)
    assert [x["target"] for x in cmp["resolved"]] == ["participation"]
    assert [x["target"] for x in cmp["persisting"]] == ["children-vulnerable"]
    assert [x["target"] for x in cmp["new"]] == ["GM-12"]
    assert cmp["gapsClosed"] == ["participation"] and cmp["gapsPersisting"] == ["children-vulnerable"]
    assert "não que o problema" in cmp["caveat"]


def test_sheet_flags_what_reviewers_must_see():
    packet = _packet(proposals=[_prop("P1", "excess", "remove", componentId="GM-03", requiresLegalReview=True,
                                      weakEvidence=True, genericity="generic", minorityOpinion=True)])
    text = gv.render_sheet(packet)
    for needle in ("REVISÃO JURÍDICA", "evidência fraca", "genérica", "dissenso registrado", "Q2.", "scse govern apply"):
        assert needle in text


# ------------------------------------------------ two iterations through the CLI
def test_two_iterations_with_a_human_in_the_loop(tmp_path, capsys):
    out1 = run_scenario(GOV, ModelConfig.load(), RunOptions(dry_run=True, seats=8, replicates=2, critic=True),
                        out_root=tmp_path / "runs")
    review = out1["review"]
    assert Path(review["reviewSheet"]).exists() and review["proposals"] > 0
    template = json.loads(Path(review["decisionsTemplate"]).read_text())
    packet = json.loads(Path(review["mergedPacket"]).read_text())
    assert all(d["decision"] is None for d in template["decisions"])
    model_v0 = json.loads(MODEL.read_text())
    # with no human decision nothing changes, and a reviewer is still required
    with pytest.raises(gv.GovernanceError, match="named human reviewer"):
        gv.apply_decisions(model_v0, packet, template)
    # a human accepts the first three omissions and rejects the rest
    omissions = [d for d in template["decisions"] if d["lens"] == "omission" and d["change"] == "add"][:3]
    ids = {d["proposalId"] for d in omissions}
    for d in template["decisions"]:
        if d["proposalId"] in ids:
            d.update(decision="accept", rationale=RAT)
            d["edited"] = {"kind": "mechanism", "topics": [next(p for p in packet["proposals"] if p["proposalId"] == d["proposalId"])["topic"]]}
        elif not d["requiresLegalReview"]:
            d.update(decision="reject", rationale="")
    template["reviewers"] = ["Revisor Humano"]
    dec_path = tmp_path / "decisions.json"
    dec_path.write_text(json.dumps(template, ensure_ascii=False))
    v1_path = tmp_path / "model-v1.json"
    rc = cli_main(["govern", "apply", "--model", str(MODEL), "--packet", review["mergedPacket"],
                   "--decisions", str(dec_path), "--out", str(v1_path), "--taxonomy", str(TAXO)])
    assert rc == 0
    v1 = json.loads(v1_path.read_text())
    assert v1["version"] == "0.2.0" and len(v1["components"]) == len(model_v0["components"]) + 3
    assert v1["history"][-1]["reviewers"] == ["Revisor Humano"]
    # iteration 2: same scenario pointing at the revised model
    sc2 = load_scenario(GOV)
    sc2["governance"].update(modelPath=str(v1_path), taxonomyPath=str(TAXO),
                             contextPath=str(ROOT / "scenarios/governanca-brasil/context"))
    sc2["scenarioId"] = "GOV-BR-001-it2"
    sc2_path = tmp_path / "GOV-BR-001-it2.json"
    sc2_path.write_text(json.dumps(sc2, ensure_ascii=False))
    out2 = run_scenario(sc2_path, ModelConfig.load(), RunOptions(dry_run=True, seats=8, replicates=2, critic=True),
                        out_root=tmp_path / "runs")
    p2 = json.loads(Path(out2["review"]["mergedPacket"]).read_text())
    assert p2["modelVersion"] == "0.2.0"
    cmp = gv.compare_packets(packet, p2)
    assert set(cmp) >= {"persisting", "resolved", "new", "gapsClosed", "gapsOpened", "caveat"}
    covered = {t for d in template["decisions"] if d["decision"] == "accept"
               for t in next(p for p in packet["proposals"] if p["proposalId"] == d["proposalId"])["topic"].split()}
    still_gap = {r["topic"] for r in p2["coverageMatrix"] if r["gap"]}
    assert not (covered & still_gap)  # accepted topics are no longer gaps
    rc = cli_main(["govern", "diff", str(MODEL), str(v1_path)])
    assert rc == 0 and "added" in capsys.readouterr().out


# ------------------------------------------------- per-stratum positions (no false consensus)
def _seat_of(eng, stratum, n=0):
    return [s for s in eng.roster.seats if s.stratumId == stratum][n]


def _turn(*actions):
    return {"actions": list(actions), "insufficientGrounding": False, "notes": ""}


def test_packet_shows_every_stratum_position_in_its_own_words():
    eng = _engine(seats=16)
    author, backer = _seat_of(eng, "civilSociety"), _seat_of(eng, "workers")
    critic_, editor = _seat_of(eng, "business"), _seat_of(eng, "research")
    eng._apply(author, "R1", _turn(_action(lens="expectation", topic="participation", text="participação social " * 3)))
    eng._apply(author, "R2", _turn(_action(lens="omission", change="add", topic="participation",
                                           text="Falta um canal permanente de participação social.")))
    fid = next(c.id for c in eng.claims.values() if c.lens == "omission")
    eng._apply(backer, "R3", _turn(_action(action="support", targetClaimId=fid,
                                           text="Trabalhadores precisam de assento onde a IA muda o trabalho.")))
    eng._apply(critic_, "R3", _turn(_action(action="challenge", targetClaimId=fid,
                                            text="Mais um conselho consultivo atrasa decisões sem mudar resultado.")))
    eng._apply(editor, "R5", _turn(_action(action="proposeAmendment", targetClaimId=fid, change="add",
                                           topic="participation", text="Participação com prazo e devolutiva pública.")))
    packet = gv.build_packet(eng)
    prop = next(p for p in packet["proposals"] if p["claimId"] == fid)
    rows = {r["stratumId"]: r for r in prop["stratumPositions"]}
    assert len(rows) == 8 and set(rows) == {s["stratumId"] for s in packet["strata"]}
    assert rows["civilSociety"]["stance"] == "for"
    assert rows["workers"]["stance"] == "for" and "assento" in rows["workers"]["statements"][0]["text"]
    assert rows["business"]["stance"] == "against" and "atrasa" in rows["business"]["statements"][0]["text"]
    assert rows["research"]["stance"] == "amend"
    assert rows["regulators"]["stance"] == "silent" and rows["regulators"]["statements"] == []
    spread = prop["positionSpread"]
    assert spread["contested"] and set(spread["for"]) == {"civilSociety", "workers"} and spread["against"] == ["business"]
    persp = {sp["stratumId"]: sp for sp in packet["strataPerspectives"]}
    assert persp["business"]["aloneAgainst"] == [prop["proposalId"]]
    assert persp["civilSociety"]["authored"] == [prop["proposalId"]]
    assert persp["civilSociety"]["blindExpectations"][0]["topic"] == "participation"
    sheet = gv.render_sheet(packet)
    assert "Cada estrato, sua leitura" in sheet and "| Empresas / startups | contra |" in sheet
    assert "contestada" in sheet and "Um estrato calado não concorda" in sheet


def test_split_stratum_and_supports_on_revised_versions():
    eng = _engine(seats=16)
    author = _seat_of(eng, "civilSociety")
    pro, con = _seat_of(eng, "business", 0), _seat_of(eng, "business", 1)
    eng._apply(author, "R2", _turn(_action(lens="omission", change="add", topic="participation")))
    fid = next(iter(eng.claims))
    eng._apply(pro, "R3", _turn(_action(action="support", targetClaimId=fid, text="apoio com ressalva de custo " * 2)))
    eng._apply(con, "R3", _turn(_action(action="challenge", targetClaimId=fid, text="custo de conformidade alto " * 2)))
    eng._apply(author, "R4", _turn(_action(action="revise", targetClaimId=fid, text="versão revisada com prazo " * 2)))
    rid = eng.claims[fid].supersededBy
    packet = gv.build_packet(eng)
    prop = next(p for p in packet["proposals"] if p["claimId"] == rid)
    row = next(r for r in prop["stratumPositions"] if r["stratumId"] == "business")
    assert row["stance"] == "split" and row["seatsSpoke"] == 2
    assert all(st["onEarlierVersion"] for st in row["statements"])


def test_merge_pools_findings_and_flags_unstable_stances():
    def rows(stance_by_stratum):
        return [{"stratumId": k, "label": k, "stance": v, "seatsTotal": 2, "seatsSpoke": int(v != "silent"),
                 "seatStances": {} if v == "silent" else {f"agent:{k}-01": v}, "statements": []}
                for k, v in stance_by_stratum.items()]
    a1 = _prop("P1", "omission", "add", topic="participation", stratumPositions=rows({"workers": "for", "business": "silent"}))
    a2 = _prop("P2", "omission", "add", topic="participation", stratumPositions=rows({"workers": "silent", "business": "against"}))
    b1 = _prop("P1", "omission", "add", topic="participation", stratumPositions=rows({"workers": "for", "business": "silent"}))
    strata = [{"stratumId": "workers", "label": "workers", "seats": 2}, {"stratumId": "business", "label": "business", "seats": 2}]
    m = gv.merge_packets([_packet(packetId="a", strata=strata, proposals=[a1, a2]),
                          _packet(packetId="b", runIds=["r2"], strata=strata, proposals=[b1])])
    pos = {r["stratumId"]: r for r in m["proposals"][0]["stratumPositions"]}
    assert pos["workers"]["stance"] == "for"  # pooled within replicate 1, held in replicate 2
    assert pos["business"]["stance"] == "variesAcrossReplicates" and pos["business"]["byReplicate"] == {"1": "against", "2": "silent"}
    assert [sp["stratumId"] for sp in m["strataPerspectives"]] == ["workers", "business"]
