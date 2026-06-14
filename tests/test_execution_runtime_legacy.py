from agent_orchestrator import OrchestrationMode
from agent_orchestrator.execution import ExecutionRequest, LegacyExecutionRuntime
from agent_orchestrator.intake import ClarifyPolicy, ExecutionMode, TaskKind, TaskRouterResult
from agent_orchestrator.orchestrator import Orchestrator


def _route() -> TaskRouterResult:
    return TaskRouterResult(
        task_kind=TaskKind.DIRECT_FIX,
        clarify_policy=ClarifyPolicy.LIGHT,
        execution_mode=ExecutionMode.LEGACY,
        ambiguity_level="low",
        risk_level="medium",
        scope_confidence="high",
        needs_repo_context=True,
        requires_human_confirmation=False,
        reasons=["test route"],
    )


def test_legacy_execution_runtime_runs_sync_requests() -> None:
    runtime = LegacyExecutionRuntime(orchestrator=Orchestrator())
    request = ExecutionRequest(
        requirement="Fix the flaky validation path in tests/test_jobs.py.",
        route=_route(),
        runtime_name="legacy",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-1",
        turn_id="turn-1",
        context_snapshot={"snapshot_id": "snapshot-1"},
    )

    result = runtime.run(request)

    assert result.runtime_name == "legacy"
    assert result.execution_mode == ExecutionMode.LEGACY
    assert result.task_kind == TaskKind.DIRECT_FIX
    assert result.kernel_contract is not None
    assert result.kernel_contract.kernel_role == "compatibility_execution_runtime"
    assert result.payload["kernel_contract"]["provider_runtime_role"] == "execution_backend"
    assert result.payload["adapter_contract"]["adapter_family"] == "external_hot_plug"
    assert result.payload["adapter_contract"]["agent_kind"] == "legacy_provider_runtime"
    assert result.payload["adapter_contract"]["capability_surface"]["format"] == "agent_orchestrator.adapter_capability_surface.v1"
    assert result.payload["adapter_contract"]["capability_surface"]["comparability"]["comparison_mode"] == "same_contract_two_executors"
    assert result.run_id
    assert result.status in {"completed", "failed", "blocked"}
    assert "run_id" in result.payload
    assert result.session_id == "agent-session-1"
    assert result.turn_id == "turn-1"
    assert result.payload["session_id"] == "agent-session-1"


def test_legacy_execution_runtime_starts_async_requests() -> None:
    runtime = LegacyExecutionRuntime(orchestrator=Orchestrator())
    request = ExecutionRequest(
        requirement="Investigate why the run queue stalls.",
        route=_route(),
        runtime_name="legacy",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-2",
        turn_id="turn-2",
        context_snapshot={"snapshot_id": "snapshot-2"},
    )

    result = runtime.start(request)

    assert result.runtime_name == "legacy"
    assert result.run_id
    assert result.status in {"queued", "running", "completed", "failed", "blocked"}
    assert result.payload["adapter_contract"]["adapter_family"] == "external_hot_plug"
    assert result.payload["adapter_contract"]["capability_surface"]["governance"]["hot_plug_supported"] is True
    assert "run_id" in result.payload
    assert result.payload["turn_id"] == "turn-2"


def test_legacy_execution_runtime_resume_from_state_falls_back_to_sync_run() -> None:
    runtime = LegacyExecutionRuntime(orchestrator=Orchestrator())
    request = ExecutionRequest(
        requirement="Resume the compatibility execution path for a bounded direct fix.",
        route=_route(),
        runtime_name="legacy",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-3",
        turn_id="turn-3",
        context_snapshot={"snapshot_id": "snapshot-3"},
        resume_kind="approval_resume",
    )

    result = runtime.resume_from_state(request)

    assert result.runtime_name == "legacy"
    assert result.run_id
    assert result.session_id == "agent-session-3"
    assert result.turn_id == "turn-3"
