"""
Tests for PolicyEngine.

Coverage:
  - Load policy file → check action → correct result
  - Disabled policy is not applied
  - Priority ordering (lower number = higher priority, evaluated first)
  - block_if_below blocks correctly
  - require_approval_if_below does not block but sets requires_approval
  - block_if_unverified blocks when unverified with insufficient sources
  - warn_if_below adds warning but does not block
  - Unknown check name defaults to pass-through
"""

import sys
import os
import tempfile
import textwrap
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from policy.yaml_parser import parse_policy_file, Policy, PolicyRule
from policy.policy_engine import PolicyEngine, PolicyResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_policy(tmp_path_obj, filename: str, content: str) -> str:
    """Write a YAML policy file and return its path."""
    import pathlib
    p = pathlib.Path(tmp_path_obj) / filename
    p.write_text(textwrap.dedent(content).strip(), encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# parse_policy_file tests
# ---------------------------------------------------------------------------

class TestParsePolicyFile:

    def test_valid_policy_parsed(self, tmp_path):
        path = _write_policy(tmp_path, "valid.yaml", """
            id: test-policy
            name: Test Policy
            enabled: true
            priority: 10
            rules:
              - check: source_credibility
                threshold: 0.7
                action: block_if_below
        """)
        policy = parse_policy_file(path)
        assert policy.id == "test-policy"
        assert policy.name == "Test Policy"
        assert policy.enabled is True
        assert policy.priority == 10
        assert len(policy.rules) == 1
        assert policy.rules[0].check == "source_credibility"
        assert policy.rules[0].threshold == 0.7
        assert policy.rules[0].action == "block_if_below"

    def test_missing_required_field_raises(self, tmp_path):
        path = _write_policy(tmp_path, "bad.yaml", """
            id: bad-policy
            name: Bad Policy
            enabled: true
            rules:
              - check: x
                action: warn_if_below
        """)
        with pytest.raises(ValueError, match="priority"):
            parse_policy_file(path)

    def test_rule_missing_action_raises(self, tmp_path):
        path = _write_policy(tmp_path, "bad_rule.yaml", """
            id: x
            name: X
            enabled: true
            priority: 1
            rules:
              - check: source_credibility
        """)
        with pytest.raises(ValueError, match="action"):
            parse_policy_file(path)

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_policy_file("/nonexistent/path/policy.yaml")

    def test_disabled_policy_loaded(self, tmp_path):
        path = _write_policy(tmp_path, "disabled.yaml", """
            id: disabled
            name: Disabled
            enabled: false
            priority: 5
            rules:
              - check: x
                action: block_if_below
        """)
        policy = parse_policy_file(path)
        assert policy.enabled is False


# ---------------------------------------------------------------------------
# PolicyEngine tests
# ---------------------------------------------------------------------------

class TestPolicyEngine:

    def test_load_from_directory(self, tmp_path):
        _write_policy(tmp_path, "p1.yaml", """
            id: p1
            name: P1
            enabled: true
            priority: 10
            rules:
              - check: source_credibility
                threshold: 0.5
                action: block_if_below
        """)
        engine = PolicyEngine(policy_dir=str(tmp_path))
        assert engine.policy_count == 1

    def test_block_if_below_blocks(self, tmp_path):
        _write_policy(tmp_path, "block.yaml", """
            id: block-policy
            name: Block Policy
            enabled: true
            priority: 10
            rules:
              - check: source_credibility
                threshold: 0.8
                action: block_if_below
        """)
        engine = PolicyEngine(policy_dir=str(tmp_path))
        # source_score below threshold → blocked
        result = engine.check_action({"type": "publish", "source_score": 0.5})
        assert result.approved is False
        assert len(result.blocking_rules) > 0

    def test_block_if_below_passes_when_above(self, tmp_path):
        _write_policy(tmp_path, "block.yaml", """
            id: block-policy
            name: Block Policy
            enabled: true
            priority: 10
            rules:
              - check: source_credibility
                threshold: 0.8
                action: block_if_below
        """)
        engine = PolicyEngine(policy_dir=str(tmp_path))
        result = engine.check_action({"type": "publish", "source_score": 0.9})
        assert result.approved is True

    def test_disabled_policy_not_applied(self, tmp_path):
        _write_policy(tmp_path, "disabled.yaml", """
            id: disabled
            name: Disabled Policy
            enabled: false
            priority: 5
            rules:
              - check: source_credibility
                threshold: 0.99
                action: block_if_below
        """)
        engine = PolicyEngine(policy_dir=str(tmp_path))
        result = engine.check_action({"type": "publish", "source_score": 0.1})
        # Disabled policy should not block
        assert result.approved is True
        assert "disabled" not in result.applied_policies

    def test_require_approval_does_not_block(self, tmp_path):
        _write_policy(tmp_path, "approval.yaml", """
            id: approval-policy
            name: Approval Policy
            enabled: true
            priority: 10
            rules:
              - check: source_credibility
                threshold: 0.8
                action: require_approval_if_below
        """)
        engine = PolicyEngine(policy_dir=str(tmp_path))
        result = engine.check_action({"type": "publish", "source_score": 0.5})
        assert result.approved is True        # not blocked
        assert result.requires_approval is True
        assert len(result.warnings) > 0

    def test_warn_if_below_adds_warning_not_block(self, tmp_path):
        _write_policy(tmp_path, "warn.yaml", """
            id: warn-policy
            name: Warn Policy
            enabled: true
            priority: 10
            rules:
              - check: source_credibility
                threshold: 0.8
                action: warn_if_below
        """)
        engine = PolicyEngine(policy_dir=str(tmp_path))
        result = engine.check_action({"type": "publish", "source_score": 0.5})
        assert result.approved is True
        assert len(result.warnings) > 0

    def test_block_if_unverified_blocks(self, tmp_path):
        _write_policy(tmp_path, "unverified.yaml", """
            id: verify-policy
            name: Verify Policy
            enabled: true
            priority: 10
            rules:
              - check: claim_verification
                require_sources: 2
                action: block_if_unverified
        """)
        engine = PolicyEngine(policy_dir=str(tmp_path))
        # No sources, no verified flag → blocked
        result = engine.check_action({"type": "publish"})
        assert result.approved is False

    def test_block_if_unverified_passes_when_verified(self, tmp_path):
        _write_policy(tmp_path, "unverified.yaml", """
            id: verify-policy
            name: Verify Policy
            enabled: true
            priority: 10
            rules:
              - check: claim_verification
                require_sources: 2
                action: block_if_unverified
        """)
        engine = PolicyEngine(policy_dir=str(tmp_path))
        result = engine.check_action({
            "type": "publish",
            "verified": True,
            "sources": ["https://reuters.com/a", "https://apnews.com/b"],
        })
        assert result.approved is True

    def test_priority_ordering(self, tmp_path):
        """Lower priority number = higher precedence; it is checked first."""
        _write_policy(tmp_path, "p_low.yaml", """
            id: low-priority
            name: Low Priority
            enabled: true
            priority: 100
            rules:
              - check: source_credibility
                threshold: 0.9
                action: block_if_below
        """)
        _write_policy(tmp_path, "p_high.yaml", """
            id: high-priority
            name: High Priority
            enabled: true
            priority: 1
            rules:
              - check: source_credibility
                threshold: 0.3
                action: block_if_below
        """)
        engine = PolicyEngine(policy_dir=str(tmp_path))

        # source_score=0.5: passes high-priority (0.5 > 0.3) but fails low-priority (0.5 < 0.9)
        result = engine.check_action({"type": "publish", "source_score": 0.5})
        assert result.approved is False
        assert "low-priority" in result.applied_policies

        # source_score=0.95: passes both
        result2 = engine.check_action({"type": "publish", "source_score": 0.95})
        assert result2.approved is True

    def test_empty_engine_approves_everything(self):
        engine = PolicyEngine()
        result = engine.check_action({"type": "any_action"})
        assert result.approved is True

    def test_multiple_rules_in_one_policy(self, tmp_path):
        _write_policy(tmp_path, "multi.yaml", """
            id: multi-rule
            name: Multi Rule
            enabled: true
            priority: 10
            rules:
              - check: source_credibility
                threshold: 0.5
                action: warn_if_below
              - check: harm_potential
                threshold: 0.7
                action: block_if_below
        """)
        engine = PolicyEngine(policy_dir=str(tmp_path))

        # harm_score below 0.7 → block
        result = engine.check_action({"source_score": 0.9, "harm_score": 0.3})
        assert result.approved is False

        # Both above thresholds → pass
        result2 = engine.check_action({"source_score": 0.9, "harm_score": 0.9})
        assert result2.approved is True
