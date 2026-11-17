"""OpenRouter: one key, OpenAI-compatible chat completions, all four providers.

Comparability safeguards (configurable in [openrouter]):
* ``pin_upstream``: route only to the model's original host (``provider.only``),
  so replicates do not silently land on different hosts.
* ``allow_fallbacks = false``: fail instead of switching host.
* ``require_parameters = true``: only hosts that honour response_format/reasoning.
"""
from __future__ import annotations

import time
import threading

from .base import CompletionRequest, CompletionResult, Provider, ProviderError
from .openai_provider import _translate

# Maps per-provider reasoning knobs to OpenRouter's unified ``reasoning.effort``.
_GEMINI_LEVEL = {"minimal": "minimal", "low": "low", "medium": "medium", "high": "high", "xhigh": "high"}


class OpenRouterProvider(Provider):
    def __init__(self, spec):
        super().__init__(spec)
        self._client_lock = threading.Lock()
        self._openai_client = None
        self._http_client = None

    def _client(self):
        if self._openai_client is not None:
            return self._openai_client
        with self._client_lock:
            if self._openai_client is not None:
                return self._openai_client
            if self.trace_recorder is None:
                raise ProviderError("OpenRouter network call blocked: full HTTP trace is not configured")
            import openai
            import httpx

            timeout = float(self.opt("timeout_seconds", 300))
            self._http_client = httpx.Client(
                timeout=timeout,
                follow_redirects=True,
                event_hooks=self.trace_recorder.event_hooks,
            )
            try:
                self._openai_client = openai.OpenAI(
                    api_key=self.api_key(),
                    base_url=self.opt("base_url", "https://openrouter.ai/api/v1"),
                    timeout=timeout,
                    http_client=self._http_client,
                )
            except Exception:
                self._http_client.close()
                self._http_client = None
                raise
            return self._openai_client

    def routing(self) -> dict:
        prefs: dict = {"allow_fallbacks": bool(self.opt("allow_fallbacks", False)),
                       "require_parameters": bool(self.opt("require_parameters", True))}
        upstream = self.opt("openrouter_upstream")
        if self.opt("pin_upstream", True) and upstream:
            prefs["only"] = list(upstream)
            prefs["order"] = list(upstream)
        return prefs

    def reasoning(self) -> dict | None:
        effort = self.opt("effort")
        if effort is None and self.opt("thinking_level"):
            effort = _GEMINI_LEVEL.get(str(self.opt("thinking_level")).lower())
        return {"effort": effort} if effort else None

    def request_kwargs(self, req: CompletionRequest) -> dict:
        kwargs: dict = dict(
            model=self.spec.id,
            messages=[{"role": "system", "content": req.system}, {"role": "user", "content": req.user}],
            max_tokens=req.max_output_tokens,
        )
        if self.opt("temperature") is not None:
            kwargs["temperature"] = float(self.opt("temperature"))
        mode = self.opt("structured_output", "schema")
        if mode == "schema":
            kwargs["response_format"] = {"type": "json_schema", "json_schema": {
                "name": req.schema_name, "schema": req.schema, "strict": True}}
        elif mode == "json_mode":
            kwargs["response_format"] = {"type": "json_object"}
        extra: dict = {"provider": self.routing()}
        if self.reasoning():
            extra["reasoning"] = self.reasoning()
        kwargs["extra_body"] = extra
        return kwargs

    def complete(self, req: CompletionRequest) -> CompletionResult:
        import openai

        started = time.monotonic()
        try:
            resp = self._client().chat.completions.create(**self.request_kwargs(req))
        except openai.OpenAIError as exc:
            if self.trace_recorder is not None:
                self.trace_recorder.record_sdk_error(exc)
            raise _translate(exc, f"openrouter[{self.name}]") from exc
        latency = time.monotonic() - started
        choice = resp.choices[0]
        refusal_text = getattr(choice.message, "refusal", None)
        usage = resp.usage
        cost = getattr(usage, "cost", None) if usage is not None else None
        host = getattr(resp, "provider", None)
        return CompletionResult(
            text=choice.message.content or "",
            model_requested=self.spec.id,
            model_served=f"{resp.model}@{host}" if host else resp.model,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency_s=latency,
            refusal=bool(refusal_text) or choice.finish_reason == "content_filter",
            refusal_detail=refusal_text,
            stop_reason=choice.finish_reason,
            extra={"cost_usd": float(cost) if cost is not None else None, "host": host},
        )

    def list_models(self) -> list[str]:
        import openai

        try:
            return [m.id for m in self._client().models.list()]
        except openai.OpenAIError as exc:
            if self.trace_recorder is not None:
                self.trace_recorder.record_sdk_error(exc)
            raise _translate(exc, f"openrouter[{self.name}]") from exc

    def close(self) -> None:
        if self._openai_client is not None:
            self._openai_client.close()
            self._openai_client = None
            self._http_client = None
