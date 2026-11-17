from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROTOTYPES = ROOT / "docs/scse/prototipo"
CURRENT_PAGE = PROTOTYPES / "mural-de-tensoes.html"
REVISED_PAGE = PROTOTYPES / "mural-de-tensoes-revisado.html"


def test_revised_page_keeps_the_existing_prototype_untouched():
    current = CURRENT_PAGE.read_text(encoding="utf-8")
    revised = REVISED_PAGE.read_text(encoding="utf-8")

    assert "Mural de Tensões" in current
    assert "O que ficou em aberto" in revised
    assert current != revised


def test_revised_page_loads_real_run_and_offers_local_review_actions():
    html = REVISED_PAGE.read_text(encoding="utf-8")

    assert "../../../runs/${encodeURIComponent(scenario)}/latest.json" in html
    assert "run.packetPath" in html
    assert "state.run.reportPath" in html
    assert "state.run.httpTracePath" in html
    assert "Requests e responses (.jsonl)" in html
    assert "data-queue" in html
    assert "personal-review-agenda" in html
    assert "localStorage" in html
    assert "review.proposalCount" in html
    assert "tensões emergentes" in html
