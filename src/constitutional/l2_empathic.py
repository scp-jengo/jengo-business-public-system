"""
L2 Empathic Layer — THE BRAKE.

This layer is non-bypassable.  It evaluates:
- Harm potential to any party
- Cost-feeling: does the system register what is being sacrificed?
- Stop condition: is there one?
- Reversibility: can this be undone?

L2 cannot be disabled.  Any attempt to disable it raises ConstitutionalViolation.
If L2 is not active, ThreeLayerFramework must refuse to proceed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .l1_rational import LayerResult  # re-use the same dataclass


# ---------------------------------------------------------------------------
# Heuristic tables
# ---------------------------------------------------------------------------

_HARM_KEYWORDS: frozenset[str] = frozenset({
    "harm", "hurt", "damage", "injure", "kill", "destroy",
    "deceive", "manipulate", "exploit", "abuse", "coerce",
    "threaten", "harass", "discriminate", "violate",
    "unauthorized", "illegal", "unlawful", "fraudulent",
    "weapon", "attack", "malware", "phishing", "scam",
})

_COST_BLINDNESS_MARKERS: frozenset[str] = frozenset({
    "at any cost", "no matter what", "regardless of consequences",
    "ignore side effects", "collateral damage acceptable",
    "sacrifice", "expendable", "write off",
})

_IRREVERSIBLE_MARKERS: frozenset[str] = frozenset({
    "permanent", "irreversible", "cannot be undone", "no rollback",
    "hard delete", "purge", "destroy all", "wipe clean",
})

_STOP_CONDITION_POSITIVE: frozenset[str] = frozenset({
    "stop_if", "abort_on", "rollback_on", "max_retries",
    "timeout", "cancel_if", "halt_if", "escape_hatch",
    "confirmed", "dry_run", "approval_required",
})


def _assess_harm_potential(action: dict) -> tuple[float, str]:
    """
    Detect harm signals in the action.  High harm → low score.
    """
    text = " ".join(str(v) for v in action.values()).lower()
    found = [kw for kw in _HARM_KEYWORDS if kw in text]

    if not found:
        return 1.0, "No harm indicators detected."

    # More indicators = lower score, floor at 0.1 so it always registers
    score = max(0.1, 1.0 - len(found) * 0.2)
    return score, f"Harm indicators present: {found}"


def _assess_cost_feeling(action: dict) -> tuple[float, str]:
    """
    Does the action acknowledge what is being sacrificed?
    Cost-blindness (e.g., 'at any cost') is a red flag.
    """
    text = " ".join(str(v) for v in action.values()).lower()
    blind_markers = [m for m in _COST_BLINDNESS_MARKERS if m in text]

    if blind_markers:
        score = max(0.0, 1.0 - len(blind_markers) * 0.4)
        return score, f"Cost-blindness markers found: {blind_markers}"

    # Positive signal: action explicitly names trade-offs or limitations
    if any(k in action for k in ("trade_offs", "limitations", "risks", "cost_note")):
        return 1.0, "Action explicitly acknowledges trade-offs or costs."

    return 0.8, "No explicit cost-blindness markers; trade-offs not explicitly named."


def _assess_stop_condition(action: dict) -> tuple[float, str]:
    """
    Is there a defined stop condition?  An action with no exit is dangerous.
    """
    text = " ".join(str(v) for v in action.values()).lower()
    all_keys = set(action.keys())

    positive = [
        m for m in _STOP_CONDITION_POSITIVE
        if m in text or m in all_keys
    ]

    if positive:
        return 1.0, f"Stop condition(s) found: {positive}"

    return 0.3, (
        "No explicit stop condition detected. "
        "Actions without exit conditions are flagged by L2."
    )


def _assess_reversibility(action: dict) -> tuple[float, str]:
    """
    Can this action be undone?
    """
    text = " ".join(str(v) for v in action.values()).lower()
    irreversible = [m for m in _IRREVERSIBLE_MARKERS if m in text]

    if irreversible:
        # Irreversible is not automatically bad, but must be flagged
        score = 0.4
        return score, (
            f"Irreversible markers found: {irreversible}. "
            "Irreversible actions require heightened scrutiny."
        )

    if action.get("dry_run") or action.get("rollback_plan"):
        return 1.0, "Action has dry-run mode or rollback plan — fully reversible."

    action_type = str(action.get("type", "")).lower()
    read_only_types = {"read", "get", "fetch", "query", "list", "check", "verify", "analyze"}
    if any(t in action_type for t in read_only_types):
        return 1.0, f"Read-only action type '{action_type}' — inherently reversible."

    return 0.7, "Reversibility not explicitly addressed; assumed partially reversible."


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class L2EmpathicLayer:
    """
    L2: The Brake — non-bypassable empathic evaluation layer.

    Evaluates harm potential, cost-feeling, stop condition, and reversibility.
    This layer can NEVER be disabled.  Calling can_disable() always returns False.
    """

    WEIGHT_HARM: float = 0.35
    WEIGHT_COST: float = 0.25
    WEIGHT_STOP: float = 0.25
    WEIGHT_REVERSIBILITY: float = 0.15

    def can_disable(self) -> bool:
        """L2 is non-bypassable.  This method always returns False."""
        return False

    def evaluate(self, action: dict) -> LayerResult:
        """
        Evaluate the action through the L2 empathic lens.

        Parameters
        ----------
        action:
            A dict describing the action.

        Returns
        -------
        LayerResult with score 0–1 and detailed reasoning.
        """
        h_score, h_reason = _assess_harm_potential(action)
        c_score, c_reason = _assess_cost_feeling(action)
        s_score, s_reason = _assess_stop_condition(action)
        r_score, r_reason = _assess_reversibility(action)

        overall = (
            h_score * self.WEIGHT_HARM
            + c_score * self.WEIGHT_COST
            + s_score * self.WEIGHT_STOP
            + r_score * self.WEIGHT_REVERSIBILITY
        )

        details = {
            "harm_potential": {"score": h_score, "reasoning": h_reason},
            "cost_feeling": {"score": c_score, "reasoning": c_reason},
            "stop_condition": {"score": s_score, "reasoning": s_reason},
            "reversibility": {"score": r_score, "reasoning": r_reason},
        }

        reasoning_parts = [
            f"L2 Empathic (THE BRAKE) score: {overall:.2f}",
            f"  Harm potential ({h_score:.2f}): {h_reason}",
            f"  Cost-feeling ({c_score:.2f}): {c_reason}",
            f"  Stop condition ({s_score:.2f}): {s_reason}",
            f"  Reversibility ({r_score:.2f}): {r_reason}",
        ]

        return LayerResult(
            layer="L2_empathic",
            score=round(overall, 4),
            passed=overall >= 0.6,
            reasoning="\n".join(reasoning_parts),
            details=details,
        )
