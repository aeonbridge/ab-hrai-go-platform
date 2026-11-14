"""Provider registry."""
from __future__ import annotations

from ..config import ModelConfig, ModelSpec
from .base import CompletionRequest, CompletionResult, Provider, ProviderError

__all__ = ["CompletionRequest", "CompletionResult", "Provider", "ProviderError", "build_provider", "resolve"]


def build_provider(spec: ModelSpec, *, dry_run: bool = False) -> Provider:
    from .mock_provider import MockProvider

    if dry_run or spec.sdk == "mock":
        return MockProvider(spec, persona=spec.provider)
    if spec.sdk == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(spec)
    if spec.sdk == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(spec)
    if spec.sdk == "xai":
        from .openai_provider import XAIProvider
        return XAIProvider(spec)
    if spec.sdk == "gemini":
        from .gemini_provider import GeminiProvider
        return GeminiProvider(spec)
    raise ProviderError(f"unknown sdk {spec.sdk!r} for provider {spec.provider!r}")


def resolve(config: ModelConfig, provider: str, profile: str, *, dry_run: bool = False) -> Provider:
    return build_provider(config.model(provider, profile), dry_run=dry_run)
