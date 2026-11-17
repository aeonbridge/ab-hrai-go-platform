"""Live server for the Mural de Tensões: humans join a tension by QR code, vote and comment.

Standard library only (http.server, sqlite3, threading), so it adds no dependency to the
package. The page (``docs/scse/prototipo/mural-de-tensoes-execucao.html``) detects the server
through ``/api/health`` and switches from local-only mode to live mode.

Flow
----
1. The facilitator opens a tension and shows its QR code. The code points to ``/m/<tension>``.
2. ``/m/<tension>`` redirects to the page with ``?t=<tension>&entrar=1``; the page asks for one
   of the eight council roles and calls ``POST /api/join``. The person enters anonymously: the
   server derives a nickname ("Pesquisa·7f3") and a face from the random participant id.
   Adding a real name, at join or later (``POST /api/identify``), never changes either.
3. The browser keeps the returned secret token and sends it as ``Authorization: Bearer``.
   It reports which tension it is looking at (``POST /api/presence``, heartbeat every 20 s),
   votes (``POST /api/vote``) and comments (``POST /api/comment``).
4. Every change is appended to ``mural_event`` and pushed to all open pages through
   Server-Sent Events (``GET /api/events``), which redraw presence avatars, tallies and comments.

Storage schema: ``schemas/mural.sql``. Run with ``scse mural serve``.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import secrets
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schemas/mural.sql"
PAGE_PATH = "/docs/scse/prototipo/mural-de-tensoes-execucao.html"
STRATA = ("regulators", "publicOperators", "business", "research", "civilSociety", "workers", "affectedGroups", "infrastructure")
STANCES = ("for", "amend", "against")
PRESENCE_TIMEOUT_S = 45
SWEEP_EVERY_S = 10
SSE_KEEPALIVE_S = 15
MAX_BODY = 16 * 1024
# Short role names used in anonymous nicknames; same wording as the page (STRATA_SHORT).
STRATUM_NICK = {"regulators": "Reguladores", "publicOperators": "Poder público", "business": "Empresas", "research": "Pesquisa",
                "civilSociety": "Sociedade civil", "workers": "Trabalhadores", "affectedGroups": "Afetados", "infrastructure": "Infraestrutura"}
ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def now() -> str:
    """Current UTC time as an ISO-8601 string (seconds precision)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def token_hash(token: str) -> str:
    """SHA-256 of a participant secret; only the hash is stored."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class BadRequest(Exception):
    """Client error with a message safe to show to the person."""

    def __init__(self, message: str, status: int = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status = status


def clean_text(value, field: str, max_len: int) -> str:
    """Trim, drop control characters and bound the length of user text."""
    if not isinstance(value, str):
        raise BadRequest(f"Campo {field} ausente.")
    text = CONTROL_RE.sub(" ", value).strip()
    if not text:
        raise BadRequest(f"Preencha {field}.")
    if len(text) > max_len:
        raise BadRequest(f"{field} passa de {max_len} caracteres.")
    return text


def clean_id(value, field: str, required: bool = True) -> str | None:
    """Validate identifiers coming from the page (session, tension, proposal)."""
    if value in (None, "") and not required:
        return None
    if not isinstance(value, str) or not ID_RE.match(value):
        raise BadRequest(f"Identificador inválido em {field}.")
    return value


def identity_of(participant_id: str, stratum: str, digits: int = 3) -> tuple[str, int]:
    """Nickname and avatar seed derived from the participant id, so every device draws the same person."""
    digest = hashlib.sha256(participant_id.encode("utf-8")).hexdigest()
    return f"{STRATUM_NICK[stratum]}·{digest[:digits]}", int(digest[-8:], 16) % 10000


def clean_optional_name(value) -> str | None:
    """Real name a person chooses to show; empty or missing means anonymous."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return clean_text(value, "nome", 60)


# ---------------------------------------------------------------- storage
class MuralStore:
    """SQLite-backed store. One connection guarded by a lock; writers notify SSE listeners."""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA.read_text(encoding="utf-8"))
        self._migrate()
        self.lock = threading.RLock()
        self.changed = threading.Condition()

    def _migrate(self) -> None:
        """Bring databases created before anonymous participation up to the current schema."""
        cols = {r["name"] for r in self.db.execute("PRAGMA table_info(participant)")}
        if "identified_name" not in cols:
            self.db.execute("ALTER TABLE participant ADD COLUMN identified_name TEXT CHECK (identified_name IS NULL OR length(identified_name) BETWEEN 1 AND 60)")
            self.db.execute("ALTER TABLE participant ADD COLUMN identified_at TEXT")
        ddl = self.db.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'mural_event'").fetchone()[0]
        if "'identified'" not in ddl:
            # SQLite cannot alter a CHECK constraint: rebuild the event table and keep every row and id.
            self.db.execute("BEGIN")
            self.db.execute("ALTER TABLE mural_event RENAME TO mural_event_v1")
            self.db.execute("DROP INDEX IF EXISTS event_session")
            self.db.execute("COMMIT")
            self.db.executescript(SCHEMA.read_text(encoding="utf-8"))
            self.db.execute("INSERT INTO mural_event SELECT * FROM mural_event_v1")
            self.db.execute("DROP TABLE mural_event_v1")

    # -- helpers
    def _event(self, session_id, type_, participant_id=None, tension_id=None, proposal_id=None, payload=None) -> int:
        cur = self.db.execute(
            "INSERT INTO mural_event(session_id, type, participant_id, tension_id, proposal_id, payload, created_at) VALUES (?,?,?,?,?,?,?)",
            (session_id, type_, participant_id, tension_id, proposal_id, json.dumps(payload or {}, ensure_ascii=False), now()),
        )
        return cur.lastrowid

    def _notify(self) -> None:
        with self.changed:
            self.changed.notify_all()

    def authenticate(self, token: str | None) -> sqlite3.Row:
        """Return the participant owning ``token`` or raise 401."""
        if not token:
            raise BadRequest("Entre na sessão primeiro.", HTTPStatus.UNAUTHORIZED)
        with self.lock:
            row = self.db.execute("SELECT * FROM participant WHERE token_hash = ?", (token_hash(token),)).fetchone()
            if not row:
                raise BadRequest("Sessão não reconhecida. Entre de novo.", HTTPStatus.UNAUTHORIZED)
            self.db.execute("UPDATE participant SET last_seen_at = ? WHERE participant_id = ?", (now(), row["participant_id"]))
        return row

    # -- commands
    def join(self, data: dict) -> dict:
        session_id = clean_id(data.get("session"), "session")
        scenario_id = clean_id(data.get("scenarioId") or "desconhecido", "scenarioId")
        run_id = clean_id(data.get("runId"), "runId", required=False)
        stratum = data.get("stratumId")
        if stratum not in STRATA:
            raise BadRequest("Escolha um dos papéis da lista.")
        real_name = clean_optional_name(data.get("name"))  # optional: people may join anonymously
        tension = clean_id(data.get("tensionId"), "tensionId", required=False)
        token = secrets.token_urlsafe(32)
        ts = now()
        with self.lock:
            self.db.execute("INSERT OR IGNORE INTO mural_session(session_id, scenario_id, run_id, created_at) VALUES (?,?,?,?)",
                            (session_id, scenario_id, run_id, ts))
            taken = {r[0] for r in self.db.execute("SELECT display_name FROM participant WHERE session_id = ?", (session_id,))}
            while True:  # a nickname is unique within the session; retry on the rare clash
                pid = str(uuid.uuid4())
                nick, seed = identity_of(pid, stratum)
                if nick not in taken:
                    break
            self.db.execute(
                "INSERT INTO participant(participant_id, session_id, display_name, stratum_id, avatar_seed, token_hash, identified_name, identified_at, joined_tension, created_at, last_seen_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (pid, session_id, nick, stratum, seed, token_hash(token), real_name, ts if real_name else None, tension, ts, ts),
            )
            self._event(session_id, "joined", pid, tension, payload={"stratumId": stratum, "identified": bool(real_name)})
        self._notify()
        return {"participantId": pid, "token": token, "name": nick, "identifiedAs": real_name, "stratumId": stratum,
                "avatarSeed": seed, "session": session_id}

    def identify(self, who: sqlite3.Row, data: dict) -> dict:
        """Show (or stop showing) the person's real name. Nickname and face stay as they are."""
        real_name = clean_optional_name(data.get("name"))
        with self.lock:
            self.db.execute("UPDATE participant SET identified_name = ?, identified_at = ? WHERE participant_id = ?",
                            (real_name, now() if real_name else None, who["participant_id"]))
            self._event(who["session_id"], "identified", who["participant_id"], payload={"identified": bool(real_name)})
        self._notify()
        return {"ok": True, "name": who["display_name"], "identifiedAs": real_name, "avatarSeed": who["avatar_seed"]}

    def presence(self, who: sqlite3.Row, data: dict) -> dict:
        """Enter a tension (or heartbeat it). ``tensionId`` null means the person left all tensions."""
        tension = clean_id(data.get("tensionId"), "tensionId", required=False)
        pid, sid, ts = who["participant_id"], who["session_id"], now()
        changed = False
        with self.lock:
            open_rows = self.db.execute("SELECT presence_id, tension_id FROM presence WHERE participant_id = ? AND left_at IS NULL", (pid,)).fetchall()
            for row in open_rows:
                if row["tension_id"] != tension:
                    self.db.execute("UPDATE presence SET left_at = ? WHERE presence_id = ?", (ts, row["presence_id"]))
                    self._event(sid, "left", pid, row["tension_id"])
                    changed = True
            if tension:
                if any(r["tension_id"] == tension for r in open_rows):
                    self.db.execute("UPDATE presence SET heartbeat_at = ? WHERE participant_id = ? AND tension_id = ? AND left_at IS NULL", (ts, pid, tension))
                else:
                    self.db.execute("INSERT INTO presence(participant_id, tension_id, entered_at, heartbeat_at) VALUES (?,?,?,?)", (pid, tension, ts, ts))
                    self._event(sid, "entered", pid, tension, payload={"stratumId": who["stratum_id"]})
                    changed = True
        if changed:
            self._notify()
        return {"ok": True}

    def vote(self, who: sqlite3.Row, data: dict) -> dict:
        """Set, change or clear (stance null) the person's position on a proposal."""
        proposal = clean_id(data.get("proposalId"), "proposalId")
        tension = clean_id(data.get("tensionId"), "tensionId", required=False)
        stance = data.get("stance")
        if stance is not None and stance not in STANCES:
            raise BadRequest("Posição inválida.")
        pid, sid, ts = who["participant_id"], who["session_id"], now()
        with self.lock:
            if stance is None:
                self.db.execute("DELETE FROM vote WHERE participant_id = ? AND proposal_id = ?", (pid, proposal))
            else:
                self.db.execute(
                    "INSERT INTO vote(participant_id, proposal_id, tension_id, stance, created_at, updated_at) VALUES (?,?,?,?,?,?) "
                    "ON CONFLICT(participant_id, proposal_id) DO UPDATE SET stance = excluded.stance, tension_id = excluded.tension_id, updated_at = excluded.updated_at",
                    (pid, proposal, tension, stance, ts, ts),
                )
            self._event(sid, "vote", pid, tension, proposal, {"stance": stance})
        self._notify()
        return {"ok": True}

    def comment(self, who: sqlite3.Row, data: dict) -> dict:
        proposal = clean_id(data.get("proposalId"), "proposalId")
        tension = clean_id(data.get("tensionId"), "tensionId", required=False)
        body = clean_text(data.get("body"), "comentário", 1000)
        pid, sid, ts = who["participant_id"], who["session_id"], now()
        with self.lock:
            cur = self.db.execute("INSERT INTO comment(participant_id, proposal_id, tension_id, body, created_at) VALUES (?,?,?,?,?)",
                                  (pid, proposal, tension, body, ts))
            self._event(sid, "comment", pid, tension, proposal, {"commentId": cur.lastrowid})
        self._notify()
        return {"ok": True, "commentId": cur.lastrowid}

    def delete_comment(self, who: sqlite3.Row, data: dict) -> dict:
        cid = data.get("commentId")
        if not isinstance(cid, int):
            raise BadRequest("Comentário inválido.")
        with self.lock:
            row = self.db.execute("SELECT * FROM comment WHERE comment_id = ? AND deleted_at IS NULL", (cid,)).fetchone()
            if not row or row["participant_id"] != who["participant_id"]:
                raise BadRequest("Só quem escreveu pode apagar.", HTTPStatus.FORBIDDEN)
            self.db.execute("UPDATE comment SET deleted_at = ? WHERE comment_id = ?", (now(), cid))
            self._event(who["session_id"], "comment.deleted", who["participant_id"], row["tension_id"], row["proposal_id"], {"commentId": cid})
        self._notify()
        return {"ok": True}

    def sweep(self) -> int:
        """Close presence rows whose page stopped sending heartbeats."""
        limit = (datetime.now(timezone.utc) - timedelta(seconds=PRESENCE_TIMEOUT_S)).isoformat(timespec="seconds")
        with self.lock:
            stale = self.db.execute(
                "SELECT p.presence_id, p.participant_id, p.tension_id, pa.session_id FROM presence p JOIN participant pa USING(participant_id) "
                "WHERE p.left_at IS NULL AND p.heartbeat_at < ?", (limit,)).fetchall()
            for row in stale:
                self.db.execute("UPDATE presence SET left_at = ? WHERE presence_id = ?", (now(), row["presence_id"]))
                self._event(row["session_id"], "left", row["participant_id"], row["tension_id"], payload={"reason": "timeout"})
        if stale:
            self._notify()
        return len(stale)

    # -- queries
    def state(self, session_id: str) -> dict:
        """Everything the page needs to draw people, presence, tallies and comments."""
        session_id = clean_id(session_id, "session")
        with self.lock:
            people = self.db.execute("SELECT participant_id, display_name, identified_name, stratum_id, avatar_seed FROM participant WHERE session_id = ?", (session_id,)).fetchall()
            pres = self.db.execute(
                "SELECT p.tension_id, p.participant_id FROM presence p JOIN participant pa USING(participant_id) "
                "WHERE pa.session_id = ? AND p.left_at IS NULL ORDER BY p.entered_at", (session_id,)).fetchall()
            votes = self.db.execute(
                "SELECT v.proposal_id, v.stance, v.participant_id FROM vote v JOIN participant pa USING(participant_id) WHERE pa.session_id = ?",
                (session_id,)).fetchall()
            comments = self.db.execute(
                "SELECT c.comment_id, c.proposal_id, c.participant_id, c.body, c.created_at FROM comment c JOIN participant pa USING(participant_id) "
                "WHERE pa.session_id = ? AND c.deleted_at IS NULL ORDER BY c.comment_id", (session_id,)).fetchall()
            last = self.db.execute("SELECT COALESCE(MAX(event_id), 0) FROM mural_event WHERE session_id = ?", (session_id,)).fetchone()[0]
        out = {"session": session_id, "lastEventId": last,
               "participants": {r["participant_id"]: {"name": r["display_name"], "identifiedAs": r["identified_name"], "stratumId": r["stratum_id"],
                                                    "avatarSeed": r["avatar_seed"]} for r in people},
               "presence": {}, "votes": {}, "comments": {}}
        for r in pres:
            out["presence"].setdefault(r["tension_id"], []).append(r["participant_id"])
        for r in votes:
            out["votes"].setdefault(r["proposal_id"], {}).setdefault(r["stance"], []).append(r["participant_id"])
        for r in comments:
            out["comments"].setdefault(r["proposal_id"], []).append(
                {"id": r["comment_id"], "participantId": r["participant_id"], "body": r["body"], "createdAt": r["created_at"]})
        return out

    def events_since(self, session_id: str, after: int) -> list[dict]:
        with self.lock:
            rows = self.db.execute(
                "SELECT e.*, pa.display_name, pa.identified_name, pa.stratum_id FROM mural_event e LEFT JOIN participant pa USING(participant_id) "
                "WHERE e.session_id = ? AND e.event_id > ? ORDER BY e.event_id LIMIT 200", (session_id, after)).fetchall()
        return [{"id": r["event_id"], "type": r["type"], "participantId": r["participant_id"], "name": r["display_name"],
                 "identifiedAs": r["identified_name"], "stratumId": r["stratum_id"], "tensionId": r["tension_id"], "proposalId": r["proposal_id"],
                 "payload": json.loads(r["payload"] or "{}"), "at": r["created_at"]} for r in rows]


# ---------------------------------------------------------------- HTTP
class MuralHandler(BaseHTTPRequestHandler):
    """Routes: /api/*, /m/<tension> short links, and static files of the prototype folder."""

    server_version = "scse-mural/1.0"
    store: MuralStore
    public_url: str | None = None
    static_roots: tuple[Path, ...] = ()

    def log_message(self, fmt, *args):  # keep the console quiet; errors still surface
        return

    # -- responses
    def _json(self, payload, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise BadRequest("Pedido grande demais.", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            raise BadRequest("JSON inválido.") from exc
        if not isinstance(data, dict):
            raise BadRequest("JSON inválido.")
        return data

    def _who(self, data: dict | None = None) -> sqlite3.Row:
        """Participant from the Bearer header, or from ``token`` in the body (navigator.sendBeacon cannot set headers)."""
        auth = self.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.startswith("Bearer ") else (data or {}).get("token")
        return self.store.authenticate(token if isinstance(token, str) else None)

    # -- verbs
    def do_GET(self):  # noqa: N802 (http.server naming)
        url = urlparse(self.path)
        qs = parse_qs(url.query)
        try:
            if url.path == "/api/health":
                return self._json({"ok": True, "live": True, "publicUrl": self.public_url, "page": PAGE_PATH})
            if url.path == "/api/state":
                return self._json(self.store.state((qs.get("session") or [""])[0]))
            if url.path == "/api/events":
                return self._sse((qs.get("session") or [""])[0], int((qs.get("after") or [self.headers.get("Last-Event-ID") or "0"])[0] or 0))
            if url.path in ("/", "/mural"):
                return self._redirect(PAGE_PATH + (f"?{url.query}" if url.query else ""))
            m = re.fullmatch(r"/m/([A-Za-z0-9_-]{1,20})", url.path)
            if m:
                return self._redirect(f"{PAGE_PATH}?t={quote(m.group(1))}&entrar=1#tensao-{quote(m.group(1))}")
            return self._static(url.path)
        except BadRequest as exc:
            return self._json({"error": str(exc)}, exc.status)

    def do_POST(self):  # noqa: N802
        url = urlparse(self.path)
        try:
            data = self._body()
            if url.path == "/api/join":
                return self._json(self.store.join(data), HTTPStatus.CREATED)
            routes = {"/api/presence": self.store.presence, "/api/vote": self.store.vote,
                      "/api/comment": self.store.comment, "/api/identify": self.store.identify, "/api/comment/delete": self.store.delete_comment}
            if url.path in routes:
                return self._json(routes[url.path](self._who(data), data))
            return self._json({"error": "Rota desconhecida."}, HTTPStatus.NOT_FOUND)
        except BadRequest as exc:
            return self._json({"error": str(exc)}, exc.status)
        except sqlite3.IntegrityError as exc:
            return self._json({"error": f"Dado rejeitado pelo banco: {exc}"}, HTTPStatus.BAD_REQUEST)

    # -- live stream
    def _sse(self, session_id: str, after: int) -> None:
        session_id = clean_id(session_id, "session")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        last = after
        try:
            self.wfile.write(b"retry: 3000\n\n")
            self.wfile.flush()
            while True:
                events = self.store.events_since(session_id, last)
                for ev in events:
                    self.wfile.write(f"id: {ev['id']}\nevent: mural\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n".encode("utf-8"))
                    last = ev["id"]
                if events:
                    self.wfile.flush()
                    continue
                with self.store.changed:
                    self.store.changed.wait(SSE_KEEPALIVE_S)
                if not self.store.events_since(session_id, last):
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return

    # -- static files (prototype folder only, unless runs were explicitly allowed)
    def _static(self, path: str) -> None:
        rel = path.lstrip("/")
        target = (ROOT / rel).resolve()
        if not any(target == r or r in target.parents for r in self.static_roots) or not target.is_file() or target.name.startswith("._"):
            return self._json({"error": "Não encontrado."}, HTTPStatus.NOT_FOUND)
        data = target.read_bytes()
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/json", "application/javascript"):
            ctype += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def make_server(host: str, port: int, db_path: Path, public_url: str | None = None, serve_runs: bool = False) -> ThreadingHTTPServer:
    """Build the server (not started). ``serve_runs`` also exposes ``runs/`` for the artifact links."""
    store = MuralStore(db_path)
    roots = [(ROOT / "docs/scse/prototipo").resolve()]
    if serve_runs:
        roots.append((ROOT / "runs").resolve())
    handler = type("BoundMuralHandler", (MuralHandler,), {"store": store, "public_url": public_url.rstrip("/") if public_url else None,
                                                           "static_roots": tuple(roots)})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    server.store = store  # type: ignore[attr-defined]

    def sweeper():
        while True:
            time.sleep(SWEEP_EVERY_S)
            try:
                store.sweep()
            except sqlite3.Error:
                pass

    threading.Thread(target=sweeper, daemon=True).start()
    return server


def serve(host: str, port: int, db_path: Path, public_url: str | None, serve_runs: bool) -> None:
    """Run until interrupted, printing the addresses people can use."""
    server = make_server(host, port, db_path, public_url, serve_runs)
    local = f"http://{'127.0.0.1' if host in ('0.0.0.0', '') else host}:{port}"
    print(f"Mural ao vivo em {local}/mural")
    if public_url:
        print(f"QR codes apontam para {public_url.rstrip('/')}/m/<tensão>")
    elif host in ("127.0.0.1", "localhost"):
        print("Só este computador acessa. Para celulares na mesma rede use --host 0.0.0.0, ou --public-url com um túnel.")
    print(f"Banco: {db_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
