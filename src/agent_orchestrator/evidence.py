"""Versioned evidence harness and benchmark reports for team workflow comparisons."""

from __future__ import annotations

# DEPS: __future__, agent_orchestrator, dataclasses, json, pathlib, typing
# RESPONSIBILITY: Capture versioned, reportable evidence showing what planning-governed team workflow adds over direct execution.
# MODULE: decision_core
# ---

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.policies import OrchestrationMode
from agent_orchestrator.planning import PlanStore, TeamOrchestrator
from agent_orchestrator.run_store import RunStore


EVIDENCE_SCHEMA_VERSION = "1.0"
REPORTABLE_FORMAT = "agent_orchestrator.workflow_evidence.v1"


@dataclass(frozen=True, slots=True)
class WorkflowEvidenceCase:
    requirement: str
    mode: OrchestrationMode = OrchestrationMode.SUCCESS_FIRST
    label: str | None = None
    scenario_type: str | None = None


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
    ]


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

    normalized_cases = _normalize_cases(requirements)
    cases: list[dict[str, object]] = []
    for case in normalized_cases:
        case = _capture_case(
            case,
            project_root=root,
            plans_root=plans_root,
            team_runs_root=team_runs_root,
            direct_runs_root=direct_runs_root,
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
    executed = None
    execution_payload: dict[str, object] | None = None
    if session.status == "approved_for_execution":
        executed = team.execute(session.id, case.mode)
        if executed.resume.linked_execution_run_id:
            execution_payload = team_orchestrator.run_store.read(executed.resume.linked_execution_run_id)

    team_session = executed or session
    team_summary = team_session.to_dict()["status_summary"]
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
        },
        "signals": signals,
        "comparison": {
            "team_advantages": team_advantages,
            "direct_limitations": direct_limitations,
            "benefit_score": benefit_score,
            "team_outcome_better_documented": bool(team_advantages or direct_limitations),
        },
    }


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
    if provenance.get("plan_session_id") == session.id:
        advantages.append("execution_provenance")
    if status_summary.get("recommended_commands"):
        advantages.append("recovery_guidance")
    if session.decision_verdict is not None and session.decision_verdict.selected_provider_runtime:
        advantages.append("provider_runtime_selection")
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
    }


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
