"""Execution-runtime models for the coding-agent skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from agent_orchestrator.intake.models import ExecutionMode, TaskKind, TaskRouterResult
from agent_orchestrator.policies import OrchestrationMode

ActionRiskLevel = Literal["low", "medium", "high"]
StepStatus = Literal["pending", "running", "completed", "blocked", "failed"]
DecisionDisposition = Literal["continue", "pause", "block", "complete"]


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    kind: str
    location: str
    label: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "location": self.location,
            "label": self.label,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ActionRequest:
    action_id: str
    action_type: str
    description: str
    parameters: dict[str, object] = field(default_factory=dict)
    risk_level: ActionRiskLevel = "low"
    requires_approval: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "description": self.description,
            "parameters": dict(self.parameters),
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
        }


@dataclass(frozen=True, slots=True)
class ActionResult:
    action_id: str
    action_type: str
    status: str
    summary: str
    error: str | None = None
    artifacts: list[ArtifactReference] = field(default_factory=list)
    payload: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "status": self.status,
            "summary": self.summary,
            "error": self.error,
            "artifacts": [item.to_dict() for item in self.artifacts],
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class ObservationRecord:
    observation_id: str
    kind: str
    summary: str
    source: str
    payload: dict[str, object] = field(default_factory=dict)
    artifact_refs: list[ArtifactReference] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "kind": self.kind,
            "summary": self.summary,
            "source": self.source,
            "payload": dict(self.payload),
            "artifact_refs": [item.to_dict() for item in self.artifact_refs],
        }


@dataclass(frozen=True, slots=True)
class PendingApprovalState:
    reason: str
    scope: str
    status: str = "not_required"
    approval_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "reason": self.reason,
            "scope": self.scope,
            "status": self.status,
            "approval_id": self.approval_id,
        }


@dataclass(frozen=True, slots=True)
class ExecutionResumeContract:
    resume_kind: str
    run_id: str
    session_id: str | None = None
    turn_id: str | None = None
    current_stage: str | None = None
    current_step_id: str | None = None
    approved_approval_id: str | None = None
    pending_approval: dict[str, object] | None = None
    resume_supported: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "resume_kind": self.resume_kind,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "current_stage": self.current_stage,
            "current_step_id": self.current_step_id,
            "approved_approval_id": self.approved_approval_id,
            "pending_approval": dict(self.pending_approval) if isinstance(self.pending_approval, dict) else None,
            "resume_supported": self.resume_supported,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "ExecutionResumeContract | None":
        if not isinstance(payload, dict):
            return None
        run_id = payload.get("run_id")
        resume_kind = payload.get("resume_kind")
        if not isinstance(run_id, str) or not run_id or not isinstance(resume_kind, str) or not resume_kind:
            return None
        pending_approval = payload.get("pending_approval")
        return cls(
            resume_kind=resume_kind,
            run_id=run_id,
            session_id=str(payload.get("session_id")) if payload.get("session_id") is not None else None,
            turn_id=str(payload.get("turn_id")) if payload.get("turn_id") is not None else None,
            current_stage=str(payload.get("current_stage")) if payload.get("current_stage") is not None else None,
            current_step_id=str(payload.get("current_step_id")) if payload.get("current_step_id") is not None else None,
            approved_approval_id=str(payload.get("approved_approval_id")) if payload.get("approved_approval_id") is not None else None,
            pending_approval=dict(pending_approval) if isinstance(pending_approval, dict) else None,
            resume_supported=bool(payload.get("resume_supported", True)),
        )


@dataclass(frozen=True, slots=True)
class CompressedExecutionContext:
    objective: str
    session_context: dict[str, object]
    current_status: str
    recent_steps: list[dict[str, object]] = field(default_factory=list)
    summarized_history: dict[str, object] = field(default_factory=dict)
    artifact_refs: list[dict[str, object]] = field(default_factory=list)
    pending_approval: dict[str, object] | None = None
    latest_recovery_hint: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "objective": self.objective,
            "session_context": dict(self.session_context),
            "current_status": self.current_status,
            "recent_steps": [dict(item) for item in self.recent_steps],
            "summarized_history": dict(self.summarized_history),
            "artifact_refs": [dict(item) for item in self.artifact_refs],
            "pending_approval": dict(self.pending_approval) if isinstance(self.pending_approval, dict) else None,
            "latest_recovery_hint": self.latest_recovery_hint,
        }


@dataclass(frozen=True, slots=True)
class ExecutionKernelContract:
    kernel_name: str
    kernel_role: str
    input_sources: list[str] = field(default_factory=list)
    output_surfaces: list[str] = field(default_factory=list)
    state_authority: str = "control_plane"
    session_owner: str = "session_runtime"
    provider_runtime_role: str = "execution_backend"
    topology_role: str = "upstream_execution_shape"

    def to_dict(self) -> dict[str, object]:
        return {
            "kernel_name": self.kernel_name,
            "kernel_role": self.kernel_role,
            "input_sources": list(self.input_sources),
            "output_surfaces": list(self.output_surfaces),
            "state_authority": self.state_authority,
            "session_owner": self.session_owner,
            "provider_runtime_role": self.provider_runtime_role,
            "topology_role": self.topology_role,
        }


@dataclass(frozen=True, slots=True)
class UnifiedAgentAdapterContract:
    adapter_family: str
    agent_kind: str
    execution_contract: dict[str, object] = field(default_factory=dict)
    runtime_metadata: dict[str, object] = field(default_factory=dict)
    capability_surface: dict[str, object] = field(default_factory=dict)
    path_selection: dict[str, object] = field(default_factory=dict)
    approval_semantics: dict[str, object] = field(default_factory=dict)
    evidence_outputs: list[str] = field(default_factory=list)
    recovery_surfaces: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter_family": self.adapter_family,
            "agent_kind": self.agent_kind,
            "execution_contract": dict(self.execution_contract),
            "runtime_metadata": dict(self.runtime_metadata),
            "capability_surface": dict(self.capability_surface),
            "path_selection": dict(self.path_selection),
            "approval_semantics": dict(self.approval_semantics),
            "evidence_outputs": list(self.evidence_outputs),
            "recovery_surfaces": list(self.recovery_surfaces),
        }


@dataclass(frozen=True, slots=True)
class ExecutionStepDecision:
    step_id: str
    step_kind: str
    disposition: DecisionDisposition
    reason: str
    next_step_kind: str | None = None
    pending_approval: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "step_id": self.step_id,
            "step_kind": self.step_kind,
            "disposition": self.disposition,
            "reason": self.reason,
            "next_step_kind": self.next_step_kind,
            "pending_approval": dict(self.pending_approval) if isinstance(self.pending_approval, dict) else None,
        }


@dataclass(frozen=True, slots=True)
class ExecutionStep:
    step_id: str
    title: str
    kind: str
    status: StepStatus
    actions: list[ActionRequest] = field(default_factory=list)
    results: list[ActionResult] = field(default_factory=list)
    observations: list[ObservationRecord] = field(default_factory=list)
    approval: PendingApprovalState | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "kind": self.kind,
            "status": self.status,
            "actions": [item.to_dict() for item in self.actions],
            "results": [item.to_dict() for item in self.results],
            "observations": [item.to_dict() for item in self.observations],
            "approval": self.approval.to_dict() if self.approval is not None else None,
        }


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    requirement: str
    route: TaskRouterResult
    runtime_name: str
    mode: OrchestrationMode | None
    reroute: bool = True
    agent_enabled: bool | None = None
    depth: int | None = None
    review_policy_override: str | None = None
    provider_health_snapshot: dict[str, object] | None = None
    task_contract: dict[str, object] | None = None
    session_id: str | None = None
    turn_id: str | None = None
    context_snapshot: dict[str, object] | None = None
    resume_kind: str | None = None
    session_metadata: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement": self.requirement,
            "route": self.route.to_dict(),
            "runtime_name": self.runtime_name,
            "mode": self.mode.value if self.mode else None,
            "reroute": self.reroute,
            "agent_enabled": self.agent_enabled,
            "depth": self.depth,
            "review_policy_override": self.review_policy_override,
            "provider_health_snapshot": dict(self.provider_health_snapshot)
            if isinstance(self.provider_health_snapshot, dict)
            else None,
            "task_contract": dict(self.task_contract) if isinstance(self.task_contract, dict) else None,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "context_snapshot": dict(self.context_snapshot) if isinstance(self.context_snapshot, dict) else None,
            "resume_kind": self.resume_kind,
            "session_metadata": dict(self.session_metadata) if isinstance(self.session_metadata, dict) else None,
        }


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    runtime_name: str
    execution_mode: ExecutionMode
    task_kind: TaskKind
    payload: dict[str, object]
    run_id: str | None = None
    accepted: bool | None = None
    status: str | None = None
    reasons: list[str] = field(default_factory=list)
    session_id: str | None = None
    turn_id: str | None = None
    kernel_contract: ExecutionKernelContract | None = None
    path_selection: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "runtime_name": self.runtime_name,
            "execution_mode": self.execution_mode.value,
            "task_kind": self.task_kind.value,
            "payload": dict(self.payload),
            "run_id": self.run_id,
            "accepted": self.accepted,
            "status": self.status,
            "reasons": list(self.reasons),
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "kernel_contract": self.kernel_contract.to_dict() if self.kernel_contract is not None else None,
            "path_selection": dict(self.path_selection),
        }
