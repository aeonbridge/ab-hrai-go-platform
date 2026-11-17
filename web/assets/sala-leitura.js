/* HRAI-GO · sala ao vivo, compartilhada pelo telão e pelo celular do participante.
   Fontes: Supabase (leitura pública via RLS; escrita com a sessão anônima criada na participação) ou,
   sem configuração, BroadcastChannel entre abas (ensaio).
   API: HRAIGO_LEITURA.sala, .on(fn(msg, novo)), .estado(fn(cls, txt)), .participantes(), .injetar(msg),
        .eu(), .setor(), .apelido(pid, setor), .enviar(k, v), .podeEnviar(), .iniciar() */
(() => {
"use strict";
const CFG = window.HRAIGO_CONFIG || {};
const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
const params = new URLSearchParams(location.search);
const EV = window.HRAIGO_EVENTO || {};
let sala = (params.get("sala") || EV.sala || ls.get("hraigo.sala") || "").toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 40);
if (sala.length < 4) sala = "sala-" + Math.random().toString(36).slice(2, 8);
ls.set("hraigo.sala", sala);
if (location.protocol.startsWith("http") && params.get("sala") !== sala) { const u = new URL(location.href); u.searchParams.set("sala", sala); history.replaceState(null, "", u); }

/* identidade: a mesma da página de participação (mesmo localStorage e mesma sessão anônima) */
let localPid = ls.get("hraigo.pid"); if (!localPid) { localPid = "local-" + Math.random().toString(36).slice(2, 10); ls.set("hraigo.pid", localPid); }
let sb = null, sessao = null;
const supa = !!(CFG.supabaseUrl && CFG.supabaseAnonKey && window.supabase);
const CURTO = { gov: "Governo", reg: "Regulador", leg: "Legislativo", est: "Estados", aca: "Academia", soc: "Sociedade", pri: "Privado", out: "Outro" };
function apelido(pid, setor) { return (CURTO[setor] || "Pessoa") + "·" + String(pid || "").replace(/[^a-z0-9]/gi, "").slice(-3).toLowerCase(); }
function eu() { return supa ? (sessao ? sessao.user.id : null) : localPid; }

const msgs = new Map(), ouvintes = [], estados = [];
function emitirEstado(cls, txt) { estados.forEach(f => f(cls, txt)); }
function injetar(m) {
  if (!m || !m.pid || !m.k) return;
  const key = m.pid + "|" + m.k, prev = msgs.get(key);
  if (prev && (m.ts || 0) < (prev.ts || 0)) return;
  if (prev && JSON.stringify(prev.v) === JSON.stringify(m.v)) return;
  const novoParticipante = ![...msgs.keys()].some(k => k.startsWith(m.pid + "|"));
  msgs.set(key, m);
  ouvintes.forEach(f => f(m, novoParticipante));
}
function participantes() {
  const by = new Map();
  for (const m of msgs.values()) {
    let p = by.get(m.pid); if (!p) { p = { pid: m.pid, sim: !!m.sim }; by.set(m.pid, p); }
    p[m.k] = m; if (m.setor) p.setor = m.setor; if (m.k === "setor") p.setor = m.v;
  }
  return [...by.values()];
}
const bc = "BroadcastChannel" in window ? new BroadcastChannel("hraigo-" + sala) : null;
if (bc) bc.onmessage = e => injetar(e.data);

async function enviar(k, v) {
  const pid = eu();
  if (!pid) throw new Error("sem sessão: entre pela participação");
  const m = { pid, k, v, setor: ls.get("hraigo.setor"), ts: Date.now() };
  injetar(m); bc && bc.postMessage(m);
  if (!k.startsWith("r:")) { try { const r = JSON.parse(ls.get("hraigo.resp." + sala) || "{}"); r[k] = v; ls.set("hraigo.resp." + sala, JSON.stringify(r)); } catch (e) {} }
  if (supa) {
    const { error } = await sb.from("respostas").upsert({ sala, pid, k, v, setor: m.setor || null, ts: m.ts }, { onConflict: "sala,pid,k" });
    if (error) throw error;
  }
}

async function iniciar() {
  if (!supa) { emitirEstado("", "modo local · ensaio"); return; }
  emitirEstado("", "conectando");
  try {
    sb = supabase.createClient(CFG.supabaseUrl, CFG.supabaseAnonKey, { auth: { persistSession: true, storageKey: "hraigo-auth" } });
    try { const { data } = await sb.auth.getSession(); sessao = data.session; } catch (e) {}
    const { data, error } = await sb.from("respostas").select("pid,k,v,setor,ts").eq("sala", sala).order("ts").limit(5000);
    if (error) throw error;
    data.forEach(r => injetar({ pid: r.pid, k: r.k, v: r.v, setor: r.setor, ts: r.ts }));
    sb.channel("telao:" + sala + ":" + Math.random().toString(36).slice(2, 6))
      .on("postgres_changes", { event: "*", schema: "public", table: "respostas", filter: "sala=eq." + sala },
        p => p.new && injetar({ pid: p.new.pid, k: p.new.k, v: p.new.v, setor: p.new.setor, ts: p.new.ts }))
      .subscribe(st => {
        if (st === "SUBSCRIBED") emitirEstado("vivo", "ao vivo · " + sala);
        else if (st === "CHANNEL_ERROR" || st === "TIMED_OUT") emitirEstado("erro", "tempo real indisponível");
      });
  } catch (e) { console.warn(e); emitirEstado("erro", "sem conexão com o banco"); }
}

window.HRAIGO_LEITURA = {
  sala, injetar, participantes, apelido, enviar, eu,
  setor() { return ls.get("hraigo.setor"); },
  podeEnviar() { return !!eu() && !!ls.get("hraigo.setor"); },
  on(f) { ouvintes.push(f); }, estado(f) { estados.push(f); },
  linkParticipar() { if (EV.linkPublico && EV.sala === sala) return EV.linkPublico; const u = new URL("../", location.href); u.searchParams.set("sala", sala); u.hash = "participar"; return u.toString(); },
  iniciar
};
})();
