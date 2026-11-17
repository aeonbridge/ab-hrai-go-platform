"""Lossless, local HTTP exchange recording for OpenRouter calls.

Each request and response body is stored byte-for-byte as base64, with a UTF-8
copy for convenient review. Credential-bearing headers and URL parameters are
redacted. The trace is private to the current user (directory mode 0700, file
mode 0600) and writes are fsynced before an exchange continues.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_SENSITIVE_HEADER_PARTS = ("authorization", "api-key", "apikey", "token", "secret", "cookie")
_SENSITIVE_QUERY_PARTS = ("key", "token", "secret", "auth")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_url(url: str) -> str:
    parts = urlsplit(url)
    query = [
        (key, "[REDACTED]" if any(part in key.lower() for part in _SENSITIVE_QUERY_PARTS) else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    authority = parts.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parts.scheme, authority, parts.path, urlencode(query), parts.fragment))


def _safe_headers(headers) -> list[list[str]]:
    result = []
    for key, value in headers.multi_items():
        lowered = key.lower().replace("_", "-")
        safe_value = "[REDACTED]" if any(part in lowered for part in _SENSITIVE_HEADER_PARTS) else value
        result.append([key, safe_value])
    return result


def _body_fields(body: bytes) -> dict:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    return {
        "bodyBytes": len(body),
        "bodySha256": hashlib.sha256(body).hexdigest(),
        "bodyBase64": base64.b64encode(body).decode("ascii"),
        "bodyText": text,
    }


class OpenRouterHttpTrace:
    """Append-only JSONL trace; failures abort the request before it is sent."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        self._fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_APPEND, 0o600)
        os.fchmod(self._fd, 0o600)
        self._lock = threading.Lock()
        self._counts = {"request": 0, "response": 0, "transport_error": 0, "sdk_error": 0}

    @property
    def event_hooks(self) -> dict[str, list]:
        return {"request": [self.record_request], "response": [self.record_response]}

    def _append(self, record: dict) -> None:
        data = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        with self._lock:
            if self._fd < 0:
                raise RuntimeError("OpenRouter HTTP trace is already closed")
            view = memoryview(data)
            while view:
                written = os.write(self._fd, view)
                view = view[written:]
            os.fsync(self._fd)
            kind = record["event"]
            self._counts[kind] += 1

    def record_request(self, request) -> None:
        exchange_id = uuid.uuid4().hex
        request.extensions["scse_openrouter_exchange_id"] = exchange_id
        body = request.read()
        self._append({
            "event": "request",
            "exchangeId": exchange_id,
            "recordedAt": _now(),
            "method": request.method,
            "url": _safe_url(str(request.url)),
            "headers": _safe_headers(request.headers),
            **_body_fields(body),
        })

    def record_response(self, response) -> None:
        # Read in the response hook so the full entity body is durable before
        # the SDK parses it. httpx keeps the loaded bytes available to callers.
        body = response.read()
        request = response.request
        self._append({
            "event": "response",
            "exchangeId": request.extensions.get("scse_openrouter_exchange_id"),
            "recordedAt": _now(),
            "requestMethod": request.method,
            "requestUrl": _safe_url(str(request.url)),
            "statusCode": response.status_code,
            "headers": _safe_headers(response.headers),
            **_body_fields(body),
        })

    def record_sdk_error(self, error: Exception) -> None:
        request = getattr(error, "request", None)
        response = getattr(error, "response", None)
        event = "sdk_error" if response is not None else "transport_error"
        self._append({
            "event": event,
            "exchangeId": request.extensions.get("scse_openrouter_exchange_id") if request else None,
            "recordedAt": _now(),
            "requestMethod": request.method if request else None,
            "requestUrl": _safe_url(str(request.url)) if request else None,
            "errorType": type(error).__name__,
            "error": str(error),
        })

    def close(self) -> None:
        with self._lock:
            if self._fd >= 0:
                os.fsync(self._fd)
                os.close(self._fd)
                self._fd = -1

    def summary(self, relative_to: str | Path | None = None) -> dict:
        self.close()
        digest = hashlib.sha256()
        with self.path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        requests = self._counts["request"]
        accounted = self._counts["response"] + self._counts["transport_error"]
        display_path = self.path
        if relative_to is not None:
            display_path = self.path.relative_to(Path(relative_to))
        return {
            "path": display_path.as_posix(),
            "format": "JSONL; request and response bodies are preserved byte-for-byte as base64",
            "requestRecords": requests,
            "responseRecords": self._counts["response"],
            "transportErrors": self._counts["transport_error"],
            "sdkErrors": self._counts["sdk_error"],
            "allRequestsAccountedFor": requests == accounted,
            "sha256": digest.hexdigest(),
        }
