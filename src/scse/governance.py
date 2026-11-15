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


NOTICE = ("Propostas levantadas por assentos de um conselho sintético, a decidir por pessoas. O conselho não "
          "delibera uma resposta única: cada proposta traz a posição de cada estrato, inclusive os que contestaram "
          "ou ficaram calados. Apoio de assentos é procedência do argumento, não voto, e não substitui evidência "
          "nem revisão jurídica.")


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
    files = sorted(f for f in p.glob("*.json") if not f.name.startswith(".")) if p.is_dir() else [p]
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


# ------------------------------------------------------------- stratum positions
# The council does not vote and does not reach a collective answer. Each proposal is shown with
# where every stratum stood on it (for / against / amend / split / silent), in its own words,
# so reviewers see the disagreement instead of a seat count that reads like a verdict.
STANCES = ("for", "against", "amend", "split", "silent", "notSeated")
STANCE_LABEL = {"for": "a favor", "against": "contra", "amend": "propõe ajuste", "split": "dividido",
                "silent": "sem posição", "notSeated": "sem assento", "variesAcrossReplicates": "varia entre réplicas"}
ROUND_ORDER = {f"R{i}": i for i in range(9)}


def strata_meta(engine) -> list[dict]:
    """Every stratum the world pack defines, plus any stratum that only appears on a seat."""
    seats_by: dict[str, list] = defaultdict(list)
    for s in engine.roster.seats:
        seats_by[s.stratumId].append(s)
    meta, seen = [], set()
    for st in engine.snapshot.world.get("strata", []):
        seen.add(st["id"])
        meta.append({"stratumId": st["id"], "label": st.get("label") or st.get("name") or st["id"],
                     "seats": [s.agentId for s in seats_by.get(st["id"], [])],
                     "providers": sorted({s.provider for s in seats_by.get(st["id"], [])})})
    for sid, seats in seats_by.items():
        if sid not in seen:
            meta.append({"stratumId": sid, "label": sid, "seats": [s.agentId for s in seats],
                         "providers": sorted({s.provider for s in seats})})
    return meta


def _lineage(claims: dict, c) -> list:
    """The claim and the earlier versions it revised (newest first)."""
    out, cur = [c], c
    while cur.kind == "revision" and cur.targetClaimId in claims:
        cur = claims[cur.targetClaimId]
        out.append(cur)
    return out


def _statements(engine, c) -> list[dict]:
    """Every public statement any seat made about this finding, in deliberation order."""
    claims = engine.claims
    seat_info = {s.agentId: s for s in engine.roster.seats}
    out = []

    def add(agent, stratum, stance, rnd, text, claim_id=None, earlier=False, **extra):
        seat = seat_info.get(agent)
        out.append({"agentId": agent, "stratumId": stratum, "provider": seat.provider if seat else None,
                    "stance": stance, "roundId": rnd, "claimId": claim_id, "text": text,
                    "onEarlierVersion": earlier, **extra})

    for depth, v in enumerate(_lineage(claims, c)):
        earlier = depth > 0
        add(v.agentId, v.stratumId, "for", v.roundId, v.text, v.id, earlier, role="author")
        for n in v.supportNotes:
            add(n["agentId"], n["stratumId"], "for", n["roundId"], n["text"], None, earlier, role="support")
        for n in v.supporters:  # supports recorded before supportNotes existed
            if not any(x["agentId"] == n for x in v.supportNotes) and n in seat_info:
                add(n, seat_info[n].stratumId, "for", v.roundId, "", None, earlier, role="support")
        for x in v.challengedBy:
            ch = claims[x]
            if ch.status != "withdrawn":
                add(ch.agentId, ch.stratumId, "against", ch.roundId, ch.text, ch.id, earlier, role="challenge")
        for x in v.amendedBy:
            am = claims[x]
            if am.status == "active":
                add(am.agentId, am.stratumId, "amend", am.roundId, am.text, am.id, earlier, role="amendment",
                    change=am.change, componentId=am.componentId)
    ids = {v.id for v in _lineage(claims, c)}
    for m in engine.minority:
        if m["claimId"] in ids:
            prior = [s for s in out if s["agentId"] == m["agentId"]]
            stance = prior[-1]["stance"] if prior else "against"
            add(m["agentId"], m.get("stratumId") or getattr(seat_info.get(m["agentId"]), "stratumId", "?"),
                stance, m.get("roundId", "R7"), m["rationale"], None, False, role="minorityOpinion")
    out.sort(key=lambda s: (ROUND_ORDER.get(s["roundId"], 99), s["onEarlierVersion"] is False))
    return out


def stratum_positions(meta: list[dict], statements: list[dict]) -> list[dict]:
    """One row per stratum. A seat's stance is its latest statement; a stratum is 'split' when its
    seats disagree and 'silent' when none of its seats said anything about the finding."""
    rows = []
    for st in meta:
        mine = [s for s in statements if s["stratumId"] == st["stratumId"]]
        last: dict[str, str] = {}
        for s in mine:
            last[s["agentId"]] = s["stance"]
        stances = set(last.values())
        if not st["seats"]:
            stance = "notSeated"
        elif not stances:
            stance = "silent"
        elif len(stances) == 1:
            stance = stances.pop()
        else:
            stance = "split"
        rows.append({"stratumId": st["stratumId"], "label": st["label"], "stance": stance,
                     "seatsTotal": len(st["seats"]), "seatsSpoke": len(last),
                     "seatStances": dict(sorted(last.items())),
                     "statements": [{k: s[k] for k in ("agentId", "provider", "stance", "role", "roundId",
                                                       "claimId", "text", "onEarlierVersion") if k in s}
                                    for s in mine]})
    return rows


def position_spread(rows: list[dict]) -> dict:
    spread = {k: [] for k in ("for", "against", "amend", "split", "silent", "notSeated", "variesAcrossReplicates")}
    for r in rows:
        spread.setdefault(r["stance"], []).append(r["stratumId"])
    spread = {k: v for k, v in spread.items() if v}
    spoke = [r for r in rows if r["stance"] not in ("silent", "notSeated")]
    spread["contested"] = bool(spread.get("against") or spread.get("split"))
    spread["onlyAuthorStratum"] = len(spoke) == 1 and spoke[0]["stance"] == "for"
    return spread


def strata_perspectives(meta: list[dict], proposals: list[dict], expectations: dict[str, list[dict]],
                        minority: list[dict]) -> list[dict]:
    """Per-stratum reading of the whole round: what it expected blind (R1), what it raised, what it
    backed, contested or wanted changed, and where it stood alone. No synthesis across strata."""
    out = []
    for st in meta:
        sid = st["stratumId"]
        pos = {k: [] for k in ("for", "against", "amend", "split", "silent", "variesAcrossReplicates")}
        alone_for, alone_against, authored = [], [], []
        for p in proposals:
            row = next((r for r in p.get("stratumPositions", []) if r["stratumId"] == sid), None)
            if row is None or row["stance"] == "notSeated":
                continue
            pos.setdefault(row["stance"], []).append(p["proposalId"])
            if p["author"]["stratumId"] == sid:
                authored.append(p["proposalId"])
            others = [r for r in p["stratumPositions"] if r["stratumId"] != sid]
            if row["stance"] == "for" and not any(r["stance"] == "for" for r in others):
                alone_for.append(p["proposalId"])
            if row["stance"] == "against" and not any(r["stance"] == "against" for r in others):
                alone_against.append(p["proposalId"])
        out.append({"stratumId": sid, "label": st["label"], "seats": len(st["seats"]),
                    "providers": st.get("providers", []),
                    "blindExpectations": expectations.get(sid, []),
                    "authored": authored,
                    "positions": {k: v for k, v in pos.items() if v},
                    "aloneFor": alone_for, "aloneAgainst": alone_against,
                    "minorityOpinions": [{"claimId": m["claimId"], "rationale": m["rationale"]}
                                         for m in minority if m.get("stratumId") == sid]})
    return out


def _blind_expectations(engine) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for c in sorted(engine.claims.values(), key=lambda x: x.id):
        if c.lens == "expectation" and c.status != "withdrawn":
            out[c.stratumId].append({"agentId": c.agentId, "topic": c.topic or "other", "title": c.title,
                                     "text": c.text})
    return dict(out)


def build_packet(engine) -> dict:
    """Revision packet from one finished run (engine is a GovernanceEngine)."""
    b: GovernanceBundle = engine.snapshot.governance
    sc = engine.snapshot.scenario
    seat_info = {s.agentId: s for s in engine.roster.seats}
    meta = strata_meta(engine)
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
        rows = stratum_positions(meta, _statements(engine, c))
        proposals[-1]["stratumPositions"] = rows
        proposals[-1]["positionSpread"] = position_spread(rows)
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
        seeds.append({"id": s["id"], "title": s["title"], "description": s.get("description", ""),
                      "strata": s.get("strata", []), "findings": len(refs), "expectationSeats": exp,
                      "challengedFindings": sum(1 for p in refs if p["challenges"]),
                      "status": "addressed" if refs else ("expectedOnly" if exp else "unaddressed")})
    return {
        "packetId": f"{engine.run_id}:packet", "kind": "revisionPacket", "status": "pendingHumanReview",
        "runIds": [engine.run_id], "scenarioId": sc["scenarioId"], "asOfDate": sc["asOfDate"],
        "modelId": b.model["modelId"], "modelVersion": b.model["version"], "contextId": b.context["contextId"],
        "councilNature": "synthetic",
        "notice": NOTICE,
        "strata": [{k: st[k] for k in ("stratumId", "label")} | {"seats": len(st["seats"])} for st in meta],
        "coverageMatrix": matrix, "seedTensions": seeds, "proposals": proposals,
        "strataPerspectives": strata_perspectives(meta, proposals, _blind_expectations(engine), engine.minority),
        "minorityOpinions": [{"claimId": m["claimId"], "agentId": m["agentId"], "stratumId": m.get("stratumId"),
                              "rationale": m["rationale"]} for m in engine.minority],
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
        m["raisedBy"] = sorted({p["author"]["stratumId"] for _, p in items})
        if any(p.get("stratumPositions") for _, p in items):
            m["stratumPositions"] = _merge_positions(items)
            m["positionSpread"] = position_spread(m["stratumPositions"])
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
            x = seeds.setdefault(s["id"], {"id": s["id"], "title": s["title"], "description": s.get("description", ""),
                                           "strata": s.get("strata", []), "findingsByReplicate": [],
                                           "expectationSeatsByReplicate": []})
            x["findingsByReplicate"].append(s["findings"])
            x["expectationSeatsByReplicate"].append(s.get("expectationSeats", 0))
    first = packets[0]
    meta = _merged_meta(packets)
    blind: dict[str, list[dict]] = defaultdict(list)
    for i, pk in enumerate(packets, 1):
        for sp in pk.get("strataPerspectives", []):
            blind[sp["stratumId"]] += [{**e, "replicate": i} for e in sp["blindExpectations"]]
    minority = [m for p in packets for m in p["minorityOpinions"]]
    return {"packetId": "merge:" + sha256_json([p["packetId"] for p in packets])[:12], "kind": "revisionPacket",
            "merged": True, "status": "pendingHumanReview", "runIds": [r for p in packets for r in p["runIds"]],
            "replicates": n, "scenarioId": first["scenarioId"], "asOfDate": first["asOfDate"],
            "modelId": first["modelId"], "modelVersion": first["modelVersion"], "contextId": first["contextId"],
            "councilNature": "synthetic", "notice": first["notice"],
            "strata": [{"stratumId": m["stratumId"], "label": m["label"], "seats": len(m["seats"])} for m in meta],
            "coverageMatrix": list(cov.values()), "seedTensions": list(seeds.values()),
            "proposals": merged,
            "strataPerspectives": strata_perspectives(meta, merged, blind, minority) if meta else [],
            "minorityOpinions": minority}


def _merged_meta(packets: list[dict]) -> list[dict]:
    """Strata of a merge; seat counts are the per-replicate maximum (seats are re-drawn per replicate)."""
    meta: dict[str, dict] = {}
    for pk in packets:
        for st in pk.get("strata", []):
            m = meta.setdefault(st["stratumId"], {"stratumId": st["stratumId"], "label": st["label"], "n": 0})
            m["n"] = max(m["n"], st["seats"])
    return [{"stratumId": k, "label": v["label"], "seats": [None] * v["n"]} for k, v in meta.items()]


def _merge_positions(items: list[tuple[int, dict]]) -> list[dict]:
    """Stance of each stratum on the merged proposal. Within a replicate, several findings can share a
    key; their seat stances are pooled. Across replicates a stratum keeps a stance only if it held it in
    every replicate where the proposal appeared; otherwise it is 'variesAcrossReplicates'."""
    by: dict[str, dict] = {}
    for i, p in items:
        for r in p.get("stratumPositions", []):
            x = by.setdefault(r["stratumId"], {"stratumId": r["stratumId"], "label": r["label"], "seatsTotal": 0,
                                               "statements": [], "_rep": defaultdict(dict)})
            x["seatsTotal"] = max(x["seatsTotal"], r["seatsTotal"])
            x["statements"] += [{**st, "replicate": i} for st in r["statements"]]
            seats = x["_rep"][i]
            for agent, stance in r.get("seatStances", {}).items():
                seats.setdefault(agent, set()).add(stance)
    rows = []
    for x in by.values():
        rep = x.pop("_rep")
        reps = sorted({i for i, _ in items})
        by_rep = {}
        for i in reps:
            stances = {st for v in rep.get(i, {}).values() for st in v}
            by_rep[str(i)] = ("notSeated" if not x["seatsTotal"] else "silent" if not stances
                              else stances.pop() if len(stances) == 1 else "split")
        vals = set(by_rep.values())
        x.update({"byReplicate": by_rep, "stance": vals.pop() if len(vals) == 1 else "variesAcrossReplicates",
                  "seatsSpoke": max((len(rep.get(i, {})) for i in reps), default=0)})
        rows.append(x)
    return rows


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
         "- O conselho não chega a uma resposta comum. Leia a tabela de estratos de cada proposta: quem defendeu, quem "
         "contestou, quem pediu ajuste e quem ficou calado. Um estrato calado não concorda; ele não se pronunciou.",
         "- Ninguém altera o modelo além de você: `scse govern apply` só aplica o que estiver decidido no arquivo de decisões.", ""]
    L += _render_strata(packet)
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
            spread = p.get("positionSpread") or {}
            if spread:
                tag.append(" · ".join(f"{STANCE_LABEL[k]}: {len(v)}" for k, v in spread.items()
                                      if k in STANCE_LABEL and k != "notSeated") + " estrato(s)")
                if spread.get("contested"):
                    tag.append("contestada")
                if spread.get("onlyAuthorStratum"):
                    tag.append("só o estrato autor se pronunciou")
            else:
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
                  f"- Levantada por: {', '.join(p.get('raisedBy') or [p['author']['stratumId']])}",
                  f"- Sinais: {'; '.join(tag)}",
                  f"- Fontes: {', '.join(p['sourceIds']) or 'nenhuma válida'}"
                  + (f" · traços de contexto: {', '.join(p['contextFeatureIds'])}" if p["contextFeatureIds"] else "")
                  + (f" · tensões: {', '.join(p['tensionIds'])}" if p["tensionIds"] else "")]
            if p.get("stratumPositions"):
                L += ["", "| Estrato | Posição | Assentos | Argumento |", "|---|---|---|---|"]
                for r in p["stratumPositions"]:
                    if r["stance"] == "notSeated":
                        continue
                    pos = STANCE_LABEL.get(r["stance"], r["stance"])
                    if r.get("byReplicate"):
                        pos += " (" + ", ".join(f"r{k}: {STANCE_LABEL.get(v, v)}" for k, v in r["byReplicate"].items()) + ")"
                    said = [st for st in r["statements"] if st.get("text")]
                    arg = " / ".join(f"{STANCE_LABEL.get(st['stance'], st['stance'])}: {_cell(st['text'], 220)}"
                                     + (" (versão anterior)" if st.get("onEarlierVersion") else "")
                                     for st in said[-2:]) or "-"
                    L.append(f"| {r['label']} | {pos} | {r['seatsSpoke']}/{r['seatsTotal']} | {arg} |")
                L.append("")
            else:
                for ch in p["challenges"][:3]:
                    L.append(f"- Contestação ({ch['stratumId']}): {ch['text'][:300]}")
            for br in p["branchAssessments"][:4]:
                L.append(f"- Sob `{br['branchId']}`: {br['text'][:240]}")
            L += ["", "Decisão: [ ] accept   [ ] modify   [ ] reject   [ ] defer", ""]
    if packet["minorityOpinions"]:
        L += ["## Dissenso registrado", ""]
        L += [f"- {m['claimId']}: {m['rationale'][:300]}" for m in packet["minorityOpinions"]]
    return "\n".join(L) + "\n"


def _cell(text: str, n: int) -> str:
    t = " ".join(text.split()).replace("|", "/")
    return t if len(t) <= n else t[: n - 1] + "…"


def _render_strata(packet: dict) -> list[str]:
    persp = packet.get("strataPerspectives") or []
    if not persp:
        return []
    L = ["## Cada estrato, sua leitura", "",
         "Cada estrato aparece com a própria leitura. Não há síntese entre eles: divergência é informação para "
         "quem decide, não ruído a eliminar.", ""]
    for sp in persp:
        if not sp["seats"]:
            L += [f"### {sp['label']} (`{sp['stratumId']}`)", "", "Sem assento nesta rodada.", ""]
            continue
        pos = sp["positions"]
        topics = sorted({e["topic"] for e in sp["blindExpectations"]})
        L += [f"### {sp['label']} (`{sp['stratumId']}`)", "",
              f"- Assentos: {sp['seats']} · modelos: {', '.join(sp['providers']) or '-'}",
              f"- Esperava às cegas (R1): {', '.join(topics) or 'nada registrado'}",
              f"- Levantou: {', '.join(sp['authored']) or '-'}",
              f"- A favor: {', '.join(pos.get('for', [])) or '-'} · contra: {', '.join(pos.get('against', [])) or '-'}"
              f" · ajuste: {', '.join(pos.get('amend', [])) or '-'} · dividido: {', '.join(pos.get('split', [])) or '-'}",
              f"- Sem posição em {len(pos.get('silent', []))} proposta(s)"]
        if sp["aloneFor"]:
            L.append(f"- Único estrato a favor: {', '.join(sp['aloneFor'])}")
        if sp["aloneAgainst"]:
            L.append(f"- Único estrato contra: {', '.join(sp['aloneAgainst'])}")
        for m in sp["minorityOpinions"][:3]:
            L.append(f"- Opinião minoritária ({m['claimId']}): {_cell(m['rationale'], 240)}")
        L.append("")
    return L


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
