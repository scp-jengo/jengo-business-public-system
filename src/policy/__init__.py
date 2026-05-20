"""
Policy Engine — YAML-based policy evaluation, approval workflows, audit trail.

Public surface:
  PolicyEngine      — loads YAML policy files and checks actions
  Policy            — parsed policy data class
  PolicyResult      — result of PolicyEngine.check_action()
  ApprovalWorkflow  — create/approve/reject approval requests
  ApprovalRequest   — individual approval request
  ApprovalStatus    — enum: pending / approved / rejected / expired
  AuditTrail        — append-only JSON Lines decision log
"""

from .yaml_parser import parse_policy_file, Policy, PolicyRule
from .policy_engine import PolicyEngine, PolicyResult
from .approval_workflow import (
    ApprovalWorkflow,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalNotFoundError,
    ApprovalAlreadyDecidedError,
)
from .audit_trail import AuditTrail

__all__ = [
    "PolicyEngine",
    "Policy",
    "PolicyRule",
    "PolicyResult",
    "parse_policy_file",
    "ApprovalWorkflow",
    "ApprovalRequest",
    "ApprovalStatus",
    "ApprovalNotFoundError",
    "ApprovalAlreadyDecidedError",
    "AuditTrail",
]
