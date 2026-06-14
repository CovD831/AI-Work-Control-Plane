"""Session-layer models for the coding-agent architecture."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


SessionStatus = str
TurnStatus = str
ResumeKind = str


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


@dataclass(frozen=True, slots=True)
class AgentSession:
    session_id: str
    status: SessionStatus
    created_at: str
    updated_at: str
    current_turn_id: str | None = None
    turn_ids: list[str] = field(default_factory=list)
    origin: str = "cli_direct"
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_turn_id": self.current_turn_id,
            "turn_ids": list(self.turn_ids),
            "origin": self.origin,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "AgentSession":
        return cls(
            session_id=str(data["session_id"]),
            status=str(data.get("status", "active")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            current_turn_id=str(data["current_turn_id"]) if data.get("current_turn_id") else None,
            turn_ids=[str(item) for item in data.get("turn_ids", [])],
            origin=str(data.get("origin", "cli_direct")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class SessionTurn:
    turn_id: str
    session_id: str
    requirement: str
    status: TurnStatus
    route: dict[str, object]
    clarify_summary: dict[str, object]
    strategy_summary: dict[str, object]
    linked_run_id: str | None
    resume_from_turn_id: str | None
    context_snapshot_id: str | None
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "requirement": self.requirement,
            "status": self.status,
            "route": dict(self.route),
            "clarify_summary": dict(self.clarify_summary),
            "strategy_summary": dict(self.strategy_summary),
            "linked_run_id": self.linked_run_id,
            "resume_from_turn_id": self.resume_from_turn_id,
            "context_snapshot_id": self.context_snapshot_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SessionTurn":
        return cls(
            turn_id=str(data["turn_id"]),
            session_id=str(data["session_id"]),
            requirement=str(data.get("requirement", "")),
            status=str(data.get("status", "prepared")),
            route=dict(data.get("route", {})),
            clarify_summary=dict(data.get("clarify_summary", {})),
            strategy_summary=dict(data.get("strategy_summary", {})),
            linked_run_id=str(data["linked_run_id"]) if data.get("linked_run_id") else None,
            resume_from_turn_id=str(data["resume_from_turn_id"]) if data.get("resume_from_turn_id") else None,
            context_snapshot_id=str(data["context_snapshot_id"]) if data.get("context_snapshot_id") else None,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    snapshot_id: str
    session_id: str
    turn_id: str
    task_contract: dict[str, object]
    selected_execution_strategy: str
    planner_family: str
    compatibility_metadata: dict[str, object]
    resume_kind: ResumeKind
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "task_contract": dict(self.task_contract),
            "selected_execution_strategy": self.selected_execution_strategy,
            "planner_family": self.planner_family,
            "compatibility_metadata": dict(self.compatibility_metadata),
            "resume_kind": self.resume_kind,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ContextSnapshot":
        return cls(
            snapshot_id=str(data["snapshot_id"]),
            session_id=str(data["session_id"]),
            turn_id=str(data["turn_id"]),
            task_contract=dict(data.get("task_contract", {})),
            selected_execution_strategy=str(data.get("selected_execution_strategy", "unknown")),
            planner_family=str(data.get("planner_family", "compatibility")),
            compatibility_metadata=dict(data.get("compatibility_metadata", {})),
            resume_kind=str(data.get("resume_kind", "fresh")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ExecutionActivity:
    activity_id: str
    session_id: str
    turn_id: str
    runtime_name: str
    linked_run_id: str | None
    status: str
    accepted: bool | None
    summary: str
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "activity_id": self.activity_id,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "runtime_name": self.runtime_name,
            "linked_run_id": self.linked_run_id,
            "status": self.status,
            "accepted": self.accepted,
            "summary": self.summary,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class TrajectoryRecord:
    trajectory_id: str
    session_id: str
    turn_id: str
    task_class: str
    path_selection: dict[str, object]
    stage: str
    outcome: str
    summary: str
    evidence_refs: list[str] = field(default_factory=list)
    asset_refs: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "trajectory_id": self.trajectory_id,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "task_class": self.task_class,
            "path_selection": dict(self.path_selection),
            "stage": self.stage,
            "outcome": self.outcome,
            "summary": self.summary,
            "evidence_refs": list(self.evidence_refs),
            "asset_refs": list(self.asset_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "TrajectoryRecord":
        return cls(
            trajectory_id=str(data["trajectory_id"]),
            session_id=str(data["session_id"]),
            turn_id=str(data["turn_id"]),
            task_class=str(data.get("task_class", "unknown")),
            path_selection=dict(data.get("path_selection", {})),
            stage=str(data.get("stage", "unknown")),
            outcome=str(data.get("outcome", "unknown")),
            summary=str(data.get("summary", "")),
            evidence_refs=[str(item) for item in data.get("evidence_refs", [])],
            asset_refs=[str(item) for item in data.get("asset_refs", [])],
            metadata=dict(data.get("metadata", {})),
        )


def new_session_id() -> str:
    return _new_id("agent-session")


def new_turn_id() -> str:
    return _new_id("turn")


def new_snapshot_id() -> str:
    return _new_id("snapshot")


def new_activity_id() -> str:
    return _new_id("activity")
