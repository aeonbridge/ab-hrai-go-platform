"""Guards the official platform name defined in docs/NOMENCLATURA.md.

HRAI-GO = Human-centred Regulatory AI, Governance Observatory.
The legacy expansion "High-Risk AI" must not come back as the meaning of the acronym.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Canonical expansion of the acronym; must match docs/NOMENCLATURA.md exactly.
CANONICAL = "Human-centred Regulatory AI, Governance Observatory"

# Entry points where a reader first meets the name; each must state the full expansion.
ENTRY_POINTS = [
    "docs/NOMENCLATURA.md",
    "CLAUDE.md",
    "README.md",
    "pyproject.toml",
    "web/index.html",
    "web/README.md",
    "design-system/README.md",
    "ontologies/regulatory/README.md",
    "docs/scse/SCSE_README.md",
    "docs/hrai-go/HRAI-GO_Plataforma_Inteligencia_Regulatoria_Shadow_Council.tex",
]

# Text file types scanned for a forbidden expansion of the acronym.
TEXT_SUFFIXES = {".md", ".tex", ".html", ".js", ".py", ".toml", ".json", ".ttl", ".owl", ".txt"}

# Directories that hold generated output, vendored code or scratch material.
SKIP_DIRS = {".git", "node_modules", ".venv", "graphify-out", ".superpowers", ".taste-skill", "__pycache__", "vendor"}

# "HRAI-GO" (or HRAI) presented as standing for High-Risk AI, in either order.
FORBIDDEN = re.compile(
    r"HRAI(?:-GO)?\s*(?:[:=(—–-]|significa|means|stands for)\s*\(?\s*High[- ]Risk"
    r"|High[- ]Risk\s+AI\s*\(\s*HRAI-GO\s*\)",
    re.IGNORECASE,
)

# Files allowed to mention the legacy meaning, because they document it as retired.
LEGACY_EXPLAINERS = {"docs/NOMENCLATURA.md", "README.md", "CLAUDE.md", "ontologies/regulatory/README.md"}


@pytest.mark.parametrize("relpath", ENTRY_POINTS)
def test_entry_point_states_canonical_name(relpath: str) -> None:
    text = (ROOT / relpath).read_text(encoding="utf-8")
    assert CANONICAL in text, f"{relpath} must state 'HRAI-GO: {CANONICAL}'"


def test_canonical_doc_declares_full_name() -> None:
    text = (ROOT / "docs/NOMENCLATURA.md").read_text(encoding="utf-8")
    assert f"HRAI-GO: {CANONICAL}" in text


def _scanned_files():
    for path in ROOT.rglob("*"):
        if path.suffix not in TEXT_SUFFIXES or not path.is_file():
            continue
        if SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
            continue
        yield path


def test_no_file_expands_hrai_as_high_risk() -> None:
    offenders = []
    for path in _scanned_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in LEGACY_EXPLAINERS or rel == "tests/test_nomenclatura.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if FORBIDDEN.search(text):
            offenders.append(rel)
    assert not offenders, f"Legacy 'High-Risk AI' expansion of HRAI-GO found in: {offenders}"
