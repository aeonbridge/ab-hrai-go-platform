"""Model routing configuration (config/scse/models.toml) with overrides."""
from __future__ import annotations

import copy
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "scse" / "models.toml"
ENV_PREFIX = "SCSE_MODEL__"


class ConfigError(ValueError):
    pass


TRANSPORTS = ("openrouter", "direct")


@dataclass(frozen=True)
class ModelSpec:
    provider: str          # logical provider (family): anthropic, openai, xai, gemini, mock
    tier: str
    id: str                # id sent on the wire for the chosen transport
    sdk: str               # adapter: anthropic | openai | xai | gemini | openrouter | mock
    options: dict[str, Any] = field(default_factory=dict)
    transport: str = "direct"
    direct_id: str = ""

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.id}"


@dataclass(frozen=True)
class MixEntry:
    provider: str
    weight: float
    tier: str | None = None
    model: str | None = None

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.model or self.tier or '<profile>'}"


def _deep_merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def parse_set_option(expr: str) -> dict:
    """Turn ``provider.tier=model`` or ``provider.tier.key=value`` into a patch."""
    if "=" not in expr:
        raise ConfigError(f"--set expects provider.tier[.key]=value, got {expr!r}")
    path, value = expr.split("=", 1)
    parts = path.strip().split(".")
    if len(parts) == 2:
        parts.append("id")
    if len(parts) != 3:
        raise ConfigError(f"--set path must be provider.tier[.key], got {path!r}")
    provider, tier, key = parts
    value = value.strip()
    if key == "id" and "/" in value:
        key = "openrouter_id"  # "vendor/model" is an OpenRouter slug
    return {"providers": {provider: {"models": {tier: {key: value}}}}}


class ModelConfig:
    def __init__(self, data: dict, source: str = "<memory>"):
        self.data = data
        self.source = source
        self._validate()

    @classmethod
    def load(cls, path: str | Path | None = None, overrides: list[dict] | None = None,
             env: dict[str, str] | None = None) -> "ModelConfig":
        p = Path(path) if path else DEFAULT_CONFIG
        with p.open("rb") as fh:
            data = tomllib.load(fh)
        env = os.environ if env is None else env
        for name, value in env.items():
            if not name.startswith(ENV_PREFIX):
                continue
            bits = name[len(ENV_PREFIX):].lower().split("__")
            if len(bits) == 2:
                data = _deep_merge(data, parse_set_option(f"{bits[0]}.{bits[1]}={value}"))
        for patch in overrides or []:
            data = _deep_merge(data, patch)
        return cls(data, str(p))

    def _validate(self) -> None:
        providers = self.data.get("providers", {})
        for name in self.required_providers:
            if name not in providers:
                raise ConfigError(f"required provider {name!r} missing from config")
        for name, prov in providers.items():
            if "sdk" not in prov:
                raise ConfigError(f"provider {name!r} has no sdk")
            for tier, spec in prov.get("models", {}).items():
                if not spec.get("id"):
                    raise ConfigError(f"{name}.{tier} has no model id")
        for stratum in self.data.get("strata", {}):
            self.stratum_mix(stratum)
        tiers = set(self.data.get("profiles", {}).values())
        for name in self.required_providers:
            missing = tiers - set(providers[name].get("models", {}))
            if missing:
                raise ConfigError(f"provider {name!r} lacks tiers {sorted(missing)}")

    @property
    def defaults(self) -> dict:
        return self.data.get("defaults", {})

    @property
    def required_providers(self) -> list[str]:
        return list(self.data.get("defaults", {}).get("required_providers", []))

    @property
    def assignment(self) -> str:
        return self.defaults.get("assignment", "weighted")

    def transport_for(self, provider: str, override: str | None = None) -> str:
        prov = self.provider(provider)
        if prov["sdk"] == "mock":
            return "direct"
        t = override or prov.get("transport") or self.defaults.get("transport", "direct")
        if t not in TRANSPORTS:
            raise ConfigError(f"transport must be one of {TRANSPORTS}, got {t!r}")
        return t

    def provider_names(self) -> list[str]:
        return list(self.data["providers"])

    def provider(self, name: str) -> dict:
        try:
            return self.data["providers"][name]
        except KeyError as exc:
            raise ConfigError(f"unknown provider {name!r}") from exc

    def tier_for_profile(self, profile: str) -> str:
        profiles = self.data.get("profiles", {})
        if profile not in profiles:
            raise ConfigError(f"unknown profile {profile!r}; known: {sorted(profiles)}")
        return profiles[profile]

    def model(self, provider: str, profile: str, *, tier: str | None = None, model: str | None = None,
              transport: str | None = None) -> ModelSpec:
        """Resolve a model for a logical provider.

        Precedence: explicit ``model`` id > explicit ``tier`` > tier of ``profile``.
        An explicit id may be a direct id or an ``openrouter_id``; when it matches a
        configured tier, that tier's options (effort, thinking_level, prices) apply.
        """
        prov = self.provider(provider)
        models = prov.get("models", {})
        spec: dict | None = None
        if model:
            for t, m in models.items():
                if model in (m.get("id"), m.get("openrouter_id")):
                    tier, spec = t, dict(m)
                    break
            if spec is None:
                tier = "custom"
                spec = {"id": model, "openrouter_id": model}
        else:
            tier = tier or self.tier_for_profile(profile)
            spec = dict(models.get(tier) or {})
            if not spec:
                raise ConfigError(f"provider {provider!r} has no tier {tier!r}")
        mode = self.transport_for(provider, transport)
        direct_id = spec.pop("id")
        or_id = spec.pop("openrouter_id", None)
        options = {k: v for k, v in prov.items() if k not in ("models", "sdk")}
        options.update(spec)
        if mode == "openrouter":
            if not or_id:
                raise ConfigError(f"{provider}.{tier} has no openrouter_id")
            options.update(self.data.get("openrouter", {}))
            options["verified"] = bool(spec.get("openrouter_verified", False))
            return ModelSpec(provider=provider, tier=tier, id=or_id, sdk="openrouter", options=options,
                             transport=mode, direct_id=direct_id)
        return ModelSpec(provider=provider, tier=tier, id=direct_id, sdk=prov["sdk"], options=options,
                         transport=mode, direct_id=direct_id)

    def stratum_mix(self, stratum: str, providers: list[str] | None = None) -> list[MixEntry]:
        """Weighted provider/model mix for a stratum, filtered to ``providers``."""
        strata = self.data.get("strata", {})
        raw = (strata.get(stratum) or strata.get("default") or {}).get("mix")
        if not raw:
            raw = [{"provider": p, "weight": 1} for p in (providers or self.required_providers)]
        entries = []
        for item in raw:
            weight = float(item.get("weight", 1))
            if weight < 0:
                raise ConfigError(f"strata.{stratum}: negative weight")
            if item["provider"] not in self.data["providers"]:
                raise ConfigError(f"strata.{stratum}: unknown provider {item['provider']!r}")
            if providers is not None and item["provider"] not in providers:
                continue
            if weight > 0:
                entries.append(MixEntry(provider=item["provider"], weight=weight,
                                        tier=item.get("tier"), model=item.get("model")))
        if not entries:
            raise ConfigError(f"strata.{stratum}: no positive-weight entry for providers {providers}")
        return entries

    def fixed_assignment(self) -> dict[str, str]:
        return dict(self.data.get("assignment", {}).get("fixed", {}))

    def unverified_models(self, providers: list[str] | None = None, transport: str | None = None) -> list[str]:
        out = []
        for name in providers or self.provider_names():
            mode = self.transport_for(name, transport)
            for tier, spec in self.provider(name).get("models", {}).items():
                if mode == "openrouter":
                    if not spec.get("openrouter_verified", False):
                        out.append(f"{name}.{tier}={spec.get('openrouter_id')} (openrouter)")
                elif not spec.get("verified", False):
                    out.append(f"{name}.{tier}={spec['id']}")
        return out
