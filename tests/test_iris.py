"""RNF-01 / V-24: every HRAI-GO IRI resolves to an anchored section of a page generated from the graph."""

import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/ontologia"))
import publicar_iris  # noqa: E402


def test_pages_are_generated_from_the_graph():
    assert subprocess.run([sys.executable, str(ROOT / "scripts/ontologia/publicar_iris.py"), "--check"]).returncode == 0


def test_random_iris_land_on_their_anchor():
    """Open three IRIs at random (V-24): the page for the namespace has a section with the fragment as id."""
    import rdflib
    g = rdflib.Graph()
    for f in publicar_iris.consultas.files():
        g.parse(f)
    iris = sorted({str(s) for s in g.subjects() if isinstance(s, rdflib.URIRef) and str(s).startswith(publicar_iris.BASE) and "#" in str(s)})
    for iri in random.Random(17).sample(iris, 3) + ["https://hrai-go.aeonbridge.io/ontology/regulatory#LegalProvision",
                                                       "https://hrai-go.aeonbridge.io/data/regulatory/br/pl2338#Art_2024_054"]:
        ns, frag = iri.split("#", 1)
        page = publicar_iris.page_path(ns).read_text(encoding="utf-8")
        assert f"id='{frag}'" in page, iri


def test_inferences_show_their_rule():
    page = (ROOT / "web/data/regulatory/br/pl2338/index.html").read_text(encoding="utf-8")
    assert "inferido por R22_ProposedProvision" in page   # every PL provision is a proposal, by rule R22
