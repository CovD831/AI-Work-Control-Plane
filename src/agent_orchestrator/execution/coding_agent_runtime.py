"""MVP coding-agent execution runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from agent_orchestrator.control_plane_approvals import ApprovalItem, ApprovalStore
from agent_orchestrator.control_plane_workspace import WorkspaceIndexStore
from agent_orchestrator.adapters import EnvSlotFillConfig, _default_openai_compatible_transport, _extract_openai_message_content
from agent_orchestrator.events import EventStore
from agent_orchestrator.execution.coding_components import (
    ContextBuilder,
    EditExecutor,
    RepoExplorer,
    VerifyLoop,
)
from agent_orchestrator.execution.models import (
    ActionRequest,
    ActionResult,
    CompressedExecutionContext,
    ExecutionRequest,
    ExecutionResumeContract,
    ExecutionResult,
    ExecutionStep,
    ExecutionStepDecision,
    ObservationRecord,
    PendingApprovalState,
)
from agent_orchestrator.execution.state_store import ExecutionStateStore
from agent_orchestrator.execution.runtime import ExecutionRuntime
from agent_orchestrator.intake import ExecutionMode
from agent_orchestrator.memory import MemoryStore
from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.policies import get_policy
from agent_orchestrator.session import ScratchpadStore
from agent_orchestrator.strategy import CompatibilityStrategyPlanner
from agent_orchestrator.tasks import TaskContract


@dataclass(frozen=True, slots=True)
class _ContextSelection:
    deterministic: dict[str, object]
    model_driven: dict[str, object]
    retrieval: dict[str, object]
    selected_context: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "deterministic": dict(self.deterministic),
            "model_driven": dict(self.model_driven),
            "retrieval": dict(self.retrieval),
            "selected_context": dict(self.selected_context),
        }


@dataclass(frozen=True, slots=True)
class _CompactionState:
    stage: str
    observation_count: int
    preserve_recent: int
    masked_count: int
    light_compaction_applied: bool
    summarization_triggered: bool
    summarization_reason: str | None
    summarization_summary: str | None = None
    summarization_source: str | None = None
    system_prompt_compacted: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "observation_count": self.observation_count,
            "preserve_recent": self.preserve_recent,
            "masked_count": self.masked_count,
            "light_compaction_applied": self.light_compaction_applied,
            "summarization_triggered": self.summarization_triggered,
            "summarization_reason": self.summarization_reason,
            "summarization_summary": self.summarization_summary,
            "summarization_source": self.summarization_source,
            "system_prompt_compacted": self.system_prompt_compacted,
        }


@dataclass(frozen=True, slots=True)
class _IsolationState:
    applied: bool
    strategy: str
    reason: str
    input_target_count: int
    output_target_count: int
    input_patch_plan_count: int
    output_patch_plan_count: int
    digest: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "applied": self.applied,
            "strategy": self.strategy,
            "reason": self.reason,
            "input_target_count": self.input_target_count,
            "output_target_count": self.output_target_count,
            "input_patch_plan_count": self.input_patch_plan_count,
            "output_patch_plan_count": self.output_patch_plan_count,
            "digest": dict(self.digest),
        }


@dataclass(slots=True)
class CodingAgentExecutionRuntime(ExecutionRuntime):
    """Phase-4 execution backend that directly explores repo context and verifies a bounded plan."""

    orchestrator: Orchestrator
    repo_explorer: RepoExplorer = field(default_factory=RepoExplorer)
    context_builder: ContextBuilder = field(default_factory=ContextBuilder)
    edit_executor: EditExecutor = field(default_factory=EditExecutor)
    verify_loop: VerifyLoop = field(default_factory=VerifyLoop)
    state_store: ExecutionStateStore = field(default_factory=ExecutionStateStore)
    event_store: EventStore = field(default_factory=EventStore)
    scratchpad_store: ScratchpadStore = field(default_factory=ScratchpadStore)
    memory_store: MemoryStore = field(default_factory=MemoryStore)
    model_selector_transport: Callable[[str, dict[str, object], dict[str, str], int], dict[str, object]] | None = None
    summarizer_transport: Callable[[str, dict[str, object], dict[str, str], int], dict[str, object]] | None = None
    intent_refiner_transport: Callable[[str, dict[str, object], dict[str, str], int], dict[str, object]] | None = None
    enforce_approvals: bool = False
    approvals_root: Path | str | None = None
    name: str = "coding_agent"

    def run(self, request: ExecutionRequest) -> ExecutionResult:
        policy = get_policy(request.mode) if request.mode is not None else get_policy()
        task_contract = TaskContract.from_dict(request.task_contract) if isinstance(request.task_contract, dict) else None
        strategy_planner = self.orchestrator.strategy_planner or CompatibilityStrategyPlanner(self.orchestrator.decomposer)
        strategy_plan = strategy_planner.plan(task_contract, policy, route=request.route) if task_contract is not None else None
        repo_report = self.repo_explorer.explore(request)
        context = self.context_builder.build(request=request, strategy_plan=strategy_plan, repo_report=repo_report)
        context_selection = _select_runtime_context(
            self,
            request=request,
            context=context,
            repo_report=repo_report.to_dict(),
        )
        self.edit_executor.intent_refiner_transport = self.intent_refiner_transport
        edit_intent = self.edit_executor.build_intent(
            request=request,
            repo_report=repo_report,
            context=context,
            context_selection=context_selection.to_dict(),
        )
        isolation_state = _isolate_runtime_context(
            request=request,
            context_selection=context_selection.to_dict(),
            edit_intent=edit_intent.to_dict(),
        )
        kernel_result = _run_execution_kernel(self, request=request, edit_intent=edit_intent)
        pending_approval = kernel_result.pending_approval
        applied_changes = kernel_result.applied_changes
        applied_change_payloads = [
            item.to_dict() if hasattr(item, "to_dict") else dict(item)
            for item in applied_changes
            if hasattr(item, "to_dict") or isinstance(item, dict)
        ]
        repair_summary_payload = kernel_result.repair_summary
        final_verification = kernel_result.final_verification
        applied_change_count = kernel_result.applied_change_count
        status = kernel_result.status
        accepted = kernel_result.accepted
        planner_context_trace = kernel_result.planner_context_trace
        next_stage_proposals = kernel_result.next_stage_proposals
        stage_selection_trace = kernel_result.stage_selection_trace
        action_selection_trace = kernel_result.action_selection_trace
        structured_observations = _structured_observation_records(
            steps=_build_execution_steps(
                request=request,
                repo_report=repo_report.to_dict(),
                context=context.to_dict(),
                edit_intent=edit_intent.to_dict(),
                applied_changes=applied_change_payloads,
                final_verification=dict(final_verification),
                repair_summary=repair_summary_payload,
                status=status,
                pending_approval=pending_approval,
            )
        )
        _write_runtime_context(
            self,
            request=request,
            planner_context_trace=planner_context_trace,
            structured_observations=structured_observations,
            context_selection=context_selection.to_dict(),
            isolation_state=isolation_state.to_dict(),
            status=status,
        )
        steps = _build_execution_steps(
            request=request,
            repo_report=repo_report.to_dict(),
            context=context.to_dict(),
            edit_intent=edit_intent.to_dict(),
            applied_changes=applied_change_payloads,
            final_verification=dict(final_verification),
            repair_summary=repair_summary_payload,
            status=status,
            pending_approval=pending_approval,
        )
        step_decisions = _build_step_decisions(
            steps=steps,
            pending_approval=pending_approval,
            final_status=status,
        )
        payload = {
            "runtime_name": self.name,
            "execution_mode": ExecutionMode.CODING_AGENT.value,
            "task_kind": request.route.task_kind.value,
            "session_id": request.session_id,
            "turn_id": request.turn_id,
            "context_snapshot": dict(request.context_snapshot or {}),
            "repo_report": repo_report.to_dict(),
            "execution_context": context.to_dict(),
            "context_selection": context_selection.to_dict(),
            "isolation_state": isolation_state.to_dict(),
            "edit_intent": edit_intent.to_dict(),
            "llm_assisted_intent": dict(edit_intent.refinement) if isinstance(edit_intent.refinement, dict) else None,
            "applied_changes": applied_change_payloads,
            "applied_change_count": applied_change_count,
            "verification": dict(final_verification),
            "repair_summary": dict(repair_summary_payload),
            "attempt_memory": list(repair_summary_payload.get("attempts", [])),
            "recovery_summary": dict(repair_summary_payload.get("recovery_recommendation", {})),
            "strategy_summary": strategy_plan.summary() if strategy_plan is not None else {},
            "execution_steps": [step.to_dict() for step in steps],
            "planner_context_trace": list(planner_context_trace),
            "next_stage_proposals": list(next_stage_proposals),
            "stage_selection_trace": list(stage_selection_trace),
            "action_selection_trace": list(action_selection_trace),
            "scratchpad_entries": self.scratchpad_store.query(session_id=request.session_id or "", turn_id=request.turn_id or "", limit=20)
            if request.session_id and request.turn_id
            else [],
            "step_decisions": [decision.to_dict() for decision in step_decisions],
            "governance_summary": _governance_summary(steps),
            "artifact_summary": _artifact_summary(steps),
            "execution_history_summary": _execution_history_summary(
                request=request,
                status=status,
                steps=steps,
                pending_approval=pending_approval,
            ),
            "pending_approval": dict(pending_approval) if isinstance(pending_approval, dict) else None,
            "status": status,
            "accepted": accepted,
        }
        if request.session_id:
            payload["retrieved_memory"] = self.memory_store.search(request.requirement, session_id=request.session_id, limit=5)
        else:
            payload["retrieved_memory"] = self.memory_store.search(request.requirement, limit=5)
        payload["resume_context"] = _resume_context_payload(
            request=request,
            steps=steps,
            final_verification=final_verification,
            repair_summary=repair_summary_payload,
        )
        payload["compaction_state"] = _compaction_state(
            self,
            request=request,
            steps=steps,
            context_selection=payload["context_selection"],
        )
        payload["compressed_context"] = _compressed_execution_context(
            request=request,
            status=status,
            steps=steps,
            payload=payload,
            pending_approval=pending_approval,
        )
        payload["next_step_contract"] = _next_step_contract(
            decisions=step_decisions,
            status=status,
            pending_approval=pending_approval,
            resume_context=payload["resume_context"],
        )
        payload["event_summary"] = _emit_execution_events(
            self,
            request=request,
            status=status,
            accepted=accepted,
            steps=steps,
            pending_approval=pending_approval,
        )
        _persist_execution_state(
            self,
            request=request,
            status=status,
            accepted=accepted,
            pending_approval=pending_approval,
            steps=steps,
            payload=payload,
        )
        _record_execution_artifacts(self, request=request, payload=payload)
        return ExecutionResult(
            runtime_name=self.name,
            execution_mode=ExecutionMode.CODING_AGENT,
            task_kind=request.route.task_kind,
            payload=payload,
            run_id=_runtime_run_id(request),
            accepted=accepted,
            status=status,
            reasons=list(request.route.reasons),
            session_id=request.session_id,
            turn_id=request.turn_id,
        )

    def start(self, request: ExecutionRequest) -> ExecutionResult:
        run_id = _runtime_run_id(request)
        payload = {
            "run_id": run_id,
            "status": "queued",
            "job_ids": [],
            "active_attempt_id": None,
            "runtime_name": self.name,
            "session_id": request.session_id,
            "turn_id": request.turn_id,
        }
        return ExecutionResult(
            runtime_name=self.name,
            execution_mode=ExecutionMode.CODING_AGENT,
            task_kind=request.route.task_kind,
            payload=payload,
            run_id=run_id,
            accepted=None,
            status="queued",
            reasons=list(request.route.reasons),
            session_id=request.session_id,
            turn_id=request.turn_id,
        )

    def resume_from_state(self, request: ExecutionRequest) -> ExecutionResult:
        restored_request = _request_with_resume_contract(self, request)
        return self.run(restored_request)


RuntimeStage = Literal["explore", "edit", "verify", "completed"]


@dataclass(frozen=True, slots=True)
class _KernelState:
    stage_cursor: RuntimeStage
    pending_approval: dict[str, object] | None
    applied_changes: list[object]
    repair_summary: dict[str, object]
    final_verification: dict[str, object]
    status: str
    accepted: bool
    applied_change_count: int
    planner_context_trace: list[dict[str, object]]
    next_stage_proposals: list[dict[str, object]]
    stage_selection_trace: list[dict[str, object]]
    action_selection_trace: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class _KernelStageSelection:
    stage: RuntimeStage
    outcome: str
    next_stage: RuntimeStage | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "outcome": self.outcome,
            "next_stage": self.next_stage,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class _KernelActionSelection:
    stage: RuntimeStage
    action_type: str
    source: str
    selected: dict[str, object]
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "action_type": self.action_type,
            "source": self.source,
            "selected": dict(self.selected),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class _KernelResumeState:
    stage_cursor: RuntimeStage
    applied_changes: list[dict[str, object]]
    recent_observations: list[dict[str, object]]
    final_verification: dict[str, object]
    repair_summary: dict[str, object]
    verification_command: list[str]
    remaining_retry_budget: int | None
    should_block_verify_resume: bool


@dataclass(frozen=True, slots=True)
class _KernelPlannerContext:
    stage_cursor: RuntimeStage
    resume_kind: str
    route_risk_level: str
    edit_mode: str
    operation_count: int
    operation_paths: list[str]
    target_paths: list[str]
    workspace_root: str
    verification_command: list[str]
    remaining_retry_budget: int | None
    should_block_verify_resume: bool
    latest_observation_kind: str | None
    action_feasibility: str
    approval_required: bool
    approval_resolved: bool
    pending_approval_stage: str | None
    applied_change_count: int
    recent_observation_count: int
    verification_status: str | None
    repair_outcome: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "stage_cursor": self.stage_cursor,
            "resume_kind": self.resume_kind,
            "route_risk_level": self.route_risk_level,
            "edit_mode": self.edit_mode,
            "operation_count": self.operation_count,
            "operation_paths": list(self.operation_paths),
            "target_paths": list(self.target_paths),
            "workspace_root": self.workspace_root,
            "verification_command": list(self.verification_command),
            "remaining_retry_budget": self.remaining_retry_budget,
            "should_block_verify_resume": self.should_block_verify_resume,
            "latest_observation_kind": self.latest_observation_kind,
            "action_feasibility": self.action_feasibility,
            "approval_required": self.approval_required,
            "approval_resolved": self.approval_resolved,
            "pending_approval_stage": self.pending_approval_stage,
            "applied_change_count": self.applied_change_count,
            "recent_observation_count": self.recent_observation_count,
            "verification_status": self.verification_status,
            "repair_outcome": self.repair_outcome,
        }


@dataclass(frozen=True, slots=True)
class _KernelNextStageCandidate:
    candidate_id: str
    stage: RuntimeStage
    disposition: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "stage": self.stage,
            "disposition": self.disposition,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class _KernelNextStageProposal:
    current_stage: RuntimeStage
    proposed_stage: RuntimeStage
    disposition: str
    reason: str
    candidates: list[_KernelNextStageCandidate]
    selected_candidate_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "current_stage": self.current_stage,
            "proposed_stage": self.proposed_stage,
            "disposition": self.disposition,
            "reason": self.reason,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "selected_candidate_id": self.selected_candidate_id,
        }


@dataclass(frozen=True, slots=True)
class _KernelStagePlan:
    stage_cursor: RuntimeStage
    stage_strategy: _KernelStageStrategy
    planner_context: _KernelPlannerContext
    next_stage_proposal: _KernelNextStageProposal
    stage_selection: _KernelStageSelection
    action_selection: _KernelActionSelection | None = None


@dataclass(frozen=True, slots=True)
class _KernelStageOutcome:
    next_stage: RuntimeStage
    pending_approval: dict[str, object] | None
    applied_changes: list[object]
    repair_summary: dict[str, object]
    final_verification: dict[str, object]
    status: str
    accepted: bool
    should_stop: bool


@dataclass(frozen=True, slots=True)
class _KernelStageOutcomeSemantics:
    pause: Callable[..., _KernelStageOutcome] | None = None
    block: Callable[..., _KernelStageOutcome] | None = None
    continue_outcome: Callable[..., _KernelStageOutcome] | None = None
    complete: Callable[..., _KernelStageOutcome] | None = None


@dataclass(frozen=True, slots=True)
class _KernelStageStrategy:
    candidate_generator: Callable[
        [_KernelPlannerContext, _KernelResumeState],
        list[_KernelNextStageCandidate],
    ]
    ranking_enabled: Callable[[_KernelPlannerContext], bool]
    rank_adjustment: Callable[[_KernelNextStageCandidate, _KernelPlannerContext], int]
    action_selector: Callable[[_KernelPlannerContext], _KernelActionSelection | None]
    stage_selector: Callable[
        [_KernelActionSelection | None, _KernelNextStageProposal],
        _KernelStageSelection,
    ]
    executor: Callable[
        [CodingAgentExecutionRuntime, ExecutionRequest, object, _KernelResumeState, _KernelStagePlan, list[object]],
        _KernelStageOutcome,
    ]
    outcomes: _KernelStageOutcomeSemantics

    def propose_next_stage(
        self,
        *,
        current_stage: RuntimeStage,
        planner_context: _KernelPlannerContext,
        resume_state: _KernelResumeState,
    ) -> _KernelNextStageProposal:
        candidates = self.candidate_generator(
            planner_context,
            resume_state,
        )
        selected = _select_next_stage_candidate(
            candidates,
            planner_context=planner_context,
            stage_strategy=self,
        )
        return _proposal_from_selected_candidate(
            current_stage=current_stage,
            candidates=candidates,
            selected_candidate=selected,
        )

    def build_stage_plan(
        self,
        *,
        stage_cursor: RuntimeStage,
        planner_context: _KernelPlannerContext,
        resume_state: _KernelResumeState,
    ) -> _KernelStagePlan:
        next_stage_proposal = self.propose_next_stage(
            current_stage=stage_cursor,
            planner_context=planner_context,
            resume_state=resume_state,
        )
        action_selection = self.action_selector(planner_context)
        stage_selection = self.stage_selector(action_selection, next_stage_proposal)
        return _KernelStagePlan(
            stage_cursor=stage_cursor,
            stage_strategy=self,
            planner_context=planner_context,
            next_stage_proposal=next_stage_proposal,
            stage_selection=stage_selection,
            action_selection=action_selection,
        )

    def execute_stage(
        self,
        *,
        runtime: CodingAgentExecutionRuntime,
        request: ExecutionRequest,
        edit_intent,
        resume_state: _KernelResumeState,
        plan: _KernelStagePlan,
        applied_changes: list[object],
    ) -> _KernelStageOutcome:
        return self.executor(
            runtime,
            request,
            edit_intent,
            resume_state,
            plan,
            applied_changes,
        )

    def pause_stage(self, **kwargs) -> _KernelStageOutcome:
        if self.outcomes.pause is None:
            raise RuntimeError("pause outcome semantics are not configured for this stage strategy")
        return self.outcomes.pause(**kwargs)

    def block_stage(self, **kwargs) -> _KernelStageOutcome:
        if self.outcomes.block is None:
            raise RuntimeError("block outcome semantics are not configured for this stage strategy")
        return self.outcomes.block(**kwargs)

    def continue_stage(self, **kwargs) -> _KernelStageOutcome:
        if self.outcomes.continue_outcome is None:
            raise RuntimeError("continue outcome semantics are not configured for this stage strategy")
        return self.outcomes.continue_outcome(**kwargs)

    def complete_stage(self, **kwargs) -> _KernelStageOutcome:
        if self.outcomes.complete is None:
            raise RuntimeError("complete outcome semantics are not configured for this stage strategy")
        return self.outcomes.complete(**kwargs)


def _runtime_run_id(request: ExecutionRequest) -> str:
    if request.turn_id:
        return f"coding-{request.turn_id}"
    if request.session_id:
        return f"coding-{request.session_id}"
    return "coding-inline"


def _run_execution_kernel(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    edit_intent,
) -> _KernelState:
    resume_state = _kernel_resume_state(runtime, request=request)
    stage_cursor: RuntimeStage = resume_state.stage_cursor
    pending_approval: dict[str, object] | None = None
    applied_changes: list[object] = list(resume_state.applied_changes)
    repair_summary_payload: dict[str, object] = dict(resume_state.repair_summary)
    final_verification: dict[str, object] = dict(resume_state.final_verification)
    status = "blocked"
    accepted = False
    planner_context_trace: list[dict[str, object]] = []
    next_stage_proposals: list[dict[str, object]] = []
    stage_selection_trace: list[dict[str, object]] = []
    action_selection_trace: list[dict[str, object]] = []

    while stage_cursor != "completed":
        plan = _plan_kernel_stage(
            runtime,
            request=request,
            edit_intent=edit_intent,
            resume_state=resume_state,
            stage_cursor=stage_cursor,
        )
        planner_context_trace.append(plan.planner_context.to_dict())
        next_stage_proposals.append(plan.next_stage_proposal.to_dict())
        stage_selection_trace.append(
            {
                **plan.stage_selection.to_dict(),
                "next_stage_proposal": plan.next_stage_proposal.to_dict(),
                "planner_context": plan.planner_context.to_dict(),
            }
        )
        if plan.action_selection is not None:
            action_selection_trace.append(
                {
                    **plan.action_selection.to_dict(),
                    "planner_context": plan.planner_context.to_dict(),
                }
            )
        outcome = _execute_kernel_stage(
            runtime,
            request=request,
            edit_intent=edit_intent,
            resume_state=resume_state,
            plan=plan,
            applied_changes=applied_changes,
        )
        pending_approval = outcome.pending_approval
        applied_changes = outcome.applied_changes
        repair_summary_payload = outcome.repair_summary
        final_verification = outcome.final_verification
        status = outcome.status
        accepted = outcome.accepted
        stage_cursor = outcome.next_stage
        if outcome.should_stop:
            break

    applied_change_count = sum(
        1
        for item in applied_changes
        if (getattr(item, "status", None) == "applied")
        or (isinstance(item, dict) and item.get("status") == "applied")
    )
    return _KernelState(
        stage_cursor=stage_cursor,
        pending_approval=pending_approval,
        applied_changes=applied_changes,
        repair_summary=repair_summary_payload,
        final_verification=final_verification,
        status=status,
        accepted=accepted,
        applied_change_count=applied_change_count,
        planner_context_trace=planner_context_trace,
        next_stage_proposals=next_stage_proposals,
        stage_selection_trace=stage_selection_trace,
        action_selection_trace=action_selection_trace,
    )


def _kernel_resume_state(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
) -> _KernelResumeState:
    if request.resume_kind not in {"approval_resume"}:
        return _KernelResumeState(
            stage_cursor="explore",
            applied_changes=[],
            recent_observations=[],
            final_verification={},
            repair_summary={},
            verification_command=[],
            remaining_retry_budget=None,
            should_block_verify_resume=False,
        )
    stored = runtime.state_store.read(_runtime_run_id(request))
    current_stage = str(stored.get("current_stage") or "")
    result_summary = stored.get("result_summary", {}) if isinstance(stored.get("result_summary"), dict) else {}
    persisted_changes = result_summary.get("applied_changes", []) if isinstance(result_summary.get("applied_changes"), list) else []
    restored_changes = [dict(item) for item in persisted_changes if isinstance(item, dict)]
    recent_observations = result_summary.get("recent_observations", []) if isinstance(result_summary.get("recent_observations"), list) else []
    final_verification = result_summary.get("verification", {}) if isinstance(result_summary.get("verification"), dict) else {}
    repair_summary = result_summary.get("repair_summary", {}) if isinstance(result_summary.get("repair_summary"), dict) else {}
    resume_context = stored.get("resume_context", {}) if isinstance(stored.get("resume_context"), dict) else {}
    verification_command = final_verification.get("command", []) if isinstance(final_verification.get("command"), list) else []
    if not verification_command and isinstance(resume_context.get("planned_verification_command"), list):
        verification_command = [str(item) for item in resume_context.get("planned_verification_command", []) if isinstance(item, str)]
    remaining_retry_budget = _remaining_retry_budget(repair_summary)
    should_block_verify_resume = _should_block_verify_resume(
        final_verification=final_verification,
        repair_summary=repair_summary,
        remaining_retry_budget=remaining_retry_budget,
    )
    if current_stage == "edit":
        return _KernelResumeState(
            stage_cursor="edit",
            applied_changes=[],
            recent_observations=[dict(item) for item in recent_observations if isinstance(item, dict)],
            final_verification=dict(final_verification),
            repair_summary=dict(repair_summary),
            verification_command=[str(item) for item in verification_command if isinstance(item, str)],
            remaining_retry_budget=remaining_retry_budget,
            should_block_verify_resume=False,
        )
    if current_stage == "verify":
        return _KernelResumeState(
            stage_cursor="verify",
            applied_changes=restored_changes,
            recent_observations=[dict(item) for item in recent_observations if isinstance(item, dict)],
            final_verification=dict(final_verification),
            repair_summary=dict(repair_summary),
            verification_command=[str(item) for item in verification_command if isinstance(item, str)],
            remaining_retry_budget=remaining_retry_budget,
            should_block_verify_resume=should_block_verify_resume,
        )
    return _KernelResumeState(
        stage_cursor="explore",
        applied_changes=[],
        recent_observations=[dict(item) for item in recent_observations if isinstance(item, dict)],
        final_verification=dict(final_verification),
        repair_summary=dict(repair_summary),
        verification_command=[str(item) for item in verification_command if isinstance(item, str)],
        remaining_retry_budget=remaining_retry_budget,
        should_block_verify_resume=False,
    )


def _plan_kernel_stage(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    edit_intent,
    resume_state: _KernelResumeState,
    stage_cursor: RuntimeStage,
) -> _KernelStagePlan:
    planner_context = _planner_context_for_stage(
        runtime,
        request=request,
        edit_intent=edit_intent,
        resume_state=resume_state,
        stage_cursor=stage_cursor,
    )
    stage_strategy = _stage_strategy(stage_cursor)
    return stage_strategy.build_stage_plan(
        stage_cursor=stage_cursor,
        planner_context=planner_context,
        resume_state=resume_state,
    )


def _planner_context_for_stage(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    edit_intent,
    resume_state: _KernelResumeState,
    stage_cursor: RuntimeStage,
) -> _KernelPlannerContext:
    operations = getattr(edit_intent, "operations", None)
    target_paths = getattr(edit_intent, "target_paths", None)
    mode = getattr(edit_intent, "mode", None)
    if isinstance(edit_intent, dict):
        if operations is None:
            operations = edit_intent.get("operations", [])
        if target_paths is None:
            target_paths = edit_intent.get("target_paths", [])
        if mode is None:
            mode = edit_intent.get("mode")
    latest_observation_kind = None
    if resume_state.recent_observations:
        latest = resume_state.recent_observations[-1]
        if isinstance(latest, dict):
            kind = latest.get("kind")
            latest_observation_kind = str(kind) if kind is not None else None
    workspace_root = runtime.edit_executor.workspace_root
    operation_paths = [
        str(item.get("path", ""))
        for item in operations
        if isinstance(operations, list) and isinstance(item, dict)
    ] if isinstance(operations, list) else []
    target_path_list = [str(item) for item in target_paths if isinstance(item, str)] if isinstance(target_paths, list) else []
    approval_required = _approval_required_for_stage(
        runtime,
        stage_cursor=stage_cursor,
        edit_mode=str(mode or "report_first"),
        target_paths=target_path_list,
    )
    approval_resolved = _approval_resolved_for_stage(runtime, request=request, stage=stage_cursor) if approval_required else False
    pending_approval_stage = stage_cursor if approval_required and not approval_resolved else None
    action_feasibility = _action_feasibility_for_stage(
        stage_cursor=stage_cursor,
        edit_mode=str(mode or "report_first"),
        operation_count=len(operations) if isinstance(operations, list) else 0,
        operation_paths=operation_paths,
        target_paths=target_path_list,
        workspace_root=workspace_root if isinstance(workspace_root, Path) else Path(workspace_root),
        should_block_verify_resume=resume_state.should_block_verify_resume,
    )
    applied_change_count = sum(
        1
        for item in resume_state.applied_changes
        if isinstance(item, dict) and item.get("status") == "applied"
    )
    return _KernelPlannerContext(
        stage_cursor=stage_cursor,
        resume_kind=request.resume_kind or "fresh",
        route_risk_level=str(getattr(request.route, "risk_level", "unknown") or "unknown"),
        edit_mode=str(mode or "report_first"),
        operation_count=len(operations) if isinstance(operations, list) else 0,
        operation_paths=operation_paths,
        target_paths=target_path_list,
        workspace_root=str(workspace_root.resolve()) if isinstance(workspace_root, Path) else str(workspace_root),
        verification_command=[str(item) for item in resume_state.verification_command if isinstance(item, str)],
        remaining_retry_budget=resume_state.remaining_retry_budget,
        should_block_verify_resume=resume_state.should_block_verify_resume,
        latest_observation_kind=latest_observation_kind,
        action_feasibility=action_feasibility,
        approval_required=approval_required,
        approval_resolved=approval_resolved,
        pending_approval_stage=pending_approval_stage,
        applied_change_count=applied_change_count,
        recent_observation_count=len(resume_state.recent_observations),
        verification_status=str(resume_state.final_verification.get("status")) if resume_state.final_verification.get("status") is not None else None,
        repair_outcome=str(resume_state.repair_summary.get("outcome")) if resume_state.repair_summary.get("outcome") is not None else None,
    )


def _execute_kernel_stage(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    edit_intent,
    resume_state: _KernelResumeState,
    plan: _KernelStagePlan,
    applied_changes: list[object],
) -> _KernelStageOutcome:
    return plan.stage_strategy.execute_stage(
        runtime=runtime,
        request=request,
        edit_intent=edit_intent,
        resume_state=resume_state,
        plan=plan,
        applied_changes=applied_changes,
    )


def _execute_edit_stage(
    runtime: CodingAgentExecutionRuntime,
    request: ExecutionRequest,
    edit_intent,
    resume_state: _KernelResumeState,
    plan: _KernelStagePlan,
    applied_changes: list[object],
) -> _KernelStageOutcome:
    stage_strategy = plan.stage_strategy
    edit_selection = plan.action_selection
    if edit_selection is not None and edit_selection.action_type == "pause":
        pending_approval = _approval_gate_for_edit(runtime, request=request, edit_intent=edit_intent)
        return stage_strategy.pause_stage(
            pending_approval=pending_approval,
            plan=plan,
            resume_state=resume_state,
        )
    if edit_selection is not None and edit_selection.action_type == "block":
        return stage_strategy.block_stage(
            edit_selection=edit_selection,
            plan=plan,
            resume_state=resume_state,
        )
    applied_changes = runtime.edit_executor.apply(edit_intent)
    return stage_strategy.continue_stage(
        applied_changes=applied_changes,
        plan=plan,
        resume_state=resume_state,
    )


def _paused_edit_outcome(
    *,
    pending_approval: dict[str, object] | None,
    plan: _KernelStagePlan,
    resume_state: _KernelResumeState,
) -> _KernelStageOutcome:
    return _stage_outcome(
        next_stage=plan.stage_cursor,
        pending_approval=pending_approval,
        applied_changes=[],
        repair_summary=_pending_repair_summary(pending_approval or {"stage": "edit"}),
        final_verification=dict(resume_state.final_verification),
        status="blocked",
        accepted=False,
        should_stop=True,
    )


def _blocked_edit_outcome(
    *,
    edit_selection: _KernelActionSelection,
    plan: _KernelStagePlan,
    resume_state: _KernelResumeState,
) -> _KernelStageOutcome:
    return _stage_outcome(
        next_stage=plan.next_stage_proposal.proposed_stage,
        pending_approval=None,
        applied_changes=[],
        repair_summary=_blocked_edit_repair_summary(edit_selection),
        final_verification=dict(resume_state.final_verification),
        status="blocked",
        accepted=False,
        should_stop=True,
    )


def _applied_edit_outcome(
    *,
    applied_changes: list[object],
    plan: _KernelStagePlan,
    resume_state: _KernelResumeState,
) -> _KernelStageOutcome:
    return _continue_stage_outcome(
        next_stage=plan.next_stage_proposal.proposed_stage,
        applied_changes=applied_changes,
        repair_summary=dict(resume_state.repair_summary),
        final_verification=dict(resume_state.final_verification),
    )


def _continue_stage_outcome(
    *,
    next_stage: RuntimeStage,
    applied_changes: list[object],
    repair_summary: dict[str, object],
    final_verification: dict[str, object],
) -> _KernelStageOutcome:
    return _stage_outcome(
        next_stage=next_stage,
        pending_approval=None,
        applied_changes=list(applied_changes),
        repair_summary=repair_summary,
        final_verification=final_verification,
        status="blocked",
        accepted=False,
        should_stop=False,
    )


def _continue_without_side_effects_stage(
    runtime: CodingAgentExecutionRuntime,
    request: ExecutionRequest,
    edit_intent,
    resume_state: _KernelResumeState,
    plan: _KernelStagePlan,
    applied_changes: list[object],
) -> _KernelStageOutcome:
    return _continue_stage_outcome(
        next_stage=plan.next_stage_proposal.proposed_stage,
        applied_changes=applied_changes,
        repair_summary=dict(resume_state.repair_summary),
        final_verification=dict(resume_state.final_verification),
    )


def _execute_verify_stage(
    runtime: CodingAgentExecutionRuntime,
    request: ExecutionRequest,
    edit_intent,
    resume_state: _KernelResumeState,
    plan: _KernelStagePlan,
    applied_changes: list[object],
) -> _KernelStageOutcome:
    stage_strategy = plan.stage_strategy
    action_selection = plan.action_selection
    if action_selection is not None and action_selection.action_type == "pause":
        pending_approval = _approval_gate_for_verification(runtime, request=request, edit_intent=edit_intent)
        return stage_strategy.pause_stage(
            pending_approval=pending_approval,
            plan=plan,
            resume_state=resume_state,
            applied_changes=applied_changes,
        )
    if resume_state.should_block_verify_resume:
        return stage_strategy.block_stage(
            plan=plan,
            resume_state=resume_state,
            applied_changes=applied_changes,
        )
    continuation_notes = _verification_continuation_notes(resume_state)
    verification_command = (
        list(action_selection.selected.get("command", []))
        if action_selection is not None and isinstance(action_selection.selected.get("command"), list)
        else None
    )
    repair_summary = runtime.verify_loop.verify(
        request,
        edit_intent,
        command_override=verification_command,
        continuation_notes=continuation_notes,
        retry_budget_override=resume_state.remaining_retry_budget,
    )
    repair_summary_payload = repair_summary.to_dict()
    final_attempt = repair_summary.attempts[-1] if repair_summary.attempts else {}
    final_verification = final_attempt.get("verification", {}) if isinstance(final_attempt, dict) else {}
    final_status = str(final_verification.get("status", repair_summary.outcome))
    applied_change_count = sum(
        1
        for item in applied_changes
        if (getattr(item, "status", None) == "applied")
        or (isinstance(item, dict) and item.get("status") == "applied")
    )
    status, accepted = _verify_terminal_status(
        final_status=final_status,
        edit_mode=edit_intent.mode,
        applied_change_count=applied_change_count,
    )
    return stage_strategy.complete_stage(
        plan=plan,
        applied_changes=applied_changes,
        repair_summary=repair_summary_payload,
        final_verification=final_verification,
        status=status,
        accepted=accepted,
    )


def _paused_verify_outcome(
    *,
    pending_approval: dict[str, object] | None,
    plan: _KernelStagePlan,
    resume_state: _KernelResumeState,
    applied_changes: list[object],
) -> _KernelStageOutcome:
    return _stage_outcome(
        next_stage=plan.stage_cursor,
        pending_approval=pending_approval,
        applied_changes=list(applied_changes),
        repair_summary=_pending_repair_summary(pending_approval or {"stage": "verify"}),
        final_verification=dict(resume_state.final_verification),
        status="blocked",
        accepted=False,
        should_stop=True,
    )


def _blocked_verify_resume_outcome(
    *,
    plan: _KernelStagePlan,
    resume_state: _KernelResumeState,
    applied_changes: list[object],
) -> _KernelStageOutcome:
    return _stage_outcome(
        next_stage=plan.stage_cursor,
        pending_approval=None,
        applied_changes=list(applied_changes),
        repair_summary=dict(resume_state.repair_summary),
        final_verification=dict(resume_state.final_verification),
        status="blocked",
        accepted=False,
        should_stop=True,
    )


def _verify_terminal_status(
    *,
    final_status: str,
    edit_mode: str,
    applied_change_count: int,
) -> tuple[str, bool]:
    direct_apply_without_change = edit_mode == "direct_apply" and applied_change_count == 0
    status = "completed" if final_status in {"passed", "skipped"} and not direct_apply_without_change else "blocked"
    accepted = final_status != "failed" and not direct_apply_without_change
    return status, accepted


def _completed_verify_outcome(
    *,
    plan: _KernelStagePlan,
    applied_changes: list[object],
    repair_summary: dict[str, object],
    final_verification: dict[str, object],
    status: str,
    accepted: bool,
) -> _KernelStageOutcome:
    return _stage_outcome(
        next_stage=plan.next_stage_proposal.proposed_stage,
        pending_approval=None,
        applied_changes=list(applied_changes),
        repair_summary=repair_summary,
        final_verification=final_verification,
        status=status,
        accepted=accepted,
        should_stop=True,
    )


def _stage_outcome(
    *,
    next_stage: RuntimeStage,
    pending_approval: dict[str, object] | None,
    applied_changes: list[object],
    repair_summary: dict[str, object],
    final_verification: dict[str, object],
    status: str,
    accepted: bool,
    should_stop: bool,
) -> _KernelStageOutcome:
    return _KernelStageOutcome(
        next_stage=next_stage,
        pending_approval=pending_approval,
        applied_changes=applied_changes,
        repair_summary=repair_summary,
        final_verification=final_verification,
        status=status,
        accepted=accepted,
        should_stop=should_stop,
    )
def _terminal_stage_outcome(
    runtime: CodingAgentExecutionRuntime,
    request: ExecutionRequest,
    edit_intent,
    resume_state: _KernelResumeState,
    plan: _KernelStagePlan,
    applied_changes: list[object],
) -> _KernelStageOutcome:
    return _KernelStageOutcome(
        next_stage="completed",
        pending_approval=None,
        applied_changes=list(applied_changes),
        repair_summary=dict(resume_state.repair_summary),
        final_verification=dict(resume_state.final_verification),
        status="blocked",
        accepted=False,
        should_stop=True,
    )


def _verification_continuation_notes(resume_state: _KernelResumeState) -> list[str]:
    notes: list[str] = []
    if resume_state.verification_command:
        notes.append("Resume reused the previously planned verification command.")
    if resume_state.recent_observations:
        latest = resume_state.recent_observations[-1]
        kind = latest.get("kind")
        if kind:
            notes.append(f"Resume continued from observation kind={kind}.")
    if resume_state.remaining_retry_budget is not None:
        notes.append(f"Resume selected remaining retry budget={resume_state.remaining_retry_budget}.")
    return notes


def _propose_next_stage(
    *,
    stage_strategy: _KernelStageStrategy,
    stage_cursor: RuntimeStage,
    planner_context: _KernelPlannerContext,
    resume_state: _KernelResumeState,
) -> _KernelNextStageProposal:
    return stage_strategy.propose_next_stage(
        current_stage=stage_cursor,
        planner_context=planner_context,
        resume_state=resume_state,
    )


def _select_next_stage(*, next_stage_proposal: _KernelNextStageProposal) -> _KernelStageSelection:
    return _KernelStageSelection(
        stage=next_stage_proposal.current_stage,
        outcome=next_stage_proposal.disposition,
        next_stage=next_stage_proposal.proposed_stage,
        reason=next_stage_proposal.reason,
    )


def _proposal_stage_selection(
    action_selection: _KernelActionSelection | None,
    next_stage_proposal: _KernelNextStageProposal,
) -> _KernelStageSelection:
    return _select_next_stage(next_stage_proposal=next_stage_proposal)


def _edit_stage_selection(
    action_selection: _KernelActionSelection | None,
    next_stage_proposal: _KernelNextStageProposal,
) -> _KernelStageSelection:
    if action_selection is None:
        return _select_next_stage(next_stage_proposal=next_stage_proposal)
    return _select_edit_stage(
        edit_selection=action_selection,
        next_stage_proposal=next_stage_proposal,
    )


def _build_next_stage_candidates(
    *,
    stage_strategy: _KernelStageStrategy,
    stage_cursor: RuntimeStage,
    planner_context: _KernelPlannerContext,
    resume_state: _KernelResumeState,
) -> list[_KernelNextStageCandidate]:
    return stage_strategy.candidate_generator(
        planner_context=planner_context,
        resume_state=resume_state,
    )


def _explore_stage_strategy() -> _KernelStageStrategy:
    return _KernelStageStrategy(
        candidate_generator=_explore_candidates_via_strategy,
        ranking_enabled=_explore_ranking_enabled,
        rank_adjustment=_explore_rank_adjustment,
        action_selector=_no_action_selection,
        stage_selector=_proposal_stage_selection,
        executor=_continue_without_side_effects_stage,
        outcomes=_KernelStageOutcomeSemantics(
            continue_outcome=_continue_stage_outcome,
        ),
    )


def _edit_stage_strategy() -> _KernelStageStrategy:
    return _KernelStageStrategy(
        candidate_generator=_edit_candidates_via_strategy,
        ranking_enabled=_edit_ranking_enabled,
        rank_adjustment=_edit_rank_adjustment,
        action_selector=_select_edit_action,
        stage_selector=_edit_stage_selection,
        executor=_execute_edit_stage,
        outcomes=_KernelStageOutcomeSemantics(
            pause=_paused_edit_outcome,
            block=_blocked_edit_outcome,
            continue_outcome=_applied_edit_outcome,
        ),
    )


def _verify_stage_strategy() -> _KernelStageStrategy:
    return _KernelStageStrategy(
        candidate_generator=_verify_candidates_via_strategy,
        ranking_enabled=_verify_ranking_enabled,
        rank_adjustment=_verify_rank_adjustment,
        action_selector=_select_verify_action,
        stage_selector=_proposal_stage_selection,
        executor=_execute_verify_stage,
        outcomes=_KernelStageOutcomeSemantics(
            pause=_paused_verify_outcome,
            block=_blocked_verify_resume_outcome,
            complete=_completed_verify_outcome,
        ),
    )


def _stage_strategy_map() -> dict[RuntimeStage, _KernelStageStrategy]:
    return {
        "explore": _explore_stage_strategy(),
        "edit": _edit_stage_strategy(),
        "verify": _verify_stage_strategy(),
    }


def _terminal_stage_strategy(stage_cursor: RuntimeStage) -> _KernelStageStrategy:
    return _KernelStageStrategy(
        candidate_generator=lambda planner_context, resume_state: _terminal_stage_candidates(stage_cursor),
        ranking_enabled=_ranking_disabled,
        rank_adjustment=_zero_rank_adjustment,
        action_selector=_no_action_selection,
        stage_selector=_proposal_stage_selection,
        executor=_terminal_stage_outcome,
        outcomes=_KernelStageOutcomeSemantics(
            complete=_terminal_stage_outcome,
        ),
    )


def _stage_strategy(stage_cursor: RuntimeStage) -> _KernelStageStrategy:
    return _stage_strategy_map().get(stage_cursor, _terminal_stage_strategy(stage_cursor))


def _next_stage_candidate_generator(
    stage_strategy: _KernelStageStrategy,
) -> Callable[[_KernelPlannerContext, _KernelResumeState], list[_KernelNextStageCandidate]]:
    return stage_strategy.candidate_generator


def _terminal_stage_candidates(stage_cursor: RuntimeStage) -> list[_KernelNextStageCandidate]:
    return [
        _candidate(
            candidate_id=f"{stage_cursor}_complete",
            stage="completed",
            disposition="complete",
            reason="Kernel reached a terminal stage.",
        )
    ]


def _explore_candidates_via_strategy(
    planner_context: _KernelPlannerContext,
    resume_state: _KernelResumeState,
) -> list[_KernelNextStageCandidate]:
    return _explore_next_stage_candidates(planner_context)


def _edit_candidates_via_strategy(
    planner_context: _KernelPlannerContext,
    resume_state: _KernelResumeState,
) -> list[_KernelNextStageCandidate]:
    return _edit_next_stage_candidates(planner_context)


def _verify_candidates_via_strategy(
    planner_context: _KernelPlannerContext,
    resume_state: _KernelResumeState,
) -> list[_KernelNextStageCandidate]:
    return _verify_next_stage_candidates(
        planner_context,
        resume_state=resume_state,
    )


def _proposal_from_selected_candidate(
    *,
    current_stage: RuntimeStage,
    candidates: list[_KernelNextStageCandidate],
    selected_candidate: _KernelNextStageCandidate,
) -> _KernelNextStageProposal:
    return _KernelNextStageProposal(
        current_stage=current_stage,
        proposed_stage=selected_candidate.stage,
        disposition=selected_candidate.disposition,
        reason=selected_candidate.reason,
        candidates=candidates,
        selected_candidate_id=selected_candidate.candidate_id,
    )


def _candidate(
    *,
    candidate_id: str,
    stage: RuntimeStage,
    disposition: str,
    reason: str,
) -> _KernelNextStageCandidate:
    return _KernelNextStageCandidate(
        candidate_id=candidate_id,
        stage=stage,
        disposition=disposition,
        reason=reason,
    )


def _candidate_pair(
    first: _KernelNextStageCandidate,
    second: _KernelNextStageCandidate,
) -> list[_KernelNextStageCandidate]:
    return [first, second]


def _path_vs_terminal_candidates(
    *,
    path_candidate_id: str,
    path_stage: RuntimeStage,
    path_disposition: str,
    path_reason: str,
    terminal_candidate_id: str,
    terminal_stage: RuntimeStage,
    terminal_disposition: str,
    terminal_reason: str,
) -> list[_KernelNextStageCandidate]:
    return _candidate_pair(
        _candidate(
            candidate_id=path_candidate_id,
            stage=path_stage,
            disposition=path_disposition,
            reason=path_reason,
        ),
        _candidate(
            candidate_id=terminal_candidate_id,
            stage=terminal_stage,
            disposition=terminal_disposition,
            reason=terminal_reason,
        ),
    )


def _approval_candidates(
    *,
    wait_candidate_id: str,
    wait_stage: RuntimeStage,
    wait_reason: str,
    proceed_candidate_id: str,
    proceed_stage: RuntimeStage,
    proceed_reason: str,
) -> list[_KernelNextStageCandidate]:
    return _path_vs_terminal_candidates(
        path_candidate_id=wait_candidate_id,
        path_stage=wait_stage,
        path_disposition="pause",
        path_reason=wait_reason,
        terminal_candidate_id=proceed_candidate_id,
        terminal_stage=proceed_stage,
        terminal_disposition="advance",
        terminal_reason=proceed_reason,
    )


def _history_complete_candidates(
    *,
    complete_candidate_id: str,
    complete_reason: str,
    alternate_candidate_id: str,
    alternate_stage: RuntimeStage,
    alternate_reason: str,
) -> list[_KernelNextStageCandidate]:
    return _path_vs_terminal_candidates(
        path_candidate_id=complete_candidate_id,
        path_stage="completed",
        path_disposition="complete",
        path_reason=complete_reason,
        terminal_candidate_id=alternate_candidate_id,
        terminal_stage=alternate_stage,
        terminal_disposition="advance",
        terminal_reason=alternate_reason,
    )


def _advance_or_complete_candidates(
    *,
    advance_candidate: _KernelNextStageCandidate,
    complete_candidate: _KernelNextStageCandidate,
) -> list[_KernelNextStageCandidate]:
    return _candidate_pair(
        advance_candidate,
        complete_candidate,
    )


def _complete_or_retry_candidates(
    *,
    complete_candidate: _KernelNextStageCandidate,
    retry_candidate: _KernelNextStageCandidate,
) -> list[_KernelNextStageCandidate]:
    return _candidate_pair(
        complete_candidate,
        retry_candidate,
    )


def _block_or_retry_candidates(
    *,
    block_candidate: _KernelNextStageCandidate,
    retry_candidate: _KernelNextStageCandidate,
) -> list[_KernelNextStageCandidate]:
    return _candidate_pair(
        block_candidate,
        retry_candidate,
    )


def _verify_complete_candidate(
    *,
    planner_context: _KernelPlannerContext,
    variant: str,
    reason: str | None = None,
) -> _KernelNextStageCandidate:
    resolved_reason = reason or (
        "Verification remains the terminal stage once approval is satisfied."
        if variant == "approval"
        else "Continuation state already records a satisfied verification outcome, so the planner can complete directly."
        if variant == "history"
        else "Applied changes and recent observations indicate verification is the natural terminal hop in the current kernel."
        if variant == "observed_change"
        else "Verification is the terminal stage in the current bounded execution kernel."
    )
    candidate_id = (
        "verify_complete"
        if variant == "approval"
        else "verify_complete_from_history"
        if variant == "history"
        else "verify_complete_after_observed_change"
        if variant == "observed_change"
        else "verify_complete"
    )
    if planner_context.verification_status in {"passed", "skipped"} and variant == "default":
        candidate_id = "verify_complete_from_history"
    return _candidate(
        candidate_id=candidate_id,
        stage="completed",
        disposition="complete",
        reason=resolved_reason,
    )


def _explore_complete_candidate(
    *,
    planner_context: _KernelPlannerContext,
    reason: str | None = None,
) -> _KernelNextStageCandidate:
    resolved_reason = reason or (
        "Observed repository context is sufficient for a low-risk read-only path to terminate without entering bounded edit execution."
        if planner_context.latest_observation_kind in {"repo_report", "execution_context"}
        else "Low-risk read-only exploration could terminate without entering bounded edit execution."
    )
    candidate_id = (
        "explore_complete_from_context"
        if planner_context.latest_observation_kind in {"repo_report", "execution_context"}
        else "explore_stop_completed"
    )
    return _candidate(
        candidate_id=candidate_id,
        stage="completed",
        disposition="complete",
        reason=resolved_reason,
    )


def _edit_verify_candidate(
    *,
    planner_context: _KernelPlannerContext,
    variant: str,
    reason: str | None = None,
) -> _KernelNextStageCandidate:
    resolved_reason = reason or (
        "Edit stage would normally continue to verification after bounded mutation."
        if variant == "approval"
        else "Bounded file mutation has already been applied in continuation state, so verification is the next hop."
        if variant == "after_change"
        else "Prepared edit context is sufficient for the current bounded flow, so verification is the next governed hop."
        if planner_context.action_feasibility == "prepare_only"
        else "Edit stage is next to apply or confirm bounded changes before verification."
    )
    candidate_id = (
        "edit_to_verify"
        if variant == "approval"
        else "edit_to_verify_after_change"
        if variant == "after_change"
        else "edit_to_verify"
    )
    return _candidate(
        candidate_id=candidate_id,
        stage="verify",
        disposition="advance",
        reason=resolved_reason,
    )


def _edit_complete_candidate(
    *,
    planner_context: _KernelPlannerContext,
    variant: str,
    reason: str | None = None,
) -> _KernelNextStageCandidate:
    resolved_reason = reason or (
        "A future planner could terminate after confirmed bounded changes if verification were explicitly waived."
        if variant == "after_change"
        else "Low-risk preparation can terminate without entering verification when the planner already has sufficient context."
        if planner_context.action_feasibility == "prepare_only"
        else "Edit stage could terminate early if a later planner decides verification is unnecessary."
    )
    candidate_id = (
        "edit_complete_after_change"
        if variant == "after_change"
        else "edit_complete_after_prepare"
        if planner_context.action_feasibility == "prepare_only"
        else "edit_stop_completed"
    )
    return _candidate(
        candidate_id=candidate_id,
        stage="completed",
        disposition="complete",
        reason=resolved_reason,
    )


def _explore_next_stage_candidates(
    planner_context: _KernelPlannerContext,
) -> list[_KernelNextStageCandidate]:
    complete_candidate = _explore_complete_candidate(planner_context=planner_context)
    return _advance_or_complete_candidates(
        advance_candidate=_candidate(
            candidate_id="explore_to_edit",
            stage="edit",
            disposition="advance",
            reason="Repository exploration completed; edit planning is the next bounded stage.",
        ),
        complete_candidate=complete_candidate,
    )


def _edit_next_stage_candidates(
    planner_context: _KernelPlannerContext,
) -> list[_KernelNextStageCandidate]:
    if planner_context.approval_required and not planner_context.approval_resolved:
        proceed_candidate = _edit_verify_candidate(
            planner_context=planner_context,
            variant="approval",
        )
        return _approval_candidates(
            wait_candidate_id="edit_wait_approval",
            wait_stage="edit",
            wait_reason="Edit stage requires human approval before bounded file mutation can continue.",
            proceed_candidate_id=proceed_candidate.candidate_id,
            proceed_stage=proceed_candidate.stage,
            proceed_reason=proceed_candidate.reason,
        )
    if planner_context.edit_mode == "direct_apply" and planner_context.applied_change_count > 0:
        verify_candidate = _edit_verify_candidate(
            planner_context=planner_context,
            variant="after_change",
        )
        complete_candidate = _edit_complete_candidate(
            planner_context=planner_context,
            variant="after_change",
        )
        return _advance_or_complete_candidates(
            advance_candidate=verify_candidate,
            complete_candidate=complete_candidate,
        )
    verify_candidate = _edit_verify_candidate(
        planner_context=planner_context,
        variant="default",
    )
    complete_candidate = _edit_complete_candidate(
        planner_context=planner_context,
        variant="default",
    )
    return _advance_or_complete_candidates(
        advance_candidate=verify_candidate,
        complete_candidate=complete_candidate,
    )


def _verify_next_stage_candidates(
    planner_context: _KernelPlannerContext,
    *,
    resume_state: _KernelResumeState,
) -> list[_KernelNextStageCandidate]:
    if planner_context.approval_required and not planner_context.approval_resolved:
        approval_complete = _verify_complete_candidate(
            planner_context=planner_context,
            variant="approval",
        )
        return _approval_candidates(
            wait_candidate_id="verify_wait_approval",
            wait_stage="verify",
            wait_reason="Verification stage requires human approval before bounded command execution can continue.",
            proceed_candidate_id=approval_complete.candidate_id,
            proceed_stage="completed",
            proceed_reason=approval_complete.reason,
        )
    if resume_state.should_block_verify_resume:
        return _block_or_retry_candidates(
            block_candidate=_candidate(
                candidate_id="verify_block_completed",
                stage="completed",
                disposition="block",
                reason="Continuation state indicates verification already failed and remaining retry budget is exhausted.",
            ),
            retry_candidate=_candidate(
                candidate_id="verify_retry_same_stage",
                stage="verify",
                disposition="advance",
                reason="Verification could stay active if future planner logic decides another retry is allowed.",
            ),
        )
    if planner_context.verification_status in {"passed", "skipped"}:
        history_complete = _verify_complete_candidate(
            planner_context=planner_context,
            variant="history",
        )
        return _complete_or_retry_candidates(
            complete_candidate=history_complete,
            retry_candidate=_candidate(
                candidate_id="verify_repeat_same_stage",
                stage="verify",
                disposition="advance",
                reason="A future planner could choose to re-run verification despite the recorded satisfied outcome.",
            ),
        )
    if planner_context.recent_observation_count > 0 and planner_context.applied_change_count > 0:
        observed_complete = _verify_complete_candidate(
            planner_context=planner_context,
            variant="observed_change",
        )
        return _complete_or_retry_candidates(
            complete_candidate=observed_complete,
            retry_candidate=_candidate(
                candidate_id="verify_retry_same_stage",
                stage="verify",
                disposition="advance",
                reason="Verification could remain active if future planner logic decides another bounded step is required.",
            ),
        )
    default_complete = _verify_complete_candidate(
        planner_context=planner_context,
        variant="default",
    )
    return _complete_or_retry_candidates(
        complete_candidate=default_complete,
        retry_candidate=_candidate(
            candidate_id="verify_retry_same_stage",
            stage="verify",
            disposition="advance",
            reason="Verification could remain active if future planner logic decides another bounded step is required.",
        ),
    )


def _select_next_stage_candidate(
    candidates: list[_KernelNextStageCandidate],
    *,
    planner_context: _KernelPlannerContext | None = None,
    stage_strategy: _KernelStageStrategy | None = None,
) -> _KernelNextStageCandidate:
    if not candidates:
        return _KernelNextStageCandidate(
            candidate_id="fallback_completed",
            stage="completed",
            disposition="complete",
            reason="No stage candidates were available; fall back to terminal completion.",
        )
    if planner_context is None:
        return candidates[0]
    strategy = stage_strategy or _stage_strategy(planner_context.stage_cursor)
    if not _ranking_enabled_for_stage(planner_context, stage_strategy=strategy):
        return candidates[0]
    ranked = sorted(
        candidates,
        key=lambda candidate: _candidate_rank(
            candidate,
            planner_context=planner_context,
            stage_strategy=strategy,
        ),
    )
    return ranked[0]


def _ranking_enabled_for_stage(
    planner_context: _KernelPlannerContext,
    *,
    stage_strategy: _KernelStageStrategy,
) -> bool:
    return stage_strategy.ranking_enabled(planner_context)


def _candidate_rank(
    candidate: _KernelNextStageCandidate,
    *,
    planner_context: _KernelPlannerContext,
    stage_strategy: _KernelStageStrategy,
) -> tuple[int, int, int, str]:
    disposition_priority = {"pause": 0, "block": 1, "complete": 2, "advance": 3}
    stage_priority = {
        "completed": 0,
        planner_context.stage_cursor: 1,
        "verify": 2,
        "edit": 3,
        "explore": 4,
    }
    score = disposition_priority.get(candidate.disposition, 9)
    score += _stage_specific_rank_adjustment(
        candidate,
        planner_context=planner_context,
        stage_strategy=stage_strategy,
    )
    return (
        score,
        stage_priority.get(candidate.stage, 9),
        len(candidate.reason),
        candidate.candidate_id,
    )


def _stage_specific_rank_adjustment(
    candidate: _KernelNextStageCandidate,
    *,
    planner_context: _KernelPlannerContext,
    stage_strategy: _KernelStageStrategy,
) -> int:
    return stage_strategy.rank_adjustment(candidate, planner_context=planner_context)


def _ranking_disabled(planner_context: _KernelPlannerContext) -> bool:
    return False


def _no_action_selection(planner_context: _KernelPlannerContext) -> _KernelActionSelection | None:
    return None


def _zero_rank_adjustment(
    candidate: _KernelNextStageCandidate,
    *,
    planner_context: _KernelPlannerContext,
) -> int:
    return 0


def _explore_ranking_enabled(planner_context: _KernelPlannerContext) -> bool:
    return (
        planner_context.route_risk_level == "low"
        and planner_context.edit_mode == "report_first"
        and planner_context.recent_observation_count > 0
    )


def _edit_ranking_enabled(planner_context: _KernelPlannerContext) -> bool:
    return (
        planner_context.action_feasibility == "prepare_only"
        and planner_context.route_risk_level == "low"
        and planner_context.recent_observation_count > 0
    )


def _verify_ranking_enabled(planner_context: _KernelPlannerContext) -> bool:
    if planner_context.approval_required and not planner_context.approval_resolved:
        return False
    if planner_context.should_block_verify_resume:
        return False
    return (
        planner_context.verification_status in {"passed", "skipped"}
        or (planner_context.repair_outcome == "failed" and planner_context.latest_observation_kind == "verification")
    )


def _explore_rank_adjustment(
    candidate: _KernelNextStageCandidate,
    *,
    planner_context: _KernelPlannerContext,
) -> int:
    score = 0
    if planner_context.route_risk_level == "low" and candidate.stage == "completed":
        score -= 2
    if planner_context.latest_observation_kind in {"repo_report", "execution_context"} and candidate.stage == "completed":
        score -= 1
    return score


def _edit_rank_adjustment(
    candidate: _KernelNextStageCandidate,
    *,
    planner_context: _KernelPlannerContext,
) -> int:
    score = 0
    if planner_context.action_feasibility == "prepare_only" and candidate.stage == "completed":
        score -= 2
    if planner_context.route_risk_level == "low" and candidate.disposition == "complete":
        score -= 1
    if planner_context.latest_observation_kind in {"edit_intent", "execution_context"} and candidate.stage == "completed":
        score -= 1
    return score


def _verify_rank_adjustment(
    candidate: _KernelNextStageCandidate,
    *,
    planner_context: _KernelPlannerContext,
) -> int:
    score = 0
    if planner_context.latest_observation_kind == "verification" and candidate.stage == "completed":
        score -= 1
    if planner_context.latest_observation_kind == "repair_summary" and candidate.disposition == "block":
        score -= 1
    if planner_context.verification_status in {"passed", "skipped"} and candidate.stage == "completed":
        score -= 2
    if planner_context.repair_outcome == "failed" and candidate.disposition == "block":
        score -= 2
    return score


def _select_edit_stage(
    *,
    edit_selection: _KernelActionSelection,
    next_stage_proposal: _KernelNextStageProposal,
) -> _KernelStageSelection:
    if edit_selection.action_type == "pause":
        return _KernelStageSelection(
            stage="edit",
            outcome="pause",
            next_stage=next_stage_proposal.proposed_stage,
            reason="Edit action selection determined the bounded mutation is waiting on approval before execution.",
        )
    if edit_selection.action_type == "block":
        return _KernelStageSelection(
            stage="edit",
            outcome="block",
            next_stage=next_stage_proposal.proposed_stage,
            reason="Edit action selection determined the bounded mutation cannot safely execute.",
        )
    return _KernelStageSelection(
        stage="edit",
        outcome=next_stage_proposal.disposition,
        next_stage=next_stage_proposal.proposed_stage,
        reason="Edit stage is next to apply or confirm bounded changes before verification.",
    )


def _select_edit_action(planner_context: _KernelPlannerContext) -> _KernelActionSelection:
    if planner_context.approval_required and not planner_context.approval_resolved:
        return _KernelActionSelection(
            stage="edit",
            action_type="pause",
            source="approval_policy",
            selected={
                "mode": planner_context.edit_mode,
                "operation_count": planner_context.operation_count,
                "pending_approval_stage": planner_context.pending_approval_stage,
            },
            reason="Edit action is paused until the required human approval is resolved.",
        )
    if planner_context.edit_mode == "direct_apply" and planner_context.operation_count == 0:
        return _KernelActionSelection(
            stage="edit",
            action_type="block",
            source="invalid_intent",
            selected={
                "mode": planner_context.edit_mode,
                "operation_count": planner_context.operation_count,
            },
            reason="Direct-apply edit intent did not contain executable bounded operations.",
        )
    boundary_violation = _edit_boundary_violation(
        planner_context.operation_paths,
        workspace_root=Path(planner_context.workspace_root),
    )
    if boundary_violation is not None:
        return _KernelActionSelection(
            stage="edit",
            action_type="block",
            source="boundary_policy",
            selected={
                "mode": planner_context.edit_mode,
                "operation_count": planner_context.operation_count,
                "path": boundary_violation,
                "boundary_policy": "workspace_root_only",
            },
            reason="Edit action was blocked before mutation because the selected file path escapes the workspace root.",
        )
    return _KernelActionSelection(
        stage="edit",
        action_type="file_mutation" if planner_context.edit_mode == "direct_apply" else "edit_prepare",
        source="explicit_operations" if planner_context.edit_mode == "direct_apply" else "bounded_context",
        selected={
            "mode": planner_context.edit_mode,
            "operation_count": planner_context.operation_count,
        },
        reason="Edit action follows explicit bounded operations when present, otherwise stays in report-first preparation mode.",
    )


def _edit_boundary_violation(
    candidate_paths: list[str],
    *,
    workspace_root: Path,
) -> str | None:
    for raw_path in candidate_paths:
        raw_path = str(raw_path).strip()
        if not raw_path:
            continue
        candidate = workspace_root / raw_path
        if not _is_within_workspace(workspace_root, candidate):
            return raw_path
    return None


def _is_within_workspace(workspace_root: Path, candidate: Path) -> bool:
    try:
        workspace = workspace_root.resolve()
        target = candidate.resolve(strict=False)
    except OSError:
        return False
    try:
        target.relative_to(workspace)
    except ValueError:
        return False
    return True


def _approval_required_for_stage(
    runtime: CodingAgentExecutionRuntime,
    *,
    stage_cursor: RuntimeStage,
    edit_mode: str,
    target_paths: list[str],
) -> bool:
    if not runtime.enforce_approvals:
        return False
    if stage_cursor == "edit":
        return edit_mode == "direct_apply"
    if stage_cursor == "verify":
        return bool(target_paths)
    return False


def _action_feasibility_for_stage(
    *,
    stage_cursor: RuntimeStage,
    edit_mode: str,
    operation_count: int,
    operation_paths: list[str],
    target_paths: list[str],
    workspace_root: Path,
    should_block_verify_resume: bool,
) -> str:
    if stage_cursor == "edit":
        if edit_mode == "direct_apply" and operation_count == 0:
            return "invalid_intent"
        if _edit_boundary_violation(operation_paths, workspace_root=workspace_root) is not None:
            return "boundary_blocked"
        if edit_mode == "direct_apply":
            return "ready_to_mutate"
        return "prepare_only"
    if stage_cursor == "verify":
        if should_block_verify_resume:
            return "retry_exhausted"
        if target_paths:
            return "ready_to_verify"
        return "no_targets"
    return "advance"


def _blocked_edit_repair_summary(edit_selection: _KernelActionSelection) -> dict[str, object]:
    return {
        "outcome": "blocked",
        "attempt_count": 0,
        "retry_budget": 0,
        "attempts": [],
        "recovery_recommendation": {
            "action": "human_review",
            "reason": edit_selection.source,
            "human_review_recommended": True,
        },
    }


def _select_verify_action(planner_context: _KernelPlannerContext) -> _KernelActionSelection:
    if planner_context.approval_required and not planner_context.approval_resolved:
        return _KernelActionSelection(
            stage="verify",
            action_type="pause",
            source="approval_policy",
            selected={
                "pending_approval_stage": planner_context.pending_approval_stage,
                "target_paths": list(planner_context.target_paths),
            },
            reason="Verification action is paused until the required human approval is resolved.",
        )
    if planner_context.should_block_verify_resume:
        return _KernelActionSelection(
            stage="verify",
            action_type="block",
            source="exhausted_recovery",
            selected={
                "remaining_retry_budget": planner_context.remaining_retry_budget,
                "latest_observation_kind": planner_context.latest_observation_kind,
            },
            reason="Verification is blocked because continuation state shows failure with no remaining retry budget.",
        )
    if planner_context.verification_command:
        return _KernelActionSelection(
            stage="verify",
            action_type="run_command",
            source="resume_context",
            selected={"command": list(planner_context.verification_command)},
            reason="Verification reused the planned command from continuation state.",
        )
    derived = _planned_verification_command(planner_context.target_paths)
    return _KernelActionSelection(
        stage="verify",
        action_type="run_command",
        source="derived_from_targets",
        selected={"command": list(derived)},
        reason="Verification command derived from bounded target paths in the current edit intent.",
    )


def _remaining_retry_budget(repair_summary: dict[str, object]) -> int | None:
    if not isinstance(repair_summary, dict):
        return None
    retry_budget = repair_summary.get("retry_budget")
    attempt_count = repair_summary.get("attempt_count")
    if not isinstance(retry_budget, int) or not isinstance(attempt_count, int):
        return None
    retries_already_used = max(attempt_count - 1, 0)
    return max(retry_budget - retries_already_used, 0)


def _should_block_verify_resume(
    *,
    final_verification: dict[str, object],
    repair_summary: dict[str, object],
    remaining_retry_budget: int | None,
) -> bool:
    if remaining_retry_budget != 0:
        return False
    status = final_verification.get("status")
    outcome = repair_summary.get("outcome")
    return status == "failed" or outcome == "failed"


def _planned_verification_command(target_paths: list[str] | object) -> list[str]:
    if not isinstance(target_paths, list) or not target_paths:
        return []
    return ["python3", "-m", "compileall", *[str(item) for item in target_paths if isinstance(item, str)]]


def _build_execution_steps(
    *,
    request: ExecutionRequest,
    repo_report: dict[str, object],
    context: dict[str, object],
    edit_intent: dict[str, object],
    applied_changes: list[dict[str, object]],
    final_verification: dict[str, object],
    repair_summary: dict[str, object],
    status: str,
    pending_approval: dict[str, object] | None = None,
) -> list[ExecutionStep]:
    repo_step = ExecutionStep(
        step_id=f"{request.turn_id or request.session_id or 'inline'}:explore",
        title="Explore repository context",
        kind="repo_exploration",
        status="completed",
        actions=[
            ActionRequest(
                action_id="explore-repo",
                action_type="repo_explore",
                description="Inspect repository paths relevant to the request.",
                parameters={"requirement": request.requirement},
                risk_level="low",
                requires_approval=False,
            )
        ],
        results=[
            ActionResult(
                action_id="explore-repo",
                action_type="repo_explore",
                status="completed",
                summary="Repository exploration report built.",
                payload=repo_report,
            )
        ],
        observations=[
            ObservationRecord(
                observation_id="obs-repo-report",
                kind="repo_report",
                summary="Candidate repository paths identified for bounded execution.",
                source="repo_explorer",
                payload=repo_report,
            ),
            ObservationRecord(
                observation_id="obs-context-package",
                kind="execution_context",
                summary="Execution context package assembled from route, session, and repository state.",
                source="context_builder",
                payload=context,
            ),
        ],
        approval=PendingApprovalState(reason="read_only_step", scope="repo_exploration"),
    )
    edit_requires_approval = edit_intent.get("mode") == "direct_apply"
    edit_risk = "high" if any(
        isinstance(item, dict) and str(item.get("kind", "")).lower() == "replace"
        for item in edit_intent.get("operations", [])
    ) else "medium" if edit_requires_approval else "low"
    edit_pending = isinstance(pending_approval, dict) and pending_approval.get("stage") == "edit"
    edit_status = (
        "pending" if edit_pending
        else "completed" if any(item.get("status") == "applied" for item in applied_changes)
        else "blocked" if edit_requires_approval else "completed"
    )
    edit_step = ExecutionStep(
        step_id=f"{request.turn_id or request.session_id or 'inline'}:edit",
        title="Build and apply bounded edit intent",
        kind="edit_execution",
        status=edit_status,
        actions=[
            ActionRequest(
                action_id="edit-intent",
                action_type="edit_prepare",
                description="Build bounded implementation intent from repository context.",
                parameters={"mode": edit_intent.get("mode"), "target_paths": list(edit_intent.get("target_paths", []))},
                risk_level="low" if not edit_requires_approval else "medium",
                requires_approval=False,
            ),
            ActionRequest(
                action_id="edit-apply",
                action_type="file_mutation",
                description="Apply bounded file mutations when direct edits are requested.",
                parameters={"operations": list(edit_intent.get("operations", []))},
                risk_level=edit_risk,
                requires_approval=edit_requires_approval,
            ),
        ],
        results=[
            ActionResult(
                action_id="edit-intent",
                action_type="edit_prepare",
                status="completed",
                summary=str(edit_intent.get("summary") or "Edit intent prepared."),
                payload=edit_intent,
            ),
            ActionResult(
                action_id="edit-apply",
                action_type="file_mutation",
                status="completed" if any(item.get("status") == "applied" for item in applied_changes) else "blocked" if edit_requires_approval else "skipped",
                summary="Bounded edit operations evaluated.",
                payload={
                    "applied_changes": applied_changes,
                    "governance": {
                        "workspace_root": repo_report.get("workspace_root"),
                        "risk_level": edit_risk,
                        "requires_approval": edit_requires_approval,
                        "boundary_policy": "workspace_root_only",
                    },
                },
            ),
        ],
        observations=[
            ObservationRecord(
                observation_id="obs-edit-intent",
                kind="edit_intent",
                summary="Runtime produced a bounded edit intent for the task.",
                source="edit_executor",
                payload=edit_intent,
            ),
            ObservationRecord(
                observation_id="obs-applied-changes",
                kind="applied_changes",
                summary="Runtime recorded the outcomes of bounded edit operations.",
                source="edit_executor",
                payload={"applied_changes": applied_changes},
            ),
        ],
        approval=PendingApprovalState(
            reason="file_mutation_requires_governance" if edit_requires_approval else "not_required",
            scope="edit_execution",
            status="pending" if edit_pending else "not_required",
            approval_id=str(pending_approval.get("approval_id")) if edit_pending and pending_approval.get("approval_id") else None,
        ),
    )
    planned_verification_command = _planned_verification_command(edit_intent.get("target_paths", []))
    verify_requires_approval = bool(final_verification.get("command")) or bool(planned_verification_command)
    verify_pending = isinstance(pending_approval, dict) and pending_approval.get("stage") == "verify"
    verify_step_status = (
        "pending" if verify_pending
        else "completed" if final_verification.get("status") in {"passed", "skipped"}
        else "blocked" if status == "blocked" else "failed"
    )
    verify_step = ExecutionStep(
        step_id=f"{request.turn_id or request.session_id or 'inline'}:verify",
        title="Verify bounded runtime result",
        kind="verification",
        status=verify_step_status,
        actions=[
            ActionRequest(
                action_id="verify-runtime",
                action_type="run_command",
                description="Run bounded verification commands over target paths.",
                parameters={"command": list(final_verification.get("command", planned_verification_command))},
                risk_level="high" if verify_requires_approval else "low",
                requires_approval=verify_requires_approval,
            )
        ],
        results=[
            ActionResult(
                action_id="verify-runtime",
                action_type="run_command",
                status=str(final_verification.get("status") or repair_summary.get("outcome") or "unknown"),
                summary="Verification loop completed.",
                payload={
                    "verification": final_verification,
                    "repair_summary": repair_summary,
                    "artifact": _verification_artifact_summary(final_verification),
                    "planned_command": planned_verification_command,
                    "governance": {
                        "workspace_root": repo_report.get("workspace_root"),
                        "risk_level": "high" if verify_requires_approval else "low",
                        "requires_approval": verify_requires_approval,
                        "boundary_policy": "workspace_root_only",
                    },
                },
            )
        ],
        observations=[
            ObservationRecord(
                observation_id="obs-verification",
                kind="verification",
                summary="Verification result captured for the final runtime attempt.",
                source="verify_loop",
                payload=final_verification,
            ),
            ObservationRecord(
                observation_id="obs-repair-summary",
                kind="repair_summary",
                summary="Repair loop summary captured for the execution result.",
                source="verify_loop",
                payload=repair_summary,
            ),
        ],
        approval=PendingApprovalState(
            reason="command_execution_requires_governance" if verify_requires_approval else "not_required",
            scope="verification",
            status="pending" if verify_pending else "not_required",
            approval_id=str(pending_approval.get("approval_id")) if verify_pending and pending_approval.get("approval_id") else None,
        ),
    )
    return [repo_step, edit_step, verify_step]


def _governance_summary(steps: list[ExecutionStep]) -> dict[str, object]:
    actions = [
        action.to_dict()
        for step in steps
        for action in step.actions
    ]
    result_governance = [
        result.payload.get("governance")
        for step in steps
        for result in step.results
        if isinstance(result.payload.get("governance"), dict)
    ]
    return {
        "workspace_boundary_policy": "workspace_root_only",
        "approval_required_action_count": sum(1 for action in actions if action.get("requires_approval") is True),
        "high_risk_action_count": sum(1 for action in actions if action.get("risk_level") == "high"),
        "result_governance": [dict(item) for item in result_governance if isinstance(item, dict)],
        "pending_approval_count": sum(
            1
            for step in steps
            if step.approval is not None and step.approval.status == "pending"
        ),
    }


def _build_step_decisions(
    *,
    steps: list[ExecutionStep],
    pending_approval: dict[str, object] | None,
    final_status: str,
) -> list[ExecutionStepDecision]:
    decisions: list[ExecutionStepDecision] = []
    for index, step in enumerate(steps):
        next_step = steps[index + 1] if index + 1 < len(steps) else None
        if isinstance(pending_approval, dict) and pending_approval.get("stage") == "edit" and step.kind == "edit_execution":
            decisions.append(
                ExecutionStepDecision(
                    step_id=step.step_id,
                    step_kind=step.kind,
                    disposition="pause",
                    reason="Await human approval before file mutation can continue.",
                    next_step_kind="edit_execution",
                    pending_approval=dict(pending_approval),
                )
            )
            continue
        if isinstance(pending_approval, dict) and pending_approval.get("stage") == "verify" and step.kind == "verification":
            decisions.append(
                ExecutionStepDecision(
                    step_id=step.step_id,
                    step_kind=step.kind,
                    disposition="pause",
                    reason="Await human approval before verification command can continue.",
                    next_step_kind="verification",
                    pending_approval=dict(pending_approval),
                )
            )
            continue
        if step.status == "blocked":
            decisions.append(
                ExecutionStepDecision(
                    step_id=step.step_id,
                    step_kind=step.kind,
                    disposition="block",
                    reason="Step ended in a blocked state and needs recovery or operator intervention.",
                    next_step_kind=next_step.kind if next_step is not None else None,
                )
            )
            continue
        if next_step is not None:
            decisions.append(
                ExecutionStepDecision(
                    step_id=step.step_id,
                    step_kind=step.kind,
                    disposition="continue",
                    reason=f"Step completed; continue to {next_step.kind}.",
                    next_step_kind=next_step.kind,
                )
            )
            continue
        decisions.append(
            ExecutionStepDecision(
                step_id=step.step_id,
                step_kind=step.kind,
                disposition="complete" if final_status == "completed" else "block",
                reason="Execution has reached its terminal step." if final_status == "completed" else "Execution finished in a non-completed terminal state.",
                next_step_kind=None,
            )
        )
    return decisions


def _next_step_contract(
    *,
    decisions: list[ExecutionStepDecision],
    status: str,
    pending_approval: dict[str, object] | None,
    resume_context: dict[str, object] | None = None,
) -> dict[str, object]:
    active: ExecutionStepDecision | None = None
    if isinstance(pending_approval, dict):
        pending_stage = str(pending_approval.get("stage") or "")
        target_kind = "edit_execution" if pending_stage == "edit" else "verification" if pending_stage == "verify" else None
        if target_kind is not None:
            active = next((decision for decision in decisions if decision.step_kind == target_kind), None)
    if active is None:
        active = next(
            (decision for decision in reversed(decisions) if decision.disposition in {"pause", "block", "complete"}),
            decisions[-1] if decisions else None,
        )
    resume_reason = _resume_reason_hint(resume_context)
    return {
        "status": status,
        "current_disposition": active.disposition if active is not None else "complete",
        "current_step_kind": active.step_kind if active is not None else None,
        "next_step_kind": active.next_step_kind if active is not None else None,
        "reason": resume_reason or (active.reason if active is not None else "No further steps recorded."),
        "pending_approval": dict(pending_approval) if isinstance(pending_approval, dict) else None,
    }


def _artifact_summary(steps: list[ExecutionStep]) -> dict[str, object]:
    artifacts = [
        result.payload.get("artifact")
        for step in steps
        for result in step.results
        if isinstance(result.payload.get("artifact"), dict)
    ]
    observation_artifacts = [
        observation.payload.get("artifact")
        for step in steps
        for observation in step.observations
        if isinstance(observation.payload.get("artifact"), dict)
    ]
    return {
        "artifact_count": len(artifacts) + len(observation_artifacts),
        "artifacts": [
            *[dict(item) for item in artifacts if isinstance(item, dict)],
            *[dict(item) for item in observation_artifacts if isinstance(item, dict)],
        ],
    }


def _resume_context_payload(
    *,
    request: ExecutionRequest,
    steps: list[ExecutionStep],
    final_verification: dict[str, object],
    repair_summary: dict[str, object],
) -> dict[str, object]:
    recent_observations = _compact_observation_window(
        _structured_observation_records(steps=steps),
        preserve_recent=4,
    )
    planned_command: list[str] = []
    if len(steps) >= 3:
        verify_actions = steps[2].actions
        if verify_actions:
            parameters = verify_actions[0].parameters
            if isinstance(parameters.get("command"), list):
                planned_command = [str(item) for item in parameters.get("command", []) if isinstance(item, str)]
    return {
        "resume_kind": request.resume_kind or "fresh",
        "recent_observations": recent_observations,
        "verification": dict(final_verification),
        "repair_summary": dict(repair_summary),
        "planned_verification_command": planned_command,
    }


def _resume_reason_hint(resume_context: dict[str, object] | None) -> str | None:
    if not isinstance(resume_context, dict):
        return None
    repair_summary = resume_context.get("repair_summary", {})
    if isinstance(repair_summary, dict):
        recommendation = repair_summary.get("recovery_recommendation", {})
        if isinstance(recommendation, dict):
            action = recommendation.get("action")
            reason = recommendation.get("reason")
            if action or reason:
                return f"Resume context: action={action or 'continue'} reason={reason or 'n/a'}"
    observations = resume_context.get("recent_observations", [])
    if isinstance(observations, list) and observations:
        latest = observations[-1] if isinstance(observations[-1], dict) else {}
        if latest:
            return f"Resume context: latest observation={latest.get('kind') or 'unknown'}"
    return None


def _execution_history_summary(
    *,
    request: ExecutionRequest,
    status: str,
    steps: list[ExecutionStep],
    pending_approval: dict[str, object] | None,
) -> dict[str, object]:
    artifacts = _artifact_summary(steps)
    return {
        "objective": request.requirement,
        "status": status,
        "completed_steps": [step.kind for step in steps if step.status == "completed"],
        "pending_steps": [step.kind for step in steps if step.status == "pending"],
        "blocked_steps": [step.kind for step in steps if step.status == "blocked"],
        "pending_approval": dict(pending_approval) if isinstance(pending_approval, dict) else None,
        "artifact_count": artifacts.get("artifact_count", 0),
        "artifact_ids": [
            item.get("artifact_id")
            for item in artifacts.get("artifacts", [])
            if isinstance(item, dict) and item.get("artifact_id")
        ],
        "latest_recovery_hint": "No approval gate pending; continue with the next coding step.",
    }


def _compressed_execution_context(
    *,
    request: ExecutionRequest,
    status: str,
    steps: list[ExecutionStep],
    payload: dict[str, object],
    pending_approval: dict[str, object] | None,
) -> dict[str, object]:
    resume_context = payload.get("resume_context", {}) if isinstance(payload.get("resume_context"), dict) else {}
    history = payload.get("execution_history_summary", {}) if isinstance(payload.get("execution_history_summary"), dict) else {}
    artifact_summary = payload.get("artifact_summary", {}) if isinstance(payload.get("artifact_summary"), dict) else {}
    execution_context = payload.get("execution_context", {}) if isinstance(payload.get("execution_context"), dict) else {}
    context_selection = payload.get("context_selection", {}) if isinstance(payload.get("context_selection"), dict) else {}
    compaction_state = payload.get("compaction_state", {}) if isinstance(payload.get("compaction_state"), dict) else {}
    session_context = (
        execution_context.get("session_context", {})
        if isinstance(execution_context.get("session_context"), dict)
        else {}
    )
    recent_steps = [
        {
            "step_id": step.step_id,
            "kind": step.kind,
            "status": step.status,
            "title": step.title,
            "latest_action": step.actions[-1].action_type if step.actions else None,
        }
        for step in steps[-3:]
    ]
    structured_observations = _compact_observation_window(
        _structured_observation_records(steps=steps),
        preserve_recent=3,
    )
    artifact_refs = [
        {
            "artifact_id": item.get("artifact_id"),
            "path": item.get("path"),
            "format": item.get("ref", {}).get("format") if isinstance(item.get("ref"), dict) else None,
        }
        for item in artifact_summary.get("artifacts", [])
        if isinstance(item, dict)
    ]
    return CompressedExecutionContext(
        objective=request.requirement,
        session_context=dict(session_context),
        current_status=status,
        recent_steps=recent_steps,
        summarized_history={
            "completed_steps": list(history.get("completed_steps", [])),
            "pending_steps": list(history.get("pending_steps", [])),
            "blocked_steps": list(history.get("blocked_steps", [])),
            "artifact_count": history.get("artifact_count", 0),
            "observation_count": len(structured_observations),
            "selected_memory_count": context_selection.get("retrieval", {}).get("selected_memory_count", 0)
            if isinstance(context_selection.get("retrieval"), dict)
            else 0,
            "compaction_stage": compaction_state.get("stage"),
            "masked_observation_count": compaction_state.get("masked_count", 0),
            "summarization_triggered": compaction_state.get("summarization_triggered", False),
        },
        artifact_refs=artifact_refs,
        pending_approval=dict(pending_approval) if isinstance(pending_approval, dict) else None,
        latest_recovery_hint=(
            _resume_reason_hint(resume_context)
            or (
                f"Resume from {pending_approval.get('stage')}"
                if isinstance(pending_approval, dict) and pending_approval.get("stage")
                else str(history.get("latest_recovery_hint") or "")
            )
        ),
    ).to_dict()


def _compaction_state(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    steps: list[ExecutionStep],
    context_selection: dict[str, object],
) -> dict[str, object]:
    observations = _structured_observation_records(steps=steps)
    observation_count = len(observations)
    preserve_recent = 3
    masked_count = max(observation_count - preserve_recent, 0)
    candidate_count = 0
    deterministic = context_selection.get("deterministic", {})
    retrieval = context_selection.get("retrieval", {})
    if isinstance(deterministic, dict) and isinstance(deterministic.get("selected_items"), list):
        candidate_count += len(deterministic.get("selected_items", []))
    if isinstance(retrieval, dict):
        candidate_count += int(retrieval.get("selected_memory_count", 0) or 0)
    light_compaction_applied = observation_count > preserve_recent or candidate_count >= 6
    summarization_triggered = observation_count >= 10 or candidate_count >= 12
    summarization_summary: str | None = None
    summarization_source: str | None = None
    if summarization_triggered:
        stage = "summarization_ready"
        reason = "Context volume exceeded the high-water mark for future LLM summarization."
        summarization_summary, summarization_source = _summarize_compacted_history(
            runtime,
            request=request,
            observations=observations,
        )
    elif masked_count > 0:
        stage = "observation_masking"
        reason = "Older observations were masked while preserving the most recent observation window."
    elif light_compaction_applied:
        stage = "light_compaction"
        reason = "Lightweight compaction reduced observation and candidate noise without LLM summarization."
    else:
        stage = "full_fidelity"
        reason = None
    return _CompactionState(
        stage=stage,
        observation_count=observation_count,
        preserve_recent=preserve_recent,
        masked_count=masked_count,
        light_compaction_applied=light_compaction_applied,
        summarization_triggered=summarization_triggered,
        summarization_reason=reason,
        summarization_summary=summarization_summary,
        summarization_source=summarization_source,
        system_prompt_compacted=False,
    ).to_dict()


def _summarize_compacted_history(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    observations: list[dict[str, object]],
) -> tuple[str, str]:
    config = EnvSlotFillConfig.from_env()
    historical_window = observations[:-3] if len(observations) > 3 else observations
    local_fallback = _local_compaction_summary(historical_window)
    if config is None:
        return local_fallback, "local_fallback"
    payload = {
        "model": config.model,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Summarize older execution history into a compact high-level digest. "
                    "Return only JSON with a single key summary. "
                    "Do not mention or alter the system prompt."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "requirement": request.requirement,
                        "historical_observations": historical_window,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    request_url = f"{config.base_url}/chat/completions"
    transport = runtime.summarizer_transport or _default_openai_compatible_transport
    try:
        response = transport(request_url, payload, headers, config.timeout_seconds)
        content = _extract_openai_message_content(response)
        parsed = json.loads(content) if content else {}
        summary = parsed.get("summary") if isinstance(parsed, dict) else None
        if isinstance(summary, str) and summary.strip():
            return summary.strip(), "llm"
    except Exception:
        pass
    return local_fallback, "local_fallback"


def _local_compaction_summary(observations: list[dict[str, object]]) -> str:
    if not observations:
        return "No older observations required summarization."
    kinds: list[str] = []
    for item in observations:
        kind = str(item.get("kind") or "unknown")
        if kind not in kinds:
            kinds.append(kind)
    return (
        f"Older execution history was compacted across {len(observations)} observations; "
        f"dominant kinds: {', '.join(kinds[:4])}."
    )


def _structured_observation_records(*, steps: list[ExecutionStep]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    seen_fingerprints: set[str] = set()
    for step in steps:
        for observation in step.observations:
            payload = dict(observation.payload)
            artifact = payload.get("artifact")
            payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            summary = _trim_text(observation.summary, limit=140)
            compact_payload = _compact_observation_payload(payload)
            fingerprint = f"{observation.kind}:{observation.source}:{payload_json}"
            deduplicated = fingerprint in seen_fingerprints
            seen_fingerprints.add(fingerprint)
            records.append(
                {
                    "observation_id": observation.observation_id,
                    "kind": observation.kind,
                    "source": observation.source,
                    "summary": summary,
                    "payload": compact_payload,
                    "has_artifact": isinstance(artifact, dict),
                    "deduplicated": deduplicated,
                    "masked": False,
                }
            )
    return records


def _compact_observation_payload(payload: dict[str, object]) -> dict[str, object]:
    compacted: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            compacted[key] = _trim_text(value, limit=400)
            continue
        if isinstance(value, list):
            compacted[key] = _compact_sequence(value)
            continue
        if isinstance(value, dict):
            compacted[key] = _compact_mapping(value)
            continue
        compacted[key] = value
    return compacted


def _compact_mapping(value: dict[str, object]) -> dict[str, object]:
    compacted: dict[str, object] = {}
    for key, item in value.items():
        if isinstance(item, str):
            compacted[key] = _trim_text(item, limit=240)
        elif isinstance(item, list):
            compacted[key] = _compact_sequence(item)
        elif isinstance(item, dict):
            compacted[key] = {
                nested_key: _trim_text(nested_value, limit=180) if isinstance(nested_value, str) else nested_value
                for nested_key, nested_value in item.items()
            }
        else:
            compacted[key] = item
    return compacted


def _compact_sequence(values: list[object]) -> list[object]:
    compacted: list[object] = []
    seen_strings: set[str] = set()
    for item in values:
        if isinstance(item, str):
            trimmed = _trim_text(item, limit=160)
            if trimmed in seen_strings:
                continue
            seen_strings.add(trimmed)
            compacted.append(trimmed)
        else:
            compacted.append(item)
        if len(compacted) >= 8:
            break
    return compacted


def _compact_observation_window(
    observations: list[dict[str, object]],
    *,
    preserve_recent: int,
) -> list[dict[str, object]]:
    if len(observations) <= preserve_recent:
        return observations
    compacted: list[dict[str, object]] = []
    cutoff = len(observations) - preserve_recent
    for index, observation in enumerate(observations):
        if index < cutoff:
            compacted.append(
                {
                    **observation,
                    "payload": {"masked": True, "keys": sorted(observation.get("payload", {}).keys()) if isinstance(observation.get("payload"), dict) else []},
                    "masked": True,
                }
            )
            continue
        compacted.append(observation)
    return compacted


def _trim_text(value: str, *, limit: int) -> str:
    normalized_lines = [line for line in value.splitlines() if line.strip()]
    normalized = "\n".join(normalized_lines)
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}...<trimmed>"


def _write_runtime_context(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    planner_context_trace: list[dict[str, object]],
    structured_observations: list[dict[str, object]],
    context_selection: dict[str, object],
    isolation_state: dict[str, object],
    status: str,
) -> None:
    if request.session_id and request.turn_id:
        runtime.scratchpad_store.append(
            session_id=request.session_id,
            turn_id=request.turn_id,
            kind="runtime_context",
            summary="Session-level runtime context snapshot for the current coding-agent turn.",
            payload={
                "status": status,
                "planner_context_trace": list(planner_context_trace),
                "context_selection": dict(context_selection),
                "isolation_state": dict(isolation_state),
                "observations": _compact_observation_window(structured_observations, preserve_recent=4),
            },
        )
        runtime.memory_store.append(
            namespace="coding_agent",
            session_id=request.session_id,
            record_type="runtime_preference_or_fact",
            summary=f"Coding-agent run status={status} for turn {request.turn_id}.",
            provider="coding_agent",
            payload={
                "turn_id": request.turn_id,
                "status": status,
                "requirement": request.requirement,
            },
            freshness="session",
        )


def _isolate_runtime_context(
    *,
    request: ExecutionRequest,
    context_selection: dict[str, object],
    edit_intent: dict[str, object],
) -> _IsolationState:
    target_paths = list(edit_intent.get("target_paths", [])) if isinstance(edit_intent.get("target_paths"), list) else []
    patch_plan = list(edit_intent.get("patch_plan", [])) if isinstance(edit_intent.get("patch_plan"), list) else []
    model_selected = (
        context_selection.get("model_driven", {}).get("selected_items", [])
        if isinstance(context_selection.get("model_driven"), dict)
        and isinstance(context_selection.get("model_driven", {}).get("selected_items"), list)
        else []
    )
    should_isolate = len(target_paths) > 3 or len(patch_plan) > 4 or len(model_selected) > 2
    if not should_isolate:
        return _IsolationState(
            applied=False,
            strategy="inline_context",
            reason="Context breadth remained small enough for inline handling.",
            input_target_count=len(target_paths),
            output_target_count=len(target_paths),
            input_patch_plan_count=len(patch_plan),
            output_patch_plan_count=len(patch_plan),
            digest={
                "requirement": request.requirement,
                "selected_model_items": list(model_selected),
            },
        )
    reduced_targets = target_paths[:3]
    reduced_patch_plan = patch_plan[:3]
    return _IsolationState(
        applied=True,
        strategy="subtask_digest",
        reason="A dedicated isolation unit reduced target and patch-plan breadth before the main loop consumed it.",
        input_target_count=len(target_paths),
        output_target_count=len(reduced_targets),
        input_patch_plan_count=len(patch_plan),
        output_patch_plan_count=len(reduced_patch_plan),
        digest={
            "requirement": request.requirement,
            "target_focus": reduced_targets,
            "patch_focus": reduced_patch_plan,
            "selected_model_items": list(model_selected)[:2],
        },
    )


def _select_runtime_context(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    context,
    repo_report: dict[str, object],
) -> _ContextSelection:
    deterministic_items = [
        {
            "source": "governance_policy",
            "kind": "workspace_boundary_policy",
            "value": "workspace_root_only",
        },
        {
            "source": "request_context",
            "kind": "session_context",
            "value": dict(context.session_context),
        },
        {
            "source": "request_context",
            "kind": "task_contract",
            "value": dict(request.task_contract or {}),
        },
        {
            "source": "repo_explorer",
            "kind": "repo_candidates",
            "value": {
                "candidate_paths": list(repo_report.get("candidate_paths", []))[:5]
                if isinstance(repo_report.get("candidate_paths"), list)
                else [],
                "existing_paths": list(repo_report.get("existing_paths", []))[:5]
                if isinstance(repo_report.get("existing_paths"), list)
                else [],
            },
        },
    ]
    if request.session_id:
        memory_records = runtime.memory_store.search(request.requirement, session_id=request.session_id, limit=5)
    else:
        memory_records = runtime.memory_store.search(request.requirement, limit=5)
    model_driven = _model_driven_context_selection(
        runtime,
        request=request,
        deterministic_items=deterministic_items,
        memory_records=memory_records,
    )
    retrieval = {
        "strategy": "memory_search",
        "query": request.requirement,
        "selected_memory_count": len(memory_records),
        "records": [dict(record) for record in memory_records],
    }
    selected_context = {
        "deterministic_sources": [item["kind"] for item in deterministic_items],
        "retrieved_memory_ids": [record.get("id") for record in memory_records if isinstance(record, dict)],
        "model_selected_items": list(model_driven.get("selected_items", [])) if isinstance(model_driven.get("selected_items"), list) else [],
        "session_context": dict(context.session_context),
        "task_contract": dict(request.task_contract or {}),
    }
    return _ContextSelection(
        deterministic={
            "strategy": "fixed_runtime_sources",
            "selected_items": deterministic_items,
        },
        model_driven=model_driven,
        retrieval=retrieval,
        selected_context=selected_context,
    )


def _model_driven_context_selection(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    deterministic_items: list[dict[str, object]],
    memory_records: list[dict[str, object]],
) -> dict[str, object]:
    candidates = [
        {"candidate_id": f"deterministic:{item['kind']}", "kind": str(item["kind"]), "source": str(item["source"])}
        for item in deterministic_items
    ]
    candidates.extend(
        {
            "candidate_id": f"memory:{record.get('id')}",
            "kind": str(record.get("record_type") or "memory"),
            "source": "memory",
            "summary": str(record.get("summary") or ""),
        }
        for record in memory_records
        if isinstance(record, dict)
    )
    if not _should_use_model_driven_select(request.requirement, candidates):
        return {
            "strategy": "deterministic_fallback",
            "used_model": False,
            "selected_items": [],
            "reason": "Candidate set is small enough for deterministic and retrieval-based selection alone.",
        }
    config = EnvSlotFillConfig.from_env()
    if config is None:
        return {
            "strategy": "deterministic_fallback",
            "used_model": False,
            "selected_items": [],
            "reason": "Model-driven selection config was unavailable.",
        }
    payload = {
        "model": config.model,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You select the most relevant context candidates for the current coding subtask. "
                    "Return only a JSON object with keys selected_items and rationale. "
                    "selected_items must be a list of candidate_id strings chosen from the provided candidates. "
                    "Choose at most 5 items."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "requirement": request.requirement,
                        "candidates": candidates,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    request_url = f"{config.base_url}/chat/completions"
    transport = runtime.model_selector_transport or _default_openai_compatible_transport
    try:
        response = transport(request_url, payload, headers, config.timeout_seconds)
    except Exception as exc:
        return {
            "strategy": "deterministic_fallback",
            "used_model": False,
            "selected_items": [],
            "reason": f"Model-driven selection request failed: {exc}",
        }
    content = _extract_openai_message_content(response)
    if not content:
        return {
            "strategy": "deterministic_fallback",
            "used_model": False,
            "selected_items": [],
            "reason": "Model-driven selection returned no message content.",
        }
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {
            "strategy": "deterministic_fallback",
            "used_model": False,
            "selected_items": [],
            "reason": "Model-driven selection returned non-JSON content.",
        }
    selected_items = parsed.get("selected_items", []) if isinstance(parsed, dict) else []
    normalized = [
        item
        for item in selected_items
        if isinstance(item, str) and any(candidate["candidate_id"] == item for candidate in candidates)
    ]
    return {
        "strategy": "openai_compatible_model_selector",
        "used_model": True,
        "selected_items": normalized[:5],
        "reason": str(parsed.get("rationale") or "Model selected relevant context candidates.") if isinstance(parsed, dict) else "Model selected relevant context candidates.",
    }


def _should_use_model_driven_select(requirement: str, candidates: list[dict[str, object]]) -> bool:
    if len(candidates) >= 6:
        return True
    lowered = requirement.lower()
    return any(token in lowered for token in ["broad", "investigate", "multiple", "compare", "several"])


def _approval_store(runtime: CodingAgentExecutionRuntime) -> ApprovalStore:
    if runtime.approvals_root is not None:
        return ApprovalStore(runtime.approvals_root)
    workspace_root = runtime.repo_explorer.workspace_root if isinstance(runtime.repo_explorer.workspace_root, Path) else Path(runtime.repo_explorer.workspace_root)
    return ApprovalStore(workspace_root / ".agent_orchestrator" / "approvals")


def _approval_gate_for_edit(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    edit_intent,
) -> dict[str, object] | None:
    if not runtime.enforce_approvals or edit_intent.mode != "direct_apply":
        return None
    if _approval_resolved_for_stage(runtime, request=request, stage="edit"):
        return None
    approval = _create_runtime_approval(
        runtime,
        request=request,
        stage="edit",
        scope="edit_execution",
        reason="File mutation requires human approval before execution.",
    )
    return {
        "stage": "edit",
        "approval_id": approval.id,
        "scope": approval.scope,
        "reason": approval.reason,
        "status": approval.status,
    }


def _approval_gate_for_verification(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    edit_intent,
) -> dict[str, object] | None:
    if not runtime.enforce_approvals or not edit_intent.target_paths:
        return None
    if _approval_resolved_for_stage(runtime, request=request, stage="verify"):
        return None
    approval = _create_runtime_approval(
        runtime,
        request=request,
        stage="verify",
        scope="verification",
        reason="Command execution requires human approval before verification.",
    )
    return {
        "stage": "verify",
        "approval_id": approval.id,
        "scope": approval.scope,
        "reason": approval.reason,
        "status": approval.status,
    }


def _create_runtime_approval(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    stage: str,
    scope: str,
    reason: str,
) -> ApprovalItem:
    run_id = _runtime_run_id(request)
    item = ApprovalItem(
        id=f"approval-{run_id}-{stage}",
        status="pending",
        reason_code="awaiting_human_decision",
        reason=reason,
        scope=scope,
        scope_id=f"{request.turn_id or request.session_id or run_id}:{stage}",
        recommended_action="team approvals resolve",
        session_id=request.session_id,
        run_id=run_id,
        evidence_refs=[f"runtime:{run_id}", f"turn:{request.turn_id or 'unknown'}"],
    )
    return _approval_store(runtime).append(item)


def _approval_resolved_for_stage(
    runtime: CodingAgentExecutionRuntime,
    request: ExecutionRequest,
    *,
    stage: str,
) -> bool:
    approved_approval_id = _approved_approval_id(runtime, request)
    if not isinstance(approved_approval_id, str) or not approved_approval_id:
        return False
    expected_id = f"approval-{_runtime_run_id(request)}-{stage}"
    if approved_approval_id != expected_id:
        return False
    latest = _approval_store(runtime).latest_by_id().get(approved_approval_id)
    return latest is not None and latest.status == "approved"


def _pending_repair_summary(pending_approval: dict[str, object]) -> dict[str, object]:
    return {
        "outcome": "awaiting_approval",
        "attempt_count": 0,
        "retry_budget": 0,
        "attempts": [],
        "recovery_recommendation": {
            "action": "await_approval",
            "reason": pending_approval.get("reason", "approval_required"),
            "human_review_recommended": True,
            "approval_id": pending_approval.get("approval_id"),
        },
    }


def _verification_artifact_summary(final_verification: dict[str, object]) -> dict[str, object] | None:
    artifact = final_verification.get("artifact")
    return dict(artifact) if isinstance(artifact, dict) else None


def _persist_execution_state(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    status: str,
    accepted: bool,
    pending_approval: dict[str, object] | None,
    steps: list[ExecutionStep],
    payload: dict[str, object],
) -> dict[str, object]:
    current_step = next(
        (step for step in steps if step.status in {"pending", "blocked", "running"}),
        steps[-1] if steps else None,
    )
    state_payload = {
        "format": "agent_orchestrator.execution_state.v1",
        "runtime_name": runtime.name,
        "session_id": request.session_id,
        "turn_id": request.turn_id,
        "resume_kind": request.resume_kind,
        "status": status,
        "accepted": accepted,
        "current_stage": pending_approval.get("stage") if isinstance(pending_approval, dict) else current_step.kind if current_step else None,
        "current_step_id": current_step.step_id if current_step is not None else None,
        "pending_approval": dict(pending_approval) if isinstance(pending_approval, dict) else None,
        "step_statuses": [
            {
                "step_id": step.step_id,
                "kind": step.kind,
                "status": step.status,
                "approval": step.approval.to_dict() if step.approval is not None else None,
            }
            for step in steps
        ],
        "resume_contract": _resume_contract(request, pending_approval, current_step),
        "execution_history_summary": payload.get("execution_history_summary"),
        "compressed_context": payload.get("compressed_context"),
        "next_step_contract": payload.get("next_step_contract"),
        "planner_context_trace": payload.get("planner_context_trace"),
        "next_stage_proposals": payload.get("next_stage_proposals"),
        "stage_selection_trace": payload.get("stage_selection_trace"),
        "action_selection_trace": payload.get("action_selection_trace"),
        "step_decisions": payload.get("step_decisions"),
        "resume_context": payload.get("resume_context"),
        "result_summary": {
            "applied_change_count": payload.get("applied_change_count"),
            "applied_changes": payload.get("applied_changes"),
            "verification": payload.get("verification"),
            "repair_summary": payload.get("repair_summary"),
            "recent_observations": payload.get("resume_context", {}).get("recent_observations", [])
            if isinstance(payload.get("resume_context"), dict)
            else [],
        },
    }
    return runtime.state_store.write(_runtime_run_id(request), state_payload)


def _record_execution_artifacts(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    payload: dict[str, object],
) -> None:
    artifact_summary = payload.get("artifact_summary", {}) if isinstance(payload.get("artifact_summary"), dict) else {}
    artifacts = artifact_summary.get("artifacts", []) if isinstance(artifact_summary.get("artifacts"), list) else []
    if not artifacts:
        return
    workspace_root = runtime.repo_explorer.workspace_root if isinstance(runtime.repo_explorer.workspace_root, Path) else Path(runtime.repo_explorer.workspace_root)
    WorkspaceIndexStore(workspace_root / ".agent_orchestrator" / "workspace").record_artifact(
        "execution_artifacts",
        {
            "format": "agent_orchestrator.execution_artifact_summary.v1",
            "run_id": _runtime_run_id(request),
            "session_id": request.session_id,
            "turn_id": request.turn_id,
            "artifact_count": artifact_summary.get("artifact_count", 0),
            "artifacts": artifacts,
            "compressed_context": payload.get("compressed_context"),
        },
    )


def _resume_contract(
    request: ExecutionRequest,
    pending_approval: dict[str, object] | None,
    current_step: ExecutionStep | None,
) -> dict[str, object]:
    metadata = request.session_metadata if isinstance(request.session_metadata, dict) else {}
    return ExecutionResumeContract(
        resume_kind=request.resume_kind or "fresh",
        run_id=_runtime_run_id(request),
        session_id=request.session_id,
        turn_id=request.turn_id,
        current_stage=pending_approval.get("stage") if isinstance(pending_approval, dict) else current_step.kind if current_step is not None else None,
        current_step_id=current_step.step_id if current_step is not None else None,
        approved_approval_id=str(metadata.get("approved_approval_id")) if metadata.get("approved_approval_id") is not None else None,
        pending_approval=dict(pending_approval) if isinstance(pending_approval, dict) else None,
        resume_supported=True,
    ).to_dict()


def _emit_execution_events(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    status: str,
    accepted: bool,
    steps: list[ExecutionStep],
    pending_approval: dict[str, object] | None,
) -> dict[str, object]:
    run_id = _runtime_run_id(request)
    store = _event_store(runtime)
    emitted: list[dict[str, object]] = []
    for step in steps:
        event = store.append(
            type="execution.step",
            scope="run",
            scope_id=run_id,
            message=f"Step {step.kind} entered status {step.status}.",
            payload={
                "run_id": run_id,
                "session_id": request.session_id,
                "turn_id": request.turn_id,
                "runtime_name": runtime.name,
                "step_id": step.step_id,
                "step_kind": step.kind,
                "step_status": step.status,
                "approval": step.approval.to_dict() if step.approval is not None else None,
            },
        )
        emitted.append(event.to_dict())
        for action in step.actions:
            action_requested = store.append(
                type="execution.action_requested",
                scope="run",
                scope_id=run_id,
                message=f"Action {action.action_type} requested in step {step.kind}.",
                payload={
                    "run_id": run_id,
                    "session_id": request.session_id,
                    "turn_id": request.turn_id,
                    "runtime_name": runtime.name,
                    "step_id": step.step_id,
                    "step_kind": step.kind,
                    "action_id": action.action_id,
                    "action_type": action.action_type,
                    "risk_level": action.risk_level,
                    "requires_approval": action.requires_approval,
                },
            )
            emitted.append(action_requested.to_dict())
        for result in step.results:
            action_completed = store.append(
                type="execution.action_completed",
                scope="run",
                scope_id=run_id,
                message=f"Action {result.action_type} completed with status {result.status}.",
                payload={
                    "run_id": run_id,
                    "session_id": request.session_id,
                    "turn_id": request.turn_id,
                    "runtime_name": runtime.name,
                    "step_id": step.step_id,
                    "step_kind": step.kind,
                    "action_id": result.action_id,
                    "action_type": result.action_type,
                    "result_status": result.status,
                    "error": result.error,
                },
            )
            emitted.append(action_completed.to_dict())
            artifact = result.payload.get("artifact")
            if isinstance(artifact, dict):
                artifact_event = store.append(
                    type="execution.artifact_externalized",
                    scope="run",
                    scope_id=run_id,
                    message=f"Artifact externalized for {result.action_type}.",
                    payload={
                        "run_id": run_id,
                        "session_id": request.session_id,
                        "turn_id": request.turn_id,
                        "runtime_name": runtime.name,
                        "step_id": step.step_id,
                        "step_kind": step.kind,
                        "action_id": result.action_id,
                        "artifact": dict(artifact),
                    },
                )
                emitted.append(artifact_event.to_dict())
        for observation in step.observations:
            artifact = observation.payload.get("artifact")
            if isinstance(artifact, dict):
                artifact_event = store.append(
                    type="execution.artifact_externalized",
                    scope="run",
                    scope_id=run_id,
                    message=f"Artifact externalized for observation {observation.kind}.",
                    payload={
                        "run_id": run_id,
                        "session_id": request.session_id,
                        "turn_id": request.turn_id,
                        "runtime_name": runtime.name,
                        "step_id": step.step_id,
                        "step_kind": step.kind,
                        "observation_id": observation.observation_id,
                        "observation_kind": observation.kind,
                        "artifact": dict(artifact),
                    },
                )
                emitted.append(artifact_event.to_dict())
    compressed_context = _compressed_execution_context(
        request=request,
        status=status,
        steps=steps,
        payload={
            "execution_context": {"session_context": dict(request.context_snapshot or {})},
            "execution_history_summary": _execution_history_summary(
                request=request,
                status=status,
                steps=steps,
                pending_approval=pending_approval,
            ),
            "artifact_summary": _artifact_summary(steps),
        },
        pending_approval=pending_approval,
    )
    context_event = store.append(
        type="execution.context_compressed",
        scope="run",
        scope_id=run_id,
        message="Compressed execution context snapshot recorded.",
        payload={
            "run_id": run_id,
            "session_id": request.session_id,
            "turn_id": request.turn_id,
            "runtime_name": runtime.name,
            "compressed_context": compressed_context,
        },
    )
    emitted.append(context_event.to_dict())
    next_step_contract = _next_step_contract(
        decisions=_build_step_decisions(
            steps=steps,
            pending_approval=pending_approval,
            final_status=status,
        ),
        status=status,
        pending_approval=pending_approval,
        resume_context=None,
    )
    decision_event = store.append(
        type="execution.next_step_decided",
        scope="run",
        scope_id=run_id,
        message=f"Next step disposition decided as {next_step_contract.get('current_disposition', 'unknown')}.",
        payload={
            "run_id": run_id,
            "session_id": request.session_id,
            "turn_id": request.turn_id,
            "runtime_name": runtime.name,
            "next_step_contract": next_step_contract,
        },
    )
    emitted.append(decision_event.to_dict())
    if isinstance(pending_approval, dict):
        event = store.append(
            type="execution.approval_requested",
            scope="run",
            scope_id=run_id,
            message=f"Approval requested for {pending_approval.get('stage', 'unknown')} stage.",
            payload={
                "run_id": run_id,
                "session_id": request.session_id,
                "turn_id": request.turn_id,
                "runtime_name": runtime.name,
                **pending_approval,
            },
        )
        emitted.append(event.to_dict())
    terminal_type = "execution.run_completed" if status == "completed" else "execution.run_blocked"
    terminal_event = store.append(
        type=terminal_type,
        scope="run",
        scope_id=run_id,
        message=f"Execution run {run_id} finished with status {status}.",
        payload={
            "run_id": run_id,
            "session_id": request.session_id,
            "turn_id": request.turn_id,
            "runtime_name": runtime.name,
            "status": status,
            "accepted": accepted,
        },
    )
    emitted.append(terminal_event.to_dict())
    type_counts: dict[str, int] = {}
    for event in emitted:
        event_type = str(event.get("type") or "unknown")
        type_counts[event_type] = type_counts.get(event_type, 0) + 1
    return {
        "event_count": len(emitted),
        "type_counts": type_counts,
        "recent_events": emitted[-5:],
    }


def _event_store(runtime: CodingAgentExecutionRuntime) -> EventStore:
    root = runtime.event_store.root
    if root != ".agent_orchestrator/events":
        runtime.event_store.__post_init__()
        return runtime.event_store
    workspace_root = runtime.repo_explorer.workspace_root if isinstance(runtime.repo_explorer.workspace_root, Path) else Path(runtime.repo_explorer.workspace_root)
    return EventStore(workspace_root / ".agent_orchestrator" / "events")


def _approved_approval_id(runtime: CodingAgentExecutionRuntime, request: ExecutionRequest) -> str | None:
    metadata = request.session_metadata if isinstance(request.session_metadata, dict) else {}
    direct = metadata.get("approved_approval_id")
    if isinstance(direct, str) and direct:
        return direct
    stored = runtime.state_store.read(_runtime_run_id(request))
    resume_contract = stored.get("resume_contract", {}) if isinstance(stored.get("resume_contract"), dict) else {}
    value = resume_contract.get("approved_approval_id")
    if not isinstance(value, str) or not value:
        pending = stored.get("pending_approval", {}) if isinstance(stored.get("pending_approval"), dict) else {}
        pending_id = pending.get("approval_id")
        if isinstance(pending_id, str) and pending_id:
            latest = _approval_store(runtime).latest_by_id().get(pending_id)
            if latest is not None and latest.status == "approved":
                value = pending_id
    return value if isinstance(value, str) and value else None


def _request_with_resume_contract(
    runtime: CodingAgentExecutionRuntime,
    request: ExecutionRequest,
) -> ExecutionRequest:
    stored = runtime.state_store.read(_runtime_run_id(request))
    resume_contract = ExecutionResumeContract.from_dict(
        stored.get("resume_contract", {}) if isinstance(stored.get("resume_contract"), dict) else None
    )
    if resume_contract is None:
        return request
    session_metadata = dict(request.session_metadata or {})
    approved_approval_id = resume_contract.approved_approval_id
    if approved_approval_id and "approved_approval_id" not in session_metadata:
        session_metadata["approved_approval_id"] = approved_approval_id
    resume_kind = request.resume_kind or resume_contract.resume_kind or "approval_resume"
    return ExecutionRequest(
        requirement=request.requirement,
        route=request.route,
        runtime_name=request.runtime_name,
        mode=request.mode,
        reroute=request.reroute,
        agent_enabled=request.agent_enabled,
        depth=request.depth,
        review_policy_override=request.review_policy_override,
        provider_health_snapshot=request.provider_health_snapshot,
        task_contract=request.task_contract,
        session_id=request.session_id,
        turn_id=request.turn_id,
        context_snapshot=request.context_snapshot,
        resume_kind=resume_kind,
        session_metadata=session_metadata,
    )
