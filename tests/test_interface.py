"""Item 15: comparator generated from the graph, declared limits in the interface (V-25), touch targets (V-18)."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_comparator_is_generated_and_shows_limits_matrix_and_specificities():
    assert subprocess.run([sys.executable, str(ROOT / "scripts/ontologia/build_comparador.py"), "--check"]).returncode == 0
    page = (ROOT / "web/comparador/index.html").read_text(encoding="utf-8")
    for text in ("Limites declarados", "Não é aconselhamento jurídico", "Critérios da taxonomia", "Dispositivos lado a lado",
                 "Incorporado sem capacidade", "O que é próprio do Brasil"):
        assert text in page, text
    assert page.count("<tr><td><b>C") >= 25
    assert 'href="comparador/"' in (ROOT / "web/index.html").read_text(encoding="utf-8")


def test_fichas_show_the_limits():
    camara = (ROOT / "web/ao-vivo/index.html").read_text(encoding="utf-8")
    assert 'class="limite"' in camara and "não é aconselhamento jurídico" in camara


def test_touch_targets_declare_44px():
    """Static guard; the measured check in the browser found every visible control at 44 px or more (PROGRESSO, item 15)."""
    css = (ROOT / "web/assets/hraigo.css").read_text(encoding="utf-8")
    camara = (ROOT / "web/ao-vivo/index.html").read_text(encoding="utf-8")
    assert re.search(r"\.bt,\.opcao,\.mov\{min-height:44px\}", css)
    assert ".abas button,.reacoes button,#gaveta button,#ficha .fx,#voce,.chip.cta{min-height:44px;min-width:44px}" in camara
    assert "html body.participante #voce{min-height:44px}" in camara and ".pav::before" in camara
