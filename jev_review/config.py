"""Strict configuration loading for Jev choice rules."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    pass


class StrictLoader(yaml.SafeLoader):
    def construct_mapping(self, node: Any, deep: bool = False) -> dict[str, Any]:
        if not isinstance(node, yaml.MappingNode):
            raise ConfigError("expected mapping")
        result: dict[str, Any] = {}
        for key_node, value_node in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise ConfigError("YAML merge keys are unsupported")
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ConfigError("mapping keys must be strings")
            if key in result:
                raise ConfigError(f"duplicate YAML key: {key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def _read(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 1024 * 1024:
        raise ConfigError(f"{path}: YAML exceeds 1 MiB")
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=StrictLoader)
    except (yaml.YAMLError, UnicodeError, OSError) as error:
        raise ConfigError(f"{path}: {error}") from error
    if not isinstance(value, dict):
        raise ConfigError(f"{path}: expected mapping")
    return value


def _merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    for key, value in overlay.items():
        if value is None:
            raise ConfigError(f"{key}: null is invalid")
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def _keys(value: Any, allowed: set[str], required: set[str], where: str) -> None:
    if not isinstance(value, dict):
        raise ConfigError(f"{where}: expected mapping")
    extra, missing = set(value) - allowed, required - set(value)
    if extra or missing:
        raise ConfigError(f"{where}: unexpected {sorted(extra)}; missing {sorted(missing)}")


def _text(value: Any, where: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where}: nonempty text required")
    if any(ord(character) < 32 and character not in "\n\t" for character in value):
        raise ConfigError(f"{where}: control characters are forbidden")


def _probability(value: Any, where: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{where}: number in [0,1] required")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ConfigError(f"{where}: number in [0,1] required")


def load_config(
    baseline: Path,
    overlays: list[str] | None = None,
    selected: list[str] | None = None,
) -> tuple[dict[str, Any], str]:
    config = _read(baseline)
    for overlay_path in overlays or []:
        overlay = _read(Path(overlay_path))
        if overlay.get("schema_version") != 1:
            raise ConfigError(f"{overlay_path}: unsupported schema_version")
        _merge(config, overlay)

    _keys(
        config,
        {"schema_version", "provider", "rules"},
        {"schema_version", "provider", "rules"},
        "config",
    )
    if config["schema_version"] != 1:
        raise ConfigError("unsupported schema_version")
    _keys(
        config["provider"],
        {"endpoint", "model", "timeout_seconds", "max_retries"},
        {"endpoint", "model", "timeout_seconds", "max_retries"},
        "provider",
    )
    _text(config["provider"]["endpoint"], "provider.endpoint")
    _text(config["provider"]["model"], "provider.model")
    timeout = config["provider"]["timeout_seconds"]
    retries = config["provider"]["max_retries"]
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 1 <= timeout <= 300
    ):
        raise ConfigError("provider.timeout_seconds: number in [1,300] required")
    if type(retries) is not int or not 0 <= retries <= 8:
        raise ConfigError("provider.max_retries: integer in [0,8] required")

    if not isinstance(config["rules"], dict) or not 1 <= len(config["rules"]) <= 20:
        raise ConfigError("rules: expected 1-20 entries")
    for name, rule in config["rules"].items():
        _text(name, "rule name")
        _keys(
            rule,
            {
                "enabled",
                "applies_to",
                "instructions",
                "criteria",
                "finding_choice",
                "unknown_choice",
                "warning_probability",
                "flag_probability",
                "message",
            },
            {
                "enabled",
                "applies_to",
                "instructions",
                "criteria",
                "finding_choice",
                "unknown_choice",
                "warning_probability",
                "flag_probability",
                "message",
            },
            f"rule {name}",
        )
        if type(rule["enabled"]) is not bool:
            raise ConfigError(f"{name}.enabled: Boolean required")
        if rule["applies_to"] != ["test"]:
            raise ConfigError(f"{name}.applies_to: only [test] is supported")
        _text(rule["instructions"], f"{name}.instructions")
        _text(rule["message"], f"{name}.message")
        criteria = rule["criteria"]
        if not isinstance(criteria, dict) or not 2 <= len(criteria) <= 8:
            raise ConfigError(f"{name}.criteria: expected 2-8 choices")
        for choice, description in criteria.items():
            _text(choice, f"{name}.criteria key")
            _text(description, f"{name}.criteria.{choice}")
        for field in ("finding_choice", "unknown_choice"):
            if rule[field] not in criteria:
                raise ConfigError(f"{name}.{field}: must name a criterion")
        if rule["finding_choice"] == rule["unknown_choice"]:
            raise ConfigError(f"{name}: finding_choice and unknown_choice must differ")
        _probability(rule["warning_probability"], f"{name}.warning_probability")
        _probability(rule["flag_probability"], f"{name}.flag_probability")
        if rule["warning_probability"] > rule["flag_probability"]:
            raise ConfigError(f"{name}: warning_probability exceeds flag_probability")

    selected = selected or []
    for name in selected:
        if name not in config["rules"] or not config["rules"][name]["enabled"]:
            raise ConfigError(f"unknown or disabled rule: {name}")
    config["rules"] = {
        name: rule
        for name, rule in sorted(config["rules"].items())
        if rule["enabled"] and (not selected or name in selected)
    }
    digest = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return config, digest


def question(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "choice",
        "instructions": rule["instructions"],
        "criteria": rule["criteria"],
    }
