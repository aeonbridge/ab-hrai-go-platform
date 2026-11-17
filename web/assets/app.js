/* HRAI·GO · aplicação do observatório.
   Transporte ao vivo: Supabase (Postgres + Realtime, sessão anônima, RLS por participante).
   Sem configuração: modo local entre abas do mesmo navegador (ensaio), mais simulação no telão. */
(() => {
"use strict";
const C = window.HRAIGO_CONTEUDO, CFG = window.HRAIGO_CONFIG || {};
const LV = ["", "baixa", "moderada", "alta", "crítica"];
const $ = s => document.querySelector(s);
const el = (tag, a = {}, ...kids) => { const n = document.createElement(tag);
  for (const [k, v] of Object.entries(a)) { if (v == null || v === false) continue;
    if (k === "class") n.className = v; else if (k === "html") n.innerHTML = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v === true ? "" : v); }
  for (const c of kids.flat()) { if (c == null || c === false) continue; n.append(c.nodeType ? c : document.createTextNode(String(c))); }
  return n; };
const put = (n, ...k) => n.replaceChildren(...k.flat().filter(x => x != null && x !== false));
const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
const sgn = v => (v > 0 ? "+" : "") + (Math.round(v * 10) / 10).toString().replace(".", ",");
const adeVar = v => v <= -1.5 ? "--ade-n2" : v <= -.5 ? "--ade-n1" : v < .5 ? "--ade-0" : v < 1.5 ? "--ade-p1" : "--ade-p2";
const dataBR = d => d.split("-").reverse().join("/");

/* ---------- sala ---------- */
const params = new URLSearchParams(location.search);
let SALA = (params.get("sala") || ls.get("hraigo.sala") || "").toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 40);
if (SALA.length < 4) SALA = "sala-" + Math.random().toString(36).slice(2, 8);
ls.set("hraigo.sala", SALA);
if (location.protocol.startsWith("http") && params.get("sala") !== SALA) { const u = new URL(location.href); u.searchParams.set("sala", SALA); history.replaceState(null, "", u); }

const S = { pid: ls.get("hraigo.pid") || ("local-" + Math.random().toString(36).slice(2, 10)), setor: ls.get("hraigo.setor"), resp: {}, passo: 0,
  msgs: new Map(), sim: [], ocultar: new Set(), textos: true, vista: "participar", kbSel: "br", kbQ: "", monF: "todos", modo: "local" };
ls.set("hraigo.pid", S.pid);
try { S.resp = JSON.parse(ls.get("hraigo.resp." + SALA) || "{}"); } catch (e) {}

const estado = $("#estado");
const status = (cls, txt) => { estado.className = "estado " + cls; estado.querySelector("span").textContent = txt; };

/* ---------- transporte ---------- */
const bc = "BroadcastChannel" in window ? new BroadcastChannel("hraigo-" + SALA) : null;
function ingest(m) {
  if (!m || !m.pid || !m.k) return;
  const key = m.pid + "|" + m.k, prev = S.msgs.get(key);
  if (!prev || (m.ts || 0) >= (prev.ts || 0)) { S.msgs.set(key, m); agendar(); }
}
if (bc) bc.onmessage = e => ingest(e.data);
let enviar = async m => { ingest(m); bc && bc.postMessage(m); };

async function iniciarSupabase() {
  status("", "conectando");
  const sb = supabase.createClient(CFG.supabaseUrl, CFG.supabaseAnonKey, { auth: { persistSession: true, storageKey: "hraigo-auth" } });
  let { data: { session } } = await sb.auth.getSession();
  if (!session) {
    const r = await sb.auth.signInAnonymously();
    if (r.error) throw r.error;
    session = r.data.session;
  }
  S.pid = session.user.id; S.modo = "supabase";
  const linha = r => ({ pid: r.pid, k: r.k, v: r.v, setor: r.setor, ts: r.ts });
  const { data, error } = await sb.from("respostas").select("pid,k,v,setor,ts").eq("sala", SALA).limit(5000);
  if (error) throw error;
  data.forEach(r => ingest(linha(r)));
  sb.channel("sala:" + SALA)
    .on("postgres_changes", { event: "*", schema: "public", table: "respostas", filter: "sala=eq." + SALA }, p => p.new && ingest(linha(p.new)))
    .subscribe(st => {
      if (st === "SUBSCRIBED") status("vivo", "ao vivo · " + SALA);
      else if (st === "CHANNEL_ERROR" || st === "TIMED_OUT") status("erro", "tempo real indisponível");
    });
  enviar = async m => {
    ingest(m);
    const { error } = await sb.from("respostas").upsert({ sala: SALA, pid: S.pid, k: m.k, v: m.v, setor: m.setor || null, ts: m.ts }, { onConflict: "sala,pid,k" });
    if (error) throw error;
  };
}

async function registrar(k, v) {
  S.resp[k] = v; ls.set("hraigo.resp." + SALA, JSON.stringify(S.resp));
  const m = { pid: S.pid, k, v, setor: S.setor, ts: Date.now() };
  const r = $("#registro");
  try { await enviar(m); if (r) { r.textContent = "✓ registrado"; r.className = "registro"; } }
  catch (e) { console.warn(e); if (r) { r.textContent = "Não foi possível enviar. Verifique a conexão e toque de novo."; r.className = "registro erro"; } }
}

/* ---------- agregação ---------- */
function participantes() {
  const by = new Map();
  for (const m of [...S.msgs.values(), ...S.sim]) {
    let p = by.get(m.pid); if (!p) { p = { pid: m.pid, sim: !!m.sim }; by.set(m.pid, p); }
    p[m.k] = m; if (m.setor) p.setor = m.setor; if (m.k === "setor") p.setor = m.v;
  }
  return [...by.values()];
}
function simular(n) {
  const sorteia = a => a[Math.floor(Math.random() * a.length)], agora = Date.now();
  const falas = [["challenge","Auditoria prévia sem credenciamento de auditores vira carimbo."],["evidence","Qual o custo médio de uma auditoria para uma startup brasileira?"],["amend","Escalonar por risco e porte, com prazo maior para pequenas empresas."],["support","Serviços públicos essenciais precisam de auditoria antes de operar."],["challenge","Testes com dados sintéticos não captam o viés do histórico real."],["evidence","Quantos sistemas de IA o governo federal usa hoje? Não há inventário público."],["amend","Registro público obrigatório de algoritmos usados por órgãos federais."]];
  for (let i = 0; i < n; i++) {
    const pid = "sim-" + (S.sim.length + i), setor = sorteia(C.setores)[0], b = { pid, setor, sim: true, ts: agora };
    S.sim.push({ ...b, k: "setor", v: setor },
      { ...b, k: "q1", v: Math.random() < .42 ? "t2" : Math.random() < .5 ? "t1" : sorteia(C.tensoes)[0] },
      { ...b, k: "q2", v: Math.max(-1, Math.min(1, (Math.random() - .55) * 1.4)) },
      { ...b, k: "q3", v: Object.fromEntries(C.modelos.map(([id, , a]) => [id, Math.max(-2, Math.min(2, Math.round(a + (id === "ue" ? 2 : 0) + (Math.random() - .5) * 2)))])) });
    if (Math.random() < .6) { const f = sorteia(falas); S.sim.push({ ...b, k: "q4", v: { mv: f[0], tx: f[1] } }); }
  }
  agendar();
}
let raf = 0; function agendar() { cancelAnimationFrame(raf); raf = requestAnimationFrame(render); }
function linkParticipar() { const u = new URL(location.href); u.searchParams.set("sala", SALA); u.hash = "participar"; return u.toString(); }

/* ---------- participar ---------- */
const TOTAL = 5;
function renderParticipar() {
  const p = $("#part"), st = S.passo;
  const navegar = (pode, rot) => el("div", { class: "acoes" },
    st > 0 ? el("button", { class: "bt leve", onclick: () => { S.passo--; render(); } }, "Voltar") : el("span"),
    el("button", { class: "bt ipe", disabled: !pode, onclick: () => { S.passo++; render(); scrollTo({ top: 0, behavior: "smooth" }); } }, rot || "Próximo"));
  const reg = el("div", { class: "registro", id: "registro", "aria-live": "polite" });
  const topo = (n, rot, perg, apoio) => [el("div", { class: "progresso" }, el("i", { style: `width:${Math.min(n, TOTAL) / TOTAL * 100}%` })),
    el("div", { class: "passo-n" }, String(n).padStart(2, "0"), el("small", {}, "/0" + TOTAL)), el("div", { class: "rotulo" }, rot), el("h1", { class: "pergunta" }, perg), apoio ? el("p", { class: "apoio" }, apoio) : null];
  if (st === 0) {
    put(p, ...topo(1, "anônimo · nenhum nome é coletado", "De onde você olha para a governança de IA?", "O setor serve só para mostrar no telão a diversidade de perspectivas na sala."),
      el("div", { class: "opcoes" }, C.setores.map(([k, l]) => el("button", { class: "opcao", "aria-pressed": String(S.setor === k), onclick: () => { S.setor = k; ls.set("hraigo.setor", k); registrar("setor", k); render(); } }, el("span", { class: "marca-op" }), l, el("span"))) ), reg, navegar(!!S.setor));
  } else if (st === 1) {
    put(p, ...topo(2, "prioridade", "Qual tensão o Brasil precisa resolver primeiro?", "Ao lado de cada uma, a criticidade estimada pelo modelo. Você pode discordar dela."),
      el("div", { class: "opcoes" }, C.tensoes.map(([k, l, c]) => el("button", { class: "opcao", "aria-pressed": String(S.resp.q1 === k), onclick: () => { registrar("q1", k); render(); } }, el("span", { class: "marca-op" }), l, el("span", { class: "k" }, "modelo: " + LV[c])))), reg, navegar(!!S.resp.q1));
  } else if (st === 2) {
    const r = el("input", { class: "eixo-input", type: "range", min: "-100", max: "100", step: "5", value: String(Math.round((S.resp.q2 ?? 0) * 100)), "aria-label": "Sua posição entre os dois polos" });
    r.addEventListener("change", () => registrar("q2", Number(r.value) / 100));
    put(p, ...topo(3, "posição", "Onde você se posiciona nesta tensão?", "No telão, sua posição aparece no mesmo eixo que os assentos sintéticos do Conselho das Sombras."),
      el("div", { class: "polos" }, el("span", {}, C.polos[0]), el("span", {}, C.polos[1])), r, reg, navegar(S.resp.q2 != null));
  } else if (st === 3) {
    const q3 = S.resp.q3 || {};
    put(p, ...topo(4, "comparação de modelos", "Quão adequado cada modelo seria ao Brasil em " + C.criterio + "?", "De −2 (inadequado) a +2 (muito adequado). Os agentes já deram a leitura deles; o telão mostra onde vocês divergem."),
      el("div", { class: "notas" }, C.modelos.flatMap(([id, n]) => [el("b", {}, n), el("div", {}, el("div", { class: "escala", role: "group", "aria-label": n },
        [-2, -1, 0, 1, 2].map(v => el("button", { "aria-pressed": String(q3[id] === v), onclick: () => { registrar("q3", { ...q3, [id]: v }); render(); } }, (v > 0 ? "+" : "") + v))))])),
      reg, navegar(Object.keys(q3).length >= 3));
  } else if (st === 4) {
    let mv = S.resp.q4?.mv || "challenge";
    const ta = el("textarea", { id: "q4t", maxlength: "280", placeholder: "Até 280 caracteres. O que falta nesse debate?", "aria-label": "Sua contribuição" }); ta.value = S.resp.q4?.tx || "";
    const movs = el("div", { class: "movs", role: "group", "aria-label": "Tipo de contribuição" }, C.movimentos.map(([k, l]) => el("button", { class: "mov", "aria-pressed": String(mv === k), onclick: e => { mv = k; movs.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b === e.currentTarget))); } }, l)));
    put(p, ...topo(5, "contribuição", "O que você leva para a mesa?", null), movs, ta, reg,
      el("div", { class: "acoes" }, el("button", { class: "bt leve", onclick: () => { S.passo--; render(); } }, "Voltar"),
        el("button", { class: "bt ipe", onclick: async () => { const t = ta.value.trim(); if (t.length > 2) await registrar("q4", { mv, tx: t.slice(0, 280) }); S.passo = 5; render(); } }, "Enviar")));
  } else {
    put(p, el("div", { class: "progresso" }, el("i", { style: "width:100%" })),
      el("div", { class: "fim" }, el("h1", { class: "pergunta" }, "Obrigado. O resultado está no telão."),
        el("p", { class: "apoio" }, "Você pode mudar suas respostas até o fim da sessão; vale a última. Enquanto isso, explore a base de conhecimento e o monitoramento.")),
      el("div", { class: "acoes" }, el("a", { class: "bt", href: "#conhecimento" }, "Conhecimento"), el("a", { class: "bt", href: "#monitoramento" }, "Monitoramento")),
      el("button", { class: "bt leve", style: "margin-top:16px", onclick: () => { S.passo = 0; render(); } }, "Revisar respostas"));
  }
}

/* ---------- ao vivo ---------- */
let qrUrl = "", qrSvg = "";
function renderLateral() {
  const url = linkParticipar();
  if (url !== qrUrl) { qrUrl = url; const q = qrcode(0, "M"); q.addData(url); q.make(); qrSvg = q.createSvgTag({ cellSize: 6, margin: 0, scalable: true }); }
  const ps = participantes(), reais = ps.filter(p => !p.sim).length;
  put($("#lateral"),
    el("div", { class: "qr", html: qrSvg, role: "img", "aria-label": "QR code para participar" }),
    el("div", {}, el("div", { class: "contagem" }, String(ps.length)), el("div", { class: "contagem-l" }, "participantes" + (S.sim.length ? ` · ${ps.length - reais} simulados` : ""))),
    el("div", { class: "link" }, url),
    S.modo === "local" ? el("div", { class: "aviso" }, "Modo local: o Supabase não está configurado. A participação só funciona entre abas deste navegador.") : null,
    el("div", { class: "ctrls" },
      el("button", { class: "bt", onclick: () => simular(12) }, S.sim.length ? "+12 simulados" : "Simular participantes"),
      S.sim.length ? el("button", { class: "bt", onclick: () => { S.sim = []; agendar(); } }, "Remover simulação") : null,
      el("button", { class: "bt", onclick: () => { S.textos = !S.textos; agendar(); } }, S.textos ? "Ocultar textos" : "Mostrar textos"),
      el("button", { class: "bt", onclick: () => { const u = new URL(location.href); u.searchParams.set("sala", "sala-" + Math.random().toString(36).slice(2, 8)); ls.set("hraigo.sala", ""); location.href = u.toString(); } }, "Nova sala")));
}
function celSVG(a, h) { return `<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><polygon points="0,0 100,0 0,100" fill="var(${adeVar(a)})"/><polygon points="100,0 100,100 0,100" fill="${h == null ? "var(--papel-2)" : `var(${adeVar(h)})`}"/><line x1="100" y1="0" x2="0" y2="100" stroke="var(--papel)" stroke-width="3" vector-effect="non-scaling-stroke"/></svg>`; }
const barras = (linhas, max) => el("div", { class: "barras" }, linhas.map(([rot, n, extra]) => el("div", { class: "barra" },
  el("div", { class: "r" }, el("span", {}, rot, extra ? " " : null, extra || null), el("span", { class: "dado" }, String(n))), el("div", { class: "t" }, el("i", { style: `width:${n / Math.max(1, max) * 100}%` })))));
function renderBlocos() {
  const ps = participantes();
  const setores = C.setores.map(([k, l]) => [l, ps.filter(p => p.setor === k).length]).filter(x => x[1]).sort((a, b) => b[1] - a[1]);
  const q1 = C.tensoes.map(([k, l, c]) => [l, ps.filter(p => p.q1 && p.q1.v === k).length, el("span", { class: "selo" }, "modelo: " + LV[c])]).sort((a, b) => b[1] - a[1]);
  const n1 = q1.reduce((a, x) => a + x[1], 0);
  const pos = ps.filter(p => p.q2 && typeof p.q2.v === "number").map(p => p.q2.v);
  const med = pos.length ? [...pos].sort((a, b) => a - b)[Math.floor(pos.length / 2)] : null;
  const X = v => (v + 1) / 2 * 100;
  const campo = el("div", { class: "campo", role: "img", "aria-label": "Assentos sintéticos acima do eixo, pessoas abaixo" }, el("div", { class: "eixo" }));
  C.assentos.forEach(([c, l, v], i) => campo.append(el("div", { class: "mk s", style: `left:${X(v)}%;top:${20 + (i % 2) * 17}%`, title: l + " (sintético)" }, el("span", {}, c))));
  pos.forEach((v, i) => campo.append(el("div", { class: "mk h", style: `left:${X(v)}%;top:${63 + (i * 37) % 30}%` })));
  if (med != null) campo.append(el("div", { class: "mk med", style: `left:${X(med)}%` }, el("b", {}, "mediana da sala")));
  const mediaS = C.assentos.reduce((a, s) => a + s[2], 0) / C.assentos.length;
  const q3 = C.modelos.map(([id, n, a]) => { const vs = ps.map(p => p.q3 && p.q3.v && p.q3.v[id]).filter(v => typeof v === "number"); return { n, a, h: vs.length ? vs.reduce((x, y) => x + y, 0) / vs.length : null }; });
  const falas = ps.filter(p => p.q4 && p.q4.v && p.q4.v.tx && !S.ocultar.has(p.pid)).map(p => ({ pid: p.pid, sim: p.sim, mv: p.q4.v.mv, tx: p.q4.v.tx, ts: p.q4.ts || 0, setor: p.setor })).sort((a, b) => b.ts - a.ts);
  const cab = (p, t, n) => el("div", { class: "bloco-cab" }, el("span", { class: "p" }, p), el("h2", {}, t), el("span", { class: "n" }, n));
  put($("#blocos"),
    el("section", { class: "bloco" }, cab("P1", "Quem está na sala", ps.length + " pessoas"),
      setores.length ? barras(setores, setores[0][1]) : el("p", { class: "apoio" }, "Aguardando os primeiros participantes."),
      setores.length && setores.length < 4 ? el("div", { class: "aviso" }, "Poucos setores representados. Leia os resultados com cautela.") : null),
    el("section", { class: "bloco" }, cab("P2", "O que resolver primeiro", n1 + " respostas"), barras(q1, Math.max(...q1.map(x => x[1]), 1))),
    el("section", { class: "bloco largo" }, cab("P3", "Pessoas e Conselho das Sombras no mesmo eixo", pos.length + " pessoas · " + C.assentos.length + " assentos sintéticos"),
      el("div", { class: "legenda" }, el("span", {}, el("span", { class: "losango" }), "assentos sintéticos (acima)"), el("span", {}, el("span", { class: "ponto" }), "pessoas na sala (abaixo)")),
      campo, el("div", { class: "polos-t" }, el("span", {}, "← " + C.polos[0]), el("span", {}, C.polos[1] + " →")),
      med != null ? el("p", { class: "apoio", style: "margin:0" }, `Mediana da sala: ${sgn(med)}. Média dos assentos sintéticos: ${sgn(mediaS)}. A sala não representa a população.`) : null),
    el("section", { class: "bloco largo" }, cab("P4", "Onde agentes e pessoas divergem", "adequação ao Brasil em " + C.criterio),
      el("div", { class: "prisma" }, q3.map(m => el("div", { class: "cel" }, el("div", { class: "q", html: celSVG(m.a, m.h) + (m.h != null && Math.abs(m.h - m.a) >= 1.5 ? '<span class="ne">≠ diverge</span>' : "") }),
        el("b", {}, m.n), el("small", {}, "agentes " + sgn(m.a) + " · sala " + (m.h == null ? "—" : sgn(m.h)))))),
      el("div", { class: "legenda" }, el("span", {}, "triângulo superior: leitura dos agentes · inferior: média da sala"))),
    el("section", { class: "bloco largo" }, cab("P5", "O que a sala trouxe para a mesa", falas.length + " contribuições"),
      !S.textos ? el("p", { class: "apoio" }, "Textos ocultos pelo apresentador.") :
      falas.length ? el("div", { class: "mural" }, falas.slice(0, 12).map(f => el("div", { class: "fala " + f.mv },
        el("span", { class: "m" }, (C.movimentos.find(m => m[0] === f.mv) || ["", ""])[1]), el("p", {}, f.tx),
        el("small", {}, (C.setores.find(s => s[0] === f.setor) || ["", "sem setor"])[1] + (f.sim ? " · simulado" : "")),
        el("button", { onclick: () => { S.ocultar.add(f.pid); agendar(); } }, "ocultar")))) : el("p", { class: "apoio" }, "As contribuições aparecem aqui assim que chegam.")));
}

/* ---------- conhecimento ---------- */
function renderKB() {
  const q = S.kbQ.toLowerCase();
  const lista = q ? C.jurisdicoes.map(j => ({ ...j, itens: j.itens.filter(i => (i.t + i.d + i.rel + j.n).toLowerCase().includes(q)) })).filter(j => j.itens.length) : C.jurisdicoes.filter(j => j.id === S.kbSel);
  const busca = el("input", { type: "search", id: "kbq", placeholder: "Buscar: risco, sandbox, Omnibus…", "aria-label": "Buscar na base de conhecimento" }); busca.value = S.kbQ;
  busca.addEventListener("input", () => { S.kbQ = busca.value; renderKB(); const n = $("#kbq"); n.focus(); n.setSelectionRange(n.value.length, n.value.length); });
  put($("#kb"), el("nav", { class: "indice", "aria-label": "Jurisdições" }, busca, C.jurisdicoes.map(j => el("button", { "aria-pressed": String(!q && S.kbSel === j.id), onclick: () => { S.kbSel = j.id; S.kbQ = ""; renderKB(); } }, j.n))),
    el("div", {}, lista.length ? lista.map(j => el("article", { class: "jur" }, el("h2", {}, j.n), el("p", { class: "modelo" }, j.modelo),
      j.itens.map(i => el("div", { class: "item" }, el("h3", {}, i.t), el("span", { class: "selo " + i.st[1] }, i.st[0]), el("p", {}, i.d),
        el("div", { class: "rel" }, el("b", {}, "Por que importa para o Brasil: "), i.rel),
        el("div", { class: "fonte" }, i.f.length ? ["Fonte: ", ...i.f.flatMap(([l, u], x) => [x ? ", " : "", el("a", { href: u, target: "_blank", rel: "noopener" }, l)])] : "Fonte primária a confirmar."))))) : el("p", { class: "apoio" }, "Nada encontrado."),
      el("p", { class: "nota" }, "Estado em nov/2026, a partir de fontes oficiais e secundárias. Itens marcados “Verificar” vêm de conhecimento prévio e precisam de checagem antes de uso formal.")));
}

/* ---------- monitoramento ---------- */
function renderMon() {
  const hoje = new Date().toISOString().slice(0, 10), f = S.monF;
  const evs = C.eventos.filter(e => f === "todos" || (f === "fut" ? e[0] > hoje : e[1] === f || (e[1] === "fut" && ((f === "br") === /PBIA/.test(e[2])))));
  const linha = []; let ano = "", marcado = false;
  for (const e of evs) {
    if (!marcado && e[0] > hoje) { linha.push(el("div", { class: "hoje" }, "hoje · " + dataBR(hoje))); marcado = true; }
    if (e[0].slice(0, 4) !== ano) { ano = e[0].slice(0, 4); linha.push(el("div", { class: "ano" }, ano)); }
    linha.push(el("div", { class: "ev " + e[1] }, el("span", { class: "d" }, dataBR(e[0])), el("span", { class: "tr" }, el("i")),
      el("div", { class: "c" }, el("b", {}, e[2]), el("p", {}, e[3]), e[4] ? el("span", { class: "selo sint" }, "ontologia: " + e[4]) : null)));
  }
  put($("#mon"), el("h1", {}, "Pulso normativo"),
    el("p", { class: "apoio", style: "margin-top:10px" }, "Cada evento pode se tornar um RegulatoryChangeEvent na ontologia HRAI·GO e reabrir conclusões por regras SWRL, sempre com revisão humana antes de publicar."),
    el("div", { class: "filtros", role: "group", "aria-label": "Filtro" }, [["todos", "Tudo"], ["br", "Brasil"], ["mu", "Mundo"], ["fut", "Próximos marcos"]].map(([k, l]) => el("button", { "aria-pressed": String(f === k), onclick: () => { S.monF = k; renderMon(); } }, l))),
    linha, el("p", { class: "nota" }, "Datas de fontes secundárias consultadas em nov/2026; confirmar nas fontes oficiais."));
}

/* ---------- rotas ---------- */
const VISTAS = ["participar", "ao-vivo", "conhecimento", "monitoramento"];
function rota() {
  const v = location.hash.slice(1);
  S.vista = VISTAS.includes(v) ? v : (params.get("sala") ? "participar" : (matchMedia("(min-width: 1050px)").matches ? "ao-vivo" : "participar"));
  for (const n of VISTAS) $("#v-" + n).hidden = n !== S.vista;
  document.body.classList.toggle("modo-tela", S.vista === "ao-vivo");
  document.querySelectorAll(".menu a").forEach(a => a.setAttribute("aria-current", a.dataset.v === S.vista ? "page" : "false"));
  render();
}
function render() {
  if (S.vista === "participar") { const a = document.activeElement; if (!(a && a.id === "q4t")) renderParticipar(); }
  if (S.vista === "ao-vivo") { renderLateral(); renderBlocos(); }
  if (S.vista === "conhecimento" && !$("#kb").childElementCount) renderKB();
  if (S.vista === "monitoramento" && !$("#mon").childElementCount) renderMon();
}
addEventListener("hashchange", rota);
$("#sala-rotulo").textContent = "observatório · " + SALA;
rota();
if (CFG.supabaseUrl && CFG.supabaseAnonKey && window.supabase) {
  iniciarSupabase().catch(e => { console.warn(e); S.modo = "local"; status("erro", "sem conexão: " + (e.message || "erro").slice(0, 40)); agendar(); });
} else status("", "modo local · ensaio");
})();
