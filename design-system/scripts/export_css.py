#!/usr/bin/env python3
"""Export a semantic theme to CSS custom properties.

Usage: python3 design-system/scripts/export_css.py camara web/assets/tokens.css
Writes --color-<path> for every semantic color (aliases resolved), plus font families.
Standard library only; same resolution rules as contrast_check.py.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from contrast_check import TOKENS, flatten, resolve  # noqa: E402


def main(theme: str, out: str) -> None:
    primitives = flatten(json.loads((TOKENS / "primitives.tokens.json").read_text()))
    semantic = flatten(json.loads((TOKENS / f"semantic.{theme}.tokens.json").read_text()))
    table = {**primitives, **semantic}
    lines = [f"/* GERADO por design-system/scripts/export_css.py a partir do tema '{theme}'. Não editar à mão. */", ":root{"]
    for key, value in semantic.items():
        if key.startswith("color."):
            lines.append(f"  --{key.replace('.', '-')}:{resolve(value, table)};")
    for group in ("stratum", "provider"):
        for key, value in primitives.items():
            if key.startswith(f"color.{group}."):
                lines.append(f"  --{key.replace('.', '-')}:{value};")
    fam = json.loads((TOKENS / "primitives.tokens.json").read_text())["font"]["family"]
    for name, node in fam.items():
        if not name.startswith("$"):
            stack = ",".join(f'"{f}"' if " " in f else f for f in node["$value"])
            lines.append(f"  --font-{name}:{stack};")
    lines.append(f"  color-scheme:{'light' if theme == 'light' else 'dark'};")
    lines.append("}")
    Path(out).write_text("\n".join(lines) + "\n")
    print(f"wrote {out} ({len(lines) - 3} variables)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
