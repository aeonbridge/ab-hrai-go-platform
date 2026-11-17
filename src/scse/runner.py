"""Scenario orchestration: replicates, preflight checks and sensitivity report."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import metrics
from .config import ConfigError, ModelConfig
from .council import compose
from .deliberation import DeliberationEngine
from .report import compile_run
from .world import load_scenario, prepare, sha256_json


@dataclass
class RunOptions:
    providers: list[str] | None = None
    assignment: str | None = None
    mode: str = "stratified"
    seats: int | None = None
    replicates: int | None = None
    rounds: int | None = None
    dry_run: bool = False
    critic: bool = False
    synthesize: bool = False
    workers: int = 8
    label: str | None = None
    transport: str | None = None
    extra_limitations: list[str] = field(default_factory=list)


def preflight(config: ModelConfig, providers: list[str], dry_run: bool, transport: str | None = None) -> list[str]:
    """Return blocking problems (missing keys/SDKs). Warnings go to the manifest."""
    if dry_run:
        return []
    problems = []
    sdk_modules = {"anthropic": "anthropic", "openai": "openai", "xai": "openai", "gemini": "google.genai"}
    via_openrouter = [n for n in providers if config.provider(n)["sdk"] != "mock"
                      and config.transport_for(n, transport) == "openrouter"]
    if via_openrouter:
        env = config.data.get("openrouter", {}).get("api_key_env", "OPENROUTER_API_KEY")
        if not os.environ.get(env):
            problems.append(f"openrouter ({', '.join(via_openrouter)}): defina ${env}")
        try:
            __import__("openai")
        except ImportError:
            problems.append("openrouter: instale o SDK openai; ex.: pip install -e '.[all]'")
    for name in providers:
        prov = config.provider(name)
        if prov["sdk"] == "mock" or name in via_openrouter:
            continue
        envs = [prov.get("api_key_env")] + (["GOOGLE_API_KEY"] if prov["sdk"] == "gemini" else [])
        if not any(e and os.environ.get(e) for e in envs):
            problems.append(f"{name}: defina ${prov.get('api_key_env')}")
        module = sdk_modules.get(prov["sdk"])
        try:
            __import__(module)
        except ImportError:
            problems.append(f"{name}: instale o SDK ({module}); ex.: pip install -e '.[all]'")
    return problems


def write_latest_index(base: Path, scenario_id: str, label: str, *, dry_run: bool = False) -> Path:
    """Write a portable index for the latest run and its downloadable artifacts."""
    root = base.parent
    artifacts = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.name.startswith("._"):
            continue
        artifacts.append({
            "path": path.relative_to(root).as_posix(),
            "name": path.name,
            "sizeBytes": path.stat().st_size,
        })

    def artifact_path(relative_path: str) -> str | None:
        candidate = base / relative_path
        return candidate.relative_to(root).as_posix() if candidate.is_file() else None

    index = {
        "schemaVersion": 1,
        "scenarioId": scenario_id,
        "runId": base.name,
        "label": label,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "dryRun": dry_run,
        "packetPath": artifact_path("merged-packet.json"),
        "reportPath": artifact_path("rep-01/report.md"),
        "reportJsonPath": artifact_path("rep-01/report.json"),
        "httpTracePath": next((item["path"] for item in artifacts if item["name"] == "openrouter-http.jsonl"), None),
        "artifacts": artifacts,
    }
    index_path = root / "latest.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = index_path.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(index_path)
    return index_path


def run_scenario(scenario_path: str | Path, config: ModelConfig, opts: RunOptions,
                 out_root: str | Path = "runs") -> dict:
    scenario = load_scenario(scenario_path)
    if opts.replicates:
        scenario["simulation"]["replicates"] = opts.replicates
    if opts.rounds:
        scenario["simulation"]["rounds"] = opts.rounds
    snapshot = prepare(scenario, scenario_path=scenario_path, seats_override=opts.seats)
    providers = opts.providers or config.required_providers
    problems = preflight(config, providers, opts.dry_run, opts.transport)
    if problems:
        raise ConfigError("preflight falhou:\n  " + "\n  ".join(problems))
    sim = scenario["simulation"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = opts.label or f"{opts.mode}-{opts.assignment or config.assignment}"
    base = Path(out_root) / scenario["scenarioId"] / f"{stamp}-{label}{'-dryrun' if opts.dry_run else ''}"
    results = []
    for rep in range(int(sim["replicates"])):
        seed = int(sim["randomSeed"]) + rep
        roster = compose(snapshot, config, providers=providers, assignment=opts.assignment, mode=opts.mode,
                         seed=int(sim["randomSeed"]), replicate=rep, transport=opts.transport)
        run_id = f"{scenario['scenarioId']}-{label}-r{rep + 1}-{sha256_json([snapshot.snapshot_hash, seed, label])[:8]}"
        if scenario["mode"] == "governanceReview":
            from .governance_engine import GovernanceEngine as engine_cls
        else:
            engine_cls = DeliberationEngine
        trace_enabled = not opts.dry_run and any(
            config.provider(p)["sdk"] != "mock" and config.transport_for(p, opts.transport) == "openrouter"
            for p in providers
        )
        trace_path = (base / f"rep-{rep + 1:02d}" / "http" / "openrouter-http.jsonl") if trace_enabled else None
        engine = engine_cls(snapshot, roster, config, run_id=run_id, seed=seed, dry_run=opts.dry_run,
                                    max_workers=opts.workers, critic=opts.critic, synthesize=opts.synthesize,
                                    transport=opts.transport, openrouter_trace_path=str(trace_path) if trace_path else None)
        limitations = list(opts.extra_limitations)
        try:
            engine.run()
            if opts.dry_run:
                limitations.append("DRY-RUN: respostas geradas pelo provider mock determinístico; nenhum modelo real foi consultado.")
            unverified = config.unverified_models(providers, opts.transport)
            if unverified and not opts.dry_run:
                limitations.append("IDs de modelo não verificados na API: " + ", ".join(unverified))
            results.append(compile_run(engine, base / f"rep-{rep + 1:02d}", extra_limitations=limitations))
        finally:
            engine.close()
    sens = metrics.sensitivity([r["summary"] for r in results])
    review = None
    if scenario["mode"] == "governanceReview":
        from . import governance
        merged = governance.merge_packets([r["packet"] for r in results])
        base.mkdir(parents=True, exist_ok=True)
        (base / "merged-packet.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        (base / "review-sheet.md").write_text(governance.render_sheet(merged), encoding="utf-8")
        (base / "decisions.template.json").write_text(json.dumps(
            governance.decisions_template(merged, snapshot.governance.model), ensure_ascii=False, indent=2), encoding="utf-8")
        review = {"mergedPacket": str(base / "merged-packet.json"), "reviewSheet": str(base / "review-sheet.md"),
                  "decisionsTemplate": str(base / "decisions.template.json"), "proposals": len(merged["proposals"])}
    agg = metrics.aggregate_scorecards([r["scorecard"] for r in results])
    out = {"scenarioId": scenario["scenarioId"], "label": label, "outDir": str(base),
           "snapshotHash": snapshot.snapshot_hash, "sensitivity": sens, "providerScorecard": agg,
           "runs": [r["report"]["runId"] for r in results]}
    if review:
        out["review"] = review
    base.mkdir(parents=True, exist_ok=True)
    (base / "sensitivity-report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    write_latest_index(base, scenario["scenarioId"], label, dry_run=opts.dry_run)
    return out
