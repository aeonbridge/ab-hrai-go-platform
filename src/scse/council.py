"""CouncilComposer: seats, PerspectiveCharters, model routing and BalanceCheck."""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import asdict, dataclass, field

from .config import ConfigError, ModelConfig
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

    def to_dict(self) -> dict:
        d = asdict(self)
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

    def to_dict(self) -> dict:
        return {"syntheticCouncil": True, "assignment": self.assignment, "mode": self.mode,
                "providers": self.providers, "coverage": self.coverage, "balance": self.balance,
                "unrepresented": self.unrepresented, "seats": [s.to_dict() for s in self.seats]}


DISCLOSURE = ("Perspectiva sintética gerada para simulação. Não representa pessoa, órgão ou grupo real "
              "e não mede opinião ou adesão social.")


def _provider_for(index: int, stratum: str, providers: list[str], assignment: str,
                  fixed: dict[str, str], offset: int) -> str:
    if assignment == "single":
        return providers[0]
    if assignment == "fixed":
        if stratum not in fixed:
            raise ConfigError(f"assignment.fixed has no provider for stratum {stratum!r}")
        return fixed[stratum]
    if assignment == "rotate":
        return providers[(index + offset) % len(providers)]
    raise ConfigError(f"unknown assignment {assignment!r}")


def compose(snapshot: WorldSnapshot, config: ModelConfig, *, providers: list[str] | None = None,
            assignment: str | None = None, mode: str = "stratified", seed: int = 0,
            replicate: int = 0) -> CouncilRoster:
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
            provider = _provider_for(index, stratum_id, order, assignment, fixed, replicate)
            spec = config.model(provider, profile)
            charter.modelVersion = spec.label
            seat_no = f"{stratum_id}-{k + 1:02d}" if mode == "stratified" else f"{mode}-{k + 1:02d}"
            seats.append(CouncilSeat(seatId=f"seat:{seat_no}", agentId=f"agent:{seat_no}",
                                     stratumId=charter.stratumId, profile=profile, provider=provider,
                                     model=spec.id, charter=charter,
                                     rationale=f"quota documentada do estrato; provider via {assignment}"))
            index += 1
    return CouncilRoster(seats=seats, assignment=assignment, mode=mode, providers=order,
                         coverage=coverage(snapshot, seats, mode), balance=balance_check(seats),
                         unrepresented=world.get("unrepresented", []))


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
