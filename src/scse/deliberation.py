"""DeliberationEngine: R0-R8 state machine over a CouncilRoster."""
from __future__ import annotations

import hashlib
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from jsonschema import Draft202012Validator

from . import prompts
from .config import ModelConfig
from .council import CouncilRoster, CouncilSeat
from .ledger import EventLedger
from .providers import CompletionRequest, Provider, ProviderError, build_provider
from .world import WorldSnapshot

ROUND_SEQUENCE = ["R1", "R2", "R3", "R4", "R5", "R6"]
CREATES_CLAIM = {"assertClaim": "thesis", "challenge": "challenge", "revise": "revision",
                 "proposeAmendment": "amendment", "declareUncertainty": "uncertainty"}
NEEDS_TARGET = {"support", "challenge", "revise", "withdraw", "proposeAmendment", "submitMinorityOpinion"}
OWN_TARGET = {"revise", "withdraw", "submitMinorityOpinion"}
_TURN_VALIDATOR = Draft202012Validator(prompts.TURN_SCHEMA)


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Claim:
    id: str
    agentId: str
    stratumId: str
    provider: str
    roundId: str
    kind: str
    text: str
    sourceIds: list[str]
    classification: str
    confidence: str
    visibility: str = "public"
    status: str = "active"            # active | withdrawn | superseded | draft
    targetClaimId: str | None = None
    branchId: str | None = None
    supporters: list[str] = field(default_factory=list)
    supportNotes: list[dict] = field(default_factory=list)   # {agentId, stratumId, roundId, text}: why they back it
    challengedBy: list[str] = field(default_factory=list)
    amendedBy: list[str] = field(default_factory=list)
    supersededBy: str | None = None
    invalidSourceIds: list[str] = field(default_factory=list)
    insufficientGrounding: bool = False
    criticVerdict: str | None = None
    # governanceReview only (None / empty elsewhere)
    lens: str | None = None
    topic: str | None = None
    componentId: str | None = None
    change: str | None = None
    title: str | None = None
    contextFeatureIds: list[str] = field(default_factory=list)
    tensionIds: list[str] = field(default_factory=list)
    genericity: str | None = None


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cost_known: bool = True
    latency_s: float = 0.0


def stable_int(*parts) -> int:
    """Process-independent hash (Python's hash() is salted per process)."""
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def round_plan(rounds: int) -> list[str]:
    """``rounds`` counts R1..R6 (spec); extra rounds repeat R3/R4 cycles before R5."""
    if rounds <= 6:
        return ROUND_SEQUENCE[:rounds]
    extra = []
    for i in range(rounds - 6):
        extra.append("R3" if i % 2 == 0 else "R4")
    return ROUND_SEQUENCE[:4] + extra + ROUND_SEQUENCE[4:]


def extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fenced:
        return json.loads(fenced.group(1))
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError("no JSON object in model output")


class DeliberationEngine:
    def __init__(self, snapshot: WorldSnapshot, roster: CouncilRoster, config: ModelConfig, *,
                 run_id: str, seed: int, dry_run: bool = False, max_workers: int = 8,
                 max_actions: int = 4, critic: bool = False, synthesize: bool = False,
                 providers_factory=None, transport: str | None = None,
                 openrouter_trace_path: str | None = None):
        self.snapshot = snapshot
        self.roster = roster
        self.config = config
        self.run_id = run_id
        self.seed = seed
        self.dry_run = dry_run
        self.max_workers = max_workers
        self.max_actions = max_actions
        self.use_critic = critic
        self.use_synth = synthesize
        self.transport = transport
        self.ledger = EventLedger(run_id)
        self.claims: dict[str, Claim] = {}
        self.minority: list[dict] = []
        self.questions: list[dict] = []
        self.episodic: dict[str, list[str]] = {s.agentId: [] for s in roster.seats}
        self.usage: dict[str, Usage] = {}
        self.turn_stats: list[dict] = []
        self._counter = 0
        sim = snapshot.scenario["simulation"]
        self.token_budget = sim.get("tokenBudget")
        self.max_cost = sim.get("maxCostUsd")
        self.stopped_reason: str | None = None
        self._factory = providers_factory or (lambda spec: build_provider(spec, dry_run=dry_run))
        self._providers: dict[str, Provider] = {}
        self.http_trace = None
        if openrouter_trace_path is not None:
            from .providers.http_trace import OpenRouterHttpTrace
            self.http_trace = OpenRouterHttpTrace(openrouter_trace_path)
        self.models_used: set[str] = set()

    # ------------------------------------------------------------------ infra
    def _provider(self, provider: str, profile: str, spec=None) -> Provider:
        spec = spec or self.config.model(provider, profile, transport=self.transport)
        key = f"{spec.provider}|{spec.transport}|{spec.id}"
        if key not in self._providers:
            self._providers[key] = self._factory(spec)
        instance = self._providers[key]
        if self.http_trace is not None and spec.sdk == "openrouter":
            instance.set_trace_recorder(self.http_trace)
        return instance

    def close(self) -> None:
        """Close provider clients and fsync the raw HTTP trace."""
        try:
            for provider in self._providers.values():
                close = getattr(provider, "close", None)
                if callable(close):
                    close()
        finally:
            if self.http_trace is not None:
                self.http_trace.close()

    def _next_id(self, round_id: str) -> str:
        self._counter += 1
        return f"C{self._counter:04d}-{round_id}"

    def _account(self, provider: Provider, result) -> None:
        u = self.usage.setdefault(provider.spec.label, Usage())
        u.calls += 1
        u.input_tokens += result.input_tokens
        u.output_tokens += result.output_tokens
        u.latency_s += result.latency_s
        reported = (result.extra or {}).get("cost_usd")
        pin, pout = provider.spec.options.get("price_in"), provider.spec.options.get("price_out")
        if reported is not None:
            u.cost_usd += reported  # OpenRouter returns the billed cost per call
        elif pin is None or pout is None:
            u.cost_known = provider.spec.sdk == "mock"
        else:
            u.cost_usd += (result.input_tokens * float(pin) + result.output_tokens * float(pout)) / 1e6
        self.models_used.add(f"{provider.spec.provider}:{result.model_served}")

    def _check_budget(self) -> None:
        tokens = sum(u.input_tokens + u.output_tokens for u in self.usage.values())
        cost = sum(u.cost_usd for u in self.usage.values())
        if self.token_budget and tokens > self.token_budget:
            raise BudgetExceeded(f"tokenBudget {self.token_budget} exceeded ({tokens})")
        if self.max_cost and cost > self.max_cost:
            raise BudgetExceeded(f"maxCostUsd {self.max_cost} exceeded ({cost:.2f})")

    def _call(self, provider: Provider, system: str, user: str, schema: dict, name: str,
              validator: Draft202012Validator, seed: int) -> tuple[dict | None, dict]:
        """Call with transport retries and one schema-repair retry. Returns (payload, stats)."""
        defaults = self.config.defaults
        stats = {"provider": provider.name, "model": provider.spec.id, "schemaValid": False,
                 "repaired": False, "refusal": False, "error": None, "attempts": 0}
        repairs = int(defaults.get("repair_attempts", 1))
        prompt = user
        for attempt in range(repairs + 1):
            result = None
            for transport_try in range(3):
                stats["attempts"] += 1
                try:
                    result = provider.complete(CompletionRequest(
                        system=system, user=prompt, schema=schema, schema_name=name,
                        max_output_tokens=int(defaults.get("max_output_tokens", 8000)),
                        timeout_seconds=float(defaults.get("timeout_seconds", 300)), seed=seed))
                    break
                except ProviderError as exc:
                    stats["error"] = str(exc)
                    if not exc.retryable or transport_try == 2:
                        return None, stats
                    time.sleep(2 ** transport_try)
            self._account(provider, result)
            stats["latency_s"] = round(result.latency_s, 3)
            if result.refusal:
                stats["refusal"] = True
                stats["error"] = result.refusal_detail or "refusal"
                return None, stats
            try:
                payload = extract_json(result.text)
                errors = [e.message for e in validator.iter_errors(payload)]
            except (ValueError, json.JSONDecodeError) as exc:
                payload, errors = None, [str(exc)]
            if not errors:
                stats["schemaValid"] = True
                stats["repaired"] = attempt > 0
                stats["error"] = None
                return payload, stats
            stats["error"] = "; ".join(errors[:3])
            prompt = (user + "\n\nSua resposta anterior violou o contrato JSON: " + stats["error"][:500]
                      + "\nResponda novamente apenas com JSON válido.")
        return None, stats

    # ------------------------------------------------------------- run phases
    def run(self) -> None:
        sc = self.snapshot.scenario
        self.ledger.emit("scenario.ingested", scenarioId=sc["scenarioId"], mode=sc["mode"])
        self.ledger.emit("snapshot.frozen", snapshotHash=self.snapshot.snapshot_hash)
        self.ledger.emit("council.prepared", seats=len(self.roster.seats), balance=self.roster.balance,
                         coverage=self.roster.coverage)
        rounds = round_plan(int(sc["simulation"]["rounds"]))
        try:
            for idx, round_id in enumerate(rounds):
                if round_id == "R6" and not sc["simulation"].get("branches"):
                    self.ledger.emit("round.skipped", round_id=round_id, reason="no branches declared")
                    continue
                productive = self._run_round(round_id, idx)
                self._check_budget()
                if round_id in ("R3", "R4") and idx >= 6 and productive == 0:
                    self.ledger.emit("round.earlyStop", round_id=round_id, reason="no new arguments")
                    break
            self._run_round("R7", len(rounds))
            self._audit()
            if self.use_critic:
                self._critic()
        except BudgetExceeded as exc:
            self.stopped_reason = str(exc)
            self.ledger.emit("run.budgetExceeded", reason=str(exc))
        self.ledger.emit("run.completed", stoppedReason=self.stopped_reason)

    def _speaking_order(self, round_index: int) -> list[CouncilSeat]:
        seats = list(self.roster.seats)
        random.Random(f"{self.seed}:{round_index}").shuffle(seats)
        return seats

    def _public(self) -> list[Claim]:
        return [c for c in self.claims.values() if c.visibility == "public"]

    def _turn_inputs(self, seat: CouncilSeat, round_id: str) -> dict:
        public = self._public()
        own = [c for c in public if c.agentId == seat.agentId and c.status == "active"]
        challenges = []
        for c in own:
            live = [self.claims[x] for x in c.challengedBy if self.claims[x].status == "active"]
            if live:
                challenges.append({"claimId": c.id, "challenges": [
                    {"id": x.id, "by": x.agentId, "text": x.text[:400], "sourceIds": x.sourceIds} for x in live]})
        visible = [c for c in public if c.status == "active"] if round_id != "R1" else []
        drafts = [c for c in self.claims.values() if c.agentId == seat.agentId and c.visibility == "private"] \
            if round_id == "R2" else []
        return dict(visible_claims=visible, own_claims=own, private_drafts=drafts,
                    challenges_to_own=challenges, episodic=self.episodic[seat.agentId],
                    branches=self.snapshot.scenario["simulation"].get("branches", []),
                    open_questions=[q["text"] for q in self.questions], max_actions=self.max_actions)

    def _run_round(self, round_id: str, round_index: int) -> int:
        self.ledger.emit("round.started", round_id=round_id, name=self._round_name(round_id))
        seats = self._speaking_order(round_index)
        if round_id == "R7":
            seats = [s for s in seats if self._turn_inputs(s, "R7")["challenges_to_own"]]
        jobs = []
        for seat in seats:
            inputs = self._turn_inputs(seat, round_id)
            if round_id in ("R4",) and not inputs["challenges_to_own"]:
                continue  # nothing to revise; avoids paying for empty turns
            system = self._system_prompt(seat, round_id)
            user = self._user_prompt(round_id, seat, inputs)
            jobs.append((seat, system, user))
        schema, validator, schema_name = self._turn_schema()

        def work(job):
            seat, system, user = job
            provider = self._provider(seat.provider, seat.profile, seat.spec)
            seed = stable_int(self.seed, seat.agentId, round_id)
            payload, stats = self._call(provider, system, user, schema, schema_name, validator, seed)
            return seat, payload, stats

        with ThreadPoolExecutor(max_workers=max(1, self.max_workers)) as pool:
            results = list(pool.map(work, jobs))
        productive = 0
        for seat, payload, stats in results:  # deterministic application order
            stats.update({"roundId": round_id, "agentId": seat.agentId, "stratumId": seat.stratumId})
            if payload is None:
                kind = "agent.refused" if stats["refusal"] else "agent.failed"
                self.ledger.emit(kind, round_id=round_id, agent_id=seat.agentId, provider=seat.provider,
                                 detail=stats["error"])
                stats.update({"accepted": 0, "rejected": 0})
                self.turn_stats.append(stats)
                continue
            accepted, rejected = self._apply(seat, round_id, payload)
            productive += sum(1 for a in accepted if a != "abstain")
            stats.update({"accepted": len(accepted), "rejected": rejected,
                          "selfDeclaredInsufficientGrounding": payload.get("insufficientGrounding", False)})
            self.turn_stats.append(stats)
        self.ledger.emit("round.completed", round_id=round_id, turns=len(jobs), productiveActions=productive)
        self._after_round(round_id)
        return productive

    # ----------------------------------------------- extension hooks (see GovernanceEngine)
    def _round_name(self, round_id: str) -> str:
        return prompts.ROUND_INSTRUCTIONS[round_id][0]

    def _round_actions(self, round_id: str) -> list[str]:
        return prompts.ROUND_ACTIONS[round_id]

    def _max_actions(self, round_id: str) -> int:
        return self.max_actions

    def _system_prompt(self, seat, round_id: str) -> str:
        return prompts.system_prompt(seat, self.snapshot)

    def _user_prompt(self, round_id: str, seat, inputs: dict) -> str:
        return prompts.user_prompt(round_id, seat, **inputs)

    def _turn_schema(self):
        return prompts.TURN_SCHEMA, _TURN_VALIDATOR, "council_turn"

    def _extra_validate(self, seat, round_id: str, action: dict, target) -> str | None:
        return None

    def _decorate_claim(self, claim, action: dict, target) -> None:
        return None

    def _after_round(self, round_id: str) -> None:
        return None

    # ------------------------------------------------------------ apply rules
    def _reject(self, seat, round_id, action, reason):
        self.ledger.emit("action.rejected", round_id=round_id, agent_id=seat.agentId,
                         action=action.get("action"), reason=reason)

    def _apply(self, seat: CouncilSeat, round_id: str, payload: dict) -> tuple[list[str], int]:
        allowed = set(self._round_actions(round_id))
        branch_ids = {b["id"] for b in self.snapshot.scenario["simulation"].get("branches", [])}
        known = self.snapshot.evidence_ids
        accepted, rejected = [], 0
        for action in payload["actions"][: self._max_actions(round_id)]:
            kind = action["action"]
            target_id = action.get("targetClaimId")
            target = self.claims.get(target_id) if target_id else None
            reason = None
            if kind not in allowed:
                reason = f"action {kind} not allowed in {round_id}"
            elif kind in NEEDS_TARGET and (target is None or target.visibility != "public"):
                reason = f"unknown or non-public target {target_id!r}"
            elif kind in OWN_TARGET and target.agentId != seat.agentId:
                reason = "can only revise/withdraw/defend own claims"
            elif kind in ("support", "challenge") and target.agentId == seat.agentId:
                reason = "cannot support/challenge own claim"
            elif target is not None and target.status != "active":
                reason = f"target {target_id} is {target.status}"
            elif action.get("branchId") and (round_id != "R6" or action["branchId"] not in branch_ids):
                reason = f"invalid branchId {action.get('branchId')!r}"
            elif round_id == "R6" and kind != "abstain" and not action.get("branchId"):
                reason = "R6 actions must declare branchId"
            if reason is None:
                reason = self._extra_validate(seat, round_id, action, target)
            if reason:
                rejected += 1
                self._reject(seat, round_id, action, reason)
                continue
            valid_src = [s for s in action["sourceIds"] if s in known]
            invalid_src = [s for s in action["sourceIds"] if s not in known]
            claim_id = None
            if kind in CREATES_CLAIM:
                classification = action["classification"]
                insufficient = not valid_src or bool(invalid_src)
                if kind == "declareUncertainty":
                    classification = "unknown"
                elif insufficient and classification == "syntheticPerspective":
                    classification = "hypothesis"  # EvidenceVerifier downgrade
                claim_id = self._next_id(round_id)
                claim = Claim(id=claim_id, agentId=seat.agentId, stratumId=seat.stratumId, provider=seat.provider,
                              roundId=round_id, kind=CREATES_CLAIM[kind], text=action["text"],
                              sourceIds=valid_src, classification=classification,
                              confidence=action["confidence"], targetClaimId=target_id,
                              branchId=action.get("branchId"), invalidSourceIds=invalid_src,
                              insufficientGrounding=insufficient,
                              visibility="private" if round_id == "R1" else "public",
                              status="draft" if round_id == "R1" else "active")
                self.claims[claim_id] = claim
                self._decorate_claim(claim, action, target)
                if kind == "challenge":
                    target.challengedBy.append(claim_id)
                elif kind == "proposeAmendment":
                    target.amendedBy.append(claim_id)
                elif kind == "revise":
                    target.status = "superseded"
                    target.supersededBy = claim_id
            elif kind == "support":
                if seat.agentId not in target.supporters:
                    target.supporters.append(seat.agentId)
                target.supportNotes.append({"agentId": seat.agentId, "stratumId": seat.stratumId,
                                            "roundId": round_id, "text": action["text"]})
            elif kind == "withdraw":
                target.status = "withdrawn"
            elif kind == "requestEvidence":
                self.questions.append({"agentId": seat.agentId, "roundId": round_id, "text": action["text"]})
            elif kind == "submitMinorityOpinion":
                self.minority.append({"claimId": target_id, "agentId": seat.agentId, "stratumId": seat.stratumId,
                                      "roundId": round_id, "rationale": action["text"],
                                      "sourceIds": valid_src})
            self.ledger.emit("claim.challenged" if kind == "challenge" else "action.accepted",
                             round_id=round_id, agent_id=seat.agentId, action=kind,
                             claim_id=claim_id or target_id, evidence_ids=valid_src,
                             invalidSourceIds=invalid_src, text=action["text"][:2000],
                             classification=action["classification"], confidence=action["confidence"],
                             branchId=action.get("branchId"))
            self.episodic[seat.agentId].append(f"{round_id} {kind} {claim_id or target_id or ''}: {action['text'][:160]}")
            accepted.append(kind)
        return accepted, rejected

    # ---------------------------------------------------------- R7 audit/critic
    def _audit(self) -> None:
        flagged = [c.id for c in self.claims.values() if c.insufficientGrounding and c.visibility == "public"]
        self.ledger.emit("audit.grounding", round_id="R7", insufficientGrounding=flagged,
                         invalidCitations=sum(len(c.invalidSourceIds) for c in self.claims.values()))

    def _critic(self) -> None:
        """Cross-provider critic: each claim is reviewed by a provider other than its author."""
        theses = [c for c in self._public() if c.status == "active" and c.kind in ("thesis", "revision", "amendment")]
        providers = self.roster.providers
        groups: dict[str, list[Claim]] = {}
        for c in theses:
            others = [p for p in providers if p != c.provider] or providers
            groups.setdefault(others[stable_int(self.seed, c.id) % len(others)], []).append(c)
        validator = Draft202012Validator(prompts.CRITIC_SCHEMA)
        for provider_name, claims in groups.items():
            for chunk in range(0, len(claims), 12):
                batch = claims[chunk:chunk + 12]
                system, user = prompts.critic_prompts(batch, self.snapshot)
                payload, stats = self._call(self._provider(provider_name, "critic"), system, user,
                                            prompts.CRITIC_SCHEMA, "critic_review", validator, self.seed)
                if payload is None:
                    self.ledger.emit("critic.failed", round_id="R7", provider=provider_name, detail=stats["error"])
                    continue
                for review in payload["reviews"]:
                    c = self.claims.get(review["claimId"])
                    if c is None or c not in batch:
                        continue
                    c.criticVerdict = review["verdict"]
                    if review["verdict"] != "groundedInSources" and c.classification == "syntheticPerspective":
                        c.classification = "hypothesis"
                    self.ledger.emit("critic.review", round_id="R7", agent_id=f"critic:{provider_name}",
                                     claim_id=c.id, verdict=review["verdict"], note=review["note"][:500])

    def synthesize(self, tensions: list[dict]) -> dict | None:
        if not self.use_synth or not tensions:
            return None
        provider_name = self.roster.providers[0]
        system, user = prompts.synth_prompts(tensions, self.claims, [q["text"] for q in self.questions],
                                             self.snapshot.scenario)
        payload, stats = self._call(self._provider(provider_name, "synthesizer"), system, user,
                                    prompts.SYNTH_SCHEMA, "synthesis", Draft202012Validator(prompts.SYNTH_SCHEMA),
                                    self.seed)
        self.ledger.emit("synthesis." + ("completed" if payload else "failed"), round_id="R8",
                         provider=provider_name, detail=stats.get("error"))
        return payload
