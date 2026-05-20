"""
Skill Executor.

Registry of named skills (callables).  All executions are logged to the
audit trail.  A skill is any callable that accepts a single dict of params
and returns any value.

Usage::

    audit = AuditTrail()
    executor = SkillExecutor(audit_trail=audit)

    # Register a skill
    executor.register("greet", lambda params: f"Hello, {params.get('name', 'world')}!")

    # Execute
    result = executor.execute("greet", {"name": "Martien"})
    print(result.output)  # Hello, Martien!
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..policy.audit_trail import AuditTrail


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SkillResult:
    """Result of a skill execution."""
    skill_name: str
    params: dict
    output: Any
    success: bool
    error: str | None = None

    def as_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "params": self.params,
            "output": self.output,
            "success": self.success,
            "error": self.error,
        }


class SkillNotFoundError(Exception):
    """Raised when an unregistered skill name is requested."""


class SkillExecutionError(Exception):
    """Raised when a skill raises an unexpected exception."""


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class SkillExecutor:
    """
    Registry and runner for named skills.

    Each execution is automatically logged to the provided AuditTrail.
    If no AuditTrail is supplied, a default one (audit.jsonl) is created.
    """

    def __init__(self, audit_trail: AuditTrail | None = None) -> None:
        self._registry: dict[str, Callable[[dict], Any]] = {}
        self._audit = audit_trail or AuditTrail()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, fn: Callable[[dict], Any]) -> None:
        """
        Register a skill by name.

        Parameters
        ----------
        name:
            Skill identifier used in execute() calls.
        fn:
            Any callable that accepts a single dict and returns any value.
            The callable is responsible for its own error handling; any
            exception it raises will be caught and surfaced as a SkillResult
            with success=False.
        """
        if not callable(fn):
            raise TypeError(f"Skill '{name}' must be callable, got {type(fn).__name__}")
        self._registry[name] = fn

    def unregister(self, name: str) -> None:
        """Remove a skill from the registry."""
        self._registry.pop(name, None)

    @property
    def registered_skills(self) -> list[str]:
        return list(self._registry.keys())

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, skill_name: str, params: dict) -> SkillResult:
        """
        Execute a registered skill.

        Parameters
        ----------
        skill_name:
            Name of a previously registered skill.
        params:
            Parameters forwarded to the skill callable.

        Returns
        -------
        SkillResult — always returns a SkillResult (never raises on skill error).

        Raises
        ------
        SkillNotFoundError — if skill_name is not registered.
        """
        if skill_name not in self._registry:
            raise SkillNotFoundError(
                f"Skill '{skill_name}' is not registered. "
                f"Available skills: {self.registered_skills}"
            )

        fn = self._registry[skill_name]

        try:
            output = fn(params)
            result = SkillResult(
                skill_name=skill_name,
                params=params,
                output=output,
                success=True,
            )
        except Exception as exc:
            result = SkillResult(
                skill_name=skill_name,
                params=params,
                output=None,
                success=False,
                error=str(exc),
            )

        # Always log — success or failure
        self._audit.log_skill_execution(
            skill_name=skill_name,
            params=params,
            result=result.output,
            success=result.success,
        )

        return result
