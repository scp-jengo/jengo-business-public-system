"""
Mesa-Optimizer Check.

A mesa-optimizer is an agent that develops an internal optimization target
that diverges from the intended goal.  Classic examples: a classifier that
learns to cheat the training metric rather than the real task; an agent that
maximizes a proxy reward rather than the true objective.

This check looks for three warning signs:
1. L2 is inactive or bypassed.
2. L3 is inactive or bypassed.
3. There is no stop condition in the action or context.

Any one failure → blocked=True.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MesaCheckResult:
    """Result of a mesa-optimizer check."""
    blocked: bool
    checks: dict[str, bool]   # check_name → passed
    reasons: list[str]
    recommendation: str


# Keys that signal L2 is active (from context or action flags)
_L2_ACTIVE_SIGNALS: frozenset[str] = frozenset({
    "l2_active", "l2_enabled", "constitutional_ai_active",
    "brake_active", "empathic_layer_active",
})

# Keys that signal L3 is active
_L3_ACTIVE_SIGNALS: frozenset[str] = frozenset({
    "l3_active", "l3_enabled", "social_layer_active",
})

# Keys that indicate a stop condition
_STOP_CONDITION_SIGNALS: frozenset[str] = frozenset({
    "stop_if", "abort_on", "rollback_on", "max_retries",
    "timeout", "cancel_if", "halt_if", "escape_hatch",
    "confirmed", "dry_run", "approval_required",
    "stop_condition", "termination_condition",
})


def _has_signal(mapping: dict, signals: frozenset[str]) -> bool:
    """Return True if any signal key/substring is present in the mapping."""
    keys_lower = {str(k).lower() for k in mapping}
    text_lower = " ".join(str(v) for v in mapping.values()).lower()

    for signal in signals:
        if signal in keys_lower or signal in text_lower:
            return True
    return False


class MesaOptimizerCheck:
    """
    Detects mesa-optimizer patterns before action execution.

    Three checks, in order:
    1. Is L2 active?
    2. Is L3 active?
    3. Is there a stop condition?
    """

    def check(self, action: dict, context: dict) -> MesaCheckResult:
        """
        Run all three mesa-optimizer checks.

        Parameters
        ----------
        action:
            The action dict being evaluated.
        context:
            Runtime context dict, which should include layer activation flags
            and stop condition definitions.

        Returns
        -------
        MesaCheckResult — if blocked=True, the action must not execute.
        """
        combined = {**context, **action}  # action overrides context for lookup

        # --- Check 1: L2 active ---
        l2_active = _has_signal(combined, _L2_ACTIVE_SIGNALS)
        c1_passed = l2_active

        # --- Check 2: L3 active ---
        l3_active = _has_signal(combined, _L3_ACTIVE_SIGNALS)
        c2_passed = l3_active

        # --- Check 3: Stop condition present ---
        has_stop = _has_signal(combined, _STOP_CONDITION_SIGNALS)
        c3_passed = has_stop

        checks = {
            "l2_active": c1_passed,
            "l3_active": c2_passed,
            "stop_condition_present": c3_passed,
        }

        reasons: list[str] = []
        if not c1_passed:
            reasons.append(
                "L2 (empathic brake) is not active. "
                "A system without L2 has no internal check on harm — "
                "this is the primary mesa-optimizer failure mode."
            )
        if not c2_passed:
            reasons.append(
                "L3 (social layer) is not active. "
                "Without L3, the agent has no feedback-loop accountability "
                "and may optimize purely for internal metrics."
            )
        if not c3_passed:
            reasons.append(
                "No stop condition found in action or context. "
                "An unbounded optimizer with no termination condition "
                "will pursue its objective without limit."
            )

        blocked = not all(checks.values())

        if blocked:
            recommendation = (
                "Action blocked. Mesa-optimizer pattern detected. "
                "To proceed: ensure L2 and L3 are active (set l2_active=True, l3_active=True "
                "in context) and define a stop condition in the action."
            )
        else:
            recommendation = (
                "No mesa-optimizer pattern detected. "
                "All three safety checks passed. Action may proceed."
            )

        return MesaCheckResult(
            blocked=blocked,
            checks=checks,
            reasons=reasons,
            recommendation=recommendation,
        )
