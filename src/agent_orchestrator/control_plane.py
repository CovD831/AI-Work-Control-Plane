"""AI Work Control Plane artifact models and snapshot builders."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, json, pathlib, shutil, subprocess, typing
# RESPONSIBILITY: Build AI-native workspace, context, strategy, topology, approval, evidence, and memory artifacts.
# MODULE: decision_core
# ---

import json
import shutil
import subprocess
from pathlib import Path

from agent_orchestrator.control_plane_artifacts import (
    artifact_ref as _artifact_ref,
    resolve_root as _resolve_root,
    stable_id as _stable_id,
)
from agent_orchestrator.control_plane_approvals import (
    ApprovalItem,
    ApprovalReasonCode,
    ApprovalStatus,
    ApprovalStore,
)
from agent_orchestrator.control_plane_constants import (
    CONTROL_PLANE_FORMATS,
)
from agent_orchestrator.control_plane_governance import build_governance_bundle as build_governance_bundle
from agent_orchestrator.control_plane_governance import inspect_governance_bundle as inspect_governance_bundle
from agent_orchestrator.control_plane_ledger import build_run_ledger as build_run_ledger
from agent_orchestrator.control_plane_recovery import build_recovery_recommendation as build_recovery_recommendation
from agent_orchestrator.control_plane_recovery import build_recovery_timeline as build_recovery_timeline
from agent_orchestrator.control_plane_runtime import build_provider_session_snapshot as build_provider_session_snapshot
from agent_orchestrator.control_plane_runtime import build_runtime_event_stream as build_runtime_event_stream
from agent_orchestrator.control_plane_topology import build_execution_topology_snapshot as build_execution_topology_snapshot
from agent_orchestrator.control_plane_workspace import WorkspaceIndexStore, WorkspaceStateSnapshot
from agent_orchestrator.control_plane_workspace import workspace_index_payload as _workspace_index_payload
from agent_orchestrator.control_plane_workspace import workspace_recovery_dashboard as _workspace_recovery_dashboard
from agent_orchestrator.events import EventStore
from agent_orchestrator.jobs import AgentJob, FileJobRuntime, now_iso
from agent_orchestrator.memory import MemoryRecord, MemoryStore
from agent_orchestrator.planning import PlanSession
from agent_orchestrator.planning_governance import get_governance_status
from agent_orchestrator.planning_support import build_document_context_package


def build_workspace_state_snapshot(
    project_root: Path | str = ".",
    *,
    plans_root: Path | str = ".agent_orchestrator/plans",
    runs_root: Path | str = ".agent_orchestrator/runs",
    jobs_root: Path | str = ".agent_orchestrator/jobs",
    approvals_root: Path | str = ".agent_orchestrator/approvals",
    provider_health: dict[str, object] | None = None,
    write_index: bool = False,
) -> dict[str, object]:
    root = Path(project_root)
    plans_path = _resolve_root(root, plans_root)
    runs_path = _resolve_root(root, runs_root)
    jobs_path = _resolve_root(root, jobs_root)
    approvals_path = _resolve_root(root, approvals_root)
    sessions = _read_plan_sessions(plans_path)
    approvals = build_approval_queue(
        root,
        plans_root=plans_path,
        approvals_root=approvals_path,
        sessions=sessions,
    )
    snapshot = WorkspaceStateSnapshot(
        project_root=str(root.resolve()),
        plans=[_session_index_entry(session) for session in sessions],
        runs=_read_run_entries(runs_path),
        jobs=_read_job_entries(jobs_path),
        evidence=_evidence_state(root),
        approvals=approvals["items"],
        provider_health=provider_health,
        dirty_state=_git_dirty_state(root),
        memory_digest=_memory_digest(root / ".agent_orchestrator" / "memory"),
        external_cache=_external_cache_status(root),
    )
    if write_index:
        WorkspaceIndexStore(root / ".agent_orchestrator" / "workspace").write(snapshot)
    return snapshot.to_dict()


def build_workspace_index(
    project_root: Path | str = ".",
    *,
    plans_root: Path | str = ".agent_orchestrator/plans",
    runs_root: Path | str = ".agent_orchestrator/runs",
    jobs_root: Path | str = ".agent_orchestrator/jobs",
    approvals_root: Path | str = ".agent_orchestrator/approvals",
    provider_health: dict[str, object] | None = None,
) -> dict[str, object]:
    root = Path(project_root)
    plans_path = _resolve_root(root, plans_root)
    runs_path = _resolve_root(root, runs_root)
    jobs_path = _resolve_root(root, jobs_root)
    approvals_path = _resolve_root(root, approvals_root)
    snapshot_payload = build_workspace_state_snapshot(
        root,
        plans_root=plans_path,
        runs_root=runs_path,
        jobs_root=jobs_path,
        approvals_root=approvals_path,
        provider_health=provider_health,
        write_index=False,
    )
    snapshot = WorkspaceStateSnapshot.from_dict(snapshot_payload)
    loaded_sessions = _read_plan_sessions(plans_path)
    runtime_events = build_runtime_event_stream(
        root,
        plans_root=plans_path,
        runs_root=runs_path,
        jobs_root=jobs_path,
        approvals_root=approvals_path,
        sessions=loaded_sessions,
    )
    recovery_timeline = build_recovery_timeline(
        root,
        plans_root=plans_path,
        runs_root=runs_path,
        jobs_root=jobs_path,
        approvals_root=approvals_path,
        sessions=loaded_sessions,
    )
    active_session = next((session for session in loaded_sessions if session.status not in {"accepted", "completed"}), None)
    recovery_recommendation = build_recovery_recommendation(
        active_session,
        recovery_timeline=recovery_timeline,
        runtime_event_stream=runtime_events,
    ) if active_session is not None else None
    index = WorkspaceIndexStore(root / ".agent_orchestrator" / "workspace")
    existing = index.payload() or {}
    artifacts = existing.get("artifacts", {}) if isinstance(existing.get("artifacts"), dict) else {}
    dashboard = _workspace_recovery_dashboard(
        recovery_timeline=recovery_timeline,
        runtime_events=runtime_events,
        recovery_recommendation=recovery_recommendation,
    )
    payload = _workspace_index_payload(
        snapshot,
        artifacts={
            **artifacts,
            "workspace_state": _artifact_ref(snapshot_payload),
            "recovery_timeline": _artifact_ref(recovery_timeline),
            "runtime_event_stream": _artifact_ref(runtime_events),
            **({"recovery_recommendation": _artifact_ref(recovery_recommendation)} if recovery_recommendation else {}),
        },
    )
    payload["provider_evidence_summary"] = build_provider_evidence_summary(jobs_path)
    payload.update(dashboard)
    return index.write_index(payload)


def build_context_packet(
    project_root: Path | str = ".",
    *,
    query: str = "",
    changed_files: list[str] | None = None,
    jobs_root: Path | str = ".agent_orchestrator/jobs",
    memory_root: Path | str = ".agent_orchestrator/memory",
) -> dict[str, object]:
    root = Path(project_root)
    jobs_path = _resolve_root(root, jobs_root)
    memory_path = _resolve_root(root, memory_root)
    changed = list(changed_files or [])
    docs_context = build_document_context_package(
        root,
        FileJobRuntime(jobs_path),
        query=query,
        changed_files=changed,
        include_all=False,
    )
    memory = MemoryStore(memory_path)
    memory_records = memory.search(query, limit=5) if query.strip() else memory.query(limit=5)
    source_artifacts = [
        {"kind": "doc", "id": doc_id}
        for doc_id in docs_context.get("selected_doc_ids", [])
    ]
    source_artifacts.extend(
        {"kind": "memory", "id": str(record.get("id", ""))}
        for record in memory_records
        if record.get("id")
    )
    content_chars = len(str(docs_context.get("injection_markdown", ""))) + sum(
        len(str(record.get("summary", ""))) for record in memory_records
    )
    stale_warnings = _context_stale_warnings(docs_context, memory_records)
    retrieval_assessment = _retrieval_assessment(query, docs_context, memory_records)
    payload = {
        "format": CONTROL_PLANE_FORMATS["context_packet"],
        "query": query,
        "changed_files": changed,
        "docs_context": docs_context,
        "memory_records": memory_records,
        "source_artifacts": source_artifacts,
        "stale_warnings": stale_warnings,
        "retrieval_assessment": retrieval_assessment,
        "source_conflict_summary": _source_conflict_summary(stale_warnings, retrieval_assessment),
        "evidence_support_matrix": _evidence_support_matrix(query, docs_context, memory_records),
        "token_budget_summary": {
            "estimated_chars": content_chars,
            "estimated_tokens": max(1, content_chars // 4) if content_chars else 0,
            "policy": "minimum sufficient context; does not choose strategy",
        },
        "external_cache": _external_cache_status(root),
        "created_at": now_iso(),
    }
    WorkspaceIndexStore(root / ".agent_orchestrator" / "workspace").record_artifact("context_packet", payload)
    return payload


def build_strategy_decision(session: PlanSession, workspace_state: dict[str, object] | None = None) -> dict[str, object]:
    payload = session.to_dict()
    status = get_governance_status(payload)
    decision = session.decision_verdict.to_dict() if session.decision_verdict else {}
    next_task = status.get("next_executable_task") if isinstance(status.get("next_executable_task"), dict) else None
    current_checkpoint_objective = (
        str(next_task.get("title"))
        if isinstance(next_task, dict)
        else str(status.get("primary_reason") or session.requirement)
    )
    verification_requirements = [
        "Run the current phase targeted pytest slice before moving phases.",
        "Run full pytest and team check-compliance only at convergence.",
    ]
    if isinstance(next_task, dict):
        verification_requirements.extend(str(item) for item in next_task.get("validation", []) if item)
    return {
        "format": CONTROL_PLANE_FORMATS["strategy_decision"],
        "session_id": session.id,
        "goal": session.structured_brief.goal or session.requirement,
        "current_checkpoint_objective": current_checkpoint_objective,
        "next_goal": current_checkpoint_objective,
        "status": session.status,
        "selected_topology": decision.get("selected_topology"),
        "selected_provider_runtime": decision.get("selected_provider_runtime", {}),
        "control_plane_focus": "state_context_strategy_topology_approval_evidence_memory_recovery",
        "orchestration_horizon": {
            "short_term": "explicit orchestration solves real local work",
            "medium_term": "control plane governs orchestration and evidence",
            "long_term": "models may internalize orchestration while external artifacts remain auditable",
        },
        "topology_policy": _strategy_topology_policy(session, status, decision),
        "recovery_policy": _strategy_recovery_policy(status),
        "runtime_health": _runtime_health_payload(decision.get("selected_provider_runtime", {})),
        "tool_inventory": _tool_inventory_payload(),
        "usage_cost": _usage_cost_placeholder(),
        "rationale": list(decision.get("decision_rationale", [])) if isinstance(decision.get("decision_rationale"), list) else [],
        "tradeoffs": [
            "Keep explicit orchestration for short-term reliability.",
            "Move durable state, evidence, approvals, and memory into the control-plane artifact chain.",
            "Allow orchestration to shrink over time while keeping state, evidence, approvals, memory, and recovery external.",
        ],
        "risks": [str(item) for item in session.structured_brief.risks],
        "verification_requirements": verification_requirements,
        "validation_plan": verification_requirements,
        "executes": False,
        "workspace_state_created_at": workspace_state.get("created_at") if isinstance(workspace_state, dict) else None,
        "created_at": now_iso(),
    }


def _strategy_topology_policy(
    session: PlanSession,
    status: dict[str, object],
    decision: dict[str, object],
) -> dict[str, object]:
    recommendation = (
        dict(session.structured_brief.topology_recommendation)
        if isinstance(session.structured_brief.topology_recommendation, dict)
        else {}
    )
    provider_runtime = decision.get("selected_provider_runtime", {})
    fallback_signals = {
        key: value
        for key, value in dict(provider_runtime).items()
        if isinstance(key, str) and "fallback" in key and value
    } if isinstance(provider_runtime, dict) else {}
    return {
        "task_size": recommendation.get("subtask_count"),
        "selected_topology": decision.get("selected_topology") or recommendation.get("recommended_topology"),
        "selection_reason": recommendation.get("selection_reason") or status.get("topology_reason"),
        "signals": recommendation.get("signals", {}),
        "review_policy": dict(session.structured_brief.review_policy)
        if isinstance(session.structured_brief.review_policy, dict)
        else {},
        "provider_fallback": fallback_signals,
    }


def _strategy_recovery_policy(status: dict[str, object]) -> dict[str, object]:
    recovery_semantics = status.get("recovery_semantics", {}) if isinstance(status.get("recovery_semantics"), dict) else {}
    return {
        "resume_action": status.get("resume_action"),
        "resume_reason": status.get("resume_reason"),
        "recovery_actions": list(status.get("recovery_actions", []))
        if isinstance(status.get("recovery_actions"), list)
        else [],
        "interruption_aware": bool(recovery_semantics.get("interruption_aware", True)),
        "execution_gate_authority": recovery_semantics.get("execution_gate_authority", "approved_plan_gate"),
        "records_only": bool(recovery_semantics.get("records_only", True)),
    }


def _runtime_health_payload(provider_runtime: object | None = None) -> dict[str, object]:
    runtime = provider_runtime if isinstance(provider_runtime, dict) else {}
    runtime_mode = str(runtime.get("runtime_mode") or runtime.get("mode") or "unknown")
    provider = runtime.get("provider") or runtime.get("selected_provider") or "unknown"
    degraded_reason = runtime.get("fallback_detail") or runtime.get("fallback_reason") or runtime.get("degraded_reason")
    return {
        "runtime_mode": runtime_mode,
        "provider": provider,
        "availability": runtime.get("availability", "not_checked"),
        "setup_doctor": {
            "source": "team setup",
            "status": "not_checked",
            "degraded_capability_reason": degraded_reason,
        },
        "provider_fallback": {
            key: value
            for key, value in runtime.items()
            if isinstance(key, str) and "fallback" in key and value
        },
        "degraded_capability_reason": degraded_reason,
        "records_only": True,
    }


def _tool_inventory_payload(project_root: Path | None = None) -> dict[str, object]:
    root = project_root or Path(".")
    return {
        "source": "control_plane_placeholder",
        "mcp": {
            "available": shutil.which("explore-cache-mcp") is not None,
            "required": False,
            "inventory_status": "placeholder",
        },
        "local_tools": [
            {"name": "pytest", "available": shutil.which("pytest") is not None},
            {"name": "git", "available": shutil.which("git") is not None},
            {"name": "explore-cache", "available": shutil.which("explore-cache") is not None},
        ],
        "project_root": str(root.resolve()) if root.exists() else str(root),
        "mutation_policy": "inventory only; tool execution remains below approved-plan/runtime gates",
    }


def _usage_cost_placeholder() -> dict[str, object]:
    return {
        "source": "placeholder",
        "measurement_status": "placeholder",
        "usage_available": False,
        "cost_available": False,
        "policy": "record provider usage/cost here when runtime supplies it",
    }


def build_approval_queue(
    project_root: Path | str = ".",
    *,
    plans_root: Path | str = ".agent_orchestrator/plans",
    approvals_root: Path | str = ".agent_orchestrator/approvals",
    sessions: list[PlanSession] | None = None,
) -> dict[str, object]:
    root = Path(project_root)
    plans_path = _resolve_root(root, plans_root)
    approvals_path = _resolve_root(root, approvals_root)
    loaded_sessions = sessions if sessions is not None else _read_plan_sessions(plans_path)
    generated = _generated_approval_items(loaded_sessions)
    store = ApprovalStore(approvals_path)
    latest = store.latest_by_id()
    merged: dict[str, ApprovalItem] = {item.id: item for item in generated}
    merged.update(latest)
    items = sorted(merged.values(), key=lambda item: (item.status != "pending", item.created_at, item.id))
    counts = {
        "pending": sum(1 for item in items if item.status == "pending"),
        "approved": sum(1 for item in items if item.status == "approved"),
        "rejected": sum(1 for item in items if item.status == "rejected"),
        "resolved": sum(1 for item in items if item.status == "resolved"),
        "total": len(items),
    }
    reason_code_distribution: dict[str, int] = {}
    for item in items:
        reason_code_distribution[item.reason_code] = reason_code_distribution.get(item.reason_code, 0) + 1
    blocking_count = sum(1 for item in items if item.status == "pending" and item.reason_code in {"blocked_session", "compliance_blocking"})
    recommended_command = "team approvals list"
    first_pending = next((item for item in items if item.status == "pending"), None)
    if first_pending is not None:
        recommended_command = f"team approvals resolve {first_pending.id} --status resolved --reason \"<decision>\""
    return {
        "format": CONTROL_PLANE_FORMATS["approval_queue"],
        "project_root": str(Path(project_root).resolve()),
        "items": [item.to_dict() for item in items],
        "counts": counts,
        "inbox_summary": {
            "pending_count": counts["pending"],
            "resolved_count": counts["resolved"],
            "blocking_count": blocking_count,
            "reason_code_distribution": reason_code_distribution,
            "recommended_next_command": recommended_command,
        },
        "mutation_policy": "resolve only records the human decision; it does not execute gated work",
    }


def resolve_approval_item(
    approval_id: str,
    *,
    status: ApprovalStatus,
    reason: str,
    project_root: Path | str = ".",
    plans_root: Path | str = ".agent_orchestrator/plans",
    approvals_root: Path | str = ".agent_orchestrator/approvals",
    actor: str = "human",
) -> dict[str, object]:
    root = Path(project_root)
    plans_path = _resolve_root(root, plans_root)
    approvals_path = _resolve_root(root, approvals_root)
    queue = build_approval_queue(root, plans_root=plans_path, approvals_root=approvals_path)
    by_id = {
        str(item.get("id")): ApprovalItem.from_dict(item)
        for item in queue.get("items", [])
        if isinstance(item, dict)
    }
    item = by_id.get(
        approval_id,
        ApprovalItem(
            id=approval_id,
            status="pending",
            reason_code="awaiting_human_decision",
            reason="Manual approval item resolved without a generated queue entry.",
            scope="manual",
            scope_id=approval_id,
            recommended_action="inspect",
        ),
    )
    resolved = item.resolved(status=status, reason=reason, actor=actor)
    ApprovalStore(approvals_path).append(resolved)
    EventStore(root / ".agent_orchestrator" / "events").append(
        type="approval.resolved",
        scope=resolved.scope,
        scope_id=resolved.scope_id,
        message=f"Approval {resolved.id} resolved as {status}.",
        payload=resolved.to_dict(),
    )
    MemoryStore(root / ".agent_orchestrator" / "memory").append(
        namespace="approval",
        session_id=resolved.session_id or "",
        record_type="approval_resolution",
        role="approval_gate",
        provider="control_plane",
        summary=f"{resolved.id}: {status}",
        payload=resolved.to_dict(),
        provenance={
            "source_artifacts": [resolved.id],
            "base_commit": _git_head(root),
        },
        freshness="fresh",
        confidence=1.0,
        external_cache_status=_external_cache_status(root),
    )
    return {
        "format": CONTROL_PLANE_FORMATS["approval_queue"],
        "resolved_item": resolved.to_dict(),
        "mutation_policy": "recorded approval decision only; execution gates remain authoritative",
    }


def build_evidence_bundle(project_root: Path | str = ".", compliance: dict[str, object] | None = None) -> dict[str, object]:
    root = Path(project_root)
    evidence_state = _evidence_state(root)
    compliance_payload = compliance or {"blocking": False, "blocking_reasons": [], "warnings": []}
    gate_evidence = _gate_evidence_summary(root, compliance_payload, evidence_state)
    failed = [gate for gate in gate_evidence["gates"] if gate.get("status") in {"failed", "missing"}]
    payload = {
        "format": CONTROL_PLANE_FORMATS["evidence_bundle"],
        "status": "blocked" if any(gate.get("status") == "failed" for gate in failed) else "ready_with_gaps" if failed else "ready",
        "gate_evidence": gate_evidence,
        "evidence_state": evidence_state,
        "recovery_refs": _evidence_recovery_refs(root),
        "runtime_fidelity": _evidence_runtime_fidelity(root),
        "provider_evidence_summary": build_provider_evidence_summary(root / ".agent_orchestrator" / "jobs"),
        "compliance": {
            "blocking": bool(compliance_payload.get("blocking", False)),
            "blocking_reasons": list(compliance_payload.get("blocking_reasons", []))
            if isinstance(compliance_payload.get("blocking_reasons", []), list)
            else [],
            "warnings": list(compliance_payload.get("warnings", []))
            if isinstance(compliance_payload.get("warnings", []), list)
                else [],
        },
        "runtime_health": _runtime_health_payload(),
        "tool_inventory": _tool_inventory_payload(project_root=root),
        "usage_cost": _usage_cost_placeholder(),
        "memory_recommendation": _evidence_memory_recommendation(root, gate_evidence, compliance_payload),
        "created_at": now_iso(),
    }
    WorkspaceIndexStore(root / ".agent_orchestrator" / "workspace").record_artifact("evidence_bundle", payload)
    return payload


def build_provider_evidence_summary(jobs_root: Path | str) -> dict[str, object]:
    jobs = _read_job_payloads(Path(jobs_root))
    provider_session_refs: list[dict[str, object]] = []
    codex_payloads: list[dict[str, object]] = []
    codex_pilots: list[dict[str, object]] = []
    usage_payloads: list[dict[str, object]] = []
    for job in jobs:
        parsed = job.get("parsed_payload", {}) if isinstance(job.get("parsed_payload"), dict) else {}
        provider_ref = parsed.get("provider_session_ref") if isinstance(parsed.get("provider_session_ref"), dict) else None
        codex_json = parsed.get("codex_exec_json") if isinstance(parsed.get("codex_exec_json"), dict) else None
        codex_pilot = parsed.get("codex_pilot") if isinstance(parsed.get("codex_pilot"), dict) else None
        usage = parsed.get("usage") if isinstance(parsed.get("usage"), dict) else None
        if provider_ref:
            provider_session_refs.append(provider_ref)
        if codex_json:
            codex_payloads.append(codex_json)
            if isinstance(codex_json.get("usage"), dict) and usage is None:
                usage_payloads.append(codex_json["usage"])
        if codex_pilot:
            codex_pilots.append(codex_pilot)
        if usage:
            usage_payloads.append(usage)
    final_message_artifact_count = sum(
        1
        for pilot in codex_pilots
        if pilot.get("output_last_message") and pilot.get("final_message_source") == "output_last_message"
    )
    codex_json_event_count = sum(int(payload.get("event_count", 0) or 0) for payload in codex_payloads)
    malformed_event_count = sum(int(payload.get("malformed_event_count", 0) or 0) for payload in codex_payloads)
    provider_owned_ref_count = sum(1 for ref in provider_session_refs if ref.get("provider_owned") is True)
    continuation_provider_owned_count = sum(
        1 for ref in provider_session_refs if ref.get("continuation_guarantee") == "provider_owned"
    )
    return {
        "format": "agent_orchestrator.provider_evidence_summary.v1",
        "job_count": len(jobs),
        "provider_session_ref_count": len(provider_session_refs),
        "provider_owned_ref_count": provider_owned_ref_count,
        "continuation_provider_owned_count": continuation_provider_owned_count,
        "codex_exec_json_job_count": len(codex_payloads),
        "codex_json_event_count": codex_json_event_count,
        "codex_malformed_event_count": malformed_event_count,
        "final_message_artifact_count": final_message_artifact_count,
        "provider_reported_usage_count": len(usage_payloads),
        "usage_cost_measurement_status": "measured" if usage_payloads else "placeholder",
        "session_ownership_claim": "provider_owned" if provider_owned_ref_count else "none",
        "policy": "provider evidence is read-only; provider-owned refs do not imply persistent session ownership",
    }


def _read_plan_sessions(plans_root: Path) -> list[PlanSession]:
    sessions: list[PlanSession] = []
    for path in sorted(plans_root.glob("*/session.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                sessions.append(PlanSession.from_dict(payload))
        except Exception:
            continue
    return sessions


def _session_index_entry(session: PlanSession) -> dict[str, object]:
    status = get_governance_status(session.to_dict())
    return {
        "id": session.id,
        "status": session.status,
        "phase": session.resume.current_phase,
        "pending_role": session.resume.pending_role,
        "goal": session.structured_brief.goal or session.requirement,
        "selected_topology": session.decision_verdict.selected_topology if session.decision_verdict else None,
        "linked_execution_run_id": session.resume.linked_execution_run_id,
        "primary_action": status.get("primary_action"),
        "blocking_reasons": status.get("blocking_reasons", []),
    }


def _read_run_entries(runs_root: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for path in sorted(runs_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        entries.append(
            {
                "id": payload.get("id") or path.stem,
                "status": payload.get("status"),
                "initial_mode": payload.get("initial_mode"),
                "final_mode": payload.get("final_mode"),
                "accepted": payload.get("accepted"),
                "path": str(path),
            }
        )
    return entries[-25:][::-1]


def _read_job_entries(jobs_root: Path) -> list[dict[str, object]]:
    jobs: list[AgentJob] = []
    try:
        jobs = FileJobRuntime(jobs_root).list_recent()
    except Exception:
        jobs = []
    if not jobs:
        for path in sorted(jobs_root.glob("job-*.json"))[-25:]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    jobs.append(AgentJob.from_dict(payload))
            except Exception:
                continue
    return [
        {
            "id": job.id,
            "provider": job.provider,
            "kind": job.kind,
            "status": job.status,
            "phase": job.phase,
            "runtime_mode": job.runtime_mode,
            "updated_at": job.updated_at,
            "summary": job.summary,
        }
        for job in jobs[-25:][::-1]
    ]


def _read_job_payloads(jobs_root: Path) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for path in sorted(jobs_root.glob("job-*.json"))[-25:]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    for job in _read_job_entries(jobs_root):
        if not any(existing.get("id") == job.get("id") for existing in payloads):
            payloads.append(dict(job))
    return payloads[-25:][::-1]


def _evidence_state(project_root: Path) -> dict[str, object]:
    evidence_root = project_root / ".agent_orchestrator" / "evidence"
    return {
        "benchmark_report_present": (project_root / "docs" / "process" / "v1x-evidence-report.md").exists(),
        "trend_report_present": (project_root / "docs" / "process" / "v1x-evidence-trend.md").exists(),
        "evidence_cases_present": (project_root / "docs" / "process" / "evidence-cases.json").exists(),
        "real_tasks_json_present": (evidence_root / "real-tasks.json").exists(),
        "evidence_root": str(evidence_root),
    }


def _git_dirty_state(project_root: Path) -> dict[str, object]:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except Exception as exc:
        return {"available": False, "reason": str(exc), "changed_files": [], "dirty": False}
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return {
        "available": result.returncode == 0,
        "dirty": bool(lines),
        "changed_files": lines,
        "count": len(lines),
        "detail": result.stderr.strip() if result.returncode else "",
    }


def _git_head(project_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except Exception:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _memory_digest(memory_root: Path) -> dict[str, object]:
    path = memory_root / "memory.jsonl"
    if not path.exists():
        return {"count": 0, "recent": [], "namespaces": []}
    records: list[MemoryRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(MemoryRecord.from_dict(payload))
    namespaces = sorted({record.namespace for record in records})
    return {
        "count": len(records),
        "namespaces": namespaces,
        "recent": [record.to_dict() for record in records[-5:]][::-1],
    }


def _external_cache_status(project_root: Path) -> dict[str, object]:
    cli_path = shutil.which("explore-cache")
    mcp_path = shutil.which("explore-cache-mcp")
    return {
        "name": "explore_cache",
        "required": False,
        "cli_available": bool(cli_path),
        "mcp_available": bool(mcp_path),
        "cli_path": cli_path,
        "mcp_path": mcp_path,
        "project_cache_present": (project_root / "explore-cache").exists(),
        "status": "available" if cli_path or mcp_path else "optional_unavailable",
    }


def _evidence_memory_recommendation(
    project_root: Path,
    gate_evidence: dict[str, object],
    compliance: dict[str, object],
) -> dict[str, object]:
    gates = gate_evidence.get("gates", []) if isinstance(gate_evidence.get("gates"), list) else []
    eligible: list[dict[str, object]] = []
    compliance_has_signal = bool(compliance.get("blocking")) or bool(compliance.get("blocking_reasons")) or bool(compliance.get("warnings"))
    if compliance_has_signal:
        eligible.append(
            {
                "record_type": "compliance_result",
                "namespace": "evidence",
                "source_artifacts": ["team check-compliance"],
                "freshness": "fresh",
                "confidence": 1.0,
            }
        )
    if any(isinstance(gate, dict) and gate.get("name") == "full_tests" and gate.get("status") == "passed" for gate in gates):
        eligible.append(
            {
                "record_type": "full_gate_result",
                "namespace": "evidence",
                "source_artifacts": ["pytest"],
                "freshness": "fresh",
                "confidence": 1.0,
            }
        )
    if any(isinstance(gate, dict) and gate.get("name") == "evidence_report" and gate.get("status") == "passed" for gate in gates):
        eligible.append(
            {
                "record_type": "evidence_report",
                "namespace": "evidence",
                "source_artifacts": ["docs/process/v1x-evidence-report.md"],
                "freshness": "fresh",
                "confidence": 0.9,
            }
        )
    external = _external_cache_status(project_root)
    candidates = _memory_promotion_candidates(gate_evidence, compliance)
    return {
        "policy": "write only durable gate outcomes, compliance results, approval resolutions, and dogfood outcomes",
        "auto_write": False,
        "eligible_records": eligible,
        "promotion_policy": "candidates require provenance and explicit promotion before durable MemoryRecord write",
        "candidates": candidates,
        "candidate_count": len(candidates),
        "excluded": ["transient status", "planned gates without result"],
        "required_provenance_fields": ["source_artifacts"],
        "recovery_refs": _evidence_recovery_refs(project_root),
        "external_cache_status": external if external.get("status") == "available" else {**external, "status": "optional_unavailable"},
    }


def _evidence_recovery_refs(project_root: Path) -> dict[str, object]:
    index = WorkspaceIndexStore(project_root / ".agent_orchestrator" / "workspace").payload() or {}
    artifacts = index.get("artifacts", {}) if isinstance(index.get("artifacts"), dict) else {}
    return {
        "recovery_timeline": artifacts.get("recovery_timeline"),
        "runtime_event_stream": artifacts.get("runtime_event_stream"),
        "recovery_recommendation": artifacts.get("recovery_recommendation"),
        "run_ledger": artifacts.get("run_ledger"),
    }


def _evidence_runtime_fidelity(project_root: Path) -> dict[str, object]:
    index = WorkspaceIndexStore(project_root / ".agent_orchestrator" / "workspace").payload() or {}
    artifacts = index.get("artifacts", {}) if isinstance(index.get("artifacts"), dict) else {}
    return {
        "provider_session_snapshot": artifacts.get("provider_session_snapshot"),
        "runtime_event_stream": artifacts.get("runtime_event_stream"),
        "operation_receipt_format": CONTROL_PLANE_FORMATS["runtime_operation_receipt"],
        "policy": "read-only runtime fidelity evidence; does not imply persistent provider session ownership",
    }


def _memory_promotion_candidates(
    gate_evidence: dict[str, object],
    compliance: dict[str, object],
) -> list[dict[str, object]]:
    gates = gate_evidence.get("gates", []) if isinstance(gate_evidence.get("gates"), list) else []
    candidates = [
        _memory_candidate(
            "durable_outcome",
            "evidence",
            "Durable gate outcome can be promoted after final convergence evidence exists.",
            ["agent_orchestrator.evidence_bundle.v1"],
            ready=any(isinstance(gate, dict) and gate.get("status") == "passed" for gate in gates),
        ),
        _memory_candidate(
            "decision",
            "decision",
            "Control-plane operations track decisions can be promoted when linked to docs and evidence.",
            ["docs/process/ai-work-control-plane-operations-track-plan.md"],
            ready=True,
        ),
        _memory_candidate(
            "lesson",
            "knowledge",
            "Lessons from targeted-test failures can be promoted when backed by command output and patch context.",
            ["phase targeted tests"],
            ready=False,
        ),
        _memory_candidate(
            "recovery_note",
            "recovery",
            "Recovery notes can be promoted when they explain an interrupted, failed, or blocked run.",
            ["agent_orchestrator.run_ledger.v1"],
            ready=bool(compliance.get("blocking")) or bool(compliance.get("blocking_reasons")),
        ),
        _memory_candidate(
            "provider_runtime_health_note",
            "runtime_health",
            "Provider/runtime health notes can be promoted after setup or evidence gates record degraded capability.",
            ["agent_orchestrator.evidence_bundle.v1"],
            ready=False,
        ),
        _memory_candidate(
            "recovery_pattern",
            "recovery",
            "Live recovery patterns can be promoted after the timeline explains a repeated blocked or interrupted path.",
            ["agent_orchestrator.recovery_timeline.v1"],
            ready=bool(compliance.get("blocking")) or bool(compliance.get("blocking_reasons")),
        ),
        _memory_candidate(
            "runtime_degradation_note",
            "runtime_health",
            "Runtime degradation notes can be promoted when provider fallback or failed runtime events have provenance.",
            ["agent_orchestrator.runtime_event_stream.v1"],
            ready=False,
        ),
        _memory_candidate(
            "approval_delay_note",
            "approval",
            "Approval delay notes can be promoted when recovery timeline and approval inbox show a durable waiting pattern.",
            ["agent_orchestrator.approval_queue.v1", "agent_orchestrator.recovery_timeline.v1"],
            ready=False,
        ),
        _memory_candidate(
            "compliance_blocking_note",
            "compliance",
            "Compliance blocking notes can be promoted when blocking reasons are linked to recovery evidence.",
            ["team check-compliance", "agent_orchestrator.recovery_timeline.v1"],
            ready=bool(compliance.get("blocking")),
        ),
    ]
    return candidates


def _memory_candidate(
    record_type: str,
    namespace: str,
    summary: str,
    source_artifacts: list[str],
    *,
    ready: bool,
) -> dict[str, object]:
    return {
        "id": _stable_id("memory-candidate", record_type, namespace, *source_artifacts),
        "record_type": record_type,
        "namespace": namespace,
        "summary": summary,
        "ready_for_promotion": ready,
        "provenance": {
            "source_artifacts": source_artifacts,
        },
        "promotion_gate": "explicit approval or evidence-backed curator action required",
    }


def _context_stale_warnings(docs_context: dict[str, object], memory_records: list[dict[str, object]]) -> list[str]:
    warnings: list[str] = []
    doc_sync = docs_context.get("doc_sync", {}) if isinstance(docs_context.get("doc_sync"), dict) else {}
    if doc_sync.get("missing_docs"):
        warnings.append("docs context has missing canonical docs")
    if doc_sync.get("stale_docs"):
        warnings.append("docs context has stale canonical docs")
    for record in memory_records:
        freshness = record.get("freshness")
        if freshness and freshness != "fresh":
            warnings.append(f"memory {record.get('id')} freshness={freshness}")
    return warnings


def _retrieval_assessment(
    query: str,
    docs_context: dict[str, object],
    memory_records: list[dict[str, object]],
) -> dict[str, object]:
    doc_sync = docs_context.get("doc_sync", {}) if isinstance(docs_context.get("doc_sync"), dict) else {}
    freshness = "fresh" if bool(doc_sync.get("fresh", True)) and not any(record.get("freshness") not in {None, "fresh"} for record in memory_records) else "mixed"
    authority = "canonical_docs_plus_memory" if docs_context.get("selected_doc_ids") and memory_records else "canonical_docs" if docs_context.get("selected_doc_ids") else "memory_only" if memory_records else "limited"
    relevance_scores = _relevance_scores(query, docs_context, memory_records)
    average_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    return {
        "freshness_summary": freshness,
        "authority_summary": authority,
        "relevance_summary": "high" if average_relevance >= 0.66 else "medium" if average_relevance >= 0.33 else "low",
        "average_relevance_score": round(average_relevance, 2),
        "doc_count": len(docs_context.get("selected_doc_ids", [])) if isinstance(docs_context.get("selected_doc_ids"), list) else 0,
        "memory_count": len(memory_records),
    }


def _source_conflict_summary(stale_warnings: list[str], retrieval_assessment: dict[str, object]) -> dict[str, object]:
    stale_count = len(stale_warnings)
    return {
        "has_conflicts": stale_count > 0 or retrieval_assessment.get("freshness_summary") == "mixed",
        "stale_warning_count": stale_count,
        "conflict_level": "medium" if stale_count else "low" if retrieval_assessment.get("freshness_summary") == "mixed" else "none",
    }


def _evidence_support_matrix(
    query: str,
    docs_context: dict[str, object],
    memory_records: list[dict[str, object]],
) -> dict[str, object]:
    query_tokens = {token for token in query.lower().split() if token}
    doc_markdown = str(docs_context.get("injection_markdown", "")).lower()
    docs_support = bool(query_tokens and any(token in doc_markdown for token in query_tokens)) or bool(docs_context.get("selected_doc_ids"))
    memory_support = bool(
        query_tokens
        and any(any(token in str(record.get("summary", "")).lower() for token in query_tokens) for record in memory_records)
    ) or bool(memory_records)
    return {
        "query": query,
        "docs_support": docs_support,
        "memory_support": memory_support,
        "combined_support": docs_support and memory_support,
        "support_gap": not docs_support and not memory_support,
    }


def _relevance_scores(query: str, docs_context: dict[str, object], memory_records: list[dict[str, object]]) -> list[float]:
    query_tokens = {token for token in query.lower().split() if token}
    if not query_tokens:
        return [1.0] if docs_context.get("selected_doc_ids") or memory_records else []
    scores: list[float] = []
    doc_markdown = str(docs_context.get("injection_markdown", "")).lower()
    if doc_markdown:
        doc_hits = sum(1 for token in query_tokens if token in doc_markdown)
        scores.append(doc_hits / len(query_tokens))
    for record in memory_records:
        summary = str(record.get("summary", "")).lower()
        if not summary:
            continue
        hits = sum(1 for token in query_tokens if token in summary)
        scores.append(hits / len(query_tokens))
    return scores


def _generated_approval_items(sessions: list[PlanSession]) -> list[ApprovalItem]:
    items: list[ApprovalItem] = []
    for session in sessions:
        payload = session.to_dict()
        summary = get_governance_status(payload)
        if session.status in {"blocked", "awaiting_human", "awaiting_human_confirmation"}:
            reason = str(summary.get("primary_reason") or summary.get("block_detail") or f"Session {session.status} needs human decision.")
            items.append(
                _approval_item(
                    session=session,
                    reason=reason,
                    reason_code="awaiting_human_decision"
                    if session.status in {"awaiting_human", "awaiting_human_confirmation"}
                    else "blocked_session",
                    scope="session",
                    scope_id=session.id,
                    recommended_action=str(summary.get("primary_action") or "human_decision"),
                    evidence_refs=[f"plans/{session.id}/session.json"],
                )
            )
        compliance = session.compliance if isinstance(session.compliance, dict) else {}
        if compliance.get("blocking"):
            for reason in compliance.get("blocking_reasons", []) or ["compliance blocking"]:
                items.append(
                    _approval_item(
                        session=session,
                        reason=f"Compliance blocking: {reason}",
                        reason_code="compliance_blocking",
                        scope="compliance",
                        scope_id=session.id,
                        recommended_action="inspect_compliance",
                        evidence_refs=["team check-compliance", f"plans/{session.id}/session.json"],
                    )
                )
        if isinstance(session.decision_verdict, object) and session.decision_verdict:
            provider_runtime = session.decision_verdict.selected_provider_runtime
            for key, value in provider_runtime.items():
                if "fallback_from" in key and value:
                    items.append(
                        _approval_item(
                            session=session,
                            reason=f"Provider fallback observed: {key}={value}",
                            reason_code="provider_fallback",
                            scope="provider_fallback",
                            scope_id=session.id,
                            recommended_action="inspect_provider_fallback",
                            evidence_refs=[f"plans/{session.id}/verdict.json"],
                        )
                    )
    return items


def _approval_item(
    *,
    session: PlanSession,
    reason: str,
    reason_code: ApprovalReasonCode,
    scope: str,
    scope_id: str,
    recommended_action: str,
    evidence_refs: list[str],
) -> ApprovalItem:
    return ApprovalItem(
        id=_stable_id("approval", session.id, scope, reason),
        status="pending",
        reason_code=reason_code,
        reason=reason,
        scope=scope,
        scope_id=scope_id,
        recommended_action=recommended_action,
        session_id=session.id,
        run_id=session.resume.linked_execution_run_id,
        plan_ref=f"plans/{session.id}/session.json",
        topology_ref=f"topology:{session.id}",
        run_ref=f"runs/{session.resume.linked_execution_run_id}.json" if session.resume.linked_execution_run_id else None,
        evidence_ref=evidence_refs[0] if evidence_refs else None,
        memory_candidate_ref=f"memory-candidate:{session.id}:{scope}",
        evidence_refs=evidence_refs,
    )


def _gate_evidence_summary(
    project_root: Path,
    compliance: dict[str, object],
    evidence_state: dict[str, object],
) -> dict[str, object]:
    gates = [
        {
            "name": "targeted_tests",
            "command": "phase-specific pytest slice",
            "cwd": str(project_root),
            "exit_code": None,
            "duration_seconds": None,
            "summary": "recorded per implementation phase",
            "artifact_path": None,
            "status": "planned",
        },
        {
            "name": "full_tests",
            "command": "pytest",
            "cwd": str(project_root),
            "exit_code": None,
            "duration_seconds": None,
            "summary": "reserved for final convergence",
            "artifact_path": None,
            "status": "planned",
        },
        {
            "name": "compliance",
            "command": "env PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance",
            "cwd": str(project_root),
            "exit_code": 1 if bool(compliance.get("blocking", False)) else 0,
            "duration_seconds": None,
            "summary": "blocked" if bool(compliance.get("blocking", False)) else "passed or warning-only",
            "artifact_path": None,
            "status": "failed" if bool(compliance.get("blocking", False)) else "passed",
        },
        {
            "name": "evidence_report",
            "command": "python -m agent_orchestrator.cli evidence report --output docs/process/v1x-evidence-report.md",
            "cwd": str(project_root),
            "exit_code": 0 if bool(evidence_state.get("benchmark_report_present", False)) else None,
            "duration_seconds": None,
            "summary": "local markdown evidence report present"
            if bool(evidence_state.get("benchmark_report_present", False))
            else "local markdown evidence report missing",
            "artifact_path": "docs/process/v1x-evidence-report.md",
            "status": "passed" if bool(evidence_state.get("benchmark_report_present", False)) else "missing",
        },
    ]
    return {
        "format": "agent_orchestrator.gate_evidence.v1",
        "log_policy": "large logs stay in artifact_path; setup and release readiness show summaries only",
        "gates": gates,
        "latest": gates[-1],
    }
