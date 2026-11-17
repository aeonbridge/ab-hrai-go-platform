#!/usr/bin/env python3
"""Build run-backed copies of the SCSE prototype pages.

The original prototypes (``shadow-council-tour.html`` and ``mural-de-tensoes.html``)
ship with illustrative example data. This script reads the latest completed run of a
scenario (``runs/<scenario>/latest.json``) and writes two new self-contained pages whose
data comes from that run only:

* ``shadow-council-tour-execucao.html``: tour with the real roster (seat, provider,
  model), blind R1 expectations, coverage gaps, deliberation arcs (challenge, support,
  amendment), round counts, provider usage and the 21 proposals with the stance of each
  stratum.
* ``mural-de-tensoes-execucao.html``: tension wall as a social feed (strata as stories,
  proposals as posts with the council table as cover), built from
  ``mural-feed.template.html`` with the run embedded, so it opens from ``file://``.

The originals are never modified. Usage::

    python3 scripts/build_run_prototypes.py [--scenario GOV-BR-001]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPES = ROOT / "docs/scse/prototipo"
TOUR_SRC = PROTOTYPES / "shadow-council-tour.html"
MURAL_TEMPLATE = PROTOTYPES / "mural-feed.template.html"
TOUR_OUT = PROTOTYPES / "shadow-council-tour-execucao.html"
MURAL_OUT = PROTOTYPES / "mural-de-tensoes-execucao.html"

STRATA_SHORT_PT = {"regulators": "Reguladores", "publicOperators": "Poder público", "business": "Empresas", "research": "Pesquisa",
                   "civilSociety": "Sociedade civil", "workers": "Trabalhadores", "affectedGroups": "Afetados", "infrastructure": "Infraestrutura"}
PROVIDER_ORDER = ["anthropic", "openai", "xai", "gemini"]  # same order as PROV in the tour
SHORT_PROPOSAL_CHARS = 420
SHORT_STATEMENT_CHARS = 300


# ---------------------------------------------------------------- helpers
def load_json(path: Path):
    """Read a UTF-8 JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    """Read a UTF-8 JSON Lines file, skipping blank lines."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def js(value) -> str:
    """Serialise a value as a JS literal that is safe inside a <script> element."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def shorten(text: str | None, limit: int) -> str:
    """Cut text at a sentence or word boundary, marking the cut with an ellipsis."""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    stop = max(cut.rfind(". "), cut.rfind("; "))
    if stop > limit * 0.55:
        return cut[: stop + 1]
    return cut[: cut.rfind(" ")].rstrip(",;:") + "…"


def replace_once(html: str, old: str, new: str) -> str:
    """Replace a fragment that must occur exactly once in the source page."""
    count = html.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one occurrence, found {count}: {old[:90]!r}")
    return html.replace(old, new)


def replace_between(html: str, start: str, end: str, new: str) -> str:
    """Replace html[start:end) (start marker included, end marker kept)."""
    i = html.index(start)
    j = html.index(end, i)
    if html.count(start) != 1:
        raise SystemExit(f"Start marker is not unique: {start[:60]!r}")
    return html[:i] + new + html[j:]


# ---------------------------------------------------------------- run data
def load_run(scenario: str) -> dict:
    """Collect everything both pages need from the latest run of ``scenario``."""
    scenario_dir = ROOT / "runs" / scenario
    index = load_json(scenario_dir / "latest.json")
    if index.get("dryRun"):
        raise SystemExit("latest.json points to a dry run; run a real execution first.")
    run_dir = scenario_dir / index["runId"]
    rep = run_dir / "rep-01"
    return {
        "scenarioDir": scenario_dir,
        "index": index,
        "packet": load_json(scenario_dir / index["packetPath"]),
        "summary": load_json(rep / "run-summary.json"),
        "roster": load_json(rep / "council-roster.json"),
        "claims": load_json(rep / "claims.json"),
        "events": load_jsonl(rep / "deliberation-events.jsonl"),
        "scorecard": load_json(rep / "provider-scorecard.json"),
        "turns": load_json(rep / "turn-stats.json"),
        "httpLines": sum(1 for _ in (rep / "http/openrouter-http.jsonl").open(encoding="utf-8")),
    }


def humanize(text: str | None, glossary: dict) -> str:
    """Plain-text version of a council statement: codes become names, pure source lists in parentheses go away."""
    text = text or ""
    if not glossary:
        return text
    keys = sorted(glossary, key=len, reverse=True)
    code_re = re.compile(r"(?<![\w-])(" + "|".join(re.escape(k) for k in keys) + r")(?![\w-])")

    def drop_sources(match: re.Match) -> str:
        inner = match.group(1)
        codes = code_re.findall(inner)
        rest = re.sub(r"[\s,;]|\be\b", "", code_re.sub("", inner))
        if codes and not rest and all(glossary[c]["kind"] in {"source", "indicator", "claim"} for c in codes):
            return ""
        return match.group(0)

    text = re.sub(r"\s?\(([^()]{2,500})\)", drop_sources, text)
    text = code_re.sub(lambda m: m.group(1) if re.fullmatch(r"[A-Z]+", m.group(1)) else glossary[m.group(1)]["plain"], text)
    return re.sub(r"\s+([,.;:])", r"\1", text)


def proposal_for_tour(p: dict, stratum_ids: list[str], glossary: dict | None = None) -> dict:
    """Map a packet proposal to the PROPS shape used by the tour."""
    pos = {}
    by_stratum = {r["stratumId"]: r for r in p["stratumPositions"]}
    for sid in stratum_ids:
        row = by_stratum.get(sid) or {"stance": "silent", "statements": []}
        stance = row["stance"] if row["stance"] in {"for", "against", "amend", "split"} else "silent"
        texts = [s["text"] for s in row.get("statements", []) if s.get("text")]
        pos[sid] = [stance, shorten(humanize(texts[0], glossary or {}), SHORT_STATEMENT_CHARS) if texts else ""]
    title = p.get("proposedTitle") or shorten(p.get("title"), 110)
    author = p.get("author") or {}
    support = p.get("support") or {}
    flags = []
    if p.get("requiresLegalReview"):
        flags.append("revisão jurídica")
    if p.get("weakEvidence"):
        flags.append("evidência fraca")
    if p.get("genericity") == "generic":
        flags.append("genérica: serviria a qualquer país")
    meta = f"autor {author.get('provider', '?')} · {support.get('seats', 0)} assento(s) em apoio · {len(p.get('challenges') or [])} contestação(ões) · {len(p.get('amendments') or [])} emenda(s)"
    has_comp = bool(p.get("componentId")) and p.get("change") in {"modify", "remove", "keep"}
    return {
        "id": p["proposalId"],
        "lens": p["lens"],
        "change": p["change"],
        "comp": p.get("componentId") if has_comp else None,
        "topic": p.get("topic"),
        "title": title,
        "text": shorten(humanize(p.get("text"), glossary or {}), SHORT_PROPOSAL_CHARS),
        "full": humanize(p.get("text"), glossary or {}),
        "proposed": humanize(p.get("proposedDescription"), glossary or {}),
        "reps": f"{p.get('replicateCount', 1)}/{p.get('of', 1)}",
        "raised": author.get("stratumId"),
        "feats": p.get("contextFeatureIds") or None,
        "tensions": p.get("tensionIds") or [],
        "legal": bool(p.get("requiresLegalReview")),
        "flags": flags,
        "meta": meta,
        "pos": pos,
    }


def build_arcs(claims: list[dict], seat_index: dict[str, int]) -> list[list[int]]:
    """Deliberation arcs [fromSeat, toSeat or -1, kind]; kind 0 challenge, 1 support, 2 amendment."""
    by_id = {c["id"]: c for c in claims}
    arcs: list[list[int]] = []
    for c in claims:
        src = seat_index.get(c["agentId"])
        target = by_id.get(c.get("targetClaimId") or "")
        if c["kind"] == "challenge" and target and src is not None:
            dst = seat_index.get(target["agentId"])
            if dst is not None and dst != src:
                arcs.append([src, dst, 0])
        if c["kind"] == "amendment" and src is not None:
            arcs.append([src, -1, 2])
        for supporter in c.get("supporters") or []:
            sup = seat_index.get(supporter)
            dst = seat_index.get(c["agentId"])
            if sup is not None and dst is not None and sup != dst:
                arcs.append([sup, dst, 1])
    return arcs


def tour_run_object(run: dict, stratum_ids: list[str]) -> dict:
    """Facts shown by the run-backed tour (RUN constant)."""
    index, packet, events = run["index"], run["packet"], run["events"]
    seats_by_stratum = {s["stratumId"]: s for s in run["roster"]["seats"]}
    seats = []
    for sid in stratum_ids:
        s = seats_by_stratum.get(sid)
        if s:
            seats.append({"agentId": s["agentId"], "stratumId": sid, "provider": s["provider"], "model": s["model"],
                          "role": s["charter"]["role"], "p": PROVIDER_ORDER.index(s["provider"]) if s["provider"] in PROVIDER_ORDER else 0})
    seat_index = {s["agentId"]: i for i, s in enumerate(seats)}
    actions = Counter((e.get("roundId"), e.get("action")) for e in events if e["type"] in {"action.accepted", "claim.challenged"})
    aggregated = next((e["payload"] for e in events if e["type"] == "expectations.aggregated"), {})
    expectations = [x for sp in packet["strataPerspectives"] for x in sp.get("blindExpectations", [])]
    usage = {"calls": 0, "inputTokens": 0, "outputTokens": 0, "costUsd": 0.0}
    for card in run["scorecard"].values():
        for u in (card.get("usage") or {}).values():
            for k in usage:
                usage[k] += u.get(k, 0)
    started = [e["timestamp"] for e in events if e["type"] == "scenario.ingested"]
    finished = [e["timestamp"] for e in events if e["type"] == "run.completed"]
    rel = "../../../runs/" + index["scenarioId"] + "/"
    arcs = build_arcs(run["claims"], seat_index)
    return {
        "runId": index["runId"],
        "scenarioId": index["scenarioId"],
        "generatedAt": index["generatedAt"],
        "startedAt": started[0] if started else None,
        "finishedAt": finished[0] if finished else None,
        "seats": seats,
        "byProvider": run["roster"]["balance"]["byProvider"],
        "coverage": run["roster"]["coverage"],
        "summary": run["summary"],
        "rounds": {
            "R1": actions[("R1", "assertClaim")],
            "R2": actions[("R2", "assertClaim")],
            "R3": {"challenge": actions[("R3", "challenge")], "support": actions[("R3", "support")], "requestEvidence": actions[("R3", "requestEvidence")]},
            "R4": {"revise": actions[("R4", "revise")], "withdraw": actions[("R4", "withdraw")]},
            "R5": actions[("R5", "proposeAmendment")],
            "R6": actions[("R6", "assertClaim")],
        },
        "r1": {"expectations": len(expectations), "topics": aggregated.get("topics"),
               "gaps": aggregated.get("gaps", []), "fragile": aggregated.get("fragile", [])},
        "arcCounts": dict(Counter(a[2] for a in arcs)),
        "arcs": arcs,
        "usage": {**usage, "costUsd": round(usage["costUsd"], 2)},
        "turns": len(run["turns"]),
        "httpPairs": run["httpLines"] // 2,
        "links": {
            "report": rel + index["reportPath"],
            "packet": rel + index["packetPath"],
            "http": rel + index["httpTracePath"],
        },
    }


# ---------------------------------------------------------------- tour
def build_tour(run: dict) -> str:
    """Return the run-backed tour page."""
    html = TOUR_SRC.read_text(encoding="utf-8")
    packet = run["packet"]

    # D: keep the model structure, take strata seats and unrepresented perspectives from the run.
    d_start = html.index("const D = ") + len("const D = ")
    d_end = html.index(";\n", d_start)
    data = json.loads(html[d_start:d_end])
    data["strata"] = [{"id": s["stratumId"], "label": s["label"], "seats": s["seats"]} for s in packet["strata"]]
    data["unrep"] = [u["perspective"] for u in run["roster"].get("unrepresented", [])]
    stratum_ids = [s["id"] for s in data["strata"]]
    run_obj = tour_run_object(run, stratum_ids)
    html = html[:d_start] + js(data) + ";\nconst RUN = " + js(run_obj) + html[d_end:]

    glossary = build_glossary(run)
    props = [proposal_for_tour(p, stratum_ids, glossary) for p in packet["proposals"]]
    html = replace_between(html, "/* Example proposals for the review step.", "const STANCE = {",
                           "/* Proposals from the real run (merged revision packet). pos: stance and first argument of each stratum. */\n"
                           f"const PROPS = {js(props)};\n")
    expect = {}
    for sp in packet["strataPerspectives"]:
        topics = []
        for x in sp.get("blindExpectations", []):
            if x.get("topic") and x["topic"] not in topics:
                topics.append(x["topic"])
        expect[sp["stratumId"]] = topics
    html = replace_between(html, "const EXPECT = {", "function spread(p)",
                           f"/* Blind R1 expectations recorded in the run, per stratum. */\nconst EXPECT = {js(expect)};\n")

    rep = [
        ("<title>Shadow Council Tour</title>", f"<title>Shadow Council Tour · execução {run_obj['scenarioId']}</title>"),
        ('<div class="kicker">SCSE v2 · protótipo de aplicação</div>',
         f'<div class="kicker">SCSE v2 · execução real {run_obj["scenarioId"]}</div>'),
        ("Estrutura do modelo, taxonomia e contexto são os do repositório; propostas e números de deliberação são exemplos e estão marcados.",
         f"Dados da execução <span class=\"mono\">{run_obj['runId']}</span>: {len(run_obj['seats'])} assentos via OpenRouter, "
         f"rodadas R1–R7, {run_obj['summary']['publicClaims']} claims públicos e {len(props)} propostas. Conselho sintético; mundo com indicadores fictícios."),
        ('<span class="full chip">Modelo <b id="ver">v0.1.0</b></span>',
         '<span class="full chip">Modelo <b id="ver">v0.1.0</b></span> <span class="full chip">Execução real</span>'),
        ('title:"20 assentos, 8 estratos, 4 famílias de modelos"', 'title:`${RUN.seats.length} assentos, ${D.strata.length} estratos, 4 famílias de modelos`'),
        ("As famílias de modelos se alternam dentro de cada estrato, para separar viés de modelo de perspectiva.</p>",
         "Nesta execução houve um assento por estrato e dois por família de modelo. Cobertura documental: ${RUN.coverage.numerator}/${RUN.coverage.denominator} perspectivas.</p>"),
        ("${D.unrep.length} perspectivas sem fonte documental, como povos indígenas e o Judiciário, ficam fora e aparecem no relatório como ausentes.",
         "${D.unrep.length} perspectiva(s) sem fonte documental (${D.unrep.map(esc).join(\", \")}) fica(m) fora e aparece(m) no relatório como ausente(s)."),
        ('${p.name} · 25%', '${p.name} · ${RUN.byProvider[p.id]||0} assentos'),
        ('<p><span class="tag demo">exemplo</span> <span class="muted">Fluxo ilustrativo. Numa execução real, as expectativas vêm dos modelos.</span></p>',
         '<p><span class="tag">execução real</span> <span class="muted">${RUN.r1.expectations} expectativas de ${RUN.seats.length} assentos, sobre ${RUN.r1.topics} áreas. O fluxo mostra as áreas que cada estrato esperou.</span></p>'),
        ('<div class="detail"><span class="id">${FRAGILE.length} áreas frágeis</span>',
         '<div class="detail"><span class="id">Na R1 desta execução</span><p>Esperadas pelo conselho e sem componente: ${RUN.r1.gaps.map(t=>esc(TOPIC[t]?TOPIC[t].label:t)).join(" · ")}. Esperadas e frágeis: ${RUN.r1.fragile.map(t=>esc(TOPIC[t]?TOPIC[t].label:t)).join(" · ")}.</p></div>\n   <div class="detail"><span class="id">${FRAGILE.length} áreas frágeis</span>'),
        ('<li data-r="2"><b>R2</b>Achados nas três lentes, com a matriz à vista</li>',
         '<li data-r="2"><b>R2</b>Achados nas três lentes, com a matriz à vista · ${RUN.rounds.R2} achados</li>'),
        ('<li data-r="3"><b>R3</b>Contestação, apoio e pedidos de evidência</li>',
         '<li data-r="3"><b>R3</b>Contestação, apoio e pedidos de evidência · ${RUN.rounds.R3.challenge} contestações, ${RUN.rounds.R3.support} apoios, ${RUN.rounds.R3.requestEvidence} pedidos</li>'),
        ('<li data-r="4"><b>R4</b>Quem foi contestado mantém, revisa ou retira</li>',
         '<li data-r="4"><b>R4</b>Quem foi contestado mantém, revisa ou retira · ${RUN.rounds.R4.revise} revisões, ${RUN.rounds.R4.withdraw} retirada</li>'),
        ('<li data-r="5"><b>R5</b>Propostas concretas: adicionar, modificar, remover</li>',
         '<li data-r="5"><b>R5</b>Propostas concretas: adicionar, modificar, remover · ${RUN.rounds.R5} emendas</li>'),
        ('<li data-r="7"><b>R7</b>Dissenso preservado, fontes auditadas, genéricos marcados</li>',
         '<li data-r="7"><b>R7</b>Dissenso preservado, fontes auditadas, genéricos marcados · ${RUN.summary.insufficientGrounding} claims com fundamentação insuficiente, ${RUN.summary.minorityOpinions} opiniões minoritárias</li>'),
        ('<span class="tag demo">arcos de exemplo</span>',
         '<span class="tag">arcos da execução: ${RUN.arcCounts[0]||0} contestações · ${RUN.arcCounts[1]||0} apoios · ${RUN.arcCounts[2]||0} emendas</span>'),
        ('<p class="muted">Proposta que só vale num ramo é frágil.',
         '<p>Na R6 desta execução, o conselho registrou ${RUN.summary.branchClaims} achados sob os ramos.</p>\n   <p class="muted">Proposta que só vale num ramo é frágil.'),
        ('Calar não é concordar: o estrato não se pronunciou. <span class="tag demo">exemplo</span></p>',
         'Calar não é concordar: o estrato não se pronunciou.</p>'),
        ('<span class="tag demo">propostas de exemplo</span>', '<span class="tag">${PROPS.length} propostas da execução</span>'),
        ('<div class="row"><button class="btn small" id="fill">Preencher exemplo</button><span class="muted">para apresentar sem digitar</span></div>\n', ''),
        ('extra:"Posição de exemplo."', 'extra:"Posição registrada na execução."'),
        ('extra:`Família de modelo nesta réplica: ${PROV[u.p].name}. Na próxima réplica, outra.`',
         'extra:RUN.seats[u.i] ? `${RUN.seats[u.i].role} · modelo ${RUN.seats[u.i].model}` : ""'),
        ('const x = Math.cos(a)*R, z = Math.sin(a)*R, p = idx % 4;',
         'const x = Math.cos(a)*R, z = Math.sin(a)*R, p = RUN.seats[idx] ? RUN.seats[idx].p : idx % 4;'),
        ('ex:PROPS[0]}', 'ex:PROPS.find(p => p.lens === "omission")}'),
        ('ex:PROPS[4]}', 'ex:PROPS.find(p => p.lens === "excess")}'),
        ('ex:PROPS[6]}', 'ex:PROPS.find(p => p.lens === "advantage")}'),
        ('<span class="id">${L.ex.id} · exemplo</span>', '<span class="id">${L.ex.id} · da execução</span>'),
        ('    <h4>${esc(p.title)}</h4>\n    <p>${esc(p.text)}</p>',
         '    <h4>${esc(p.title)}</h4>\n    <p>${esc(p.text)}</p>\n'
         '    ${p.full && p.full !== p.text ? `<details><summary>Texto integral e redação proposta</summary><p>${esc(p.full)}</p>${p.proposed ? `<p><b>Redação proposta:</b> ${esc(p.proposed)}</p>` : ""}</details>` : ""}'),
        ('réplicas ${p.reps} · levantada por ${esc(STRATA_PT[p.raised])}',
         'réplicas ${p.reps} · levantada por ${esc(STRATA_PT[p.raised])}${p.tensions.length ? ` · tensões ${p.tensions.join(", ")}` : ""}<br>${esc(p.meta)}'),
        ('<li>Runtime do conselho com 86 testes offline</li>',
         '<li>Runtime do conselho com 86 testes offline</li>\n       <li>Execução real ${esc(RUN.runId)}: ${RUN.turns} turnos, ${RUN.httpPairs} pares HTTP gravados, ${RUN.usage.calls} chamadas, US$ ${RUN.usage.costUsd.toFixed(2)}</li>'),
        ('<li>Primeira execução com modelos reais</li>',
         '<li>Mais réplicas: esta execução teve 1, sem medir estabilidade</li>\n       <li>Entender por que houve ${RUN.summary.tensions} tensões entre estratos detectadas</li>'),
        ('<div class="row"><button class="btn primary" data-go="0">Rever o tour</button>',
         '<p class="muted"><a href="${RUN.links.report}" style="color:var(--brass-2)">relatório</a> · <a href="${RUN.links.packet}" style="color:var(--brass-2)">pacote de revisão</a> · <a href="${RUN.links.http}" style="color:var(--brass-2)">trilha HTTP (.jsonl)</a> · <a href="mural-de-tensoes-execucao.html" style="color:var(--brass-2)">mural de tensões</a></p>\n'
         '   <div class="row"><button class="btn primary" data-go="0">Rever o tour</button>'),
    ]
    for old, new in rep:
        html = replace_once(html, old, new)
    html = html.replace("https://claude.ai/artifact/8QP1JLSsZed2z2f2CS4vSh", "mural-de-tensoes-execucao.html")

    # Deliberation arcs from the real claims graph instead of seeded random pairs.
    html = replace_between(html, "  const arcList = []; {", "\n  /* ---- lenses ---- */", """  const arcList = []; {
    const cols = ["#FF7A59","#38C2B4","#E8A33D"];
    RUN.arcs.forEach(([from, to, ki], n) => {
      const a = seats[from]; if (!a) return;
      const end = ki === 2 || !seats[to] ? new T.Vector3(0, 5, 0) : seats[to].pos;
      const lift = ki === 2 ? 1.2 : 2.2 + (n % 5) * .4;
      const pts = []; for (let i = 0; i <= 48; i++) pts.push(bez(a.pos, end, lift, i/48, new T.Vector3()));
      const geo = new T.BufferGeometry().setFromPoints(pts); geo.setDrawRange(0, 0);
      const line = new T.Line(geo, lineMat(cols[ki], .95, true)); line.userData.noFade = true;
      arcs.add(line); arcList.push({line, start: (n * 10.5 / Math.max(1, RUN.arcs.length)) % 10.5, kind: ki});
    });
  }
""")
    html = html.replace("/* ---- deliberation arcs (illustrative) ---- */", "/* ---- deliberation arcs (from the run) ---- */")
    html = html.replace("/* ---- blind-round expectation flow (illustrative) ---- */", "/* ---- blind-round expectation flow (from the run) ---- */")
    return html


# ---------------------------------------------------------------- mural
PACKET_KEYS = ("packetId", "scenarioId", "modelId", "modelVersion", "asOfDate", "replicates", "notice", "strata", "seedTensions")
PROPOSAL_KEYS = ("proposalId", "lens", "change", "componentId", "componentTitle", "topic", "title", "text", "proposedTitle",
                 "proposedDescription", "tensionIds", "author", "support", "challenges", "amendments", "requiresLegalReview",
                 "weakEvidence", "genericity", "contextFeatureIds", "stratumPositions")
STATEMENT_KEYS = ("agentId", "provider", "stance", "role", "roundId", "text")


def slim_packet(packet: dict) -> dict:
    """Keep only the packet fields the feed renders, so the page stays light."""
    out = {k: packet.get(k) for k in PACKET_KEYS}
    out["proposals"] = []
    for p in packet["proposals"]:
        q = {k: p.get(k) for k in PROPOSAL_KEYS}
        q["challenges"] = [{"claimId": c.get("claimId")} for c in p.get("challenges") or []]
        q["amendments"] = [{"claimId": a.get("claimId")} for a in p.get("amendments") or []]
        q["stratumPositions"] = [
            {"stratumId": r["stratumId"], "stance": r["stance"],
             "statements": [{k: s.get(k) for k in STATEMENT_KEYS} for s in r.get("statements") or []]}
            for r in p["stratumPositions"]
        ]
        out["proposals"].append(q)
    return out


def _short_title(title: str, limit: int = 46) -> str:
    """Readable inline name: drop the [Fictício] prefix and trailing parentheticals, cap the length."""
    title = re.sub(r"^\[Fict[ií]cio\]\s*", "", title or "").strip()
    head = re.split(r"\s+\(|:\s", title, maxsplit=1)[0].strip() or title
    if len(head) < 14:
        head = re.sub(r"\s*\([^)]*\)?", "", title).strip() or title
    return shorten(head, limit)


def build_glossary(run: dict) -> dict:
    """Map every code the council cites (GM, CF, CTX, IND, sources, claim ids) to a human-readable entry.

    Sources are the scenario files under ``scenarios/`` (model components, dated context facts and
    features, world evidence and indicators) plus the run's claims, so each code shown in the feed
    can be replaced by a name and opened for detail.
    """
    glossary: dict[str, dict] = {}

    def add(code, kind, name, detail="", fictional=False):
        if code and code not in glossary:
            glossary[code] = {"kind": kind, "name": name, "short": _short_title(name), "plain": _short_title(name, 90),
                              "detail": detail, "fictional": bool(fictional)}

    for path in sorted((ROOT / "scenarios").rglob("*.json")):
        if path.name.startswith("._"):
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(doc, dict):
            continue
        for c in doc.get("components") or []:
            if isinstance(c, dict) and str(c.get("id", "")).startswith("GM-"):
                add(c["id"], "component", c.get("title", c["id"]), c.get("description", ""))
        for f in doc.get("features") or []:
            if isinstance(f, dict) and str(f.get("id", "")).startswith("CF-"):
                add(f["id"], "feature", f.get("title", f["id"]), f.get("description", ""))
        for f in doc.get("facts") or []:
            if isinstance(f, dict) and str(f.get("id", "")).startswith("CTX-"):
                add(f["id"], "fact", f.get("title", f["id"]), f.get("text", ""), "fict" in (f.get("title", "") + f.get("text", "")).lower())
        for e in doc.get("evidence") or []:
            if isinstance(e, dict) and e.get("id"):
                add(e["id"], "source", e.get("title", e["id"]), e.get("excerpt", ""), e.get("synthetic"))
        for i in doc.get("contextIndicators") or []:
            if isinstance(i, dict) and i.get("id"):
                value = i.get("value")
                unit = i.get("unit") or ""
                shown = f"{value} {unit}".strip() if unit not in {"status"} else str(value)
                add(i["id"], "indicator", f"{i.get('name', i['id'])}: {shown}", "", i.get("synthetic"))
    strata = {s["stratumId"]: s["label"] for s in run["packet"]["strata"]}
    for c in run["claims"]:
        label = strata.get(c.get("stratumId"), c.get("stratumId", ""))
        round_id = c.get("roundId", "")
        add(c["id"], "claim", f"fala de {STRATA_SHORT_PT.get(c.get('stratumId'), label)} na {round_id}", shorten(c.get("text"), 600))
    return glossary


def _topic_labels() -> dict:
    """Taxonomy topic id -> Portuguese label, for proposals that target a topic instead of a component."""
    path = ROOT / "scenarios/governanca-brasil/taxonomy.json"
    if not path.exists():
        return {}
    return {t["id"]: t["label"] for t in load_json(path).get("topics", [])}


def build_mural(run: dict) -> str:
    """Return the run-backed tension wall: a social-feed page with the run embedded."""
    html = MURAL_TEMPLATE.read_text(encoding="utf-8")
    payload = {
        "index": run["index"],
        "summary": run["summary"],
        "packet": slim_packet(run["packet"]),
        "seats": [{"stratumId": s["stratumId"], "provider": s["provider"], "model": s["model"]} for s in run["roster"]["seats"]],
        "glossary": {},
        "topics": _topic_labels(),
    }
    # Keep only the codes the embedded packet actually cites.
    cited = json.dumps(payload["packet"], ensure_ascii=False)
    payload["glossary"] = {k: v for k, v in build_glossary(run).items() if re.search(rf"(?<![\w-]){re.escape(k)}(?![\w-])", cited)}
    html = replace_once(html, "<title>Mural de Tensões</title>", f"<title>Mural de Tensões · {run['index']['scenarioId']}</title>")
    return replace_once(html, "/*__RUN__*/null", js(payload))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scenario", default="GOV-BR-001")
    args = parser.parse_args()
    run = load_run(args.scenario)
    TOUR_OUT.write_text(build_tour(run), encoding="utf-8")
    MURAL_OUT.write_text(build_mural(run), encoding="utf-8")
    print(f"{TOUR_OUT.relative_to(ROOT)}\n{MURAL_OUT.relative_to(ROOT)}\nrun {run['index']['runId']}")


if __name__ == "__main__":
    main()
