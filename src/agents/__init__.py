"""
Agent Orchestration — task decomposition, skill execution, orchestration.

Public surface:
  Orchestrator     — runs tasks through constitutional AI then skills
  TaskDecomposer   — breaks tasks into subtasks with dependencies
  SkillExecutor    — registry + runner for named skill callables
  OrchestratorResult, SubtaskOutcome  — result data classes
  SubTask          — individual subtask data class
  SkillResult      — result of a single skill execution
"""

from .orchestrator import Orchestrator, OrchestratorResult, SubtaskOutcome
from .task_decomposer import TaskDecomposer, SubTask
from .skill_executor import SkillExecutor, SkillResult, SkillNotFoundError

__all__ = [
    "Orchestrator",
    "OrchestratorResult",
    "SubtaskOutcome",
    "TaskDecomposer",
    "SubTask",
    "SkillExecutor",
    "SkillResult",
    "SkillNotFoundError",
]
