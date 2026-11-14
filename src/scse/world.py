"""Scenario loading, contract validation and frozen WorldSnapshot (R0 Prepare)."""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from .config import REPO_ROOT

SCHEMA_DIR = REPO_ROOT / "schemas" / "scse"
WORLD_URN = "urn:scse:world:"


class ScenarioError(ValueError):
    pass


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_schema(stem: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{stem}.schema.json").read_text(encoding="utf-8"))


def validate(instance: dict, stem: str) -> list[str]:
    """FR-01: return field-level errors (empty list when valid)."""
    validator = Draft202012Validator(load_schema(stem), format_checker=FormatChecker())
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))]


def allocate_seats(strata: list[dict], target: int) -> dict[str, int]:
    """Largest-remainder scaling of documented quotas to ``target`` (min 1 each)."""
    base = {s["id"]: s["seats"] for s in strata}
    total = sum(base.values())
    if target == total:
        return base
    if target < len(base):
        raise ScenarioError(f"targetSeats={target} smaller than number of strata ({len(base)})")
    raw = {k: v * target / total for k, v in base.items()}
    out = {k: max(1, int(v)) for k, v in raw.items()}
    order = sorted(raw, key=lambda k: (raw[k] - int(raw[k]), base[k]), reverse=True)
    i = 0
    while sum(out.values()) < target:
        out[order[i % len(order)]] += 1
        i += 1
    while sum(out.values()) > target:
        k = max((k for k in out if out[k] > 1), key=lambda k: out[k] - raw[k])
        out[k] -= 1
    return out


@dataclass
class WorldSnapshot:
    scenario: dict
    world: dict
    seat_plan: dict[str, int]
    snapshot_hash: str
    scenario_path: str | None = None

    @property
    def evidence_ids(self) -> set[str]:
        ids = {e["id"] for e in self.world.get("evidence", [])}
        ids |= {s["id"] for s in self.scenario.get("regulatorySources", [])}
        ids |= {s["id"] for s in self.scenario.get("contextSources", [])}
        return ids

    def evidence(self, eid: str) -> dict | None:
        for e in self.world.get("evidence", []):
            if e["id"] == eid:
                return e
        for s in self.scenario.get("regulatorySources", []) + self.scenario.get("contextSources", []):
            if s["id"] == eid:
                return s
        return None

    def as_document(self) -> dict:
        return {
            "@context": {"scse": "https://github.com/aeonbridge/ab-hrai-go-platform/ontology/scse#"},
            "@type": "scse:WorldSnapshot",
            "snapshotHash": self.snapshot_hash,
            "scenario": self.scenario,
            "world": self.world,
            "seatPlan": self.seat_plan,
        }


def _resolve_world(scenario: dict, scenario_path: Path | None) -> dict:
    for src in scenario.get("contextSources", []):
        if src["uri"].startswith(WORLD_URN):
            name = src["uri"][len(WORLD_URN):]
            candidates = []
            if scenario_path:
                candidates.append(scenario_path.parent / "world.json")
            candidates.append(REPO_ROOT / "scenarios" / name / "world.json")
            for c in candidates:
                if c.exists():
                    world = json.loads(c.read_text(encoding="utf-8"))
                    if world.get("worldId", "").startswith(name) or c.parent.name == name:
                        return world
            raise ScenarioError(f"world pack {name!r} not found (looked in {', '.join(map(str, candidates))})")
    return {"worldId": "empty", "fictional": False, "evidence": [], "contextIndicators": [], "strata": []}


def prepare(scenario: dict, *, scenario_path: str | Path | None = None,
            seats_override: int | None = None) -> WorldSnapshot:
    errors = validate(scenario, "scenario")
    if errors:
        raise ScenarioError("scenario contract violations:\n  " + "\n  ".join(errors))
    path = Path(scenario_path) if scenario_path else None
    world = _resolve_world(scenario, path)
    if not world.get("strata"):
        raise ScenarioError("world pack defines no strata; council cannot be composed")
    strata = copy.deepcopy(world["strata"])
    for override in scenario["council"].get("strata", []):
        match = next((s for s in strata if s["id"] == override["id"]), None)
        if match is None:
            raise ScenarioError(f"council.strata references unknown stratum {override['id']!r}")
        match["seats"] = override["seats"]
        if override.get("sourceIds"):
            match["sourceIds"] = override["sourceIds"]
    world = {**world, "strata": strata}
    target = seats_override or scenario["council"]["targetSeats"]
    seat_plan = allocate_seats(strata, target)
    frozen = {"scenario": scenario, "world": world, "seatPlan": seat_plan}
    return WorldSnapshot(scenario=scenario, world=world, seat_plan=seat_plan,
                         snapshot_hash=sha256_json(frozen), scenario_path=str(path) if path else None)


def load_scenario(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
