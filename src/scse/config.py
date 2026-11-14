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


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    tier: str
    id: str
    sdk: str
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.id}"


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
    return {"providers": {provider: {"models": {tier: {key: value.strip()}}}}}


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
                data = _deep_merge(data, {"providers": {bits[0]: {"models": {bits[1]: {"id": value}}}}})
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
        return self.defaults.get("assignment", "rotate")

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

    def model(self, provider: str, profile: str) -> ModelSpec:
        tier = self.tier_for_profile(profile)
        prov = self.provider(provider)
        spec = dict(prov.get("models", {}).get(tier) or {})
        if not spec:
            raise ConfigError(f"provider {provider!r} has no tier {tier!r}")
        model_id = spec.pop("id")
        options = {k: v for k, v in prov.items() if k not in ("models", "sdk")}
        options.update(spec)
        return ModelSpec(provider=provider, tier=tier, id=model_id, sdk=prov["sdk"], options=options)

    def fixed_assignment(self) -> dict[str, str]:
        return dict(self.data.get("assignment", {}).get("fixed", {}))

    def unverified_models(self, providers: list[str] | None = None) -> list[str]:
        out = []
        for name in providers or self.provider_names():
            for tier, spec in self.provider(name).get("models", {}).items():
                if not spec.get("verified", False):
                    out.append(f"{name}.{tier}={spec['id']}")
        return out
