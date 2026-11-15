"""OpenAI Responses API and xAI (OpenAI-compatible chat completions)."""
from __future__ import annotations

import time

from .base import CompletionRequest, CompletionResult, Provider, ProviderError


def _translate(exc: Exception, name: str) -> ProviderError:
    import openai

    if isinstance(exc, openai.RateLimitError):
        return ProviderError(f"{name} rate limited: {exc}", retryable=True, status=429)
    if isinstance(exc, openai.APIStatusError):
        return ProviderError(f"{name} HTTP {exc.status_code}: {exc.message}",
                             retryable=exc.status_code >= 500, status=exc.status_code)
    if isinstance(exc, openai.APIConnectionError):
        return ProviderError(f"{name} connection error: {exc}", retryable=True)
    return ProviderError(f"{name} error: {exc}")


class OpenAIProvider(Provider):
    def _client(self):
        import openai

        return openai.OpenAI(api_key=self.api_key(), base_url=self.opt("base_url"),
                             timeout=float(self.opt("timeout_seconds", 300)))

    def complete(self, req: CompletionRequest) -> CompletionResult:
        import openai

        kwargs: dict = dict(model=self.spec.id, instructions=req.system, input=req.user,
                            max_output_tokens=req.max_output_tokens)
        if self.opt("effort"):
            kwargs["reasoning"] = {"effort": self.opt("effort")}
        if self.opt("temperature") is not None:
            kwargs["temperature"] = float(self.opt("temperature"))
        mode = self.opt("structured_output", "schema")
        if mode == "schema":
            kwargs["text"] = {"format": {"type": "json_schema", "name": req.schema_name,
                                         "schema": req.schema, "strict": True}}
        elif mode == "json_mode":
            kwargs["text"] = {"format": {"type": "json_object"}}
        started = time.monotonic()
        try:
            resp = self._client().responses.create(**kwargs)
        except openai.OpenAIError as exc:
            raise _translate(exc, "openai") from exc
        latency = time.monotonic() - started
        refusal_text = None
        for item in resp.output or []:
            for part in getattr(item, "content", None) or []:
                if getattr(part, "type", None) == "refusal":
                    refusal_text = getattr(part, "refusal", "refused")
        usage = resp.usage
        return CompletionResult(
            text=resp.output_text or "",
            model_requested=self.spec.id,
            model_served=resp.model,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            latency_s=latency,
            refusal=refusal_text is not None,
            refusal_detail=refusal_text,
            stop_reason=getattr(resp, "status", None),
        )

    def list_models(self) -> list[str]:
        return [m.id for m in self._client().models.list()]


class XAIProvider(OpenAIProvider):
    """xAI exposes an OpenAI-compatible API; chat completions is the stable surface."""

    def complete(self, req: CompletionRequest) -> CompletionResult:
        import openai

        kwargs: dict = dict(
            model=self.spec.id,
            messages=[{"role": "system", "content": req.system}, {"role": "user", "content": req.user}],
            max_tokens=req.max_output_tokens,
        )
        if self.opt("effort"):
            kwargs["reasoning_effort"] = self.opt("effort")
        if self.opt("temperature") is not None:
            kwargs["temperature"] = float(self.opt("temperature"))
        mode = self.opt("structured_output", "schema")
        if mode == "schema":
            kwargs["response_format"] = {"type": "json_schema", "json_schema": {
                "name": req.schema_name, "schema": req.schema, "strict": True}}
        elif mode == "json_mode":
            kwargs["response_format"] = {"type": "json_object"}
        started = time.monotonic()
        try:
            resp = self._client().chat.completions.create(**kwargs)
        except openai.OpenAIError as exc:
            raise _translate(exc, "xai") from exc
        latency = time.monotonic() - started
        choice = resp.choices[0]
        refusal_text = getattr(choice.message, "refusal", None)
        usage = resp.usage
        return CompletionResult(
            text=choice.message.content or "",
            model_requested=self.spec.id,
            model_served=resp.model,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency_s=latency,
            refusal=bool(refusal_text) or choice.finish_reason == "content_filter",
            refusal_detail=refusal_text,
            stop_reason=choice.finish_reason,
        )
