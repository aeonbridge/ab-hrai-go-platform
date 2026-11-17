#!/usr/bin/env python3
"""Measure WCAG 2.2 contrast for every HRAI-GO semantic color pair, in both themes.

Reads the DTCG token files, resolves {aliases}, computes the WCAG relative
luminance contrast ratio for each declared pair and writes
docs/contrast-report.md. Exits with status 1 if any pair is below its threshold,
so it can run in CI.

Usage:
    python3 scripts/contrast_check.py            # write report, fail on violations
    python3 scripts/contrast_check.py --stdout   # print report instead of writing it

Standard library only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "tokens"
REPORT = ROOT / "docs" / "contrast-report.md"

TEXT = 4.5  # WCAG 1.4.3, normal text
NON_TEXT = 3.0  # WCAG 1.4.11, UI component boundaries and meaningful graphics

TONES = ["neutral", "civic", "verdant", "crimson", "ochre", "iris", "lagoon"]
SURFACES = ["bg.canvas", "bg.surface", "bg.subtle"]
GLASS = ["bg.glass", "bg.glassStrong"]  # tema camara: compostos sobre bg.canvas antes de medir


def pairs() -> list[tuple[str, str, float, str]]:
    """(foreground token, background token, minimum ratio, what the pair is used for)."""
    out: list[tuple[str, str, float, str]] = []
    for fg in ["text.primary", "text.secondary", "text.tertiary", "text.link"]:
        for bg in SURFACES:
            out.append((fg, bg, TEXT, "body text"))
    out.append(("text.inverse", "bg.inverse", TEXT, "tooltip / toast"))
    for state in ["bg", "bgHover", "bgPress"]:
        out.append(("action.primary.fg", f"action.primary.{state}", TEXT, "primary button label"))
    for state in ["bg", "bgHover"]:
        out.append(("action.secondary.fg", f"action.secondary.{state}", TEXT, "secondary button label"))
        out.append(("action.danger.fg", f"action.danger.{state}", TEXT, "danger button label"))
    out.append(("action.secondary.border", "bg.surface", NON_TEXT, "secondary button outline"))
    out.append(("action.selected.fg", "action.selected.bg", TEXT, "selected nav item"))
    out.append(("action.selected.indicator", "bg.surface", NON_TEXT, "selection indicator bar"))
    for bg in SURFACES:
        out.append(("border.control", bg, NON_TEXT, "input boundary"))
        out.append(("border.focus", bg, NON_TEXT, "focus ring"))
    for tone in TONES:
        t = f"tone.{tone}"
        out.append((f"{t}.fg", f"{t}.bg", TEXT, "badge label on tint"))
        for bg in SURFACES:
            out.append((f"{t}.fg", bg, TEXT, "status text on surface"))
        out.append((f"{t}.border", "bg.surface", NON_TEXT, "badge/card outline"))
        out.append((f"{t}.border", f"{t}.bg", NON_TEXT, "outline on its own tint"))
        out.append((f"{t}.solidFg", f"{t}.solid", TEXT, "solid badge label"))
    out.append(("simulation.labelFg", "simulation.hatchBg", TEXT, "simulation label on hatch"))
    out.append(("simulation.labelFg", "simulation.hatchLine", TEXT, "simulation label over stripe"))
    return out


def flatten(node: dict, prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in node.items():
        if key.startswith("$"):
            continue
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and "$value" in value:
            flat[path] = value["$value"]
        elif isinstance(value, dict):
            flat.update(flatten(value, path))
    return flat


ALIAS = re.compile(r"^\{([^}]+)\}$")


def resolve(value, table: dict, depth: int = 0) -> str:
    if depth > 10:
        raise ValueError(f"alias loop at {value}")
    if isinstance(value, str):
        m = ALIAS.match(value)
        if m:
            return resolve(table[m.group(1)], table, depth + 1)
    return value


def rgba(hex_value: str) -> tuple[float, float, float, float]:
    h = hex_value.lstrip("#")
    if len(h) not in (6, 8):
        raise ValueError(f"unsupported color {hex_value}")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return r, g, b, a


def luminance(rgb: tuple[float, float, float]) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg_hex: str, bg_hex: str) -> float:
    fr, fgc, fb, fa = rgba(fg_hex)
    br, bgc, bb, _ = rgba(bg_hex)
    # Composite a translucent foreground over the (opaque) background.
    comp = (fr * fa + br * (1 - fa), fgc * fa + bgc * (1 - fa), fb * fa + bb * (1 - fa))
    l1, l2 = luminance(comp), luminance((br, bgc, bb))
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def composite(top_hex: str, under_hex: str) -> str:
    """Flatten a translucent color over an opaque one, returning #RRGGBB."""
    tr, tg, tb, ta = rgba(top_hex)
    ur, ug, ub, _ = rgba(under_hex)
    mix = (tr * ta + ur * (1 - ta), tg * ta + ug * (1 - ta), tb * ta + ub * (1 - ta))
    return "#" + "".join(f"{round(c * 255):02X}" for c in mix)


def load_theme(name: str) -> dict[str, str]:
    primitives = flatten(json.loads((TOKENS / "primitives.tokens.json").read_text()))
    semantic = flatten(json.loads((TOKENS / f"semantic.{name}.tokens.json").read_text()))
    table = {**primitives, **semantic}
    return {k.removeprefix("color."): resolve(v, table) for k, v in semantic.items() if k.startswith("color.")}


def main() -> int:
    lines = [
        "# Contrast report (generated)",
        "",
        "Generated by `scripts/contrast_check.py` from the token files. Do not edit by hand.",
        f"Thresholds: text {TEXT}:1 (WCAG 1.4.3), non-text {NON_TEXT}:1 (WCAG 1.4.11).",
        "",
    ]
    failures = 0
    for theme in ["camara", "light", "dark"]:
        colors = load_theme(theme)
        theme_pairs = pairs()
        for g in GLASS:
            if g in colors:
                colors[g] = composite(colors[g], colors["bg.canvas"])
                for fg in ["text.primary", "text.secondary", "text.tertiary", "text.link"]:
                    theme_pairs.append((fg, g, TEXT, "text on translucent panel over canvas"))
                for tone in TONES:
                    theme_pairs.append((f"tone.{tone}.fg", g, TEXT, "status text on translucent panel"))
        lines += [f"## {theme}", "", "| Foreground | Background | Use | Ratio | Min | Result |", "|---|---|---|---:|---:|---|"]
        for fg, bg, minimum, use in theme_pairs:
            r = ratio(colors[fg], colors[bg])
            ok = r >= minimum
            failures += not ok
            lines.append(
                f"| `{fg}` {colors[fg]} | `{bg}` {colors[bg]} | {use} | {r:.2f} | {minimum} | {'pass' if ok else '**FAIL**'} |"
            )
        lines.append("")
    lines.append(f"Total failures: {failures}")
    report = "\n".join(lines) + "\n"
    if "--stdout" in sys.argv:
        print(report)
    else:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(report)
        print(f"wrote {REPORT} ({failures} failures)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
