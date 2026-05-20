"""
Policy Engine.

Loads YAML policy files from a directory, applies them in priority order
(lowest priority number first), and returns a PolicyResult.

Supported rule actions:
  block_if_below          — block action if check score is below threshold
  require_approval_if_below — require approval if check score is below threshold
  block_if_unverified     — block action if check returns unverified
  warn_if_below           — add a warning but do not block
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .yaml_parser import parse_policy_file, Policy, PolicyRule


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class PolicyResult:
    """Result of PolicyEngine.check_action()."""
    approved: bool
    applied_policies: list[str]
    reasoning: str
    requires_approval: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_rules: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Built-in check implementations
# ---------------------------------------------------------------------------

def _run_check(check_name: str, action: dict) -> float:
    """
    Run a named check against an action dict.

    Returns a score between 0.0 and 1.0.

    Built-in checks:
      source_credibility    — from action['source_score'] or heuristic
      claim_verification    — from action['claim_score'] or heuristic
      bias_score            — from action['bias_score'] or heuristic
      harm_potential        — from action['harm_score'] or heuristic

    Unknown checks default to 1.0 (pass-through).
    """
    known_score_keys = {
        "source_credibility": "source_score",
        "claim_verification": "claim_score",
        "bias_score": "bias_score",
        "harm_potential": "harm_score",
    }

    if check_name in known_score_keys:
        score_key = known_score_keys[check_name]
        # Use explicitly provided score if available
        if score_key in action:
            return float(action[score_key])

        # Fallback: look for any key containing the check name
        for k, v in action.items():
            if check_name.replace("_", "") in k.replace("_", "").lower():
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass

        # Default to a neutral-positive score when no data provided
        return 0.8

    # Unknown check — pass through
    return 1.0


def _is_verified(action: dict) -> bool:
    """Return True if the action carries a verification flag."""
    return bool(
        action.get("verified")
        or action.get("claim_verified")
        or action.get("source_verified")
    )


def _source_count(action: dict) -> int:
    """Return the number of sources referenced in the action."""
    sources = action.get("sources") or action.get("source_list") or []
    if isinstance(sources, list):
        return len(sources)
    if isinstance(sources, str):
        return 1
    return int(action.get("source_count", 0))


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class PolicyEngine:
    """
    YAML-based policy engine.

    Policies are loaded from a directory at construction time (or lazily via
    load_policies()).  They are applied in ascending priority order (lowest
    number = highest precedence).

    Example::

        engine = PolicyEngine(policy_dir='./policies')
        result = engine.check_action({'type': 'publish', 'source_score': 0.5})
        if result.approved:
            # proceed
            pass
    """

    def __init__(self, policy_dir: str | None = None) -> None:
        self._policies: list[Policy] = []
        if policy_dir:
            self.load_policies(policy_dir)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_policies(self, policy_dir: str) -> int:
        """
        Load all .yaml / .yml files from policy_dir.

        Returns the number of policies loaded.
        Files that fail to parse are skipped with a warning.
        """
        dir_path = Path(policy_dir)
        if not dir_path.is_dir():
            return 0

        loaded = 0
        for fpath in sorted(dir_path.glob("**/*.yaml")) + sorted(dir_path.glob("**/*.yml")):
            try:
                policy = parse_policy_file(str(fpath))
                self._policies.append(policy)
                loaded += 1
            except Exception as exc:
                import warnings
                warnings.warn(f"Failed to load policy '{fpath}': {exc}")

        # Sort by priority (ascending — lower number = higher priority)
        self._policies.sort(key=lambda p: p.priority)
        return loaded

    def add_policy(self, policy: Policy) -> None:
        """Add a pre-parsed Policy object and re-sort by priority."""
        self._policies.append(policy)
        self._policies.sort(key=lambda p: p.priority)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def check_action(self, action: dict) -> PolicyResult:
        """
        Apply all enabled policies to the action, in priority order.

        Parameters
        ----------
        action:
            A dict describing the action.  Policy checks read values from here.

        Returns
        -------
        PolicyResult
        """
        applied: list[str] = []
        warnings_list: list[str] = []
        blocking_rules: list[str] = []
        requires_approval = False
        blocked = False

        for policy in self._policies:
            if not policy.enabled:
                continue

            policy_applied = False

            for rule in policy.rules:
                score = _run_check(rule.check, action)

                if rule.action == "block_if_below":
                    threshold = rule.threshold if rule.threshold is not None else 0.7
                    if score < threshold:
                        blocked = True
                        blocking_rules.append(
                            f"[{policy.name}] Rule '{rule.check}': "
                            f"score {score:.2f} < threshold {threshold:.2f} → blocked"
                        )
                        policy_applied = True

                elif rule.action == "require_approval_if_below":
                    threshold = rule.threshold if rule.threshold is not None else 0.7
                    if score < threshold:
                        requires_approval = True
                        warnings_list.append(
                            f"[{policy.name}] Rule '{rule.check}': "
                            f"score {score:.2f} < threshold {threshold:.2f} → approval required"
                        )
                        policy_applied = True

                elif rule.action == "block_if_unverified":
                    min_sources = rule.require_sources or 1
                    if not _is_verified(action) and _source_count(action) < min_sources:
                        blocked = True
                        blocking_rules.append(
                            f"[{policy.name}] Rule '{rule.check}': "
                            f"unverified with {_source_count(action)} source(s), "
                            f"need {min_sources} → blocked"
                        )
                        policy_applied = True

                elif rule.action == "warn_if_below":
                    threshold = rule.threshold if rule.threshold is not None else 0.7
                    if score < threshold:
                        warnings_list.append(
                            f"[{policy.name}] Rule '{rule.check}': "
                            f"score {score:.2f} < threshold {threshold:.2f} → warning"
                        )
                        policy_applied = True

            if policy_applied:
                applied.append(policy.id)

        # Build reasoning
        parts: list[str] = []
        if blocking_rules:
            parts.append("Blocking rules triggered:")
            parts.extend(f"  - {r}" for r in blocking_rules)
        if warnings_list:
            parts.append("Warnings:")
            parts.extend(f"  - {w}" for w in warnings_list)
        if not parts:
            parts.append("All policy checks passed.")

        reasoning = "\n".join(parts)

        return PolicyResult(
            approved=not blocked,
            applied_policies=applied,
            reasoning=reasoning,
            requires_approval=requires_approval,
            warnings=warnings_list,
            blocking_rules=blocking_rules,
        )

    @property
    def policy_count(self) -> int:
        return len(self._policies)

    @property
    def enabled_policies(self) -> list[Policy]:
        return [p for p in self._policies if p.enabled]
