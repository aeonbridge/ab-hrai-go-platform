"""Classifica as afirmações de um arquivo de teses (hrai:PolicyClaim) pelo raciocinador e gera tabela LaTeX + JSON.

Status derivado só do grafo:
  contestada          -> inferida hrai:ContestedPolicyClaim (R05): há contra-afirmação explícita
  com evidência       -> inferida hrai:EvidencedPolicyClaim (R17): há evidência anexada do corpus
  sem evidência       -> nenhuma das duas: hipótese a testar
Uso: python scripts/ontologia/afirmacoes.py [arquivo.ttl] [pasta-saida]
"""
import json
import sys
from pathlib import Path

from rdflib import RDF, RDFS, URIRef

sys.path.insert(0, str(Path(__file__).parent))
from raciocinar import RAIZ, TBOX, ABOX_PBIA, H, Raciocinador  # noqa: E402
from experimentos import tex  # noqa: E402

ARQ = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "ontologies/regulatory/afirmacoes/A1_analise_comparativa_BR_AIAct.ttl"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "docs/especificacoes/ESP-ONT-02"


def main():
    rz = Raciocinador(TBOX, ABOX_PBIA, ARQ)
    rz.executar()
    g = rz.g
    teses = sorted((s for s in g.subjects(RDF.type, H.PolicyClaim) if "/claims/" in str(s) and str(s).split("#")[1].startswith("C")),
                   key=lambda s: str(s))
    linhas, dados = [], []
    for s in teses:
        contestada = (s, RDF.type, H.ContestedPolicyClaim) in g
        evid = (s, RDF.type, H.EvidencedPolicyClaim) in g
        status = "contestada" if contestada else "com evidência" if evid else "sem evidência no corpus"
        ev = [str(g.value(e, RDFS.label)) for e in g.objects(s, H.claimSupportedByEvidence)]
        contra = []
        for k in g.objects(s, H.challengedByClaim):
            contra.append({"afirmacao": str(g.value(k, RDFS.label)), "evidencias": [str(g.value(e, RDFS.label)) for e in g.objects(k, H.claimSupportedByEvidence)]})
        d = {"id": str(s).split("#")[1], "tese": str(g.value(s, RDFS.label)), "status": status, "evidencias": ev,
             "contestada_por": contra, "nota": str(g.value(s, RDFS.comment) or "")}
        dados.append(d)
        obs = "; ".join([c["afirmacao"] for c in contra] + ([d["nota"]] if d["nota"] else []))
        linhas.append(f"{d['id']} & {tex(d['tese'])} & \\textbf{{{tex(status)}}} & {tex(obs) or '--'} \\\\")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tabelas").mkdir(exist_ok=True)
    (OUT / "tabelas/afirmacoes.tex").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    (OUT / "afirmacoes.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    from collections import Counter
    print(Counter(d["status"] for d in dados))


if __name__ == "__main__":
    main()
