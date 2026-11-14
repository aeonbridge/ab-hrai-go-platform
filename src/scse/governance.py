"""Governance-model review.

The council critiques a *versioned governance model* against the country context at a date.
It never edits the model: it produces a ``RevisionPacket`` that humans decide on, and
``apply_decisions`` turns those human decisions into the next model version.

Pipeline:  model vN  ->  council run(s)  ->  revision packet(s)  ->  merge  ->  review sheet
           ->  human decisions  ->  apply  ->  model vN+1  ->  next run  ->  compare
"""
from __future__ import annotations

import copy
import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .config import REPO_ROOT
from .world import sha256_json, validate

LENSES = ("omission", "excess", "advantage")
LENS_QUESTION = {
    "omission": "Q1. O que deveria estar sendo considerado e não está",
    "excess": "Q2. O que está sendo considerado e não deveria",
    "advantage": "Q3. Especificidades do contexto para uma vantagem competitiva distintiva",
}
CHANGES = ("add", "modify", "remove", "keep")
DECISIONS = ("accept", "reject", "modify", "defer")
LEGAL_GUARD = {"effective", "enactedNotEffective"}  # changing these needs a recorded legal review
COMPONENT_KINDS = ("principle", "institution", "instrument", "mechanism", "resource", "metric")


class GovernanceError(ValueError):
    pass


# --------------------------------------------------------------------------- loading
def _resolve(path: str | Path, base: Path | None) -> Path:
    cands = []
    p = Path(path)
    if p.is_absolute():
        cands.append(p)
    else:
        if base:
            cands.append(base / p)
        cands += [REPO_ROOT / p, REPO_ROOT / "scenarios" / p]
    for c in cands:
        if c.exists():
            return c
    raise GovernanceError(f"file not found: {path} (looked in {', '.join(map(str, cands))})")


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GovernanceError(f"{path}: invalid JSON: {exc}") from exc


def load_taxonomy(path: str | Path, base: Path | None = None) -> dict:
    data = _read(_resolve(path, base))
    ids = [t["id"] for t in data.get("topics", [])]
    if not ids:
        raise GovernanceError("taxonomy has no topics")
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise GovernanceError(f"duplicate taxonomy topics: {sorted(dup)}")
    return data


def validate_model(model: dict, taxonomy: dict | None = None) -> list[str]:
    errors = validate(model, "governance-model")
    ids = [c["id"] for c in model.get("components", [])]
    errors += [f"components: duplicate id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    retired = {r["component"]["id"] for r in model.get("retiredComponents", [])}
    errors += [f"components: id {i} is also retired" for i in sorted(set(ids) & retired)]
    if taxonomy:
        topics = {t["id"] for t in taxonomy["topics"]}
        for c in model.get("components", []):
            for t in c.get("topics", []):
                if t not in topics:
                    errors.append(f"component {c['id']}: unknown topic {t!r}")
    return errors


def load_model(path: str | Path, taxonomy: dict | None = None, base: Path | None = None) -> dict:
    model = _read(_resolve(path, base))
    errors = validate_model(model, taxonomy)
    if errors:
        raise GovernanceError("governance model violations:\n  " + "\n  ".join(errors))
    return model


def _check_context(ctx: dict, where: str) -> dict:
    for key in ("contextId", "validFrom", "facts", "features"):
        if key not in ctx:
            raise GovernanceError(f"{where}: context snapshot missing {key!r}")
    ids = [x["id"] for k in ("evidence", "facts", "features") for x in ctx.get(k, [])]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise GovernanceError(f"{where}: duplicate ids in context: {sorted(dup)}")
    return ctx


def load_context(path: str | Path, as_of: str, base: Path | None = None) -> dict:
    """Context at the round date. A directory holds dated snapshots; the latest with
    validFrom <= asOfDate is used. Fails closed when none applies (no anachronistic context)."""
    p = _resolve(path, base)
    files = sorted(p.glob("*.json")) if p.is_dir() else [p]
    best = None
    for f in files:
        ctx = _check_context(_read(f), str(f))
        if ctx["validFrom"] <= as_of and (best is None or ctx["validFrom"] > best["validFrom"]):
            best = ctx
    if best is None:
        raise GovernanceError(f"no context snapshot valid on {as_of} in {p}")
    return best


@dataclass
class GovernanceBundle:
    model: dict
    taxonomy: dict
    context: dict
    seeds: list[dict]
    lenses: list[str]

    @property
    def topic_ids(self) -> list[str]:
        return [t["id"] for t in self.taxonomy["topics"]]

    @property
    def component_ids(self) -> list[str]:
        return [c["id"] for c in self.model["components"]]

    @property
    def feature_ids(self) -> list[str]:
        return [f["id"] for f in self.context.get("features", [])]

    @property
    def seed_ids(self) -> list[str]:
        return [s["id"] for s in self.seeds]

    def component(self, cid: str) -> dict | None:
        return next((c for c in self.model["components"] if c["id"] == cid), None)

    def citable(self) -> dict[str, dict]:
        """Everything a seat may cite in sourceIds, with a short excerpt for the verifier."""
        out: dict[str, dict] = {}
        for e in self.context.get("evidence", []):
            out[e["id"]] = {"title": e["title"], "excerpt": e.get("excerpt", ""), "kind": "evidence", "uri": e.get("uri")}
        for f in self.context.get("facts", []):
            out[f["id"]] = {"title": f["title"], "excerpt": f["text"], "kind": "fact"}
        for f in self.context.get("features", []):
            out[f["id"]] = {"title": f["title"], "excerpt": f["description"], "kind": f"feature:{f['kind']}"}
        for c in self.model["components"]:
            out[c["id"]] = {"title": c["title"], "excerpt": c["description"], "kind": "component"}
        return out

    def digest(self) -> dict:
        return {"model": self.model, "taxonomy": self.taxonomy, "context": self.context,
                "seeds": self.seeds, "lenses": self.lenses}


def load_bundle(scenario: dict, scenario_path: Path | None) -> GovernanceBundle:
    g = scenario["governance"]
    base = scenario_path.parent if scenario_path else None
    as_of = scenario["asOfDate"]
    taxonomy = load_taxonomy(g["taxonomyPath"], base)
    model = load_model(g["modelPath"], taxonomy, base)
    if model["effectiveAsOf"] > as_of:
        raise GovernanceError(f"model {model['modelId']} v{model['version']} is dated {model['effectiveAsOf']}, "
                              f"after the round date {as_of} (anachronism)")
    context = load_context(g["contextPath"], as_of, base)
    seeds = g.get("seedTensions", [])
    ids = [s["id"] for s in seeds]
    if len(ids) != len(set(ids)):
        raise GovernanceError("seedTensions: duplicate ids")
    comps = {c["id"] for c in model["components"]}
    for s in seeds:
        for cid in s.get("componentIds", []):
            if cid not in comps:
                raise GovernanceError(f"seedTensions {s['id']}: unknown component {cid}")
    return GovernanceBundle(model=model, taxonomy=taxonomy, context=context, seeds=seeds,
                            lenses=list(g.get("lenses") or LENSES))


# ------------------------------------------------------------------- coverage matrix
def coverage_matrix(model: dict, taxonomy: dict, expectations: dict[str, dict]) -> list[dict]:
    """Expected topics (blind council round) vs. topics the model covers, computed in code.

    strength: documentedInForce | documentedProposedOnly | inferredOnly | none.
    gap = expected by someone and nothing covers it; fragile = covered only by a bill or by
    topic tags that are the model author's reading.
    """
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for c in model["components"]:
        for t in c["topics"]:
            by_topic[t].append(c)
    rows = []
    for topic in taxonomy["topics"]:
        comps = by_topic.get(topic["id"], [])
        exp = expectations.get(topic["id"], {})
        cov = [{"componentId": c["id"], "legalStatus": c["legalStatus"], "basis": c.get("topicsBasis", "inferred")}
               for c in comps]
        documented = [x for x in cov if x["basis"] == "documented"]
        if not comps:
            strength = "none"
        elif any(x["legalStatus"] in ("effective", "policy") for x in documented):
            strength = "documentedInForce"
        elif documented:
            strength = "documentedProposedOnly"
        else:
            strength = "inferredOnly"
        n_seats = len(exp.get("seats", ()))
        rows.append({"topic": topic["id"], "label": topic["label"], "expectedBySeats": n_seats,
                     "expectedByStrata": sorted(exp.get("strata", ())), "coveredBy": cov,
                     "coverageStrength": strength,
                     "gap": bool(n_seats) and strength == "none",
                     "fragile": bool(n_seats) and strength in ("documentedProposedOnly", "inferredOnly")})
    other = expectations.get("other")
    if other:
        rows.append({"topic": "other", "label": "Fora da taxonomia", "expectedBySeats": len(other["seats"]),
                     "expectedByStrata": sorted(other["strata"]), "coveredBy": [], "coverageStrength": "none",
                     "gap": True, "fragile": False, "titles": sorted(other.get("titles", ()))})
    return rows


# --------------------------------------------------------------------- revision packet
def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return "-".join(re.findall(r"[a-z0-9]+", t)[:6])


def proposal_key(p: dict) -> str:
    anchor = p.get("componentId") or (p.get("topic") if p.get("topic") not in (None, "none", "other") else None)
    anchor = anchor or f"other:{_norm(p.get('title') or p.get('text', ''))}"
    return f"{p['lens']}|{p['change']}|{anchor}"


def build_packet(engine) -> dict:
    """Revision packet from one finished run (engine is a GovernanceEngine)."""
    b: GovernanceBundle = engine.snapshot.governance
    sc = engine.snapshot.scenario
    seat_info = {s.agentId: s for s in engine.roster.seats}
    claims = engine.claims
    findings = [c for c in claims.values()
                if c.visibility == "public" and c.lens in LENSES and c.kind in ("thesis", "revision")
                and c.status == "active" and c.branchId is None]
    proposals = []
    for c in sorted(findings, key=lambda x: x.id):
        authors = {c.agentId, *c.supporters}
        challengers = [claims[x] for x in c.challengedBy if claims[x].status == "active"]
        amendments = [claims[x] for x in c.amendedBy if claims[x].status == "active"]
        branch_notes = [claims[x] for x in claims
                        if claims[x].targetClaimId == c.id and claims[x].branchId and claims[x].status == "active"]
        comp = b.component(c.componentId) if c.componentId else None
        guard = bool(comp and comp["legalStatus"] in LEGAL_GUARD and c.change in ("remove", "modify"))
        best = amendments[-1] if amendments else None
        proposals.append({
            "proposalId": f"P{len(proposals) + 1:03d}", "claimId": c.id, "lens": c.lens, "change": c.change,
            "componentId": c.componentId, "componentTitle": comp["title"] if comp else None,
            "topic": c.topic, "title": c.title or (best.title if best else None) or c.text[:80],
            "text": c.text,
            "proposedTitle": (best.title if best and best.title else c.title),
            "proposedDescription": best.text if best else c.text,
            "sourceIds": c.sourceIds, "invalidSourceIds": c.invalidSourceIds,
            "contextFeatureIds": c.contextFeatureIds, "tensionIds": c.tensionIds,
            "classification": c.classification, "confidence": c.confidence,
            "author": {"agentId": c.agentId, "stratumId": c.stratumId, "provider": c.provider},
            "support": {"seats": len(authors), "strata": sorted({seat_info[a].stratumId for a in authors if a in seat_info}),
                        "providers": sorted({seat_info[a].provider for a in authors if a in seat_info})},
            "challenges": [{"claimId": x.id, "stratumId": x.stratumId, "text": x.text} for x in challengers],
            "amendments": [{"claimId": x.id, "stratumId": x.stratumId, "change": x.change, "componentId": x.componentId,
                            "title": x.title, "text": x.text} for x in amendments],
            "branchAssessments": [{"branchId": x.branchId, "claimId": x.id, "text": x.text} for x in branch_notes],
            "criticVerdict": c.criticVerdict, "genericity": c.genericity,
            "weakEvidence": bool(c.invalidSourceIds) or c.insufficientGrounding,
            "minorityOpinion": any(m["claimId"] == c.id for m in engine.minority),
            "requiresLegalReview": guard,
            "decision": None})
    expectations = engine.expectations()
    matrix = coverage_matrix(b.model, b.taxonomy, expectations)
    seeds = []
    exp_by_seed: dict[str, set] = defaultdict(set)
    for c in claims.values():
        if c.lens == "expectation":
            for t in c.tensionIds:
                exp_by_seed[t].add(c.agentId)
    for s in b.seeds:
        refs = [p for p in proposals if s["id"] in p["tensionIds"]]
        exp = len(exp_by_seed[s["id"]])
        seeds.append({"id": s["id"], "title": s["title"], "findings": len(refs), "expectationSeats": exp,
                      "challengedFindings": sum(1 for p in refs if p["challenges"]),
                      "status": "addressed" if refs else ("expectedOnly" if exp else "unaddressed")})
    return {
        "packetId": f"{engine.run_id}:packet", "kind": "revisionPacket", "status": "pendingHumanReview",
        "runIds": [engine.run_id], "scenarioId": sc["scenarioId"], "asOfDate": sc["asOfDate"],
        "modelId": b.model["modelId"], "modelVersion": b.model["version"], "contextId": b.context["contextId"],
        "councilNature": "synthetic",
        "notice": ("Propostas de um conselho sintético, a decidir por pessoas. O apoio de assentos sintéticos é "
                   "procedência do argumento, não voto, e não substitui evidência nem revisão jurídica."),
        "coverageMatrix": matrix, "seedTensions": seeds, "proposals": proposals,
        "minorityOpinions": [{"claimId": m["claimId"], "agentId": m["agentId"], "rationale": m["rationale"]}
                             for m in engine.minority],
    }


def report_section(packet: dict) -> dict:
    lenses = {l: [p["claimId"] for p in packet["proposals"] if p["lens"] == l] for l in LENSES}
    topics_expected = sum(1 for r in packet["coverageMatrix"] if r["expectedBySeats"])
    return {"modelId": packet["modelId"], "modelVersion": packet["modelVersion"], "contextId": packet["contextId"],
            "asOfDate": packet["asOfDate"], "status": "pendingHumanReview", "lenses": lenses,
            "coverage": {"topicsExpected": topics_expected,
                         "gaps": [r["topic"] for r in packet["coverageMatrix"] if r["gap"]],
                         "fragile": [r["topic"] for r in packet["coverageMatrix"] if r["fragile"]]},
            "seedTensions": [{"id": s["id"], "findings": s["findings"]} for s in packet["seedTensions"]],
            "proposalCount": len(packet["proposals"]), "packetFile": "revision-packet.json"}


# ------------------------------------------------------------------------- merge
def load_packets(path: str | Path) -> list[dict]:
    p = Path(path)
    if p.is_file():
        return [json.loads(p.read_text(encoding="utf-8"))]
    found = sorted(p.glob("rep-*/revision-packet.json")) or sorted(p.glob("revision-packet.json"))
    if not found:
        raise GovernanceError(f"no revision-packet.json under {p}")
    return [json.loads(f.read_text(encoding="utf-8")) for f in found]


def merge_packets(packets: list[dict]) -> dict:
    """Merge replicate packets. A proposal that recurs in more replicates is more robust to
    seed, model mix and speaking order; that, not seat count, is the main filter for reviewers."""
    if not packets:
        raise GovernanceError("nothing to merge")
    ident = {(p["modelId"], p["modelVersion"], p["scenarioId"], p["contextId"]) for p in packets}
    if len(ident) != 1:
        raise GovernanceError("packets come from different models, versions or scenarios; refusing to merge")
    n = len(packets)
    groups: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for i, pk in enumerate(packets, 1):
        for prop in pk["proposals"]:
            groups[proposal_key(prop)].append((i, prop))
    merged = []
    for key, items in groups.items():
        rep = max(items, key=lambda it: (it[1]["support"]["seats"], len(it[1]["amendments"])))[1]
        m = copy.deepcopy(rep)
        reps = sorted({i for i, _ in items})
        m.update({"key": key, "replicates": reps, "replicateCount": len(reps), "of": n,
                  "supportSeatsByReplicate": {str(i): p["support"]["seats"] for i, p in items},
                  "strataUnion": sorted({s for _, p in items for s in p["support"]["strata"]}),
                  "challengesTotal": sum(len(p["challenges"]) for _, p in items),
                  "changeVariants": sorted({p["change"] for _, p in items}),
                  "sourceClaims": [f"{packets[i - 1]['runIds'][0]}:{p['claimId']}" for i, p in items],
                  "requiresLegalReview": any(p["requiresLegalReview"] for _, p in items),
                  "weakEvidence": all(p["weakEvidence"] for _, p in items)})
        merged.append(m)
    merged.sort(key=lambda m: (-m["replicateCount"], -m["support"]["seats"], m["key"]))
    for i, m in enumerate(merged, 1):
        m["proposalId"] = f"M{i:03d}"
    cov: dict[str, dict] = {}
    for pk in packets:
        for r in pk["coverageMatrix"]:
            c = cov.setdefault(r["topic"], {**r, "gapInReplicates": 0, "expectedInReplicates": 0, "seatsMax": 0})
            c["gapInReplicates"] += int(r["gap"])
            c["expectedInReplicates"] += int(r["expectedBySeats"] > 0)
            c["seatsMax"] = max(c["seatsMax"], r["expectedBySeats"])
            c["expectedByStrata"] = sorted(set(c["expectedByStrata"]) | set(r["expectedByStrata"]))
    for c in cov.values():
        c["gap"] = c["gapInReplicates"] > 0
        c["fragile"] = c["fragile"] or False
    seeds: dict[str, dict] = {}
    for pk in packets:
        for s in pk["seedTensions"]:
            x = seeds.setdefault(s["id"], {"id": s["id"], "title": s["title"], "findingsByReplicate": [],
                                           "expectationSeatsByReplicate": []})
            x["findingsByReplicate"].append(s["findings"])
            x["expectationSeatsByReplicate"].append(s.get("expectationSeats", 0))
    first = packets[0]
    return {"packetId": "merge:" + sha256_json([p["packetId"] for p in packets])[:12], "kind": "revisionPacket",
            "merged": True, "status": "pendingHumanReview", "runIds": [r for p in packets for r in p["runIds"]],
            "replicates": n, "scenarioId": first["scenarioId"], "asOfDate": first["asOfDate"],
            "modelId": first["modelId"], "modelVersion": first["modelVersion"], "contextId": first["contextId"],
            "councilNature": "synthetic", "notice": first["notice"],
            "coverageMatrix": list(cov.values()), "seedTensions": list(seeds.values()),
            "proposals": merged, "minorityOpinions": [m for p in packets for m in p["minorityOpinions"]]}


# ---------------------------------------------------------------------- review sheet
def render_sheet(packet: dict) -> str:
    n = packet.get("replicates", 1)
    L = [f"# Folha de revisão: {packet['modelId']} v{packet['modelVersion']}", "",
         f"Cenário {packet['scenarioId']} · contexto `{packet['contextId']}` · data da rodada {packet['asOfDate']} · "
         f"{n} réplica(s)", "",
         f"> {packet['notice']}", "",
         "## Como decidir", "",
         "- Cada proposta pede uma decisão humana: `accept`, `modify`, `reject` ou `defer`, com justificativa de pelo menos 20 caracteres para as duas primeiras.",
         "- **Réplicas** mostra em quantas execuções a proposta apareceu. Proposta que aparece em uma só pode ser ruído do modelo.",
         "- **Evidência fraca** e **Revisão jurídica** exigem atenção antes de aceitar.",
         "- Ninguém altera o modelo além de você: `scse govern apply` só aplica o que estiver decidido no arquivo de decisões.", ""]
    gaps = [r for r in packet["coverageMatrix"] if r.get("gap") or r.get("fragile")]
    L += ["## Cobertura de tópicos esperados", ""]
    if gaps:
        L += ["| Tópico | Esperado por | Cobertura | Situação |", "|---|---|---|---|"]
        for r in gaps:
            seats = r.get("seatsMax", r["expectedBySeats"])
            state = "lacuna" if r["gap"] else "frágil"
            if n > 1 and r.get("gapInReplicates") is not None:
                state += f" ({r['gapInReplicates']}/{n} réplicas)" if r["gap"] else ""
            L.append(f"| {r['label']} (`{r['topic']}`) | {seats} assento(s) · {', '.join(r['expectedByStrata']) or '-'} | "
                     f"{r['coverageStrength']} | {state} |")
    else:
        L.append("Nenhum tópico esperado ficou sem cobertura.")
    L += ["", "## Tensões iniciais", ""]
    for s in packet["seedTensions"]:
        found = s.get("findings", s.get("findingsByReplicate"))
        exp = s.get("expectationSeats", s.get("expectationSeatsByReplicate"))
        L.append(f"- **{s['id']}** {s['title']}: achados {found} · assentos que a citaram na R1 {exp}")
    for lens in LENSES:
        props = [p for p in packet["proposals"] if p["lens"] == lens]
        L += ["", f"## {LENS_QUESTION[lens]} ({len(props)})", ""]
        for p in props:
            tag = []
            if p.get("replicateCount"):
                tag.append(f"réplicas {p['replicateCount']}/{p['of']}")
            tag.append(f"{p['support']['seats']} assento(s) sintético(s)")
            if p["weakEvidence"]:
                tag.append("evidência fraca")
            if p["requiresLegalReview"]:
                tag.append("REVISÃO JURÍDICA")
            if p.get("minorityOpinion"):
                tag.append("dissenso registrado")
            if p.get("genericity") == "generic":
                tag.append("genérica: serviria a qualquer país")
            target = p["componentId"] or p["topic"] or "-"
            if p.get("componentTitle"):
                target += f" ({p['componentTitle']})"
            L += [f"### {p['proposalId']} · {p['change']} · {target}", "",
                  f"**{p.get('proposedTitle') or p['title']}**", "", p.get("proposedDescription") or p["text"], "",
                  f"- Sinais: {'; '.join(tag)}",
                  f"- Estratos: {', '.join(p.get('strataUnion') or p['support']['strata'])}",
                  f"- Fontes: {', '.join(p['sourceIds']) or 'nenhuma válida'}"
                  + (f" · traços de contexto: {', '.join(p['contextFeatureIds'])}" if p["contextFeatureIds"] else "")
                  + (f" · tensões: {', '.join(p['tensionIds'])}" if p["tensionIds"] else "")]
            for ch in p["challenges"][:3]:
                L.append(f"- Contestação ({ch['stratumId']}): {ch['text'][:300]}")
            for br in p["branchAssessments"][:4]:
                L.append(f"- Sob `{br['branchId']}`: {br['text'][:240]}")
            L += ["", "Decisão: [ ] accept   [ ] modify   [ ] reject   [ ] defer", ""]
    if packet["minorityOpinions"]:
        L += ["## Dissenso registrado", ""]
        L += [f"- {m['claimId']}: {m['rationale'][:300]}" for m in packet["minorityOpinions"]]
    return "\n".join(L) + "\n"


def decisions_template(packet: dict, model: dict) -> dict:
    return {
        "packetId": packet["packetId"], "modelId": model["modelId"], "baseVersion": model["version"],
        "reviewers": [], "decidedOn": None,
        "instructions": ("Preencha `reviewers` com o nome de quem decide. Para cada proposta, `decision` = accept | modify | reject | defer. "
                         "`rationale` tem 20 ou mais caracteres para accept e modify. Em `modify`, `edited` traz os campos corrigidos "
                         "(title, description, topics, kind, componentId, change, newComponentId). Propostas com requiresLegalReview exigem "
                         "`legalReview: {reviewer, note}`. Propostas sem decisão (null) ficam pendentes."),
        "decisions": [{"proposalId": p["proposalId"], "lens": p["lens"], "change": p["change"],
                       "componentId": p["componentId"], "title": p.get("proposedTitle") or p["title"],
                       "requiresLegalReview": p["requiresLegalReview"],
                       "decision": None, "rationale": "", "edited": {}, "legalReview": None}
                      for p in packet["proposals"]]}


# ------------------------------------------------------------------- apply decisions
def _bump(version: str) -> str:
    a, b, c = (int(x) for x in version.split("."))
    return f"{a}.{b + 1}.0"


def _next_id(model: dict, prefix: str = "GM-") -> str:
    used = {c["id"] for c in model["components"]} | {r["component"]["id"] for r in model.get("retiredComponents", [])}
    nums = [int(m.group(1)) for i in used if (m := re.fullmatch(re.escape(prefix) + r"(\d+)", i))]
    return f"{prefix}{(max(nums) + 1 if nums else 1):02d}"


def apply_decisions(model: dict, packet: dict, decisions: dict, *, new_version: str | None = None,
                    taxonomy: dict | None = None) -> tuple[dict, dict]:
    """Apply human decisions to ``model`` and return (new_model, log). Nothing is applied that a
    named human did not decide, and every applied change is written to model.history."""
    reviewers = [str(r).strip() for r in decisions.get("reviewers") or [] if str(r).strip()]
    if not reviewers:
        raise GovernanceError("at least one named human reviewer is required in decisions.reviewers")
    if decisions.get("packetId") != packet["packetId"]:
        raise GovernanceError("decisions refer to a different packet")
    if decisions.get("modelId") != model["modelId"] or decisions.get("baseVersion") != model["version"]:
        raise GovernanceError(f"decisions were made on {decisions.get('modelId')} v{decisions.get('baseVersion')}, "
                              f"not on {model['modelId']} v{model['version']}")
    props = {p["proposalId"]: p for p in packet["proposals"]}
    decided_on = decisions.get("decidedOn") or packet["asOfDate"]
    date.fromisoformat(decided_on)
    version = new_version or _bump(model["version"])
    new = copy.deepcopy(model)
    comps = {c["id"]: c for c in new["components"]}
    changes, pending, skipped = [], [], []
    seen = set()
    for d in decisions.get("decisions", []):
        pid = d.get("proposalId")
        if pid not in props:
            raise GovernanceError(f"unknown proposal {pid!r}")
        if pid in seen:
            raise GovernanceError(f"proposal {pid} decided twice")
        seen.add(pid)
        dec = d.get("decision")
        if dec is None:
            pending.append(pid)
            continue
        if dec not in DECISIONS:
            raise GovernanceError(f"{pid}: decision must be one of {DECISIONS}")
        rationale = (d.get("rationale") or "").strip()
        p = props[pid]
        entry = {"proposalId": pid, "decision": dec, "rationale": rationale, "op": "none",
                 "componentId": p["componentId"], "legalReview": d.get("legalReview")}
        if dec in ("reject", "defer"):
            skipped.append(entry)
            changes.append(entry)
            continue
        if len(rationale) < 20:
            raise GovernanceError(f"{pid}: a rationale of at least 20 characters is required to {dec}")
        edited = d.get("edited") or {}
        if dec == "modify" and not edited:
            raise GovernanceError(f"{pid}: 'modify' needs the corrected fields in 'edited'")
        if p["requiresLegalReview"]:
            lr = d.get("legalReview") or {}
            if not (str(lr.get("reviewer", "")).strip() and str(lr.get("note", "")).strip()):
                raise GovernanceError(f"{pid}: touches a component in force; record legalReview {{reviewer, note}}")
        op = edited.get("change", p["change"])
        cid = edited.get("componentId", p["componentId"])
        if op not in CHANGES:
            raise GovernanceError(f"{pid}: change must be one of {CHANGES}")
        entry.update({"op": op, "componentId": cid})
        if op == "add":
            title = edited.get("title") or p.get("proposedTitle") or p.get("title")
            desc = edited.get("description") or p.get("proposedDescription")
            topics = edited.get("topics") or ([p["topic"]] if p.get("topic") not in (None, "none", "other") else None)
            if not (title and desc and topics):
                raise GovernanceError(f"{pid}: 'add' needs title, description and topics (supply them in 'edited')")
            kind = edited.get("kind", "mechanism")
            if kind not in COMPONENT_KINDS:
                raise GovernanceError(f"{pid}: kind must be one of {COMPONENT_KINDS}")
            new_id = edited.get("newComponentId") or _next_id(new)
            if new_id in comps:
                raise GovernanceError(f"{pid}: component id {new_id} already exists")
            comp = {"id": new_id, "kind": kind, "title": title, "description": desc, "topics": list(topics),
                    "topicsBasis": "inferred", "legalStatus": "policy",
                    "sourceIds": list(p["sourceIds"]), "verification": "pending", "origin": "councilProposed",
                    "notes": f"Adicionado por decisão humana na v{version} (proposta {pid}); ainda não adotado em norma."}
            new["components"].append(comp)
            comps[new_id] = comp
            entry["componentId"] = new_id
        elif op in ("modify", "remove", "keep"):
            if cid not in comps:
                raise GovernanceError(f"{pid}: component {cid!r} is not in the model")
            if op == "modify":
                fields = {k: edited[k] for k in ("title", "description", "topics", "kind") if k in edited}
                if not fields and p.get("proposedDescription") and dec == "accept":
                    fields = {"description": p["proposedDescription"]}
                if not fields:
                    raise GovernanceError(f"{pid}: 'modify' has no field to change")
                if "kind" in fields and fields["kind"] not in COMPONENT_KINDS:
                    raise GovernanceError(f"{pid}: invalid kind")
                comps[cid].update(fields)
                comps[cid]["verification"] = "pending"      # edited text is no longer what the source said
                comps[cid]["origin"] = "humanAuthored"
            elif op == "remove":
                new.setdefault("retiredComponents", []).append(
                    {"component": comps.pop(cid), "retiredInVersion": version, "reason": rationale, "proposalId": pid})
                new["components"] = [c for c in new["components"] if c["id"] != cid]
        changes.append(entry)
    if taxonomy:
        unknown = {t for c in new["components"] for t in c["topics"]} - {t["id"] for t in taxonomy["topics"]}
        if unknown:
            raise GovernanceError(f"unknown topics after revision: {sorted(unknown)}")
    new["version"] = version
    new["effectiveAsOf"] = decided_on
    new["status"] = "draft"
    applied = [c for c in changes if c["decision"] in ("accept", "modify") and c["op"] not in ("none",)]
    new.setdefault("history", []).append({
        "version": version, "fromVersion": model["version"], "date": decided_on, "reviewers": reviewers,
        "packetId": packet["packetId"], "runIds": packet["runIds"],
        "changes": [{"op": c["op"], "componentId": c["componentId"], "proposalId": c["proposalId"],
                     "decision": c["decision"], "rationale": c["rationale"], "legalReview": c["legalReview"]}
                    for c in changes],
        "note": f"{len(applied)} mudança(s) aplicada(s); {len(skipped)} rejeitada(s) ou adiada(s); {len(pending)} pendente(s)."})
    errors = validate_model(new, taxonomy)
    if errors:
        raise GovernanceError("revised model is invalid:\n  " + "\n  ".join(errors))
    return new, {"fromVersion": model["version"], "toVersion": version, "applied": applied,
                 "notApplied": skipped, "pending": pending, "reviewers": reviewers}


def diff_models(a: dict, b: dict) -> dict:
    ca = {c["id"]: c for c in a["components"]}
    cb = {c["id"]: c for c in b["components"]}
    modified = {}
    for cid in ca.keys() & cb.keys():
        ch = {k: [ca[cid].get(k), cb[cid].get(k)] for k in set(ca[cid]) | set(cb[cid])
              if ca[cid].get(k) != cb[cid].get(k)}
        if ch:
            modified[cid] = ch
    return {"from": a["version"], "to": b["version"], "added": sorted(cb.keys() - ca.keys()),
            "removed": sorted(ca.keys() - cb.keys()), "modified": modified}


def compare_packets(a: dict, b: dict) -> dict:
    """What the council still says after a revision: persisted / resolved / new proposals and gaps."""
    ka = {proposal_key(p): p for p in a["proposals"]}
    kb = {proposal_key(p): p for p in b["proposals"]}
    gaps_a = {r["topic"] for r in a["coverageMatrix"] if r.get("gap")}
    gaps_b = {r["topic"] for r in b["coverageMatrix"] if r.get("gap")}
    brief = lambda p: {"proposalId": p["proposalId"], "lens": p["lens"], "change": p["change"],
                       "target": p.get("componentId") or p.get("topic"), "title": p.get("proposedTitle") or p["title"]}
    return {"from": f"{a['modelId']} v{a['modelVersion']}", "to": f"{b['modelId']} v{b['modelVersion']}",
            "persisting": [brief(kb[k]) for k in ka.keys() & kb.keys()],
            "resolved": [brief(ka[k]) for k in ka.keys() - kb.keys()],
            "new": [brief(kb[k]) for k in kb.keys() - ka.keys()],
            "gapsClosed": sorted(gaps_a - gaps_b), "gapsOpened": sorted(gaps_b - gaps_a),
            "gapsPersisting": sorted(gaps_a & gaps_b),
            "caveat": ("'Resolvida' significa que o conselho deixou de levantar o ponto nesta execução, não que o problema "
                       "esteja resolvido. Replicar antes de concluir.")}
