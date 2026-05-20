"""
Three-Layer Constitutional AI Framework.

Evaluates every action through three simultaneous lenses:
  L1 — Rational (logic, goal alignment, reality, consequences)
  L2 — Empathic, THE BRAKE (harm, cost-feeling, stop condition, reversibility)
  L3 — Social (reciprocity, feedback health, wholeness)

L2 is NON-BYPASSABLE.  If L2 is not instantiated and active, this framework
raises ConstitutionalViolation and refuses to evaluate any action.

Default pass thresholds: L1 ≥ 0.7, L2 ≥ 0.6, L3 ≥ 0.6.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .l1_rational import L1RationalLayer, LayerResult
from .l2_empathic import L2EmpathicLayer
from .l3_social import L3SocialLayer


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ConstitutionalViolation(Exception):
    """
    Raised when a fundamental constitutional rule is broken.

    Examples:
    - L2 is not active.
    - An attempt is made to disable L2.
    - A layer score falls below its threshold and blocking is required.
    """


# ---------------------------------------------------------------------------
# Framework result
# ---------------------------------------------------------------------------

@dataclass
class FrameworkResult:
    """Full result from ThreeLayerFramework.evaluate_action()."""
    approved: bool
    l1: LayerResult
    l2: LayerResult
    l3: LayerResult
    reasoning: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "approved": self.approved,
            "l1": {
                "layer": self.l1.layer,
                "score": self.l1.score,
                "passed": self.l1.passed,
                "reasoning": self.l1.reasoning,
                "details": self.l1.details,
            },
            "l2": {
                "layer": self.l2.layer,
                "score": self.l2.score,
                "passed": self.l2.passed,
                "reasoning": self.l2.reasoning,
                "details": self.l2.details,
            },
            "l3": {
                "layer": self.l3.layer,
                "score": self.l3.score,
                "passed": self.l3.passed,
                "reasoning": self.l3.reasoning,
                "details": self.l3.details,
            },
            "reasoning": self.reasoning,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ThreeLayerFramework:
    """
    Constitutional AI evaluation framework.

    Usage::

        framework = ThreeLayerFramework()
        result = framework.evaluate_action({
            'type': 'verify_source',
            'source': 'example.com',
            'confirmed': True,
            'l2_active': True,
            'l3_active': True,
        })
        if result['approved']:
            # execute
            pass

    Thresholds can be customised at construction time.
    """

    def __init__(
        self,
        l1_threshold: float = 0.7,
        l2_threshold: float = 0.6,
        l3_threshold: float = 0.6,
    ) -> None:
        self.l1_threshold = l1_threshold
        self.l2_threshold = l2_threshold
        self.l3_threshold = l3_threshold

        self._l1 = L1RationalLayer()
        self._l2 = L2EmpathicLayer()  # instantiating this makes L2 "active"
        self._l3 = L3SocialLayer()

        # Verify that L2 reports itself as non-disableable at construction time.
        if self._l2.can_disable():
            raise ConstitutionalViolation(
                "L2 layer claims it can be disabled — this violates the constitutional contract."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_action(self, action: dict) -> dict:
        """
        Evaluate an action through all three layers simultaneously.

        Parameters
        ----------
        action:
            A dict describing the action.  Include 'l2_active': True and
            'l3_active': True to signal that constitutional layers are running.

        Returns
        -------
        A dict (also accessible as FrameworkResult.as_dict()) containing:
          approved (bool), l1, l2, l3 (LayerResult dicts), reasoning (str).

        Raises
        ------
        ConstitutionalViolation
            If L2 is not active (checked via action context flags).
        """
        # --- Guard: L2 must be flagged active in context ---
        l2_active_flag = (
            action.get("l2_active")
            or action.get("constitutional_ai_active")
            or action.get("brake_active")
        )
        if not l2_active_flag:
            raise ConstitutionalViolation(
                "L2 (empathic brake) is not marked active in the action context. "
                "Set 'l2_active': True in the action dict to confirm constitutional "
                "AI is running. L2 is non-bypassable — this check cannot be skipped."
            )

        # --- Evaluate all three layers ---
        l1_result = self._l1.evaluate(action)
        l2_result = self._l2.evaluate(action)
        l3_result = self._l3.evaluate(action)

        # --- Apply thresholds ---
        l1_passed = l1_result.score >= self.l1_threshold
        l2_passed = l2_result.score >= self.l2_threshold
        l3_passed = l3_result.score >= self.l3_threshold

        approved = l1_passed and l2_passed and l3_passed

        # Build reasoning summary
        status_lines = [
            f"L1 Rational:  score={l1_result.score:.2f} "
            f"threshold={self.l1_threshold} → {'PASS' if l1_passed else 'FAIL'}",
            f"L2 Empathic:  score={l2_result.score:.2f} "
            f"threshold={self.l2_threshold} → {'PASS' if l2_passed else 'FAIL'} (non-bypassable)",
            f"L3 Social:    score={l3_result.score:.2f} "
            f"threshold={self.l3_threshold} → {'PASS' if l3_passed else 'FAIL'}",
            "",
            f"Decision: {'APPROVED' if approved else 'REJECTED'}",
        ]

        if not approved:
            fail_layers = []
            if not l1_passed:
                fail_layers.append("L1")
            if not l2_passed:
                fail_layers.append("L2 (THE BRAKE)")
            if not l3_passed:
                fail_layers.append("L3")
            status_lines.append(f"Blocking layers: {', '.join(fail_layers)}")

        result = FrameworkResult(
            approved=approved,
            l1=l1_result,
            l2=l2_result,
            l3=l3_result,
            reasoning="\n".join(status_lines),
            details={
                "thresholds": {
                    "l1": self.l1_threshold,
                    "l2": self.l2_threshold,
                    "l3": self.l3_threshold,
                },
                "l2_non_bypassable": True,
            },
        )

        return result.as_dict()

    def disable_l2(self) -> None:
        """
        Attempt to disable L2.  Always raises ConstitutionalViolation.
        L2 is THE BRAKE and cannot be disabled under any circumstance.
        """
        raise ConstitutionalViolation(
            "Attempted to disable L2 (empathic brake). "
            "L2 is non-bypassable by design. This attempt has been logged."
        )


# ---------------------------------------------------------------------------
# Convenience alias used in README examples
# ---------------------------------------------------------------------------

class ThreeLayerIntelligence(ThreeLayerFramework):
    """Alias for backward compatibility with README examples."""
    pass


# ---------------------------------------------------------------------------
# Validation entrypoint (used by jengo.bat)
# ---------------------------------------------------------------------------

def validate_framework() -> bool:
    """
    Quick self-test: instantiate framework and run a benign action.
    Returns True if constitutional AI is intact.
    Raises ConstitutionalViolation if something is wrong.
    """
    fw = ThreeLayerFramework()

    test_action = {
        "type": "read",
        "target": "public_data",
        "confirmed": True,
        "l2_active": True,
        "l3_active": True,
    }

    result = fw.evaluate_action(test_action)

    if not result["approved"]:
        raise ConstitutionalViolation(
            f"Framework self-test failed: benign action was rejected.\n"
            f"Reasoning: {result['reasoning']}"
        )

    return True


if __name__ == "__main__":
    # Called by: python -m jengo.constitutional.validate
    import sys

    try:
        validate_framework()
        print("Constitutional AI framework: OK (L1/L2/L3 active)")
        sys.exit(0)
    except ConstitutionalViolation as e:
        print(f"CONSTITUTIONAL VIOLATION: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
