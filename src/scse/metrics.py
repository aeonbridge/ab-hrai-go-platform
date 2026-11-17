"""Provider scorecards ("practice" of each model) and replicate sensitivity."""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict


def _rate(n: float, d: float) -> float | None:
    return round(n / d, 4) if d else None


def provider_scorecard(engine) -> dict:
    """Behavioural metrics per provider for one run.

    These describe how each model *behaved inside the protocol* (format
    discipline, grounding, contestation, responsiveness, self-preference). They
    are not quality or truth scores; those require the expert rubric of the
    spec (ClaimEvidencePrecision, RelevantGapRecall, ...).
    """
    turns = defaultdict(list)
    for t in engine.turn_stats:
        turns[t["provider"]].append(t)
    claims = [c for c in engine.claims.values()]
    by_id = engine.claims
    seat_provider = {s.agentId: s.provider for s in engine.roster.seats}
    out = {}
    for provider in sorted({s.provider for s in engine.roster.seats}):
        ts = turns.get(provider, [])
        mine = [c for c in claims if c.provider == provider]
        public_mine = [c for c in mine if c.visibility == "public"]
        theses = [c for c in public_mine if c.kind in ("thesis", "revision", "amendment")]
        challenges = [c for c in public_mine if c.kind == "challenge"]
        r3_turns = [t for t in ts if t["roundId"] == "R3"]
        challenged_own = [c for c in public_mine if c.challengedBy]
        responded = [c for c in challenged_own if c.status in ("withdrawn", "superseded")]
        support_given = Counter()
        for c in claims:
            for agent in c.supporters:
                if seat_provider.get(agent) == provider:
                    support_given[c.provider] += 1
        challenge_given = Counter(by_id[c.targetClaimId].provider for c in challenges if c.targetClaimId in by_id)
        total_support = sum(support_given.values())
        total_chal = sum(challenge_given.values())
        n_prov = len({s.provider for s in engine.roster.seats})
        out[provider] = {
            "turns": len(ts),
            "schemaValidRate": _rate(sum(t["schemaValid"] for t in ts), len(ts)),
            "repairRate": _rate(sum(t.get("repaired", False) for t in ts), len(ts)),
            "refusalRate": _rate(sum(t["refusal"] for t in ts), len(ts)),
            "failureRate": _rate(sum((not t["schemaValid"]) and not t["refusal"] for t in ts), len(ts)),
            "rejectedActionRate": _rate(sum(t.get("rejected", 0) for t in ts),
                                        sum(t.get("rejected", 0) + t.get("accepted", 0) for t in ts)),
            "claims": len(public_mine),
            "groundingRate": _rate(sum(1 for c in public_mine if c.sourceIds and not c.invalidSourceIds), len(public_mine)),
            "invalidCitationRate": _rate(sum(1 for c in mine if c.invalidSourceIds), len(mine)),
            "hypothesisShare": _rate(sum(1 for c in public_mine if c.classification == "hypothesis"), len(public_mine)),
            "challengesPerR3Turn": _rate(len([c for c in challenges if c.roundId == "R3"]), len(r3_turns)),
            "receivedChallengeRate": _rate(len(challenged_own), len(theses)),
            "responsivenessRate": _rate(len(responded), len(challenged_own)),
            "minorityOpinions": sum(1 for m in engine.minority if seat_provider.get(m["agentId"]) == provider),
            "criticGroundedRate": _rate(sum(1 for c in theses if c.criticVerdict == "groundedInSources"),
                                        sum(1 for c in theses if c.criticVerdict)),
            # >1/n_providers means the provider favours claims from its own family.
            "selfSupportShare": _rate(support_given.get(provider, 0), total_support),
            "selfChallengeShare": _rate(challenge_given.get(provider, 0), total_chal),
            "baselineShare": _rate(1, n_prov),
            "supportGivenTo": dict(support_given),
            "challengesGivenTo": dict(challenge_given),
        }
    for label, u in engine.usage.items():
        prov = label.split(":", 1)[0]
        card = out.setdefault(prov, {})
        card.setdefault("usage", {})[label] = {
            "calls": u.calls, "inputTokens": u.input_tokens, "outputTokens": u.output_tokens,
            "costUsd": round(u.cost_usd, 4) if u.cost_known else None,
            "avgLatencyS": round(u.latency_s / u.calls, 3) if u.calls else None}
    return out


def run_summary(engine, tensions: list[dict]) -> dict:
    public = [c for c in engine.claims.values() if c.visibility == "public"]
    strata_pairs = sorted({f"{engine.claims[t['supportingClaimIds'][0]].stratumId}<-"
                           f"{engine.claims[x].stratumId}"
                           for t in tensions for x in t["counterClaimIds"]})
    return {
        "publicClaims": len(public),
        "activeClaims": sum(1 for c in public if c.status == "active"),
        "challenges": sum(1 for c in public if c.kind == "challenge"),
        "withdrawn": sum(1 for c in public if c.status == "withdrawn"),
        "revised": sum(1 for c in public if c.status == "superseded"),
        "amendments": sum(1 for c in public if c.kind == "amendment"),
        "branchClaims": sum(1 for c in public if c.branchId),
        "tensions": len(tensions),
        "minorityOpinions": len(engine.minority),
        "evidenceRequests": len(engine.questions),
        "insufficientGrounding": sum(1 for c in public if c.insufficientGrounding),
        "tensionStratumPairs": strata_pairs,
        "stoppedReason": engine.stopped_reason,
    }


def sensitivity(summaries: list[dict]) -> dict:
    """RunSensitivity: dispersion of run-level counts and structural overlap across replicates."""
    keys = ["publicClaims", "challenges", "withdrawn", "revised", "amendments", "tensions",
            "minorityOpinions", "insufficientGrounding"]
    out = {"replicates": len(summaries), "metrics": {}}
    for k in keys:
        vals = [s[k] for s in summaries]
        out["metrics"][k] = {"values": vals, "mean": round(statistics.fmean(vals), 3) if vals else None,
                             "stdev": round(statistics.pstdev(vals), 3) if len(vals) > 1 else 0.0}
    sets = [set(s["tensionStratumPairs"]) for s in summaries]
    pairs = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            union = sets[i] | sets[j]
            pairs.append(len(sets[i] & sets[j]) / len(union) if union else 1.0)
    out["tensionStructureJaccard"] = {
        "mean": round(statistics.fmean(pairs), 3) if pairs else None,
        "note": "Sobreposição dos pares estrato(tese)<-estrato(contestação) entre réplicas; "
                "baixa sobreposição indica resultado sensível a seed/modelo/ordem de fala."}
    return out


def aggregate_scorecards(cards: list[dict]) -> dict:
    """Mean of numeric scorecard fields per provider across runs."""
    acc: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for card in cards:
        for provider, metrics in card.items():
            for k, v in metrics.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    acc[provider][k].append(float(v))
    return {p: {k: round(statistics.fmean(v), 4) for k, v in m.items()} for p, m in acc.items()}
