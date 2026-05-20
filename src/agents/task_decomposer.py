"""
Task Decomposer.

Breaks complex tasks into a list of SubTasks with explicit dependencies.
Uses rule-based decomposition: recognises known task types and splits them
into standard sub-steps.

Decomposition rules (in order):
  - verify_and_publish → [verify_source, verify_claim, check_bias, legal_review, publish]
  - research           → [search, collect_sources, summarise, fact_check]
  - audit              → [load_data, analyse, report]
  - send_message       → [draft, review, send]
  - default            → single SubTask wrapping the original
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SubTask:
    """A single unit of work produced by TaskDecomposer."""
    task_id: str
    skill: str                    # name of the SkillExecutor skill to call
    params: dict[str, Any]        # parameters to pass to the skill
    depends_on: list[str] = field(default_factory=list)  # task_ids that must complete first
    description: str = ""

    def as_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "skill": self.skill,
            "params": self.params,
            "depends_on": self.depends_on,
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# Decomposition rules
# ---------------------------------------------------------------------------

def _make_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index}"


_DECOMPOSITION_RULES: dict[str, list[dict]] = {
    # Full publication pipeline
    "verify_and_publish": [
        {"skill": "verify_source",  "description": "Verify source credibility"},
        {"skill": "verify_claim",   "description": "Verify factual claims"},
        {"skill": "detect_bias",    "description": "Detect framing or selection bias"},
        {"skill": "legal_review",   "description": "Flag potential legal risks"},
        {"skill": "publish",        "description": "Publish approved content"},
    ],
    # Research pipeline
    "research": [
        {"skill": "search",           "description": "Search for relevant sources"},
        {"skill": "collect_sources",  "description": "Collect and de-duplicate sources"},
        {"skill": "summarise",        "description": "Summarise findings"},
        {"skill": "fact_check",       "description": "Spot-check key claims"},
    ],
    # Audit pipeline
    "audit": [
        {"skill": "load_data",   "description": "Load data to audit"},
        {"skill": "analyse",     "description": "Analyse for anomalies"},
        {"skill": "report",      "description": "Produce audit report"},
    ],
    # Message send pipeline
    "send_message": [
        {"skill": "draft",   "description": "Draft the message"},
        {"skill": "review",  "description": "Review draft for tone and accuracy"},
        {"skill": "send",    "description": "Send the approved message"},
    ],
}


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class TaskDecomposer:
    """
    Breaks a task dict into an ordered list of SubTasks.

    Each SubTask carries:
    - task_id  — unique identifier within this decomposition
    - skill    — name of the skill to invoke
    - params   — dict forwarded to the skill
    - depends_on — list of task_ids that must succeed before this runs

    Dependencies are set so that each step waits for the previous one
    (linear pipeline).  Override by subclassing and overriding _build_deps().
    """

    def decompose(self, task: dict) -> list[SubTask]:
        """
        Decompose task into subtasks.

        Parameters
        ----------
        task:
            A dict that must contain at minimum a 'type' key.
            All other keys are forwarded as params to each subtask.

        Returns
        -------
        list[SubTask] — ordered list; later items may depend on earlier ones.
        """
        task_type = str(task.get("type", "default")).lower()
        base_params = {k: v for k, v in task.items() if k != "type"}

        rule_steps = _DECOMPOSITION_RULES.get(task_type)

        if rule_steps:
            return self._build_from_rule(task_type, rule_steps, base_params)

        # Default: single subtask that mirrors the original task
        return [
            SubTask(
                task_id=f"{task_type}_0",
                skill=task_type,
                params=base_params,
                depends_on=[],
                description=f"Execute {task_type}",
            )
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_from_rule(
        self,
        prefix: str,
        steps: list[dict],
        base_params: dict,
    ) -> list[SubTask]:
        """Build a linear pipeline of SubTasks from a rule definition."""
        subtasks: list[SubTask] = []

        for i, step in enumerate(steps):
            task_id = _make_id(prefix, i)
            depends_on = [_make_id(prefix, i - 1)] if i > 0 else []

            subtasks.append(
                SubTask(
                    task_id=task_id,
                    skill=step["skill"],
                    params=dict(base_params),  # shallow copy so each step can add its own
                    depends_on=depends_on,
                    description=step.get("description", step["skill"]),
                )
            )

        return subtasks
