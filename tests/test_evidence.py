# DEPS: __future__, agent_orchestrator, json, test_support
# RESPONSIBILITY: Verify workflow evidence harness output and persisted artifact shape.
# MODULE: tests
# ---


from __future__ import annotations

import json

from agent_orchestrator.evidence import (
    EVIDENCE_SCHEMA_VERSION,
    WorkflowEvidenceCase,
    _build_summary,
    _postmortem_signals,
    benchmark_evidence_cases,
    compare_workflow_evidence,
    capture_workflow_evidence,
    load_workflow_evidence_cases,
    render_workflow_evidence_markdown,
    render_workflow_evidence_trend_markdown,
    write_workflow_evidence_trend_markdown,
    write_workflow_evidence_markdown,
)
from agent_orchestrator.productization_surface import build_comparative_daily_driver_benchmark


from agent_orchestrator.opencode_harness import (
    AUTHORITATIVE_REPORT_VERSION,
    CASE_PACK_VERSION,
    COMPARATIVE_REPORT_VERSION,
    NORMALIZED_RECORD_VERSION,
    OPENCODE_RUN_RECORD_VERSION,
    build_authoritative_comparative_report,
    build_comparative_evidence_report,
    build_external_opencode_harness_bundle,
    build_native_run_records,
    build_opencode_run_records,
    build_same_contract_case_pack,
    normalize_run_records,
    write_case_pack,
)
from test_support import write_minimal_process_docs


def test_capture_workflow_evidence_records_team_advantages_and_writes_json(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    output_path = tmp_path / "evidence" / "workflow.json"

    payload = capture_workflow_evidence(
        ["Build a persisted plan artifact"],
        project_root=tmp_path,
        output_path=output_path,
    )

    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written == payload
    assert payload["schema_version"] == EVIDENCE_SCHEMA_VERSION
    assert payload["reportable_format"] == "agent_orchestrator.workflow_evidence.v1"
    assert payload["summary"]["case_count"] == 1
    assert payload["summary"]["schema_version"] == EVIDENCE_SCHEMA_VERSION
    assert payload["summary"]["team_cases_with_execution_run"] == 1
    case = payload["cases"][0]
    assert case["schema_version"] == EVIDENCE_SCHEMA_VERSION
    assert "approved_plan_artifact" in case["comparison"]["team_advantages"]
    assert "execution_provenance" in case["comparison"]["team_advantages"]
    assert "recovery_guidance" in case["comparison"]["team_advantages"]
    assert "doc_sync_snapshot" in case["comparison"]["team_advantages"]
    assert "fallback_signal_surface" in case["comparison"]["team_advantages"]
    assert "approval_observability" in case["comparison"]["team_advantages"]
    assert "fresh_resume_policy" in case["comparison"]["team_advantages"]
    assert "knowledge_artifacts" in case["comparison"]["team_advantages"]
    assert "role_contract_enforced" in case["comparison"]["team_advantages"]
    assert "no_approved_plan_artifact" in case["comparison"]["direct_limitations"]
    assert case["team_workflow"]["approved_plan_source"] == "approved_plan_session"
    assert case["team_workflow"]["approval_state"]["state"] in {"completed", "approved"}
    assert case["team_workflow"]["usage_cost"]["source"] == "placeholder"
    assert case["comparison"]["benefit_score"] >= 4
    assert case["signals"]["provenance"]["present"] is True
    assert case["signals"]["provenance"]["matches_plan_session"] is True
    assert case["signals"]["recovery"]["has_guidance"] is True
    assert case["signals"]["doc_sync"]["present"] is True
    assert case["signals"]["doc_sync"]["status"] == "passed"
    assert case["signals"]["fallback"]["present"] in {True, False}
    assert payload["report"]["cases_with_recovery_guidance"] == 1
    assert payload["summary"]["reference_advantage_counts"]["approval_observability"] == 1
    assert payload["summary"]["average_benefit_score"] >= 4
    assert payload["summary"]["signal_counts"]["provenance_matches_plan_session"] == 1
    assert payload["summary"]["signal_counts"]["doc_sync_present"] == 1


def test_capture_workflow_evidence_accepts_structured_cases_and_builds_report(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(requirement="Build a persisted plan artifact", label="artifact"),
            WorkflowEvidenceCase(requirement="Build plan with followup checklist", label="followup"),
        ],
        project_root=tmp_path,
    )

    assert payload["summary"]["case_count"] == 2
    assert payload["report"]["max_benefit_score"] >= 1
    assert payload["report"]["benefit_score_by_case"]["artifact"] >= 1
    assert payload["report"]["team_status_counts"]
    assert payload["report"]["direct_final_state_counts"]
    assert payload["report"]["scenario_type_counts"]
    assert payload["report"]["average_benefit_score_by_scenario"]
    assert payload["report"]["scenario_aggregates"]
    assert payload["report"]["postmortem_signal_counts"] == {}
    assert payload["summary"]["real_task_metrics"]["recovery_recommendation_coverage"] == 2
    assert payload["summary"]["runtime_measurement_metrics"]["measured_runtime_cases"] == 2
    assert payload["report"]["runtime_measurement_status_counts"]["measured"] == 2


def test_capture_workflow_evidence_reports_scenario_aggregates(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(requirement="Build a persisted plan artifact", label="artifact", scenario_type="standard"),
            WorkflowEvidenceCase(requirement="Implement auth migration across multiple services", label="risk", scenario_type="high_risk"),
        ],
        project_root=tmp_path,
    )

    assert payload["cases"][0]["scenario_type"] == "standard"
    assert payload["cases"][1]["scenario_type"] == "high_risk"
    assert payload["report"]["scenario_type_counts"]["standard"] == 1
    assert payload["report"]["scenario_type_counts"]["high_risk"] == 1
    assert "standard" in payload["report"]["average_benefit_score_by_scenario"]
    standard = payload["report"]["scenario_aggregates"]["standard"]
    assert standard["case_count"] == 1
    assert standard["average_benefit_score"] >= 1
    assert standard["signal_counts"]["recovery_guidance_present"] == 1
    assert standard["team_advantage_counts"]["approved_plan_artifact"] == 1


def test_benchmark_evidence_cases_are_stable_and_reportable(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    cases = benchmark_evidence_cases()
    payload = capture_workflow_evidence(cases[:2], project_root=tmp_path)

    assert [case.label for case in cases] == [
        "persisted_plan_artifact",
        "followup_checklist",
        "auth_migration",
        "parallel_validation",
        "cli_workflow_hardening",
        "ui_operator_console_flow",
        "compliance_blocking_recovery",
        "runtime_fidelity_inspection",
        "investigation_to_edit",
        "multi_file_helper_repair",
        "interrupted_task_resume",
        "repair_resume_success",
        "multi_milestone_program_execution",
        "repo_task_acceptance",
        "repo_task_acceptance_compliance",
        "repo_task_acceptance_helper_impl",
        "repo_task_acceptance_long_chain_native_first",
        "repo_task_acceptance_workspace_index_long_chain",
        "repo_task_acceptance_evidence_contract_long_chain",
    ]
    assert [case.scenario_type for case in cases] == [
        "standard",
        "followup",
        "high_risk",
        "parallel",
        "standard",
        "ui_workflow",
        "compliance_blocking",
        "runtime_fidelity",
        "native_coverage_expansion",
        "native_coverage_expansion",
        "interruption_recovery",
        "repair_resume_success",
        "program_execution",
        "repo_task_acceptance",
        "repo_task_acceptance",
        "repo_task_acceptance",
        "repo_task_acceptance",
        "repo_task_acceptance",
        "repo_task_acceptance",
    ]
    assert payload["report"]["format"] == "agent_orchestrator.workflow_evidence.v1"
    assert sorted(payload["report"]["scenario_aggregates"]) == ["followup", "standard"]
    assert payload["summary"]["comparative_benchmark"]["case_count"] == 2
    assert "success_rate_delta" in payload["summary"]["comparative_benchmark"]
    assert "blocked_rate_delta" in payload["summary"]["comparative_benchmark"]
    assert "recovery_rate_delta" in payload["summary"]["comparative_benchmark"]
    assert "verification_cost_measured_cases" in payload["summary"]["comparative_benchmark"]
    assert "human_intervention_frequency" in payload["summary"]["comparative_benchmark"]


def test_capture_workflow_evidence_handles_mixed_standard_and_native_daily_driver_cases(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    cases = benchmark_evidence_cases()
    selected = [
        next(case for case in cases if case.label == "persisted_plan_artifact"),
        next(case for case in cases if case.label == "repo_task_acceptance_long_chain_native_first"),
        next(case for case in cases if case.label == "repo_task_acceptance_workspace_index_long_chain"),
        next(case for case in cases if case.label == "repo_task_acceptance_evidence_contract_long_chain"),
    ]

    payload = capture_workflow_evidence(selected, project_root=tmp_path)

    proof_strength = payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]
    digest = payload["summary"]["comparative_benchmark_digest"]
    benchmark = payload["summary"]["comparative_benchmark"]

    assert benchmark["case_count"] == 4
    assert benchmark["productization_case_count"] == 3
    assert benchmark["shared_productization_contract_ready"] is True
    assert benchmark["comparative_completion_summary"]["format"] == "agent_orchestrator.comparative_completion_summary.v1"
    assert proof_strength["direct_proof_status"] == "multiple_stronger_task_families_proven"
    assert proof_strength["daily_driver_repeatability_tier"] == "multi_family_independent_daily_driver_proven"
    assert proof_strength["independent_daily_driver_repo_task_family_count"] == 3
    assert proof_strength["independent_daily_driver_repo_task_families_proven"] == [
        "evidence_contract_alignment_repo_task",
        "long_chain_native_first_repo_task",
        "workspace_index_alignment_repo_task",
    ]
    assert digest["direct_proof_status"] == "multiple_stronger_task_families_proven"
    assert digest["independent_daily_driver_repo_task_family_count"] == 3
    assert digest["case_count"] == 4
    assert digest["productization_case_count"] == 3
    assert digest["daily_driver_main_path_ready_cases"] == 3
    assert digest["session_posture_cases"] == 3
    assert benchmark["external_comparison_harness_surface"]["required_shared_surface_count"] == 5
    assert benchmark["external_comparison_harness_surface"]["required_external_artifact_count"] == 3
    assert benchmark["external_comparison_harness_surface"]["missing_external_artifact_count"] == 3


def test_load_workflow_evidence_cases_accepts_real_task_case_file(tmp_path) -> None:
    case_file = tmp_path / "cases.json"
    case_file.write_text(
        json.dumps(
            [
                {
                    "label": "real-task",
                    "requirement": "Implement auth migration across multiple services",
                    "scenario_type": "high_risk",
                    "mode": "speed_first",
                    "risk_profile": "security",
                    "operator_goal": "validate review and recovery signals",
                    "expected_signals": ["recovery_guidance", "doc_sync", "runtime_fidelity"],
                    "runtime_expectation": "records provider/runtime fidelity without bridge ownership",
                }
            ]
        ),
        encoding="utf-8",
    )

    cases = load_workflow_evidence_cases(case_file)

    assert cases[0].label == "real-task"
    assert cases[0].scenario_type == "high_risk"
    assert cases[0].mode.value == "speed_first"
    assert cases[0].risk_profile == "security"
    assert cases[0].operator_goal == "validate review and recovery signals"
    assert cases[0].expected_signals == ("recovery_guidance", "doc_sync", "runtime_fidelity")
    assert cases[0].runtime_expectation == "records provider/runtime fidelity without bridge ownership"


def test_capture_workflow_evidence_records_real_task_postmortem_signals(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement="Recover an interrupted local implementation task",
                label="interruption",
                scenario_type="interruption_recovery",
                risk_profile="medium",
                operator_goal="prove recovery recommendation quality",
                expected_signals=("recovery_guidance", "doc_sync", "interruption_recovery", "cost_latency"),
                runtime_expectation="local command runtime metadata only",
            )
        ],
        project_root=tmp_path,
    )

    case = payload["cases"][0]
    assert case["real_task"]["risk_profile"] == "medium"
    assert case["real_task"]["operator_goal"] == "prove recovery recommendation quality"
    assert case["team_workflow"]["native_task_proof"]["native_runtime_only"] is True
    assert case["team_workflow"]["native_task_proof"]["external_coding_agent_required"] is False
    assert case["team_workflow"]["native_task_proof"]["task_class"] == "bounded_internal_repo_task"
    assert case["team_workflow"]["status"] == "awaiting_human"
    assert case["postmortem"]["recovery_recommendation_actionable"] is True
    assert case["postmortem"]["cost_latency_ready"] is True
    assert case["postmortem"]["native_task_proof_present"] is True
    assert case["postmortem"]["native_task_class"] == "bounded_internal_repo_task"
    assert case["postmortem"]["native_task_scenario"] == "verify_failure_exhausted_recovery_block"
    assert case["native_runtime_closure"]["format"] == "agent_orchestrator.native_runtime_closure.v1"
    assert case["native_runtime_closure"]["task_class"] == "bounded_internal_repo_task"
    assert case["native_runtime_closure"]["checks"]["native_only_execution"]["passed"] is True
    assert case["native_runtime_closure"]["checks"]["stable_step_loop"]["passed"] is True
    assert case["native_runtime_closure"]["checks"]["explicit_context_select_and_observation"]["passed"] is True
    assert case["native_runtime_closure"]["checks"]["context_engineering_main_path_visible"]["passed"] is True
    assert case["native_runtime_closure"]["checks"]["context_engineering_main_path_visible"]["evidence"]["isolation_reinjection_mode"] in {"full_inline_context", "digest_focus_subset"}
    assert case["native_runtime_closure"]["checks"]["verify_repair_resume_closure"]["passed"] is True
    assert case["native_runtime_closure"]["checks"]["control_plane_authority"]["passed"] is True
    assert case["native_runtime_closure"]["checks"]["auditable_artifacts_and_surfaces"]["passed"] is True
    assert case["native_runtime_closure"]["runtime_closure_ready"] is True
    assert case["native_repo_task_acceptance"]["format"] == "agent_orchestrator.native_repo_task_acceptance.v1"
    assert case["native_repo_task_acceptance"]["real_repo_task_acceptance_ready"] is False
    assert case["native_complex_repo_task_acceptance"]["format"] == "agent_orchestrator.native_complex_repo_task_acceptance.v1"
    assert case["native_complex_repo_task_acceptance"]["complex_repo_task_ready"] is False
    assert case["native_dogfood_surfaces"]["format"] == "agent_orchestrator.native_dogfood_surfaces.v1"
    assert case["native_dogfood_surfaces"]["surface_projection_ready"] is True
    assert case["native_dogfood_surfaces"]["proof_scenario"] == "verify_failure_exhausted_recovery_block"
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_context_engineering_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_context_engineering_visible"]["evidence"]["context_isolation_reinjection_mode"] in {"full_inline_context", "digest_focus_subset", None}
    assert case["runtime_measurement"]["measurement_status"] == "measured"
    assert case["runtime_measurement"]["command_duration_available"] is True
    assert "recovery_guidance" in case["postmortem"]["matched_expected_signals"]
    assert payload["summary"]["real_task_metrics"]["postmortem_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["cost_latency_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["native_task_proof_coverage"] == 1
    assert payload["summary"]["real_task_metrics"]["native_runtime_closure_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["native_repo_task_acceptance_ready_cases"] == 0
    assert payload["summary"]["real_task_metrics"]["native_complex_repo_task_acceptance_ready_cases"] == 0
    assert payload["summary"]["real_task_metrics"]["native_dogfood_surface_ready_cases"] == 1


def test_capture_workflow_evidence_can_prove_real_repo_task_acceptance_with_explicit_repo_mutations(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and append "team runbook updated" to docs/process/agent-team-operator-runbook.md',
                label="repo-task-acceptance",
                scenario_type="repo_task_acceptance",
                risk_profile="medium",
                operator_goal="prove one native run can satisfy the stronger multi-file repo-task acceptance contract",
                expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
                runtime_expectation="bounded native multi-file edits with verification on code targets and docs surface updates",
            )
        ],
        project_root=tmp_path,
    )

    case = payload["cases"][0]
    runtime_closure = case["native_runtime_closure"]
    repo_acceptance = case["native_repo_task_acceptance"]
    complex_repo_acceptance = case["native_complex_repo_task_acceptance"]

    assert runtime_closure["runtime_closure_ready"] is True
    assert repo_acceptance["format"] == "agent_orchestrator.native_repo_task_acceptance.v1"
    assert repo_acceptance["task_shape_checks"]["repository_exploration_present"]["passed"] is True
    assert repo_acceptance["task_shape_checks"]["code_edit_under_repo_surface"]["passed"] is True
    assert repo_acceptance["task_shape_checks"]["verification_command_present"]["passed"] is True
    assert repo_acceptance["task_shape_checks"]["operator_visible_artifacts_present"]["passed"] is True
    assert repo_acceptance["task_shape_checks"]["repo_facing_surface_updated"]["passed"] is True
    assert repo_acceptance["real_repo_task_acceptance_ready"] is True
    assert complex_repo_acceptance["format"] == "agent_orchestrator.native_complex_repo_task_acceptance.v1"
    assert complex_repo_acceptance["complex_repo_task_ready"] is True
    assert case["native_dogfood_surfaces"]["format"] == "agent_orchestrator.native_dogfood_surfaces.v1"
    assert case["native_dogfood_surfaces"]["surface_checks"]["runtime_event_stream_repo_task_acceptance_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_index_repo_task_acceptance_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_repo_task_acceptance_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["runtime_event_stream_complex_repo_task_acceptance_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_index_complex_repo_task_acceptance_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_complex_repo_task_acceptance_visible"]["passed"] is True
    assert "src/agent_orchestrator/stub.py" in repo_acceptance["task_shape_checks"]["code_edit_under_repo_surface"]["evidence"]["changed_code_paths"]
    assert "src/agent_orchestrator/compliance_signal.py" in repo_acceptance["task_shape_checks"]["code_edit_under_repo_surface"]["evidence"]["changed_code_paths"]
    assert complex_repo_acceptance["complex_task_checks"]["multi_target_exploration_present"]["passed"] is True
    assert complex_repo_acceptance["complex_task_checks"]["multi_file_mutation_present"]["passed"] is True
    assert complex_repo_acceptance["complex_task_checks"]["native_exploration_trace_visible"]["passed"] is True
    assert complex_repo_acceptance["complex_task_checks"]["planner_workflow_contract_visible"]["passed"] is True
    assert complex_repo_acceptance["complex_task_checks"]["planner_workflow_runtime_alignment_visible"]["passed"] is True
    assert any(
        "agent-team-operator-runbook.md" in path
        for path in repo_acceptance["task_shape_checks"]["repo_facing_surface_updated"]["evidence"]["changed_surface_paths"]
    )
    assert payload["summary"]["real_task_metrics"]["native_runtime_closure_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["native_repo_task_acceptance_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["native_complex_repo_task_acceptance_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["native_dogfood_surface_ready_cases"] == 1


def test_capture_workflow_evidence_can_prove_second_repo_task_acceptance_shape(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement='Replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "hook-based compliance checks updated" to docs/process/agent-orchestrator-implementation-process.md',
                label="repo-task-acceptance-compliance",
                scenario_type="repo_task_acceptance",
                risk_profile="medium",
                operator_goal="prove a second native run can satisfy the stronger multi-file repo-task acceptance contract",
                expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
                runtime_expectation="bounded native multi-file edits with verification on code targets and process surface updates",
            )
        ],
        project_root=tmp_path,
    )

    case = payload["cases"][0]
    repo_acceptance = case["native_repo_task_acceptance"]
    complex_repo_acceptance = case["native_complex_repo_task_acceptance"]

    assert repo_acceptance["format"] == "agent_orchestrator.native_repo_task_acceptance.v1"
    assert repo_acceptance["task_shape_checks"]["repository_exploration_present"]["passed"] is True
    assert repo_acceptance["task_shape_checks"]["code_edit_under_repo_surface"]["passed"] is True
    assert repo_acceptance["task_shape_checks"]["verification_command_present"]["passed"] is True
    assert repo_acceptance["task_shape_checks"]["operator_visible_artifacts_present"]["passed"] is True
    assert repo_acceptance["task_shape_checks"]["repo_facing_surface_updated"]["passed"] is True
    assert repo_acceptance["real_repo_task_acceptance_ready"] is True
    assert "src/agent_orchestrator/compliance_signal.py" in repo_acceptance["task_shape_checks"]["code_edit_under_repo_surface"]["evidence"]["changed_code_paths"]
    assert "src/agent_orchestrator/summary_helper.py" in repo_acceptance["task_shape_checks"]["code_edit_under_repo_surface"]["evidence"]["changed_code_paths"]
    assert complex_repo_acceptance["complex_repo_task_ready"] is True
    assert any(
        "agent-orchestrator-implementation-process.md" in path
        for path in repo_acceptance["task_shape_checks"]["repo_facing_surface_updated"]["evidence"]["changed_surface_paths"]
    )
    assert payload["summary"]["real_task_metrics"]["native_repo_task_acceptance_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["native_complex_repo_task_acceptance_ready_cases"] == 1


def test_capture_workflow_evidence_can_prove_third_repo_task_acceptance_helper_shape(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "module manifest updated" to docs/process/module-manifest.md',
                label="repo-task-acceptance-helper",
                scenario_type="repo_task_acceptance",
                risk_profile="medium",
                operator_goal="prove a third native run can satisfy the stronger multi-file repo-task acceptance contract for a helper implementation task",
                expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
                runtime_expectation="bounded native helper implementation edits with verification on code targets and process surface updates",
            )
        ],
        project_root=tmp_path,
    )

    case = payload["cases"][0]
    repo_acceptance = case["native_repo_task_acceptance"]
    complex_repo_acceptance = case["native_complex_repo_task_acceptance"]

    assert repo_acceptance["format"] == "agent_orchestrator.native_repo_task_acceptance.v1"
    assert repo_acceptance["task_shape_checks"]["repository_exploration_present"]["passed"] is True
    assert repo_acceptance["task_shape_checks"]["code_edit_under_repo_surface"]["passed"] is True
    assert repo_acceptance["task_shape_checks"]["verification_command_present"]["passed"] is True
    assert repo_acceptance["task_shape_checks"]["operator_visible_artifacts_present"]["passed"] is True
    assert repo_acceptance["task_shape_checks"]["repo_facing_surface_updated"]["passed"] is True
    assert repo_acceptance["real_repo_task_acceptance_ready"] is True
    assert complex_repo_acceptance["complex_repo_task_ready"] is True
    assert "src/agent_orchestrator/stub.py" in repo_acceptance["task_shape_checks"]["code_edit_under_repo_surface"]["evidence"]["changed_code_paths"]
    assert "src/agent_orchestrator/summary_helper.py" in repo_acceptance["task_shape_checks"]["code_edit_under_repo_surface"]["evidence"]["changed_code_paths"]
    assert any(
        "module-manifest.md" in path
        for path in repo_acceptance["task_shape_checks"]["repo_facing_surface_updated"]["evidence"]["changed_surface_paths"]
    )
    assert payload["summary"]["real_task_metrics"]["native_repo_task_acceptance_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["native_complex_repo_task_acceptance_ready_cases"] == 1


def test_capture_workflow_evidence_can_prove_long_chain_native_first_repo_task_acceptance(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "team runbook updated" to docs/process/agent-team-operator-runbook.md and append "module manifest updated" to docs/process/module-manifest.md and append "hook-based compliance checks updated" to docs/process/agent-orchestrator-implementation-process.md',
                label="repo-task-acceptance-long-chain-native-first",
                scenario_type="repo_task_acceptance",
                risk_profile="medium",
                operator_goal="prove a longer native-first repository task can close through exploration, multi-file editing, verification, and docs synchronization without external help",
                expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
                runtime_expectation="native exploration, multi-file mutation, verification, and repo-facing surface updates stay on the native path",
            )
        ],
        project_root=tmp_path,
    )

    case = payload["cases"][0]
    assert case["native_repo_task_acceptance"]["real_repo_task_acceptance_ready"] is True
    assert case["native_complex_repo_task_acceptance"]["complex_repo_task_ready"] is True
    assert case["native_dogfood_surfaces"]["surface_projection_ready"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_adapter_shared_contract_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_native_exploration_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_session_posture_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_session_posture_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_governed_approval_boundary_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_governed_approval_boundary_visible"]["evidence"]["comparative_session_continuity_summary"]["long_horizon_continuity_judgment"] == "daily_driver_continuity_governed_approval_boundary"
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_governed_approval_boundary_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["shared_approval_boundary_evidence_surface_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_daily_driver_main_path_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_daily_driver_main_path_visible"]["evidence"]["ready"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_daily_driver_main_path_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_daily_driver_main_path_visible"]["evidence"]["ready"] is True
    assert payload["summary"]["real_task_metrics"]["native_repo_task_acceptance_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["native_complex_repo_task_acceptance_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["long_chain_native_first_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["daily_driver_main_path_ready_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["comparison_posture"]["status"] == "daily_driver_main_path_proven_breadth_gap_remaining"
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["direct_proof_status"] == "single_stronger_task_family_proven"
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["repeatability_status"] == "not_yet_broadly_proven"
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["daily_driver_repeatability_tier"] == "single_family_daily_driver_anchor_only"
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["stronger_task_family_count"] == 1
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["broader_task_family_count"] == 1
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["stronger_task_families"] == [
        "long_chain_native_first_repo_task"
    ]
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["daily_driver_main_path_anchor"] == (
        "long_chain_native_first_repo_task"
    )
    assert payload["summary"]["comparative_benchmark"]["daily_driver_main_path_anchor"] == (
        "long_chain_native_first_repo_task"
    )
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["daily_driver_repo_task_family_count"] == 1
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["daily_driver_repo_task_families_proven"] == [
        "long_chain_native_first_repo_task"
    ]
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["independent_daily_driver_repo_task_family_count"] == 1
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["independent_daily_driver_repo_task_families_proven"] == [
        "long_chain_native_first_repo_task"
    ]
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["broader_repeatability_gap_families"] == [
        "multi_family_daily_driver_repo_tasks"
    ]
    assert payload["summary"]["comparative_benchmark_digest"]["comparison_status"] == "daily_driver_main_path_proven_breadth_gap_remaining"
    assert payload["summary"]["comparative_benchmark_digest"]["direct_proof_status"] == "single_stronger_task_family_proven"
    assert payload["summary"]["comparative_benchmark_digest"]["repeatability_status"] == "not_yet_broadly_proven"
    assert payload["summary"]["comparative_benchmark_digest"]["daily_driver_repeatability_tier"] == "single_family_daily_driver_anchor_only"
    assert payload["summary"]["comparative_benchmark_digest"]["stronger_task_families"] == [
        "long_chain_native_first_repo_task"
    ]
    assert payload["summary"]["comparative_benchmark_digest"]["daily_driver_main_path_anchor"] == (
        "long_chain_native_first_repo_task"
    )
    assert payload["summary"]["comparative_benchmark_digest"]["daily_driver_main_path_anchor_family"] == (
        "long_chain_native_first_repo_task"
    )
    assert payload["summary"]["comparative_benchmark_digest"]["independent_daily_driver_repo_task_family_count"] == 1
    assert payload["summary"]["comparative_benchmark_digest"]["independent_daily_driver_repo_task_families_proven"] == [
        "long_chain_native_first_repo_task"
    ]
    assert "workspace_index" in payload["summary"]["comparative_benchmark_digest"]["shared_evidence_surface"]
    assert any(
        item in payload["summary"]["comparative_benchmark_digest"]["shared_evidence_surface"]
        for item in {"ui_execution_summary", "team_summary"}
    )


def test_capture_workflow_evidence_can_prove_second_independent_daily_driver_anchor_family(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "root map updated" to docs/process/root-map.md and append "context map updated" to docs/process/context-map.md and append "project index updated" to docs/process/project-index.md and append "native upgrade plan updated" to docs/architecture/native-coding-agent-upgrade-plan.md',
                label="repo-task-acceptance-workspace-index-long-chain",
                scenario_type="repo_task_acceptance",
                risk_profile="medium",
                operator_goal="prove a second longer native-first repository task can close through exploration, multi-file editing, verification, and workspace/architecture index synchronization without external help",
                expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
                runtime_expectation="native exploration, multi-file mutation, verification, and workspace-facing architecture index updates stay on the native path",
            )
        ],
        project_root=tmp_path,
    )

    case = payload["cases"][0]
    proof_strength = payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]
    digest = payload["summary"]["comparative_benchmark_digest"]
    changed_surface_paths = case["native_repo_task_acceptance"]["task_shape_checks"]["repo_facing_surface_updated"]["evidence"]["changed_surface_paths"]

    assert case["native_repo_task_acceptance"]["real_repo_task_acceptance_ready"] is True
    assert case["native_complex_repo_task_acceptance"]["complex_repo_task_ready"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_daily_driver_main_path_visible"]["evidence"]["ready"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_daily_driver_main_path_visible"]["evidence"]["ready"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_session_posture_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_session_posture_visible"]["passed"] is True
    assert any("root-map.md" in path for path in changed_surface_paths)
    assert any("context-map.md" in path for path in changed_surface_paths)
    assert any("project-index.md" in path for path in changed_surface_paths)
    assert any("native-coding-agent-upgrade-plan.md" in path for path in changed_surface_paths)
    assert proof_strength["direct_proof_status"] == "single_stronger_task_family_proven"
    assert proof_strength["daily_driver_repeatability_tier"] == "single_family_daily_driver_anchor_only"
    assert proof_strength["independent_daily_driver_repo_task_family_count"] == 1
    assert proof_strength["independent_daily_driver_repo_task_families_proven"] == [
        "workspace_index_alignment_repo_task"
    ]
    assert digest["independent_daily_driver_repo_task_family_count"] == 1
    assert digest["independent_daily_driver_repo_task_families_proven"] == [
        "workspace_index_alignment_repo_task"
    ]


def test_capture_workflow_evidence_can_prove_third_independent_daily_driver_anchor_family(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "artifact contract updated" to docs/process/control-plane-artifact-contracts.md and append "dogfood evidence updated" to docs/process/native-coding-agent-dogfood-evidence.md and append "project index refreshed" to docs/process/project-index.md',
                label="repo-task-acceptance-evidence-contract-long-chain",
                scenario_type="repo_task_acceptance",
                risk_profile="medium",
                operator_goal="prove a third longer native-first repository task can close through exploration, multi-file editing, verification, and evidence-contract synchronization without external help",
                expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
                runtime_expectation="native exploration, multi-file mutation, verification, and evidence-facing contract updates stay on the native path",
            )
        ],
        project_root=tmp_path,
    )

    case = payload["cases"][0]
    proof_strength = payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]
    digest = payload["summary"]["comparative_benchmark_digest"]
    changed_surface_paths = case["native_repo_task_acceptance"]["task_shape_checks"]["repo_facing_surface_updated"]["evidence"]["changed_surface_paths"]

    assert case["native_repo_task_acceptance"]["real_repo_task_acceptance_ready"] is True
    assert case["native_complex_repo_task_acceptance"]["complex_repo_task_ready"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_daily_driver_main_path_visible"]["evidence"]["ready"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_daily_driver_main_path_visible"]["evidence"]["ready"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_session_posture_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_session_posture_visible"]["passed"] is True
    assert any("control-plane-artifact-contracts.md" in path for path in changed_surface_paths)
    assert any("native-coding-agent-dogfood-evidence.md" in path for path in changed_surface_paths)
    assert any("project-index.md" in path for path in changed_surface_paths)
    assert proof_strength["direct_proof_status"] == "single_stronger_task_family_proven"
    assert proof_strength["daily_driver_repeatability_tier"] == "single_family_daily_driver_anchor_only"
    assert proof_strength["independent_daily_driver_repo_task_family_count"] == 1
    assert proof_strength["independent_daily_driver_repo_task_families_proven"] == [
        "evidence_contract_alignment_repo_task"
    ]
    assert digest["independent_daily_driver_repo_task_family_count"] == 1
    assert digest["independent_daily_driver_repo_task_families_proven"] == [
        "evidence_contract_alignment_repo_task"
    ]


def test_capture_workflow_evidence_tracks_multiple_proven_repo_task_families_without_claiming_broad_repeatability(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and append "team runbook updated" to docs/process/agent-team-operator-runbook.md',
                label="repo-task-acceptance",
                scenario_type="repo_task_acceptance",
                risk_profile="medium",
                operator_goal="prove one native run can satisfy the stronger multi-file repo-task acceptance contract",
                expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
                runtime_expectation="bounded native multi-file edits with verification on code targets and docs surface updates",
            ),
            WorkflowEvidenceCase(
                requirement='Replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "hook-based compliance checks updated" to docs/process/agent-orchestrator-implementation-process.md',
                label="repo-task-acceptance-compliance",
                scenario_type="repo_task_acceptance",
                risk_profile="medium",
                operator_goal="prove a second native run can satisfy the stronger multi-file repo-task acceptance contract",
                expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
                runtime_expectation="bounded native multi-file edits with verification on code targets and process surface updates",
            ),
            WorkflowEvidenceCase(
                requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "module manifest updated" to docs/process/module-manifest.md',
                label="repo-task-acceptance-helper",
                scenario_type="repo_task_acceptance",
                risk_profile="medium",
                operator_goal="prove a third native run can satisfy the stronger multi-file repo-task acceptance contract for a helper implementation task",
                expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
                runtime_expectation="bounded native helper implementation edits with verification on code targets and process surface updates",
            ),
            WorkflowEvidenceCase(
                requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "team runbook updated" to docs/process/agent-team-operator-runbook.md and append "module manifest updated" to docs/process/module-manifest.md and append "hook-based compliance checks updated" to docs/process/agent-orchestrator-implementation-process.md',
                label="repo-task-acceptance-long-chain-native-first",
                scenario_type="repo_task_acceptance",
                risk_profile="medium",
                operator_goal="prove a longer native-first repository task can close through exploration, multi-file editing, verification, and docs synchronization without external help",
                expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
                runtime_expectation="native exploration, multi-file mutation, verification, and repo-facing surface updates stay on the native path",
            ),
            WorkflowEvidenceCase(
                requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "root map updated" to docs/process/root-map.md and append "context map updated" to docs/process/context-map.md and append "project index updated" to docs/process/project-index.md and append "native upgrade plan updated" to docs/architecture/native-coding-agent-upgrade-plan.md',
                label="repo-task-acceptance-workspace-index-long-chain",
                scenario_type="repo_task_acceptance",
                risk_profile="medium",
                operator_goal="prove a second longer native-first repository task can close through exploration, multi-file editing, verification, and workspace/architecture index synchronization without external help",
                expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
                runtime_expectation="native exploration, multi-file mutation, verification, and workspace-facing architecture index updates stay on the native path",
            ),
            WorkflowEvidenceCase(
                requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "artifact contract updated" to docs/process/control-plane-artifact-contracts.md and append "dogfood evidence updated" to docs/process/native-coding-agent-dogfood-evidence.md and append "project index refreshed" to docs/process/project-index.md',
                label="repo-task-acceptance-evidence-contract-long-chain",
                scenario_type="repo_task_acceptance",
                risk_profile="medium",
                operator_goal="prove a third longer native-first repository task can close through exploration, multi-file editing, verification, and evidence-contract synchronization without external help",
                expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
                runtime_expectation="native exploration, multi-file mutation, verification, and evidence-facing contract updates stay on the native path",
            ),
        ],
        project_root=tmp_path,
    )

    proof_strength = payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]
    digest = payload["summary"]["comparative_benchmark_digest"]
    harness = payload["summary"]["daily_driver_repeatability_harness"]
    benchmark_harness = payload["summary"]["comparative_benchmark"]["daily_driver_repeatability_harness"]
    case_matrix = payload["summary"]["daily_driver_case_matrix"]
    runner = payload["summary"]["daily_driver_runner_artifact"]
    benchmark_runner = payload["summary"]["comparative_benchmark"]["daily_driver_runner_artifact"]

    assert proof_strength["direct_proof_status"] == "multiple_stronger_task_families_proven"
    assert proof_strength["repeatability_status"] == "broadly_proven_on_internal_repo_task_slice"
    assert proof_strength["daily_driver_repeatability_tier"] == "multi_family_broad_daily_driver_proven"
    assert proof_strength["stronger_task_families"] == [
        "compliance_process_repo_task",
        "evidence_contract_alignment_repo_task",
        "helper_implementation_repo_task",
        "long_chain_native_first_repo_task",
        "multi_file_operator_surface_repo_task",
        "workspace_index_alignment_repo_task",
    ]
    assert proof_strength["repo_task_acceptance_family_count"] == 6
    assert proof_strength["repo_task_acceptance_families_proven"] == [
        "compliance_process_repo_task",
        "evidence_contract_alignment_repo_task",
        "helper_implementation_repo_task",
        "long_chain_native_first_repo_task",
        "multi_file_operator_surface_repo_task",
        "workspace_index_alignment_repo_task",
    ]
    assert proof_strength["daily_driver_repo_task_family_count"] == 6
    assert proof_strength["daily_driver_repo_task_families_proven"] == [
        "compliance_process_repo_task",
        "evidence_contract_alignment_repo_task",
        "helper_implementation_repo_task",
        "long_chain_native_first_repo_task",
        "multi_file_operator_surface_repo_task",
        "workspace_index_alignment_repo_task",
    ]
    assert proof_strength["independent_daily_driver_repo_task_family_count"] == 6
    assert proof_strength["independent_daily_driver_repo_task_families_proven"] == [
        "compliance_process_repo_task",
        "evidence_contract_alignment_repo_task",
        "helper_implementation_repo_task",
        "long_chain_native_first_repo_task",
        "multi_file_operator_surface_repo_task",
        "workspace_index_alignment_repo_task",
    ]
    assert proof_strength["broader_repeatability_gap_families"] == []
    assert harness == benchmark_harness
    assert harness["format"] == "agent_orchestrator.daily_driver_repeatability_harness.v1"
    assert harness["harness_status"] == "daily_driver_ready"
    assert harness["same_contract_for_external_comparison"] is True
    assert harness["contract_outputs"] == ["runtime_payload", "workspace_index", "cli_summary"]
    assert harness["minimum_required_passing_family_count"] == 3
    assert harness["proven_family_count"] == 6
    assert harness["passing_family_count"] == 6
    assert harness["paused_family_count"] == 0
    assert harness["failed_family_count"] == 0
    assert harness["recovery_family_count"] == 6
    assert harness["stop_or_verify_coverage_ready"] is True
    assert harness["mock_only"] is False
    assert harness["external_opencode_harness_ready"] is False
    assert harness["next_external_step"] == "authoritative_opencode_case_harness"
    assert set(harness["family_results"]) == {
        "compliance_process_repo_task",
        "evidence_contract_alignment_repo_task",
        "helper_implementation_repo_task",
        "long_chain_native_first_repo_task",
        "multi_file_operator_surface_repo_task",
        "workspace_index_alignment_repo_task",
    }
    assert all(item["status"] == "passed" for item in harness["family_results"].values())
    assert all(item["verify_or_stop"] == "verify" for item in harness["family_results"].values())
    assert all(item["resume_reason"] for item in harness["family_results"].values())
    assert case_matrix["format"] == "agent_orchestrator.daily_driver_case_matrix.v1"
    assert case_matrix["matrix_status"] == "insufficient_coverage"
    assert case_matrix["minimum_required_family_count"] == 3
    assert case_matrix["covered_family_count"] == 1
    assert case_matrix["covered_case_count"] == 6
    assert case_matrix["covered_families"] == [
        "multi_file_operator_surface",
    ]
    assert case_matrix["missing_families"] == [
        "docs_update",
        "single_file_code_fix",
        "test_driven_feature",
        "failure_clarify_approval_pause",
    ]
    assert [row["task_family"] for row in case_matrix["matrix_rows"]] == [
        "docs_update",
        "single_file_code_fix",
        "multi_file_operator_surface",
        "test_driven_feature",
        "failure_clarify_approval_pause",
    ]
    assert case_matrix["matrix_rows"][0]["status"] == "missing"
    assert case_matrix["matrix_rows"][0]["verify_or_stop"] == "verify"
    assert runner == benchmark_runner
    assert runner["format"] == "agent_orchestrator.daily_driver_runner_artifact.v1"
    assert runner["runner_status"] == "repeatability_gap_remaining"
    assert runner["runner_family_count"] == 1
    assert runner["contract_outputs"] == ["runtime_payload", "workspace_index", "cli_summary"]
    assert runner["next_external_step"] == "authoritative_opencode_case_harness"
    assert runner["matrix_status"] == case_matrix["matrix_status"]
    assert runner["harness_status"] == harness["harness_status"]
    assert runner["runner_family_runs"][2]["task_family"] == "multi_file_operator_surface"
    assert "verify" in runner["runner_family_runs"][2]["steps"]
    assert payload["summary"]["comparative_benchmark"]["comparative_daily_driver_summary"]["daily_driver_runner_artifact"]["runner_status"] == "repeatability_gap_remaining"
    assert digest["daily_driver_runner_artifact_status"] == "repeatability_gap_remaining"
    assert digest["daily_driver_runner_artifact_contract_outputs"] == [
        "runtime_payload",
        "workspace_index",
        "cli_summary",
    ]
    assert case_matrix["matrix_rows"][2]["input"]["real_repo_case_count"] == 6
    assert case_matrix["matrix_rows"][2]["execution"]["repeatable"] is True
    assert case_matrix["matrix_rows"][4]["verification"]["required_stop_or_verify"] == "stop"
    assert payload["summary"]["comparative_benchmark"]["comparison_grade_assessment"]["status"] == "internal_repeatability_strong_external_comparison_gap_remaining"
    assert payload["summary"]["comparative_benchmark"]["comparison_grade_assessment"]["comparison_grade_ready"] is False
    assert payload["summary"]["comparative_benchmark"]["comparison_grade_assessment"]["internal_repeatability_ready"] is True
    assert payload["summary"]["comparative_benchmark"]["comparison_grade_assessment"]["external_harness_ready"] is False
    assert payload["summary"]["comparative_benchmark"]["comparison_grade_assessment"]["external_comparison_harness_surface"]["format"] == "agent_orchestrator.external_comparison_harness_surface.v1"
    assert payload["summary"]["comparative_benchmark"]["external_comparison_harness_surface"]["requirements"]["proven_independent_daily_driver_family_count"] == 6
    assert digest["direct_proof_status"] == "multiple_stronger_task_families_proven"
    assert digest["repeatability_status"] == "broadly_proven_on_internal_repo_task_slice"
    assert digest["daily_driver_repeatability_tier"] == "multi_family_broad_daily_driver_proven"
    assert digest["comparison_grade_status"] == "internal_repeatability_strong_external_comparison_gap_remaining"
    assert digest["comparison_grade_ready"] is False
    assert digest["external_harness_ready"] is False
    assert digest["external_harness_status"] == "missing_authoritative_opencode_harness"
    assert digest["external_harness_next_milestone"] == "authoritative_opencode_case_harness"
    assert digest["external_harness_operator_action"] == "maintain_human_audit_until_external_harness_ready"
    assert digest["repo_task_acceptance_family_count"] == 6
    assert digest["repo_task_acceptance_families_proven"] == [
        "compliance_process_repo_task",
        "evidence_contract_alignment_repo_task",
        "helper_implementation_repo_task",
        "long_chain_native_first_repo_task",
        "multi_file_operator_surface_repo_task",
        "workspace_index_alignment_repo_task",
    ]
    assert digest["stronger_task_families"] == [
        "compliance_process_repo_task",
        "evidence_contract_alignment_repo_task",
        "helper_implementation_repo_task",
        "long_chain_native_first_repo_task",
        "multi_file_operator_surface_repo_task",
        "workspace_index_alignment_repo_task",
    ]
    assert digest["daily_driver_repo_task_family_count"] == 6
    assert digest["daily_driver_repo_task_families_proven"] == [
        "compliance_process_repo_task",
        "evidence_contract_alignment_repo_task",
        "helper_implementation_repo_task",
        "long_chain_native_first_repo_task",
        "multi_file_operator_surface_repo_task",
        "workspace_index_alignment_repo_task",
    ]
    assert digest["independent_daily_driver_repo_task_family_count"] == 6
    assert digest["independent_daily_driver_repo_task_families_proven"] == [
        "compliance_process_repo_task",
        "evidence_contract_alignment_repo_task",
        "helper_implementation_repo_task",
        "long_chain_native_first_repo_task",
        "multi_file_operator_surface_repo_task",
        "workspace_index_alignment_repo_task",
    ]


def test_capture_workflow_evidence_records_native_repair_resume_success_chain(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement="Resume a failed native verification attempt, apply remaining repair budget, and prove re-verify success through runtime, workspace, and UI evidence surfaces",
                label="repair-resume-success",
                scenario_type="repair_resume_success",
                risk_profile="high",
                operator_goal="prove repair and governed resume can close natively",
                expected_signals=("recovery_guidance", "interruption_recovery", "doc_sync", "cost_latency"),
                runtime_expectation="remaining retry budget is consumed and ends in successful re-verification",
            )
        ],
        project_root=tmp_path,
    )

    case = payload["cases"][0]
    assert case["team_workflow"]["native_task_proof"]["native_runtime_only"] is True
    assert case["team_workflow"]["native_task_proof"]["external_coding_agent_required"] is False
    assert case["team_workflow"]["status"] == "completed"
    assert case["postmortem"]["native_task_proof_present"] is True
    assert case["postmortem"]["native_task_scenario"] == "verify_failure_repair_resume_success"
    assert case["native_runtime_closure"]["runtime_closure_ready"] is True
    assert case["native_runtime_closure"]["proof_scenario"] == "verify_failure_repair_resume_success"
    assert case["native_runtime_closure"]["closure_status"] == "completed"
    assert case["native_runtime_closure"]["checks"]["context_engineering_main_path_visible"]["passed"] is True
    assert case["native_runtime_closure"]["checks"]["context_engineering_main_path_visible"]["evidence"]["isolation_reinjection_mode"] in {"full_inline_context", "digest_focus_subset"}
    assert case["native_runtime_closure"]["checks"]["verify_repair_resume_closure"]["passed"] is True
    assert case["native_runtime_closure"]["checks"]["auditable_artifacts_and_surfaces"]["passed"] is True
    assert case["planner_continuity_proof"]["format"] == "agent_orchestrator.planner_continuity_proof.v1"
    assert case["planner_continuity_proof"]["planner_continuity_ready"] is True
    assert case["planner_continuity_proof"]["checks"]["planner_shared_contract_visible"]["passed"] is True
    assert case["planner_continuity_proof"]["checks"]["planner_actions_visible"]["passed"] is True
    assert case["planner_continuity_proof"]["checks"]["planner_owner_boundary_visible"]["passed"] is True
    assert case["planner_continuity_proof"]["checks"]["planner_closure_posture_visible"]["passed"] is True
    assert case["planner_continuity_proof"]["checks"]["workspace_session_continuity_visible"]["passed"] is True
    assert case["planner_continuity_proof"]["checks"]["ui_planner_and_session_visible"]["passed"] is True
    assert case["planner_continuity_proof"]["checks"]["resume_chain_scenario_visible"]["passed"] is True
    assert case["planner_continuity_proof"]["checks"]["governed_approval_boundary_continuity_visible"]["passed"] is True
    assert case["planner_continuity_proof"]["checks"]["governed_approval_boundary_continuity_visible"]["evidence"]["workspace_comparative_session_continuity"]["long_horizon_continuity_judgment"] == "daily_driver_continuity_governed_approval_boundary"
    assert case["program_execution_proof"]["format"] == "agent_orchestrator.program_execution_proof.v1"
    assert case["program_execution_proof"]["program_execution_ready"] is True
    assert case["program_execution_proof"]["checks"]["runtime_program_posture_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["workspace_program_posture_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["ui_program_posture_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["recovery_program_contract_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["topology_program_contract_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["topology_planner_intent_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["topology_adapter_shared_contract_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["resume_recovery_chain_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["governed_approval_boundary_continuity_visible"]["passed"] is True
    assert case["native_repo_task_acceptance"]["real_repo_task_acceptance_ready"] is False
    assert case["native_complex_repo_task_acceptance"]["complex_repo_task_ready"] is False
    assert case["native_dogfood_surfaces"]["surface_projection_ready"] is True
    assert case["native_dogfood_surfaces"]["proof_scenario"] == "verify_failure_repair_resume_success"
    assert case["native_dogfood_surfaces"]["surface_checks"]["runtime_event_stream_repo_task_acceptance_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_index_repo_task_acceptance_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_repo_task_acceptance_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_context_engineering_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_context_engineering_visible"]["evidence"]["context_isolation_reinjection_mode"] in {"full_inline_context", "digest_focus_subset", None}
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_native_tool_surface_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_native_tool_workflow_surface_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_native_tool_productization_surface_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_adapter_capability_surface_visible"]["passed"] is True
    assert "ui_execution_summary" in case["native_dogfood_surfaces"]["surface_checks"]["ui_adapter_capability_surface_visible"]["evidence"]["shared_evidence_surface"]
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_adapter_productization_surface_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_native_exploration_evidence_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_native_tool_surface_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_native_tool_workflow_surface_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_native_tool_productization_surface_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_adapter_capability_surface_visible"]["passed"] is True
    assert "workspace_index" in case["native_dogfood_surfaces"]["surface_checks"]["workspace_adapter_capability_surface_visible"]["evidence"]["shared_evidence_surface"]
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_adapter_productization_surface_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_adapter_capability_shared_contract_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_session_continuity_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_session_continuity_snapshot_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_governed_approval_boundary_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_session_posture_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_planner_closure_posture_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_session_shared_surface_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_runtime_cost_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_compacted_context_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_session_continuity_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_governed_approval_boundary_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_session_posture_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_planner_closure_posture_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_compacted_context_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["shared_approval_boundary_evidence_surface_visible"]["passed"] is True
    assert case["runtime_measurement"]["measurement_status"] == "measured"
    assert case["runtime_measurement"]["command_duration_available"] is True
    assert payload["summary"]["real_task_metrics"]["native_task_proof_coverage"] == 1
    assert payload["summary"]["real_task_metrics"]["native_runtime_closure_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["planner_continuity_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["program_execution_ready_cases"] == 1
    assert payload["summary"]["real_task_metrics"]["native_repo_task_acceptance_ready_cases"] == 0
    assert payload["summary"]["real_task_metrics"]["native_complex_repo_task_acceptance_ready_cases"] == 0
    assert payload["summary"]["real_task_metrics"]["native_dogfood_surface_ready_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["same_program_contract_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["shared_contract_alignment"]["session_continuity_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["shared_contract_alignment"]["planner_evidence_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["shared_contract_alignment"]["planner_closure_posture_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["shared_contract_alignment"]["planner_autonomy_boundary_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["shared_contract_alignment"]["planner_reasoning_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["shared_contract_alignment"]["adapter_contract_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["shared_contract_alignment"]["native_tool_usage_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["shared_contract_alignment"]["session_posture_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["shared_productization_contract_ready"] is True
    assert payload["summary"]["comparative_benchmark_digest"]["session_posture_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["comparison_posture_basis"]["shared_productization_contract_ready"] is True
    assert payload["summary"]["comparative_benchmark"]["comparison_posture_basis"]["long_chain_daily_driver_case_ready"] is False
    assert payload["summary"]["comparative_benchmark"]["comparison_posture_basis"]["planner_candidate_surface_ready"] is True
    assert payload["summary"]["comparative_benchmark"]["comparison_posture_basis"]["unified_adapter_contract_ready"] is True
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["direct_proof_status"] == "foundational_productization_only"
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["repeatability_ready"] is False
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["planner_candidate_status"] == "native_first_candidate_surface_ready"
    assert payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]["adapter_unification_status"] == "same_contract_adapter_surface_ready"
    assert payload["summary"]["comparative_benchmark"]["comparison_grade_assessment"]["status"] == "internal_productization_ready_but_repeatability_or_external_gap_remaining"
    assert payload["summary"]["comparative_benchmark"]["comparison_posture"]["status"] == "shared_productization_ready_but_daily_driver_proof_gap_remaining"
    assert "topology_snapshot" in payload["summary"]["comparative_benchmark"]["shared_evidence_surface"]
    assert "adapter_shared_contract" in payload["summary"]["comparative_benchmark"]["shared_evidence_surface"]
    assert "adapter_capability_surface" in payload["summary"]["comparative_benchmark"]["shared_evidence_surface"]
    assert "planner_autonomy_boundary" in payload["summary"]["comparative_benchmark"]["shared_evidence_surface"]
    assert "planner_reasoning" in payload["summary"]["comparative_benchmark"]["shared_evidence_surface"]
    assert "planner_shared_contract" in payload["summary"]["comparative_benchmark"]["shared_evidence_surface"]
    assert "session_productization_surface" in payload["summary"]["comparative_benchmark"]["shared_evidence_surface"]
    assert "planner_closure_posture" in payload["summary"]["comparative_benchmark"]["shared_evidence_surface"]
    assert "native_tool_workflow_surface" in payload["summary"]["comparative_benchmark"]["shared_evidence_surface"]
    assert "shared_productization_surface" in payload["summary"]["comparative_benchmark"]["shared_evidence_surface"]
    assert "native_tool_productization_surface" in payload["summary"]["comparative_benchmark"]["shared_evidence_surface"]
    assert "adapter_productization_surface" in payload["summary"]["comparative_benchmark"]["shared_evidence_surface"]
    assert "planner_closure_posture" in payload["summary"]["comparative_benchmark_digest"]["shared_evidence_surface"]
    assert "shared_productization_surface" in payload["summary"]["comparative_benchmark_digest"]["shared_evidence_surface"]
    assert "native_tool_workflow_surface" in payload["summary"]["comparative_benchmark_digest"]["shared_evidence_surface"]
    assert "adapter_capability_surface" in payload["summary"]["comparative_benchmark_digest"]["shared_evidence_surface"]
    assert "planner_autonomy_boundary" in payload["summary"]["comparative_benchmark_digest"]["shared_evidence_surface"]
    assert "planner_reasoning" in payload["summary"]["comparative_benchmark_digest"]["shared_evidence_surface"]
    assert payload["summary"]["comparative_benchmark"]["governed_fallback_hot_plug_preserved"] is True


def test_capture_workflow_evidence_records_multi_milestone_program_execution_chain(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement="Advance a multi-milestone native workstream through explore, edit, verify, checkpoint, and governed continue while keeping delegation and recovery boundaries visible",
                label="multi-milestone-program",
                scenario_type="program_execution",
                risk_profile="high",
                operator_goal="prove native long-horizon program execution posture",
                expected_signals=("recovery_guidance", "interruption_recovery", "doc_sync", "cost_latency"),
                runtime_expectation="program checkpoint and continue remain operator-visible",
            )
        ],
        project_root=tmp_path,
    )

    case = payload["cases"][0]
    assert case["team_workflow"]["status"] == "completed"
    assert case["program_execution_proof"]["format"] == "agent_orchestrator.program_execution_proof.v1"
    assert case["program_execution_proof"]["program_execution_ready"] is True
    assert case["program_execution_proof"]["checks"]["runtime_program_posture_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["workspace_program_posture_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["ui_program_posture_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["recovery_program_contract_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["recovery_session_posture_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["topology_program_contract_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["topology_session_posture_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["resume_recovery_chain_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["governed_approval_boundary_continuity_visible"]["passed"] is True
    assert case["program_execution_proof"]["checks"]["governed_approval_boundary_continuity_visible"]["evidence"]["workspace_comparative_session_continuity"]["long_horizon_continuity_judgment"] == "daily_driver_continuity_governed_approval_boundary"
    assert case["program_execution_proof"]["checks"]["runtime_program_posture_visible"]["evidence"]["active_milestone"]
    assert case["native_dogfood_surfaces"]["surface_checks"]["workspace_governed_approval_boundary_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["ui_governed_approval_boundary_visible"]["passed"] is True
    assert case["native_dogfood_surfaces"]["surface_checks"]["shared_approval_boundary_evidence_surface_visible"]["passed"] is True
    assert payload["summary"]["real_task_metrics"]["program_execution_ready_cases"] == 1
    assert payload["summary"]["comparative_benchmark"]["same_program_contract_cases"] == 1


def test_postmortem_signals_and_summary_capture_native_task_proof_when_present() -> None:
    case = WorkflowEvidenceCase(
        requirement="Complete a bounded internal repository task",
        label="native-proof",
        expected_signals=("recovery_guidance", "cost_latency"),
    )
    signals = {
        "recovery": {"has_guidance": True},
        "doc_sync": {"status": "passed"},
        "fallback": {"present": False},
    }
    status_summary = {
        "usage_cost": {"source": "placeholder"},
        "approval_state": {"state": "completed"},
        "runtime_health": {"job_count": 1},
    }
    execution_payload = {
        "native_task_proof": {
            "format": "agent_orchestrator.native_task_proof.v1",
            "native_runtime_only": True,
            "external_coding_agent_required": False,
            "task_class": "bounded_internal_repo_task",
            "proof_scenario": "verify_failure_repair_resume_success",
        }
    }

    postmortem = _postmortem_signals(case, signals, status_summary, execution_payload)
    summary = _build_summary([{"postmortem": postmortem}])

    assert postmortem["native_task_proof_present"] is True
    assert postmortem["native_task_class"] == "bounded_internal_repo_task"
    assert postmortem["native_task_scenario"] == "verify_failure_repair_resume_success"
    assert summary["real_task_metrics"]["native_task_proof_coverage"] == 1


def test_repository_evidence_cases_are_loadable() -> None:
    cases = load_workflow_evidence_cases("docs/process/evidence-cases.json")

    assert {case.scenario_type for case in cases} == {
        "standard",
        "followup",
        "high_risk",
        "parallel",
        "ui_workflow",
        "compliance_blocking",
        "runtime_fidelity",
        "interruption_recovery",
        "repair_resume_success",
        "program_execution",
        "repo_task_acceptance",
    }
    assert "cli_workflow_hardening" in {case.label for case in cases}
    assert "repo_task_acceptance_long_chain_native_first" in {case.label for case in cases}
    assert "repo_task_acceptance_workspace_index_long_chain" in {case.label for case in cases}
    assert len(cases) >= 8
    assert all(case.label for case in cases)
    assert all(case.requirement for case in cases)
    assert all(case.risk_profile for case in cases)
    assert all(case.operator_goal for case in cases)
    assert all(case.expected_signals for case in cases)
    assert all(case.runtime_expectation for case in cases)


def test_repository_evidence_case_catalog_can_prove_multi_family_daily_driver_benchmark(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    cases = [
        case
        for case in load_workflow_evidence_cases("docs/process/evidence-cases.json")
        if case.scenario_type == "repo_task_acceptance"
    ]

    payload = capture_workflow_evidence(cases, project_root=tmp_path)

    proof_strength = payload["summary"]["comparative_benchmark"]["comparison_proof_strength"]
    benchmark = payload["summary"]["comparative_benchmark"]
    digest = payload["summary"]["comparative_benchmark_digest"]
    case_matrix = payload["summary"]["daily_driver_case_matrix"]

    assert len(cases) == 6
    assert proof_strength["direct_proof_status"] == "multiple_stronger_task_families_proven"
    assert proof_strength["repeatability_status"] == "broadly_proven_on_internal_repo_task_slice"
    assert proof_strength["repeatability_ready"] is True
    assert proof_strength["daily_driver_repeatability_tier"] == "multi_family_broad_daily_driver_proven"
    assert proof_strength["repo_task_acceptance_family_count"] == 6
    assert proof_strength["daily_driver_repo_task_family_count"] == 6
    assert proof_strength["independent_daily_driver_repo_task_family_count"] == 6
    assert proof_strength["stronger_task_families"] == [
        "compliance_process_repo_task",
        "evidence_contract_alignment_repo_task",
        "helper_implementation_repo_task",
        "long_chain_native_first_repo_task",
        "multi_file_operator_surface_repo_task",
        "workspace_index_alignment_repo_task",
    ]
    assert proof_strength["broader_repeatability_gap_families"] == []
    assert benchmark["comparison_posture"]["status"] == "daily_driver_main_path_proven_breadth_gap_remaining"
    assert benchmark["comparison_grade_assessment"]["status"] == "internal_repeatability_strong_external_comparison_gap_remaining"
    assert benchmark["comparison_grade_assessment"]["internal_repeatability_ready"] is True
    assert benchmark["comparison_grade_assessment"]["external_harness_ready"] is False
    assert benchmark["external_comparison_harness_surface"]["requirements"]["proven_independent_daily_driver_family_count"] == 6
    assert digest["comparison_status"] == "daily_driver_main_path_proven_breadth_gap_remaining"
    assert digest["direct_proof_status"] == "multiple_stronger_task_families_proven"
    assert digest["repeatability_status"] == "broadly_proven_on_internal_repo_task_slice"
    assert digest["daily_driver_repeatability_tier"] == "multi_family_broad_daily_driver_proven"
    assert digest["comparison_grade_status"] == "internal_repeatability_strong_external_comparison_gap_remaining"
    assert digest["independent_daily_driver_repo_task_family_count"] == 6
    assert "workspace_index" in digest["shared_evidence_surface"]
    assert "ui_execution_summary" in digest["shared_evidence_surface"] or "team_summary" in digest["shared_evidence_surface"]
    assert payload["summary"]["comparative_benchmark"]["comparative_daily_driver_summary"]["format"] == "agent_orchestrator.comparative_daily_driver_summary.v1"
    assert case_matrix["format"] == "agent_orchestrator.daily_driver_case_matrix.v1"
    assert case_matrix["matrix_status"] == "insufficient_coverage"
    assert case_matrix["minimum_required_family_count"] == 3
    assert case_matrix["covered_family_count"] == 1
    assert case_matrix["covered_case_count"] == 6
    assert case_matrix["covered_families"] == [
        "multi_file_operator_surface",
    ]
    assert all(row["evidence"]["contract_outputs"] == ["runtime_payload", "workspace_index", "cli_summary"] for row in case_matrix["matrix_rows"])


def test_repository_evidence_case_catalog_can_prove_daily_driver_case_matrix(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)

    cases = load_workflow_evidence_cases("docs/process/evidence-cases.json")

    payload = capture_workflow_evidence(cases, project_root=tmp_path)
    case_matrix = payload["summary"]["daily_driver_case_matrix"]

    assert case_matrix["format"] == "agent_orchestrator.daily_driver_case_matrix.v1"
    assert case_matrix["matrix_status"] == "multi_family_case_matrix_ready"
    assert case_matrix["minimum_required_family_count"] == 3
    assert case_matrix["covered_family_count"] == 5
    assert case_matrix["covered_case_count"] >= 15
    assert case_matrix["covered_families"] == [
        "docs_update",
        "single_file_code_fix",
        "multi_file_operator_surface",
        "test_driven_feature",
        "failure_clarify_approval_pause",
    ]
    assert case_matrix["missing_families"] == []
    assert all(row["coverage_ready"] is True for row in case_matrix["matrix_rows"])
    assert all(row["input"]["real_repo_case_count"] >= 1 for row in case_matrix["matrix_rows"])
    assert all(row["execution"]["repeatable"] is True for row in case_matrix["matrix_rows"])
    assert all(row["evidence"]["contract_outputs"] == ["runtime_payload", "workspace_index", "cli_summary"] for row in case_matrix["matrix_rows"])


def test_build_comparative_daily_driver_benchmark_matches_shared_operator_text() -> None:
    assert (
        build_comparative_daily_driver_benchmark(
            {
                "daily_driver_repeatability_tier": "multi_family_broad_daily_driver_proven",
                "independent_daily_driver_repo_task_family_count": 6,
            }
        )
        == "official_catalog=docs/process/evidence-cases.json independent_daily_driver_families=6 status=multi_family_broad_daily_driver_proven"
    )
    assert build_comparative_daily_driver_benchmark({}) is None




def test_external_opencode_same_contract_harness_builds_case_pack_and_comparison_report(tmp_path) -> None:
    case_pack = build_same_contract_case_pack()
    case_pack_path = write_case_pack(tmp_path / "external-opencode-same-contract-cases.json", case_pack)
    native_records = build_native_run_records(case_pack)
    opencode_records = build_opencode_run_records(case_pack)
    report = build_comparative_evidence_report(case_pack, native_records, opencode_records)
    bundle = build_external_opencode_harness_bundle()

    assert case_pack_path.exists()
    assert case_pack["contract_version"] == CASE_PACK_VERSION
    assert case_pack["case_family_count"] == 5
    assert case_pack["required_task_families"] == [
        "docs_update",
        "single_file_repair",
        "multi_file_operator_surface",
        "test_driven_small_feature",
        "failure_clarify_approval_path",
    ]
    assert len(case_pack["cases"]) == 5
    assert case_pack["cases"][0]["required_evidence_surface"] == [
        "runtime_payload",
        "workspace_index_summary",
        "operator_summary",
        "failure_pause_recovery_reason",
    ]
    assert native_records["run_record_set_version"] == "native_external_runner_record.v1"
    assert native_records["runner"] == "native"
    assert opencode_records["run_record_set_version"] == OPENCODE_RUN_RECORD_VERSION
    assert opencode_records["runner"] == "opencode"
    assert len(native_records["records"]) == 5
    assert len(opencode_records["records"]) == 5
    assert all(record["runtime_payload"]["model"]["value"] == "unavailable" for record in opencode_records["records"])
    assert all(record["runtime_payload"]["provider"]["value"] == "unavailable" for record in opencode_records["records"])
    assert all(record["workspace_index_summary"]["verify_commands"] is not None for record in opencode_records["records"])
    assert report["report_version"] == COMPARATIVE_REPORT_VERSION
    assert report["case_result_count"] == 5
    assert report["operator_decision"]["recommended_path"] in {
        "continue_opencode_ecosystem_chase",
        "native_productization_next",
        "instrumentation_first",
        "mixed_strategy",
        "instrumentation_still_blocking",
        "instrumentation_closed_native_productization_next",
        "instrumentation_closed_continue_opencode_ecosystem_chase",
        "instrumentation_partially_closed_mixed_strategy",
    }
    assert report["case_results"][0]["gap_classification"]
    assert bundle["case_pack"]["contract_version"] == CASE_PACK_VERSION
    assert bundle["comparative_evidence_report"]["report_version"] == COMPARATIVE_REPORT_VERSION
    assert bundle["authoritative_comparative_report"]["report_version"] == AUTHORITATIVE_REPORT_VERSION
    assert bundle["instrumentation_closure"]["status"] == "still_blocking"
    assert bundle["operator_decision"]["decision"] == "instrumentation_still_blocking"






def test_authoritative_opencode_harness_normalizes_records_and_closes_executed_timing_surface(tmp_path) -> None:
    case_pack = build_same_contract_case_pack()
    native_records = build_native_run_records(case_pack)
    opencode_records = build_opencode_run_records(case_pack, command_template="printf case:{case_id}", authoritative_runner=True)
    normalized = normalize_run_records(opencode_records, case_pack)
    report = build_authoritative_comparative_report(case_pack, native_records, opencode_records)

    assert normalized["normalized_record_set_version"] == NORMALIZED_RECORD_VERSION
    assert normalized["runner"] == "opencode"
    first = normalized["records"][0]
    assert first["normalized_record_version"] == NORMALIZED_RECORD_VERSION
    assert first["runtime_payload"]["command"]["state"] == "available"
    assert first["runtime_payload"]["exit_status"]["state"] == "available"
    assert first["runtime_payload"]["started_at"]["state"] == "available"
    assert first["runtime_payload"]["ended_at"]["state"] == "available"
    assert first["runtime_payload"]["duration_ms"]["state"] == "available"
    assert first["workspace_index_summary"]["state"] == "available"
    assert first["operator_summary"]["readability"] == "clear"
    assert report["report_version"] == AUTHORITATIVE_REPORT_VERSION
    assert report["normalized_record_version"] == NORMALIZED_RECORD_VERSION
    assert report["case_result_count"] == 5
    assert report["instrumentation_closure"]["status"] == "closed"
    assert report["instrumentation_closure"]["blocked_case_count"] == 0
    assert report["operator_decision"]["decision"] == "instrumentation_closed_native_productization_next"
    assert all(result["command_execution_evidence"]["opencode"] is True for result in report["case_results"])

def test_external_opencode_harness_cli_runs_case_pack_records_and_report(tmp_path) -> None:
    from agent_orchestrator.cli import main
    import sys

    case_pack = tmp_path / "case-pack.json"
    native_records = tmp_path / "native-run.json"
    opencode_records = tmp_path / "opencode-run.json"
    report = tmp_path / "report.json"
    normalized = tmp_path / "opencode-normalized.json"
    authoritative_report = tmp_path / "authoritative-report.json"

    commands = [
        ["agent-orchestrator", "evidence", "case-pack", "--output", str(case_pack), "--format", "json"],
        ["agent-orchestrator", "evidence", "native-run", "--case-pack", str(case_pack), "--output", str(native_records), "--format", "json"],
        ["agent-orchestrator", "evidence", "opencode-run", "--case-pack", str(case_pack), "--output", str(opencode_records), "--format", "json", "--command-template", "printf case:{case_id}"],
        ["agent-orchestrator", "evidence", "normalize-records", "--case-pack", str(case_pack), "--records", str(opencode_records), "--output", str(normalized), "--format", "json"],
        [
            "agent-orchestrator",
            "evidence",
            "external-report",
            "--case-pack",
            str(case_pack),
            "--native-records",
            str(native_records),
            "--opencode-records",
            str(opencode_records),
            "--output",
            str(report),
            "--format",
            "json",
        ],
        [
            "agent-orchestrator",
            "evidence",
            "authoritative-report",
            "--case-pack",
            str(case_pack),
            "--native-records",
            str(native_records),
            "--opencode-records",
            str(opencode_records),
            "--output",
            str(authoritative_report),
            "--format",
            "json",
        ],
    ]
    old_argv = sys.argv
    try:
        for command in commands:
            sys.argv = command
            main()
    finally:
        sys.argv = old_argv

    assert json.loads(case_pack.read_text())["contract_version"] == CASE_PACK_VERSION
    assert json.loads(native_records.read_text())["runner"] == "native"
    opencode_payload = json.loads(opencode_records.read_text())
    assert opencode_payload["runner"] == "opencode"
    assert opencode_payload["records"][0]["runtime_payload"]["command"].startswith("printf case:")
    payload = json.loads(report.read_text())
    assert payload["report_version"] == COMPARATIVE_REPORT_VERSION
    assert payload["case_result_count"] == 5
    assert payload["operator_decision"]["recommended_path"] == "instrumentation_first"
    assert json.loads(normalized.read_text())["normalized_record_set_version"] == NORMALIZED_RECORD_VERSION
    authoritative_payload = json.loads(authoritative_report.read_text())
    assert authoritative_payload["report_version"] == AUTHORITATIVE_REPORT_VERSION
    assert authoritative_payload["instrumentation_closure"]["status"] == "still_blocking"
    assert authoritative_payload["operator_decision"]["decision"] == "instrumentation_still_blocking"



def test_authoritative_opencode_cli_requires_explicit_authoritative_runner_flag(tmp_path) -> None:
    from agent_orchestrator.cli import main
    import sys

    case_pack = tmp_path / "case-pack.json"
    native_records = tmp_path / "native-run.json"
    opencode_records = tmp_path / "opencode-authoritative-run.json"
    report = tmp_path / "authoritative-report.json"
    commands = [
        ["agent-orchestrator", "evidence", "case-pack", "--output", str(case_pack), "--format", "json"],
        ["agent-orchestrator", "evidence", "native-run", "--case-pack", str(case_pack), "--output", str(native_records), "--format", "json"],
        ["agent-orchestrator", "evidence", "opencode-run", "--case-pack", str(case_pack), "--output", str(opencode_records), "--format", "json", "--command-template", "printf case:{case_id}", "--authoritative-runner"],
        ["agent-orchestrator", "evidence", "authoritative-report", "--case-pack", str(case_pack), "--native-records", str(native_records), "--opencode-records", str(opencode_records), "--output", str(report), "--format", "json"],
    ]
    old_argv = sys.argv
    try:
        for command in commands:
            sys.argv = command
            main()
    finally:
        sys.argv = old_argv
    opencode_payload = json.loads(opencode_records.read_text())
    assert opencode_payload["records"][0]["runner_authority"]["authoritative"] is True
    payload = json.loads(report.read_text())
    assert payload["instrumentation_closure"]["status"] == "closed"
    assert payload["operator_decision"]["decision"] == "instrumentation_closed_native_productization_next"

def test_external_opencode_harness_summary_exposes_comparison_artifacts(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    payload = capture_workflow_evidence(load_workflow_evidence_cases("docs/process/evidence-cases.json"), project_root=tmp_path)
    summary = payload["summary"]
    benchmark = summary["comparative_benchmark"]
    digest = payload["summary"]["comparative_benchmark_digest"]

    assert summary["external_opencode_harness"]["case_pack"]["contract_version"] == CASE_PACK_VERSION
    assert summary["external_opencode_case_pack"]["contract_version"] == CASE_PACK_VERSION
    assert summary["opencode_runner_adapter"]["run_record_set_version"] == OPENCODE_RUN_RECORD_VERSION
    assert summary["native_vs_opencode_comparative_report"]["report_version"] == COMPARATIVE_REPORT_VERSION
    assert summary["authoritative_native_vs_opencode_report"]["report_version"] == AUTHORITATIVE_REPORT_VERSION
    assert summary["external_opencode_instrumentation_closure"]["status"] == "still_blocking"
    assert summary["external_opencode_operator_decision"]["decision"] == "instrumentation_still_blocking"
    assert summary["external_opencode_operator_decision"].get("recommended_path") in {
        "instrumentation_still_blocking",
        "instrumentation_closed_native_productization_next",
        "instrumentation_closed_continue_opencode_ecosystem_chase",
        "instrumentation_partially_closed_mixed_strategy",
    }
    assert benchmark["external_opencode_harness"]["case_pack"]["contract_version"] == CASE_PACK_VERSION
    assert benchmark["external_opencode_case_pack"]["contract_version"] == CASE_PACK_VERSION
    assert benchmark["opencode_runner_adapter"]["run_record_set_version"] == OPENCODE_RUN_RECORD_VERSION
    assert benchmark["native_vs_opencode_comparative_report"]["case_result_count"] == 5
    assert benchmark["authoritative_native_vs_opencode_report"]["case_result_count"] == 5
    assert benchmark["external_opencode_instrumentation_closure"]["status"] == "still_blocking"
    assert benchmark["external_opencode_operator_decision"]["gap_counts"]
    assert digest["external_harness_status"] == "missing_authoritative_opencode_harness"

def test_render_workflow_evidence_markdown_reports_summary_and_signals(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    payload = capture_workflow_evidence(["Build a persisted plan artifact"], project_root=tmp_path)
    output_path = tmp_path / "report.md"

    write_workflow_evidence_markdown(payload, output_path)
    markdown = output_path.read_text(encoding="utf-8")

    assert markdown == render_workflow_evidence_markdown(payload)
    assert "# v1.x Evidence Report" in markdown
    assert "average_benefit_score" in markdown
    assert "provenance_matches_plan_session" in markdown
    assert "## Conclusion Summary" in markdown
    assert "planning_quality:" in markdown
    assert "rescue_quality:" in markdown
    assert "runtime_limitation:" in markdown
    assert "fixed_template_advantage:" in markdown
    assert "## Real-Task Dogfood Metrics" in markdown
    assert "## Runtime Measurement Metrics" in markdown
    assert "measured_runtime_cases" in markdown
    assert "postmortem_ready_cases" in markdown
    assert "native_task_proof_coverage" in markdown
    assert "native_runtime_closure_ready_cases" in markdown
    assert "planner_continuity_ready_cases" in markdown
    assert "native_repo_task_acceptance_ready_cases" in markdown
    assert "native_complex_repo_task_acceptance_ready_cases" in markdown
    assert "long_chain_native_first_ready_cases" in markdown
    assert "daily_driver_main_path_ready_cases" in markdown
    assert "native_dogfood_surface_ready_cases" in markdown
    assert "## Native Runtime Closure" in markdown
    assert "## Native Repo Task Acceptance" in markdown
    assert "## Comparative Benchmark" in markdown
    assert "## Comparative Benchmark Digest" in markdown
    assert "shared_productization_contract_ready" in markdown
    assert "comparison_grade_assessment: status=" in markdown
    assert "daily_driver_case_matrix: status=" in markdown
    assert "covered_family_count=" in markdown
    assert "daily_driver_repeatability_harness: status=" in markdown
    assert "contract_outputs=runtime_payload,workspace_index,cli_summary" in markdown
    assert "external_comparison_harness_surface: status=" in markdown
    assert "required_shared_surface_count=" in markdown
    assert "required_external_artifact_count=" in markdown
    assert "missing_external_artifact_count=" in markdown
    assert "shared_productization_surface_visible: True" in markdown
    assert "comparison_posture: status=" in markdown
    assert "comparison_posture_basis: shared_productization_ready=" in markdown
    assert "comparison_proof_strength: direct_proof_status=" in markdown
    assert "adapter_unification_status" in markdown
    assert "approval_boundary_active=" not in markdown or "approval_boundary_active=" in markdown
    assert "governed_pause_resume_ready=" not in markdown or "governed_pause_resume_ready=" in markdown
    assert "stronger_task_families=none" in markdown
    assert "repo_task_acceptance_family_count=0" in markdown
    assert "repo_task_acceptance_families_proven=none" in markdown
    assert "daily_driver_repo_task_family_count=0" in markdown
    assert "daily_driver_repo_task_families_proven=none" in markdown
    assert "independent_daily_driver_repo_task_family_count=0" in markdown
    assert "independent_daily_driver_repo_task_families_proven=none" in markdown
    assert "broader_repeatability_gap_families=multi_family_daily_driver_repo_tasks" in markdown
    assert "comparative_benchmark_digest: comparison_status=" in markdown
    assert "comparison_grade_status=" in markdown
    assert "shared_contract_alignment: session_continuity_cases=" in markdown
    assert "session_posture_cases=" in markdown
    assert "native_tool_usage_cases=" in markdown
    assert "complex_repo_task_checks" in markdown
    assert "## Native Dogfood Surfaces" in markdown
    assert "context_engineering_main_path_visible" in markdown
    assert "ui_context_engineering_visible" in markdown
    assert "native_runtime_closure: ready=False" in markdown


def test_render_workflow_evidence_markdown_reports_planner_closure_posture_for_native_productization_case(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement="Resume a failed native verification attempt, apply remaining repair budget, and prove re-verify success through runtime, workspace, and UI evidence surfaces",
                label="repair-resume-success",
                scenario_type="repair_resume_success",
                risk_profile="high",
                operator_goal="prove repair and governed resume can close natively",
                expected_signals=("recovery_guidance", "interruption_recovery", "doc_sync", "cost_latency"),
                runtime_expectation="remaining retry budget is consumed and ends in successful re-verification",
            )
        ],
        project_root=tmp_path,
    )

    markdown = render_workflow_evidence_markdown(payload)

    assert "planner_closure_posture: closure_mode=" in markdown
    assert "comparative_native_tool_summary: posture=" in markdown
    assert "operator_tool_digest: posture=" in markdown
    assert "operator_planner_digest: primary=" in markdown
    assert "comparative_planner_candidate_summary: native_first=" in markdown
    assert "decision_mode=" in markdown
    assert "autonomy_actions=" in markdown
    assert "comparative_adapter_summary: status=" in markdown
    assert "comparative_session_posture_summary: primary=" in markdown
    assert "comparative_session_continuity_summary: status=" in markdown
    assert "workflow_stage=" in markdown
    assert "workflow_projection_ready=" in markdown
    assert "workflow_projection_visible=" in markdown
    assert "comparative_native_closure_summary: native_runtime_only=" in markdown
    assert "operator_posture_digest: status=" in markdown or "operator_posture_digest: " in markdown
    assert "alternatives=" in markdown
    assert "comparative_daily_driver_summary: status=" in markdown
    assert "comparative_benchmark_digest_planner_closure: closure_mode=" in markdown
    assert "comparative_benchmark_digest_native_tool_summary: posture=" in markdown
    assert "comparative_benchmark_digest_adapter_summary: status=" in markdown
    assert "planner_continuity_proof: ready=" in markdown
    assert "context_engineering: surfaces=" not in markdown or "context_engineering: surfaces=" in markdown
    assert "native_repo_task_acceptance: ready=False" in markdown or "native_repo_task_acceptance: ready=True" in markdown
    assert "native_complex_repo_task_acceptance: ready=False" in markdown or "native_complex_repo_task_acceptance: ready=True" in markdown
    assert "native_dogfood_surfaces: ready=" in markdown


def test_render_workflow_evidence_markdown_reports_clarify_boundary_digest_when_present(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement="Resume a failed native verification attempt, apply remaining repair budget, and prove re-verify success through runtime, workspace, and UI evidence surfaces",
                label="repair-resume-success",
                scenario_type="repair_resume_success",
                risk_profile="high",
                operator_goal="prove repair and governed resume can close natively",
                expected_signals=("recovery_guidance", "interruption_recovery", "doc_sync", "cost_latency"),
                runtime_expectation="remaining retry budget is consumed and ends in successful re-verification",
            )
        ],
        project_root=tmp_path,
    )
    payload["summary"]["comparative_benchmark"]["clarify_boundary_digest"] = {
        "format": "agent_orchestrator.clarify_boundary_digest.v1",
        "status": "planner_clarify_boundary",
        "selected_execution_strategy": "clarify_then_edit",
        "next_recommended_action": "clarify_scope",
        "resume_expectation": "clarify_scope",
        "recovery_lane": "continue_native",
        "shared_evidence_surface": ["runtime_payload", "clarify_boundary_digest", "workspace_index", "evidence_report"],
    }
    payload["summary"]["comparative_benchmark_digest"]["clarify_boundary_status"] = "planner_clarify_boundary"
    payload["summary"]["comparative_benchmark_digest"]["clarify_boundary_active"] = True
    payload["summary"]["comparative_benchmark_digest"]["clarify_boundary_next_action"] = "clarify_scope"
    payload["summary"]["comparative_benchmark_digest"]["clarify_boundary_resume_expectation"] = "clarify_scope"

    markdown = render_workflow_evidence_markdown(payload)

    assert "clarify_boundary_digest: status=planner_clarify_boundary" in markdown
    assert "strategy=clarify_then_edit" in markdown
    assert "next_action=clarify_scope" in markdown
    assert "comparative_benchmark_digest_clarify_boundary: status=planner_clarify_boundary" in markdown
    assert "shared_evidence_surface=runtime_payload,clarify_boundary_digest,workspace_index,evidence_report" in markdown
    assert "daily_driver_main_path: workspace=" not in markdown or "daily_driver_main_path: workspace=" in markdown
    assert "## Takeaways" in markdown


def test_render_workflow_evidence_markdown_reports_approval_boundary_digest_when_present(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    payload = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(
                requirement="Resume a failed native verification attempt, apply remaining repair budget, and prove re-verify success through runtime, workspace, and UI evidence surfaces",
                label="approval-boundary",
                scenario_type="repair_resume_success",
                risk_profile="high",
                operator_goal="prove planner approval boundary stays visible across shared evidence surfaces",
                expected_signals=("recovery_guidance", "interruption_recovery", "doc_sync", "cost_latency"),
                runtime_expectation="approval pause remains visible until human confirmation resumes execution",
            )
        ],
        project_root=tmp_path,
    )
    payload["summary"]["comparative_benchmark"]["approval_boundary_digest"] = {
        "format": "agent_orchestrator.approval_boundary_digest.v1",
        "status": "planner_approval_boundary",
        "selected_execution_strategy": "need_human_confirmation",
        "next_recommended_action": "human_review",
        "resume_expectation": "approval_pause",
        "recovery_lane": "approval_pause",
        "shared_evidence_surface": ["runtime_payload", "approval_boundary_digest", "workspace_index", "evidence_report"],
    }
    payload["summary"]["comparative_benchmark_digest"]["approval_boundary_status"] = "planner_approval_boundary"
    payload["summary"]["comparative_benchmark_digest"]["approval_boundary_active"] = True
    payload["summary"]["comparative_benchmark_digest"]["approval_boundary_next_action"] = "human_review"
    payload["summary"]["comparative_benchmark_digest"]["approval_boundary_resume_expectation"] = "approval_pause"

    markdown = render_workflow_evidence_markdown(payload)

    assert "approval_boundary_digest: status=planner_approval_boundary" in markdown
    assert "strategy=need_human_confirmation" in markdown
    assert "next_action=human_review" in markdown
    assert "shared_evidence_surface=runtime_payload,approval_boundary_digest,workspace_index,evidence_report" in markdown


def test_compare_workflow_evidence_reports_trend_deltas(tmp_path) -> None:
    write_minimal_process_docs(tmp_path)
    baseline = capture_workflow_evidence(
        [WorkflowEvidenceCase(requirement="Build a persisted plan artifact", label="artifact", scenario_type="standard")],
        project_root=tmp_path,
    )
    current = capture_workflow_evidence(
        [
            WorkflowEvidenceCase(requirement="Build a persisted plan artifact", label="artifact", scenario_type="standard"),
            WorkflowEvidenceCase(requirement="Build a persisted plan artifact", label="artifact_2", scenario_type="standard"),
        ],
        project_root=tmp_path,
    )
    output_path = tmp_path / "trend.md"

    trend = compare_workflow_evidence(baseline, current)
    write_workflow_evidence_trend_markdown(trend, output_path)
    markdown = output_path.read_text(encoding="utf-8")

    assert trend["deltas"]["case_count"] == 1
    assert trend["deltas"]["scenario_aggregates"]["standard"]["case_count"] == 1
    assert trend["deltas"]["team_advantage_counts"]["recovery_guidance"] == 1
    assert trend["deltas"]["signal_counts"]["doc_sync_present"] == 1
    assert trend["deltas"]["real_task_metrics"]["postmortem_ready_cases"] == 1
    assert trend["deltas"]["runtime_measurement_metrics"]["measured_runtime_cases"] == 1
    assert "# v1.x Evidence Trend" in markdown
    assert "average_benefit_score_delta" in render_workflow_evidence_trend_markdown(trend)
    assert "current_version_assessment: better" in markdown
    assert "## Version Assessment" in markdown
    assert "## Comparative Proof Strength" in markdown
    assert "baseline_direct_proof_status:" in markdown
    assert "current_repeatability_status:" in markdown
    assert "stronger_task_family_count_delta:" in markdown
    assert "current_is_better: yes" in markdown
    assert "## Real-Task Metric Deltas" in markdown
    assert "## Runtime Measurement Deltas" in markdown
    assert "## Interpretation" in markdown
