"""Hash-chained event ledger (deliberation-events.jsonl)."""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from .world import canonical_json

GENESIS = "0" * 64


class EventLedger:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.events: list[dict] = []
        self._lock = threading.Lock()

    def emit(self, kind: str, *, round_id: str | None = None, agent_id: str | None = None,
             action: str | None = None, claim_id: str | None = None, evidence_ids: list[str] | None = None,
             **payload) -> dict:
        with self._lock:
            prev = self.events[-1]["contentHash"] if self.events else GENESIS
            event = {
                "eventId": f"{self.run_id}:e{len(self.events) + 1:05d}",
                "runId": self.run_id,
                "seq": len(self.events) + 1,
                "type": kind,
                "roundId": round_id,
                "agentId": agent_id,
                "action": action,
                "claimId": claim_id,
                "evidenceIds": evidence_ids or [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": payload,
                "prevHash": prev,
            }
            event["contentHash"] = hashlib.sha256(canonical_json(event).encode()).hexdigest()
            self.events.append(event)
            return event

    def verify(self) -> bool:
        prev = GENESIS
        for ev in self.events:
            body = {k: v for k, v in ev.items() if k != "contentHash"}
            if body["prevHash"] != prev:
                return False
            if hashlib.sha256(canonical_json(body).encode()).hexdigest() != ev["contentHash"]:
                return False
            prev = ev["contentHash"]
        return True

    def write(self, path: Path) -> None:
        with path.open("w", encoding="utf-8") as fh:
            for ev in self.events:
                fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
