/* HRAI·GO · aplicação do observatório.
   Transporte ao vivo: Supabase (Postgres + Realtime, sessão anônima, RLS por participante).
   Sem configuração: modo local entre abas do mesmo navegador (ensaio), mais simulação no telão. */
(() => {
"use strict";
const C = window.HRAIGO_CONTEUDO, M = window.HRAIGO_MODELO, CFG = window.HRAIGO_CONFIG || {};
const SEMENTES = M.seeds.map(s => [s.id, s.title]);
const LACUNAS = M.topics.filter(t => t.strength === "none").map(t => [t.id, t.label]);
const ESTRATO = Object.fromEntries(M.strata.map(s => [s.id, s.label]));
const COD = {regulators:"REG",publicOperators:"POD",business:"EMP",research:"PES",civilSociety:"SOC",workers:"TRA",affectedGroups:"AFE",infrastructure:"INF"};
const STATUS = {effective:["Em vigor","vigente"],policy:["Política pública","politica"],proposed:["Projeto de lei","proposta"]};
const TIPO = {instrument:"Instrumento",institution:"Instituição",mechanism:"Mecanismo",resource:"Recurso",metric:"Métrica"};
const FORCA = {inForce:["coberta","vigente"],proposedOnly:["só por projeto de lei","proposta"],inferredOnly:["só por leitura inferida","inferido"],none:["sem componente","lacuna"]};
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
const dataBR = d => d.split("-").reverse().join("/");

/* ---------- sala ---------- */
const params = new URLSearchParams(location.search);
const EV = window.HRAIGO_EVENTO || {};
let SALA = (params.get("sala") || EV.sala || ls.get("hraigo.sala") || "").toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 40);
if (SALA.length < 4) SALA = "sala-" + Math.random().toString(36).slice(2, 8);
ls.set("hraigo.sala", SALA);
if (location.protocol.startsWith("http") && params.get("sala") !== SALA) { const u = new URL(location.href); u.searchParams.set("sala", SALA); history.replaceState(null, "", u); }

const CURTO = { gov: "Governo", reg: "Regulador", leg: "Legislativo", est: "Estados", aca: "Academia", soc: "Sociedade", pri: "Privado", out: "Outro" };
const apelido = (pid, setor) => (CURTO[setor] || "Pessoa") + "·" + String(pid || "").replace(/[^a-z0-9]/gi, "").slice(-3).toLowerCase();   /* mesma fórmula de sala-leitura.js */
const S = { pid: ls.get("hraigo.pid") || ("local-" + Math.random().toString(36).slice(2, 10)), setor: ls.get("hraigo.setor"), resp: {}, passo: 0,
  msgs: new Map(), sim: [], ocultar: new Set(), textos: true, vista: "participar", kbSel: "modelo", kbQ: "", monF: "todos", modo: "local" };
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
  S.pid = session.user.id; S.modo = "supabase"; status("vivo", "conectado · " + SALA); agendar();
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
      { ...b, k: "q1", v: Math.random() < .4 ? "T5" : Math.random() < .5 ? "T4" : sorteia(SEMENTES)[0] },
      { ...b, k: "q2", v: Math.max(-1, Math.min(1, (Math.random() - .55) * 1.4)) },
      { ...b, k: "q3", v: Math.random() < .35 ? "participation" : Math.random() < .5 ? "children-vulnerable" : sorteia(LACUNAS)[0] });
    if (Math.random() < .6) { const f = sorteia(falas); S.sim.push({ ...b, k: "q4", v: { mv: f[0], tx: f[1] } }); }
  }
  agendar();
}
/* atualizações vindas da sala não redesenham o formulário de participação: refazer o DOM entre o toque e a soltura
   faz o iPhone perder o toque ("Próximo" exigindo dois toques). O formulário só redesenha com ações da própria pessoa. */
let raf = 0; function agendar() { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => render(false)); }
function linkParticipar() { if (EV.linkPublico && EV.sala === SALA) return EV.linkPublico; const u = new URL(location.href); u.searchParams.set("sala", SALA); u.hash = "participar"; return u.toString(); }

/* ---------- participar ---------- */
const TOTAL = 5;
function renderParticipar() {
  const p = $("#part"), st = S.passo;
  const navegar = (pode, rot) => el("div", { class: "acoes" },
    st > 0 ? el("button", { class: "bt leve", onclick: () => { S.passo--; render(); } }, "Voltar") : el("span"),
    el("button", { class: "bt ipe", disabled: !pode, onclick: () => { S.passo++; render(); scrollTo({ top: 0, behavior: "smooth" }); } }, rot || "Próximo"));
  const reg = el("div", { class: "registro", id: "registro", "aria-live": "polite" });
  const topo = (n, rot, perg, apoio) => [el("div", { class: "progresso", "aria-label": `passo ${n} de ${TOTAL}` }, Array.from({ length: TOTAL }, (_, i) => el("i", { class: i < n ? "on" : "" }))),
    el("div", { class: "eyebrow rotulo" }, `Passo ${n} de ${TOTAL} · ${rot}`), el("h1", { class: "pergunta" }, perg), apoio ? el("p", { class: "apoio" }, apoio) : null];
  if (st === 0) {
    put(p, ...topo(1, "anônimo · seu nome só aparece se você quiser", "De onde você olha para a governança de IA?", "O setor serve só para mostrar no telão a diversidade de perspectivas na sala."),
      el("div", { class: "opcoes" }, C.setores.map(([k, l]) => el("button", { class: "opcao", "aria-pressed": String(S.setor === k), onclick: () => { S.setor = k; ls.set("hraigo.setor", k); registrar("setor", k); render(); } }, el("span", { class: "marca-op" }), l, el("span"))) ), reg, navegar(!!S.setor));
  } else if (st === 1) {
    put(p, ...topo(2, "prioridade", "Qual tensão do modelo brasileiro precisa ser enfrentada primeiro?", "São as seis tensões-semente que o Shadow Council usa para questionar o modelo."),
      el("div", { class: "opcoes" }, SEMENTES.map(([k, l]) => el("button", { class: "opcao", "aria-pressed": String(S.resp.q1 === k), onclick: () => { registrar("q1", k); render(); } }, el("span", { class: "marca-op" }), l, el("span", { class: "k" }, k)))), reg, navegar(!!S.resp.q1));
  } else if (st === 2) {
    const r = el("input", { class: "eixo-input", type: "range", min: "-100", max: "100", step: "5", value: String(Math.round((S.resp.q2 ?? 0) * 100)), "aria-label": "Sua posição entre os dois polos" });
    r.addEventListener("change", () => registrar("q2", Number(r.value) / 100));
    put(p, ...topo(3, "posição", "Onde você se posiciona nesta tensão?", "Tensão T5 do modelo. No telão, sua posição aparece no mesmo eixo que os oito estratos do Shadow Council."),
      el("div", { class: "polos" }, el("span", {}, C.polos[0]), el("span", {}, C.polos[1])), r, reg,
      el("div", { class: "acoes" }, el("button", { class: "bt leve", onclick: () => { S.passo--; render(); } }, "Voltar"),
        el("button", { class: "bt ipe", onclick: async () => { if (S.resp.q2 == null) await registrar("q2", Number(r.value) / 100); S.passo++; render(); scrollTo({ top: 0, behavior: "smooth" }); } }, "Próximo")));
  } else if (st === 3) {
    put(p, ...topo(4, "lente Q1 · omissão", "Qual lacuna do modelo brasileiro é mais urgente?", "Nenhum dos " + M.components.length + " componentes do modelo cobre estas áreas. Ao lado, quantos estratos do conselho sintético esperavam cada uma antes de ver o modelo."),
      el("div", { class: "opcoes" }, LACUNAS.map(([k, l]) => { const n = (C.esperadoPor[k] || []).length;
        return el("button", { class: "opcao", "aria-pressed": String(S.resp.q3 === k), onclick: () => { registrar("q3", k); render(); } }, el("span", { class: "marca-op" }), l, el("span", { class: "k" }, n ? `esperada por ${n} estrato${n > 1 ? "s" : ""}` : "nenhum estrato esperava")); })),
      reg, navegar(!!S.resp.q3));
  } else if (st === 4) {
    let mv = S.resp.q4?.mv || "challenge";
    const ta = el("textarea", { id: "q4t", maxlength: "280", placeholder: "Até 280 caracteres. O que falta nesse debate?", "aria-label": "Sua contribuição" }); ta.value = S.resp.q4?.tx || "";
    const movs = el("div", { class: "movs", role: "group", "aria-label": "Tipo de contribuição" }, C.movimentos.map(([k, l]) => el("button", { class: "mov", "aria-pressed": String(mv === k), onclick: e => { mv = k; movs.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b === e.currentTarget))); } }, l)));
    put(p, ...topo(5, "contribuição", "O que você leva para a mesa?", null), movs, ta, reg,
      el("div", { class: "acoes" }, el("button", { class: "bt leve", onclick: () => { S.passo--; render(); } }, "Voltar"),
        el("button", { class: "bt ipe", onclick: async () => { const t = ta.value.trim(); if (t.length > 2) await registrar("q4", { mv, tx: t.slice(0, 280) }); S.passo = 5; render(); } }, "Enviar")));
  } else {
    put(p, el("div", { class: "progresso" }, Array.from({ length: TOTAL }, () => el("i", { class: "on" }))),
      el("div", { class: "fim" }, el("div", { class: "eu-id" }, window.PixelAvatar ? el("img", { class: "eu-av", src: PixelAvatar.url(S.pid, 4, "#E9EFF7"), alt: "" }) : null, el("span", {}, "Você é ", el("b", {}, apelido(S.pid, S.setor)))),
        el("h1", { class: "pergunta" }, "Sua luz entrou na câmara."),
        el("p", { class: "apoio" }, "Olhe o telão: você está no anel externo, no arco de " + ((C.setores.find(s => s[0] === S.setor) || ["", "outros"])[1]) + ". Cada escolha sua viajou até a tensão e a lacuna que você marcou."),
        el("p", { class: "apoio" }, "Você pode mudar suas respostas até o fim da sessão; vale a última. Enquanto isso, explore a base de conhecimento e o monitoramento."),
        identificacao()),
      el("a", { class: "bt ipe", href: "ao-vivo/?sala=" + encodeURIComponent(SALA) + "&modo=participante", style: "margin-top:8px;justify-content:center" }, "Entrar na câmara →"),
      el("p", { class: "apoio", style: "font-size:14px" }, "Na câmara você vê as contribuições da sala, reage a elas e muda suas escolhas. Tudo aparece para todos e no telão, com o seu avatar."),
      el("div", { class: "acoes" }, el("a", { class: "bt", href: "#conhecimento" }, "Conhecimento"), el("a", { class: "bt", href: "#monitoramento" }, "Monitoramento")),
      el("button", { class: "bt leve", style: "margin-top:16px", onclick: () => { S.passo = 0; render(); } }, "Revisar respostas"));
  }
}

/* Identificação opcional: o nome aparece ao lado do apelido; apelido e avatar continuam os mesmos. */
function identificacao() {
  const atual = S.resp.nome || "";
  const inp = el("input", { class: "ident-in", maxlength: "60", autocomplete: "name", placeholder: "Seu nome", "aria-label": "Seu nome (opcional)" }); inp.value = atual;
  const salvar = async v => { await registrar("nome", v); render(); };
  return el("form", { class: "ident", onsubmit: e => { e.preventDefault(); salvar(inp.value.trim().slice(0, 60) || null); } },
    el("p", { class: "apoio", style: "font-size:14px;margin:0" }, atual ? "Você se identificou como " + atual + ". O apelido e o avatar continuam os mesmos." : "Quer se identificar? É opcional e pode ser feito a qualquer momento. Seu nome aparece ao lado do apelido, que continua o mesmo, assim como o avatar."),
    inp,
    el("div", { class: "acoes" }, el("button", { class: "bt", type: "submit" }, atual ? "Atualizar nome" : "Mostrar meu nome"),
      atual ? el("button", { class: "bt leve", type: "button", onclick: () => salvar(null) }, "Voltar a ficar anônimo") : el("span")));
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
const barras = (linhas, max) => el("div", { class: "barras" }, linhas.map(([rot, n, extra]) => el("div", { class: "barra" },
  el("div", { class: "r" }, el("span", { class: "rot" }, rot, extra || null), el("span", { class: "dado" }, String(n))), el("div", { class: "t" }, el("i", { style: `width:${n / Math.max(1, max) * 100}%` })))));
function renderBlocos() {
  const ps = participantes();
  const setores = C.setores.map(([k, l]) => [l, ps.filter(p => p.setor === k).length]).filter(x => x[1]).sort((a, b) => b[1] - a[1]);
  const q1 = SEMENTES.map(([k, l]) => [l, ps.filter(p => p.q1 && p.q1.v === k).length, el("span", { class: "selo" }, k)]).sort((a, b) => b[1] - a[1]);
  const n1 = q1.reduce((a, x) => a + x[1], 0);
  const pos = ps.filter(p => p.q2 && typeof p.q2.v === "number").map(p => p.q2.v);
  const med = pos.length ? [...pos].sort((a, b) => a - b)[Math.floor(pos.length / 2)] : null;
  const X = v => (v + 1) / 2 * 100;
  const campo = el("div", { class: "campo", role: "img", "aria-label": "Assentos sintéticos acima do eixo, pessoas abaixo" }, el("div", { class: "eixo" }));
  Object.entries(C.posicoesEstratos).forEach(([id, v], i) => campo.append(el("div", { class: "mk s", style: `left:${X(v)}%;top:${16 + (i % 3) * 13}%;color:var(--color-stratum-${id})`, title: ESTRATO[id] + " (perspectiva sintética, posição ilustrativa)" }, el("span", {}, COD[id]))));
  pos.forEach((v, i) => campo.append(el("div", { class: "mk h", style: `left:${X(v)}%;top:${63 + (i * 37) % 30}%` })));
  if (med != null) campo.append(el("div", { class: "mk med", style: `left:${X(med)}%` }, el("b", {}, "mediana da sala")));
  const vs = Object.values(C.posicoesEstratos), mediaS = vs.reduce((a, v) => a + v, 0) / vs.length;
  const q3 = LACUNAS.map(([k, l]) => { const e = C.esperadoPor[k] || []; return [l, ps.filter(p => p.q3 && p.q3.v === k).length, el("span", { class: "selo sint" }, e.length ? `esperada por ${e.length} estrato${e.length > 1 ? "s" : ""} na R1` : "nenhum estrato esperava")]; }).sort((a, b) => b[1] - a[1]);
  const n3 = q3.reduce((a, x) => a + x[1], 0);
  const falas = ps.filter(p => p.q4 && p.q4.v && p.q4.v.tx && !S.ocultar.has(p.pid)).map(p => ({ pid: p.pid, sim: p.sim, mv: p.q4.v.mv, tx: p.q4.v.tx, ts: p.q4.ts || 0, setor: p.setor })).sort((a, b) => b.ts - a.ts);
  const cab = (p, t, n) => el("div", { class: "bloco-cab" }, el("span", { class: "p" }, p), el("h2", {}, t), el("span", { class: "n" }, n));
  put($("#blocos"),
    el("section", { class: "bloco" }, cab("P1", "Quem está na sala", ps.length + " pessoas"),
      setores.length ? barras(setores, setores[0][1]) : el("p", { class: "apoio" }, "Aguardando os primeiros participantes."),
      setores.length && setores.length < 4 ? el("div", { class: "aviso" }, "Poucos setores representados. Leia os resultados com cautela.") : null),
    el("section", { class: "bloco" }, cab("P2", "O que resolver primeiro", n1 + " respostas"), barras(q1, Math.max(...q1.map(x => x[1]), 1))),
    el("section", { class: "bloco largo" }, cab("P3", "Sala e Shadow Council no mesmo eixo", "T5 · " + pos.length + " pessoas · 8 estratos"),
      el("div", { class: "legenda" }, el("span", {}, el("span", { class: "losango" }), "estratos sintéticos (acima)"), el("span", {}, el("span", { class: "ponto" }), "pessoas na sala (abaixo)"), el("span", { class: "selo exemplo" }, "posições sintéticas ilustrativas")),
      campo, el("div", { class: "polos-t" }, el("span", {}, "← " + C.polos[0]), el("span", {}, C.polos[1] + " →")),
      med != null ? el("p", { class: "apoio", style: "margin:0" }, `Mediana da sala: ${sgn(med)}. Média dos estratos sintéticos: ${sgn(mediaS)}. Nem a sala nem o conselho representam a população.`) : null),
    el("section", { class: "bloco largo" }, cab("P4", "Lente Q1 · o que falta no modelo", n3 + " respostas"),
      el("p", { class: "apoio", style: "margin:0" }, "Áreas sem nenhum componente no modelo brasileiro. A barra é a prioridade da sala; o selo mostra quantos estratos do conselho esperavam a área antes de ver o modelo."),
      barras(q3, Math.max(...q3.map(x => x[1]), 1))),
    el("section", { class: "bloco largo" }, cab("P5", "O que a sala trouxe para a mesa", falas.length + " contribuições"),
      !S.textos ? el("p", { class: "apoio" }, "Textos ocultos pelo apresentador.") :
      falas.length ? el("div", { class: "mural" }, falas.slice(0, 12).map(f => el("div", { class: "fala " + f.mv },
        el("span", { class: "m" }, (C.movimentos.find(m => m[0] === f.mv) || ["", ""])[1]), el("p", {}, f.tx),
        el("small", {}, (C.setores.find(s => s[0] === f.setor) || ["", "sem setor"])[1] + (f.sim ? " · simulado" : "")),
        el("button", { onclick: () => { S.ocultar.add(f.pid); agendar(); } }, "ocultar")))) : el("p", { class: "apoio" }, "As contribuições aparecem aqui assim que chegam.")));
}

/* ---------- conhecimento ---------- */
function itemComponente(c) {
  const st = STATUS[c.status] || ["", ""];
  return el("div", { class: "item" }, el("div", {}, el("div", { class: "id" }, c.id + " · " + (TIPO[c.kind] || c.kind)), el("h3", {}, c.title)),
    el("div", { class: "selos" }, el("span", { class: "selo " + st[1] }, st[0]), c.basis === "inferred" ? el("span", { class: "selo inferido" }, "a confirmar") : el("span", { class: "selo" }, "documentado")),
    el("p", {}, c.desc),
    el("div", { class: "nota-i" }, "Áreas: " + c.topics.map(t => (M.topics.find(x => x.id === t) || { label: t }).label).join(" · ")),
    c.note ? el("div", { class: "rel" }, el("b", {}, "Ressalva: "), c.note) : null);
}
function vistaModelo(q) {
  const comps = M.components.filter(c => !q || (c.title + c.desc + c.id).toLowerCase().includes(q));
  const grupos = ["inForce", "proposedOnly", "inferredOnly", "none"].map(f => [f, M.topics.filter(t => t.strength === f)]);
  return el("article", { class: "jur vidro" }, el("div", { class: "eyebrow" }, "Objeto em exame · Shadow Council"), el("h2", { style: "margin-top:8px" }, "Modelo brasileiro de governança de IA"),
    el("p", { class: "modelo" }, M.components.length + " componentes: instrumentos, instituições, mecanismos, recursos e métricas. A proposta (PL 2338) aparece tracejada em violeta porque não vincula."),
    !q ? el("div", { style: "margin-bottom:18px" }, el("h3", { style: "font-size:20px" }, "Cobertura das " + M.topics.length + " áreas"),
      grupos.map(([f, ts]) => el("div", { style: "margin-top:10px" }, el("div", { class: "nota-i", style: "margin-bottom:4px" }, ts.length + " áreas " + FORCA[f][0]),
        el("div", { class: "cobertura" }, ts.map(t => el("span", { class: "selo " + FORCA[f][1] }, t.label)))))) : null,
    comps.map(itemComponente));
}
function renderKB() {
  const q = S.kbQ.toLowerCase();
  const indice = [{ id: "modelo", n: "Modelo brasileiro" }, ...C.jurisdicoes];
  const busca = el("input", { type: "search", id: "kbq", placeholder: "Buscar: risco, sandbox, ANPD…", "aria-label": "Buscar na base de conhecimento" }); busca.value = S.kbQ;
  busca.addEventListener("input", () => { S.kbQ = busca.value; renderKB(); const n = $("#kbq"); n.focus(); n.setSelectionRange(n.value.length, n.value.length); });
  const jurs = q ? C.jurisdicoes.map(j => ({ ...j, itens: j.itens.filter(i => (i.t + i.d + i.rel + j.n).toLowerCase().includes(q)) })).filter(j => j.itens.length) : C.jurisdicoes.filter(j => j.id === S.kbSel);
  const mostraModelo = q ? M.components.some(c => (c.title + c.desc + c.id).toLowerCase().includes(q)) : S.kbSel === "modelo";
  const vistaJur = j => el("article", { class: "jur vidro" }, el("div", { class: "eyebrow" }, "Modelo de referência"), el("h2", { style: "margin-top:8px" }, j.n), el("p", { class: "modelo" }, j.modelo),
    j.itens.map(i => el("div", { class: "item" }, el("h3", {}, i.t), el("div", { class: "selos" }, el("span", { class: "selo " + i.st[1] }, i.st[0])), el("p", {}, i.d),
      el("div", { class: "rel" }, el("b", {}, "Por que importa para o Brasil: "), i.rel),
      el("div", { class: "fonte" }, i.f.length ? ["Fonte: ", ...i.f.flatMap(([l, u], x) => [x ? ", " : "", el("a", { href: u, target: "_blank", rel: "noopener" }, l)])] : "Fonte primária a confirmar."))));
  put($("#kb"), el("nav", { class: "indice vidro", "aria-label": "Índice" }, busca, indice.map(j => el("button", { "aria-pressed": String(!q && S.kbSel === j.id), onclick: () => { S.kbSel = j.id; S.kbQ = ""; renderKB(); } }, j.n))),
    el("div", { style: "display:flex;flex-direction:column;gap:20px;min-width:0" }, mostraModelo ? vistaModelo(q) : null, jurs.map(vistaJur),
      !mostraModelo && !jurs.length ? el("p", { class: "apoio" }, "Nada encontrado.") : null,
      el("p", { class: "nota" }, "Estado em nov/2026. Itens \u201cVerificar\u201d e componentes \u201ca confirmar\u201d precisam de checagem em fonte primária antes de uso formal.")));
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
  /* Fila de reabertura gerada do grafo (PC7, scripts/ontologia/monitorar.py): o que cada mudança de texto reabre. */
  const MON = window.HRAIGO_MONITOR || { eventos: [] };
  const NOMES = { "dispositivo": "dispositivos", "requisito": "requisitos", "avaliação": "avaliações", "aplicação": "aplicações", "codificação": "codificações", "especificidade": "especificidades", "afirmação": "afirmações" };
  const reaberto = MON.eventos.length ? el("section", { class: "reaberto" },
    el("h2", {}, "Reaberto no grafo"),
    el("p", { class: "apoio" }, "O que cada mudança de texto reabre, pelas regras R10 a R13 e pela versão anterior do instrumento. Nada vira fato: tudo vai para revisão humana."),
    MON.eventos.map(e => el("div", { class: "ev-reab" }, el("b", {}, e.rotulo),
      el("p", {}, Object.entries(e.reaberto).map(([k, n]) => n + " " + (n === 1 ? k : (NOMES[k] || k))).join(" · ")),
      e.itens["afirmação"] ? el("p", { class: "nota" }, "Afirmações: " + e.itens["afirmação"].join("; ")) : null))) : null;
  put($("#mon"), reaberto, el("h1", {}, "Pulso normativo"),
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
function render(participacao = true) {
  if (S.vista === "participar" && participacao) { const a = document.activeElement; if (!(a && a.id === "q4t")) renderParticipar(); }
  if (S.vista === "ao-vivo") { renderLateral(); renderBlocos(); }
  if (S.vista === "conhecimento" && !$("#kb").childElementCount) renderKB();
  if (S.vista === "monitoramento" && !$("#mon").childElementCount) renderMon();
}
addEventListener("hashchange", rota);
$("#sala-rotulo").textContent = "observatório · " + SALA;
$("#lnkVivo").href = "ao-vivo/?sala=" + encodeURIComponent(SALA);
rota();
if (CFG.supabaseUrl && CFG.supabaseAnonKey && window.supabase) {
  iniciarSupabase().catch(e => { console.warn(e); S.modo = "local"; status("erro", "sem conexão: " + (e.message || "erro").slice(0, 40)); agendar(); });
} else status("", "modo local · ensaio");
})();
