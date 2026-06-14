"""Compatibility wrapper around the current orchestration execution flow."""

from __future__ import annotations

from dataclasses import dataclass

from agent_orchestrator.execution.models import (
    ExecutionKernelContract,
    ExecutionRequest,
    ExecutionResult,
    UnifiedAgentAdapterContract,
)
from agent_orchestrator.execution.runtime import ExecutionRuntime
from agent_orchestrator.orchestrator import Orchestrator


@dataclass(slots=True)
class LegacyExecutionRuntime(ExecutionRuntime):
    """Phase-1 adapter that treats the current orchestration flow as a runtime."""

    orchestrator: Orchestrator
    name: str = "legacy"

    def _kernel_contract(self) -> ExecutionKernelContract:
        return ExecutionKernelContract(
            kernel_name=self.name,
            kernel_role="compatibility_execution_runtime",
            input_sources=[
                "execution_request",
                "route_result",
                "provider_runtime_capabilities",
            ],
            output_surfaces=[
                "execution_result",
                "run_handle",
                "runtime_event_stream",
            ],
        )

    def _adapter_contract(self) -> UnifiedAgentAdapterContract:
        capability_surface = _shared_adapter_capability_surface(
            adapter_family="external_hot_plug",
            agent_kind="legacy_provider_runtime",
            runtime_metadata={
                "runtime_name": self.name,
                "execution_mode": "legacy",
            },
            approval_required=False,
            approval_pause_supported=False,
            evidence_outputs=[
                "execution_result",
                "run_handle",
                "runtime_event_stream",
            ],
            recovery_surfaces=[
                "run_store",
            ],
        )
        return UnifiedAgentAdapterContract(
            adapter_family="external_hot_plug",
            agent_kind="legacy_provider_runtime",
            execution_contract=self._kernel_contract().to_dict(),
            runtime_metadata={
                "runtime_name": self.name,
                "execution_mode": "legacy",
            },
            capability_surface=capability_surface,
            approval_semantics={
                "approval_required": False,
                "approval_pause_supported": False,
            },
            evidence_outputs=[
                "execution_result",
                "run_handle",
                "runtime_event_stream",
            ],
            recovery_surfaces=[
                "run_store",
            ],
        )

    def run(self, request: ExecutionRequest) -> ExecutionResult:
        run = self.orchestrator.run(
            request.requirement,
            request.mode,
            reroute=request.reroute,
            agent_enabled=request.agent_enabled,
            depth=request.depth,
            review_policy_override=request.review_policy_override,
            provider_health_snapshot=request.provider_health_snapshot,
        )
        payload = run.to_dict()
        payload.setdefault("kernel_contract", self._kernel_contract().to_dict())
        payload.setdefault("adapter_contract", self._adapter_contract().to_dict())
        payload.setdefault("session_id", request.session_id)
        payload.setdefault("turn_id", request.turn_id)
        if isinstance(request.context_snapshot, dict):
            payload.setdefault("context_snapshot", dict(request.context_snapshot))
        return ExecutionResult(
            runtime_name=self.name,
            execution_mode=request.route.execution_mode,
            task_kind=request.route.task_kind,
            payload=payload,
            run_id=run.run_id,
            accepted=run.accepted,
            status=run.status,
            reasons=list(request.route.reasons),
            session_id=request.session_id,
            turn_id=request.turn_id,
            kernel_contract=self._kernel_contract(),
        )

    def start(self, request: ExecutionRequest) -> ExecutionResult:
        handle = self.orchestrator.start_run(
            request.requirement,
            request.mode,
            reroute=request.reroute,
            agent_enabled=request.agent_enabled,
            depth=request.depth,
            review_policy_override=request.review_policy_override,
            provider_health_snapshot=request.provider_health_snapshot,
        )
        payload = handle.to_dict()
        payload.setdefault("kernel_contract", self._kernel_contract().to_dict())
        payload.setdefault("adapter_contract", self._adapter_contract().to_dict())
        payload.setdefault("session_id", request.session_id)
        payload.setdefault("turn_id", request.turn_id)
        if isinstance(request.context_snapshot, dict):
            payload.setdefault("context_snapshot", dict(request.context_snapshot))
        return ExecutionResult(
            runtime_name=self.name,
            execution_mode=request.route.execution_mode,
            task_kind=request.route.task_kind,
            payload=payload,
            run_id=handle.run_id,
            accepted=None,
            status=handle.status,
            reasons=list(request.route.reasons),
            session_id=request.session_id,
            turn_id=request.turn_id,
            kernel_contract=self._kernel_contract(),
        )

    def resume_from_state(self, request: ExecutionRequest) -> ExecutionResult:
        # Legacy execution has no step-level persisted resume contract yet, so resume
        # currently re-enters the compatibility runtime through the normal sync path.
        return self.run(request)


def _shared_adapter_capability_surface(
    *,
    adapter_family: str,
    agent_kind: str,
    runtime_metadata: dict[str, object],
    approval_required: bool,
    approval_pause_supported: bool,
    evidence_outputs: list[str],
    recovery_surfaces: list[str],
) -> dict[str, object]:
    return {
        "format": "agent_orchestrator.adapter_capability_surface.v1",
        "adapter_family": adapter_family,
        "agent_kind": agent_kind,
        "runtime_metadata": dict(runtime_metadata),
        "path_selection": {
            "default_path": "external",
            "operating_boundary": "fallback_governed",
            "selection_reason": "Legacy runtime remains hot-pluggable under governed fallback.",
            "handoff_reason_code": None,
            "fallback_reason_code": "external_runtime_unavailable",
        },
        "governance": {
            "approval_required": approval_required,
            "approval_pause_supported": approval_pause_supported,
            "fallback_governed": True,
            "hot_plug_supported": True,
        },
        "evidence_outputs": list(evidence_outputs),
        "recovery_surfaces": list(recovery_surfaces),
        "comparability": {
            "shared_with_external": True,
            "shared_with_native": True,
            "comparison_mode": "same_contract_two_executors",
        },
    }
