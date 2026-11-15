"""Google Gemini API via the google-genai SDK."""
from __future__ import annotations

import time

from .base import CompletionRequest, CompletionResult, Provider, ProviderError

BLOCKING_FINISH = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION"}


class GeminiProvider(Provider):
    def _client(self):
        from google import genai

        return genai.Client(api_key=self.api_key("GOOGLE_API_KEY"))

    def complete(self, req: CompletionRequest) -> CompletionResult:
        from google.genai import errors, types

        cfg: dict = dict(system_instruction=req.system, max_output_tokens=req.max_output_tokens)
        mode = self.opt("structured_output", "schema")
        if mode in ("schema", "json_mode"):
            cfg["response_mime_type"] = "application/json"
        if mode == "schema":
            cfg["response_json_schema"] = req.schema
        if self.opt("thinking_level"):
            cfg["thinking_config"] = types.ThinkingConfig(thinking_level=self.opt("thinking_level"))
        if self.opt("temperature") is not None:
            cfg["temperature"] = float(self.opt("temperature"))
        if req.seed is not None:
            cfg["seed"] = req.seed
        started = time.monotonic()
        try:
            resp = self._client().models.generate_content(
                model=self.spec.id, contents=req.user, config=types.GenerateContentConfig(**cfg))
        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            raise ProviderError(f"gemini HTTP {code}: {exc}",
                                retryable=code in (429, 500, 502, 503, 504), status=code) from exc
        latency = time.monotonic() - started
        finish = None
        if resp.candidates:
            finish = str(getattr(resp.candidates[0].finish_reason, "name", resp.candidates[0].finish_reason))
        block = getattr(getattr(resp, "prompt_feedback", None), "block_reason", None)
        refusal = bool(block) or (finish in BLOCKING_FINISH)
        usage = resp.usage_metadata
        try:
            text = resp.text or ""
        except ValueError:
            text = ""
        return CompletionResult(
            text=text,
            model_requested=self.spec.id,
            model_served=getattr(resp, "model_version", None) or self.spec.id,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=(getattr(usage, "candidates_token_count", 0) or 0)
            + (getattr(usage, "thoughts_token_count", 0) or 0),
            latency_s=latency,
            refusal=refusal,
            refusal_detail=str(block or finish) if refusal else None,
            stop_reason=finish,
        )

    def list_models(self) -> list[str]:
        out = []
        for m in self._client().models.list():
            name = m.name or ""
            out.append(name.split("/", 1)[1] if name.startswith("models/") else name)
        return out
