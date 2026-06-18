import json
from pathlib import Path

from agent_orchestrator import OrchestrationMode
from agent_orchestrator.control_plane import (
    WorkspaceIndexStore,
    build_approval_queue,
    build_context_packet,
    build_evidence_bundle,
    build_execution_topology_snapshot,
    build_governance_bundle,
    build_provider_session_snapshot,
    build_recovery_recommendation,
    build_recovery_timeline,
    build_run_ledger,
    build_runtime_event_stream,
    build_workspace_index,
    build_workspace_state_snapshot,
    inspect_governance_bundle,
    resolve_approval_item,
)
from agent_orchestrator.control_plane_workspace import WorkspaceStateSnapshot, workspace_index_optional_sections
from agent_orchestrator.evidence import WorkflowEvidenceCase, capture_workflow_evidence
from agent_orchestrator.execution import CodingAgentExecutionRuntime, ExecutionRequest
from agent_orchestrator.intake import ClarifyPolicy, ExecutionMode, TaskKind, TaskRouterResult
from agent_orchestrator.jobs import FileJobRuntime, JobRequest
from agent_orchestrator.memory import MemoryRecord, MemoryStore
from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.planning import PlanStore, TeamOrchestrator
from test_support import start_approved_session, start_reviewed_session, write_minimal_process_docs


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "control_plane"


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
        reasons=["control-plane artifact visibility test"],
    )


def test_control_plane_golden_fixtures_pin_minimum_contracts() -> None:
    expected_formats = {
        "empty_workspace_state.json": "agent_orchestrator.workspace_state.v1",
        "active_topology_snapshot.json": "agent_orchestrator.execution_topology_snapshot.v1",
        "blocked_approval_item.json": "agent_orchestrator.approval_item.v1",
        "resolved_approval_item.json": "agent_orchestrator.approval_item.v1",
        "evidence_bundle.json": "agent_orchestrator.evidence_bundle.v1",
    }

    for fixture_name, expected_format in expected_formats.items():
        payload = json.loads((FIXTURE_ROOT / fixture_name).read_text(encoding="utf-8"))
        assert payload["format"] == expected_format

    topology = json.loads((FIXTURE_ROOT / "active_topology_snapshot.json").read_text(encoding="utf-8"))
    assert topology["read_only"] is True
    assert topology["strategy_decision"]["executes"] is False

    approval = json.loads((FIXTURE_ROOT / "blocked_approval_item.json").read_text(encoding="utf-8"))
    assert {"id", "status", "reason_code", "reason", "scope", "scope_id", "recommended_action", "evidence_refs"} <= set(approval)


def test_workspace_state_snapshot_empty_workspace_is_valid(tmp_path) -> None:
    payload = build_workspace_state_snapshot(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
        write_index=True,
    )

    assert payload["format"] == "agent_orchestrator.workspace_state.v1"
    assert payload["plans"] == []
    assert payload["runs"] == []
    assert payload["jobs"] == []
    assert payload["external_cache"]["required"] is False
    assert WorkspaceIndexStore(tmp_path / ".agent_orchestrator" / "workspace").read() is not None


def test_workspace_index_records_control_plane_artifact_lifecycle_refs(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    build_workspace_state_snapshot(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
        write_index=True,
    )
    build_context_packet(
        tmp_path,
        query="workspace lifecycle",
        jobs_root=tmp_path / ".agent_orchestrator" / "jobs",
        memory_root=tmp_path / ".agent_orchestrator" / "memory",
    )
    build_evidence_bundle(tmp_path)

    payload = json.loads((tmp_path / ".agent_orchestrator" / "workspace" / "index.json").read_text(encoding="utf-8"))
    assert payload["format"] == "agent_orchestrator.workspace_index.v1"
    assert payload["workspace_state"]["format"] == "agent_orchestrator.workspace_state.v1"
    assert payload["artifacts"]["workspace_state"]["format"] == "agent_orchestrator.workspace_state.v1"
    assert payload["artifacts"]["context_packet"]["format"] == "agent_orchestrator.context_packet.v1"
    assert payload["artifacts"]["evidence_bundle"]["format"] == "agent_orchestrator.evidence_bundle.v1"
    assert payload["artifacts"]["context_packet"]["digest"]
    assert WorkspaceIndexStore(tmp_path / ".agent_orchestrator" / "workspace").read() is not None


def test_workspace_index_v2_surfaces_operator_current_state(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )
    session = start_reviewed_session(team, "Need a workspace program index")
    session.status = "awaiting_human"
    team.store.write_session(session)

    payload = build_workspace_index(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
        provider_health={"runtime_mode": "mock", "status": "available"},
    )

    assert payload["format"] == "agent_orchestrator.workspace_index.v1"
    assert payload["workspace_state"]["format"] == "agent_orchestrator.workspace_state.v1"
    assert payload["program"]["kind"] == "workspace_program"
    assert payload["program"]["active_plan_count"] >= 1
    assert payload["open_approvals"]
    assert payload["active_artifacts"]["workspace_state"]["format"] == "agent_orchestrator.workspace_state.v1"
    assert isinstance(payload["recent_artifacts"], list)
    assert isinstance(payload["recent_runs"], list)
    assert isinstance(payload["memory_candidates"], list)
    assert payload["provider_runtime_health"]["runtime_mode"] == "mock"
    assert payload["recovery_timeline"]["format"] == "agent_orchestrator.recovery_timeline.v1"
    assert payload["runtime_events"]["format"] == "agent_orchestrator.runtime_event_stream.v1"
    assert payload["recovery_recommendation"]["format"] == "agent_orchestrator.recovery_recommendation.v1"
    assert "blocking" in payload["blocking_summary"]
    assert payload["resume_hint"]
    assert payload["last_checkpoint"]["status"] == "checkpointed"


def test_workspace_index_summarizes_codex_pilot_provider_evidence(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    runtime = FileJobRuntime(tmp_path / "jobs")
    job = runtime.start(
        JobRequest(
            task_id="task-codex-evidence",
            provider="codex",
            kind="implementation",
            prompt="build",
            cwd=str(tmp_path),
        )
    )
    runtime.complete(
        job.id,
        summary="done",
        parsed_payload={
            "codex_exec_json": {
                "format": "agent_orchestrator.codex_exec_json.v1",
                "event_count": 2,
                "malformed_event_count": 0,
                "session_id": "codex-session-1",
            },
            "provider_session_ref": {
                "format": "agent_orchestrator.provider_session_ref.v1",
                "provider": "codex",
                "runtime_id": "codex_exec_json",
                "session_id": "codex-session-1",
                "provider_owned": True,
                "continuation_guarantee": "provider_owned",
            },
            "codex_pilot": {
                "runtime_id": "codex_exec_json",
                "json_events": True,
                "output_last_message": str(tmp_path / "codex-final.txt"),
                "final_message_source": "output_last_message",
            },
        },
        exit_code=0,
    )

    payload = build_workspace_index(tmp_path, jobs_root=tmp_path / "jobs")
    summary = payload["provider_evidence_summary"]

    assert summary["format"] == "agent_orchestrator.provider_evidence_summary.v1"
    assert summary["provider_session_ref_count"] == 1
    assert summary["provider_owned_ref_count"] == 1
    assert summary["codex_exec_json_job_count"] == 1
    assert summary["codex_json_event_count"] == 2
    assert summary["final_message_artifact_count"] == 1
    assert summary["usage_cost_measurement_status"] == "placeholder"
    assert summary["session_ownership_claim"] == "provider_owned"


def test_governance_bundle_exports_portable_externalized_artifacts(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    _ = build_governance_bundle(
        tmp_path,
        query="externalized governance",
        changed_files=["src/agent_orchestrator/control_plane.py"],
        output_path=tmp_path / "governance-bundle.json",
        compliance={"blocking": False, "blocking_reasons": [], "warnings": []},
    )

    payload = json.loads((tmp_path / "governance-bundle.json").read_text(encoding="utf-8"))
    inspection = inspect_governance_bundle(tmp_path / "governance-bundle.json")

    assert payload["format"] == "agent_orchestrator.governance_bundle.v1"
    assert payload["externalization"]["portable"] is True
    assert payload["externalization"]["offline_inspectable"] is True
    assert payload["boundaries"]["provider_session_ownership"] == "provider_owned_refs_are_evidence_only"
    assert payload["artifacts"]["workspace_index"]["format"] == "agent_orchestrator.workspace_index.v1"
    assert payload["artifacts"]["context_packet"]["format"] == "agent_orchestrator.context_packet.v1"
    assert payload["artifacts"]["evidence_bundle"]["format"] == "agent_orchestrator.evidence_bundle.v1"
    assert payload["artifacts"]["approval_queue"]["format"] == "agent_orchestrator.approval_queue.v1"
    assert payload["artifacts"]["provider_evidence_summary"]["format"] == "agent_orchestrator.provider_evidence_summary.v1"
    assert inspection["format"] == "agent_orchestrator.governance_bundle_inspection.v1"
    assert inspection["complete"] is True
    assert inspection["auditable"] is True
    assert inspection["blocking"] is False


def test_context_packet_combines_docs_and_memory_without_strategy(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    MemoryStore(tmp_path / ".agent_orchestrator" / "memory").append(
        namespace="research",
        session_id="plan-1",
        record_type="note",
        summary="workspace state and context packet should stay separate from strategy",
        provenance={"source_artifacts": ["docs/process/context-map.md"], "base_commit": "abc"},
        freshness="fresh",
        confidence=0.9,
    )

    payload = build_context_packet(
        tmp_path,
        query="workspace state context packet",
        changed_files=["src/agent_orchestrator/control_plane.py"],
        jobs_root=tmp_path / ".agent_orchestrator" / "jobs",
        memory_root=tmp_path / ".agent_orchestrator" / "memory",
    )

    assert payload["format"] == "agent_orchestrator.context_packet.v1"
    assert payload["docs_context"]["format"] == "agent_orchestrator.docs_context.v1"
    assert payload["memory_records"]
    assert payload["retrieval_assessment"]["freshness_summary"] in {"fresh", "mixed"}
    assert payload["retrieval_assessment"]["authority_summary"] in {"canonical_docs_plus_memory", "canonical_docs", "memory_only", "limited"}
    assert payload["source_conflict_summary"]["conflict_level"] in {"none", "low", "medium"}
    assert "docs_support" in payload["evidence_support_matrix"]
    assert payload["token_budget_summary"]["policy"].startswith("minimum sufficient context")


def test_topology_snapshot_is_read_only_and_links_approval_evidence(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )
    team.orchestrator.run_store.root = tmp_path / "runs"
    session = start_approved_session(team, "Implement workspace telemetry summaries")
    executed = team.execute(session.id, OrchestrationMode.SUCCESS_FIRST)

    payload = build_execution_topology_snapshot(
        executed,
        plans_root=tmp_path / "plans",
        approvals_root=tmp_path / "approvals",
        project_root=tmp_path,
    )

    assert payload["format"] == "agent_orchestrator.execution_topology_snapshot.v1"
    assert payload["read_only"] is True
    assert {"state", "context", "strategy", "manager_slot", "evidence", "memory"} <= set(payload["fixed_node_types"])
    assert {"implementation", "review", "rescue", "condition", "approval"} <= set(payload["fixed_node_types"])
    assert payload["blueprint"]["read_only"] is True
    assert payload["blueprint"]["export_policy"] == "snapshot only; topology editing is out of scope"
    assert payload["lanes"]
    assert isinstance(payload["approval_points"], list)
    assert payload["evidence_points"]
    assert payload["runtime_boundaries"][0]["authority"] == "approved_plan_gate"
    assert payload["strategy_decision"]["executes"] is False
    assert payload["strategy_decision"]["control_plane_focus"] == "state_context_strategy_topology_approval_evidence_memory_recovery"
    assert payload["strategy_decision"]["topology_policy"]["signals"]
    assert payload["strategy_decision"]["route_planner_intent"]["native_first"] is True
    assert payload["strategy_decision"]["adapter_shared_contract"]["format"] == "agent_orchestrator.adapter_shared_contract.v1"
    assert payload["strategy_decision"]["adapter_shared_contract"]["comparison_mode"] == "same_contract_two_executors"
    assert payload["strategy_decision"]["runtime_health"]["records_only"] is True
    assert payload["strategy_decision"]["tool_inventory"]["mutation_policy"].startswith("inventory only")
    assert payload["strategy_decision"]["usage_cost"]["source"] == "placeholder"
    assert payload["program_posture"]["program_goal"]
    assert "selected_executor" in payload["delegation_contract"]
    assert "verification_status" in payload["milestone_verification"]
    assert "next_recommended_action" in payload["operator_control"]
    assert payload["session_planner_decision"]["format"] == "agent_orchestrator.session_planner_snapshot.v1"
    assert payload["session_planner_decision"]["autonomy_posture"]["pause_expected"] in {True, False}
    assert payload["session_planner_decision"]["tool_workflow_plan"]["workflow_projection_required"] in {True, False}
    assert payload["session_continuity_outline"]["format"] == "agent_orchestrator.session_continuity_outline.v1"
    assert payload["session_continuity_outline"]["autonomy_posture"]["resume_posture"] in {
        "fresh_entry",
        "same_task_resume",
        "approval_reentry",
        None,
    }
    assert payload["evidence_bundle"]["format"] == "agent_orchestrator.evidence_bundle.v1"


def test_approval_queue_resolve_records_decision_without_execution(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )
    blocked = start_reviewed_session(team, "Need architecture direction before implementation")
    blocked.status = "awaiting_human"
    team.store.write_session(blocked)

    queue = build_approval_queue(tmp_path, plans_root=tmp_path / "plans", approvals_root=tmp_path / "approvals")
    item = queue["items"][0]
    assert queue["inbox_summary"]["pending_count"] >= 1
    assert queue["inbox_summary"]["blocking_count"] >= 0
    assert queue["inbox_summary"]["reason_code_distribution"]["awaiting_human_decision"] >= 1
    assert "team approvals resolve" in queue["inbox_summary"]["recommended_next_command"]
    assert item["plan_ref"] == f"plans/{blocked.id}/session.json"
    assert item["topology_ref"] == f"topology:{blocked.id}"
    assert item["evidence_ref"]
    assert item["memory_candidate_ref"]
    result = resolve_approval_item(
        item["id"],
        status="resolved",
        reason="Documented human decision",
        project_root=tmp_path,
        plans_root=tmp_path / "plans",
        approvals_root=tmp_path / "approvals",
    )

    assert result["resolved_item"]["status"] == "resolved"
    assert result["resolved_item"]["reason_code"] == "awaiting_human_decision"
    assert "execution gates remain authoritative" in result["mutation_policy"]
    memory = MemoryStore(tmp_path / ".agent_orchestrator" / "memory").query(namespace="approval")
    assert memory[0]["provenance"]["source_artifacts"] == [item["id"]]


def test_approval_queue_hydrates_legacy_reason_code() -> None:
    from agent_orchestrator.control_plane import ApprovalItem

    legacy = ApprovalItem.from_dict(
        {
            "id": "approval-legacy",
            "status": "pending",
            "reason": "Compliance blocking: docs drift",
            "scope": "compliance",
            "scope_id": "plan-1",
            "recommended_action": "inspect_compliance",
        }
    )

    assert legacy.reason_code == "compliance_blocking"
    assert legacy.to_dict()["reason_code"] == "compliance_blocking"
    assert legacy.to_dict()["plan_ref"] is None


def test_evidence_bundle_reports_gate_evidence_shape(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    payload = build_evidence_bundle(tmp_path, compliance={"blocking": True, "blocking_reasons": ["docs drift"], "warnings": []})

    assert payload["format"] == "agent_orchestrator.evidence_bundle.v1"
    assert payload["gate_evidence"]["format"] == "agent_orchestrator.gate_evidence.v1"
    assert payload["runtime_health"]["records_only"] is True
    assert payload["provider_evidence_summary"]["format"] == "agent_orchestrator.provider_evidence_summary.v1"
    assert payload["provider_evidence_summary"]["usage_cost_measurement_status"] == "placeholder"
    assert payload["tool_inventory"]["source"] == "control_plane_placeholder"
    assert payload["usage_cost"]["source"] == "placeholder"
    assert "recovery_refs" in payload
    assert payload["compliance"]["blocking"] is True
    recommendation = payload["memory_recommendation"]
    assert recommendation["auto_write"] is False
    assert recommendation["eligible_records"][0]["record_type"] == "compliance_result"
    assert recommendation["candidate_count"] == 9
    assert {candidate["record_type"] for candidate in recommendation["candidates"]} == {
        "durable_outcome",
        "decision",
        "lesson",
        "recovery_note",
        "provider_runtime_health_note",
        "recovery_pattern",
        "runtime_degradation_note",
        "approval_delay_note",
        "compliance_blocking_note",
    }
    assert all(candidate["provenance"]["source_artifacts"] for candidate in recommendation["candidates"])
    assert recommendation["external_cache_status"]["status"] in {"available", "optional_unavailable"}


def test_memory_record_hydrates_legacy_and_provenance_payloads() -> None:
    legacy = MemoryRecord.from_dict({"summary": "legacy", "session_id": "plan-1"})
    current = MemoryRecord.from_dict(
        {
            "summary": "current",
            "session_id": "plan-1",
            "provenance": {"base_commit": "abc"},
            "freshness": "fresh",
            "confidence": 0.8,
            "external_cache_status": {"status": "optional_unavailable"},
        }
    )

    assert legacy.provenance == {}
    assert current.to_dict()["provenance"]["base_commit"] == "abc"
    assert json.loads(json.dumps(current.to_dict()))["freshness"] == "fresh"


def test_dogfood_control_plane_pipeline_links_state_context_strategy_approval_evidence_memory(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )
    active = start_reviewed_session(team, "Build a persisted plan artifact")
    blocked = start_reviewed_session(team, "Need architecture direction before implementation")
    blocked.status = "awaiting_human"
    team.store.write_session(blocked)

    workspace = build_workspace_state_snapshot(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
        write_index=True,
    )
    workspace_index = build_workspace_index(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
    )
    context = build_context_packet(
        tmp_path,
        query="dogfood control plane pipeline",
        jobs_root=tmp_path / ".agent_orchestrator" / "jobs",
        memory_root=tmp_path / ".agent_orchestrator" / "memory",
    )
    topology = build_execution_topology_snapshot(
        active,
        plans_root=tmp_path / "plans",
        approvals_root=tmp_path / "approvals",
        project_root=tmp_path,
    )
    evidence = build_evidence_bundle(tmp_path)
    queue = build_approval_queue(tmp_path, plans_root=tmp_path / "plans", approvals_root=tmp_path / "approvals")
    approval = next(item for item in queue["items"] if item["session_id"] == blocked.id)
    resolved = resolve_approval_item(
        approval["id"],
        status="resolved",
        reason="Dogfood human decision recorded",
        project_root=tmp_path,
        plans_root=tmp_path / "plans",
        approvals_root=tmp_path / "approvals",
    )
    MemoryStore(tmp_path / ".agent_orchestrator" / "memory").append(
        namespace="dogfood",
        session_id=active.id,
        record_type="dogfood_outcome",
        summary="Control-plane dogfood pipeline completed.",
        provenance={"source_artifacts": [active.id, approval["id"], "agent_orchestrator.evidence_bundle.v1"]},
        freshness="fresh",
        confidence=1.0,
    )
    resolved_queue = build_approval_queue(tmp_path, plans_root=tmp_path / "plans", approvals_root=tmp_path / "approvals")
    memory = MemoryStore(tmp_path / ".agent_orchestrator" / "memory").query(namespace="dogfood")

    assert workspace["format"] == "agent_orchestrator.workspace_state.v1"
    assert workspace_index["format"] == "agent_orchestrator.workspace_index.v1"
    assert workspace_index["program"]["kind"] == "workspace_program"
    assert context["format"] == "agent_orchestrator.context_packet.v1"
    assert topology["strategy_decision"]["format"] == "agent_orchestrator.strategy_decision.v1"
    assert topology["blueprint"]["read_only"] is True
    assert topology["run_ledger"]["format"] == "agent_orchestrator.run_ledger.v1"
    assert queue["inbox_summary"]["pending_count"] >= 1
    assert topology["strategy_decision"]["executes"] is False
    assert topology["strategy_decision"]["route_planner_intent"]["native_first"] is True
    assert topology["strategy_decision"]["adapter_shared_contract"]["format"] == "agent_orchestrator.adapter_shared_contract.v1"
    assert topology["strategy_decision"]["recovery_policy"]["execution_gate_authority"] == "approved_plan_gate"
    assert evidence["memory_recommendation"]["auto_write"] is False
    assert evidence["memory_recommendation"]["candidates"]
    assert resolved["resolved_item"]["status"] == "resolved"
    assert any(item["id"] == approval["id"] and item["status"] == "resolved" for item in resolved_queue["items"])
    assert memory[0]["provenance"]["source_artifacts"] == [active.id, approval["id"], "agent_orchestrator.evidence_bundle.v1"]


def test_run_ledger_records_recovery_statuses_and_links_workspace_index(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )
    awaiting = start_reviewed_session(team, "Need human decision")
    awaiting.status = "awaiting_human"
    team.store.write_session(awaiting)
    awaiting_payload = build_run_ledger(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
    )

    assert awaiting_payload["format"] == "agent_orchestrator.run_ledger.v1"
    statuses = {entry["status"] for entry in awaiting_payload["entries"]}
    assert "awaiting_human" in statuses
    awaiting.status = "needs_revision"
    awaiting.compliance = {"blocking": True, "blocking_reasons": ["docs drift"], "warnings": []}
    team.store.write_session(awaiting)

    payload = build_run_ledger(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
    )
    statuses = {entry["status"] for entry in payload["entries"]}
    assert "compliance_blocking" in statuses
    assert payload["summary"]["entry_count"] >= 1
    index = json.loads((tmp_path / ".agent_orchestrator" / "workspace" / "index.json").read_text(encoding="utf-8"))
    assert index["artifacts"]["run_ledger"]["format"] == "agent_orchestrator.run_ledger.v1"


def test_recovery_timeline_records_operator_recovery_statuses(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )
    session = start_reviewed_session(team, "Need live recovery telemetry")
    session.status = "awaiting_human"
    team.store.write_session(session)

    payload = build_recovery_timeline(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
    )

    assert payload["format"] == "agent_orchestrator.recovery_timeline.v1"
    assert payload["read_only"] is True
    assert {
        "started",
        "checkpointed",
        "awaiting_human",
        "approval_blocked",
        "evidence_blocked",
        "compliance_blocked",
        "provider_degraded",
        "runtime_failed",
        "interrupted",
        "recovery_ready",
        "completed",
    } <= set(payload["status_catalog"])
    assert payload["summary"]["current_status"] == "awaiting_human"
    assert payload["summary"]["resume_hint"]
    assert payload["summary"]["last_checkpoint"]["status"] == "checkpointed"
    index = json.loads((tmp_path / ".agent_orchestrator" / "workspace" / "index.json").read_text(encoding="utf-8"))
    assert index["artifacts"]["recovery_timeline"]["format"] == "agent_orchestrator.recovery_timeline.v1"


def test_runtime_event_stream_records_runtime_intent_result_and_fallback(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    runtime = FileJobRuntime(tmp_path / "jobs")
    job = runtime.start(
        JobRequest(
            task_id="task-runtime",
            provider="claude",
            kind="review",
            prompt="review",
            cwd=str(tmp_path),
            runtime_mode="direct_api",
            metadata={"fallback_reason": "provider unavailable", "degraded_capability_reason": "auth missing"},
        )
    )
    runtime.fail(job.id, summary="review failed", error="auth missing")

    payload = build_runtime_event_stream(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
    )

    assert payload["format"] == "agent_orchestrator.runtime_event_stream.v1"
    assert payload["read_only"] is True
    assert payload["mutation_policy"].startswith("records runtime intent")
    job_event = next(event for event in payload["events"] if event.get("job_id") == job.id)
    assert job_event["runtime_mode"] == "direct_api"
    assert job_event["result_status"] == "failed"
    assert job_event["failure_reason"] == "auth missing"
    assert job_event["degraded_capability_reason"] == "auth missing"
    assert job_event["session_liveness"]["state"] == "terminal"
    assert job_event["operation_support"]["send"] == "already_terminal"
    assert job_event["runtime_measurement"]["measurement_status"] == "measured"
    assert job_event["runtime_measurement"]["exit_code"] is None
    assert job_event["usage_cost"]["source"] == "placeholder"
    assert job_event["usage_cost"]["measurement_status"] == "placeholder"
    assert payload["provider_session_snapshots"][0]["format"] == "agent_orchestrator.provider_session_snapshot.v1"
    index = json.loads((tmp_path / ".agent_orchestrator" / "workspace" / "index.json").read_text(encoding="utf-8"))
    assert index["artifacts"]["runtime_event_stream"]["format"] == "agent_orchestrator.runtime_event_stream.v1"


def test_provider_session_snapshot_records_liveness_and_receipts(tmp_path) -> None:
    runtime = FileJobRuntime(tmp_path / "jobs")
    job = runtime.start(
        JobRequest(
            task_id="task-session",
            provider="codex",
            kind="implementation",
            prompt="build",
            cwd=str(tmp_path),
            runtime_mode="cli_isolated",
        )
    )
    runtime.send(job.id, "continue")

    payload = build_provider_session_snapshot(job.id, tmp_path, jobs_root=tmp_path / "jobs")

    assert payload["format"] == "agent_orchestrator.provider_session_snapshot.v1"
    assert payload["job_id"] == job.id
    assert payload["runtime_mode"] == "cli_isolated"
    assert payload["liveness"]["state"] == "unknown"
    assert payload["runtime_measurement"]["format"] == "agent_orchestrator.runtime_measurement.v1"
    assert payload["runtime_measurement"]["measurement_status"] == "placeholder"
    assert payload["operation_support"]["send"] == "available"
    assert payload["last_operation_receipt"]["format"] == "agent_orchestrator.runtime_operation_receipt.v1"
    assert payload["last_operation_receipt"]["status"] == "accepted"


def test_provider_session_snapshot_exposes_provider_owned_ref(tmp_path) -> None:
    runtime = FileJobRuntime(tmp_path / "jobs")
    job = runtime.start(
        JobRequest(
            task_id="task-session-ref",
            provider="codex",
            kind="implementation",
            prompt="build",
            cwd=str(tmp_path),
        )
    )
    runtime.complete(
        job.id,
        summary="done",
        parsed_payload={
            "provider_session_ref": {
                "format": "agent_orchestrator.provider_session_ref.v1",
                "provider": "codex",
                "runtime_id": "codex_exec_json",
                "session_id": "codex-session-1",
                "thread_id": "codex-thread-1",
                "provider_owned": True,
                "continuation_guarantee": "provider_owned",
            }
        },
        exit_code=0,
    )

    payload = build_provider_session_snapshot(job.id, tmp_path, jobs_root=tmp_path / "jobs")

    assert payload["provider_session_ref"]["format"] == "agent_orchestrator.provider_session_ref.v1"
    assert payload["provider_session_ref"]["runtime_id"] == "codex_exec_json"
    assert payload["provider_session_ref"]["provider_owned"] is True


def test_recovery_recommendation_is_read_only_and_explains_next_step(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )
    session = start_reviewed_session(team, "Need a recovery recommendation")
    session.status = "awaiting_human"
    team.store.write_session(session)

    payload = build_recovery_recommendation(session)

    assert payload["format"] == "agent_orchestrator.recovery_recommendation.v1"
    assert payload["read_only"] is True
    assert payload["human_decision_required"] is True
    assert payload["may_resume_execution"] is False
    assert payload["required_approval_or_evidence"]["approval_required"] is True
    assert payload["safest_next_operator_command"]
    assert "agent_orchestrator.recovery_timeline.v1" in payload["recoverable_artifact_refs"]
    assert payload["program_posture"]["program_goal"] == "Need a recovery recommendation"
    assert payload["delegation_contract"]["selected_executor"] == "human"
    assert payload["session_planner_decision"]["format"] == "agent_orchestrator.session_planner_snapshot.v1"
    assert payload["session_planner_decision"]["autonomy_posture"]["pause_expected"] in {True, False}
    assert payload["session_continuity_outline"]["format"] == "agent_orchestrator.session_continuity_outline.v1"
    assert payload["session_continuity_outline"]["autonomy_posture"]["resume_posture"] in {
        "fresh_entry",
        "same_task_resume",
        "approval_reentry",
        None,
    }
    assert payload["milestone_verification"]["verification_status"] == "blocked"
    assert payload["operator_control"]["approval_pause_state"] is True
    assert payload["branch_candidates"]
    assert payload["recovery_search"]["selected_branch"]
    assert payload["recovery_search"]["candidate_count"] >= 1


def test_recovery_recommendation_exposes_ranked_recovery_branches(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )
    session = start_reviewed_session(team, "Need a recovery recommendation")
    session.status = "awaiting_human"
    team.store.write_session(session)

    payload = build_recovery_recommendation(session)
    branches = payload["branch_candidates"]

    assert branches[0]["score"] >= branches[-1]["score"]
    assert any(branch["selected"] for branch in branches)
    assert all("rationale" in branch for branch in branches)
    assert payload["recovery_search"]["selected_command"] == payload["safest_next_operator_command"]
    assert payload["recovery_search"]["disagreement_level"] in {"low", "medium", "high"}
    assert payload["session_continuity_outline"]["resume_expectation"] is not None


def test_workspace_index_records_execution_artifact_summary_from_coding_runtime(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    target = tmp_path / "note.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = tmp_path
    runtime.edit_executor.workspace_root = tmp_path
    runtime.edit_executor.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.workspace_root = tmp_path
    runtime.verify_loop.verifier.action_executor.artifact_store.root = tmp_path / "execution-artifacts"
    runtime.verify_loop.verifier.action_executor.artifact_store.__post_init__()

    runtime.run(
        ExecutionRequest(
            requirement='Append "print(\'bye\')" to note.py',
            route=_coding_route(),
            runtime_name="coding_agent",
            mode=OrchestrationMode.SUCCESS_FIRST,
            session_id="agent-session-cp-1",
            turn_id="turn-cp-1",
            context_snapshot={"snapshot_id": "snapshot-cp-1"},
            task_contract={
                "id": "task-cp-1",
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

    index = build_workspace_index(
        tmp_path,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
    )
    assert index["artifacts"]["execution_artifacts"]["format"] == "agent_orchestrator.execution_artifact_summary.v1"
    assert index["execution_artifact_summary"]["recent_execution_artifacts"]
    assert index["execution_artifact_summary"]["compressed_context"]["objective"] == 'Append "print(\'bye\')" to note.py'
    assert index["execution_artifact_summary"]["context_engineering_contract"]["format"] == "agent_orchestrator.context_engineering_contract.v1"
    assert index["execution_artifact_summary"]["native_tool_surface"]["format"] == "agent_orchestrator.native_tool_surface.v1"
    assert index["execution_artifact_summary"]["native_tool_surface"]["capability_profile"]["read"]["purpose"] == "bounded file inspection"
    assert index["execution_artifact_summary"]["native_tool_surface"]["capability_profile"]["diff_preview"]["purpose"] == "governed bounded change preview for operator-visible review"
    assert index["execution_artifact_summary"]["native_tool_surface"]["workflow_surface"]["daily_driver_path"]["tools"] == [
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
    assert index["execution_artifact_summary"]["native_tool_surface"]["daily_driver_readiness"]["repo_exploration_ready"] is True
    assert index["execution_artifact_summary"]["native_tool_surface"]["daily_driver_readiness"]["glob_ready"] is True
    assert index["execution_artifact_summary"]["native_tool_surface"]["daily_driver_readiness"]["diff_preview_ready"] is True
    assert index["execution_artifact_summary"]["native_tool_productization_surface"]["format"] == "agent_orchestrator.native_tool_productization_surface.v1"
    assert index["execution_artifact_summary"]["native_tool_productization_surface"]["operator_visibility_ready"] is True
    assert index["execution_artifact_summary"]["native_tool_productization_surface"]["readiness"]["glob_ready"] is True
    assert index["execution_artifact_summary"]["native_tool_productization_surface"]["readiness"]["structural_outline_ready"] is True
    assert index["operator_tool_digest"]["format"] == "agent_orchestrator.operator_tool_digest.v1"
    assert index["operator_tool_digest"]["tooling_posture"] == "daily_driver_ready"
    assert "repo_map" in index["operator_tool_digest"]["daily_driver_tools"]
    assert index["operator_planner_digest"]["format"] == "agent_orchestrator.operator_planner_digest.v1"
    assert index["operator_planner_digest"]["primary_action"]
    assert index["operator_planner_digest"]["selected_executor"] == "native"
    assert index["operator_planner_digest"]["next_recommended_action"]
    assert index["execution_artifact_summary"]["native_tool_workflow_surface"]["edit"]["tools"] == [
        "patch_preview",
        "structured_patch",
        "diff_preview",
    ]
    assert index["execution_artifact_summary"]["native_tool_usage"]["trace_count"] >= 1
    assert index["execution_artifact_summary"]["compacted_context_summary"]["objective"] == 'Append "print(\'bye\')" to note.py'
    assert index["execution_artifact_summary"]["compacted_context_summary"]["compaction_stage"] in {"full_fidelity", "light_compaction", "observation_masking", "summarization_ready"}
    assert index["execution_artifact_summary"]["native_exploration"]["candidate_path_count"] >= 1
    assert index["execution_artifact_summary"]["native_exploration"]["exploration_profile"]["candidate_reason"] in {
        "explicit_existing_paths",
        "search_matches",
        "repo_map_fallback",
    }
    assert index["execution_artifact_summary"]["native_exploration"]["exploration_evidence"]["format"] == "agent_orchestrator.native_exploration_evidence.v1"
    assert "workspace_index" in index["execution_artifact_summary"]["native_exploration"]["exploration_evidence"]["shared_evidence_surface"]
    assert "outline_projection" in index["execution_artifact_summary"]["native_exploration"]["exploration_evidence"]["shared_evidence_surface"]
    assert index["execution_artifact_summary"]["repository_understanding"]["format"] == "agent_orchestrator.repository_understanding.v1"
    assert index["execution_artifact_summary"]["repository_understanding"]["candidate_count"] >= 1
    assert index["execution_artifact_summary"]["repository_understanding"]["candidate_evidence"][0]["selection_reason"]
    assert index["execution_artifact_summary"]["native_exploration"]["repository_understanding"]["format"] == "agent_orchestrator.repository_understanding.v1"
    assert "workspace_index" in index["execution_artifact_summary"]["repository_understanding"]["operator_visibility"]["shared_evidence_surface"]
    assert index["execution_artifact_summary"]["native_tool_evidence"]["format"] == "agent_orchestrator.native_tool_evidence.v1"
    assert index["execution_artifact_summary"]["native_tool_evidence"]["verify_evidence_ready"] is True
    assert index["execution_artifact_summary"]["native_tool_evidence"]["tool_counts"]["verify"] >= 1
    assert "workspace_index" in index["execution_artifact_summary"]["native_tool_evidence"]["shared_evidence_surface"]
    assert index["execution_artifact_summary"]["adapter_shared_contract"]["comparison_mode"] == "same_contract_two_executors"
    assert index["execution_artifact_summary"]["adapter_shared_contract"]["hot_plug_supported"] is True
    assert index["execution_artifact_summary"]["adapter_shared_contract"]["default_path"] == "native"
    assert "workspace_index" in index["execution_artifact_summary"]["adapter_shared_contract"]["shared_evidence_surface"]
    assert index["execution_artifact_summary"]["adapter_shared_contract"]["operator_visibility_contract"]["tool_surface_required"] is True
    assert index["execution_artifact_summary"]["adapter_shared_contract"]["tooling_contract"]["workflow_projection_required"] is True
    assert index["execution_artifact_summary"]["adapter_shared_contract"]["recovery_contract"]["fallback_allowed"] is True
    assert index["execution_artifact_summary"]["adapter_shared_contract"]["operator_recovery_surface"]["default_recovery_lane"] == "approval_pause"
    assert index["execution_artifact_summary"]["adapter_execution_fact"]["format"] == "agent_orchestrator.adapter_execution_fact.v1"
    assert index["execution_artifact_summary"]["adapter_execution_fact"]["default_path"] == "native"
    assert index["execution_artifact_summary"]["adapter_execution_fact"]["source_visibility"]["source_label"] == "native_first_party:coding_agent"
    assert "workspace_index" in index["execution_artifact_summary"]["adapter_execution_fact"]["shared_evidence_surface"]
    assert index["execution_artifact_summary"]["adapter_productization_surface"]["format"] == "agent_orchestrator.adapter_productization_surface.v1"
    assert index["execution_artifact_summary"]["adapter_productization_surface"]["surface_status"] == "same_contract_two_executors_governed"
    assert index["execution_artifact_summary"]["adapter_productization_surface"]["resume_contract_supported"] is True
    assert index["execution_artifact_summary"]["adapter_productization_surface"]["operator_recovery_surface"]["default_recovery_lane"] == "approval_pause"
    assert index["execution_artifact_summary"]["shared_productization_surface"]["format"] == "agent_orchestrator.shared_productization_surface.v1"
    assert index["execution_artifact_summary"]["shared_productization_surface"]["shared_productization_contract_ready"] is True
    assert index["execution_artifact_summary"]["shared_productization_surface"]["contract_readiness"]["session_ready"] is True
    assert index["execution_artifact_summary"]["shared_productization_surface"]["contract_readiness"]["tool_ready"] is True
    assert index["execution_artifact_summary"]["shared_productization_surface"]["contract_readiness"]["adapter_ready"] is True
    assert index["execution_artifact_summary"]["shared_productization_surface"]["contract_readiness"]["planner_ready"] is True
    assert index["execution_artifact_summary"]["shared_productization_surface"]["native_tool_workflow_surface"]["daily_driver_path"]["tools"] == [
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
    assert index["execution_artifact_summary"]["session_continuity"]["resume_supported"] is True
    assert index["execution_artifact_summary"]["session_continuity"]["resume_kind"] in {None, "fresh", "approval_resume"}
    assert index["execution_artifact_summary"]["session_continuity"]["resume_contract"]["resume_supported"] is True
    assert index["execution_artifact_summary"]["session_continuity"]["resume_contract"]["continuity_snapshot"]["format"] == "agent_orchestrator.session_continuity_snapshot.v1"
    assert index["execution_artifact_summary"]["session_continuity"]["resume_contract"]["program_posture"]["program_goal"]
    assert index["execution_artifact_summary"]["resume_contract"]["native_tool_usage"]["trace_count"] >= 1
    assert "find_files" in index["execution_artifact_summary"]["native_complex_repo_task_acceptance"]["complex_task_checks"]["native_exploration_trace_visible"]["evidence"]["explored_tools"]
    assert index["execution_artifact_summary"]["session_continuity"]["long_horizon_posture"]["resume_ready"] is True
    assert index["execution_artifact_summary"]["session_continuity"]["long_horizon_posture"]["resume_posture"] in {
        "fresh_entry",
        "same_task_resume",
        "approval_reentry",
    }
    assert "workspace_index" in index["execution_artifact_summary"]["session_continuity"]["shared_evidence_surface"]
    assert index["execution_artifact_summary"]["session_continuity"]["continuity_snapshot"]["format"] == "agent_orchestrator.session_continuity_snapshot.v1"
    assert index["execution_artifact_summary"]["session_continuity"]["session_productization_surface"]["format"] == "agent_orchestrator.session_productization_surface.v1"
    assert index["execution_artifact_summary"]["session_continuity"]["session_productization_surface"]["continuity_readiness"]["resume_ready"] is True
    assert index["execution_artifact_summary"]["session_continuity"]["comparative_benchmark_digest"]["external_harness_status"] == (
        "missing_authoritative_opencode_harness"
    )
    assert index["execution_artifact_summary"]["session_continuity"]["session_productization_surface"]["comparative_benchmark_digest"]["external_harness_status"] == (
        "missing_authoritative_opencode_harness"
    )
    assert index["execution_artifact_summary"]["session_continuity"]["program_posture"]["program_goal"]
    assert "active_milestone" in index["execution_artifact_summary"]["session_continuity"]["program_posture"]
    assert "selected_executor" in index["execution_artifact_summary"]["session_continuity"]["delegation_contract"]
    assert index["execution_artifact_summary"]["session_continuity"]["program_continuity"]["long_chain_native_first_ready"] is False
    assert index["execution_artifact_summary"]["session_continuity"]["program_continuity"]["closure_strength"] == "runtime_closure_only"
    assert "verification_status" in index["execution_artifact_summary"]["session_continuity"]["milestone_verification"]
    assert "next_recommended_action" in index["execution_artifact_summary"]["session_continuity"]["operator_control"]
    assert index["execution_artifact_summary"]["runtime_cost"]["usage_cost_measurement_status"] == "placeholder"
    assert index["execution_artifact_summary"]["context_isolation_strategy"] in {"inline_context", "subtask_digest"}
    assert index["execution_artifact_summary"]["context_isolation_reinjection_mode"] in {"full_inline_context", "digest_focus_subset"}
    assert index["execution_artifact_summary"]["step_loop_context_surfaces"] == [
        "select",
        "structured_observation",
        "compact",
        "resume_continuity",
    ]
    assert index["execution_artifact_summary"]["native_task_proof"]["format"] == "agent_orchestrator.native_task_proof.v1"
    assert index["execution_artifact_summary"]["native_task_proof"]["native_runtime_only"] is True
    assert index["execution_artifact_summary"]["planner_decision"]["format"] == "agent_orchestrator.session_planner_snapshot.v1"
    assert index["execution_artifact_summary"]["planner_decision"]["autonomy_posture"]["pause_expected"] in {True, False}
    assert index["execution_artifact_summary"]["planner_closure_posture"]["format"] == "agent_orchestrator.planner_closure_posture.v1"
    assert index["execution_artifact_summary"]["planner_closure_posture"]["closure_mode"] in {
        "verify",
        "continue_native",
        "planner_complete",
        "approval_pause",
        "handoff",
        "fallback",
    }
    assert "next_recommended_action" in index["execution_artifact_summary"]["planner_closure_posture"]
    assert index["execution_artifact_summary"]["continuity_outline"]["format"] == "agent_orchestrator.session_continuity_outline.v1"
    assert index["execution_artifact_summary"]["continuity_outline"]["autonomy_posture"]["resume_posture"] in {
        "fresh_entry",
        "same_task_resume",
        "approval_reentry",
        None,
    }
    assert index["execution_artifact_summary"]["planner_shared_contract"]["format"] == "agent_orchestrator.native_planner_decision.v1"
    assert index["execution_artifact_summary"]["planner_shared_contract_summary"]["decision_candidates"]
    assert index["execution_artifact_summary"]["planner_shared_contract_summary"]["decision_boundary"]["risk_level"]
    assert index["execution_artifact_summary"]["planner_shared_contract_summary"]["selected_executor"] == "native"
    assert "edit" in index["execution_artifact_summary"]["planner_shared_contract_summary"]["route_planner_intent"]["priority"]
    assert index["execution_artifact_summary"]["planner_shared_contract_summary"]["autonomy_surface"]["format"] == "agent_orchestrator.native_planner_autonomy_surface.v1"
    assert index["execution_artifact_summary"]["planner_shared_contract_summary"]["autonomy_surface"]["actions"]["edit"]["selected"] is True
    assert index["execution_artifact_summary"]["planner_shared_contract_summary"]["planner_reasoning"]["native_first"] is True
    assert index["execution_artifact_summary"]["planner_shared_contract_summary"]["autonomy_boundary"]["requires_edit"] is True
    assert index["execution_artifact_summary"]["planner_shared_contract_summary"]["planner_reasoning"]["requires_verify"] is True
    assert index["execution_artifact_summary"]["native_repo_task_acceptance"]["format"] == "agent_orchestrator.native_repo_task_acceptance.v1"
    assert index["execution_artifact_summary"]["native_repo_task_acceptance"]["real_repo_task_acceptance_ready"] is False
    assert index["execution_artifact_summary"]["native_complex_repo_task_acceptance"]["format"] == "agent_orchestrator.native_complex_repo_task_acceptance.v1"
    assert index["execution_artifact_summary"]["native_complex_repo_task_acceptance"]["complex_repo_task_ready"] is False
    assert index["execution_artifact_summary"]["adapter_capability_surface"]["format"] == "agent_orchestrator.adapter_capability_surface.v1"
    assert index["execution_artifact_summary"]["adapter_capability"]["format"] == "agent_orchestrator.adapter_capability_surface.v1"
    assert index["execution_artifact_summary"]["adapter_capability"]["comparison_mode"] == "same_contract_two_executors"
    assert "workspace_index" in index["execution_artifact_summary"]["adapter_capability_surface"]["shared_evidence_surface"]
    assert "ui_execution_summary" in index["execution_artifact_summary"]["adapter_capability"]["shared_evidence_surface"]
    assert index["execution_fact_chain"]["format"] == "agent_orchestrator.execution_fact_chain.v1"
    assert index["execution_fact_chain"]["objective"] == 'Append "print(\'bye\')" to note.py'
    assert index["execution_fact_chain"]["resume_supported"] is True
    assert index["execution_fact_chain"]["task_class"] == "bounded_internal_repo_task"
    assert "ui.operator_summary.execution_fact_chain" in index["execution_fact_chain"]["shared_surface_refs"]
    assert index["comparative_benchmark"]["format"] == "agent_orchestrator.comparative_benchmark_summary.v1"
    assert index["comparative_benchmark"]["native_default_path"] is True
    assert index["comparative_benchmark"]["comparative_acceptance_bundle_ready"] is True
    assert index["comparative_benchmark"]["native_coverage_class"] == "bounded_internal_repo_task"
    assert index["comparative_benchmark"]["native_complex_repo_task_acceptance_ready"] is False
    assert index["comparative_benchmark"]["long_chain_native_first_ready"] is False
    assert index["comparative_benchmark"]["daily_driver_main_path_ready"] is False
    assert index["comparative_benchmark"]["daily_driver_readiness"]["shared_productization_ready"] is True
    assert index["comparative_benchmark"]["daily_driver_readiness"]["open_product_gap"] == "long_chain_repo_closure_not_yet_proven"
    assert index["comparative_benchmark"]["comparison_posture"]["status"] == "shared_productization_ready_but_daily_driver_proof_gap_remaining"
    assert index["comparative_benchmark"]["comparison_posture"]["foundation_gap_remaining"] is False
    assert "platform_breadth" in index["comparative_benchmark"]["comparison_posture"]["remaining_gap_classes"]
    assert index["comparative_benchmark"]["comparison_posture_basis"]["shared_productization_contract_ready"] is True
    assert index["comparative_benchmark"]["comparison_posture_basis"]["daily_driver_main_path_ready"] is False
    assert index["comparative_benchmark"]["comparison_posture_basis"]["planner_candidate_surface_ready"] is True
    assert index["comparative_benchmark"]["comparison_posture_basis"]["unified_adapter_contract_ready"] is True
    assert "shared_contract_alignment" in index["comparative_benchmark"]["comparison_posture_basis"]["basis_surface_refs"]
    assert "planner_candidate_surface_ready" in index["comparative_benchmark"]["comparison_posture_basis"]["basis_surface_refs"]
    assert "unified_adapter_contract_ready" in index["comparative_benchmark"]["comparison_posture_basis"]["basis_surface_refs"]
    assert "session_productization_surface" in index["comparative_benchmark"]["shared_evidence_surface"]
    assert "native_tool_productization_surface" in index["comparative_benchmark"]["shared_evidence_surface"]
    assert "adapter_productization_surface" in index["comparative_benchmark"]["shared_evidence_surface"]
    assert "planner_autonomy_boundary" in index["comparative_benchmark"]["shared_evidence_surface"]
    assert "planner_reasoning" in index["comparative_benchmark"]["shared_evidence_surface"]
    assert index["comparative_benchmark"]["comparison_proof_strength"]["direct_proof_status"] == "foundational_productization_only"
    assert index["comparative_benchmark"]["comparison_proof_strength"]["repeatability_ready"] is False
    assert index["comparative_benchmark"]["comparison_proof_strength"]["planner_candidate_status"] == "native_first_candidate_surface_ready"
    assert index["comparative_benchmark"]["comparison_proof_strength"]["adapter_unification_status"] == "same_contract_adapter_surface_ready"
    assert index["comparative_benchmark"]["comparison_grade_assessment"]["status"] == "internal_productization_ready_but_repeatability_or_external_gap_remaining"
    assert index["comparative_benchmark"]["comparison_grade_assessment"]["comparison_grade_ready"] is False
    assert index["comparative_benchmark"]["comparison_grade_assessment"]["external_harness_ready"] is False
    assert index["comparative_benchmark"]["comparison_grade_assessment"]["external_comparison_harness_surface"]["format"] == "agent_orchestrator.external_comparison_harness_surface.v1"
    assert index["comparative_benchmark"]["external_comparison_harness_surface"]["harness_status"] == "missing_authoritative_opencode_harness"
    assert index["comparative_benchmark"]["external_comparison_harness_surface"]["operator_action"] == "maintain_human_audit_until_external_harness_ready"
    assert index["comparative_daily_driver_benchmark"] is None
    assert index["comparative_benchmark"]["shared_contract_alignment"]["session_continuity_ready"] is True
    assert index["comparative_benchmark"]["shared_contract_alignment"]["planner_evidence_ready"] is True
    assert index["comparative_benchmark"]["shared_contract_alignment"]["adapter_contract_ready"] is True
    assert index["comparative_benchmark"]["shared_contract_alignment"]["native_tool_usage_ready"] is True
    assert index["comparative_benchmark"]["shared_productization_contract_ready"] is True
    assert "workspace_index" in index["comparative_benchmark"]["shared_evidence_surface"]
    assert "adapter_shared_contract" in index["comparative_benchmark"]["shared_evidence_surface"]
    assert "cli_execution_summary" in index["comparative_benchmark"]["shared_evidence_surface"]
    assert index["comparative_benchmark_digest"]["native_default_path"] is True
    assert index["comparative_benchmark_digest"]["case_count"] == 1
    assert index["comparative_benchmark_digest"]["productization_case_count"] == 1
    assert index["comparative_benchmark_digest"]["daily_driver_main_path_ready"] is False
    assert index["comparative_benchmark_digest"]["daily_driver_main_path_ready_cases"] == 0
    assert index["comparative_benchmark_digest"]["comparison_status"] == "shared_productization_ready_but_daily_driver_proof_gap_remaining"
    assert index["comparative_benchmark_digest"]["planner_candidate_surface_ready"] is True
    assert index["comparative_benchmark_digest"]["planner_candidate_status"] == "native_first_candidate_surface_ready"
    assert index["comparative_benchmark_digest"]["unified_adapter_contract_ready"] is True
    assert index["comparative_benchmark_digest"]["adapter_unification_status"] == "same_contract_adapter_surface_ready"
    assert index["comparative_benchmark_digest"]["evidence_scope"] == "bounded_internal_evidence_only"
    assert index["comparative_benchmark_digest"]["direct_proof_status"] == "foundational_productization_only"
    assert index["comparative_benchmark_digest"]["repeatability_status"] == "not_yet_proven"
    assert index["comparative_benchmark_digest"]["stronger_task_families"] == []
    assert index["comparative_benchmark_digest"]["repo_task_acceptance_families_proven"] == []
    assert index["comparative_benchmark_digest"]["repo_task_acceptance_family_count"] is None
    assert index["comparative_benchmark_digest"]["daily_driver_repo_task_families_proven"] == []
    assert index["comparative_benchmark_digest"]["daily_driver_repo_task_family_count"] == 0
    assert index["comparative_benchmark_digest"]["session_posture_cases"] == 1
    assert index["comparative_benchmark_digest"]["comparison_grade_status"] == "internal_productization_ready_but_repeatability_or_external_gap_remaining"
    assert index["comparative_benchmark_digest"]["comparison_grade_ready"] is False
    assert index["comparative_benchmark_digest"]["external_harness_ready"] is False
    assert index["comparative_benchmark_digest"]["external_harness_status"] == "missing_authoritative_opencode_harness"
    assert index["comparative_planner_closure_summary"]["format"] == "agent_orchestrator.comparative_planner_closure_summary.v1"
    assert index["comparative_planner_closure_summary"]["closure_mode"]
    assert "mode=" in index["comparative_planner_closure_summary"]["summary"]
    assert index["comparative_planner_autonomy_summary"]["format"] == "agent_orchestrator.comparative_planner_autonomy_summary.v1"
    assert index["comparative_planner_autonomy_summary"]["native_first"] is True
    assert index["comparative_planner_autonomy_summary"]["autonomy_boundary"]["requires_edit"] is True
    assert index["comparative_planner_autonomy_summary"]["planner_reasoning"]["requires_verify"] is True
    assert index["comparative_planner_candidate_summary"]["format"] == "agent_orchestrator.comparative_planner_candidate_summary.v1"
    assert index["comparative_planner_candidate_summary"]["native_first"] is True
    assert index["comparative_planner_candidate_summary"]["selected_strategy"]
    assert index["comparative_planner_candidate_summary"]["workflow_projection_ready"] is True
    assert isinstance(index["comparative_planner_candidate_summary"]["decision_candidates"], list)
    assert index["comparative_planner_candidate_summary"]["action_coverage"]["autonomy_selected_action_count"] >= 1
    assert index["comparative_benchmark_digest"]["operator_planner_decision_mode"] == "native_first_autonomous"
    assert index["comparative_benchmark_digest"]["operator_planner_candidate_count"] >= 1
    assert index["comparative_benchmark_digest"]["planner_candidate_autonomy_selected_action_count"] >= 1
    assert index["comparative_native_tool_summary"]["format"] == "agent_orchestrator.comparative_native_tool_summary.v1"
    assert index["comparative_native_tool_summary"]["tooling_posture"] == "daily_driver_ready"
    assert index["comparative_native_tool_summary"]["verification_ready"] is True
    assert "repo_map" in index["comparative_native_tool_summary"]["daily_driver_tools"]
    assert "posture=daily_driver_ready" in index["comparative_native_tool_summary"]["summary"]
    assert index["comparative_adapter_summary"]["format"] == "agent_orchestrator.comparative_adapter_summary.v1"
    assert index["comparative_adapter_summary"]["surface_status"] == "same_contract_two_executors_governed"
    assert index["comparative_adapter_summary"]["hot_plug_supported"] is True
    assert index["comparative_adapter_summary"]["resume_contract_supported"] is True
    assert "status=same_contract_two_executors_governed" in index["comparative_adapter_summary"]["summary"]
    assert index["comparative_session_posture_summary"]["format"] == "agent_orchestrator.comparative_session_posture_summary.v1"
    assert index["comparative_session_posture_summary"]["pause_expected"] in {True, False}
    assert index["comparative_session_posture_summary"]["workflow_projection_ready"] in {True, False}
    assert "primary=" in index["comparative_session_posture_summary"]["summary"]
    assert index["comparative_session_continuity_summary"]["format"] == "agent_orchestrator.comparative_session_continuity_summary.v1"
    assert index["comparative_session_continuity_summary"]["resume_supported"] is True
    assert index["comparative_session_continuity_summary"]["resume_ready"] is True
    assert index["comparative_session_continuity_summary"]["runtime_cost_ready"] is True
    assert index["comparative_session_continuity_summary"]["workflow_projection_visible"] in {True, False}
    assert index["comparative_session_continuity_summary"]["compaction_stage"] in {
        "full_fidelity",
        "light_compaction",
        "observation_masking",
        "summarization_ready",
    }
    assert index["comparative_session_continuity_summary"]["runtime_cost_provenance"]["duration_source"] in {
        "native_tool_trace",
        "unavailable",
    }
    assert "status=" in index["comparative_session_continuity_summary"]["summary"]
    assert index["comparative_native_closure_summary"]["format"] == "agent_orchestrator.comparative_native_closure_summary.v1"
    assert index["comparative_native_closure_summary"]["native_runtime_only"] is True
    assert index["comparative_native_closure_summary"]["external_coding_agent_required"] is False
    assert index["comparative_native_closure_summary"]["closure_status"] in {"completed", "blocked"}
    assert index["comparative_native_closure_summary"]["proof_ready"] in {True, False}
    assert "native_runtime_only=" in index["comparative_native_closure_summary"]["summary"]
    assert index["operator_posture_digest"]["format"] == "agent_orchestrator.session_operator_posture_digest.v1"
    assert index["operator_posture_digest"]["next_recommended_action"]
    assert index["operator_posture_digest"]["summary"]
    assert "operator_posture_approval_boundary_active" in index["comparative_benchmark_digest"]
    assert "session_continuity_approval_boundary_active" in index["comparative_benchmark_digest"]
    assert "session_continuity_governed_pause_resume_ready" in index["comparative_benchmark_digest"]
    assert index["comparative_daily_driver_summary"]["format"] == "agent_orchestrator.comparative_daily_driver_summary.v1"
    assert "status=" in index["comparative_daily_driver_summary"]["summary"]
    assert index["comparative_daily_driver_summary"]["daily_driver_case_matrix"]["matrix_status"] == "insufficient_coverage"
    assert index["comparative_daily_driver_summary"]["daily_driver_repeatability_harness"]["harness_status"] == "daily_driver_ready"
    assert index["comparative_benchmark_digest"]["external_harness_next_milestone"] == "authoritative_opencode_case_harness"
    assert index["comparative_benchmark_digest"]["external_harness_operator_action"] == "maintain_human_audit_until_external_harness_ready"
    assert index["comparative_benchmark_digest"]["external_harness_required_shared_surface_count"] == 5
    assert index["comparative_benchmark_digest"]["external_harness_required_external_artifact_count"] == 3
    assert index["comparative_benchmark_digest"]["external_harness_missing_external_artifact_count"] == 3
    assert index["comparative_benchmark_digest"]["external_harness_missing_artifacts"] == [
        "authoritative_opencode_case_harness",
        "same_contract_executor_comparison",
        "governed_recovery_and_cost_comparison",
    ]
    assert index["comparative_benchmark_digest"]["daily_driver_case_matrix_status"] == "insufficient_coverage"
    assert index["comparative_benchmark_digest"]["daily_driver_repeatability_harness_status"] == "daily_driver_ready"
    assert index["comparative_benchmark_digest"]["broader_repeatability_gap_families"] == [
        "multi_family_daily_driver_repo_tasks"
    ]
    assert "clarify_boundary_digest" in index["comparative_benchmark_digest"]["shared_evidence_surface"]
    assert "approval_boundary_digest" in index["comparative_benchmark_digest"]["shared_evidence_surface"]
    assert "planner_autonomy_boundary" in index["comparative_benchmark_digest"]["shared_evidence_surface"]
    assert "planner_reasoning" in index["comparative_benchmark_digest"]["shared_evidence_surface"]
    assert "workspace_index" in index["comparative_benchmark_digest"]["shared_evidence_surface"]


def test_workspace_index_optional_sections_surface_multi_family_daily_driver_benchmark() -> None:
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as d:
        root = Path(d)
        write_minimal_process_docs(root)
        evidence_payload = capture_workflow_evidence(
            [
                WorkflowEvidenceCase(
                    requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and append "team runbook updated" to docs/process/agent-team-operator-runbook.md',
                    label="repo-task-acceptance",
                    scenario_type="repo_task_acceptance",
                ),
                WorkflowEvidenceCase(
                    requirement='Replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "hook-based compliance checks updated" to docs/process/agent-orchestrator-implementation-process.md',
                    label="repo-task-acceptance-compliance",
                    scenario_type="repo_task_acceptance",
                ),
                WorkflowEvidenceCase(
                    requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "module manifest updated" to docs/process/module-manifest.md',
                    label="repo-task-acceptance-helper",
                    scenario_type="repo_task_acceptance",
                ),
                WorkflowEvidenceCase(
                    requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "team runbook updated" to docs/process/agent-team-operator-runbook.md and append "module manifest updated" to docs/process/module-manifest.md and append "hook-based compliance checks updated" to docs/process/agent-orchestrator-implementation-process.md',
                    label="repo-task-acceptance-long-chain-native-first",
                    scenario_type="repo_task_acceptance",
                ),
                WorkflowEvidenceCase(
                    requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "root map updated" to docs/process/root-map.md and append "context map updated" to docs/process/context-map.md and append "project index updated" to docs/process/project-index.md and append "native upgrade plan updated" to docs/architecture/native-coding-agent-upgrade-plan.md',
                    label="repo-task-acceptance-workspace-index-long-chain",
                    scenario_type="repo_task_acceptance",
                ),
                WorkflowEvidenceCase(
                    requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "artifact contract updated" to docs/process/control-plane-artifact-contracts.md and append "dogfood evidence updated" to docs/process/native-coding-agent-dogfood-evidence.md and append "project index refreshed" to docs/process/project-index.md',
                    label="repo-task-acceptance-evidence-contract-long-chain",
                    scenario_type="repo_task_acceptance",
                ),
            ],
            project_root=root,
        )

        summary = evidence_payload["summary"]
        snapshot = WorkspaceStateSnapshot(
            project_root=str(root),
            plans=[],
            runs=[],
            jobs=[],
            evidence={},
            approvals=[],
            provider_health=None,
            dirty_state={},
            memory_digest={},
            external_cache={},
        )
        payload = workspace_index_optional_sections(
            snapshot,
            artifacts={
                "execution_artifacts": {
                    "summary": {
                        "comparative_benchmark": summary["comparative_benchmark"],
                        "comparative_benchmark_digest": summary["comparative_benchmark_digest"],
                    }
                }
            },
        )

        assert (
            payload["comparative_daily_driver_benchmark"]
            == "official_catalog=docs/process/evidence-cases.json independent_daily_driver_families=6 status=multi_family_broad_daily_driver_proven"
        )
        assert (
            payload["comparative_daily_driver_runner_artifact"]["format"]
            == "agent_orchestrator.daily_driver_runner_artifact.v1"
        )
        assert payload["comparative_daily_driver_runner_artifact"]["runner_status"] == "repeatability_gap_remaining"
        assert payload["comparative_daily_driver_runner_artifact"]["contract_outputs"] == [
            "runtime_payload",
            "workspace_index",
            "cli_summary",
        ]


def test_runtime_event_stream_includes_execution_artifact_refs(tmp_path) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    run_payload = {
        "id": "run-artifact-1",
        "initial_mode": "coding_agent",
        "final_mode": "coding_agent",
        "accepted": True,
        "path": str(runs_root / "run-artifact-1.json"),
        "payload": {
            "kernel_contract": {
                "kernel_name": "coding_agent",
                "kernel_role": "governed_execution_kernel",
                "state_authority": "control_plane",
                "output_surfaces": ["execution_result", "runtime_event_stream"],
            },
            "step_loop_contract": {
                "loop_model": "explicit_stage_step_loop",
                "status": "completed",
                "current_stage": "verify",
                "current_disposition": "complete",
                "resume_supported": True,
            },
            "artifact_summary": {
                "artifact_count": 1,
                "artifacts": [
                    {
                        "artifact_id": "exec-artifact-123",
                        "path": str(tmp_path / "execution-artifacts" / "exec-artifact-123.json"),
                        "ref": {"format": "agent_orchestrator.execution_command_artifact.v1"},
                    }
                ],
            },
                "native_task_proof": {
                    "format": "agent_orchestrator.native_task_proof.v1",
                    "native_runtime_only": True,
                    "external_coding_agent_required": False,
                    "closure_status": "completed",
                },
                "native_repo_task_acceptance": {
                    "format": "agent_orchestrator.native_repo_task_acceptance.v1",
                    "real_repo_task_acceptance_ready": False,
                    "passed_check_count": 3,
                    "total_check_count": 5,
                },
                "native_complex_repo_task_acceptance": {
                    "format": "agent_orchestrator.native_complex_repo_task_acceptance.v1",
                    "complex_repo_task_ready": False,
                    "passed_check_count": 2,
                    "total_check_count": 5,
                },
            },
        }
    (runs_root / "run-artifact-1.json").write_text(json.dumps(run_payload, ensure_ascii=False), encoding="utf-8")

    payload = build_runtime_event_stream(
        tmp_path,
        runs_root=runs_root,
        plans_root=tmp_path / "plans",
        jobs_root=tmp_path / "jobs",
        approvals_root=tmp_path / "approvals",
    )

    execution_run = next(event for event in payload["events"] if event.get("kind") == "execution_run")
    assert "exec-artifact-123" in execution_run["artifact_refs"]
    assert execution_run["kernel_contract"]["kernel_role"] == "governed_execution_kernel"
    assert execution_run["kernel_contract"]["state_authority"] == "control_plane"
    assert execution_run["step_loop_contract"]["loop_model"] == "explicit_stage_step_loop"
    assert execution_run["step_loop_contract"]["current_disposition"] == "complete"
    assert execution_run["native_task_proof"]["native_runtime_only"] is True
    assert execution_run["native_task_proof"]["closure_status"] == "completed"
    assert execution_run["native_repo_task_acceptance"]["format"] == "agent_orchestrator.native_repo_task_acceptance.v1"
    assert execution_run["native_complex_repo_task_acceptance"]["format"] == "agent_orchestrator.native_complex_repo_task_acceptance.v1"
    assert execution_run["artifact_summary"]["artifact_count"] == 1


def test_evidence_bundle_includes_native_product_ux_snapshot(tmp_path) -> None:
    from agent_orchestrator.control_plane import build_evidence_bundle

    payload = build_evidence_bundle(tmp_path)

    assert payload["native_product_ux"]["format"] == "agent_orchestrator.native_product_ux_snapshot.v1"
    assert payload["native_product_ux"]["read_only"] is True
    assert payload["native_product_ux"]["provider_runtime"]["release_candidate_verdict"]
    assert payload["native_release_candidate"]["format"] == "agent_orchestrator.native_release_candidate_report.v1"
    assert payload["native_release_candidate"]["verdict"] in {"pass", "degraded", "fail"}
    assert payload["native_release_bundle"]["format"] == "agent_orchestrator.native_release_operator_bundle.v1"
    assert payload["native_release_bundle"]["verdict"] in {"pass", "degraded", "fail"}
    assert "next_action" in payload["native_product_ux"]


def test_evidence_bundle_includes_native_rc_adoption_summary(tmp_path) -> None:
    from agent_orchestrator.control_plane import build_evidence_bundle

    payload = build_evidence_bundle(tmp_path)

    adoption = payload["native_rc_adoption"]
    assert adoption["format"] == "agent_orchestrator.native_rc_adoption_summary.v1"
    assert adoption["lane_count"] == 3
    assert adoption["verdict"] in {"pass", "degraded", "fail"}
    assert adoption["gap_classification"] in {"agent_capability", "product_thickness", "runtime_provider_setup", "instrumentation_evidence", "operator_workflow_friction", "none"}
    assert adoption["next_action"]
