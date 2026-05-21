"""Task state machine for orchestration runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agent_orchestrator.observability import EventLog

TaskState = Literal[
    "draft",
    "clarified",
    "decomposed",
    "dispatched",
    "running",
    "blocked",
    "rescue",
    "review",
    "merged",
    "accepted",
]


ALLOWED_TRANSITIONS: dict[TaskState | None, set[TaskState]] = {
    None: {"draft"},
    "draft": {"clarified"},
    "clarified": {"decomposed"},
    "decomposed": {"dispatched"},
    "dispatched": {"running"},
    "running": {"blocked", "rescue", "review"},
    "rescue": {"running", "review", "blocked"},
    "review": {"running", "merged", "accepted", "blocked"},
    "merged": {"accepted", "blocked"},
    "blocked": {"rescue", "decomposed"},
    "accepted": set(),
}


@dataclass(slots=True)
class StateMachine:
    event_log: EventLog
    current: TaskState | None = None

    def transition(self, next_state: TaskState) -> None:
        allowed = ALLOWED_TRANSITIONS[self.current]
        if next_state not in allowed:
            raise ValueError(f"Invalid state transition: {self.current} -> {next_state}")
        previous = self.current
        self.current = next_state
        self.event_log.record("state_transition", previous=previous, current=next_state)
