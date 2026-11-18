#!/usr/bin/env python3
"""Turn a live session (room) into graph positions and a session report (ESP-ONT-02, RF-10; RT-VIS-03, M9).

Input: the rows of the room (table respostas: pid, k, v, setor, ts), read from a JSON export or from Supabase
(public read of the room, same as the big screen). Session assumptions (PREMISSAS.md):
  P-06  round 1 (blind position) = first position on the T5 axis, kept in key q2r1; round 3 = current q2.
  P-08  each published contribution (q4) is a human claim; reactions "apoio" and "contesto" are positions that
        support or challenge it; "fonte" is an evidence request.
  P-09  phone sectors map onto council strata (SETOR_ESTRATO below).
  P-12  people stay anonymous in the graph: nickname derived from the anonymous id, never the name.

Outputs, in docs/sessoes/<room>/:
  sessao.ttl        participants, claims and positions (SCSE deliberation layer, never source instances)
  relatorio.md      the four metrics of RF-10: breadth, anchoring, position revision, preserved divergence
  decisao-modelo.json  template of the human decision record; the session never fills it. When a person saves
                    it as decisao.json, the DecisionRecord is written into sessao.ttl.

Usage:
  python3 scripts/ontologia/sessao.py --sala ai-ethic-br --supabase          # live room (needs SUPABASE_URL/_ANON_KEY)
  python3 scripts/ontologia/sessao.py --sala ensaio-simulado --json docs/sessoes/ensaio-simulado/respostas.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

import rdflib
from rdflib import Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consultas  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
H = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/regulatory#")
S = rdflib.Namespace("https://hrai-go.aeonbridge.io/ontology/scse#")
GOV = rdflib.Namespace("https://hrai-go.aeonbridge.io/data/scse/gov-br-001#")
CURTO = {"gov": "Governo", "reg": "Regulador", "leg": "Legislativo", "est": "Estados", "aca": "Academia", "soc": "Sociedade", "pri": "Privado", "out": "Outro"}
SETOR_ESTRATO = {"gov": "PublicOperators", "reg": "Regulators", "leg": "PublicOperators", "est": "PublicOperators",
                 "aca": "Research", "soc": "CivilSociety", "pri": "Business", "out": "AffectedGroups"}   # premissa P-09
REVISION_MIN = 0.1   # change on the T5 axis (from -1 to 1) that counts as a revised position


def apelido(pid: str, setor: str | None) -> str:
    """Same nickname rule as the site (web/assets/sala-leitura.js)."""
    tail = "".join(ch for ch in pid if ch.isalnum())[-3:].lower()
    return f"{CURTO.get(setor or '', 'Pessoa')}·{tail}"


def load_rows(args) -> list[dict]:
    if args.json:
        return json.loads(Path(args.json).read_text(encoding="utf-8"))
    url, key = os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"]
    req = urllib.request.Request(f"{url}/rest/v1/respostas?sala=eq.{args.sala}&select=pid,k,v,setor,ts&order=ts",
                                 headers={"apikey": key, "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def build(sala: str, rows: list[dict], decision: dict | None) -> tuple[rdflib.Graph, dict]:
    ns = rdflib.Namespace(f"https://hrai-go.aeonbridge.io/data/sessoes/{sala}#")
    people: dict[str, dict] = defaultdict(dict)
    for r in sorted(rows, key=lambda r: r.get("ts", 0)):
        p = people[r["pid"]]
        p[r["k"]] = r["v"]
        if r.get("setor"):
            p["setor"] = r["setor"]
        if r.get("sim"):
            p["sim"] = True
    g = rdflib.Graph()
    for pref, n in (("hrai", H), ("scse", S), ("gov", GOV), ("ses", ns), ("dcterms", DCTERMS)):
        g.bind(pref, n)
    onto = URIRef(str(ns)[:-1])
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal(f"Sessão ao vivo '{sala}': posições humanas sobre afirmações (RF-10)", lang="pt")))
    g.add((onto, RDFS.comment, Literal("Gerado por scripts/ontologia/sessao.py. Pessoas anônimas (apelido). Camada de deliberação (SCSE).", lang="pt")))
    session = ns.Sessao
    g.add((session, RDF.type, S.Deliberation))
    g.add((session, RDFS.label, Literal(f"Sessão '{sala}'", lang="pt")))

    pid_node, claim_of = {}, {}
    for pid, p in people.items():
        x = ns["Pessoa_" + "".join(ch for ch in pid if ch.isalnum())[-12:]]
        pid_node[pid] = x
        g.add((x, RDF.type, H.Stakeholder))
        g.add((x, RDFS.label, Literal(apelido(pid, p.get("setor")), lang="pt")))
        if p.get("sim"):
            g.add((x, RDFS.comment, Literal("Participante simulado (ensaio).", lang="pt")))
        if p.get("setor") in SETOR_ESTRATO:
            g.add((x, S.stakeholderInStratum, GOV["Estrato_" + SETOR_ESTRATO[p["setor"]]]))
        g.add((session, H.deliberationIncludesStakeholder, x))
        if p.get("q1"):
            g.add((session, H.deliberatesOnTension, GOV["Semente_" + p["q1"]]))
        contrib = p.get("q4")
        if isinstance(contrib, dict) and contrib.get("tx"):
            c = ns["Contribuicao_" + str(x).split("_")[-1]]
            claim_of[pid] = c
            g.add((c, RDF.type, H.PolicyClaim))
            g.add((c, RDFS.label, Literal(contrib["tx"], lang="pt")))
            g.add((c, DCTERMS.creator, x))
            g.add((c, DCTERMS.type, Literal(contrib.get("mv", "challenge"))))
        if isinstance(p.get("q2"), (int, float)):
            now = ns["PosicaoT5_R3_" + str(x).split("_")[-1]]
            g.add((now, RDF.type, H.StakeholderPosition))
            g.add((now, H.positionExpressedBy, x))
            g.add((now, H.positionText, Literal(f"posição no eixo de T5: {p['q2']:+.2f} (rodada 3)")))
            if isinstance(p.get("q2r1"), (int, float)) and abs(p["q2r1"] - p["q2"]) >= REVISION_MIN:
                before = ns["PosicaoT5_R1_" + str(x).split("_")[-1]]
                g.add((before, RDF.type, H.StakeholderPosition))
                g.add((before, H.positionExpressedBy, x))
                g.add((before, H.positionText, Literal(f"posição no eixo de T5: {p['q2r1']:+.2f} (rodada 1, cega)")))
                g.add((before, S.positionRevisedAs, now))

    support, challenge, evidence_requests = defaultdict(set), defaultdict(set), defaultdict(int)
    for pid, p in people.items():
        for k, v in p.items():
            if not (isinstance(k, str) and k.startswith("r:")) or k[2:] not in claim_of:
                continue
            claim = claim_of[k[2:]]
            if v == "fonte":
                evidence_requests[claim] += 1
                g.add((claim, S.evidenceRequestedBy, pid_node[pid]))
                continue
            if v not in ("apoio", "contesto"):
                continue
            pos = ns[f"Reacao_{str(pid_node[pid]).split('_')[-1]}_{str(claim).split('_')[-1]}"]
            g.add((pos, RDF.type, H.StakeholderPosition))
            g.add((pos, H.positionExpressedBy, pid_node[pid]))
            g.add((pos, H.positionSupportsClaim if v == "apoio" else H.positionChallengesClaim, claim))
            g.add((session, H.deliberationIncludesPosition, pos))
            (support if v == "apoio" else challenge)[claim].add(people[pid].get("setor"))

    # Metrics (RF-10, ESP-ONT-02 section "Como medir se ajudou").
    graph = consultas.reasoned_graph()
    seed_claims = {c for t in g.objects(session, H.deliberatesOnTension) for c in graph.objects(t, H.hasPolicyClaim)}
    considered = seed_claims | set(claim_of.values())
    evidenced = {c for c in seed_claims if (c, RDF.type, H.EvidencedPolicyClaim) in graph or (c, H.claimSupportedByEvidence, None) in graph}
    cited = seed_claims | set(support) | set(challenge)
    with_position = [p for p in people.values() if isinstance(p.get("q2r1"), (int, float)) and isinstance(p.get("q2"), (int, float))]
    revised = sum(1 for p in with_position if abs(p["q2r1"] - p["q2"]) >= REVISION_MIN)
    divergent = [c for c in claim_of.values() if support[c] and challenge[c] and (support[c] | challenge[c]) - {None} and len(support[c] | challenge[c]) > 1
                 and not (support[c] == challenge[c] and len(support[c]) == 1)]
    metrics = {
        "participantes": len(people), "simulados": sum(1 for p in people.values() if p.get("sim")),
        "amplitude": len(considered),
        "ancoragem": round(len(evidenced) / len(cited), 3) if cited else None,
        "revisaoDePosicao": {"revisaram": revised, "comPosicaoNasDuasRodadas": len(with_position)},
        "divergenciaPreservada": len(divergent),
        "pedidosDeFonte": sum(evidence_requests.values()),
    }
    if decision:
        d = ns.Decisao
        g.add((d, RDF.type, S.DecisionRecord))
        g.add((d, RDFS.label, Literal(decision["texto"], lang="pt")))
        g.add((d, DCTERMS.creator, Literal(decision["registradoPor"])))
        g.add((d, DCTERMS.date, Literal(decision["data"], datatype=XSD.date)))
        for cid in decision.get("afirmacoesCitadas", []):
            g.add((d, S.decisionCitesClaim, URIRef(cid)))
        for cid in decision.get("divergenciasPreservadas", []):
            g.add((d, RDFS.seeAlso, URIRef(cid)))
    return g, {"metricas": metrics, "divergentes": [str(c) for c in divergent], "afirmacoesConsideradas": sorted(map(str, considered))}


def report(sala: str, m: dict, decision: dict | None) -> str:
    met = m["metricas"]
    sim = f" ({met['simulados']} simulados)" if met["simulados"] else ""
    anc = f"{met['ancoragem']:.0%}" if met["ancoragem"] is not None else "—"
    rev = met["revisaoDePosicao"]
    return "\n".join([
        f"# Relatório da sessão '{sala}'", "",
        "Gerado por `scripts/ontologia/sessao.py` a partir das respostas da sala (RF-10). Pessoas anônimas. "
        "O conselho sintético não vota: só posições humanas entram nas métricas (I-4).", "",
        "| Métrica | Valor | O que mede |", "|---|---|---|",
        f"| Participantes | {met['participantes']}{sim} | pessoas que registraram ao menos uma resposta |",
        f"| Amplitude | {met['amplitude']} | afirmações consideradas (das tensões escolhidas e das contribuições) |",
        f"| Ancoragem | {anc} | fração das afirmações citadas que têm evidência no corpus |",
        f"| Revisão de posição | {rev['revisaram']} de {rev['comPosicaoNasDuasRodadas']} | posições que mudaram entre a rodada 1 (cega) e a 3 (premissa P-06) |",
        f"| Divergência preservada | {met['divergenciaPreservada']} | contribuições com apoio e contestação de estratos diferentes |",
        f"| Pedidos de fonte | {met['pedidosDeFonte']} | reações \"falta fonte\" |", "",
        "## Decisão humana", "",
        (f"Registrada por {decision['registradoPor']} em {decision['data']}: {decision['texto']}" if decision else
         "Ainda não registrada. Preencha `decisao-modelo.json`, salve como `decisao.json` e rode o script de novo."), ""])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sala", required=True)
    ap.add_argument("--json")
    ap.add_argument("--supabase", action="store_true")
    args = ap.parse_args()
    if not args.json and not args.supabase:
        ap.error("use --json ARQUIVO ou --supabase")
    out = ROOT / "docs/sessoes" / args.sala
    out.mkdir(parents=True, exist_ok=True)
    decision_file = out / "decisao.json"
    decision = json.loads(decision_file.read_text(encoding="utf-8")) if decision_file.exists() else None
    g, m = build(args.sala, load_rows(args), decision)
    (out / "sessao.ttl").write_text("# Gerado por scripts/ontologia/sessao.py.\n" + g.serialize(format="turtle"), encoding="utf-8")
    (out / "metricas.json").write_text(json.dumps(m, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (out / "relatorio.md").write_text(report(args.sala, m, decision), encoding="utf-8")
    (out / "decisao-modelo.json").write_text(json.dumps({
        "registradoPor": "nome da pessoa da coordenação que registra a decisão",
        "data": "AAAA-MM-DD", "texto": "decisão tomada na rodada 4, com a justificativa",
        "afirmacoesCitadas": ["IRI das afirmações em que a decisão se apoia (ver metricas.json)"],
        "divergenciasPreservadas": m["divergentes"]}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(m["metricas"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
