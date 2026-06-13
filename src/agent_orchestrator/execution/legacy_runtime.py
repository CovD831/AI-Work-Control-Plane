"""Compatibility wrapper around the current orchestration execution flow."""

from __future__ import annotations

from dataclasses import dataclass

from agent_orchestrator.execution.models import ExecutionRequest, ExecutionResult
from agent_orchestrator.execution.runtime import ExecutionRuntime
from agent_orchestrator.orchestrator import Orchestrator


@dataclass(slots=True)
class LegacyExecutionRuntime(ExecutionRuntime):
    """Phase-1 adapter that treats the current orchestration flow as a runtime."""

    orchestrator: Orchestrator
    name: str = "legacy"

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
        )

    def resume_from_state(self, request: ExecutionRequest) -> ExecutionResult:
        # Legacy execution has no step-level persisted resume contract yet, so resume
        # currently re-enters the compatibility runtime through the normal sync path.
        return self.run(request)
