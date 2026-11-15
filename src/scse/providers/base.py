"""Provider-neutral completion contract used by the deliberation engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..config import ModelSpec


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False, status: int | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.status = status


@dataclass
class CompletionRequest:
    system: str
    user: str
    schema: dict
    schema_name: str = "council_turn"
    max_output_tokens: int = 8000
    timeout_seconds: float = 300.0
    seed: int | None = None


@dataclass
class CompletionResult:
    text: str
    model_requested: str
    model_served: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    refusal: bool = False
    refusal_detail: str | None = None
    stop_reason: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class Provider:
    """One configured model of one provider."""

    def __init__(self, spec: ModelSpec):
        self.spec = spec

    @property
    def name(self) -> str:
        return self.spec.provider

    def complete(self, req: CompletionRequest) -> CompletionResult:  # pragma: no cover - interface
        raise NotImplementedError

    def list_models(self) -> list[str]:  # pragma: no cover - interface
        raise NotImplementedError

    # helpers -------------------------------------------------------------
    def opt(self, key: str, default: Any = None) -> Any:
        return self.spec.options.get(key, default)

    def api_key(self, *fallback_envs: str) -> str:
        import os

        for env in (self.opt("api_key_env"), *fallback_envs):
            if env and os.environ.get(env):
                return os.environ[env]
        raise ProviderError(
            f"{self.name}: no API key in ${self.opt('api_key_env')}"
            + (f" or ${', $'.join(fallback_envs)}" if fallback_envs else ""),
            retryable=False,
        )
