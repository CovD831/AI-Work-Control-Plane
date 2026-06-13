"""Task-intake models for the coding-agent entry skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from agent_orchestrator.tasks import RiskLevel


class TaskKind(str, Enum):
    DIRECT_FIX = "direct_fix"
    INVESTIGATION = "investigation"
    MIGRATION = "migration"
    DOCS = "docs"
    QUESTION_ONLY = "question_only"
    GENERAL_CODING = "general_coding"


class ClarifyPolicy(str, Enum):
    SKIP = "skip"
    LIGHT = "light"
    DEEP = "deep"


class ExecutionMode(str, Enum):
    LEGACY = "legacy"
    CODING_AGENT = "coding_agent"
    NO_EXECUTION = "no_execution"


AmbiguityLevel = RiskLevel


@dataclass(frozen=True, slots=True)
class TaskRouterResult:
    task_kind: TaskKind
    clarify_policy: ClarifyPolicy
    execution_mode: ExecutionMode
    ambiguity_level: AmbiguityLevel
    risk_level: RiskLevel
    scope_confidence: RiskLevel
    needs_repo_context: bool
    requires_human_confirmation: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "task_kind": self.task_kind.value,
            "clarify_policy": self.clarify_policy.value,
            "execution_mode": self.execution_mode.value,
            "ambiguity_level": self.ambiguity_level,
            "risk_level": self.risk_level,
            "scope_confidence": self.scope_confidence,
            "needs_repo_context": self.needs_repo_context,
            "requires_human_confirmation": self.requires_human_confirmation,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class IntentIntakeResult:
    raw_requirement: str
    normalized_requirement: str
    clarify_policy: ClarifyPolicy
    task_kind: TaskKind
    execution_mode: ExecutionMode
    risk_level: RiskLevel
    scope_confidence: RiskLevel
    requires_human_confirmation: bool
    reasons: list[str] = field(default_factory=list)
    task_contract: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "raw_requirement": self.raw_requirement,
            "normalized_requirement": self.normalized_requirement,
            "clarify_policy": self.clarify_policy.value,
            "task_kind": self.task_kind.value,
            "execution_mode": self.execution_mode.value,
            "risk_level": self.risk_level,
            "scope_confidence": self.scope_confidence,
            "requires_human_confirmation": self.requires_human_confirmation,
            "reasons": list(self.reasons),
            "task_contract": dict(self.task_contract) if isinstance(self.task_contract, dict) else None,
        }
