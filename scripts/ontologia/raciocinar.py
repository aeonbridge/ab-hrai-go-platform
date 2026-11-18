"""Motor de raciocínio da ontologia regulatória HRAI-GO (v1.1.0).

Executa as regras SWRL serializadas em RDF na própria ontologia (swrl:Imp) por encadeamento para frente
até o ponto fixo, mais um fechamento OWL/RDFS mínimo e explícito:
  - rdfs:subClassOf  (tipo herdado pelas superclasses)
  - rdfs:subPropertyOf
  - owl:inverseOf
Cada tripla inferida guarda a justificativa (regra, ligações das variáveis e triplas do corpo), o que permite
responder "por quê?" com a cadeia inteira até as triplas declaradas e, delas, até a fonte (prov:wasDerivedFrom).

Não é um raciocinador OWL completo (não trata restrições, cardinalidade, classes definidas, etc.). Essa limitação é
deliberada: o resultado é auditável linha a linha, e as regras da ontologia foram escritas para serem seguras
(nenhuma cabeça afirma status jurídico, conformidade ou publicação).

Uso:
  python scripts/ontologia/raciocinar.py                                  # TBox + ABox do PBIA
  python scripts/ontologia/raciocinar.py --extra <arquivo.ttl> ...        # acrescenta cenários e alinhamentos
  python scripts/ontologia/raciocinar.py --json saida.json --explicar <IRI-sujeito>
"""
from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef
from rdflib.collection import Collection

RAIZ = Path(__file__).resolve().parents[2]
TBOX = RAIZ / "ontologies/regulatory/HRAI_GO_Regulatory_General.ttl"
ABOX_PBIA = RAIZ / "ontologies/regulatory/instances/br/HRAI_GO_Regulatory_BR_PBIA_2025.ttl"
H = Namespace("https://hrai-go.aeonbridge.io/ontology/regulatory#")
SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
SWRLB = Namespace("http://www.w3.org/2003/11/swrlb#")
PROV = Namespace("http://www.w3.org/ns/prov#")
# predicados que nenhuma inferência pode produzir: decisão jurídica e publicação são humanas
PROIBIDOS = {H.assessmentHasStatus, H.hasLegalStatus, H.releasePublishesCandidate}


def _num(x):
    if isinstance(x, Literal):
        v = x.toPython()
        if isinstance(v, (int, float, Decimal)) and not isinstance(v, bool):
            return Decimal(str(v))
    return None


class Regra:
    def __init__(self, g: Graph, iri: URIRef):
        self.iri, self.nome = iri, str(g.value(iri, RDFS.label) or iri.split("#")[-1])
        self.ressalva = str(g.value(iri, RDFS.comment) or "")
        self.corpo = [self._atomo(g, a) for a in Collection(g, g.value(iri, SWRL.body))]
        self.cabeca = [self._atomo(g, a) for a in Collection(g, g.value(iri, SWRL.head))]
        # átomos de dados primeiro, builtins no fim (na ordem em que aparecem)
        self.corpo.sort(key=lambda a: a[0] == "builtin")

    @staticmethod
    def _termo(g, t):
        return ("var", t) if (t, RDF.type, SWRL.Variable) in g else ("const", t)

    def _atomo(self, g, a):
        tipo = g.value(a, RDF.type)
        if tipo == SWRL.ClassAtom:
            return ("classe", g.value(a, SWRL.classPredicate), [self._termo(g, g.value(a, SWRL.argument1))])
        if tipo in (SWRL.IndividualPropertyAtom, SWRL.DatavaluedPropertyAtom):
            return ("prop", g.value(a, SWRL.propertyPredicate),
                    [self._termo(g, g.value(a, SWRL.argument1)), self._termo(g, g.value(a, SWRL.argument2))])
        if tipo == SWRL.BuiltinAtom:
            return ("builtin", g.value(a, SWRL.builtin), [self._termo(g, t) for t in Collection(g, g.value(a, SWRL.arguments))])
        raise ValueError(f"{self.nome}: átomo SWRL não suportado: {tipo}")


class Raciocinador:
    def __init__(self, *arquivos: Path):
        self.g = Graph()
        for f in arquivos:
            self.g.parse(f, format="turtle")
        self.declaradas = set(self.g)
        self.regras = [Regra(self.g, r) for r in sorted(self.g.subjects(RDF.type, SWRL.Imp))]
        self.justificativa: dict[tuple, dict] = {}
        self.disparos = Counter()

    # ---------- fechamento OWL/RDFS mínimo ----------
    def _schema(self):
        g = self.g
        sup = defaultdict(set)
        for s, o in g.subject_objects(RDFS.subClassOf):
            if isinstance(o, URIRef):
                sup[s].add(o)
        supp = defaultdict(set)
        for s, o in g.subject_objects(RDFS.subPropertyOf):
            supp[s].add(o)
        inv = defaultdict(set)
        for s, o in g.subject_objects(OWL.inverseOf):
            inv[s].add(o); inv[o].add(s)

        def fecho(d):
            out = {}
            for k in list(d):
                vistos, pilha = set(), list(d[k])
                while pilha:
                    x = pilha.pop()
                    if x not in vistos:
                        vistos.add(x); pilha.extend(d.get(x, ()))
                out[k] = vistos
            return out
        return fecho(sup), fecho(supp), inv

    def _adicionar(self, t, como):
        if t in self.g:
            return False
        if t[1] in PROIBIDOS:
            raise AssertionError(f"inferência proibida: {t} via {como['regra']}")
        self.g.add(t)
        self.justificativa[t] = como
        return True

    def _passo_schema(self, sup, supp, inv):
        novos = 0
        for s, c in list(self.g.subject_objects(RDF.type)):
            for c2 in sup.get(c, ()):
                novos += self._adicionar((s, RDF.type, c2), {"regra": "rdfs:subClassOf", "corpo": [(s, RDF.type, c), (c, RDFS.subClassOf, c2)], "ligacoes": {}})
        for p, ps in supp.items():
            for s, o in list(self.g.subject_objects(p)):
                for p2 in ps:
                    novos += self._adicionar((s, p2, o), {"regra": "rdfs:subPropertyOf", "corpo": [(s, p, o), (p, RDFS.subPropertyOf, p2)], "ligacoes": {}})
        for p, ps in inv.items():
            for s, o in list(self.g.subject_objects(p)):
                if isinstance(o, Literal):
                    continue
                for p2 in ps:
                    novos += self._adicionar((o, p2, s), {"regra": "owl:inverseOf", "corpo": [(s, p, o), (p, OWL.inverseOf, p2)], "ligacoes": {}})
        return novos

    # ---------- SWRL ----------
    def _casar(self, atomos, lig, usadas):
        if not atomos:
            yield lig, usadas
            return
        tipo, pred, args = atomos[0]
        val = lambda t: lig.get(t[1]) if t[0] == "var" else t[1]
        if tipo == "classe":
            x = val(args[0])
            cands = [x] if x is not None else list(self.g.subjects(RDF.type, pred))
            for c in cands:
                if (c, RDF.type, pred) in self.g:
                    l2 = dict(lig)
                    if args[0][0] == "var":
                        l2[args[0][1]] = c
                    yield from self._casar(atomos[1:], l2, usadas + [(c, RDF.type, pred)])
        elif tipo == "prop":
            a, b = val(args[0]), val(args[1])
            for s, o in self.g.subject_objects(pred) if a is None and b is None else (
                    [(a, o) for o in self.g.objects(a, pred)] if a is not None else [(s, b) for s in self.g.subjects(pred, b)]):
                if (a is not None and s != a) or (b is not None and o != b):
                    continue
                l2 = dict(lig)
                if args[0][0] == "var": l2[args[0][1]] = s
                if args[1][0] == "var": l2[args[1][1]] = o
                yield from self._casar(atomos[1:], l2, usadas + [(s, pred, o)])
        else:
            nome = pred.split("#")[-1]
            vs = [val(t) for t in args]
            if nome in ("greaterThan", "lessThan", "greaterThanOrEqual", "lessThanOrEqual", "equal"):
                x, y = _num(vs[0]), _num(vs[1])
                if x is None or y is None:
                    return
                ok = {"greaterThan": x > y, "lessThan": x < y, "greaterThanOrEqual": x >= y, "lessThanOrEqual": x <= y, "equal": x == y}[nome]
                if ok:
                    yield from self._casar(atomos[1:], lig, usadas)
            elif nome == "notEqual":   # swrlb:notEqual(?a, ?b): both bound and different terms
                if vs[0] is not None and vs[1] is not None and vs[0] != vs[1]:
                    yield from self._casar(atomos[1:], lig, usadas)
            elif nome == "divide":   # swrlb:divide(?r, ?a, ?b): r = a / b
                a, b = _num(vs[1]), _num(vs[2])
                if a is None or b is None or b == 0:
                    return
                r = a / b
                if vs[0] is None:
                    l2 = dict(lig); l2[args[0][1]] = Literal(r)
                    yield from self._casar(atomos[1:], l2, usadas)
                elif _num(vs[0]) == r:
                    yield from self._casar(atomos[1:], lig, usadas)
            else:
                raise ValueError(f"builtin não suportado: {nome}")

    def _passo_regras(self):
        novos = 0
        for r in self.regras:
            for lig, usadas in list(self._casar(r.corpo, {}, [])):
                for tipo, pred, args in r.cabeca:
                    v = [lig[t[1]] if t[0] == "var" else t[1] for t in args]
                    t = (v[0], RDF.type, pred) if tipo == "classe" else (v[0], pred, v[1])
                    if self._adicionar(t, {"regra": r.nome, "ressalva": r.ressalva, "corpo": usadas,
                                           "ligacoes": {k.split("_")[-1]: v for k, v in lig.items()}}):
                        novos += 1; self.disparos[r.nome] += 1
        return novos

    def executar(self):
        sup, supp, inv = self._schema()
        rodadas = 0
        while True:
            rodadas += 1
            n = self._passo_schema(sup, supp, inv) + self._passo_regras()
            if n == 0:
                return rodadas

    # ---------- explicação ----------
    def rotulo(self, x):
        if isinstance(x, Literal):
            return str(x)
        l = self.g.value(x, RDFS.label)
        return str(l) if l else self.g.namespace_manager.normalizeUri(x) if isinstance(x, URIRef) else str(x)

    def curto(self, x):
        if isinstance(x, URIRef):
            try:
                return self.g.namespace_manager.normalizeUri(x)
            except Exception:
                return str(x)
        return str(x)

    def explicar(self, t, nivel=0, vistos=None):
        """Árvore de justificativa até as triplas declaradas (e a fonte, quando houver prov:wasDerivedFrom)."""
        vistos = vistos or set()
        s, p, o = t
        linha = {"tripla": [self.curto(s), self.curto(p), self.curto(o)]}
        if t in self.justificativa and t not in vistos:
            j = self.justificativa[t]
            vistos = vistos | {t}
            linha["por"] = j["regra"]
            if j.get("ressalva"):
                linha["ressalva"] = j["ressalva"]
            linha["porque"] = [self.explicar(c, nivel + 1, vistos) for c in j["corpo"]
                               if c[1] not in (RDFS.subClassOf, RDFS.subPropertyOf, OWL.inverseOf)]
        else:
            linha["declarada"] = True
            fontes = [self.curto(f) for f in self.g.objects(s, PROV.wasDerivedFrom)]
            if fontes:
                linha["fonte"] = fontes
        return linha


def resumo(rz: Raciocinador):
    inferidas = [t for t in rz.justificativa]
    por_regra = Counter(j["regra"] for j in rz.justificativa.values())
    return {"triplas_declaradas": len(rz.declaradas), "triplas_inferidas": len(inferidas),
            "inferidas_por_regra_swrl": dict(sorted(rz.disparos.items())),
            "inferidas_por_fechamento": {k: v for k, v in por_regra.items() if ":" in k},
            "regras_carregadas": len(rz.regras),
            "regras_sem_disparo": sorted(r.nome for r in rz.regras if not rz.disparos[r.nome])}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extra", nargs="*", default=[], help="arquivos Turtle adicionais (cenários, alinhamentos)")
    ap.add_argument("--json", help="grava o resumo e as inferências SWRL com justificativa")
    ap.add_argument("--explicar", nargs="*", default=[], help="IRIs de sujeitos cujas inferências serão explicadas")
    a = ap.parse_args()
    rz = Raciocinador(TBOX, ABOX_PBIA, *map(Path, a.extra))
    rodadas = rz.executar()
    r = resumo(rz) | {"rodadas_ate_ponto_fixo": rodadas}
    swrl = [t for t, j in rz.justificativa.items() if ":" not in j["regra"]]
    r["inferencias_swrl"] = [{"tripla": [rz.curto(x) for x in t], "rotulos": [rz.rotulo(x) for x in t], "regra": rz.justificativa[t]["regra"]} for t in swrl]
    r["explicacoes"] = {s: [rz.explicar(t) for t in swrl if str(t[0]) == s or rz.curto(t[0]) == s] for s in a.explicar}
    print(json.dumps({k: v for k, v in r.items() if k not in ("inferencias_swrl", "explicacoes")}, ensure_ascii=False, indent=2))
    if a.json:
        Path(a.json).write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
