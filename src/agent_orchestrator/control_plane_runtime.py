"""Runtime event stream and provider session snapshots for the control plane."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, json, pathlib
# RESPONSIBILITY: Build read-only runtime event streams and provider session liveness snapshots.
# MODULE: decision_core
# ---

import json
from pathlib import Path

from agent_orchestrator.control_plane_artifacts import resolve_root as _resolve_root
from agent_orchestrator.control_plane_artifacts import stable_id as _stable_id
from agent_orchestrator.control_plane_constants import CONTROL_PLANE_FORMATS
from agent_orchestrator.jobs import now_iso, runtime_measurement_payload
from agent_orchestrator.planning import PlanSession


def build_runtime_event_stream(
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
        _read_job_payloads,
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
    events: list[dict[str, object]] = []
    for session in loaded_sessions:
        events.extend(_runtime_events_for_session(session))
    for run in _read_run_entries(runs_path):
        events.append(_runtime_event_for_run(run))
    session_snapshots = [_provider_session_snapshot_from_job(job) for job in _read_job_payloads(jobs_path)]
    for snapshot in session_snapshots:
        events.append(_runtime_event_for_session_snapshot(snapshot))
    approvals = build_approval_queue(root, plans_root=plans_path, approvals_root=approvals_path, sessions=loaded_sessions)
    pending_approvals = [
        item
        for item in approvals.get("items", [])
        if isinstance(item, dict) and item.get("status") == "pending"
    ]
    if pending_approvals:
        events.append(
            {
                "id": _stable_id("runtime-event", "approval", str(len(pending_approvals))),
                "kind": "approval_gate",
                "runtime_mode": "control_plane",
                "intent": "record human approval requirement",
                "tool_intent": "team approvals list",
                "result_status": "awaiting_human",
                "artifact_refs": ["agent_orchestrator.approval_queue.v1"],
                "usage_cost": _usage_cost_placeholder(),
                "records_only": True,
                "created_at": now_iso(),
            }
        )
    status_counts: dict[str, int] = {}
    for event in events:
        status = str(event.get("result_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    payload = {
        "format": CONTROL_PLANE_FORMATS["runtime_event_stream"],
        "project_root": str(root.resolve()),
        "events": events,
        "summary": {
            "event_count": len(events),
            "status_counts": status_counts,
            "failed_count": status_counts.get("failed", 0),
            "degraded_count": status_counts.get("provider_degraded", 0),
            "fallback_count": status_counts.get("provider_fallback", 0),
            "live_session_count": sum(
                1
                for snapshot in session_snapshots
                if isinstance(snapshot.get("liveness"), dict)
                and snapshot["liveness"].get("state") == "running"
            ),
            "missing_session_count": sum(
                1
                for snapshot in session_snapshots
                if isinstance(snapshot.get("liveness"), dict)
                and snapshot["liveness"].get("state") == "missing"
            ),
        },
        "provider_session_snapshots": session_snapshots,
        "operation_receipts": [
            receipt
            for snapshot in session_snapshots
            for receipt in snapshot.get("operation_receipts", [])
            if isinstance(receipt, dict)
        ],
        "mutation_policy": "records runtime intent/result/fallback only; execution remains gated by approved plans",
        "usage_cost": _usage_cost_placeholder(),
        "read_only": True,
        "created_at": now_iso(),
    }
    WorkspaceIndexStore(root / ".agent_orchestrator" / "workspace").record_artifact("runtime_event_stream", payload)
    return payload


def build_provider_session_snapshot(
    job_id: str,
    project_root: Path | str = ".",
    *,
    jobs_root: Path | str = ".agent_orchestrator/jobs",
) -> dict[str, object]:
    from agent_orchestrator.control_plane import WorkspaceIndexStore

    root = Path(project_root)
    jobs_path = _resolve_root(root, jobs_root)
    job_path = jobs_path / f"{job_id}.json"
    if not job_path.exists():
        payload = {
            "format": CONTROL_PLANE_FORMATS["provider_session_snapshot"],
            "job_id": job_id,
            "status": "missing",
            "liveness": {
                "state": "missing",
                "detail": f"Job {job_id} is not available.",
                "checked_at": now_iso(),
            },
            "operation_support": {
                "send": "session_missing",
                "cancel": "session_missing",
                "attach": "unavailable",
                "continue": "unavailable",
            },
            "recommended_recovery_command": "python -m agent_orchestrator.cli team workspace-status",
            "read_only": True,
            "created_at": now_iso(),
        }
        WorkspaceIndexStore(root / ".agent_orchestrator" / "workspace").record_artifact("provider_session_snapshot", payload)
        return payload
    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
    except Exception:
        job = {"id": job_id, "status": "failed", "error": "job payload could not be parsed"}
    payload = _provider_session_snapshot_from_job(job if isinstance(job, dict) else {"id": job_id})
    WorkspaceIndexStore(root / ".agent_orchestrator" / "workspace").record_artifact("provider_session_snapshot", payload)
    return payload


def _runtime_events_for_session(session: PlanSession) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    provider_runtime = (
        session.decision_verdict.selected_provider_runtime
        if session.decision_verdict and isinstance(session.decision_verdict.selected_provider_runtime, dict)
        else {}
    )
    runtime_mode = str(provider_runtime.get("runtime_mode") or provider_runtime.get("mode") or "control_plane")
    fallback_reason = provider_runtime.get("fallback_reason") or provider_runtime.get("recovery_provider_fallback_reason")
    degraded_reason = provider_runtime.get("degraded_reason") or provider_runtime.get("fallback_detail") or fallback_reason
    events.append(
        {
            "id": _stable_id("runtime-event", "session", session.id),
            "kind": "plan_session",
            "session_id": session.id,
            "runtime_mode": runtime_mode,
            "provider": provider_runtime.get("provider") or provider_runtime.get("selected_provider"),
            "intent": "govern plan session through approved-plan gate",
            "tool_intent": "team summary",
            "result_status": session.status,
            "fallback_reason": fallback_reason,
            "degraded_capability_reason": degraded_reason,
            "artifact_refs": [f"plans/{session.id}/session.json"],
            "usage_cost": _usage_cost_placeholder(),
            "records_only": True,
            "created_at": now_iso(),
        }
    )
    if degraded_reason or _session_has_provider_fallback(session):
        events.append(
            {
                "id": _stable_id("runtime-event", "provider-degraded", session.id, str(degraded_reason)),
                "kind": "provider_runtime_health",
                "session_id": session.id,
                "runtime_mode": runtime_mode,
                "provider": provider_runtime.get("provider") or provider_runtime.get("selected_provider"),
                "intent": "record provider/runtime fallback or degraded capability",
                "tool_intent": "team setup",
                "result_status": "provider_degraded",
                "fallback_reason": fallback_reason,
                "degraded_capability_reason": degraded_reason,
                "artifact_refs": [f"plans/{session.id}/session.json", "agent_orchestrator.strategy_decision.v1"],
                "usage_cost": _usage_cost_placeholder(),
                "records_only": True,
                "created_at": now_iso(),
            }
        )
    return events


def _runtime_event_for_run(run: dict[str, object]) -> dict[str, object]:
    accepted = run.get("accepted")
    status = "completed" if accepted is True else "failed" if accepted is False else "interrupted"
    return {
        "id": _stable_id("runtime-event", "run", str(run.get("id"))),
        "kind": "execution_run",
        "run_id": run.get("id"),
        "runtime_mode": run.get("final_mode") or run.get("initial_mode") or "unknown",
        "intent": "execute approved plan",
        "tool_intent": "team execute",
        "result_status": status,
        "failure_reason": "execution rejected or failed" if accepted is False else None,
        "artifact_refs": [str(run.get("path"))] if run.get("path") else [],
        "usage_cost": _usage_cost_placeholder(),
        "records_only": True,
        "created_at": now_iso(),
    }


def _provider_session_snapshot_from_job(job: dict[str, object]) -> dict[str, object]:
    status = str(job.get("status") or "unknown")
    metadata = job.get("metadata", {}) if isinstance(job.get("metadata"), dict) else {}
    parsed = job.get("parsed_payload", {}) if isinstance(job.get("parsed_payload"), dict) else {}
    operation = parsed.get("operation") if isinstance(parsed.get("operation"), dict) else None
    provider_session_ref = parsed.get("provider_session_ref") if isinstance(parsed.get("provider_session_ref"), dict) else None
    receipts = parsed.get("runtime_operation_receipts", []) if isinstance(parsed.get("runtime_operation_receipts"), list) else []
    if operation and not any(isinstance(item, dict) and item.get("id") == operation.get("id") for item in receipts):
        receipts = [*receipts, operation]
    terminal = status in {"completed", "failed", "cancelled"}
    pid = job.get("pid")
    if terminal:
        liveness_state = "terminal"
    elif pid:
        liveness_state = "running"
    elif job.get("session_id"):
        liveness_state = "unknown"
    else:
        liveness_state = "missing"
    runtime_mode = metadata.get("runtime_mode", {}) if isinstance(metadata.get("runtime_mode"), dict) else {}
    degraded_reason = (
        job.get("error")
        if status == "failed"
        else _metadata_value(job, "degraded_capability_reason")
        or _metadata_value(job, "fallback_reason")
    )
    support = _runtime_operation_support(job, liveness_state=liveness_state)
    measurement = _runtime_measurement_from_job(job)
    return {
        "format": CONTROL_PLANE_FORMATS["provider_session_snapshot"],
        "job_id": job.get("id"),
        "task_id": job.get("task_id"),
        "provider": job.get("provider"),
        "kind": job.get("kind"),
        "status": status,
        "phase": job.get("phase"),
        "runtime_mode": job.get("runtime_mode") or runtime_mode.get("mode") or "unknown",
        "model": job.get("model"),
        "session_id": job.get("session_id"),
        "thread_id": job.get("thread_id"),
        "provider_session_ref": provider_session_ref,
        "pid": pid,
        "command": list(job.get("command", [])) if isinstance(job.get("command"), list) else [],
        "home_isolation": {
            "runtime_home": runtime_mode.get("runtime_home"),
            "config_source": runtime_mode.get("config_source"),
            "inherits_user_config": runtime_mode.get("inherits_user_config"),
            "sandbox": runtime_mode.get("sandbox") or job.get("sandbox"),
        },
        "liveness": {
            "state": liveness_state,
            "terminal": terminal,
            "last_seen_at": job.get("updated_at") or job.get("completed_at") or job.get("started_at"),
            "degraded_reason": degraded_reason,
            "checked_at": now_iso(),
        },
        "runtime_measurement": measurement,
        "operation_support": support,
        "operation_receipts": [_runtime_operation_receipt(item, job) for item in receipts if isinstance(item, dict)][-10:],
        "last_operation_receipt": _runtime_operation_receipt(operation, job) if isinstance(operation, dict) else None,
        "recommended_recovery_command": _runtime_recovery_command(job, liveness_state=liveness_state),
        "artifact_refs": [f"jobs/{job.get('id')}.json"],
        "read_only": True,
        "created_at": now_iso(),
    }


def _runtime_event_for_session_snapshot(snapshot: dict[str, object]) -> dict[str, object]:
    status = str(snapshot.get("status") or "unknown")
    liveness = snapshot.get("liveness", {}) if isinstance(snapshot.get("liveness"), dict) else {}
    support = snapshot.get("operation_support", {}) if isinstance(snapshot.get("operation_support"), dict) else {}
    measurement = snapshot.get("runtime_measurement", {}) if isinstance(snapshot.get("runtime_measurement"), dict) else {}
    degraded = liveness.get("degraded_reason")
    return {
        "id": _stable_id("runtime-event", "job", str(snapshot.get("job_id"))),
        "kind": "delegated_job",
        "job_id": snapshot.get("job_id"),
        "session_id": snapshot.get("session_id"),
        "thread_id": snapshot.get("thread_id"),
        "runtime_mode": snapshot.get("runtime_mode") or "unknown",
        "provider": snapshot.get("provider"),
        "intent": snapshot.get("kind") or "delegated runtime job",
        "tool_intent": "job runtime",
        "result_status": "failed" if status == "failed" else "completed" if status == "completed" else status,
        "failure_reason": degraded if status == "failed" else None,
        "fallback_reason": degraded if "fallback" in str(degraded or "") else None,
        "degraded_capability_reason": degraded,
        "session_liveness": liveness,
        "operation_support": support,
        "runtime_measurement": measurement,
        "operation_receipts": snapshot.get("operation_receipts", []),
        "attachable": support.get("attach") == "available",
        "continuation_supported": support.get("continue") == "available",
        "recovery_safe_next_command": snapshot.get("recommended_recovery_command"),
        "artifact_refs": snapshot.get("artifact_refs", []),
        "usage_cost": measurement.get("usage_cost") if isinstance(measurement.get("usage_cost"), dict) else _usage_cost_placeholder(),
        "records_only": True,
        "created_at": liveness.get("last_seen_at") or now_iso(),
    }


def _runtime_measurement_from_job(job: dict[str, object]) -> dict[str, object]:
    existing = job.get("runtime_measurement")
    if isinstance(existing, dict):
        return existing
    metadata = job.get("metadata", {}) if isinstance(job.get("metadata"), dict) else {}
    parsed = job.get("parsed_payload", {}) if isinstance(job.get("parsed_payload"), dict) else {}
    return runtime_measurement_payload(
        provider=str(job.get("provider") or "unknown"),
        runtime_mode=str(job.get("runtime_mode") or "unknown"),
        status=str(job.get("status") or "unknown"),
        started_at=job.get("started_at") if isinstance(job.get("started_at"), str) else None,
        completed_at=job.get("completed_at") if isinstance(job.get("completed_at"), str) else None,
        exit_code=job.get("exit_code") if isinstance(job.get("exit_code"), int) else None,
        error=job.get("error") if isinstance(job.get("error"), str) else None,
        metadata=metadata,
        parsed_payload=parsed,
    )


def _runtime_operation_receipt(operation: dict[str, object] | None, job: dict[str, object]) -> dict[str, object] | None:
    if not operation:
        return None
    return {
        "format": operation.get("format") or CONTROL_PLANE_FORMATS["runtime_operation_receipt"],
        "id": operation.get("id") or _stable_id("receipt", str(job.get("id")), str(operation.get("action")), str(operation.get("updated_at"))),
        "job_id": operation.get("job_id") or job.get("id"),
        "provider": operation.get("provider") or job.get("provider"),
        "runtime_mode": operation.get("runtime_mode") or job.get("runtime_mode"),
        "session_id": operation.get("session_id") or job.get("session_id"),
        "thread_id": operation.get("thread_id") or job.get("thread_id"),
        "action": operation.get("action"),
        "status": operation.get("status"),
        "reason": operation.get("reason") or operation.get("status"),
        "detail": operation.get("detail"),
        "terminal_state": bool(operation.get("terminal_state")) or str(job.get("status")) in {"completed", "failed", "cancelled"},
        "records_only": True,
        "updated_at": operation.get("updated_at") or job.get("updated_at"),
    }


def _runtime_operation_support(job: dict[str, object], *, liveness_state: str) -> dict[str, object]:
    status = str(job.get("status") or "unknown")
    attach_available = bool(_metadata_value(job, "attach_available"))
    if status in {"completed", "failed", "cancelled"}:
        send = cancel = "already_terminal"
        continuation = "unavailable"
    elif liveness_state == "missing":
        send = cancel = "session_missing"
        continuation = "unavailable"
    else:
        send = cancel = "available"
        continuation = "available"
    return {
        "send": send,
        "cancel": cancel,
        "attach": "available" if attach_available else "unavailable",
        "continue": continuation,
    }


def _runtime_recovery_command(job: dict[str, object], *, liveness_state: str) -> str:
    job_id = str(job.get("id") or "")
    status = str(job.get("status") or "")
    if status == "running" and liveness_state in {"running", "unknown"}:
        return f"python -m agent_orchestrator.cli status {job_id}"
    if status == "failed":
        return f"python -m agent_orchestrator.cli result {job_id}"
    if status == "cancelled":
        return f"python -m agent_orchestrator.cli result {job_id}"
    if liveness_state == "missing":
        return "python -m agent_orchestrator.cli team workspace-status"
    return f"python -m agent_orchestrator.cli result {job_id}" if job_id else "python -m agent_orchestrator.cli team workspace-status"


def _metadata_value(payload: dict[str, object], key: str) -> object | None:
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}
    return metadata.get(key)


def _session_has_provider_fallback(session: PlanSession) -> bool:
    if not session.decision_verdict:
        return False
    provider_runtime = session.decision_verdict.selected_provider_runtime
    return any("fallback" in str(key) and bool(value) for key, value in provider_runtime.items())


def _usage_cost_placeholder() -> dict[str, object]:
    return {
        "source": "placeholder",
        "measurement_status": "placeholder",
        "usage_available": False,
        "cost_available": False,
        "policy": "record provider usage/cost here when runtime supplies it",
    }
