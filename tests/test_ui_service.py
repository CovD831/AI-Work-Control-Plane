from pathlib import Path

from agent_orchestrator import OrchestrationMode, Orchestrator
from agent_orchestrator.control_plane import build_runtime_event_stream, resolve_approval_item
from agent_orchestrator.execution import CodingAgentExecutionRuntime, ExecutionRequest
from agent_orchestrator.execution.coding_components import VerificationReport
from agent_orchestrator.intake import ClarifyPolicy, ExecutionMode, TaskKind, TaskRouterResult
from agent_orchestrator.jobs import FileJobRuntime, JobRequest
from agent_orchestrator.planning import PlanStore, TeamOrchestrator
from agent_orchestrator.run_store import RunStore
from agent_orchestrator.ui_service import DashboardService, build_dashboard_service
from test_support import start_approved_session, write_minimal_process_docs


def _service(tmp_path):
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=FileJobRuntime(root=tmp_path / "jobs"),
        project_root=tmp_path,
    )
    team.orchestrator.run_store = RunStore(root=tmp_path / "runs")
    return DashboardService(
        team=team,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
    )


def test_dashboard_lists_sessions_and_builds_detail(tmp_path) -> None:
    service = _service(tmp_path)
    session = service.create_session("Build a persisted plan artifact")

    sessions = service.list_sessions()["sessions"]
    detail = service.get_session(str(session["id"]))

    assert sessions[0]["id"] == session["id"]
    assert detail["session"]["id"] == session["id"]
    assert detail["next_action"]["primary_action"] == "mark_draft_ready"
    assert detail["next_action"]["primary_label"] == "确认初稿"
    assert detail["actions"]
    draft_action = next(action for action in detail["actions"] if action["id"] == "mark_draft_ready")
    assert draft_action["enabled"] is True
    assert draft_action["state_changes"]
    assert detail["events"]
    assert detail["messages"]["count"] >= 2
    assert detail["messages"]["threads"].get("main", 0) >= 1
    assert detail["evidence_summary"]["memory_record_count"] >= 1
    assert detail["evidence_summary"]["recent_memory"]
    assert "retrieved_memory" in detail["evidence_summary"]
    assert detail["timeline"]
    assert detail["runbook"]
    assert detail["agent_cards"]
    assert detail["agent_cards"][0]["attach_available"] is False
    assert detail["agent_cards"][0]["terminal_ref"] is None
    assert detail["role_groups"]
    assert detail["governance_summary"]["primary_action"] == "mark_draft_ready"
    assert detail["operator_summary"]["session"]["id"] == session["id"]
    assert detail["operator_summary"]["review_policy"]["policy_name"]
    assert "fallback_snapshot" in detail["operator_summary"]
    assert detail["operator_summary"]["approval_observability"]["approval_state"]["state"] == "drafting"
    assert detail["operator_summary"]["approval_observability"]["usage_cost"]["source"] == "placeholder"
    assert detail["operator_summary"]["compliance_snapshot"]["status"] in {"passed", "warning", "blocked", "unknown"}
    assert detail["operator_summary"]["message_timeline"]
    assert "thread" in detail["operator_summary"]["message_timeline"][0]
    assert detail["control_plane"]["workspace_state"]["format"] == "agent_orchestrator.workspace_state.v1"
    assert detail["control_plane"]["workspace_index"]["format"] == "agent_orchestrator.workspace_index.v1"
    assert detail["control_plane"]["read_only"] is True
    assert detail["control_plane"]["strategy_decision"]["format"] == "agent_orchestrator.strategy_decision.v1"
    assert detail["control_plane"]["strategy_decision"]["executes"] is False
    assert detail["control_plane"]["topology_snapshot"]["format"] == "agent_orchestrator.execution_topology_snapshot.v1"
    assert detail["control_plane"]["topology_snapshot"]["program_posture"]["program_goal"]
    assert "selected_executor" in detail["control_plane"]["topology_snapshot"]["delegation_contract"]
    assert detail["control_plane"]["approval_queue"]["format"] == "agent_orchestrator.approval_queue.v1"
    assert detail["control_plane"]["evidence_bundle"]["format"] == "agent_orchestrator.evidence_bundle.v1"
    assert detail["plan_tree"]["kind"] == "session"
    assert detail["plan_tree"]["children"]
    assert detail["evidence_summary"]["review_round_count"] >= 1
    assert "job_log" in detail["evidence_summary"]["memory_namespaces"]
    assert "learning_consumption_ready" in detail["evidence_summary"]


def test_dashboard_creates_ideation_session_with_messages(tmp_path) -> None:
    service = _service(tmp_path)

    session = service.create_ideation_session("Explore a multi-agent debate mode")
    detail = service.get_session(str(session["id"]))

    assert detail["session"]["resume"]["current_phase"] == "ideation"
    assert detail["messages"]["count"] >= 5
    assert any(message["from_role"] == "proponent" for message in detail["messages"]["items"])
    groups = {group["layer"]: group for group in detail["role_groups"]}
    assert any(card["role"] == "proponent" for card in groups["decision"]["cards"])


def test_dashboard_job_list_detail_and_missing_log(tmp_path) -> None:
    service = _service(tmp_path)
    runtime = FileJobRuntime(root=tmp_path / "jobs")
    job = runtime.start(
        JobRequest(
            task_id="ui-job",
            provider="codex",
            kind="implementation",
            prompt="Build UI",
            cwd=str(tmp_path),
        )
    )
    runtime.complete(job.id, summary="done", stdout="ok")

    jobs = service.list_jobs()["jobs"]
    detail = service.get_job(job.id)
    missing_log = service.get_job_log("missing-job")

    assert jobs[0]["id"] == job.id
    assert detail["summary"] == "done"
    assert detail["attach_available"] is False
    assert detail["log_available"] is True
    assert detail["output_preview"] == "ok"
    assert detail["last_log_excerpt"]
    assert detail["last_seen_at"]
    assert detail["runtime_fidelity"]["format"] == "agent_orchestrator.provider_session_snapshot.v1"
    assert detail["runtime_fidelity"]["liveness"]["state"] == "terminal"
    assert "ok" in service.get_job_log(job.id)["log"]
    assert missing_log["log"] == ""


def test_dashboard_job_send_cancel_surface_operation_status(tmp_path) -> None:
    service = _service(tmp_path)
    runtime = FileJobRuntime(root=tmp_path / "jobs")
    job = runtime.start(
        JobRequest(
            task_id="ui-job-operation",
            provider="codex",
            kind="implementation",
            prompt="Build UI",
            cwd=str(tmp_path),
        )
    )

    sent = service.send_job(job.id, "continue")
    cancelled = service.cancel_job(job.id)
    missing = service.send_job("missing-job", "continue")

    assert sent["operation"]["status"] == "accepted"
    assert sent["runtime_fidelity"]["last_operation_receipt"]["format"] == "agent_orchestrator.runtime_operation_receipt.v1"
    assert cancelled["operation"]["status"] == "accepted"
    assert missing["operation"]["status"] == "session_missing"


def test_dashboard_job_terminal_input_and_reconnect_surface_status(tmp_path) -> None:
    service = _service(tmp_path)
    runtime = FileJobRuntime(root=tmp_path / "jobs")
    job = runtime.start(
        JobRequest(
            task_id="ui-job-terminal-operation",
            provider="codex",
            kind="implementation",
            prompt="Build UI",
            cwd=str(tmp_path),
            metadata={"terminal_ref": "tmux:agent-job", "attach_available": True},
        )
    )

    sent = service.send_job_terminal_input(job.id, "continue")
    snapshot = service.reconnect_job_terminal(job.id)

    assert sent["operation"]["status"] == "accepted"
    assert snapshot["job_id"] == job.id
    assert snapshot["terminal_ref"] == "tmux:agent-job"


def test_dashboard_job_cards_surface_terminal_metadata(tmp_path) -> None:
    service = _service(tmp_path)
    runtime = FileJobRuntime(root=tmp_path / "jobs")
    job = runtime.start(
        JobRequest(
            task_id="ui-job",
            provider="codex",
            kind="implementation",
            prompt="Build UI",
            cwd=str(tmp_path),
            metadata={"terminal_ref": "tmux:agent-job", "attach_available": True},
        )
    )

    detail = service.get_job(job.id)

    assert detail["terminal_ref"] == "tmux:agent-job"
    assert detail["attach_available"] is True


def test_dashboard_job_terminal_snapshot_surfaces_stdout_and_terminal_ref(tmp_path) -> None:
    service = _service(tmp_path)
    runtime = FileJobRuntime(root=tmp_path / "jobs")
    job = runtime.start(
        JobRequest(
            task_id="ui-job-terminal",
            provider="codex",
            kind="implementation",
            prompt="Build terminal UI",
            cwd=str(tmp_path),
            metadata={"terminal_ref": "tmux:agent-terminal", "attach_available": True},
        )
    )
    runtime.complete(job.id, summary="captured", stdout="pane output")

    snapshot = service.get_job_terminal_snapshot(job.id)

    assert snapshot["job_id"] == job.id
    assert snapshot["terminal_ref"] == "tmux:agent-terminal"
    assert snapshot["attach_available"] is True
    assert snapshot["stdout"] == "pane output"


def test_dashboard_service_can_use_tmux_job_runtime(tmp_path) -> None:
    service = build_dashboard_service(
        plans_root=str(tmp_path / "plans"),
        runs_root=str(tmp_path / "runs"),
        jobs_root=str(tmp_path / "jobs"),
        runtime="tmux",
    )

    assert service.health()["job_runtime"] == "TmuxJobRuntime"


def test_dashboard_actions_execute_and_read_run(tmp_path) -> None:
    service = _service(tmp_path)
    session = service.create_session("Build a persisted plan artifact")
    session = service.mark_draft_ready(str(session["id"]))
    session = service.submit_draft_for_review(str(session["id"]))
    session = service.approve_session(str(session["id"]))

    executed = service.execute_session(str(session["id"]), mode=OrchestrationMode.SUCCESS_FIRST.value)
    run_id = executed["resume"]["linked_execution_run_id"]
    run = service.get_run(run_id)

    assert executed["status"] in {"accepted", "needs_followup"}
    assert run["run_id"] == run_id
    assert run["metadata"]["approved_plan"]["session_id"] == session["id"]
    assert run["metadata"]["team_execution_mode"] == "native"
    assert run["payload"]["runtime_name"] == "coding_agent"
    assert run["payload"]["native_task_proof"]["native_runtime_only"] is True
    assert any(event["payload"].get("action") == "execute" for event in service.list_session_events(str(session["id"]))["events"])
    assert service.list_events()["events"]
    assert any(record["record_type"] == "action" for record in service.list_session_memory(str(session["id"]))["records"])
    assert service.list_memory()["records"]
    assert service.search_memory("Build persisted")["records"]
    assert service.list_session_messages(str(session["id"]))["messages"]

    detail = service.get_session(str(session["id"]))
    operator = detail["operator_summary"]
    assert operator["execution_provenance"]["plan_session_id"] == session["id"]
    assert operator["execution_provenance"]["linked_run_status"] in {"completed", "blocked"}
    assert "execution_runtime_summary" in operator
    assert operator["execution_runtime_summary"]["runtime_name"] == "coding_agent"
    assert operator["execution_runtime_summary"]["native_runtime_only"] is True
    assert operator["execution_runtime_summary"]["repo_task_acceptance_ready"] is False
    assert operator["execution_runtime_summary"]["complex_repo_task_acceptance_ready"] is False
    assert operator["execution_runtime_summary"]["default_path"] == "native"
    assert operator["execution_runtime_summary"]["operating_boundary"] == "native_preferred"
    assert operator["execution_runtime_summary"]["selection_reason"]
    assert operator["comparative_benchmark_summary"]["format"] == "agent_orchestrator.comparative_benchmark_summary.v1"
    assert operator["comparative_benchmark_summary"]["native_default_path"] is True
    assert operator["comparative_benchmark_summary"]["native_complex_repo_task_acceptance_ready"] is False
    assert operator["execution_runtime_summary"]["context_engineering_contract_format"] == "agent_orchestrator.context_engineering_contract.v1"
    assert operator["execution_runtime_summary"]["context_engineering_main_path_required"] is True
    assert operator["execution_runtime_summary"]["context_isolation_reinjection_mode"] in {"full_inline_context", "digest_focus_subset", None}
    assert operator["execution_runtime_summary"]["native_tool_trace_count"] >= 1
    assert operator["execution_runtime_summary"]["runtime_cost_measurement_status"] == "placeholder"
    assert operator["execution_runtime_summary"]["session_resume_kind"] == "resume_if_same_task"
    assert operator["execution_runtime_summary"]["session_long_horizon_posture"]["resume_ready"] is True
    assert operator["execution_runtime_summary"]["program_posture"]["program_goal"]
    assert "selected_executor" in operator["execution_runtime_summary"]["delegation_contract"]
    assert "verification_status" in operator["execution_runtime_summary"]["milestone_verification"]
    assert "next_recommended_action" in operator["execution_runtime_summary"]["operator_control"]
    assert operator["execution_runtime_summary"]["native_exploration"]["candidate_path_count"] >= 1
    assert operator["execution_runtime_summary"]["native_exploration"]["candidate_reason"] in {
        "explicit_existing_paths",
        "search_matches",
        "repo_map_fallback",
    }
    assert operator["execution_runtime_summary"]["adapter_capability"]["comparison_mode"] == "same_contract_two_executors"
    assert operator["execution_runtime_summary"]["adapter_capability"]["hot_plug_supported"] is True
    assert operator["execution_runtime_summary"]["step_loop_context_surfaces"] == [
        "select",
        "structured_observation",
        "compact",
        "resume_continuity",
    ]
    assert operator["work_graph_summary"]["node_count"] >= 1
    assert service.list_messages()["messages"]


def test_dashboard_reads_native_team_execute_runtime_summary(tmp_path) -> None:
    service = _service(tmp_path)
    session = service.create_session("Build a persisted plan artifact")
    session = service.mark_draft_ready(str(session["id"]))
    session = service.submit_draft_for_review(str(session["id"]))
    session = service.approve_session(str(session["id"]))

    team = service.team
    executed = team.execute(str(session["id"]), OrchestrationMode.SUCCESS_FIRST, execution_mode="native")
    detail = service.get_session(str(executed.id))

    assert detail["operator_summary"]["execution_runtime_summary"]["runtime_name"] == "coding_agent"
    assert detail["operator_summary"]["execution_runtime_summary"]["native_runtime_only"] is True
    assert detail["operator_summary"]["execution_runtime_summary"]["task_class"] == "bounded_internal_repo_task"
    assert detail["operator_summary"]["execution_runtime_summary"]["context_select_strategy"] == "fixed_runtime_sources"
    assert detail["operator_summary"]["execution_runtime_summary"]["context_compaction_stage"] is not None
    assert detail["operator_summary"]["execution_runtime_summary"]["planner_family"] == "native"
    assert detail["operator_summary"]["execution_runtime_summary"]["planner_decision_format"] == "agent_orchestrator.native_planner_decision.v1"
    assert detail["operator_summary"]["execution_runtime_summary"]["planner_native_work_units"] is True
    assert detail["operator_summary"]["execution_runtime_summary"]["adapter_family"] == "native_first_party"
    assert detail["operator_summary"]["execution_runtime_summary"]["session_compaction_stage"] is not None
    assert detail["operator_summary"]["execution_runtime_summary"]["native_tool_trace_count"] >= 1
    assert detail["operator_summary"]["comparative_benchmark_summary"]["format"] == "agent_orchestrator.comparative_benchmark_summary.v1"


def test_dashboard_rejects_unavailable_session_action(tmp_path) -> None:
    service = _service(tmp_path)
    session = service.create_session("Build a persisted plan artifact")

    try:
        service.approve_session(str(session["id"]))
    except ValueError as exc:
        assert "不允许执行" in str(exc)
    else:
        raise AssertionError("approve_session should reject an approved session")


def test_dashboard_sessions_empty_when_index_missing(tmp_path) -> None:
    service = _service(tmp_path)

    assert service.list_sessions() == {"sessions": []}
    assert service.list_jobs() == {"jobs": []}


def test_dashboard_role_groups_map_session_jobs_to_layers(tmp_path) -> None:
    service = _service(tmp_path)
    session = service.create_session("Build a persisted plan artifact")

    detail = service.get_session(str(session["id"]))
    groups = {group["layer"]: group for group in detail["role_groups"]}
    review_cards = groups["review"]["cards"]
    decision_cards = groups["decision"]["cards"]
    runtime_cards = groups["runtime"]["cards"]

    assert decision_cards[0]["role"] == "lead"
    assert decision_cards[0]["layer_label"] == "治理层"
    assert any(card["role"] == "reviewer" for card in review_cards)
    assert any(card["role"] == "adversarial_reviewer" for card in review_cards)
    assert runtime_cards[0]["role"] == "runtime"
    assert review_cards[0]["attach_available"] is False
    assert review_cards[0]["terminal_ref"] is None


def test_dashboard_governance_summary_surfaces_topology_and_recovery(tmp_path) -> None:
    service = _service(tmp_path)
    session = service.create_session("Build a persisted plan artifact")

    summary = service.get_session(str(session["id"]))["governance_summary"]

    assert summary["selected_topology"]
    assert isinstance(summary["selected_provider_runtime"], dict)
    assert summary["primary_action"] == "mark_draft_ready"
    assert isinstance(summary["blocking"], bool)
    assert isinstance(summary["recovery_actions"], list)
    assert summary["recovery_action_count"] == len(summary["recovery_actions"])
    assert summary["recovery_dashboard"]["read_only"] is True
    assert "current_status" in summary["recovery_dashboard"]
    assert summary["gate_status"] in {"open", "approved", "blocked", "needs_revision", "completed"}
    assert summary["review_intensity"] in {"standard", "reviewed", "strict"}
    assert isinstance(summary["recommended_commands"], list)
    assert summary["recommended_command_count"] == len(summary["recommended_commands"])
    assert "compliance_status" in summary


def test_dashboard_plan_tree_includes_subtasks_rounds_and_execution(tmp_path) -> None:
    service = _service(tmp_path)
    session = service.create_session("Build a persisted plan artifact")
    detail = service.get_session(str(session["id"]))
    children = detail["plan_tree"]["children"]

    assert any(node["kind"] == "subtask" for node in children)
    review_nodes = [node for node in children if node["kind"] == "review_round"]
    assert review_nodes
    assert any(node["related_agent_ids"] for node in review_nodes)

    session = service.mark_draft_ready(str(session["id"]))
    session = service.submit_draft_for_review(str(session["id"]))
    session = service.approve_session(str(session["id"]))
    executed = service.execute_session(str(session["id"]), mode=OrchestrationMode.SUCCESS_FIRST.value)
    executed_detail = service.get_session(str(executed["id"]))
    executed_children = executed_detail["plan_tree"]["children"]

    assert any(node["kind"] == "execution_run" for node in executed_children)
    assert any(action["id"] == "inspect_execution" and action["enabled"] for action in executed_detail["actions"])


def test_dashboard_falls_back_when_work_graph_is_missing(tmp_path) -> None:
    service = _service(tmp_path)
    session = service.create_session("Build a persisted plan artifact")
    graph_path = Path(tmp_path / "plans" / str(session["id"]) / "work_graph.json")
    graph_path.unlink()

    detail = service.get_session(str(session["id"]))

    assert detail["work_graph"] is None
    assert detail["plan_tree"]["kind"] == "session"
    assert detail["plan_tree"]["children"]


def test_dashboard_role_groups_prefer_persisted_work_graph(tmp_path) -> None:
    service = _service(tmp_path)
    session = service.create_session("Build a persisted plan artifact")

    detail = service.get_session(str(session["id"]))
    groups = {group["layer"]: group for group in detail["role_groups"]}

    assert detail["work_graph"]["session_id"] == session["id"]
    assert "schedulable_nodes" in detail["work_graph"]
    assert any(card["role"] == "builder" for card in groups["execution"]["cards"])
    lead_cards = [card for card in groups["decision"]["cards"] if card["role"] == "lead"]
    assert lead_cards
    assert lead_cards[0]["outbox_count"] >= 1
    assert lead_cards[0]["latest_message_summary"]
    assert any(card["role"] == "runtime" for card in groups["runtime"]["cards"])


def test_dashboard_summarizes_coding_agent_execution_artifacts(tmp_path) -> None:
    service = _service(tmp_path)
    session = service.create_session("Build a persisted plan artifact")
    plan_id = str(session["id"])
    run_id = "coding-run-1"
    service.team.orchestrator.run_store.write(
        run_id,
        {
            "run_id": run_id,
            "parent_run_id": None,
            "requirement": "Fix the login handler",
            "initial_mode": "success_first",
            "final_mode": "success_first",
            "attempts": [],
            "reroute_history": [],
            "accepted": False,
            "final_state": None,
            "status": "blocked",
            "reroute_enabled": True,
            "events": [],
            "jobs": [],
            "job_ids": [],
            "job_status_summary": {},
            "active_attempt_id": None,
            "lineage": [],
            "metadata": {
                "provenance": {
                    "plan_session_id": plan_id,
                    "linked_execution_run_id": run_id,
                }
            },
                "payload": {
                    "runtime_name": "coding_agent",
                    "execution_mode": "coding_agent",
                    "planner_family": "native",
                    "adapter_contract": {
                        "adapter_family": "native_first_party",
                        "agent_kind": "coding_agent",
                    },
                    "kernel_contract": {
                        "kernel_name": "coding_agent",
                        "kernel_role": "governed_execution_kernel",
                        "state_authority": "control_plane",
                        "output_surfaces": ["execution_result", "runtime_event_stream", "recovery_projection"],
                },
                "step_loop_contract": {
                    "loop_model": "explicit_stage_step_loop",
                    "status": "blocked",
                    "current_stage": "verify",
                    "current_disposition": "block",
                    "resume_supported": True,
                },
                    "native_task_proof": {
                        "format": "agent_orchestrator.native_task_proof.v1",
                        "native_runtime_only": True,
                        "external_coding_agent_required": False,
                        "task_class": "bounded_internal_repo_task",
                        "closure_status": "blocked",
                        "artifact_count": 2,
                        "event_count": 11,
                    },
                "verification": {
                    "status": "failed",
                    "failure_kind": "nonzero_exit",
                },
                "repair_summary": {
                    "attempt_count": 2,
                    "outcome": "failed",
                },
                "recovery_summary": {
                    "action": "inspect_and_retry_later",
                    "reason": "nonzero_exit",
                    "human_review_recommended": True,
                },
                "attempt_memory": [
                    {"verification": {"status": "failed"}},
                    {"verification": {"status": "failed"}},
                ],
            },
        },
    )
    stored = service.team.status(plan_id)
    stored.resume.linked_execution_run_id = run_id
    service.team.store.write_session(stored)

    detail = service.get_session(plan_id)

    assert detail["evidence_summary"]["execution_runtime"] == "coding_agent"
    assert detail["evidence_summary"]["verification_status"] == "failed"
    assert detail["evidence_summary"]["repair_attempt_count"] == 2
    assert detail["operator_summary"]["execution_runtime_summary"]["runtime_name"] == "coding_agent"
    assert detail["operator_summary"]["execution_runtime_summary"]["kernel_role"] == "governed_execution_kernel"
    assert detail["operator_summary"]["execution_runtime_summary"]["kernel_state_authority"] == "control_plane"
    assert "runtime_event_stream" in detail["operator_summary"]["execution_runtime_summary"]["kernel_output_surfaces"]
    assert detail["operator_summary"]["execution_runtime_summary"]["step_loop_model"] == "explicit_stage_step_loop"
    assert detail["operator_summary"]["execution_runtime_summary"]["step_loop_status"] == "blocked"
    assert detail["operator_summary"]["execution_runtime_summary"]["step_loop_stage"] == "verify"
    assert detail["operator_summary"]["execution_runtime_summary"]["step_loop_context_surfaces"] == [
        "select",
        "structured_observation",
        "compact",
        "resume_continuity",
    ]
    assert detail["operator_summary"]["execution_runtime_summary"]["native_runtime_only"] is True
    assert detail["operator_summary"]["execution_runtime_summary"]["external_coding_agent_required"] is False
    assert detail["operator_summary"]["execution_runtime_summary"]["task_class"] == "bounded_internal_repo_task"
    assert detail["operator_summary"]["execution_runtime_summary"]["planner_family"] == "native"
    assert detail["operator_summary"]["execution_runtime_summary"]["adapter_family"] == "native_first_party"
    assert detail["operator_summary"]["execution_runtime_summary"]["closure_status"] == "blocked"
    assert detail["operator_summary"]["execution_runtime_summary"]["proof_artifact_count"] == 2
    assert detail["operator_summary"]["execution_runtime_summary"]["proof_event_count"] == 11
    assert detail["operator_summary"]["execution_runtime_summary"]["recovery_action"] == "inspect_and_retry_later"
    execution_nodes = [node for node in detail["plan_tree"]["children"] if node["kind"] == "execution_run"]
    assert execution_nodes


def test_dashboard_surfaces_native_dogfood_chain_from_real_pause_resume_run(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    service = _service(tmp_path)
    session = start_approved_session(service.team, "Append \"print('bye')\" to note.py")
    plan_id = str(session.id)

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
    runtime.verify_loop.verifier.action_executor.artifact_store.root = tmp_path / "execution-artifacts"
    runtime.verify_loop.verifier.action_executor.artifact_store.__post_init__()
    runtime.event_store.root = tmp_path / "events"
    runtime.event_store.__post_init__()

    request = ExecutionRequest(
        requirement='Append "print(\'bye\')" to note.py',
        route=TaskRouterResult(
            task_kind=TaskKind.DIRECT_FIX,
            clarify_policy=ClarifyPolicy.LIGHT,
            execution_mode=ExecutionMode.CODING_AGENT,
            ambiguity_level="low",
            risk_level="medium",
            scope_confidence="high",
            needs_repo_context=True,
            requires_human_confirmation=False,
            reasons=["native dogfood chain test"],
        ),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="agent-session-ui-dogfood",
        turn_id="turn-ui-dogfood",
        context_snapshot={"snapshot_id": "snapshot-ui-dogfood"},
        task_contract={
            "id": "task-ui-dogfood",
            "goal": "Append a line with approval and resume",
            "non_goals": [],
            "context": "Use repository context.",
            "inputs": ["Append a line"],
            "outputs": ["native dogfood proof"],
            "acceptance_criteria": ["No syntax errors"],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    first = runtime.run(request)
    edit_approval_id = first.payload["pending_approval"]["approval_id"]
    resolve_approval_item(
        edit_approval_id,
        status="approved",
        reason="Approve edit execution",
        project_root=tmp_path,
        approvals_root=approvals_root,
    )

    second = runtime.run(
        ExecutionRequest(
            requirement=request.requirement,
            route=request.route,
            runtime_name=request.runtime_name,
            mode=request.mode,
            session_id=request.session_id,
            turn_id=request.turn_id,
            context_snapshot=request.context_snapshot,
            task_contract=request.task_contract,
            resume_kind="approval_resume",
        )
    )
    verify_approval_id = second.payload["pending_approval"]["approval_id"]
    resolve_approval_item(
        verify_approval_id,
        status="approved",
        reason="Approve verify execution",
        project_root=tmp_path,
        approvals_root=approvals_root,
    )

    resumed = runtime.run(
        ExecutionRequest(
            requirement=request.requirement,
            route=request.route,
            runtime_name=request.runtime_name,
            mode=request.mode,
            session_id=request.session_id,
            turn_id=request.turn_id,
            context_snapshot=request.context_snapshot,
            task_contract=request.task_contract,
            resume_kind="approval_resume",
        )
    )

    run_id = resumed.run_id
    service.team.orchestrator.run_store.write(
        run_id,
        {
            "run_id": run_id,
            "parent_run_id": None,
            "requirement": request.requirement,
            "initial_mode": "coding_agent",
            "final_mode": "coding_agent",
            "attempts": [],
            "reroute_history": [],
            "accepted": resumed.accepted,
            "final_state": None,
            "status": resumed.status,
            "reroute_enabled": True,
            "events": [],
            "jobs": [],
            "job_ids": [],
            "job_status_summary": {},
            "active_attempt_id": None,
            "lineage": [],
            "metadata": {
                "provenance": {
                    "plan_session_id": plan_id,
                    "linked_execution_run_id": run_id,
                }
            },
            "payload": resumed.payload,
        },
    )
    stored = service.team.status(plan_id)
    stored.resume.linked_execution_run_id = run_id
    service.team.store.write_session(stored)

    detail = service.get_session(plan_id)
    runtime_events = build_runtime_event_stream(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
    )
    execution_run = next(event for event in runtime_events["events"] if event.get("kind") == "execution_run" and event.get("run_id") == run_id)

    assert resumed.status == "completed"
    assert resumed.accepted is True
    assert resumed.payload["native_task_proof"]["native_runtime_only"] is True
    assert resumed.payload["native_task_proof"]["external_coding_agent_required"] is False
    assert resumed.payload["native_task_proof"]["artifact_count"] >= 1
    assert resumed.payload["native_task_proof"]["event_count"] >= 9
    assert detail["control_plane"]["workspace_index"]["execution_artifact_summary"]["native_task_proof"]["native_runtime_only"] is True
    assert detail["control_plane"]["workspace_index"]["comparative_benchmark"]["format"] == "agent_orchestrator.comparative_benchmark_summary.v1"
    assert detail["control_plane"]["workspace_index"]["execution_artifact_summary"]["context_engineering_contract"]["format"] == "agent_orchestrator.context_engineering_contract.v1"
    assert detail["control_plane"]["workspace_index"]["execution_artifact_summary"]["context_isolation_reinjection_mode"] in {"full_inline_context", "digest_focus_subset"}
    assert detail["control_plane"]["workspace_index"]["execution_artifact_summary"]["step_loop_context_surfaces"] == [
        "select",
        "structured_observation",
        "compact",
        "resume_continuity",
    ]
    assert detail["operator_summary"]["execution_runtime_summary"]["native_runtime_only"] is True
    assert detail["operator_summary"]["execution_runtime_summary"]["closure_status"] == "completed"
    assert detail["operator_summary"]["execution_runtime_summary"]["repo_task_acceptance_ready"] is False
    assert detail["operator_summary"]["execution_runtime_summary"]["closure_strength"] == "runtime_closure_only"
    assert detail["operator_summary"]["execution_runtime_summary"]["proof_artifact_count"] >= 1
    assert detail["operator_summary"]["execution_runtime_summary"]["proof_event_count"] >= 9
    assert detail["operator_summary"]["execution_runtime_summary"]["proof_scenario"] == "approval_pause_resume_complete"
    assert execution_run["native_task_proof"]["native_runtime_only"] is True
    assert execution_run["native_task_proof"]["closure_status"] == "completed"


def test_dashboard_surfaces_native_failure_recovery_chain_from_real_runtime_state(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    service = _service(tmp_path)
    session = start_approved_session(service.team, "Inspect note.py after failed verification")
    plan_id = str(session.id)

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    runtime.event_store.root = tmp_path / "events"
    runtime.event_store.__post_init__()
    run_id = "coding-turn-ui-failure"

    runtime.state_store.write(
        run_id,
        {
            "format": "agent_orchestrator.execution_state.v1",
            "runtime_name": "coding_agent",
            "session_id": "agent-session-ui-failure",
            "turn_id": "turn-ui-failure",
            "resume_kind": "approval_resume",
            "status": "blocked",
            "accepted": False,
            "current_stage": "verify",
            "current_step_id": "turn-ui-failure:verify",
            "pending_approval": None,
            "step_statuses": [],
            "resume_contract": {
                "resume_kind": "approval_resume",
                "run_id": run_id,
                "session_id": "agent-session-ui-failure",
                "turn_id": "turn-ui-failure",
                "current_stage": "verify",
                "current_step_id": "turn-ui-failure:verify",
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
            route=TaskRouterResult(
                task_kind=TaskKind.DIRECT_FIX,
                clarify_policy=ClarifyPolicy.LIGHT,
                execution_mode=ExecutionMode.CODING_AGENT,
                ambiguity_level="low",
                risk_level="medium",
                scope_confidence="high",
                needs_repo_context=True,
                requires_human_confirmation=False,
                reasons=["native failure chain test"],
            ),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-ui-failure",
            turn_id="turn-ui-failure",
            context_snapshot={"snapshot_id": "snapshot-ui-failure"},
            task_contract={
                "id": "task-ui-failure",
                "goal": "Inspect a file after failed verification",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Inspect a file"],
                "outputs": ["recovery proof"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    service.team.orchestrator.run_store.write(
        resumed.run_id,
        {
            "run_id": resumed.run_id,
            "parent_run_id": None,
            "requirement": "Inspect note.py",
            "initial_mode": "coding_agent",
            "final_mode": "coding_agent",
            "attempts": [],
            "reroute_history": [],
            "accepted": resumed.accepted,
            "final_state": None,
            "status": resumed.status,
            "reroute_enabled": True,
            "events": [],
            "jobs": [],
            "job_ids": [],
            "job_status_summary": {},
            "active_attempt_id": None,
            "lineage": [],
            "metadata": {
                "provenance": {
                    "plan_session_id": plan_id,
                    "linked_execution_run_id": resumed.run_id,
                }
            },
            "payload": resumed.payload,
        },
    )
    stored = service.team.status(plan_id)
    stored.resume.linked_execution_run_id = resumed.run_id
    service.team.store.write_session(stored)

    detail = service.get_session(plan_id)
    runtime_events = build_runtime_event_stream(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
    )
    execution_run = next(
        event
        for event in runtime_events["events"]
        if event.get("kind") == "execution_run" and event.get("run_id") == resumed.run_id
    )

    assert resumed.status == "blocked"
    assert resumed.accepted is False
    assert resumed.payload["repair_summary"]["outcome"] == "failed"
    assert resumed.payload["recovery_summary"]["action"] == "human_review"
    assert resumed.payload["action_selection_trace"][-1]["source"] == "exhausted_recovery"
    assert resumed.payload["native_task_proof"]["closure_status"] == "blocked"
    assert resumed.payload["native_task_proof"]["recovery_action"] == "human_review"
    assert detail["control_plane"]["workspace_index"]["recovery_timeline"]["format"] == "agent_orchestrator.recovery_timeline.v1"
    assert detail["control_plane"]["workspace_index"]["runtime_events"]["format"] == "agent_orchestrator.runtime_event_stream.v1"
    assert detail["control_plane"]["workspace_index"]["runtime_events"]["summary"]["event_count"] >= 1
    assert detail["operator_summary"]["execution_runtime_summary"]["step_loop_status"] == "blocked"
    assert detail["operator_summary"]["execution_runtime_summary"]["verification_status"] == "failed"
    assert detail["operator_summary"]["execution_runtime_summary"]["recovery_action"] == "human_review"
    assert detail["operator_summary"]["execution_runtime_summary"]["proof_scenario"] == "verify_failure_exhausted_recovery_block"
    assert detail["operator_summary"]["execution_runtime_summary"]["context_isolation_strategy"] in {"inline_context", "subtask_digest", None}
    assert detail["operator_summary"]["execution_runtime_summary"]["context_isolation_reinjection_mode"] in {"full_inline_context", "digest_focus_subset", None}
    assert execution_run["native_task_proof"]["closure_status"] == "blocked"
    assert execution_run["step_loop_contract"]["current_disposition"] == "block"


def test_dashboard_surfaces_native_repair_resume_success_chain(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    service = _service(tmp_path)
    session = start_approved_session(service.team, "Resume note.py verification after repair")
    plan_id = str(session.id)

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    runtime.event_store.root = tmp_path / "events"
    runtime.event_store.__post_init__()

    artifact_root = tmp_path / "execution-artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_root / "verify-success.json"
    artifact_path.write_text('{"status":"passed"}\n', encoding="utf-8")

    class _ResumeRepairVerifier:
        def __init__(self) -> None:
            self.calls = 0

        def run(self, request, edit_intent, command_override=None):
            self.calls += 1
            if self.calls == 1:
                return VerificationReport(
                    status="failed",
                    command=list(command_override or ["python3", "-m", "compileall", "note.py"]),
                    exit_code=1,
                    stdout="",
                    stderr="still failing",
                    failure_kind="nonzero_exit",
                    attempt_index=0,
                )
            return VerificationReport(
                status="passed",
                command=list(command_override or ["python3", "-m", "compileall", "note.py"]),
                exit_code=0,
                stdout="ok",
                stderr="",
                artifact={
                    "artifact_id": "verify-success-artifact",
                    "path": str(artifact_path),
                    "ref": {"format": "agent_orchestrator.execution_command_artifact.v1"},
                },
                attempt_index=1,
            )

    runtime.verify_loop.verifier = _ResumeRepairVerifier()
    run_id = "coding-turn-ui-repair-success"

    runtime.state_store.write(
        run_id,
        {
            "format": "agent_orchestrator.execution_state.v1",
            "runtime_name": "coding_agent",
            "session_id": "agent-session-ui-repair-success",
            "turn_id": "turn-ui-repair-success",
            "resume_kind": "approval_resume",
            "status": "blocked",
            "accepted": False,
            "current_stage": "verify",
            "current_step_id": "turn-ui-repair-success:verify",
            "pending_approval": None,
            "step_statuses": [],
            "resume_contract": {
                "resume_kind": "approval_resume",
                "run_id": run_id,
                "session_id": "agent-session-ui-repair-success",
                "turn_id": "turn-ui-repair-success",
                "current_stage": "verify",
                "current_step_id": "turn-ui-repair-success:verify",
                "pending_approval": None,
                "resume_supported": True,
            },
            "execution_history_summary": {
                "objective": "Repair note.py verification",
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
                    "retry_budget": 2,
                    "attempts": [{"attempt_index": 0}, {"attempt_index": 1}],
                    "recovery_recommendation": {"action": "retry_verify", "reason": "retry_available"},
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
                    "retry_budget": 2,
                    "attempts": [{"attempt_index": 0}, {"attempt_index": 1}],
                    "recovery_recommendation": {"action": "retry_verify", "reason": "retry_available"},
                },
                "recent_observations": [{"kind": "verification", "summary": "previous verify failed"}],
            },
        },
    )

    resumed = runtime.resume_from_state(
        ExecutionRequest(
            requirement="Repair note.py verification",
            route=TaskRouterResult(
                task_kind=TaskKind.DIRECT_FIX,
                clarify_policy=ClarifyPolicy.LIGHT,
                execution_mode=ExecutionMode.CODING_AGENT,
                ambiguity_level="low",
                risk_level="medium",
                scope_confidence="high",
                needs_repo_context=True,
                requires_human_confirmation=False,
                reasons=["native repair resume success test"],
            ),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-ui-repair-success",
            turn_id="turn-ui-repair-success",
            context_snapshot={"snapshot_id": "snapshot-ui-repair-success"},
            task_contract={
                "id": "task-ui-repair-success",
                "goal": "Repair and re-verify a file",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Repair and re-verify a file"],
                "outputs": ["repair success proof"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    service.team.orchestrator.run_store.write(
        resumed.run_id,
        {
            "run_id": resumed.run_id,
            "parent_run_id": None,
            "requirement": "Repair note.py verification",
            "initial_mode": "coding_agent",
            "final_mode": "coding_agent",
            "attempts": [],
            "reroute_history": [],
            "accepted": resumed.accepted,
            "final_state": None,
            "status": resumed.status,
            "reroute_enabled": True,
            "events": [],
            "jobs": [],
            "job_ids": [],
            "job_status_summary": {},
            "active_attempt_id": None,
            "lineage": [],
            "metadata": {
                "provenance": {
                    "plan_session_id": plan_id,
                    "linked_execution_run_id": resumed.run_id,
                }
            },
            "payload": resumed.payload,
        },
    )
    stored = service.team.status(plan_id)
    stored.resume.linked_execution_run_id = resumed.run_id
    service.team.store.write_session(stored)

    detail = service.get_session(plan_id)
    runtime_events = build_runtime_event_stream(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
    )
    execution_run = next(
        event
        for event in runtime_events["events"]
        if event.get("kind") == "execution_run" and event.get("run_id") == resumed.run_id
    )

    assert resumed.status == "completed"
    assert resumed.accepted is True
    assert runtime.verify_loop.verifier.calls == 2
    assert resumed.payload["repair_summary"]["outcome"] == "passed"
    assert resumed.payload["verification"]["status"] == "passed"
    assert resumed.payload["native_task_proof"]["closure_status"] == "completed"
    assert resumed.payload["native_task_proof"]["artifact_count"] >= 1
    assert any(
        "remaining retry budget=1" in note
        for attempt in resumed.payload["repair_summary"]["attempts"]
        for note in attempt.get("notes", [])
    )
    assert detail["control_plane"]["workspace_index"]["execution_artifact_summary"]["native_task_proof"]["closure_status"] == "completed"
    assert detail["operator_summary"]["execution_runtime_summary"]["verification_status"] == "passed"
    assert detail["operator_summary"]["execution_runtime_summary"]["closure_status"] == "completed"
    assert detail["operator_summary"]["execution_runtime_summary"]["proof_artifact_count"] >= 1
    assert detail["operator_summary"]["execution_runtime_summary"]["proof_scenario"] == "verify_failure_repair_resume_success"
    assert detail["operator_summary"]["execution_runtime_summary"]["step_loop_context_surfaces"] == [
        "select",
        "structured_observation",
        "compact",
        "resume_continuity",
    ]
    assert execution_run["native_task_proof"]["closure_status"] == "completed"


def test_dashboard_lists_execution_step_events(tmp_path) -> None:
    route = TaskRouterResult(
        task_kind=TaskKind.DIRECT_FIX,
        clarify_policy=ClarifyPolicy.LIGHT,
        execution_mode=ExecutionMode.CODING_AGENT,
        ambiguity_level="low",
        risk_level="medium",
        scope_confidence="high",
        needs_repo_context=True,
        requires_human_confirmation=False,
        reasons=["ui event visibility test"],
    )
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

    runtime.run(
        ExecutionRequest(
            requirement='Append "print(\'bye\')" to note.py',
            route=route,
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-ui-1",
            turn_id="turn-ui-1",
            context_snapshot={"snapshot_id": "snapshot-ui-1"},
            task_contract={
                "id": "task-ui-1",
                "goal": "Append a line",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": ["Append a line"],
                "outputs": ["ui events"],
                "acceptance_criteria": ["No syntax errors"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
        )
    )

    service = _service(tmp_path)
    events = service.list_session_events("agent-session-ui-1")["events"]

    assert any(event["type"] == "execution.step" for event in events)
    assert any(event["type"] == "execution.action_requested" for event in events)
    assert any(event["type"] == "execution.action_completed" for event in events)
    assert any(event["type"] == "execution.context_compressed" for event in events)
