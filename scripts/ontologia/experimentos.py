"""Experimentos do relatório técnico (docs/relatorios/ontologia): gera dados.json e tabelas LaTeX.

  E0  linha de base: TBox + ABox do PBIA
  E1  cenário ilustrativo de mudança do PL 2338 (ontologies/regulatory/cenarios/E1_*.ttl)
  A1  alinhamento dos componentes da câmara (GM-01..22) com a instância do PBIA
  V1  verificação independente: para cada regra sem builtin, uma consulta SPARQL gerada a partir do corpo
      roda sobre o grafo final; toda cabeça encontrada precisa já estar no grafo (ponto fixo completo)
  V2  segurança: nenhuma inferência afirma status jurídico, conformidade ou publicação; nenhum dispositivo
      de proposta vira requisito vigente

Uso: python scripts/ontologia/experimentos.py
"""
import json
import sys
import time
from pathlib import Path

from rdflib import Graph, RDF, RDFS, URIRef, Namespace
from rdflib.collection import Collection

sys.path.insert(0, str(Path(__file__).parent))
from raciocinar import RAIZ, TBOX, ABOX_PBIA, H, SWRL, PROIBIDOS, Raciocinador, resumo  # noqa: E402

SAIDA = RAIZ / "docs/relatorios/ontologia"
E1 = RAIZ / "ontologies/regulatory/cenarios/E1_PL2338_texto_camara.ttl"
ALIN = RAIZ / "ontologies/regulatory/alinhamentos/camara_GM_para_PBIA.ttl"
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")


def texq(s):
    """como tex(), mas permite quebrar linha depois de _ e : (identificadores longos)"""
    return tex(s).replace(r"\_", r"\_\allowbreak{}").replace(":", r":\allowbreak{}")


def tex(s):
    return (str(s).replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
            .replace("#", r"\#").replace("$", r"\$").replace("{", r"\{").replace("}", r"\}").replace("~", r"\textasciitilde{}"))


def rodar(*extras):
    t0 = time.perf_counter()
    rz = Raciocinador(TBOX, ABOX_PBIA, *extras)
    rodadas = rz.executar()
    return rz, rodadas, time.perf_counter() - t0


def verificar_ponto_fixo(rz):
    """V1: SPARQL gerado a partir de cada regra; resultado deve estar todo materializado."""
    out = {}
    for r in rz.regras:
        if any(a[0] == "builtin" for a in r.corpo):
            out[r.nome] = "não verificável por SPARQL simples (builtin)"
            continue
        termo = lambda t: "?" + t[1].split("_")[-1] if t[0] == "var" else f"<{t[1]}>"
        pad = []
        for tipo, pred, args in r.corpo:
            pad.append(f"{termo(args[0])} a <{pred}> ." if tipo == "classe" else f"{termo(args[0])} <{pred}> {termo(args[1])} .")
        tipo, pred, args = r.cabeca[0]
        vs = sorted({termo(a) for a in args if a[0] == "var"})
        q = f"SELECT DISTINCT {' '.join(vs)} WHERE {{ {' '.join(pad)} }}"
        faltando, total = 0, 0
        for row in rz.g.query(q):
            lig = {v: row[v[1:]] for v in vs}
            v = [lig[termo(a)] if a[0] == "var" else a[1] for a in args]
            t = (v[0], RDF.type, pred) if tipo == "classe" else (v[0], pred, v[1])
            total += 1
            faltando += t not in rz.g
        out[r.nome] = {"cabecas_pelo_sparql": total, "faltando_no_grafo": faltando}
    return out


def verificar_seguranca(rz):
    proibidas = [t for t in rz.justificativa if t[1] in PROIBIDOS]
    vigente_de_proposta = [s for s in rz.g.subjects(RDF.type, H.ProspectiveRequirement)
                           if (s, RDF.type, H.ProspectiveRequirement) in rz.g and any(True for _ in rz.g.triples((s, H.hasLegalStatus, None)))]
    return {"inferencias_proibidas": len(proibidas), "requisitos_prospectivos_com_status_juridico": len(vigente_de_proposta)}


def alinhamento(rz):
    g = Graph().parse(ALIN)
    linhas = []
    for gm in sorted(set(g.subjects(RDFS.label)), key=lambda x: int(str(x).split("GM-")[1])):
        ex, pr = list(g.objects(gm, SKOS.exactMatch)), list(g.objects(gm, SKOS.closeMatch))
        alvos = ex + pr
        inf = [t for t in rz.justificativa if t[0] in alvos and ":" not in rz.justificativa[t]["regra"]]
        linhas.append({"gm": str(gm).split("#")[1], "rotulo": str(g.value(gm, RDFS.label)),
                       "tipo": "exato" if ex else "próximo" if pr else "ausente",
                       "alvos": [rz.curto(a) for a in alvos], "inferencias_swrl_sobre_alvos": len(inf),
                       "regras": sorted({rz.justificativa[t]["regra"] for t in inf}),
                       "nota": str(g.value(gm, RDFS.comment) or "")})
    return linhas


def caminho(rz, t, prof=0, linhas=None):
    linhas = [] if linhas is None else linhas
    j = rz.justificativa.get(t)
    s, p, o = (rz.curto(x) for x in t)
    if j and j["regra"] in ("owl:inverseOf", "rdfs:subClassOf"):
        linhas.append((prof, f"{s} {p} {o}", j["regra"]))
        for c in j["corpo"][:1]:
            caminho(rz, c, prof + 1, linhas)
        return linhas
    linhas.append((prof, f"{s} {p} {o}", j["regra"] if j else "declarada"))
    if j:
        for c in j["corpo"]:
            if c in rz.justificativa:
                caminho(rz, c, prof + 1, linhas)
    return linhas


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "tabelas").mkdir(exist_ok=True)
    rz0, r0, s0 = rodar()
    rz1, r1, s1 = rodar(E1)
    rzA, _, _ = rodar(ALIN)
    regras = [(r.nome, r.ressalva) for r in rz1.regras]
    dados = {
        "E0": resumo(rz0) | {"rodadas": r0, "segundos": round(s0, 2)},
        "E1": resumo(rz1) | {"rodadas": r1, "segundos": round(s1, 2)},
        "V1_E1": verificar_ponto_fixo(rz1), "V2_E1": verificar_seguranca(rz1), "V2_E0": verificar_seguranca(rz0),
        "A1": alinhamento(rzA),
    }
    PB = "https://hrai-go.aeonbridge.io/data/regulatory/br/pbia#"
    EX = "https://hrai-go.aeonbridge.io/data/regulatory/br/cenario-e1#"
    alvo = (URIRef(PB + "App_BBProvaDeVida"), H.applicationPotentiallyImpactedBy, URIRef(EX + "Mudanca_TextoCamara"))
    dados["E1_cadeia"] = caminho(rz1, alvo)
    dados["E1_inferencias_cenario"] = [[rz1.justificativa[t]["regra"]] + [rz1.curto(x) for x in t] for t in rz1.justificativa
                                       if "cenario-e1" in "".join(map(str, t)) and ":" not in rz1.justificativa[t]["regra"]]
    q = """SELECT ?req WHERE { ?req a <%sProspectiveRequirement> .
             FILTER NOT EXISTS { ?c <%scontrolPotentiallyAddressesRequirement> ?req } }""" % (H, H)
    dados["E1_requisitos_sem_controle"] = [rz1.curto(r[0]) for r in rz1.g.query(q)]
    (SAIDA / "dados.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # ---------- tabelas LaTeX ----------
    T = SAIDA / "tabelas"
    linhas = []
    for nome, ress in regras:
        a, b = dados["E0"]["inferidas_por_regra_swrl"].get(nome, 0), dados["E1"]["inferidas_por_regra_swrl"].get(nome, 0)
        linhas.append(f"{tex(nome.split('_')[0])} & {tex(nome.split('_', 1)[1])} & {a} & {b} \\\\")
    (T / "regras.tex").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    linhas = []
    for l in dados["A1"]:
        linhas.append(f"{l['gm']} & {tex(l['rotulo'])} & {l['tipo']} & {texq(', '.join(a.split(':')[1] for a in l['alvos'])) or '--'} & {l['inferencias_swrl_sobre_alvos'] or '--'} \\\\")
    (T / "alinhamento.tex").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    linhas = []
    for prof, txt, por in dados["E1_cadeia"]:
        linhas.append(f"\\cadeia{{{prof}}}{{{texq(txt)}}}{{{tex(por)}}}")
    (T / "cadeia.tex").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    linhas = []
    for nome, res in dados["V1_E1"].items():
        if isinstance(res, str):
            linhas.append(f"{tex(nome.split('_')[0])} & \\multicolumn{{2}}{{l}}{{{tex(res)}}} \\\\")
        else:
            linhas.append(f"{tex(nome.split('_')[0])} & {res['cabecas_pelo_sparql']} & {res['faltando_no_grafo']} \\\\")
    (T / "verificacao.tex").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    cont = {k: sum(1 for l in dados["A1"] if l["tipo"] == k) for k in ("exato", "próximo", "ausente")}
    print(json.dumps({"E0": {k: dados["E0"][k] for k in ("triplas_declaradas", "triplas_inferidas", "rodadas", "segundos")},
                      "E1": {k: dados["E1"][k] for k in ("triplas_declaradas", "triplas_inferidas", "rodadas", "segundos")},
                      "E0_regras_disparadas": len(dados["E0"]["inferidas_por_regra_swrl"]),
                      "E1_regras_disparadas": len(dados["E1"]["inferidas_por_regra_swrl"]),
                      "V1_faltando": sum(v["faltando_no_grafo"] for v in dados["V1_E1"].values() if isinstance(v, dict)),
                      "V2": dados["V2_E1"], "A1": cont, "sem_controle": dados["E1_requisitos_sem_controle"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
