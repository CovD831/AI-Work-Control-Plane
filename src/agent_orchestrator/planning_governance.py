"""Governance snapshot helpers derived from planning-session state."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_orchestrator.planning import PlanSession

from agent_orchestrator.planning_support import build_session_guidance


def build_governance_snapshot(session: "PlanSession") -> dict[str, Any]:
    """Build a governance-facing snapshot from a control-plane session.

    This is intentionally a narrow, governance-only view. Prefer `governance_status`
    for new consumers; keep `status_summary` only as a compatibility alias.
    """

    governance_status = _governance_status_summary(session)
    return {
        "schema_version": "1.0",
        "session_guidance": build_session_guidance(session).to_dict(),
        "governance_status": governance_status,
        # Compatibility alias for older consumers; prefer `governance_status`.
        "status_summary": governance_status,
        "compliance": session.compliance if isinstance(session.compliance, dict) else {},
        "decision_verdict": session.decision_verdict.to_dict() if session.decision_verdict else None,
        "approved_plan": session.approved_plan,
    }


def get_governance_status(payload: dict[str, Any]) -> dict[str, Any]:
    governance_snapshot = payload.get("governance_snapshot", {})
    if isinstance(governance_snapshot, dict):
        governance_status = governance_snapshot.get("governance_status", {})
        if isinstance(governance_status, dict):
            return governance_status
    return {}


def _governance_status_summary(session: "PlanSession") -> dict[str, Any]:
    guidance = build_session_guidance(session)
    from agent_orchestrator.planning import (
        _approval_state_for_session,
        _runtime_health_for_session,
        _session_execution_context_policy,
        _usage_cost_placeholder,
    )

    return {
        "phase": session.resume.current_phase,
        "status": session.status,
        "gate_verdict": session.gate_verdict,
        "approved_plan_ready": bool(session.approved_plan),
        "execution_run_id": session.resume.linked_execution_run_id,
        "primary_action": guidance.primary_action,
        "primary_reason": guidance.primary_reason,
        "resume_action": guidance.resume_action,
        "resume_reason": guidance.resume_reason,
        "block_source": guidance.block_source,
        "block_detail": guidance.block_detail,
        "recommended_commands": guidance.recommended_commands,
        "recovery_actions": guidance.recovery_actions,
        "approval_state": _approval_state_for_session(session, guidance),
        "runtime_health": _runtime_health_for_session(session),
        "usage_cost": _usage_cost_placeholder(),
        "execution_context_policy": _session_execution_context_policy(session),
    }
