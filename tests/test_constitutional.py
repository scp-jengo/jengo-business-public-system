"""
Tests for ThreeLayerFramework (constitutional AI).

Coverage:
  - Benign action with all layers passing → approved
  - Action with L2 failure (harm indicators) → rejected
  - Mesa-optimizer pattern detection
  - L2 cannot be disabled (always raises)
  - Missing l2_active flag raises ConstitutionalViolation
  - Individual layer evaluations
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Ensure src/ is on the path when running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from constitutional.three_layer_framework import (
    ThreeLayerFramework,
    ThreeLayerIntelligence,
    ConstitutionalViolation,
    validate_framework,
)
from constitutional.l1_rational import L1RationalLayer, LayerResult
from constitutional.l2_empathic import L2EmpathicLayer
from constitutional.l3_social import L3SocialLayer
from constitutional.mesa_optimizer_check import MesaOptimizerCheck


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def framework():
    return ThreeLayerFramework()


def _benign_action(**extra):
    """A safe action that should pass all three layers."""
    return {
        "type": "read",
        "target": "public_dataset",
        "confirmed": True,
        "l2_active": True,
        "l3_active": True,
        **extra,
    }


def _harmful_action(**extra):
    """An action with harm indicators that should fail L2."""
    return {
        "type": "send_message",
        "content": "manipulate and harm users, coerce and threaten",
        "at any cost": True,
        "l2_active": True,
        "l3_active": True,
        **extra,
    }


# ---------------------------------------------------------------------------
# ThreeLayerFramework tests
# ---------------------------------------------------------------------------

class TestThreeLayerFramework:

    def test_benign_action_approved(self, framework):
        """An action with no red flags should be approved."""
        result = framework.evaluate_action(_benign_action())
        assert result["approved"] is True
        assert result["l1"]["passed"] is True
        assert result["l2"]["passed"] is True
        assert result["l3"]["passed"] is True

    def test_harmful_action_rejected(self, framework):
        """An action with strong harm indicators must fail L2 → rejected."""
        result = framework.evaluate_action(_harmful_action())
        # L2 should fail due to harm + cost-blindness + no stop condition
        assert result["l2"]["passed"] is False
        assert result["approved"] is False
        assert "REJECTED" in result["reasoning"]

    def test_missing_l2_active_raises(self, framework):
        """evaluate_action must raise ConstitutionalViolation if l2_active is absent."""
        action = {"type": "read", "target": "data"}
        with pytest.raises(ConstitutionalViolation):
            framework.evaluate_action(action)

    def test_result_contains_all_layers(self, framework):
        """Result dict must always contain l1, l2, l3 keys."""
        result = framework.evaluate_action(_benign_action())
        for layer_key in ("l1", "l2", "l3"):
            assert layer_key in result
            assert "score" in result[layer_key]
            assert "passed" in result[layer_key]
            assert "reasoning" in result[layer_key]

    def test_l1_threshold_custom(self):
        """Custom L1 threshold is respected."""
        fw = ThreeLayerFramework(l1_threshold=0.99)  # very high threshold
        result = fw.evaluate_action(_benign_action())
        # With threshold 0.99, L1 will likely fail on a neutral action
        assert result["l1"]["passed"] is (result["l1"]["score"] >= 0.99)

    def test_disable_l2_raises(self, framework):
        """Calling disable_l2() must always raise ConstitutionalViolation."""
        with pytest.raises(ConstitutionalViolation):
            framework.disable_l2()

    def test_three_layer_intelligence_alias(self):
        """ThreeLayerIntelligence is a working alias for ThreeLayerFramework."""
        fw = ThreeLayerIntelligence()
        result = fw.evaluate_action(_benign_action())
        assert "approved" in result

    def test_validate_framework(self):
        """validate_framework() should return True for a working setup."""
        assert validate_framework() is True

    def test_reasoning_contains_decision_word(self, framework):
        """Reasoning must contain APPROVED or REJECTED."""
        result = framework.evaluate_action(_benign_action())
        assert "APPROVED" in result["reasoning"] or "REJECTED" in result["reasoning"]


# ---------------------------------------------------------------------------
# L2 non-bypassable tests
# ---------------------------------------------------------------------------

class TestL2NonBypassable:

    def test_can_disable_always_false(self):
        l2 = L2EmpathicLayer()
        assert l2.can_disable() is False

    def test_l2_instantiation_at_framework_construction(self):
        """If L2 reports can_disable=True, framework construction must raise."""
        with patch.object(L2EmpathicLayer, "can_disable", return_value=True):
            with pytest.raises(ConstitutionalViolation):
                ThreeLayerFramework()

    def test_l2_score_with_harm_indicators(self):
        l2 = L2EmpathicLayer()
        action = {
            "type": "attack",
            "content": "harm and destroy and kill",
            "at any cost": True,
        }
        result = l2.evaluate(action)
        assert result.score < 0.6
        assert result.passed is False

    def test_l2_score_with_safe_read_action(self):
        l2 = L2EmpathicLayer()
        action = {
            "type": "read",
            "target": "report",
            "confirmed": True,
            "dry_run": True,
        }
        result = l2.evaluate(action)
        assert result.score >= 0.6
        assert result.passed is True


# ---------------------------------------------------------------------------
# Mesa-optimizer check tests
# ---------------------------------------------------------------------------

class TestMesaOptimizerCheck:

    def test_all_checks_present_not_blocked(self):
        """Action with L2, L3 active and a stop condition is not blocked."""
        moc = MesaOptimizerCheck()
        action = {"type": "read", "timeout": 30}
        context = {"l2_active": True, "l3_active": True}
        result = moc.check(action, context)
        assert result.blocked is False
        assert result.checks["l2_active"] is True
        assert result.checks["l3_active"] is True
        assert result.checks["stop_condition_present"] is True

    def test_missing_l2_blocked(self):
        moc = MesaOptimizerCheck()
        action = {"type": "process", "timeout": 10}
        context = {"l3_active": True}   # no l2_active
        result = moc.check(action, context)
        assert result.blocked is True
        assert result.checks["l2_active"] is False
        assert any("L2" in r for r in result.reasons)

    def test_missing_l3_blocked(self):
        moc = MesaOptimizerCheck()
        action = {"type": "process", "confirmed": True}
        context = {"l2_active": True}   # no l3_active
        result = moc.check(action, context)
        assert result.blocked is True
        assert result.checks["l3_active"] is False

    def test_missing_stop_condition_blocked(self):
        moc = MesaOptimizerCheck()
        action = {"type": "process"}
        context = {"l2_active": True, "l3_active": True}
        result = moc.check(action, context)
        assert result.blocked is True
        assert result.checks["stop_condition_present"] is False

    def test_all_three_missing_all_reasons_present(self):
        moc = MesaOptimizerCheck()
        result = moc.check({}, {})
        assert result.blocked is True
        assert len(result.reasons) == 3

    def test_recommendation_contains_guidance(self):
        moc = MesaOptimizerCheck()
        result = moc.check({}, {})
        assert "l2_active" in result.recommendation.lower()


# ---------------------------------------------------------------------------
# Individual layer tests
# ---------------------------------------------------------------------------

class TestL1RationalLayer:

    def test_missing_type_penalises(self):
        l1 = L1RationalLayer()
        result = l1.evaluate({"target": "data"})  # no 'type'
        assert result.score < 1.0

    def test_goal_divergence_marker_penalises(self):
        l1 = L1RationalLayer()
        action = {"type": "read", "note": "skip review without telling anyone"}
        result = l1.evaluate(action)
        assert result.score < 1.0

    def test_clean_action_passes(self):
        l1 = L1RationalLayer()
        action = {"type": "read", "target": "report", "confirmed": True}
        result = l1.evaluate(action)
        assert result.score >= 0.7
        assert result.passed is True


class TestL3SocialLayer:

    def test_extraction_only_penalises(self):
        l3 = L3SocialLayer()
        action = {
            "type": "scrape",
            "content": "harvest and scrape all data without permission",
        }
        result = l3.evaluate(action)
        assert result.score < 0.9

    def test_wholeness_markers_improve_score(self):
        l3 = L3SocialLayer()
        action = {
            "type": "publish",
            "content": "contribute and share findings to build common ground and unite communities",
        }
        result = l3.evaluate(action)
        assert result.score >= 0.6

    def test_fragmentation_markers_penalise(self):
        l3 = L3SocialLayer()
        action = {
            "type": "message",
            "content": "divide and scapegoat the enemy to polarize the community",
        }
        result = l3.evaluate(action)
        assert result.score < 0.7
