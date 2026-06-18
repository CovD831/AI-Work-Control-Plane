"""Shared productization surface helpers for native execution evidence."""
from __future__ import annotations

from agent_orchestrator.control_plane_posture import derive_planner_closure_posture_summary


def derive_native_tool_productization_surface(
    *,
    native_tool_surface: dict[str, object] | None = None,
    native_tool_trace: dict[str, object] | None = None,
    native_tool_productization_surface: dict[str, object] | None = None,
    shared_evidence_surface: list[object] | None = None,
) -> dict[str, object]:
    native_tool_surface = native_tool_surface if isinstance(native_tool_surface, dict) else {}
    native_tool_trace = native_tool_trace if isinstance(native_tool_trace, dict) else {}
    native_tool_productization_surface = (
        native_tool_productization_surface if isinstance(native_tool_productization_surface, dict) else {}
    )
    if native_tool_productization_surface:
        return native_tool_productization_surface
    readiness = (
        native_tool_surface.get("daily_driver_readiness", {})
        if isinstance(native_tool_surface.get("daily_driver_readiness"), dict)
        else {}
    )
    bounded_read_search_ready = readiness.get("bounded_read_search_ready")
    if bounded_read_search_ready is None:
        bounded_read_search_ready = readiness.get("repo_exploration_ready")
    glob_ready = readiness.get("glob_ready")
    if glob_ready is None:
        glob_ready = readiness.get("repo_exploration_ready")
    structured_patch_ready = readiness.get("structured_patch_ready")
    if structured_patch_ready is None:
        structured_patch_ready = readiness.get("patch_preview_ready")
    governance = native_tool_surface.get("governance", {}) if isinstance(native_tool_surface.get("governance"), dict) else {}
    trace_entries = native_tool_trace.get("trace", []) if isinstance(native_tool_trace.get("trace"), list) else []
    recent_tools = [
        item.get("tool")
        for item in trace_entries[-5:]
        if isinstance(item, dict) and item.get("tool")
    ]
    tool_count = len(native_tool_surface.get("tools", [])) if isinstance(native_tool_surface.get("tools"), list) else 0
    trace_count = len(trace_entries)
    return {
        "format": "agent_orchestrator.native_tool_productization_surface.compat.v1",
        "tool_count": tool_count,
        "trace_count": trace_count,
        "recent_tools": recent_tools,
        "tooling_posture": (
            "daily_driver_ready"
            if tool_count >= 1
            and trace_count >= 1
            and bool(readiness.get("repo_exploration_ready"))
            and bool(bounded_read_search_ready)
            and bool(glob_ready)
            and bool(structured_patch_ready)
            and bool(readiness.get("diff_preview_ready"))
            and bool(readiness.get("verification_ready"))
            else "productization_gap_remaining"
        ),
        "operator_visibility_ready": tool_count >= 1 and trace_count >= 1,
        "usage_visibility_ready": trace_count >= 1,
        "readiness": {
            "repo_exploration_ready": bool(readiness.get("repo_exploration_ready")),
            "bounded_read_search_ready": bool(bounded_read_search_ready),
            "glob_ready": bool(glob_ready),
            "structured_patch_ready": bool(structured_patch_ready),
            "patch_preview_ready": bool(readiness.get("patch_preview_ready")),
            "diff_preview_ready": bool(readiness.get("diff_preview_ready")),
            "verification_ready": bool(readiness.get("verification_ready")),
            "artifact_backed": bool(readiness.get("artifact_backed")),
        },
        "governance_boundary": {
            "boundary_policy": governance.get("boundary_policy"),
            "approval_aware": governance.get("approval_aware"),
            "artifact_backed": governance.get("artifact_backed"),
        },
        "shared_evidence_surface": list(
            dict.fromkeys(
                [
                    "runtime_payload",
                    "clarify_boundary_digest",
                    "approval_boundary_digest",
                    "workspace_index",
                    "ui_execution_summary",
                    "cli_execution_summary",
                    "evidence_report",
                    *[str(item) for item in (shared_evidence_surface or []) if isinstance(item, str)],
                ]
            )
        ),
    }


def derive_operator_tool_digest(
    *,
    native_tool_productization_surface: dict[str, object],
    native_tool_workflow_surface: dict[str, object] | None = None,
) -> dict[str, object]:
    native_tool_productization_surface = (
        native_tool_productization_surface if isinstance(native_tool_productization_surface, dict) else {}
    )
    native_tool_workflow_surface = (
        native_tool_workflow_surface if isinstance(native_tool_workflow_surface, dict) else {}
    )
    if not native_tool_workflow_surface:
        native_tool_workflow_surface = (
            native_tool_productization_surface.get("workflow_surface", {})
            if isinstance(native_tool_productization_surface.get("workflow_surface"), dict)
            else {}
        )
    if not native_tool_productization_surface and not native_tool_workflow_surface:
        return {}
    readiness = (
        native_tool_productization_surface.get("readiness", {})
        if isinstance(native_tool_productization_surface.get("readiness"), dict)
        else {}
    )
    explore = (
        native_tool_workflow_surface.get("explore", {})
        if isinstance(native_tool_workflow_surface.get("explore"), dict)
        else {}
    )
    edit = (
        native_tool_workflow_surface.get("edit", {})
        if isinstance(native_tool_workflow_surface.get("edit"), dict)
        else {}
    )
    verify = (
        native_tool_workflow_surface.get("verify", {})
        if isinstance(native_tool_workflow_surface.get("verify"), dict)
        else {}
    )
    daily_driver = (
        native_tool_workflow_surface.get("daily_driver_path", {})
        if isinstance(native_tool_workflow_surface.get("daily_driver_path"), dict)
        else {}
    )
    return {
        "format": "agent_orchestrator.operator_tool_digest.v1",
        "tooling_posture": native_tool_productization_surface.get("tooling_posture"),
        "tool_count": native_tool_productization_surface.get("tool_count"),
        "trace_count": native_tool_productization_surface.get("trace_count"),
        "recent_tools": list(native_tool_productization_surface.get("recent_tools", []))
        if isinstance(native_tool_productization_surface.get("recent_tools"), list)
        else [],
        "repo_exploration_ready": readiness.get("repo_exploration_ready"),
        "bounded_read_search_ready": readiness.get("bounded_read_search_ready"),
        "glob_ready": readiness.get("glob_ready"),
        "structured_patch_ready": readiness.get("structured_patch_ready"),
        "verification_ready": readiness.get("verification_ready"),
        "explore_tools": list(explore.get("tools", [])) if isinstance(explore.get("tools"), list) else [],
        "edit_tools": list(edit.get("tools", [])) if isinstance(edit.get("tools"), list) else [],
        "verify_tools": list(verify.get("tools", [])) if isinstance(verify.get("tools"), list) else [],
        "daily_driver_tools": list(daily_driver.get("tools", []))
        if isinstance(daily_driver.get("tools"), list)
        else [],
        "summary": (
            f"posture={native_tool_productization_surface.get('tooling_posture')} "
            f"recent={','.join(str(item) for item in native_tool_productization_surface.get('recent_tools', [])) if isinstance(native_tool_productization_surface.get('recent_tools'), list) and native_tool_productization_surface.get('recent_tools') else 'none'} "
            f"explore={','.join(str(item) for item in explore.get('tools', [])) if isinstance(explore.get('tools'), list) and explore.get('tools') else 'none'} "
            f"edit={','.join(str(item) for item in edit.get('tools', [])) if isinstance(edit.get('tools'), list) and edit.get('tools') else 'none'} "
            f"verify={','.join(str(item) for item in verify.get('tools', [])) if isinstance(verify.get('tools'), list) and verify.get('tools') else 'none'}"
        ),
    }


def derive_operator_planner_digest(
    *,
    planner_decision: dict[str, object],
    planner_closure_posture: dict[str, object] | None = None,
    continuity_outline: dict[str, object] | None = None,
) -> dict[str, object]:
    planner_decision = planner_decision if isinstance(planner_decision, dict) else {}
    planner_closure_posture = (
        planner_closure_posture if isinstance(planner_closure_posture, dict) else {}
    )
    continuity_outline = continuity_outline if isinstance(continuity_outline, dict) else {}
    if not planner_decision and not planner_closure_posture and not continuity_outline:
        return {}
    autonomy_posture = (
        planner_decision.get("autonomy_posture", {})
        if isinstance(planner_decision.get("autonomy_posture"), dict)
        else {}
    )
    delegation_contract = (
        planner_decision.get("delegation_contract", {})
        if isinstance(planner_decision.get("delegation_contract"), dict)
        else {}
    )
    decision_boundary = (
        planner_decision.get("decision_boundary", {})
        if isinstance(planner_decision.get("decision_boundary"), dict)
        else {}
    )
    control_surface = (
        planner_decision.get("control_surface", {})
        if isinstance(planner_decision.get("control_surface"), dict)
        else {}
    )
    planner_reasoning = (
        planner_decision.get("planner_reasoning", {})
        if isinstance(planner_decision.get("planner_reasoning"), dict)
        else {}
    )
    planner_independence = (
        planner_decision.get("planner_independence", {})
        if isinstance(planner_decision.get("planner_independence"), dict)
        else {}
    )
    action_coverage = (
        planner_decision.get("action_coverage", {})
        if isinstance(planner_decision.get("action_coverage"), dict)
        else {}
    )
    planner_governed_alternatives = (
        [dict(item) for item in planner_decision.get("planner_governed_alternatives", []) if isinstance(item, dict)]
        if isinstance(planner_decision.get("planner_governed_alternatives"), list)
        else []
    )
    continuity_posture = (
        continuity_outline.get("autonomy_posture", {})
        if isinstance(continuity_outline.get("autonomy_posture"), dict)
        else {}
    )
    selected_actions = (
        [str(item) for item in planner_decision.get("selected_actions", []) if item not in {None, ""}]
        if isinstance(planner_decision.get("selected_actions"), list)
        else []
    )
    resolved_autonomy_selected_actions = (
        list(action_coverage.get("autonomy_selected_actions", []))
        if isinstance(action_coverage.get("autonomy_selected_actions"), list)
        and action_coverage.get("autonomy_selected_actions")
        else list(selected_actions)
    )
    resolved_candidate_count = action_coverage.get("candidate_count")
    if resolved_candidate_count in {None, 0}:
        resolved_candidate_count = (
            len(planner_decision.get("decision_candidates", []))
            if isinstance(planner_decision.get("decision_candidates"), list)
            else 0
        )
    resolved_governed_alternative_count = action_coverage.get("governed_alternative_count")
    if resolved_governed_alternative_count is None:
        resolved_governed_alternative_count = len(planner_governed_alternatives)
    decision_mode = control_surface.get("decision_mode") or (
        "native_first_autonomous"
        if (planner_decision.get("planner_family") or continuity_outline.get("planner_family")) == "native"
        else "compatibility_guided"
    )
    return {
        "format": "agent_orchestrator.operator_planner_digest.v1",
        "planner_family": planner_decision.get("planner_family") or continuity_outline.get("planner_family"),
        "selected_execution_strategy": planner_decision.get("selected_execution_strategy"),
        "primary_action": autonomy_posture.get("primary_action") or planner_decision.get("primary_action"),
        "selected_actions": selected_actions,
        "selected_executor": delegation_contract.get("selected_executor"),
        "closure_mode": planner_closure_posture.get("closure_mode"),
        "next_recommended_action": planner_closure_posture.get("next_recommended_action")
        or continuity_outline.get("next_recommended_action")
        or control_surface.get("next_recommended_action")
        or autonomy_posture.get("primary_action")
        or planner_decision.get("primary_action"),
        "resume_expectation": delegation_contract.get("resume_expectation")
        or continuity_outline.get("resume_expectation"),
        "resume_posture": planner_closure_posture.get("resume_posture")
        or continuity_posture.get("resume_posture"),
        "pause_expected": autonomy_posture.get("pause_expected"),
        "handoff_expected": autonomy_posture.get("handoff_expected"),
        "fallback_expected": autonomy_posture.get("fallback_expected"),
        "clarify_pause_state": autonomy_posture.get("clarify_pause_state"),
        "approval_pause_state": autonomy_posture.get("approval_pause_state"),
        "requires_human_confirmation": decision_boundary.get("requires_human_confirmation"),
        "risk_level": decision_boundary.get("risk_level"),
        "task_type": decision_boundary.get("task_type"),
        "route_task_kind": decision_boundary.get("route_task_kind"),
        "verification_status": planner_closure_posture.get("verification_status"),
        "decision_mode": decision_mode,
        "candidate_count": resolved_candidate_count,
        "selected_candidate_count": planner_decision.get("selected_candidate_count"),
        "governed_alternative_count": resolved_governed_alternative_count,
        "autonomy_selected_action_count": action_coverage.get("autonomy_selected_action_count")
        if action_coverage.get("autonomy_selected_action_count") is not None
        else len(resolved_autonomy_selected_actions),
        "autonomy_selected_actions": resolved_autonomy_selected_actions,
        "planner_governed_alternatives": planner_governed_alternatives,
        "native_first_contract_authoritative": planner_independence.get("native_first_contract_authoritative"),
        "legacy_reference_used": planner_independence.get("legacy_reference_used"),
        "planner_reasoning": planner_reasoning,
        "summary": (
            f"primary={autonomy_posture.get('primary_action') or planner_decision.get('primary_action')} "
            f"executor={delegation_contract.get('selected_executor')} "
            f"mode={planner_closure_posture.get('closure_mode')} "
            f"next_action={planner_closure_posture.get('next_recommended_action') or continuity_outline.get('next_recommended_action') or control_surface.get('next_recommended_action') or autonomy_posture.get('primary_action') or planner_decision.get('primary_action')} "
            f"resume_expectation={delegation_contract.get('resume_expectation') or continuity_outline.get('resume_expectation')} "
            f"resume_posture={planner_closure_posture.get('resume_posture') or continuity_posture.get('resume_posture')} "
            f"pause_expected={autonomy_posture.get('pause_expected')} "
            f"handoff_expected={autonomy_posture.get('handoff_expected')} "
            f"fallback_expected={autonomy_posture.get('fallback_expected')} "
            f"requires_confirmation={decision_boundary.get('requires_human_confirmation')} "
            f"decision_mode={decision_mode} "
            f"candidates={resolved_candidate_count} "
            f"governed_alternatives={resolved_governed_alternative_count} "
            f"autonomy_actions={','.join(str(item) for item in resolved_autonomy_selected_actions) if resolved_autonomy_selected_actions else 'none'}"
        ),
    }


def derive_clarify_boundary_digest(
    *,
    operator_planner_digest: dict[str, object] | None = None,
    comparative_session_posture_summary: dict[str, object] | None = None,
    execution_fact_chain: dict[str, object] | None = None,
    shared_evidence_surface: list[object] | None = None,
) -> dict[str, object]:
    operator_planner_digest = operator_planner_digest if isinstance(operator_planner_digest, dict) else {}
    comparative_session_posture_summary = (
        comparative_session_posture_summary
        if isinstance(comparative_session_posture_summary, dict)
        else {}
    )
    execution_fact_chain = execution_fact_chain if isinstance(execution_fact_chain, dict) else {}
    next_action = (
        execution_fact_chain.get("next_recommended_action")
        or comparative_session_posture_summary.get("next_recommended_action")
        or operator_planner_digest.get("next_recommended_action")
    )
    clarify_pause_state = any(
        bool(source.get("clarify_pause_state"))
        for source in (
            operator_planner_digest,
            comparative_session_posture_summary,
            execution_fact_chain,
        )
        if isinstance(source, dict)
    )
    active = clarify_pause_state or next_action in {"clarify", "clarify_scope"}
    if not active:
        return {}
    resume_expectation = (
        comparative_session_posture_summary.get("resume_expectation")
        or operator_planner_digest.get("resume_expectation")
    )
    recovery_lane = (
        execution_fact_chain.get("recovery_lane")
        or comparative_session_posture_summary.get("runbook_recovery_lane")
    )
    surface = [
        "runtime_payload",
        "clarify_boundary_digest",
        "workspace_index",
        "ui_execution_summary",
        "cli_execution_summary",
        *[str(item) for item in (shared_evidence_surface or []) if isinstance(item, str)],
    ]
    return {
        "format": "agent_orchestrator.clarify_boundary_digest.v1",
        "status": "planner_clarify_boundary",
        "planner_family": operator_planner_digest.get("planner_family")
        or comparative_session_posture_summary.get("planner_family"),
        "selected_execution_strategy": operator_planner_digest.get("selected_execution_strategy"),
        "primary_action": operator_planner_digest.get("primary_action")
        or comparative_session_posture_summary.get("primary_action"),
        "next_recommended_action": next_action,
        "clarify_pause_state": clarify_pause_state,
        "resume_expectation": resume_expectation,
        "resume_posture": comparative_session_posture_summary.get("resume_posture")
        or operator_planner_digest.get("resume_posture"),
        "recovery_lane": recovery_lane,
        "scope_realign_required": True,
        "shared_evidence_surface": list(dict.fromkeys(surface)),
        "summary": (
            f"status=planner_clarify_boundary "
            f"strategy={operator_planner_digest.get('selected_execution_strategy')} "
            f"next_action={next_action} "
            f"resume_expectation={resume_expectation} "
            f"recovery_lane={recovery_lane}"
        ),
    }


def derive_approval_boundary_digest(
    *,
    operator_planner_digest: dict[str, object] | None = None,
    comparative_session_posture_summary: dict[str, object] | None = None,
    execution_fact_chain: dict[str, object] | None = None,
    shared_evidence_surface: list[object] | None = None,
) -> dict[str, object]:
    operator_planner_digest = operator_planner_digest if isinstance(operator_planner_digest, dict) else {}
    comparative_session_posture_summary = (
        comparative_session_posture_summary
        if isinstance(comparative_session_posture_summary, dict)
        else {}
    )
    execution_fact_chain = execution_fact_chain if isinstance(execution_fact_chain, dict) else {}
    next_action = (
        execution_fact_chain.get("next_recommended_action")
        or comparative_session_posture_summary.get("next_recommended_action")
        or operator_planner_digest.get("next_recommended_action")
    )
    approval_pause_state = any(
        bool(source.get("approval_pause_state"))
        for source in (
            operator_planner_digest,
            comparative_session_posture_summary,
            execution_fact_chain,
        )
        if isinstance(source, dict)
    )
    human_confirmation_required = bool(
        operator_planner_digest.get("requires_human_confirmation")
        or comparative_session_posture_summary.get("approval_pause_state")
        or execution_fact_chain.get("approval_pause_state")
    )
    active = approval_pause_state or human_confirmation_required or next_action in {
        "approval_pause",
        "human_review",
        "await_approval",
        "human_decision",
    }
    if not active:
        return {}
    resume_expectation = (
        comparative_session_posture_summary.get("resume_expectation")
        or operator_planner_digest.get("resume_expectation")
    )
    recovery_lane = (
        execution_fact_chain.get("recovery_lane")
        or comparative_session_posture_summary.get("runbook_recovery_lane")
    )
    surface = [
        "runtime_payload",
        "approval_boundary_digest",
        "workspace_index",
        "ui_execution_summary",
        "cli_execution_summary",
        *[str(item) for item in (shared_evidence_surface or []) if isinstance(item, str)],
    ]
    return {
        "format": "agent_orchestrator.approval_boundary_digest.v1",
        "status": "planner_approval_boundary",
        "planner_family": operator_planner_digest.get("planner_family")
        or comparative_session_posture_summary.get("planner_family"),
        "selected_execution_strategy": operator_planner_digest.get("selected_execution_strategy"),
        "primary_action": operator_planner_digest.get("primary_action")
        or comparative_session_posture_summary.get("primary_action"),
        "next_recommended_action": next_action,
        "approval_pause_state": approval_pause_state,
        "resume_expectation": resume_expectation,
        "resume_posture": comparative_session_posture_summary.get("resume_posture")
        or operator_planner_digest.get("resume_posture"),
        "recovery_lane": recovery_lane,
        "human_confirmation_required": human_confirmation_required,
        "shared_evidence_surface": list(dict.fromkeys(surface)),
        "summary": (
            f"status=planner_approval_boundary "
            f"strategy={operator_planner_digest.get('selected_execution_strategy')} "
            f"next_action={next_action} "
            f"resume_expectation={resume_expectation} "
            f"recovery_lane={recovery_lane}"
        ),
    }


def build_external_comparison_harness_surface(
    *,
    shared_productization_contract_ready: bool,
    internal_repeatability_ready: bool,
    evidence_scope: str,
    proven_independent_daily_driver_family_count: int,
    comparative_shared_evidence_surface: list[object] | None = None,
) -> dict[str, object]:
    comparative_surface = [
        str(item)
        for item in (comparative_shared_evidence_surface or [])
        if isinstance(item, str)
    ]
    required_shared_surfaces = [
        "runtime_payload",
        "workspace_index",
        "ui_execution_summary",
        "cli_execution_summary",
        "evidence_report",
    ]
    required_external_artifacts = [
        "authoritative_opencode_case_harness",
        "same_contract_executor_comparison",
        "governed_recovery_and_cost_comparison",
    ]
    missing_external_artifacts = list(required_external_artifacts)
    return {
        "format": "agent_orchestrator.external_comparison_harness_surface.v1",
        "authoritative": False,
        "harness_status": "missing_authoritative_opencode_harness",
        "comparison_grade_ready": False,
        "decision_mode": "human_audit_required_until_external_comparison_ready",
        "blocking_gap": "no_authoritative_external_opencode_harness",
        "operator_action": "maintain_human_audit_until_external_harness_ready",
        "next_evidence_milestone": "authoritative_opencode_case_harness",
        "evidence_scope": evidence_scope,
        "required_shared_surface_count": len(required_shared_surfaces),
        "required_external_artifact_count": len(required_external_artifacts),
        "missing_external_artifact_count": len(missing_external_artifacts),
        "shared_surface_count": len(comparative_surface),
        "readiness": {
            "shared_productization_contract_ready": shared_productization_contract_ready,
            "internal_repeatability_ready": internal_repeatability_ready,
            "external_harness_ready": False,
        },
        "requirements": {
            "minimum_independent_daily_driver_family_count": 5,
            "proven_independent_daily_driver_family_count": proven_independent_daily_driver_family_count,
            "required_shared_surfaces": required_shared_surfaces,
            "required_external_artifacts": required_external_artifacts,
            "missing_external_artifacts": missing_external_artifacts,
        },
        "operator_gap_summary": {
            "required_shared_surface_count": len(required_shared_surfaces),
            "required_external_artifact_count": len(required_external_artifacts),
            "missing_external_artifact_count": len(missing_external_artifacts),
            "proven_independent_daily_driver_family_count": proven_independent_daily_driver_family_count,
        },
        "shared_evidence_surface": list(
            dict.fromkeys(
                [
                    *required_shared_surfaces,
                    *comparative_surface,
                ]
            )
        ),
    }


def build_comparative_daily_driver_benchmark(
    proof_strength: dict[str, object],
) -> str | None:
    proof_strength = proof_strength if isinstance(proof_strength, dict) else {}
    if proof_strength.get("daily_driver_repeatability_tier") != "multi_family_broad_daily_driver_proven":
        return None
    return (
        "official_catalog=docs/process/evidence-cases.json "
        f"independent_daily_driver_families={proof_strength.get('independent_daily_driver_repo_task_family_count')} "
        "status=multi_family_broad_daily_driver_proven"
    )


def build_comparative_daily_driver_summary(
    *,
    proof_strength: dict[str, object],
    benchmark_digest: dict[str, object] | None = None,
    comparative_benchmark: dict[str, object] | None = None,
) -> dict[str, object]:
    proof_strength = proof_strength if isinstance(proof_strength, dict) else {}
    benchmark_digest = benchmark_digest if isinstance(benchmark_digest, dict) else {}
    comparative_benchmark = comparative_benchmark if isinstance(comparative_benchmark, dict) else {}
    if not proof_strength and not benchmark_digest and not comparative_benchmark:
        return {}
    daily_driver_repeatability_tier = proof_strength.get("daily_driver_repeatability_tier")
    independent_count = proof_strength.get("independent_daily_driver_repo_task_family_count")
    daily_driver_main_path_ready = benchmark_digest.get("daily_driver_main_path_ready")
    if daily_driver_main_path_ready is None:
        daily_driver_main_path_ready = comparative_benchmark.get("daily_driver_main_path_ready")
    if daily_driver_main_path_ready is None:
        daily_driver_main_path_ready = bool(
            proof_strength.get("daily_driver_repeatability_tier") == "multi_family_broad_daily_driver_proven"
        )
    daily_driver_main_path_anchor = proof_strength.get("daily_driver_main_path_anchor")
    if daily_driver_main_path_anchor is None and daily_driver_main_path_ready:
        daily_driver_main_path_anchor = "long_chain_native_first_repo_task"
    daily_driver_case_matrix = comparative_benchmark.get("daily_driver_case_matrix", {})
    if not isinstance(daily_driver_case_matrix, dict):
        daily_driver_case_matrix = {}
    daily_driver_repeatability_harness = comparative_benchmark.get("daily_driver_repeatability_harness", {})
    if not isinstance(daily_driver_repeatability_harness, dict):
        daily_driver_repeatability_harness = {}
    daily_driver_runner_artifact = comparative_benchmark.get("daily_driver_runner_artifact", {})
    if not isinstance(daily_driver_runner_artifact, dict):
        daily_driver_runner_artifact = {}
    daily_driver_repeatability_judgment = (
        "main_path_anchor_proven_repeatability_gap_remaining"
        if daily_driver_main_path_ready and proof_strength.get("repeatability_ready") is not True
        else "multi_family_repeatability_proven"
        if proof_strength.get("repeatability_ready") is True
        else "daily_driver_path_unproven"
    )
    return {
        "format": "agent_orchestrator.comparative_daily_driver_summary.v1",
        "comparison_status": benchmark_digest.get("comparison_status")
        or comparative_benchmark.get("comparison_posture", {}).get("status")
        if isinstance(comparative_benchmark.get("comparison_posture"), dict)
        else benchmark_digest.get("comparison_status"),
        "daily_driver_main_path_ready": bool(daily_driver_main_path_ready),
        "daily_driver_repeatability_tier": daily_driver_repeatability_tier,
        "daily_driver_main_path_anchor": daily_driver_main_path_anchor,
        "daily_driver_repeatability_judgment": daily_driver_repeatability_judgment,
        "daily_driver_case_matrix": daily_driver_case_matrix,
        "daily_driver_repeatability_harness": daily_driver_repeatability_harness,
        "daily_driver_runner_artifact": daily_driver_runner_artifact,
        "direct_proof_status": proof_strength.get("direct_proof_status"),
        "repeatability_status": proof_strength.get("repeatability_status"),
        "stronger_task_family_count": proof_strength.get("stronger_task_family_count"),
        "independent_daily_driver_repo_task_family_count": independent_count,
        "daily_driver_repo_task_family_count": proof_strength.get("daily_driver_repo_task_family_count"),
        "daily_driver_repo_task_families_proven": list(proof_strength.get("daily_driver_repo_task_families_proven", []))
        if isinstance(proof_strength.get("daily_driver_repo_task_families_proven"), list)
        else [],
        "independent_daily_driver_repo_task_families_proven": list(
            proof_strength.get("independent_daily_driver_repo_task_families_proven", [])
        )
        if isinstance(proof_strength.get("independent_daily_driver_repo_task_families_proven"), list)
        else [],
        "summary": (
            f"status={benchmark_digest.get('comparison_status') or comparative_benchmark.get('comparison_posture', {}).get('status') if isinstance(comparative_benchmark.get('comparison_posture'), dict) else benchmark_digest.get('comparison_status')} "
            f"tier={daily_driver_repeatability_tier} "
            f"anchor={daily_driver_main_path_anchor or 'none'} "
            f"judgment={daily_driver_repeatability_judgment} "
            f"families={independent_count} "
            f"matrix={daily_driver_case_matrix.get('matrix_status') or 'none'} "
            f"harness={daily_driver_repeatability_harness.get('harness_status') or 'none'} "
            f"runner={daily_driver_runner_artifact.get('runner_status') or 'none'} "
            f"direct={proof_strength.get('direct_proof_status')} "
            f"repeatability={proof_strength.get('repeatability_status')}"
        ),
    }


def build_comparative_completion_summary(
    *,
    benchmark_digest: dict[str, object] | None = None,
    comparative_benchmark: dict[str, object] | None = None,
) -> dict[str, object]:
    benchmark_digest = benchmark_digest if isinstance(benchmark_digest, dict) else {}
    comparative_benchmark = comparative_benchmark if isinstance(comparative_benchmark, dict) else {}
    posture = (
        comparative_benchmark.get("comparison_posture", {})
        if isinstance(comparative_benchmark.get("comparison_posture"), dict)
        else {}
    )
    comparison_grade = (
        comparative_benchmark.get("comparison_grade_assessment", {})
        if isinstance(comparative_benchmark.get("comparison_grade_assessment"), dict)
        else {}
    )
    harness_surface = (
        comparative_benchmark.get("external_comparison_harness_surface", {})
        if isinstance(comparative_benchmark.get("external_comparison_harness_surface"), dict)
        else comparison_grade.get("external_comparison_harness_surface", {})
        if isinstance(comparison_grade.get("external_comparison_harness_surface"), dict)
        else {}
    )
    if not benchmark_digest and not comparative_benchmark:
        return {}
    comparison_status = benchmark_digest.get("comparison_status") or posture.get("status")
    comparison_grade_status = benchmark_digest.get("comparison_grade_status") or comparison_grade.get("status")
    blocking_gap = benchmark_digest.get("blocking_gap") or comparison_grade.get("blocking_gap")
    operator_action = benchmark_digest.get("external_harness_operator_action") or harness_surface.get("operator_action")
    completion_ready = bool(benchmark_digest.get("comparison_grade_ready"))
    human_audit_required = not completion_ready
    return {
        "format": "agent_orchestrator.comparative_completion_summary.v1",
        "completion_ready": completion_ready,
        "human_audit_required": human_audit_required,
        "comparison_status": comparison_status,
        "comparison_grade_status": comparison_grade_status,
        "blocking_gap": blocking_gap,
        "operator_action": operator_action,
        "remaining_gap_classes": list(benchmark_digest.get("remaining_gap_classes", []))
        if isinstance(benchmark_digest.get("remaining_gap_classes"), list)
        else list(posture.get("remaining_gap_classes", []))
        if isinstance(posture.get("remaining_gap_classes"), list)
        else [],
        "summary": (
            f"completion_ready={completion_ready} "
            f"human_audit_required={human_audit_required} "
            f"comparison_status={comparison_status} "
            f"grade_status={comparison_grade_status} "
            f"blocking_gap={blocking_gap} "
            f"operator_action={operator_action}"
        ),
    }


def build_comparative_native_closure_summary(
    *,
    native_task_proof: dict[str, object],
    verification: dict[str, object] | None = None,
    recovery_summary: dict[str, object] | None = None,
    comparative_shared_evidence_surface: list[object] | None = None,
) -> dict[str, object]:
    native_task_proof = native_task_proof if isinstance(native_task_proof, dict) else {}
    verification = verification if isinstance(verification, dict) else {}
    recovery_summary = recovery_summary if isinstance(recovery_summary, dict) else {}
    if not native_task_proof and not verification and not recovery_summary:
        return {}
    closure_status = native_task_proof.get("closure_status") or verification.get("status")
    proof_scenario = native_task_proof.get("proof_scenario")
    return {
        "format": "agent_orchestrator.comparative_native_closure_summary.v1",
        "native_runtime_only": native_task_proof.get("native_runtime_only"),
        "external_coding_agent_required": native_task_proof.get("external_coding_agent_required"),
        "task_class": native_task_proof.get("task_class"),
        "proof_scenario": proof_scenario,
        "closure_status": closure_status,
        "artifact_count": native_task_proof.get("artifact_count"),
        "event_count": native_task_proof.get("event_count"),
        "verification_status": verification.get("status"),
        "verification_failure_kind": verification.get("failure_kind"),
        "repair_outcome": recovery_summary.get("outcome"),
        "recovery_action": recovery_summary.get("action"),
        "recovery_reason": recovery_summary.get("reason"),
        "proof_ready": closure_status == "completed"
        and native_task_proof.get("native_runtime_only") is True
        and native_task_proof.get("external_coding_agent_required") is False,
        "summary": (
            f"native_runtime_only={native_task_proof.get('native_runtime_only')} "
            f"closure_status={closure_status} "
            f"verification_status={verification.get('status')} "
            f"repair_outcome={recovery_summary.get('outcome')} "
            f"proof_scenario={proof_scenario}"
        ),
        "shared_evidence_surface": list(
            dict.fromkeys(
                [
                    "runtime_payload",
                    "session_continuity",
                    "session_productization_surface",
                    "runtime_cost",
                    "native_task_proof",
                    "verification",
                    "recovery_summary",
                    "workspace_index",
                    "ui_execution_summary",
                    "cli_execution_summary",
                    "evidence_report",
                    *[str(item) for item in (comparative_shared_evidence_surface or []) if isinstance(item, str)],
                ]
            )
        ),
    }


def build_runtime_comparative_benchmark_summary(
    execution_artifact_summary: dict[str, object],
) -> dict[str, object]:
    execution_artifact_summary = (
        execution_artifact_summary if isinstance(execution_artifact_summary, dict) else {}
    )
    native_repo_task_acceptance = (
        execution_artifact_summary.get("native_repo_task_acceptance", {})
        if isinstance(execution_artifact_summary.get("native_repo_task_acceptance"), dict)
        else {}
    )
    native_complex_repo_task_acceptance = (
        execution_artifact_summary.get("native_complex_repo_task_acceptance", {})
        if isinstance(execution_artifact_summary.get("native_complex_repo_task_acceptance"), dict)
        else {}
    )
    native_task_proof = (
        execution_artifact_summary.get("native_task_proof", {})
        if isinstance(execution_artifact_summary.get("native_task_proof"), dict)
        else {}
    )
    adapter_shared_contract = (
        execution_artifact_summary.get("adapter_shared_contract", {})
        if isinstance(execution_artifact_summary.get("adapter_shared_contract"), dict)
        else {}
    )
    session_continuity = (
        execution_artifact_summary.get("session_continuity", {})
        if isinstance(execution_artifact_summary.get("session_continuity"), dict)
        else {}
    )
    session_productization_surface = (
        session_continuity.get("session_productization_surface", {})
        if isinstance(session_continuity.get("session_productization_surface"), dict)
        else {}
    )
    native_tool_productization_surface = (
        execution_artifact_summary.get("native_tool_productization_surface", {})
        if isinstance(execution_artifact_summary.get("native_tool_productization_surface"), dict)
        else {}
    )
    adapter_productization_surface = (
        execution_artifact_summary.get("adapter_productization_surface", {})
        if isinstance(execution_artifact_summary.get("adapter_productization_surface"), dict)
        else {}
    )
    program_continuity = (
        session_continuity.get("program_continuity", {})
        if isinstance(session_continuity.get("program_continuity"), dict)
        else {}
    )
    daily_driver_readiness = (
        session_continuity.get("daily_driver_readiness", {})
        if isinstance(session_continuity.get("daily_driver_readiness"), dict)
        else {}
    )
    planner_shared_contract = (
        execution_artifact_summary.get("planner_shared_contract", {})
        if isinstance(execution_artifact_summary.get("planner_shared_contract"), dict)
        else {}
    )
    native_tool_usage = (
        execution_artifact_summary.get("native_tool_usage", {})
        if isinstance(execution_artifact_summary.get("native_tool_usage"), dict)
        else {}
    )
    planner_decision = (
        execution_artifact_summary.get("planner_decision", {})
        if isinstance(execution_artifact_summary.get("planner_decision"), dict)
        else {}
    )
    planner_closure_posture = (
        execution_artifact_summary.get("planner_closure_posture", {})
        if isinstance(execution_artifact_summary.get("planner_closure_posture"), dict)
        else derive_planner_closure_posture_summary(
            planner_decision=planner_decision,
            continuity=(
                execution_artifact_summary.get("continuity_outline", {})
                if isinstance(execution_artifact_summary.get("continuity_outline"), dict)
                else {}
            ),
        )
    )
    continuity_outline = (
        execution_artifact_summary.get("continuity_outline", {})
        if isinstance(execution_artifact_summary.get("continuity_outline"), dict)
        else {}
    )
    comparative_planner_candidate_summary = build_comparative_planner_candidate_summary(
        planner_shared_contract=planner_shared_contract,
        comparative_shared_evidence_surface=[
            "planner_shared_contract",
            "planner_closure_posture",
            "planner_autonomy_boundary",
            "planner_reasoning",
        ],
    )
    unified_adapter_contract_ready = bool(
        adapter_productization_surface.get("surface_status") == "same_contract_two_executors_governed"
        and (
            adapter_productization_surface.get("comparison_mode")
            or adapter_shared_contract.get("comparison_mode")
        )
        == "same_contract_two_executors"
        and (
            adapter_productization_surface.get("resume_contract_supported")
            if "resume_contract_supported" in adapter_productization_surface
            else adapter_shared_contract.get("shared_contract_resume_supported")
        )
        is True
        and adapter_productization_surface.get("governed_recovery_ready") is True
        and adapter_shared_contract.get("default_path") == "native"
        and adapter_shared_contract.get("hot_plug_supported") is True
    )
    shared_contract_alignment = {
        "session_continuity_ready": bool(session_productization_surface.get("format"))
        or (
            bool(session_continuity.get("continuity_snapshot", {}).get("format"))
            if isinstance(session_continuity.get("continuity_snapshot"), dict)
            else False
        ),
        "runtime_cost_ready": bool(execution_artifact_summary.get("runtime_cost", {}).get("usage_cost_measurement_status"))
        if isinstance(execution_artifact_summary.get("runtime_cost"), dict)
        else False,
        "native_tool_usage_ready": bool(native_tool_usage.get("tool_count"))
        and isinstance(native_tool_usage.get("trace_count"), int)
        and native_tool_usage.get("trace_count") >= 1
        and bool(native_tool_productization_surface.get("format")),
        "planner_evidence_ready": planner_shared_contract.get("format") == "agent_orchestrator.native_planner_decision.v1",
        "planner_candidate_surface_ready": bool(comparative_planner_candidate_summary.get("format"))
        and comparative_planner_candidate_summary.get("native_first") is not None
        and bool(comparative_planner_candidate_summary.get("selected_strategy"))
        and isinstance(comparative_planner_candidate_summary.get("decision_candidates"), list)
        and len(comparative_planner_candidate_summary.get("decision_candidates", [])) >= 1
        and comparative_planner_candidate_summary.get("workflow_projection_ready") is True,
        "planner_closure_posture_ready": bool(planner_closure_posture.get("format"))
        and bool(planner_closure_posture.get("closure_mode")),
        "adapter_contract_ready": adapter_shared_contract.get("comparison_mode") == "same_contract_two_executors"
        and bool(adapter_productization_surface.get("format")),
        "session_posture_ready": bool(planner_decision.get("autonomy_posture"))
        and bool(continuity_outline.get("autonomy_posture"))
        and "resume_expectation" in continuity_outline,
        "session_posture_cases": 1
        if bool(planner_decision.get("autonomy_posture"))
        and bool(continuity_outline.get("autonomy_posture"))
        and "resume_expectation" in continuity_outline
        else 0,
    }
    shared_productization_contract_ready = all(bool(value) for value in shared_contract_alignment.values())
    long_chain_task_ready = daily_driver_readiness.get("long_chain_task_ready") is True
    daily_driver_main_path_ready = (
        daily_driver_readiness.get("daily_driver_main_path_ready") is True
        if "daily_driver_main_path_ready" in daily_driver_readiness
        else bool(shared_productization_contract_ready and long_chain_task_ready)
    )
    daily_driver_readiness = {
        "shared_productization_ready": shared_productization_contract_ready,
        "long_chain_task_ready": long_chain_task_ready,
        "daily_driver_main_path_ready": daily_driver_main_path_ready,
        "daily_driver_main_path_ready_cases": 1 if daily_driver_main_path_ready else 0,
        "open_product_gap": (
            "platform_breadth_remaining"
            if daily_driver_main_path_ready
            else "long_chain_repo_closure_not_yet_proven"
            if shared_productization_contract_ready
            else "productization_contract_incomplete"
        ),
    }
    comparison_posture_basis = {
        "shared_productization_contract_ready": shared_productization_contract_ready,
        "daily_driver_main_path_ready": daily_driver_main_path_ready,
        "long_chain_native_first_ready": (
            program_continuity.get("long_chain_native_first_ready")
            if isinstance(program_continuity.get("long_chain_native_first_ready"), bool)
            else bool(
                native_repo_task_acceptance.get("real_repo_task_acceptance_ready") is True
                and native_complex_repo_task_acceptance.get("complex_repo_task_ready") is True
                and native_task_proof.get("task_class") == "bounded_internal_repo_task"
            )
        ),
        "native_repo_task_acceptance_ready": native_repo_task_acceptance.get("real_repo_task_acceptance_ready") is True,
        "native_complex_repo_task_acceptance_ready": native_complex_repo_task_acceptance.get("complex_repo_task_ready") is True,
        "planner_candidate_surface_ready": shared_contract_alignment.get("planner_candidate_surface_ready") is True,
        "planner_candidate_governed_alternative_count": len(
            comparative_planner_candidate_summary.get("governed_alternatives", [])
        )
        if isinstance(comparative_planner_candidate_summary.get("governed_alternatives"), list)
        else 0,
        "unified_adapter_contract_ready": unified_adapter_contract_ready,
        "evidence_scope": "bounded_internal_evidence_only",
        "comparison_limitations": [
            "no_authoritative_external_opencode_harness",
            "single_stronger_long_chain_repo_task_family",
            "platform_breadth_and_product_thickness_still_manual_gap_judgment",
        ],
        "basis_surface_refs": [
            "shared_contract_alignment",
            "shared_productization_contract_ready",
            "planner_candidate_surface_ready",
            "unified_adapter_contract_ready",
            "planner_closure_posture",
            "daily_driver_readiness",
            "daily_driver_main_path_ready",
            "native_repo_task_acceptance",
            "native_complex_repo_task_acceptance",
        ],
    }
    comparison_proof_strength = {
        "direct_proof_status": (
            "single_stronger_task_family_proven"
            if daily_driver_main_path_ready is True
            else "foundational_productization_only"
            if shared_productization_contract_ready
            else "foundational_gap_remaining"
        ),
        "repeatability_status": (
            "not_yet_broadly_proven"
            if daily_driver_main_path_ready is True
            else "not_applicable_until_direct_proof"
            if shared_productization_contract_ready is False
            else "not_yet_proven"
        ),
        "repeatability_ready": False,
        "stronger_task_family_count": 1 if daily_driver_main_path_ready is True else 0,
        "broader_task_family_count": 0,
        "stronger_task_families": (
            ["long_chain_native_first_repo_task"]
            if daily_driver_main_path_ready is True
            else []
        ),
        "daily_driver_main_path_anchor": (
            "long_chain_native_first_repo_task"
            if daily_driver_main_path_ready is True
            else None
        ),
        "daily_driver_repo_task_families_proven": (
            ["long_chain_native_first_repo_task"]
            if daily_driver_main_path_ready is True
            else []
        ),
        "daily_driver_repo_task_family_count": 1 if daily_driver_main_path_ready is True else 0,
        "broader_repeatability_gap_families": [
            "multi_family_daily_driver_repo_tasks",
        ],
        "proof_limitations": [
            "single_stronger_long_chain_repo_task_family",
            "no_repeatable_multi_family_daily_driver_proof",
        ],
        "planner_candidate_status": (
            "native_first_candidate_surface_ready"
            if shared_contract_alignment.get("planner_candidate_surface_ready") is True
            else "candidate_surface_gap_remaining"
        ),
        "adapter_unification_status": (
            "same_contract_adapter_surface_ready"
            if unified_adapter_contract_ready
            else "adapter_unification_gap_remaining"
        ),
    }
    comparison_posture = (
        {
            "status": "daily_driver_main_path_proven_breadth_gap_remaining",
            "confidence": "bounded_internal_evidence_only",
            "remaining_gap_classes": [
                "multi_family_daily_driver_repeatability",
                "platform_breadth",
                "plugin_ecosystem",
                "session_ux_thickness",
                "wider_general_task_coverage",
            ],
            "foundation_gap_remaining": False,
        }
        if daily_driver_main_path_ready is True
        else {
            "status": "shared_productization_ready_but_daily_driver_proof_gap_remaining",
            "confidence": "bounded_internal_evidence_only",
            "remaining_gap_classes": [
                "long_chain_repo_closure_repeatability",
                "multi_family_daily_driver_repeatability",
                "platform_breadth",
                "plugin_ecosystem",
                "wider_general_task_coverage",
            ],
            "foundation_gap_remaining": False,
        }
        if shared_productization_contract_ready
        else {
            "status": "foundational_gap_remaining",
            "confidence": "bounded_internal_evidence_only",
            "remaining_gap_classes": [
                "tool_surface_depth",
                "planner_independence",
                "session_continuity_productization",
                "adapter_unification",
            ],
            "foundation_gap_remaining": True,
        }
    )
    comparison_grade_assessment = {
        "status": (
            "internal_repeatability_strong_external_comparison_gap_remaining"
            if daily_driver_main_path_ready is True
            else "internal_productization_ready_but_repeatability_or_external_gap_remaining"
            if shared_productization_contract_ready
            else "foundational_gap_remaining"
        ),
        "comparison_grade_ready": False,
        "internal_repeatability_ready": daily_driver_main_path_ready is True,
        "external_harness_ready": False,
        "external_harness_status": "missing_authoritative_opencode_harness",
        "blocking_gap": "no_authoritative_external_opencode_harness",
        "decision_mode": "human_audit_required_until_external_comparison_ready",
    }
    external_comparison_harness_surface = build_external_comparison_harness_surface(
        shared_productization_contract_ready=shared_productization_contract_ready,
        internal_repeatability_ready=daily_driver_main_path_ready is True,
        evidence_scope="bounded_internal_evidence_only",
        proven_independent_daily_driver_family_count=1 if daily_driver_main_path_ready is True else 0,
        comparative_shared_evidence_surface=[
            "runtime_event_stream",
            "session_continuity",
            "session_productization_surface",
            "planner_closure_posture",
            "planner_autonomy_boundary",
            "planner_reasoning",
            "clarify_boundary_digest",
            "approval_boundary_digest",
            "native_tool_workflow_surface",
            "native_tool_productization_surface",
            "adapter_productization_surface",
            "adapter_capability_surface",
            "workspace_index",
            "ui_execution_summary",
            "cli_execution_summary",
            "adapter_shared_contract",
            "planner_shared_contract",
            "evidence_report",
        ],
    )
    comparative_adapter_summary = build_comparative_adapter_summary(
        adapter_productization_surface=adapter_productization_surface,
        adapter_shared_contract=adapter_shared_contract,
        adapter_capability_surface=(
            execution_artifact_summary.get("adapter_capability_surface", {})
            if isinstance(execution_artifact_summary.get("adapter_capability_surface"), dict)
            else execution_artifact_summary.get("adapter_capability", {})
            if isinstance(execution_artifact_summary.get("adapter_capability"), dict)
            else {}
        ),
    )
    operator_tool_digest = derive_operator_tool_digest(
        native_tool_productization_surface=native_tool_productization_surface,
        native_tool_workflow_surface=(
            execution_artifact_summary.get("native_tool_workflow_surface", {})
            if isinstance(execution_artifact_summary.get("native_tool_workflow_surface"), dict)
            else native_tool_productization_surface.get("workflow_surface", {})
            if isinstance(native_tool_productization_surface.get("workflow_surface"), dict)
            else {}
        ),
    )
    operator_planner_digest = derive_operator_planner_digest(
        planner_decision=planner_decision,
        planner_closure_posture=planner_closure_posture,
        continuity_outline=continuity_outline,
    )
    comparative_session_posture_summary = build_comparative_session_posture_summary(
        session_productization_surface=session_productization_surface,
        planner_decision=planner_decision,
        continuity_outline=continuity_outline,
    )
    comparative_session_continuity_summary = build_comparative_session_continuity_summary(
        session_productization_surface=session_productization_surface,
        continuity_outline=continuity_outline,
        comparative_shared_evidence_surface=[
            "session_continuity",
            "session_productization_surface",
            "runtime_cost",
            "runtime_cost_provenance",
        ],
    )
    comparative_planner_autonomy_summary = build_comparative_planner_autonomy_summary(
        planner_shared_contract=planner_shared_contract,
        operator_planner_digest=operator_planner_digest,
        comparative_shared_evidence_surface=[
            "planner_shared_contract",
            "planner_closure_posture",
            "planner_autonomy_boundary",
            "planner_reasoning",
        ],
    )
    comparative_planner_candidate_summary = build_comparative_planner_candidate_summary(
        planner_shared_contract=planner_shared_contract,
        operator_planner_digest=operator_planner_digest,
        comparative_shared_evidence_surface=[
            "planner_shared_contract",
            "planner_closure_posture",
            "planner_autonomy_boundary",
            "planner_reasoning",
        ],
    )
    comparison_grade_assessment["external_comparison_harness_surface"] = external_comparison_harness_surface
    comparative_daily_driver_summary = build_comparative_daily_driver_summary(
        proof_strength=comparison_proof_strength,
        benchmark_digest={
            "comparison_status": comparison_posture.get("status"),
            "daily_driver_main_path_ready": daily_driver_main_path_ready,
        },
        comparative_benchmark={
            "comparison_posture": comparison_posture,
            "daily_driver_main_path_ready": daily_driver_main_path_ready,
        },
    )
    comparative_completion_summary = build_comparative_completion_summary(
        benchmark_digest={
            "comparison_status": comparison_posture.get("status"),
            "comparison_grade_status": comparison_grade_assessment.get("status"),
            "comparison_grade_ready": comparison_grade_assessment.get("comparison_grade_ready"),
            "blocking_gap": comparison_grade_assessment.get("blocking_gap"),
            "external_harness_operator_action": external_comparison_harness_surface.get("operator_action"),
            "remaining_gap_classes": comparison_posture.get("remaining_gap_classes", []),
        },
        comparative_benchmark={
            "comparison_posture": comparison_posture,
            "comparison_grade_assessment": comparison_grade_assessment,
            "external_comparison_harness_surface": external_comparison_harness_surface,
        },
    )
    comparative_native_closure_summary = build_comparative_native_closure_summary(
        native_task_proof=native_task_proof,
        verification=(
            session_continuity.get("milestone_verification", {})
            if isinstance(session_continuity.get("milestone_verification"), dict)
            else {}
        ),
        recovery_summary=(
            session_continuity.get("recovery_summary", {})
            if isinstance(session_continuity.get("recovery_summary"), dict)
            else {}
        ),
        comparative_shared_evidence_surface=[
            "native_task_proof",
            "verification",
            "recovery_summary",
            "session_continuity",
            "session_productization_surface",
        ],
    )
    clarify_boundary_digest = derive_clarify_boundary_digest(
        operator_planner_digest=operator_planner_digest,
        comparative_session_posture_summary=comparative_session_posture_summary,
        shared_evidence_surface=[
            "session_continuity",
            "session_productization_surface",
            "planner_closure_posture",
            "planner_shared_contract",
            "evidence_report",
        ],
    )
    approval_boundary_digest = derive_approval_boundary_digest(
        operator_planner_digest=operator_planner_digest,
        comparative_session_posture_summary=comparative_session_posture_summary,
        shared_evidence_surface=[
            "session_continuity",
            "session_productization_surface",
            "planner_closure_posture",
            "planner_shared_contract",
            "evidence_report",
        ],
    )
    return {
        "format": "agent_orchestrator.comparative_benchmark_summary.v1",
        "case_count": 1,
        "productization_case_count": 1,
        "native_default_path": native_task_proof.get("native_runtime_only") is True,
        "native_task_class": native_task_proof.get("task_class"),
        "native_recovery_scenario": native_task_proof.get("proof_scenario"),
        "native_coverage_class": adapter_shared_contract.get("native_coverage_class"),
        "learning_consumed": adapter_shared_contract.get("learning_consumed"),
        "learning_source_count": adapter_shared_contract.get("learning_source_count"),
        "comparative_acceptance_bundle_ready": bool(native_task_proof.get("native_runtime_only") is True),
        "native_repo_task_acceptance_ready": native_repo_task_acceptance.get("real_repo_task_acceptance_ready"),
        "native_repo_task_acceptance_passed_checks": native_repo_task_acceptance.get("passed_check_count"),
        "native_repo_task_acceptance_total_checks": native_repo_task_acceptance.get("total_check_count"),
        "native_complex_repo_task_acceptance_ready": native_complex_repo_task_acceptance.get("complex_repo_task_ready"),
        "native_complex_repo_task_acceptance_passed_checks": native_complex_repo_task_acceptance.get("passed_check_count"),
        "native_complex_repo_task_acceptance_total_checks": native_complex_repo_task_acceptance.get("total_check_count"),
        "shared_contract_alignment": shared_contract_alignment,
        "shared_productization_contract_ready": shared_productization_contract_ready,
        "daily_driver_readiness": daily_driver_readiness,
        "daily_driver_main_path_ready": daily_driver_main_path_ready,
        "daily_driver_main_path_ready_cases": daily_driver_readiness["daily_driver_main_path_ready_cases"],
        "comparison_posture_basis": comparison_posture_basis,
        "comparison_proof_strength": comparison_proof_strength,
        "comparison_posture": comparison_posture,
        "comparison_grade_assessment": comparison_grade_assessment,
        "external_comparison_harness_surface": external_comparison_harness_surface,
        "planner_closure_posture": planner_closure_posture,
        "operator_planner_digest": operator_planner_digest,
        "comparative_planner_autonomy_summary": comparative_planner_autonomy_summary,
        "comparative_planner_candidate_summary": comparative_planner_candidate_summary,
        "operator_tool_digest": operator_tool_digest,
        "comparative_adapter_summary": comparative_adapter_summary,
        "adapter_unification_status": comparative_adapter_summary.get("unified_adapter_contract_ready"),
        "comparative_session_posture_summary": comparative_session_posture_summary,
        "comparative_session_continuity_summary": comparative_session_continuity_summary,
        "comparative_native_closure_summary": comparative_native_closure_summary,
        "clarify_boundary_digest": clarify_boundary_digest,
        "approval_boundary_digest": approval_boundary_digest,
        "comparative_daily_driver_summary": comparative_daily_driver_summary,
        "comparative_completion_summary": comparative_completion_summary,
        "long_chain_native_first_ready": (
            program_continuity.get("long_chain_native_first_ready")
            if isinstance(program_continuity.get("long_chain_native_first_ready"), bool)
            else bool(
                native_repo_task_acceptance.get("real_repo_task_acceptance_ready") is True
                and native_complex_repo_task_acceptance.get("complex_repo_task_ready") is True
                and native_task_proof.get("task_class") == "bounded_internal_repo_task"
            )
        ),
        "daily_driver_main_path_anchor": comparison_proof_strength.get("daily_driver_main_path_anchor"),
        "shared_evidence_surface": [
            "runtime_event_stream",
            "session_continuity",
            "session_productization_surface",
            "planner_closure_posture",
            "planner_autonomy_boundary",
            "planner_reasoning",
            "clarify_boundary_digest",
            "approval_boundary_digest",
            "operator_planner_digest",
            "native_tool_workflow_surface",
            "native_tool_productization_surface",
            "adapter_productization_surface",
            "adapter_capability_surface",
            "workspace_index",
            "ui_execution_summary",
            "cli_execution_summary",
            "adapter_shared_contract",
            "planner_shared_contract",
            "evidence_report",
        ],
    }


def build_runtime_comparative_benchmark_digest(benchmark: dict[str, object]) -> dict[str, object]:
    benchmark = benchmark if isinstance(benchmark, dict) else {}
    posture = benchmark.get("comparison_posture", {}) if isinstance(benchmark.get("comparison_posture"), dict) else {}
    posture_basis = (
        benchmark.get("comparison_posture_basis", {})
        if isinstance(benchmark.get("comparison_posture_basis"), dict)
        else {}
    )
    proof_strength = (
        benchmark.get("comparison_proof_strength", {})
        if isinstance(benchmark.get("comparison_proof_strength"), dict)
        else {}
    )
    comparison_grade = (
        benchmark.get("comparison_grade_assessment", {})
        if isinstance(benchmark.get("comparison_grade_assessment"), dict)
        else {}
    )
    harness_surface = (
        benchmark.get("external_comparison_harness_surface", {})
        if isinstance(benchmark.get("external_comparison_harness_surface"), dict)
        else comparison_grade.get("external_comparison_harness_surface", {})
        if isinstance(comparison_grade.get("external_comparison_harness_surface"), dict)
        else {}
    )
    requirements = (
        harness_surface.get("requirements", {})
        if isinstance(harness_surface.get("requirements"), dict)
        else {}
    )
    shared_surface = benchmark.get("shared_evidence_surface", [])
    native_tool_summary = (
        benchmark.get("comparative_native_tool_summary", {})
        if isinstance(benchmark.get("comparative_native_tool_summary"), dict)
        else {}
    )
    comparative_session_posture_summary = (
        benchmark.get("comparative_session_posture_summary", {})
        if isinstance(benchmark.get("comparative_session_posture_summary"), dict)
        else {}
    )
    comparative_session_continuity_summary = (
        benchmark.get("comparative_session_continuity_summary", {})
        if isinstance(benchmark.get("comparative_session_continuity_summary"), dict)
        else {}
    )
    operator_planner_digest = (
        benchmark.get("operator_planner_digest", {})
        if isinstance(benchmark.get("operator_planner_digest"), dict)
        else {}
    )
    operator_tool_digest = (
        benchmark.get("operator_tool_digest", {})
        if isinstance(benchmark.get("operator_tool_digest"), dict)
        else {}
    )
    planner_candidate_summary = (
        benchmark.get("comparative_planner_candidate_summary", {})
        if isinstance(benchmark.get("comparative_planner_candidate_summary"), dict)
        else {}
    )
    clarify_boundary_digest = (
        benchmark.get("clarify_boundary_digest", {})
        if isinstance(benchmark.get("clarify_boundary_digest"), dict)
        else {}
    )
    approval_boundary_digest = (
        benchmark.get("approval_boundary_digest", {})
        if isinstance(benchmark.get("approval_boundary_digest"), dict)
        else {}
    )
    daily_driver_case_matrix = (
        benchmark.get("daily_driver_case_matrix", {})
        if isinstance(benchmark.get("daily_driver_case_matrix"), dict)
        else {}
    )
    daily_driver_repeatability_harness = (
        benchmark.get("daily_driver_repeatability_harness", {})
        if isinstance(benchmark.get("daily_driver_repeatability_harness"), dict)
        else {}
    )
    daily_driver_runner_artifact = (
        benchmark.get("daily_driver_runner_artifact", {})
        if isinstance(benchmark.get("daily_driver_runner_artifact"), dict)
        else {}
    )
    return {
        "native_default_path": benchmark.get("native_default_path"),
        "native_task_class": benchmark.get("native_task_class"),
        "native_coverage_class": benchmark.get("native_coverage_class"),
        "case_count": benchmark.get("case_count"),
        "productization_case_count": benchmark.get("productization_case_count"),
        "long_chain_native_first_ready": benchmark.get("long_chain_native_first_ready"),
        "daily_driver_main_path_ready": benchmark.get("daily_driver_main_path_ready"),
        "daily_driver_main_path_anchor": benchmark.get("daily_driver_main_path_anchor"),
        "daily_driver_main_path_ready_cases": (
            posture_basis.get("daily_driver_main_path_ready_cases")
            if "daily_driver_main_path_ready_cases" in posture_basis
            else benchmark.get("daily_driver_main_path_ready_cases")
        ),
        "shared_productization_contract_ready": benchmark.get("shared_productization_contract_ready"),
        "comparison_status": posture.get("status"),
        "comparison_confidence": posture.get("confidence"),
        "foundation_gap_remaining": posture.get("foundation_gap_remaining"),
        "remaining_gap_classes": list(posture.get("remaining_gap_classes", []))
        if isinstance(posture.get("remaining_gap_classes"), list)
        else [],
        "planner_candidate_surface_ready": posture_basis.get("planner_candidate_surface_ready"),
        "planner_candidate_governed_alternative_count": posture_basis.get("planner_candidate_governed_alternative_count"),
        "unified_adapter_contract_ready": posture_basis.get("unified_adapter_contract_ready"),
        "evidence_scope": posture_basis.get("evidence_scope"),
        "comparison_limitations": list(posture_basis.get("comparison_limitations", []))
        if isinstance(posture_basis.get("comparison_limitations"), list)
        else [],
        "direct_proof_status": proof_strength.get("direct_proof_status"),
        "repeatability_status": proof_strength.get("repeatability_status"),
        "planner_candidate_status": proof_strength.get("planner_candidate_status"),
        "adapter_unification_status": proof_strength.get("adapter_unification_status"),
        "daily_driver_repeatability_tier": proof_strength.get("daily_driver_repeatability_tier"),
        "daily_driver_case_matrix_status": daily_driver_case_matrix.get("matrix_status"),
        "daily_driver_case_matrix_covered_family_count": daily_driver_case_matrix.get("covered_family_count"),
        "daily_driver_case_matrix_covered_case_count": daily_driver_case_matrix.get("covered_case_count"),
        "daily_driver_case_matrix_covered_families": list(daily_driver_case_matrix.get("covered_families", []))
        if isinstance(daily_driver_case_matrix.get("covered_families"), list)
        else [],
        "daily_driver_case_matrix_matrix_rows": list(daily_driver_case_matrix.get("matrix_rows", []))
        if isinstance(daily_driver_case_matrix.get("matrix_rows"), list)
        else [],
        "daily_driver_repeatability_harness_status": daily_driver_repeatability_harness.get("harness_status"),
        "daily_driver_repeatability_harness_passing_family_count": daily_driver_repeatability_harness.get("passing_family_count"),
        "daily_driver_repeatability_harness_failed_family_count": daily_driver_repeatability_harness.get("failed_family_count"),
        "daily_driver_repeatability_harness_contract_outputs": list(daily_driver_repeatability_harness.get("contract_outputs", []))
        if isinstance(daily_driver_repeatability_harness.get("contract_outputs"), list)
        else [],
        "daily_driver_runner_artifact_status": daily_driver_runner_artifact.get("runner_status"),
        "daily_driver_runner_artifact_family_count": daily_driver_runner_artifact.get("runner_family_count"),
        "daily_driver_runner_artifact_contract_outputs": list(daily_driver_runner_artifact.get("contract_outputs", []))
        if isinstance(daily_driver_runner_artifact.get("contract_outputs"), list)
        else [],
        "repeatability_ready": proof_strength.get("repeatability_ready"),
        "stronger_task_family_count": proof_strength.get("stronger_task_family_count"),
        "broader_task_family_count": proof_strength.get("broader_task_family_count"),
        "stronger_task_families": list(proof_strength.get("stronger_task_families", []))
        if isinstance(proof_strength.get("stronger_task_families"), list)
        else [],
        "daily_driver_main_path_anchor_family": proof_strength.get("daily_driver_main_path_anchor"),
        "repo_task_acceptance_families_proven": list(proof_strength.get("repo_task_acceptance_families_proven", []))
        if isinstance(proof_strength.get("repo_task_acceptance_families_proven"), list)
        else [],
        "repo_task_acceptance_family_count": proof_strength.get("repo_task_acceptance_family_count"),
        "daily_driver_repo_task_families_proven": list(proof_strength.get("daily_driver_repo_task_families_proven", []))
        if isinstance(proof_strength.get("daily_driver_repo_task_families_proven"), list)
        else [],
        "daily_driver_repo_task_family_count": proof_strength.get("daily_driver_repo_task_family_count"),
        "independent_daily_driver_repo_task_families_proven": list(
            proof_strength.get("independent_daily_driver_repo_task_families_proven", [])
        )
        if isinstance(proof_strength.get("independent_daily_driver_repo_task_families_proven"), list)
        else [],
        "independent_daily_driver_repo_task_family_count": proof_strength.get(
            "independent_daily_driver_repo_task_family_count"
        ),
        "session_posture_cases": benchmark.get("shared_contract_alignment", {}).get("session_posture_cases")
        if isinstance(benchmark.get("shared_contract_alignment"), dict)
        else None,
        "planner_closure_mode": benchmark.get("planner_closure_posture", {}).get("closure_mode")
        if isinstance(benchmark.get("planner_closure_posture"), dict)
        else None,
        "planner_next_recommended_action": benchmark.get("planner_closure_posture", {}).get("next_recommended_action")
        if isinstance(benchmark.get("planner_closure_posture"), dict)
        else None,
        "planner_resume_posture": benchmark.get("planner_closure_posture", {}).get("resume_posture")
        if isinstance(benchmark.get("planner_closure_posture"), dict)
        else None,
        "planner_verify_selected": benchmark.get("planner_closure_posture", {}).get("verify_selected")
        if isinstance(benchmark.get("planner_closure_posture"), dict)
        else None,
        "planner_verification_status": benchmark.get("planner_closure_posture", {}).get("verification_status")
        if isinstance(benchmark.get("planner_closure_posture"), dict)
        else None,
        "operator_planner_primary_action": operator_planner_digest.get("primary_action"),
        "operator_planner_selected_actions": list(operator_planner_digest.get("selected_actions", []))
        if isinstance(operator_planner_digest.get("selected_actions"), list)
        else [],
        "operator_planner_selected_executor": operator_planner_digest.get("selected_executor"),
        "operator_planner_closure_mode": operator_planner_digest.get("closure_mode"),
        "operator_planner_next_recommended_action": operator_planner_digest.get("next_recommended_action"),
        "operator_planner_resume_expectation": operator_planner_digest.get("resume_expectation"),
        "operator_planner_resume_posture": operator_planner_digest.get("resume_posture"),
        "operator_planner_pause_expected": operator_planner_digest.get("pause_expected"),
        "operator_planner_handoff_expected": operator_planner_digest.get("handoff_expected"),
        "operator_planner_fallback_expected": operator_planner_digest.get("fallback_expected"),
        "operator_planner_requires_human_confirmation": operator_planner_digest.get("requires_human_confirmation"),
        "operator_planner_decision_mode": operator_planner_digest.get("decision_mode"),
        "operator_planner_candidate_count": (
            operator_planner_digest.get("candidate_count")
            if operator_planner_digest.get("candidate_count") not in {None, 0}
            else len(planner_candidate_summary.get("decision_candidates", []))
            if isinstance(planner_candidate_summary.get("decision_candidates"), list)
            else operator_planner_digest.get("candidate_count")
        ),
        "operator_planner_governed_alternative_count": operator_planner_digest.get("governed_alternative_count"),
        "operator_planner_autonomy_selected_action_count": operator_planner_digest.get("autonomy_selected_action_count"),
        "operator_planner_autonomy_selected_actions": list(operator_planner_digest.get("autonomy_selected_actions", []))
        if isinstance(operator_planner_digest.get("autonomy_selected_actions"), list)
        else [],
        "operator_planner_native_first_contract_authoritative": operator_planner_digest.get(
            "native_first_contract_authoritative"
        ),
        "operator_planner_legacy_reference_used": operator_planner_digest.get("legacy_reference_used"),
        "planner_candidate_selected_strategy": planner_candidate_summary.get("selected_strategy"),
        "planner_candidate_native_first": planner_candidate_summary.get("native_first"),
        "planner_candidate_count": len(planner_candidate_summary.get("decision_candidates", []))
        if isinstance(planner_candidate_summary.get("decision_candidates"), list)
        else 0,
        "planner_candidate_governed_alternatives": len(planner_candidate_summary.get("governed_alternatives", []))
        if isinstance(planner_candidate_summary.get("governed_alternatives"), list)
        else 0,
        "planner_candidate_selected_action_count": planner_candidate_summary.get("action_coverage", {}).get(
            "selected_action_count"
        )
        if isinstance(planner_candidate_summary.get("action_coverage"), dict)
        else None,
        "planner_candidate_autonomy_selected_action_count": planner_candidate_summary.get("action_coverage", {}).get(
            "autonomy_selected_action_count"
        )
        if isinstance(planner_candidate_summary.get("action_coverage"), dict)
        else None,
        "planner_candidate_autonomy_selected_actions": list(
            planner_candidate_summary.get("action_coverage", {}).get("autonomy_selected_actions", [])
        )
        if isinstance(planner_candidate_summary.get("action_coverage"), dict)
        and isinstance(planner_candidate_summary.get("action_coverage", {}).get("autonomy_selected_actions"), list)
        else [],
        "operator_posture_next_recommended_action": comparative_session_posture_summary.get("next_recommended_action"),
        "operator_posture_resume_expectation": comparative_session_posture_summary.get("resume_expectation"),
        "operator_posture_resume_posture": comparative_session_posture_summary.get("resume_posture"),
        "operator_posture_recovery_lane": comparative_session_posture_summary.get("runbook_recovery_lane"),
        "operator_posture_approval_boundary_active": comparative_session_posture_summary.get("approval_boundary_active"),
        "operator_posture_compaction_stage": comparative_session_posture_summary.get("compaction_stage"),
        "operator_posture_compaction_pressure": comparative_session_posture_summary.get("compaction_pressure"),
        "operator_posture_workflow_active_stage": comparative_session_posture_summary.get("workflow_active_stage"),
        "operator_posture_selected_workflow_stages": list(comparative_session_posture_summary.get("selected_workflow_stages", []))
        if isinstance(comparative_session_posture_summary.get("selected_workflow_stages"), list)
        else [],
        "operator_posture_workflow_projection_ready": comparative_session_posture_summary.get("workflow_projection_ready"),
        "operator_posture_governed_alternatives": list(comparative_session_posture_summary.get("planner_governed_alternatives", []))
        if isinstance(comparative_session_posture_summary.get("planner_governed_alternatives"), list)
        else [],
        "session_continuity_resume_supported": comparative_session_continuity_summary.get("resume_supported"),
        "session_continuity_resume_kind": comparative_session_continuity_summary.get("resume_kind"),
        "session_continuity_resume_ready": comparative_session_continuity_summary.get("resume_ready"),
        "session_continuity_resume_posture": comparative_session_continuity_summary.get("resume_posture"),
        "session_continuity_recovery_active": comparative_session_continuity_summary.get("recovery_active"),
        "session_continuity_approval_boundary_active": comparative_session_continuity_summary.get("approval_boundary_active"),
        "session_continuity_governed_pause_resume_ready": comparative_session_continuity_summary.get("governed_pause_resume_ready"),
        "session_continuity_verification_resume_ready": comparative_session_continuity_summary.get("verification_resume_ready"),
        "session_continuity_compaction_stage": comparative_session_continuity_summary.get("compaction_stage"),
        "session_continuity_compaction_pressure": comparative_session_continuity_summary.get("compaction_pressure"),
        "session_continuity_context_pressure": comparative_session_continuity_summary.get("context_pressure"),
        "session_continuity_summarization_ready": comparative_session_continuity_summary.get("summarization_ready"),
        "session_continuity_runtime_duration_seconds": comparative_session_continuity_summary.get("runtime_duration_seconds"),
        "session_continuity_usage_cost_measurement_status": comparative_session_continuity_summary.get("usage_cost_measurement_status"),
        "session_continuity_pending_followup_count": comparative_session_continuity_summary.get("pending_followup_count"),
        "session_continuity_workflow_active_stage": comparative_session_continuity_summary.get("workflow_active_stage"),
        "session_continuity_selected_workflow_stages": list(comparative_session_continuity_summary.get("selected_workflow_stages", []))
        if isinstance(comparative_session_continuity_summary.get("selected_workflow_stages"), list)
        else [],
        "session_continuity_workflow_resume_ready": comparative_session_continuity_summary.get("workflow_resume_ready"),
        "session_continuity_workflow_projection_visible": comparative_session_continuity_summary.get("workflow_projection_visible"),
        "session_continuity_workflow_recovery_aligned": comparative_session_continuity_summary.get("workflow_recovery_aligned"),
        "operator_tool_posture": operator_tool_digest.get("tooling_posture"),
        "operator_tool_recent_tools": list(operator_tool_digest.get("recent_tools", []))
        if isinstance(operator_tool_digest.get("recent_tools"), list)
        else [],
        "operator_tool_explore_tools": list(operator_tool_digest.get("explore_tools", []))
        if isinstance(operator_tool_digest.get("explore_tools"), list)
        else [],
        "operator_tool_edit_tools": list(operator_tool_digest.get("edit_tools", []))
        if isinstance(operator_tool_digest.get("edit_tools"), list)
        else [],
        "operator_tool_verify_tools": list(operator_tool_digest.get("verify_tools", []))
        if isinstance(operator_tool_digest.get("verify_tools"), list)
        else [],
        "native_tool_summary": native_tool_summary.get("summary"),
        "native_tool_posture": native_tool_summary.get("tooling_posture"),
        "native_tool_bounded_read_search_ready": native_tool_summary.get("bounded_read_search_ready"),
        "native_tool_structured_patch_ready": native_tool_summary.get("structured_patch_ready"),
        "native_tool_verification_ready": native_tool_summary.get("verification_ready"),
        "native_tool_daily_driver_tools": list(native_tool_summary.get("daily_driver_tools", []))
        if isinstance(native_tool_summary.get("daily_driver_tools"), list)
        else [],
        "adapter_summary": (
            benchmark.get("comparative_adapter_summary", {}).get("summary")
            if isinstance(benchmark.get("comparative_adapter_summary"), dict)
            else None
        ),
        "adapter_surface_status": (
            benchmark.get("comparative_adapter_summary", {}).get("surface_status")
            if isinstance(benchmark.get("comparative_adapter_summary"), dict)
            else None
        ),
        "adapter_comparison_mode": (
            benchmark.get("comparative_adapter_summary", {}).get("comparison_mode")
            if isinstance(benchmark.get("comparative_adapter_summary"), dict)
            else None
        ),
        "adapter_hot_plug_supported": (
            benchmark.get("comparative_adapter_summary", {}).get("hot_plug_supported")
            if isinstance(benchmark.get("comparative_adapter_summary"), dict)
            else None
        ),
        "adapter_fallback_governed": (
            benchmark.get("comparative_adapter_summary", {}).get("fallback_governed")
            if isinstance(benchmark.get("comparative_adapter_summary"), dict)
            else None
        ),
        "adapter_resume_contract_supported": (
            benchmark.get("comparative_adapter_summary", {}).get("resume_contract_supported")
            if isinstance(benchmark.get("comparative_adapter_summary"), dict)
            else None
        ),
        "broader_repeatability_gap_families": list(proof_strength.get("broader_repeatability_gap_families", []))
        if isinstance(proof_strength.get("broader_repeatability_gap_families"), list)
        else [],
        "proof_limitations": list(proof_strength.get("proof_limitations", []))
        if isinstance(proof_strength.get("proof_limitations"), list)
        else [],
        "comparison_grade_status": comparison_grade.get("status"),
        "comparison_grade_ready": comparison_grade.get("comparison_grade_ready"),
        "internal_repeatability_ready": comparison_grade.get("internal_repeatability_ready"),
        "external_harness_ready": comparison_grade.get("external_harness_ready"),
        "external_harness_status": comparison_grade.get("external_harness_status")
        or harness_surface.get("harness_status"),
        "external_harness_next_milestone": harness_surface.get("next_evidence_milestone"),
        "external_harness_operator_action": harness_surface.get("operator_action"),
        "external_harness_required_shared_surface_count": harness_surface.get("required_shared_surface_count"),
        "external_harness_required_external_artifact_count": harness_surface.get("required_external_artifact_count"),
        "external_harness_missing_external_artifact_count": harness_surface.get("missing_external_artifact_count"),
        "external_harness_missing_artifacts": list(requirements.get("missing_external_artifacts", []))
        if isinstance(requirements.get("missing_external_artifacts"), list)
        else [],
        "blocking_gap": comparison_grade.get("blocking_gap"),
        "clarify_boundary_status": clarify_boundary_digest.get("status"),
        "clarify_boundary_active": bool(clarify_boundary_digest),
        "clarify_boundary_next_action": clarify_boundary_digest.get("next_recommended_action"),
        "clarify_boundary_resume_expectation": clarify_boundary_digest.get("resume_expectation"),
        "approval_boundary_status": approval_boundary_digest.get("status"),
        "approval_boundary_active": bool(approval_boundary_digest),
        "approval_boundary_next_action": approval_boundary_digest.get("next_recommended_action"),
        "approval_boundary_resume_expectation": approval_boundary_digest.get("resume_expectation"),
        "shared_evidence_surface": list(shared_surface) if isinstance(shared_surface, list) else [],
    }


def build_comparative_native_tool_summary(
    *,
    native_tool_productization_surface: dict[str, object],
    native_tool_workflow_surface: dict[str, object] | None = None,
) -> dict[str, object]:
    native_tool_productization_surface = (
        native_tool_productization_surface
        if isinstance(native_tool_productization_surface, dict)
        else {}
    )
    native_tool_workflow_surface = (
        native_tool_workflow_surface if isinstance(native_tool_workflow_surface, dict) else {}
    )
    if not native_tool_workflow_surface:
        native_tool_workflow_surface = (
            native_tool_productization_surface.get("workflow_surface", {})
            if isinstance(native_tool_productization_surface.get("workflow_surface"), dict)
            else {}
        )
    readiness = (
        native_tool_productization_surface.get("readiness", {})
        if isinstance(native_tool_productization_surface.get("readiness"), dict)
        else {}
    )
    daily_driver_path = (
        native_tool_workflow_surface.get("daily_driver_path", {})
        if isinstance(native_tool_workflow_surface.get("daily_driver_path"), dict)
        else {}
    )
    if not native_tool_productization_surface and not native_tool_workflow_surface:
        return {}
    return {
        "format": "agent_orchestrator.comparative_native_tool_summary.v1",
        "tooling_posture": native_tool_productization_surface.get("tooling_posture"),
        "operator_visibility_ready": native_tool_productization_surface.get("operator_visibility_ready"),
        "usage_visibility_ready": native_tool_productization_surface.get("usage_visibility_ready"),
        "repo_exploration_ready": readiness.get("repo_exploration_ready"),
        "bounded_read_search_ready": readiness.get("bounded_read_search_ready"),
        "glob_ready": readiness.get("glob_ready"),
        "structured_patch_ready": readiness.get("structured_patch_ready"),
        "patch_preview_ready": readiness.get("patch_preview_ready"),
        "diff_preview_ready": readiness.get("diff_preview_ready"),
        "verification_ready": readiness.get("verification_ready"),
        "daily_driver_tools": list(daily_driver_path.get("tools", []))
        if isinstance(daily_driver_path.get("tools"), list)
        else [],
        "summary": (
            f"posture={native_tool_productization_surface.get('tooling_posture')} "
            f"read_search={readiness.get('bounded_read_search_ready')} "
            f"patch={readiness.get('structured_patch_ready')} "
            f"verify={readiness.get('verification_ready')} "
            f"daily_driver={','.join(str(item) for item in daily_driver_path.get('tools', [])) if isinstance(daily_driver_path.get('tools'), list) and daily_driver_path.get('tools') else 'none'}"
        ),
    }


def build_comparative_adapter_summary(
    *,
    adapter_productization_surface: dict[str, object],
    adapter_shared_contract: dict[str, object] | None = None,
    adapter_capability_surface: dict[str, object] | None = None,
) -> dict[str, object]:
    adapter_productization_surface = (
        adapter_productization_surface
        if isinstance(adapter_productization_surface, dict)
        else {}
    )
    adapter_shared_contract = (
        adapter_shared_contract if isinstance(adapter_shared_contract, dict) else {}
    )
    adapter_capability_surface = (
        adapter_capability_surface if isinstance(adapter_capability_surface, dict) else {}
    )
    if (
        not adapter_productization_surface
        and not adapter_shared_contract
        and not adapter_capability_surface
    ):
        return {}
    recovery_contract = (
        adapter_shared_contract.get("recovery_contract", {})
        if isinstance(adapter_shared_contract.get("recovery_contract"), dict)
        else {}
    )
    evidence_outputs = (
        adapter_shared_contract.get("evidence_outputs", [])
        if isinstance(adapter_shared_contract.get("evidence_outputs"), list)
        else adapter_capability_surface.get("evidence_outputs", [])
        if isinstance(adapter_capability_surface.get("evidence_outputs"), list)
        else []
    )
    recovery_surfaces = (
        adapter_shared_contract.get("recovery_surfaces", [])
        if isinstance(adapter_shared_contract.get("recovery_surfaces"), list)
        else adapter_capability_surface.get("recovery_surfaces", [])
        if isinstance(adapter_capability_surface.get("recovery_surfaces"), list)
        else []
    )
    unified_adapter_contract_ready = bool(
        adapter_productization_surface.get("surface_status") == "same_contract_two_executors_governed"
        and adapter_productization_surface.get("comparison_mode") == "same_contract_two_executors"
        and adapter_productization_surface.get("resume_contract_supported") is True
        and adapter_productization_surface.get("governed_recovery_ready") is True
        and adapter_shared_contract.get("comparison_mode") == "same_contract_two_executors"
        and adapter_shared_contract.get("default_path") == "native"
        and adapter_shared_contract.get("hot_plug_supported") is True
        and isinstance(adapter_shared_contract.get("shared_evidence_surface"), list)
        and "workspace_index" in adapter_shared_contract.get("shared_evidence_surface", [])
        and "ui_execution_summary" in adapter_shared_contract.get("shared_evidence_surface", [])
        and isinstance(adapter_shared_contract.get("operator_visibility_contract"), dict)
        and adapter_shared_contract.get("operator_visibility_contract", {}).get("session_surface_required") is True
        and adapter_shared_contract.get("operator_visibility_contract", {}).get("planner_surface_required") is True
        and adapter_shared_contract.get("operator_visibility_contract", {}).get("tool_surface_required") is True
        and isinstance(adapter_shared_contract.get("tooling_contract"), dict)
        and adapter_shared_contract.get("tooling_contract", {}).get("workflow_projection_required") is True
        and adapter_capability_surface.get("format") == "agent_orchestrator.adapter_capability_surface.v1"
    )
    return {
        "format": "agent_orchestrator.comparative_adapter_summary.v1",
        "surface_status": adapter_productization_surface.get("surface_status"),
        "comparison_mode": adapter_productization_surface.get("comparison_mode")
        or adapter_shared_contract.get("comparison_mode"),
        "hot_plug_supported": adapter_productization_surface.get("hot_plug_supported")
        if "hot_plug_supported" in adapter_productization_surface
        else adapter_shared_contract.get("hot_plug_supported"),
        "fallback_governed": adapter_productization_surface.get("fallback_governed")
        if "fallback_governed" in adapter_productization_surface
        else adapter_shared_contract.get("fallback_governed"),
        "resume_contract_supported": adapter_productization_surface.get("resume_contract_supported")
        if "resume_contract_supported" in adapter_productization_surface
        else adapter_shared_contract.get("shared_contract_resume_supported"),
        "governed_recovery_ready": adapter_productization_surface.get("governed_recovery_ready"),
        "shared_contract_format": adapter_productization_surface.get("shared_contract_format")
        or adapter_shared_contract.get("shared_contract_format"),
        "default_path": adapter_shared_contract.get("default_path"),
        "ownership_boundary": adapter_shared_contract.get("operating_boundary"),
        "fallback_allowed": recovery_contract.get("fallback_allowed"),
        "handoff_allowed": recovery_contract.get("handoff_allowed"),
        "resume_continuity_required": recovery_contract.get("resume_continuity_required"),
        "shared_evidence_surface": list(adapter_shared_contract.get("shared_evidence_surface", []))
        if isinstance(adapter_shared_contract.get("shared_evidence_surface"), list)
        else [],
        "operator_visibility_contract": dict(adapter_shared_contract.get("operator_visibility_contract", {}))
        if isinstance(adapter_shared_contract.get("operator_visibility_contract"), dict)
        else {},
        "tooling_contract": dict(adapter_shared_contract.get("tooling_contract", {}))
        if isinstance(adapter_shared_contract.get("tooling_contract"), dict)
        else {},
        "unified_adapter_contract_ready": unified_adapter_contract_ready,
        "evidence_outputs": list(evidence_outputs),
        "recovery_surfaces": list(recovery_surfaces),
        "summary": (
            f"status={adapter_productization_surface.get('surface_status')} "
            f"comparison_mode={adapter_productization_surface.get('comparison_mode') or adapter_shared_contract.get('comparison_mode')} "
            f"hot_plug={adapter_productization_surface.get('hot_plug_supported') if 'hot_plug_supported' in adapter_productization_surface else adapter_shared_contract.get('hot_plug_supported')} "
            f"fallback_governed={adapter_productization_surface.get('fallback_governed') if 'fallback_governed' in adapter_productization_surface else adapter_shared_contract.get('fallback_governed')} "
            f"resume_supported={adapter_productization_surface.get('resume_contract_supported') if 'resume_contract_supported' in adapter_productization_surface else adapter_shared_contract.get('shared_contract_resume_supported')} "
            f"recovery_ready={adapter_productization_surface.get('governed_recovery_ready')} "
            f"default_path={adapter_shared_contract.get('default_path')} "
            f"boundary={adapter_shared_contract.get('operating_boundary')} "
            f"unified_contract={unified_adapter_contract_ready}"
        ),
    }


def build_comparative_session_posture_summary(
    *,
    session_productization_surface: dict[str, object],
    planner_decision: dict[str, object] | None = None,
    continuity_outline: dict[str, object] | None = None,
) -> dict[str, object]:
    session_productization_surface = (
        session_productization_surface
        if isinstance(session_productization_surface, dict)
        else {}
    )
    planner_decision = planner_decision if isinstance(planner_decision, dict) else {}
    continuity_outline = continuity_outline if isinstance(continuity_outline, dict) else {}
    if not session_productization_surface and not planner_decision and not continuity_outline:
        return {}
    planner_posture = (
        planner_decision.get("autonomy_posture", {})
        if isinstance(planner_decision.get("autonomy_posture"), dict)
        else {}
    )
    continuity_posture = (
        continuity_outline.get("autonomy_posture", {})
        if isinstance(continuity_outline.get("autonomy_posture"), dict)
        else {}
    )
    productization_posture = (
        session_productization_surface.get("autonomy_posture", {})
        if isinstance(session_productization_surface.get("autonomy_posture"), dict)
        else {}
    )
    operator_continuity = (
        session_productization_surface.get("operator_continuity", {})
        if isinstance(session_productization_surface.get("operator_continuity"), dict)
        else {}
    )
    operator_posture_digest = (
        session_productization_surface.get("operator_posture_digest", {})
        if isinstance(session_productization_surface.get("operator_posture_digest"), dict)
        else {}
    )
    workflow_continuity = (
        session_productization_surface.get("workflow_continuity", {})
        if isinstance(session_productization_surface.get("workflow_continuity"), dict)
        else {}
    )
    return {
        "format": "agent_orchestrator.comparative_session_posture_summary.v1",
        "planner_family": planner_decision.get("planner_family") or continuity_outline.get("planner_family"),
        "primary_action": planner_posture.get("primary_action") or continuity_posture.get("primary_action"),
        "pause_expected": (
            planner_posture.get("pause_expected")
            if "pause_expected" in planner_posture
            else continuity_posture.get("pause_expected")
        ),
        "handoff_expected": (
            planner_posture.get("handoff_expected")
            if "handoff_expected" in planner_posture
            else continuity_posture.get("handoff_expected")
        ),
        "fallback_expected": (
            planner_posture.get("fallback_expected")
            if "fallback_expected" in planner_posture
            else continuity_posture.get("fallback_expected")
        ),
        "clarify_pause_state": planner_posture.get("clarify_pause_state"),
        "approval_pause_state": planner_posture.get("approval_pause_state"),
        "approval_boundary_active": (
            operator_posture_digest.get("approval_boundary_active")
            if "approval_boundary_active" in operator_posture_digest
            else bool(planner_posture.get("approval_pause_state"))
        ),
        "resume_expectation": (
            operator_posture_digest.get("resume_expectation")
            or planner_decision.get("delegation_contract", {}).get("resume_expectation")
            if isinstance(planner_decision.get("delegation_contract"), dict)
            else continuity_outline.get("resume_expectation")
        ),
        "resume_posture": operator_posture_digest.get("resume_posture")
        or productization_posture.get("resume_posture")
        or continuity_posture.get("resume_posture"),
        "next_recommended_action": operator_posture_digest.get("next_recommended_action")
        or operator_continuity.get("next_recommended_action")
        or continuity_outline.get("next_recommended_action")
        or planner_posture.get("primary_action"),
        "runbook_recovery_lane": operator_posture_digest.get("runbook_recovery_lane")
        or operator_continuity.get("runbook_recovery_lane"),
        "workflow_active_stage": operator_posture_digest.get("workflow_active_stage")
        or operator_continuity.get("workflow_active_stage")
        or workflow_continuity.get("active_stage"),
        "selected_workflow_stages": (
            [str(item) for item in operator_posture_digest.get("selected_workflow_stages", []) if item not in {None, ""}]
            if isinstance(operator_posture_digest.get("selected_workflow_stages"), list)
            else [str(item) for item in operator_continuity.get("selected_workflow_stages", []) if item not in {None, ""}]
            if isinstance(operator_continuity.get("selected_workflow_stages"), list)
            else [str(item) for item in workflow_continuity.get("selected_workflow_stages", []) if item not in {None, ""}]
            if isinstance(workflow_continuity.get("selected_workflow_stages"), list)
            else []
        ),
        "workflow_projection_ready": (
            operator_posture_digest.get("workflow_projection_ready")
            if "workflow_projection_ready" in operator_posture_digest
            else operator_continuity.get("workflow_projection_ready")
            if "workflow_projection_ready" in operator_continuity
            else workflow_continuity.get("workflow_projection_ready")
        ),
        "compaction_stage": operator_posture_digest.get("compaction_stage"),
        "compaction_pressure": operator_posture_digest.get("compaction_pressure"),
        "context_pressure": operator_posture_digest.get("context_pressure"),
        "summarization_ready": operator_posture_digest.get("summarization_ready"),
        "runtime_duration_seconds": operator_posture_digest.get("runtime_duration_seconds"),
        "usage_cost_measurement_status": operator_posture_digest.get("usage_cost_measurement_status"),
        "runtime_cost_provenance": (
            dict(operator_posture_digest.get("runtime_cost_provenance", {}))
            if isinstance(operator_posture_digest.get("runtime_cost_provenance"), dict)
            else {}
        ),
        "planner_governed_alternatives": (
            [dict(item) for item in operator_posture_digest.get("planner_governed_alternatives", []) if isinstance(item, dict)]
            if isinstance(operator_posture_digest.get("planner_governed_alternatives"), list)
            else [dict(item) for item in operator_continuity.get("planner_governed_alternatives", []) if isinstance(item, dict)]
            if isinstance(operator_continuity.get("planner_governed_alternatives"), list)
            else []
        ),
        "operator_posture_digest": operator_posture_digest,
        "summary": (
            f"primary={planner_posture.get('primary_action') or continuity_posture.get('primary_action')} "
            f"pause_expected={planner_posture.get('pause_expected') if 'pause_expected' in planner_posture else continuity_posture.get('pause_expected')} "
            f"handoff_expected={planner_posture.get('handoff_expected') if 'handoff_expected' in planner_posture else continuity_posture.get('handoff_expected')} "
            f"fallback_expected={planner_posture.get('fallback_expected') if 'fallback_expected' in planner_posture else continuity_posture.get('fallback_expected')} "
            f"clarify_pause={planner_posture.get('clarify_pause_state')} "
            f"approval_pause={planner_posture.get('approval_pause_state')} "
            f"approval_boundary_active={(operator_posture_digest.get('approval_boundary_active') if 'approval_boundary_active' in operator_posture_digest else bool(planner_posture.get('approval_pause_state')))} "
            f"resume_expectation={(operator_posture_digest.get('resume_expectation') or (planner_decision.get('delegation_contract', {}).get('resume_expectation') if isinstance(planner_decision.get('delegation_contract'), dict) else continuity_outline.get('resume_expectation')))} "
            f"resume_posture={operator_posture_digest.get('resume_posture') or productization_posture.get('resume_posture') or continuity_posture.get('resume_posture')} "
            f"next_action={operator_posture_digest.get('next_recommended_action') or operator_continuity.get('next_recommended_action') or continuity_outline.get('next_recommended_action') or planner_posture.get('primary_action')} "
            f"recovery_lane={operator_posture_digest.get('runbook_recovery_lane') or operator_continuity.get('runbook_recovery_lane')} "
            f"workflow_stage={(operator_posture_digest.get('workflow_active_stage') or operator_continuity.get('workflow_active_stage') or workflow_continuity.get('active_stage'))} "
            f"workflow_selected={','.join(str(item) for item in (([str(item) for item in operator_posture_digest.get('selected_workflow_stages', []) if item not in {None, ''}] if isinstance(operator_posture_digest.get('selected_workflow_stages'), list) else [str(item) for item in operator_continuity.get('selected_workflow_stages', []) if item not in {None, ''}] if isinstance(operator_continuity.get('selected_workflow_stages'), list) else [str(item) for item in workflow_continuity.get('selected_workflow_stages', []) if item not in {None, ''}] if isinstance(workflow_continuity.get('selected_workflow_stages'), list) else [])) or ['none'])} "
            f"workflow_projection_ready={(operator_posture_digest.get('workflow_projection_ready') if 'workflow_projection_ready' in operator_posture_digest else operator_continuity.get('workflow_projection_ready') if 'workflow_projection_ready' in operator_continuity else workflow_continuity.get('workflow_projection_ready'))} "
            f"alternatives={','.join(str(item.get('action')) for item in (([dict(item) for item in operator_posture_digest.get('planner_governed_alternatives', []) if isinstance(item, dict)] if isinstance(operator_posture_digest.get('planner_governed_alternatives'), list) else [dict(item) for item in operator_continuity.get('planner_governed_alternatives', []) if isinstance(item, dict)] if isinstance(operator_continuity.get('planner_governed_alternatives'), list) else [])) if item.get('action')) or 'none'} "
            f"compaction_stage={operator_posture_digest.get('compaction_stage')} "
            f"compaction_pressure={operator_posture_digest.get('compaction_pressure')} "
            f"context_pressure={operator_posture_digest.get('context_pressure')} "
            f"summarization_ready={operator_posture_digest.get('summarization_ready')} "
            f"runtime_duration_seconds={operator_posture_digest.get('runtime_duration_seconds')} "
            f"usage_cost_status={operator_posture_digest.get('usage_cost_measurement_status')}"
        ),
    }


def build_comparative_session_continuity_summary(
    *,
    session_productization_surface: dict[str, object],
    continuity_outline: dict[str, object] | None = None,
    comparative_shared_evidence_surface: list[object] | None = None,
) -> dict[str, object]:
    session_productization_surface = (
        session_productization_surface if isinstance(session_productization_surface, dict) else {}
    )
    continuity_outline = continuity_outline if isinstance(continuity_outline, dict) else {}
    if not session_productization_surface and not continuity_outline:
        return {}
    continuity_readiness = (
        session_productization_surface.get("continuity_readiness", {})
        if isinstance(session_productization_surface.get("continuity_readiness"), dict)
        else {}
    )
    operator_continuity = (
        session_productization_surface.get("operator_continuity", {})
        if isinstance(session_productization_surface.get("operator_continuity"), dict)
        else {}
    )
    operator_posture_digest = (
        session_productization_surface.get("operator_posture_digest", {})
        if isinstance(session_productization_surface.get("operator_posture_digest"), dict)
        else {}
    )
    long_horizon_posture = (
        session_productization_surface.get("long_horizon_posture", {})
        if isinstance(session_productization_surface.get("long_horizon_posture"), dict)
        else {}
    )
    workflow_continuity = (
        session_productization_surface.get("workflow_continuity", {})
        if isinstance(session_productization_surface.get("workflow_continuity"), dict)
        else {}
    )
    runtime_cost_provenance = (
        dict(session_productization_surface.get("runtime_cost_provenance", {}))
        if isinstance(session_productization_surface.get("runtime_cost_provenance"), dict)
        else {}
    )
    continuity_autonomy_posture = (
        continuity_outline.get("autonomy_posture", {})
        if isinstance(continuity_outline.get("autonomy_posture"), dict)
        else {}
    )
    planner_governed_alternatives = (
        [dict(item) for item in operator_posture_digest.get("planner_governed_alternatives", []) if isinstance(item, dict)]
        if isinstance(operator_posture_digest.get("planner_governed_alternatives"), list)
        else [dict(item) for item in operator_continuity.get("planner_governed_alternatives", []) if isinstance(item, dict)]
        if isinstance(operator_continuity.get("planner_governed_alternatives"), list)
        else []
    )
    approval_boundary_active = bool(
        operator_posture_digest.get("approval_boundary_active")
        if "approval_boundary_active" in operator_posture_digest
        else operator_continuity.get("approval_boundary_active")
        if "approval_boundary_active" in operator_continuity
        else False
    )
    long_horizon_continuity_ready = (
        bool(session_productization_surface.get("resume_supported"))
        and bool(continuity_readiness.get("resume_ready"))
        and bool(continuity_readiness.get("runtime_cost_ready"))
        and bool(continuity_readiness.get("compaction_ready"))
    )
    long_horizon_continuity_judgment = (
        "daily_driver_continuity_governed_approval_boundary"
        if long_horizon_continuity_ready and approval_boundary_active
        else "daily_driver_continuity_ready"
        if long_horizon_continuity_ready
        and bool(long_horizon_posture.get("recovery_active")) is not True
        else "daily_driver_continuity_partial"
        if bool(session_productization_surface.get("resume_supported"))
        else "daily_driver_continuity_missing"
    )
    return {
        "format": "agent_orchestrator.comparative_session_continuity_summary.v1",
        "continuity_status": session_productization_surface.get("continuity_status"),
        "resume_supported": session_productization_surface.get("resume_supported"),
        "resume_kind": session_productization_surface.get("resume_kind"),
        "resume_ready": continuity_readiness.get("resume_ready"),
        "resume_posture": operator_posture_digest.get("resume_posture")
        or long_horizon_posture.get("resume_posture")
        or continuity_autonomy_posture.get("resume_posture"),
        "recovery_ready": continuity_readiness.get("recovery_ready"),
        "recovery_active": long_horizon_posture.get("recovery_active"),
        "approval_boundary_active": approval_boundary_active,
        "governed_pause_resume_ready": continuity_readiness.get("governed_pause_resume_ready"),
        "verification_resume_ready": long_horizon_posture.get("verification_resume_ready"),
        "compaction_ready": continuity_readiness.get("compaction_ready"),
        "compaction_stage": session_productization_surface.get("compaction_stage"),
        "compaction_pressure": operator_posture_digest.get("compaction_pressure"),
        "context_pressure": (
            operator_posture_digest.get("context_pressure")
            if "context_pressure" in operator_posture_digest
            else long_horizon_posture.get("context_pressure")
        ),
        "summarization_ready": (
            operator_posture_digest.get("summarization_ready")
            if "summarization_ready" in operator_posture_digest
            else long_horizon_posture.get("summarization_ready")
        ),
        "pressure_visible": continuity_readiness.get("pressure_visible"),
        "pending_followup_count": long_horizon_posture.get("pending_followup_count"),
        "runtime_cost_ready": continuity_readiness.get("runtime_cost_ready"),
        "runtime_duration_seconds": session_productization_surface.get("runtime_duration_seconds"),
        "usage_cost_measurement_status": session_productization_surface.get("usage_cost_measurement_status"),
        "runtime_cost_provenance": runtime_cost_provenance,
        "workflow_active_stage": operator_posture_digest.get("workflow_active_stage")
        or operator_continuity.get("workflow_active_stage")
        or workflow_continuity.get("active_stage"),
        "selected_workflow_stages": (
            [str(item) for item in operator_posture_digest.get("selected_workflow_stages", []) if item not in {None, ""}]
            if isinstance(operator_posture_digest.get("selected_workflow_stages"), list)
            else [str(item) for item in operator_continuity.get("selected_workflow_stages", []) if item not in {None, ""}]
            if isinstance(operator_continuity.get("selected_workflow_stages"), list)
            else [str(item) for item in workflow_continuity.get("selected_workflow_stages", []) if item not in {None, ""}]
            if isinstance(workflow_continuity.get("selected_workflow_stages"), list)
            else []
        ),
        "workflow_resume_ready": continuity_readiness.get("workflow_resume_ready"),
        "workflow_projection_visible": continuity_readiness.get("workflow_projection_visible"),
        "workflow_recovery_aligned": continuity_readiness.get("workflow_recovery_aligned"),
        "workflow_projection_ready": (
            operator_posture_digest.get("workflow_projection_ready")
            if "workflow_projection_ready" in operator_posture_digest
            else operator_continuity.get("workflow_projection_ready")
            if "workflow_projection_ready" in operator_continuity
            else workflow_continuity.get("workflow_projection_ready")
        ),
        "long_horizon_continuity_ready": long_horizon_continuity_ready,
        "long_horizon_continuity_judgment": long_horizon_continuity_judgment,
        "next_recommended_action": operator_posture_digest.get("next_recommended_action")
        or operator_continuity.get("next_recommended_action")
        or continuity_outline.get("next_recommended_action"),
        "runbook_recovery_lane": operator_posture_digest.get("runbook_recovery_lane")
        or operator_continuity.get("runbook_recovery_lane"),
        "latest_recovery_hint": operator_posture_digest.get("latest_recovery_hint")
        or operator_continuity.get("latest_recovery_hint"),
        "planner_governed_alternatives": planner_governed_alternatives,
        "summary": (
            f"status={session_productization_surface.get('continuity_status')} "
            f"resume_supported={session_productization_surface.get('resume_supported')} "
            f"resume_kind={session_productization_surface.get('resume_kind')} "
            f"resume_ready={continuity_readiness.get('resume_ready')} "
            f"resume_posture={(operator_posture_digest.get('resume_posture') or long_horizon_posture.get('resume_posture') or continuity_autonomy_posture.get('resume_posture'))} "
            f"recovery_ready={continuity_readiness.get('recovery_ready')} "
            f"recovery_active={long_horizon_posture.get('recovery_active')} "
            f"approval_boundary_active={approval_boundary_active} "
            f"governed_pause_resume_ready={continuity_readiness.get('governed_pause_resume_ready')} "
            f"verification_resume_ready={long_horizon_posture.get('verification_resume_ready')} "
            f"compaction_stage={session_productization_surface.get('compaction_stage')} "
            f"compaction_pressure={operator_posture_digest.get('compaction_pressure')} "
            f"context_pressure={(operator_posture_digest.get('context_pressure') if 'context_pressure' in operator_posture_digest else long_horizon_posture.get('context_pressure'))} "
            f"summarization_ready={(operator_posture_digest.get('summarization_ready') if 'summarization_ready' in operator_posture_digest else long_horizon_posture.get('summarization_ready'))} "
            f"runtime_duration_seconds={session_productization_surface.get('runtime_duration_seconds')} "
            f"usage_cost_status={session_productization_surface.get('usage_cost_measurement_status')} "
            f"duration_source={runtime_cost_provenance.get('duration_source')} "
            f"workflow_stage={(operator_posture_digest.get('workflow_active_stage') or operator_continuity.get('workflow_active_stage') or workflow_continuity.get('active_stage'))} "
            f"workflow_selected={','.join(str(item) for item in (([str(item) for item in operator_posture_digest.get('selected_workflow_stages', []) if item not in {None, ''}] if isinstance(operator_posture_digest.get('selected_workflow_stages'), list) else [str(item) for item in operator_continuity.get('selected_workflow_stages', []) if item not in {None, ''}] if isinstance(operator_continuity.get('selected_workflow_stages'), list) else [str(item) for item in workflow_continuity.get('selected_workflow_stages', []) if item not in {None, ''}] if isinstance(workflow_continuity.get('selected_workflow_stages'), list) else [])) or ['none'])} "
            f"workflow_resume_ready={continuity_readiness.get('workflow_resume_ready')} "
            f"workflow_projection_visible={continuity_readiness.get('workflow_projection_visible')} "
            f"workflow_recovery_aligned={continuity_readiness.get('workflow_recovery_aligned')} "
            f"long_horizon_ready={long_horizon_continuity_ready} "
            f"long_horizon_judgment={long_horizon_continuity_judgment} "
            f"next_action={(operator_posture_digest.get('next_recommended_action') or operator_continuity.get('next_recommended_action') or continuity_outline.get('next_recommended_action'))}"
        ),
        "shared_evidence_surface": list(
            dict.fromkeys(
                [
                    "runtime_event_stream",
                    "session_continuity",
                    "session_productization_surface",
                    "runtime_cost",
                    "runtime_cost_provenance",
                    "workspace_index",
                    "ui_execution_summary",
                    "cli_execution_summary",
                    "evidence_report",
                    *[str(item) for item in (comparative_shared_evidence_surface or []) if isinstance(item, str)],
                ]
            )
        ),
    }


def build_comparative_planner_autonomy_summary(
    *,
    planner_shared_contract: dict[str, object],
    operator_planner_digest: dict[str, object] | None = None,
    comparative_shared_evidence_surface: list[object] | None = None,
) -> dict[str, object]:
    planner_shared_contract = (
        planner_shared_contract if isinstance(planner_shared_contract, dict) else {}
    )
    operator_planner_digest = operator_planner_digest if isinstance(operator_planner_digest, dict) else {}
    if not planner_shared_contract and not operator_planner_digest:
        return {}
    autonomy_boundary = (
        planner_shared_contract.get("autonomy_boundary", {})
        if isinstance(planner_shared_contract.get("autonomy_boundary"), dict)
        else {}
    )
    planner_reasoning = (
        planner_shared_contract.get("planner_reasoning", {})
        if isinstance(planner_shared_contract.get("planner_reasoning"), dict)
        else {}
    )
    autonomy_surface = (
        planner_shared_contract.get("autonomy_surface", {})
        if isinstance(planner_shared_contract.get("autonomy_surface"), dict)
        else {}
    )
    tool_workflow_plan = (
        planner_shared_contract.get("tool_workflow_plan", {})
        if isinstance(planner_shared_contract.get("tool_workflow_plan"), dict)
        else {}
    )
    operator_control = (
        planner_shared_contract.get("operator_control", {})
        if isinstance(planner_shared_contract.get("operator_control"), dict)
        else {}
    )
    decision_boundary = (
        planner_shared_contract.get("decision_boundary", {})
        if isinstance(planner_shared_contract.get("decision_boundary"), dict)
        else {}
    )
    return {
        "format": "agent_orchestrator.comparative_planner_autonomy_summary.v1",
        "planner_family": planner_shared_contract.get("planner_family") or operator_planner_digest.get("planner_family"),
        "selected_strategy": planner_shared_contract.get("selected_strategy") or operator_planner_digest.get("selected_execution_strategy"),
        "selected_owner": planner_shared_contract.get("selected_owner") or operator_planner_digest.get("selected_executor"),
        "primary_action": planner_reasoning.get("primary_action") or operator_planner_digest.get("primary_action"),
        "native_first": (
            planner_reasoning.get("native_first")
            if "native_first" in planner_reasoning
            else autonomy_boundary.get("native_first")
        ),
        "autonomy_boundary": autonomy_boundary,
        "planner_reasoning": planner_reasoning,
        "autonomy_surface": autonomy_surface,
        "decision_boundary": decision_boundary,
        "next_recommended_action": operator_control.get("next_recommended_action") or operator_planner_digest.get("next_recommended_action"),
        "resume_posture": operator_planner_digest.get("resume_posture"),
        "summary": (
            f"native_first={planner_reasoning.get('native_first') if 'native_first' in planner_reasoning else autonomy_boundary.get('native_first')} "
            f"primary={planner_reasoning.get('primary_action') or operator_planner_digest.get('primary_action')} "
            f"clarify={autonomy_boundary.get('requires_clarify')} "
            f"pause={autonomy_boundary.get('requires_pause')} "
            f"handoff={autonomy_boundary.get('requires_handoff')} "
            f"fallback={autonomy_boundary.get('requires_fallback')} "
            f"explore={autonomy_boundary.get('requires_explore')} "
            f"edit={autonomy_boundary.get('requires_edit')} "
            f"verify={autonomy_boundary.get('requires_verify')} "
            f"next_action={operator_control.get('next_recommended_action') or operator_planner_digest.get('next_recommended_action')} "
            f"resume_posture={operator_planner_digest.get('resume_posture')}"
        ),
        "shared_evidence_surface": list(
            dict.fromkeys(
                [
                    "runtime_event_stream",
                    "planner_shared_contract",
                    "planner_closure_posture",
                    "planner_autonomy_boundary",
                    "planner_reasoning",
                    "workspace_index",
                    "ui_execution_summary",
                    "cli_execution_summary",
                    "evidence_report",
                    *[str(item) for item in (comparative_shared_evidence_surface or []) if isinstance(item, str)],
                ]
            )
        ),
    }


def build_comparative_planner_candidate_summary(
    *,
    planner_shared_contract: dict[str, object],
    operator_planner_digest: dict[str, object] | None = None,
    comparative_shared_evidence_surface: list[object] | None = None,
) -> dict[str, object]:
    planner_shared_contract = (
        planner_shared_contract if isinstance(planner_shared_contract, dict) else {}
    )
    operator_planner_digest = operator_planner_digest if isinstance(operator_planner_digest, dict) else {}
    if not planner_shared_contract and not operator_planner_digest:
        return {}
    decision_boundary = (
        planner_shared_contract.get("decision_boundary", {})
        if isinstance(planner_shared_contract.get("decision_boundary"), dict)
        else {}
    )
    planner_reasoning = (
        planner_shared_contract.get("planner_reasoning", {})
        if isinstance(planner_shared_contract.get("planner_reasoning"), dict)
        else {}
    )
    planner_independence = (
        planner_shared_contract.get("planner_independence", {})
        if isinstance(planner_shared_contract.get("planner_independence"), dict)
        else {}
    )
    autonomy_surface = (
        planner_shared_contract.get("autonomy_surface", {})
        if isinstance(planner_shared_contract.get("autonomy_surface"), dict)
        else {}
    )
    tool_workflow_plan = (
        planner_shared_contract.get("tool_workflow_plan", {})
        if isinstance(planner_shared_contract.get("tool_workflow_plan"), dict)
        else {}
    )
    action_coverage = (
        planner_shared_contract.get("action_coverage", {})
        if isinstance(planner_shared_contract.get("action_coverage"), dict)
        else {}
    )
    candidate_evidence = (
        planner_shared_contract.get("decision_candidate_evidence", [])
        if isinstance(planner_shared_contract.get("decision_candidate_evidence"), list)
        else []
    )
    selected_candidate = next(
        (item for item in candidate_evidence if isinstance(item, dict) and item.get("selected")),
        {},
    )
    governed_alternatives = [
        {
            "strategy": str(item.get("strategy")),
            "score": item.get("score"),
            "reason": next((reason for reason in item.get("reasons", []) if isinstance(reason, str)), None),
        }
        for item in candidate_evidence
        if isinstance(item, dict) and not item.get("selected")
    ]
    resolved_selected_actions = (
        list(action_coverage.get("selected_actions", []))
        if isinstance(action_coverage.get("selected_actions"), list)
        else list(planner_shared_contract.get("selected_actions", []))
        if isinstance(planner_shared_contract.get("selected_actions"), list)
        else []
    )
    resolved_autonomy_selected_actions = (
        list(action_coverage.get("autonomy_selected_actions", []))
        if isinstance(action_coverage.get("autonomy_selected_actions"), list)
        else [
            name
            for name, payload in autonomy_surface.get("actions", {}).items()
            if isinstance(name, str) and isinstance(payload, dict) and payload.get("selected") is True
        ]
        if isinstance(autonomy_surface.get("actions"), dict)
        else list(resolved_selected_actions)
    )
    resolved_decision_mode = autonomy_surface.get("decision_mode") or (
        "native_first_autonomous"
        if (planner_shared_contract.get("planner_family") or operator_planner_digest.get("planner_family")) == "native"
        else "compatibility_guided"
    )
    native_first = (
        planner_reasoning.get("native_first")
        if "native_first" in planner_reasoning
        else planner_independence.get("native_first_contract_authoritative")
        if "native_first_contract_authoritative" in planner_independence
        else planner_shared_contract.get("planner_family") == "native"
    )
    if not tool_workflow_plan:
        workflow_stages_fallback: dict[str, object] = {}
        daily_driver_tools: list[str] = []
        for stage_name, required_tools in {
            "explore": ["repo_map", "find_files", "search", "outline", "read"],
            "edit": ["patch_preview", "structured_patch", "diff_preview"],
            "verify": ["verify", "tool_trace"],
        }.items():
            selected = stage_name in resolved_selected_actions
            workflow_stages_fallback[stage_name] = {
                "selected": selected,
                "required_tools": list(required_tools),
                "projection_required": selected,
            }
            if selected:
                for tool_name in required_tools:
                    if tool_name not in daily_driver_tools:
                        daily_driver_tools.append(tool_name)
        tool_workflow_plan = {
            "format": "agent_orchestrator.native_tool_workflow_plan.v1"
            if (planner_shared_contract.get("planner_family") or operator_planner_digest.get("planner_family")) == "native"
            else "agent_orchestrator.compatibility_tool_workflow_plan.v1",
            "planner_family": planner_shared_contract.get("planner_family") or operator_planner_digest.get("planner_family"),
            "selected_strategy": planner_shared_contract.get("selected_strategy") or operator_planner_digest.get("selected_execution_strategy"),
            "workflow_stage_order": [
                stage_name for stage_name in ("explore", "edit", "verify") if stage_name in resolved_selected_actions
            ],
            "workflow_stages": workflow_stages_fallback,
            "daily_driver_path": {
                "tools": daily_driver_tools,
                "selected_stage_count": len([item for item in workflow_stages_fallback.values() if item.get("selected") is True]),
            },
            "workflow_projection_required": True,
        }
    workflow_stages = (
        tool_workflow_plan.get("workflow_stages", {})
        if isinstance(tool_workflow_plan.get("workflow_stages"), dict)
        else {}
    )
    workflow_projection_ready = (
        tool_workflow_plan.get("workflow_projection_required") is True
        and tool_workflow_plan.get("format") == "agent_orchestrator.native_tool_workflow_plan.v1"
        and all(
            isinstance(workflow_stages.get(stage_name), dict)
            and workflow_stages.get(stage_name, {}).get("selected") is True
            for stage_name in ("explore", "edit", "verify")
            if stage_name in resolved_selected_actions
        )
    )
    return {
        "format": "agent_orchestrator.comparative_planner_candidate_summary.v1",
        "planner_family": planner_shared_contract.get("planner_family") or operator_planner_digest.get("planner_family"),
        "selected_strategy": planner_shared_contract.get("selected_strategy") or operator_planner_digest.get("selected_execution_strategy"),
        "selected_owner": planner_shared_contract.get("selected_owner") or operator_planner_digest.get("selected_executor"),
        "native_first": native_first,
        "decision_candidates": list(planner_shared_contract.get("decision_candidates", []))
        if isinstance(planner_shared_contract.get("decision_candidates"), list)
        else [],
        "candidate_count": action_coverage.get("candidate_count") if action_coverage else len(candidate_evidence),
        "selected_candidate": selected_candidate,
        "selected_candidate_count": len([item for item in candidate_evidence if isinstance(item, dict) and item.get("selected")]),
        "governed_alternatives": governed_alternatives,
        "governed_alternative_count": len(governed_alternatives),
        "decision_boundary": decision_boundary,
        "planner_reasoning": planner_reasoning,
        "planner_independence": planner_independence,
        "autonomy_surface": {
            **autonomy_surface,
            "decision_mode": resolved_decision_mode,
        },
        "tool_workflow_plan": tool_workflow_plan,
        "workflow_projection_ready": workflow_projection_ready,
        "action_coverage": {
            "selected_action_count": action_coverage.get("selected_action_count")
            if action_coverage.get("selected_action_count") is not None
            else len(resolved_selected_actions),
            "selected_actions": resolved_selected_actions,
            "autonomy_selected_action_count": action_coverage.get("autonomy_selected_action_count")
            if action_coverage.get("autonomy_selected_action_count") is not None
            else len(resolved_autonomy_selected_actions),
            "autonomy_selected_actions": resolved_autonomy_selected_actions,
        },
        "summary": (
            f"native_first={native_first} "
            f"selected={selected_candidate.get('strategy') if isinstance(selected_candidate, dict) else planner_shared_contract.get('selected_strategy')} "
            f"candidates={(action_coverage.get('candidate_count') if action_coverage else len(candidate_evidence))} "
            f"governed_alternatives={len(governed_alternatives)} "
            f"boundary={decision_boundary.get('task_type')}:{decision_boundary.get('risk_level')} "
            f"reason={planner_reasoning.get('primary_action')} "
            f"executor={operator_planner_digest.get('selected_executor') or planner_shared_contract.get('selected_owner')} "
            f"decision_mode={resolved_decision_mode} "
            f"workflow_projection_ready={workflow_projection_ready} "
            f"autonomy_actions={','.join(str(item) for item in action_coverage.get('autonomy_selected_actions', [])) if isinstance(action_coverage.get('autonomy_selected_actions'), list) and action_coverage.get('autonomy_selected_actions') else 'none'}"
        ),
        "shared_evidence_surface": list(
            dict.fromkeys(
                [
                    "runtime_event_stream",
                    "planner_shared_contract",
                    "tool_workflow_plan",
                    "planner_autonomy_boundary",
                    "planner_reasoning",
                    "planner_closure_posture",
                    "workspace_index",
                    "ui_execution_summary",
                    "cli_execution_summary",
                    "evidence_report",
                    *[str(item) for item in (comparative_shared_evidence_surface or []) if isinstance(item, str)],
                ]
            )
        ),
    }


def build_shared_productization_surface(
    *,
    session_productization_surface: dict[str, object],
    native_tool_productization_surface: dict[str, object],
    native_tool_workflow_surface: dict[str, object] | None = None,
    adapter_productization_surface: dict[str, object],
    planner_decision: dict[str, object],
    continuity_outline: dict[str, object],
    planner_closure_posture: dict[str, object] | None = None,
    runtime_cost: dict[str, object] | None = None,
    native_tool_usage: dict[str, object] | None = None,
    adapter_capability_surface: dict[str, object] | None = None,
    comparative_shared_evidence_surface: list[object] | None = None,
) -> dict[str, object]:
    session_productization_surface = (
        session_productization_surface if isinstance(session_productization_surface, dict) else {}
    )
    native_tool_productization_surface = (
        native_tool_productization_surface if isinstance(native_tool_productization_surface, dict) else {}
    )
    native_tool_workflow_surface = (
        native_tool_workflow_surface if isinstance(native_tool_workflow_surface, dict) else {}
    )
    adapter_productization_surface = (
        adapter_productization_surface if isinstance(adapter_productization_surface, dict) else {}
    )
    planner_decision = planner_decision if isinstance(planner_decision, dict) else {}
    continuity_outline = continuity_outline if isinstance(continuity_outline, dict) else {}
    planner_closure_posture = (
        planner_closure_posture
        if isinstance(planner_closure_posture, dict)
        else derive_planner_closure_posture_summary(
            planner_decision=planner_decision,
            continuity=continuity_outline,
        )
    )
    runtime_cost = runtime_cost if isinstance(runtime_cost, dict) else {}
    native_tool_usage = native_tool_usage if isinstance(native_tool_usage, dict) else {}
    adapter_capability_surface = (
        adapter_capability_surface if isinstance(adapter_capability_surface, dict) else {}
    )
    comparative_surface = [
        str(item)
        for item in (comparative_shared_evidence_surface or [])
        if isinstance(item, str)
    ]
    session_readiness = (
        session_productization_surface.get("continuity_readiness", {})
        if isinstance(session_productization_surface.get("continuity_readiness"), dict)
        else {}
    )
    tool_readiness = (
        native_tool_productization_surface.get("readiness", {})
        if isinstance(native_tool_productization_surface.get("readiness"), dict)
        else {}
    )
    if not native_tool_workflow_surface:
        native_tool_workflow_surface = (
            native_tool_productization_surface.get("workflow_surface", {})
            if isinstance(native_tool_productization_surface.get("workflow_surface"), dict)
            else {}
        )
    planner_posture = (
        planner_decision.get("autonomy_posture", {})
        if isinstance(planner_decision.get("autonomy_posture"), dict)
        else {}
    )
    continuity_posture = (
        continuity_outline.get("autonomy_posture", {})
        if isinstance(continuity_outline.get("autonomy_posture"), dict)
        else {}
    )
    adapter_ready = (
        adapter_productization_surface.get("surface_status") == "same_contract_two_executors_governed"
        and adapter_productization_surface.get("resume_contract_supported") is True
        and adapter_productization_surface.get("governed_recovery_ready") is True
    )
    session_ready = (
        session_readiness.get("resume_ready") is True
        and session_readiness.get("runtime_cost_ready") is True
        and session_readiness.get("compaction_ready") is True
        and session_readiness.get("pressure_visible") is True
    )
    tool_ready = (
        native_tool_productization_surface.get("operator_visibility_ready") is True
        and tool_readiness.get("bounded_read_search_ready") is True
        and tool_readiness.get("structured_patch_ready") is True
        and tool_readiness.get("verification_ready") is True
    )
    planner_ready = (
        bool(planner_decision.get("format"))
        and bool(continuity_outline.get("format"))
        and bool(planner_closure_posture.get("format"))
        and bool(planner_closure_posture.get("closure_mode"))
    )
    shared_contract_alignment = session_ready and tool_ready and adapter_ready and planner_ready
    return {
        "format": "agent_orchestrator.shared_productization_surface.v1",
        "shared_contract_alignment": shared_contract_alignment,
        "shared_productization_contract_ready": shared_contract_alignment,
        "surface_status": (
            "shared_productization_contract_ready"
            if shared_contract_alignment
            else "shared_productization_gap_remaining"
        ),
        "session_productization_surface": session_productization_surface,
        "native_tool_workflow_surface": native_tool_workflow_surface,
        "native_tool_productization_surface": native_tool_productization_surface,
        "adapter_productization_surface": adapter_productization_surface,
        "planner_decision": planner_decision,
        "continuity_outline": continuity_outline,
        "planner_closure_posture": planner_closure_posture,
        "runtime_cost": {
            "duration_seconds": runtime_cost.get("duration_seconds"),
            "usage_cost_measurement_status": runtime_cost.get("usage_cost_measurement_status"),
            "runtime_cost_provenance": (
                runtime_cost.get("runtime_cost_provenance", {})
                if isinstance(runtime_cost.get("runtime_cost_provenance"), dict)
                else {}
            ),
        },
        "native_tool_usage": {
            "tool_count": native_tool_usage.get("tool_count"),
            "trace_count": native_tool_usage.get("trace_count"),
            "recent_tools": list(native_tool_usage.get("recent_tools", []))
            if isinstance(native_tool_usage.get("recent_tools"), list)
            else [],
        },
        "adapter_capability_surface": adapter_capability_surface,
        "session_posture": {
            "resume_expectation": (
                session_productization_surface.get("operator_continuity", {}).get("resume_expectation")
                if isinstance(session_productization_surface.get("operator_continuity"), dict)
                else None
            ),
            "resume_posture": continuity_posture.get("resume_posture") or planner_posture.get("resume_posture"),
            "next_recommended_action": (
                session_productization_surface.get("operator_continuity", {}).get("next_recommended_action")
                if isinstance(session_productization_surface.get("operator_continuity"), dict)
                else None
            ),
        },
        "contract_readiness": {
            "session_ready": session_ready,
            "tool_ready": tool_ready,
            "adapter_ready": adapter_ready,
            "planner_ready": planner_ready,
        },
        "shared_evidence_surface": list(
            dict.fromkeys(
                [
                    "runtime_payload",
                    "clarify_boundary_digest",
                    "approval_boundary_digest",
                    "workspace_index",
                    "ui_execution_summary",
                    "cli_execution_summary",
                    "evidence_report",
                    "planner_closure_posture",
                    *comparative_surface,
                ]
            )
        ),
    }
