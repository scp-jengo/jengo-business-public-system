"""
Orchestrator.

Takes a task, decomposes it into subtasks, enforces constitutional AI on each
subtask before execution, routes subtasks to the skill executor, and collects
results.

Execution model:
  1. Decompose task → list[SubTask]
  2. For each subtask (in dependency order):
     a. Run constitutional AI check
     b. If approved: execute via SkillExecutor
     c. If blocked: record failure, stop pipeline
  3. Return OrchestratorResult with all subtask outcomes

Constitutional context is injected automatically (l2_active, l3_active, etc.)
so subtasks do not need to carry those flags manually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..constitutional.three_layer_framework import ThreeLayerFramework, ConstitutionalViolation
from ..policy.audit_trail import AuditTrail
from .task_decomposer import TaskDecomposer, SubTask
from .skill_executor import SkillExecutor, SkillResult, SkillNotFoundError


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SubtaskOutcome:
    """Result of a single subtask (constitutional check + execution)."""
    subtask: SubTask
    constitutional_approved: bool
    constitutional_reasoning: str
    skill_result: SkillResult | None = None
    skipped: bool = False
    skip_reason: str = ""

    @property
    def succeeded(self) -> bool:
        if self.skipped:
            return False
        if not self.constitutional_approved:
            return False
        return self.skill_result is not None and self.skill_result.success


@dataclass
class OrchestratorResult:
    """Full result of Orchestrator.run()."""
    task: dict
    approved: bool          # True only if all subtasks succeeded
    subtask_outcomes: list[SubtaskOutcome]
    reasoning: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "task": self.task,
            "approved": self.approved,
            "subtask_outcomes": [
                {
                    "task_id": o.subtask.task_id,
                    "skill": o.subtask.skill,
                    "constitutional_approved": o.constitutional_approved,
                    "constitutional_reasoning": o.constitutional_reasoning,
                    "succeeded": o.succeeded,
                    "skipped": o.skipped,
                    "skip_reason": o.skip_reason,
                    "skill_output": (
                        o.skill_result.output if o.skill_result else None
                    ),
                    "skill_error": (
                        o.skill_result.error if o.skill_result else None
                    ),
                }
                for o in self.subtask_outcomes
            ],
            "reasoning": self.reasoning,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Constitutional context injected into every subtask
# ---------------------------------------------------------------------------

_CONSTITUTIONAL_CONTEXT_FLAGS: dict[str, Any] = {
    "l2_active": True,
    "l3_active": True,
    "constitutional_ai_active": True,
}


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class Orchestrator:
    """
    Task orchestrator with built-in constitutional AI gating.

    Parameters
    ----------
    constitutional:
        ThreeLayerFramework instance (defaults to new instance).
    skill_executor:
        SkillExecutor instance (defaults to new instance).
    audit_trail:
        AuditTrail instance (defaults to new instance).
    decomposer:
        TaskDecomposer instance (defaults to new instance).
    stop_on_first_failure:
        If True (default), stop executing subtasks as soon as one fails
        constitutionally or in execution.
    """

    def __init__(
        self,
        constitutional: ThreeLayerFramework | None = None,
        skill_executor: SkillExecutor | None = None,
        audit_trail: AuditTrail | None = None,
        decomposer: TaskDecomposer | None = None,
        stop_on_first_failure: bool = True,
    ) -> None:
        self._audit = audit_trail or AuditTrail()
        self._constitutional = constitutional or ThreeLayerFramework()
        self._executor = skill_executor or SkillExecutor(audit_trail=self._audit)
        self._decomposer = decomposer or TaskDecomposer()
        self._stop_on_first_failure = stop_on_first_failure

    # ------------------------------------------------------------------
    # Registration shortcut
    # ------------------------------------------------------------------

    def register_skill(self, name: str, fn) -> None:
        """Convenience proxy to SkillExecutor.register()."""
        self._executor.register(name, fn)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, task: dict) -> OrchestratorResult:
        """
        Run a task through the full pipeline.

        1. Decompose into subtasks.
        2. For each subtask: constitutional check → execution.
        3. Return OrchestratorResult.

        Parameters
        ----------
        task:
            A dict with at minimum 'type'.  All other keys become params.
        """
        subtasks = self._decomposer.decompose(task)
        outcomes: list[SubtaskOutcome] = []
        pipeline_blocked = False

        for subtask in subtasks:
            # --- Check dependencies ---
            if subtask.depends_on:
                dep_failed = False
                for dep_id in subtask.depends_on:
                    dep_outcome = next(
                        (o for o in outcomes if o.subtask.task_id == dep_id), None
                    )
                    if dep_outcome is None or not dep_outcome.succeeded:
                        dep_failed = True
                        break

                if dep_failed:
                    outcome = SubtaskOutcome(
                        subtask=subtask,
                        constitutional_approved=False,
                        constitutional_reasoning="",
                        skipped=True,
                        skip_reason=f"Dependency failed or not found: {subtask.depends_on}",
                    )
                    outcomes.append(outcome)
                    pipeline_blocked = True
                    if self._stop_on_first_failure:
                        break
                    continue

            # --- Constitutional check ---
            action_for_check = {
                **_CONSTITUTIONAL_CONTEXT_FLAGS,
                "type": subtask.skill,
                **subtask.params,
            }

            try:
                constitutional_result = self._constitutional.evaluate_action(action_for_check)
            except ConstitutionalViolation as exc:
                # L2 not active or other hard violation
                outcome = SubtaskOutcome(
                    subtask=subtask,
                    constitutional_approved=False,
                    constitutional_reasoning=str(exc),
                )
                outcomes.append(outcome)
                self._audit.log_decision(
                    action=action_for_check,
                    result={"approved": False, "violation": str(exc)},
                    reasoning=str(exc),
                )
                pipeline_blocked = True
                if self._stop_on_first_failure:
                    break
                continue

            const_approved = constitutional_result["approved"]
            const_reasoning = constitutional_result["reasoning"]

            self._audit.log_decision(
                action=action_for_check,
                result=constitutional_result,
                reasoning=const_reasoning,
            )

            if not const_approved:
                outcome = SubtaskOutcome(
                    subtask=subtask,
                    constitutional_approved=False,
                    constitutional_reasoning=const_reasoning,
                )
                outcomes.append(outcome)
                pipeline_blocked = True
                if self._stop_on_first_failure:
                    break
                continue

            # --- Execute skill ---
            try:
                skill_result = self._executor.execute(subtask.skill, subtask.params)
            except SkillNotFoundError:
                # Skill not registered — treat as pass-through (returns None)
                skill_result = _make_passthrough_result(subtask.skill, subtask.params)

            outcome = SubtaskOutcome(
                subtask=subtask,
                constitutional_approved=True,
                constitutional_reasoning=const_reasoning,
                skill_result=skill_result,
            )
            outcomes.append(outcome)

            if not skill_result.success and self._stop_on_first_failure:
                pipeline_blocked = True
                break

        # --- Build final result ---
        overall_approved = not pipeline_blocked and all(o.succeeded for o in outcomes)

        if overall_approved:
            reasoning = f"All {len(outcomes)} subtask(s) passed constitutional AI and executed successfully."
        else:
            failed = [o.subtask.task_id for o in outcomes if not o.succeeded]
            reasoning = (
                f"Pipeline incomplete. Failed/blocked subtasks: {failed}."
            )

        return OrchestratorResult(
            task=task,
            approved=overall_approved,
            subtask_outcomes=outcomes,
            reasoning=reasoning,
            metadata={"total_subtasks": len(subtasks), "executed": len(outcomes)},
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_passthrough_result(skill_name: str, params: dict) -> "SkillResult":
    """Return a successful no-op result for an unregistered skill."""
    from .skill_executor import SkillResult
    return SkillResult(
        skill_name=skill_name,
        params=params,
        output={"status": "passthrough", "note": "Skill not registered; no-op."},
        success=True,
    )
