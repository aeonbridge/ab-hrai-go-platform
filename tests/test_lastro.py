"""RF-12 / RF-15: counter of displayed elements without ontology backing, seal and slide."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lastro", ROOT / "scripts/ontologia/lastro.py")
lastro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lastro)


def test_counter_covers_the_seven_sets_and_matches_alignment():
    data = lastro.build()
    modelo = lastro.load_modelo()
    assert set(data["conjuntos"]) == set(lastro.SETS)
    assert data["total"] == sum(len(modelo[k]) for k in lastro.SETS)
    assert data["comLastro"] + data["semLastro"] == data["total"]
    # Only exactMatch to an existing individual counts; closeMatch stays "próximo" and without backing.
    exact = [k for k, v in data["itens"].items() if v["estado"] == "exato"]
    near = [k for k, v in data["itens"].items() if v["estado"] == "proximo"]
    assert len(exact) == data["comLastro"]
    assert "topics:energy-environment" in exact  # area backed by hrai:displayKey in the comparative module
    assert "components:GM-02" in exact and "components:GM-15" in near
    assert not set(exact) & set(near)


def test_published_file_is_current():
    assert lastro.OUT.read_text(encoding="utf-8") == lastro.render(lastro.build())


def test_check_fails_when_counter_rises(tmp_path):
    data = lastro.build()
    better = json.loads(json.dumps(data))
    better["semLastro"] -= 1
    better["conjuntos"]["topics"]["semLastro"] -= 1
    base = tmp_path / "base.js"
    base.write_text(lastro.render(better), encoding="utf-8")
    problems = lastro.check(data, str(base))
    assert any("subiu" in p for p in problems) and any(p.startswith("topics") for p in problems)
    base.write_text(lastro.render(data), encoding="utf-8")
    assert lastro.check(data, str(base)) == []


def test_seal_and_slide_use_the_counter():
    camara = (ROOT / "web/ao-vivo/index.html").read_text(encoding="utf-8")
    slide = (ROOT / "web/apresentacao/index.html").read_text(encoding="utf-8")
    assert '../assets/lastro.js' in camara and '../assets/lastro.js' in slide
    for conjunto in ("components", "seeds", "strata", "unrep", "topics"):
        assert f'selo("{conjunto}"' in camara
    # The unconditional claim only appears behind the zero-counter guard.
    assert slide.count("Cada peça é um indivíduo da ontologia") == 1
    assert "LASTRO.semLastro === 0" in slide
