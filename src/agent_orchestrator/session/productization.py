"""Shared session productization helpers for operator-visible continuity surfaces."""
from __future__ import annotations


def _summary_dict(summary: dict[str, object], key: str) -> dict[str, object]:
    value = summary.get(key, {})
    return value if isinstance(value, dict) else {}


def _summary_list(summary: dict[str, object], key: str) -> list[object]:
    value = summary.get(key, [])
    return value if isinstance(value, list) else []


def _workflow_continuity_surface(continuity_contract: dict[str, object], surface: dict[str, object]) -> dict[str, object]:
    workflow_continuity = _summary_dict(continuity_contract, "workflow_continuity")
    if workflow_continuity:
        return workflow_continuity
    return _summary_dict(surface, "workflow_continuity")


def derive_session_productization_surface(continuity_contract: dict[str, object]) -> dict[str, object]:
    """Return a stable session productization surface from a continuity contract.

    The runtime can emit a first-class `session_productization_surface.v1`.
    Older or compatibility-only continuity contracts may only expose the
    underlying continuity fields. This helper derives a compat surface while
    preserving any richer first-class surface when present.
    """

    if not isinstance(continuity_contract, dict):
        return {}
    surface = _summary_dict(continuity_contract, "session_productization_surface")
    continuity_snapshot = _summary_dict(continuity_contract, "continuity_snapshot")
    latest_recovery_hint = continuity_contract.get("latest_recovery_hint")
    operator_control = _summary_dict(continuity_contract, "operator_control")
    autonomy_posture = _summary_dict(continuity_contract, "autonomy_posture")
    continuity_pressure = _summary_dict(continuity_contract, "continuity_pressure")
    workflow_continuity = _workflow_continuity_surface(continuity_contract, surface)
    workflow_resume_alignment = _summary_dict(workflow_continuity, "resume_alignment")
    workflow_recovery_alignment = _summary_dict(workflow_continuity, "recovery_alignment")
    planner_governed_alternatives = _summary_list(operator_control, "planner_governed_alternatives")
    approval_boundary_active = bool(
        operator_control.get("approval_pause_state")
        or operator_control.get("resume_expectation") == "approval_pause"
        or operator_control.get("next_recommended_action")
        in {"approval_pause", "human_review", "await_approval", "human_decision"}
    )
    continuity_status = (
        "governed_approval_boundary"
        if continuity_contract.get("resume_supported") and approval_boundary_active
        else "ready"
        if continuity_contract.get("resume_supported")
        else "limited"
    )
    derived_operator_continuity = {
        "latest_recovery_hint": latest_recovery_hint,
        "next_recommended_action": operator_control.get("next_recommended_action"),
        "runbook_recovery_lane": operator_control.get("runbook_recovery_lane"),
        "approval_pause_state": operator_control.get("approval_pause_state"),
        "approval_boundary_active": approval_boundary_active,
        "clarify_pause_state": operator_control.get("clarify_pause_state"),
        "resume_expectation": operator_control.get("resume_expectation"),
        "resume_posture": operator_control.get("resume_posture"),
        "planner_governed_alternatives": [
            dict(item) for item in planner_governed_alternatives if isinstance(item, dict)
        ],
        "workflow_active_stage": workflow_continuity.get("active_stage"),
        "selected_workflow_stages": _summary_list(workflow_continuity, "selected_workflow_stages"),
        "workflow_projection_ready": workflow_continuity.get("workflow_projection_ready"),
    }
    derived_surface = {
        "format": "agent_orchestrator.session_productization_surface.compat.v1",
        "resume_supported": continuity_contract.get("resume_supported"),
        "resume_kind": continuity_contract.get("resume_kind"),
        "continuity_status": continuity_status,
        "compaction_stage": continuity_contract.get("compaction_stage"),
        "runtime_duration_seconds": continuity_contract.get("runtime_duration_seconds"),
        "usage_cost_measurement_status": continuity_contract.get("usage_cost_measurement_status"),
        "runtime_cost_provenance": _summary_dict(continuity_contract, "runtime_cost_provenance"),
        "continuity_snapshot": continuity_snapshot,
        "continuity_pressure": continuity_pressure,
        "workflow_continuity": workflow_continuity,
        "operator_continuity": derived_operator_continuity,
        "continuity_readiness": {
            "resume_ready": bool(continuity_contract.get("resume_supported")),
            "runtime_cost_ready": continuity_contract.get("runtime_duration_seconds") is not None
            and bool(continuity_contract.get("usage_cost_measurement_status")),
            "compaction_ready": bool(continuity_contract.get("compaction_stage")),
            "pressure_visible": (
                bool(continuity_pressure.get("format"))
                or (
                    continuity_contract.get("runtime_duration_seconds") is not None
                    and bool(continuity_contract.get("usage_cost_measurement_status"))
                )
            ),
            "recovery_ready": bool(latest_recovery_hint),
            "approval_boundary_visible": approval_boundary_active,
            "governed_pause_resume_ready": bool(continuity_contract.get("resume_supported")) and approval_boundary_active,
            "workflow_resume_ready": bool(workflow_resume_alignment.get("aligned")),
            "workflow_projection_visible": bool(workflow_continuity.get("tool_workflow_plan"))
            or workflow_continuity.get("workflow_projection_ready") is True,
            "workflow_recovery_aligned": (
                workflow_recovery_alignment.get("aligned")
                if "aligned" in workflow_recovery_alignment
                else bool(workflow_continuity)
            ),
        },
        "operator_posture_digest": {
            "format": "agent_orchestrator.session_operator_posture_digest.v1",
            "continuity_status": continuity_status,
            "compaction_stage": continuity_contract.get("compaction_stage"),
            "compaction_pressure": continuity_pressure.get("compaction_pressure"),
            "context_pressure": continuity_pressure.get("context_pressure"),
            "summarization_ready": continuity_pressure.get("summarization_ready"),
            "runtime_duration_seconds": continuity_contract.get("runtime_duration_seconds"),
            "usage_cost_measurement_status": continuity_contract.get("usage_cost_measurement_status"),
            "runtime_cost_provenance": _summary_dict(continuity_contract, "runtime_cost_provenance"),
            "next_recommended_action": derived_operator_continuity.get("next_recommended_action"),
            "runbook_recovery_lane": derived_operator_continuity.get("runbook_recovery_lane"),
            "resume_expectation": derived_operator_continuity.get("resume_expectation"),
            "resume_posture": derived_operator_continuity.get("resume_posture"),
            "approval_pause_state": derived_operator_continuity.get("approval_pause_state"),
            "approval_boundary_active": approval_boundary_active,
            "clarify_pause_state": derived_operator_continuity.get("clarify_pause_state"),
            "workflow_active_stage": workflow_continuity.get("active_stage"),
            "selected_workflow_stages": _summary_list(workflow_continuity, "selected_workflow_stages"),
            "workflow_projection_ready": workflow_continuity.get("workflow_projection_ready"),
            "tool_workflow_plan_format": _summary_dict(workflow_continuity, "tool_workflow_plan").get("format"),
            "pause_expected": autonomy_posture.get("pause_expected"),
            "handoff_expected": autonomy_posture.get("handoff_expected"),
            "fallback_expected": autonomy_posture.get("fallback_expected"),
            "latest_recovery_hint": latest_recovery_hint,
            "planner_governed_alternatives": [
                dict(item) for item in planner_governed_alternatives if isinstance(item, dict)
            ],
            "summary": (
                f"continuity_status={continuity_status} "
                f"next_action={derived_operator_continuity.get('next_recommended_action')} "
                f"recovery_lane={derived_operator_continuity.get('runbook_recovery_lane')} "
                f"resume_expectation={derived_operator_continuity.get('resume_expectation')} "
                f"resume_posture={derived_operator_continuity.get('resume_posture')} "
                f"approval_pause={derived_operator_continuity.get('approval_pause_state')} "
                f"approval_boundary_active={approval_boundary_active} "
                f"clarify_pause={derived_operator_continuity.get('clarify_pause_state')} "
                f"workflow_stage={workflow_continuity.get('active_stage')} "
                f"workflow_selected={','.join(str(item) for item in _summary_list(workflow_continuity, 'selected_workflow_stages')) or 'none'} "
                f"workflow_projection_ready={workflow_continuity.get('workflow_projection_ready')} "
                f"pause_expected={autonomy_posture.get('pause_expected')} "
                f"handoff_expected={autonomy_posture.get('handoff_expected')} "
                f"fallback_expected={autonomy_posture.get('fallback_expected')} "
                f"alternatives={','.join(str(item.get('action')) for item in planner_governed_alternatives if isinstance(item, dict) and item.get('action')) or 'none'} "
                f"compaction_stage={continuity_contract.get('compaction_stage')} "
                f"compaction_pressure={continuity_pressure.get('compaction_pressure')} "
                f"context_pressure={continuity_pressure.get('context_pressure')} "
                f"summarization_ready={continuity_pressure.get('summarization_ready')} "
                f"runtime_duration_seconds={continuity_contract.get('runtime_duration_seconds')} "
                f"usage_cost_status={continuity_contract.get('usage_cost_measurement_status')} "
                f"duration_source={_summary_dict(continuity_contract, 'runtime_cost_provenance').get('duration_source')}"
            ),
        },
        "autonomy_posture": autonomy_posture,
        "long_horizon_posture": _summary_dict(continuity_contract, "long_horizon_posture"),
        "program_posture": _summary_dict(continuity_contract, "program_posture"),
        "daily_driver_readiness": _summary_dict(continuity_contract, "daily_driver_readiness"),
        "comparative_benchmark_digest": _summary_dict(continuity_contract, "comparative_benchmark_digest"),
        "shared_evidence_surface": _summary_list(continuity_contract, "shared_evidence_surface"),
    }
    if not surface:
        return derived_surface
    readiness = _summary_dict(surface, "continuity_readiness")
    operator_continuity = _summary_dict(surface, "operator_continuity")
    merged_surface = dict(surface)
    merged_surface["continuity_readiness"] = {
        **derived_surface["continuity_readiness"],
        **readiness,
        "pressure_visible": readiness.get("pressure_visible")
        if "pressure_visible" in readiness
        else derived_surface["continuity_readiness"]["pressure_visible"],
    }
    merged_surface["operator_continuity"] = {
        **derived_surface["operator_continuity"],
        **operator_continuity,
    }
    merged_surface["workflow_continuity"] = {
        **derived_surface["workflow_continuity"],
        **_summary_dict(surface, "workflow_continuity"),
    }
    merged_surface["operator_posture_digest"] = {
        **derived_surface["operator_posture_digest"],
        **_summary_dict(surface, "operator_posture_digest"),
        "summary": (
            _summary_dict(surface, "operator_posture_digest").get("summary")
            or derived_surface["operator_posture_digest"]["summary"]
        ),
    }
    if "continuity_pressure" not in merged_surface:
        merged_surface["continuity_pressure"] = derived_surface["continuity_pressure"]
    if "shared_evidence_surface" not in merged_surface:
        merged_surface["shared_evidence_surface"] = derived_surface["shared_evidence_surface"]
    if "autonomy_posture" not in merged_surface:
        merged_surface["autonomy_posture"] = derived_surface["autonomy_posture"]
    if "comparative_benchmark_digest" not in merged_surface:
        merged_surface["comparative_benchmark_digest"] = derived_surface["comparative_benchmark_digest"]
    return merged_surface
