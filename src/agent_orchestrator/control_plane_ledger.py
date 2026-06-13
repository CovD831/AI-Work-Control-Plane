"""Run ledger builder for control-plane recovery artifacts."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, pathlib
# RESPONSIBILITY: Build run ledger summaries from plan sessions, execution runs, and delegated jobs.
# MODULE: decision_core
# ---

from pathlib import Path

from agent_orchestrator.control_plane_artifacts import resolve_root as _resolve_root
from agent_orchestrator.control_plane_constants import CONTROL_PLANE_FORMATS
from agent_orchestrator.jobs import now_iso
from agent_orchestrator.planning_governance import get_governance_status
from agent_orchestrator.planning import PlanSession


def build_run_ledger(
    project_root: Path | str = ".",
    *,
    plans_root: Path | str = ".agent_orchestrator/plans",
    runs_root: Path | str = ".agent_orchestrator/runs",
    jobs_root: Path | str = ".agent_orchestrator/jobs",
    approvals_root: Path | str = ".agent_orchestrator/approvals",
    sessions: list[PlanSession] | None = None,
) -> dict[str, object]:
    from agent_orchestrator.control_plane import (
        WorkspaceIndexStore,
        _read_job_entries,
        _read_plan_sessions,
        _read_run_entries,
        build_approval_queue,
    )

    root = Path(project_root)
    plans_path = _resolve_root(root, plans_root)
    runs_path = _resolve_root(root, runs_root)
    jobs_path = _resolve_root(root, jobs_root)
    approvals_path = _resolve_root(root, approvals_root)
    loaded_sessions = sessions if sessions is not None else _read_plan_sessions(plans_path)
    approvals = build_approval_queue(root, plans_root=plans_path, approvals_root=approvals_path, sessions=loaded_sessions)
    approval_items = approvals.get("items", []) if isinstance(approvals.get("items"), list) else []
    entries: list[dict[str, object]] = []
    for session in loaded_sessions:
        entries.append(_run_ledger_plan_entry(session, approval_items))
    for run in _read_run_entries(runs_path):
        entries.append(_run_ledger_run_entry(run))
    for job in _read_job_entries(jobs_path):
        entries.append(_run_ledger_job_entry(job))
    status_counts: dict[str, int] = {}
    for entry in entries:
        status = str(entry.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    payload = {
        "format": CONTROL_PLANE_FORMATS["run_ledger"],
        "project_root": str(root.resolve()),
        "entries": entries,
        "summary": {
            "entry_count": len(entries),
            "status_counts": status_counts,
            "recovery_ready_count": status_counts.get("recovery_ready", 0),
            "awaiting_human_count": status_counts.get("awaiting_human", 0),
            "failed_count": status_counts.get("failed", 0),
            "provider_fallback_count": status_counts.get("provider_fallback", 0),
            "compliance_blocking_count": status_counts.get("compliance_blocking", 0),
        },
        "evidence_ref": "agent_orchestrator.evidence_bundle.v1",
        "created_at": now_iso(),
    }
    WorkspaceIndexStore(root / ".agent_orchestrator" / "workspace").record_artifact("run_ledger", payload)
    return payload


def _run_ledger_plan_entry(session: PlanSession, approval_items: list[object]) -> dict[str, object]:
    payload = session.to_dict()
    summary = get_governance_status(payload)
    approval_count = sum(
        1
        for item in approval_items
        if isinstance(item, dict) and item.get("session_id") == session.id and item.get("status") == "pending"
    )
    status = _ledger_status_for_session(session, summary, approval_count)
    return {
        "id": f"plan:{session.id}",
        "kind": "plan_session",
        "status": status,
        "session_id": session.id,
        "phase": session.resume.current_phase,
        "primary_action": summary.get("primary_action"),
        "resume_action": summary.get("resume_action"),
        "resume_reason": summary.get("resume_reason"),
        "recovery_actions": list(summary.get("recovery_actions", [])) if isinstance(summary.get("recovery_actions"), list) else [],
        "approval_count": approval_count,
        "provider_fallback": _session_has_provider_fallback(session),
        "evidence_refs": [f"plans/{session.id}/session.json"],
    }


def _run_ledger_run_entry(run: dict[str, object]) -> dict[str, object]:
    accepted = run.get("accepted")
    status = "completed" if accepted is True else "failed" if accepted is False else "interrupted"
    return {
        "id": f"run:{run.get('id')}",
        "kind": "execution_run",
        "status": status,
        "run_id": run.get("id"),
        "final_mode": run.get("final_mode"),
        "accepted": accepted,
        "evidence_refs": [str(run.get("path"))] if run.get("path") else [],
    }


def _run_ledger_job_entry(job: dict[str, object]) -> dict[str, object]:
    raw_status = str(job.get("status") or "unknown")
    status = "failed" if raw_status == "failed" else "completed" if raw_status == "completed" else "interrupted"
    return {
        "id": f"job:{job.get('id')}",
        "kind": "delegated_job",
        "status": status,
        "job_id": job.get("id"),
        "provider": job.get("provider"),
        "runtime_mode": job.get("runtime_mode"),
        "phase": job.get("phase"),
        "summary": job.get("summary"),
        "evidence_refs": [f"jobs/{job.get('id')}.json"],
    }


def _ledger_status_for_session(session: PlanSession, summary: dict[str, object], approval_count: int) -> str:
    if session.status in {"awaiting_human", "awaiting_human_confirmation"}:
        return "awaiting_human"
    compliance = session.compliance if isinstance(session.compliance, dict) else {}
    if compliance.get("blocking"):
        return "compliance_blocking"
    if _session_has_provider_fallback(session):
        return "provider_fallback"
    if session.status in {"accepted", "completed"}:
        return "completed"
    if session.status in {"blocked", "failed"}:
        return "failed"
    recovery_actions = summary.get("recovery_actions", []) if isinstance(summary.get("recovery_actions"), list) else []
    if approval_count or summary.get("resume_action") or recovery_actions:
        return "recovery_ready"
    return "interrupted"


def _session_has_provider_fallback(session: PlanSession) -> bool:
    if not session.decision_verdict:
        return False
    provider_runtime = session.decision_verdict.selected_provider_runtime
    return any("fallback" in str(key) and bool(value) for key, value in provider_runtime.items())
