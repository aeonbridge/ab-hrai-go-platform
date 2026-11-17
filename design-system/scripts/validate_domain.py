#!/usr/bin/env python3
"""Validate tokens/domain.tokens.json against the rules in docs/03-semantica-de-dominio.md.

Checks, per domain group:
  * every value has a pt-BR and an en label;
  * every tone exists in BOTH semantic themes (color.tone.<tone>);
  * every stroke is a valid DTCG strokeStyle keyword;
  * icons are unique inside a group (color is never the only carrier);
  * the full signature (icon, stroke, tone) is unique inside a group;
  * no binding-capable state uses the 'iris' tone (iris is reserved for non-binding content).

Exits 1 on any error. Standard library only.

Usage: python3 scripts/validate_domain.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "tokens"
STROKES = {"solid", "dashed", "dotted", "double", "groove", "ridge", "outset", "inset"}
# Groups whose values can bind someone legally; iris must not appear in them except
# for values that are explicitly non-binding.
IRIS_ALLOWED = {
    ("bindingness", "nonBinding"),
    ("normativeState", "proposed"),
    ("normativeState", "underDeliberation"),
    ("normativeState", "approved"),
    ("obligationStatus", "legalUncertainty"),
    ("epistemicKind", "agentHypothesis"),
    ("epistemicKind", "normativeProposal"),
    ("module", "foresight"),
    ("knowledgeGraph", "comparative"),
}


def themes_tones() -> set[str]:
    sets = []
    for name in ("light", "dark"):
        data = json.loads((TOKENS / f"semantic.{name}.tokens.json").read_text())
        sets.append({k for k in data["color"]["tone"] if not k.startswith("$")})
    return sets[0] & sets[1]


def main() -> int:
    domain = json.loads((TOKENS / "domain.tokens.json").read_text())
    tones = themes_tones()
    errors: list[str] = []
    count = 0
    for group, values in domain.items():
        if group.startswith("$"):
            continue
        icons: dict[str, str] = {}
        signatures: dict[tuple, str] = {}
        for key, entry in values.items():
            if key.startswith("$"):
                continue
            count += 1
            where = f"{group}.{key}"
            ext = entry.get("$extensions", {}).get("org.hraigo", {})
            label = ext.get("label", {})
            if not label.get("pt-BR") or not label.get("en"):
                errors.append(f"{where}: missing pt-BR or en label")
            tone = entry.get("tone", {}).get("$value")
            if tone is not None and tone not in tones:
                errors.append(f"{where}: tone '{tone}' not defined in both themes")
            stroke = entry.get("stroke", {}).get("$value")
            if stroke is not None and stroke not in STROKES:
                errors.append(f"{where}: invalid stroke '{stroke}'")
            if tone == "iris" and (group, key) not in IRIS_ALLOWED:
                errors.append(f"{where}: iris is reserved for non-binding content")
            icon = ext.get("icon")
            if icon:
                if icon in icons:
                    errors.append(f"{where}: icon {icon} already used by {group}.{icons[icon]}")
                icons[icon] = key
            sig = (icon, stroke, tone)
            if icon and sig in signatures:
                errors.append(f"{where}: same signature as {group}.{signatures[sig]}")
            signatures[sig] = key
    for e in errors:
        print("ERROR", e)
    print(f"checked {count} domain values, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
