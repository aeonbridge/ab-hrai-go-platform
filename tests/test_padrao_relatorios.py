"""Checks that HRAI-GO LaTeX documents follow the ABNT NBR 10719:2015 house standard.

Standard: docs/PADRAO_RELATORIOS.md. Style: docs/latex/hraigo-abnt.sty.
Static checks always run; the compile check runs only when latexmk and xelatex are installed.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Registered documents and their identification code (keep in sync with scripts/build-relatorios.sh).
REPORTS = {
    "docs/latex/modelo-relatorio-tecnico.tex": "RT-XXX-00",
    "docs/relatorios/ontologia/relatorio.tex": "RT-ONT-01",
    "docs/especificacoes/ESP-ONT-02/especificacao.tex": "ESP-ONT-02",
    "docs/relatorios/visao/hrai-go-visao.tex": "RT-VIS-03",
    "docs/hrai-go/HRAI-GO_Plataforma_Inteligencia_Regulatoria_Shadow_Council.tex": "DC-PLAT-01",
    "docs/scse/SCSE_Shadow_Council_Simulation_Spec.tex": "ESP-SCSE-01",
}

# Mandatory elements of NBR 10719 (section 4) and how each appears in the source.
MANDATORY = {
    "abnTeX2 class": r"\\documentclass\[[^\]]*12pt[^\]]*\]\{abntex2\}",
    "house style": r"\\usepackage\{hraigo-abnt\}",
    "title page": r"\\imprimirfolhaderostorelatorio",
    "abstract (resumo)": r"\\begin\{resumorelatorio\}",
    "keywords": r"\\palavraschave\{[^}]+\}",
    "summary (sumário)": r"\\tableofcontents\*",
    "textual part": r"\\textual\b",
    "post-textual part": r"\\postextual\b",
    "references": r"\\bibliography\{[^}]*referencias[^}]*\}",
}

# Constructs that bypass the standard layout.
FORBIDDEN = {
    "geometry overrides NBR margins": r"\\usepackage(\[[^\]]*\])?\{geometry\}",
    "fancyhdr overrides abnTeX2 page style": r"\\usepackage(\[[^\]]*\])?\{fancyhdr\}",
    "maketitle instead of NBR title page": r"\\maketitle\b",
    "article-style abstract": r"\\begin\{abstract\}",
    "manual bibliography instead of NBR 6023 via BibTeX": r"\\begin\{thebibliography\}",
    "own titlepage instead of NBR title page": r"\\begin\{titlepage\}",
}


def _read(relpath: str) -> str:
    text = (ROOT / relpath).read_text(encoding="utf-8")
    # Ignore commented-out lines so documentation comments do not count.
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("%"))


@pytest.mark.parametrize("relpath", REPORTS)
@pytest.mark.parametrize("element", MANDATORY)
def test_mandatory_element_present(relpath: str, element: str) -> None:
    assert re.search(MANDATORY[element], _read(relpath)), f"{relpath}: missing {element}"


@pytest.mark.parametrize("relpath", REPORTS)
@pytest.mark.parametrize("construct", FORBIDDEN)
def test_forbidden_construct_absent(relpath: str, construct: str) -> None:
    assert not re.search(FORBIDDEN[construct], _read(relpath)), f"{relpath}: {construct}"


@pytest.mark.parametrize("relpath,code", REPORTS.items())
def test_identification_code(relpath: str, code: str) -> None:
    assert re.search(r"\\codigo\{" + re.escape(code) + r"\}", _read(relpath)), f"{relpath}: code {code}"


def test_build_script_registers_all_reports() -> None:
    script = (ROOT / "scripts/build-relatorios.sh").read_text(encoding="utf-8")
    missing = [p for p in REPORTS if p not in script]
    assert not missing, f"not registered in scripts/build-relatorios.sh: {missing}"


def test_bibliography_corporate_authors_uppercase() -> None:
    bib = (ROOT / "docs/latex/referencias.bib").read_text(encoding="utf-8")
    for name in re.findall(r"author\s*=\s*\{\{([^{}]+)\}", bib):
        assert name == name.upper(), f"corporate author must be uppercase (NBR 6023): {name}"


@pytest.mark.skipif(
    not (shutil.which("latexmk") and shutil.which("xelatex")) or os.environ.get("SKIP_LATEX") == "1",
    reason="latexmk/xelatex not installed",
)
def test_template_compiles(tmp_path: Path) -> None:
    result = subprocess.run(
        [str(ROOT / "scripts/build-relatorios.sh"), "docs/latex/modelo-relatorio-tecnico.tex"],
        cwd=ROOT, capture_output=True, text=True, timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# Authorship: the doctoral candidate is the author; AeonBridge Co. is the sponsor (CLAUDE.md, PADRAO_RELATORIOS.md).
AUTHOR = "Jefferson Wellington da Cunha"
SPONSOR = "AeonBridge Co."


def test_style_sets_author_and_sponsor() -> None:
    sty = (ROOT / "docs/latex/hraigo-abnt.sty").read_text(encoding="utf-8")
    assert f"\\autor{{{AUTHOR}}}" in sty
    assert f"\\patrocinador{{\\href{{https://aeonbridge.com/}}{{{SPONSOR}}}}}" in sty
    assert "jefferson.cunha@ufpe.br" in sty and "jc@aeonbridge.com" in sty


@pytest.mark.parametrize("relpath", REPORTS)
def test_report_does_not_override_authorship(relpath: str) -> None:
    text = _read(relpath)
    override = re.search(r"\\autor\{([^}]*)\}", text)
    assert override is None or override.group(1) == AUTHOR, f"{relpath}: author overridden to {override.group(1)!r}"
    assert not re.search(r"Equipe HRAI-GO|Plataforma HRAI-GO\s*·\s*Aeonbridge", text), f"{relpath}: team named as author"


@pytest.mark.parametrize("relpath", REPORTS)
def test_text_is_black(relpath: str) -> None:
    # NBR text is black; color is allowed only inside illustrations (TikZ figures), never via \textcolor.
    assert "\\textcolor" not in _read(relpath), f"{relpath}: colored text"


def test_headings_use_text_font_at_12pt() -> None:
    sty = (ROOT / "docs/latex/hraigo-abnt.sty").read_text(encoding="utf-8")
    for level in ("chapter", "section", "subsection", "subsubsection", "subsubsubsection"):
        assert f"\\renewcommand{{\\ABNTEX{level}fontsize}}{{\\normalsize}}" in sty, level
        assert re.search(rf"\\renewcommand\{{\\ABNTEX{level}font\}}\{{\\rmfamily", sty), level


def test_sponsor_links_and_acknowledgements() -> None:
    sty = (ROOT / "docs/latex/hraigo-abnt.sty").read_text(encoding="utf-8")
    assert "\\patrocinador{\\href{https://aeonbridge.com/}{AeonBridge Co.}}" in sty
    assert "\\begin{agradecimentos}" in sty and "\\imprimirpatrocinio" in sty
    # Every Shadow Council model configured must be acknowledged in the sponsorship text.
    models = (ROOT / "config/scse/models.toml").read_text(encoding="utf-8")
    for name in ("Opus", "Sonnet", "Haiku", "Grok", "Gemini", "GPT-6"):
        if name.lower().replace("-", "") in models.lower().replace("-", ""):
            assert name in sty, f"model family {name} missing from sponsorship text"
    for doc in ("README.md", "CLAUDE.md", "docs/PADRAO_RELATORIOS.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        assert "AeonBridge Co." not in text or "https://aeonbridge.com/" in text, doc
