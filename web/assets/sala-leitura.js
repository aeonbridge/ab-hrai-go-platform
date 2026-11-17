/* HRAI-GO · leitura ao vivo de uma sala (telão). Não grava nada.
   Fontes: Supabase (leitura pública via RLS) ou, sem configuração, BroadcastChannel entre abas (ensaio).
   API: HRAIGO_LEITURA.sala, .on(fn(msg, novo)), .estado(fn(cls, txt)), .participantes(), .injetar(msg) */
(() => {
"use strict";
const CFG = window.HRAIGO_CONFIG || {};
const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
const params = new URLSearchParams(location.search);
let sala = (params.get("sala") || ls.get("hraigo.sala") || "").toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 40);
if (sala.length < 4) sala = "sala-" + Math.random().toString(36).slice(2, 8);
ls.set("hraigo.sala", sala);
if (location.protocol.startsWith("http") && params.get("sala") !== sala) { const u = new URL(location.href); u.searchParams.set("sala", sala); history.replaceState(null, "", u); }

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

async function iniciar() {
  if (!(CFG.supabaseUrl && CFG.supabaseAnonKey && window.supabase)) { emitirEstado("", "modo local · ensaio"); return; }
  emitirEstado("", "conectando");
  try {
    const sb = supabase.createClient(CFG.supabaseUrl, CFG.supabaseAnonKey, { auth: { persistSession: false } });
    const { data, error } = await sb.from("respostas").select("pid,k,v,setor,ts").eq("sala", sala).order("ts").limit(5000);
    if (error) throw error;
    data.forEach(r => injetar({ pid: r.pid, k: r.k, v: r.v, setor: r.setor, ts: r.ts }));
    sb.channel("telao:" + sala)
      .on("postgres_changes", { event: "*", schema: "public", table: "respostas", filter: "sala=eq." + sala },
        p => p.new && injetar({ pid: p.new.pid, k: p.new.k, v: p.new.v, setor: p.new.setor, ts: p.new.ts }))
      .subscribe(st => {
        if (st === "SUBSCRIBED") emitirEstado("vivo", "ao vivo · " + sala);
        else if (st === "CHANNEL_ERROR" || st === "TIMED_OUT") emitirEstado("erro", "tempo real indisponível");
      });
  } catch (e) { console.warn(e); emitirEstado("erro", "sem conexão com o banco"); }
}

window.HRAIGO_LEITURA = {
  sala, injetar, participantes,
  on(f) { ouvintes.push(f); }, estado(f) { estados.push(f); },
  linkParticipar() { const u = new URL("../", location.href); u.searchParams.set("sala", sala); u.hash = "participar"; return u.toString(); },
  iniciar
};
})();
