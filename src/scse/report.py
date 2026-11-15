"""ReportCompiler (R8 Publish): report.json + run artefacts listed in the spec."""
from __future__ import annotations

import json
from pathlib import Path

from . import legal, metrics
from .world import validate

BASE_LIMITATIONS = [
    "Conselho sintético: perspectivas geradas por modelos de linguagem a partir de fontes documentais; não representam pessoas, órgãos ou grupos reais.",
    "Contagens de apoio são resultados internos desta execução e nunca percentuais de cidadãos, eleitores ou stakeholders reais.",
    "Efeitos dos ramos contrafactuais são efeitos simulados sob suposições declaradas, não previsões.",
    "Achados de conformidade vêm do motor jurídico e se limitam ao status declarado das fontes; nenhum achado deriva de voto sintético.",
    "Fontes constam como verificationStatus=pending: o runtime não verifica vigência nem conteúdo online.",
    "Modelos compartilham vieses e corpora; dissenso e consenso podem ser artefatos do modelo.",
]


def build_tensions(engine) -> list[dict]:
    tensions = []
    for c in sorted(engine.claims.values(), key=lambda x: x.id):
        if c.visibility != "public" or c.status != "active" or c.kind not in ("thesis", "revision", "amendment"):
            continue
        counters = [x for x in c.challengedBy if engine.claims[x].status == "active"]
        if not counters:
            continue
        supporting = [c.id] + [a for a in c.amendedBy if engine.claims[a].status == "active"]
        challenger_strata = sorted({engine.claims[x].stratumId for x in counters})
        tensions.append({
            "id": f"T{len(tensions) + 1:03d}",
            "description": (f"Tese de {c.stratumId} ({c.id}) contestada por {len(counters)} assento(s) de "
                            f"{', '.join(challenger_strata)}; {len(c.supporters)} apoio(s) sintético(s)."),
            "supportingClaimIds": supporting,
            "counterClaimIds": counters,
        })
    return tensions


def _report_claim(c) -> dict:
    d = {"id": c.id, "text": c.text, "classification": c.classification, "sourceIds": c.sourceIds,
         "agentId": c.agentId, "challengedBy": list(c.challengedBy)}
    return d


def compile_run(engine, out_dir: Path, *, extra_limitations: list[str] | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    snap = engine.snapshot
    sc = snap.scenario
    tensions = build_tensions(engine)
    synthesis = engine.synthesize(tensions)
    if synthesis:
        desc = {t["id"]: t["description"] for t in synthesis.get("tensions", [])}
        for t in tensions:
            if desc.get(t["id"]):
                t["description"] = desc[t["id"]]
    findings = legal.assess(sc)
    public_active = [c for c in engine.claims.values() if c.visibility == "public" and c.status == "active"]
    sources = []
    seen = set()
    for item in snap.world.get("evidence", []) + sc.get("regulatorySources", []) + sc.get("contextSources", []):
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        sources.append({"id": item["id"], "uri": item["uri"], "verificationStatus": "pending"})
    limitations = list(BASE_LIMITATIONS)
    if snap.world.get("fictional"):
        limitations.append("Mundo fictício: indicadores marcados [FICTÍCIO] são inventados; conclusões não se transferem ao Brasil real sem validação empírica.")
    if engine.stopped_reason:
        limitations.append(f"Execução interrompida: {engine.stopped_reason}.")
    failed = [t for t in engine.turn_stats if not t["schemaValid"]]
    if failed:
        limitations.append(f"{len(failed)} turno(s) sem resposta válida (recusa, erro ou contrato JSON violado); ver deliberation-events.jsonl.")
    limitations += extra_limitations or []
    questions = list(dict.fromkeys(q["text"] for q in engine.questions))
    report = {
        "runId": engine.run_id,
        "scenarioId": sc["scenarioId"],
        "mode": sc["mode"],
        "asOfDate": sc["asOfDate"],
        "manifest": {"snapshotHash": snap.snapshot_hash,
                     "models": sorted(engine.models_used) or sorted({f"{s.provider}:{s.model}" for s in engine.roster.seats}),
                     "syntheticCouncil": True, "runSeed": engine.seed},
        "sourceInventory": sources,
        "findings": findings,
        "claims": [_report_claim(c) for c in sorted(public_active, key=lambda x: x.id)],
        "minorityOpinions": [{"claimId": m["claimId"], "rationale": m["rationale"], "sourceIds": m["sourceIds"],
                              "perspectiveAgentIds": [m["agentId"]]} for m in engine.minority
                             if len(m["rationale"]) >= 5],
        "tensions": tensions,
        "limitations": limitations,
        "unresolvedQuestions": (synthesis or {}).get("unresolvedQuestions") or questions,
        "nextActions": (synthesis or {}).get("nextActions") or [
            "Validar fontes e status normativo nas bases oficiais antes de qualquer uso.",
            "Submeter tensões e relatório minoritário a especialistas independentes com rubrica publicada.",
            "Testar hipóteses dos ramos contrafactuais com dados e pessoas reais."],
    }
    packet = None
    if sc["mode"] == "governanceReview":
        from . import governance
        packet = engine.packet()
        report["governanceReview"] = governance.report_section(packet)
        report["limitations"] += [
            "O conselho só propõe: nenhuma mudança no modelo de governança é aplicada sem decisão de pessoas (scse govern apply).",
            "As expectativas da R1 são geradas por modelos de linguagem; a matriz de cobertura mede concordância entre assentos sintéticos, não necessidade real.",
            "Traços de contexto (CF-xx) são hipóteses de trabalho ainda por verificar; achados Q3 dependem deles.",
        ]
    errors = validate(report, "report")
    if errors:
        raise ValueError("report violates report.schema.json:\n  " + "\n  ".join(errors))

    summary = metrics.run_summary(engine, tensions)
    scorecard = metrics.provider_scorecard(engine)
    manifest = {
        "runId": engine.run_id, "scenarioId": sc["scenarioId"], "snapshotHash": snap.snapshot_hash,
        "seed": engine.seed, "dryRun": engine.dry_run, "assignment": engine.roster.assignment,
        "councilMode": engine.roster.mode, "providers": engine.roster.providers,
        "seats": [{"agentId": s.agentId, "stratumId": s.stratumId, "provider": s.provider, "model": s.model,
                   "tier": s.tier, "transport": s.transport, "profile": s.profile, "mixKey": s.mixKey}
                  for s in engine.roster.seats],
        "strataMix": engine.roster.mix,
        "modelsServed": sorted(engine.models_used), "configSource": engine.config.source,
        "unverifiedModelIds": engine.config.unverified_models(engine.roster.providers, engine.transport),
        "transport": sorted({s.transport for s in engine.roster.seats}),
        "usage": {k: vars(v) for k, v in engine.usage.items()},
        "ledgerIntact": engine.ledger.verify(), "events": len(engine.ledger.events),
        "note": "Seeds não asseguram determinismo de modelos externos.",
    }
    if engine.http_trace is not None:
        manifest["openRouterHttpTrace"] = engine.http_trace.summary(relative_to=out_dir)
    claims_graph = [vars(c) for c in sorted(engine.claims.values(), key=lambda x: x.id)]
    if packet is not None:
        g = engine.snapshot.governance
        manifest["governance"] = {"modelId": g.model["modelId"], "modelVersion": g.model["version"],
                                  "contextId": g.context["contextId"], "taxonomyId": g.taxonomy["taxonomyId"],
                                  "taxonomyVersion": g.taxonomy["version"], "lenses": g.lenses,
                                  "seedTensions": g.seed_ids, "blindFirstRound": True}

    def dump(name, value):
        (out_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    dump("report.json", report)
    dump("run-manifest.json", manifest)
    dump("world-snapshot.jsonld", snap.as_document())
    dump("council-roster.json", engine.roster.to_dict())
    dump("claims.json", claims_graph)
    dump("compliance-matrix.json", findings)
    dump("tensions.json", tensions)
    dump("turn-stats.json", engine.turn_stats)
    dump("provider-scorecard.json", scorecard)
    dump("run-summary.json", summary)
    engine.ledger.write(out_dir / "deliberation-events.jsonl")
    if packet is not None:
        from . import governance
        dump("revision-packet.json", packet)
        dump("coverage-matrix.json", packet["coverageMatrix"])
        (out_dir / "review-sheet.md").write_text(governance.render_sheet(packet), encoding="utf-8")
    (out_dir / "minority-report.md").write_text(_minority_md(engine, report), encoding="utf-8")
    (out_dir / "report.md").write_text(_report_md(engine, report, summary, scorecard), encoding="utf-8")
    return {"report": report, "summary": summary, "scorecard": scorecard, "manifest": manifest, "packet": packet}


def _minority_md(engine, report) -> str:
    lines = [f"# Relatório minoritário — {report['scenarioId']} ({report['runId']})", "",
             "> Posições sintéticas minoritárias, fundamentadas e não resolvidas. Não representam grupos reais.", ""]
    if not report["minorityOpinions"]:
        lines.append("Nenhuma opinião minoritária registrada nesta execução.")
    for m in report["minorityOpinions"]:
        c = engine.claims.get(m["claimId"])
        lines += [f"## {m['claimId']} — {c.stratumId if c else '?'}", "",
                  f"**Tese:** {c.text if c else '?'}", "", f"**Dissenso:** {m['rationale']}", "",
                  f"Fontes: {', '.join(m['sourceIds']) or 'nenhuma válida'}", ""]
    return "\n".join(lines)


def _report_md(engine, report, summary, scorecard) -> str:
    lines = [f"# {report['scenarioId']} — execução {report['runId']}", "",
             f"Pergunta: {engine.snapshot.scenario['question']}", "",
             "> Resultado de simulação deliberativa sintética. Não é parecer jurídico, consulta pública nem previsão.", "",
             "## Resumo", ""]
    lines += [f"- {k}: {v}" for k, v in summary.items() if k != "tensionStratumPairs"]
    lines += ["", "## Tensões", ""]
    for t in report["tensions"]:
        lines.append(f"- **{t['id']}** {t['description']}")
    lines += ["", "## Achados do motor jurídico", ""]
    for f in report["findings"]:
        lines.append(f"- {f['requirementId']}: `{f['status']}` — {f['rationale']}")
    lines += ["", "## Comportamento por provider", "",
              "| provider | turnos | JSON válido | recusas | fundamentação | contestações/R3 | responsividade | auto-apoio |",
              "|---|---|---|---|---|---|---|---|"]
    for p, m in scorecard.items():
        lines.append(f"| {p} | {m.get('turns')} | {m.get('schemaValidRate')} | {m.get('refusalRate')} | "
                     f"{m.get('groundingRate')} | {m.get('challengesPerR3Turn')} | {m.get('responsivenessRate')} | "
                     f"{m.get('selfSupportShare')} (base {m.get('baselineShare')}) |")
    lines += ["", "## Limitações", ""] + [f"- {x}" for x in report["limitations"]]
    return "\n".join(lines) + "\n"
