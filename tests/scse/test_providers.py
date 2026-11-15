"""Offline checks of request shape and response parsing for each real adapter."""
from types import SimpleNamespace as NS

import pytest

from scse.config import ModelConfig
from scse.prompts import TURN_SCHEMA
from scse.providers import CompletionRequest, build_provider

REQ = CompletionRequest(system="sys", user="usr", schema=TURN_SCHEMA, max_output_tokens=1234)
CFG = ModelConfig.load()


class Recorder:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def __call__(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def _patch(provider, client, monkeypatch):
    monkeypatch.setattr(provider, "_client", lambda: client)


def test_anthropic_request_and_refusal(monkeypatch):
    p = build_provider(CFG.model("anthropic", "perspective.deep", transport="direct"))
    resp = NS(model="claude-opus-5-5", stop_reason="refusal",
              stop_details=NS(category="cyber", explanation="x"),
              content=[NS(type="text", text="{}")], usage=NS(input_tokens=10, output_tokens=2))
    rec = Recorder(resp)
    _patch(p, NS(beta=NS(messages=NS(create=rec)), messages=NS(create=None)), monkeypatch)
    out = p.complete(REQ)
    k = rec.kwargs
    assert k["model"] == "claude-opus-5-5" and k["max_tokens"] == 1234 and k["system"] == "sys"
    assert k["output_config"]["effort"] == "high"
    assert k["output_config"]["format"]["type"] == "json_schema"
    assert k["fallbacks"] == "default" and k["betas"] == ["server-side-fallback-2026-07-01"]
    assert "temperature" not in k and "thinking" not in k
    assert out.refusal and out.refusal_detail.startswith("cyber")


def test_anthropic_without_fallbacks_uses_ga_endpoint(monkeypatch):
    p = build_provider(CFG.model("anthropic", "smoke", transport="direct"))
    resp = NS(model="claude-haiku-5-5", stop_reason="end_turn", content=[NS(type="text", text='{"ok":true}')],
              usage=NS(input_tokens=1, output_tokens=1))
    rec = Recorder(resp)
    _patch(p, NS(messages=NS(create=rec)), monkeypatch)
    assert p.complete(REQ).text == '{"ok":true}'
    assert "fallbacks" not in rec.kwargs


def test_openai_responses_request(monkeypatch):
    p = build_provider(CFG.model("openai", "perspective.deep", transport="direct"))
    resp = NS(output_text='{"a":1}', model="gpt-x", status="completed",
              output=[NS(type="message", content=[NS(type="output_text", text='{"a":1}')])],
              usage=NS(input_tokens=5, output_tokens=3))
    rec = Recorder(resp)
    _patch(p, NS(responses=NS(create=rec)), monkeypatch)
    out = p.complete(REQ)
    k = rec.kwargs
    assert k["instructions"] == "sys" and k["input"] == "usr" and k["max_output_tokens"] == 1234
    assert k["reasoning"] == {"effort": "high"}
    fmt = k["text"]["format"]
    assert fmt["type"] == "json_schema" and fmt["strict"] is True and fmt["name"] == "council_turn"
    assert out.text == '{"a":1}' and not out.refusal


def test_openai_refusal_detected(monkeypatch):
    p = build_provider(CFG.model("openai", "perspective.standard", transport="direct"))
    resp = NS(output_text="", model="gpt-x", status="completed",
              output=[NS(type="message", content=[NS(type="refusal", refusal="no")])],
              usage=NS(input_tokens=1, output_tokens=1))
    _patch(p, NS(responses=NS(create=Recorder(resp))), monkeypatch)
    assert p.complete(REQ).refusal


def test_xai_chat_completions_request(monkeypatch):
    p = build_provider(CFG.model("xai", "perspective.deep", transport="direct"))
    assert p.opt("base_url") == "https://api.x.ai/v1"
    resp = NS(model="grok", choices=[NS(message=NS(content='{"a":1}', refusal=None), finish_reason="stop")],
              usage=NS(prompt_tokens=4, completion_tokens=2))
    rec = Recorder(resp)
    _patch(p, NS(chat=NS(completions=NS(create=rec))), monkeypatch)
    out = p.complete(REQ)
    k = rec.kwargs
    assert k["messages"][0] == {"role": "system", "content": "sys"}
    assert k["response_format"]["type"] == "json_schema"
    assert out.input_tokens == 4 and out.text == '{"a":1}'


def test_gemini_request(monkeypatch):
    pytest.importorskip("google.genai")
    p = build_provider(CFG.model("gemini", "perspective.deep", transport="direct"))
    resp = NS(text='{"a":1}', candidates=[NS(finish_reason=NS(name="STOP"))], prompt_feedback=None,
              usage_metadata=NS(prompt_token_count=7, candidates_token_count=2, thoughts_token_count=5),
              model_version="gemini-x")
    rec = Recorder(resp)
    _patch(p, NS(models=NS(generate_content=rec)), monkeypatch)
    out = p.complete(REQ)
    cfg = rec.kwargs["config"]
    assert rec.kwargs["model"] == "gemini-4-argon"
    assert cfg.response_mime_type == "application/json" and cfg.response_json_schema == TURN_SCHEMA
    assert cfg.thinking_config.thinking_level is not None
    assert out.output_tokens == 7 and not out.refusal


def test_gemini_safety_block(monkeypatch):
    pytest.importorskip("google.genai")
    p = build_provider(CFG.model("gemini", "perspective.standard", transport="direct"))
    resp = NS(text="", candidates=[NS(finish_reason=NS(name="SAFETY"))], prompt_feedback=None,
              usage_metadata=NS(prompt_token_count=1, candidates_token_count=0, thoughts_token_count=0),
              model_version=None)
    _patch(p, NS(models=NS(generate_content=Recorder(resp))), monkeypatch)
    assert p.complete(REQ).refusal


def test_schema_uses_portable_subset():
    def walk(node):
        if isinstance(node, dict):
            assert not isinstance(node.get("type"), list), "use anyOf instead of type arrays"
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
                assert set(node["required"]) == set(node["properties"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(TURN_SCHEMA)


# ------------------------------------------------------------------ OpenRouter
def test_openrouter_is_default_transport():
    for p in ("anthropic", "openai", "xai", "gemini"):
        spec = CFG.model(p, "perspective.deep")
        assert spec.transport == "openrouter" and spec.sdk == "openrouter" and "/" in spec.id
    assert CFG.model("anthropic", "perspective.deep").id == "anthropic/claude-opus-5.5"
    assert CFG.model("mock", "perspective.deep").transport == "direct"


@pytest.mark.parametrize("provider,upstream,effort", [
    ("anthropic", "anthropic", "high"), ("openai", "openai", "high"),
    ("xai", "xai", None), ("gemini", "google-ai-studio", "high")])
def test_openrouter_request_pins_upstream(monkeypatch, provider, upstream, effort):
    p = build_provider(CFG.model(provider, "perspective.deep"))
    usage = NS(prompt_tokens=9, completion_tokens=4, cost=0.0123)
    resp = NS(model="m", provider="HostX", usage=usage,
              choices=[NS(message=NS(content='{"a":1}', refusal=None), finish_reason="stop")])
    rec = Recorder(resp)
    _patch(p, NS(chat=NS(completions=NS(create=rec))), monkeypatch)
    out = p.complete(REQ)
    k = rec.kwargs
    prefs = k["extra_body"]["provider"]
    assert prefs["only"] == [upstream] and prefs["order"] == [upstream]
    assert prefs["allow_fallbacks"] is False and prefs["require_parameters"] is True
    assert k["response_format"]["json_schema"]["strict"] is True
    assert k["extra_body"].get("reasoning") == ({"effort": effort} if effort else None)
    assert out.extra["cost_usd"] == pytest.approx(0.0123) and out.model_served == "m@HostX"


def test_set_with_slash_targets_openrouter_id():
    cfg = ModelConfig.load(overrides=[__import__("scse.config", fromlist=["x"]).parse_set_option(
        "xai.deep=x-ai/grok-test")])
    assert cfg.model("xai", "perspective.deep").id == "x-ai/grok-test"
    assert cfg.model("xai", "perspective.deep", transport="direct").id == "grok-4.7"
