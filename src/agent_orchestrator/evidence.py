"""Evidence harness for comparing team workflow outputs against direct runs."""

from __future__ import annotations

# DEPS: __future__, agent_orchestrator, dataclasses, json, pathlib, typing
# RESPONSIBILITY: Capture lightweight evidence showing what planning-governed team workflow adds over direct execution.
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


@dataclass(frozen=True, slots=True)
class WorkflowEvidenceCase:
    requirement: str
    mode: OrchestrationMode = OrchestrationMode.SUCCESS_FIRST
    label: str | None = None
    scenario_type: str | None = None


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

    team_advantages = _team_advantages(team_session, team_summary, approved_plan, provenance)
    direct_limitations = _direct_limitations(direct_payload)
    benefit_score = len(team_advantages) + len(direct_limitations)
    return {
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
            "execution_provenance_keys": sorted(provenance.keys()),
        },
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


def _team_advantages(
    session: Any,
    status_summary: dict[str, object],
    approved_plan: dict[str, object],
    provenance: dict[str, object],
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
    return {
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
    }


def _build_report(cases: list[dict[str, object]]) -> dict[str, object]:
    direct_runs = [case.get("direct_run", {}) for case in cases if isinstance(case, dict)]
    team_runs = [case.get("team_workflow", {}) for case in cases if isinstance(case, dict)]
    comparisons = [case.get("comparison", {}) for case in cases if isinstance(case, dict)]
    return {
        "team_status_counts": _status_counts(team_runs, "status"),
        "direct_final_state_counts": _status_counts(direct_runs, "final_state"),
        "scenario_type_counts": _status_counts(cases, "scenario_type"),
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
