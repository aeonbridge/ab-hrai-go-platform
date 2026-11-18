"""Seeding from the project's seed documents (METODO_EXTRACAO.md): provenance, honesty marks, no decisions."""

import hashlib
import importlib.util
from pathlib import Path

import rdflib
from rdflib.namespace import PROV, RDF, SKOS

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("semear", ROOT / "scripts/ontologia/semear.py")
semear = importlib.util.module_from_spec(spec)
spec.loader.exec_module(semear)
H = semear.H


def g():
    return rdflib.Graph().parse(semear.OUT)


def test_output_is_current_and_outside_source_instances():
    from rdflib.compare import isomorphic
    assert isomorphic(semear.build(), g())
    assert "regulatory/sementes" in str(semear.OUT) and "instances" not in str(semear.OUT)


def test_every_seed_has_provenance_and_a_pending_candidate():
    gr = g()
    seeded = set(gr.subjects(H.displayKey, None))
    assert len(seeded) == 31
    candidates = {gr.value(c, rdflib.namespace.DCTERMS.subject): c for c in gr.subjects(RDF.type, H.CandidateAssertion)}
    for x in seeded:
        snap = gr.value(x, PROV.wasDerivedFrom)
        assert snap is not None and (snap, RDF.type, H.SourceSnapshot) in gr, x
        path = ROOT / str(gr.value(snap, H.snapshotURI)).split("/blob/main/", 1)[1]
        assert str(gr.value(snap, H.snapshotSHA256)) == hashlib.sha256(path.read_bytes()).hexdigest()
        c = candidates[x]
        assert (c, H.candidateProducedBy, semear.SEM.ExtratorDeSementes) in gr
        assert (c, H.hasReviewDecision, None) not in gr
    # Invariant I-3: the seeding never decides.
    assert not set(gr.subjects(RDF.type, H.ReviewDecision)) and not set(gr.subjects(RDF.type, H.ApprovalDecision))


def test_traits_without_real_source_are_flagged():
    gr = g()
    by = {str(gr.value(x, SKOS.notation)): x for x in gr.subjects(RDF.type, H.ContextIndicator)}
    assert gr.value(by["CF-04"], H.seedHasRealSource).toPython() is False   # no source at all
    assert gr.value(by["CF-01"], H.seedHasRealSource).toPython() is False   # only the fictional world pack
    assert gr.value(by["CF-03"], H.seedHasRealSource).toPython() is True    # cites the PBIA
    assert str(gr.value(by["CF-04"], H.seedBasis)) == "hipótese de trabalho"


def test_exact_components_are_not_duplicated_and_proposals_are_marked():
    gr = g()
    notations = {str(gr.value(x, SKOS.notation)) for x in gr.subjects(H.displayKey, None)}
    assert "GM-02" not in notations and "GM-05" in notations
    sia = next(x for x in gr.subjects(SKOS.notation, rdflib.Literal("GM-05")))
    assert (sia, rdflib.namespace.DCTERMS.isPartOf, semear.PBIA.PL_2338_2023) in gr
    assert (sia, RDF.type, H.Stakeholder) in gr
