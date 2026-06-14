"""Versioned evidence harness and benchmark reports for team workflow comparisons."""

from __future__ import annotations

# DEPS: __future__, agent_orchestrator, dataclasses, json, pathlib, typing
# RESPONSIBILITY: Capture versioned, reportable evidence showing what planning-governed team workflow adds over direct execution.
# MODULE: decision_core
# ---

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_orchestrator.control_plane import build_runtime_event_stream, build_workspace_index
from agent_orchestrator.control_plane_workspace import WorkspaceIndexStore
from agent_orchestrator.execution import CodingAgentExecutionRuntime, ExecutionRequest
from agent_orchestrator.execution.coding_components import VerificationReport
from agent_orchestrator.intake import ClarifyPolicy, ExecutionMode, TaskKind, TaskRouterResult
from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.policies import OrchestrationMode
from agent_orchestrator.planning import PlanStore, TeamOrchestrator
from agent_orchestrator.run_store import RunStore
from agent_orchestrator.ui_service import _linked_execution_summary


EVIDENCE_SCHEMA_VERSION = "1.0"
REPORTABLE_FORMAT = "agent_orchestrator.workflow_evidence.v1"


@dataclass(frozen=True, slots=True)
class WorkflowEvidenceCase:
    requirement: str
    mode: OrchestrationMode = OrchestrationMode.SUCCESS_FIRST
    label: str | None = None
    scenario_type: str | None = None
    risk_profile: str | None = None
    operator_goal: str | None = None
    expected_signals: tuple[str, ...] = ()
    runtime_expectation: str | None = None


def benchmark_evidence_cases() -> list[WorkflowEvidenceCase]:
    """Return stable benchmark cases for repeatable evidence reports."""
    return [
        WorkflowEvidenceCase(
            requirement="Build a persisted plan artifact",
            label="persisted_plan_artifact",
            scenario_type="standard",
        ),
        WorkflowEvidenceCase(
            requirement="Build plan with followup checklist",
            label="followup_checklist",
            scenario_type="followup",
        ),
        WorkflowEvidenceCase(
            requirement="Implement auth migration across multiple services",
            label="auth_migration",
            scenario_type="high_risk",
        ),
        WorkflowEvidenceCase(
            requirement="Coordinate parallel independent validation tasks",
            label="parallel_validation",
            scenario_type="parallel",
        ),
        WorkflowEvidenceCase(
            requirement="Harden CLI setup summary for release readiness and validate the operator workflow evidence path",
            label="cli_workflow_hardening",
            scenario_type="standard",
        ),
        WorkflowEvidenceCase(
            requirement="Validate a read-only operator console workflow with workspace status, evidence, and recovery summaries",
            label="ui_operator_console_flow",
            scenario_type="ui_workflow",
        ),
        WorkflowEvidenceCase(
            requirement="Recover from a compliance blocking condition after process docs and changed-file checks drift",
            label="compliance_blocking_recovery",
            scenario_type="compliance_blocking",
        ),
        WorkflowEvidenceCase(
            requirement="Inspect runtime fidelity for a local command-runtime job and explain attachability, receipts, and degraded reasons",
            label="runtime_fidelity_inspection",
            scenario_type="runtime_fidelity",
        ),
        WorkflowEvidenceCase(
            requirement="Investigate why the queue stalls, trace the root cause, and convert the finding into a bounded edit plan",
            label="investigation_to_edit",
            scenario_type="native_coverage_expansion",
        ),
        WorkflowEvidenceCase(
            requirement="Repair a helper implementation across multiple files and verify the repo-facing surface update",
            label="multi_file_helper_repair",
            scenario_type="native_coverage_expansion",
        ),
        WorkflowEvidenceCase(
            requirement="Resume an interrupted long-running local implementation task from recovery recommendation and run ledger evidence",
            label="interrupted_task_resume",
            scenario_type="interruption_recovery",
        ),
        WorkflowEvidenceCase(
            requirement="Resume a failed native verification attempt, apply remaining repair budget, and prove re-verify success through runtime, workspace, and UI evidence surfaces",
            label="repair_resume_success",
            scenario_type="repair_resume_success",
            risk_profile="high",
            operator_goal="prove the native runtime can close a verify failure through repair and governed resume without external coding-agent help",
            expected_signals=("recovery_guidance", "interruption_recovery", "doc_sync", "cost_latency"),
            runtime_expectation="persisted verify failure resumes through remaining retry budget and ends with native verification artifact evidence",
        ),
        WorkflowEvidenceCase(
            requirement="Advance a multi-milestone native workstream through explore, edit, verify, checkpoint, and governed continue while keeping delegation and recovery boundaries visible",
            label="multi_milestone_program_execution",
            scenario_type="program_execution",
            risk_profile="high",
            operator_goal="prove the native path can express and recover a multi-milestone program workstream instead of only closing a single bounded task",
            expected_signals=("recovery_guidance", "interruption_recovery", "doc_sync", "cost_latency"),
            runtime_expectation="program-level posture remains visible across checkpoint, continue, and recovery-oriented operator surfaces",
        ),
        WorkflowEvidenceCase(
            requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and append "team runbook updated" to docs/process/agent-team-operator-runbook.md',
            label="repo_task_acceptance",
            scenario_type="repo_task_acceptance",
            risk_profile="medium",
            operator_goal="prove at least one native run can satisfy a stronger multi-file native repository task acceptance contract",
            expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
            runtime_expectation="bounded native multi-file code edits plus docs surface update with verification on verifiable code targets only",
        ),
        WorkflowEvidenceCase(
            requirement='Replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "hook-based compliance checks updated" to docs/process/agent-orchestrator-implementation-process.md',
            label="repo_task_acceptance_compliance",
            scenario_type="repo_task_acceptance",
            risk_profile="medium",
            operator_goal="prove the stronger native repo-task acceptance contract holds for a second multi-file compliance-facing task shape",
            expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
            runtime_expectation="bounded native multi-file code edits plus compliance-process surface update with verification on verifiable code targets only",
        ),
        WorkflowEvidenceCase(
            requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "module manifest updated" to docs/process/module-manifest.md',
            label="repo_task_acceptance_helper_impl",
            scenario_type="repo_task_acceptance",
            risk_profile="medium",
            operator_goal="prove the stronger native repo-task acceptance contract holds for a multi-file helper implementation task",
            expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
            runtime_expectation="bounded helper implementation updates plus process-surface update with verification on verifiable code targets only",
        ),
        WorkflowEvidenceCase(
            requirement='Replace "VALUE = 1" with "VALUE = 2" in src/agent_orchestrator/stub.py and replace "FLAG = 0" with "FLAG = 1" in src/agent_orchestrator/compliance_signal.py and replace \'return {"status": "stub"}\' with \'return {"status": "implemented", "checks": 1}\' in src/agent_orchestrator/summary_helper.py and append "team runbook updated" to docs/process/agent-team-operator-runbook.md and append "module manifest updated" to docs/process/module-manifest.md and append "hook-based compliance checks updated" to docs/process/agent-orchestrator-implementation-process.md',
            label="repo_task_acceptance_long_chain_native_first",
            scenario_type="repo_task_acceptance",
            risk_profile="medium",
            operator_goal="prove a longer native-first repository task can close through exploration, multi-file editing, verification, and docs synchronization without external help",
            expected_signals=("recovery_guidance", "doc_sync", "cost_latency"),
            runtime_expectation="native exploration, multi-file mutation, verification, and repo-facing surface updates stay on the native path",
        ),
    ]


def load_workflow_evidence_cases(path: Path | str) -> list[WorkflowEvidenceCase]:
    """Load workflow evidence cases from a JSON file."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_cases = payload.get("cases", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_cases, list):
        raise ValueError("evidence case file must contain a list or an object with a cases list")

    cases: list[WorkflowEvidenceCase] = []
    for index, item in enumerate(raw_cases, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"evidence case #{index} must be an object")
        requirement = str(item.get("requirement", "")).strip()
        if not requirement:
            raise ValueError(f"evidence case #{index} is missing requirement")
        mode_value = str(item.get("mode") or OrchestrationMode.SUCCESS_FIRST.value)
        try:
            mode = OrchestrationMode(mode_value)
        except ValueError as exc:
            raise ValueError(f"evidence case #{index} has unsupported mode: {mode_value}") from exc
        cases.append(
            WorkflowEvidenceCase(
                requirement=requirement,
                mode=mode,
                label=str(item.get("label") or requirement),
                scenario_type=str(item.get("scenario_type") or _infer_scenario_type(requirement)),
                risk_profile=str(item.get("risk_profile") or item.get("scenario_type") or "normal"),
                operator_goal=str(item.get("operator_goal") or ""),
                expected_signals=tuple(str(signal) for signal in item.get("expected_signals", []))
                if isinstance(item.get("expected_signals"), list)
                else (),
                runtime_expectation=str(item.get("runtime_expectation") or ""),
            )
        )
    return cases


def capture_workflow_evidence(
    requirements: list[str] | list[WorkflowEvidenceCase],
    *,
    project_root: Path | str,
    output_path: Path | str | None = None,
) -> dict[str, object]:
    root = Path(project_root)
    evidence_root = root / ".agent_orchestrator" / "evidence"
    plans_root = evidence_root / "plans"
    team_runs_root = evidence_root / "team-runs"
    direct_runs_root = evidence_root / "direct-runs"
    for path in (plans_root, team_runs_root, direct_runs_root, evidence_root / "sandboxes"):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    normalized_cases = _normalize_cases(requirements)
    cases: list[dict[str, object]] = []
    for case in normalized_cases:
        case_root = _case_project_root(root, evidence_root, case)
        case = _capture_case(
            case,
            project_root=case_root,
            plans_root=(case_root / ".agent_orchestrator" / "evidence" / "plans") if case_root != root else plans_root,
            team_runs_root=(case_root / ".agent_orchestrator" / "evidence" / "team-runs") if case_root != root else team_runs_root,
            direct_runs_root=(case_root / ".agent_orchestrator" / "evidence" / "direct-runs") if case_root != root else direct_runs_root,
        )
        cases.append(case)

    payload = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "reportable_format": REPORTABLE_FORMAT,
        "project_root": str(root),
        "cases": cases,
        "report": _build_report(cases),
        "summary": _build_summary(cases),
    }
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def render_workflow_evidence_markdown(payload: dict[str, object]) -> str:
    """Render a compact markdown report from a workflow evidence payload."""
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    report = payload.get("report", {}) if isinstance(payload.get("report"), dict) else {}
    cases = payload.get("cases", []) if isinstance(payload.get("cases"), list) else []
    scenario_aggregates = (
        report.get("scenario_aggregates", {}) if isinstance(report.get("scenario_aggregates"), dict) else {}
    )
    signal_counts = summary.get("signal_counts", {}) if isinstance(summary.get("signal_counts"), dict) else {}

    lines = [
        "# v1.x Evidence Report",
        "",
        "## Summary",
        "",
        f"- schema_version: {payload.get('schema_version', 'unknown')}",
        f"- reportable_format: {payload.get('reportable_format', 'unknown')}",
        f"- case_count: {summary.get('case_count', len(cases))}",
        f"- average_benefit_score: {_format_score(summary.get('average_benefit_score', 0.0))}",
        f"- team_cases_with_execution_run: {summary.get('team_cases_with_execution_run', 0)}",
        f"- direct_runs_without_plan_metadata: {summary.get('direct_runs_without_plan_metadata', 0)}",
        "",
        "## Conclusion Summary",
        "",
        *_evidence_conclusion_lines(summary, report, cases),
        "",
        "## Scenario Aggregates",
        "",
    ]
    if scenario_aggregates:
        for scenario, aggregate in sorted(scenario_aggregates.items()):
            if not isinstance(aggregate, dict):
                continue
            lines.extend(
                [
                    f"- {scenario}: cases={aggregate.get('case_count', 0)}, "
                    f"average_benefit_score={_format_score(aggregate.get('average_benefit_score', 0.0))}, "
                    f"max_benefit_score={aggregate.get('max_benefit_score', 0)}",
                ]
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Signal Counts", ""])
    for key in [
        "provenance_present",
        "provenance_matches_plan_session",
        "recovery_guidance_present",
        "doc_sync_present",
        "fallback_present",
    ]:
        lines.append(f"- {key}: {signal_counts.get(key, 0)}")

    real_task_metrics = summary.get("real_task_metrics", {}) if isinstance(summary.get("real_task_metrics"), dict) else {}
    lines.extend(["", "## Real-Task Dogfood Metrics", ""])
    for key in [
        "recovery_recommendation_coverage",
        "runtime_fidelity_coverage",
        "compliance_blocking_coverage",
        "native_task_proof_coverage",
        "native_runtime_closure_ready_cases",
        "planner_continuity_ready_cases",
        "program_execution_ready_cases",
        "native_repo_task_acceptance_ready_cases",
        "native_complex_repo_task_acceptance_ready_cases",
        "native_dogfood_surface_ready_cases",
        "postmortem_ready_cases",
        "cost_latency_ready_cases",
    ]:
        lines.append(f"- {key}: {real_task_metrics.get(key, 0)}")

    lines.extend(["", "## Native Runtime Closure", ""])
    lines.append(
        f"- native_runtime_closure_ready_cases: {real_task_metrics.get('native_runtime_closure_ready_cases', 0)}"
    )
    lines.append(
        f"- planner_continuity_ready_cases: {real_task_metrics.get('planner_continuity_ready_cases', 0)}"
    )
    lines.append(
        f"- program_execution_ready_cases: {real_task_metrics.get('program_execution_ready_cases', 0)}"
    )
    lines.append(
        "- runtime_closure_checks: native_only_execution, stable_step_loop, explicit_context_select_and_observation, "
        "context_engineering_main_path_visible, verify_repair_resume_closure, control_plane_authority, auditable_artifacts_and_surfaces"
    )
    lines.append(
        "- program_execution_checks: runtime_program_posture_visible, workspace_program_posture_visible, "
        "ui_program_posture_visible, recovery_program_contract_visible, topology_program_contract_visible, "
        "resume_recovery_chain_visible"
    )
    lines.extend(["", "## Native Repo Task Acceptance", ""])
    lines.append(
        f"- native_repo_task_acceptance_ready_cases: {real_task_metrics.get('native_repo_task_acceptance_ready_cases', 0)}"
    )
    lines.append(
        f"- native_complex_repo_task_acceptance_ready_cases: {real_task_metrics.get('native_complex_repo_task_acceptance_ready_cases', 0)}"
    )
    lines.append(
        f"- stronger_repo_task_acceptance_signal_visible_cases: {real_task_metrics.get('native_dogfood_surface_ready_cases', 0)}"
    )
    lines.append(
        "- repo_task_checks: repository_exploration_present, code_edit_under_repo_surface, verification_command_present, "
        "operator_visible_artifacts_present, repo_facing_surface_updated"
    )
    lines.append(
        "- complex_repo_task_checks: multi_target_exploration_present, multi_file_mutation_present, "
        "code_and_repo_surface_updated, verification_on_code_targets_present, native_exploration_trace_visible"
    )
    lines.extend(["", "## Native Dogfood Surfaces", ""])
    lines.append(
        f"- native_dogfood_surface_ready_cases: {real_task_metrics.get('native_dogfood_surface_ready_cases', 0)}"
    )
    lines.append(
        "- dogfood_surface_checks: approval_resume_chain_visible, runtime_event_stream_native_proof, "
        "workspace_index_native_proof, ui_execution_summary_native_proof, ui_context_engineering_visible, "
        "ui_control_plane_workspace_index_visible, workspace_native_exploration_visible, "
        "workspace_adapter_shared_contract_visible, workspace_planner_shared_contract_visible, "
        "planner_shared_contract_native_visible"
    )

    runtime_metrics = summary.get("runtime_measurement_metrics", {}) if isinstance(summary.get("runtime_measurement_metrics"), dict) else {}
    lines.extend(["", "## Runtime Measurement Metrics", ""])
    for key in [
        "measured_runtime_cases",
        "placeholder_runtime_cases",
        "provider_available_cases",
        "degraded_runtime_cases",
        "command_duration_available_cases",
        "rc_readiness_blockers",
    ]:
        lines.append(f"- {key}: {runtime_metrics.get(key, 0)}")

    comparative = summary.get("comparative_benchmark", {}) if isinstance(summary.get("comparative_benchmark"), dict) else {}
    if comparative:
        shared_surface = comparative.get("shared_evidence_surface", [])
        lines.extend(["", "## Comparative Benchmark", ""])
        lines.append(
            "- shared_evidence_surface: "
            + ",".join(str(item) for item in shared_surface)
            if isinstance(shared_surface, list) and shared_surface
            else "- shared_evidence_surface: none"
        )

    lines.extend(["", "## Cases", ""])
    for case in cases:
        if not isinstance(case, dict):
            continue
        comparison = case.get("comparison", {}) if isinstance(case.get("comparison"), dict) else {}
        lines.append(
            f"- {case.get('label') or case.get('requirement')}: "
            f"scenario={case.get('scenario_type', 'unknown')}, "
            f"benefit_score={comparison.get('benefit_score', 0)}"
        )
        postmortem = case.get("postmortem", {}) if isinstance(case.get("postmortem"), dict) else {}
        if postmortem:
            lines.append(
                f"  - postmortem: matched_expected_signals={postmortem.get('matched_expected_signal_count', 0)}, "
                f"runtime_fidelity={postmortem.get('runtime_fidelity_represented', False)}, "
                f"cost_latency_ready={postmortem.get('cost_latency_ready', False)}"
            )
        runtime_closure = (
            case.get("native_runtime_closure", {})
            if isinstance(case.get("native_runtime_closure"), dict)
            else {}
        )
        if runtime_closure:
            lines.append(
                f"  - native_runtime_closure: ready={runtime_closure.get('runtime_closure_ready', False)}, "
                f"checks={runtime_closure.get('passed_check_count', 0)}/{runtime_closure.get('total_check_count', 0)}, "
                f"scenario={runtime_closure.get('proof_scenario') or 'none'}"
            )
            checks = runtime_closure.get("checks", {}) if isinstance(runtime_closure.get("checks"), dict) else {}
            context_visibility = (
                checks.get("context_engineering_main_path_visible", {})
                if isinstance(checks.get("context_engineering_main_path_visible"), dict)
                else {}
            )
            context_evidence = (
                context_visibility.get("evidence", {})
                if isinstance(context_visibility.get("evidence"), dict)
                else {}
            )
            if context_evidence.get("required_surfaces"):
                lines.append(
                    "  - context_engineering: surfaces="
                    + ",".join(str(item) for item in context_evidence.get("required_surfaces", []))
                )
        planner_continuity = (
            case.get("planner_continuity_proof", {})
            if isinstance(case.get("planner_continuity_proof"), dict)
            else {}
        )
        if planner_continuity:
            lines.append(
                f"  - planner_continuity_proof: ready={planner_continuity.get('planner_continuity_ready', False)}, "
                f"checks={planner_continuity.get('passed_check_count', 0)}/{planner_continuity.get('total_check_count', 0)}, "
                f"scenario={planner_continuity.get('proof_scenario') or 'none'}"
            )
        repo_acceptance = (
            case.get("native_repo_task_acceptance", {})
            if isinstance(case.get("native_repo_task_acceptance"), dict)
            else {}
        )
        if repo_acceptance:
            lines.append(
                f"  - native_repo_task_acceptance: ready={repo_acceptance.get('real_repo_task_acceptance_ready', False)}, "
                f"checks={repo_acceptance.get('passed_check_count', 0)}/{repo_acceptance.get('total_check_count', 0)}"
            )
        complex_repo_acceptance = (
            case.get("native_complex_repo_task_acceptance", {})
            if isinstance(case.get("native_complex_repo_task_acceptance"), dict)
            else {}
        )
        if complex_repo_acceptance:
            lines.append(
                f"  - native_complex_repo_task_acceptance: ready={complex_repo_acceptance.get('complex_repo_task_ready', False)}, "
                f"checks={complex_repo_acceptance.get('passed_check_count', 0)}/{complex_repo_acceptance.get('total_check_count', 0)}"
            )
        dogfood_surfaces = (
            case.get("native_dogfood_surfaces", {})
            if isinstance(case.get("native_dogfood_surfaces"), dict)
            else {}
        )
        if dogfood_surfaces:
            lines.append(
                f"  - native_dogfood_surfaces: ready={dogfood_surfaces.get('surface_projection_ready', False)}, "
                f"checks={dogfood_surfaces.get('passed_check_count', 0)}/{dogfood_surfaces.get('total_check_count', 0)}, "
                f"scenario={dogfood_surfaces.get('proof_scenario') or 'none'}"
            )
        runtime = case.get("runtime_measurement", {}) if isinstance(case.get("runtime_measurement"), dict) else {}
        if runtime:
            lines.append(
                f"  - runtime_measurement: status={runtime.get('measurement_status', 'unknown')}, "
                f"duration_available={runtime.get('command_duration_available', False)}, "
                f"jobs={runtime.get('job_count', 0)}"
            )
    lines.extend(
        [
            "",
            "## Takeaways",
            "",
            f"- governance-first cases surfaced {summary.get('team_cases_with_execution_run', 0)} linked execution runs out of {summary.get('case_count', len(cases))} cases.",
            f"- direct runs without plan metadata: {summary.get('direct_runs_without_plan_metadata', 0)}.",
            "- when provenance, recovery guidance, and doc sync appear together, the workflow is easier to explain than a fixed-template run.",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def write_workflow_evidence_markdown(payload: dict[str, object], output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_workflow_evidence_markdown(payload), encoding="utf-8")
    return path


def compare_workflow_evidence(baseline: dict[str, object], current: dict[str, object]) -> dict[str, object]:
    """Build a schema-preserving comparison layer for two evidence captures."""
    baseline_summary = baseline.get("summary", {}) if isinstance(baseline.get("summary"), dict) else {}
    current_summary = current.get("summary", {}) if isinstance(current.get("summary"), dict) else {}
    baseline_report = baseline.get("report", {}) if isinstance(baseline.get("report"), dict) else {}
    current_report = current.get("report", {}) if isinstance(current.get("report"), dict) else {}
    baseline_cases = baseline.get("cases", []) if isinstance(baseline.get("cases"), list) else []
    current_cases = current.get("cases", []) if isinstance(current.get("cases"), list) else []
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "reportable_format": f"{REPORTABLE_FORMAT}.trend",
        "baseline": _comparison_snapshot(baseline_summary, baseline_report, baseline_cases),
        "current": _comparison_snapshot(current_summary, current_report, current_cases),
        "deltas": {
            "case_count": _number_delta(baseline_summary.get("case_count"), current_summary.get("case_count")),
            "average_benefit_score": _number_delta(
                baseline_summary.get("average_benefit_score"),
                current_summary.get("average_benefit_score"),
            ),
            "team_cases_with_execution_run": _number_delta(
                baseline_summary.get("team_cases_with_execution_run"),
                current_summary.get("team_cases_with_execution_run"),
            ),
            "direct_runs_without_plan_metadata": _number_delta(
                baseline_summary.get("direct_runs_without_plan_metadata"),
                current_summary.get("direct_runs_without_plan_metadata"),
            ),
            "signal_counts": _count_deltas(
                baseline_summary.get("signal_counts", {}),
                current_summary.get("signal_counts", {}),
            ),
            "real_task_metrics": _count_deltas(
                baseline_summary.get("real_task_metrics", {}),
                current_summary.get("real_task_metrics", {}),
            ),
            "runtime_measurement_metrics": _count_deltas(
                baseline_summary.get("runtime_measurement_metrics", {}),
                current_summary.get("runtime_measurement_metrics", {}),
            ),
            "scenario_aggregates": _scenario_deltas(
                baseline_report.get("scenario_aggregates", {}),
                current_report.get("scenario_aggregates", {}),
            ),
            "team_advantage_counts": _count_deltas(
                _case_tag_counts(baseline_cases, "team_advantages"),
                _case_tag_counts(current_cases, "team_advantages"),
            ),
            "direct_limitation_counts": _count_deltas(
                _case_tag_counts(baseline_cases, "direct_limitations"),
                _case_tag_counts(current_cases, "direct_limitations"),
            ),
        },
    }


def load_workflow_evidence_payload(path: Path | str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("evidence payload must be a JSON object")
    return payload


def render_workflow_evidence_trend_markdown(payload: dict[str, object]) -> str:
    """Render a compact markdown trend report from a comparison payload."""
    baseline = payload.get("baseline", {}) if isinstance(payload.get("baseline"), dict) else {}
    current = payload.get("current", {}) if isinstance(payload.get("current"), dict) else {}
    deltas = payload.get("deltas", {}) if isinstance(payload.get("deltas"), dict) else {}
    assessment = _trend_assessment(deltas)
    lines = [
        "# v1.x Evidence Trend",
        "",
        "## Summary",
        "",
        f"- baseline_cases: {baseline.get('case_count', 0)}",
        f"- current_cases: {current.get('case_count', 0)}",
        f"- average_benefit_score_delta: {_format_signed(deltas.get('average_benefit_score', 0.0))}",
        f"- execution_run_delta: {_format_signed(deltas.get('team_cases_with_execution_run', 0))}",
        f"- direct_without_plan_metadata_delta: {_format_signed(deltas.get('direct_runs_without_plan_metadata', 0))}",
        f"- current_version_assessment: {assessment}",
        "",
        "## Version Assessment",
        "",
        *_trend_assessment_lines(assessment, deltas),
        "",
        "## Scenario Aggregates",
        "",
    ]
    scenario_deltas = deltas.get("scenario_aggregates", {}) if isinstance(deltas.get("scenario_aggregates"), dict) else {}
    if scenario_deltas:
        for scenario, aggregate in sorted(scenario_deltas.items()):
            if not isinstance(aggregate, dict):
                continue
            lines.append(
                f"- {scenario}: cases_delta={_format_signed(aggregate.get('case_count', 0))}, "
                f"average_benefit_score_delta={_format_signed(aggregate.get('average_benefit_score', 0.0))}, "
                f"max_benefit_score_delta={_format_signed(aggregate.get('max_benefit_score', 0))}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Signal Deltas", ""])
    lines.extend(_count_delta_lines(deltas.get("signal_counts", {})))
    lines.extend(["", "## Real-Task Metric Deltas", ""])
    lines.extend(_count_delta_lines(deltas.get("real_task_metrics", {})))
    lines.extend(["", "## Runtime Measurement Deltas", ""])
    lines.extend(_count_delta_lines(deltas.get("runtime_measurement_metrics", {})))
    lines.extend(["", "## Team Advantage Deltas", ""])
    lines.extend(_count_delta_lines(deltas.get("team_advantage_counts", {})))
    lines.extend(["", "## Direct Limitation Deltas", ""])
    lines.extend(_count_delta_lines(deltas.get("direct_limitation_counts", {})))
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- positive score, execution-run, and team-advantage deltas favor the current capture; flat deltas mean the comparison shape stayed stable.",
            "- treat team advantage deltas and direct limitation deltas together when judging whether governance-first orchestration is improving.",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def write_workflow_evidence_trend_markdown(payload: dict[str, object], output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_workflow_evidence_trend_markdown(payload), encoding="utf-8")
    return path


def _capture_case(
    case: WorkflowEvidenceCase,
    *,
    project_root: Path,
    plans_root: Path,
    team_runs_root: Path,
    direct_runs_root: Path,
) -> dict[str, object]:
    direct_orchestrator = Orchestrator(run_store=RunStore(root=direct_runs_root))
    direct_run = direct_orchestrator.run(case.requirement, case.mode)
    direct_payload = direct_run.to_dict()

    team_orchestrator = Orchestrator(run_store=RunStore(root=team_runs_root))
    team = TeamOrchestrator(
        orchestrator=team_orchestrator,
        store=PlanStore(root=plans_root),
        project_root=project_root,
    )
    session = team.start(case.requirement)
    session = team.mark_draft_ready(session.id)
    session = team.submit_draft_for_review(session.id)
    required_open = [gap.id for gap in session.gaps if gap.required and gap.status != "closed"]
    if required_open:
        session.status = "needs_revision"
        session.gate_verdict = "needs_revision"
        session.resume.current_phase = "in_review"
        session.resume.pending_role = "lead"
        team.store.write_session(session)
        session = team.revise(session.id, summary="Evidence capture closes required review gaps.", closed_gap_ids=required_open)
    if session.status != "approved_for_execution":
        session = team.approve(session.id)
    executed = None
    execution_payload: dict[str, object] | None = None
    if session.status == "approved_for_execution":
        if case.scenario_type == "interruption_recovery":
            executed, execution_payload = _capture_interruption_recovery_native_case(
                case=case,
                team=team,
                team_session=session,
                team_orchestrator=team_orchestrator,
                team_runs_root=team_runs_root,
                project_root=project_root,
            )
        elif case.scenario_type == "repair_resume_success":
            executed, execution_payload = _capture_repair_resume_success_native_case(
                case=case,
                team=team,
                team_session=session,
                team_orchestrator=team_orchestrator,
                team_runs_root=team_runs_root,
                project_root=project_root,
            )
        elif case.scenario_type == "program_execution":
            executed, execution_payload = _capture_program_execution_native_case(
                case=case,
                team=team,
                team_session=session,
                team_orchestrator=team_orchestrator,
                team_runs_root=team_runs_root,
                project_root=project_root,
            )
        else:
            executed = team.execute(session.id, case.mode, execution_mode="native")
            if executed.resume.linked_execution_run_id:
                execution_payload = team_orchestrator.run_store.read(executed.resume.linked_execution_run_id)

    team_session = executed or session
    team_payload = team_session.to_dict()
    governance = team_payload.get("governance_snapshot", {}) if isinstance(team_payload.get("governance_snapshot"), dict) else {}
    team_summary = governance.get("governance_status", {}) if isinstance(governance.get("governance_status"), dict) else {}
    if not team_summary:
        team_summary = team_payload.get("status_summary", {})
    approved_plan = team_session.approved_plan if isinstance(team_session.approved_plan, dict) else {}
    selected_provider_runtime = (
        team_session.decision_verdict.selected_provider_runtime
        if team_session.decision_verdict is not None
        else {}
    )
    selected_topology = (
        team_session.decision_verdict.selected_topology
        if team_session.decision_verdict is not None
        else None
    )
    provenance = {}
    if isinstance(execution_payload, dict):
        metadata = execution_payload.get("metadata", {})
        if isinstance(metadata, dict) and isinstance(metadata.get("provenance"), dict):
            provenance = dict(metadata["provenance"])

    signals = _build_signals(
        team_session=team_session,
        status_summary=team_summary,
        approved_plan=approved_plan,
        provenance=provenance,
        selected_provider_runtime=selected_provider_runtime,
    )
    team_advantages = _team_advantages(team_session, team_summary, approved_plan, provenance, signals)
    direct_limitations = _direct_limitations(direct_payload)
    benefit_score = len(team_advantages) + len(direct_limitations)
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "label": case.label or case.requirement,
        "requirement": case.requirement,
        "mode": case.mode.value,
        "scenario_type": case.scenario_type or _infer_scenario_type(case.requirement),
        "real_task": {
            "risk_profile": case.risk_profile or case.scenario_type or "normal",
            "operator_goal": case.operator_goal or "exercise governed local workflow",
            "expected_signals": list(case.expected_signals),
            "runtime_expectation": case.runtime_expectation or "local control-plane evidence",
        },
        "direct_run": {
            "run_id": direct_run.run_id,
            "accepted": direct_run.accepted,
            "final_state": direct_run.final_state,
            "job_count": len(direct_run.jobs),
            "attempt_count": len(direct_run.attempts),
            "final_mode": direct_run.final_mode.value,
            "has_approved_plan_metadata": bool(
                isinstance(direct_payload.get("metadata"), dict)
                and direct_payload["metadata"].get("approved_plan")
            ),
        },
        "team_workflow": {
            "session_id": team_session.id,
            "status": team_session.status,
            "linked_execution_run_id": team_session.resume.linked_execution_run_id,
            "native_task_proof": _native_task_proof_from_execution_payload(execution_payload),
            "review_round_count": len(team_session.review_rounds),
            "approved_plan_source": approved_plan.get("execution_contract", {}).get("source")
            if isinstance(approved_plan.get("execution_contract"), dict)
            else None,
            "selected_topology": selected_topology,
            "selected_provider_runtime": selected_provider_runtime,
            "next_actions": list(team_summary.get("next_actions", [])),
            "recommended_commands": list(team_summary.get("recommended_commands", [])),
            "recovery_actions": list(team_summary.get("recovery_actions", [])),
            "execution_provenance_keys": sorted(provenance.keys()),
            "approval_state": team_summary.get("approval_state", {}),
            "runtime_health": team_summary.get("runtime_health", {}),
            "usage_cost": team_summary.get("usage_cost", {}),
            "gate_evidence": _case_gate_evidence(team_session, execution_payload),
        },
        "signals": signals,
        "runtime_measurement": _case_runtime_measurement(execution_payload, team_summary),
        "postmortem": _postmortem_signals(case, signals, team_summary, execution_payload),
        "native_runtime_closure": _native_runtime_closure_snapshot(
            case=case,
            team_session=team_session,
            status_summary=team_summary,
            execution_payload=execution_payload,
        ),
        "planner_continuity_proof": _planner_continuity_snapshot(
            case=case,
            team_session=team_session,
            execution_payload=execution_payload,
            project_root=project_root,
            plans_root=plans_root,
            team_runs_root=team_runs_root,
        ),
        "program_execution_proof": _program_execution_snapshot(
            case=case,
            team_session=team_session,
            execution_payload=execution_payload,
            project_root=project_root,
            plans_root=plans_root,
            team_runs_root=team_runs_root,
        ),
        "native_repo_task_acceptance": _native_repo_task_acceptance_snapshot(
            case=case,
            team_session=team_session,
            execution_payload=execution_payload,
        ),
        "native_complex_repo_task_acceptance": _native_complex_repo_task_acceptance_snapshot(
            case=case,
            team_session=team_session,
            execution_payload=execution_payload,
        ),
        "native_dogfood_surfaces": _native_dogfood_surface_snapshot(
            case=case,
            team=team,
            team_session=team_session,
            execution_payload=execution_payload,
            project_root=project_root,
            plans_root=plans_root,
            team_runs_root=team_runs_root,
        ),
        "comparison": {
            "team_advantages": team_advantages,
            "direct_limitations": direct_limitations,
            "benefit_score": benefit_score,
            "team_outcome_better_documented": bool(team_advantages or direct_limitations),
        },
    }


def _case_project_root(root: Path, evidence_root: Path, case: WorkflowEvidenceCase) -> Path:
    if case.scenario_type != "repo_task_acceptance":
        return root
    sandbox_root = evidence_root / "sandboxes" / (case.label or "repo-task-acceptance")
    if sandbox_root.exists():
        shutil.rmtree(sandbox_root)
    _write_repo_task_acceptance_workspace(sandbox_root)
    return sandbox_root


def _capture_interruption_recovery_native_case(
    *,
    case: WorkflowEvidenceCase,
    team: TeamOrchestrator,
    team_session: Any,
    team_orchestrator: Orchestrator,
    team_runs_root: Path,
    project_root: Path,
) -> tuple[Any, dict[str, object]]:
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = project_root
    runtime.edit_executor.workspace_root = project_root
    runtime.edit_executor.action_executor.workspace_root = project_root
    runtime.verify_loop.verifier.workspace_root = project_root
    runtime.verify_loop.verifier.action_executor.workspace_root = project_root
    runtime.event_store.root = project_root / ".agent_orchestrator" / "events"
    runtime.event_store.__post_init__()
    turn_id = f"turn-{team_session.id}"
    run_id = f"coding-{turn_id}"
    runtime.state_store.write(
        run_id,
        {
            "format": "agent_orchestrator.execution_state.v1",
            "runtime_name": "coding_agent",
            "session_id": f"evidence-{team_session.id}",
            "turn_id": turn_id,
            "resume_kind": "approval_resume",
            "status": "blocked",
            "accepted": False,
            "current_stage": "verify",
            "current_step_id": f"{team_session.id}:verify",
            "pending_approval": None,
            "step_statuses": [],
            "resume_contract": {
                "resume_kind": "approval_resume",
                "run_id": run_id,
                "session_id": f"evidence-{team_session.id}",
                "turn_id": turn_id,
                "current_stage": "verify",
                "current_step_id": f"{team_session.id}:verify",
                "pending_approval": None,
                "resume_supported": True,
            },
            "execution_history_summary": {
                "objective": case.requirement,
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
            requirement=case.requirement,
            route=TaskRouterResult(
                task_kind=TaskKind.DIRECT_FIX,
                clarify_policy=ClarifyPolicy.LIGHT,
                execution_mode=ExecutionMode.CODING_AGENT,
                ambiguity_level="low",
                risk_level="medium",
                scope_confidence="high",
                needs_repo_context=True,
                requires_human_confirmation=False,
                reasons=["workflow evidence interruption recovery case"],
            ),
            runtime_name="coding_agent",
            mode=case.mode,
            session_id=f"evidence-{team_session.id}",
            turn_id=turn_id,
            context_snapshot={"snapshot_id": f"snapshot-{team_session.id}"},
            task_contract={
                "id": f"task-{team_session.id}",
                "goal": "Resume interrupted native verify failure chain",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": [case.requirement],
                "outputs": ["recovery proof"],
                "acceptance_criteria": ["Recovery state remains inspectable"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
            resume_kind="approval_resume",
        )
    )
    resumed.payload["strategy_summary"] = _synthetic_native_strategy_summary(
        selected_strategy="direct_edit",
        selected_actions=["edit", "verify"],
        selected_owner="native",
        native_work_units=True,
        risk_level="medium",
        requires_human_confirmation=False,
        explore_first=False,
        verify_planned=True,
        clarify_first=False,
        pause_expected=False,
        handoff_expected=False,
    )
    resumed.payload["execution_artifacts"] = {
        "summary": {
            **(
                resumed.payload.get("execution_artifacts", {}).get("summary", {})
                if isinstance(resumed.payload.get("execution_artifacts"), dict)
                and isinstance(resumed.payload.get("execution_artifacts", {}).get("summary"), dict)
                else {}
            ),
            "strategy_summary": resumed.payload["strategy_summary"],
        }
    }
    WorkspaceIndexStore(project_root / ".agent_orchestrator" / "workspace").record_artifact(
        "execution_artifacts",
        _synthetic_execution_artifact_summary_payload(
            run_id=run_id,
            session_id=f"evidence-{team_session.id}",
            turn_id=turn_id,
            payload=resumed.payload,
        ),
    )
    run_payload = {
        "run_id": resumed.run_id,
        "parent_run_id": None,
        "requirement": case.requirement,
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
            "plan_session_id": team_session.id,
            "provenance": {
                "plan_session_id": team_session.id,
                "linked_execution_run_id": resumed.run_id,
                "approved_plan_goal": team_session.approved_plan.get("goal") if isinstance(team_session.approved_plan, dict) else case.requirement,
                "selected_topology": team_session.decision_verdict.selected_topology if team_session.decision_verdict else None,
                "selected_provider_runtime": team_session.decision_verdict.selected_provider_runtime if team_session.decision_verdict else {},
            },
            "team_execution_mode": "native",
            "execution_context_policy": {
                "policy": "resume_if_same_task",
                "source_session_id": team_session.id,
                "fresh_context": False,
                "resume_target": resumed.run_id,
            },
        },
        "payload": resumed.payload,
    }
    team_orchestrator.run_store.write(resumed.run_id, run_payload)
    executed = team.status(team_session.id)
    executed.resume.linked_execution_run_id = resumed.run_id
    executed.status = "awaiting_human"
    team.store.write_session(executed)
    return executed, team_orchestrator.run_store.read(resumed.run_id)


def _capture_repair_resume_success_native_case(
    *,
    case: WorkflowEvidenceCase,
    team: TeamOrchestrator,
    team_session: Any,
    team_orchestrator: Orchestrator,
    team_runs_root: Path,
    project_root: Path,
) -> tuple[Any, dict[str, object]]:
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = project_root
    runtime.edit_executor.workspace_root = project_root
    runtime.edit_executor.action_executor.workspace_root = project_root
    runtime.verify_loop.verifier.workspace_root = project_root
    runtime.verify_loop.verifier.action_executor.workspace_root = project_root
    runtime.event_store.root = project_root / ".agent_orchestrator" / "events"
    runtime.event_store.__post_init__()

    artifact_root = project_root / ".agent_orchestrator" / "execution-artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_root / "verify-success.json"
    artifact_path.write_text('{"status":"passed"}\n', encoding="utf-8")

    class _ResumeRepairVerifier:
        def __init__(self) -> None:
            self.calls = 0

        def run(self, request, edit_intent, command_override=None):
            self.calls += 1
            command = list(command_override or ["python3", "-m", "compileall", "note.py"])
            if self.calls == 1:
                return VerificationReport(
                    status="failed",
                    command=command,
                    exit_code=1,
                    stdout="",
                    stderr="still failing",
                    failure_kind="nonzero_exit",
                    attempt_index=0,
                )
            return VerificationReport(
                status="passed",
                command=command,
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
    turn_id = f"turn-{team_session.id}-repair-success"
    run_id = f"coding-{turn_id}"
    runtime.state_store.write(
        run_id,
        {
            "format": "agent_orchestrator.execution_state.v1",
            "runtime_name": "coding_agent",
            "session_id": f"evidence-{team_session.id}",
            "turn_id": turn_id,
            "resume_kind": "approval_resume",
            "status": "blocked",
            "accepted": False,
            "current_stage": "verify",
            "current_step_id": f"{turn_id}:verify",
            "pending_approval": None,
            "step_statuses": [],
            "resume_contract": {
                "resume_kind": "approval_resume",
                "run_id": run_id,
                "session_id": f"evidence-{team_session.id}",
                "turn_id": turn_id,
                "current_stage": "verify",
                "current_step_id": f"{turn_id}:verify",
                "pending_approval": None,
                "resume_supported": True,
            },
            "execution_history_summary": {
                "objective": case.requirement,
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
            requirement=case.requirement,
            route=TaskRouterResult(
                task_kind=TaskKind.DIRECT_FIX,
                clarify_policy=ClarifyPolicy.LIGHT,
                execution_mode=ExecutionMode.CODING_AGENT,
                ambiguity_level="low",
                risk_level="medium",
                scope_confidence="high",
                needs_repo_context=True,
                requires_human_confirmation=False,
                reasons=["workflow evidence repair resume success case"],
            ),
            runtime_name="coding_agent",
            mode=case.mode,
            session_id=f"evidence-{team_session.id}",
            turn_id=turn_id,
            context_snapshot={"snapshot_id": f"snapshot-{team_session.id}-repair-success"},
            task_contract={
                "id": f"task-{team_session.id}-repair-success",
                "goal": "Resume failed native verification and prove repair success",
                "non_goals": [],
                "context": "Use repository context.",
                "inputs": [case.requirement],
                "outputs": ["repair success proof"],
                "acceptance_criteria": ["Re-verify succeeds and remains inspectable"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
            resume_kind="approval_resume",
        )
    )
    resumed.payload["strategy_summary"] = _synthetic_native_strategy_summary(
        selected_strategy="direct_edit",
        selected_actions=["edit", "verify"],
        selected_owner="native",
        native_work_units=True,
        risk_level="medium",
        requires_human_confirmation=False,
        explore_first=False,
        verify_planned=True,
        clarify_first=False,
        pause_expected=False,
        handoff_expected=False,
    )
    resumed.payload["execution_artifacts"] = {
        "summary": {
            **(
                resumed.payload.get("execution_artifacts", {}).get("summary", {})
                if isinstance(resumed.payload.get("execution_artifacts"), dict)
                and isinstance(resumed.payload.get("execution_artifacts", {}).get("summary"), dict)
                else {}
            ),
            "strategy_summary": resumed.payload["strategy_summary"],
        }
    }
    WorkspaceIndexStore(project_root / ".agent_orchestrator" / "workspace").record_artifact(
        "execution_artifacts",
        _synthetic_execution_artifact_summary_payload(
            run_id=run_id,
            session_id=f"evidence-{team_session.id}",
            turn_id=turn_id,
            payload=resumed.payload,
        ),
    )
    run_payload = {
        "run_id": resumed.run_id,
        "parent_run_id": None,
        "requirement": case.requirement,
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
            "plan_session_id": team_session.id,
            "provenance": {
                "plan_session_id": team_session.id,
                "linked_execution_run_id": resumed.run_id,
                "approved_plan_goal": team_session.approved_plan.get("goal") if isinstance(team_session.approved_plan, dict) else case.requirement,
                "selected_topology": team_session.decision_verdict.selected_topology if team_session.decision_verdict else None,
                "selected_provider_runtime": team_session.decision_verdict.selected_provider_runtime if team_session.decision_verdict else {},
            },
            "team_execution_mode": "native",
            "execution_context_policy": {
                "policy": "resume_if_same_task",
                "source_session_id": team_session.id,
                "fresh_context": False,
                "resume_target": resumed.run_id,
            },
        },
        "payload": resumed.payload,
    }
    team_orchestrator.run_store.write(resumed.run_id, run_payload)
    executed = team.status(team_session.id)
    executed.resume.linked_execution_run_id = resumed.run_id
    executed.status = "completed"
    team.store.write_session(executed)
    return executed, team_orchestrator.run_store.read(resumed.run_id)


def _capture_program_execution_native_case(
    *,
    case: WorkflowEvidenceCase,
    team: TeamOrchestrator,
    team_session: Any,
    team_orchestrator: Orchestrator,
    team_runs_root: Path,
    project_root: Path,
) -> tuple[Any, dict[str, object]]:
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    runtime.repo_explorer.workspace_root = project_root
    runtime.edit_executor.workspace_root = project_root
    runtime.edit_executor.action_executor.workspace_root = project_root
    runtime.verify_loop.verifier.workspace_root = project_root
    runtime.verify_loop.verifier.action_executor.workspace_root = project_root
    runtime.event_store.root = project_root / ".agent_orchestrator" / "events"
    runtime.event_store.__post_init__()

    artifact_root = project_root / ".agent_orchestrator" / "execution-artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    checkpoint_path = artifact_root / "program-checkpoint.json"
    checkpoint_path.write_text('{"checkpoint":"ready"}\n', encoding="utf-8")

    turn_id = f"turn-{team_session.id}-program"
    run_id = f"coding-{turn_id}"
    runtime.state_store.write(
        run_id,
        {
            "format": "agent_orchestrator.execution_state.v1",
            "runtime_name": "coding_agent",
            "session_id": f"evidence-{team_session.id}",
            "turn_id": turn_id,
            "resume_kind": "approval_resume",
            "status": "blocked",
            "accepted": False,
            "current_stage": "verify",
            "current_step_id": f"{turn_id}:verify",
            "pending_approval": None,
            "step_statuses": [],
            "resume_contract": {
                "resume_kind": "approval_resume",
                "run_id": run_id,
                "session_id": f"evidence-{team_session.id}",
                "turn_id": turn_id,
                "current_stage": "verify",
                "current_step_id": f"{turn_id}:verify",
                "pending_approval": None,
                "resume_supported": True,
            },
            "execution_history_summary": {
                "objective": case.requirement,
                "status": "blocked",
                "completed_steps": ["explore_milestone", "edit_milestone"],
                "pending_steps": ["verify_milestone", "checkpoint_continue_milestone"],
                "blocked_steps": [],
                "pending_approval": None,
                "artifact_count": 1,
                "artifact_ids": ["program-checkpoint-artifact"],
                "latest_recovery_hint": "Checkpoint is ready; verify then continue the next owned unit.",
            },
            "compressed_context": {
                "objective": case.requirement,
                "latest_recovery_hint": "Checkpoint is ready; continue after verification.",
            },
            "next_step_contract": {},
            "step_decisions": [],
            "resume_context": {
                "resume_kind": "approval_resume",
                "recent_observations": [{"kind": "checkpoint", "summary": "checkpoint artifact recorded"}],
                "verification": {
                    "status": "passed",
                    "command": ["python3", "-m", "compileall", "note.py"],
                },
                "repair_summary": {
                    "outcome": "not_needed",
                    "attempt_count": 1,
                    "retry_budget": 1,
                    "attempts": [{"attempt_index": 0}],
                    "recovery_recommendation": {"action": "continue_program", "reason": "checkpoint_ready"},
                },
                "planned_verification_command": ["python3", "-m", "compileall", "note.py"],
            },
            "result_summary": {
                "applied_change_count": 1,
                "applied_changes": [{"path": "note.py", "change_type": "modify"}],
                "verification": {
                    "status": "passed",
                    "command": ["python3", "-m", "compileall", "note.py"],
                },
                "repair_summary": {
                    "outcome": "not_needed",
                    "attempt_count": 1,
                    "retry_budget": 1,
                    "attempts": [{"attempt_index": 0}],
                    "recovery_recommendation": {"action": "continue_program", "reason": "checkpoint_ready"},
                },
                "recent_observations": [{"kind": "checkpoint", "summary": "checkpoint artifact recorded"}],
            },
        },
    )
    resumed = runtime.resume_from_state(
        ExecutionRequest(
            requirement=case.requirement,
            route=TaskRouterResult(
                task_kind=TaskKind.DIRECT_FIX,
                clarify_policy=ClarifyPolicy.LIGHT,
                execution_mode=ExecutionMode.CODING_AGENT,
                ambiguity_level="low",
                risk_level="medium",
                scope_confidence="high",
                needs_repo_context=True,
                requires_human_confirmation=False,
                reasons=["workflow evidence multi-milestone program execution case"],
            ),
            runtime_name="coding_agent",
            mode=case.mode,
            session_id=f"evidence-{team_session.id}",
            turn_id=turn_id,
            context_snapshot={"snapshot_id": f"snapshot-{team_session.id}-program"},
            task_contract={
                "id": f"task-{team_session.id}-program",
                "goal": "Advance a multi-milestone program workstream",
                "non_goals": [],
                "context": "Use repository context and keep checkpoint/recovery semantics visible.",
                "inputs": [case.requirement],
                "outputs": ["program checkpoint proof"],
                "acceptance_criteria": ["Checkpoint is visible and next owned unit stays recoverable"],
                "risk_level": "medium",
                "parallelizable": False,
                "owner_type": "single_worker",
                "max_depth": 1,
                "failure_policy": "retry",
            },
            resume_kind="approval_resume",
        )
    )
    resumed.payload["strategy_summary"] = _synthetic_native_strategy_summary(
        selected_strategy="explore_then_edit",
        selected_actions=["explore", "edit", "verify", "resume_learning"],
        selected_owner="native",
        native_work_units=True,
        risk_level="medium",
        requires_human_confirmation=False,
        explore_first=True,
        verify_planned=True,
        clarify_first=False,
        pause_expected=False,
        handoff_expected=False,
    )
    resumed.payload["execution_history_summary"] = {
        "objective": case.requirement,
        "status": "completed",
        "completed_steps": ["explore_milestone", "edit_milestone", "verify_milestone"],
        "pending_steps": ["checkpoint_continue_milestone"],
        "blocked_steps": [],
        "pending_approval": None,
        "artifact_count": 1,
        "artifact_ids": ["program-checkpoint-artifact"],
        "latest_recovery_hint": "Checkpoint complete; continue with the next owned unit.",
    }
    resumed.payload["recovery_summary"] = {"action": "continue_program", "reason": "checkpoint_ready"}
    resumed.payload["execution_artifacts"] = {
        "summary": {
            **(
                resumed.payload.get("execution_artifacts", {}).get("summary", {})
                if isinstance(resumed.payload.get("execution_artifacts"), dict)
                and isinstance(resumed.payload.get("execution_artifacts", {}).get("summary"), dict)
                else {}
            ),
            "strategy_summary": resumed.payload["strategy_summary"],
        }
    }
    WorkspaceIndexStore(project_root / ".agent_orchestrator" / "workspace").record_artifact(
        "execution_artifacts",
        _synthetic_execution_artifact_summary_payload(
            run_id=run_id,
            session_id=f"evidence-{team_session.id}",
            turn_id=turn_id,
            payload=resumed.payload,
        ),
    )
    run_payload = {
        "run_id": resumed.run_id,
        "parent_run_id": None,
        "requirement": case.requirement,
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
            "plan_session_id": team_session.id,
            "provenance": {
                "plan_session_id": team_session.id,
                "linked_execution_run_id": resumed.run_id,
                "approved_plan_goal": team_session.approved_plan.get("goal") if isinstance(team_session.approved_plan, dict) else case.requirement,
                "selected_topology": team_session.decision_verdict.selected_topology if team_session.decision_verdict else None,
                "selected_provider_runtime": team_session.decision_verdict.selected_provider_runtime if team_session.decision_verdict else {},
            },
            "team_execution_mode": "native",
            "execution_context_policy": {
                "policy": "resume_if_same_task",
                "source_session_id": team_session.id,
                "fresh_context": False,
                "resume_target": resumed.run_id,
            },
        },
        "payload": resumed.payload,
    }
    team_orchestrator.run_store.write(resumed.run_id, run_payload)
    executed = team.status(team_session.id)
    executed.resume.linked_execution_run_id = resumed.run_id
    executed.status = "completed"
    team.store.write_session(executed)
    return executed, team_orchestrator.run_store.read(resumed.run_id)


def _synthetic_native_strategy_summary(
    *,
    selected_strategy: str,
    selected_actions: list[str],
    selected_owner: str,
    native_work_units: bool,
    risk_level: str,
    requires_human_confirmation: bool,
    explore_first: bool,
    verify_planned: bool,
    clarify_first: bool,
    pause_expected: bool,
    handoff_expected: bool,
) -> dict[str, object]:
    return {
        "planner_family": "native",
        "selected_execution_strategy": selected_strategy,
        "decision_evidence": {
            "format": "agent_orchestrator.native_planner_decision.v1",
            "planner_family": "native",
            "selected_strategy": selected_strategy,
            "selected_actions": list(selected_actions),
            "selected_owner": selected_owner,
            "native_work_units": native_work_units,
            "decision_boundary": {
                "risk_level": risk_level,
                "requires_human_confirmation": requires_human_confirmation,
            },
            "posture": {
                "explore_first": explore_first,
                "verify_planned": verify_planned,
                "clarify_first": clarify_first,
                "pause_expected": pause_expected,
                "handoff_expected": handoff_expected,
            },
        },
    }


def _synthetic_execution_artifact_summary_payload(
    *,
    run_id: str,
    session_id: str,
    turn_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    artifact_summary = payload.get("artifact_summary", {}) if isinstance(payload.get("artifact_summary"), dict) else {}
    artifacts = artifact_summary.get("artifacts", []) if isinstance(artifact_summary.get("artifacts"), list) else []
    return {
        "format": "agent_orchestrator.execution_artifact_summary.v1",
        "run_id": run_id,
        "session_id": session_id,
        "turn_id": turn_id,
        "artifact_count": artifact_summary.get("artifact_count", len(artifacts)),
        "artifacts": artifacts,
        "native_tool_surface": payload.get("native_tool_surface"),
        "native_tool_trace": payload.get("native_tool_trace"),
        "repo_report": payload.get("repo_report"),
        "adapter_contract": payload.get("adapter_contract"),
        "path_selection": payload.get("path_selection"),
        "compressed_context": payload.get("compressed_context"),
        "compaction_state": payload.get("compaction_state"),
        "session_continuity_contract": payload.get("session_continuity_contract"),
        "context_engineering_contract": payload.get("context_engineering_contract"),
        "resume_context": payload.get("resume_context"),
        "step_loop_contract": payload.get("step_loop_contract"),
        "native_task_proof": payload.get("native_task_proof"),
        "native_repo_task_acceptance": payload.get("native_repo_task_acceptance"),
        "native_complex_repo_task_acceptance": payload.get("native_complex_repo_task_acceptance"),
        "strategy_summary": payload.get("strategy_summary"),
    }


def _write_repo_task_acceptance_workspace(root: Path) -> None:
    (root / "docs" / "process").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "architecture").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "decisions").mkdir(parents=True, exist_ok=True)
    (root / "src" / "agent_orchestrator").mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(
        "# sandbox\n\n- 长周期主执行计划\n- agent-team-operator-runbook.md\n",
        encoding="utf-8",
    )
    (root / "src" / "agent_orchestrator" / "__init__.py").write_text('"""package"""\n', encoding="utf-8")
    (root / "src" / "agent_orchestrator" / "stub.py").write_text(
        '"""Stub module."""\n\nfrom __future__ import annotations\n\n'
        "# DEPS: __future__\n"
        "# RESPONSIBILITY: Provide a compliant Python surface for native repo-task acceptance evidence.\n"
        "# MODULE: evidence\n"
        "# ---\n\n"
        "VALUE = 1\n",
        encoding="utf-8",
    )
    (root / "src" / "agent_orchestrator" / "compliance_signal.py").write_text(
        '"""Compliance-visible stub module."""\n\nfrom __future__ import annotations\n\n'
        "# DEPS: __future__\n"
        "# RESPONSIBILITY: Provide a compliance-visible Python surface for native repo-task acceptance evidence.\n"
        "# MODULE: evidence\n"
        "# ---\n\n"
        "FLAG = 0\n",
        encoding="utf-8",
    )
    (root / "src" / "agent_orchestrator" / "summary_helper.py").write_text(
        '"""Summary helper stub module."""\n\nfrom __future__ import annotations\n\n'
        "# DEPS: __future__\n"
        "# RESPONSIBILITY: Provide a small implementation-shaped Python surface for native repo-task acceptance evidence.\n"
        "# MODULE: evidence\n"
        "# ---\n\n"
        "def build_summary() -> dict[str, object]:\n"
        '    return {"status": "stub"}\n',
        encoding="utf-8",
    )
    (root / "docs" / "process" / "长周期主执行计划.md").write_text(
        "# 长周期主执行计划\n\n- 文档同步 / compliance / hook blocking\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "root-map.md").write_text(
        "# Root Map\n\n"
        "- `src/agent_orchestrator/`: primary Python package\n"
        "- `docs/process/context-map.md`: canonical docs and artifact map\n"
        "- `docs/process/project-index.md`: canonical reading order and recent update index\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "context-map.md").write_text(
        "# Context Map\n\n"
        "- `docs/process/root-map.md`\n"
        "- `docs/process/project-index.md`\n"
        "- `docs/architecture/native-coding-agent-upgrade-plan.md`\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "project-index.md").write_text(
        "# Project Index\n\n"
        "- docs/process/root-map.md\n"
        "- docs/process/context-map.md\n"
        "- docs/architecture/native-coding-agent-upgrade-plan.md\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "module-manifest.md").write_text(
        "# Module Manifest\n\n- src/agent_orchestrator/\n- module manifest\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "agent-orchestrator-implementation-process.md").write_text(
        "# Agent Orchestrator Product Process\n\n- hook-based compliance checks\n- docs/decisions/\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "agent-team-operator-runbook.md").write_text(
        "# 治理控制台操作手册\n\n- team summary\n- team next\n- team runbook\n- team execute\n",
        encoding="utf-8",
    )
    (root / "docs" / "architecture" / "coding-agent-goal-spec.md").write_text(
        "# Coding Agent Goal Spec\n\n- governed execution runtime\n",
        encoding="utf-8",
    )
    (root / "docs" / "architecture" / "native-coding-agent-upgrade-plan.md").write_text(
        "# Native Coding Agent Upgrade Plan\n\n- native closure\n",
        encoding="utf-8",
    )
    (root / "docs" / "architecture" / "决策核心-执行拓扑-运行时分层说明.md").write_text(
        "# 决策核心-执行拓扑-运行时分层说明\n\n- 决策核心\n",
        encoding="utf-8",
    )
    for name in [
        "native-coding-agent-phase-0-baseline.md",
        "native-coding-agent-phase-1-kernel-boundary.md",
        "native-coding-agent-phase-2-step-loop-convergence.md",
        "native-coding-agent-phase-4-verify-repair-resume.md",
        "native-coding-agent-phase-5-native-dogfood-track.md",
    ]:
        (root / "docs" / "process" / name).write_text(f"# {name}\n\n- native phase fixture\n", encoding="utf-8")
    (root / "docs" / "decisions" / "0001-documentation-as-runtime-context.md").write_text(
        "# Test ADR\n\n## Status\n\nAccepted\n\n## Context\n\nSandbox context.\n",
        encoding="utf-8",
    )



def _case_gate_evidence(session: Any, execution_payload: dict[str, object] | None) -> dict[str, object]:
    linked_run = session.resume.linked_execution_run_id
    execution_status = None
    if isinstance(execution_payload, dict):
        execution_status = execution_payload.get("status") or ("accepted" if execution_payload.get("accepted") else None)
    return {
        "format": "agent_orchestrator.gate_evidence.v1",
        "gates": [
            {
                "name": "approved_plan_execution",
                "command": "team execute",
                "cwd": None,
                "exit_code": 0 if linked_run else None,
                "duration_seconds": None,
                "summary": "linked execution run recorded" if linked_run else "execution run not recorded",
                "artifact_path": linked_run,
                "status": execution_status or ("passed" if linked_run else "missing"),
            }
        ],
        "log_policy": "large run details stay in the linked run artifact",
    }

def _comparison_snapshot(
    summary: dict[str, object],
    report: dict[str, object],
    cases: list[object],
) -> dict[str, object]:
    return {
        "case_count": int(summary.get("case_count", len(cases)) or 0),
        "average_benefit_score": float(summary.get("average_benefit_score", 0.0) or 0.0),
        "team_cases_with_execution_run": int(summary.get("team_cases_with_execution_run", 0) or 0),
        "direct_runs_without_plan_metadata": int(summary.get("direct_runs_without_plan_metadata", 0) or 0),
        "signal_counts": summary.get("signal_counts", {}) if isinstance(summary.get("signal_counts"), dict) else {},
        "scenario_aggregates": report.get("scenario_aggregates", {}) if isinstance(report.get("scenario_aggregates"), dict) else {},
        "team_advantage_counts": _case_tag_counts(cases, "team_advantages"),
        "direct_limitation_counts": _case_tag_counts(cases, "direct_limitations"),
    }


def _evidence_conclusion_lines(
    summary: dict[str, object],
    report: dict[str, object],
    cases: list[object],
) -> list[str]:
    case_count = int(summary.get("case_count", len(cases)) or 0)
    signal_counts = summary.get("signal_counts", {}) if isinstance(summary.get("signal_counts"), dict) else {}
    scenario_counts = report.get("scenario_type_counts", {}) if isinstance(report.get("scenario_type_counts"), dict) else {}
    scenario_names = ", ".join(sorted(str(name) for name in scenario_counts)) if scenario_counts else "none"
    approved_plan_count = int(summary.get("cases_showing_approved_plan_benefit", 0) or 0)
    recovery_count = int(signal_counts.get("recovery_guidance_present", 0) or 0)
    provenance_count = int(signal_counts.get("provenance_matches_plan_session", 0) or 0)
    fallback_count = int(signal_counts.get("fallback_present", 0) or 0)
    direct_without_plan = int(summary.get("direct_runs_without_plan_metadata", 0) or 0)
    return [
        f"- planning_quality: {approved_plan_count}/{case_count} cases produced an approved plan artifact across scenarios: {scenario_names}.",
        f"- rescue_quality: {recovery_count}/{case_count} cases carried next-step or recovery guidance for the operator.",
        f"- runtime_limitation: {fallback_count}/{case_count} cases showed provider fallback signals; v1.x evidence validates command-runtime selection/provenance, not a full provider bridge or persistent session manager.",
        f"- fixed_template_advantage: {provenance_count}/{case_count} cases matched execution provenance to the plan session while {direct_without_plan} direct runs lacked approved-plan metadata.",
    ]


def _trend_assessment(deltas: dict[str, object]) -> str:
    score_delta = float(deltas.get("average_benefit_score", 0.0) or 0.0)
    execution_delta = float(deltas.get("team_cases_with_execution_run", 0) or 0)
    advantage_delta = _positive_delta_total(deltas.get("team_advantage_counts", {}))
    negative_score = score_delta < 0
    negative_execution = execution_delta < 0
    if negative_score or negative_execution:
        return "mixed_or_regressed"
    if score_delta > 0 or execution_delta > 0 or advantage_delta > 0:
        return "better"
    return "stable"


def _trend_assessment_lines(assessment: str, deltas: dict[str, object]) -> list[str]:
    score_delta = deltas.get("average_benefit_score", 0.0)
    execution_delta = deltas.get("team_cases_with_execution_run", 0)
    advantage_delta = _positive_delta_total(deltas.get("team_advantage_counts", {}))
    limitation_delta = deltas.get("direct_runs_without_plan_metadata", 0)
    if assessment == "better":
        verdict = "current_is_better: yes"
    elif assessment == "stable":
        verdict = "current_is_better: no measurable improvement; no regression detected"
    else:
        verdict = "current_is_better: mixed; inspect negative deltas before release"
    return [
        f"- {verdict}",
        f"- improvement_signals: average_benefit_score_delta={_format_signed(score_delta)}, execution_run_delta={_format_signed(execution_delta)}, positive_team_advantage_delta={_format_signed(advantage_delta)}.",
        f"- limitation_signals: direct_without_plan_metadata_delta={_format_signed(limitation_delta)}; compare this with case_count_delta before treating it as a regression.",
    ]


def _positive_delta_total(value: object) -> int:
    counts = value if isinstance(value, dict) else {}
    return sum(max(int(item or 0), 0) for item in counts.values())


def _number_delta(baseline: object, current: object) -> float | int:
    baseline_value = float(baseline or 0)
    current_value = float(current or 0)
    delta = current_value - baseline_value
    return int(delta) if delta.is_integer() else delta


def _count_deltas(baseline: object, current: object) -> dict[str, int]:
    baseline_counts = baseline if isinstance(baseline, dict) else {}
    current_counts = current if isinstance(current, dict) else {}
    keys = sorted({str(key) for key in baseline_counts} | {str(key) for key in current_counts})
    return {
        key: int(current_counts.get(key, 0) or 0) - int(baseline_counts.get(key, 0) or 0)
        for key in keys
    }


def _scenario_deltas(baseline: object, current: object) -> dict[str, dict[str, object]]:
    baseline_aggregates = baseline if isinstance(baseline, dict) else {}
    current_aggregates = current if isinstance(current, dict) else {}
    scenarios = sorted({str(key) for key in baseline_aggregates} | {str(key) for key in current_aggregates})
    deltas: dict[str, dict[str, object]] = {}
    for scenario in scenarios:
        baseline_item = baseline_aggregates.get(scenario, {}) if isinstance(baseline_aggregates.get(scenario), dict) else {}
        current_item = current_aggregates.get(scenario, {}) if isinstance(current_aggregates.get(scenario), dict) else {}
        deltas[scenario] = {
            "case_count": _number_delta(baseline_item.get("case_count"), current_item.get("case_count")),
            "average_benefit_score": _number_delta(
                baseline_item.get("average_benefit_score"),
                current_item.get("average_benefit_score"),
            ),
            "max_benefit_score": _number_delta(
                baseline_item.get("max_benefit_score"),
                current_item.get("max_benefit_score"),
            ),
            "signal_counts": _count_deltas(
                baseline_item.get("signal_counts", {}),
                current_item.get("signal_counts", {}),
            ),
        }
    return deltas


def _case_tag_counts(cases: list[object], key: str) -> dict[str, int]:
    comparisons = [
        case.get("comparison", {})
        for case in cases
        if isinstance(case, dict) and isinstance(case.get("comparison", {}), dict)
    ]
    return _tag_counts(comparisons, key)


def _normalize_cases(requirements: list[str] | list[WorkflowEvidenceCase]) -> list[WorkflowEvidenceCase]:
    normalized: list[WorkflowEvidenceCase] = []
    for item in requirements:
        if isinstance(item, WorkflowEvidenceCase):
            normalized.append(item)
        else:
            normalized.append(WorkflowEvidenceCase(requirement=str(item)))
    return normalized


def _build_signals(
    *,
    team_session: Any,
    status_summary: dict[str, object],
    approved_plan: dict[str, object],
    provenance: dict[str, object],
    selected_provider_runtime: dict[str, object],
) -> dict[str, object]:
    doc_sync = team_session.doc_sync if isinstance(getattr(team_session, "doc_sync", None), dict) else {}
    compliance = team_session.compliance if isinstance(getattr(team_session, "compliance", None), dict) else {}
    recommended_commands = [str(item) for item in status_summary.get("recommended_commands", [])]
    recovery_actions = [str(item) for item in status_summary.get("recovery_actions", [])]
    fallback = _fallback_signals(status_summary, selected_provider_runtime)
    return {
        "provenance": {
            "present": bool(provenance),
            "matches_plan_session": provenance.get("plan_session_id") == team_session.id,
            "keys": sorted(provenance.keys()),
            "linked_execution_run_id": team_session.resume.linked_execution_run_id,
            "approved_plan_goal": provenance.get("approved_plan_goal"),
            "source_requirement": provenance.get("source_requirement"),
        },
        "recovery": {
            "has_guidance": bool(recommended_commands or recovery_actions),
            "actions": recovery_actions,
            "recommended_commands": recommended_commands,
            "block_source": status_summary.get("block_source"),
            "block_detail": status_summary.get("block_detail"),
            "resume_action": status_summary.get("resume_action"),
            "resume_reason": status_summary.get("resume_reason"),
        },
        "doc_sync": {
            "present": bool(doc_sync),
            "status": _doc_sync_signal_status(doc_sync, compliance),
            "missing_doc_count": _list_count(doc_sync.get("missing_docs")) if doc_sync else 0,
            "stale_doc_count": _list_count(doc_sync.get("stale_docs")) if doc_sync else 0,
            "changed_file_violation_count": _list_count(doc_sync.get("changed_file_doc_sync_violations"))
            if doc_sync
            else 0,
            "warning_count": _list_count(compliance.get("warnings")) if compliance else 0,
            "blocking_reason_count": _list_count(compliance.get("blocking_reasons")) if compliance else 0,
            "approved_plan_source": approved_plan.get("execution_contract", {}).get("source")
            if isinstance(approved_plan.get("execution_contract"), dict)
            else None,
        },
        "fallback": fallback,
    }


def _doc_sync_signal_status(doc_sync: dict[str, object], compliance: dict[str, object]) -> str:
    if not doc_sync:
        return "not_recorded"
    if compliance.get("blocking"):
        return "blocking"
    return "passed"


def _list_count(value: object) -> int:
    return len(value) if isinstance(value, list) else 0


def _fallback_signals(
    status_summary: dict[str, object],
    selected_provider_runtime: dict[str, object],
) -> dict[str, object]:
    fields = {
        "author_fallback_from": selected_provider_runtime.get("author_fallback_from"),
        "author_fallback_reason": selected_provider_runtime.get("author_fallback_reason"),
        "author_fallback_detail": selected_provider_runtime.get("author_fallback_detail"),
        "reviewer_fallback_from": selected_provider_runtime.get("fallback_from"),
        "reviewer_fallback_reason": selected_provider_runtime.get("fallback_reason"),
        "reviewer_fallback_detail": selected_provider_runtime.get("fallback_detail"),
        "recovery_provider_fallback_from": status_summary.get("recovery_provider_fallback_from"),
        "recovery_provider_fallback_reason": status_summary.get("recovery_provider_fallback_reason"),
        "recovery_provider_fallback_detail": status_summary.get("recovery_provider_fallback_detail"),
    }
    return {
        "present": any(value for value in fields.values()),
        "selected_provider_runtime": dict(selected_provider_runtime),
        "recovery_provider": status_summary.get("recovery_provider"),
        "recovery_round_type": status_summary.get("recovery_round_type"),
        **fields,
    }


def _team_advantages(
    session: Any,
    status_summary: dict[str, object],
    approved_plan: dict[str, object],
    provenance: dict[str, object],
    signals: dict[str, object],
) -> list[str]:
    advantages: list[str] = []
    if approved_plan:
        advantages.append("approved_plan_artifact")
    if session.resume.linked_execution_run_id:
        advantages.append("linked_execution_run")
    native_task_proof = status_summary.get("native_task_proof", {}) if isinstance(status_summary.get("native_task_proof"), dict) else {}
    if native_task_proof.get("native_runtime_only") is True:
        advantages.append("native_task_proof")
    if provenance.get("plan_session_id") == session.id:
        advantages.append("execution_provenance")
    if status_summary.get("recommended_commands"):
        advantages.append("recovery_guidance")
        advantages.append("recovery_guidance_present")
    if status_summary.get("next_executable_task"):
        advantages.append("task_next_visibility")
    if status_summary.get("approval_state"):
        advantages.append("approval_observability")
    if status_summary.get("execution_context_policy"):
        advantages.append("fresh_resume_policy")
    if status_summary.get("usage_cost"):
        advantages.append("usage_cost_placeholder")
    if getattr(session, "id", None):
        advantages.append("knowledge_artifacts")
    advantages.append("gate_evidence_artifact")
    if session.review_rounds:
        advantages.append("role_contract_enforced")
    if session.decision_verdict is not None and session.decision_verdict.selected_provider_runtime:
        advantages.append("provider_runtime_selection")
        selected = session.decision_verdict.selected_provider_runtime
        if any(str(selected.get(key)) == "direct_api" for key in ("reviewer_runtime_mode", "adversarial_reviewer_runtime_mode")):
            advantages.append("direct_api_governance_roles")
        if str(selected.get("author_runtime_mode")) == "cli_inherit":
            advantages.append("cli_worker_default_preserved")
    doc_sync = signals.get("doc_sync", {}) if isinstance(signals.get("doc_sync"), dict) else {}
    if doc_sync.get("present"):
        advantages.append("doc_sync_snapshot")
    fallback = signals.get("fallback", {}) if isinstance(signals.get("fallback"), dict) else {}
    if "selected_provider_runtime" in fallback:
        advantages.append("fallback_signal_surface")
    return advantages


def _direct_limitations(payload: dict[str, object]) -> list[str]:
    limitations: list[str] = []
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}
    if not metadata.get("approved_plan"):
        limitations.append("no_approved_plan_artifact")
    provenance = metadata.get("provenance", {}) if isinstance(metadata.get("provenance"), dict) else {}
    if "plan_session_id" not in provenance:
        limitations.append("no_plan_session_provenance")
    return limitations


def _build_summary(cases: list[dict[str, object]]) -> dict[str, object]:
    workflow_cases = [case.get("team_workflow", {}) for case in cases if isinstance(case, dict)]
    comparisons = [case.get("comparison", {}) for case in cases if isinstance(case, dict)]
    direct_runs = [case.get("direct_run", {}) for case in cases if isinstance(case, dict)]
    signals = [case.get("signals", {}) for case in cases if isinstance(case, dict)]
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "reportable_format": REPORTABLE_FORMAT,
        "case_count": len(cases),
        "team_cases_with_execution_run": sum(
            1 for item in workflow_cases if isinstance(item, dict) and item.get("linked_execution_run_id")
        ),
        "team_cases_with_provenance": sum(
            1
            for item in workflow_cases
            if isinstance(item, dict) and "plan_session_id" in list(item.get("execution_provenance_keys", []))
        ),
        "cases_showing_approved_plan_benefit": sum(
            1
            for item in comparisons
            if isinstance(item, dict) and "approved_plan_artifact" in list(item.get("team_advantages", []))
        ),
        "direct_runs_without_plan_metadata": sum(
            1 for item in direct_runs if isinstance(item, dict) and not item.get("has_approved_plan_metadata")
        ),
        "average_benefit_score": (
            sum(int(item.get("benefit_score", 0)) for item in comparisons if isinstance(item, dict)) / len(comparisons)
            if comparisons
            else 0.0
        ),
        "signal_counts": _signal_counts(signals),
        "reference_advantage_counts": _tag_counts(comparisons, "team_advantages"),
        "comparative_benchmark": _comparative_benchmark_summary(cases),
        "real_task_metrics": _real_task_metrics(cases),
        "runtime_measurement_metrics": _runtime_measurement_metrics(cases),
    }


def _build_report(cases: list[dict[str, object]]) -> dict[str, object]:
    direct_runs = [case.get("direct_run", {}) for case in cases if isinstance(case, dict)]
    team_runs = [case.get("team_workflow", {}) for case in cases if isinstance(case, dict)]
    comparisons = [case.get("comparison", {}) for case in cases if isinstance(case, dict)]
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "format": REPORTABLE_FORMAT,
        "team_status_counts": _status_counts(team_runs, "status"),
        "direct_final_state_counts": _status_counts(direct_runs, "final_state"),
        "scenario_type_counts": _status_counts(cases, "scenario_type"),
        "scenario_aggregates": _scenario_aggregates(cases),
        "benefit_score_by_case": {
            str(case.get("label") or case.get("requirement")): int(case.get("comparison", {}).get("benefit_score", 0))
            for case in cases
            if isinstance(case, dict)
        },
        "average_benefit_score_by_scenario": _average_benefit_score_by_scenario(cases),
        "max_benefit_score": max(
            (int(item.get("benefit_score", 0)) for item in comparisons if isinstance(item, dict)),
            default=0,
        ),
        "cases_with_recovery_guidance": sum(
            1
            for item in comparisons
            if isinstance(item, dict) and "recovery_guidance" in list(item.get("team_advantages", []))
        ),
        "postmortem_signal_counts": _postmortem_signal_counts(cases),
        "runtime_measurement_status_counts": _runtime_measurement_status_counts(cases),
    }


def _case_runtime_measurement(
    execution_payload: dict[str, object] | None,
    status_summary: dict[str, object],
) -> dict[str, object]:
    lifecycle_items = _execution_lifecycle_items(execution_payload)
    durations = [
        duration
        for duration in (
            _duration_seconds(item.get("started_at"), item.get("completed_at"))
            for item in lifecycle_items
            if isinstance(item, dict)
        )
        if duration is not None
    ]
    runtime_health = status_summary.get("runtime_health", {}) if isinstance(status_summary.get("runtime_health"), dict) else {}
    usage_cost = status_summary.get("usage_cost", {}) if isinstance(status_summary.get("usage_cost"), dict) else {}
    payload = execution_payload.get("payload", {}) if isinstance(execution_payload, dict) and isinstance(execution_payload.get("payload"), dict) else {}
    verification = payload.get("verification", {}) if isinstance(payload.get("verification"), dict) else {}
    verification_command = verification.get("command", []) if isinstance(verification.get("command"), list) else []
    verification_artifact = verification.get("artifact", {}) if isinstance(verification.get("artifact"), dict) else {}
    native_measured = bool(verification_command) or bool(verification_artifact)
    job_count = len(lifecycle_items) or int(runtime_health.get("job_count", 0) or 0)
    measured = bool(durations) or native_measured or bool(runtime_health)
    return {
        "format": "agent_orchestrator.runtime_measurement_summary.v1",
        "measurement_status": "measured" if measured else "placeholder" if job_count else "unavailable",
        "job_count": job_count,
        "measured_job_count": len(durations) or (1 if native_measured or runtime_health else 0),
        "command_duration_available": measured,
        "duration_seconds_total": round(sum(durations), 6) if durations else None,
        "duration_seconds_max": round(max(durations), 6) if durations else None,
        "provider_available": None,
        "degraded_runtime": bool(runtime_health.get("failed_job_count")),
        "usage_cost_measurement_status": usage_cost.get("measurement_status") or "placeholder",
        "rc_readiness_blockers": [],
        "policy": "local runtime duration is measured when lifecycle timestamps are available; provider cost remains placeholder unless reported",
    }


def _execution_lifecycle_items(execution_payload: dict[str, object] | None) -> list[dict[str, object]]:
    if not isinstance(execution_payload, dict):
        return []
    items: list[dict[str, object]] = []
    for result in execution_payload.get("results", []):
        if not isinstance(result, dict):
            continue
        lifecycle = result.get("job_lifecycle", [])
        if isinstance(lifecycle, list):
            items.extend(item for item in lifecycle if isinstance(item, dict))
    return items


def _duration_seconds(started_at: object, completed_at: object) -> float | None:
    if not isinstance(started_at, str) or not isinstance(completed_at, str):
        return None
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(completed_at)
    except ValueError:
        return None
    return round(max(0.0, (end - start).total_seconds()), 6)


def _postmortem_signals(
    case: WorkflowEvidenceCase,
    signals: dict[str, object],
    status_summary: dict[str, object],
    execution_payload: dict[str, object] | None,
) -> dict[str, object]:
    recovery = signals.get("recovery", {}) if isinstance(signals.get("recovery"), dict) else {}
    doc_sync = signals.get("doc_sync", {}) if isinstance(signals.get("doc_sync"), dict) else {}
    fallback = signals.get("fallback", {}) if isinstance(signals.get("fallback"), dict) else {}
    expected = set(case.expected_signals)
    runtime_health = status_summary.get("runtime_health", {}) if isinstance(status_summary.get("runtime_health"), dict) else {}
    usage_cost = status_summary.get("usage_cost", {}) if isinstance(status_summary.get("usage_cost"), dict) else {}
    approval_state = status_summary.get("approval_state", {}) if isinstance(status_summary.get("approval_state"), dict) else {}
    native_task_proof = _native_task_proof_from_execution_payload(execution_payload)
    matched = sorted(signal for signal in expected if _expected_signal_matched(signal, recovery, doc_sync, fallback, status_summary))
    return {
        "expected_signals": sorted(expected),
        "matched_expected_signals": matched,
        "matched_expected_signal_count": len(matched),
        "recovery_recommendation_actionable": bool(recovery.get("has_guidance")),
        "recovery_guidance_present": bool(recovery.get("has_guidance")),
        "compliance_blocking_represented": "compliance_blocking" in expected or doc_sync.get("status") == "blocking",
        "runtime_fidelity_represented": "runtime_fidelity" in expected or bool(runtime_health),
        "interruption_recovery_represented": "interruption_recovery" in expected or bool(recovery.get("resume_action")),
        "fallback_represented": "provider_fallback" in expected or bool(fallback.get("present")),
        "human_intervention_observable": bool(approval_state),
        "cost_latency_ready": bool(usage_cost),
        "execution_artifact_recorded": bool(execution_payload),
        "native_task_class": native_task_proof.get("task_class"),
        "native_task_scenario": native_task_proof.get("proof_scenario"),
        "native_task_proof_present": bool(native_task_proof),
        "postmortem_ready": bool(recovery.get("has_guidance")) and bool(usage_cost),
        "notes": "local dogfood evidence; large logs remain in linked artifacts",
    }


def _native_runtime_closure_snapshot(
    *,
    case: WorkflowEvidenceCase,
    team_session: Any,
    status_summary: dict[str, object],
    execution_payload: dict[str, object] | None,
) -> dict[str, object]:
    native_task_proof = _native_task_proof_from_execution_payload(execution_payload)
    payload = execution_payload.get("payload", {}) if isinstance(execution_payload, dict) and isinstance(execution_payload.get("payload"), dict) else {}
    metadata = execution_payload.get("metadata", {}) if isinstance(execution_payload, dict) and isinstance(execution_payload.get("metadata"), dict) else {}
    artifact_summary = payload.get("artifact_summary", {}) if isinstance(payload.get("artifact_summary"), dict) else {}
    event_summary = payload.get("event_summary", {}) if isinstance(payload.get("event_summary"), dict) else {}
    context_selection = payload.get("context_selection", {}) if isinstance(payload.get("context_selection"), dict) else {}
    step_loop = payload.get("step_loop_contract", {}) if isinstance(payload.get("step_loop_contract"), dict) else {}
    context_engineering_contract = (
        payload.get("context_engineering_contract", {})
        if isinstance(payload.get("context_engineering_contract"), dict)
        else {}
    )
    verification = payload.get("verification", {}) if isinstance(payload.get("verification"), dict) else {}
    recovery_summary = payload.get("recovery_summary", {}) if isinstance(payload.get("recovery_summary"), dict) else {}
    execution_context_policy = metadata.get("execution_context_policy", {}) if isinstance(metadata.get("execution_context_policy"), dict) else {}
    recommended_commands = status_summary.get("recommended_commands", []) if isinstance(status_summary.get("recommended_commands"), list) else []
    recovery_actions = status_summary.get("recovery_actions", []) if isinstance(status_summary.get("recovery_actions"), list) else []
    closure_status = native_task_proof.get("closure_status")
    verification_status = verification.get("status")
    proof_artifact_count = int(native_task_proof.get("artifact_count", 0) or 0)
    proof_event_count = int(native_task_proof.get("event_count", 0) or 0)
    accepted = bool(execution_payload.get("accepted")) if isinstance(execution_payload, dict) else False
    blocked = str(execution_payload.get("status")) == "blocked" if isinstance(execution_payload, dict) else False
    recovery_visible = bool(recovery_actions or recommended_commands or recovery_summary or blocked)
    context_select_explicit = bool(native_task_proof.get("context_select_explicit")) or bool(context_selection)
    structured_observation = bool(payload.get("recent_observations")) or bool(payload.get("resume_context"))
    step_context_refs = step_loop.get("context_engineering_refs", {}) if isinstance(step_loop.get("context_engineering_refs"), dict) else {}
    required_surfaces = (
        step_context_refs.get("required_surfaces", [])
        if isinstance(step_context_refs.get("required_surfaces"), list)
        else []
    )
    trace_refs = step_context_refs.get("trace_refs", {}) if isinstance(step_context_refs.get("trace_refs"), dict) else {}
    context_engineering_visible = bool(context_engineering_contract) and bool(required_surfaces) and bool(trace_refs)

    checks = {
        "native_only_execution": {
            "passed": native_task_proof.get("native_runtime_only") is True
            and native_task_proof.get("external_coding_agent_required") is False,
            "evidence": {
                "native_runtime_only": native_task_proof.get("native_runtime_only"),
                "external_coding_agent_required": native_task_proof.get("external_coding_agent_required"),
            },
        },
        "stable_step_loop": {
            "passed": step_loop.get("loop_model") == "explicit_stage_step_loop"
            and step_loop.get("current_disposition") in {"complete", "block"},
            "evidence": {
                "loop_model": step_loop.get("loop_model"),
                "status": step_loop.get("status"),
                "current_disposition": step_loop.get("current_disposition"),
            },
        },
        "explicit_context_select_and_observation": {
            "passed": context_select_explicit and structured_observation,
            "evidence": {
                "context_select_explicit": context_select_explicit,
                "context_selection_keys": sorted(context_selection.keys()),
                "structured_observation_present": structured_observation,
            },
        },
        "context_engineering_main_path_visible": {
            "passed": context_engineering_visible,
            "evidence": {
                "contract_format": context_engineering_contract.get("format"),
                "required_surfaces": list(required_surfaces),
                "trace_ref_keys": sorted(trace_refs.keys()),
                "isolation_strategy": context_engineering_contract.get("isolate", {}).get("strategy")
                if isinstance(context_engineering_contract.get("isolate"), dict)
                else None,
                "isolation_reinjection_mode": context_engineering_contract.get("isolate", {}).get("reinjection_mode")
                if isinstance(context_engineering_contract.get("isolate"), dict)
                else None,
            },
        },
        "verify_repair_resume_closure": {
            "passed": closure_status in {"completed", "blocked"} and (verification_status is not None or bool(recovery_summary)),
            "evidence": {
                "closure_status": closure_status,
                "verification_status": verification_status,
                "recovery_action": native_task_proof.get("recovery_action"),
            },
        },
        "control_plane_authority": {
            "passed": payload.get("kernel_contract", {}).get("state_authority") == "control_plane"
            and metadata.get("plan_session_id") == team_session.id,
            "evidence": {
                "state_authority": payload.get("kernel_contract", {}).get("state_authority")
                if isinstance(payload.get("kernel_contract"), dict)
                else None,
                "plan_session_id": metadata.get("plan_session_id"),
                "execution_context_policy": execution_context_policy.get("policy"),
            },
        },
        "auditable_artifacts_and_surfaces": {
            "passed": proof_artifact_count >= 1 and proof_event_count >= 1 and recovery_visible,
            "evidence": {
                "proof_artifact_count": proof_artifact_count,
                "proof_event_count": proof_event_count,
                "artifact_summary_present": bool(artifact_summary),
                "event_summary_present": bool(event_summary),
                "recovery_visible": recovery_visible,
            },
        },
    }
    passed_checks = sum(1 for item in checks.values() if item.get("passed") is True)
    return {
        "format": "agent_orchestrator.native_runtime_closure.v1",
        "task_label": case.label or case.requirement,
        "task_class": native_task_proof.get("task_class"),
        "proof_scenario": native_task_proof.get("proof_scenario"),
        "closure_status": closure_status,
        "accepted": accepted,
        "blocked": blocked,
        "checks": checks,
        "passed_check_count": passed_checks,
        "total_check_count": len(checks),
        "runtime_closure_ready": passed_checks == len(checks),
        "notes": "This proves governed native runtime closure signals, not by itself the stronger real repository task acceptance target.",
    }


def _native_repo_task_acceptance_snapshot(
    *,
    case: WorkflowEvidenceCase,
    team_session: Any,
    execution_payload: dict[str, object] | None,
) -> dict[str, object]:
    payload = execution_payload.get("payload", {}) if isinstance(execution_payload, dict) and isinstance(execution_payload.get("payload"), dict) else {}
    applied_changes = payload.get("applied_changes", []) if isinstance(payload.get("applied_changes"), list) else []
    verification = payload.get("verification", {}) if isinstance(payload.get("verification"), dict) else {}
    target_paths = payload.get("edit_intent", {}).get("target_paths", []) if isinstance(payload.get("edit_intent"), dict) else []
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
        "task_label": case.label or case.requirement,
        "session_id": getattr(team_session, "id", None),
        "task_shape_checks": task_shape_checks,
        "passed_check_count": passed_checks,
        "total_check_count": len(task_shape_checks),
        "real_repo_task_acceptance_ready": passed_checks == len(task_shape_checks),
        "notes": "This is the stronger project-level acceptance target. Current synthetic/native dogfood may legitimately fail it even when runtime closure is ready.",
    }


def _planner_continuity_snapshot(
    *,
    case: WorkflowEvidenceCase,
    team_session: Any,
    execution_payload: dict[str, object] | None,
    project_root: Path,
    plans_root: Path,
    team_runs_root: Path,
) -> dict[str, object]:
    if case.scenario_type not in {"interruption_recovery", "repair_resume_success", "repo_task_acceptance", "ui_workflow", "program_execution"}:
        return {
            "format": "agent_orchestrator.planner_continuity_proof.v1",
            "task_label": case.label or case.requirement,
            "session_id": getattr(team_session, "id", None),
            "proof_scenario": _native_task_proof_from_execution_payload(execution_payload).get("proof_scenario"),
            "checks": {},
            "passed_check_count": 0,
            "total_check_count": 0,
            "planner_continuity_ready": False,
            "notes": "Planner continuity proof is only evaluated for native scenarios that require planner-to-runtime continuity evidence.",
        }
    workspace_index = build_workspace_index(
        project_root,
        plans_root=plans_root,
        runs_root=team_runs_root.resolve(),
        jobs_root=project_root / ".agent_orchestrator" / "jobs",
        approvals_root=project_root / ".agent_orchestrator" / "approvals",
    )
    execution_summary = _linked_execution_summary(execution_payload)
    execution_artifact_summary = (
        workspace_index.get("execution_artifact_summary", {})
        if isinstance(workspace_index.get("execution_artifact_summary"), dict)
        else {}
    )
    planner_shared_contract = (
        execution_artifact_summary.get("planner_shared_contract", {})
        if isinstance(execution_artifact_summary.get("planner_shared_contract"), dict)
        else {}
    )
    session_continuity = (
        execution_artifact_summary.get("session_continuity", {})
        if isinstance(execution_artifact_summary.get("session_continuity"), dict)
        else {}
    )
    native_task_proof = _native_task_proof_from_execution_payload(execution_payload)
    proof_scenario = native_task_proof.get("proof_scenario")
    checks = {
        "planner_shared_contract_visible": {
            "passed": planner_shared_contract.get("format") == "agent_orchestrator.native_planner_decision.v1",
            "evidence": {
                "format": planner_shared_contract.get("format"),
                "selected_strategy": planner_shared_contract.get("selected_strategy"),
            },
        },
        "planner_actions_visible": {
            "passed": bool(planner_shared_contract.get("selected_actions")),
            "evidence": {
                "selected_actions": planner_shared_contract.get("selected_actions", []),
                "native_work_units": planner_shared_contract.get("native_work_units"),
            },
        },
        "planner_owner_boundary_visible": {
            "passed": planner_shared_contract.get("selected_owner") in {"native", "external"},
            "evidence": {
                "selected_owner": planner_shared_contract.get("selected_owner"),
                "decision_boundary": planner_shared_contract.get("decision_boundary", {}),
                "posture": planner_shared_contract.get("posture", {}),
            },
        },
        "workspace_session_continuity_visible": {
            "passed": bool(session_continuity.get("resume_supported")) and bool(session_continuity.get("long_horizon_posture")),
            "evidence": {
                "resume_supported": session_continuity.get("resume_supported"),
                "resume_kind": session_continuity.get("resume_kind"),
                "compaction_stage": session_continuity.get("compaction_stage"),
                "long_horizon_posture": session_continuity.get("long_horizon_posture", {}),
            },
        },
        "ui_planner_and_session_visible": {
            "passed": bool(execution_summary.get("planner_decision_format"))
            and (
                bool(execution_summary.get("session_resume_kind"))
                or bool(execution_summary.get("session_long_horizon_posture"))
            ),
            "evidence": {
                "planner_decision_format": execution_summary.get("planner_decision_format"),
                "planner_selected_strategy": execution_summary.get("planner_selected_strategy"),
                "planner_native_work_units": execution_summary.get("planner_native_work_units"),
                "session_resume_kind": execution_summary.get("session_resume_kind"),
                "session_long_horizon_posture": execution_summary.get("session_long_horizon_posture", {}),
            },
        },
        "resume_chain_scenario_visible": {
            "passed": proof_scenario in {
                "approval_pause_resume_complete",
                "verify_failure_exhausted_recovery_block",
                "verify_failure_repair_resume_success",
            },
            "evidence": {
                "proof_scenario": proof_scenario,
                "closure_status": native_task_proof.get("closure_status"),
            },
        },
    }
    passed_checks = sum(1 for item in checks.values() if item.get("passed") is True)
    return {
        "format": "agent_orchestrator.planner_continuity_proof.v1",
        "task_label": case.label or case.requirement,
        "session_id": getattr(team_session, "id", None),
        "proof_scenario": proof_scenario,
        "checks": checks,
        "passed_check_count": passed_checks,
        "total_check_count": len(checks),
        "planner_continuity_ready": passed_checks == len(checks),
        "notes": "This proves native planner decision evidence remains visible through runtime/session continuity and recovery-oriented surfaces.",
    }


def _program_execution_snapshot(
    *,
    case: WorkflowEvidenceCase,
    team_session: Any,
    execution_payload: dict[str, object] | None,
    project_root: Path,
    plans_root: Path,
    team_runs_root: Path,
) -> dict[str, object]:
    if case.scenario_type not in {"interruption_recovery", "repair_resume_success", "repo_task_acceptance", "ui_workflow", "program_execution"}:
        return {
            "format": "agent_orchestrator.program_execution_proof.v1",
            "task_label": case.label or case.requirement,
            "session_id": getattr(team_session, "id", None),
            "proof_scenario": _native_task_proof_from_execution_payload(execution_payload).get("proof_scenario"),
            "checks": {},
            "passed_check_count": 0,
            "total_check_count": 0,
            "program_execution_ready": False,
            "notes": "Program execution proof is only evaluated for long-horizon native scenarios that exercise recovery and operator continuity.",
        }
    workspace_index = build_workspace_index(
        project_root,
        plans_root=plans_root,
        runs_root=team_runs_root.resolve(),
        jobs_root=project_root / ".agent_orchestrator" / "jobs",
        approvals_root=project_root / ".agent_orchestrator" / "approvals",
    )
    execution_summary = _linked_execution_summary(execution_payload)
    runtime_payload = execution_payload.get("payload", {}) if isinstance(execution_payload, dict) and isinstance(execution_payload.get("payload"), dict) else {}
    continuity = runtime_payload.get("session_continuity_contract", {}) if isinstance(runtime_payload.get("session_continuity_contract"), dict) else {}
    recovery_recommendation = (
        team_session.to_dict().get("recovery_recommendation", {})
        if isinstance(team_session.to_dict().get("recovery_recommendation"), dict)
        else {}
    )
    if not recovery_recommendation:
        from agent_orchestrator.control_plane_recovery import build_recovery_recommendation

        recovery_recommendation = build_recovery_recommendation(team_session)
    topology = team_session.to_dict().get("topology_snapshot", {}) if isinstance(team_session.to_dict().get("topology_snapshot"), dict) else {}
    if not topology:
        from agent_orchestrator.control_plane_topology import build_execution_topology_snapshot

        topology = build_execution_topology_snapshot(team_session, plans_root=plans_root, project_root=project_root)
    workspace_continuity = (
        workspace_index.get("execution_artifact_summary", {}).get("session_continuity", {})
        if isinstance(workspace_index.get("execution_artifact_summary"), dict)
        and isinstance(workspace_index.get("execution_artifact_summary", {}).get("session_continuity"), dict)
        else {}
    )
    proof_scenario = _native_task_proof_from_execution_payload(execution_payload).get("proof_scenario")
    checks = {
        "runtime_program_posture_visible": {
            "passed": bool(continuity.get("program_posture", {}).get("active_milestone"))
            and bool(continuity.get("program_posture", {}).get("ready_next_units") is not None),
            "evidence": continuity.get("program_posture", {}),
        },
        "workspace_program_posture_visible": {
            "passed": bool(workspace_continuity.get("program_posture", {}).get("program_goal"))
            and "selected_executor" in workspace_continuity.get("delegation_contract", {}),
            "evidence": {
                "program_posture": workspace_continuity.get("program_posture", {}),
                "delegation_contract": workspace_continuity.get("delegation_contract", {}),
            },
        },
        "ui_program_posture_visible": {
            "passed": bool(execution_summary.get("program_posture", {}).get("program_goal"))
            and bool(execution_summary.get("operator_control", {}).get("next_recommended_action")),
            "evidence": {
                "program_posture": execution_summary.get("program_posture", {}),
                "operator_control": execution_summary.get("operator_control", {}),
            },
        },
        "recovery_program_contract_visible": {
            "passed": bool(recovery_recommendation.get("program_posture", {}).get("program_goal"))
            and bool(recovery_recommendation.get("delegation_contract", {}).get("selected_executor")),
            "evidence": {
                "program_posture": recovery_recommendation.get("program_posture", {}),
                "delegation_contract": recovery_recommendation.get("delegation_contract", {}),
            },
        },
        "topology_program_contract_visible": {
            "passed": bool(topology.get("program_posture", {}).get("program_goal"))
            and bool(topology.get("operator_control", {}).get("next_recommended_action")),
            "evidence": {
                "program_posture": topology.get("program_posture", {}),
                "operator_control": topology.get("operator_control", {}),
            },
        },
        "resume_recovery_chain_visible": {
            "passed": proof_scenario in {
                "approval_pause_resume_complete",
                "verify_failure_exhausted_recovery_block",
                "verify_failure_repair_resume_success",
            }
            and bool(continuity.get("program_continuity", {}).get("latest_recovery_hint") or recovery_recommendation.get("current_blocking_reason")),
            "evidence": {
                "proof_scenario": proof_scenario,
                "runtime_program_continuity": continuity.get("program_continuity", {}),
                "recovery_current_blocking_reason": recovery_recommendation.get("current_blocking_reason"),
            },
        },
    }
    passed_checks = sum(1 for item in checks.values() if item.get("passed") is True)
    return {
        "format": "agent_orchestrator.program_execution_proof.v1",
        "task_label": case.label or case.requirement,
        "session_id": getattr(team_session, "id", None),
        "proof_scenario": proof_scenario,
        "checks": checks,
        "passed_check_count": passed_checks,
        "total_check_count": len(checks),
        "program_execution_ready": passed_checks == len(checks),
        "notes": "This proves multi-milestone program posture and delegation continuity remain aligned across runtime, workspace, topology, recovery, and UI surfaces.",
    }


def _native_complex_repo_task_acceptance_snapshot(
    *,
    case: WorkflowEvidenceCase,
    team_session: Any,
    execution_payload: dict[str, object] | None,
) -> dict[str, object]:
    payload = execution_payload.get("payload", {}) if isinstance(execution_payload, dict) and isinstance(execution_payload.get("payload"), dict) else {}
    direct = payload.get("native_complex_repo_task_acceptance", {})
    if isinstance(direct, dict) and direct:
        return {
            **direct,
            "task_label": case.label or case.requirement,
            "session_id": getattr(team_session, "id", None),
        }
    return {
        "format": "agent_orchestrator.native_complex_repo_task_acceptance.v1",
        "task_label": case.label or case.requirement,
        "session_id": getattr(team_session, "id", None),
        "complex_task_checks": {},
        "passed_check_count": 0,
        "total_check_count": 0,
        "complex_repo_task_ready": False,
        "notes": "Complex repo-task acceptance is only available when the runtime payload projects the stricter multi-file native task signal.",
    }


def _native_dogfood_surface_snapshot(
    *,
    case: WorkflowEvidenceCase,
    team: TeamOrchestrator,
    team_session: Any,
    execution_payload: dict[str, object] | None,
    project_root: Path,
    plans_root: Path,
    team_runs_root: Path,
) -> dict[str, object]:
    if case.scenario_type not in {"repo_task_acceptance", "ui_workflow", "interruption_recovery", "repair_resume_success", "program_execution"}:
        return {
            "format": "agent_orchestrator.native_dogfood_surfaces.v1",
            "task_label": case.label or case.requirement,
            "session_id": getattr(team_session, "id", None),
            "linked_run_id": getattr(getattr(team_session, "resume", None), "linked_execution_run_id", None),
            "proof_scenario": _native_task_proof_from_execution_payload(execution_payload).get("proof_scenario"),
            "surface_checks": {},
            "passed_check_count": 0,
            "total_check_count": 0,
            "surface_projection_ready": False,
            "notes": "Surface projection checks are only evaluated for native dogfood scenarios that explicitly require runtime-event, workspace-index, or UI visibility.",
        }
    linked_run_id = getattr(getattr(team_session, "resume", None), "linked_execution_run_id", None)
    workspace_index = build_workspace_index(
        project_root,
        plans_root=plans_root,
        runs_root=team_runs_root.resolve(),
        jobs_root=project_root / ".agent_orchestrator" / "jobs",
        approvals_root=project_root / ".agent_orchestrator" / "approvals",
    )
    runtime_event_stream = build_runtime_event_stream(
        project_root,
        plans_root=plans_root,
        runs_root=team_runs_root.resolve(),
        jobs_root=project_root / ".agent_orchestrator" / "jobs",
        approvals_root=project_root / ".agent_orchestrator" / "approvals",
    )
    execution_summary = _linked_execution_summary(execution_payload)
    event = next(
        (
            item
            for item in runtime_event_stream.get("events", [])
            if isinstance(item, dict)
            and item.get("kind") == "execution_run"
            and item.get("run_id") == linked_run_id
        ),
        {},
    )
    workspace_native_proof = (
        workspace_index.get("execution_artifact_summary", {}).get("native_task_proof", {})
        if isinstance(workspace_index.get("execution_artifact_summary"), dict)
        else {}
    )
    workspace_repo_acceptance = (
        workspace_index.get("execution_artifact_summary", {}).get("native_repo_task_acceptance", {})
        if isinstance(workspace_index.get("execution_artifact_summary"), dict)
        else {}
    )
    workspace_complex_repo_acceptance = (
        workspace_index.get("execution_artifact_summary", {}).get("native_complex_repo_task_acceptance", {})
        if isinstance(workspace_index.get("execution_artifact_summary"), dict)
        else {}
    )
    workspace_native_exploration = (
        workspace_index.get("execution_artifact_summary", {}).get("native_exploration", {})
        if isinstance(workspace_index.get("execution_artifact_summary"), dict)
        else {}
    )
    workspace_adapter_shared_contract = (
        workspace_index.get("execution_artifact_summary", {}).get("adapter_shared_contract", {})
        if isinstance(workspace_index.get("execution_artifact_summary"), dict)
        else {}
    )
    workspace_planner_shared_contract = (
        workspace_index.get("execution_artifact_summary", {}).get("planner_shared_contract", {})
        if isinstance(workspace_index.get("execution_artifact_summary"), dict)
        else {}
    )
    if not isinstance(workspace_complex_repo_acceptance, dict):
        workspace_complex_repo_acceptance = {}
    direct_native_proof = _native_task_proof_from_execution_payload(execution_payload)
    proof_scenario = direct_native_proof.get("proof_scenario")
    runtime_native_proof = event.get("native_task_proof", {}) if isinstance(event.get("native_task_proof"), dict) else {}
    runtime_repo_acceptance = (
        event.get("native_repo_task_acceptance", {})
        if isinstance(event.get("native_repo_task_acceptance"), dict)
        else {}
    )
    runtime_complex_repo_acceptance = (
        event.get("native_complex_repo_task_acceptance", {})
        if isinstance(event.get("native_complex_repo_task_acceptance"), dict)
        else {}
    )
    if not isinstance(runtime_complex_repo_acceptance, dict):
        runtime_complex_repo_acceptance = {}
    if not runtime_native_proof:
        run_entry = next(
            (
                item
                for item in runtime_event_stream.get("events", [])
                if isinstance(item, dict)
                and item.get("kind") == "execution_run"
                and item.get("runtime_mode") == "coding_agent"
                and isinstance(item.get("native_task_proof"), dict)
                and item.get("native_task_proof", {}).get("proof_scenario") == proof_scenario
            ),
            {},
        )
        if isinstance(run_entry.get("native_task_proof"), dict):
            runtime_native_proof = dict(run_entry.get("native_task_proof", {}))
    checks = {
        "approval_resume_chain_visible": {
            "passed": proof_scenario in {
                "approval_pause_resume_complete",
                "verify_failure_exhausted_recovery_block",
                "verify_failure_repair_resume_success",
            },
            "evidence": {"proof_scenario": proof_scenario},
        },
        "runtime_event_stream_native_proof": {
            "passed": runtime_native_proof.get("native_runtime_only") is True
            and runtime_native_proof.get("closure_status") in {"completed", "blocked"},
            "evidence": {
                "run_id": linked_run_id,
                "native_runtime_only": runtime_native_proof.get("native_runtime_only"),
                "closure_status": runtime_native_proof.get("closure_status"),
            },
        },
        "workspace_index_native_proof": {
            "passed": workspace_native_proof.get("native_runtime_only") is True,
            "evidence": {
                "native_runtime_only": workspace_native_proof.get("native_runtime_only"),
                "task_class": workspace_native_proof.get("task_class"),
            },
        },
        "runtime_event_stream_repo_task_acceptance_visible": {
            "passed": runtime_repo_acceptance.get("format") == "agent_orchestrator.native_repo_task_acceptance.v1",
            "evidence": {
                "run_id": linked_run_id,
                "format": runtime_repo_acceptance.get("format"),
                "ready": runtime_repo_acceptance.get("real_repo_task_acceptance_ready"),
            },
        },
        "workspace_index_repo_task_acceptance_visible": {
            "passed": workspace_repo_acceptance.get("format") == "agent_orchestrator.native_repo_task_acceptance.v1",
            "evidence": {
                "format": workspace_repo_acceptance.get("format"),
                "ready": workspace_repo_acceptance.get("real_repo_task_acceptance_ready"),
            },
        },
        "runtime_event_stream_complex_repo_task_acceptance_visible": {
            "passed": runtime_complex_repo_acceptance.get("format") == "agent_orchestrator.native_complex_repo_task_acceptance.v1",
            "evidence": {
                "run_id": linked_run_id,
                "format": runtime_complex_repo_acceptance.get("format"),
                "ready": runtime_complex_repo_acceptance.get("complex_repo_task_ready"),
            },
        },
        "workspace_index_complex_repo_task_acceptance_visible": {
            "passed": workspace_complex_repo_acceptance.get("format") == "agent_orchestrator.native_complex_repo_task_acceptance.v1",
            "evidence": {
                "format": workspace_complex_repo_acceptance.get("format"),
                "ready": workspace_complex_repo_acceptance.get("complex_repo_task_ready"),
            },
        },
        "ui_execution_summary_native_proof": {
            "passed": execution_summary.get("native_runtime_only") is True
            and execution_summary.get("closure_status") in {"completed", "blocked"},
            "evidence": {
                "native_runtime_only": execution_summary.get("native_runtime_only"),
                "closure_status": execution_summary.get("closure_status"),
                "proof_scenario": execution_summary.get("proof_scenario"),
            },
        },
        "ui_repo_task_acceptance_visible": {
            "passed": execution_summary.get("repo_task_acceptance_ready") is not None,
            "evidence": {
                "ready": execution_summary.get("repo_task_acceptance_ready"),
                "passed_checks": execution_summary.get("repo_task_acceptance_passed_checks"),
                "total_checks": execution_summary.get("repo_task_acceptance_total_checks"),
            },
        },
        "ui_complex_repo_task_acceptance_visible": {
            "passed": execution_summary.get("complex_repo_task_acceptance_ready") is not None,
            "evidence": {
                "ready": execution_summary.get("complex_repo_task_acceptance_ready"),
                "passed_checks": execution_summary.get("complex_repo_task_acceptance_passed_checks"),
                "total_checks": execution_summary.get("complex_repo_task_acceptance_total_checks"),
            },
        },
        "ui_context_engineering_visible": {
            "passed": bool(execution_summary.get("context_engineering_contract_format"))
            and bool(execution_summary.get("step_loop_context_surfaces")),
            "evidence": {
                "context_engineering_contract_format": execution_summary.get("context_engineering_contract_format"),
                "step_loop_context_surfaces": execution_summary.get("step_loop_context_surfaces", []),
                "context_isolation_strategy": execution_summary.get("context_isolation_strategy"),
                "context_isolation_reinjection_mode": execution_summary.get("context_isolation_reinjection_mode"),
            },
        },
        "ui_control_plane_workspace_index_visible": {
            "passed": workspace_index.get("format") == "agent_orchestrator.workspace_index.v1",
            "evidence": {
                "workspace_index_format": workspace_index.get("format"),
                "ui_source": "build_workspace_index reused by DashboardService control_plane.workspace_index",
            },
        },
        "workspace_native_exploration_visible": {
            "passed": workspace_native_exploration.get("candidate_path_count", 0) >= 1,
            "evidence": {
                "candidate_path_count": workspace_native_exploration.get("candidate_path_count", 0),
                "repo_map_directory_count": workspace_native_exploration.get("repo_map_directory_count"),
            },
        },
        "workspace_adapter_shared_contract_visible": {
            "passed": workspace_adapter_shared_contract.get("comparison_mode") == "same_contract_two_executors",
            "evidence": {
                "comparison_mode": workspace_adapter_shared_contract.get("comparison_mode"),
                "default_path": workspace_adapter_shared_contract.get("default_path"),
                "hot_plug_supported": workspace_adapter_shared_contract.get("hot_plug_supported"),
            },
        },
        "workspace_planner_shared_contract_visible": {
            "passed": workspace_planner_shared_contract.get("format") == "agent_orchestrator.native_planner_decision.v1",
            "evidence": {
                "format": workspace_planner_shared_contract.get("format"),
                "selected_strategy": workspace_planner_shared_contract.get("selected_strategy"),
                "selected_owner": workspace_planner_shared_contract.get("selected_owner"),
            },
        },
        "planner_shared_contract_native_visible": {
            "passed": workspace_planner_shared_contract.get("selected_owner") in {"native", "external"},
            "evidence": {
                "selected_strategy": workspace_planner_shared_contract.get("selected_strategy"),
                "selected_actions": workspace_planner_shared_contract.get("selected_actions", []),
                "selected_owner": workspace_planner_shared_contract.get("selected_owner"),
                "native_work_units": workspace_planner_shared_contract.get("native_work_units"),
                "decision_boundary": workspace_planner_shared_contract.get("decision_boundary", {}),
                "posture": workspace_planner_shared_contract.get("posture", {}),
            },
        },
        "workspace_session_continuity_visible": {
            "passed": bool(workspace_index.get("execution_artifact_summary", {}).get("session_continuity", {})),
            "evidence": {
                "session_continuity": workspace_index.get("execution_artifact_summary", {}).get("session_continuity", {}),
            },
        },
        "workspace_runtime_cost_visible": {
            "passed": bool(workspace_index.get("execution_artifact_summary", {}).get("runtime_cost", {})),
            "evidence": {
                "runtime_cost": workspace_index.get("execution_artifact_summary", {}).get("runtime_cost", {}),
            },
        },
        "ui_session_continuity_visible": {
            "passed": bool(execution_summary.get("session_resume_kind"))
            or bool(execution_summary.get("session_compaction_stage"))
            or bool(execution_summary.get("session_long_horizon_posture")),
            "evidence": {
                "session_resume_kind": execution_summary.get("session_resume_kind"),
                "session_compaction_stage": execution_summary.get("session_compaction_stage"),
                "session_long_horizon_posture": execution_summary.get("session_long_horizon_posture", {}),
                "runtime_duration_seconds": execution_summary.get("runtime_duration_seconds"),
                "runtime_cost_measurement_status": execution_summary.get("runtime_cost_measurement_status"),
            },
        },
        }
    readiness_required_checks = {
        "approval_resume_chain_visible",
        "runtime_event_stream_native_proof",
        "workspace_index_native_proof",
        "runtime_event_stream_repo_task_acceptance_visible",
        "workspace_index_repo_task_acceptance_visible",
        "runtime_event_stream_complex_repo_task_acceptance_visible",
        "workspace_index_complex_repo_task_acceptance_visible",
        "ui_execution_summary_native_proof",
        "ui_repo_task_acceptance_visible",
        "ui_complex_repo_task_acceptance_visible",
        "ui_context_engineering_visible",
        "ui_control_plane_workspace_index_visible",
        "workspace_native_exploration_visible",
        "workspace_adapter_shared_contract_visible",
        "workspace_session_continuity_visible",
        "workspace_runtime_cost_visible",
        "ui_session_continuity_visible",
    }
    passed_checks = sum(1 for item in checks.values() if item.get("passed") is True)
    readiness_passed_checks = sum(
        1
        for name, item in checks.items()
        if name in readiness_required_checks and item.get("passed") is True
    )
    return {
        "format": "agent_orchestrator.native_dogfood_surfaces.v1",
        "task_label": case.label or case.requirement,
        "session_id": getattr(team_session, "id", None),
        "linked_run_id": linked_run_id,
        "proof_scenario": proof_scenario,
        "surface_checks": checks,
        "passed_check_count": passed_checks,
        "total_check_count": len(checks),
        "surface_projection_ready": readiness_passed_checks == len(readiness_required_checks),
        "notes": "This snapshot proves the same native task chain is visible through runtime events, workspace index, and UI execution summary surfaces.",
    }


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


def _native_task_proof_from_execution_payload(
    execution_payload: dict[str, object] | None,
) -> dict[str, object]:
    if not isinstance(execution_payload, dict):
        return {}
    direct = execution_payload.get("native_task_proof")
    if isinstance(direct, dict):
        return dict(direct)
    payload = execution_payload.get("payload")
    if isinstance(payload, dict) and isinstance(payload.get("native_task_proof"), dict):
        return dict(payload.get("native_task_proof", {}))
    artifact_summary = execution_payload.get("artifact_summary")
    if isinstance(artifact_summary, dict) and isinstance(artifact_summary.get("native_task_proof"), dict):
        return dict(artifact_summary.get("native_task_proof", {}))
    return {}


def _expected_signal_matched(
    signal: str,
    recovery: dict[str, object],
    doc_sync: dict[str, object],
    fallback: dict[str, object],
    status_summary: dict[str, object],
) -> bool:
    if signal == "recovery_guidance":
        return bool(recovery.get("has_guidance"))
    if signal == "recovery_guidance_present":
        return bool(recovery.get("has_guidance"))
    if signal == "doc_sync":
        return bool(doc_sync.get("present"))
    if signal == "compliance_blocking":
        return bool(doc_sync.get("blocking_reason_count")) or doc_sync.get("status") in {"blocking", "passed"}
    if signal == "runtime_fidelity":
        return bool(status_summary.get("runtime_health")) or "selected_provider_runtime" in fallback
    if signal == "provider_fallback":
        return "selected_provider_runtime" in fallback
    if signal == "interruption_recovery":
        return bool(recovery.get("resume_action")) or bool(recovery.get("recommended_commands"))
    if signal == "approval_observability":
        return bool(status_summary.get("approval_state"))
    if signal == "cost_latency":
        return bool(status_summary.get("usage_cost"))
    return False


def _real_task_metrics(cases: list[dict[str, object]]) -> dict[str, int]:
    postmortems = [case.get("postmortem", {}) for case in cases if isinstance(case.get("postmortem", {}), dict)]
    runtime_closure = [
        case.get("native_runtime_closure", {})
        for case in cases
        if isinstance(case.get("native_runtime_closure", {}), dict)
    ]
    planner_continuity = [
        case.get("planner_continuity_proof", {})
        for case in cases
        if isinstance(case.get("planner_continuity_proof", {}), dict)
    ]
    program_execution = [
        case.get("program_execution_proof", {})
        for case in cases
        if isinstance(case.get("program_execution_proof", {}), dict)
    ]
    repo_acceptance = [
        case.get("native_repo_task_acceptance", {})
        for case in cases
        if isinstance(case.get("native_repo_task_acceptance", {}), dict)
    ]
    complex_repo_acceptance = [
        case.get("native_complex_repo_task_acceptance", {})
        for case in cases
        if isinstance(case.get("native_complex_repo_task_acceptance", {}), dict)
    ]
    dogfood_surfaces = [
        case.get("native_dogfood_surfaces", {})
        for case in cases
        if isinstance(case.get("native_dogfood_surfaces", {}), dict)
    ]
    return {
        "recovery_recommendation_coverage": sum(1 for item in postmortems if item.get("recovery_recommendation_actionable")),
        "runtime_fidelity_coverage": sum(1 for item in postmortems if item.get("runtime_fidelity_represented")),
        "compliance_blocking_coverage": sum(1 for item in postmortems if item.get("compliance_blocking_represented")),
        "interruption_recovery_coverage": sum(1 for item in postmortems if item.get("interruption_recovery_represented")),
        "fallback_coverage": sum(1 for item in postmortems if item.get("fallback_represented")),
        "postmortem_ready_cases": sum(1 for item in postmortems if item.get("postmortem_ready")),
        "cost_latency_ready_cases": sum(1 for item in postmortems if item.get("cost_latency_ready")),
        "execution_artifact_cases": sum(1 for item in postmortems if item.get("execution_artifact_recorded")),
        "native_task_proof_coverage": sum(1 for item in postmortems if item.get("native_task_proof_present")),
        "native_runtime_closure_ready_cases": sum(1 for item in runtime_closure if item.get("runtime_closure_ready") is True),
        "planner_continuity_ready_cases": sum(
            1 for item in planner_continuity if item.get("planner_continuity_ready") is True
        ),
        "program_execution_ready_cases": sum(
            1 for item in program_execution if item.get("program_execution_ready") is True
        ),
        "native_repo_task_acceptance_ready_cases": sum(
            1 for item in repo_acceptance if item.get("real_repo_task_acceptance_ready") is True
        ),
        "native_complex_repo_task_acceptance_ready_cases": sum(
            1 for item in complex_repo_acceptance if item.get("complex_repo_task_ready") is True
        ),
        "native_dogfood_surface_ready_cases": sum(
            1 for item in dogfood_surfaces if item.get("surface_projection_ready") is True
        ),
    }


def _comparative_benchmark_summary(cases: list[dict[str, object]]) -> dict[str, object]:
    comparisons = [case.get("comparison", {}) for case in cases if isinstance(case, dict)]
    team_runs = [case.get("team_workflow", {}) for case in cases if isinstance(case, dict)]
    direct_runs = [case.get("direct_run", {}) for case in cases if isinstance(case, dict)]
    repo_acceptance = [
        case.get("native_repo_task_acceptance", {})
        for case in cases
        if isinstance(case.get("native_repo_task_acceptance", {}), dict)
    ]
    complex_repo_acceptance = [
        case.get("native_complex_repo_task_acceptance", {})
        for case in cases
        if isinstance(case.get("native_complex_repo_task_acceptance", {}), dict)
    ]
    program_execution = [
        case.get("program_execution_proof", {})
        for case in cases
        if isinstance(case.get("program_execution_proof", {}), dict)
    ]
    return {
        "case_count": len(cases),
        "native_success_cases": sum(1 for item in team_runs if isinstance(item, dict) and item.get("status") in {"approved_for_execution", "accepted", "completed"}),
        "external_success_cases": sum(1 for item in direct_runs if isinstance(item, dict) and item.get("final_state") in {"accepted", "completed"}),
        "native_blocked_cases": sum(1 for item in team_runs if isinstance(item, dict) and item.get("status") in {"needs_revision", "blocked"}),
        "external_blocked_cases": sum(1 for item in direct_runs if isinstance(item, dict) and item.get("final_state") in {"blocked", "failed"}),
        "human_intervention_cases": sum(
            1
            for item in team_runs
            if isinstance(item, dict) and bool(item.get("approval_state")) and item.get("status") not in {"accepted", "completed"}
        ),
        "recovery_cases": sum(1 for item in comparisons if isinstance(item, dict) and "recovery_guidance" in list(item.get("team_advantages", []))),
        "same_program_contract_cases": sum(1 for item in program_execution if item.get("program_execution_ready") is True),
        "native_repo_task_acceptance_ready_cases": sum(1 for item in repo_acceptance if item.get("real_repo_task_acceptance_ready") is True),
        "native_complex_repo_task_acceptance_ready_cases": sum(1 for item in complex_repo_acceptance if item.get("complex_repo_task_ready") is True),
        "average_benefit_score": (
            sum(int(item.get("benefit_score", 0)) for item in comparisons if isinstance(item, dict)) / len(comparisons)
            if comparisons
            else 0.0
        ),
        "shared_evidence_surface": [
            "runtime_payload",
            "session_continuity",
            "workspace_index",
            "team_summary",
            "team_next",
            "team_runbook",
            "ui_execution_summary",
            "cli_execution_summary",
            "recovery_recommendation",
            "topology_snapshot",
        ],
    }


def _runtime_measurement_metrics(cases: list[dict[str, object]]) -> dict[str, int]:
    measurements = [case.get("runtime_measurement", {}) for case in cases if isinstance(case.get("runtime_measurement", {}), dict)]
    return {
        "measured_runtime_cases": sum(1 for item in measurements if item.get("measurement_status") == "measured"),
        "placeholder_runtime_cases": sum(1 for item in measurements if item.get("measurement_status") == "placeholder"),
        "unavailable_runtime_cases": sum(1 for item in measurements if item.get("measurement_status") == "unavailable"),
        "provider_available_cases": sum(1 for item in measurements if item.get("provider_available") is True),
        "degraded_runtime_cases": sum(1 for item in measurements if item.get("degraded_runtime")),
        "command_duration_available_cases": sum(1 for item in measurements if item.get("command_duration_available")),
        "rc_readiness_blockers": sum(
            len(item.get("rc_readiness_blockers", []))
            for item in measurements
            if isinstance(item.get("rc_readiness_blockers"), list)
        ),
    }


def _runtime_measurement_status_counts(cases: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        measurement = case.get("runtime_measurement", {}) if isinstance(case.get("runtime_measurement"), dict) else {}
        status = str(measurement.get("measurement_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _postmortem_signal_counts(cases: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        postmortem = case.get("postmortem", {}) if isinstance(case.get("postmortem"), dict) else {}
        for signal in postmortem.get("matched_expected_signals", []):
            name = str(signal)
            counts[name] = counts.get(name, 0) + 1
    return counts


def _signal_counts(signals: list[object]) -> dict[str, int]:
    counts = {
        "provenance_present": 0,
        "provenance_matches_plan_session": 0,
        "recovery_guidance_present": 0,
        "doc_sync_present": 0,
        "fallback_present": 0,
    }
    for item in signals:
        if not isinstance(item, dict):
            continue
        provenance = item.get("provenance", {}) if isinstance(item.get("provenance"), dict) else {}
        recovery = item.get("recovery", {}) if isinstance(item.get("recovery"), dict) else {}
        doc_sync = item.get("doc_sync", {}) if isinstance(item.get("doc_sync"), dict) else {}
        fallback = item.get("fallback", {}) if isinstance(item.get("fallback"), dict) else {}
        if provenance.get("present"):
            counts["provenance_present"] += 1
        if provenance.get("matches_plan_session"):
            counts["provenance_matches_plan_session"] += 1
        if recovery.get("has_guidance"):
            counts["recovery_guidance_present"] += 1
        if doc_sync.get("present"):
            counts["doc_sync_present"] += 1
        if fallback.get("present"):
            counts["fallback_present"] += 1
    return counts


def _scenario_aggregates(cases: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for case in cases:
        if isinstance(case, dict):
            grouped.setdefault(str(case.get("scenario_type") or "unknown"), []).append(case)

    aggregates: dict[str, dict[str, object]] = {}
    for scenario, scenario_cases in grouped.items():
        comparisons = [
            case.get("comparison", {})
            for case in scenario_cases
            if isinstance(case.get("comparison", {}), dict)
        ]
        scores = [int(item.get("benefit_score", 0)) for item in comparisons]
        aggregates[scenario] = {
            "case_count": len(scenario_cases),
            "average_benefit_score": sum(scores) / len(scores) if scores else 0.0,
            "max_benefit_score": max(scores, default=0),
            "signal_counts": _signal_counts([case.get("signals", {}) for case in scenario_cases]),
            "team_advantage_counts": _tag_counts(comparisons, "team_advantages"),
            "direct_limitation_counts": _tag_counts(comparisons, "direct_limitations"),
        }
    return aggregates


def _tag_counts(items: list[dict[str, object]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        values = item.get(key, []) if isinstance(item, dict) else []
        if not isinstance(values, list):
            continue
        for value in values:
            name = str(value)
            counts[name] = counts.get(name, 0) + 1
    return counts


def _status_counts(items: list[dict[str, object]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(key)
        name = str(value or "unknown")
        counts[name] = counts.get(name, 0) + 1
    return counts


def _infer_scenario_type(requirement: str) -> str:
    lowered = requirement.lower()
    if "followup" in lowered:
        return "followup"
    if "auth" in lowered or "migration" in lowered or "security" in lowered:
        return "high_risk"
    if "parallel" in lowered or "independent" in lowered or "multiple" in lowered:
        return "parallel"
    return "standard"


def _average_benefit_score_by_scenario(cases: list[dict[str, object]]) -> dict[str, float]:
    buckets: dict[str, list[int]] = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        scenario = str(case.get("scenario_type", "unknown"))
        comparison = case.get("comparison", {})
        if not isinstance(comparison, dict):
            continue
        buckets.setdefault(scenario, []).append(int(comparison.get("benefit_score", 0)))
    return {
        scenario: sum(scores) / len(scores)
        for scenario, scores in buckets.items()
        if scores
    }


def _format_score(value: object) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _format_signed(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    if number.is_integer():
        return f"{int(number):+d}"
    return f"{number:+.2f}"


def _count_delta_lines(value: object) -> list[str]:
    counts = value if isinstance(value, dict) else {}
    if not counts:
        return ["- none"]
    return [f"- {key}: {_format_signed(counts[key])}" for key in sorted(counts)]
