"""OpenRouter HTTP audit tests; all requests use an in-process transport."""
import base64
import json
import os
import stat

import pytest

httpx = pytest.importorskip("httpx")

from scse.config import ModelConfig
from scse.providers import ProviderError, build_provider
from scse.providers.http_trace import OpenRouterHttpTrace


def test_http_trace_keeps_complete_bodies_and_redacts_credentials(tmp_path):
    path = tmp_path / "private" / "openrouter-http.jsonl"
    trace = OpenRouterHttpTrace(path)
    request_body = b'{"model":"vendor/test","messages":[{"role":"user","content":"Revisao completa"}]}'
    response_body = b'{"id":"resp-1","choices":[{"message":{"content":"resposta integral"}}]}'

    def respond(request):
        return httpx.Response(200, headers={"x-request-id": "req-1"}, content=response_body)

    with httpx.Client(transport=httpx.MockTransport(respond), event_hooks=trace.event_hooks) as client:
        response = client.post(
            "https://openrouter.ai/api/v1/chat/completions?api_key=query-secret&trace=on",
            headers={"Authorization": "Bearer header-secret", "X-Api-Key": "key-secret", "X-Trace": "keep"},
            content=request_body,
        )
        assert response.content == response_body

    summary = trace.summary()
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    request, result = records
    assert request["event"] == "request"
    assert request["bodyBase64"] == base64.b64encode(request_body).decode("ascii")
    assert request["bodyText"] == request_body.decode("utf-8")
    assert request["bodySha256"]
    assert "query-secret" not in request["url"] and "%5BREDACTED%5D" in request["url"]
    assert [value for name, value in request["headers"] if name.lower() == "authorization"] == ["[REDACTED]"]
    assert [value for name, value in request["headers"] if name.lower() == "x-api-key"] == ["[REDACTED]"]
    assert [value for name, value in request["headers"] if name.lower() == "x-trace"] == ["keep"]
    assert result["event"] == "response" and result["statusCode"] == 200
    assert result["bodyBase64"] == base64.b64encode(response_body).decode("ascii")
    assert result["bodyText"] == response_body.decode("utf-8")
    assert request["exchangeId"] == result["exchangeId"]
    assert summary["requestRecords"] == summary["responseRecords"] == 1
    assert summary["allRequestsAccountedFor"] is True
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_trace_write_failure_blocks_request_before_transport(tmp_path, monkeypatch):
    trace = OpenRouterHttpTrace(tmp_path / "blocked" / "trace.jsonl")
    sent = False

    def transport(request):
        nonlocal sent
        sent = True
        return httpx.Response(200, content=b"{}")

    def fail_write(_record):
        raise OSError("disk unavailable")

    monkeypatch.setattr(trace, "_append", fail_write)
    with httpx.Client(transport=httpx.MockTransport(transport), event_hooks=trace.event_hooks) as client:
        with pytest.raises(OSError, match="disk unavailable"):
            client.post("https://openrouter.ai/api/v1/chat/completions", content=b"{}")
    assert sent is False
    trace.close()


def test_openrouter_provider_refuses_network_without_trace():
    config = ModelConfig.load()
    provider = build_provider(config.model("anthropic", "smoke"))
    with pytest.raises(ProviderError, match="full HTTP trace is not configured"):
        provider._client()
