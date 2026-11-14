from collections import Counter
from pathlib import Path

import pytest

from scse.config import ConfigError, ModelConfig, parse_set_option
from scse.council import compose
from scse.world import allocate_seats, load_scenario, prepare

ROOT = Path(__file__).resolve().parents[2]
SC1 = ROOT / "scenarios/brasil-ficticio/BR-PBIA-001.json"
REQUIRED = {"anthropic", "openai", "xai", "gemini"}


def test_required_providers_present():
    cfg = ModelConfig.load()
    assert set(cfg.required_providers) == REQUIRED
    for p in REQUIRED:
        for profile in ("perspective.deep", "perspective.standard", "critic", "synthesizer", "smoke"):
            assert cfg.model(p, profile).id


def test_overrides_cli_and_env():
    # "vendor/model" -> OpenRouter slug; plain id -> direct API id
    cfg = ModelConfig.load(overrides=[parse_set_option("xai.deep=x-ai/grok-test"),
                                      parse_set_option("openai.deep=gpt-direct-test")],
                           env={"SCSE_MODEL__GEMINI__STANDARD": "google/gemini-test"})
    assert cfg.model("xai", "perspective.deep").id == "x-ai/grok-test"
    assert cfg.model("gemini", "perspective.standard").id == "google/gemini-test"
    assert cfg.model("openai", "perspective.deep", transport="direct").id == "gpt-direct-test"
    cfg2 = ModelConfig.load(overrides=[parse_set_option("openai.deep.effort=low")])
    assert cfg2.model("openai", "perspective.deep").options["effort"] == "low"


def test_missing_required_provider_rejected():
    cfg = ModelConfig.load()
    data = dict(cfg.data)
    data["providers"] = {k: v for k, v in data["providers"].items() if k != "xai"}
    with pytest.raises(ConfigError):
        ModelConfig(data)


def test_seat_allocation_scales():
    strata = [{"id": "a", "seats": 3}, {"id": "b", "seats": 2}, {"id": "c", "seats": 5}]
    assert sum(allocate_seats(strata, 8).values()) == 8
    assert min(allocate_seats(strata, 4).values()) >= 1


def test_rotate_mixes_providers_within_strata_and_across_replicates():
    cfg = ModelConfig.load()
    snap = prepare(load_scenario(SC1), scenario_path=SC1)
    r0 = compose(snap, cfg, seed=1, replicate=0)
    r1 = compose(snap, cfg, seed=1, replicate=1)
    assert len(r0.seats) == 20
    assert set(Counter(s.provider for s in r0.seats)) == REQUIRED
    assert max(Counter(s.provider for s in r0.seats).values()) == 5
    assert "regulators" in r0.balance["strataWithMixedProviders"]
    assert [s.provider for s in r0.seats] != [s.provider for s in r1.seats]
    assert r0.coverage["denominator"] == 9 and r0.coverage["numerator"] == 8


def test_profile_selects_tier():
    cfg = ModelConfig.load()
    snap = prepare(load_scenario(SC1), scenario_path=SC1)
    roster = compose(snap, cfg, seed=1)
    reg = next(s for s in roster.seats if s.stratumId == "regulators")
    biz = next(s for s in roster.seats if s.stratumId == "business")
    assert reg.model == cfg.model(reg.provider, "perspective.deep").id
    assert biz.model == cfg.model(biz.provider, "perspective.standard").id


def test_single_and_fixed_assignment():
    cfg = ModelConfig.load()
    snap = prepare(load_scenario(SC1), scenario_path=SC1)
    solo = compose(snap, cfg, providers=["xai"], assignment="single")
    assert {s.provider for s in solo.seats} == {"xai"}
    assert any("provider único" in w for w in solo.balance["warnings"])
    fixed = compose(snap, cfg, assignment="fixed")
    assert all(s.provider == cfg.fixed_assignment()[s.stratumId] for s in fixed.seats)
    with pytest.raises(ConfigError):
        compose(snap, cfg, assignment="fixed", mode="unstratified")


def test_baseline_modes():
    cfg = ModelConfig.load()
    snap = prepare(load_scenario(SC1), scenario_path=SC1, seats_override=8)
    assert len(compose(snap, cfg, mode="singleAgent").seats) == 1
    b2 = compose(snap, cfg, mode="unstratified")
    assert len(b2.seats) == 8 and {s.stratumId for s in b2.seats} == {"unstratified"}


def test_default_mix_equal_weights_everywhere():
    cfg = ModelConfig.load()
    for stratum in ["regulators", "publicOperators", "business", "research", "civilSociety", "workers",
                    "affectedGroups", "infrastructure", "anyUnknownStratum"]:
        entries = cfg.stratum_mix(stratum)
        assert {e.provider for e in entries} == REQUIRED
        assert len({e.weight for e in entries}) == 1


def test_weighted_default_matches_balanced_rotation():
    cfg = ModelConfig.load()
    snap = prepare(load_scenario(SC1), scenario_path=SC1)
    roster = compose(snap, cfg, seed=1)
    assert roster.assignment == "weighted"
    assert set(Counter(s.provider for s in roster.seats).values()) == {5}
    assert all(s.transport == "openrouter" for s in roster.seats)
    assert roster.mix["regulators"]["configuredPercent"] == {f"{p}:<profile>": 25.0 for p in REQUIRED}


def _custom(mix):
    return ModelConfig.load(overrides=[{"strata": {"regulators": {"mix": mix}}}])


def test_custom_weights_realised_across_replicates():
    cfg = _custom([{"provider": "anthropic", "weight": 50}, {"provider": "openai", "weight": 25},
                   {"provider": "gemini", "weight": 25}])
    snap = prepare(load_scenario(SC1), scenario_path=SC1)
    counts = Counter()
    for rep in range(40):
        roster = compose(snap, cfg, seed=3, replicate=rep)
        counts.update(s.provider for s in roster.seats if s.stratumId == "regulators")
    total = sum(counts.values())
    assert "xai" not in counts
    assert abs(counts["anthropic"] / total - 0.5) < 0.05
    assert abs(counts["openai"] / total - 0.25) < 0.05


def test_mix_can_split_models_within_provider():
    cfg = _custom([{"provider": "anthropic", "tier": "deep", "weight": 1},
                   {"provider": "anthropic", "model": "anthropic/claude-sonnet-5.5", "weight": 1},
                   {"provider": "xai", "model": "x-ai/grok-custom", "weight": 1}])
    snap = prepare(load_scenario(SC1), scenario_path=SC1)
    roster = compose(snap, cfg, seed=0)
    models = {s.model for s in roster.seats if s.stratumId == "regulators"}
    assert models == {"anthropic/claude-opus-5.5", "anthropic/claude-sonnet-5.5", "x-ai/grok-custom"}
    sonnet = next(s for s in roster.seats if s.model == "anthropic/claude-sonnet-5.5")
    assert sonnet.tier == "standard" and sonnet.spec.options.get("effort") == "medium"


def test_providers_filter_renormalises_mix():
    cfg = ModelConfig.load()
    snap = prepare(load_scenario(SC1), scenario_path=SC1)
    roster = compose(snap, cfg, providers=["anthropic", "gemini"], seed=0)
    assert {s.provider for s in roster.seats} == {"anthropic", "gemini"}


def test_invalid_mix_rejected():
    with pytest.raises(ConfigError):
        _custom([{"provider": "nope", "weight": 1}])
    with pytest.raises(ConfigError):
        _custom([{"provider": "xai", "weight": 0}])
