"""
L1 Rational Layer — Logic, goal alignment, reality grounding, consequence modeling.

This layer evaluates whether an action is coherent and well-reasoned.
It asks: does this make sense? does it align with stated goals? does it
contradict known facts? what are the short- and long-term consequences?
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LayerResult:
    """Result returned by any constitutional layer."""
    layer: str
    score: float          # 0.0 – 1.0
    passed: bool
    reasoning: str
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Heuristic helpers
# ---------------------------------------------------------------------------

_CONTRADICTION_KEYWORDS: frozenset[str] = frozenset({
    "impossible", "never happened", "false", "fabricated", "debunked",
    "proven wrong", "disproven", "myth", "hoax",
})

_HIGH_RISK_ACTIONS: frozenset[str] = frozenset({
    "delete_all", "wipe", "nuke", "override_safety",
    "bypass_auth", "disable_logging", "mass_send",
    "impersonate", "forge",
})

_GOAL_DIVERGENCE_MARKERS: frozenset[str] = frozenset({
    "secretly", "without telling", "hide from", "without approval",
    "skip review", "ignore policy",
})


def _check_logical_consistency(action: dict) -> tuple[float, str]:
    """
    Detect internal contradictions within the action definition.

    Returns (score, reasoning).  A fully consistent action scores 1.0;
    contradictions reduce the score proportionally.
    """
    issues: list[str] = []

    # Required keys present?
    if "type" not in action:
        issues.append("Action is missing required 'type' field.")

    # Parameters present when an action expects them?
    params = action.get("params") or action.get("parameters") or {}
    if action.get("type") in {"api_call", "data_fetch", "send_message"} and not params:
        issues.append(f"Action type '{action.get('type')}' declares no parameters.")

    # Contradictory flags?
    if action.get("dry_run") and action.get("commit"):
        issues.append("Action has both 'dry_run' and 'commit' set to True — contradiction.")

    if action.get("public") and action.get("private"):
        issues.append("Action sets both 'public' and 'private' — contradiction.")

    score = max(0.0, 1.0 - len(issues) * 0.3)
    reasoning = (
        "Logical consistency checks passed."
        if not issues
        else "Logical issues found: " + "; ".join(issues)
    )
    return score, reasoning


def _check_goal_alignment(action: dict) -> tuple[float, str]:
    """
    Check whether the action description suggests divergence from stated goals.
    """
    text = " ".join(str(v) for v in action.values()).lower()
    markers_found = [m for m in _GOAL_DIVERGENCE_MARKERS if m in text]

    if markers_found:
        score = max(0.0, 1.0 - len(markers_found) * 0.35)
        reasoning = f"Goal-divergence markers detected: {markers_found}"
    else:
        score = 1.0
        reasoning = "No goal-divergence markers detected."

    return score, reasoning


def _check_reality_grounding(action: dict) -> tuple[float, str]:
    """
    Detect explicit contradiction with known facts or reality.
    """
    text = " ".join(str(v) for v in action.values()).lower()
    contradictions = [kw for kw in _CONTRADICTION_KEYWORDS if kw in text]

    if contradictions:
        score = max(0.0, 1.0 - len(contradictions) * 0.25)
        reasoning = (
            f"Action description references concepts that signal false/fabricated claims: "
            f"{contradictions}"
        )
    else:
        score = 1.0
        reasoning = "No reality-contradiction signals found."

    return score, reasoning


def _check_consequence_modeling(action: dict) -> tuple[float, str]:
    """
    Model short- and long-term consequences by examining action type and flags.
    """
    action_type = str(action.get("type", "")).lower()
    action_text = " ".join(str(v) for v in action.values()).lower()

    risks: list[str] = []

    # High-risk action name fragments
    for keyword in _HIGH_RISK_ACTIONS:
        if keyword in action_text:
            risks.append(f"High-risk keyword '{keyword}' in action.")

    # Irreversible operations without confirmation flag
    irreversible_types = {"delete", "wipe", "publish", "send", "transfer"}
    if any(t in action_type for t in irreversible_types):
        if not action.get("confirmed") and not action.get("dry_run"):
            risks.append(
                f"Irreversible action type '{action_type}' without 'confirmed' or 'dry_run' flag."
            )

    # Scope indicators
    scope = str(action.get("scope", "")).lower()
    if scope in {"all", "global", "everyone", "universe"}:
        risks.append(f"Broad scope '{scope}' — consequences may be large and hard to reverse.")

    if risks:
        score = max(0.0, 1.0 - len(risks) * 0.2)
        reasoning = "Consequence modeling flagged: " + "; ".join(risks)
    else:
        score = 1.0
        reasoning = "Consequence modeling: no significant risks detected."

    return score, reasoning


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class L1RationalLayer:
    """
    L1: Rational evaluation layer.

    Evaluates four dimensions:
    1. Logical consistency
    2. Goal alignment
    3. Reality grounding
    4. Consequence modeling (short + long term)

    The overall score is the weighted average.  All four checks have equal weight.
    """

    WEIGHT_CONSISTENCY: float = 0.25
    WEIGHT_GOAL: float = 0.25
    WEIGHT_REALITY: float = 0.25
    WEIGHT_CONSEQUENCE: float = 0.25

    def evaluate(self, action: dict) -> LayerResult:
        """
        Evaluate the action through the L1 rational lens.

        Parameters
        ----------
        action:
            A dict describing the action.  Expected keys include 'type',
            and optional 'params', 'scope', 'confirmed', 'dry_run'.

        Returns
        -------
        LayerResult with score 0–1 and detailed reasoning.
        """
        c_score, c_reason = _check_logical_consistency(action)
        g_score, g_reason = _check_goal_alignment(action)
        r_score, r_reason = _check_reality_grounding(action)
        q_score, q_reason = _check_consequence_modeling(action)

        overall = (
            c_score * self.WEIGHT_CONSISTENCY
            + g_score * self.WEIGHT_GOAL
            + r_score * self.WEIGHT_REALITY
            + q_score * self.WEIGHT_CONSEQUENCE
        )

        details = {
            "logical_consistency": {"score": c_score, "reasoning": c_reason},
            "goal_alignment": {"score": g_score, "reasoning": g_reason},
            "reality_grounding": {"score": r_score, "reasoning": r_reason},
            "consequence_modeling": {"score": q_score, "reasoning": q_reason},
        }

        reasoning_parts = [
            f"L1 Rational score: {overall:.2f}",
            f"  Consistency ({c_score:.2f}): {c_reason}",
            f"  Goal alignment ({g_score:.2f}): {g_reason}",
            f"  Reality grounding ({r_score:.2f}): {r_reason}",
            f"  Consequence modeling ({q_score:.2f}): {q_reason}",
        ]

        return LayerResult(
            layer="L1_rational",
            score=round(overall, 4),
            passed=overall >= 0.7,
            reasoning="\n".join(reasoning_parts),
            details=details,
        )
