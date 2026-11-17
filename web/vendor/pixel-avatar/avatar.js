/* Avatar em pixel para cada participante.
   Porte para JavaScript puro do componente PixelAvatar de pixel-avatar-lib
   (https://github.com/snjyor/pixel-avatar-lib, commit cb594db, Apache 2.0; ver LICENSE nesta pasta).
   Mudanças em relação ao original: sem React; o "DNA" vem de um hash do identificador da pessoa,
   para que o mesmo avatar apareça em todos os aparelhos sem gravar nada a mais no banco.
   API: PixelAvatar.dna(id) -> "h-f-n-c-m-i"; PixelAvatar.url(id, px) -> data URL PNG (com cache);
        PixelAvatar.canvas(id, px) -> HTMLCanvasElement */
(() => {
"use strict";
const PARTS = window.PIXEL_AVATAR_PARTS;
const ORDEM = ["neck", "clothing", "hands", "hair", "face", "item"];   /* do fundo para a frente, como no original */
const CAMPOS = ["hair", "face", "neck", "clothing", "hands", "item"];
function hash(s) { let h = 2166136261 >>> 0; for (const ch of String(s)) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; } return h; }
function dna(id) { let h = hash(id); return CAMPOS.map(() => { const d = h % 10; h = Math.floor(h / 10) || hash(h + ":" + id); return d; }).join("-"); }
function desenhar(ctx, d, px, fundo) {
  const v = d.split("-").map(Number), sel = Object.fromEntries(CAMPOS.map((k, i) => [k, v[i]]));
  ctx.fillStyle = fundo; ctx.fillRect(0, 0, 24 * px, 24 * px);
  const offX = -3.5, offY = 0;
  for (const k of ORDEM) {
    const variante = (PARTS[k] && PARTS[k].variants[sel[k]]) || [];
    for (const [x, y, cor] of variante) {
      const ax = x + offX, ay = y + offY;
      if (ax >= 0 && ax < 24 && ay >= 0 && ay < 24) { ctx.fillStyle = cor; ctx.fillRect(ax * px, ay * px, px, px); }
    }
  }
}
function canvas(id, px = 4, fundo = "#E9EFF7") {
  const c = document.createElement("canvas"); c.width = c.height = 24 * px;
  desenhar(c.getContext("2d"), dna(id), px, fundo); return c;
}
const cache = new Map();
function url(id, px = 4, fundo = "#E9EFF7") {
  const k = id + "|" + px + "|" + fundo; if (!cache.has(k)) cache.set(k, canvas(id, px, fundo).toDataURL("image/png"));
  return cache.get(k);
}
window.PixelAvatar = { dna, url, canvas };
})();
