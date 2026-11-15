"""Anthropic Messages API via the official SDK."""
from __future__ import annotations

import time

from .base import CompletionRequest, CompletionResult, Provider, ProviderError

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider(Provider):
    def _client(self):
        import anthropic

        return anthropic.Anthropic(api_key=self.api_key(), timeout=float(self.opt("timeout_seconds", 300)))

    def complete(self, req: CompletionRequest) -> CompletionResult:
        import anthropic

        client = self._client()
        output_config: dict = {}
        if self.opt("effort"):
            output_config["effort"] = self.opt("effort")
        if self.opt("structured_output", "schema") == "schema":
            output_config["format"] = {"type": "json_schema", "schema": req.schema}
        kwargs: dict = dict(
            model=self.spec.id,
            max_tokens=req.max_output_tokens,
            system=req.system,
            messages=[{"role": "user", "content": req.user}],
        )
        if output_config:
            kwargs["output_config"] = output_config
        fallbacks = self.opt("fallbacks")
        started = time.monotonic()
        try:
            if fallbacks:
                resp = client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks=fallbacks, **kwargs)
            else:
                resp = client.messages.create(**kwargs)
        except anthropic.RateLimitError as exc:
            raise ProviderError(f"anthropic rate limited: {exc}", retryable=True, status=429) from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError(f"anthropic HTTP {exc.status_code}: {exc.message}",
                                retryable=exc.status_code >= 500, status=exc.status_code) from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError(f"anthropic connection error: {exc}", retryable=True) from exc
        latency = time.monotonic() - started
        refusal = resp.stop_reason == "refusal"
        detail = None
        if refusal and getattr(resp, "stop_details", None):
            detail = f"{resp.stop_details.category}: {resp.stop_details.explanation}"
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return CompletionResult(
            text=text,
            model_requested=self.spec.id,
            model_served=resp.model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            latency_s=latency,
            refusal=refusal,
            refusal_detail=detail,
            stop_reason=resp.stop_reason,
        )

    def list_models(self) -> list[str]:
        return [m.id for m in self._client().models.list()]
