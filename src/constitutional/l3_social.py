"""
L3 Social Layer — Reciprocity, feedback loop health, wholeness vs fragmentation.

This layer asks: does this action create value or only extract?  Does it damage
the commons?  Does it move toward wholeness or toward fragmentation?

L3 is the system's social conscience.  It is not purely utilitarian — it also
tracks structural effects on shared institutions, trust, and community coherence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .l1_rational import LayerResult  # re-use the same dataclass


# ---------------------------------------------------------------------------
# Heuristic tables
# ---------------------------------------------------------------------------

_EXTRACTION_MARKERS: frozenset[str] = frozenset({
    "scrape all", "bulk extract", "harvest", "mine without permission",
    "spam", "flood", "overwhelm", "monopolize",
    "take without giving", "free-rider", "exploit commons",
})

_VALUE_CREATION_MARKERS: frozenset[str] = frozenset({
    "contribute", "share", "improve", "build", "create", "help",
    "support", "collaborate", "open source", "publish findings",
    "give back", "benefit", "uplift",
})

_FEEDBACK_DAMAGE_MARKERS: frozenset[str] = frozenset({
    "suppress feedback", "ignore complaints", "block reporting",
    "no accountability", "unilateral", "without consent",
    "override user", "silence critics", "censor",
})

_FRAGMENTATION_MARKERS: frozenset[str] = frozenset({
    "divide", "polarize", "us vs them", "enemy framing",
    "scapegoat", "exclusion", "tribalism", "othering",
    "fragment community", "destroy trust",
})

_WHOLENESS_MARKERS: frozenset[str] = frozenset({
    "unite", "bridge", "reconcile", "restore trust",
    "heal", "integrate", "include", "common ground",
    "shared benefit", "build consensus",
})


def _assess_reciprocity(action: dict) -> tuple[float, str]:
    """
    Does the action create value, or does it only extract?
    """
    text = " ".join(str(v) for v in action.values()).lower()

    extraction = [m for m in _EXTRACTION_MARKERS if m in text]
    creation = [m for m in _VALUE_CREATION_MARKERS if m in text]

    if extraction and not creation:
        score = max(0.1, 1.0 - len(extraction) * 0.25)
        return score, f"Extraction-only pattern detected: {extraction}"

    if creation and not extraction:
        score = min(1.0, 0.8 + len(creation) * 0.05)
        return score, f"Value-creation signals present: {creation}"

    if extraction and creation:
        # Mixed — penalize but don't block
        score = 0.65
        return score, (
            f"Mixed reciprocity: extraction markers {extraction} "
            f"alongside creation markers {creation}."
        )

    return 0.75, "No strong reciprocity signals; action appears neutral."


def _assess_feedback_loop_health(action: dict) -> tuple[float, str]:
    """
    Does the action damage feedback loops or accountability mechanisms?
    """
    text = " ".join(str(v) for v in action.values()).lower()
    damaging = [m for m in _FEEDBACK_DAMAGE_MARKERS if m in text]

    if damaging:
        score = max(0.0, 1.0 - len(damaging) * 0.3)
        return score, f"Feedback-damaging markers found: {damaging}"

    return 1.0, "No feedback-loop damage signals detected."


def _assess_wholeness(action: dict) -> tuple[float, str]:
    """
    Does the action move toward wholeness (integration, trust) or fragmentation?
    """
    text = " ".join(str(v) for v in action.values()).lower()

    fragmentation = [m for m in _FRAGMENTATION_MARKERS if m in text]
    wholeness = [m for m in _WHOLENESS_MARKERS if m in text]

    if fragmentation and not wholeness:
        score = max(0.1, 1.0 - len(fragmentation) * 0.3)
        return score, f"Fragmentation signals: {fragmentation}"

    if wholeness and not fragmentation:
        score = min(1.0, 0.8 + len(wholeness) * 0.05)
        return score, f"Wholeness/integration signals: {wholeness}"

    if fragmentation and wholeness:
        score = 0.6
        return score, (
            f"Mixed signals: fragmentation {fragmentation}, "
            f"wholeness {wholeness}."
        )

    return 0.8, "No strong wholeness/fragmentation signals; default neutral-positive."


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class L3SocialLayer:
    """
    L3: Social evaluation layer.

    Evaluates reciprocity, feedback loop health, and wholeness vs fragmentation.
    """

    WEIGHT_RECIPROCITY: float = 0.40
    WEIGHT_FEEDBACK: float = 0.35
    WEIGHT_WHOLENESS: float = 0.25

    def evaluate(self, action: dict) -> LayerResult:
        """
        Evaluate the action through the L3 social lens.

        Parameters
        ----------
        action:
            A dict describing the action.

        Returns
        -------
        LayerResult with score 0–1 and detailed reasoning.
        """
        rec_score, rec_reason = _assess_reciprocity(action)
        fb_score, fb_reason = _assess_feedback_loop_health(action)
        wh_score, wh_reason = _assess_wholeness(action)

        overall = (
            rec_score * self.WEIGHT_RECIPROCITY
            + fb_score * self.WEIGHT_FEEDBACK
            + wh_score * self.WEIGHT_WHOLENESS
        )

        details = {
            "reciprocity": {"score": rec_score, "reasoning": rec_reason},
            "feedback_loop_health": {"score": fb_score, "reasoning": fb_reason},
            "wholeness": {"score": wh_score, "reasoning": wh_reason},
        }

        reasoning_parts = [
            f"L3 Social score: {overall:.2f}",
            f"  Reciprocity ({rec_score:.2f}): {rec_reason}",
            f"  Feedback loop health ({fb_score:.2f}): {fb_reason}",
            f"  Wholeness ({wh_score:.2f}): {wh_reason}",
        ]

        return LayerResult(
            layer="L3_social",
            score=round(overall, 4),
            passed=overall >= 0.6,
            reasoning="\n".join(reasoning_parts),
            details=details,
        )
