"""Configuration loading and validation for AISKG.

All non-legacy scientific parameters are read from YAML.  The frozen legacy
engines remain versioned compatibility implementations so that the published
manuscript outputs can be reproduced exactly.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml


class ConfigError(ValueError):
    """Raised when an AISKG configuration is incomplete or inconsistent."""


def _deep_get(mapping: Mapping[str, Any], path: str) -> Any:
    value: Any = mapping
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise ConfigError(f"Missing required configuration key: {path}")
        value = value[part]
    return value


REQUIRED_KEYS = (
    "project.name",
    "project.version",
    "project.mode",
    "project.random_seed",
    "paths.section1_input_bundle",
    "paths.section2_input_bundle",
    "paths.ablation_frozen_bundle",
    "paths.ablation_expected_results",
    "paths.output_root",
    "paths.work_root",
    "stages.section1_snapshot",
    "stages.section2_snapshot",
    "stages.ablation",
    "reproducibility.verify_input_sha256",
    "reproducibility.verify_ablation_expected_results",
    "release.archive_name",
)


@dataclass(frozen=True)
class AISKGConfig:
    """Loaded YAML configuration together with its repository root."""

    data: dict[str, Any]
    path: Path
    repository_root: Path

    @classmethod
    def load(cls, path: str | Path) -> "AISKGConfig":
        config_path = Path(path).expanduser().resolve()
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ConfigError("The root YAML object must be a mapping")

        root = _find_repository_root(config_path.parent)
        config = cls(data=payload, path=config_path, repository_root=root)
        config.validate()
        return config

    def validate(self) -> None:
        for key in REQUIRED_KEYS:
            _deep_get(self.data, key)

        weights = self.get("research_representation.weights")
        if not isinstance(weights, Mapping):
            raise ConfigError("research_representation.weights must be a mapping")
        total = sum(float(value) for value in weights.values())
        if abs(total - 1.0) > 1e-10:
            raise ConfigError(f"Research-representation weights must sum to 1.0; got {total}")

        variants = self.get("ablation.variants")
        if not isinstance(variants, list) or not variants:
            raise ConfigError("ablation.variants must contain at least one variant")
        names = [str(item.get("name", "")) for item in variants]
        if len(names) != len(set(names)):
            raise ConfigError("Ablation variant names must be unique")
        if "FULL_FRAMEWORK" not in names:
            raise ConfigError("Ablation configuration must include FULL_FRAMEWORK")

    def get(self, path: str) -> Any:
        """Return a required value without silently applying a fallback."""
        return _deep_get(self.data, path)

    def path_value(self, path: str) -> Path:
        value = Path(str(self.get(path)))
        return value if value.is_absolute() else (self.repository_root / value).resolve()

    def stage_enabled(self, name: str) -> bool:
        return bool(self.get(f"stages.{name}"))

    def variants(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self.get("ablation.variants")]


def _find_repository_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() or (candidate / "run_pipeline.py").exists():
            return candidate
    # During early bootstrap/tests, the config file itself can define the root.
    return start.resolve()


def require_paths(config: AISKGConfig, keys: Iterable[str]) -> None:
    missing = [str(config.path_value(key)) for key in keys if not config.path_value(key).exists()]
    if missing:
        raise FileNotFoundError("Missing configured input files:\n- " + "\n- ".join(missing))
