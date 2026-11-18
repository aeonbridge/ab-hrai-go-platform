"""Validate regulatory ABox files against the HRAI-GO General Regulatory TBox.

Checks, for every Turtle file under ontologies/regulatory/instances/:
  1. Turtle and RDF/XML twins are isomorphic graphs.
  2. Every hrai: term used exists in the TBox; every hrai: rdf:type is an owl:Class.
  3. rdfs:domain / rdfs:range of hrai: properties hold (with rdfs:subClassOf closure).
  4. Literal datatypes match declared datatype ranges.
  5. Epistemic safeguards: no automatic compliance status, no approved candidates
     without review decisions, LegislativeProposal/EnactedLegalInstrument disjointness.
  6. The 18 SWRL rules serialized in the TBox are executed by a small forward-chaining
     interpreter. This is a structural smoke test, not a substitute for a reasoner
     such as Pellet or Drools.

PBIA-specific assertions (budget totals and expected inferences) run when the
PBIA ABox is present.
"""
from __future__ import annotations

import itertools
from decimal import Decimal
from pathlib import Path

from rdflib import RDF, RDFS, OWL, XSD, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.compare import isomorphic

ROOT = Path(__file__).resolve().parents[1] / "ontologies" / "regulatory"
H = Namespace("https://hrai-go.aeonbridge.io/ontology/regulatory#")
SW = Namespace("http://www.w3.org/2003/11/swrl#")
SWRLB = Namespace("http://www.w3.org/2003/11/swrlb#")
SCHEMA = Namespace("https://schema.org/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
PBIA = Namespace("https://hrai-go.aeonbridge.io/data/regulatory/br/pbia#")

TBOX = Graph().parse(ROOT / "HRAI_GO_Regulatory_General.ttl", format="turtle")


# --------------------------------------------------------------------------- helpers
def superclasses(cls: URIRef) -> set[URIRef]:
    """Reflexive-transitive rdfs:subClassOf closure in the TBox."""
    seen, stack = {cls}, [cls]
    while stack:
        for sup in TBOX.objects(stack.pop(), RDFS.subClassOf):
            if sup not in seen:
                seen.add(sup)
                stack.append(sup)
    return seen


def types_of(graph: Graph, node) -> set[URIRef]:
    out: set[URIRef] = set()
    for t in graph.objects(node, RDF.type):
        out |= superclasses(t)
    return out


def instance_files() -> list[Path]:
    # Skip macOS AppleDouble metadata files created on exFAT volumes.
    return sorted(p for p in (ROOT / "instances").rglob("*.ttl") if not p.name.startswith("._"))


# --------------------------------------------------------------------------- SWRL
def load_rules() -> list[tuple[URIRef, list, list]]:
    def atoms(lst):
        result = []
        for atom in Collection(TBOX, lst):
            kind = TBOX.value(atom, RDF.type)
            if kind == SW.ClassAtom:
                result.append(("class", TBOX.value(atom, SW.classPredicate), [TBOX.value(atom, SW.argument1)]))
            elif kind == SW.BuiltinAtom:
                args = list(Collection(TBOX, TBOX.value(atom, SW.arguments)))
                result.append(("builtin", TBOX.value(atom, SW.builtin), args))
            else:  # IndividualPropertyAtom / DatavaluedPropertyAtom
                result.append(("prop", TBOX.value(atom, SW.propertyPredicate),
                               [TBOX.value(atom, SW.argument1), TBOX.value(atom, SW.argument2)]))
        return result

    return [(r, atoms(TBOX.value(r, SW.body)), atoms(TBOX.value(r, SW.head)))
            for r in TBOX.subjects(RDF.type, SW.Imp)]


def is_var(term) -> bool:
    return (term, RDF.type, SW.Variable) in TBOX


def resolve(term, binding):
    return binding.get(term, term) if is_var(term) else term


def match(graph: Graph, body, binding):
    if not body:
        yield binding
        return
    (kind, pred, args), rest = body[0], body[1:]
    if kind == "builtin":
        vals = [resolve(a, binding) for a in args]
        if pred == SWRLB.greaterThan and Decimal(str(vals[0])) > Decimal(str(vals[1])):
            yield from match(graph, rest, binding)
        return
    if kind == "class":
        subj = resolve(args[0], binding)
        candidates = [subj] if not is_var(subj) else set(graph.subjects(RDF.type, None))
        for node in candidates:
            if pred in types_of(graph, node):
                yield from match(graph, rest, {**binding, args[0]: node} if is_var(args[0]) else binding)
        return
    s, o = (resolve(a, binding) for a in args)
    for ts, _, to in graph.triples((None if is_var(s) else s, pred, None if is_var(o) else o)):
        new = dict(binding)
        if is_var(s):
            new[s] = ts
        if is_var(o):
            new[o] = to
        yield from match(graph, rest, new)


def run_rules(graph: Graph) -> dict[URIRef, int]:
    """Forward-chain all rules to a fixpoint; return number of new triples per rule."""
    rules, fired = load_rules(), {}
    for _ in range(20):
        added = 0
        for name, body, head in rules:
            for binding in list(match(graph, body, {})):
                for kind, pred, args in head:
                    vals = [resolve(a, binding) for a in args]
                    triple = (vals[0], RDF.type, pred) if kind == "class" else (vals[0], pred, vals[1])
                    if triple not in graph:
                        graph.add(triple)
                        fired[name] = fired.get(name, 0) + 1
                        added += 1
        if not added:
            return fired
    raise AssertionError("SWRL forward chaining did not reach a fixpoint")


# --------------------------------------------------------------------------- checks
def check_file(ttl_path: Path) -> Graph:
    abox = Graph().parse(ttl_path, format="turtle")
    owl_path = ttl_path.with_suffix(".owl")
    assert owl_path.exists(), f"missing RDF/XML twin {owl_path}"
    assert isomorphic(abox, Graph().parse(owl_path, format="xml")), \
        f"{owl_path.name} is stale: run python scripts/build_regulatory_instances.py"

    tbox_terms = set(TBOX.subjects())
    for triple in abox:
        for term in triple:
            if isinstance(term, URIRef) and str(term).startswith(str(H)):
                assert term in tbox_terms, f"unknown TBox term {term}"
    for node, cls in abox.subject_objects(RDF.type):
        if str(cls).startswith(str(H)):
            assert (cls, RDF.type, OWL.Class) in TBOX, f"{cls} is not an owl:Class"

    for s, p, o in abox:
        if not str(p).startswith(str(H)):
            continue
        domain, rng = TBOX.value(p, RDFS.domain), TBOX.value(p, RDFS.range)
        if domain is not None:
            assert domain in types_of(abox, s), f"domain violation: {s} {p} (expects {domain})"
        if (p, RDF.type, OWL.ObjectProperty) in TBOX:
            assert isinstance(o, URIRef), f"object property {p} has literal value"
            if rng is not None:
                assert rng in types_of(abox, o) | types_of(TBOX, o), f"range violation: {p} -> {o} (expects {rng})"
        elif (p, RDF.type, OWL.DatatypeProperty) in TBOX:
            assert isinstance(o, Literal), f"datatype property {p} has IRI value"
            expected = rng or XSD.string
            actual = o.datatype or (XSD.string if o.language is None else RDF.langString)
            ok = actual == expected or (expected == XSD.string and actual == RDF.langString)
            assert ok, f"datatype violation: {s} {p} {o!r} (expects {expected})"
            assert not o.ill_typed, f"ill-typed literal {o!r}"

    # Epistemic safeguards
    assert not list(abox.triples((None, H.assessmentHasStatus, None))), "ABox must not assert compliance status"
    for cand in abox.subjects(RDF.type, H.ReviewedAndApprovedCandidate):
        assert abox.value(cand, H.hasReviewDecision) is not None, f"{cand} approved without review decision"
    for node in abox.subjects(RDF.type, H.LegislativeProposal):
        assert H.EnactedLegalInstrument not in types_of(abox, node), f"{node} violates proposal/enacted disjointness"
    return abox


def check_pbia(abox: Graph) -> None:
    # The PBIA is a policy plan: never a legal instrument, never a source of requirements.
    assert H.PolicyInstrument in types_of(abox, PBIA.PBIA_Plan)
    assert H.LegalInstrument not in types_of(abox, PBIA.PBIA_Plan)
    assert not list(abox.subjects(RDF.type, H.NormativeRequirement))
    assert (PBIA.PL_2338_2023_AsCitedInPBIA, H.hasLegalStatus, H.ProposedLegalStatus) in abox

    def amount(node) -> Decimal:
        money = abox.value(node, SCHEMA.amount)
        return Decimal(str(abox.value(money, SCHEMA.value)))

    parts = [PBIA.PBIA_ImmediateImpactActions, PBIA.PBIA_Axis1_InfrastructureDevelopment,
             PBIA.PBIA_Axis2_DiffusionTraining, PBIA.PBIA_Axis3_PublicServices,
             PBIA.PBIA_Axis4_BusinessInnovation, PBIA.PBIA_Axis5_RegulatoryGovernanceSupport]
    # Table 2 rounds each line; the parts must match the R$ 23.03 bi total within R$ 10 mi.
    assert abs(sum(map(amount, parts)) - amount(PBIA.PBIA_Plan)) <= Decimal("10000000")
    axis5_actions = [PBIA.Action50_ResponsibleAIGuides, PBIA.Action51_AlgorithmicTransparencyCentre,
                     PBIA.Action52_BrazilianAIObservatory, PBIA.Action53_AIGovernanceSupportNetwork,
                     PBIA.Action54_InternationalDebateNetwork]
    assert sum(map(amount, axis5_actions)) == amount(PBIA.PBIA_Axis5_RegulatoryGovernanceSupport)

    # Stakeholders: institutional actors only, every link target typed and labelled.
    all_sh = set(abox.subjects(RDF.type, H.Stakeholder))
    assert not list(abox.subjects(RDF.type, FOAF.Person)), "natural persons must not be instantiated"
    for sh in all_sh:
        assert abox.value(sh, RDFS.label) is not None, f"{sh} without label"
        assert len(set(abox.objects(sh, RDF.type))) >= 2, f"{sh} lacks a schema:* organization type"
    link_props = [SCHEMA.memberOf, SCHEMA.parentOrganization, SCHEMA.funder, SCHEMA.provider,
                  DCTERMS.contributor, DCTERMS.creator, H.positionExpressedBy, H.deliberationIncludesStakeholder]
    for prop in link_props:
        for target in abox.objects(None, prop):
            assert target in all_sh, f"{prop} points to non-stakeholder {target}"
    cct_members = set(abox.subjects(SCHEMA.memberOf, PBIA.SH_CCT))
    assert len(cct_members) == 27, ("CCT: 17 ministries (I) + 10 entities (III)", len(cct_members))
    wg_members = set(abox.subjects(SCHEMA.memberOf, PBIA.SH_WG_PBIA))
    assert wg_members == {PBIA.SH_Sexec_MCTI, PBIA.SH_Setad_MCTI, PBIA.SH_ASCCT_MCTI, PBIA.SH_SAM_CasaCivil,
                          PBIA.SH_MDIC, PBIA.SH_MGI, PBIA.SH_MJSP, PBIA.SH_MRE, PBIA.SH_CGEE, PBIA.SH_CNI}
    for app in abox.subjects(RDF.type, H.AIApplication):
        assert abox.value(app, SCHEMA.provider) is not None, f"{app} without provider"
    # dcterms:references also targets legal instruments, so it only counts as a link here.
    linked = {o for p in link_props + [DCTERMS.references] for o in abox.objects(None, p)}
    linked |= set(abox.subjects(SCHEMA.memberOf, None))
    orphans = all_sh - linked - set(abox.subjects(SCHEMA.parentOrganization, None))
    assert not orphans, f"stakeholders without any link: {sorted(orphans)}"

    # Unreviewed extraction must never become an approved candidate.
    reviewed = abox + TBOX
    fired = run_rules(reviewed)
    assert not list(reviewed.subjects(RDF.type, H.ReviewedAndApprovedCandidate))
    assert (PBIA.Claim_AIThreatensEmployment, RDF.type, H.ContestedPolicyClaim) in reviewed           # R05
    assert (PBIA.Tension_AutomationVsLabourProtection, RDF.type, H.ContestedRegulatoryTension) in reviewed  # R06
    explicit = set(abox.objects(PBIA.Delib_PBIAElaboration2024, H.deliberationIncludesStakeholder))
    stakeholders = set(reviewed.objects(PBIA.Delib_PBIAElaboration2024, H.deliberationIncludesStakeholder))
    position_authors = {PBIA.SH_PresidencyOfTheRepublic, PBIA.SH_MCTI, PBIA.SH_ABC, PBIA.SH_CNI}
    assert stakeholders == explicit | position_authors                                                  # R07
    assert fired.get(H.R07_DeliberationStakeholder) == len(position_authors - explicit)
    print(f"  stakeholders: {len(all_sh)} (CCT {len(cct_members)}, GT {len(wg_members)}, "
          f"deliberation {len(stakeholders)})")
    assert (PBIA.Alt_DualApproachImmediateAndStructural, RDF.type, H.IndicatorAssessedAlternative) in reviewed  # R08
    for instrument in abox.objects(PBIA.BrazilAIRegulatoryModel_PBIA, H.usesPolicyInstrument):         # R03
        assert (instrument, H.policyInstrumentInJurisdiction, PBIA.Brazil) in reviewed
    for indicator in abox.subjects(RDF.type, H.ContextIndicator):                                       # R04
        assert (indicator, H.indicatorRelevantToJurisdiction, PBIA.Brazil) in reviewed
    assert (PBIA.Change_PBIA_VN8_Captured, H.changeHasSource, PBIA.Source_PBIA) in reviewed             # R15
    for tension in abox.subjects(RDF.type, H.RegulatoryTension):                                        # R16
        assert (tension, H.tensionHasContext, PBIA.BrazilAIContext_PBIA) in reviewed
    claims = set(abox.subjects(RDF.type, H.PolicyClaim))
    assert claims == set(reviewed.subjects(RDF.type, H.EvidencedPolicyClaim))                          # R17
    assert not list(reviewed.subjects(RDF.type, H.ThresholdExceededIndicator))                         # R18: no thresholds set
    print("  SWRL inferences:", ", ".join(f"{str(r).split('#')[1]}={n}" for r, n in sorted(fired.items())))


def main() -> None:
    files = instance_files()
    assert files, "no ABox files found"
    for path in files:
        abox = check_file(path)
        print(f"OK: {path.relative_to(ROOT)} — {len(abox)} triples")
        if (PBIA.PBIA_Plan, RDF.type, H.PolicyInstrument) in abox:
            check_pbia(abox)


if __name__ == "__main__":
    main()
