"""Optional identification in the live chamber (web/ao-vivo).

Participation is anonymous by default: nickname and pixel avatar come from the anonymous id.
A person may show their real name at any time (key "nome") and remove it again; the nickname
and the avatar never change. These tests run the real room client (sala-leitura.js) in Node,
in local mode (no Supabase), and check the database migration and the pages that use it.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
MIGRATION = ROOT / "supabase/migrations/20261117030000_identificacao.sql"

# Minimal browser stand-ins so sala-leitura.js runs unchanged in Node (local mode, no BroadcastChannel).
NODE_HARNESS = r"""
const store = {};
globalThis.window = globalThis;
delete globalThis.BroadcastChannel;  // Node has one; the page would keep the process alive
globalThis.localStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
globalThis.location = { search: "?sala=sala-teste", protocol: "file:", href: "file:///web/ao-vivo/index.html" };
globalThis.history = { replaceState() {} };
localStorage.setItem("hraigo.pid", "local-abc12345");
localStorage.setItem("hraigo.setor", "aca");
require(process.argv[2]);
const L = window.HRAIGO_LEITURA;
(async () => {
  const me = L.eu(), out = {};
  await L.enviar("setor", "aca");
  out.anon = { apelido: L.apelido(me, "aca"), nome: L.nome(me), rotulo: L.rotulo(me, "aca") };
  await L.enviar("nome", "  Ana Souza ");
  out.ident = { apelido: L.apelido(me, "aca"), nome: L.nome(me), rotulo: L.rotulo(me, "aca") };
  await L.enviar("nome", null);
  out.back = { apelido: L.apelido(me, "aca"), nome: L.nome(me), rotulo: L.rotulo(me, "aca") };
  out.other = L.nome("local-outra");
  console.log(JSON.stringify(out));
})();
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_room_client_identifies_without_changing_nickname(tmp_path):
    harness = tmp_path / "harness.js"
    harness.write_text(NODE_HARNESS, encoding="utf-8")
    res = subprocess.run(["node", str(harness), str(WEB / "assets/sala-leitura.js")], capture_output=True, text=True, timeout=20)
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout.strip().splitlines()[-1])
    nick = out["anon"]["apelido"]
    assert nick == "Academia·345"
    assert out["anon"] == {"apelido": nick, "nome": None, "rotulo": nick}
    assert out["ident"] == {"apelido": nick, "nome": "Ana Souza", "rotulo": f"{nick} · Ana Souza"}
    assert out["back"] == {"apelido": nick, "nome": None, "rotulo": nick}
    assert out["other"] is None


def test_migration_allows_optional_name_only():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "'nome'" in sql and "respostas_k_check" in sql
    assert re.search(r"jsonb_typeof\(v\) = 'null'", sql), "null must mean back to anonymous"
    assert "between 1 and 60" in sql
    # Older migrations stay untouched; the new one only widens the key check.
    assert "drop table" not in sql.lower()


def test_pages_show_name_beside_nickname_and_keep_avatar():
    camara = (WEB / "ao-vivo/index.html").read_text(encoding="utf-8")
    app = (WEB / "assets/app.js").read_text(encoding="utf-8")
    assert "nenhum nome é coletado" not in app
    assert 'registrar("nome"' in app and "identificacao()" in app
    assert 'L.enviar("nome"' in camara and "data-ident" in camara
    # Avatars are always drawn from the anonymous id, never from the name.
    assert not re.search(r"PixelAvatar\.url\([^)]*nome", camara + app)
