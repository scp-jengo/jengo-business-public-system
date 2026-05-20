"""
Audit Trail — Append-only decision log.

All decisions and approval outcomes are written as JSON Lines (one JSON object
per line) to a log file.  The log is append-only: existing entries are never
modified or deleted.

Format::

    {"event": "decision", "timestamp": "...", "action": {...}, "result": {...}, "reasoning": "..."}
    {"event": "approval", "timestamp": "...", "request_id": "...", "decision": "approved", "reviewer": "..."}
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditTrail:
    """
    Append-only audit log in JSON Lines format.

    Parameters
    ----------
    log_path:
        Path to the .jsonl log file.  Parent directories are created
        automatically.  Defaults to 'audit.jsonl' in the current directory.
    """

    def __init__(self, log_path: str = "audit.jsonl") -> None:
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_decision(self, action: dict, result: dict, reasoning: str) -> None:
        """
        Log a constitutional AI or policy decision.

        Parameters
        ----------
        action:
            The action dict that was evaluated.
        result:
            The result dict (from ThreeLayerFramework or PolicyEngine).
        reasoning:
            Human-readable reasoning string.
        """
        entry: dict[str, Any] = {
            "event": "decision",
            "timestamp": _utcnow(),
            "action": self._sanitize(action),
            "result": self._sanitize(result),
            "reasoning": reasoning,
        }
        self._append(entry)

    def log_approval(self, request_id: str, decision: str, reviewer: str) -> None:
        """
        Log an approval workflow decision.

        Parameters
        ----------
        request_id:
            UUID of the approval request.
        decision:
            'approved' | 'rejected' | 'pending' | 'expired'
        reviewer:
            Identifier of the reviewer.
        """
        entry: dict[str, Any] = {
            "event": "approval",
            "timestamp": _utcnow(),
            "request_id": request_id,
            "decision": decision,
            "reviewer": reviewer,
        }
        self._append(entry)

    def log_skill_execution(
        self,
        skill_name: str,
        params: dict,
        result: Any,
        success: bool,
    ) -> None:
        """Log a skill execution (called by SkillExecutor)."""
        entry: dict[str, Any] = {
            "event": "skill_execution",
            "timestamp": _utcnow(),
            "skill_name": skill_name,
            "params": self._sanitize(params),
            "success": success,
            "result_type": type(result).__name__,
        }
        self._append(entry)

    def read_all(self) -> list[dict]:
        """
        Read all entries from the audit log.  Returns an empty list if the
        log file does not exist yet.
        """
        if not self._log_path.exists():
            return []

        entries = []
        with open(self._log_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass  # skip corrupted lines
        return entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append(self, entry: dict) -> None:
        """Write one JSON Lines entry (append, never overwrite)."""
        with open(self._log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    @staticmethod
    def _sanitize(obj: Any, max_depth: int = 5) -> Any:
        """
        Recursively sanitize an object for JSON serialization.
        Strips non-serializable values; redacts known secret keys.
        """
        _SECRET_KEYS = frozenset({
            "password", "token", "secret", "api_key", "private_key",
            "credential", "auth", "bearer",
        })

        if max_depth <= 0:
            return "<truncated>"

        if isinstance(obj, dict):
            sanitized = {}
            for k, v in obj.items():
                if any(s in str(k).lower() for s in _SECRET_KEYS):
                    sanitized[k] = "<redacted>"
                else:
                    sanitized[k] = AuditTrail._sanitize(v, max_depth - 1)
            return sanitized

        if isinstance(obj, (list, tuple)):
            return [AuditTrail._sanitize(item, max_depth - 1) for item in obj]

        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj

        # Fallback: convert to string
        return str(obj)
