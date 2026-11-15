"""Command line interface: ``scse validate|run|experiment|models``."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ConfigError, ModelConfig, parse_set_option
from .governance import GovernanceError
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
                      critic=args.critic, synthesize=args.synthesize, workers=args.workers, label=args.label,
                      transport=args.transport)
    if not args.dry_run:
        unverified = config.unverified_models(providers or config.required_providers, args.transport)
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


def _json(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path, value) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_govern(args) -> int:
    from . import governance as gv

    cmd = args.govern_cmd
    if cmd == "validate":
        taxonomy = gv.load_taxonomy(args.taxonomy) if args.taxonomy else None
        errors = gv.validate_model(_json(args.model), taxonomy)
        print(("OK   " if not errors else "FAIL ") + args.model)
        for e in errors:
            print("     " + e)
        return 1 if errors else 0
    if cmd == "sheet":
        packets = gv.load_packets(args.packet)
        packet = packets[0] if len(packets) == 1 else gv.merge_packets(packets)
        out = Path(args.out or (args.packet if Path(args.packet).is_dir() else Path(args.packet).parent))
        out.mkdir(parents=True, exist_ok=True)
        (out / "review-sheet.md").write_text(gv.render_sheet(packet), encoding="utf-8")
        _write(out / "merged-packet.json", packet)
        _write(out / "decisions.template.json", gv.decisions_template(packet, _json(args.model)))
        print(f"{len(packet['proposals'])} propostas de {len(packets)} réplica(s) em {out}")
        print(f"1) leia {out / 'review-sheet.md'}   2) preencha {out / 'decisions.template.json'}   "
              f"3) scse govern apply --model {args.model} --packet {out / 'merged-packet.json'} --decisions <arquivo> --out <novo-modelo.json>")
        return 0
    if cmd == "apply":
        taxonomy = gv.load_taxonomy(args.taxonomy) if args.taxonomy else None
        packets = gv.load_packets(args.packet)
        packet = packets[0] if len(packets) == 1 else gv.merge_packets(packets)
        new, log = gv.apply_decisions(_json(args.model), packet, _json(args.decisions),
                                      new_version=args.new_version, taxonomy=taxonomy)
        _write(args.out, new)
        _write(str(args.out) + ".changelog.json", log)
        print(f"{log['fromVersion']} -> {log['toVersion']} por {', '.join(log['reviewers'])}: "
              f"{len(log['applied'])} aplicada(s), {len(log['notApplied'])} rejeitada(s)/adiada(s), {len(log['pending'])} pendente(s)")
        return 0
    if cmd == "compare":
        a, b = (gv.load_packets(x) for x in (args.a, args.b))
        a = a[0] if len(a) == 1 else gv.merge_packets(a)
        b = b[0] if len(b) == 1 else gv.merge_packets(b)
        print(json.dumps(gv.compare_packets(a, b), ensure_ascii=False, indent=2))
        return 0
    if cmd == "diff":
        print(json.dumps(gv.diff_models(_json(args.a), _json(args.b)), ensure_ascii=False, indent=2))
        return 0
    return 2


def cmd_models(args) -> int:
    config = _config(args)
    providers = args.providers.split(",") if args.providers else [
        p for p in config.provider_names() if config.provider(p)["sdk"] != "mock"]
    transport = args.transport
    if args.action == "list":
        print(f"config: {config.source}  assignment padrão: {config.assignment}  "
              f"transporte: {', '.join(sorted({config.transport_for(p, transport) for p in providers}))}")
        for profile, tier in config.data.get("profiles", {}).items():
            row = [f"{profile:22s} -> {tier:9s}"]
            for p in providers:
                spec = config.model(p, profile, transport=transport)
                tier_cfg = config.provider(p)["models"][tier]
                ok = tier_cfg.get("openrouter_verified") if spec.transport == "openrouter" else tier_cfg.get("verified")
                row.append(f"{p}={spec.id}{'' if ok else '*'}")
            print("  ".join(row))
        print("(* = ID não verificado na API)")
        print("\nDistribuição por estrato (% configurado):")
        for stratum in config.data.get("strata", {}):
            entries = config.stratum_mix(stratum)
            total = sum(e.weight for e in entries)
            print(f"  {stratum:16s} " + "  ".join(f"{e.key}={100 * e.weight / total:.0f}%" for e in entries))
        return 0
    from .providers import CompletionRequest, ProviderError, build_provider

    rc = 0
    for p in providers:
        tiers = config.provider(p)["models"]
        if args.action == "verify":
            try:
                available = set(build_provider(config.model(p, "smoke", transport=transport)).list_models())
            except (ProviderError, Exception) as exc:  # noqa: BLE001 - report any SDK/network failure
                print(f"{p}: ERRO ao listar modelos: {exc}")
                rc = 1
                continue
            for tier in tiers:
                model_id = config.model(p, "smoke", tier=tier, transport=transport).id
                ok = model_id in available
                rc |= not ok
                print(f"{p}.{tier}: {model_id} {'OK' if ok else 'AUSENTE na API'}")
        elif args.action == "ping":
            prov = build_provider(config.model(p, "smoke", transport=transport))
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
    r.add_argument("--assignment", choices=["weighted", "rotate", "fixed", "single"])
    r.add_argument("--transport", choices=["openrouter", "direct"], help="sobrescreve o transporte de todos os providers")
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

    g = sub.add_parser("govern", help="ciclo de revisão humana do modelo de governança (modo governanceReview)")
    gs = g.add_subparsers(dest="govern_cmd", required=True)
    gv_ = gs.add_parser("validate", help="valida um modelo de governança")
    gv_.add_argument("model")
    gv_.add_argument("--taxonomy")
    sh = gs.add_parser("sheet", help="gera a folha de revisão e o modelo de decisões a partir de uma execução")
    sh.add_argument("packet", help="revision-packet.json, merged-packet.json ou diretório da execução (com rep-*)")
    sh.add_argument("--model", required=True, help="o modelo avaliado (mesma versão do pacote)")
    sh.add_argument("--out")
    ap_ = gs.add_parser("apply", help="aplica DECISÕES HUMANAS e grava a próxima versão do modelo")
    ap_.add_argument("--model", required=True)
    ap_.add_argument("--packet", required=True)
    ap_.add_argument("--decisions", required=True)
    ap_.add_argument("--out", required=True)
    ap_.add_argument("--new-version")
    ap_.add_argument("--taxonomy")
    cp_ = gs.add_parser("compare", help="compara duas execuções: o que persiste, o que sumiu, o que é novo")
    cp_.add_argument("a")
    cp_.add_argument("b")
    df_ = gs.add_parser("diff", help="diferença entre duas versões do modelo")
    df_.add_argument("a")
    df_.add_argument("b")
    g.set_defaults(func=cmd_govern)

    m = sub.add_parser("models", help="list | verify | ping")
    m.add_argument("action", choices=["list", "verify", "ping"])
    m.add_argument("--providers")
    m.add_argument("--transport", choices=["openrouter", "direct"])
    m.set_defaults(func=cmd_models)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, ScenarioError, GovernanceError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
