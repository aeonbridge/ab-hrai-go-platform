"""End-to-end checks for the live mural server (stdlib HTTP + SQLite + SSE)."""

import json
import re
import sqlite3
import threading
import urllib.error
import urllib.request

import pytest

from scse import mural_server

SESSION = "merge:test-session"


@pytest.fixture()
def server(tmp_path):
    srv = mural_server.make_server("127.0.0.1", 0, tmp_path / "mural.sqlite3", public_url="https://exemplo.test/")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", srv
    srv.shutdown()
    srv.server_close()


def call(base, path, data=None, token=None, method=None):
    req = urllib.request.Request(base + path, method=method or ("POST" if data is not None else "GET"))
    if data is not None:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status, json.loads(res.read() or b"null")
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"null")


def join(base, name=None, stratum="civilSociety", tension="T4"):
    data = {"session": SESSION, "scenarioId": "GOV-BR-001", "runId": "r1", "stratumId": stratum, "tensionId": tension}
    if name is not None:
        data["name"] = name
    status, body = call(base, "/api/join", data)
    assert status == 201, body
    return body


def test_health_reports_public_url(server):
    base, _ = server
    status, body = call(base, "/api/health")
    assert status == 200 and body["live"] and body["publicUrl"] == "https://exemplo.test"


def test_join_presence_vote_comment_roundtrip(server):
    base, _ = server
    ana = join(base, "Ana")
    bia = join(base, "Bia", "regulators")
    assert call(base, "/api/presence", {"tensionId": "T4"}, ana["token"])[0] == 200
    assert call(base, "/api/presence", {"tensionId": "T4"}, bia["token"])[0] == 200
    assert call(base, "/api/vote", {"proposalId": "M017", "tensionId": "T4", "stance": "for"}, ana["token"])[0] == 200
    assert call(base, "/api/vote", {"proposalId": "M017", "tensionId": "T4", "stance": "against"}, bia["token"])[0] == 200
    assert call(base, "/api/vote", {"proposalId": "M017", "tensionId": "T4", "stance": "amend"}, ana["token"])[0] == 200
    status, c = call(base, "/api/comment", {"proposalId": "M017", "tensionId": "T4", "body": "Falta prazo."}, ana["token"])
    assert status == 200

    _, state = call(base, f"/api/state?session={SESSION}")
    assert state["presence"]["T4"] == [ana["participantId"], bia["participantId"]]
    assert state["votes"]["M017"] == {"amend": [ana["participantId"]], "against": [bia["participantId"]]}
    assert state["comments"]["M017"][0]["body"] == "Falta prazo."
    assert state["participants"][bia["participantId"]]["stratumId"] == "regulators"

    # Moving to another tension closes the first presence row.
    call(base, "/api/presence", {"tensionId": "T1"}, ana["token"])
    _, state = call(base, f"/api/state?session={SESSION}")
    assert state["presence"]["T4"] == [bia["participantId"]] and state["presence"]["T1"] == [ana["participantId"]]

    # Only the author deletes a comment.
    assert call(base, "/api/comment/delete", {"commentId": c["commentId"]}, bia["token"])[0] == 403
    assert call(base, "/api/comment/delete", {"commentId": c["commentId"]}, ana["token"])[0] == 200


def test_rejects_bad_input_and_missing_token(server):
    base, _ = server
    assert call(base, "/api/join", {"session": SESSION, "name": "X", "stratumId": "aliens"})[0] == 400
    assert call(base, "/api/join", {"session": SESSION, "name": "x" * 61, "stratumId": "workers"})[0] == 400
    assert call(base, "/api/join", {"session": "bad session!", "name": "X", "stratumId": "workers"})[0] == 400
    assert call(base, "/api/vote", {"proposalId": "M001", "stance": "for"})[0] == 401
    ana = join(base)
    assert call(base, "/api/vote", {"proposalId": "M001", "stance": "maybe"}, ana["token"])[0] == 400
    assert call(base, "/api/comment", {"proposalId": "M001", "body": "x" * 1001}, ana["token"])[0] == 400


def test_event_stream_delivers_joins(server):
    base, _ = server
    join(base, "Caio", "workers")
    with urllib.request.urlopen(f"{base}/api/events?session={SESSION}&after=0", timeout=5) as res:
        assert res.headers["Content-Type"].startswith("text/event-stream")
        lines = []
        while not any(line.startswith("data:") for line in lines):
            lines.append(res.readline().decode())
    event = json.loads(next(line for line in lines if line.startswith("data:"))[5:])
    assert event["type"] == "joined" and event["identifiedAs"] == "Caio" and event["stratumId"] == "workers"
    assert event["name"].startswith("Trabalhadores·")


def test_stale_presence_is_swept(server):
    base, srv = server
    ana = join(base)
    call(base, "/api/presence", {"tensionId": "T4"}, ana["token"])
    srv.store.db.execute("UPDATE presence SET heartbeat_at = '2000-01-01T00:00:00+00:00'")
    assert srv.store.sweep() == 1
    _, state = call(base, f"/api/state?session={SESSION}")
    assert "T4" not in state["presence"]


def test_short_link_and_static_guard(server):
    base, _ = server

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    with pytest.raises(urllib.error.HTTPError) as err:
        opener.open(base + "/m/T4", timeout=5)
    assert err.value.code == 302 and "t=T4&entrar=1" in err.value.headers["Location"]
    # Files outside the prototype folder (runs, sources, .env) are never served.
    for path in ("/runs/GOV-BR-001/latest.json", "/.env", "/src/scse/mural_server.py", "/docs/scse/prototipo/../../../.env"):
        assert call(base, path)[0] == 404


def test_anonymous_join_and_identify_keep_nickname_and_face(server):
    base, _ = server
    anon = join(base, stratum="research")
    assert anon["identifiedAs"] is None and re.fullmatch(r"Pesquisa·[0-9a-f]{3,}", anon["name"])
    # Same id, same nickname and face on every device.
    assert mural_server.identity_of(anon["participantId"], "research") == (anon["name"], anon["avatarSeed"])

    status, body = call(base, "/api/identify", {"name": "  Dra. Lia Prado "}, anon["token"])
    assert status == 200 and body["identifiedAs"] == "Dra. Lia Prado"
    _, state = call(base, f"/api/state?session={SESSION}")
    me = state["participants"][anon["participantId"]]
    assert me == {"name": anon["name"], "identifiedAs": "Dra. Lia Prado", "stratumId": "research", "avatarSeed": anon["avatarSeed"]}

    # Back to anonymous: the real name goes away, nickname and face stay.
    call(base, "/api/identify", {"name": ""}, anon["token"])
    _, state = call(base, f"/api/state?session={SESSION}")
    assert state["participants"][anon["participantId"]]["identifiedAs"] is None
    assert state["participants"][anon["participantId"]]["name"] == anon["name"]
    assert call(base, "/api/identify", {"name": "Lia"})[0] == 401


def test_old_database_is_migrated(tmp_path):
    db = tmp_path / "old.sqlite3"
    old = mural_server.SCHEMA.read_text(encoding="utf-8")
    old = old.replace(",'identified'", "")
    old = "\n".join(line for line in old.splitlines() if not line.lstrip().startswith("identified_"))
    con = sqlite3.connect(db)
    con.executescript(old)
    con.execute("INSERT INTO mural_session VALUES ('s1', 'GOV-BR-001', NULL, '2026-01-01T00:00:00+00:00')")
    con.execute("INSERT INTO mural_event(session_id, type, payload, created_at) VALUES ('s1', 'joined', '{}', '2026-01-01T00:00:00+00:00')")
    con.commit()
    con.close()

    store = mural_server.MuralStore(db)
    cols = {r["name"] for r in store.db.execute("PRAGMA table_info(participant)")}
    assert {"identified_name", "identified_at"} <= cols
    assert [r["event_id"] for r in store.db.execute("SELECT event_id FROM mural_event")] == [1]
    store.db.execute("INSERT INTO mural_event(session_id, type, payload, created_at) VALUES ('s1', 'identified', '{}', 'x')")
