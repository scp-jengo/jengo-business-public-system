"""
YAML Policy File Parser.

Schema for a policy file::

    id: source-verification
    name: Source Verification Policy
    enabled: true
    priority: 10            # lower number = higher priority
    rules:
      - check: source_credibility
        threshold: 0.7
        action: require_approval_if_below
      - check: claim_verification
        require_sources: 2
        action: block_if_unverified

Required top-level fields: id, name, enabled, priority, rules.
Each rule must have at minimum: check and action.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PolicyRule:
    """A single rule within a policy."""
    check: str
    action: str
    threshold: float | None = None
    require_sources: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyRule":
        if "check" not in data:
            raise ValueError(f"Policy rule is missing required field 'check': {data}")
        if "action" not in data:
            raise ValueError(f"Policy rule is missing required field 'action': {data}")

        extra = {
            k: v
            for k, v in data.items()
            if k not in {"check", "action", "threshold", "require_sources"}
        }

        return cls(
            check=data["check"],
            action=data["action"],
            threshold=data.get("threshold"),
            require_sources=data.get("require_sources"),
            extra=extra,
        )


@dataclass
class Policy:
    """A parsed policy loaded from a YAML file."""
    id: str
    name: str
    enabled: bool
    priority: int
    rules: list[PolicyRule]
    source_path: str = ""

    @classmethod
    def from_dict(cls, data: dict, source_path: str = "") -> "Policy":
        _require_fields(data, ["id", "name", "enabled", "priority", "rules"], source_path)

        raw_rules = data["rules"]
        if not isinstance(raw_rules, list):
            raise ValueError(f"'rules' must be a list in policy '{data.get('id', '?')}' ({source_path})")

        rules = [PolicyRule.from_dict(r) for r in raw_rules]

        return cls(
            id=data["id"],
            name=data["name"],
            enabled=bool(data["enabled"]),
            priority=int(data["priority"]),
            rules=rules,
            source_path=source_path,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_fields(data: dict, fields: list[str], source: str) -> None:
    missing = [f for f in fields if f not in data]
    if missing:
        raise ValueError(
            f"Policy file '{source}' is missing required fields: {missing}"
        )


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def parse_policy_file(path: str) -> Policy:
    """
    Parse a YAML policy file and return a Policy instance.

    Parameters
    ----------
    path:
        Absolute or relative path to the .yaml policy file.

    Returns
    -------
    Policy

    Raises
    ------
    FileNotFoundError  — if the file does not exist.
    ValueError         — if required fields are missing or types are wrong.
    yaml.YAMLError     — if the file is not valid YAML.
    """
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Policy file not found: {resolved}")

    with open(resolved, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError(f"Policy file '{resolved}' must be a YAML mapping, got {type(data).__name__}")

    return Policy.from_dict(data, source_path=str(resolved))
