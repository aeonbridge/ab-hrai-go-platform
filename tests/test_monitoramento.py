"""M10 / V-23: a new version of the PL reopens provisions, requirements, codings, specificities and claims."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MON = ROOT / "web/assets/monitoramento.js"


def data():
    return json.loads(MON.read_text(encoding="utf-8").split("=", 1)[1].rstrip(";\n"))


def test_queue_is_generated_from_the_graph():
    assert subprocess.run([sys.executable, str(ROOT / "scripts/ontologia/monitorar.py"), "--check"]).returncode == 0


def test_senate_text_reopens_provisions_requirements_and_claims():
    ev = next(e for e in data()["eventos"] if "aprovado pelo Senado" in e["rotulo"])
    assert ev["reaberto"]["dispositivo"] == 79
    assert ev["reaberto"]["requisito"] >= 3
    assert any("instância consultiva técnica independente" in a for a in ev["itens"]["afirmação"])  # thesis C04


def test_monitoring_page_reads_the_queue():
    assert 'assets/monitoramento.js' in (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "HRAIGO_MONITOR" in (ROOT / "web/assets/app.js").read_text(encoding="utf-8")
