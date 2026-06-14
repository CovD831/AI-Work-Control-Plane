"""Strategy-layer models for coding-agent execution planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from agent_orchestrator.tasks import TaskContract, WorkUnit


class ExecutionStrategy(str, Enum):
    DIRECT_EDIT = "direct_edit"
    EXPLORE_THEN_EDIT = "explore_then_edit"
    INVESTIGATION_ONLY = "investigation_only"
    MIGRATION_GUARDED = "migration_guarded"
    DOCS_SYNC = "docs_sync"
    NEED_HUMAN_CONFIRMATION = "need_human_confirmation"
    CLARIFY_THEN_EDIT = "clarify_then_edit"
    EXTERNAL_HANDOFF = "external_handoff"
    GOVERNED_FALLBACK = "governed_fallback"


@dataclass(frozen=True, slots=True)
class StrategyCandidate:
    strategy: ExecutionStrategy
    score: int
    selected: bool
    reasons: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy.value,
            "score": self.score,
            "selected": self.selected,
            "reasons": list(self.reasons),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    strategy: ExecutionStrategy
    contract: TaskContract
    work_units: list[WorkUnit]
    reasons: list[str] = field(default_factory=list)
    candidates: list[StrategyCandidate] = field(default_factory=list)
    compatibility_metadata: dict[str, object] = field(default_factory=dict)
    planner_family: str = "compatibility"
    planner_actions: list[str] = field(default_factory=list)
    decision_evidence: dict[str, object] = field(default_factory=dict)
    operating_boundary: str = "native_preferred"
    selection_reason: str = ""
    handoff_reason_code: str | None = None
    fallback_reason_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy.value,
            "contract": self.contract.to_dict(),
            "work_units": [work_unit.to_dict() for work_unit in self.work_units],
            "reasons": list(self.reasons),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "compatibility_metadata": dict(self.compatibility_metadata),
            "planner_family": self.planner_family,
            "planner_actions": list(self.planner_actions),
            "decision_evidence": dict(self.decision_evidence),
            "operating_boundary": self.operating_boundary,
            "selection_reason": self.selection_reason,
            "handoff_reason_code": self.handoff_reason_code,
            "fallback_reason_code": self.fallback_reason_code,
        }

    def summary(self) -> dict[str, object]:
        return {
            "selected_execution_strategy": self.strategy.value,
            "reasons": list(self.reasons),
            "candidate_count": len(self.candidates),
            "compatibility_metadata": dict(self.compatibility_metadata),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "planner_family": self.planner_family,
            "planner_actions": list(self.planner_actions),
            "decision_evidence": dict(self.decision_evidence),
            "operating_boundary": self.operating_boundary,
            "selection_reason": self.selection_reason,
            "handoff_reason_code": self.handoff_reason_code,
            "fallback_reason_code": self.fallback_reason_code,
        }
