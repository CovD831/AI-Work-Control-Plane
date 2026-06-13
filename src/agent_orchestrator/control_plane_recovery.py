"""Recovery timeline and recommendation builders for the control plane."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, pathlib
# RESPONSIBILITY: Build read-only recovery timelines and operator recovery recommendations.
# MODULE: decision_core
# ---

from pathlib import Path

from agent_orchestrator.control_plane_artifacts import artifact_ref as _artifact_ref
from agent_orchestrator.control_plane_artifacts import resolve_root as _resolve_root
from agent_orchestrator.control_plane_artifacts import stable_id as _stable_id
from agent_orchestrator.control_plane_constants import CONTROL_PLANE_FORMATS, RECOVERY_TIMELINE_STATUSES
from agent_orchestrator.jobs import now_iso
from agent_orchestrator.planning import PlanSession
from agent_orchestrator.planning_governance import get_governance_status


def build_recovery_timeline(
    project_root: Path | str = ".",
    *,
    plans_root: Path | str = ".agent_orchestrator/plans",
    runs_root: Path | str = ".agent_orchestrator/runs",
    jobs_root: Path | str = ".agent_orchestrator/jobs",
    approvals_root: Path | str = ".agent_orchestrator/approvals",
    sessions: list[PlanSession] | None = None,
    compliance: dict[str, object] | None = None,
) -> dict[str, object]:
    from agent_orchestrator.control_plane import (
        WorkspaceIndexStore,
        _read_plan_sessions,
        build_approval_queue,
        build_evidence_bundle,
        build_run_ledger,
    )

    root = Path(project_root)
    plans_path = _resolve_root(root, plans_root)
    runs_path = _resolve_root(root, runs_root)
    jobs_path = _resolve_root(root, jobs_root)
    approvals_path = _resolve_root(root, approvals_root)
    loaded_sessions = sessions if sessions is not None else _read_plan_sessions(plans_path)
    approvals = build_approval_queue(root, plans_root=plans_path, approvals_root=approvals_path, sessions=loaded_sessions)
    run_ledger = build_run_ledger(
        root,
        plans_root=plans_path,
        runs_root=runs_path,
        jobs_root=jobs_path,
        approvals_root=approvals_path,
        sessions=loaded_sessions,
    )
    evidence_bundle = build_evidence_bundle(root, compliance=compliance)
    entries: list[dict[str, object]] = []
    approval_items = approvals.get("items", []) if isinstance(approvals.get("items"), list) else []
    for session in loaded_sessions:
        entries.extend(_recovery_timeline_session_entries(session, approval_items, evidence_bundle))
    for entry in run_ledger.get("entries", []) if isinstance(run_ledger.get("entries"), list) else []:
        if isinstance(entry, dict):
            timeline_entry = _recovery_timeline_ledger_entry(entry)
            if timeline_entry:
                entries.append(timeline_entry)
    status_counts: dict[str, int] = {}
    for entry in entries:
        status = str(entry.get("status") or "interrupted")
        status_counts[status] = status_counts.get(status, 0) + 1
    current = _current_recovery_status(entries)
    payload = {
        "format": CONTROL_PLANE_FORMATS["recovery_timeline"],
        "project_root": str(root.resolve()),
        "status_catalog": list(RECOVERY_TIMELINE_STATUSES),
        "entries": entries,
        "summary": {
            "entry_count": len(entries),
            "status_counts": status_counts,
            "current_status": current,
            "blocking_summary": _recovery_blocking_summary(entries),
            "resume_hint": _recovery_resume_hint(entries),
            "last_checkpoint": _recovery_last_checkpoint(entries),
        },
        "source_refs": {
            "run_ledger": _artifact_ref(run_ledger),
            "approval_queue": _artifact_ref(approvals),
            "evidence_bundle": _artifact_ref(evidence_bundle),
        },
        "read_only": True,
        "created_at": now_iso(),
    }
    WorkspaceIndexStore(root / ".agent_orchestrator" / "workspace").record_artifact("recovery_timeline", payload)
    return payload


def build_recovery_recommendation(
    session: PlanSession,
    *,
    recovery_timeline: dict[str, object] | None = None,
    runtime_event_stream: dict[str, object] | None = None,
    approval_queue: dict[str, object] | None = None,
    evidence_bundle: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = session.to_dict()
    summary = get_governance_status(payload)
    timeline_summary = (
        recovery_timeline.get("summary", {})
        if isinstance(recovery_timeline, dict) and isinstance(recovery_timeline.get("summary"), dict)
        else summary.get("recovery_timeline", {})
        if isinstance(summary.get("recovery_timeline"), dict)
        else {}
    )
    blocking_reasons = list(summary.get("blocking_reasons", [])) if isinstance(summary.get("blocking_reasons"), list) else []
    current_blocking_reason = (
        blocking_reasons[0]
        if blocking_reasons
        else str(summary.get("primary_reason") or summary.get("resume_reason") or "inspect current control-plane state")
    )
    recommended_commands = (
        [str(command) for command in summary.get("recommended_commands", [])]
        if isinstance(summary.get("recommended_commands"), list)
        else []
    )
    safest_command = recommended_commands[0] if recommended_commands else _recovery_default_command(session, summary)
    compliance = session.compliance if isinstance(session.compliance, dict) else {}
    approval_state = summary.get("approval_state", {}) if isinstance(summary.get("approval_state"), dict) else {}
    current_status = str(timeline_summary.get("current_status") or summary.get("primary_action") or session.status)
    required = _recovery_required_approval_or_evidence(
        current_status,
        session_status=session.status,
        compliance=compliance,
        approval_state=approval_state,
        evidence_bundle=evidence_bundle,
    )
    artifact_refs = [f"plans/{session.id}/session.json", "agent_orchestrator.recovery_timeline.v1"]
    if runtime_event_stream is not None:
        artifact_refs.append("agent_orchestrator.runtime_event_stream.v1")
    if approval_queue is not None:
        artifact_refs.append("agent_orchestrator.approval_queue.v1")
    if evidence_bundle is not None:
        artifact_refs.append("agent_orchestrator.evidence_bundle.v1")
    compliance_first = bool(compliance.get("blocking")) or current_status == "compliance_blocked"
    human_required = bool(approval_state.get("human_required")) or session.status in {
        "awaiting_human",
        "awaiting_human_confirmation",
    } or current_status in {"awaiting_human", "approval_blocked", "awaiting_human_confirmation"}
    may_resume = (
        not compliance_first
        and not human_required
        and current_status
        not in {"runtime_failed", "provider_degraded", "evidence_blocked", "interrupted"}
    )
    branch_candidates = _recovery_branch_candidates(
        session=session,
        current_status=current_status,
        summary=summary,
        compliance_first=compliance_first,
        human_required=human_required,
        safest_command=safest_command,
        required=required,
    )
    return {
        "format": "agent_orchestrator.recovery_recommendation.v1",
        "session_id": session.id,
        "current_status": current_status,
        "current_blocking_reason": current_blocking_reason,
        "safest_next_operator_command": safest_command,
        "required_approval_or_evidence": required,
        "recoverable_artifact_refs": artifact_refs,
        "may_resume_execution": may_resume,
        "human_decision_required": human_required,
        "compliance_must_be_fixed_first": compliance_first,
        "recovery_search": _recovery_search_summary(branch_candidates),
        "branch_candidates": branch_candidates,
        "read_only": True,
        "mutation_policy": "recommendation only; execution remains gated by approved-plan runtime",
        "created_at": now_iso(),
    }


def _recovery_branch_candidates(
    *,
    session: PlanSession,
    current_status: str,
    summary: dict[str, object],
    compliance_first: bool,
    human_required: bool,
    safest_command: str,
    required: dict[str, object],
) -> list[dict[str, object]]:
    recommended_commands = (
        [str(command) for command in summary.get("recommended_commands", [])]
        if isinstance(summary.get("recommended_commands"), list)
        else []
    )
    primary_action = str(summary.get("resume_action") or summary.get("primary_action") or "inspect_session")
    candidates: list[dict[str, object]] = []

    def add_candidate(
        branch_id: str,
        *,
        command: str,
        score: int,
        rationale: list[str],
        branch_type: str,
        requirements: list[str] | None = None,
    ) -> None:
        candidates.append(
            {
                "branch_id": branch_id,
                "branch_type": branch_type,
                "command": command,
                "score": score,
                "selected": command == safest_command,
                "rationale": rationale,
                "requirements": list(requirements or []),
            }
        )

    add_candidate(
        "primary_recovery_path",
        command=safest_command,
        score=10,
        rationale=[f"Current control-plane guidance prefers `{primary_action}` for status `{current_status}`."],
        branch_type="primary",
        requirements=_required_labels(required),
    )
    if compliance_first:
        add_candidate(
            "compliance_first",
            command=_command_for_action(session, "inspect_compliance"),
            score=9,
            rationale=["Compliance is blocking, so recovery must start with compliance inspection and repair."],
            branch_type="compliance",
            requirements=["compliance_blocking"],
        )
    if human_required:
        add_candidate(
            "human_decision",
            command=_command_for_action(session, "human_decision"),
            score=8,
            rationale=["Human approval is required before execution can safely resume."],
            branch_type="approval",
            requirements=["human_decision"],
        )
    if current_status in {"runtime_failed", "provider_degraded", "recovery_ready"}:
        add_candidate(
            "inspect_execution",
            command=_command_for_action(session, "inspect_execution"),
            score=7,
            rationale=["Execution-side evidence may explain the blocker more directly than a plan-only inspection."],
            branch_type="execution",
            requirements=[],
        )
    if primary_action not in {"retry_review", "retry_adversarial_review"} and current_status in {"runtime_failed", "interrupted", "recovery_ready"}:
        add_candidate(
            "inspect_blockers",
            command=_command_for_action(session, "inspect_blockers"),
            score=6,
            rationale=["A blocker summary can narrow the safest re-entry path before retrying work."],
            branch_type="inspection",
            requirements=[],
        )
    for command in recommended_commands[1:3]:
        add_candidate(
            f"alternative:{command}",
            command=command,
            score=5,
            rationale=["This command is a secondary recovery option surfaced by the current session guidance."],
            branch_type="alternative",
            requirements=[],
        )
    ranked = sorted(candidates, key=lambda item: int(item.get("score", 0)), reverse=True)
    deduped: list[dict[str, object]] = []
    seen_commands: set[str] = set()
    for candidate in ranked:
        command = str(candidate.get("command"))
        if command in seen_commands:
            continue
        seen_commands.add(command)
        deduped.append(candidate)
    if deduped and not any(candidate.get("selected") for candidate in deduped):
        deduped[0]["selected"] = True
    return deduped


def _recovery_search_summary(candidates: list[dict[str, object]]) -> dict[str, object]:
    if not candidates:
        return {
            "selected_branch": None,
            "runner_up_branch": None,
            "candidate_count": 0,
            "disagreement_level": "none",
        }
    ranked = sorted(candidates, key=lambda item: int(item.get("score", 0)), reverse=True)
    selected = next((item for item in ranked if item.get("selected")), ranked[0])
    runner_up = next((item for item in ranked if item is not selected), None)
    selected_score = int(selected.get("score", 0))
    runner_up_score = int(runner_up.get("score", 0)) if runner_up is not None else 0
    delta = selected_score - runner_up_score
    disagreement = "high" if delta <= 1 else "medium" if delta <= 3 else "low"
    return {
        "selected_branch": selected.get("branch_id"),
        "selected_command": selected.get("command"),
        "runner_up_branch": runner_up.get("branch_id") if runner_up is not None else None,
        "runner_up_command": runner_up.get("command") if runner_up is not None else None,
        "candidate_count": len(candidates),
        "disagreement_level": disagreement,
    }


def _required_labels(required: dict[str, object]) -> list[str]:
    labels: list[str] = []
    if bool(required.get("approval")):
        labels.append("approval")
    if bool(required.get("evidence")):
        labels.append("evidence")
    if bool(required.get("compliance")):
        labels.append("compliance")
    return labels


def _recovery_timeline_session_entries(
    session: PlanSession,
    approval_items: list[object],
    evidence_bundle: dict[str, object],
) -> list[dict[str, object]]:
    payload = session.to_dict()
    summary = get_governance_status(payload)
    entries = [
        {
            "id": f"timeline:{session.id}:started",
            "status": "started",
            "kind": "plan_session",
            "session_id": session.id,
            "message": "Plan session exists in the control plane.",
            "artifact_refs": [f"plans/{session.id}/session.json"],
            "created_at": now_iso(),
        },
        {
            "id": f"timeline:{session.id}:checkpointed",
            "status": "checkpointed",
            "kind": "plan_session",
            "session_id": session.id,
            "message": f"Checkpoint at phase {session.resume.current_phase}.",
            "artifact_refs": [f"plans/{session.id}/session.json"],
            "created_at": now_iso(),
            "checkpoint": {
                "phase": session.resume.current_phase,
                "pending_role": session.resume.pending_role,
                "linked_execution_run_id": session.resume.linked_execution_run_id,
            },
        },
    ]
    current_status = _recovery_status_for_session(session, summary, approval_items, evidence_bundle)
    entries.append(
        {
            "id": f"timeline:{session.id}:current",
            "status": current_status,
            "kind": "recovery_state",
            "session_id": session.id,
            "message": _recovery_message_for_status(current_status, summary),
            "resume_action": summary.get("resume_action") or summary.get("primary_action"),
            "resume_reason": summary.get("resume_reason") or summary.get("primary_reason"),
            "blocking_reasons": list(summary.get("blocking_reasons", []))
            if isinstance(summary.get("blocking_reasons"), list)
            else [],
            "artifact_refs": [f"plans/{session.id}/session.json", "agent_orchestrator.run_ledger.v1"],
            "created_at": now_iso(),
        }
    )
    return entries


def _recovery_status_for_session(
    session: PlanSession,
    summary: dict[str, object],
    approval_items: list[object],
    evidence_bundle: dict[str, object],
) -> str:
    compliance = session.compliance if isinstance(session.compliance, dict) else {}
    if compliance.get("blocking"):
        return "compliance_blocked"
    if session.status in {"awaiting_human", "awaiting_human_confirmation"}:
        return "awaiting_human"
    if any(
        isinstance(item, dict) and item.get("session_id") == session.id and item.get("status") == "pending"
        for item in approval_items
    ):
        return "approval_blocked"
    if evidence_bundle.get("status") == "blocked":
        return "evidence_blocked"
    if _session_has_provider_fallback(session):
        return "provider_degraded"
    delegated_jobs = summary.get("delegated_jobs", []) if isinstance(summary.get("delegated_jobs"), list) else []
    if any(isinstance(job, dict) and job.get("status") == "failed" for job in delegated_jobs):
        return "runtime_failed"
    if session.status in {"accepted", "completed"}:
        return "completed"
    if summary.get("resume_action") or summary.get("recovery_actions"):
        return "recovery_ready"
    return "interrupted"


def _recovery_timeline_ledger_entry(entry: dict[str, object]) -> dict[str, object] | None:
    status_map = {
        "completed": "completed",
        "failed": "runtime_failed",
        "interrupted": "interrupted",
        "awaiting_human": "awaiting_human",
        "compliance_blocking": "compliance_blocked",
        "provider_fallback": "provider_degraded",
        "recovery_ready": "recovery_ready",
    }
    status = status_map.get(str(entry.get("status") or ""))
    if not status:
        return None
    entry_id = str(entry.get("id") or _stable_id("ledger", str(entry)))
    return {
        "id": f"timeline:{entry_id}",
        "status": status,
        "kind": str(entry.get("kind") or "run_ledger_entry"),
        "session_id": entry.get("session_id"),
        "run_id": entry.get("run_id"),
        "job_id": entry.get("job_id"),
        "message": f"Run ledger entry {entry_id} reports {status}.",
        "resume_action": entry.get("resume_action") or entry.get("primary_action"),
        "resume_reason": entry.get("resume_reason"),
        "artifact_refs": list(entry.get("evidence_refs", [])) if isinstance(entry.get("evidence_refs"), list) else [],
        "created_at": now_iso(),
    }


def _current_recovery_status(entries: list[dict[str, object]]) -> str:
    priority = [
        "compliance_blocked",
        "approval_blocked",
        "awaiting_human",
        "runtime_failed",
        "provider_degraded",
        "evidence_blocked",
        "recovery_ready",
        "interrupted",
        "checkpointed",
        "completed",
        "started",
    ]
    statuses = {str(entry.get("status")) for entry in entries}
    for status in priority:
        if status in statuses:
            return status
    return "interrupted"


def _recovery_blocking_summary(entries: list[dict[str, object]]) -> dict[str, object]:
    blocking_statuses = {
        "awaiting_human",
        "approval_blocked",
        "evidence_blocked",
        "compliance_blocked",
        "provider_degraded",
        "runtime_failed",
        "interrupted",
    }
    blockers = [entry for entry in entries if str(entry.get("status")) in blocking_statuses]
    return {
        "blocking": bool(blockers),
        "count": len(blockers),
        "statuses": sorted({str(entry.get("status")) for entry in blockers}),
        "reasons": [
            str(reason)
            for entry in blockers
            for reason in (
                entry.get("blocking_reasons", []) if isinstance(entry.get("blocking_reasons"), list) else []
            )
        ],
    }


def _recovery_resume_hint(entries: list[dict[str, object]]) -> str:
    for entry in reversed(entries):
        action = entry.get("resume_action")
        if action:
            return str(action)
    current = _current_recovery_status(entries)
    defaults = {
        "compliance_blocked": "inspect_compliance",
        "approval_blocked": "resolve_approval",
        "awaiting_human": "human_decision",
        "runtime_failed": "inspect_blockers",
        "provider_degraded": "inspect_runtime_health",
        "evidence_blocked": "inspect_evidence",
        "recovery_ready": "team next",
        "completed": "inspect_execution",
    }
    return defaults.get(current, "team summary")


def _recovery_last_checkpoint(entries: list[dict[str, object]]) -> dict[str, object] | None:
    checkpoints = [entry for entry in entries if entry.get("status") == "checkpointed"]
    return checkpoints[-1] if checkpoints else None


def _recovery_message_for_status(status: str, summary: dict[str, object]) -> str:
    reason = summary.get("primary_reason") or summary.get("resume_reason")
    if reason:
        return str(reason)
    messages = {
        "awaiting_human": "Human decision is required before work can continue.",
        "approval_blocked": "Pending approval blocks the next execution step.",
        "evidence_blocked": "Evidence gates are blocking recovery.",
        "compliance_blocked": "Compliance must be fixed before resuming.",
        "provider_degraded": "Provider/runtime fallback or degraded capability is active.",
        "runtime_failed": "Runtime or delegated job failure requires inspection.",
        "interrupted": "Work is interrupted and needs operator inspection.",
        "recovery_ready": "Recovery path is available.",
        "completed": "Work is completed.",
    }
    return messages.get(status, "Recovery timeline checkpoint recorded.")


def _recovery_default_command(session: PlanSession, summary: dict[str, object]) -> str:
    action = str(summary.get("resume_action") or summary.get("primary_action") or "summary")
    commands = {
        "revise": f"python -m agent_orchestrator.cli team revise {session.id} --summary \"close required gaps\"",
        "approve": f"python -m agent_orchestrator.cli team approve {session.id}",
        "execute": f"python -m agent_orchestrator.cli team execute {session.id}",
        "human_decision": f"python -m agent_orchestrator.cli team summary {session.id}",
        "inspect_compliance": "python -m agent_orchestrator.cli team check-compliance",
        "inspect_blockers": f"python -m agent_orchestrator.cli team inspect-blockers {session.id}",
        "inspect_execution": f"python -m agent_orchestrator.cli team inspect-execution {session.id}",
        "retry_review": f"python -m agent_orchestrator.cli team retry-review {session.id}",
        "retry_adversarial_review": f"python -m agent_orchestrator.cli team retry-adversarial-review {session.id}",
    }
    return commands.get(action, f"python -m agent_orchestrator.cli team summary {session.id}")


def _command_for_action(session: PlanSession, action: str) -> str:
    return _recovery_default_command(session, {"primary_action": action})


def _recovery_required_approval_or_evidence(
    current_status: str,
    *,
    session_status: str,
    compliance: dict[str, object],
    approval_state: dict[str, object],
    evidence_bundle: dict[str, object] | None,
) -> dict[str, object]:
    evidence_status = evidence_bundle.get("status") if isinstance(evidence_bundle, dict) else None
    return {
        "approval_required": bool(approval_state.get("human_required"))
        or session_status in {"awaiting_human", "awaiting_human_confirmation"}
        or current_status in {"awaiting_human", "approval_blocked", "awaiting_human_confirmation"},
        "evidence_required": current_status == "evidence_blocked" or evidence_status == "blocked",
        "compliance_required": bool(compliance.get("blocking")) or current_status == "compliance_blocked",
        "reason": current_status,
    }


def _session_has_provider_fallback(session: PlanSession) -> bool:
    if not session.decision_verdict:
        return False
    provider_runtime = session.decision_verdict.selected_provider_runtime
    return any("fallback" in str(key) and bool(value) for key, value in provider_runtime.items())
