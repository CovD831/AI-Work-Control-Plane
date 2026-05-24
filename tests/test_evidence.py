# DEPS: agent_orchestrator, json, pathlib
# RESPONSIBILITY: Verify workflow evidence harness output and persisted artifact shape.
# MODULE: tests
# ---

from __future__ import annotations

import json

from agent_orchestrator.evidence import (
    EVIDENCE_SCHEMA_VERSION,
    WorkflowEvidenceCase,
    benchmark_evidence_cases,
    capture_workflow_evidence,
    load_workflow_evidence_cases,
    render_workflow_evidence_markdown,
    write_workflow_evidence_markdown,
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
    assert "no_approved_plan_artifact" in case["comparison"]["direct_limitations"]
    assert case["team_workflow"]["approved_plan_source"] == "approved_plan_session"
    assert case["comparison"]["benefit_score"] >= 4
    assert case["signals"]["provenance"]["present"] is True
    assert case["signals"]["provenance"]["matches_plan_session"] is True
    assert case["signals"]["recovery"]["has_guidance"] is True
    assert case["signals"]["doc_sync"]["present"] is True
    assert case["signals"]["doc_sync"]["status"] == "passed"
    assert case["signals"]["fallback"]["present"] in {True, False}
    assert payload["report"]["cases_with_recovery_guidance"] == 1
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
    ]
    assert [case.scenario_type for case in cases] == ["standard", "followup", "high_risk", "parallel"]
    assert payload["report"]["format"] == "agent_orchestrator.workflow_evidence.v1"
    assert sorted(payload["report"]["scenario_aggregates"]) == ["followup", "standard"]


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
                }
            ]
        ),
        encoding="utf-8",
    )

    cases = load_workflow_evidence_cases(case_file)

    assert cases[0].label == "real-task"
    assert cases[0].scenario_type == "high_risk"
    assert cases[0].mode.value == "speed_first"


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
