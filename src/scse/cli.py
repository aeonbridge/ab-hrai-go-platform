"""Command line interface: ``scse validate|run|experiment|models``."""
from __future__ import annotations

import argparse
import json
import sys

from .config import ConfigError, ModelConfig, parse_set_option
from .world import ScenarioError, load_scenario, validate


def _config(args) -> ModelConfig:
    return ModelConfig.load(args.config, overrides=[parse_set_option(x) for x in (args.set or [])])


def cmd_validate(args) -> int:
    rc = 0
    for path in args.scenarios:
        errors = validate(load_scenario(path), "scenario")
        print(("OK   " if not errors else "FAIL ") + path)
        for e in errors:
            print("     " + e)
        rc |= bool(errors)
    return rc


def cmd_run(args) -> int:
    from .runner import RunOptions, run_scenario

    config = _config(args)
    providers = args.providers.split(",") if args.providers else None
    if args.assignment == "single" and not providers:
        print("--assignment single requer --providers <um provider>", file=sys.stderr)
        return 2
    opts = RunOptions(providers=providers, assignment=args.assignment, mode=args.mode, seats=args.seats,
                      replicates=args.replicates, rounds=args.rounds, dry_run=args.dry_run,
                      critic=args.critic, synthesize=args.synthesize, workers=args.workers, label=args.label)
    if not args.dry_run:
        unverified = config.unverified_models(providers or config.required_providers)
        if unverified:
            print("AVISO: IDs não verificados na API (rode `scse models verify`): " + ", ".join(unverified),
                  file=sys.stderr)
    out = run_scenario(args.scenario, config, opts, out_root=args.out)
    print(json.dumps({k: out[k] for k in ("scenarioId", "outDir", "runs")}, ensure_ascii=False, indent=2))
    return 0


def cmd_experiment(args) -> int:
    from .experiment import load_experiment, plan, run_experiment

    if args.plan:
        print(json.dumps(plan(load_experiment(args.file)), ensure_ascii=False, indent=2))
        return 0
    out = run_experiment(args.file, dry_run=args.dry_run, config_path=args.config, out_root=args.out,
                         workers=args.workers)
    print(f"Resumo: {out['outDir']}/experiment-summary.md")
    return 0


def cmd_models(args) -> int:
    config = _config(args)
    providers = args.providers.split(",") if args.providers else [
        p for p in config.provider_names() if config.provider(p)["sdk"] != "mock"]
    if args.action == "list":
        print(f"config: {config.source}  assignment padrão: {config.assignment}")
        for profile, tier in config.data.get("profiles", {}).items():
            row = [f"{profile:22s} -> {tier:9s}"]
            for p in providers:
                spec = config.model(p, profile)
                flag = "" if config.provider(p)["models"][tier].get("verified") else "*"
                row.append(f"{p}={spec.id}{flag}")
            print("  ".join(row))
        print("(* = ID não verificado na API do provider)")
        return 0
    from .providers import CompletionRequest, ProviderError, build_provider

    rc = 0
    for p in providers:
        tiers = config.provider(p)["models"]
        if args.action == "verify":
            try:
                available = set(build_provider(config.model(p, "smoke")).list_models())
            except (ProviderError, Exception) as exc:  # noqa: BLE001 - report any SDK/network failure
                print(f"{p}: ERRO ao listar modelos: {exc}")
                rc = 1
                continue
            for tier, spec in tiers.items():
                ok = spec["id"] in available
                rc |= not ok
                print(f"{p}.{tier}: {spec['id']} {'OK' if ok else 'AUSENTE na API'}")
        elif args.action == "ping":
            prov = build_provider(config.model(p, "smoke"))
            schema = {"type": "object", "additionalProperties": False, "required": ["ok"],
                      "properties": {"ok": {"type": "boolean"}}}
            try:
                res = prov.complete(CompletionRequest(system="Responda só JSON.", user='Retorne {"ok": true}.',
                                                      schema=schema, schema_name="ping", max_output_tokens=2000))
                print(f"{p}: {res.model_served} -> {res.text[:80]!r} ({res.latency_s:.1f}s)")
            except ProviderError as exc:
                print(f"{p}: ERRO {exc}")
                rc = 1
    return rc


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="scse", description="Shadow Council Simulation Environment")
    ap.add_argument("--config", help="arquivo de roteamento de modelos (padrão config/scse/models.toml)")
    ap.add_argument("--set", action="append", metavar="PROVIDER.TIER[.KEY]=VALOR",
                    help="sobrescreve modelo/opção, ex.: --set xai.deep=grok-4.6")
    sub = ap.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate", help="valida cenários contra scenario.schema.json")
    v.add_argument("scenarios", nargs="+")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("run", help="executa um cenário (réplicas, relatórios)")
    r.add_argument("scenario")
    r.add_argument("--providers", help="lista separada por vírgula (padrão: required_providers)")
    r.add_argument("--assignment", choices=["rotate", "fixed", "single"])
    r.add_argument("--mode", choices=["stratified", "unstratified", "singleAgent"], default="stratified")
    r.add_argument("--seats", type=int, help="sobrescreve targetSeats (redução de custo)")
    r.add_argument("--replicates", type=int)
    r.add_argument("--rounds", type=int)
    r.add_argument("--critic", action="store_true", help="crítica cruzada entre providers na R7")
    r.add_argument("--synthesize", action="store_true", help="descrições de tensões por modelo sintetizador")
    r.add_argument("--dry-run", action="store_true", help="usa provider mock offline")
    r.add_argument("--workers", type=int, default=8)
    r.add_argument("--label")
    r.add_argument("--out", default="runs")
    r.set_defaults(func=cmd_run)

    e = sub.add_parser("experiment", help="matriz cenários x braços (comparação de providers)")
    e.add_argument("file")
    e.add_argument("--plan", action="store_true", help="só estima execuções e chamadas")
    e.add_argument("--dry-run", action="store_true")
    e.add_argument("--workers", type=int, default=8)
    e.add_argument("--out", default="runs/experiments")
    e.set_defaults(func=cmd_experiment)

    m = sub.add_parser("models", help="list | verify | ping")
    m.add_argument("action", choices=["list", "verify", "ping"])
    m.add_argument("--providers")
    m.set_defaults(func=cmd_models)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, ScenarioError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
