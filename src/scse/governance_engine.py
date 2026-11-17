"""GovernanceEngine: the council examines a governance model; it proposes, humans decide.

Round mapping (same R1-R7 state machine, different content):
  R1 BlindExpectations   seats list what a national AI governance model must consider, WITHOUT the model
  R2 ModelReview         model revealed; findings in three lenses (omission / excess / advantage)
  R3 CrossExamination    challenge, support, request evidence
  R4 EvidenceRevision    keep, revise or withdraw
  R5 ChangeProposals     concrete changes to the model (add / modify / remove / keep)
  R6 ContextStress       do the findings survive the context branches (bill passes, funding cut, ...)
  R7 MinorityAndAudit    dissent preserved; grounding audited; genericity checked
"""
from __future__ import annotations

from jsonschema import Draft202012Validator

from . import gov_prompts as gp
from .deliberation import Claim, DeliberationEngine, stable_int
from .governance import LENSES, build_packet, coverage_matrix


class GovernanceEngine(DeliberationEngine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.snapshot.governance is None:
            raise ValueError("GovernanceEngine needs a governanceReview scenario")
        self.bundle = self.snapshot.governance
        self._schema = gp.turn_schema(self.bundle.topic_ids)
        self._validator = Draft202012Validator(self._schema)
        self._aggregated: list[dict] = []
        self._coverage: list[dict] = []

    # --------------------------------------------------------------- hooks
    def _round_name(self, round_id):
        return gp.ROUND_NAMES[round_id]

    def _round_actions(self, round_id):
        return gp.ROUND_ACTIONS[round_id]

    def _max_actions(self, round_id):
        return max(self.max_actions, 6) if round_id in ("R1", "R2") else self.max_actions

    def _system_prompt(self, seat, round_id):
        return gp.system_prompt(seat, self.snapshot, show_model=(round_id != "R1"))

    def _user_prompt(self, round_id, seat, inputs):
        extras = {}
        if round_id == "R2":
            extras = {"expectations": self._aggregated,
                      "coverage": [self._cov_view(r) for r in self._coverage if r["expectedBySeats"]]}
        elif round_id == "R5":
            extras = {"coverage": [self._cov_view(r) for r in self._coverage if r["gap"] or r["fragile"]]}
        return gp.user_prompt(round_id, seat, inputs, self.bundle, extras)

    def _turn_schema(self):
        return self._schema, self._validator, "gov_turn"

    @staticmethod
    def _cov_view(r):
        return {"topic": r["topic"], "label": r["label"], "expectedBySeats": r["expectedBySeats"],
                "coverageStrength": r["coverageStrength"], "gap": r["gap"], "fragile": r["fragile"],
                "coveredBy": [x["componentId"] for x in r["coveredBy"]]}

    # ----------------------------------------------------------- expectations
    def expectations(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for c in self.claims.values():
            if c.lens != "expectation" or c.status == "withdrawn":
                continue
            key = c.topic or "other"
            e = out.setdefault(key, {"seats": set(), "strata": set(), "titles": set()})
            e["seats"].add(c.agentId)
            e["strata"].add(c.stratumId)
            if key == "other" and c.title:
                e["titles"].add(c.title)
        return out

    def _after_round(self, round_id):
        if round_id != "R1":
            return
        exp = self.expectations()
        labels = {t["id"]: t["label"] for t in self.bundle.taxonomy["topics"]}
        self._aggregated = sorted(
            ({"topic": k, "label": labels.get(k, "Fora da taxonomia"), "seats": len(v["seats"]),
              "strata": sorted(v["strata"]), **({"titles": sorted(v["titles"])} if k == "other" else {})}
             for k, v in exp.items()), key=lambda r: (-r["seats"], r["topic"]))
        self._coverage = coverage_matrix(self.bundle.model, self.bundle.taxonomy, exp)
        self.ledger.emit("expectations.aggregated", round_id="R1", topics=len(self._aggregated),
                         gaps=[r["topic"] for r in self._coverage if r["gap"]],
                         fragile=[r["topic"] for r in self._coverage if r["fragile"]])

    # ------------------------------------------------------------ rules per lens
    def _extra_validate(self, seat, round_id, action, target):
        b = self.bundle
        kind = action["action"]
        lens = action.get("lens", "none")
        topic = action.get("topic", "none")
        cid = action.get("componentId")
        change = action.get("change", "none")
        feats = action.get("contextFeatureIds") or []
        title = action.get("title")
        if topic not in (*b.topic_ids, "other", "none"):
            return f"unknown topic {topic!r}"
        if cid and b.component(cid) is None:
            return f"unknown componentId {cid!r}"
        bad = [f for f in feats if f not in b.feature_ids]
        if bad:
            return f"unknown contextFeatureIds {bad}"
        bad = [t for t in action.get("tensionIds") or [] if t not in b.seed_ids]
        if bad:
            return f"unknown tensionIds {bad}"
        if kind == "assertClaim":
            if round_id == "R1":
                if lens != "expectation":
                    return "R1 claims must use lens=expectation"
                if topic == "none" or (topic == "other" and not title):
                    return "R1 expectation needs a taxonomy topic (or topic=other with a title)"
                if cid:
                    return "R1 is blind: componentId is not allowed"
            elif round_id == "R2":
                if lens not in b.lenses:
                    return f"lens {lens!r} is not enabled; use one of {b.lenses}"
                topic_ok = topic != "none" and (topic != "other" or bool(title))
                if lens == "omission":
                    if change not in ("add", "modify"):
                        return "omission needs change=add (or modify for partial coverage)"
                    if change == "modify" and not cid:
                        return "omission with change=modify needs componentId"
                    if not topic_ok:
                        return "omission needs a topic (or topic=other with a title)"
                elif lens == "excess":
                    if not cid:
                        return "excess needs the componentId of the component in question"
                    if change not in ("remove", "modify"):
                        return "excess needs change=remove or modify"
                elif lens == "advantage":
                    if not feats:
                        return "advantage needs at least one contextFeatureIds entry"
                    if change not in ("add", "modify", "keep"):
                        return "advantage needs change=add, modify or keep"
                    if change in ("modify", "keep") and not cid:
                        return "advantage with modify/keep needs componentId"
                    if change == "add" and not topic_ok:
                        return "advantage with add needs a topic (or topic=other with a title)"
            elif round_id == "R6":
                if target is None or target.visibility != "public" or target.lens not in LENSES:
                    return "R6 assertions must target a public finding (targetClaimId)"
        elif kind == "proposeAmendment":
            if target is not None and target.lens not in LENSES:
                return "amendments must target a finding that carries a lens"
            if change not in ("add", "modify", "remove", "keep"):
                return "amendment needs change=add, modify, remove or keep"
            if change in ("modify", "remove") and not cid:
                return f"amendment with change={change} needs componentId"
            if change == "add" and topic == "none":
                return "amendment with change=add needs a topic"
        return None

    def _decorate_claim(self, claim: Claim, action: dict, target) -> None:
        if claim.kind not in ("thesis", "amendment", "revision"):
            return
        lens = action.get("lens", "none")
        claim.lens = None if lens == "none" else lens
        claim.topic = None if action.get("topic", "none") == "none" else action["topic"]
        claim.componentId = action.get("componentId")
        claim.change = None if action.get("change", "none") == "none" else action["change"]
        claim.title = action.get("title")
        claim.contextFeatureIds = list(dict.fromkeys(action.get("contextFeatureIds") or []))
        claim.tensionIds = list(dict.fromkeys(action.get("tensionIds") or []))
        if claim.kind in ("amendment", "revision") and target is not None:
            claim.lens = target.lens
            if claim.kind == "revision":
                for f in ("topic", "componentId", "change", "title"):
                    if getattr(claim, f) is None:
                        setattr(claim, f, getattr(target, f))
                claim.contextFeatureIds = claim.contextFeatureIds or list(target.contextFeatureIds)
                claim.tensionIds = claim.tensionIds or list(target.tensionIds)
            elif claim.topic is None:
                claim.topic = target.topic
        # context features count as grounding for Q3 findings
        if claim.contextFeatureIds and not claim.invalidSourceIds:
            claim.insufficientGrounding = False
            if action["classification"] == "syntheticPerspective":
                claim.classification = "syntheticPerspective"

    # --------------------------------------------------------------- critic
    def _critic(self) -> None:
        reviewable = [c for c in self._public() if c.status == "active" and c.lens in LENSES
                      and c.kind in ("thesis", "revision", "amendment")]
        providers = self.roster.providers
        groups: dict[str, list[Claim]] = {}
        for c in reviewable:
            others = [p for p in providers if p != c.provider] or providers
            groups.setdefault(others[stable_int(self.seed, c.id) % len(others)], []).append(c)
        validator = Draft202012Validator(gp.CRITIC_SCHEMA)
        for provider_name, claims in groups.items():
            for i in range(0, len(claims), 12):
                batch = claims[i:i + 12]
                system, user = gp.critic_prompts(batch, self.snapshot)
                payload, stats = self._call(self._provider(provider_name, "critic"), system, user,
                                            gp.CRITIC_SCHEMA, "gov_critic", validator, self.seed)
                if payload is None:
                    self.ledger.emit("critic.failed", round_id="R7", provider=provider_name, detail=stats["error"])
                    continue
                for r in payload["reviews"]:
                    c = self.claims.get(r["claimId"])
                    if c is None or c not in batch:
                        continue
                    c.criticVerdict, c.genericity = r["verdict"], r["genericity"]
                    if r["verdict"] != "groundedInSources" and c.classification == "syntheticPerspective":
                        c.classification = "hypothesis"
                    self.ledger.emit("critic.review", round_id="R7", agent_id=f"critic:{provider_name}",
                                     claim_id=c.id, verdict=r["verdict"], genericity=r["genericity"], note=r["note"][:500])

    def synthesize(self, tensions):  # the packet is deterministic; no model-written synthesis
        return None

    def packet(self) -> dict:
        return build_packet(self)
