#!/usr/bin/env python3
"""Convert human-readable SWRL rules into the RDF (swrl:Imp) Turtle used by the HRAI-GO ontologies.

Text syntax, one rule per string (same as the .swrl files):
    hrai:LegalProvision(?p) ^ hrai:provisionOfVersion(?p,?v) ^ swrlb:lessThan(?x,?y) -> hrai:Foo(?p)

- ``pref:Name(?x)`` is a class atom; ``pref:name(?x,?y)`` a property atom (datavalued when the
  property is in ``datatype_props``, individual otherwise); ``swrlb:name(...)`` a builtin atom.
- Arguments starting with ``?`` are variables (named ``var_<Rule>_<name>``); others are constants
  written as ``pref:Local`` CURIEs.

The output follows the line-per-triple style of HRAI_GO_Regulatory_General.ttl, so it can be
appended to that file; ``to_graph`` gives the same triples as an rdflib Graph.
"""

from __future__ import annotations

import re

import rdflib
from rdflib import BNode, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF, RDFS

SWRL = rdflib.Namespace("http://www.w3.org/2003/11/swrl#")
SWRLB = rdflib.Namespace("http://www.w3.org/2003/11/swrlb#")
ATOM = re.compile(r"^\s*([A-Za-z][\w-]*):([\w-]+)\((.*)\)\s*$")


def _split_atoms(side: str) -> list[str]:
    return [a.strip() for a in side.split("^") if a.strip()]


def to_graph(name: str, comment: str, text: str, ns: dict[str, str], rule_ns: str,
             datatype_props: set[str] = frozenset()) -> rdflib.Graph:
    """Build the swrl:Imp triples for one rule. ``ns`` maps prefixes to namespaces."""
    ns = {"swrlb": str(SWRLB), **ns}
    if "->" not in text:
        raise ValueError(f"{name}: missing '->'")
    body_txt, head_txt = text.split("->", 1)
    g = rdflib.Graph()
    rule = URIRef(rule_ns + name)
    g.add((rule, RDF.type, SWRL.Imp))
    g.add((rule, RDFS.label, Literal(name, lang="en")))
    g.add((rule, RDFS.comment, Literal(comment, lang="en")))

    def term(arg: str):
        arg = arg.strip()
        if arg.startswith("?"):
            v = URIRef(f"{rule_ns}var_{name}_{arg[1:]}")
            g.add((v, RDF.type, SWRL.Variable))
            return v
        pref, local = arg.split(":", 1)
        return URIRef(ns[pref] + local)

    def atom(txt: str):
        m = ATOM.match(txt)
        if not m:
            raise ValueError(f"{name}: cannot parse atom {txt!r}")
        pref, local, args = m.group(1), m.group(2), [a for a in m.group(3).split(",") if a.strip()]
        iri = URIRef(ns[pref] + local)
        a = BNode()
        if pref == "swrlb":
            g.add((a, RDF.type, SWRL.BuiltinAtom))
            g.add((a, SWRL.builtin, iri))
            lst = BNode()
            Collection(g, lst, [term(x) for x in args])
            g.add((a, SWRL.arguments, lst))
        elif len(args) == 1:
            g.add((a, RDF.type, SWRL.ClassAtom))
            g.add((a, SWRL.classPredicate, iri))
            g.add((a, SWRL.argument1, term(args[0])))
        elif len(args) == 2:
            kind = SWRL.DatavaluedPropertyAtom if str(iri) in datatype_props else SWRL.IndividualPropertyAtom
            g.add((a, RDF.type, kind))
            g.add((a, SWRL.propertyPredicate, iri))
            g.add((a, SWRL.argument1, term(args[0])))
            g.add((a, SWRL.argument2, term(args[1])))
        else:
            raise ValueError(f"{name}: atom with {len(args)} arguments: {txt!r}")
        return a

    for side, prop in ((body_txt, SWRL.body), (head_txt, SWRL.head)):
        lst = BNode()
        Collection(g, lst, [atom(t) for t in _split_atoms(side)])
        g.add((rule, prop, lst))
    return g


def to_turtle_lines(g: rdflib.Graph, prefixes: dict[str, str], bnode_prefix: str) -> str:
    """Serialize a rule graph as one triple per line, with stable blank-node labels."""
    labels: dict[BNode, str] = {}

    def fmt(t):
        if isinstance(t, BNode):
            labels.setdefault(t, f"_:{bnode_prefix}_{len(labels) + 1}")
            return labels[t]
        if isinstance(t, Literal):
            return t.n3()
        s = str(t)
        for pref, base in sorted(prefixes.items(), key=lambda kv: -len(kv[1])):
            if s.startswith(base) and re.fullmatch(r"[\w-]+", s[len(base):]):
                return f"{pref}:{s[len(base):]}"
        return f"<{s}>"

    # Rule header first, then atoms in a deterministic order.
    order = sorted(g, key=lambda t: (not isinstance(t[0], URIRef), fmt(t[0]) if not isinstance(t[0], BNode) else "", str(t[1])))
    lines = []
    for s, p, o in order:
        if isinstance(s, URIRef):
            lines.append(f"{fmt(s)} {fmt(p)} {fmt(o)} .")
    bnodes = [t for t in g if isinstance(t[0], BNode)]
    # Walk lists and atoms so labels follow reading order.
    seen = set()

    def emit(node):
        if node in seen or not isinstance(node, BNode):
            return
        seen.add(node)
        for s, p, o in sorted(g.triples((node, None, None)), key=lambda t: str(t[1])):
            lines.append(f"{fmt(s)} {fmt(p)} {fmt(o)} .")
        for _, _, o in g.triples((node, None, None)):
            emit(o)

    for s, p, o in sorted(g, key=lambda t: str(t[1])):
        if isinstance(s, URIRef) and isinstance(o, BNode):
            emit(o)
    for s, _, _ in bnodes:
        emit(s)
    return "\n".join(lines) + "\n"
