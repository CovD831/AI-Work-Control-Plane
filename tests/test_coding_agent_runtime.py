from pathlib import Path

import json
import pytest

from agent_orchestrator import OrchestrationMode
from agent_orchestrator.control_plane import resolve_approval_item
from agent_orchestrator.control_plane_approvals import ApprovalStore
from agent_orchestrator.execution import coding_agent_runtime as runtime_module
from agent_orchestrator.execution import CodingAgentExecutionRuntime, ExecutionRequest
from agent_orchestrator.execution.coding_components import ActionExecutor, RepoExplorationReport, VerificationReport
from agent_orchestrator.execution.native_tools import NativeToolbox
from agent_orchestrator.execution.models import ActionRequest, ExecutionResumeContract
from agent_orchestrator.intake import ClarifyPolicy, ExecutionMode, TaskKind, TaskRouterResult
from agent_orchestrator.memory import MemoryStore
from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.session import ScratchpadStore


def _coding_route() -> TaskRouterResult:
    return TaskRouterResult(
        task_kind=TaskKind.DIRECT_FIX,
        clarify_policy=ClarifyPolicy.LIGHT,
        execution_mode=ExecutionMode.CODING_AGENT,
        ambiguity_level="low",
        risk_level="medium",
        scope_confidence="high",
        needs_repo_context=True,
        requires_human_confirmation=False,
        native_coverage_class="bounded_internal_repo_task",
        reasons=["test coding-agent route"],
    )


def test_coding_agent_runtime_returns_structured_execution_payload() -> None:
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    request = ExecutionRequest(
        requirement="Fix the login button click handler in src/agent_orchestrator/cli.py.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-1",
        turn_id="turn-1",
        context_snapshot={"snapshot_id": "snapshot-1"},
        task_contract={
            "id": "task-1",
            "goal": "Fix the click handler",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Fix the click handler"],
            "outputs": ["patch plan"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.runtime_name == "coding_agent"
    assert result.execution_mode == ExecutionMode.CODING_AGENT
    assert result.payload["adapter_contract"]["adapter_family"] == "native_first_party"
    assert result.payload["adapter_contract"]["capability_surface"]["format"] == "agent_orchestrator.adapter_capability_surface.v1"
    assert result.payload["adapter_contract"]["capability_surface"]["comparability"]["comparison_mode"] == "same_contract_two_executors"
    assert result.payload["adapter_contract"]["capability_surface"]["shared_contract"]["format"] == "agent_orchestrator.adapter_shared_contract.v1"
    assert result.payload["adapter_contract"]["capability_surface"]["shared_contract"]["path_selection"]["default_path"] == "native"
    assert result.payload["adapter_contract"]["capability_surface"]["shared_contract"]["continuity_support"]["resume_contract"] is True
    assert result.payload["adapter_contract"]["capability_surface"]["shared_contract"]["recovery_contract"]["continue_allowed"] is True
    assert result.payload["adapter_contract"]["capability_surface"]["shared_contract"]["recovery_contract"]["resume_continuity_required"] is True
    assert result.payload["adapter_contract"]["path_selection"]["default_path"] == "native"
    assert result.payload["path_selection"]["operating_boundary"] == "native_preferred"
    assert result.path_selection["selection_reason"]
    assert result.payload["path_selection"]["native_coverage_class"] == "bounded_internal_repo_task"
    assert result.payload["path_selection"]["learning_consumed"] is False
    assert result.payload["path_selection"]["planner_intent"]["edit"] is True
    assert result.payload["path_selection"]["planner_intent"]["verify"] is True
    assert result.payload["native_tool_surface"]["format"] == "agent_orchestrator.native_tool_surface.v1"
    assert result.payload["native_tool_surface"]["tools"] == [
        "read",
        "search",
        "glob",
        "find_files",
        "outline",
        "patch_preview",
        "structured_patch",
        "diff_preview",
        "verify",
        "repo_map",
        "tool_trace",
    ]
    assert result.payload["native_tool_surface"]["capability_profile"]["structured_patch"]["purpose"] == "auditable bounded mutations with preview evidence"
    assert result.payload["native_tool_surface"]["capability_profile"]["patch_preview"]["purpose"] == "pre-apply bounded mutation preview for operator-visible review"
    assert result.payload["native_tool_surface"]["capability_profile"]["diff_preview"]["purpose"] == "governed bounded change preview for operator-visible review"
    assert result.payload["native_tool_surface"]["workflow_surface"]["daily_driver_path"]["tools"] == [
        "repo_map",
        "find_files",
        "search",
        "outline",
        "read",
        "patch_preview",
        "structured_patch",
        "diff_preview",
        "verify",
    ]
    assert result.payload["native_tool_surface"]["daily_driver_readiness"]["structured_patch_ready"] is True
    assert result.payload["native_tool_surface"]["daily_driver_readiness"]["patch_preview_ready"] is True
    assert result.payload["native_tool_surface"]["daily_driver_readiness"]["diff_preview_ready"] is True
    assert result.payload["native_tool_surface"]["daily_driver_readiness"]["verification_ready"] is True
    assert result.payload["native_tool_productization_surface"]["format"] == "agent_orchestrator.native_tool_productization_surface.v1"
    assert result.payload["native_tool_productization_surface"]["operator_visibility_ready"] is True
    assert result.payload["native_tool_productization_surface"]["readiness"]["bounded_read_search_ready"] is True
    assert result.payload["native_tool_workflow_surface"]["daily_driver_path"]["tools"] == [
        "repo_map",
        "find_files",
        "search",
        "outline",
        "read",
        "patch_preview",
        "structured_patch",
        "diff_preview",
        "verify",
    ]
    assert result.payload["native_tool_productization_surface"]["workflow_surface"]["explore"]["tools"] == [
        "repo_map",
        "find_files",
        "search",
        "outline",
        "read",
    ]
    assert result.payload["adapter_productization_surface"]["format"] == "agent_orchestrator.adapter_productization_surface.v1"
    assert result.payload["adapter_productization_surface"]["surface_status"] == "same_contract_two_executors_governed"
    assert result.payload["adapter_productization_surface"]["hot_plug_supported"] is True
    assert result.payload["adapter_productization_surface"]["fallback_governed"] is True
    assert result.payload["adapter_productization_surface"]["resume_contract_supported"] is True
    assert result.payload["adapter_capability_surface"]["format"] == "agent_orchestrator.adapter_capability_surface.v1"
    assert result.payload["adapter_capability_surface"]["comparability"]["comparison_mode"] == "same_contract_two_executors"
    assert "workspace_index" in result.payload["adapter_capability_surface"]["shared_evidence_surface"]
    assert result.payload["adapter_capability_surface"]["shared_contract"]["operator_visibility_contract"]["session_surface_required"] is True
    assert result.payload["adapter_capability_surface"]["shared_contract"]["tooling_contract"]["workflow_projection_required"] is True
    assert result.payload["adapter_capability_surface"]["shared_contract"]["operator_recovery_surface"]["default_recovery_lane"] == "approval_pause"
    assert result.payload["adapter_capability"]["format"] == "agent_orchestrator.adapter_capability_surface.v1"
    assert result.payload["adapter_capability"]["shared_contract_format"] == "agent_orchestrator.adapter_shared_contract.v1"
    assert result.payload["adapter_capability"]["shared_contract_operator_recovery_surface"]["default_recovery_lane"] == "approval_pause"
    assert result.payload["native_tool_trace"]["trace_count"] >= 1
    assert result.payload["native_tool_trace"]["trace"][0]["timestamp"]
    assert result.kernel_contract is not None
    assert result.kernel_contract.kernel_role == "governed_execution_kernel"
    assert "control_plane_artifacts" in result.kernel_contract.input_sources
    assert "runtime_event_stream" in result.kernel_contract.output_surfaces
    assert result.payload["kernel_contract"]["state_authority"] == "control_plane"
    assert result.payload["repo_report"]["candidate_paths"]
    assert result.payload["repo_report"]["artifact"]["tool_surface"]["tools"] == [
        "read",
        "search",
        "glob",
        "find_files",
        "outline",
        "patch_preview",
        "structured_patch",
        "diff_preview",
        "verify",
        "repo_map",
        "tool_trace",
    ]
    assert result.payload["repo_report"]["artifact"]["tool_surface"]["capability_profile"]["structured_patch"]["output_shape"] == "applied_change_records_with_previews"
    assert result.payload["repo_report"]["artifact"]["tool_surface"]["capability_profile"]["patch_preview"]["output_shape"] == "planned_change_preview_records"
    assert result.payload["repo_report"]["artifact"]["tool_surface"]["capability_profile"]["diff_preview"]["output_shape"] == "change_preview_records"
    assert result.payload["repo_report"]["artifact"]["tool_surface"]["capability_profile"]["verify"]["output_shape"] == "command_result_artifact"
    assert result.payload["repo_report"]["artifact"]["exploration_evidence"]["format"] == "agent_orchestrator.native_exploration_evidence.v1"
    assert "runtime_payload" in result.payload["repo_report"]["artifact"]["exploration_evidence"]["shared_evidence_surface"]
    assert result.payload["repo_report"]["artifact"]["exploration_profile"]["outline_record_count"] >= 0
    assert result.payload["repo_report"]["artifact"]["exploration_evidence"]["read_record_count"] >= 1
    assert result.payload["execution_context"]["session_context"]["session_id"] == "agent-session-1"
    assert result.payload["edit_intent"]["mode"] == "report_first"
    assert "verification" in result.payload
    assert "repair_summary" in result.payload
    assert [step["kind"] for step in result.payload["execution_steps"]] == [
        "repo_exploration",
        "edit_execution",
        "verification",
    ]
    assert result.payload["step_decisions"][-1]["disposition"] == "complete"
    assert result.payload["next_step_contract"]["current_disposition"] == "complete"
    assert result.payload["next_step_contract"]["current_step_kind"] == "verification"
    assert result.payload["next_step_contract"]["context_engineering_refs"]["required_surfaces"] == [
        "select",
        "structured_observation",
        "compact",
        "resume_continuity",
    ]
    assert result.payload["step_loop_contract"]["loop_model"] == "explicit_stage_step_loop"
    assert result.payload["step_loop_contract"]["status"] == "completed"
    assert result.payload["step_loop_contract"]["current_disposition"] == "complete"
    assert result.payload["step_loop_contract"]["context_engineering_refs"]["required_surfaces"] == [
        "select",
        "structured_observation",
        "compact",
        "resume_continuity",
    ]
    assert result.payload["step_loop_contract"]["trace_lengths"]["planner_context_trace"] == 3
    assert result.payload["step_loop_contract"]["trace_refs"]["next_step_contract"] == "payload.next_step_contract"
    assert result.payload["native_task_proof"]["format"] == "agent_orchestrator.native_task_proof.v1"
    assert result.payload["native_task_proof"]["native_runtime_only"] is True
    assert result.payload["native_task_proof"]["external_coding_agent_required"] is False
    assert result.payload["native_task_proof"]["task_class"] == "bounded_internal_repo_task"
    assert result.payload["native_repo_task_acceptance"]["format"] == "agent_orchestrator.native_repo_task_acceptance.v1"
    assert result.payload["native_repo_task_acceptance"]["real_repo_task_acceptance_ready"] is False
    assert result.payload["native_complex_repo_task_acceptance"]["format"] == "agent_orchestrator.native_complex_repo_task_acceptance.v1"
    assert result.payload["native_complex_repo_task_acceptance"]["complex_repo_task_ready"] is False
    assert "find_files" in result.payload["native_complex_repo_task_acceptance"]["complex_task_checks"]["native_exploration_trace_visible"]["evidence"]["explored_tools"]
    assert "edit_workflow_tools" in result.payload["native_complex_repo_task_acceptance"]["complex_task_checks"]["governed_edit_workflow_trace_visible"]["evidence"]
    assert "verification_tools" in result.payload["native_complex_repo_task_acceptance"]["complex_task_checks"]["verification_workflow_trace_visible"]["evidence"]
    assert result.payload["native_complex_repo_task_acceptance"]["complex_task_checks"]["planner_workflow_contract_visible"]["passed"] is True
    assert result.payload["native_complex_repo_task_acceptance"]["complex_task_checks"]["planner_workflow_runtime_alignment_visible"]["passed"] is True
    assert result.payload["native_task_proof"]["kernel_governed"] is True
    assert result.payload["native_task_proof"]["context_select_explicit"] is True
    assert [item["stage"] for item in result.payload["stage_selection_trace"]] == ["explore", "edit", "verify"]
    assert result.payload["stage_selection_trace"][-1]["outcome"] == "complete"
    assert [item["stage_cursor"] for item in result.payload["planner_context_trace"]] == ["explore", "edit", "verify"]
    assert [item["current_stage"] for item in result.payload["next_stage_proposals"]] == ["explore", "edit", "verify"]
    assert result.payload["next_stage_proposals"][0]["proposed_stage"] == "edit"
    assert result.payload["next_stage_proposals"][0]["selected_candidate_id"] == "explore_to_edit"
    assert result.payload["next_stage_proposals"][0]["selection"]["ranking_enabled"] is False
    assert result.payload["next_stage_proposals"][1]["candidates"][0]["candidate_id"] == "edit_to_verify"
    assert result.payload["next_stage_proposals"][-1]["disposition"] == "complete"
    assert result.payload["next_stage_proposals"][-1]["selected_candidate_id"] == "verify_complete"
    assert result.payload["strategy_summary"]["planner_family"] == "native"
    assert result.payload["strategy_summary"]["compatibility_metadata"]["legacy_decompose_used"] is False
    assert result.payload["planner_family"] == "native"
    assert result.payload["strategy_summary"]["decision_evidence"]["autonomy_boundary"]["native_first"] is True
    assert result.payload["strategy_summary"]["decision_evidence"]["planner_reasoning"]["native_first"] is True
    assert result.payload["strategy_summary"]["decision_evidence"]["planner_reasoning"]["primary_action"]
    assert result.payload["strategy_summary"]["decision_evidence"]["planner_reasoning"]["requires_edit"] is True
    assert result.payload["strategy_summary"]["decision_evidence"]["tool_workflow_plan"]["workflow_projection_required"] is True
    assert result.payload["strategy_summary"]["decision_evidence"]["tool_workflow_plan"]["workflow_stages"]["explore"]["selected"] is True
    assert result.payload["planner_context_trace"][0]["resume_kind"] == "fresh"
    assert result.payload["planner_context_trace"][0]["tool_workflow_plan"]["format"] == "agent_orchestrator.native_tool_workflow_plan.v1"
    assert result.payload["planner_context_trace"][0]["current_stage_workflow"]["selected"] is True
    assert "read" in result.payload["planner_context_trace"][0]["current_stage_workflow"]["required_tools"]
    assert result.payload["planner_context_trace"][1]["route_risk_level"] == "medium"
    assert result.payload["planner_context_trace"][1]["applied_change_count"] == 0
    assert result.payload["planner_context_trace"][-1]["recent_observation_count"] == 0
    assert [item["stage"] for item in result.payload["action_selection_trace"]] == ["edit", "verify"]
    assert result.payload["action_selection_trace"][0]["action_type"] == "edit_prepare"
    assert result.payload["action_selection_trace"][0]["source"] == "bounded_context"
    assert result.payload["action_selection_trace"][0]["decision"]["decision_type"] == "action_selection"
    assert result.payload["action_selection_trace"][0]["decision"]["planner_feasibility"] == "prepare_only"
    assert result.payload["action_selection_trace"][0]["decision"]["workflow_projection_required"] is True
    assert "patch_preview" in result.payload["action_selection_trace"][0]["decision"]["current_stage_required_tools"]
    assert result.payload["action_selection_trace"][0]["planner_context"]["stage_cursor"] == "edit"
    assert result.payload["action_selection_trace"][-1]["source"] == "derived_from_targets"
    assert result.payload["stage_selection_trace"][0]["decision"]["selection_mode"] == "proposal_only"
    assert result.payload["stage_selection_trace"][1]["decision"]["selection_mode"] == "action_and_proposal"
    assert result.payload["action_selection_trace"][-1]["selected"]["workflow_projection_required"] is True
    assert result.payload["action_selection_trace"][-1]["selected"]["current_stage_workflow"]["selected"] is True
    assert result.payload["stage_selection_trace"][-1]["planner_context"]["target_paths"]
    assert result.payload["execution_steps"][0]["actions"][0]["action_type"] == "repo_explore"
    assert result.payload["execution_steps"][2]["results"][0]["action_type"] == "run_command"
    assert result.payload["compressed_context"]["objective"] == request.requirement
    assert result.payload["compressed_context"]["recent_steps"][-1]["kind"] == "verification"
    assert "artifact_refs" in result.payload["compressed_context"]
    assert result.payload["compaction_state"]["system_prompt_compacted"] is False
    assert result.payload["context_engineering_contract"]["format"] == "agent_orchestrator.context_engineering_contract.v1"
    assert result.payload["context_engineering_contract"]["main_path_required"] is True
    assert result.payload["context_engineering_contract"]["write"]["session_scratchpad"]["required"] is True
    assert result.payload["context_engineering_contract"]["write"]["persistent_memory"]["projection_mode"] == "explicit_memory_store"
    assert result.payload["context_engineering_contract"]["select"]["required_for_model_participation"] is True
    assert result.payload["context_engineering_contract"]["select"]["deterministic_strategy"] == "fixed_runtime_sources"
    assert result.payload["context_engineering_contract"]["structured_observation"]["required_post_action"] is True
    assert result.payload["context_engineering_contract"]["structured_observation"]["record_count"] >= 1
    assert result.payload["context_engineering_contract"]["compact"]["stage"] == result.payload["compaction_state"]["stage"]
    assert result.payload["context_engineering_contract"]["isolate"]["strategy"] == result.payload["isolation_state"]["strategy"]
    assert result.payload["context_engineering_contract"]["resume_continuity"]["resume_kind"] == result.payload["resume_context"]["resume_kind"]
    assert result.payload["context_engineering_contract"]["trace_refs"]["context_selection"] == "payload.context_selection"
    assert result.payload["scratchpad_entries"][0]["kind"] == "runtime_context"
    assert "retrieved_memory" in result.payload
    assert result.payload["context_selection"]["deterministic"]["strategy"] == "fixed_runtime_sources"
    assert result.payload["context_selection"]["retrieval"]["strategy"] == "memory_search"
    assert "model_driven" in result.payload["context_selection"]
    assert result.payload["isolation_state"]["applied"] in {True, False}
    assert result.payload["isolation_state"]["output_target_count"] == 1
    if result.payload["isolation_state"]["applied"]:
        assert result.payload["isolation_state"]["strategy"] == "subtask_digest"
        assert result.payload["isolation_state"]["reinjection_mode"] == "digest_focus_subset"
    else:
        assert result.payload["isolation_state"]["strategy"] == "inline_context"
        assert result.payload["isolation_state"]["reinjection_mode"] == "full_inline_context"
    assert result.payload["llm_assisted_intent"]["used_model"] in {True, False}
    if result.payload["llm_assisted_intent"]["used_model"]:
        assert result.payload["llm_assisted_intent"]["applied"] is True
        assert result.payload["llm_assisted_intent"]["source"] == "llm"
    else:
        assert result.payload["llm_assisted_intent"]["source"] == "rule_based"


def test_coding_agent_runtime_records_learning_assets_and_trajectory(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        memory_store=MemoryStore(workspace_root / ".agent_orchestrator" / "memory"),
    )
    runtime.repo_explorer.workspace_root = workspace_root
    request = ExecutionRequest(
        requirement="Fix the login button click handler in src/agent_orchestrator/cli.py.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-learning",
        turn_id="turn-learning",
        context_snapshot={"snapshot_id": "snapshot-learning"},
        task_contract={
            "id": "task-learning",
            "goal": "Fix the click handler",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Fix the click handler"],
            "outputs": ["patch plan"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    memory_records = MemoryStore(workspace_root / ".agent_orchestrator" / "memory").query(session_id="agent-session-learning")
    trajectory_dir = workspace_root / ".agent_orchestrator" / "agent_sessions" / "agent-session-learning" / "trajectories"
    lessons = (workspace_root / ".agent_orchestrator" / "knowledge" / "lessons.jsonl").read_text(encoding="utf-8")
    skills = (workspace_root / ".agent_orchestrator" / "knowledge" / "skills.jsonl").read_text(encoding="utf-8")

    assert result.payload["path_selection"]["selection_reason"]
    assert any(record["record_type"] == "trajectory" for record in memory_records)
    assert any(record["record_type"] == "memory" for record in memory_records)
    assert trajectory_dir.exists()
    assert any(path.name.startswith("trajectory-") for path in trajectory_dir.iterdir())
    assert "bounded_internal_repo_task" in lessons
    assert "curator_ready" in skills


def test_coding_agent_runtime_records_bounded_retry_attempts_on_failure() -> None:
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())

    class _RetryVerifier:
        def __init__(self) -> None:
            self.calls = 0

        def run(self, request, edit_intent):
            self.calls += 1
            if self.calls == 1:
                return VerificationReport(
                    status="failed",
                    command=["python3", "-m", "compileall", "missing.py"],
                    exit_code=1,
                    stdout="",
                    stderr="missing.py",
                    failure_kind="nonzero_exit",
                )
            return VerificationReport(
                status="passed",
                command=["python3", "-m", "compileall", "src/agent_orchestrator/cli.py"],
                exit_code=0,
                stdout="ok",
                stderr="",
            )

    runtime.verify_loop.verifier = _RetryVerifier()
    request = ExecutionRequest(
        requirement="Fix the login button click handler in src/agent_orchestrator/cli.py.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-2",
        turn_id="turn-2",
        context_snapshot={"snapshot_id": "snapshot-2"},
        task_contract={
            "id": "task-2",
            "goal": "Fix the click handler",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Fix the click handler"],
            "outputs": ["patch plan"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.accepted is True
    assert result.payload["repair_summary"]["attempt_count"] == 2
    assert result.payload["attempt_memory"][0]["verification"]["status"] == "failed"
    assert result.payload["attempt_memory"][1]["verification"]["status"] == "passed"


def test_coding_agent_runtime_surfaces_recovery_summary_when_retry_budget_exhausts() -> None:
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())

    class _AlwaysFailVerifier:
        def run(self, request, edit_intent):
            return VerificationReport(
                status="failed",
                command=["python3", "-m", "compileall", "broken.py"],
                exit_code=1,
                stdout="",
                stderr="broken.py",
                failure_kind="nonzero_exit",
            )

    runtime.verify_loop.verifier = _AlwaysFailVerifier()
    request = ExecutionRequest(
        requirement="Fix the login button click handler in src/agent_orchestrator/cli.py.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-3",
        turn_id="turn-3",
        context_snapshot={"snapshot_id": "snapshot-3"},
        task_contract={
            "id": "task-3",
            "goal": "Fix the click handler",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Fix the click handler"],
            "outputs": ["patch plan"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.accepted is False
    assert result.status == "blocked"
    assert result.payload["repair_summary"]["outcome"] == "failed"
    assert result.payload["recovery_summary"]["human_review_recommended"] is True


def test_coding_agent_runtime_writes_session_scratchpad_and_persistent_memory(tmp_path) -> None:
    scratchpad_root = tmp_path / "scratchpads"
    memory_root = tmp_path / "memory"
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        scratchpad_store=ScratchpadStore(scratchpad_root),
        memory_store=MemoryStore(memory_root),
    )
    request = ExecutionRequest(
        requirement="Inspect repository context for cli.py.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-scratch",
        turn_id="turn-scratch",
        context_snapshot={"snapshot_id": "snapshot-scratch"},
        task_contract={
            "id": "task-scratch",
            "goal": "Inspect context",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Inspect repository context"],
            "outputs": ["context notes"],
            "acceptance_criteria": ["Structured output exists"],
            "risk_level": "low",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    scratchpad_entries = ScratchpadStore(scratchpad_root).query(session_id="agent-session-scratch", turn_id="turn-scratch")
    assert scratchpad_entries
    assert scratchpad_entries[0]["kind"] == "runtime_context"
    assert scratchpad_entries[0]["payload"]["planner_context_trace"]
    assert scratchpad_entries[0]["payload"]["context_selection"]["deterministic"]["strategy"] == "fixed_runtime_sources"
    assert result.payload["scratchpad_entries"][0]["entry_id"] == scratchpad_entries[0]["entry_id"]
    assert result.payload["context_engineering_contract"]["write"]["session_scratchpad"]["entry_kind"] == "runtime_context"

    memory_records = MemoryStore(memory_root).query(session_id="agent-session-scratch", namespace="coding_agent")
    assert memory_records
    assert memory_records[0]["record_type"] == "runtime_preference_or_fact"
    assert memory_records[0]["payload"]["turn_id"] == "turn-scratch"
    assert result.payload["context_engineering_contract"]["write"]["persistent_memory"]["retrieved_memory_count"] >= 0


def test_coding_agent_runtime_context_selection_retrieves_memory_hits(tmp_path) -> None:
    memory_root = tmp_path / "memory"
    store = MemoryStore(memory_root)
    stored = store.append(
        namespace="coding_agent",
        session_id="agent-session-select",
        record_type="user_preference",
        summary="User prefers minimal CLI runtime changes and explicit verification.",
        provider="coding_agent",
        payload={"preference": "minimal_cli_changes"},
        freshness="fresh",
    )
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        memory_store=store,
        scratchpad_store=ScratchpadStore(tmp_path / "scratchpads"),
    )
    request = ExecutionRequest(
        requirement="Make a minimal CLI change and keep explicit verification in place.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-select",
        turn_id="turn-select",
        context_snapshot={"snapshot_id": "snapshot-select"},
        task_contract={
            "id": "task-select",
            "goal": "Update CLI behavior conservatively",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Update CLI behavior conservatively"],
            "outputs": ["runtime context packet"],
            "acceptance_criteria": ["memory-backed selection recorded"],
            "risk_level": "low",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.payload["context_selection"]["retrieval"]["selected_memory_count"] >= 1
    assert stored.id in result.payload["context_selection"]["selected_context"]["retrieved_memory_ids"]
    assert stored.id in [item["id"] for item in result.payload["retrieved_memory"]]


def test_coding_agent_runtime_uses_llm_assisted_intent_refinement_on_main_path() -> None:
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    seen_context_selection: dict[str, object] = {}

    def _fake_transport(request_url, payload, headers, timeout_seconds):
        assert request_url.endswith("/chat/completions")
        assert payload["response_format"] == {"type": "json_object"}
        messages = payload["messages"]
        assert isinstance(messages, list)
        user_message = messages[1]
        user_payload = json.loads(user_message["content"])
        seen_context_selection.update(user_payload["context_selection"])
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "summary": "Inspect the CLI handler and produce a bounded patch/report plan.",
                                "target_paths": ["src/agent_orchestrator/cli.py"],
                                "patch_plan": [
                                    "Inspect src/agent_orchestrator/cli.py and confirm the click-handler entry path.",
                                    "Describe the bounded code change before applying any mutation.",
                                ],
                                "rationale": "The requirement explicitly points to the CLI file.",
                            }
                        )
                    }
                }
            ]
        }

    runtime.intent_refiner_transport = _fake_transport
    request = ExecutionRequest(
        requirement="Fix the login button click handler in src/agent_orchestrator/cli.py.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-llm-intent",
        turn_id="turn-llm-intent",
        context_snapshot={"snapshot_id": "snapshot-llm-intent"},
        task_contract={
            "id": "task-llm-intent",
            "goal": "Fix the click handler",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Fix the click handler"],
            "outputs": ["patch plan"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.payload["llm_assisted_intent"]["used_model"] is True
    assert result.payload["llm_assisted_intent"]["applied"] is True
    assert result.payload["llm_assisted_intent"]["source"] == "llm"
    assert result.payload["edit_intent"]["target_paths"] == ["src/agent_orchestrator/cli.py"]
    assert result.payload["edit_intent"]["patch_plan"][0].startswith("Inspect src/agent_orchestrator/cli.py")
    assert seen_context_selection["deterministic"]["strategy"] == "fixed_runtime_sources"


def test_coding_agent_runtime_sanitizes_llm_intent_refinement_paths() -> None:
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())

    def _fake_transport(request_url, payload, headers, timeout_seconds):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "summary": "Inspect unrelated paths.",
                                "target_paths": ["outside/project/unknown.py"],
                                "patch_plan": ["Inspect an unrelated file."],
                                "rationale": "bad candidate",
                            }
                        )
                    }
                }
            ]
        }

    runtime.intent_refiner_transport = _fake_transport
    request = ExecutionRequest(
        requirement="Fix the login button click handler in src/agent_orchestrator/cli.py.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-llm-fallback",
        turn_id="turn-llm-fallback",
        context_snapshot={"snapshot_id": "snapshot-llm-fallback"},
        task_contract={
            "id": "task-llm-fallback",
            "goal": "Fix the click handler",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Fix the click handler"],
            "outputs": ["patch plan"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.payload["llm_assisted_intent"]["used_model"] is True
    assert result.payload["edit_intent"]["target_paths"]
    assert "outside/project/unknown.py" not in result.payload["edit_intent"]["target_paths"]


def test_model_driven_context_selection_falls_back_when_candidate_set_is_small(monkeypatch) -> None:
    monkeypatch.delenv("AO_SLOTFILL_API_KEY", raising=False)
    monkeypatch.delenv("AO_SLOTFILL_BASE_URL", raising=False)
    monkeypatch.delenv("AO_SLOTFILL_MODEL", raising=False)

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())

    selection = runtime_module._model_driven_context_selection(
        runtime,
        request=ExecutionRequest(
            requirement="Make a small targeted CLI fix.",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
        ),
        deterministic_items=[
            {"source": "request_context", "kind": "session_context"},
            {"source": "request_context", "kind": "task_contract"},
        ],
        memory_records=[],
    )

    assert selection["used_model"] is False
    assert selection["strategy"] == "deterministic_fallback"


def test_coding_agent_runtime_context_selection_uses_model_driven_selector_when_candidates_are_broad(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("AO_SLOTFILL_API_KEY", "secret-key")
    monkeypatch.setenv("AO_SLOTFILL_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("AO_SLOTFILL_MODEL", "gpt-test")

    memory_root = tmp_path / "memory"
    store = MemoryStore(memory_root)
    stored_ids: list[str] = []
    for index in range(5):
        record = store.append(
            namespace="coding_agent",
            session_id="agent-session-model-select",
            record_type=f"memory_note_{index}",
            summary=f"Relevant memory note {index} about broad CLI investigation.",
            provider="coding_agent",
            payload={"index": index},
            freshness="fresh",
        )
        stored_ids.append(record.id)

    def fake_transport(request_url: str, payload: dict[str, object], headers: dict[str, str], timeout_seconds: int) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "selected_items": [f"memory:{stored_ids[0]}", f"memory:{stored_ids[1]}"],
                                "rationale": "Choose the most relevant memory-backed context candidates.",
                            }
                        )
                    }
                }
            ]
        }

    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        memory_store=store,
        scratchpad_store=ScratchpadStore(tmp_path / "scratchpads"),
        model_selector_transport=fake_transport,
    )
    request = ExecutionRequest(
        requirement="Investigate several CLI behaviors and compare multiple possible runtime paths.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-model-select",
        turn_id="turn-model-select",
        context_snapshot={"snapshot_id": "snapshot-model-select"},
        task_contract={
            "id": "task-model-select",
            "goal": "Investigate broad CLI behavior",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Investigate broad CLI behavior"],
            "outputs": ["context selection"],
            "acceptance_criteria": ["model-driven selection recorded"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.payload["context_selection"]["model_driven"]["used_model"] is True
    assert result.payload["context_selection"]["model_driven"]["strategy"] == "openai_compatible_model_selector"
    assert result.payload["context_selection"]["model_driven"]["selected_items"] == [
        f"memory:{stored_ids[0]}",
        f"memory:{stored_ids[1]}",
    ]
    assert result.payload["scratchpad_entries"][0]["payload"]["context_selection"]["model_driven"]["used_model"] is True


def test_compact_observation_window_masks_older_history_and_preserves_recent() -> None:
    observations = [
        {
            "observation_id": f"obs-{index}",
            "kind": "verification",
            "source": "verify_loop",
            "summary": f"Observation {index}",
            "payload": {"stdout": f"log-{index}", "stderr": ""},
            "has_artifact": False,
            "deduplicated": False,
            "masked": False,
        }
        for index in range(6)
    ]

    compacted = runtime_module._compact_observation_window(observations, preserve_recent=2)

    assert len(compacted) == 6
    assert compacted[0]["masked"] is True
    assert compacted[0]["payload"]["masked"] is True
    assert compacted[-1]["masked"] is False
    assert compacted[-2]["summary"] == "Observation 4"


def test_compaction_state_reports_observation_masking_stage() -> None:
    step = runtime_module.ExecutionStep(
        step_id="turn:verify",
        title="Verify",
        kind="verification",
        status="completed",
        observations=[
            runtime_module.ObservationRecord(
                observation_id=f"obs-{index}",
                kind="verification",
                summary=f"Observation {index}",
                source="verify_loop",
                payload={"stdout": f"log-{index}", "stderr": ""},
            )
            for index in range(5)
        ],
    )

    state = runtime_module._compaction_state(
        CodingAgentExecutionRuntime(orchestrator=Orchestrator()),
        request=ExecutionRequest(
            requirement="Verify one file.",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
        ),
        steps=[step],
        context_selection={"deterministic": {"selected_items": []}, "retrieval": {"selected_memory_count": 0}},
    )

    assert state["stage"] == "observation_masking"
    assert state["masked_count"] == 2
    assert state["preserve_recent"] == 3
    assert state["light_compaction_applied"] is True
    assert state["summarization_triggered"] is False
    assert state["system_prompt_compacted"] is False


def test_compaction_state_reports_summarization_ready_at_high_water_mark() -> None:
    step = runtime_module.ExecutionStep(
        step_id="turn:verify",
        title="Verify",
        kind="verification",
        status="completed",
        observations=[
            runtime_module.ObservationRecord(
                observation_id=f"obs-{index}",
                kind="verification",
                summary=f"Observation {index}",
                source="verify_loop",
                payload={"stdout": f"log-{index}", "stderr": ""},
            )
            for index in range(10)
        ],
    )

    state = runtime_module._compaction_state(
        CodingAgentExecutionRuntime(orchestrator=Orchestrator()),
        request=ExecutionRequest(
            requirement="Verify many files.",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
        ),
        steps=[step],
        context_selection={"deterministic": {"selected_items": []}, "retrieval": {"selected_memory_count": 0}},
    )

    assert state["stage"] == "summarization_ready"


def test_coding_agent_runtime_defaults_to_success_first_policy_when_mode_missing(tmp_path) -> None:
    from agent_orchestrator.execution.coding_agent_runtime import CodingAgentExecutionRuntime
    from agent_orchestrator.execution.models import ExecutionRequest
    from agent_orchestrator.intake.models import ClarifyPolicy, ExecutionMode, TaskKind, TaskRouterResult

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path

    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    result = runtime.run(
        ExecutionRequest(
            requirement='Append "print(\'bye\')" to note.py',
            route=TaskRouterResult(
                task_kind=TaskKind.DIRECT_FIX,
                clarify_policy=ClarifyPolicy.LIGHT,
                execution_mode=ExecutionMode.CODING_AGENT,
                ambiguity_level="medium",
                reasons=["bounded fix"],
                operating_boundary="native_preferred",
                selection_reason="test default policy fallback",
                handoff_reason_code=None,
                fallback_reason_code=None,
                risk_level="medium",
                scope_confidence="high",
                needs_repo_context=True,
                requires_human_confirmation=False,
            ),
            runtime_name="coding_agent",
            mode=None,
            task_contract={
                "id": "task-default-mode",
                "goal": "Append a line",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Append a line"],
                "outputs": ["artifact summary"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    assert result.payload["planner_family"] == "native"
    assert result.payload["session_continuity_contract"]["program_posture"]["program_goal"] == "Append a line"
    assert result.payload["session_continuity_contract"]["usage_cost_measurement_status"] == "placeholder"
    assert result.payload["session_continuity_contract"]["runtime_cost_provenance"]["format"] == "agent_orchestrator.runtime_cost_provenance.v1"
    assert result.payload["session_continuity_contract"]["runtime_cost_provenance"]["duration_source"] in {"native_tool_trace", "unavailable"}
    assert result.payload["session_continuity_contract"]["continuity_pressure"]["format"] == "agent_orchestrator.continuity_pressure.v1"
    assert result.payload["session_continuity_contract"]["workflow_continuity"]["format"] == (
        "agent_orchestrator.session_workflow_continuity.v1"
    )
    assert result.payload["session_continuity_contract"]["workflow_continuity"]["tool_workflow_plan"]["format"] in {
        "agent_orchestrator.native_tool_workflow_plan.v1",
        "agent_orchestrator.compatibility_tool_workflow_plan.v1",
    }
    assert "workspace_index" in result.payload["session_continuity_contract"]["shared_evidence_surface"]
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["format"] == "agent_orchestrator.session_productization_surface.v1"
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["continuity_readiness"]["resume_ready"] is True
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["continuity_readiness"]["runtime_cost_ready"] is True
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["continuity_readiness"]["pressure_visible"] is True
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["continuity_readiness"]["workflow_projection_visible"] is True
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["runtime_cost_provenance"]["format"] == "agent_orchestrator.runtime_cost_provenance.v1"
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["continuity_pressure"]["format"] == "agent_orchestrator.continuity_pressure.v1"
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["operator_continuity"]["next_recommended_action"]
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["operator_continuity"]["resume_expectation"] == "resume_if_same_task"
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["operator_continuity"]["planner_governed_alternatives"] == []
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["workflow_continuity"]["active_stage"]
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["operator_posture_digest"]["format"] == "agent_orchestrator.session_operator_posture_digest.v1"
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["operator_posture_digest"]["runtime_duration_seconds"] == result.payload["session_continuity_contract"]["runtime_duration_seconds"]
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["operator_posture_digest"]["usage_cost_measurement_status"] == "placeholder"
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["operator_posture_digest"]["context_pressure"] is not None
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["operator_posture_digest"]["next_recommended_action"]
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["operator_posture_digest"]["resume_expectation"] == "resume_if_same_task"
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["operator_posture_digest"]["planner_governed_alternatives"] == []
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["operator_posture_digest"]["workflow_active_stage"]
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["operator_posture_digest"]["summary"]
    assert result.payload["resume_contract"]["resume_supported"] is True
    assert result.payload["resume_contract"]["continuity_snapshot"]["format"] == "agent_orchestrator.session_continuity_snapshot.v1"
    assert result.payload["resume_contract"]["program_posture"]["program_goal"] == "Append a line"
    assert result.payload["resume_contract"]["workflow_continuity"]["format"] == (
        "agent_orchestrator.session_workflow_continuity.v1"
    )
    assert result.payload["resume_contract"]["native_tool_usage"]["trace_count"] >= 1
    assert result.payload["resume_contract"]["operator_posture_digest"]["format"] == "agent_orchestrator.session_operator_posture_digest.v1"
    assert "workspace_index" in result.payload["resume_contract"]["shared_evidence_surface"]
    assert result.payload["shared_productization_surface"]["format"] == "agent_orchestrator.shared_productization_surface.v1"
    assert result.payload["shared_productization_surface"]["shared_productization_contract_ready"] is True
    assert result.payload["shared_productization_surface"]["planner_closure_posture"]["format"] == "agent_orchestrator.planner_closure_posture.v1"
    assert result.payload["shared_productization_surface"]["planner_closure_posture"]["closure_mode"]
    assert result.payload["shared_productization_surface"]["contract_readiness"]["session_ready"] is True
    assert result.payload["shared_productization_surface"]["contract_readiness"]["tool_ready"] is True
    assert result.payload["shared_productization_surface"]["contract_readiness"]["adapter_ready"] is True
    assert result.payload["shared_productization_surface"]["contract_readiness"]["planner_ready"] is True
    assert "planner_closure_posture" in result.payload["shared_productization_surface"]["shared_evidence_surface"]
    assert result.payload["shared_productization_surface"]["native_tool_workflow_surface"]["verify"]["tools"] == [
        "verify",
        "tool_trace",
    ]
    assert result.payload["shared_productization_surface"]["runtime_cost"]["usage_cost_measurement_status"] == "placeholder"
    assert result.payload["shared_productization_surface"]["session_posture"]["resume_expectation"] == "resume_if_same_task"
    assert result.payload["shared_productization_surface"]["native_tool_usage"]["trace_count"] >= 1
    assert result.payload["shared_productization_surface"]["adapter_capability_surface"]["format"] == "agent_orchestrator.adapter_capability_surface.v1"
    assert result.payload["adapter_shared_contract"]["format"] == "agent_orchestrator.adapter_shared_contract.v1"
    assert result.payload["adapter_shared_contract"]["comparison_mode"] == "same_contract_two_executors"
    assert "workspace_index" in result.payload["adapter_shared_contract"]["shared_evidence_surface"]
    assert result.payload["adapter_shared_contract"]["operator_visibility_contract"]["planner_surface_required"] is True
    assert result.payload["adapter_shared_contract"]["tooling_contract"]["explore_surface_required"] is True
    assert result.payload["adapter_shared_contract"]["operator_recovery_surface"]["default_recovery_lane"] == "approval_pause"
    assert result.payload["native_tool_usage"]["trace_count"] >= 1
    assert result.payload["comparative_benchmark"]["format"] == "agent_orchestrator.comparative_benchmark_summary.v1"
    assert result.payload["comparative_benchmark"]["shared_productization_contract_ready"] is True
    assert result.payload["comparative_benchmark"]["comparison_posture"]["status"] == "shared_productization_ready_but_daily_driver_proof_gap_remaining"
    assert result.payload["comparative_benchmark"]["planner_closure_posture"]["format"] == "agent_orchestrator.planner_closure_posture.v1"
    assert result.payload["comparative_benchmark"]["shared_contract_alignment"]["planner_closure_posture_ready"] is True
    assert result.payload["comparative_benchmark"]["external_comparison_harness_surface"]["format"] == "agent_orchestrator.external_comparison_harness_surface.v1"
    assert result.payload["comparative_benchmark"]["comparative_daily_driver_summary"]["format"] == "agent_orchestrator.comparative_daily_driver_summary.v1"
    assert result.payload["comparative_benchmark"]["comparative_completion_summary"]["format"] == "agent_orchestrator.comparative_completion_summary.v1"
    assert result.payload["comparative_benchmark"]["case_count"] == 1
    assert result.payload["comparative_benchmark"]["productization_case_count"] == 1
    assert result.payload["comparative_benchmark"]["daily_driver_main_path_ready_cases"] == 0
    assert result.payload["comparative_benchmark_digest"]["comparison_grade_status"] == "internal_productization_ready_but_repeatability_or_external_gap_remaining"
    assert result.payload["comparative_benchmark_digest"]["external_harness_status"] == "missing_authoritative_opencode_harness"
    assert result.payload["comparative_benchmark_digest"]["case_count"] == 1
    assert result.payload["comparative_benchmark_digest"]["productization_case_count"] == 1
    assert result.payload["comparative_benchmark_digest"]["daily_driver_main_path_ready_cases"] == 0
    assert "planner_closure_posture" in result.payload["comparative_benchmark_digest"]["shared_evidence_surface"]
    assert result.payload["session_continuity_contract"]["comparative_completion_summary"]["format"] == "agent_orchestrator.comparative_completion_summary.v1"
    assert result.payload["session_continuity_contract"]["comparative_completion_summary"]["completion_ready"] is False
    assert "comparative_completion_summary" in result.payload["session_continuity_contract"]["shared_evidence_surface"]
    assert result.payload["native_tool_productization_surface"]["readiness"]["glob_ready"] is True
    assert "workspace_index" in result.payload["shared_productization_surface"]["shared_evidence_surface"]
    assert result.payload["session_continuity_contract"]["session_productization_surface"]["autonomy_posture"]["resume_posture"] in {
        "fresh_entry",
        "same_task_resume",
        "approval_reentry",
    }
    assert result.payload["session_continuity_contract"]["long_horizon_posture"]["resume_posture"] in {
        "fresh_entry",
        "same_task_resume",
        "approval_reentry",
    }
    assert result.payload["session_continuity_contract"]["program_continuity"]["repo_task_acceptance_ready"] is False
    assert result.payload["session_continuity_contract"]["program_continuity"]["complex_repo_task_acceptance_ready"] is False
    assert result.payload["session_continuity_contract"]["program_continuity"]["long_chain_native_first_ready"] is False
    assert result.payload["session_continuity_contract"]["program_continuity"]["closure_strength"] == "runtime_closure_only"
    assert result.payload["session_continuity_contract"]["daily_driver_readiness"]["tool_surface_ready"] is True
    assert result.payload["session_continuity_contract"]["daily_driver_readiness"]["planner_ready"] is True
    assert result.payload["session_continuity_contract"]["daily_driver_readiness"]["session_ready"] is True
    assert result.payload["session_continuity_contract"]["daily_driver_readiness"]["adapter_ready"] is True
    assert result.payload["session_continuity_contract"]["daily_driver_readiness"]["shared_productization_ready"] is True
    assert result.payload["session_continuity_contract"]["daily_driver_readiness"]["long_chain_task_ready"] is False
    assert result.payload["session_continuity_contract"]["daily_driver_readiness"]["daily_driver_main_path_ready"] is False
    assert result.payload["session_continuity_contract"]["daily_driver_readiness"]["open_product_gap"] == "long_chain_repo_closure_not_yet_proven"


def test_compaction_state_uses_llm_summarization_when_transport_is_available(monkeypatch) -> None:
    monkeypatch.setenv("AO_SLOTFILL_API_KEY", "secret-key")
    monkeypatch.setenv("AO_SLOTFILL_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("AO_SLOTFILL_MODEL", "gpt-test")

    step = runtime_module.ExecutionStep(
        step_id="turn:verify",
        title="Verify",
        kind="verification",
        status="completed",
        observations=[
            runtime_module.ObservationRecord(
                observation_id=f"obs-{index}",
                kind="verification",
                summary=f"Observation {index}",
                source="verify_loop",
                payload={"stdout": f"log-{index}", "stderr": ""},
            )
            for index in range(10)
        ],
    )

    def fake_transport(request_url: str, payload: dict[str, object], headers: dict[str, str], timeout_seconds: int) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({"summary": "LLM summarized the earliest verification history into a compact digest."})
                    }
                }
            ]
        }

    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        summarizer_transport=fake_transport,
    )

    state = runtime_module._compaction_state(
        runtime,
        request=ExecutionRequest(
            requirement="Verify many files.",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
        ),
        steps=[step],
        context_selection={"deterministic": {"selected_items": []}, "retrieval": {"selected_memory_count": 0}},
    )

    assert state["stage"] == "summarization_ready"
    assert state["summarization_triggered"] is True
    assert state["summarization_source"] == "llm"
    assert state["summarization_summary"] == "LLM summarized the earliest verification history into a compact digest."


def test_isolate_runtime_context_reduces_broad_context() -> None:
    state = runtime_module._isolate_runtime_context(
        request=ExecutionRequest(
            requirement="Investigate several runtime paths across multiple files.",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
        ),
        context_selection={
            "model_driven": {
                "selected_items": ["memory:a", "memory:b", "memory:c"],
            }
        },
        edit_intent={
            "target_paths": ["a.py", "b.py", "c.py", "d.py"],
            "patch_plan": [
                "Inspect a.py",
                "Inspect b.py",
                "Inspect c.py",
                "Inspect d.py",
                "Inspect e.py",
            ],
        },
    )

    assert state.applied is True
    assert state.strategy == "subtask_digest"
    assert state.output_target_count == 3
    assert state.output_patch_plan_count == 3
    assert len(state.digest["target_focus"]) == 3


def test_coding_agent_runtime_surfaces_isolation_state_in_payload_and_scratchpad(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AO_SLOTFILL_API_KEY", "secret-key")
    monkeypatch.setenv("AO_SLOTFILL_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("AO_SLOTFILL_MODEL", "gpt-test")

    memory_root = tmp_path / "memory"
    store = MemoryStore(memory_root)
    stored_ids: list[str] = []
    for index in range(5):
        record = store.append(
            namespace="coding_agent",
            session_id="agent-session-isolate",
            record_type=f"memory_note_{index}",
            summary=f"Relevant memory note {index} about broad CLI investigation.",
            provider="coding_agent",
            payload={"index": index},
            freshness="fresh",
        )
        stored_ids.append(record.id)

    def fake_transport(request_url: str, payload: dict[str, object], headers: dict[str, str], timeout_seconds: int) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "selected_items": [f"memory:{stored_ids[0]}", f"memory:{stored_ids[1]}", f"memory:{stored_ids[2]}"],
                                "rationale": "Choose the most relevant memory-backed context candidates.",
                            }
                        )
                    }
                }
            ]
        }

    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        memory_store=store,
        scratchpad_store=ScratchpadStore(tmp_path / "scratchpads"),
        model_selector_transport=fake_transport,
    )
    request = ExecutionRequest(
        requirement='Append "print(\'bye\')" to src/a.py, src/b.py, src/c.py, and src/d.py after comparing several runtime paths.',
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-isolate",
        turn_id="turn-isolate",
        context_snapshot={"snapshot_id": "snapshot-isolate"},
        task_contract={
            "id": "task-isolate",
            "goal": "Investigate broad CLI behavior",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Investigate broad CLI behavior"],
            "outputs": ["isolation digest"],
            "acceptance_criteria": ["isolation recorded"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert "isolation_state" in result.payload
    assert result.payload["isolation_state"]["strategy"] in {"inline_context", "subtask_digest"}
    assert result.payload["isolation_state"]["reinjection_mode"] in {"full_inline_context", "digest_focus_subset"}
    assert isinstance(result.payload["isolation_state"]["reinjection_targets"], list)
    assert result.payload["scratchpad_entries"][0]["payload"]["isolation_state"]["strategy"] in {"inline_context", "subtask_digest"}
    assert result.payload["context_engineering_contract"]["isolate"]["reinjection_mode"] == result.payload["isolation_state"]["reinjection_mode"]
    assert result.payload["context_engineering_contract"]["isolate"]["reinjection_targets_ref"] == "payload.isolation_state.reinjection_targets"
    assert result.payload["context_engineering_contract"]["isolate"]["output_target_count"] == result.payload["isolation_state"]["output_target_count"]


def test_coding_agent_runtime_surfaces_compaction_summarization_state_in_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AO_SLOTFILL_API_KEY", "secret-key")
    monkeypatch.setenv("AO_SLOTFILL_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("AO_SLOTFILL_MODEL", "gpt-test")

    def fake_transport(request_url: str, payload: dict[str, object], headers: dict[str, str], timeout_seconds: int) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({"summary": "LLM summarized older execution history for compact context reuse."})
                    }
                }
            ]
        }

    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        summarizer_transport=fake_transport,
    )
    step = runtime_module.ExecutionStep(
        step_id="turn:verify",
        title="Verify",
        kind="verification",
        status="completed",
        observations=[
            runtime_module.ObservationRecord(
                observation_id=f"obs-{index}",
                kind="verification",
                summary=f"Observation {index}",
                source="verify_loop",
                payload={"stdout": f"log-{index}", "stderr": ""},
            )
            for index in range(10)
        ],
    )

    state = runtime_module._compaction_state(
        runtime,
        request=ExecutionRequest(
            requirement="Verify many files.",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
        ),
        steps=[step],
        context_selection={"deterministic": {"selected_items": []}, "retrieval": {"selected_memory_count": 0}},
    )

    assert state["summarization_source"] == "llm"
    assert state["summarization_summary"] == "LLM summarized older execution history for compact context reuse."


def test_structured_observation_records_trim_and_deduplicate_payloads() -> None:
    long_stdout = ("line\n" * 300) + "done"
    step = runtime_module.ExecutionStep(
        step_id="turn:verify",
        title="Verify",
        kind="verification",
        status="completed",
        observations=[
            runtime_module.ObservationRecord(
                observation_id="obs-1",
                kind="verification",
                summary="Verification result captured for the final runtime attempt.\n\n",
                source="verify_loop",
                payload={"stdout": long_stdout, "logs": ["same", "same", "different"], "status": "passed"},
            ),
            runtime_module.ObservationRecord(
                observation_id="obs-2",
                kind="verification",
                summary="Verification result captured for the final runtime attempt.\n\n",
                source="verify_loop",
                payload={"stdout": long_stdout, "logs": ["same", "same", "different"], "status": "passed"},
            ),
        ],
    )

    records = runtime_module._structured_observation_records(steps=[step])

    assert len(records) == 2
    assert records[0]["payload"]["stdout"].endswith("...<trimmed>")
    assert records[0]["payload"]["logs"] == ["same", "different"]
    assert records[0]["deduplicated"] is False
    assert records[1]["deduplicated"] is True


def test_coding_agent_runtime_can_apply_bounded_append_edit(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    request = ExecutionRequest(
        requirement='Append "print(\'bye\')" to note.py',
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-4",
        turn_id="turn-4",
        context_snapshot={"snapshot_id": "snapshot-4"},
        task_contract={
            "id": "task-4",
            "goal": "Append a line",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Append a line"],
            "outputs": ["applied patch"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "low",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.accepted is True
    assert result.payload["applied_change_count"] == 1
    assert result.payload["applied_changes"][0]["status"] == "applied"
    assert result.payload["applied_changes"][0]["preview"]["changed"] is True
    assert "diff_preview" in [
        item["tool"]
        for item in result.payload["native_tool_trace"]["trace"]
        if isinstance(item, dict) and isinstance(item.get("tool"), str)
    ]
    assert result.payload["execution_steps"][1]["actions"][1]["requires_approval"] is True
    assert "print('bye')" in target.read_text(encoding="utf-8")


def test_coding_agent_runtime_blocks_when_bounded_replace_cannot_apply(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    request = ExecutionRequest(
        requirement='Replace "missing" with "updated" in note.py',
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-5",
        turn_id="turn-5",
        context_snapshot={"snapshot_id": "snapshot-5"},
        task_contract={
            "id": "task-5",
            "goal": "Replace a missing string",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Replace a missing string"],
            "outputs": ["applied patch"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "low",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.accepted is False
    assert result.status == "blocked"
    assert result.payload["applied_change_count"] == 0
    assert result.payload["applied_changes"][0]["status"] == "failed"


def test_coding_agent_runtime_surfaces_edit_boundary_block_in_selection_trace(tmp_path) -> None:
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    request = ExecutionRequest(
        requirement='Append "print(\'escape\')" to ../escape.py',
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-5b",
        turn_id="turn-5b",
        context_snapshot={"snapshot_id": "snapshot-5b"},
        task_contract={
            "id": "task-5b",
            "goal": "Attempt to write outside workspace",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Attempt to write outside workspace"],
            "outputs": ["blocked governed edit"],
            "acceptance_criteria": ["Workspace boundary enforced"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.status == "blocked"
    assert result.accepted is False
    assert result.payload["pending_approval"] is None
    assert result.payload["stage_selection_trace"][1]["stage"] == "edit"
    assert result.payload["stage_selection_trace"][1]["outcome"] == "block"
    assert result.payload["next_stage_proposals"][1]["current_stage"] == "edit"
    assert result.payload["next_stage_proposals"][1]["disposition"] == "advance"
    assert result.payload["next_stage_proposals"][1]["proposed_stage"] == "verify"
    assert result.payload["next_stage_proposals"][1]["selected_candidate_id"] == "edit_to_verify"
    assert result.payload["action_selection_trace"][0]["stage"] == "edit"
    assert result.payload["action_selection_trace"][0]["action_type"] == "block"
    assert result.payload["action_selection_trace"][0]["source"] == "boundary_policy"
    assert result.payload["action_selection_trace"][0]["selected"]["path"] == "../escape.py"
    assert result.payload["action_selection_trace"][0]["planner_context"]["operation_paths"] == ["../escape.py"]
    assert result.payload["repair_summary"]["recovery_recommendation"]["reason"] == "boundary_policy"


def test_coding_agent_runtime_pauses_at_explore_when_route_requires_clarify() -> None:
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    route = TaskRouterResult(
        task_kind=TaskKind.GENERAL_CODING,
        clarify_policy=ClarifyPolicy.DEEP,
        execution_mode=ExecutionMode.CODING_AGENT,
        ambiguity_level="medium",
        risk_level="high",
        scope_confidence="medium",
        needs_repo_context=True,
        requires_human_confirmation=False,
        native_coverage_class="bounded_internal_repo_task",
        planner_intent={
            "version": "agent_orchestrator.route_planner_intent.v1",
            "explore": True,
            "clarify": True,
            "edit": True,
            "verify": True,
            "pause": True,
            "handoff": False,
            "fallback": False,
            "native_first": True,
            "priority": ["clarify", "explore", "edit", "verify"],
        },
        reasons=["clarify-first route"],
    )
    request = ExecutionRequest(
        requirement="Refactor auth integration safely.",
        route=route,
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-clarify",
        turn_id="turn-clarify",
        context_snapshot={"snapshot_id": "snapshot-clarify"},
        task_contract={
            "id": "task-clarify",
            "goal": "Refactor auth integration safely",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Refactor auth integration safely"],
            "outputs": ["clarified execution boundary"],
            "acceptance_criteria": ["Clarification captured before edit"],
            "risk_level": "high",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.status == "blocked"
    assert result.accepted is False
    assert result.payload["planner_context_trace"][0]["route_planner_intent"]["clarify"] is True
    assert result.payload["action_selection_trace"][0]["stage"] == "explore"
    assert result.payload["action_selection_trace"][0]["action_type"] == "pause"
    assert result.payload["action_selection_trace"][0]["source"] == "planner_control_surface"
    assert result.payload["stage_selection_trace"][0]["stage"] == "explore"
    assert result.payload["stage_selection_trace"][0]["outcome"] == "pause"
    assert result.payload["repair_summary"]["recovery_recommendation"]["action"] == "clarify_scope"
    assert [
        item["action"]
        for item in result.payload["repair_summary"]["recovery_recommendation"]["planner_governed_alternatives"]
    ] == ["clarify_scope", "handoff_external"]
    assert "alternatives=clarify_scope,handoff_external" in result.payload["compressed_context"]["latest_recovery_hint"]
    assert [
        item["action"]
        for item in result.payload["session_continuity_contract"]["session_productization_surface"]["operator_continuity"]["planner_governed_alternatives"]
    ] == ["clarify_scope", "handoff_external"]


def test_coding_agent_runtime_blocks_at_explore_for_route_handoff() -> None:
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    route = TaskRouterResult(
        task_kind=TaskKind.MIGRATION,
        clarify_policy=ClarifyPolicy.DEEP,
        execution_mode=ExecutionMode.CODING_AGENT,
        ambiguity_level="medium",
        risk_level="high",
        scope_confidence="medium",
        needs_repo_context=True,
        requires_human_confirmation=True,
        default_path="external",
        operating_boundary="external_preferred",
        handoff_reason_code="risk_exceeds_native_bounded_path",
        native_coverage_class="bounded_internal_repo_task",
        planner_intent={
            "version": "agent_orchestrator.route_planner_intent.v1",
            "explore": True,
            "clarify": False,
            "edit": False,
            "verify": False,
            "pause": True,
            "handoff": True,
            "fallback": False,
            "native_first": False,
            "priority": ["handoff", "pause"],
        },
        reasons=["handoff route"],
    )
    request = ExecutionRequest(
        requirement="Fix the auth payment permission flow in the database migration path.",
        route=route,
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-handoff",
        turn_id="turn-handoff",
        context_snapshot={"snapshot_id": "snapshot-handoff"},
        task_contract={
            "id": "task-handoff",
            "goal": "Fix auth payment migration flow",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Fix auth payment migration flow"],
            "outputs": ["governed handoff boundary"],
            "acceptance_criteria": ["High-risk path does not continue natively"],
            "risk_level": "high",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.status == "blocked"
    assert result.accepted is False
    assert [item["stage"] for item in result.payload["stage_selection_trace"]] == ["explore"]
    assert result.payload["action_selection_trace"][0]["stage"] == "explore"
    assert result.payload["action_selection_trace"][0]["action_type"] == "handoff"
    assert result.payload["action_selection_trace"][0]["source"] == "planner_control_surface"
    assert result.payload["repair_summary"]["recovery_recommendation"]["action"] == "handoff_external"
    assert [
        item["action"]
        for item in result.payload["repair_summary"]["recovery_recommendation"]["planner_governed_alternatives"]
    ] == ["handoff_external", "approval_pause"]


def test_coding_agent_runtime_uses_native_planner_control_surface_for_clarify_pause() -> None:
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    route = TaskRouterResult(
        task_kind=TaskKind.DIRECT_FIX,
        clarify_policy=ClarifyPolicy.LIGHT,
        execution_mode=ExecutionMode.CODING_AGENT,
        ambiguity_level="low",
        risk_level="medium",
        scope_confidence="high",
        needs_repo_context=True,
        requires_human_confirmation=False,
        native_coverage_class="bounded_internal_repo_task",
        reasons=["planner-driven clarify pause"],
    )
    request = ExecutionRequest(
        requirement="Refactor auth integration safely.",
        route=route,
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-planner-clarify",
        turn_id="turn-planner-clarify",
        context_snapshot={"snapshot_id": "snapshot-planner-clarify"},
        task_contract={
            "id": "task-planner-clarify",
            "goal": "Refactor auth integration safely",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Refactor auth integration safely"],
            "outputs": ["clarified execution boundary"],
            "acceptance_criteria": ["Clarification captured before edit"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
            "unknown_slots": ["target_module"],
        },
    )

    result = runtime.run(request)

    assert result.status == "blocked"
    assert result.accepted is False
    assert result.payload["strategy_summary"]["planner_family"] == "native"
    assert result.payload["strategy_summary"]["planner_actions"][0] == "clarify"
    assert result.payload["planner_context_trace"][0]["planner_actions"][0] == "clarify"
    assert result.payload["action_selection_trace"][0]["stage"] == "explore"
    assert result.payload["action_selection_trace"][0]["action_type"] == "pause"
    assert result.payload["action_selection_trace"][0]["source"] == "planner_control_surface"
    assert result.payload["stage_selection_trace"][0]["outcome"] == "pause"


def test_edit_next_stage_candidates_respect_planner_contract_when_verify_not_selected() -> None:
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="edit",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["note.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind="edit_intent",
        action_feasibility="ready_to_apply",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
        planner_actions=["edit"],
        control_surface={"continue_native": True, "clarify": False, "handoff": False, "fallback": False},
    )

    candidates = runtime_module._edit_next_stage_candidates(planner_context)

    assert [candidate.candidate_id for candidate in candidates] == [
        "edit_stop_completed",
        "edit_stop_completed",
    ]


def test_verify_stage_strategy_respects_planner_contract_when_verify_not_selected() -> None:
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="verify",
        resume_kind="approval_resume",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["note.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
        latest_observation_kind="verification",
        action_feasibility="ready_to_verify",
        approval_required=False,
        approval_resolved=True,
        pending_approval_stage=None,
        applied_change_count=1,
        recent_observation_count=1,
        verification_status="passed",
        repair_outcome="passed",
        planner_actions=["edit"],
        control_surface={"continue_native": True, "pause": False, "handoff": False, "fallback": False},
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="verify",
        applied_changes=[],
        recent_observations=[],
        final_verification={"status": "passed", "command": ["python3", "-m", "compileall", "note.py"]},
        repair_summary={},
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
    )
    strategy = runtime_module._verify_stage_strategy()

    decision = strategy.next_stage_decision(
        planner_context=planner_context,
        resume_state=resume_state,
    )
    selection = runtime_module._select_verify_action(planner_context)

    assert decision.selected_candidate.candidate_id == "verify_complete_from_history"
    assert selection.action_type == "complete"
    assert selection.source == "planner_control_surface"


def test_action_executor_applies_bounded_file_mutation(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")
    executor = ActionExecutor(workspace_root=tmp_path)

    result = executor.execute(
        ActionRequest(
            action_id="edit-apply",
            action_type="file_mutation",
            description="Append one line to the target file.",
            parameters={
                "operations": [
                    {
                        "kind": "append",
                        "path": "note.py",
                        "content": "print('bye')",
                    }
                ]
            },
            risk_level="medium",
            requires_approval=True,
        )
    )

    assert result.status == "completed"
    assert result.payload["applied_changes"][0]["status"] == "applied"
    assert result.payload["applied_changes"][0]["preview"]["after_preview"].endswith("print('bye')")
    assert "print('bye')" in target.read_text(encoding="utf-8")


def test_action_executor_applies_insert_and_delete_mutations_with_preview(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    executor = ActionExecutor(workspace_root=tmp_path)

    result = executor.execute(
        ActionRequest(
            action_id="edit-structured",
            action_type="file_mutation",
            description="Insert before and delete a bounded line.",
            parameters={
                "operations": [
                    {
                        "kind": "insert_before",
                        "path": "note.py",
                        "anchor": "beta",
                        "content": "inserted",
                    },
                    {
                        "kind": "delete",
                        "path": "note.py",
                        "old": "gamma\n",
                    },
                ]
            },
            risk_level="medium",
            requires_approval=True,
        )
    )

    assert result.status == "completed"
    assert [item["operation"] for item in result.payload["applied_changes"]] == ["insert_before", "delete"]
    assert all(item["preview"]["changed"] is True for item in result.payload["applied_changes"])
    assert target.read_text(encoding="utf-8") == "alpha\ninserted\nbeta\n"


def test_action_executor_runs_bounded_command(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")
    executor = ActionExecutor(workspace_root=tmp_path)

    result = executor.execute(
        ActionRequest(
            action_id="verify-runtime",
            action_type="run_command",
            description="Compile the target file.",
            parameters={"command": ["python3", "-m", "compileall", "note.py"]},
            risk_level="medium",
            requires_approval=True,
        )
    )

    assert result.status == "passed"
    assert result.payload["command"] == ["python3", "-m", "compileall", "note.py"]
    assert result.payload["exit_code"] == 0


def test_action_executor_blocks_file_mutation_outside_workspace(tmp_path) -> None:
    executor = ActionExecutor(workspace_root=tmp_path)

    result = executor.execute(
        ActionRequest(
            action_id="edit-apply",
            action_type="file_mutation",
            description="Attempt to write outside the workspace root.",
            parameters={
                "operations": [
                    {
                        "kind": "append",
                        "path": "../escape.py",
                        "content": "print('escape')",
                    }
                ]
            },
            risk_level="medium",
            requires_approval=True,
        )
    )

    assert result.status == "blocked"
    assert result.error == "workspace_boundary_violation:../escape.py"
    assert result.payload["governance"]["boundary_policy"] == "workspace_root_only"


def test_coding_agent_runtime_surfaces_governance_summary(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    request = ExecutionRequest(
        requirement='Replace "hello" with "bye" in note.py',
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-6",
        turn_id="turn-6",
        context_snapshot={"snapshot_id": "snapshot-6"},
        task_contract={
            "id": "task-6",
            "goal": "Replace a string",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Replace a string"],
            "outputs": ["applied patch"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.payload["governance_summary"]["workspace_boundary_policy"] == "workspace_root_only"
    assert result.payload["governance_summary"]["approval_required_action_count"] >= 2
    assert result.payload["governance_summary"]["high_risk_action_count"] >= 2
    assert result.payload["execution_steps"][1]["results"][1]["payload"]["governance"]["risk_level"] == "high"


def test_coding_agent_runtime_blocks_on_edit_approval_and_persists_item(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    approvals_root = tmp_path / "approvals"
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        enforce_approvals=True,
        approvals_root=approvals_root,
    )
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    request = ExecutionRequest(
        requirement='Append "print(\'bye\')" to note.py',
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-7",
        turn_id="turn-7",
        context_snapshot={"snapshot_id": "snapshot-7"},
        task_contract={
            "id": "task-7",
            "goal": "Append a line",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Append a line"],
            "outputs": ["approval-gated patch"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.status == "blocked"
    assert result.accepted is False
    assert result.payload["pending_approval"]["stage"] == "edit"
    assert result.payload["repair_summary"]["outcome"] == "awaiting_approval"
    assert result.payload["execution_steps"][1]["status"] == "pending"
    assert result.payload["execution_steps"][1]["approval"]["status"] == "pending"
    assert result.payload["planner_context_trace"][1]["approval_required"] is True
    assert result.payload["planner_context_trace"][1]["approval_resolved"] is False
    assert result.payload["planner_context_trace"][1]["action_feasibility"] == "ready_to_mutate"
    assert result.payload["next_stage_proposals"][1]["disposition"] == "pause"
    assert result.payload["next_stage_proposals"][1]["proposed_stage"] == "edit"
    assert result.payload["next_stage_proposals"][1]["selected_candidate_id"] == "edit_wait_approval"
    assert len(result.payload["next_stage_proposals"][1]["candidates"]) >= 2
    assert result.payload["stage_selection_trace"][1]["outcome"] == "pause"
    assert result.payload["action_selection_trace"][0]["action_type"] == "pause"
    assert result.payload["action_selection_trace"][0]["source"] == "approval_policy"
    assert result.payload["step_decisions"][1]["disposition"] == "pause"
    assert result.payload["next_step_contract"]["current_disposition"] == "pause"
    assert result.payload["next_step_contract"]["current_step_kind"] == "edit_execution"
    assert result.payload["next_step_contract"]["context_engineering_refs"]["required_surfaces"] == [
        "write",
        "select",
        "structured_observation",
        "isolate",
    ]
    assert result.payload["step_loop_contract"]["status"] == "blocked"
    assert result.payload["step_loop_contract"]["current_disposition"] == "pause"
    assert result.payload["step_loop_contract"]["context_engineering_refs"]["required_surfaces"] == [
        "write",
        "select",
        "structured_observation",
        "isolate",
    ]
    assert result.payload["step_loop_contract"]["resume_supported"] is True
    assert ApprovalStore(approvals_root).list_all()[0].scope == "edit_execution"
    assert "print('bye')" not in target.read_text(encoding="utf-8")


def test_coding_agent_runtime_blocks_on_verification_approval_when_enabled(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    approvals_root = tmp_path / "approvals"
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        enforce_approvals=True,
        approvals_root=approvals_root,
    )
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    request = ExecutionRequest(
        requirement="Inspect note.py and report what needs fixing.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-8",
        turn_id="turn-8",
        context_snapshot={"snapshot_id": "snapshot-8"},
        task_contract={
            "id": "task-8",
            "goal": "Inspect a file",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Inspect a file"],
            "outputs": ["approval-gated verification"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)

    assert result.status == "blocked"
    assert result.payload["pending_approval"]["stage"] == "verify"
    assert result.payload["execution_steps"][2]["status"] == "pending"
    assert result.payload["execution_steps"][2]["approval"]["status"] == "pending"
    assert result.payload["planner_context_trace"][2]["approval_required"] is True
    assert result.payload["planner_context_trace"][2]["approval_resolved"] is False
    assert result.payload["planner_context_trace"][2]["action_feasibility"] == "ready_to_verify"
    assert result.payload["next_stage_proposals"][2]["disposition"] == "pause"
    assert result.payload["next_stage_proposals"][2]["proposed_stage"] == "verify"
    assert result.payload["next_stage_proposals"][2]["selected_candidate_id"] == "verify_wait_approval"
    assert len(result.payload["next_stage_proposals"][2]["candidates"]) >= 2
    assert result.payload["stage_selection_trace"][2]["outcome"] == "pause"
    assert result.payload["action_selection_trace"][-1]["action_type"] == "pause"
    assert result.payload["action_selection_trace"][-1]["source"] == "approval_policy"
    assert result.payload["step_decisions"][2]["disposition"] == "pause"
    assert result.payload["next_step_contract"]["current_disposition"] == "pause"
    assert result.payload["next_step_contract"]["current_step_kind"] == "verification"
    assert result.payload["next_step_contract"]["context_engineering_refs"]["required_surfaces"] == [
        "select",
        "structured_observation",
        "compact",
        "resume_continuity",
    ]
    items = ApprovalStore(approvals_root).list_all()
    assert items[0].scope == "verification"


def test_coding_agent_runtime_can_resume_after_edit_approval_is_approved(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    approvals_root = tmp_path / "approvals"
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        enforce_approvals=True,
        approvals_root=approvals_root,
    )
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    initial_request = ExecutionRequest(
        requirement='Append "print(\'bye\')" to note.py',
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-9",
        turn_id="turn-9",
        context_snapshot={"snapshot_id": "snapshot-9"},
        task_contract={
            "id": "task-9",
            "goal": "Append a line",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Append a line"],
            "outputs": ["resume-after-approval"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    first = runtime.run(initial_request)
    approval_id = first.payload["pending_approval"]["approval_id"]
    resolve_approval_item(
        approval_id,
        status="approved",
        reason="Human approved edit execution",
        project_root=tmp_path,
        approvals_root=approvals_root,
    )

    resumed = runtime.run(
        ExecutionRequest(
            requirement=initial_request.requirement,
            route=initial_request.route,
            runtime_name=initial_request.runtime_name,
            mode=initial_request.mode,
            session_id=initial_request.session_id,
            turn_id=initial_request.turn_id,
            context_snapshot=initial_request.context_snapshot,
            task_contract=initial_request.task_contract,
            session_metadata={"approved_approval_id": approval_id},
            resume_kind="approval_resume",
        )
    )

    assert resumed.payload["pending_approval"]["stage"] == "verify"
    assert resumed.payload["applied_change_count"] == 1
    assert "print('bye')" in target.read_text(encoding="utf-8")


def test_coding_agent_runtime_can_resume_after_verification_approval_is_approved(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    approvals_root = tmp_path / "approvals"
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        enforce_approvals=True,
        approvals_root=approvals_root,
    )
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    initial_request = ExecutionRequest(
        requirement="Inspect note.py and report what needs fixing.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-10",
        turn_id="turn-10",
        context_snapshot={"snapshot_id": "snapshot-10"},
        task_contract={
            "id": "task-10",
            "goal": "Inspect a file",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Inspect a file"],
            "outputs": ["resume verification"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    first = runtime.run(initial_request)
    approval_id = first.payload["pending_approval"]["approval_id"]
    resolve_approval_item(
        approval_id,
        status="approved",
        reason="Human approved verification execution",
        project_root=tmp_path,
        approvals_root=approvals_root,
    )

    resumed = runtime.run(
        ExecutionRequest(
            requirement=initial_request.requirement,
            route=initial_request.route,
            runtime_name=initial_request.runtime_name,
            mode=initial_request.mode,
            session_id=initial_request.session_id,
            turn_id=initial_request.turn_id,
            context_snapshot=initial_request.context_snapshot,
            task_contract=initial_request.task_contract,
            session_metadata={"approved_approval_id": approval_id},
            resume_kind="approval_resume",
        )
    )

    assert resumed.status == "completed"
    assert resumed.accepted is True
    assert resumed.payload["pending_approval"] is None
    assert resumed.payload["verification"]["status"] == "passed"


def test_coding_agent_runtime_can_resume_from_persisted_resume_contract(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    approvals_root = tmp_path / "approvals"
    state_root = tmp_path / "execution-state"
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        enforce_approvals=True,
        approvals_root=approvals_root,
    )
    runtime.state_store.root = state_root
    runtime.state_store.__post_init__()
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    initial_request = ExecutionRequest(
        requirement="Inspect note.py and report what needs fixing.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-10b",
        turn_id="turn-10b",
        context_snapshot={"snapshot_id": "snapshot-10b"},
        task_contract={
            "id": "task-10b",
            "goal": "Inspect a file",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Inspect a file"],
            "outputs": ["resume verification from state"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    first = runtime.run(initial_request)
    approval_id = first.payload["pending_approval"]["approval_id"]
    resolve_approval_item(
        approval_id,
        status="approved",
        reason="Human approved verification execution",
        project_root=tmp_path,
        approvals_root=approvals_root,
    )

    resumed = runtime.run(
        ExecutionRequest(
            requirement=initial_request.requirement,
            route=initial_request.route,
            runtime_name=initial_request.runtime_name,
            mode=initial_request.mode,
            session_id=initial_request.session_id,
            turn_id=initial_request.turn_id,
            context_snapshot=initial_request.context_snapshot,
            task_contract=initial_request.task_contract,
            resume_kind="approval_resume",
        )
    )

    assert resumed.status == "completed"
    assert resumed.accepted is True
    assert resumed.payload["pending_approval"] is None
    assert resumed.payload["verification"]["status"] == "passed"
    assert resumed.payload["applied_change_count"] == 0


def test_coding_agent_runtime_resume_from_state_uses_persisted_contract(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    approvals_root = tmp_path / "approvals"
    state_root = tmp_path / "execution-state"
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        enforce_approvals=True,
        approvals_root=approvals_root,
    )
    runtime.state_store.root = state_root
    runtime.state_store.__post_init__()
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    initial_request = ExecutionRequest(
        requirement="Inspect note.py and report what needs fixing.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-10c",
        turn_id="turn-10c",
        context_snapshot={"snapshot_id": "snapshot-10c"},
        task_contract={
            "id": "task-10c",
            "goal": "Inspect a file",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Inspect a file"],
            "outputs": ["explicit resume from state"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    first = runtime.run(initial_request)
    approval_id = first.payload["pending_approval"]["approval_id"]
    resolve_approval_item(
        approval_id,
        status="approved",
        reason="Human approved verification execution",
        project_root=tmp_path,
        approvals_root=approvals_root,
    )

    resumed = runtime.resume_from_state(
        ExecutionRequest(
            requirement=initial_request.requirement,
            route=initial_request.route,
            runtime_name=initial_request.runtime_name,
            mode=initial_request.mode,
            session_id=initial_request.session_id,
            turn_id=initial_request.turn_id,
            context_snapshot=initial_request.context_snapshot,
            task_contract=initial_request.task_contract,
        )
    )

    assert resumed.status == "completed"
    assert resumed.accepted is True
    assert resumed.payload["pending_approval"] is None
    assert resumed.payload["verification"]["status"] == "passed"


def test_execution_resume_contract_round_trips_from_persisted_state(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    state_root = tmp_path / "execution-state"
    approvals_root = tmp_path / "approvals"
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        enforce_approvals=True,
        approvals_root=approvals_root,
    )
    runtime.state_store.root = state_root
    runtime.state_store.__post_init__()
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path

    result = runtime.run(
        ExecutionRequest(
            requirement="Inspect note.py and request approval before verification.",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-10d",
            turn_id="turn-10d",
            context_snapshot={"snapshot_id": "snapshot-10d"},
            task_contract={
                "id": "task-10d",
                "goal": "Inspect a file",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Inspect a file"],
                "outputs": ["resume contract"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    state = runtime.state_store.read(result.run_id or "")
    contract = ExecutionResumeContract.from_dict(state.get("resume_contract"))

    assert contract is not None
    assert contract.resume_supported is True
    assert contract.run_id == result.run_id
    assert contract.turn_id == "turn-10d"
    assert contract.current_stage == "verify"
    assert isinstance(contract.pending_approval, dict)
    assert contract.continuity_snapshot.get("format") == "agent_orchestrator.session_continuity_snapshot.v1"
    assert contract.program_posture.get("program_goal") == "Inspect a file"
    assert contract.native_tool_usage.get("trace_count", 0) >= 1
    assert contract.operator_posture_digest.get("format") == "agent_orchestrator.session_operator_posture_digest.v1"
    assert "workspace_index" in contract.shared_evidence_surface


def test_coding_agent_runtime_restores_applied_changes_for_verify_resume_from_state(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    approvals_root = tmp_path / "approvals"
    state_root = tmp_path / "execution-state"
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        enforce_approvals=True,
        approvals_root=approvals_root,
    )
    runtime.state_store.root = state_root
    runtime.state_store.__post_init__()
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path

    initial_request = ExecutionRequest(
        requirement='Append "print(\'bye\')" to note.py',
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-10e",
        turn_id="turn-10e",
        context_snapshot={"snapshot_id": "snapshot-10e"},
        task_contract={
            "id": "task-10e",
            "goal": "Append a line",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Append a line"],
            "outputs": ["restore applied changes on verify resume"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    first = runtime.run(initial_request)
    edit_approval_id = first.payload["pending_approval"]["approval_id"]
    resolve_approval_item(
        edit_approval_id,
        status="approved",
        reason="Human approved edit execution",
        project_root=tmp_path,
        approvals_root=approvals_root,
    )

    second = runtime.run(
        ExecutionRequest(
            requirement=initial_request.requirement,
            route=initial_request.route,
            runtime_name=initial_request.runtime_name,
            mode=initial_request.mode,
            session_id=initial_request.session_id,
            turn_id=initial_request.turn_id,
            context_snapshot=initial_request.context_snapshot,
            task_contract=initial_request.task_contract,
            resume_kind="approval_resume",
        )
    )
    assert second.payload["pending_approval"]["stage"] == "verify"

    verify_approval_id = second.payload["pending_approval"]["approval_id"]
    resolve_approval_item(
        verify_approval_id,
        status="approved",
        reason="Human approved verification execution",
        project_root=tmp_path,
        approvals_root=approvals_root,
    )

    resumed = runtime.run(
        ExecutionRequest(
            requirement=initial_request.requirement,
            route=initial_request.route,
            runtime_name=initial_request.runtime_name,
            mode=initial_request.mode,
            session_id=initial_request.session_id,
            turn_id=initial_request.turn_id,
            context_snapshot=initial_request.context_snapshot,
            task_contract=initial_request.task_contract,
            resume_kind="approval_resume",
        )
    )

    assert resumed.status == "completed"
    assert resumed.accepted is True
    assert resumed.payload["applied_change_count"] == 1
    assert resumed.payload["applied_changes"][0]["status"] == "applied"
    assert resumed.payload["resume_context"]["recent_observations"]
    assert resumed.payload["resume_context"]["repair_summary"]
    assert resumed.payload["verification"]["command"] == second.payload["resume_context"]["planned_verification_command"]
    assert any(
        "previously planned verification command" in note
        for attempt in resumed.payload["repair_summary"]["attempts"]
        for note in attempt.get("notes", [])
    )
    assert resumed.payload["action_selection_trace"][-1]["stage"] == "verify"
    assert resumed.payload["action_selection_trace"][-1]["source"] == "resume_context"
    assert resumed.payload["action_selection_trace"][-1]["planner_context"]["resume_kind"] == "approval_resume"
    assert resumed.payload["action_selection_trace"][-1]["planner_context"]["verification_command"] == second.payload["resume_context"]["planned_verification_command"]
    assert resumed.payload["planner_context_trace"][-1]["applied_change_count"] == 1
    assert resumed.payload["planner_context_trace"][-1]["recent_observation_count"] >= 1
    assert resumed.payload["next_step_contract"]["reason"].startswith("Resume context:")
    assert resumed.payload["compressed_context"]["latest_recovery_hint"].startswith("Resume context:")


def test_coding_agent_runtime_resume_uses_remaining_retry_budget_from_state(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    approvals_root = tmp_path / "approvals"
    state_root = tmp_path / "execution-state"
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        enforce_approvals=True,
        approvals_root=approvals_root,
    )
    runtime.state_store.root = state_root
    runtime.state_store.__post_init__()
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path

    class _CountingVerifier:
        def __init__(self) -> None:
            self.calls = 0

        def run(self, request, edit_intent, command_override=None):
            self.calls += 1
            return VerificationReport(
                status="failed",
                command=list(command_override or ["python3", "-m", "compileall", "note.py"]),
                exit_code=1,
                stdout="",
                stderr="still failing",
                failure_kind="nonzero_exit",
            )

    runtime.verify_loop.verifier = _CountingVerifier()
    runtime.verify_loop.retry_budget = 3

    initial_request = ExecutionRequest(
        requirement='Append "print(\'bye\')" to note.py',
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-10f",
        turn_id="turn-10f",
        context_snapshot={"snapshot_id": "snapshot-10f"},
        task_contract={
            "id": "task-10f",
            "goal": "Append a line",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Append a line"],
            "outputs": ["resume with remaining retry budget"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    first = runtime.run(initial_request)
    edit_approval_id = first.payload["pending_approval"]["approval_id"]
    resolve_approval_item(
        edit_approval_id,
        status="approved",
        reason="Human approved edit execution",
        project_root=tmp_path,
        approvals_root=approvals_root,
    )

    second = runtime.run(
        ExecutionRequest(
            requirement=initial_request.requirement,
            route=initial_request.route,
            runtime_name=initial_request.runtime_name,
            mode=initial_request.mode,
            session_id=initial_request.session_id,
            turn_id=initial_request.turn_id,
            context_snapshot=initial_request.context_snapshot,
            task_contract=initial_request.task_contract,
            resume_kind="approval_resume",
        )
    )
    assert second.payload["pending_approval"]["stage"] == "verify"

    verify_approval_id = second.payload["pending_approval"]["approval_id"]
    resolve_approval_item(
        verify_approval_id,
        status="approved",
        reason="Human approved verification execution",
        project_root=tmp_path,
        approvals_root=approvals_root,
    )

    state = runtime.state_store.read(second.run_id or "")
    state["result_summary"]["repair_summary"] = {
        "outcome": "failed",
        "attempt_count": 2,
        "retry_budget": 2,
        "attempts": [{"attempt_index": 0}, {"attempt_index": 1}],
        "recovery_recommendation": {"action": "human_review"},
    }
    state["resume_context"]["repair_summary"] = dict(state["result_summary"]["repair_summary"])
    runtime.state_store.write(second.run_id or "", state)

    resumed = runtime.run(
        ExecutionRequest(
            requirement=initial_request.requirement,
            route=initial_request.route,
            runtime_name=initial_request.runtime_name,
            mode=initial_request.mode,
            session_id=initial_request.session_id,
            turn_id=initial_request.turn_id,
            context_snapshot=initial_request.context_snapshot,
            task_contract=initial_request.task_contract,
            resume_kind="approval_resume",
        )
    )

    assert resumed.payload["repair_summary"]["retry_budget"] == 1
    assert runtime.verify_loop.verifier.calls == 2
    assert any(
        "remaining retry budget=1" in note
        for attempt in resumed.payload["repair_summary"]["attempts"]
        for note in attempt.get("notes", [])
    )


def test_coding_agent_runtime_resume_blocks_without_rerunning_verify_when_retry_budget_exhausted(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    state_root = tmp_path / "execution-state"
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.state_store.root = state_root
    runtime.state_store.__post_init__()
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path

    class _NeverRunVerifier:
        def __init__(self) -> None:
            self.calls = 0

        def run(self, request, edit_intent, command_override=None):
            self.calls += 1
            return VerificationReport(
                status="failed",
                command=list(command_override or ["python3", "-m", "compileall", "note.py"]),
                exit_code=1,
                stdout="",
                stderr="should not run",
                failure_kind="nonzero_exit",
            )

    runtime.verify_loop.verifier = _NeverRunVerifier()

    run_id = "coding-turn-10g"
    runtime.state_store.write(
        run_id,
        {
            "format": "agent_orchestrator.execution_state.v1",
            "runtime_name": "coding_agent",
            "session_id": "agent-session-10g",
            "turn_id": "turn-10g",
            "resume_kind": "approval_resume",
            "status": "blocked",
            "accepted": False,
            "current_stage": "verify",
            "current_step_id": "turn-10g:verify",
            "pending_approval": None,
            "step_statuses": [],
            "resume_contract": {
                "resume_kind": "approval_resume",
                "run_id": run_id,
                "session_id": "agent-session-10g",
                "turn_id": "turn-10g",
                "current_stage": "verify",
                "current_step_id": "turn-10g:verify",
                "pending_approval": None,
                "resume_supported": True,
            },
            "execution_history_summary": {
                "objective": "Inspect note.py",
                "status": "blocked",
                "completed_steps": ["repo_exploration", "edit_execution"],
                "pending_steps": [],
                "blocked_steps": ["verification"],
                "pending_approval": None,
                "artifact_count": 0,
                "artifact_ids": [],
                "latest_recovery_hint": "Verification failed previously.",
            },
            "compressed_context": {},
            "next_step_contract": {},
            "step_decisions": [],
            "resume_context": {
                "resume_kind": "approval_resume",
                "recent_observations": [{"kind": "verification", "summary": "previous verify failed"}],
                "verification": {
                    "status": "failed",
                    "command": ["python3", "-m", "compileall", "note.py"],
                },
                "repair_summary": {
                    "outcome": "failed",
                    "attempt_count": 2,
                    "retry_budget": 1,
                    "attempts": [{"attempt_index": 0}, {"attempt_index": 1}],
                    "recovery_recommendation": {"action": "human_review", "reason": "retry exhausted"},
                },
                "planned_verification_command": ["python3", "-m", "compileall", "note.py"],
            },
            "result_summary": {
                "applied_change_count": 0,
                "applied_changes": [],
                "verification": {
                    "status": "failed",
                    "command": ["python3", "-m", "compileall", "note.py"],
                },
                "repair_summary": {
                    "outcome": "failed",
                    "attempt_count": 2,
                    "retry_budget": 1,
                    "attempts": [{"attempt_index": 0}, {"attempt_index": 1}],
                    "recovery_recommendation": {"action": "human_review", "reason": "retry exhausted"},
                },
                "recent_observations": [{"kind": "verification", "summary": "previous verify failed"}],
            },
        },
    )

    resumed = runtime.resume_from_state(
        ExecutionRequest(
            requirement="Inspect note.py",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-10g",
            turn_id="turn-10g",
            context_snapshot={"snapshot_id": "snapshot-10g"},
            task_contract={
                "id": "task-10g",
                "goal": "Inspect a file",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Inspect a file"],
                "outputs": ["skip verify rerun when exhausted"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    assert resumed.status == "blocked"
    assert resumed.accepted is False
    assert runtime.verify_loop.verifier.calls == 0
    assert resumed.payload["stage_selection_trace"][-1]["stage"] == "verify"
    assert resumed.payload["stage_selection_trace"][-1]["outcome"] == "block"
    assert resumed.payload["next_stage_proposals"][-1]["current_stage"] == "verify"
    assert resumed.payload["next_stage_proposals"][-1]["disposition"] == "block"
    assert resumed.payload["next_stage_proposals"][-1]["proposed_stage"] == "completed"
    assert resumed.payload["next_stage_proposals"][-1]["selected_candidate_id"] == "verify_block_completed"
    assert resumed.payload["planner_context_trace"][-1]["verification_status"] == "failed"
    assert resumed.payload["planner_context_trace"][-1]["repair_outcome"] == "failed"
    assert resumed.payload["action_selection_trace"][-1]["stage"] == "verify"
    assert resumed.payload["action_selection_trace"][-1]["action_type"] == "block"
    assert resumed.payload["action_selection_trace"][-1]["source"] == "exhausted_recovery"
    assert resumed.payload["action_selection_trace"][-1]["planner_context"]["remaining_retry_budget"] == 0


def test_next_stage_candidate_selection_prefers_completed_when_verification_history_is_satisfied() -> None:
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="verify",
        resume_kind="approval_resume",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["note.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
        latest_observation_kind="verification",
        action_feasibility="ready_to_verify",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=1,
        recent_observation_count=2,
        verification_status="passed",
        repair_outcome="passed",
    )
    candidates = [
        runtime_module._KernelNextStageCandidate(
            candidate_id="verify_retry_same_stage",
            stage="verify",
            disposition="advance",
            reason="Retry verification again.",
        ),
        runtime_module._KernelNextStageCandidate(
            candidate_id="verify_complete_from_history",
            stage="completed",
            disposition="complete",
            reason="Verification is already satisfied in continuation state.",
        ),
    ]

    selected = runtime_module._select_next_stage_candidate(
        candidates,
        planner_context=planner_context,
        stage_strategy=runtime_module._verify_stage_strategy(),
    )

    assert selected.candidate_id == "verify_complete_from_history"


def test_next_stage_candidate_selection_prefers_completed_for_low_risk_prepare_only_edit_with_history() -> None:
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="edit",
        resume_kind="fresh",
        route_risk_level="low",
        edit_mode="report_first",
        operation_count=0,
        operation_paths=[],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind="edit_intent",
        action_feasibility="prepare_only",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=1,
        verification_status=None,
        repair_outcome=None,
    )
    candidates = runtime_module._edit_next_stage_candidates(planner_context)

    selected = runtime_module._select_next_stage_candidate(
        candidates,
        planner_context=planner_context,
        stage_strategy=runtime_module._edit_stage_strategy(),
    )

    assert [candidate.candidate_id for candidate in candidates] == [
        "edit_to_verify",
        "edit_complete_after_prepare",
    ]
    assert selected.candidate_id == "edit_complete_after_prepare"


def test_edit_next_stage_candidates_preserve_default_ids_for_direct_apply_without_history() -> None:
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="edit",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["note.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind="edit_intent",
        action_feasibility="ready_to_apply",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
    )

    candidates = runtime_module._edit_next_stage_candidates(planner_context)

    assert [candidate.candidate_id for candidate in candidates] == [
        "edit_to_verify",
        "edit_stop_completed",
    ]


def test_next_stage_candidate_selection_prefers_completed_for_low_risk_explore_with_history() -> None:
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="explore",
        resume_kind="fresh",
        route_risk_level="low",
        edit_mode="report_first",
        operation_count=0,
        operation_paths=[],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind="repo_report",
        action_feasibility="advance",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=1,
        verification_status=None,
        repair_outcome=None,
    )
    candidates = runtime_module._explore_next_stage_candidates(planner_context)

    selected = runtime_module._select_next_stage_candidate(
        candidates,
        planner_context=planner_context,
        stage_strategy=runtime_module._explore_stage_strategy(),
    )

    assert [candidate.candidate_id for candidate in candidates] == [
        "explore_to_edit",
        "explore_complete_from_context",
    ]
    assert selected.candidate_id == "explore_complete_from_context"


def test_build_next_stage_candidates_routes_explore_through_shared_entrypoint() -> None:
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="explore",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="report_first",
        operation_count=0,
        operation_paths=[],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind=None,
        action_feasibility="advance",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="explore",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )

    candidates = runtime_module._build_next_stage_candidates(
        stage_strategy=runtime_module._explore_stage_strategy(),
        stage_cursor="explore",
        planner_context=planner_context,
        resume_state=resume_state,
    )

    assert [candidate.candidate_id for candidate in candidates] == ["explore_to_edit", "explore_stop_completed"]


def test_explore_next_stage_proposal_carries_planner_governed_alternatives() -> None:
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="explore",
        resume_kind="fresh",
        route_risk_level="high",
        edit_mode="report_first",
        operation_count=0,
        operation_paths=[],
        target_paths=["src/auth.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind="repo_report",
        action_feasibility="advance",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=1,
        verification_status=None,
        repair_outcome=None,
        planner_actions=["explore", "edit", "verify"],
        control_surface={"continue_native": True, "clarify": False, "pause": False, "handoff": False, "fallback": False},
        decision_evidence={
            "decision_candidate_evidence": [
                {"strategy": "explore_then_edit", "selected": True},
                {"strategy": "need_human_confirmation", "selected": False},
                {"strategy": "external_handoff", "selected": False},
            ]
        },
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="explore",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )
    strategy = runtime_module._explore_stage_strategy()

    proposal = strategy.propose_next_stage(
        current_stage="explore",
        planner_context=planner_context,
        resume_state=resume_state,
    )

    assert proposal.selected_candidate_id == "explore_to_edit"
    assert [candidate.candidate_id for candidate in proposal.candidates[:2]] == [
        "explore_to_edit",
        "explore_complete_from_context",
    ]
    assert [candidate.candidate_id for candidate in proposal.candidates[2:]] == [
        "planner_need_human_confirmation_pause",
        "planner_external_handoff_block",
    ]
    assert proposal.selection["candidate_count"] == 4
    assert proposal.selection["planner_governed_alternative_count"] == 2
    assert proposal.selection["planner_governed_alternatives"] == [
        "planner_need_human_confirmation_pause",
        "planner_external_handoff_block",
    ]


def test_next_stage_candidate_generator_falls_back_to_terminal_stage() -> None:
    generator = runtime_module._next_stage_candidate_generator(
        runtime_module._terminal_stage_strategy("completed")
    )
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="completed",
        resume_kind="fresh",
        route_risk_level="low",
        edit_mode="report_first",
        operation_count=0,
        operation_paths=[],
        target_paths=[],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind=None,
        action_feasibility="advance",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="completed",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )

    candidates = generator(planner_context, resume_state)

    assert [candidate.candidate_id for candidate in candidates] == ["completed_complete"]


def test_stage_strategy_exposes_verify_generation_and_ranking_capabilities() -> None:
    strategy = runtime_module._stage_strategy("verify")
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="verify",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["note.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
        latest_observation_kind="verification",
        action_feasibility="ready_to_verify",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=1,
        recent_observation_count=1,
        verification_status="passed",
        repair_outcome="passed",
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="verify",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
    )

    candidates = strategy.candidate_generator(planner_context, resume_state)

    assert strategy.ranking_enabled(planner_context) is True
    assert [candidate.candidate_id for candidate in candidates] == [
        "verify_complete_from_history",
        "verify_repeat_same_stage",
    ]


def test_stage_strategy_falls_back_to_terminal_strategy_for_completed_stage() -> None:
    strategy = runtime_module._stage_strategy("completed")
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="completed",
        resume_kind="fresh",
        route_risk_level="low",
        edit_mode="report_first",
        operation_count=0,
        operation_paths=[],
        target_paths=[],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind=None,
        action_feasibility="advance",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="completed",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )

    candidates = strategy.candidate_generator(planner_context, resume_state)

    assert strategy.ranking_enabled(planner_context) is False
    assert strategy.rank_adjustment(candidates[0], planner_context=planner_context) == 0
    assert [candidate.candidate_id for candidate in candidates] == ["completed_complete"]


def test_stage_strategy_can_build_next_stage_proposal_for_verify_history() -> None:
    strategy = runtime_module._stage_strategy("verify")
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="verify",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["note.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
        latest_observation_kind="verification",
        action_feasibility="ready_to_verify",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=1,
        recent_observation_count=1,
        verification_status="passed",
        repair_outcome="passed",
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="verify",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
    )

    proposal = strategy.propose_next_stage(
        current_stage="verify",
        planner_context=planner_context,
        resume_state=resume_state,
    )

    assert proposal.current_stage == "verify"
    assert proposal.proposed_stage == "completed"
    assert proposal.disposition == "complete"
    assert proposal.selected_candidate_id == "verify_complete_from_history"
    assert proposal.selection["ranking_enabled"] is True
    assert proposal.selection["selected_candidate_id"] == "verify_complete_from_history"


def test_stage_strategy_build_stage_plan_for_explore_uses_proposal_stage_selection() -> None:
    strategy = runtime_module._stage_strategy("explore")
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="explore",
        resume_kind="fresh",
        route_risk_level="low",
        edit_mode="report_first",
        operation_count=0,
        operation_paths=[],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind="repo_report",
        action_feasibility="advance",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=1,
        verification_status=None,
        repair_outcome=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="explore",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )

    plan = strategy.build_stage_plan(
        stage_cursor="explore",
        planner_context=planner_context,
        resume_state=resume_state,
    )

    assert plan.action_selection is None
    assert plan.stage_selection.outcome == "complete"
    assert plan.next_stage_proposal.selected_candidate_id == "explore_complete_from_context"


def test_stage_strategy_build_stage_plan_for_edit_uses_edit_stage_selection() -> None:
    strategy = runtime_module._stage_strategy("edit")
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="edit",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["../outside.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind="edit_intent",
        action_feasibility="ready_to_apply",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="edit",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )

    plan = strategy.build_stage_plan(
        stage_cursor="edit",
        planner_context=planner_context,
        resume_state=resume_state,
    )

    assert plan.action_selection is not None
    assert plan.action_selection.action_type == "block"
    assert plan.stage_selection.outcome == "block"


def test_stage_strategy_execute_stage_for_explore_uses_strategy_executor() -> None:
    strategy = runtime_module._stage_strategy("explore")
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="explore",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="report_first",
        operation_count=0,
        operation_paths=[],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind=None,
        action_feasibility="advance",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="explore",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )
    plan = strategy.build_stage_plan(
        stage_cursor="explore",
        planner_context=planner_context,
        resume_state=resume_state,
    )
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())

    outcome = strategy.execute_stage(
        runtime=runtime,
        request=ExecutionRequest(
            requirement="Inspect repo",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-strategy-explore",
            turn_id="turn-strategy-explore",
            context_snapshot={"snapshot_id": "snapshot-strategy-explore"},
            task_contract={
                "id": "task-strategy-explore",
                "goal": "Inspect repo",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Inspect repo"],
                "outputs": ["plan"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "low",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        ),
        edit_intent=type("EditIntent", (), {"mode": "report_first"})(),
        resume_state=resume_state,
        plan=plan,
        applied_changes=[],
    )

    assert outcome.next_stage == plan.next_stage_proposal.proposed_stage
    assert outcome.should_stop is False


def test_stage_strategy_execute_stage_for_completed_uses_terminal_executor() -> None:
    strategy = runtime_module._stage_strategy("completed")
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="completed",
        resume_kind="fresh",
        route_risk_level="low",
        edit_mode="report_first",
        operation_count=0,
        operation_paths=[],
        target_paths=[],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind=None,
        action_feasibility="advance",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="completed",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )
    plan = strategy.build_stage_plan(
        stage_cursor="completed",
        planner_context=planner_context,
        resume_state=resume_state,
    )
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())

    outcome = strategy.execute_stage(
        runtime=runtime,
        request=ExecutionRequest(
            requirement="No-op",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-strategy-completed",
            turn_id="turn-strategy-completed",
            context_snapshot={"snapshot_id": "snapshot-strategy-completed"},
            task_contract={
                "id": "task-strategy-completed",
                "goal": "No-op",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["No-op"],
                "outputs": ["plan"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "low",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        ),
        edit_intent=type("EditIntent", (), {"mode": "report_first"})(),
        resume_state=resume_state,
        plan=plan,
        applied_changes=[],
    )

    assert outcome.next_stage == "completed"
    assert outcome.should_stop is True


def test_stage_strategy_map_contains_core_runtime_stages() -> None:
    strategy_map = runtime_module._stage_strategy_map()

    assert set(strategy_map) == {"explore", "edit", "verify"}


def test_explore_stage_strategy_uses_shared_simple_executor() -> None:
    strategy = runtime_module._explore_stage_strategy()

    assert strategy.executor is runtime_module._continue_without_side_effects_stage


def test_edit_and_verify_stage_strategies_use_direct_stage_executors() -> None:
    edit_strategy = runtime_module._edit_stage_strategy()
    verify_strategy = runtime_module._verify_stage_strategy()

    assert edit_strategy.executor is runtime_module._execute_edit_stage
    assert verify_strategy.executor is runtime_module._execute_verify_stage


def test_paused_edit_outcome_preserves_pause_semantics() -> None:
    plan = runtime_module._KernelStagePlan(
        stage_cursor="edit",
        stage_strategy=runtime_module._edit_stage_strategy(),
        planner_context=runtime_module._KernelPlannerContext(
            stage_cursor="edit",
            resume_kind="fresh",
            route_risk_level="medium",
            edit_mode="direct_apply",
            operation_count=1,
            operation_paths=["note.py"],
            target_paths=["note.py"],
            workspace_root="/tmp/workspace",
            verification_command=[],
            remaining_retry_budget=None,
            should_block_verify_resume=False,
            latest_observation_kind="edit_intent",
            action_feasibility="ready_to_apply",
            approval_required=True,
            approval_resolved=False,
            pending_approval_stage="edit",
            applied_change_count=0,
            recent_observation_count=0,
            verification_status=None,
            repair_outcome=None,
        ),
        next_stage_proposal=runtime_module._KernelNextStageProposal(
            current_stage="edit",
            proposed_stage="edit",
            disposition="pause",
            reason="Await approval.",
            candidates=[],
            selected_candidate_id="edit_wait_approval",
        ),
        stage_selection=runtime_module._KernelStageSelection(
            stage="edit",
            outcome="pause",
            next_stage="edit",
            reason="Await approval.",
        ),
        action_selection=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="edit",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )

    outcome = runtime_module._paused_edit_outcome(
        pending_approval={"stage": "edit", "approval_id": "approval-1"},
        plan=plan,
        resume_state=resume_state,
    )

    assert outcome.next_stage == "edit"
    assert outcome.pending_approval is not None
    assert outcome.should_stop is True


def test_blocked_edit_outcome_preserves_block_semantics() -> None:
    edit_selection = runtime_module._KernelActionSelection(
        stage="edit",
        action_type="block",
        source="workspace_boundary",
        selected={"path": "../outside.py"},
        reason="Block edit outside workspace.",
    )
    plan = runtime_module._KernelStagePlan(
        stage_cursor="edit",
        stage_strategy=runtime_module._edit_stage_strategy(),
        planner_context=runtime_module._KernelPlannerContext(
            stage_cursor="edit",
            resume_kind="fresh",
            route_risk_level="medium",
            edit_mode="direct_apply",
            operation_count=1,
            operation_paths=["../outside.py"],
            target_paths=["note.py"],
            workspace_root="/tmp/workspace",
            verification_command=[],
            remaining_retry_budget=None,
            should_block_verify_resume=False,
            latest_observation_kind="edit_intent",
            action_feasibility="ready_to_apply",
            approval_required=False,
            approval_resolved=False,
            pending_approval_stage=None,
            applied_change_count=0,
            recent_observation_count=0,
            verification_status=None,
            repair_outcome=None,
        ),
        next_stage_proposal=runtime_module._KernelNextStageProposal(
            current_stage="edit",
            proposed_stage="verify",
            disposition="advance",
            reason="Advance to verify.",
            candidates=[],
            selected_candidate_id="edit_to_verify",
        ),
        stage_selection=runtime_module._KernelStageSelection(
            stage="edit",
            outcome="block",
            next_stage="verify",
            reason="Blocked.",
        ),
        action_selection=edit_selection,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="edit",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )

    outcome = runtime_module._blocked_edit_outcome(
        edit_selection=edit_selection,
        plan=plan,
        resume_state=resume_state,
    )

    assert outcome.next_stage == "verify"
    assert outcome.pending_approval is None
    assert outcome.should_stop is True


def test_paused_verify_outcome_preserves_pause_semantics() -> None:
    plan = runtime_module._KernelStagePlan(
        stage_cursor="verify",
        stage_strategy=runtime_module._verify_stage_strategy(),
        planner_context=runtime_module._KernelPlannerContext(
            stage_cursor="verify",
            resume_kind="fresh",
            route_risk_level="medium",
            edit_mode="direct_apply",
            operation_count=1,
            operation_paths=["note.py"],
            target_paths=["note.py"],
            workspace_root="/tmp/workspace",
            verification_command=["python3", "-m", "compileall", "note.py"],
            remaining_retry_budget=1,
            should_block_verify_resume=False,
            latest_observation_kind="verification",
            action_feasibility="ready_to_verify",
            approval_required=True,
            approval_resolved=False,
            pending_approval_stage="verify",
            applied_change_count=1,
            recent_observation_count=1,
            verification_status=None,
            repair_outcome=None,
        ),
        next_stage_proposal=runtime_module._KernelNextStageProposal(
            current_stage="verify",
            proposed_stage="verify",
            disposition="pause",
            reason="Await approval.",
            candidates=[],
            selected_candidate_id="verify_wait_approval",
        ),
        stage_selection=runtime_module._KernelStageSelection(
            stage="verify",
            outcome="pause",
            next_stage="verify",
            reason="Await approval.",
        ),
        action_selection=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="verify",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
    )

    outcome = runtime_module._paused_verify_outcome(
        pending_approval={"stage": "verify", "approval_id": "approval-verify"},
        plan=plan,
        resume_state=resume_state,
        applied_changes=[{"status": "applied"}],
    )

    assert outcome.next_stage == "verify"
    assert outcome.pending_approval is not None
    assert outcome.should_stop is True


def test_blocked_verify_resume_outcome_preserves_block_semantics() -> None:
    plan = runtime_module._KernelStagePlan(
        stage_cursor="verify",
        stage_strategy=runtime_module._verify_stage_strategy(),
        planner_context=runtime_module._KernelPlannerContext(
            stage_cursor="verify",
            resume_kind="fresh",
            route_risk_level="medium",
            edit_mode="direct_apply",
            operation_count=1,
            operation_paths=["note.py"],
            target_paths=["note.py"],
            workspace_root="/tmp/workspace",
            verification_command=["python3", "-m", "compileall", "note.py"],
            remaining_retry_budget=0,
            should_block_verify_resume=True,
            latest_observation_kind="verification",
            action_feasibility="ready_to_verify",
            approval_required=False,
            approval_resolved=False,
            pending_approval_stage=None,
            applied_change_count=1,
            recent_observation_count=1,
            verification_status="failed",
            repair_outcome="failed",
        ),
        next_stage_proposal=runtime_module._KernelNextStageProposal(
            current_stage="verify",
            proposed_stage="completed",
            disposition="block",
            reason="Retry budget exhausted.",
            candidates=[],
            selected_candidate_id="verify_block_completed",
        ),
        stage_selection=runtime_module._KernelStageSelection(
            stage="verify",
            outcome="block",
            next_stage="completed",
            reason="Retry budget exhausted.",
        ),
        action_selection=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="verify",
        applied_changes=[],
        recent_observations=[],
        final_verification={"status": "failed"},
        repair_summary={"outcome": "failed"},
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=0,
        should_block_verify_resume=True,
    )

    outcome = runtime_module._blocked_verify_resume_outcome(
        plan=plan,
        resume_state=resume_state,
        applied_changes=[{"status": "applied"}],
    )

    assert outcome.next_stage == "verify"
    assert outcome.pending_approval is None
    assert outcome.should_stop is True


def test_completed_verify_outcome_preserves_terminal_semantics() -> None:
    plan = runtime_module._KernelStagePlan(
        stage_cursor="verify",
        stage_strategy=runtime_module._verify_stage_strategy(),
        planner_context=runtime_module._KernelPlannerContext(
            stage_cursor="verify",
            resume_kind="fresh",
            route_risk_level="medium",
            edit_mode="direct_apply",
            operation_count=1,
            operation_paths=["note.py"],
            target_paths=["note.py"],
            workspace_root="/tmp/workspace",
            verification_command=["python3", "-m", "compileall", "note.py"],
            remaining_retry_budget=1,
            should_block_verify_resume=False,
            latest_observation_kind="verification",
            action_feasibility="ready_to_verify",
            approval_required=False,
            approval_resolved=False,
            pending_approval_stage=None,
            applied_change_count=1,
            recent_observation_count=1,
            verification_status="passed",
            repair_outcome="passed",
        ),
        next_stage_proposal=runtime_module._KernelNextStageProposal(
            current_stage="verify",
            proposed_stage="completed",
            disposition="complete",
            reason="Verification passed.",
            candidates=[],
            selected_candidate_id="verify_complete_from_history",
        ),
        stage_selection=runtime_module._KernelStageSelection(
            stage="verify",
            outcome="complete",
            next_stage="completed",
            reason="Verification passed.",
        ),
        action_selection=None,
    )

    outcome = runtime_module._completed_verify_outcome(
        plan=plan,
        applied_changes=[{"status": "applied"}],
        repair_summary={"outcome": "passed"},
        final_verification={"status": "passed"},
        status="completed",
        accepted=True,
    )

    assert outcome.next_stage == "completed"
    assert outcome.status == "completed"
    assert outcome.accepted is True
    assert outcome.should_stop is True


def test_applied_edit_outcome_preserves_continue_semantics() -> None:
    plan = runtime_module._KernelStagePlan(
        stage_cursor="edit",
        stage_strategy=runtime_module._edit_stage_strategy(),
        planner_context=runtime_module._KernelPlannerContext(
            stage_cursor="edit",
            resume_kind="fresh",
            route_risk_level="medium",
            edit_mode="direct_apply",
            operation_count=1,
            operation_paths=["note.py"],
            target_paths=["note.py"],
            workspace_root="/tmp/workspace",
            verification_command=[],
            remaining_retry_budget=None,
            should_block_verify_resume=False,
            latest_observation_kind="edit_intent",
            action_feasibility="ready_to_apply",
            approval_required=False,
            approval_resolved=False,
            pending_approval_stage=None,
            applied_change_count=0,
            recent_observation_count=0,
            verification_status=None,
            repair_outcome=None,
        ),
        next_stage_proposal=runtime_module._KernelNextStageProposal(
            current_stage="edit",
            proposed_stage="verify",
            disposition="advance",
            reason="Advance to verify.",
            candidates=[],
            selected_candidate_id="edit_to_verify",
        ),
        stage_selection=runtime_module._KernelStageSelection(
            stage="edit",
            outcome="advance",
            next_stage="verify",
            reason="Advance to verify.",
        ),
        action_selection=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="edit",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )

    outcome = runtime_module._applied_edit_outcome(
        applied_changes=[{"status": "applied", "path": "note.py"}],
        plan=plan,
        resume_state=resume_state,
    )

    assert outcome.next_stage == "verify"
    assert outcome.accepted is False
    assert outcome.should_stop is False


def test_verify_terminal_status_blocks_direct_apply_without_change() -> None:
    status, accepted = runtime_module._verify_terminal_status(
        final_status="passed",
        edit_mode="direct_apply",
        applied_change_count=0,
    )

    assert status == "blocked"
    assert accepted is False


def test_verify_terminal_status_completes_when_verification_passes_with_change() -> None:
    status, accepted = runtime_module._verify_terminal_status(
        final_status="passed",
        edit_mode="direct_apply",
        applied_change_count=1,
    )

    assert status == "completed"
    assert accepted is True


def test_continue_stage_outcome_preserves_non_terminal_semantics() -> None:
    outcome = runtime_module._continue_stage_outcome(
        next_stage="verify",
        applied_changes=[{"status": "applied"}],
        repair_summary={"outcome": "pending"},
        final_verification={},
    )

    assert outcome.next_stage == "verify"
    assert outcome.accepted is False
    assert outcome.should_stop is False


def test_stage_outcome_builder_preserves_fields() -> None:
    outcome = runtime_module._stage_outcome(
        next_stage="completed",
        pending_approval={"stage": "verify"},
        applied_changes=[{"status": "applied"}],
        repair_summary={"outcome": "passed"},
        final_verification={"status": "passed"},
        status="completed",
        accepted=True,
        should_stop=True,
    )

    assert outcome.next_stage == "completed"
    assert outcome.pending_approval == {"stage": "verify"}
    assert outcome.accepted is True
    assert outcome.should_stop is True


def test_edit_stage_strategy_exposes_edit_outcome_semantics() -> None:
    strategy = runtime_module._edit_stage_strategy()

    assert strategy.outcomes.pause is runtime_module._paused_edit_outcome
    assert strategy.outcomes.block is runtime_module._blocked_edit_outcome
    assert strategy.outcomes.continue_outcome is runtime_module._applied_edit_outcome


def test_verify_stage_strategy_exposes_verify_outcome_semantics() -> None:
    strategy = runtime_module._verify_stage_strategy()

    assert strategy.outcomes.pause is runtime_module._paused_verify_outcome
    assert strategy.outcomes.block is runtime_module._blocked_verify_resume_outcome
    assert strategy.outcomes.complete is runtime_module._completed_verify_outcome


def test_stage_strategy_outcome_helpers_delegate_to_configured_semantics() -> None:
    strategy = runtime_module._edit_stage_strategy()
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="edit",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["note.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind=None,
        action_feasibility="ready_to_mutate",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
    )
    proposal = runtime_module._KernelNextStageProposal(
        current_stage="edit",
        proposed_stage="verify",
        disposition="advance",
        reason="Move to verification after bounded edit application.",
        candidates=[],
        selected_candidate_id="edit_to_verify",
    )
    plan = runtime_module._KernelStagePlan(
        stage_cursor="edit",
        stage_strategy=strategy,
        planner_context=planner_context,
        next_stage_proposal=proposal,
        stage_selection=runtime_module._KernelStageSelection(
            stage="edit",
            outcome="advance",
            next_stage="verify",
            reason="Edit stage is ready to continue.",
        ),
        action_selection=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="edit",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )

    outcome = strategy.continue_stage(
        applied_changes=[{"status": "applied", "path": "note.py"}],
        plan=plan,
        resume_state=resume_state,
    )

    assert outcome.next_stage == "verify"
    assert outcome.should_stop is False
    assert outcome.applied_changes == [{"status": "applied", "path": "note.py"}]


def test_stage_strategy_outcome_helpers_raise_when_semantics_are_missing() -> None:
    strategy = runtime_module._terminal_stage_strategy("completed")

    with pytest.raises(RuntimeError, match="pause outcome semantics are not configured"):
        strategy.pause_stage()


def test_stage_plan_carries_stage_strategy_context() -> None:
    strategy = runtime_module._edit_stage_strategy()
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="edit",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["note.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind="edit_intent",
        action_feasibility="ready_to_apply",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="edit",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )

    plan = strategy.build_stage_plan(
        stage_cursor="edit",
        planner_context=planner_context,
        resume_state=resume_state,
    )

    assert plan.stage_strategy is strategy


def test_propose_next_stage_uses_explicit_stage_strategy() -> None:
    strategy = runtime_module._verify_stage_strategy()
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="verify",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["note.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
        latest_observation_kind="verification",
        action_feasibility="ready_to_verify",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=1,
        recent_observation_count=1,
        verification_status="passed",
        repair_outcome="passed",
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="verify",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
    )

    proposal = runtime_module._propose_next_stage(
        stage_strategy=strategy,
        stage_cursor="verify",
        planner_context=planner_context,
        resume_state=resume_state,
    )

    assert proposal.current_stage == "verify"
    assert proposal.selected_candidate_id == "verify_complete_from_history"


def test_build_next_stage_candidates_uses_explicit_stage_strategy() -> None:
    strategy = runtime_module._explore_stage_strategy()
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="explore",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="report_first",
        operation_count=0,
        operation_paths=[],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind=None,
        action_feasibility="advance",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="explore",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
    )

    candidates = runtime_module._build_next_stage_candidates(
        stage_strategy=strategy,
        stage_cursor="explore",
        planner_context=planner_context,
        resume_state=resume_state,
    )

    assert [candidate.candidate_id for candidate in candidates] == [
        "explore_to_edit",
        "explore_stop_completed",
    ]


def test_ranking_enabled_for_stage_uses_explicit_stage_strategy() -> None:
    strategy = runtime_module._verify_stage_strategy()
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="verify",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["note.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
        latest_observation_kind="verification",
        action_feasibility="ready_to_verify",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=1,
        recent_observation_count=1,
        verification_status="passed",
        repair_outcome="passed",
    )

    enabled = runtime_module._ranking_enabled_for_stage(
        planner_context,
        stage_strategy=strategy,
    )

    assert enabled is True


def test_rank_adjustment_falls_back_to_zero_for_completed_stage_strategy() -> None:
    candidate = runtime_module._KernelNextStageCandidate(
        candidate_id="completed_complete",
        stage="completed",
        disposition="complete",
        reason="Kernel reached a terminal stage.",
    )
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="completed",
        resume_kind="fresh",
        route_risk_level="low",
        edit_mode="report_first",
        operation_count=0,
        operation_paths=[],
        target_paths=[],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind=None,
        action_feasibility="advance",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
    )

    assert runtime_module._stage_specific_rank_adjustment(
        candidate,
        planner_context=planner_context,
        stage_strategy=runtime_module._terminal_stage_strategy("completed"),
    ) == 0


def test_explore_next_stage_candidates_preserve_default_terminal_id_without_context_history() -> None:
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="explore",
        resume_kind="fresh",
        route_risk_level="low",
        edit_mode="report_first",
        operation_count=0,
        operation_paths=[],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=[],
        remaining_retry_budget=None,
        should_block_verify_resume=False,
        latest_observation_kind=None,
        action_feasibility="advance",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=0,
        recent_observation_count=0,
        verification_status=None,
        repair_outcome=None,
    )

    candidates = runtime_module._explore_next_stage_candidates(planner_context)

    assert [candidate.candidate_id for candidate in candidates] == [
        "explore_to_edit",
        "explore_stop_completed",
    ]


def test_advance_or_complete_candidates_preserves_candidate_order() -> None:
    advance_candidate = runtime_module._KernelNextStageCandidate(
        candidate_id="advance_candidate",
        stage="verify",
        disposition="advance",
        reason="Advance to the next bounded stage.",
    )
    complete_candidate = runtime_module._KernelNextStageCandidate(
        candidate_id="complete_candidate",
        stage="completed",
        disposition="complete",
        reason="Complete in the current bounded stage.",
    )

    candidates = runtime_module._advance_or_complete_candidates(
        advance_candidate=advance_candidate,
        complete_candidate=complete_candidate,
    )

    assert [candidate.candidate_id for candidate in candidates] == [
        "advance_candidate",
        "complete_candidate",
    ]


def test_complete_or_retry_candidates_preserves_candidate_order() -> None:
    complete_candidate = runtime_module._KernelNextStageCandidate(
        candidate_id="complete_candidate",
        stage="completed",
        disposition="complete",
        reason="Complete in the current bounded stage.",
    )
    retry_candidate = runtime_module._KernelNextStageCandidate(
        candidate_id="retry_candidate",
        stage="verify",
        disposition="advance",
        reason="Retry the current bounded stage.",
    )

    candidates = runtime_module._complete_or_retry_candidates(
        complete_candidate=complete_candidate,
        retry_candidate=retry_candidate,
    )

    assert [candidate.candidate_id for candidate in candidates] == [
        "complete_candidate",
        "retry_candidate",
    ]


def test_block_or_retry_candidates_preserves_candidate_order() -> None:
    block_candidate = runtime_module._KernelNextStageCandidate(
        candidate_id="block_candidate",
        stage="completed",
        disposition="block",
        reason="Block in the current bounded stage.",
    )
    retry_candidate = runtime_module._KernelNextStageCandidate(
        candidate_id="retry_candidate",
        stage="verify",
        disposition="advance",
        reason="Retry the current bounded stage.",
    )

    candidates = runtime_module._block_or_retry_candidates(
        block_candidate=block_candidate,
        retry_candidate=retry_candidate,
    )

    assert [candidate.candidate_id for candidate in candidates] == [
        "block_candidate",
        "retry_candidate",
    ]


def test_proposal_from_selected_candidate_uses_selected_candidate_fields() -> None:
    candidates = [
        runtime_module._KernelNextStageCandidate(
            candidate_id="explore_to_edit",
            stage="edit",
            disposition="advance",
            reason="Advance to edit.",
        ),
        runtime_module._KernelNextStageCandidate(
            candidate_id="explore_complete_from_context",
            stage="completed",
            disposition="complete",
            reason="Complete from context.",
        ),
    ]

    proposal = runtime_module._proposal_from_selected_candidate(
        current_stage="explore",
        candidates=candidates,
        selected_candidate=candidates[1],
    )

    assert proposal.current_stage == "explore"
    assert proposal.proposed_stage == "completed"
    assert proposal.disposition == "complete"
    assert proposal.reason == "Complete from context."
    assert proposal.selected_candidate_id == "explore_complete_from_context"
    assert proposal.selection["ranking_enabled"] is False
    assert proposal.selection["candidate_count"] == 2
    assert [candidate.candidate_id for candidate in proposal.candidates] == [
        "explore_to_edit",
        "explore_complete_from_context",
    ]


def test_stage_strategy_next_stage_decision_exposes_ranking_state_for_verify_history() -> None:
    strategy = runtime_module._stage_strategy("verify")
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="verify",
        resume_kind="fresh",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["note.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
        latest_observation_kind="verification",
        action_feasibility="ready_to_verify",
        approval_required=False,
        approval_resolved=False,
        pending_approval_stage=None,
        applied_change_count=1,
        recent_observation_count=1,
        verification_status="passed",
        repair_outcome="passed",
    )
    resume_state = runtime_module._KernelResumeState(
        stage_cursor="verify",
        applied_changes=[],
        recent_observations=[],
        final_verification={},
        repair_summary={},
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
    )

    decision = strategy.next_stage_decision(
        planner_context=planner_context,
        resume_state=resume_state,
    )

    assert decision.ranking_enabled is True
    assert decision.selected_candidate.candidate_id == "verify_complete_from_history"
    assert [candidate.candidate_id for candidate in decision.candidates] == [
        "verify_complete_from_history",
        "verify_repeat_same_stage",
    ]


def test_stage_selection_decision_tracks_action_and_proposal_linkage() -> None:
    action_selection = runtime_module._KernelActionSelection(
        stage="edit",
        action_type="block",
        source="boundary_policy",
        selected={"path": "../outside.py"},
        reason="Blocked before mutation.",
    )
    proposal = runtime_module._KernelNextStageProposal(
        current_stage="edit",
        proposed_stage="verify",
        disposition="advance",
        reason="Advance to verify.",
        candidates=[],
        selected_candidate_id="edit_to_verify",
    )
    stage_selection = runtime_module._stage_selection_with_decision(
        stage_selection=runtime_module._KernelStageSelection(
            stage="edit",
            outcome="block",
            next_stage="verify",
            reason="Blocked.",
        ),
        next_stage_proposal=proposal,
        action_selection=action_selection,
    )

    assert stage_selection.decision["decision_type"] == "stage_selection"
    assert stage_selection.decision["selection_mode"] == "action_and_proposal"
    assert stage_selection.decision["proposal_selected_candidate_id"] == "edit_to_verify"
    assert stage_selection.decision["action_selected_type"] == "block"


def test_action_selection_decision_captures_planner_context_semantics() -> None:
    planner_context = runtime_module._KernelPlannerContext(
        stage_cursor="verify",
        resume_kind="approval_resume",
        route_risk_level="medium",
        edit_mode="direct_apply",
        operation_count=1,
        operation_paths=["note.py"],
        target_paths=["note.py"],
        workspace_root="/tmp/workspace",
        verification_command=["python3", "-m", "compileall", "note.py"],
        remaining_retry_budget=1,
        should_block_verify_resume=False,
        latest_observation_kind="verification",
        action_feasibility="ready_to_verify",
        approval_required=False,
        approval_resolved=True,
        pending_approval_stage=None,
        applied_change_count=1,
        recent_observation_count=1,
        verification_status="passed",
        repair_outcome="passed",
    )
    selection = runtime_module._action_selection_with_decision(
        action_selection=runtime_module._KernelActionSelection(
            stage="verify",
            action_type="run_command",
            source="resume_context",
            selected={"command": ["python3", "-m", "compileall", "note.py"]},
            reason="Resume verification command.",
        ),
        planner_context=planner_context,
    )

    assert selection.decision["decision_type"] == "action_selection"
    assert selection.decision["selected_action_type"] == "run_command"
    assert selection.decision["selected_source"] == "resume_context"
    assert selection.decision["planner_feasibility"] == "ready_to_verify"


def test_coding_agent_runtime_persists_pending_execution_state(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    state_root = tmp_path / "execution-state"
    approvals_root = tmp_path / "approvals"
    runtime = CodingAgentExecutionRuntime(
        orchestrator=Orchestrator(),
        enforce_approvals=True,
        approvals_root=approvals_root,
    )
    runtime.state_store.root = state_root
    runtime.state_store.__post_init__()
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path

    result = runtime.run(
        ExecutionRequest(
            requirement='Append "print(\'bye\')" to note.py',
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-11",
            turn_id="turn-11",
            context_snapshot={"snapshot_id": "snapshot-11"},
            task_contract={
                "id": "task-11",
                "goal": "Append a line",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Append a line"],
                "outputs": ["persist pending state"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    run_id = result.run_id
    assert run_id is not None
    state = runtime.state_store.read(run_id)
    assert state["status"] == "blocked"
    assert state["current_stage"] == "edit"
    assert state["pending_approval"]["stage"] == "edit"
    assert state["planner_context_trace"][1]["stage_cursor"] == "edit"
    assert state["next_stage_proposals"][1]["disposition"] == "pause"
    assert state["planner_context_trace"][1]["operation_paths"] == ["note.py"]
    assert state["step_statuses"][1]["status"] == "pending"
    assert state["compressed_context"]["pending_approval"]["stage"] == "edit"


def test_coding_agent_runtime_persists_completed_execution_state(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    state_root = tmp_path / "execution-state"
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.state_store.root = state_root
    runtime.state_store.__post_init__()
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path

    result = runtime.run(
        ExecutionRequest(
            requirement='Append "print(\'bye\')" to note.py',
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-12",
            turn_id="turn-12",
            context_snapshot={"snapshot_id": "snapshot-12"},
            task_contract={
                "id": "task-12",
                "goal": "Append a line",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Append a line"],
                "outputs": ["persist completed state"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    run_id = result.run_id
    assert run_id is not None
    state = runtime.state_store.read(run_id)
    assert state["status"] == "completed"
    assert state["accepted"] is True
    assert state["pending_approval"] is None
    assert state["current_stage"] == "verification"
    assert [item["stage_cursor"] for item in state["planner_context_trace"]] == ["explore", "edit", "verify"]
    assert [item["current_stage"] for item in state["next_stage_proposals"]] == ["explore", "edit", "verify"]
    assert state["compressed_context"]["current_status"] == "completed"
    assert state["compressed_context"]["summarized_history"]["artifact_count"] >= 1
    assert state["result_summary"]["applied_change_count"] == 1
    assert state["result_summary"]["applied_changes"][0]["status"] == "applied"
    assert state["result_summary"]["recent_observations"]
    assert state["resume_context"]["recent_observations"]


def test_action_executor_externalizes_command_output_artifact(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")
    artifact_root = tmp_path / "execution-artifacts"
    executor = ActionExecutor(workspace_root=tmp_path)
    executor.artifact_store.root = artifact_root
    executor.artifact_store.__post_init__()

    result = executor.execute(
        ActionRequest(
            action_id="verify-runtime",
            action_type="run_command",
            description="Compile the target file.",
            parameters={"command": ["python3", "-m", "compileall", "note.py"], "run_id": "coding-turn-artifact"},
            risk_level="medium",
            requires_approval=True,
        )
    )

    artifact = result.payload["artifact"]
    assert result.status == "passed"
    assert "stdout_preview" in result.payload
    assert "stderr_preview" in result.payload
    assert Path(artifact["path"]).exists()


def test_coding_agent_runtime_surfaces_externalized_artifact_summary(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    artifact_root = tmp_path / "execution-artifacts"
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.artifact_store.root = artifact_root
    runtime.verify_loop.verifier.action_executor.artifact_store.__post_init__()

    result = runtime.run(
        ExecutionRequest(
            requirement='Append "print(\'bye\')" to note.py',
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-13",
            turn_id="turn-13",
            context_snapshot={"snapshot_id": "snapshot-13"},
            task_contract={
                "id": "task-13",
                "goal": "Append a line",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Append a line"],
                "outputs": ["artifact summary"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    assert result.payload["artifact_summary"]["artifact_count"] >= 1
    assert result.payload["native_task_proof"]["artifact_count"] >= 1
    artifact = result.payload["artifact_summary"]["artifacts"][0]
    assert Path(artifact["path"]).exists()
    assert result.payload["execution_steps"][2]["results"][0]["payload"]["artifact"]["artifact_id"]


def test_coding_agent_runtime_emits_step_level_events(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    runtime.event_store.root = tmp_path / "events"
    runtime.event_store.__post_init__()

    result = runtime.run(
        ExecutionRequest(
            requirement='Append "print(\'bye\')" to note.py',
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-14",
            turn_id="turn-14",
            context_snapshot={"snapshot_id": "snapshot-14"},
            task_contract={
                "id": "task-14",
                "goal": "Append a line",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Append a line"],
                "outputs": ["event summary"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    events = runtime.event_store.list_recent(limit=10)
    assert result.payload["event_summary"]["event_count"] >= 9
    assert result.payload["event_summary"]["type_counts"]["execution.step"] >= 3
    assert result.payload["event_summary"]["type_counts"]["execution.action_requested"] >= 3
    assert result.payload["event_summary"]["type_counts"]["execution.action_completed"] >= 3
    assert result.payload["event_summary"]["type_counts"]["execution.context_compressed"] == 1
    assert result.payload["event_summary"]["type_counts"]["execution.next_step_decided"] == 1
    assert result.payload["native_task_proof"]["event_count"] >= 9
    assert any(event["type"] == "execution.run_completed" for event in events)
    assert any(event["payload"].get("step_kind") == "verification" for event in events if event["type"] == "execution.step")
    assert any(event["type"] == "execution.action_requested" for event in events)
    assert any(event["type"] == "execution.action_completed" for event in events)
    assert any(event["type"] == "execution.context_compressed" for event in events)
    assert any(event["type"] == "execution.next_step_decided" for event in events)


def test_repo_explorer_externalizes_file_listing_artifact(tmp_path) -> None:
    (tmp_path / "a.py").write_text("print('a')\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("print('b')\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.repo_explorer.artifact_store.root = tmp_path / "execution-artifacts"
    runtime.repo_explorer.artifact_store.__post_init__()

    request = ExecutionRequest(
        requirement="Inspect a.py",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-15",
        turn_id="turn-15",
        context_snapshot={"snapshot_id": "snapshot-15"},
        task_contract={
            "id": "task-15",
            "goal": "Inspect a file",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Inspect a file"],
            "outputs": ["repo artifact"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "low",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    report = runtime.repo_explorer.explore(request)

    assert report.artifact is not None
    assert Path(report.artifact["path"]).exists()
    assert report.file_count >= 2


def test_coding_agent_runtime_artifact_summary_includes_repo_exploration_artifact(tmp_path) -> None:
    (tmp_path / "a.py").write_text("print('a')\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("print('b')\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.repo_explorer.artifact_store.root = tmp_path / "execution-artifacts"
    runtime.repo_explorer.artifact_store.__post_init__()
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.artifact_store.root = tmp_path / "execution-artifacts"
    runtime.verify_loop.verifier.action_executor.artifact_store.__post_init__()

    result = runtime.run(
        ExecutionRequest(
            requirement='Append "print(\'bye\')" to a.py',
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-16",
            turn_id="turn-16",
            context_snapshot={"snapshot_id": "snapshot-16"},
            task_contract={
                "id": "task-16",
                "goal": "Append a line",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Append a line"],
                "outputs": ["repo artifact summary"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    assert result.payload["artifact_summary"]["artifact_count"] >= 2
    assert any("execution_repo_exploration_artifact" in str(item.get("ref", {}).get("format")) for item in result.payload["artifact_summary"]["artifacts"])


def test_repo_explorer_uses_native_tool_surface_for_exploration(tmp_path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('app')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.repo_explorer.artifact_store.root = tmp_path / "execution-artifacts"
    runtime.repo_explorer.artifact_store.__post_init__()

    report = runtime.repo_explorer.explore(
        ExecutionRequest(
            requirement="Inspect src/app.py and explain the repo layout.",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-explore",
            turn_id="turn-explore",
            context_snapshot={"snapshot_id": "snapshot-explore"},
            task_contract={
                "id": "task-explore",
                "goal": "Inspect repository layout",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Inspect repository layout"],
                "outputs": ["repo report"],
                "acceptance_criteria": ["Relevant files identified"],
                "risk_level": "low",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    assert report.artifact is not None
    assert report.artifact["repo_map"]["directory_count"] >= 1
    assert report.artifact["exploration_profile"]["patterns"]
    assert report.artifact["exploration_profile"]["candidate_reason"] in {
        "explicit_existing_paths",
        "search_matches",
        "repo_map_fallback",
    }
    assert report.artifact["read"]["record_count"] >= 1


def test_native_toolbox_search_ranks_matches_and_centers_preview(tmp_path) -> None:
    hot_path = tmp_path / "docs" / "alpha_notes.py"
    hot_path.parent.mkdir()
    hot_path.write_text("intro\nalpha alpha alpha\nclosing\n", encoding="utf-8")
    cold_path = tmp_path / "src" / "module.py"
    cold_path.parent.mkdir()
    cold_path.write_text("noise\n" * 40 + "alpha target line\n" + "tail\n" * 10, encoding="utf-8")

    toolbox = NativeToolbox(workspace_root=tmp_path)

    result = toolbox.search("alpha", paths=["src/module.py", "docs/alpha_notes.py"], max_matches=10)

    assert result["match_count"] == 2
    assert result["matches"][0]["path"] == "docs/alpha_notes.py"
    assert result["matches"][0]["score"] > result["matches"][1]["score"]
    assert result["matches"][0]["matched_terms"] == ["alpha"]
    assert result["matches"][1]["path"] == "src/module.py"
    assert result["matches"][1]["preview"].startswith("...")
    assert "alpha target line" in result["matches"][1]["preview"]
    assert not result["matches"][1]["preview"].startswith("noise")


def test_repo_explorer_prefers_ranked_search_candidates(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "alpha.py").write_text("alpha\nalpha\nalpha\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "notes.py").write_text("alpha\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.repo_explorer.artifact_store.root = tmp_path / "execution-artifacts"
    runtime.repo_explorer.artifact_store.__post_init__()

    report = runtime.repo_explorer.explore(
        ExecutionRequest(
            requirement="Find alpha references in the repository.",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-ranked",
            turn_id="turn-ranked",
            context_snapshot={"snapshot_id": "snapshot-ranked"},
            task_contract={
                "id": "task-ranked",
                "goal": "Find alpha references",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Find alpha references"],
                "outputs": ["repo report"],
                "acceptance_criteria": ["Relevant files identified"],
                "risk_level": "low",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    assert report.candidate_paths[0] == "docs/alpha.py"
    assert report.artifact["search"]["matches"][0]["path"] == "docs/alpha.py"


def test_native_toolbox_find_files_ranks_filename_matches(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "native-agent-notes.md").write_text("notes\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "agent_runtime.py").write_text("runtime\n", encoding="utf-8")

    toolbox = NativeToolbox(workspace_root=tmp_path)

    result = toolbox.find_files("inspect native agent files", max_matches=10)

    assert result["match_count"] >= 2
    assert result["matches"][0]["path"] == "docs/native-agent-notes.md"
    assert "agent" in result["matches"][0]["matched_fragments"]


def test_native_toolbox_outline_extracts_structure(tmp_path) -> None:
    target = tmp_path / "src" / "sample.py"
    target.parent.mkdir()
    target.write_text(
        "class Sample:\n"
        "    pass\n\n"
        "def helper():\n"
        "    return 1\n",
        encoding="utf-8",
    )

    toolbox = NativeToolbox(workspace_root=tmp_path)

    result = toolbox.outline(["src/sample.py"], max_entries=10)

    assert result["record_count"] == 1
    assert result["records"][0]["path"] == "src/sample.py"
    assert result["records"][0]["outline"][0]["kind"] == "symbol"
    assert result["records"][0]["outline"][0]["line"] == 1


def test_repo_explorer_prefers_filename_matches_before_content_search(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "agent-roadmap.md").write_text("overview\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "misc.py").write_text("agent\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.repo_explorer.artifact_store.root = tmp_path / "execution-artifacts"
    runtime.repo_explorer.artifact_store.__post_init__()

    report = runtime.repo_explorer.explore(
        ExecutionRequest(
            requirement="Inspect agent roadmap files and explain next steps.",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-filename-match",
            turn_id="turn-filename-match",
            context_snapshot={"snapshot_id": "snapshot-filename-match"},
            task_contract={
                "id": "task-filename-match",
                "goal": "Inspect agent roadmap files",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Inspect agent roadmap files"],
                "outputs": ["repo report"],
                "acceptance_criteria": ["Relevant files identified"],
                "risk_level": "low",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    assert report.artifact["exploration_profile"]["candidate_reason"] == "filename_matches"
    assert report.artifact["find_files"]["matches"][0]["path"] == "docs/agent-roadmap.md"
    assert report.artifact["outline"]["record_count"] >= 1
    assert report.candidate_paths[0] == "docs/agent-roadmap.md"


def test_repo_explorer_treats_bare_filename_as_explicit_path(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.repo_explorer.artifact_store.root = tmp_path / "execution-artifacts"
    runtime.repo_explorer.artifact_store.__post_init__()

    report = runtime.repo_explorer.explore(
        ExecutionRequest(
            requirement="Inspect note.py and report what needs fixing.",
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-bare-explicit",
            turn_id="turn-bare-explicit",
            context_snapshot={"snapshot_id": "snapshot-bare-explicit"},
            task_contract={
                "id": "task-bare-explicit",
                "goal": "Inspect note.py",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Inspect note.py"],
                "outputs": ["repo report"],
                "acceptance_criteria": ["Relevant files identified"],
                "risk_level": "low",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    assert report.existing_paths == ["note.py"]
    assert report.candidate_paths[0] == "note.py"


def test_edit_intent_prioritizes_operation_path_over_repo_noise(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")
    noisy_dir = tmp_path / "plans" / "plan-1"
    noisy_dir.mkdir(parents=True)
    (noisy_dir / "session.json").write_text("{}", encoding="utf-8")
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    (jobs_dir / "job-1.json").write_text("{}", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path

    request = ExecutionRequest(
        requirement='Append "print(\'bye\')" to note.py',
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-op-path",
        turn_id="turn-op-path",
        context_snapshot={"snapshot_id": "snapshot-op-path"},
        task_contract={
            "id": "task-op-path",
            "goal": "Append a line",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Append a line"],
            "outputs": ["edit intent"],
            "acceptance_criteria": ["Target file identified"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    repo_report = RepoExplorationReport(
        workspace_root=str(tmp_path),
        explicit_paths=[],
        existing_paths=[],
        candidate_paths=["jobs/job-1.json", "plans/plan-1/session.json"],
        file_count=3,
        artifact={},
    )
    context = runtime.context_builder.build(
        request=request,
        repo_report=repo_report,
        strategy_plan=None,
    )

    intent = runtime.edit_executor.build_intent(
        request=request,
        repo_report=repo_report,
        context=context,
    )

    assert intent.mode == "direct_apply"
    assert intent.target_paths[0] == "note.py"
    assert intent.operations[0]["path"] == "note.py"


def test_edit_intent_surfaces_preapply_patch_preview_for_explicit_operations(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.artifact_store.root = tmp_path / "execution-artifacts"
    runtime.edit_executor.action_executor.artifact_store.__post_init__()

    request = ExecutionRequest(
        requirement='Append "print(\'bye\')" to note.py',
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-preview",
        turn_id="turn-preview",
        context_snapshot={"snapshot_id": "snapshot-preview"},
        task_contract={
            "id": "task-preview",
            "goal": "Append a line",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Append a line"],
            "outputs": ["preview before apply"],
            "acceptance_criteria": ["Preview shows intended change"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    repo_report = runtime.repo_explorer.explore(request)
    context = runtime.context_builder.build(
        request=request,
        repo_report=repo_report,
        strategy_plan=None,
    )
    intent = runtime.edit_executor.build_intent(
        request=request,
        repo_report=repo_report,
        context=context,
    )

    assert intent.mode == "direct_apply"
    assert intent.patch_preview is not None
    assert intent.patch_preview["preview_count"] >= 1
    assert intent.patch_preview["changed_count"] >= 1
    first_preview = intent.patch_preview["preview_records"][0]
    assert first_preview["path"] == "note.py"
    assert first_preview["operation"] == "append"
    assert first_preview["status"] == "previewed"
    assert "print('bye')" in first_preview["after_preview"]
    trace_tools = [item["tool"] for item in runtime.edit_executor.toolbox.snapshot_trace()] if runtime.edit_executor.toolbox else []
    assert "patch_preview" in trace_tools


def test_coding_agent_runtime_surfaces_execution_history_summary(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path

    result = runtime.run(
        ExecutionRequest(
            requirement='Append "print(\'bye\')" to note.py',
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-17",
            turn_id="turn-17",
            context_snapshot={"snapshot_id": "snapshot-17"},
            task_contract={
                "id": "task-17",
                "goal": "Append a line",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Append a line"],
                "outputs": ["history summary"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    summary = result.payload["execution_history_summary"]
    assert summary["status"] == "completed"
    assert "repo_exploration" in summary["completed_steps"]
    assert summary["artifact_count"] >= 1
    assert summary["latest_recovery_hint"].startswith("No approval gate pending")


def test_execution_state_persists_history_summary(tmp_path) -> None:
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    state_root = tmp_path / "execution-state"
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.state_store.root = state_root
    runtime.state_store.__post_init__()
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path

    result = runtime.run(
        ExecutionRequest(
            requirement='Append "print(\'bye\')" to note.py',
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-18",
            turn_id="turn-18",
            context_snapshot={"snapshot_id": "snapshot-18"},
            task_contract={
                "id": "task-18",
                "goal": "Append a line",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Append a line"],
                "outputs": ["persisted history summary"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    state = runtime.state_store.read(result.run_id or "")
    assert state["execution_history_summary"]["status"] == "completed"
    assert state["execution_history_summary"]["artifact_count"] >= 1
    assert state["compressed_context"]["summarized_history"]["artifact_count"] >= 1
