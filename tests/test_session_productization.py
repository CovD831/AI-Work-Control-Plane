from __future__ import annotations

from agent_orchestrator.control_plane_posture import (
    derive_session_continuity_outline_from_contract,
    derive_session_planner_decision_from_payload,
)
from agent_orchestrator.session import derive_session_productization_surface
from agent_orchestrator.productization_surface import build_shared_productization_surface


def test_derive_session_productization_surface_builds_compat_surface_from_continuity_contract() -> None:
    surface = derive_session_productization_surface(
        {
            "resume_supported": True,
            "resume_kind": "fresh",
            "compaction_stage": "light_compaction",
            "runtime_duration_seconds": 1.25,
            "usage_cost_measurement_status": "placeholder",
            "runtime_cost_provenance": {"source": "runtime_payload"},
            "continuity_snapshot": {
                "format": "agent_orchestrator.session_continuity_snapshot.v1",
            },
            "continuity_pressure": {
                "format": "agent_orchestrator.continuity_pressure.v1",
            },
            "workflow_continuity": {
                "format": "agent_orchestrator.session_workflow_continuity.v1",
                "active_stage": "edit",
                "selected_workflow_stages": ["explore", "edit", "verify"],
                "workflow_projection_ready": True,
                "tool_workflow_plan": {
                    "format": "agent_orchestrator.native_tool_workflow_plan.v1",
                },
                "resume_alignment": {"aligned": True},
                "recovery_alignment": {"aligned": True},
            },
            "operator_control": {
                "next_recommended_action": "inspect_execution",
                "runbook_recovery_lane": "inspect",
                "approval_pause_state": False,
                "clarify_pause_state": False,
                "resume_expectation": "resume_if_same_task",
                "resume_posture": "same_task_resume",
            },
            "autonomy_posture": {
                "pause_expected": False,
                "handoff_expected": False,
                "fallback_expected": False,
            },
            "long_horizon_posture": {
                "resume_ready": True,
            },
            "program_posture": {
                "program_goal": "Ship dashboard",
            },
            "daily_driver_readiness": {
                "session_ready": True,
            },
            "shared_evidence_surface": ["runtime_payload", "workspace_index"],
        }
    )

    assert surface["format"] == "agent_orchestrator.session_productization_surface.compat.v1"
    assert surface["continuity_status"] == "ready"
    assert surface["continuity_readiness"]["resume_ready"] is True
    assert surface["continuity_readiness"]["runtime_cost_ready"] is True
    assert surface["continuity_readiness"]["pressure_visible"] is True
    assert surface["continuity_readiness"]["approval_boundary_visible"] is False
    assert surface["continuity_readiness"]["governed_pause_resume_ready"] is False
    assert surface["continuity_readiness"]["workflow_resume_ready"] is True
    assert surface["continuity_readiness"]["workflow_projection_visible"] is True
    assert surface["continuity_readiness"]["workflow_recovery_aligned"] is True
    assert surface["workflow_continuity"]["active_stage"] == "edit"
    assert surface["operator_continuity"]["resume_expectation"] == "resume_if_same_task"
    assert surface["operator_continuity"]["resume_posture"] == "same_task_resume"
    assert surface["operator_continuity"]["approval_boundary_active"] is False
    assert surface["operator_continuity"]["planner_governed_alternatives"] == []
    assert surface["operator_continuity"]["workflow_active_stage"] == "edit"
    assert surface["operator_continuity"]["selected_workflow_stages"] == ["explore", "edit", "verify"]
    assert surface["operator_posture_digest"]["format"] == "agent_orchestrator.session_operator_posture_digest.v1"
    assert surface["operator_posture_digest"]["next_recommended_action"] == "inspect_execution"
    assert surface["operator_posture_digest"]["runbook_recovery_lane"] == "inspect"
    assert surface["operator_posture_digest"]["resume_expectation"] == "resume_if_same_task"
    assert surface["operator_posture_digest"]["resume_posture"] == "same_task_resume"
    assert surface["operator_posture_digest"]["approval_boundary_active"] is False
    assert surface["operator_posture_digest"]["compaction_stage"] == "light_compaction"
    assert surface["operator_posture_digest"]["planner_governed_alternatives"] == []
    assert surface["operator_posture_digest"]["workflow_active_stage"] == "edit"
    assert surface["operator_posture_digest"]["workflow_projection_ready"] is True
    assert surface["autonomy_posture"]["pause_expected"] is False
    assert surface["shared_evidence_surface"] == ["runtime_payload", "workspace_index"]


def test_derive_session_productization_surface_surfaces_planner_governed_alternatives() -> None:
    surface = derive_session_productization_surface(
        {
            "resume_supported": True,
            "resume_kind": "fresh",
            "compaction_stage": "light_compaction",
            "operator_control": {
                "planner_governed_alternatives": [
                    {"action": "need_human_confirmation", "strategy": "need_human_confirmation"},
                    {"action": "handoff_external", "strategy": "external_handoff"},
                ],
                "next_recommended_action": "inspect_execution",
                "runbook_recovery_lane": "inspect",
                "resume_expectation": "resume_if_same_task",
                "resume_posture": "same_task_resume",
            },
            "continuity_pressure": {"format": "agent_orchestrator.continuity_pressure.v1"},
        }
    )

    assert [item["action"] for item in surface["operator_continuity"]["planner_governed_alternatives"]] == [
        "need_human_confirmation",
        "handoff_external",
    ]
    assert "alternatives=need_human_confirmation,handoff_external" in surface["operator_posture_digest"]["summary"]


def test_derive_session_productization_surface_promotes_governed_approval_boundary_to_continuity_status() -> None:
    surface = derive_session_productization_surface(
        {
            "resume_supported": True,
            "resume_kind": "approval_resume",
            "compaction_stage": "light_compaction",
            "operator_control": {
                "next_recommended_action": "human_review",
                "runbook_recovery_lane": "approval_pause",
                "approval_pause_state": True,
                "clarify_pause_state": False,
                "resume_expectation": "approval_pause",
                "resume_posture": "approval_reentry",
            },
            "continuity_pressure": {"format": "agent_orchestrator.continuity_pressure.v1"},
        }
    )

    assert surface["continuity_status"] == "governed_approval_boundary"
    assert surface["continuity_readiness"]["approval_boundary_visible"] is True
    assert surface["continuity_readiness"]["governed_pause_resume_ready"] is True
    assert surface["operator_continuity"]["approval_boundary_active"] is True
    assert surface["operator_posture_digest"]["approval_boundary_active"] is True
    assert "continuity_status=governed_approval_boundary" in surface["operator_posture_digest"]["summary"]


def test_derive_session_productization_surface_preserves_first_class_surface_and_backfills_missing_fields() -> None:
    surface = derive_session_productization_surface(
        {
            "runtime_duration_seconds": 1.25,
            "usage_cost_measurement_status": "placeholder",
            "session_productization_surface": {
                "format": "agent_orchestrator.session_productization_surface.v1",
                "continuity_status": "ready",
                "continuity_readiness": {
                    "resume_ready": True,
                    "runtime_cost_ready": True,
                    "compaction_ready": True,
                    "recovery_ready": False,
                },
                "operator_continuity": {
                    "next_recommended_action": "inspect_execution",
                },
            },
            "continuity_pressure": {
                "format": "agent_orchestrator.continuity_pressure.v1",
            },
            "shared_evidence_surface": ["runtime_payload"],
        }
    )

    assert surface["format"] == "agent_orchestrator.session_productization_surface.v1"
    assert surface["operator_continuity"]["next_recommended_action"] == "inspect_execution"
    assert surface["continuity_readiness"]["pressure_visible"] is True
    assert surface["operator_posture_digest"]["summary"]
    assert surface["shared_evidence_surface"] == ["runtime_payload"]


def test_derive_session_productization_surface_backfills_workflow_continuity_from_first_class_surface() -> None:
    surface = derive_session_productization_surface(
        {
            "session_productization_surface": {
                "format": "agent_orchestrator.session_productization_surface.v1",
                "workflow_continuity": {
                    "format": "agent_orchestrator.session_workflow_continuity.v1",
                    "active_stage": "verify",
                    "selected_workflow_stages": ["explore", "edit", "verify"],
                    "workflow_projection_ready": True,
                    "resume_alignment": {"aligned": True},
                    "recovery_alignment": {"aligned": True},
                    "tool_workflow_plan": {
                        "format": "agent_orchestrator.native_tool_workflow_plan.v1",
                    },
                },
            }
        }
    )

    assert surface["workflow_continuity"]["active_stage"] == "verify"
    assert surface["continuity_readiness"]["workflow_projection_visible"] is True
    assert surface["operator_posture_digest"]["workflow_active_stage"] == "verify"
    assert "workflow_stage=verify" in surface["operator_posture_digest"]["summary"]


def test_build_shared_productization_surface_includes_runtime_and_adapter_evidence() -> None:
    surface = build_shared_productization_surface(
        session_productization_surface={
            "format": "agent_orchestrator.session_productization_surface.v1",
            "continuity_readiness": {
                "resume_ready": True,
                "runtime_cost_ready": True,
                "compaction_ready": True,
                "pressure_visible": True,
            },
            "operator_continuity": {
                "resume_expectation": "resume_if_same_task",
                "next_recommended_action": "verify",
            },
        },
        native_tool_productization_surface={
            "format": "agent_orchestrator.native_tool_productization_surface.v1",
            "operator_visibility_ready": True,
            "readiness": {
                "bounded_read_search_ready": True,
                "structured_patch_ready": True,
                "verification_ready": True,
            },
        },
        adapter_productization_surface={
            "format": "agent_orchestrator.adapter_productization_surface.v1",
            "surface_status": "same_contract_two_executors_governed",
            "resume_contract_supported": True,
            "governed_recovery_ready": True,
        },
        planner_decision={
            "format": "agent_orchestrator.native_planner_decision.v1",
            "autonomy_posture": {"resume_posture": "same_task_resume"},
        },
        continuity_outline={
            "format": "agent_orchestrator.session_continuity_outline.v1",
            "autonomy_posture": {"resume_posture": "same_task_resume"},
            "resume_expectation": "resume_if_same_task",
        },
        planner_closure_posture={
            "format": "agent_orchestrator.planner_closure_posture.v1",
            "closure_mode": "verify_then_complete",
            "resume_posture": "same_task_resume",
            "next_recommended_action": "verify",
        },
        runtime_cost={
            "duration_seconds": 1.25,
            "usage_cost_measurement_status": "placeholder",
            "runtime_cost_provenance": {"format": "agent_orchestrator.runtime_cost_provenance.v1"},
        },
        native_tool_usage={
            "tool_count": 3,
            "trace_count": 2,
            "recent_tools": ["read", "verify"],
        },
        adapter_capability_surface={
            "format": "agent_orchestrator.adapter_capability_surface.v1",
            "comparability": {"comparison_mode": "same_contract_two_executors"},
        },
        comparative_shared_evidence_surface=["runtime_payload"],
    )

    assert surface["shared_productization_contract_ready"] is True
    assert surface["planner_closure_posture"]["closure_mode"] == "verify_then_complete"
    assert "planner_closure_posture" in surface["shared_evidence_surface"]
    assert surface["runtime_cost"]["duration_seconds"] == 1.25
    assert surface["native_tool_usage"]["tool_count"] == 3
    assert surface["adapter_capability_surface"]["format"] == "agent_orchestrator.adapter_capability_surface.v1"
    assert "runtime_payload" in surface["shared_evidence_surface"]


def test_shared_control_plane_posture_helpers_build_runtime_session_posture_contract() -> None:
    planner_decision = derive_session_planner_decision_from_payload(
        strategy_summary={
            "format": "agent_orchestrator.native_planner_decision.v1",
            "planner_family": "native",
        },
        decision_evidence={
            "selected_strategy": "explore_then_edit",
            "selected_actions": ["explore", "edit", "verify"],
            "selected_owner": "native",
            "decision_candidates": ["explore_then_edit", "direct_edit", "clarify_then_edit"],
            "decision_candidate_evidence": [
                {"strategy": "explore_then_edit", "selected": True, "score": 7, "metadata": {"selected_candidate": True}},
                {"strategy": "direct_edit", "selected": False, "score": 3, "metadata": {"reason": "native_default_edit_path"}},
                {"strategy": "external_handoff", "selected": False, "score": 8, "metadata": {"reason": "risk_exceeds_native_bounded_path"}},
            ],
            "decision_boundary": {
                "task_type": "repo_task",
                "risk_level": "medium",
                "route_task_kind": "direct_fix",
                "requires_human_confirmation": False,
            },
            "planner_reasoning": {
                "primary_action": "explore",
                "candidate_count": 3,
                "native_first": True,
            },
            "planner_independence": {
                "native_first_contract_authoritative": True,
                "legacy_reference_used": False,
            },
            "posture": {
                "pause_expected": False,
                "handoff_expected": False,
                "fallback_expected": False,
            },
            "delegation_contract": {
                "selected_executor": "native",
                "resume_expectation": "resume_if_same_task",
            },
            "autonomy_surface": {
                "primary_action": "explore",
                "decision_mode": "native_first_autonomous",
                "actions": {
                    "explore": {"selected": True},
                    "edit": {"selected": True},
                    "verify": {"selected": True},
                    "handoff": {"selected": False},
                },
            },
            "tool_workflow_plan": {
                "format": "agent_orchestrator.native_tool_workflow_plan.v1",
                "workflow_projection_required": True,
                "workflow_stages": {
                    "explore": {"selected": True, "required_tools": ["repo_map", "search", "read"]},
                    "edit": {"selected": True, "required_tools": ["patch_preview", "structured_patch"]},
                    "verify": {"selected": True, "required_tools": ["verify", "tool_trace"]},
                },
                "daily_driver_path": {"tools": ["repo_map", "search", "read", "patch_preview", "structured_patch", "verify"]},
            },
        },
        operator_control={
            "next_recommended_action": "explore",
            "approval_pause_state": False,
            "clarify_pause_state": False,
        },
    )
    continuity_outline = derive_session_continuity_outline_from_contract(
        continuity_contract={
            "resume_kind": "fresh",
            "compaction_stage": "light_compaction",
            "program_posture": {
                "program_goal": "Ship dashboard",
                "active_milestone": "verify",
                "ready_next_units": ["verify"],
                "blocked_units": [],
            },
            "operator_control": {
                "next_recommended_action": "inspect_execution",
                "approval_pause_state": False,
                "clarify_pause_state": False,
            },
            "delegation_contract": {
                "resume_expectation": "resume_if_same_task",
            },
            "autonomy_posture": {
                "pause_expected": False,
                "handoff_expected": False,
                "fallback_expected": False,
            },
            "session_productization_surface": {
                "autonomy_posture": {
                    "resume_posture": "same_task_resume",
                }
            },
        },
        planner_family="native",
    )

    assert planner_decision["format"] == "agent_orchestrator.session_planner_snapshot.v1"
    assert planner_decision["primary_action"] == "explore"
    assert planner_decision["autonomy_posture"]["approval_pause_state"] is False
    assert planner_decision["delegation_contract"]["resume_expectation"] == "resume_if_same_task"
    assert planner_decision["candidate_count"] == 3
    assert planner_decision["selected_candidate"]["strategy"] == "explore_then_edit"
    assert planner_decision["planner_reasoning"]["native_first"] is True
    assert planner_decision["planner_independence"]["native_first_contract_authoritative"] is True
    assert planner_decision["action_coverage"]["autonomy_selected_actions"] == ["explore", "edit", "verify"]
    assert planner_decision["planner_governed_alternatives"][0]["strategy"] == "external_handoff"
    assert planner_decision["tool_workflow_plan"]["workflow_projection_required"] is True
    assert planner_decision["tool_workflow_plan"]["workflow_stages"]["edit"]["selected"] is True
    assert continuity_outline["format"] == "agent_orchestrator.session_continuity_outline.v1"
    assert continuity_outline["planner_family"] == "native"
    assert continuity_outline["resume_kind"] == "fresh"
    assert continuity_outline["next_recommended_action"] == "inspect_execution"
    assert continuity_outline["resume_expectation"] == "resume_if_same_task"
    assert continuity_outline["autonomy_posture"]["resume_posture"] == "same_task_resume"


def test_build_comparative_session_posture_summary_uses_operator_posture_digest() -> None:
    from agent_orchestrator.productization_surface import build_comparative_session_posture_summary

    summary = build_comparative_session_posture_summary(
        session_productization_surface={
            "format": "agent_orchestrator.session_productization_surface.v1",
            "workflow_continuity": {
                "active_stage": "verify",
                "selected_workflow_stages": ["explore", "edit", "verify"],
                "workflow_projection_ready": True,
            },
            "autonomy_posture": {"resume_posture": "same_task_resume"},
            "operator_continuity": {
                "next_recommended_action": "inspect_execution",
                "runbook_recovery_lane": "inspect",
            },
            "operator_posture_digest": {
                "format": "agent_orchestrator.session_operator_posture_digest.v1",
                "next_recommended_action": "verify",
                "runbook_recovery_lane": "repair_then_verify",
                "resume_expectation": "resume_if_same_task",
                "resume_posture": "same_task_resume",
                "compaction_stage": "light_compaction",
                "compaction_pressure": "fresh_turn",
                "planner_governed_alternatives": [
                    {"action": "clarify_scope"},
                    {"action": "handoff_external"},
                ],
            },
        },
        planner_decision={
            "planner_family": "native",
            "autonomy_posture": {
                "primary_action": "explore",
                "pause_expected": False,
                "handoff_expected": False,
                "fallback_expected": False,
                "clarify_pause_state": False,
                "approval_pause_state": False,
            },
            "delegation_contract": {"resume_expectation": "continue_native"},
        },
        continuity_outline={
            "planner_family": "native",
            "autonomy_posture": {"resume_posture": "same_task_resume"},
            "resume_expectation": "resume_if_same_task",
            "next_recommended_action": "inspect_execution",
        },
    )

    assert summary["resume_expectation"] == "resume_if_same_task"
    assert summary["resume_posture"] == "same_task_resume"
    assert summary["next_recommended_action"] == "verify"
    assert summary["runbook_recovery_lane"] == "repair_then_verify"
    assert summary["workflow_active_stage"] == "verify"
    assert summary["selected_workflow_stages"] == ["explore", "edit", "verify"]
    assert summary["workflow_projection_ready"] is True
    assert summary["compaction_stage"] == "light_compaction"
    assert [item["action"] for item in summary["planner_governed_alternatives"]] == [
        "clarify_scope",
        "handoff_external",
    ]
    assert summary["approval_boundary_active"] is False
    assert "workflow_stage=verify" in summary["summary"]
    assert "alternatives=clarify_scope,handoff_external" in summary["summary"]
    assert summary["compaction_pressure"] == "fresh_turn"


def test_build_comparative_session_continuity_summary_reports_long_horizon_judgment() -> None:
    from agent_orchestrator.productization_surface import build_comparative_session_continuity_summary

    summary = build_comparative_session_continuity_summary(
        session_productization_surface={
            "format": "agent_orchestrator.session_productization_surface.v1",
            "continuity_status": "ready",
            "resume_supported": True,
            "resume_kind": "fresh",
            "compaction_stage": "light_compaction",
            "runtime_duration_seconds": 0.8,
            "usage_cost_measurement_status": "placeholder",
            "runtime_cost_provenance": {"duration_source": "native_tool_trace"},
            "continuity_readiness": {
                "resume_ready": True,
                "runtime_cost_ready": True,
                "compaction_ready": True,
                "pressure_visible": True,
                "recovery_ready": True,
                "workflow_resume_ready": True,
                "workflow_projection_visible": True,
                "workflow_recovery_aligned": True,
            },
            "workflow_continuity": {
                "active_stage": "verify",
                "selected_workflow_stages": ["explore", "edit", "verify"],
                "workflow_projection_ready": True,
            },
            "operator_posture_digest": {
                "resume_posture": "same_task_resume",
                "runbook_recovery_lane": "repair_then_verify",
                "next_recommended_action": "verify",
                "workflow_active_stage": "verify",
                "selected_workflow_stages": ["explore", "edit", "verify"],
                "workflow_projection_ready": True,
                "compaction_pressure": "light_compaction",
                "context_pressure": True,
                "summarization_ready": False,
                "runtime_duration_seconds": 0.8,
                "usage_cost_measurement_status": "placeholder",
                "runtime_cost_provenance": {"duration_source": "native_tool_trace"},
            },
            "long_horizon_posture": {
                "recovery_active": False,
                "verification_resume_ready": False,
                "pending_followup_count": 1,
            },
        },
        continuity_outline={
            "autonomy_posture": {"resume_posture": "same_task_resume"},
            "next_recommended_action": "verify",
        },
    )

    assert summary["long_horizon_continuity_ready"] is True
    assert summary["long_horizon_continuity_judgment"] == "daily_driver_continuity_ready"
    assert summary["workflow_active_stage"] == "verify"
    assert summary["selected_workflow_stages"] == ["explore", "edit", "verify"]
    assert summary["workflow_resume_ready"] is True
    assert summary["workflow_projection_visible"] is True
    assert summary["workflow_recovery_aligned"] is True
    assert "long_horizon_ready=True" in summary["summary"]
    assert "workflow_stage=verify" in summary["summary"]
    assert "long_horizon_judgment=daily_driver_continuity_ready" in summary["summary"]


def test_build_comparative_session_continuity_summary_treats_approval_boundary_as_governed_ready_continuity() -> None:
    from agent_orchestrator.productization_surface import build_comparative_session_continuity_summary

    summary = build_comparative_session_continuity_summary(
        session_productization_surface={
            "format": "agent_orchestrator.session_productization_surface.v1",
            "continuity_status": "governed_approval_boundary",
            "resume_supported": True,
            "resume_kind": "approval_resume",
            "compaction_stage": "light_compaction",
            "runtime_duration_seconds": 0.8,
            "usage_cost_measurement_status": "placeholder",
            "continuity_readiness": {
                "resume_ready": True,
                "runtime_cost_ready": True,
                "compaction_ready": True,
                "pressure_visible": True,
                "recovery_ready": True,
                "governed_pause_resume_ready": True,
            },
            "operator_posture_digest": {
                "resume_posture": "approval_reentry",
                "runbook_recovery_lane": "approval_pause",
                "next_recommended_action": "human_review",
                "approval_boundary_active": True,
                "compaction_pressure": "light_compaction",
                "context_pressure": True,
                "summarization_ready": False,
            },
            "long_horizon_posture": {
                "recovery_active": False,
                "verification_resume_ready": False,
                "pending_followup_count": 1,
            },
        },
        continuity_outline={
            "autonomy_posture": {"resume_posture": "approval_reentry"},
            "next_recommended_action": "human_review",
        },
    )

    assert summary["approval_boundary_active"] is True
    assert summary["governed_pause_resume_ready"] is True
    assert summary["long_horizon_continuity_ready"] is True
    assert summary["long_horizon_continuity_judgment"] == "daily_driver_continuity_governed_approval_boundary"
    assert "approval_boundary_active=True" in summary["summary"]
    assert "governed_pause_resume_ready=True" in summary["summary"]
