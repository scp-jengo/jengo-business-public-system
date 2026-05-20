"""
Approval Workflow.

Manages approval requests for actions that require human (or external) review
before execution.  All requests are stored in-memory by default; the storage
backend can be swapped out by subclassing.

Lifecycle:
  request_approval() → ApprovalRequest (status=pending)
  approve() or reject() → updates status
  check_status() → returns current ApprovalStatus
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------

class ApprovalStatus(str, Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED  = "expired"


@dataclass
class ApprovalRequest:
    """An approval request created by ApprovalWorkflow.request_approval()."""
    request_id: str
    task: dict
    reason: str
    status: ApprovalStatus
    created_at: str
    updated_at: str
    reviewer: str | None = None
    comment: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "task": self.task,
            "reason": self.reason,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "reviewer": self.reviewer,
            "comment": self.comment,
            "metadata": self.metadata,
        }


class ApprovalNotFoundError(Exception):
    """Raised when an approval request ID is not found."""


class ApprovalAlreadyDecidedError(Exception):
    """Raised when an approval/rejection is attempted on a decided request."""


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ApprovalWorkflow:
    """
    In-memory approval workflow.

    Thread safety: not guaranteed for concurrent access.
    For production use, replace _store with a database-backed implementation.
    """

    def __init__(self) -> None:
        self._store: dict[str, ApprovalRequest] = {}

    # ------------------------------------------------------------------
    # Creating requests
    # ------------------------------------------------------------------

    def request_approval(self, task: dict, reason: str) -> ApprovalRequest:
        """
        Create a new approval request.

        Parameters
        ----------
        task:
            The task dict that needs approval.
        reason:
            Human-readable explanation of why approval is needed.

        Returns
        -------
        ApprovalRequest with status=pending.
        """
        now = _utcnow()
        request_id = str(uuid.uuid4())

        request = ApprovalRequest(
            request_id=request_id,
            task=task,
            reason=reason,
            status=ApprovalStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        self._store[request_id] = request
        return request

    # ------------------------------------------------------------------
    # Querying status
    # ------------------------------------------------------------------

    def check_status(self, request_id: str) -> ApprovalStatus:
        """
        Return the current status of an approval request.

        Raises
        ------
        ApprovalNotFoundError — if the request_id is not found.
        """
        request = self._get(request_id)
        return request.status

    def get_request(self, request_id: str) -> ApprovalRequest:
        """Return the full ApprovalRequest object."""
        return self._get(request_id)

    def list_pending(self) -> list[ApprovalRequest]:
        """Return all requests currently in pending state."""
        return [r for r in self._store.values() if r.status == ApprovalStatus.PENDING]

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    def approve(self, request_id: str, reviewer: str, comment: str = "") -> ApprovalRequest:
        """
        Approve a pending request.

        Parameters
        ----------
        request_id:
            The UUID of the approval request.
        reviewer:
            Identifier (name/email/user-id) of the reviewer.
        comment:
            Optional review comment.

        Returns
        -------
        Updated ApprovalRequest.

        Raises
        ------
        ApprovalNotFoundError          — unknown request_id.
        ApprovalAlreadyDecidedError    — request already approved or rejected.
        """
        return self._decide(request_id, ApprovalStatus.APPROVED, reviewer, comment)

    def reject(self, request_id: str, reviewer: str, comment: str = "") -> ApprovalRequest:
        """
        Reject a pending request.

        Raises same errors as approve().
        """
        return self._decide(request_id, ApprovalStatus.REJECTED, reviewer, comment)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, request_id: str) -> ApprovalRequest:
        if request_id not in self._store:
            raise ApprovalNotFoundError(f"Approval request '{request_id}' not found.")
        return self._store[request_id]

    def _decide(
        self,
        request_id: str,
        new_status: ApprovalStatus,
        reviewer: str,
        comment: str,
    ) -> ApprovalRequest:
        request = self._get(request_id)
        if request.status != ApprovalStatus.PENDING:
            raise ApprovalAlreadyDecidedError(
                f"Request '{request_id}' is already in state '{request.status.value}'. "
                "Cannot change a decided request."
            )

        request.status = new_status
        request.reviewer = reviewer
        request.comment = comment
        request.updated_at = _utcnow()
        return request


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()
