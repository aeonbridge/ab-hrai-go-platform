"""CouncilComposer: seats, PerspectiveCharters, model routing and BalanceCheck."""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import asdict, dataclass, field

from .config import ConfigError, MixEntry, ModelConfig, ModelSpec
from .world import WorldSnapshot

ALL_ACTIONS = ["assertClaim", "support", "challenge", "requestEvidence", "revise", "withdraw",
               "proposeAmendment", "declareUncertainty", "submitMinorityOpinion", "abstain"]

COUNCIL_MODES = ("stratified", "unstratified", "singleAgent")


@dataclass
class PerspectiveCharter:
    role: str
    stratumId: str
    variant: str
    documentedPositions: list[str]
    sourceIds: list[str]
    interests: list[str]
    constraints: list[str]
    blindSpots: list[str]
    allowedActions: list[str]
    disclosure: str
    conflictOfInterest: str
    modelVersion: str = ""


@dataclass
class CouncilSeat:
    seatId: str
    agentId: str
    stratumId: str
    profile: str
    provider: str
    model: str
    charter: PerspectiveCharter
    rationale: str = ""
    tier: str = ""
    transport: str = ""
    mixKey: str = ""
    spec: ModelSpec | None = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("spec", None)
        return d


@dataclass
class CouncilRoster:
    seats: list[CouncilSeat]
    assignment: str
    mode: str
    providers: list[str]
    coverage: dict
    balance: dict
    unrepresented: list[dict] = field(default_factory=list)
    mix: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"syntheticCouncil": True, "assignment": self.assignment, "mode": self.mode,
                "providers": self.providers, "coverage": self.coverage, "balance": self.balance,
                "mix": self.mix, "unrepresented": self.unrepresented,
                "seats": [s.to_dict() for s in self.seats]}


DISCLOSURE = ("Perspectiva sintética gerada para simulação. Não representa pessoa, órgão ou grupo real "
              "e não mede opinião ou adesão social.")


ASSIGNMENTS = ("weighted", "rotate", "fixed", "single")


def smooth_wrr(entries: list[MixEntry], length: int) -> list[MixEntry]:
    """Smooth weighted round-robin: any window of k picks is within 1 of k*w_i/W
    for every entry, so few seats still follow the configured percentages."""
    total = sum(e.weight for e in entries)
    current = [0.0] * len(entries)
    out = []
    for _ in range(length):
        for i, e in enumerate(entries):
            current[i] += e.weight
        best = max(range(len(entries)), key=lambda i: (current[i], -i))
        current[best] -= total
        out.append(entries[best])
    return out


def _mix_for(stratum: str, config: ModelConfig, providers: list[str], assignment: str,
             fixed: dict[str, str], order: list[str]) -> list[MixEntry]:
    if assignment == "single":
        return [MixEntry(provider=providers[0], weight=1)]
    if assignment == "fixed":
        if stratum not in fixed:
            raise ConfigError(f"assignment.fixed has no provider for stratum {stratum!r}")
        return [MixEntry(provider=fixed[stratum], weight=1)]
    if assignment == "rotate":
        entries = [MixEntry(provider=p, weight=1) for p in providers]
    elif assignment == "weighted":
        entries = config.stratum_mix(stratum, providers)
    else:
        raise ConfigError(f"unknown assignment {assignment!r}; use one of {ASSIGNMENTS}")
    # Seeded provider order (stable for ties) so equal weights do not always start with the same provider.
    rank = {p: i for i, p in enumerate(order)}
    return sorted(entries, key=lambda e: rank.get(e.provider, len(rank)))


def compose(snapshot: WorldSnapshot, config: ModelConfig, *, providers: list[str] | None = None,
            assignment: str | None = None, mode: str = "stratified", seed: int = 0,
            replicate: int = 0, transport: str | None = None) -> CouncilRoster:
    if mode not in COUNCIL_MODES:
        raise ConfigError(f"council mode must be one of {COUNCIL_MODES}")
    assignment = assignment or config.assignment
    providers = list(providers or config.required_providers)
    if not providers:
        raise ConfigError("no providers selected")
    if assignment == "fixed" and mode != "stratified":
        raise ConfigError("assignment=fixed maps strata to providers; use rotate/single for baselines")
    if assignment == "single" and len(providers) != 1:
        raise ConfigError("assignment=single requires exactly one provider")
    fixed = config.fixed_assignment()
    rng = random.Random(seed)
    order = providers[:]
    rng.shuffle(order)
    world = snapshot.world
    strata = {s["id"]: s for s in world["strata"]}
    all_sources = sorted(snapshot.evidence_ids)

    seats: list[CouncilSeat] = []
    mixes: dict[str, list[MixEntry]] = {}
    if mode == "singleAgent":
        plan = [("generalist", 1)]
    else:
        plan = list(snapshot.seat_plan.items())
    index = 0
    for stratum_id, count in plan:
        for k in range(count):
            if mode == "stratified":
                s = strata[stratum_id]
                variants = s.get("variants") or [s["label"]]
                variant = variants[k % len(variants)]
                charter = PerspectiveCharter(
                    role=f"{s['label']} — {variant}", stratumId=stratum_id, variant=variant,
                    documentedPositions=s.get("documentedPositions", []), sourceIds=s.get("sourceIds", []),
                    interests=s.get("interests", []), constraints=s.get("constraints", []),
                    blindSpots=s.get("blindSpots", []), allowedActions=ALL_ACTIONS,
                    disclosure=DISCLOSURE, conflictOfInterest=s.get("conflictOfInterest", "não declarado"))
                profile = s.get("profile", "perspective.standard")
            else:
                # B1 / B2 baselines: no documented perspective, full source access.
                charter = PerspectiveCharter(
                    role="Analista de políticas públicas (sem estrato)", stratumId="unstratified",
                    variant="generalista", documentedPositions=[], sourceIds=all_sources, interests=[],
                    constraints=[], blindSpots=[], allowedActions=ALL_ACTIONS, disclosure=DISCLOSURE,
                    conflictOfInterest="não aplicável")
                profile = "perspective.deep" if mode == "singleAgent" else "perspective.standard"
            mix_stratum = stratum_id if mode == "stratified" else "default"
            if mix_stratum not in mixes:
                mixes[mix_stratum] = _mix_for(mix_stratum, config, providers, assignment, fixed, order)
            entries = mixes[mix_stratum]
            # Global seat index spreads providers across strata; +replicate shifts the window.
            entry = smooth_wrr(entries, index + replicate + 1)[-1]
            spec = config.model(entry.provider, profile, tier=entry.tier, model=entry.model, transport=transport)
            charter.modelVersion = spec.label
            seat_no = f"{stratum_id}-{k + 1:02d}" if mode == "stratified" else f"{mode}-{k + 1:02d}"
            seats.append(CouncilSeat(seatId=f"seat:{seat_no}", agentId=f"agent:{seat_no}",
                                     stratumId=charter.stratumId, profile=profile, provider=entry.provider,
                                     model=spec.id, charter=charter, tier=spec.tier, transport=spec.transport,
                                     mixKey=entry.key, spec=spec,
                                     rationale=f"quota documentada do estrato; provider/modelo via {assignment}"))
            index += 1
    return CouncilRoster(seats=seats, assignment=assignment, mode=mode, providers=order,
                         coverage=coverage(snapshot, seats, mode), balance=balance_check(seats),
                         unrepresented=world.get("unrepresented", []), mix=mix_report(mixes, seats, mode))


def mix_report(mixes: dict[str, list[MixEntry]], seats: list[CouncilSeat], mode: str) -> dict:
    """Configured share vs. seats realised in this replicate, per stratum."""
    out = {}
    for stratum, entries in mixes.items():
        total = sum(e.weight for e in entries)
        configured: dict[str, float] = {}
        for e in entries:
            configured[e.key] = round(configured.get(e.key, 0) + 100 * e.weight / total, 2)
        group = [s for s in seats if (s.stratumId if mode == "stratified" else "default") == stratum]
        realised = Counter(s.mixKey for s in group)
        out[stratum] = {"configuredPercent": configured, "realisedSeats": dict(realised), "seats": len(group),
                        "note": ("com poucos assentos a distribuição exata só se realiza no acumulado das réplicas"
                                 if len(group) < len(entries) else "")}
    return out


def coverage(snapshot: WorldSnapshot, seats: list[CouncilSeat], mode: str) -> dict:
    relevant = [s["id"] for s in snapshot.world["strata"]] + [
        u["perspective"] for u in snapshot.world.get("unrepresented", [])]
    covered = sorted({s.stratumId for s in seats} & set(relevant)) if mode == "stratified" else []
    return {"indicator": "C = covered documented perspectives / relevant documented perspectives",
            "numerator": len(covered), "denominator": len(relevant),
            "value": round(len(covered) / len(relevant), 3) if relevant else 0.0,
            "covered": covered, "denominatorJustification": "estratos do world pack + perspectivas marcadas Unrepresented",
            "note": "Não mede representatividade demográfica nem adesão social."}


def balance_check(seats: list[CouncilSeat]) -> dict:
    n = len(seats)
    by_provider = Counter(s.provider for s in seats)
    by_stratum = Counter(s.stratumId for s in seats)
    warnings = []
    if len(by_provider) > 1:
        top, cnt = by_provider.most_common(1)[0]
        if cnt / n > 0.5:
            warnings.append(f"provider {top} ocupa {cnt}/{n} assentos (>50%)")
    if len(by_stratum) > 1:
        top, cnt = by_stratum.most_common(1)[0]
        if cnt / n > 0.3:
            warnings.append(f"estrato {top} ocupa {cnt}/{n} assentos (>30%)")
    if len(by_provider) == 1 and n > 1:
        warnings.append("conselho de provider único: resultados não separam viés do modelo de perspectiva")
    mixed = [st for st in by_stratum if len({s.provider for s in seats if s.stratumId == st}) > 1]
    return {"seats": n, "byProvider": dict(by_provider), "byStratum": dict(by_stratum),
            "strataWithMixedProviders": sorted(mixed), "warnings": warnings}
