"""MVP coding-agent execution runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal

from agent_orchestrator.control_plane_approvals import ApprovalItem, ApprovalStore
from agent_orchestrator.control_plane_posture import (
    derive_planner_closure_posture_summary,
    derive_session_continuity_outline_from_contract,
    derive_session_planner_decision_from_payload,
)
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
    derive_adapter_capability_summary,
    derive_adapter_execution_fact,
    derive_adapter_productization_surface,
    ExecutionKernelContract,
    ExecutionRequest,
    ExecutionResumeContract,
    ExecutionResult,
    ExecutionStep,
    ExecutionStepDecision,
    ObservationRecord,
    PendingApprovalState,
    UnifiedAgentAdapterContract,
)
from agent_orchestrator.execution.state_store import ExecutionStateStore
from agent_orchestrator.execution.runtime import ExecutionRuntime
from agent_orchestrator.intake import ExecutionMode
from agent_orchestrator.memory import KnowledgeStore, MemoryStore
from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.policies import OrchestrationMode, get_policy
from agent_orchestrator.productization_surface import (
    build_comparative_completion_summary,
    build_runtime_comparative_benchmark_digest,
    build_runtime_comparative_benchmark_summary,
    build_shared_productization_surface,
)
from agent_orchestrator.session import ScratchpadStore, SessionRuntime
from agent_orchestrator.strategy import CompatibilityStrategyPlanner, NativeStrategyPlanner
from agent_orchestrator.tasks import TaskContract
from agent_orchestrator.execution.native_tools import NativeToolbox


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
    reinjection_mode: str
    reinjection_targets: list[str]
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
            "reinjection_mode": self.reinjection_mode,
            "reinjection_targets": list(self.reinjection_targets),
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
    toolbox: NativeToolbox = field(default_factory=NativeToolbox)
    model_selector_transport: Callable[[str, dict[str, object], dict[str, str], int], dict[str, object]] | None = None
    summarizer_transport: Callable[[str, dict[str, object], dict[str, str], int], dict[str, object]] | None = None
    intent_refiner_transport: Callable[[str, dict[str, object], dict[str, str], int], dict[str, object]] | None = None
    enforce_approvals: bool = False
    approvals_root: Path | str | None = None
    name: str = "coding_agent"

    def _kernel_contract(self) -> ExecutionKernelContract:
        return ExecutionKernelContract(
            kernel_name=self.name,
            kernel_role="governed_execution_kernel",
            input_sources=[
                "execution_request",
                "task_contract",
                "session_runtime",
                "control_plane_artifacts",
                "execution_topology_intent",
                "provider_runtime_capabilities",
            ],
            output_surfaces=[
                "execution_result",
                "structured_observations",
                "resume_contract",
                "runtime_event_stream",
                "recovery_projection",
                "memory_projection",
                "approval_pause_state",
            ],
        )

    def _adapter_contract(self, request: ExecutionRequest) -> UnifiedAgentAdapterContract:
        path_selection = _path_selection_payload(request)
        return UnifiedAgentAdapterContract(
            adapter_family="native_first_party",
            agent_kind="coding_agent",
            execution_contract=self._kernel_contract().to_dict(),
            runtime_metadata={
                "runtime_name": self.name,
                "execution_mode": ExecutionMode.CODING_AGENT.value,
                "task_kind": request.route.task_kind.value,
            },
            capability_surface=_shared_adapter_capability_surface(
                adapter_family="native_first_party",
                agent_kind="coding_agent",
                path_selection=path_selection,
                approval_required=True,
                approval_pause_supported=True,
                evidence_outputs=[
                    "execution_result",
                    "structured_observations",
                    "runtime_event_stream",
                    "recovery_projection",
                    "memory_projection",
                ],
                recovery_surfaces=[
                    "state_store",
                    "resume_contract",
                    "approval_pause_state",
                ],
                runtime_metadata={
                    "runtime_name": self.name,
                    "execution_mode": ExecutionMode.CODING_AGENT.value,
                    "task_kind": request.route.task_kind.value,
                },
            ),
            path_selection=path_selection,
            approval_semantics={
                "approval_required": True,
                "approval_pause_supported": True,
            },
            evidence_outputs=[
                "execution_result",
                "structured_observations",
                "runtime_event_stream",
                "recovery_projection",
                "memory_projection",
            ],
            recovery_surfaces=[
                "state_store",
                "resume_contract",
                "approval_pause_state",
            ],
        )

    def run(self, request: ExecutionRequest) -> ExecutionResult:
        policy = get_policy(request.mode) if request.mode is not None else get_policy(OrchestrationMode.SUCCESS_FIRST)
        task_contract = TaskContract.from_dict(request.task_contract) if isinstance(request.task_contract, dict) else None
        strategy_planner = self.orchestrator.strategy_planner
        if strategy_planner is None or isinstance(strategy_planner, CompatibilityStrategyPlanner):
            strategy_planner = NativeStrategyPlanner(self.orchestrator.decomposer)
        workspace_root = self.repo_explorer.workspace_root
        verifier_runner = getattr(self.verify_loop.verifier, "runner", None)
        if verifier_runner is None:
            from agent_orchestrator.command import SubprocessCommandRunner

            verifier_runner = SubprocessCommandRunner()
        self.toolbox.workspace_root = workspace_root if isinstance(workspace_root, Path) else Path(workspace_root)
        self.toolbox.runner = verifier_runner
        self.toolbox.artifact_store = self.repo_explorer.artifact_store
        self.repo_explorer.toolbox = self.toolbox
        self.context_builder  # keep context builder explicit for current main path
        self.edit_executor.toolbox = self.toolbox
        self.verify_loop.verifier.toolbox = self.toolbox
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
        kernel_result = _run_execution_kernel(
            self,
            request=request,
            edit_intent=edit_intent,
            strategy_plan=strategy_plan,
        )
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
            "requirement": request.requirement,
            "task_contract": dict(request.task_contract or {}),
            "adapter_contract": self._adapter_contract(request).to_dict(),
            "native_tool_surface": self.toolbox.surface_summary(),
            "native_tool_trace": self.toolbox.tool_trace(),
            "task_kind": request.route.task_kind.value,
            "path_selection": _path_selection_payload(request),
            "kernel_contract": self._kernel_contract().to_dict(),
            "session_id": request.session_id,
            "turn_id": request.turn_id,
            "context_snapshot": dict(request.context_snapshot or {}),
            "repo_report": repo_report.to_dict(),
            "repository_understanding": _repository_understanding_from_repo_report(repo_report.to_dict()),
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
            "planner_family": strategy_plan.planner_family if strategy_plan is not None else "native",
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
        payload["adapter_productization_surface"] = _adapter_productization_surface(
            adapter_contract=payload["adapter_contract"],
        )
        payload["adapter_capability_surface"] = _adapter_capability_surface(payload)
        payload["adapter_capability"] = _adapter_capability_summary(payload)
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
        payload["context_engineering_contract"] = _context_engineering_contract(
            request=request,
            context_selection=payload["context_selection"],
            structured_observations=structured_observations,
            compaction_state=payload["compaction_state"],
            compressed_context=payload["compressed_context"],
            isolation_state=payload["isolation_state"],
            resume_context=payload["resume_context"],
            scratchpad_entries=payload["scratchpad_entries"],
            retrieved_memory=payload.get("retrieved_memory", []),
        )
        payload["next_step_contract"] = _next_step_contract(
            decisions=step_decisions,
            status=status,
            pending_approval=pending_approval,
            resume_context=payload["resume_context"],
            context_engineering_contract=payload["context_engineering_contract"],
        )
        payload["step_loop_contract"] = _step_loop_contract(
            status=status,
            planner_context_trace=planner_context_trace,
            next_stage_proposals=next_stage_proposals,
            stage_selection_trace=stage_selection_trace,
            action_selection_trace=action_selection_trace,
            decisions=step_decisions,
            pending_approval=pending_approval,
            next_step_contract=payload["next_step_contract"],
            resume_context=payload["resume_context"],
            context_engineering_contract=payload["context_engineering_contract"],
        )
        payload["event_summary"] = _emit_execution_events(
            self,
            request=request,
            status=status,
            accepted=accepted,
            steps=steps,
            pending_approval=pending_approval,
        )
        payload["native_task_proof"] = _native_task_proof(
            runtime=self,
            request=request,
            payload=payload,
        )
        payload["native_repo_task_acceptance"] = _native_repo_task_acceptance(
            request=request,
            payload=payload,
        )
        payload["native_complex_repo_task_acceptance"] = _native_complex_repo_task_acceptance(
            request=request,
            payload=payload,
        )
        payload["native_tool_workflow_surface"] = _native_tool_workflow_surface(payload)
        payload["native_tool_productization_surface"] = _native_tool_productization_surface(payload)
        payload["session_continuity_contract"] = _session_continuity_contract(payload=payload)
        payload["adapter_shared_contract"] = _adapter_shared_contract_summary_from_payload(payload)
        payload["adapter_execution_fact"] = derive_adapter_execution_fact(
            runtime_name=self.name,
            execution_mode=ExecutionMode.CODING_AGENT.value,
            task_kind=request.route.task_kind.value,
            status=status,
            run_id=_runtime_run_id(request),
            session_id=request.session_id,
            turn_id=request.turn_id,
            adapter_contract=payload.get("adapter_contract", {}),
            adapter_shared_contract=payload.get("adapter_shared_contract", {}),
            adapter_capability_surface=payload.get("adapter_capability_surface", {}),
        )
        payload["native_tool_usage"] = _native_tool_usage_summary(payload)
        payload["native_tool_evidence"] = _native_tool_evidence_summary(payload)
        payload["resume_contract"] = _resume_contract(
            request,
            pending_approval,
            steps[-1] if steps else None,
            payload=payload,
        )
        payload["planner_decision"] = _session_planner_decision_from_payload(payload)
        payload["continuity_outline"] = _session_continuity_outline_from_payload(payload)
        payload["runtime_cost"] = {
            "duration_seconds": (
                payload["session_continuity_contract"].get("runtime_duration_seconds")
                if isinstance(payload.get("session_continuity_contract"), dict)
                else None
            ),
            "usage_cost_measurement_status": (
                payload["session_continuity_contract"].get("usage_cost_measurement_status")
                if isinstance(payload.get("session_continuity_contract"), dict)
                else None
            ),
        }
        payload["shared_productization_surface"] = build_shared_productization_surface(
            session_productization_surface=(
                payload["session_continuity_contract"].get("session_productization_surface", {})
                if isinstance(payload.get("session_continuity_contract"), dict)
                else {}
            ),
            native_tool_productization_surface=(
                payload.get("native_tool_productization_surface", {})
                if isinstance(payload.get("native_tool_productization_surface"), dict)
                else {}
            ),
            native_tool_workflow_surface=(
                payload.get("native_tool_workflow_surface", {})
                if isinstance(payload.get("native_tool_workflow_surface"), dict)
                else {}
            ),
            adapter_productization_surface=(
                payload.get("adapter_productization_surface", {})
                if isinstance(payload.get("adapter_productization_surface"), dict)
                else {}
            ),
            planner_decision=payload.get("planner_decision", {})
            if isinstance(payload.get("planner_decision"), dict)
            else {},
            continuity_outline=payload.get("continuity_outline", {})
            if isinstance(payload.get("continuity_outline"), dict)
            else {},
            planner_closure_posture=(
                payload.get("planner_closure_posture", {})
                if isinstance(payload.get("planner_closure_posture"), dict)
                else derive_planner_closure_posture_summary(
                    planner_decision=(
                        payload.get("planner_decision", {})
                        if isinstance(payload.get("planner_decision"), dict)
                        else {}
                    ),
                    continuity=(
                        payload.get("continuity_outline", {})
                        if isinstance(payload.get("continuity_outline"), dict)
                        else {}
                    ),
                )
            ),
            runtime_cost=(
                payload.get("runtime_cost", {}) if isinstance(payload.get("runtime_cost"), dict) else {}
            ),
            native_tool_usage=(
                payload.get("native_tool_usage", {}) if isinstance(payload.get("native_tool_usage"), dict) else {}
            ),
            adapter_capability_surface=(
                payload.get("adapter_capability_surface", {})
                if isinstance(payload.get("adapter_capability_surface"), dict)
                else {}
            ),
            comparative_shared_evidence_surface=(
                payload["session_continuity_contract"].get("shared_evidence_surface", [])
                if isinstance(payload.get("session_continuity_contract"), dict)
                else []
            ),
        )
        payload["comparative_benchmark"] = build_runtime_comparative_benchmark_summary(
            _runtime_comparative_execution_artifact_summary(payload)
        )
        payload["comparative_benchmark_digest"] = build_runtime_comparative_benchmark_digest(
            payload["comparative_benchmark"]
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
        _record_native_learning_assets(self, request=request, payload=payload)
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
            kernel_contract=self._kernel_contract(),
            path_selection=_path_selection_payload(request),
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
            kernel_contract=self._kernel_contract(),
            path_selection=_path_selection_payload(request),
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
    decision: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "outcome": self.outcome,
            "next_stage": self.next_stage,
            "reason": self.reason,
            "decision": dict(self.decision),
        }


@dataclass(frozen=True, slots=True)
class _KernelActionSelection:
    stage: RuntimeStage
    action_type: str
    source: str
    selected: dict[str, object]
    reason: str
    decision: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "action_type": self.action_type,
            "source": self.source,
            "selected": dict(self.selected),
            "reason": self.reason,
            "decision": dict(self.decision),
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
    route_planner_intent: dict[str, object] = field(default_factory=dict)
    planner_family: str = "native"
    selected_strategy: str = "direct_edit"
    planner_actions: list[str] = field(default_factory=list)
    autonomy_surface: dict[str, object] = field(default_factory=dict)
    control_surface: dict[str, object] = field(default_factory=dict)
    delegation_contract: dict[str, object] = field(default_factory=dict)
    operator_control: dict[str, object] = field(default_factory=dict)
    tool_workflow_plan: dict[str, object] = field(default_factory=dict)
    current_stage_workflow: dict[str, object] = field(default_factory=dict)
    decision_evidence: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "stage_cursor": self.stage_cursor,
            "resume_kind": self.resume_kind,
            "route_risk_level": self.route_risk_level,
            "planner_family": self.planner_family,
            "selected_strategy": self.selected_strategy,
            "route_planner_intent": dict(self.route_planner_intent),
            "planner_actions": list(self.planner_actions),
            "autonomy_surface": dict(self.autonomy_surface),
            "control_surface": dict(self.control_surface),
            "delegation_contract": dict(self.delegation_contract),
            "operator_control": dict(self.operator_control),
            "tool_workflow_plan": dict(self.tool_workflow_plan),
            "current_stage_workflow": dict(self.current_stage_workflow),
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
            "decision_evidence_format": self.decision_evidence.get("format"),
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
    selection: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "current_stage": self.current_stage,
            "proposed_stage": self.proposed_stage,
            "disposition": self.disposition,
            "reason": self.reason,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "selected_candidate_id": self.selected_candidate_id,
            "selection": dict(self.selection),
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
class _KernelNextStageDecision:
    candidates: list[_KernelNextStageCandidate]
    selected_candidate: _KernelNextStageCandidate
    ranking_enabled: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "ranking_enabled": self.ranking_enabled,
            "candidate_count": len(self.candidates),
            "selected_candidate_id": self.selected_candidate.candidate_id,
        }


@dataclass(frozen=True, slots=True)
class _KernelActionDecision:
    selection: _KernelActionSelection
    planner_context: _KernelPlannerContext

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_type": "action_selection",
            "stage": self.selection.stage,
            "selected_action_type": self.selection.action_type,
            "selected_source": self.selection.source,
            "planner_feasibility": self.planner_context.action_feasibility,
            "approval_required": self.planner_context.approval_required,
            "workflow_projection_required": bool(self.planner_context.tool_workflow_plan.get("workflow_projection_required")),
            "current_stage_required_tools": list(
                self.planner_context.current_stage_workflow.get("required_tools", [])
            )
            if isinstance(self.planner_context.current_stage_workflow.get("required_tools"), list)
            else [],
        }


@dataclass(frozen=True, slots=True)
class _KernelStageDecision:
    selection: _KernelStageSelection
    next_stage_proposal: _KernelNextStageProposal
    action_selection: _KernelActionSelection | None

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_type": "stage_selection",
            "selection_mode": "action_and_proposal" if self.action_selection is not None else "proposal_only",
            "selected_outcome": self.selection.outcome,
            "selected_next_stage": self.selection.next_stage,
            "proposal_selected_candidate_id": self.next_stage_proposal.selected_candidate_id,
            "action_selected_type": self.action_selection.action_type if self.action_selection is not None else None,
            "workflow_projection_required": bool(
                self.action_selection is not None
                and isinstance(self.action_selection.selected, dict)
                and self.action_selection.selected.get("workflow_projection_required")
            ),
        }


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
        decision = _next_stage_decision(
            planner_context=planner_context,
            resume_state=resume_state,
            stage_strategy=self,
        )
        return _proposal_from_decision(
            current_stage=current_stage,
            decision=decision,
            planner_context=planner_context,
        )

    def next_stage_decision(
        self,
        *,
        planner_context: _KernelPlannerContext,
        resume_state: _KernelResumeState,
    ) -> _KernelNextStageDecision:
        candidates = self.candidate_generator(
            planner_context,
            resume_state,
        )
        ranking_enabled = _ranking_enabled_for_stage(
            planner_context,
            stage_strategy=self,
        )
        selected = _select_next_stage_candidate(
            candidates,
            planner_context=planner_context,
            stage_strategy=self,
        )
        return _KernelNextStageDecision(
            candidates=candidates,
            selected_candidate=selected,
            ranking_enabled=ranking_enabled,
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
    strategy_plan=None,
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
            strategy_plan=strategy_plan,
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
    strategy_plan=None,
) -> _KernelStagePlan:
    planner_context = _planner_context_for_stage(
        runtime,
        request=request,
        edit_intent=edit_intent,
        resume_state=resume_state,
        stage_cursor=stage_cursor,
        strategy_plan=strategy_plan,
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
    strategy_plan=None,
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
    route_planner_intent = request.route.planner_intent if isinstance(request.route.planner_intent, dict) else {}
    decision_evidence = (
        strategy_plan.decision_evidence
        if strategy_plan is not None and isinstance(getattr(strategy_plan, "decision_evidence", None), dict)
        else {}
    )
    planner_actions = (
        list(strategy_plan.planner_actions)
        if strategy_plan is not None and isinstance(getattr(strategy_plan, "planner_actions", None), list)
        else []
    )
    autonomy_surface = (
        decision_evidence.get("autonomy_surface", {})
        if isinstance(decision_evidence.get("autonomy_surface"), dict)
        else {}
    )
    control_surface = (
        decision_evidence.get("control_surface", {})
        if isinstance(decision_evidence.get("control_surface"), dict)
        else {}
    )
    delegation_contract = (
        decision_evidence.get("delegation_contract", {})
        if isinstance(decision_evidence.get("delegation_contract"), dict)
        else {}
    )
    operator_control = (
        decision_evidence.get("operator_control", {})
        if isinstance(decision_evidence.get("operator_control"), dict)
        else {}
    )
    tool_workflow_plan = (
        decision_evidence.get("tool_workflow_plan", {})
        if isinstance(decision_evidence.get("tool_workflow_plan"), dict)
        else {}
    )
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
        route_planner_intent=dict(route_planner_intent),
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
        planner_family=str(getattr(strategy_plan, "planner_family", "native") or "native"),
        selected_strategy=str(getattr(getattr(strategy_plan, "strategy", None), "value", None) or getattr(strategy_plan, "strategy", "direct_edit")),
        planner_actions=list(planner_actions),
        autonomy_surface=dict(autonomy_surface),
        control_surface=dict(control_surface),
        delegation_contract=dict(delegation_contract),
        operator_control=dict(operator_control),
        tool_workflow_plan=dict(tool_workflow_plan),
        current_stage_workflow=_current_stage_workflow(
            tool_workflow_plan=tool_workflow_plan,
            stage_cursor=stage_cursor,
        ),
        decision_evidence=dict(decision_evidence),
    )


def _current_stage_workflow(
    *,
    tool_workflow_plan: dict[str, object],
    stage_cursor: RuntimeStage,
) -> dict[str, object]:
    workflow_stages = (
        tool_workflow_plan.get("workflow_stages", {})
        if isinstance(tool_workflow_plan.get("workflow_stages"), dict)
        else {}
    )
    stage_workflow = workflow_stages.get(stage_cursor, {}) if isinstance(workflow_stages.get(stage_cursor), dict) else {}
    return dict(stage_workflow)


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


def _execute_explore_stage(
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
        return stage_strategy.pause_stage(
            action_selection=action_selection,
            plan=plan,
            resume_state=resume_state,
        )
    if action_selection is not None and action_selection.action_type in {"handoff", "fallback"}:
        return stage_strategy.block_stage(
            action_selection=action_selection,
            plan=plan,
            resume_state=resume_state,
        )
    return stage_strategy.continue_stage(
        next_stage=plan.next_stage_proposal.proposed_stage,
        applied_changes=applied_changes,
        repair_summary=dict(resume_state.repair_summary),
        final_verification=dict(resume_state.final_verification),
    )


def _kernel_terminal_outcome(
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
    return _stage_outcome(
        next_stage=next_stage,
        pending_approval=pending_approval,
        applied_changes=list(applied_changes),
        repair_summary=repair_summary,
        final_verification=final_verification,
        status=status,
        accepted=accepted,
        should_stop=should_stop,
    )


def _kernel_continue_outcome(
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


def _paused_edit_outcome(
    *,
    pending_approval: dict[str, object] | None,
    plan: _KernelStagePlan,
    resume_state: _KernelResumeState,
) -> _KernelStageOutcome:
    return _kernel_terminal_outcome(
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
    return _kernel_terminal_outcome(
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
    return _kernel_continue_outcome(
        next_stage=next_stage,
        applied_changes=list(applied_changes),
        repair_summary=repair_summary,
        final_verification=final_verification,
    )


def _continue_without_side_effects_stage(
    runtime: CodingAgentExecutionRuntime,
    request: ExecutionRequest,
    edit_intent,
    resume_state: _KernelResumeState,
    plan: _KernelStagePlan,
    applied_changes: list[object],
) -> _KernelStageOutcome:
    return _execute_explore_stage(runtime, request, edit_intent, resume_state, plan, applied_changes)


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
    if action_selection is not None and action_selection.action_type == "complete":
        inherited_verification = dict(resume_state.final_verification)
        if not inherited_verification:
            inherited_verification = {
                "status": "skipped",
                "reason": "planner_omitted_verification",
            }
        inherited_status = str(inherited_verification.get("status") or "skipped")
        status, accepted = _verify_terminal_status(
            final_status=inherited_status,
            edit_mode=edit_intent.mode,
            applied_change_count=sum(
                1
                for item in applied_changes
                if (getattr(item, "status", None) == "applied")
                or (isinstance(item, dict) and item.get("status") == "applied")
            ),
        )
        return stage_strategy.complete_stage(
            plan=plan,
            applied_changes=applied_changes,
            repair_summary=(
                dict(resume_state.repair_summary)
                if dict(resume_state.repair_summary)
                else {
                    "outcome": "planner_skipped_verification",
                    "attempt_count": 0,
                    "retry_budget": 0,
                    "attempts": [],
                    "recovery_recommendation": {
                        "action": "continue_native",
                        "reason": "planner_control_surface",
                        "human_review_recommended": False,
                    },
                }
            ),
            final_verification=inherited_verification,
            status=status,
            accepted=accepted,
        )
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
    return _kernel_terminal_outcome(
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
    return _kernel_terminal_outcome(
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
    return _kernel_terminal_outcome(
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


def _next_stage_decision(
    *,
    planner_context: _KernelPlannerContext,
    resume_state: _KernelResumeState,
    stage_strategy: _KernelStageStrategy,
) -> _KernelNextStageDecision:
    return stage_strategy.next_stage_decision(
        planner_context=planner_context,
        resume_state=resume_state,
    )


def _select_next_stage(*, next_stage_proposal: _KernelNextStageProposal) -> _KernelStageSelection:
    return _KernelStageSelection(
        stage=next_stage_proposal.current_stage,
        outcome=next_stage_proposal.disposition,
        next_stage=next_stage_proposal.proposed_stage,
        reason=next_stage_proposal.reason,
        decision={
            "decision_type": "stage_selection",
            "selection_mode": "proposal_only",
            "selected_outcome": next_stage_proposal.disposition,
            "selected_next_stage": next_stage_proposal.proposed_stage,
            "proposal_selected_candidate_id": next_stage_proposal.selected_candidate_id,
            "action_selected_type": None,
        },
    )


def _proposal_stage_selection(
    action_selection: _KernelActionSelection | None,
    next_stage_proposal: _KernelNextStageProposal,
) -> _KernelStageSelection:
    stage_selection = _select_next_stage(next_stage_proposal=next_stage_proposal)
    return _stage_selection_with_decision(
        stage_selection=stage_selection,
        next_stage_proposal=next_stage_proposal,
        action_selection=action_selection,
    )


def _edit_stage_selection(
    action_selection: _KernelActionSelection | None,
    next_stage_proposal: _KernelNextStageProposal,
) -> _KernelStageSelection:
    if action_selection is None:
        stage_selection = _select_next_stage(next_stage_proposal=next_stage_proposal)
        return _stage_selection_with_decision(
            stage_selection=stage_selection,
            next_stage_proposal=next_stage_proposal,
            action_selection=None,
        )
    stage_selection = _select_edit_stage(
        edit_selection=action_selection,
        next_stage_proposal=next_stage_proposal,
    )
    return _stage_selection_with_decision(
        stage_selection=stage_selection,
        next_stage_proposal=next_stage_proposal,
        action_selection=action_selection,
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
    return _assemble_stage_strategy(
        candidate_generator=_explore_candidates_via_strategy,
        ranking_enabled=_explore_ranking_enabled,
        rank_adjustment=_explore_rank_adjustment,
        action_selector=_select_explore_action,
        stage_selector=_explore_stage_selection,
        executor=_continue_without_side_effects_stage,
        outcomes=_stage_outcome_semantics(
            pause=_paused_explore_outcome,
            block=_blocked_explore_outcome,
            continue_outcome=_continue_stage_outcome,
        ),
    )


def _assemble_stage_strategy(
    *,
    candidate_generator: Callable[[_KernelPlannerContext, _KernelResumeState], list[_KernelNextStageCandidate]],
    ranking_enabled: Callable[[_KernelPlannerContext], bool],
    rank_adjustment: Callable[[_KernelPlannerContext, _KernelNextStageCandidate], int],
    action_selector: Callable[[_KernelPlannerContext], _KernelActionSelection | None],
    stage_selector: Callable[[_KernelActionSelection | None, _KernelNextStageProposal], _KernelStageSelection],
    executor: Callable[[CodingAgentExecutionRuntime, ExecutionRequest, object, _KernelResumeState, _KernelStagePlan, list[object]], _KernelStageOutcome],
    outcomes: _KernelStageOutcomeSemantics,
) -> _KernelStageStrategy:
    return _KernelStageStrategy(
        candidate_generator=candidate_generator,
        ranking_enabled=ranking_enabled,
        rank_adjustment=rank_adjustment,
        action_selector=action_selector,
        stage_selector=stage_selector,
        executor=executor,
        outcomes=outcomes,
    )


def _stage_outcome_semantics(
    *,
    pause: Callable[..., _KernelStageOutcome] | None = None,
    block: Callable[..., _KernelStageOutcome] | None = None,
    continue_outcome: Callable[..., _KernelStageOutcome] | None = None,
    complete: Callable[..., _KernelStageOutcome] | None = None,
) -> _KernelStageOutcomeSemantics:
    return _KernelStageOutcomeSemantics(
        pause=pause,
        block=block,
        continue_outcome=continue_outcome,
        complete=complete,
    )


def _edit_stage_strategy() -> _KernelStageStrategy:
    return _assemble_stage_strategy(
        candidate_generator=_edit_candidates_via_strategy,
        ranking_enabled=_edit_ranking_enabled,
        rank_adjustment=_edit_rank_adjustment,
        action_selector=_select_edit_action,
        stage_selector=_edit_stage_selection,
        executor=_execute_edit_stage,
        outcomes=_stage_outcome_semantics(
            pause=_paused_edit_outcome,
            block=_blocked_edit_outcome,
            continue_outcome=_applied_edit_outcome,
        ),
    )


def _verify_stage_strategy() -> _KernelStageStrategy:
    return _assemble_stage_strategy(
        candidate_generator=_verify_candidates_via_strategy,
        ranking_enabled=_verify_ranking_enabled,
        rank_adjustment=_verify_rank_adjustment,
        action_selector=_select_verify_action,
        stage_selector=_proposal_stage_selection,
        executor=_execute_verify_stage,
        outcomes=_stage_outcome_semantics(
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
        selection={
            "ranking_enabled": False,
            "candidate_count": len(candidates),
            "selected_candidate_id": selected_candidate.candidate_id,
        },
    )


def _proposal_from_decision(
    *,
    current_stage: RuntimeStage,
    decision: _KernelNextStageDecision,
    planner_context: _KernelPlannerContext | None = None,
) -> _KernelNextStageProposal:
    proposal = _KernelNextStageProposal(
        current_stage=current_stage,
        proposed_stage=decision.selected_candidate.stage,
        disposition=decision.selected_candidate.disposition,
        reason=decision.selected_candidate.reason,
        candidates=decision.candidates,
        selected_candidate_id=decision.selected_candidate.candidate_id,
        selection=decision.to_dict(),
    )
    if planner_context is None:
        return proposal
    return _augment_proposal_candidates_with_planner_alternatives(
        proposal,
        planner_context=planner_context,
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


def _planner_governed_recovery_alternatives(
    proposal: _KernelNextStageProposal,
    *,
    selected_action: str | None = None,
) -> list[dict[str, object]]:
    alternatives: list[dict[str, object]] = []
    for candidate in proposal.candidates:
        if not candidate.candidate_id.startswith("planner_"):
            continue
        action = None
        if candidate.candidate_id == "planner_need_human_confirmation_pause":
            action = "approval_pause"
        elif candidate.candidate_id == "planner_external_handoff_block":
            action = "handoff_external"
        elif candidate.candidate_id == "planner_governed_fallback_block":
            action = "fallback_external"
        if action is None:
            continue
        alternatives.append(
            {
                "candidate_id": candidate.candidate_id,
                "action": action,
                "stage": candidate.stage,
                "disposition": candidate.disposition,
                "reason": candidate.reason,
                "selected": action == selected_action,
            }
        )
    if selected_action and all(item.get("action") != selected_action for item in alternatives):
        selected_disposition = "pause" if selected_action in {"clarify_scope", "approval_pause"} else "block"
        alternatives.insert(
            0,
            {
                "candidate_id": f"selected_{selected_action}",
                "action": selected_action,
                "stage": proposal.current_stage,
                "disposition": selected_disposition,
                "reason": "Runtime selected this governed recovery lane from the native planner boundary.",
                "selected": True,
            },
        )
    return alternatives


def _augment_proposal_candidates_with_planner_alternatives(
    proposal: _KernelNextStageProposal,
    *,
    planner_context: _KernelPlannerContext,
) -> _KernelNextStageProposal:
    planner_alternatives = _planner_governed_alternative_candidates(planner_context)
    if not planner_alternatives:
        return proposal
    existing_ids = {candidate.candidate_id for candidate in proposal.candidates}
    merged_candidates = list(proposal.candidates)
    for candidate in planner_alternatives:
        if candidate.candidate_id in existing_ids:
            continue
        merged_candidates.append(candidate)
        existing_ids.add(candidate.candidate_id)
    selection = dict(proposal.selection)
    selection["candidate_count"] = len(merged_candidates)
    selection["planner_governed_alternative_count"] = len(merged_candidates) - len(proposal.candidates)
    selection["planner_governed_alternatives"] = [candidate.candidate_id for candidate in merged_candidates if candidate.candidate_id.startswith("planner_")]
    return _KernelNextStageProposal(
        current_stage=proposal.current_stage,
        proposed_stage=proposal.proposed_stage,
        disposition=proposal.disposition,
        reason=proposal.reason,
        candidates=merged_candidates,
        selected_candidate_id=proposal.selected_candidate_id,
        selection=selection,
    )


def _planner_governed_alternative_candidates(
    planner_context: _KernelPlannerContext,
) -> list[_KernelNextStageCandidate]:
    if planner_context.stage_cursor != "explore":
        return []
    evidence = planner_context.decision_evidence if isinstance(planner_context.decision_evidence, dict) else {}
    candidate_evidence = evidence.get("decision_candidate_evidence", [])
    if not isinstance(candidate_evidence, list):
        return []
    alternatives: list[_KernelNextStageCandidate] = []
    for item in candidate_evidence:
        if not isinstance(item, dict) or item.get("selected") is True:
            continue
        strategy = str(item.get("strategy") or "")
        if strategy == "need_human_confirmation":
            alternatives.append(
                _candidate(
                    candidate_id="planner_need_human_confirmation_pause",
                    stage="explore",
                    disposition="pause",
                    reason="Native planner preserved an approval-boundary pause alternative before continuing beyond exploration.",
                )
            )
        elif strategy == "external_handoff":
            alternatives.append(
                _candidate(
                    candidate_id="planner_external_handoff_block",
                    stage="explore",
                    disposition="block",
                    reason="Native planner preserved a governed external handoff alternative if bounded native execution exceeds its risk boundary.",
                )
            )
        elif strategy == "governed_fallback":
            alternatives.append(
                _candidate(
                    candidate_id="planner_governed_fallback_block",
                    stage="explore",
                    disposition="block",
                    reason="Native planner preserved a governed external fallback alternative if the native path cannot continue safely.",
                )
            )
    return alternatives


def _candidate_pair(
    first: _KernelNextStageCandidate,
    second: _KernelNextStageCandidate,
) -> list[_KernelNextStageCandidate]:
    return [first, second]


def _ordered_candidates(
    primary: _KernelNextStageCandidate,
    secondary: _KernelNextStageCandidate,
) -> list[_KernelNextStageCandidate]:
    return _candidate_pair(primary, secondary)


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
    return _ordered_candidates(advance_candidate, complete_candidate)


def _complete_or_retry_candidates(
    *,
    complete_candidate: _KernelNextStageCandidate,
    retry_candidate: _KernelNextStageCandidate,
) -> list[_KernelNextStageCandidate]:
    return _ordered_candidates(complete_candidate, retry_candidate)


def _block_or_retry_candidates(
    *,
    block_candidate: _KernelNextStageCandidate,
    retry_candidate: _KernelNextStageCandidate,
) -> list[_KernelNextStageCandidate]:
    return _ordered_candidates(block_candidate, retry_candidate)


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
    control_surface = (
        planner_context.control_surface
        if isinstance(planner_context.control_surface, dict)
        else {}
    )
    if not _planner_stage_enabled(planner_context, "edit") and not bool(control_surface.get("continue_native", True)):
        return _terminal_stage_candidates("explore")
    if not _planner_stage_enabled(planner_context, "edit") and _planner_stage_enabled(planner_context, "verify"):
        return _advance_or_complete_candidates(
            advance_candidate=_candidate(
                candidate_id="explore_to_verify_by_planner_contract",
                stage="verify",
                disposition="advance",
                reason="Planner-owned tool workflow omitted bounded edit work and advanced directly toward verification.",
            ),
            complete_candidate=_explore_complete_candidate(planner_context=planner_context),
        )
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


def _explore_stage_selection(
    action_selection: _KernelActionSelection | None,
    next_stage_proposal: _KernelNextStageProposal,
) -> _KernelStageSelection:
    if action_selection is None:
        return _select_next_stage(next_stage_proposal=next_stage_proposal)
    if action_selection.action_type == "pause":
        planner_actions = (
            action_selection.selected.get("planner_actions", [])
            if isinstance(action_selection.selected, dict)
            and isinstance(action_selection.selected.get("planner_actions"), list)
            else []
        )
        pause_reason = (
            "Native planner requested an approval pause before proceeding beyond exploration."
            if "approval_pause" in planner_actions
            else "Native planner requested a clarification pause before proceeding beyond exploration."
        )
        return _KernelStageSelection(
            stage="explore",
            outcome="pause",
            next_stage=next_stage_proposal.proposed_stage,
            reason=pause_reason,
        )
    if action_selection.action_type in {"handoff", "fallback"}:
        return _KernelStageSelection(
            stage="explore",
            outcome="block",
            next_stage=next_stage_proposal.proposed_stage,
            reason="Native planner selected a governed handoff or fallback before bounded execution could continue.",
        )
    return _select_next_stage(next_stage_proposal=next_stage_proposal)


def _select_explore_action(planner_context: _KernelPlannerContext) -> _KernelActionSelection | None:
    planner_actions = {
        str(item)
        for item in planner_context.planner_actions
        if isinstance(item, str) and item
    }
    control_surface = (
        planner_context.control_surface
        if isinstance(planner_context.control_surface, dict)
        else {}
    )
    delegation_contract = (
        planner_context.delegation_contract
        if isinstance(planner_context.delegation_contract, dict)
        else {}
    )
    operator_control = (
        planner_context.operator_control
        if isinstance(planner_context.operator_control, dict)
        else {}
    )
    intent = planner_context.route_planner_intent if isinstance(planner_context.route_planner_intent, dict) else {}
    if "approval_pause" in planner_actions or bool(operator_control.get("approval_pause_state")):
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="explore",
                action_type="pause",
                source="planner_control_surface",
                selected={
                    "planner_actions": list(planner_context.planner_actions),
                    "control_surface": dict(control_surface),
                    "operator_control": dict(operator_control),
                    "current_stage_workflow": dict(planner_context.current_stage_workflow),
                    "workflow_projection_required": bool(planner_context.tool_workflow_plan.get("workflow_projection_required")),
                },
                reason="Native planner requested an approval pause before the runtime advances beyond exploration.",
            ),
            planner_context=planner_context,
        )
    if "clarify" in planner_actions or bool(control_surface.get("clarify")) or bool(operator_control.get("clarify_pause_state")):
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="explore",
                action_type="pause",
                source="planner_control_surface",
                selected={
                    "planner_actions": list(planner_context.planner_actions),
                    "control_surface": dict(control_surface),
                    "operator_control": dict(operator_control),
                    "current_stage_workflow": dict(planner_context.current_stage_workflow),
                    "workflow_projection_required": bool(planner_context.tool_workflow_plan.get("workflow_projection_required")),
                },
                reason="Native planner requested a clarification pause before the runtime advances beyond exploration.",
            ),
            planner_context=planner_context,
        )
    if "handoff_external" in planner_actions or bool(control_surface.get("handoff")):
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="explore",
                action_type="handoff",
                source="planner_control_surface",
                selected={
                    "planner_actions": list(planner_context.planner_actions),
                    "delegation_contract": dict(delegation_contract),
                    "current_stage_workflow": dict(planner_context.current_stage_workflow),
                    "workflow_projection_required": bool(planner_context.tool_workflow_plan.get("workflow_projection_required")),
                },
                reason="Native planner selected governed external handoff before continuing natively.",
            ),
            planner_context=planner_context,
        )
    if "fallback_external" in planner_actions or bool(control_surface.get("fallback")):
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="explore",
                action_type="fallback",
                source="planner_control_surface",
                selected={
                    "planner_actions": list(planner_context.planner_actions),
                    "delegation_contract": dict(delegation_contract),
                    "current_stage_workflow": dict(planner_context.current_stage_workflow),
                    "workflow_projection_required": bool(planner_context.tool_workflow_plan.get("workflow_projection_required")),
                },
                reason="Native planner selected governed fallback before continuing natively.",
            ),
            planner_context=planner_context,
        )
    if bool(intent.get("clarify")):
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="explore",
                action_type="pause",
                source="route_planner_intent",
                selected={
                    "route_planner_intent": dict(intent),
                    "clarify_policy": planner_context.edit_mode,
                },
                reason="Route planner intent requested a clarification pause before the native path continues.",
            ),
            planner_context=planner_context,
        )
    if bool(intent.get("handoff")):
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="explore",
                action_type="handoff",
                source="route_planner_intent",
                selected={
                    "route_planner_intent": dict(intent),
                    "handoff_reason": "route_requested_handoff",
                },
                reason="Route planner intent requested a governed external handoff before continuing natively.",
            ),
            planner_context=planner_context,
        )
    if bool(intent.get("fallback")):
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="explore",
                action_type="fallback",
                source="route_planner_intent",
                selected={
                    "route_planner_intent": dict(intent),
                    "fallback_reason": "route_requested_fallback",
                },
                reason="Route planner intent requested a governed fallback before continuing natively.",
            ),
            planner_context=planner_context,
        )
    return None


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
    if planner_context.planner_actions and not _planner_stage_enabled(planner_context, "verify"):
        return _advance_or_complete_candidates(
            advance_candidate=complete_candidate,
            complete_candidate=complete_candidate,
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
    if planner_context.planner_actions and not _planner_stage_enabled(planner_context, "verify"):
        planner_complete = _verify_complete_candidate(
            planner_context=planner_context,
            variant="default",
            reason="Planner-owned tool workflow omitted verification from the active bounded path, so verify can terminate without rerunning commands.",
        )
        return _complete_or_retry_candidates(
            complete_candidate=planner_complete,
            retry_candidate=_candidate(
                candidate_id="verify_retry_same_stage",
                stage="verify",
                disposition="advance",
                reason="Verification would only remain active if a future planner revision explicitly re-enables verify.",
            ),
        )
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


def _stage_selection_with_decision(
    *,
    stage_selection: _KernelStageSelection,
    next_stage_proposal: _KernelNextStageProposal,
    action_selection: _KernelActionSelection | None,
) -> _KernelStageSelection:
    return _KernelStageSelection(
        stage=stage_selection.stage,
        outcome=stage_selection.outcome,
        next_stage=stage_selection.next_stage,
        reason=stage_selection.reason,
        decision=_KernelStageDecision(
            selection=stage_selection,
            next_stage_proposal=next_stage_proposal,
            action_selection=action_selection,
        ).to_dict(),
    )


def _action_selection_with_decision(
    *,
    action_selection: _KernelActionSelection,
    planner_context: _KernelPlannerContext,
) -> _KernelActionSelection:
    return _KernelActionSelection(
        stage=action_selection.stage,
        action_type=action_selection.action_type,
        source=action_selection.source,
        selected=dict(action_selection.selected),
        reason=action_selection.reason,
        decision=_KernelActionDecision(
            selection=action_selection,
            planner_context=planner_context,
        ).to_dict(),
    )


def _select_edit_action(planner_context: _KernelPlannerContext) -> _KernelActionSelection:
    if planner_context.approval_required and not planner_context.approval_resolved:
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="edit",
                action_type="pause",
                source="approval_policy",
                selected={
                    "mode": planner_context.edit_mode,
                    "operation_count": planner_context.operation_count,
                    "pending_approval_stage": planner_context.pending_approval_stage,
                    "current_stage_workflow": dict(planner_context.current_stage_workflow),
                    "workflow_projection_required": bool(planner_context.tool_workflow_plan.get("workflow_projection_required")),
                },
                reason="Edit action is paused until the required human approval is resolved.",
            ),
            planner_context=planner_context,
        )
    if planner_context.edit_mode == "direct_apply" and planner_context.operation_count == 0:
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="edit",
                action_type="block",
                source="invalid_intent",
                selected={
                    "mode": planner_context.edit_mode,
                    "operation_count": planner_context.operation_count,
                    "current_stage_workflow": dict(planner_context.current_stage_workflow),
                },
                reason="Direct-apply edit intent did not contain executable bounded operations.",
            ),
            planner_context=planner_context,
        )
    boundary_violation = _edit_boundary_violation(
        planner_context.operation_paths,
        workspace_root=Path(planner_context.workspace_root),
    )
    if boundary_violation is not None:
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="edit",
                action_type="block",
                source="boundary_policy",
                selected={
                    "mode": planner_context.edit_mode,
                    "operation_count": planner_context.operation_count,
                    "path": boundary_violation,
                    "boundary_policy": "workspace_root_only",
                    "current_stage_workflow": dict(planner_context.current_stage_workflow),
                },
                reason="Edit action was blocked before mutation because the selected file path escapes the workspace root.",
            ),
            planner_context=planner_context,
        )
    return _action_selection_with_decision(
        action_selection=_KernelActionSelection(
            stage="edit",
            action_type="file_mutation" if planner_context.edit_mode == "direct_apply" else "edit_prepare",
            source="explicit_operations" if planner_context.edit_mode == "direct_apply" else "bounded_context",
            selected={
                "mode": planner_context.edit_mode,
                "operation_count": planner_context.operation_count,
                "current_stage_workflow": dict(planner_context.current_stage_workflow),
                "workflow_projection_required": bool(planner_context.tool_workflow_plan.get("workflow_projection_required")),
            },
            reason="Edit action follows explicit bounded operations when present, otherwise stays in report-first preparation mode.",
        ),
        planner_context=planner_context,
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


def _paused_explore_outcome(
    *,
    action_selection: _KernelActionSelection,
    plan: _KernelStagePlan,
    resume_state: _KernelResumeState,
) -> _KernelStageOutcome:
    planner_actions = (
        action_selection.selected.get("planner_actions", [])
        if isinstance(action_selection.selected, dict)
        and isinstance(action_selection.selected.get("planner_actions"), list)
        else []
    )
    selected_pause_action = "approval_pause" if "approval_pause" in planner_actions else "clarify_scope"
    governed_alternatives = _planner_governed_recovery_alternatives(
        plan.next_stage_proposal,
        selected_action=selected_pause_action,
    )
    return _kernel_terminal_outcome(
        next_stage=plan.stage_cursor,
        pending_approval=None,
        applied_changes=[],
        repair_summary={
            "outcome": "approval_pause" if selected_pause_action == "approval_pause" else "clarify_pause",
            "attempt_count": 0,
            "retry_budget": 0,
            "attempts": [],
            "recovery_recommendation": {
                "action": selected_pause_action,
                "reason": action_selection.source,
                "human_review_recommended": True,
                "planner_governed_alternatives": governed_alternatives,
            },
        },
        final_verification=dict(resume_state.final_verification),
        status="blocked",
        accepted=False,
        should_stop=True,
    )


def _blocked_explore_outcome(
    *,
    action_selection: _KernelActionSelection,
    plan: _KernelStagePlan,
    resume_state: _KernelResumeState,
) -> _KernelStageOutcome:
    recovery_action = "handoff_external" if action_selection.action_type == "handoff" else "fallback_external"
    governed_alternatives = _planner_governed_recovery_alternatives(
        plan.next_stage_proposal,
        selected_action=recovery_action,
    )
    return _kernel_terminal_outcome(
        next_stage=plan.stage_cursor,
        pending_approval=None,
        applied_changes=[],
        repair_summary={
            "outcome": "planner_boundary_redirect",
            "attempt_count": 0,
            "retry_budget": 0,
            "attempts": [],
            "recovery_recommendation": {
                "action": recovery_action,
                "reason": action_selection.source,
                "human_review_recommended": True,
                "planner_governed_alternatives": governed_alternatives,
            },
        },
        final_verification=dict(resume_state.final_verification),
        status="blocked",
        accepted=False,
        should_stop=True,
    )


def _select_verify_action(planner_context: _KernelPlannerContext) -> _KernelActionSelection:
    if planner_context.planner_actions and not _planner_stage_enabled(planner_context, "verify"):
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="verify",
                action_type="complete",
                source="planner_control_surface",
                selected={
                    "planner_actions": list(planner_context.planner_actions),
                    "selected_strategy": planner_context.selected_strategy,
                    "current_stage_workflow": dict(planner_context.current_stage_workflow),
                    "workflow_projection_required": bool(planner_context.tool_workflow_plan.get("workflow_projection_required")),
                },
                reason="Planner-owned tool workflow omitted verification from the active bounded path, so verify should complete without rerunning commands.",
            ),
            planner_context=planner_context,
        )
    if planner_context.approval_required and not planner_context.approval_resolved:
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="verify",
                action_type="pause",
                source="approval_policy",
                selected={
                    "pending_approval_stage": planner_context.pending_approval_stage,
                    "target_paths": list(planner_context.target_paths),
                    "current_stage_workflow": dict(planner_context.current_stage_workflow),
                },
                reason="Verification action is paused until the required human approval is resolved.",
            ),
            planner_context=planner_context,
        )
    if planner_context.should_block_verify_resume:
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="verify",
                action_type="block",
                source="exhausted_recovery",
                selected={
                    "remaining_retry_budget": planner_context.remaining_retry_budget,
                    "latest_observation_kind": planner_context.latest_observation_kind,
                    "current_stage_workflow": dict(planner_context.current_stage_workflow),
                },
                reason="Verification is blocked because continuation state shows failure with no remaining retry budget.",
            ),
            planner_context=planner_context,
        )
    if planner_context.verification_command:
        return _action_selection_with_decision(
            action_selection=_KernelActionSelection(
                stage="verify",
                action_type="run_command",
                source="resume_context",
                selected={
                    "command": list(planner_context.verification_command),
                    "current_stage_workflow": dict(planner_context.current_stage_workflow),
                    "workflow_projection_required": bool(planner_context.tool_workflow_plan.get("workflow_projection_required")),
                },
                reason="Verification reused the planned command from continuation state.",
            ),
            planner_context=planner_context,
        )
    derived = _planned_verification_command(planner_context.target_paths)
    return _action_selection_with_decision(
        action_selection=_KernelActionSelection(
            stage="verify",
            action_type="run_command",
            source="derived_from_targets",
            selected={
                "command": list(derived),
                "current_stage_workflow": dict(planner_context.current_stage_workflow),
                "workflow_projection_required": bool(planner_context.tool_workflow_plan.get("workflow_projection_required")),
            },
            reason="Verification command derived from bounded target paths in the current edit intent.",
        ),
        planner_context=planner_context,
    )


def _planner_stage_enabled(
    planner_context: _KernelPlannerContext,
    stage_name: str,
) -> bool:
    workflow_stages = (
        planner_context.tool_workflow_plan.get("workflow_stages", {})
        if isinstance(planner_context.tool_workflow_plan.get("workflow_stages"), dict)
        else {}
    )
    stage_workflow = workflow_stages.get(stage_name, {}) if isinstance(workflow_stages.get(stage_name), dict) else {}
    if stage_workflow:
        return stage_workflow.get("selected") is True
    return stage_name in {
        str(item)
        for item in planner_context.planner_actions
        if isinstance(item, str) and item
    }


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
    verifiable = [str(item) for item in target_paths if isinstance(item, str) and Path(str(item)).suffix.lower() in {".py", ".pyi"}]
    if not verifiable:
        return []
    return ["python3", "-m", "compileall", *verifiable]


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


def _active_loop_decision(
    *,
    decisions: list[ExecutionStepDecision],
    pending_approval: dict[str, object] | None,
) -> ExecutionStepDecision | None:
    if isinstance(pending_approval, dict):
        pending_stage = str(pending_approval.get("stage") or "")
        target_kind = "edit_execution" if pending_stage == "edit" else "verification" if pending_stage == "verify" else None
        if target_kind is not None:
            selected = next((decision for decision in decisions if decision.step_kind == target_kind), None)
            if selected is not None:
                return selected
    return next(
        (decision for decision in reversed(decisions) if decision.disposition in {"pause", "block", "complete"}),
        decisions[-1] if decisions else None,
    )


def _next_step_contract(
    *,
    decisions: list[ExecutionStepDecision],
    status: str,
    pending_approval: dict[str, object] | None,
    resume_context: dict[str, object] | None = None,
    context_engineering_contract: dict[str, object] | None = None,
) -> dict[str, object]:
    active = _active_loop_decision(decisions=decisions, pending_approval=pending_approval)
    resume_reason = _resume_reason_hint(resume_context)
    current_step_kind = active.step_kind if active is not None else None
    return {
        "status": status,
        "current_disposition": active.disposition if active is not None else "complete",
        "current_step_kind": current_step_kind,
        "next_step_kind": active.next_step_kind if active is not None else None,
        "reason": resume_reason or (active.reason if active is not None else "No further steps recorded."),
        "pending_approval": dict(pending_approval) if isinstance(pending_approval, dict) else None,
        "context_engineering_refs": _context_refs_for_step_kind(
            step_kind=current_step_kind,
            context_engineering_contract=context_engineering_contract,
        ),
    }


def _step_loop_contract(
    *,
    status: str,
    planner_context_trace: list[dict[str, object]],
    next_stage_proposals: list[dict[str, object]],
    stage_selection_trace: list[dict[str, object]],
    action_selection_trace: list[dict[str, object]],
    decisions: list[ExecutionStepDecision],
    pending_approval: dict[str, object] | None,
    next_step_contract: dict[str, object],
    resume_context: dict[str, object],
    context_engineering_contract: dict[str, object] | None = None,
) -> dict[str, object]:
    final_context = planner_context_trace[-1] if planner_context_trace else {}
    final_stage = final_context.get("stage_cursor")
    active = _active_loop_decision(decisions=decisions, pending_approval=pending_approval)
    current_step_kind = active.step_kind if active is not None else next_step_contract.get("current_step_kind")
    return {
        "loop_model": "explicit_stage_step_loop",
        "status": status,
        "current_stage": final_stage,
        "terminal_stage": final_stage if status in {"completed", "blocked"} else None,
        "current_disposition": active.disposition if active is not None else next_step_contract.get("current_disposition"),
        "current_step_kind": current_step_kind,
        "resume_supported": bool(resume_context.get("resume_supported", True)),
        "resume_kind": resume_context.get("resume_kind"),
        "context_engineering_refs": _context_refs_for_step_kind(
            step_kind=current_step_kind,
            context_engineering_contract=context_engineering_contract,
        ),
        "trace_lengths": {
            "planner_context_trace": len(planner_context_trace),
            "next_stage_proposals": len(next_stage_proposals),
            "stage_selection_trace": len(stage_selection_trace),
            "action_selection_trace": len(action_selection_trace),
        },
        "trace_refs": {
            "planner_context_trace": "payload.planner_context_trace",
            "next_stage_proposals": "payload.next_stage_proposals",
            "stage_selection_trace": "payload.stage_selection_trace",
            "action_selection_trace": "payload.action_selection_trace",
            "next_step_contract": "payload.next_step_contract",
        },
    }


def _context_refs_for_step_kind(
    *,
    step_kind: str | None,
    context_engineering_contract: dict[str, object] | None,
) -> dict[str, object]:
    refs = (
        context_engineering_contract.get("trace_refs", {})
        if isinstance(context_engineering_contract, dict)
        and isinstance(context_engineering_contract.get("trace_refs"), dict)
        else {}
    )
    if not isinstance(step_kind, str) or not step_kind:
        return {"required_surfaces": [], "trace_refs": {}}
    required_surfaces = ["select", "structured_observation"]
    if step_kind == "repo_exploration":
        required_surfaces = ["write", "select", "structured_observation"]
    elif step_kind == "edit_execution":
        required_surfaces = ["write", "select", "structured_observation", "isolate"]
    elif step_kind == "verification":
        required_surfaces = ["select", "structured_observation", "compact", "resume_continuity"]
    surface_ref_map = {
        "write": {
            "scratchpad_entries": refs.get("scratchpad_entries"),
            "compressed_context": refs.get("compressed_context"),
            "resume_context": refs.get("resume_context"),
        },
        "select": {
            "context_selection": refs.get("context_selection"),
        },
        "structured_observation": {
            "structured_observations": refs.get("structured_observations"),
        },
        "compact": {
            "compaction_state": refs.get("compaction_state"),
            "compressed_context": refs.get("compressed_context"),
        },
        "isolate": {
            "isolation_state": refs.get("isolation_state"),
        },
        "resume_continuity": {
            "resume_context": refs.get("resume_context"),
        },
    }
    return {
        "required_surfaces": required_surfaces,
        "trace_refs": {
            surface: surface_ref_map[surface]
            for surface in required_surfaces
            if surface in surface_ref_map
        },
    }


def _context_engineering_contract(
    *,
    request: ExecutionRequest,
    context_selection: dict[str, object],
    structured_observations: list[dict[str, object]],
    compaction_state: dict[str, object],
    compressed_context: dict[str, object],
    isolation_state: dict[str, object],
    resume_context: dict[str, object],
    scratchpad_entries: list[dict[str, object]],
    retrieved_memory: list[dict[str, object]] | object,
) -> dict[str, object]:
    deterministic = context_selection.get("deterministic", {}) if isinstance(context_selection, dict) else {}
    retrieval = context_selection.get("retrieval", {}) if isinstance(context_selection, dict) else {}
    model_driven = context_selection.get("model_driven", {}) if isinstance(context_selection, dict) else {}
    latest_scratchpad = scratchpad_entries[0] if isinstance(scratchpad_entries, list) and scratchpad_entries else {}
    memory_count = len(retrieved_memory) if isinstance(retrieved_memory, list) else 0
    recent_observation_count = (
        len(resume_context.get("recent_observations", []))
        if isinstance(resume_context.get("recent_observations"), list)
        else 0
    )
    return {
        "format": "agent_orchestrator.context_engineering_contract.v1",
        "requirement": request.requirement,
        "main_path_required": True,
        "write": {
            "session_scratchpad": {
                "required": True,
                "entry_kind": latest_scratchpad.get("kind") if isinstance(latest_scratchpad, dict) else None,
                "entry_ref": "payload.scratchpad_entries[0]" if latest_scratchpad else None,
            },
            "persistent_memory": {
                "required": True,
                "namespace": "coding_agent",
                "retrieved_memory_count": memory_count,
                "projection_mode": "explicit_memory_store",
            },
            "transient_loop_context": {
                "required": True,
                "compressed_context_ref": "payload.compressed_context",
                "resume_context_ref": "payload.resume_context",
            },
        },
        "select": {
            "required_for_model_participation": True,
            "deterministic_strategy": deterministic.get("strategy"),
            "retrieval_strategy": retrieval.get("strategy"),
            "model_driven_used": bool(model_driven.get("used_model")),
            "selected_context_ref": "payload.context_selection.selected_context",
            "selected_memory_count": retrieval.get("selected_memory_count", 0),
        },
        "structured_observation": {
            "required_post_action": True,
            "record_count": len(structured_observations),
            "artifact_backed_count": sum(1 for item in structured_observations if item.get("has_artifact") is True),
            "deduplicated_count": sum(1 for item in structured_observations if item.get("deduplicated") is True),
            "records_ref": "payload.structured_observations",
        },
        "compact": {
            "required_when_context_pressure_rises": True,
            "stage": compaction_state.get("stage") if isinstance(compaction_state, dict) else None,
            "light_compaction_applied": bool(compaction_state.get("light_compaction_applied")) if isinstance(compaction_state, dict) else False,
            "summarization_triggered": bool(compaction_state.get("summarization_triggered")) if isinstance(compaction_state, dict) else False,
            "compressed_context_ref": "payload.compressed_context",
        },
        "isolate": {
            "required_when_complexity_exceeds_loop_budget": True,
            "applied": bool(isolation_state.get("applied")) if isinstance(isolation_state, dict) else False,
            "strategy": isolation_state.get("strategy") if isinstance(isolation_state, dict) else None,
            "input_target_count": isolation_state.get("input_target_count") if isinstance(isolation_state, dict) else None,
            "output_target_count": isolation_state.get("output_target_count") if isinstance(isolation_state, dict) else None,
            "input_patch_plan_count": isolation_state.get("input_patch_plan_count") if isinstance(isolation_state, dict) else None,
            "output_patch_plan_count": isolation_state.get("output_patch_plan_count") if isinstance(isolation_state, dict) else None,
            "reinjection_mode": isolation_state.get("reinjection_mode") if isinstance(isolation_state, dict) else None,
            "reinjection_targets_ref": "payload.isolation_state.reinjection_targets",
            "digest_ref": "payload.isolation_state.digest",
        },
        "resume_continuity": {
            "required": True,
            "resume_kind": resume_context.get("resume_kind") if isinstance(resume_context, dict) else None,
            "recent_observation_count": recent_observation_count,
            "planned_verification_command_present": bool(
                isinstance(resume_context, dict) and resume_context.get("planned_verification_command")
            ),
            "repair_summary_present": bool(isinstance(resume_context, dict) and isinstance(resume_context.get("repair_summary"), dict)),
        },
        "trace_refs": {
            "context_selection": "payload.context_selection",
            "structured_observations": "payload.structured_observations",
            "compaction_state": "payload.compaction_state",
            "compressed_context": "payload.compressed_context",
            "isolation_state": "payload.isolation_state",
            "resume_context": "payload.resume_context",
            "scratchpad_entries": "payload.scratchpad_entries",
        },
        "notes": "This contract lifts context-engineering behavior into one explicit main-path surface instead of relying on scattered payload fields alone.",
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
            alternatives = (
                recommendation.get("planner_governed_alternatives", [])
                if isinstance(recommendation.get("planner_governed_alternatives"), list)
                else []
            )
            alternative_actions = [
                str(item.get("action"))
                for item in alternatives
                if isinstance(item, dict) and item.get("action")
            ]
            if action or reason:
                suffix = (
                    f" alternatives={','.join(alternative_actions)}"
                    if alternative_actions
                    else ""
                )
                return f"Resume context: action={action or 'continue'} reason={reason or 'n/a'}{suffix}"
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


def _session_continuity_contract(*, payload: dict[str, object]) -> dict[str, object]:
    resume_context = payload.get("resume_context", {}) if isinstance(payload.get("resume_context"), dict) else {}
    compaction_state = payload.get("compaction_state", {}) if isinstance(payload.get("compaction_state"), dict) else {}
    step_loop_contract = payload.get("step_loop_contract", {}) if isinstance(payload.get("step_loop_contract"), dict) else {}
    strategy_summary = payload.get("strategy_summary", {}) if isinstance(payload.get("strategy_summary"), dict) else {}
    path_selection = payload.get("path_selection", {}) if isinstance(payload.get("path_selection"), dict) else {}
    adapter_contract = payload.get("adapter_contract", {}) if isinstance(payload.get("adapter_contract"), dict) else {}
    verification = payload.get("verification", {}) if isinstance(payload.get("verification"), dict) else {}
    recovery_summary = payload.get("recovery_summary", {}) if isinstance(payload.get("recovery_summary"), dict) else {}
    recovery_governed_alternatives = (
        [dict(item) for item in recovery_summary.get("planner_governed_alternatives", []) if isinstance(item, dict)]
        if isinstance(recovery_summary.get("planner_governed_alternatives"), list)
        else []
    )
    compressed_context = payload.get("compressed_context", {}) if isinstance(payload.get("compressed_context"), dict) else {}
    context_snapshot = payload.get("context_snapshot", {}) if isinstance(payload.get("context_snapshot"), dict) else {}
    native_tool_surface = (
        payload.get("native_tool_surface", {})
        if isinstance(payload.get("native_tool_surface"), dict)
        else {}
    )
    context_task_contract = (
        context_snapshot.get("task_contract", {})
        if isinstance(context_snapshot.get("task_contract"), dict)
        else {}
    )
    execution_history = (
        payload.get("execution_history_summary", {})
        if isinstance(payload.get("execution_history_summary"), dict)
        else {}
    )
    native_repo_task_acceptance = (
        payload.get("native_repo_task_acceptance", {})
        if isinstance(payload.get("native_repo_task_acceptance"), dict)
        else {}
    )
    native_complex_repo_task_acceptance = (
        payload.get("native_complex_repo_task_acceptance", {})
        if isinstance(payload.get("native_complex_repo_task_acceptance"), dict)
        else {}
    )
    recent_observations = (
        resume_context.get("recent_observations", [])
        if isinstance(resume_context.get("recent_observations"), list)
        else []
    )
    native_tool_trace = (
        payload.get("native_tool_trace", {})
        if isinstance(payload.get("native_tool_trace"), dict)
        else {}
    )
    trace_entries = (
        native_tool_trace.get("trace", [])
        if isinstance(native_tool_trace.get("trace"), list)
        else []
    )
    repair_summary = resume_context.get("repair_summary", {}) if isinstance(resume_context.get("repair_summary"), dict) else {}
    pending_steps = (
        execution_history.get("pending_steps", [])
        if isinstance(execution_history.get("pending_steps"), list)
        else []
    )
    completed_steps = (
        execution_history.get("completed_steps", [])
        if isinstance(execution_history.get("completed_steps"), list)
        else []
    )
    active_milestone = (
        step_loop_contract.get("current_stage")
        or strategy_summary.get("current_checkpoint_objective")
        or payload.get("requirement")
    )
    task_contract = payload.get("task_contract", {}) if isinstance(payload.get("task_contract"), dict) else {}
    ready_next_units = [
        str(item)
        for item in pending_steps[:3]
        if item not in {None, ""}
    ]
    blocked_units = [
        str(item)
        for item in [
            recovery_summary.get("reason"),
            verification.get("failure_kind"),
        ]
        if item not in {None, ""}
    ]
    required_handoff_artifacts = (
        list(adapter_contract.get("evidence_outputs", []))
        if isinstance(adapter_contract.get("evidence_outputs"), list)
        else []
    )
    remaining_checks = (
        list(verification.get("remaining_checks", []))
        if isinstance(verification.get("remaining_checks"), list)
        else []
    )
    resume_supported = bool(resume_context.get("resume_supported", step_loop_contract.get("resume_supported", True)))
    runtime_duration_seconds = _runtime_duration_seconds_from_trace(payload)
    usage_cost_measurement_status = _usage_cost_measurement_status(payload)
    runtime_cost_provenance = {
        "format": "agent_orchestrator.runtime_cost_provenance.v1",
        "duration_source": "native_tool_trace" if runtime_duration_seconds is not None else "unavailable",
        "usage_cost_source": "runtime_usage_payload"
        if usage_cost_measurement_status == "measured"
        else "placeholder_until_provider_reports",
        "trace_entry_count": len(trace_entries),
        "trace_time_span_ready": runtime_duration_seconds is not None,
    }
    repo_task_acceptance_ready = native_repo_task_acceptance.get("real_repo_task_acceptance_ready") is True
    complex_repo_task_acceptance_ready = native_complex_repo_task_acceptance.get("complex_repo_task_ready") is True
    long_chain_native_first_ready = repo_task_acceptance_ready and complex_repo_task_acceptance_ready
    planner_decision = (
        strategy_summary.get("decision_evidence", {})
        if isinstance(strategy_summary.get("decision_evidence"), dict)
        else {}
    )
    tool_workflow_plan = (
        dict(planner_decision.get("tool_workflow_plan", {}))
        if isinstance(planner_decision.get("tool_workflow_plan"), dict)
        else {}
    )
    if not tool_workflow_plan:
        selected_actions = (
            list(planner_decision.get("selected_actions", []))
            if isinstance(planner_decision.get("selected_actions"), list)
            else []
        )
        workflow_stages_fallback: dict[str, object] = {}
        daily_driver_tools: list[str] = []
        for stage_name, required_tools in {
            "explore": ["repo_map", "find_files", "search", "outline", "read"],
            "edit": ["patch_preview", "structured_patch", "diff_preview"],
            "verify": ["verify", "tool_trace"],
        }.items():
            selected = stage_name in selected_actions
            workflow_stages_fallback[stage_name] = {
                "selected": selected,
                "required_tools": list(required_tools),
                "projection_required": selected,
            }
            if selected:
                for tool_name in required_tools:
                    if tool_name not in daily_driver_tools:
                        daily_driver_tools.append(tool_name)
        tool_workflow_plan = {
            "format": "agent_orchestrator.native_tool_workflow_plan.v1"
            if str(planner_decision.get("planner_family") or "native") == "native"
            else "agent_orchestrator.compatibility_tool_workflow_plan.v1",
            "planner_family": planner_decision.get("planner_family") or "native",
            "selected_strategy": planner_decision.get("selected_strategy"),
            "workflow_stage_order": [
                stage_name for stage_name in ("explore", "edit", "verify") if stage_name in selected_actions
            ],
            "workflow_stages": workflow_stages_fallback,
            "daily_driver_path": {
                "tools": daily_driver_tools,
                "selected_stage_count": len([item for item in workflow_stages_fallback.values() if item.get("selected") is True]),
            },
            "workflow_projection_required": True,
        }
    workflow_stages = (
        tool_workflow_plan.get("workflow_stages", {})
        if isinstance(tool_workflow_plan.get("workflow_stages"), dict)
        else {}
    )
    planner_context_trace = (
        payload.get("planner_context_trace", [])
        if isinstance(payload.get("planner_context_trace"), list)
        else []
    )
    action_selection_trace = (
        payload.get("action_selection_trace", [])
        if isinstance(payload.get("action_selection_trace"), list)
        else []
    )
    selected_workflow_stages = [
        stage_name
        for stage_name in ("explore", "edit", "verify")
        if isinstance(workflow_stages.get(stage_name), dict) and workflow_stages.get(stage_name, {}).get("selected") is True
    ]
    trace_stage_alignment = {
        stage_name: any(
            isinstance(item, dict)
            and item.get("stage_cursor") == stage_name
            and isinstance(item.get("current_stage_workflow"), dict)
            and item.get("current_stage_workflow", {}).get("selected") is True
            for item in planner_context_trace
        )
        for stage_name in selected_workflow_stages
    }
    action_required_tool_alignment = {
        stage_name: any(
            isinstance(item, dict)
            and item.get("stage") == stage_name
            and isinstance(item.get("decision"), dict)
            and all(
                tool_name in item.get("decision", {}).get("current_stage_required_tools", [])
                for tool_name in workflow_stages.get(stage_name, {}).get("required_tools", [])
                if isinstance(tool_name, str)
            )
            for item in action_selection_trace
        )
        for stage_name in ("edit", "verify")
        if isinstance(workflow_stages.get(stage_name), dict) and workflow_stages.get(stage_name, {}).get("selected") is True
    }
    adapter_capability_surface = (
        adapter_contract.get("capability_surface", {})
        if isinstance(adapter_contract.get("capability_surface"), dict)
        else {}
    )
    adapter_governance = (
        adapter_capability_surface.get("governance", {})
        if isinstance(adapter_capability_surface.get("governance"), dict)
        else {}
    )
    adapter_comparability = (
        adapter_capability_surface.get("comparability", {})
        if isinstance(adapter_capability_surface.get("comparability"), dict)
        else {}
    )
    tool_surface_readiness = (
        native_tool_surface.get("daily_driver_readiness", {})
        if isinstance(native_tool_surface.get("daily_driver_readiness"), dict)
        else {}
    )
    tool_surface_ready = all(
        bool(tool_surface_readiness.get(key))
        for key in [
            "repo_exploration_ready",
            "structured_patch_ready",
            "patch_preview_ready",
            "diff_preview_ready",
            "verification_ready",
        ]
    )
    planner_ready = (
        planner_decision.get("format") == "agent_orchestrator.native_planner_decision.v1"
        and planner_decision.get("selected_owner") == "native"
        and bool(planner_decision.get("native_work_units"))
    )
    session_ready = bool(resume_supported) and runtime_duration_seconds is not None and bool(usage_cost_measurement_status)
    adapter_ready = (
        (
            adapter_contract.get("comparison_mode") == "same_contract_two_executors"
            or adapter_comparability.get("comparison_mode") == "same_contract_two_executors"
        )
        and bool(
            adapter_contract.get("hot_plug_supported")
            if adapter_contract.get("hot_plug_supported") is not None
            else adapter_governance.get("hot_plug_supported")
        )
        and bool(
            adapter_contract.get("fallback_governed")
            if adapter_contract.get("fallback_governed") is not None
            else adapter_governance.get("fallback_governed")
        )
    )
    shared_productization_ready = all(
        [
            tool_surface_ready,
            planner_ready,
            session_ready,
            adapter_ready,
        ]
    )
    daily_driver_main_path_ready = shared_productization_ready and long_chain_native_first_ready
    shared_evidence_surface = [
        "runtime_payload",
        "workspace_index",
        "ui_execution_summary",
        "cli_execution_summary",
        "docs_evidence",
        "comparative_completion_summary",
    ]
    long_horizon_posture = {
        "resume_ready": resume_supported,
        "recovery_active": bool(repair_summary) or bool(recent_observations),
        "verification_resume_ready": bool(resume_context.get("planned_verification_command")),
        "context_pressure": compaction_state.get("stage") in {"light_compaction", "observation_masking", "summarization_ready"},
        "summarization_ready": compaction_state.get("stage") == "summarization_ready",
        "pending_followup_count": len(pending_steps),
        "resume_posture": (
            "approval_reentry"
            if resume_context.get("resume_kind") == "approval_resume"
            else "same_task_resume"
            if resume_context.get("resume_kind") == "resume_if_same_task"
            else "fresh_entry"
        ),
    }
    continuity_pressure = {
        "format": "agent_orchestrator.continuity_pressure.v1",
        "observation_pressure": len(recent_observations),
        "compaction_pressure": compaction_state.get("stage"),
        "pending_followup_count": len(pending_steps),
        "blocked_unit_count": len(blocked_units),
        "summarization_pressure": bool(compaction_state.get("summarization_triggered"))
        or compaction_state.get("stage") == "summarization_ready",
        "pressure_level": (
            "high"
            if compaction_state.get("stage") == "summarization_ready" or len(pending_steps) >= 3
            else "medium"
            if compaction_state.get("stage") in {"light_compaction", "observation_masking"} or len(recent_observations) >= 2
            else "low"
        ),
    }
    workflow_resume_expectation = (
        "resume_if_same_task"
        if resume_supported and resume_context.get("resume_kind") in {None, "fresh", "resume_if_same_task"}
        else "approval_pause"
        if resume_context.get("resume_kind") == "approval_resume"
        else resume_context.get("resume_kind")
    )
    recovery_lane = recovery_summary.get("reason")
    workflow_active_stage = (
        recovery_summary.get("action")
        or step_loop_contract.get("current_disposition")
        or step_loop_contract.get("current_stage")
    )
    if workflow_active_stage not in {"explore", "edit", "verify"}:
        workflow_active_stage = next((item for item in selected_workflow_stages if item), None)
    workflow_projection_ready = (
        tool_workflow_plan.get("format") == "agent_orchestrator.native_tool_workflow_plan.v1"
        and tool_workflow_plan.get("workflow_projection_required") is True
        and all(trace_stage_alignment.get(stage_name) for stage_name in selected_workflow_stages)
        and all(action_required_tool_alignment.get(stage_name) for stage_name in action_required_tool_alignment)
    )
    workflow_continuity = {
        "format": "agent_orchestrator.session_workflow_continuity.v1",
        "resume_kind": resume_context.get("resume_kind"),
        "active_stage": workflow_active_stage,
        "selected_workflow_stages": selected_workflow_stages,
        "tool_workflow_plan": tool_workflow_plan,
        "workflow_projection_ready": workflow_projection_ready,
        "resume_alignment": {
            "resume_kind": resume_context.get("resume_kind"),
            "resume_posture": long_horizon_posture.get("resume_posture"),
            "resume_expectation": workflow_resume_expectation,
            "aligned": resume_supported and bool(selected_workflow_stages),
        },
        "recovery_alignment": {
            "recovery_active": bool(repair_summary) or bool(recent_observations),
            "runbook_recovery_lane": recovery_lane,
            "latest_recovery_hint": compressed_context.get("latest_recovery_hint"),
            "aligned": not bool(recovery_lane) or workflow_active_stage in {None, *selected_workflow_stages},
        },
        "shared_evidence_surface": list(dict.fromkeys([*shared_evidence_surface, "resume_contract"])),
    }
    continuity_snapshot = {
        "format": "agent_orchestrator.session_continuity_snapshot.v1",
        "artifact_backed": True,
        "snapshot_status": "ready" if resume_supported else "limited",
        "resume_anchor": {
            "resume_kind": resume_context.get("resume_kind"),
            "planned_verification_command_present": bool(resume_context.get("planned_verification_command")),
            "recent_observation_count": len(recent_observations),
            "repair_summary_present": bool(repair_summary),
        },
        "program_digest": {
            "program_goal": (
                task_contract.get("goal")
                or context_task_contract.get("goal")
                or strategy_summary.get("goal")
                or payload.get("requirement")
                or compressed_context.get("objective")
                or active_milestone
            ),
            "active_milestone": active_milestone,
            "completed_milestone_count": len(completed_steps),
            "pending_followup_count": len(pending_steps),
            "blocked_unit_count": len(blocked_units),
        },
        "compaction_digest": {
            "compaction_stage": compaction_state.get("stage"),
            "masked_observation_count": compaction_state.get("masked_count", 0),
            "summarization_triggered": compaction_state.get("summarization_triggered", False),
            "summarization_ready": compaction_state.get("stage") == "summarization_ready",
        },
        "runtime_cost": {
            "runtime_duration_seconds": runtime_duration_seconds,
            "usage_cost_measurement_status": usage_cost_measurement_status,
        },
        "runtime_cost_provenance": runtime_cost_provenance,
        "continuity_pressure": continuity_pressure,
        "shared_evidence_surface": shared_evidence_surface,
    }
    session_productization_surface = {
        "format": "agent_orchestrator.session_productization_surface.v1",
        "resume_supported": resume_supported,
        "resume_kind": resume_context.get("resume_kind"),
        "continuity_status": "ready" if resume_supported else "limited",
        "compaction_stage": compaction_state.get("stage"),
        "runtime_duration_seconds": runtime_duration_seconds,
        "usage_cost_measurement_status": usage_cost_measurement_status,
        "runtime_cost_provenance": runtime_cost_provenance,
        "continuity_snapshot": continuity_snapshot,
        "continuity_pressure": continuity_pressure,
        "workflow_continuity": workflow_continuity,
        "operator_continuity": {
            "latest_recovery_hint": compressed_context.get("latest_recovery_hint"),
            "next_recommended_action": (
                recovery_summary.get("action")
                or step_loop_contract.get("current_disposition")
                or step_loop_contract.get("current_stage")
            ),
            "runbook_recovery_lane": recovery_summary.get("reason"),
            "approval_pause_state": adapter_contract.get("approval_semantics", {}).get("approval_required")
            if isinstance(adapter_contract.get("approval_semantics"), dict)
            else None,
            "clarify_pause_state": bool(payload.get("clarify_summary", {}).get("needs_clarification"))
            if isinstance(payload.get("clarify_summary"), dict)
            else False,
            "resume_expectation": workflow_resume_expectation,
            "resume_posture": long_horizon_posture.get("resume_posture"),
            "planner_governed_alternatives": recovery_governed_alternatives,
            "workflow_active_stage": workflow_active_stage,
            "selected_workflow_stages": selected_workflow_stages,
            "workflow_projection_ready": workflow_projection_ready,
        },
        "operator_posture_digest": {
            "format": "agent_orchestrator.session_operator_posture_digest.v1",
            "continuity_status": "ready" if resume_supported else "limited",
            "compaction_stage": compaction_state.get("stage"),
            "compaction_pressure": continuity_pressure.get("compaction_pressure"),
            "context_pressure": long_horizon_posture.get("context_pressure"),
            "runtime_duration_seconds": runtime_duration_seconds,
            "usage_cost_measurement_status": usage_cost_measurement_status,
            "runtime_cost_provenance": runtime_cost_provenance,
            "next_recommended_action": (
                recovery_summary.get("action")
                or step_loop_contract.get("current_disposition")
                or step_loop_contract.get("current_stage")
            ),
            "runbook_recovery_lane": recovery_summary.get("reason"),
            "resume_expectation": workflow_resume_expectation,
            "resume_posture": long_horizon_posture.get("resume_posture"),
            "approval_pause_state": adapter_contract.get("approval_semantics", {}).get("approval_required")
            if isinstance(adapter_contract.get("approval_semantics"), dict)
            else None,
            "clarify_pause_state": bool(payload.get("clarify_summary", {}).get("needs_clarification"))
            if isinstance(payload.get("clarify_summary"), dict)
            else False,
            "workflow_active_stage": workflow_active_stage,
            "selected_workflow_stages": selected_workflow_stages,
            "workflow_projection_ready": workflow_projection_ready,
            "tool_workflow_plan_format": tool_workflow_plan.get("format"),
            "pause_expected": bool(
                strategy_summary.get("decision_evidence", {}).get("posture", {}).get("pause_expected")
            )
            if isinstance(strategy_summary.get("decision_evidence"), dict)
            and isinstance(strategy_summary.get("decision_evidence", {}).get("posture"), dict)
            else False,
            "handoff_expected": bool(
                strategy_summary.get("decision_evidence", {}).get("posture", {}).get("handoff_expected")
            )
            if isinstance(strategy_summary.get("decision_evidence"), dict)
            and isinstance(strategy_summary.get("decision_evidence", {}).get("posture"), dict)
            else False,
            "fallback_expected": bool(
                strategy_summary.get("decision_evidence", {}).get("posture", {}).get("fallback_expected")
            )
            if isinstance(strategy_summary.get("decision_evidence"), dict)
            and isinstance(strategy_summary.get("decision_evidence", {}).get("posture"), dict)
            else False,
            "latest_recovery_hint": compressed_context.get("latest_recovery_hint"),
            "planner_governed_alternatives": recovery_governed_alternatives,
            "summary": (
                f"next_action={(recovery_summary.get('action') or step_loop_contract.get('current_disposition') or step_loop_contract.get('current_stage'))} "
                f"recovery_lane={recovery_summary.get('reason')} "
                f"resume_expectation={workflow_resume_expectation} "
                f"resume_posture={long_horizon_posture.get('resume_posture')} "
                f"approval_pause={(adapter_contract.get('approval_semantics', {}).get('approval_required') if isinstance(adapter_contract.get('approval_semantics'), dict) else None)} "
                f"clarify_pause={(bool(payload.get('clarify_summary', {}).get('needs_clarification')) if isinstance(payload.get('clarify_summary'), dict) else False)} "
                f"workflow_stage={workflow_active_stage} "
                f"workflow_selected={','.join(str(item) for item in selected_workflow_stages) or 'none'} "
                f"workflow_projection_ready={workflow_projection_ready} "
                f"pause_expected={(bool(strategy_summary.get('decision_evidence', {}).get('posture', {}).get('pause_expected')) if isinstance(strategy_summary.get('decision_evidence'), dict) and isinstance(strategy_summary.get('decision_evidence', {}).get('posture'), dict) else False)} "
                f"handoff_expected={(bool(strategy_summary.get('decision_evidence', {}).get('posture', {}).get('handoff_expected')) if isinstance(strategy_summary.get('decision_evidence'), dict) and isinstance(strategy_summary.get('decision_evidence', {}).get('posture'), dict) else False)} "
                f"fallback_expected={(bool(strategy_summary.get('decision_evidence', {}).get('posture', {}).get('fallback_expected')) if isinstance(strategy_summary.get('decision_evidence'), dict) and isinstance(strategy_summary.get('decision_evidence', {}).get('posture'), dict) else False)} "
                f"alternatives={','.join(str(item.get('action')) for item in recovery_governed_alternatives if item.get('action')) if recovery_governed_alternatives else 'none'} "
                f"compaction_stage={compaction_state.get('stage')} "
                f"compaction_pressure={continuity_pressure.get('compaction_pressure')}"
            ),
        },
        "autonomy_posture": {
            "pause_expected": bool(
                strategy_summary.get("decision_evidence", {}).get("posture", {}).get("pause_expected")
            )
            if isinstance(strategy_summary.get("decision_evidence"), dict)
            and isinstance(strategy_summary.get("decision_evidence", {}).get("posture"), dict)
            else False,
            "handoff_expected": bool(
                strategy_summary.get("decision_evidence", {}).get("posture", {}).get("handoff_expected")
            )
            if isinstance(strategy_summary.get("decision_evidence"), dict)
            and isinstance(strategy_summary.get("decision_evidence", {}).get("posture"), dict)
            else False,
            "fallback_expected": bool(
                strategy_summary.get("decision_evidence", {}).get("posture", {}).get("fallback_expected")
            )
            if isinstance(strategy_summary.get("decision_evidence"), dict)
            and isinstance(strategy_summary.get("decision_evidence", {}).get("posture"), dict)
            else False,
            "resume_posture": long_horizon_posture.get("resume_posture"),
        },
        "continuity_readiness": {
            "resume_ready": resume_supported,
            "runtime_cost_ready": runtime_duration_seconds is not None and bool(usage_cost_measurement_status),
            "compaction_ready": bool(compaction_state.get("stage")),
            "pressure_visible": bool(continuity_pressure.get("format")),
            "recovery_ready": bool(recent_observations)
            or bool(repair_summary)
            or bool(resume_context.get("planned_verification_command")),
            "workflow_resume_ready": bool(workflow_continuity.get("resume_alignment", {}).get("aligned")),
            "workflow_projection_visible": bool(tool_workflow_plan) or workflow_projection_ready,
            "workflow_recovery_aligned": bool(workflow_continuity.get("recovery_alignment", {}).get("aligned")),
        },
        "long_horizon_posture": long_horizon_posture,
        "program_posture": {
            "program_goal": (
                task_contract.get("goal")
                or context_task_contract.get("goal")
                or strategy_summary.get("goal")
                or payload.get("requirement")
                or compressed_context.get("objective")
                or active_milestone
            ),
            "active_milestone": active_milestone,
            "completed_milestones": [str(item) for item in completed_steps if item not in {None, ""}],
            "ready_next_units": ready_next_units,
            "blocked_units": blocked_units,
        },
        "daily_driver_readiness": {
            "tool_surface_ready": tool_surface_ready,
            "planner_ready": planner_ready,
            "session_ready": session_ready,
            "adapter_ready": adapter_ready,
            "shared_productization_ready": shared_productization_ready,
            "long_chain_task_ready": long_chain_native_first_ready,
            "daily_driver_main_path_ready": daily_driver_main_path_ready,
            "open_product_gap": (
                "platform_breadth_remaining"
                if daily_driver_main_path_ready
                else "long_chain_repo_closure_not_yet_proven"
                if shared_productization_ready
                else "productization_contract_incomplete"
            ),
        },
        "shared_evidence_surface": shared_evidence_surface,
    }
    comparative_completion_summary = build_comparative_completion_summary(
        benchmark_digest={
            "comparison_status": (
                "daily_driver_main_path_proven_breadth_gap_remaining"
                if daily_driver_main_path_ready
                else "shared_productization_ready_but_daily_driver_proof_gap_remaining"
                if shared_productization_ready
                else "foundational_gap_remaining"
            ),
            "comparison_grade_status": "runtime_evidence_pending",
            "comparison_grade_ready": False,
            "blocking_gap": "authoritative_external_comparison_not_yet_projected_into_runtime_contract",
            "external_harness_operator_action": "inspect_workspace_or_evidence_benchmark_before_goal_closure",
            "remaining_gap_classes": [
                "external_comparison_harness",
                "goal_level_closure_audit",
            ],
        },
        comparative_benchmark={
            "comparison_posture": {
                "status": (
                    "daily_driver_main_path_proven_breadth_gap_remaining"
                    if daily_driver_main_path_ready
                    else "shared_productization_ready_but_daily_driver_proof_gap_remaining"
                    if shared_productization_ready
                    else "foundational_gap_remaining"
                ),
                "remaining_gap_classes": [
                    "external_comparison_harness",
                    "goal_level_closure_audit",
                ],
            },
            "comparison_grade_assessment": {
                "status": "runtime_evidence_pending",
                "comparison_grade_ready": False,
                "blocking_gap": "authoritative_external_comparison_not_yet_projected_into_runtime_contract",
                "external_comparison_harness_surface": {
                    "operator_action": "inspect_workspace_or_evidence_benchmark_before_goal_closure",
                },
            },
        },
    )
    return {
        "format": "agent_orchestrator.session_continuity_contract.v1",
        "resume_supported": resume_supported,
        "resume_kind": resume_context.get("resume_kind"),
        "compaction_stage": compaction_state.get("stage"),
        "masked_observation_count": compaction_state.get("masked_count", 0),
        "summarization_triggered": compaction_state.get("summarization_triggered", False),
        "runtime_duration_seconds": runtime_duration_seconds,
        "usage_cost_measurement_status": usage_cost_measurement_status,
        "runtime_cost_provenance": runtime_cost_provenance,
        "shared_evidence_surface": shared_evidence_surface,
        "workflow_continuity": workflow_continuity,
        "continuity_snapshot": continuity_snapshot,
        "continuity_pressure": continuity_pressure,
        "session_productization_surface": session_productization_surface,
        "comparative_completion_summary": comparative_completion_summary,
        "long_horizon_posture": long_horizon_posture,
        "program_posture": {
            "program_goal": (
                task_contract.get("goal")
                or context_task_contract.get("goal")
                or strategy_summary.get("goal")
                or payload.get("requirement")
                or compressed_context.get("objective")
                or active_milestone
            ),
            "active_milestone": active_milestone,
            "completed_milestones": [str(item) for item in completed_steps if item not in {None, ""}],
            "ready_next_units": ready_next_units,
            "blocked_units": blocked_units,
        },
        "delegation_contract": {
            "selected_executor": (
                path_selection.get("default_path")
                or payload.get("runtime_name")
                or "native"
            ),
            "ownership_boundary": path_selection.get("operating_boundary"),
            "handoff_reason_code": path_selection.get("handoff_reason_code"),
            "fallback_reason_code": path_selection.get("fallback_reason_code"),
            "required_handoff_artifacts": required_handoff_artifacts,
            "resume_expectation": "resume_if_same_task"
            if resume_supported and resume_context.get("resume_kind") in {None, "fresh", "resume_if_same_task"}
            else "approval_pause"
            if resume_context.get("resume_kind") == "approval_resume"
            else resume_context.get("resume_kind"),
        },
        "program_continuity": {
            "resume_supported": resume_supported,
            "resume_kind": resume_context.get("resume_kind"),
            "compaction_stage": compaction_state.get("stage"),
            "continuity_artifact_status": "ready" if resume_supported else "limited",
            "latest_recovery_hint": compressed_context.get("latest_recovery_hint"),
            "repo_task_acceptance_ready": repo_task_acceptance_ready,
            "complex_repo_task_acceptance_ready": complex_repo_task_acceptance_ready,
            "long_chain_native_first_ready": long_chain_native_first_ready,
            "closure_strength": (
                "long_chain_native_first_ready"
                if long_chain_native_first_ready
                else "repo_task_acceptance_ready"
                if repo_task_acceptance_ready
                else "runtime_closure_only"
            ),
            "shared_evidence_surface": shared_evidence_surface,
        },
        "daily_driver_readiness": {
            "tool_surface_ready": tool_surface_ready,
            "planner_ready": planner_ready,
            "session_ready": session_ready,
            "adapter_ready": adapter_ready,
            "shared_productization_ready": shared_productization_ready,
            "long_chain_task_ready": long_chain_native_first_ready,
            "daily_driver_main_path_ready": daily_driver_main_path_ready,
            "open_product_gap": (
                "platform_breadth_remaining"
                if daily_driver_main_path_ready
                else "long_chain_repo_closure_not_yet_proven"
                if shared_productization_ready
                else "productization_contract_incomplete"
            ),
            "shared_evidence_surface": shared_evidence_surface,
        },
        "milestone_verification": {
            "verification_status": verification.get("status"),
            "remaining_checks": remaining_checks,
            "checkpoint_ready": bool(verification.get("status") == "passed" and not remaining_checks),
        },
        "operator_control": {
            "next_recommended_action": (
                recovery_summary.get("action")
                or step_loop_contract.get("current_disposition")
                or step_loop_contract.get("current_stage")
            ),
            "runbook_recovery_lane": recovery_summary.get("reason"),
            "approval_pause_state": adapter_contract.get("approval_semantics", {}).get("approval_required")
            if isinstance(adapter_contract.get("approval_semantics"), dict)
            else None,
            "clarify_pause_state": bool(payload.get("clarify_summary", {}).get("needs_clarification"))
            if isinstance(payload.get("clarify_summary"), dict)
            else False,
        },
        "latest_recovery_hint": compressed_context.get("latest_recovery_hint"),
    }


def _native_tool_productization_surface(payload: dict[str, object]) -> dict[str, object]:
    workflow_surface = _native_tool_workflow_surface(payload)
    native_tool_surface = (
        payload.get("native_tool_surface", {})
        if isinstance(payload.get("native_tool_surface"), dict)
        else {}
    )
    native_tool_trace = (
        payload.get("native_tool_trace", {})
        if isinstance(payload.get("native_tool_trace"), dict)
        else {}
    )
    readiness = (
        native_tool_surface.get("daily_driver_readiness", {})
        if isinstance(native_tool_surface.get("daily_driver_readiness"), dict)
        else {}
    )
    governance = (
        native_tool_surface.get("governance", {})
        if isinstance(native_tool_surface.get("governance"), dict)
        else {}
    )
    trace_entries = (
        native_tool_trace.get("trace", [])
        if isinstance(native_tool_trace.get("trace"), list)
        else []
    )
    recent_tools = [
        item.get("tool")
        for item in trace_entries[-5:]
        if isinstance(item, dict) and item.get("tool")
    ]
    tool_count = len(native_tool_surface.get("tools", [])) if isinstance(native_tool_surface.get("tools"), list) else 0
    trace_count = len(trace_entries)
    operator_visibility_ready = tool_count >= 1 and trace_count >= 1
    return {
        "format": "agent_orchestrator.native_tool_productization_surface.v1",
        "tool_count": tool_count,
        "trace_count": trace_count,
        "recent_tools": recent_tools,
        "tooling_posture": (
            "daily_driver_ready"
            if operator_visibility_ready
            and bool(readiness.get("repo_exploration_ready"))
            and bool(readiness.get("bounded_read_search_ready"))
            and bool(readiness.get("glob_ready"))
            and bool(readiness.get("structured_patch_ready"))
            and bool(readiness.get("diff_preview_ready"))
            and bool(readiness.get("verification_ready"))
            else "productization_gap_remaining"
        ),
        "operator_visibility_ready": operator_visibility_ready,
        "usage_visibility_ready": trace_count >= 1,
        "readiness": {
            "repo_exploration_ready": bool(readiness.get("repo_exploration_ready")),
            "bounded_read_search_ready": bool(readiness.get("bounded_read_search_ready")),
            "structural_outline_ready": bool(readiness.get("structural_outline_ready")),
            "glob_ready": bool(readiness.get("glob_ready")),
            "structured_patch_ready": bool(readiness.get("structured_patch_ready")),
            "patch_preview_ready": bool(readiness.get("patch_preview_ready")),
            "diff_preview_ready": bool(readiness.get("diff_preview_ready")),
            "verification_ready": bool(readiness.get("verification_ready")),
            "artifact_backed": bool(readiness.get("artifact_backed")),
        },
        "governance_boundary": {
            "boundary_policy": governance.get("boundary_policy"),
            "approval_aware": governance.get("approval_aware"),
            "artifact_backed": governance.get("artifact_backed"),
        },
        "workflow_surface": workflow_surface,
        "shared_evidence_surface": [
            "runtime_payload",
            "workspace_index",
            "ui_execution_summary",
            "cli_execution_summary",
            "evidence_report",
        ],
    }


def _native_tool_workflow_surface(payload: dict[str, object]) -> dict[str, object]:
    workflow_surface = (
        payload.get("native_tool_workflow_surface", {})
        if isinstance(payload.get("native_tool_workflow_surface"), dict)
        else {}
    )
    if workflow_surface:
        return workflow_surface
    native_tool_surface = (
        payload.get("native_tool_surface", {})
        if isinstance(payload.get("native_tool_surface"), dict)
        else {}
    )
    return (
        native_tool_surface.get("workflow_surface", {})
        if isinstance(native_tool_surface.get("workflow_surface"), dict)
        else {}
    )


def _adapter_productization_surface(*, adapter_contract: dict[str, object]) -> dict[str, object]:
    return derive_adapter_productization_surface(adapter_contract=adapter_contract)


def _adapter_capability_surface(payload: dict[str, object]) -> dict[str, object]:
    adapter_contract = payload.get("adapter_contract", {}) if isinstance(payload.get("adapter_contract"), dict) else {}
    capability_surface = (
        adapter_contract.get("capability_surface", {})
        if isinstance(adapter_contract.get("capability_surface"), dict)
        else {}
    )
    return dict(capability_surface) if capability_surface else {}


def _adapter_capability_summary(payload: dict[str, object]) -> dict[str, object]:
    adapter_contract = payload.get("adapter_contract", {}) if isinstance(payload.get("adapter_contract"), dict) else {}
    return derive_adapter_capability_summary(
        adapter_contract=adapter_contract,
        adapter_capability_surface=_adapter_capability_surface(payload),
    )


def _session_planner_decision_from_payload(payload: dict[str, object]) -> dict[str, object]:
    strategy_summary = payload.get("strategy_summary", {}) if isinstance(payload.get("strategy_summary"), dict) else {}
    decision_evidence = (
        strategy_summary.get("decision_evidence", {})
        if isinstance(strategy_summary.get("decision_evidence"), dict)
        else {}
    )
    operator_control = (
        payload.get("session_continuity_contract", {}).get("operator_control", {})
        if isinstance(payload.get("session_continuity_contract"), dict)
        and isinstance(payload.get("session_continuity_contract", {}).get("operator_control"), dict)
        else {}
    )
    return derive_session_planner_decision_from_payload(
        strategy_summary=strategy_summary,
        decision_evidence=decision_evidence,
        operator_control=operator_control,
    )


def _session_continuity_outline_from_payload(payload: dict[str, object]) -> dict[str, object]:
    continuity_contract = (
        payload.get("session_continuity_contract", {})
        if isinstance(payload.get("session_continuity_contract"), dict)
        else {}
    )
    return derive_session_continuity_outline_from_contract(
        continuity_contract=continuity_contract,
        planner_family=(
            payload.get("strategy_summary", {}).get("planner_family")
            if isinstance(payload.get("strategy_summary"), dict)
            else None
        ),
    )


def _runtime_duration_seconds_from_trace(payload: dict[str, object]) -> float | None:
    tool_trace = payload.get("native_tool_trace", {}) if isinstance(payload.get("native_tool_trace"), dict) else {}
    trace = tool_trace.get("trace", []) if isinstance(tool_trace.get("trace"), list) else []
    timestamps = [entry.get("timestamp") for entry in trace if isinstance(entry, dict)]
    valid: list[datetime] = []
    for value in timestamps:
        if not isinstance(value, str):
            continue
        try:
            valid.append(datetime.fromisoformat(value))
        except ValueError:
            continue
    if len(valid) < 2:
        return None
    return round((max(valid) - min(valid)).total_seconds(), 6)


def _usage_cost_measurement_status(payload: dict[str, object]) -> str:
    usage = payload.get("usage", {})
    if isinstance(usage, dict) and usage:
        return "measured"
    return "placeholder"


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
            reinjection_mode="full_inline_context",
            reinjection_targets=list(target_paths),
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
        reinjection_mode="digest_focus_subset",
        reinjection_targets=list(reduced_targets),
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
        "resume_contract": payload.get("resume_contract")
        if isinstance(payload.get("resume_contract"), dict)
        else _resume_contract(request, pending_approval, current_step, payload=payload),
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
            "native_tool_surface": payload.get("native_tool_surface"),
            "native_tool_workflow_surface": payload.get("native_tool_workflow_surface"),
            "native_tool_usage": payload.get("native_tool_usage"),
            "native_tool_evidence": payload.get("native_tool_evidence"),
            "native_tool_productization_surface": payload.get("native_tool_productization_surface"),
            "adapter_capability_surface": payload.get("adapter_capability_surface"),
            "adapter_capability": payload.get("adapter_capability"),
            "adapter_shared_contract": payload.get("adapter_shared_contract"),
            "adapter_execution_fact": payload.get("adapter_execution_fact"),
            "adapter_productization_surface": payload.get("adapter_productization_surface"),
            "shared_productization_surface": payload.get("shared_productization_surface"),
            "comparative_benchmark": payload.get("comparative_benchmark"),
            "comparative_benchmark_digest": payload.get("comparative_benchmark_digest"),
            "native_tool_trace": payload.get("native_tool_trace"),
            "repo_report": payload.get("repo_report"),
            "repository_understanding": payload.get("repository_understanding"),
        "strategy_summary": payload.get("strategy_summary"),
        "planner_shared_contract": payload.get("strategy_summary", {}).get("decision_evidence")
        if isinstance(payload.get("strategy_summary"), dict)
        and isinstance(payload.get("strategy_summary", {}).get("decision_evidence"), dict)
        else None,
        "planner_decision": payload.get("context_snapshot", {}).get("planner_decision")
        if isinstance(payload.get("context_snapshot"), dict)
        and isinstance(payload.get("context_snapshot", {}).get("planner_decision"), dict)
        else None,
        "continuity_outline": payload.get("context_snapshot", {}).get("continuity_outline")
        if isinstance(payload.get("context_snapshot"), dict)
        and isinstance(payload.get("context_snapshot", {}).get("continuity_outline"), dict)
        else None,
        "adapter_contract": payload.get("adapter_contract"),
        "path_selection": payload.get("path_selection"),
        "compressed_context": payload.get("compressed_context"),
        "compaction_state": payload.get("compaction_state"),
            "session_continuity_contract": payload.get("session_continuity_contract"),
            "resume_contract": payload.get("resume_contract"),
            "context_engineering_contract": payload.get("context_engineering_contract"),
            "resume_context": payload.get("resume_context"),
            "step_loop_contract": payload.get("step_loop_contract"),
            "native_task_proof": payload.get("native_task_proof"),
            "native_repo_task_acceptance": payload.get("native_repo_task_acceptance"),
            "native_complex_repo_task_acceptance": payload.get("native_complex_repo_task_acceptance"),
        },
    )


def _path_selection_payload(request: ExecutionRequest) -> dict[str, object]:
    default_path = getattr(request.route, "default_path", None) or (
        "native" if request.route.execution_mode == ExecutionMode.CODING_AGENT else "external"
    )
    operating_boundary = getattr(request.route, "operating_boundary", None) or (
        "native_preferred" if default_path == "native" else "fallback_governed"
    )
    selection_reason = getattr(request.route, "selection_reason", None) or (
        "Bounded repository work defaults to the native governed path."
        if default_path == "native"
        else "This task remains on the governed external path."
    )
    handoff_reason_code = getattr(request.route, "handoff_reason_code", None)
    fallback_reason_code = getattr(request.route, "fallback_reason_code", None) or (
        "native_runtime_unavailable" if default_path == "native" else "external_runtime_unavailable"
    )
    planner_intent = getattr(request.route, "planner_intent", None)
    if not isinstance(planner_intent, dict) or not planner_intent:
        planner_intent = {
            "version": "agent_orchestrator.route_planner_intent.v1",
            "explore": False,
            "clarify": False,
            "edit": default_path == "native",
            "verify": default_path == "native",
            "pause": False,
            "handoff": default_path == "external" and operating_boundary == "external_preferred",
            "fallback": default_path != "native" and operating_boundary != "external_preferred",
            "priority": ["edit", "verify"] if default_path == "native" else ["handoff"],
            "native_first": default_path == "native",
            "requires_confirmation": bool(getattr(request.route, "requires_human_confirmation", False)),
            "risk_level": getattr(request.route, "risk_level", None),
        }
    return {
        "default_path": default_path,
        "operating_boundary": operating_boundary,
        "selection_reason": selection_reason,
        "handoff_reason_code": handoff_reason_code,
        "fallback_reason_code": fallback_reason_code,
        "native_coverage_class": getattr(request.route, "native_coverage_class", None),
        "learning_consumed": bool(getattr(request.route, "learning_consumed", False)),
        "learning_source_count": int(getattr(request.route, "learning_source_count", 0) or 0),
        "planner_intent": dict(planner_intent),
    }


def _shared_adapter_capability_surface(
    *,
    adapter_family: str,
    agent_kind: str,
    path_selection: dict[str, object],
    approval_required: bool,
    approval_pause_supported: bool,
    evidence_outputs: list[str],
    recovery_surfaces: list[str],
    runtime_metadata: dict[str, object],
) -> dict[str, object]:
    shared_evidence_surface = [
        "runtime_payload",
        "workspace_index",
        "ui_execution_summary",
        "cli_execution_summary",
        "evidence_report",
        "session_continuity",
        "session_productization_surface",
        "planner_closure_posture",
        "native_tool_workflow_surface",
        "native_tool_productization_surface",
        "adapter_shared_contract",
    ]
    operator_recovery_surface = {
        "format": "agent_orchestrator.adapter_operator_recovery_surface.v1",
        "governed_lanes": [
            "continue_execution",
            "approval_pause" if approval_pause_supported else "continue_execution",
            "fallback_external",
            "handoff_external",
        ],
        "default_recovery_lane": "approval_pause" if approval_pause_supported else "continue_execution",
        "continuity_expectation": "resume_contract_required" if "resume_contract" in recovery_surfaces else "fresh_or_external_reentry",
        "evidence_backed_lanes": list(evidence_outputs),
        "operator_visible": True,
    }
    shared_contract = {
        "format": "agent_orchestrator.adapter_shared_contract.v1",
        "comparison_mode": "same_contract_two_executors",
        "path_selection": dict(path_selection),
        "approval_semantics": {
            "approval_required": approval_required,
            "approval_pause_supported": approval_pause_supported,
        },
        "evidence_outputs": list(evidence_outputs),
        "recovery_surfaces": list(recovery_surfaces),
        "continuity_support": {
            "resume_contract": "resume_contract" in recovery_surfaces,
            "approval_pause_state": "approval_pause_state" in recovery_surfaces,
        },
        "shared_evidence_surface": list(shared_evidence_surface),
        "operator_visibility_contract": {
            "format": "agent_orchestrator.adapter_operator_visibility_contract.v1",
            "session_surface_required": True,
            "planner_surface_required": True,
            "tool_surface_required": True,
            "comparative_surface_required": True,
            "required_surfaces": [
                "session_continuity",
                "session_productization_surface",
                "planner_closure_posture",
                "native_tool_workflow_surface",
                "native_tool_productization_surface",
                "workspace_index",
                "ui_execution_summary",
                "cli_execution_summary",
                "evidence_report",
            ],
        },
        "tooling_contract": {
            "format": "agent_orchestrator.adapter_tooling_contract.v1",
            "explore_surface_required": True,
            "edit_surface_required": True,
            "verify_surface_required": True,
            "workflow_projection_required": True,
        },
        "operator_recovery_surface": operator_recovery_surface,
        "recovery_contract": {
            "continue_allowed": True,
            "scope_realign_required": False,
            "fallback_allowed": True,
            "handoff_allowed": True,
            "remaining_budget_preserved": True,
            "resume_continuity_required": "resume_contract" in recovery_surfaces,
        },
    }
    return {
        "format": "agent_orchestrator.adapter_capability_surface.v1",
        "adapter_family": adapter_family,
        "agent_kind": agent_kind,
        "runtime_metadata": dict(runtime_metadata),
        "path_selection": dict(path_selection),
        "governance": {
            "approval_required": approval_required,
            "approval_pause_supported": approval_pause_supported,
            "fallback_governed": True,
            "hot_plug_supported": True,
        },
        "evidence_outputs": list(evidence_outputs),
        "recovery_surfaces": list(recovery_surfaces),
        "shared_evidence_surface": list(shared_evidence_surface),
        "operator_recovery_surface": operator_recovery_surface,
        "shared_contract": shared_contract,
        "comparability": {
            "shared_with_external": True,
            "shared_with_native": True,
            "comparison_mode": "same_contract_two_executors",
        },
    }


def _adapter_shared_contract_summary_from_payload(payload: dict[str, object]) -> dict[str, object]:
    adapter_contract = payload.get("adapter_contract", {}) if isinstance(payload.get("adapter_contract"), dict) else {}
    capability_surface = (
        adapter_contract.get("capability_surface", {})
        if isinstance(adapter_contract.get("capability_surface"), dict)
        else {}
    )
    shared_contract = (
        capability_surface.get("shared_contract", {})
        if isinstance(capability_surface.get("shared_contract"), dict)
        else {}
    )
    path_selection = payload.get("path_selection", {}) if isinstance(payload.get("path_selection"), dict) else {}
    return {
        "adapter_family": adapter_contract.get("adapter_family"),
        "agent_kind": adapter_contract.get("agent_kind"),
        "format": "agent_orchestrator.adapter_shared_contract.v1",
        "comparison_mode": (
            capability_surface.get("comparability", {}).get("comparison_mode")
            if isinstance(capability_surface.get("comparability"), dict)
            else None
        ),
        "default_path": path_selection.get("default_path"),
        "operating_boundary": path_selection.get("operating_boundary"),
        "selection_reason": path_selection.get("selection_reason"),
        "handoff_reason_code": path_selection.get("handoff_reason_code"),
        "fallback_reason_code": path_selection.get("fallback_reason_code"),
        "native_coverage_class": path_selection.get("native_coverage_class"),
        "learning_consumed": path_selection.get("learning_consumed"),
        "learning_source_count": path_selection.get("learning_source_count"),
        "approval_required": adapter_contract.get("approval_semantics", {}).get("approval_required")
        if isinstance(adapter_contract.get("approval_semantics"), dict)
        else None,
        "approval_pause_supported": adapter_contract.get("approval_semantics", {}).get("approval_pause_supported")
        if isinstance(adapter_contract.get("approval_semantics"), dict)
        else None,
        "hot_plug_supported": (
            capability_surface.get("governance", {}).get("hot_plug_supported")
            if isinstance(capability_surface.get("governance"), dict)
            else None
        ),
        "fallback_governed": (
            capability_surface.get("governance", {}).get("fallback_governed")
            if isinstance(capability_surface.get("governance"), dict)
            else None
        ),
        "evidence_outputs": list(adapter_contract.get("evidence_outputs", []))
        if isinstance(adapter_contract.get("evidence_outputs"), list)
        else [],
        "recovery_surfaces": list(adapter_contract.get("recovery_surfaces", []))
        if isinstance(adapter_contract.get("recovery_surfaces"), list)
        else [],
        "recovery_contract": dict(shared_contract.get("recovery_contract", {}))
        if isinstance(shared_contract.get("recovery_contract"), dict)
        else {},
        "continuity_support": dict(shared_contract.get("continuity_support", {}))
        if isinstance(shared_contract.get("continuity_support"), dict)
        else {},
        "shared_evidence_surface": list(shared_contract.get("shared_evidence_surface", []))
        if isinstance(shared_contract.get("shared_evidence_surface"), list)
        else [],
        "operator_visibility_contract": dict(shared_contract.get("operator_visibility_contract", {}))
        if isinstance(shared_contract.get("operator_visibility_contract"), dict)
        else {},
        "tooling_contract": dict(shared_contract.get("tooling_contract", {}))
        if isinstance(shared_contract.get("tooling_contract"), dict)
        else {},
        "operator_recovery_surface": dict(shared_contract.get("operator_recovery_surface", {}))
        if isinstance(shared_contract.get("operator_recovery_surface"), dict)
        else {},
        "shared_contract_format": shared_contract.get("format"),
        "shared_contract_resume_supported": shared_contract.get("continuity_support", {}).get("resume_contract")
        if isinstance(shared_contract.get("continuity_support"), dict)
        else None,
    }


def _repository_understanding_from_repo_report(repo_report: dict[str, object]) -> dict[str, object]:
    artifact = repo_report.get("artifact", {}) if isinstance(repo_report.get("artifact"), dict) else {}
    understanding = (
        artifact.get("repository_understanding", {})
        if isinstance(artifact.get("repository_understanding"), dict)
        else {}
    )
    if understanding:
        return dict(understanding)
    return {
        "format": "agent_orchestrator.repository_understanding.v1",
        "candidate_reason": None,
        "explicit_paths": list(repo_report.get("explicit_paths", []))
        if isinstance(repo_report.get("explicit_paths"), list)
        else [],
        "explicit_path_hits": list(repo_report.get("existing_paths", []))
        if isinstance(repo_report.get("existing_paths"), list)
        else [],
        "candidate_count": len(repo_report.get("candidate_paths", []))
        if isinstance(repo_report.get("candidate_paths"), list)
        else 0,
        "candidate_evidence": [],
        "context_selection_reason": "Repository understanding evidence was unavailable in the exploration artifact.",
        "main_path_effects": {
            "affects_edit_targets": bool(repo_report.get("candidate_paths")),
            "affects_verification_targets": bool(repo_report.get("candidate_paths")),
            "records_selection_rationale": False,
            "can_trigger_clarify_or_stop_when_empty": True,
        },
        "operator_visibility": {
            "shared_evidence_surface": ["runtime_payload"],
            "status": "fallback_summary_only",
        },
    }


def _native_tool_usage_summary(payload: dict[str, object]) -> dict[str, object]:
    native_tool_trace = (
        payload.get("native_tool_trace", {})
        if isinstance(payload.get("native_tool_trace"), dict)
        else {}
    )
    trace_entries = (
        native_tool_trace.get("trace", [])
        if isinstance(native_tool_trace.get("trace"), list)
        else []
    )
    native_tool_surface = (
        payload.get("native_tool_surface", {})
        if isinstance(payload.get("native_tool_surface"), dict)
        else {}
    )
    return {
        "tool_count": len(native_tool_surface.get("tools", []))
        if isinstance(native_tool_surface.get("tools"), list)
        else 0,
        "trace_count": len(trace_entries),
        "recent_tools": [
            item.get("tool")
            for item in trace_entries[-5:]
            if isinstance(item, dict) and item.get("tool")
        ],
    }


def _native_tool_evidence_summary(payload: dict[str, object]) -> dict[str, object]:
    native_tool_trace = (
        payload.get("native_tool_trace", {})
        if isinstance(payload.get("native_tool_trace"), dict)
        else {}
    )
    trace_entries = (
        native_tool_trace.get("trace", [])
        if isinstance(native_tool_trace.get("trace"), list)
        else []
    )
    evidence_tools = {"patch_preview", "structured_patch", "diff_preview", "verify"}
    evidence_records = [
        {
            "tool": item.get("tool"),
            "summary": item.get("summary"),
            "timestamp": item.get("timestamp"),
            "arguments": dict(item.get("arguments", {})) if isinstance(item.get("arguments"), dict) else {},
            "result": dict(item.get("result", {})) if isinstance(item.get("result"), dict) else {},
        }
        for item in trace_entries
        if isinstance(item, dict) and item.get("tool") in evidence_tools
    ]
    tool_counts = {
        tool_name: len([item for item in evidence_records if item.get("tool") == tool_name])
        for tool_name in sorted(evidence_tools)
    }
    verification_records = [item for item in evidence_records if item.get("tool") == "verify"]
    patch_records = [
        item
        for item in evidence_records
        if item.get("tool") in {"patch_preview", "structured_patch", "diff_preview"}
    ]
    latest_verification = verification_records[-1] if verification_records else {}
    latest_verification_result = (
        latest_verification.get("result", {})
        if isinstance(latest_verification.get("result"), dict)
        else {}
    )
    return {
        "format": "agent_orchestrator.native_tool_evidence.v1",
        "evidence_record_count": len(evidence_records),
        "tool_counts": tool_counts,
        "patch_evidence_ready": bool(patch_records),
        "verify_evidence_ready": bool(verification_records),
        "latest_verification_status": latest_verification_result.get("status"),
        "latest_verification_exit_code": latest_verification_result.get("exit_code"),
        "latest_verification_artifact": latest_verification_result.get("artifact"),
        "records": evidence_records,
        "shared_evidence_surface": [
            "runtime_payload",
            "workspace_index",
            "ui_execution_summary",
            "cli_execution_summary",
            "evidence_report",
        ],
        "operator_visibility": {
            "patch_diff_verify_visible": bool(evidence_records),
            "status": "tool_evidence_recorded" if evidence_records else "no_patch_diff_verify_trace",
        },
    }


def _runtime_comparative_execution_artifact_summary(payload: dict[str, object]) -> dict[str, object]:
    continuity_contract = (
        payload.get("session_continuity_contract", {})
        if isinstance(payload.get("session_continuity_contract"), dict)
        else {}
    )
    return {
        "native_task_proof": payload.get("native_task_proof", {}),
        "native_repo_task_acceptance": payload.get("native_repo_task_acceptance", {}),
        "native_complex_repo_task_acceptance": payload.get("native_complex_repo_task_acceptance", {}),
        "adapter_shared_contract": payload.get("adapter_shared_contract", {}),
        "adapter_execution_fact": payload.get("adapter_execution_fact", {}),
        "session_continuity": {
            "continuity_snapshot": continuity_contract.get("continuity_snapshot", {}),
            "session_productization_surface": continuity_contract.get("session_productization_surface", {}),
            "program_continuity": continuity_contract.get("program_continuity", {}),
            "daily_driver_readiness": continuity_contract.get("daily_driver_readiness", {}),
        },
        "native_tool_workflow_surface": payload.get("native_tool_workflow_surface", {}),
        "native_tool_productization_surface": payload.get("native_tool_productization_surface", {}),
        "adapter_productization_surface": payload.get("adapter_productization_surface", {}),
        "planner_shared_contract": payload.get("strategy_summary", {}).get("decision_evidence", {})
        if isinstance(payload.get("strategy_summary"), dict)
        and isinstance(payload.get("strategy_summary", {}).get("decision_evidence"), dict)
        else {},
        "native_tool_usage": payload.get("native_tool_usage", {}),
        "planner_decision": payload.get("planner_decision", {}),
        "continuity_outline": payload.get("continuity_outline", {}),
        "runtime_cost": payload.get("runtime_cost", {}),
    }


def _record_native_learning_assets(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    payload: dict[str, object],
) -> None:
    session_id = request.session_id or _runtime_run_id(request)
    turn_id = request.turn_id or _runtime_run_id(request)
    workspace_root = runtime.repo_explorer.workspace_root if isinstance(runtime.repo_explorer.workspace_root, Path) else Path(runtime.repo_explorer.workspace_root)
    control_root = workspace_root / ".agent_orchestrator"
    session_runtime = SessionRuntime(control_root / "agent_sessions")
    knowledge_store = KnowledgeStore(control_root / "knowledge")
    path_selection = payload.get("path_selection", {}) if isinstance(payload.get("path_selection"), dict) else {}
    native_task_proof = payload.get("native_task_proof", {}) if isinstance(payload.get("native_task_proof"), dict) else {}
    native_repo_task_acceptance = (
        payload.get("native_repo_task_acceptance", {})
        if isinstance(payload.get("native_repo_task_acceptance"), dict)
        else {}
    )
    native_complex_repo_task_acceptance = (
        payload.get("native_complex_repo_task_acceptance", {})
        if isinstance(payload.get("native_complex_repo_task_acceptance"), dict)
        else {}
    )
    trajectory = session_runtime.record_trajectory(
        session_id=session_id,
        turn_id=turn_id,
        task_class=str(native_task_proof.get("task_class") or "bounded_internal_repo_task"),
        path_selection=path_selection,
        stage=str(native_task_proof.get("proof_scenario") or "completed"),
        outcome=str(payload.get("status") or "unknown"),
        summary=str(native_task_proof.get("proof_scenario") or payload.get("status") or "unknown"),
        evidence_refs=[
            "payload.native_task_proof",
            "payload.native_repo_task_acceptance",
            "payload.native_complex_repo_task_acceptance",
            "payload.event_summary",
        ],
        asset_refs=[
            "MemoryStore.memory.jsonl",
            "KnowledgeStore/lessons.jsonl",
            "SessionRuntime/trajectories",
        ],
        metadata={
            "selection_reason": path_selection.get("selection_reason"),
            "handoff_reason_code": path_selection.get("handoff_reason_code"),
            "fallback_reason_code": path_selection.get("fallback_reason_code"),
            "real_repo_task_acceptance_ready": native_repo_task_acceptance.get("real_repo_task_acceptance_ready"),
            "complex_repo_task_ready": native_complex_repo_task_acceptance.get("complex_repo_task_ready"),
        },
    )
    memory_store = runtime.memory_store
    memory_store.append(
        namespace="native_trajectory",
        session_id=session_id,
        record_type="trajectory",
        summary=trajectory.summary,
        role="coding_agent",
        provider="native",
        payload=trajectory.to_dict(),
        provenance={"source": "coding_agent_runtime", "turn_id": turn_id},
        freshness="fresh",
        confidence=0.9,
    )
    memory_store.append(
        namespace="native_learning",
        session_id=session_id,
        record_type="memory",
        summary=str(path_selection.get("selection_reason") or "native path selected"),
        role="curator",
        provider="native",
        payload={
            "path_selection": path_selection,
            "task_class": native_task_proof.get("task_class"),
            "proof_scenario": native_task_proof.get("proof_scenario"),
            "real_repo_task_acceptance_ready": native_repo_task_acceptance.get("real_repo_task_acceptance_ready"),
            "complex_repo_task_ready": native_complex_repo_task_acceptance.get("complex_repo_task_ready"),
        },
        provenance={"source": "trajectory_curator", "turn_id": turn_id},
        freshness="fresh",
        confidence=0.8,
    )
    knowledge_store.append(
        session_id=session_id,
        artifact_type="lessons",
        summary=str(path_selection.get("selection_reason") or "native path selected"),
        role="curator",
        payload={
            "task_class": native_task_proof.get("task_class"),
            "proof_scenario": native_task_proof.get("proof_scenario"),
            "path_selection": path_selection,
        },
    )
    knowledge_store.append(
        session_id=session_id,
        artifact_type="skills",
        summary="Native repo task acceptance asset",
        role="curator",
        payload={
            "trajectory_id": trajectory.trajectory_id,
            "nudge": {
                "type": "curator_ready",
                "write_rules": ["facts->Memory", "procedures->Skill", "decision->policy"],
            },
            "task_class": native_task_proof.get("task_class"),
        },
    )


def _native_task_proof(
    runtime: CodingAgentExecutionRuntime,
    *,
    request: ExecutionRequest,
    payload: dict[str, object],
) -> dict[str, object]:
    artifact_summary = payload.get("artifact_summary", {}) if isinstance(payload.get("artifact_summary"), dict) else {}
    event_summary = payload.get("event_summary", {}) if isinstance(payload.get("event_summary"), dict) else {}
    resume_context = payload.get("resume_context", {}) if isinstance(payload.get("resume_context"), dict) else {}
    step_loop_contract = payload.get("step_loop_contract", {}) if isinstance(payload.get("step_loop_contract"), dict) else {}
    kernel_contract = payload.get("kernel_contract", {}) if isinstance(payload.get("kernel_contract"), dict) else {}
    context_selection = payload.get("context_selection", {}) if isinstance(payload.get("context_selection"), dict) else {}
    isolation_state = payload.get("isolation_state", {}) if isinstance(payload.get("isolation_state"), dict) else {}
    retrieved_memory = payload.get("retrieved_memory", []) if isinstance(payload.get("retrieved_memory"), list) else []
    repair_summary = payload.get("repair_summary", {}) if isinstance(payload.get("repair_summary"), dict) else {}
    recovery_summary = payload.get("recovery_summary", {}) if isinstance(payload.get("recovery_summary"), dict) else {}
    verification = payload.get("verification", {}) if isinstance(payload.get("verification"), dict) else {}
    proof_scenario = _native_task_proof_scenario(
        pending_approval=payload.get("pending_approval"),
        verification=verification,
        repair_summary=repair_summary,
        accepted=payload.get("accepted"),
        status=payload.get("status"),
    )
    return {
        "format": "agent_orchestrator.native_task_proof.v1",
        "run_id": _runtime_run_id(request),
        "runtime_name": runtime.name,
        "native_runtime_only": True,
        "external_coding_agent_required": False,
        "task_class": "bounded_internal_repo_task",
        "proof_scenario": proof_scenario,
        "task_requirement": request.requirement,
        "task_kind": payload.get("task_kind"),
        "closure_status": payload.get("status"),
        "accepted": payload.get("accepted"),
        "kernel_governed": kernel_contract.get("kernel_role") == "governed_execution_kernel",
        "state_authority": kernel_contract.get("state_authority"),
        "step_loop_model": step_loop_contract.get("loop_model"),
        "step_loop_status": step_loop_contract.get("status"),
        "step_loop_resume_supported": step_loop_contract.get("resume_supported"),
        "context_select_explicit": bool(context_selection),
        "structured_observation_count": len(resume_context.get("recent_observations", [])) if isinstance(resume_context.get("recent_observations"), list) else 0,
        "compact_applied": bool(payload.get("compressed_context")),
        "isolate_applied": bool(isolation_state.get("applied")),
        "verification_status": verification.get("status"),
        "verification_failure_kind": verification.get("failure_kind"),
        "repair_attempt_count": repair_summary.get("attempt_count", 0),
        "recovery_action": recovery_summary.get("action"),
        "resume_ready": bool(resume_context.get("resume_supported", True)),
        "pending_approval": payload.get("pending_approval"),
        "artifact_count": artifact_summary.get("artifact_count", 0),
        "event_count": event_summary.get("event_count", 0),
        "memory_result_count": len(retrieved_memory),
        "ui_projection_ready": True,
        "proof_bundle": {
            "artifact_summary_ref": "payload.artifact_summary",
            "event_summary_ref": "payload.event_summary",
            "resume_context_ref": "payload.resume_context",
            "compressed_context_ref": "payload.compressed_context",
            "retrieved_memory_ref": "payload.retrieved_memory",
            "step_loop_contract_ref": "payload.step_loop_contract",
        },
    }


def _native_repo_task_acceptance(
    *,
    request: ExecutionRequest,
    payload: dict[str, object],
) -> dict[str, object]:
    applied_changes = payload.get("applied_changes", []) if isinstance(payload.get("applied_changes"), list) else []
    verification = payload.get("verification", {}) if isinstance(payload.get("verification"), dict) else {}
    edit_intent = payload.get("edit_intent", {}) if isinstance(payload.get("edit_intent"), dict) else {}
    target_paths = edit_intent.get("target_paths", []) if isinstance(edit_intent.get("target_paths"), list) else []
    changed_paths = _accepted_change_paths(applied_changes, payload)
    allowed_prefixes = ("src/agent_orchestrator/", "ui_frontend/")
    changed_code_paths = [path for path in changed_paths if path.startswith(allowed_prefixes)]
    changed_surface_paths = [
        path for path in changed_paths if path.startswith("docs/") or "compliance" in path or "process" in path
    ]
    verification_command = verification.get("command", []) if isinstance(verification.get("command"), list) else []
    verification_artifact = verification.get("artifact", {}) if isinstance(verification.get("artifact"), dict) else {}
    task_shape_checks = {
        "repository_exploration_present": {
            "passed": bool(target_paths),
            "evidence": {"target_paths": list(target_paths)},
        },
        "code_edit_under_repo_surface": {
            "passed": bool(changed_code_paths),
            "evidence": {"changed_code_paths": changed_code_paths},
        },
        "verification_command_present": {
            "passed": bool(verification_command),
            "evidence": {"verification_command": verification_command},
        },
        "operator_visible_artifacts_present": {
            "passed": bool(verification_artifact),
            "evidence": {"verification_artifact": verification_artifact},
        },
        "repo_facing_surface_updated": {
            "passed": bool(changed_surface_paths),
            "evidence": {"changed_surface_paths": changed_surface_paths},
        },
    }
    passed_checks = sum(1 for item in task_shape_checks.values() if item.get("passed") is True)
    return {
        "format": "agent_orchestrator.native_repo_task_acceptance.v1",
        "run_id": _runtime_run_id(request),
        "task_requirement": request.requirement,
        "task_shape_checks": task_shape_checks,
        "passed_check_count": passed_checks,
        "total_check_count": len(task_shape_checks),
        "real_repo_task_acceptance_ready": passed_checks == len(task_shape_checks),
        "notes": "This is the stronger project-level acceptance target for one real repository task chain.",
    }


def _native_complex_repo_task_acceptance(
    *,
    request: ExecutionRequest,
    payload: dict[str, object],
) -> dict[str, object]:
    applied_changes = payload.get("applied_changes", []) if isinstance(payload.get("applied_changes"), list) else []
    verification = payload.get("verification", {}) if isinstance(payload.get("verification"), dict) else {}
    edit_intent = payload.get("edit_intent", {}) if isinstance(payload.get("edit_intent"), dict) else {}
    native_tool_trace = payload.get("native_tool_trace", {}) if isinstance(payload.get("native_tool_trace"), dict) else {}
    target_paths = edit_intent.get("target_paths", []) if isinstance(edit_intent.get("target_paths"), list) else []
    operations = edit_intent.get("operations", []) if isinstance(edit_intent.get("operations"), list) else []
    changed_paths = _accepted_change_paths(applied_changes, payload)
    allowed_prefixes = ("src/agent_orchestrator/", "ui_frontend/")
    changed_code_paths = [path for path in changed_paths if path.startswith(allowed_prefixes)]
    changed_surface_paths = [
        path for path in changed_paths if path.startswith("docs/") or "compliance" in path or "process" in path
    ]
    verification_command = verification.get("command", []) if isinstance(verification.get("command"), list) else []
    verification_artifact = verification.get("artifact", {}) if isinstance(verification.get("artifact"), dict) else {}
    strategy_summary = payload.get("strategy_summary", {}) if isinstance(payload.get("strategy_summary"), dict) else {}
    planner_shared_contract = (
        strategy_summary.get("decision_evidence", {})
        if isinstance(strategy_summary.get("decision_evidence"), dict)
        else {}
    )
    tool_workflow_plan = (
        planner_shared_contract.get("tool_workflow_plan", {})
        if isinstance(planner_shared_contract.get("tool_workflow_plan"), dict)
        else {}
    )
    workflow_stages = (
        tool_workflow_plan.get("workflow_stages", {})
        if isinstance(tool_workflow_plan.get("workflow_stages"), dict)
        else {}
    )
    planner_context_trace = (
        payload.get("planner_context_trace", [])
        if isinstance(payload.get("planner_context_trace"), list)
        else []
    )
    action_selection_trace = (
        payload.get("action_selection_trace", [])
        if isinstance(payload.get("action_selection_trace"), list)
        else []
    )
    trace_entries = native_tool_trace.get("trace", []) if isinstance(native_tool_trace.get("trace"), list) else []
    explored_tools = [
        item.get("tool")
        for item in trace_entries
        if isinstance(item, dict) and item.get("tool") in {"repo_map", "find_files", "search", "outline", "read", "glob"}
    ]
    edit_workflow_tools = [
        item.get("tool")
        for item in trace_entries
        if isinstance(item, dict) and item.get("tool") in {"patch_preview", "structured_patch", "diff_preview"}
    ]
    verification_tools = [
        item.get("tool")
        for item in trace_entries
        if isinstance(item, dict) and item.get("tool") in {"verify", "tool_trace"}
    ]
    selected_workflow_stages = [
        stage_name
        for stage_name in ("explore", "edit", "verify")
        if isinstance(workflow_stages.get(stage_name), dict) and workflow_stages.get(stage_name, {}).get("selected") is True
    ]
    trace_stage_alignment = {
        stage_name: any(
            isinstance(item, dict)
            and item.get("stage_cursor") == stage_name
            and isinstance(item.get("current_stage_workflow"), dict)
            and item.get("current_stage_workflow", {}).get("selected") is True
            for item in planner_context_trace
        )
        for stage_name in selected_workflow_stages
    }
    action_required_tool_alignment = {
        stage_name: any(
            isinstance(item, dict)
            and item.get("stage") == stage_name
            and isinstance(item.get("decision"), dict)
            and all(
                tool_name in item.get("decision", {}).get("current_stage_required_tools", [])
                for tool_name in workflow_stages.get(stage_name, {}).get("required_tools", [])
                if isinstance(tool_name, str)
            )
            for item in action_selection_trace
        )
        for stage_name in ("edit", "verify")
        if isinstance(workflow_stages.get(stage_name), dict) and workflow_stages.get(stage_name, {}).get("selected") is True
    }
    complex_checks = {
        "multi_target_exploration_present": {
            "passed": len(target_paths) >= 3,
            "evidence": {"target_paths": list(target_paths), "target_path_count": len(target_paths)},
        },
        "multi_file_mutation_present": {
            "passed": len(changed_paths) >= 3 and len(operations) >= 3,
            "evidence": {
                "changed_paths": changed_paths,
                "changed_path_count": len(changed_paths),
                "operation_count": len(operations),
            },
        },
        "code_and_repo_surface_updated": {
            "passed": bool(changed_code_paths) and bool(changed_surface_paths),
            "evidence": {
                "changed_code_paths": changed_code_paths,
                "changed_surface_paths": changed_surface_paths,
            },
        },
        "verification_on_code_targets_present": {
            "passed": bool(verification_command) and bool(verification_artifact) and len(changed_code_paths) >= 2,
            "evidence": {
                "verification_command": verification_command,
                "verification_artifact": verification_artifact,
                "changed_code_path_count": len(changed_code_paths),
            },
        },
        "native_exploration_trace_visible": {
            "passed": len(explored_tools) >= 4
            and all(tool in explored_tools for tool in {"find_files", "search", "outline", "read"}),
            "evidence": {
                "explored_tools": explored_tools,
                "trace_count": len(trace_entries),
            },
        },
        "governed_edit_workflow_trace_visible": {
            "passed": all(tool in edit_workflow_tools for tool in {"patch_preview", "structured_patch", "diff_preview"}),
            "evidence": {
                "edit_workflow_tools": edit_workflow_tools,
                "trace_count": len(trace_entries),
            },
        },
        "verification_workflow_trace_visible": {
            "passed": "verify" in verification_tools,
            "evidence": {
                "verification_tools": verification_tools,
                "trace_count": len(trace_entries),
            },
        },
        "planner_workflow_contract_visible": {
            "passed": tool_workflow_plan.get("format") == "agent_orchestrator.native_tool_workflow_plan.v1"
            and tool_workflow_plan.get("workflow_projection_required") is True
            and selected_workflow_stages == ["explore", "edit", "verify"],
            "evidence": {
                "tool_workflow_plan": tool_workflow_plan,
                "selected_workflow_stages": selected_workflow_stages,
            },
        },
        "planner_workflow_runtime_alignment_visible": {
            "passed": bool(trace_stage_alignment)
            and all(trace_stage_alignment.values())
            and bool(action_required_tool_alignment)
            and all(action_required_tool_alignment.values()),
            "evidence": {
                "trace_stage_alignment": trace_stage_alignment,
                "action_required_tool_alignment": action_required_tool_alignment,
                "planner_context_trace_count": len(planner_context_trace),
                "action_selection_trace_count": len(action_selection_trace),
            },
        },
    }
    passed_checks = sum(1 for item in complex_checks.values() if item.get("passed") is True)
    return {
        "format": "agent_orchestrator.native_complex_repo_task_acceptance.v1",
        "run_id": _runtime_run_id(request),
        "task_requirement": request.requirement,
        "complex_task_checks": complex_checks,
        "passed_check_count": passed_checks,
        "total_check_count": len(complex_checks),
        "complex_repo_task_ready": passed_checks == len(complex_checks),
        "notes": "This stricter signal targets longer, multi-file native repository tasks that look closer to a daily-driver coding path.",
    }


def _native_task_proof_scenario(
    *,
    pending_approval: object,
    verification: dict[str, object],
    repair_summary: dict[str, object],
    accepted: object,
    status: object,
) -> str:
    if isinstance(pending_approval, dict):
        return "approval_pause_resume_complete" if accepted is True else "approval_pause_blocked"
    repair_outcome = str(repair_summary.get("outcome") or "")
    verification_status = str(verification.get("status") or "")
    attempts = repair_summary.get("attempts", [])
    had_failed_attempt = (
        isinstance(attempts, list)
        and any(
            isinstance(item, dict)
            and isinstance(item.get("verification"), dict)
            and item.get("verification", {}).get("status") == "failed"
            for item in attempts
        )
    )
    if verification_status == "passed" and repair_summary.get("attempt_count", 0):
        return "verify_failure_repair_resume_success" if had_failed_attempt else "approval_pause_resume_complete"
    if status == "blocked" and repair_outcome == "failed":
        return "verify_failure_exhausted_recovery_block"
    if accepted is True:
        return "approval_pause_resume_complete"
    return "bounded_internal_repo_task"


def _accepted_change_paths(applied_changes: list[object], payload: dict[str, object]) -> list[str]:
    changed_paths: list[str] = []
    for item in applied_changes:
        if not isinstance(item, dict) or item.get("status") != "applied":
            continue
        path = item.get("path")
        if isinstance(path, str) and path:
            changed_paths.append(path)
            continue
        operation = item.get("operation")
        if isinstance(operation, dict):
            op_path = operation.get("path")
            if isinstance(op_path, str) and op_path:
                changed_paths.append(op_path)
    if changed_paths:
        return _dedupe_preserve_order_strings(changed_paths)
    edit_intent = payload.get("edit_intent", {}) if isinstance(payload.get("edit_intent"), dict) else {}
    operations = edit_intent.get("operations", []) if isinstance(edit_intent.get("operations"), list) else []
    operation_paths = [
        str(item.get("path"))
        for item in operations
        if isinstance(item, dict) and isinstance(item.get("path"), str) and str(item.get("path"))
    ]
    if operation_paths and any(isinstance(item, dict) and item.get("status") == "applied" for item in applied_changes):
        return _dedupe_preserve_order_strings(operation_paths)
    return []


def _dedupe_preserve_order_strings(items: list[str]) -> list[str]:
    deduped: list[str] = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _resume_contract(
    request: ExecutionRequest,
    pending_approval: dict[str, object] | None,
    current_step: ExecutionStep | None,
    *,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata = request.session_metadata if isinstance(request.session_metadata, dict) else {}
    payload = payload if isinstance(payload, dict) else {}
    continuity_contract = (
        payload.get("session_continuity_contract", {})
        if isinstance(payload.get("session_continuity_contract"), dict)
        else {}
    )
    continuity_snapshot = (
        continuity_contract.get("continuity_snapshot", {})
        if isinstance(continuity_contract.get("continuity_snapshot"), dict)
        else {}
    )
    program_posture = (
        continuity_contract.get("program_posture", {})
        if isinstance(continuity_contract.get("program_posture"), dict)
        else {}
    )
    native_tool_usage = (
        payload.get("native_tool_usage", {})
        if isinstance(payload.get("native_tool_usage"), dict)
        else {}
    )
    session_productization_surface = (
        continuity_contract.get("session_productization_surface", {})
        if isinstance(continuity_contract.get("session_productization_surface"), dict)
        else {}
    )
    workflow_continuity = (
        continuity_contract.get("workflow_continuity", {})
        if isinstance(continuity_contract.get("workflow_continuity"), dict)
        else {}
    )
    operator_posture_digest = (
        session_productization_surface.get("operator_posture_digest", {})
        if isinstance(session_productization_surface.get("operator_posture_digest"), dict)
        else {}
    )
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
        continuity_snapshot=continuity_snapshot,
        program_posture=program_posture,
        workflow_continuity=workflow_continuity,
        native_tool_usage=native_tool_usage,
        operator_posture_digest=operator_posture_digest,
        shared_evidence_surface=list(continuity_contract.get("shared_evidence_surface", []))
        if isinstance(continuity_contract.get("shared_evidence_surface"), list)
        else [],
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
