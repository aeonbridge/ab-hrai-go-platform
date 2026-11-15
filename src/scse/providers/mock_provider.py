"""Deterministic offline provider used by tests and ``--dry-run``.

It reads the machine-readable ``<turn_context>`` block the deliberation engine
embeds in every prompt and emits schema-valid actions. A ``persona`` (by default
the logical provider it stands in for) shifts behaviour so that experiment
metrics differ between stand-ins; this exercises the pipeline only and says
nothing about the real providers.
"""
from __future__ import annotations

import hashlib
import json
import random
import re

from .base import CompletionRequest, CompletionResult, Provider

_CTX = re.compile(r"<turn_context>\s*(\{.*?\})\s*</turn_context>", re.S)

# probability knobs per persona: (cite_unknown_source, challenge, withdraw_when_challenged)
_PERSONAS = {
    "anthropic": (0.03, 0.55, 0.35),
    "openai": (0.05, 0.50, 0.30),
    "xai": (0.10, 0.70, 0.15),
    "gemini": (0.06, 0.45, 0.40),
    "mock": (0.05, 0.50, 0.30),
}


_STRATUM_TOPICS = {
    "regulators": ["oversight-institutions", "enforcement-capacity", "impact-assessment", "risk-classification", "liability", "monitoring-learning"],
    "publicOperators": ["public-sector-use", "rights-redress", "funding-continuity", "standards-certification", "data-governance"],
    "business": ["sme-competition", "innovation-sandbox", "copyright-ip", "funding-continuity", "standards-certification"],
    "research": ["open-source-science", "monitoring-learning", "data-governance", "language-culture", "workforce-skills"],
    "civilSociety": ["rights-redress", "transparency", "participation", "impact-assessment", "children-vulnerable", "info-integrity"],
    "workers": ["labor-relations", "workforce-skills", "regional-inequality", "participation"],
    "affectedGroups": ["rights-redress", "regional-inequality", "children-vulnerable", "language-culture", "participation"],
    "infrastructure": ["compute-infrastructure", "energy-environment", "data-sovereignty", "security-defense", "international-alignment"],
    "x": ["oversight-institutions", "rights-redress", "funding-continuity", "energy-environment"],
}


class MockProvider(Provider):
    def __init__(self, spec, persona: str | None = None):
        super().__init__(spec)
        self.persona = persona or spec.provider

    def list_models(self) -> list[str]:
        return [self.spec.id]

    def complete(self, req: CompletionRequest) -> CompletionResult:
        if req.schema_name in ("critic_review", "gov_critic", "synthesis", "ping"):
            return self._aux(req)
        match = _CTX.search(req.user)
        ctx = json.loads(match.group(1)) if match else {}
        digest = hashlib.sha256(f"{self.persona}|{req.seed}|{req.user}".encode()).hexdigest()
        rng = random.Random(int(digest[:16], 16))
        p_bad, p_challenge, p_withdraw = _PERSONAS.get(self.persona, _PERSONAS["mock"])
        if ctx.get("mode") == "governanceReview":
            actions = self._gov_actions(ctx, rng, p_bad, p_challenge, p_withdraw)
        else:
            actions = self._actions(ctx, rng, p_bad, p_challenge, p_withdraw)
        payload = {"actions": actions, "insufficientGrounding": rng.random() < 0.1,
                   "notes": f"mock persona={self.persona} round={ctx.get('round')}"}
        text = json.dumps(payload, ensure_ascii=False)
        return CompletionResult(text=text, model_requested=self.spec.id,
                                model_served=f"{self.spec.id}@{self.persona}",
                                input_tokens=len(req.system + req.user) // 4,
                                output_tokens=len(text) // 4, latency_s=0.0, stop_reason="end_turn")

    def _aux(self, req: CompletionRequest) -> CompletionResult:
        rng = random.Random(int(hashlib.sha256(f"{self.persona}|{req.user}".encode()).hexdigest()[:16], 16))
        if req.schema_name == "ping":
            payload = {"ok": True}
        elif req.schema_name == "gov_critic":
            items = json.loads(req.user)
            verdicts = ["groundedInSources", "extrapolatesSources", "unsupported"]
            payload = {"reviews": [{"claimId": it["claimId"],
                                    "verdict": rng.choices(verdicts, weights=[6, 3, 1])[0],
                                    "genericity": rng.choices(["specific", "generic", "unclear"], weights=[6, 3, 1])[0],
                                    "note": "revisão mock"} for it in items]}
        elif req.schema_name == "critic_review":
            items = json.loads(req.user)
            verdicts = ["groundedInSources", "extrapolatesSources", "unsupported"]
            payload = {"reviews": [{"claimId": it["claimId"],
                                    "verdict": rng.choices(verdicts, weights=[6, 3, 1])[0],
                                    "note": "revisão mock"} for it in items]}
        else:
            data = json.loads(req.user)
            payload = {"tensions": [{"id": t["id"], "description": f"[mock] tensão {t['id']} entre objetivos concorrentes."}
                                    for t in data.get("tensions", [])],
                       "unresolvedQuestions": data.get("openEvidenceRequests", [])[:5],
                       "nextActions": ["[mock] validar com especialistas independentes."]}
        text = json.dumps(payload, ensure_ascii=False)
        return CompletionResult(text=text, model_requested=self.spec.id, model_served=f"{self.spec.id}@{self.persona}",
                                input_tokens=len(req.user) // 4, output_tokens=len(text) // 4, stop_reason="end_turn")

    # ------------------------------------------------------------ governanceReview
    @staticmethod
    def _gov(a, **extra):
        a = dict(a)
        a.update({"lens": "none", "topic": "none", "componentId": None, "change": "none", "title": None,
                  "contextFeatureIds": [], "tensionIds": []})
        a.update(extra)
        return a

    def _gov_actions(self, ctx, rng, p_bad, p_challenge, p_withdraw):
        rnd = ctx.get("round")
        allowed = set(ctx.get("allowedActions", []))
        agent = ctx.get("agentId", "agent")
        stratum = (re.match(r"agent:([A-Za-z]+)-", agent) or [None, "x"])[1]
        topics = [t for t in _STRATUM_TOPICS.get(stratum, _STRATUM_TOPICS["x"]) if t in ctx.get("topicIds", [])]
        lenses = ctx.get("lenses", [])
        comps, feats = ctx.get("componentIds", []), ctx.get("featureIds", [])
        findings = ctx.get("visibleFindings", [])
        out = []
        if rnd == "R1":
            picks = rng.sample(topics, k=min(len(topics), rng.choice([3, 4])))
            for t in picks:
                tens = [rng.choice(ctx["tensionIds"])] if ctx.get("tensionIds") and rng.random() < 0.4 else []
                out.append(self._gov(self._act("assertClaim", f"[{agent}] o modelo precisa tratar {t} no contexto desta data.",
                                               self._cite(ctx, rng, p_bad)), lens="expectation", topic=t, tensionIds=tens))
            if rng.random() < 0.15:
                out.append(self._gov(self._act("assertClaim", f"[{agent}] soberania de capacidade de avaliação de modelos.",
                                               self._cite(ctx, rng, p_bad)), lens="expectation", topic="other",
                                     title="Capacidade nacional de avaliação de modelos"))
        elif rnd == "R2":
            gaps = set(ctx.get("gapTopics", []))
            if "omission" in lenses:
                for t in [t for t in ctx.get("ownExpectedTopics", []) if t in gaps][:3]:
                    tens = [rng.choice(ctx["tensionIds"])] if ctx.get("tensionIds") and rng.random() < 0.5 else []
                    out.append(self._gov(self._act("assertClaim", f"[{agent}] o modelo não trata {t}; isso importa agora.",
                                                   self._cite(ctx, rng, p_bad)), lens="omission", topic=t, change="add",
                                         title=f"Considerar {t}", tensionIds=tens))
            if "excess" in lenses and comps and rng.random() < 0.5:
                cid = rng.choice(comps)
                out.append(self._gov(self._act("assertClaim", f"[{agent}] {cid} pesa mais do que entrega neste contexto.",
                                               [*self._cite(ctx, rng, p_bad), cid]), lens="excess", componentId=cid,
                                     change=rng.choice(["remove", "modify"]), title=f"Rever {cid}"))
            if "advantage" in lenses and feats and rng.random() < 0.7:
                fs = sorted(set(rng.sample(feats, k=min(len(feats), rng.choice([1, 2])))))
                change = rng.choice(["add", "modify", "keep"])
                kw = {"topic": rng.choice(topics)} if change == "add" else {"componentId": rng.choice(comps)}
                out.append(self._gov(self._act("assertClaim", f"[{agent}] {fs[0]} sustenta um desenho que outros países não copiam.",
                                               self._cite(ctx, rng, p_bad)), lens="advantage", change=change,
                                     contextFeatureIds=fs, title=f"Explorar {fs[0]}", **kw))
        elif rnd in ("R3", "R4", "R7"):
            out = [self._gov(a) for a in self._actions(ctx, rng, p_bad, p_challenge, p_withdraw)]
        elif rnd == "R5":
            for f in rng.sample(findings, k=min(len(findings), 2)):
                change = f["change"] or "keep"
                kw = {"componentId": f["componentId"]} if f["componentId"] else {}
                topic = f["topic"] or ("none" if change != "add" else ctx["topicIds"][0])
                out.append(self._gov(self._act("proposeAmendment", f"[{agent}] redação proposta para {f['id']}.",
                                               self._cite(ctx, rng, p_bad), target=f["id"]),
                                     lens=f["lens"], change=change, topic=topic, title=f"Proposta de redação ({f['id']})", **kw))
        elif rnd == "R6" and findings:
            for br in ctx.get("branches", []):
                tgt = rng.choice(findings)
                out.append(self._gov(self._act("assertClaim", f"[{agent}] sob {br['id']}, {tgt['id']} continua plausível.",
                                               self._cite(ctx, rng, p_bad), target=tgt["id"], branch=br["id"],
                                               cls="hypothesis", conf="low")))
        return [a for a in out if a["action"] in allowed] or [self._gov(self._act("abstain", "-", []))]

    @staticmethod
    def _act(action, text, sources, target=None, branch=None, cls="syntheticPerspective", conf="medium"):
        return {"action": action, "targetClaimId": target, "branchId": branch, "text": text,
                "sourceIds": sources, "classification": cls, "confidence": conf}

    def _cite(self, ctx, rng, p_bad):
        pool = ctx.get("sourceIds") or []
        if not pool or rng.random() < p_bad:
            return ["UNREGISTERED-SOURCE"]
        return sorted(set(rng.sample(pool, k=min(len(pool), rng.choice([1, 2])))))

    def _actions(self, ctx, rng, p_bad, p_challenge, p_withdraw):
        rnd = ctx.get("round")
        allowed = set(ctx.get("allowedActions", []))
        agent = ctx.get("agentId", "agent")
        own = ctx.get("ownClaimIds", [])
        others = [c for c in ctx.get("visibleClaimIds", []) if c not in own]
        out = []
        if rnd in ("R1", "R2"):
            for i in range(rng.choice([1, 2])):
                out.append(self._act("assertClaim", f"[{agent}] tese {rnd}.{i}: a execução do PBIA exige "
                                     f"salvaguarda e capacidade institucional proporcionais.",
                                     self._cite(ctx, rng, p_bad), cls=rng.choice(["syntheticPerspective", "hypothesis"])))
            if rnd == "R2" and "requestEvidence" in allowed and rng.random() < 0.3:
                out.append(self._act("requestEvidence", "Qual a série de execução orçamentária por eixo?", []))
        elif rnd == "R3":
            if others and rng.random() < p_challenge:
                tgt = rng.choice(others)
                out.append(self._act("challenge", f"[{agent}] contesta {tgt}: premissa sem lastro suficiente.",
                                     self._cite(ctx, rng, p_bad), target=tgt))
            if others and rng.random() < 0.5:
                out.append(self._act("support", f"[{agent}] apoia.", self._cite(ctx, rng, p_bad),
                                     target=rng.choice(others)))
            if not out:
                out.append(self._act("abstain", "Sem objeções materiais.", []))
        elif rnd == "R4":
            for item in ctx.get("challengesToOwnClaims", []):
                cid = item["claimId"]
                r = rng.random()
                if r < p_withdraw:
                    out.append(self._act("withdraw", f"Retiro {cid} diante da objeção.", [], target=cid))
                elif r < p_withdraw + 0.35:
                    out.append(self._act("revise", f"[{agent}] revisão de {cid} com condição explícita.",
                                         self._cite(ctx, rng, p_bad), target=cid))
            if not out:
                out.append(self._act("abstain", "Mantenho posições.", []))
        elif rnd == "R5":
            if ctx.get("visibleClaimIds"):
                out.append(self._act("proposeAmendment", f"[{agent}] propõe salvaguarda escalonada por risco.",
                                     self._cite(ctx, rng, p_bad), target=rng.choice(ctx["visibleClaimIds"])))
        elif rnd == "R6":
            for br in ctx.get("branches", []):
                out.append(self._act("assertClaim", f"[{agent}] sob {br['id']}: efeito condicional plausível.",
                                     self._cite(ctx, rng, p_bad), branch=br["id"], cls="hypothesis", conf="low"))
        elif rnd == "R7":
            contested = [c["claimId"] for c in ctx.get("challengesToOwnClaims", [])]
            if contested and rng.random() < 0.5:
                out.append(self._act("submitMinorityOpinion", f"[{agent}] mantém dissenso fundamentado.",
                                     self._cite(ctx, rng, p_bad), target=contested[0]))
            else:
                out.append(self._act("abstain", "Sem relatório minoritário.", []))
        return [a for a in out if a["action"] in allowed] or [self._act("abstain", "-", [])]
