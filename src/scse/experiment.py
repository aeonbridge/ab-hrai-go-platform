"""Experiment matrix: scenarios x council arms, to compare each provider's practice."""
from __future__ import annotations

import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from . import metrics
from .config import ModelConfig, parse_set_option
from .runner import RunOptions, run_scenario
from .world import load_scenario


def load_experiment(path: str | Path) -> dict:
    with Path(path).open("rb") as fh:
        exp = tomllib.load(fh)
    arms = []
    for arm in exp.get("arms", []):
        if arm.get("per_provider"):
            for p in arm.get("providers") or exp.get("providers", []):
                arms.append({**{k: v for k, v in arm.items() if k != "per_provider"},
                             "id": f"{arm['id']}-{p}", "providers": [p], "assignment": "single"})
        else:
            arms.append(arm)
    exp["arms"] = arms
    return exp


def plan(exp: dict) -> dict:
    rows = []
    total_calls = 0
    for sc_path in exp["scenarios"]:
        sc = load_scenario(sc_path)
        reps = exp.get("replicates", sc["simulation"]["replicates"])
        for arm in exp["arms"]:
            seats = 1 if arm.get("mode") == "singleAgent" else exp.get("seats", sc["council"]["targetSeats"])
            rounds = exp.get("rounds", sc["simulation"]["rounds"])
            calls = seats * (rounds + 1) * reps  # upper bound: every seat every round + R7
            total_calls += calls
            rows.append({"scenario": sc["scenarioId"], "arm": arm["id"], "seats": seats,
                         "replicates": reps, "maxCalls": calls})
    return {"runs": sum(r["replicates"] for r in rows), "maxModelCalls": total_calls, "rows": rows}


def run_experiment(path: str | Path, *, dry_run: bool = False, config_path: str | None = None,
                   out_root: str | Path = "runs/experiments", workers: int = 8) -> dict:
    exp = load_experiment(path)
    overrides = [parse_set_option(f"{k}={v}") for k, v in exp.get("overrides", {}).items()]
    if exp.get("strata"):
        overrides.append({"strata": exp["strata"]})  # per-experiment stratum mixes
    config = ModelConfig.load(config_path, overrides=overrides)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = Path(out_root) / f"{stamp}-{exp['name']}{'-dryrun' if dry_run else ''}"
    results = []
    for sc_path in exp["scenarios"]:
        for arm in exp["arms"]:
            opts = RunOptions(providers=arm.get("providers") or exp.get("providers"),
                              assignment=arm.get("assignment"), mode=arm.get("mode", "stratified"),
                              seats=None if arm.get("mode") == "singleAgent" else exp.get("seats"),
                              replicates=exp.get("replicates"), rounds=exp.get("rounds"), dry_run=dry_run,
                              critic=exp.get("critic", False), synthesize=exp.get("synthesize", False),
                              workers=workers, label=arm["id"],
                              transport=arm.get("transport") or exp.get("transport"),
                              extra_limitations=[f"Braço experimental: {arm.get('description', arm['id'])}"])
            res = run_scenario(sc_path, config, opts, out_root=root / "runs")
            results.append({"scenario": res["scenarioId"], "arm": arm["id"], **res})
    summary = summarize(exp, results)
    summary["dryRun"] = dry_run
    root.mkdir(parents=True, exist_ok=True)
    (root / "experiment-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "experiment-summary.md").write_text(render_md(summary), encoding="utf-8")
    summary["outDir"] = str(root)
    return summary


def summarize(exp: dict, results: list[dict]) -> dict:
    by_arm: dict[str, list[dict]] = {}
    for r in results:
        by_arm.setdefault(r["arm"], []).append(r)
    arms = {}
    for arm, rs in by_arm.items():
        arms[arm] = {
            "scorecard": metrics.aggregate_scorecards([r["providerScorecard"] for r in rs]),
            "tensionsMean": round(sum(r["sensitivity"]["metrics"]["tensions"]["mean"] for r in rs) / len(rs), 3),
            "tensionsStdevMean": round(sum(r["sensitivity"]["metrics"]["tensions"]["stdev"] for r in rs) / len(rs), 3),
            "structureJaccardMean": _mean([r["sensitivity"]["tensionStructureJaccard"]["mean"] for r in rs]),
            "runs": [r["outDir"] for r in rs],
        }
    return {"experiment": exp["name"], "description": exp.get("description", ""),
            "hypotheses": exp.get("hypotheses", []), "arms": arms,
            "caveat": ("Métricas comportamentais dentro do protocolo; não medem verdade nem qualidade. "
                       "Para isso, aplicar a rubrica de especialistas da especificação (seção de avaliação).")}


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def render_md(summary: dict) -> str:
    lines = [f"# Experimento {summary['experiment']}", ""]
    if summary.get("dryRun"):
        lines += ["> **DRY-RUN.** Todos os números abaixo vêm do provider mock com personas arbitrárias. "
                  "Eles testam o pipeline e NÃO dizem nada sobre Anthropic, OpenAI, xAI ou Gemini.", ""]
    lines += [summary.get("description", ""), "", f"> {summary['caveat']}", ""]
    if summary.get("hypotheses"):
        lines += ["## Hipóteses", ""] + [f"- {h}" for h in summary["hypotheses"]] + [""]
    cols = ["schemaValidRate", "refusalRate", "groundingRate", "invalidCitationRate", "challengesPerR3Turn",
            "responsivenessRate", "selfSupportShare", "selfChallengeShare", "criticGroundedRate"]
    for arm, data in summary["arms"].items():
        lines += [f"## Braço `{arm}`", "",
                  f"Tensões (média): {data['tensionsMean']} · desvio entre réplicas: {data['tensionsStdevMean']} · "
                  f"estabilidade estrutural (Jaccard): {data['structureJaccardMean']}", "",
                  "| provider | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
        for p, m in sorted(data["scorecard"].items()):
            lines.append(f"| {p} | " + " | ".join(str(m.get(c, "")) for c in cols) + " |")
        lines.append("")
    return "\n".join(lines)
