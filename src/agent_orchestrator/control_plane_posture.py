"""Shared session posture summaries for control-plane artifacts."""
from __future__ import annotations

# DEPS: __future__
# RESPONSIBILITY: Derive planner and continuity posture surfaces from strategy payloads.
# MODULE: decision_core
# ---


def _planner_candidate_evidence(strategy: dict[str, object]) -> list[dict[str, object]]:
    return [
        dict(item)
        for item in strategy.get("decision_candidate_evidence", [])
        if isinstance(item, dict)
    ] if isinstance(strategy.get("decision_candidate_evidence"), list) else []


def _planner_governed_alternatives_from_candidates(
    candidate_evidence: list[dict[str, object]],
) -> list[dict[str, object]]:
    governed: list[dict[str, object]] = []
    for item in candidate_evidence:
        strategy_name = str(item.get("strategy") or "").strip()
        if strategy_name not in {"need_human_confirmation", "external_handoff", "fallback_external"}:
            continue
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
        governed.append(
            {
                "strategy": strategy_name,
                "selected": bool(item.get("selected")),
                "score": item.get("score"),
                "reason": metadata.get("reason")
                or next((reason for reason in item.get("reasons", []) if isinstance(reason, str)), None),
                "requires_human_confirmation": metadata.get("requires_human_confirmation"),
            }
        )
    return governed


def _planner_action_coverage(
    *,
    selected_actions: list[object],
    autonomy_surface: dict[str, object],
    candidate_evidence: list[dict[str, object]],
    planner_governed_alternatives: list[dict[str, object]],
) -> dict[str, object]:
    selected = [str(item) for item in selected_actions if item not in {None, ""}]
    autonomy_actions = (
        autonomy_surface.get("actions", {})
        if isinstance(autonomy_surface.get("actions"), dict)
        else {}
    )
    autonomy_selected_actions = [
        name
        for name, payload in autonomy_actions.items()
        if isinstance(name, str) and isinstance(payload, dict) and payload.get("selected") is True
    ]
    candidate_strategies = [
        str(item.get("strategy"))
        for item in candidate_evidence
        if isinstance(item, dict) and item.get("strategy")
    ]
    governed_actions = [
        str(item.get("strategy"))
        for item in planner_governed_alternatives
        if isinstance(item, dict) and item.get("strategy")
    ]
    return {
        "selected_action_count": len(selected),
        "selected_actions": selected,
        "autonomy_selected_action_count": len(autonomy_selected_actions),
        "autonomy_selected_actions": autonomy_selected_actions,
        "candidate_count": len(candidate_evidence),
        "candidate_strategies": candidate_strategies,
        "governed_alternative_count": len(planner_governed_alternatives),
        "governed_alternative_strategies": governed_actions,
    }


def derive_session_planner_decision(strategy: dict[str, object]) -> dict[str, object]:
    posture = strategy.get("posture", {}) if isinstance(strategy.get("posture"), dict) else {}
    delegation_contract = (
        strategy.get("delegation_contract", {})
        if isinstance(strategy.get("delegation_contract"), dict)
        else {}
    )
    route_planner_intent = (
        strategy.get("route_planner_intent", {})
        if isinstance(strategy.get("route_planner_intent"), dict)
        else {}
    )
    autonomy_surface = (
        strategy.get("autonomy_surface", {})
        if isinstance(strategy.get("autonomy_surface"), dict)
        else {}
    )
    control_surface = (
        strategy.get("control_surface", {})
        if isinstance(strategy.get("control_surface"), dict)
        else {}
    )
    operator_control = (
        strategy.get("operator_control", {})
        if isinstance(strategy.get("operator_control"), dict)
        else {}
    )
    planner_governed_alternatives = [
        dict(item)
        for item in operator_control.get("planner_governed_alternatives", [])
        if isinstance(item, dict)
    ] if isinstance(operator_control.get("planner_governed_alternatives"), list) else []
    decision_boundary = (
        strategy.get("decision_boundary", {})
        if isinstance(strategy.get("decision_boundary"), dict)
        else {}
    )
    selected_actions = list(strategy.get("selected_actions", [])) if isinstance(strategy.get("selected_actions"), list) else []
    planner_reasoning = (
        strategy.get("planner_reasoning", {})
        if isinstance(strategy.get("planner_reasoning"), dict)
        else {}
    )
    planner_independence = (
        strategy.get("planner_independence", {})
        if isinstance(strategy.get("planner_independence"), dict)
        else {}
    )
    decision_candidates = (
        list(strategy.get("decision_candidates", []))
        if isinstance(strategy.get("decision_candidates"), list)
        else []
    )
    tool_workflow_plan = _tool_workflow_plan_snapshot(
        planner_family=strategy.get("planner_family"),
        selected_strategy=strategy.get("selected_strategy"),
        selected_actions=selected_actions,
        workflow_plan=(
            strategy.get("tool_workflow_plan", {})
            if isinstance(strategy.get("tool_workflow_plan"), dict)
            else {}
        ),
    )
    candidate_evidence = _planner_candidate_evidence(strategy)
    primary_action = autonomy_surface.get("primary_action") or operator_control.get("next_recommended_action") or (selected_actions[0] if selected_actions else None)
    governed_candidate_alternatives = _planner_governed_alternatives_from_candidates(candidate_evidence)
    action_coverage = _planner_action_coverage(
        selected_actions=selected_actions,
        autonomy_surface=autonomy_surface,
        candidate_evidence=candidate_evidence,
        planner_governed_alternatives=planner_governed_alternatives or governed_candidate_alternatives,
    )
    return {
        "format": "agent_orchestrator.session_planner_snapshot.v1",
        "planner_family": strategy.get("planner_family"),
        "selected_execution_strategy": strategy.get("selected_strategy"),
        "selected_actions": selected_actions,
        "primary_action": primary_action,
        "selected_owner": strategy.get("selected_owner"),
        "operating_boundary": strategy.get("operating_boundary"),
        "selection_reason": strategy.get("selection_reason"),
        "route_planner_intent": dict(route_planner_intent),
        "decision_evidence_format": strategy.get("format"),
        "decision_boundary": {
            "task_type": decision_boundary.get("task_type"),
            "risk_level": decision_boundary.get("risk_level"),
            "route_task_kind": decision_boundary.get("route_task_kind"),
            "requires_human_confirmation": decision_boundary.get("requires_human_confirmation"),
        },
        "decision_candidates": decision_candidates,
        "decision_candidate_evidence": candidate_evidence,
        "candidate_count": len(candidate_evidence),
        "selected_candidate_count": len([item for item in candidate_evidence if item.get("selected")]),
        "selected_candidate": next(
            (dict(item) for item in candidate_evidence if item.get("selected")),
            {},
        ),
        "planner_reasoning": planner_reasoning,
        "planner_independence": planner_independence,
        "tool_workflow_plan": tool_workflow_plan,
        "autonomy_surface": dict(autonomy_surface),
        "autonomy_posture": {
            "primary_action": primary_action,
            "pause_expected": bool(posture.get("pause_expected")),
            "handoff_expected": bool(posture.get("handoff_expected")),
            "fallback_expected": bool(posture.get("fallback_expected")),
            "clarify_pause_state": bool(operator_control.get("clarify_pause_state")),
            "approval_pause_state": bool(operator_control.get("approval_pause_state")),
        },
        "planner_governed_alternatives": planner_governed_alternatives or governed_candidate_alternatives,
        "action_coverage": action_coverage,
        "control_surface": {
            "format": control_surface.get("format") or "agent_orchestrator.session_planner_control_surface.v1",
            "planner_family": strategy.get("planner_family"),
            "decision_mode": control_surface.get("decision_mode"),
            "continue_native": control_surface.get("continue_native"),
            "clarify": control_surface.get("clarify"),
            "pause": control_surface.get("pause"),
            "handoff": control_surface.get("handoff"),
            "fallback": control_surface.get("fallback"),
            "resume_posture": control_surface.get("resume_posture"),
            "next_recommended_action": control_surface.get("next_recommended_action") or primary_action,
        },
        "delegation_contract": {
            "selected_executor": delegation_contract.get("selected_executor"),
            "resume_expectation": delegation_contract.get("resume_expectation"),
            "handoff_reason_code": delegation_contract.get("handoff_reason_code"),
            "fallback_reason_code": delegation_contract.get("fallback_reason_code"),
        },
    }


def derive_session_continuity_outline(
    strategy: dict[str, object],
    *,
    resume_kind: object = None,
    compaction_stage: object = None,
    resume_posture: str | None = None,
) -> dict[str, object]:
    program_posture = (
        strategy.get("program_posture", {})
        if isinstance(strategy.get("program_posture"), dict)
        else {}
    )
    operator_control = (
        strategy.get("operator_control", {})
        if isinstance(strategy.get("operator_control"), dict)
        else {}
    )
    planner_governed_alternatives = [
        dict(item)
        for item in operator_control.get("planner_governed_alternatives", [])
        if isinstance(item, dict)
    ] if isinstance(operator_control.get("planner_governed_alternatives"), list) else []
    delegation_contract = (
        strategy.get("delegation_contract", {})
        if isinstance(strategy.get("delegation_contract"), dict)
        else {}
    )
    autonomy_surface = (
        strategy.get("autonomy_surface", {})
        if isinstance(strategy.get("autonomy_surface"), dict)
        else {}
    )
    control_surface = (
        strategy.get("control_surface", {})
        if isinstance(strategy.get("control_surface"), dict)
        else {}
    )
    posture = strategy.get("posture", {}) if isinstance(strategy.get("posture"), dict) else {}
    selected_actions = list(strategy.get("selected_actions", [])) if isinstance(strategy.get("selected_actions"), list) else []
    primary_action = autonomy_surface.get("primary_action") or operator_control.get("next_recommended_action") or (selected_actions[0] if selected_actions else None)
    resolved_resume_posture = resume_posture or _resume_posture_from_resume_kind(resume_kind) or _resume_posture_from_expectation(
        delegation_contract.get("resume_expectation"),
        approval_pause_state=bool(operator_control.get("approval_pause_state")),
    )
    return {
        "format": "agent_orchestrator.session_continuity_outline.v1",
        "planner_family": strategy.get("planner_family"),
        "resume_kind": resume_kind,
        "goal": program_posture.get("program_goal"),
        "active_milestone": program_posture.get("active_milestone"),
        "ready_next_units": list(program_posture.get("ready_next_units", []))
        if isinstance(program_posture.get("ready_next_units"), list)
        else [],
        "blocked_units": list(program_posture.get("blocked_units", []))
        if isinstance(program_posture.get("blocked_units"), list)
        else [],
        "next_recommended_action": operator_control.get("next_recommended_action") or primary_action,
        "clarify_pause_state": operator_control.get("clarify_pause_state"),
        "approval_pause_state": operator_control.get("approval_pause_state"),
        "compaction_stage": compaction_stage,
        "resume_expectation": delegation_contract.get("resume_expectation"),
        "planner_governed_alternatives": planner_governed_alternatives,
        "autonomy_posture": {
            "primary_action": primary_action,
            "pause_expected": bool(posture.get("pause_expected")),
            "handoff_expected": bool(posture.get("handoff_expected")),
            "fallback_expected": bool(posture.get("fallback_expected")),
            "resume_posture": resolved_resume_posture,
        },
        "control_surface": {
            "format": control_surface.get("format") or "agent_orchestrator.session_continuity_control_surface.v1",
            "planner_family": strategy.get("planner_family"),
            "decision_mode": control_surface.get("decision_mode"),
            "continue_native": control_surface.get("continue_native"),
            "clarify": control_surface.get("clarify"),
            "pause": control_surface.get("pause"),
            "handoff": control_surface.get("handoff"),
            "fallback": control_surface.get("fallback"),
            "resume_posture": control_surface.get("resume_posture") or resolved_resume_posture,
            "next_recommended_action": control_surface.get("next_recommended_action") or operator_control.get("next_recommended_action") or primary_action,
        },
    }


def derive_session_planner_decision_from_payload(
    *,
    strategy_summary: dict[str, object],
    decision_evidence: dict[str, object],
    operator_control: dict[str, object],
) -> dict[str, object]:
    payload_strategy = {
        "format": strategy_summary.get("format"),
        "planner_family": strategy_summary.get("planner_family"),
        "selected_strategy": decision_evidence.get("selected_strategy"),
        "selected_actions": decision_evidence.get("selected_actions", []),
        "selected_owner": decision_evidence.get("selected_owner"),
        "operating_boundary": decision_evidence.get("operating_boundary"),
        "selection_reason": decision_evidence.get("selection_reason"),
        "route_planner_intent": decision_evidence.get("route_planner_intent", {}),
        "decision_boundary": decision_evidence.get("decision_boundary", {}),
        "decision_candidates": decision_evidence.get("decision_candidates", []),
        "decision_candidate_evidence": decision_evidence.get("decision_candidate_evidence", []),
        "planner_reasoning": decision_evidence.get("planner_reasoning", {}),
        "planner_independence": decision_evidence.get("planner_independence", {}),
        "posture": decision_evidence.get("posture", {}),
        "delegation_contract": decision_evidence.get("delegation_contract", {}),
        "autonomy_surface": decision_evidence.get("autonomy_surface", {}),
        "control_surface": decision_evidence.get("control_surface", {}),
        "operator_control": operator_control,
        "tool_workflow_plan": decision_evidence.get("tool_workflow_plan", {}),
    }
    return derive_session_planner_decision(payload_strategy)


def derive_session_continuity_outline_from_contract(
    *,
    continuity_contract: dict[str, object],
    planner_family: object = None,
) -> dict[str, object]:
    strategy = {
        "planner_family": planner_family,
        "program_posture": continuity_contract.get("program_posture", {}),
        "operator_control": continuity_contract.get("operator_control", {}),
        "delegation_contract": continuity_contract.get("delegation_contract", {}),
        "autonomy_surface": continuity_contract.get("autonomy_surface", {}),
        "control_surface": continuity_contract.get("control_surface", {}),
        "posture": continuity_contract.get("autonomy_posture", {}),
    }
    return derive_session_continuity_outline(
        strategy,
        resume_kind=continuity_contract.get("resume_kind"),
        compaction_stage=continuity_contract.get("compaction_stage"),
        resume_posture=(
            continuity_contract.get("session_productization_surface", {})
            .get("autonomy_posture", {})
            .get("resume_posture")
            if isinstance(continuity_contract.get("session_productization_surface"), dict)
            and isinstance(continuity_contract.get("session_productization_surface", {}).get("autonomy_posture"), dict)
            else None
        ),
    )


def derive_session_planner_decision_summary(
    *,
    planner_shared: dict[str, object],
    adapter_shared: dict[str, object],
) -> dict[str, object]:
    if not planner_shared:
        return {}
    path_selection = (
        adapter_shared.get("path_selection", {})
        if isinstance(adapter_shared.get("path_selection"), dict)
        else {}
    )
    selected_actions = (
        list(planner_shared.get("selected_actions", []))
        if isinstance(planner_shared.get("selected_actions"), list)
        else []
    )
    posture = (
        planner_shared.get("posture", {})
        if isinstance(planner_shared.get("posture"), dict)
        else {}
    )
    planner_reasoning = (
        planner_shared.get("planner_reasoning", {})
        if isinstance(planner_shared.get("planner_reasoning"), dict)
        else {}
    )
    planner_independence = (
        planner_shared.get("planner_independence", {})
        if isinstance(planner_shared.get("planner_independence"), dict)
        else {}
    )
    delegation_contract = (
        planner_shared.get("delegation_contract", {})
        if isinstance(planner_shared.get("delegation_contract"), dict)
        else {}
    )
    primary_action = (
        planner_shared.get("autonomy_surface", {}).get("primary_action")
        if isinstance(planner_shared.get("autonomy_surface"), dict)
        else None
    ) or (selected_actions[0] if selected_actions else None)
    control_surface = (
        planner_shared.get("control_surface", {})
        if isinstance(planner_shared.get("control_surface"), dict)
        else {}
    )
    tool_workflow_plan = _tool_workflow_plan_snapshot(
        planner_family=planner_shared.get("planner_family"),
        selected_strategy=planner_shared.get("selected_strategy"),
        selected_actions=selected_actions,
        workflow_plan=(
            planner_shared.get("tool_workflow_plan", {})
            if isinstance(planner_shared.get("tool_workflow_plan"), dict)
            else {}
        ),
    )
    candidate_evidence = _planner_candidate_evidence(planner_shared)
    planner_governed_alternatives = _planner_governed_alternatives_from_candidates(candidate_evidence)
    action_coverage = _planner_action_coverage(
        selected_actions=selected_actions,
        autonomy_surface=(
            planner_shared.get("autonomy_surface", {})
            if isinstance(planner_shared.get("autonomy_surface"), dict)
            else {}
        ),
        candidate_evidence=candidate_evidence,
        planner_governed_alternatives=planner_governed_alternatives,
    )
    return {
        "format": "agent_orchestrator.session_planner_snapshot.v1",
        "planner_family": planner_shared.get("planner_family"),
        "selected_execution_strategy": planner_shared.get("selected_strategy"),
        "selected_actions": selected_actions,
        "primary_action": primary_action,
        "selected_owner": planner_shared.get("selected_owner"),
        "operating_boundary": adapter_shared.get("operating_boundary"),
        "selection_reason": adapter_shared.get("selection_reason"),
        "route_planner_intent": dict(path_selection.get("planner_intent", {}))
        if isinstance(path_selection.get("planner_intent"), dict)
        else dict(planner_shared.get("route_planner_intent", {}))
        if isinstance(planner_shared.get("route_planner_intent"), dict)
        else {},
        "decision_evidence_format": planner_shared.get("format"),
        "decision_boundary": {
            "task_type": planner_shared.get("decision_boundary", {}).get("task_type")
            if isinstance(planner_shared.get("decision_boundary"), dict)
            else None,
            "risk_level": planner_shared.get("decision_boundary", {}).get("risk_level")
            if isinstance(planner_shared.get("decision_boundary"), dict)
            else None,
            "route_task_kind": planner_shared.get("decision_boundary", {}).get("route_task_kind")
            if isinstance(planner_shared.get("decision_boundary"), dict)
            else None,
            "requires_human_confirmation": planner_shared.get("decision_boundary", {}).get("requires_human_confirmation")
            if isinstance(planner_shared.get("decision_boundary"), dict)
            else None,
        },
        "decision_candidates": list(planner_shared.get("decision_candidates", []))
        if isinstance(planner_shared.get("decision_candidates"), list)
        else [],
        "decision_candidate_evidence": candidate_evidence,
        "candidate_count": len(candidate_evidence),
        "selected_candidate_count": len([item for item in candidate_evidence if item.get("selected")]),
        "selected_candidate": next(
            (dict(item) for item in candidate_evidence if item.get("selected")),
            {},
        ),
        "planner_reasoning": planner_reasoning,
        "planner_independence": planner_independence,
        "tool_workflow_plan": tool_workflow_plan,
        "autonomy_surface": (
            dict(planner_shared.get("autonomy_surface", {}))
            if isinstance(planner_shared.get("autonomy_surface"), dict)
            else {}
        ),
        "autonomy_posture": {
            "primary_action": primary_action,
            "pause_expected": posture.get("pause_expected"),
            "handoff_expected": posture.get("handoff_expected"),
            "fallback_expected": posture.get("fallback_expected"),
            "clarify_pause_state": planner_shared.get("operator_control", {}).get("clarify_pause_state")
            if isinstance(planner_shared.get("operator_control"), dict)
            else None,
            "approval_pause_state": planner_shared.get("operator_control", {}).get("approval_pause_state")
            if isinstance(planner_shared.get("operator_control"), dict)
            else None,
        },
        "planner_governed_alternatives": planner_governed_alternatives,
        "action_coverage": action_coverage,
        "control_surface": {
            "format": control_surface.get("format") or "agent_orchestrator.session_planner_control_surface.v1",
            "planner_family": planner_shared.get("planner_family"),
            "decision_mode": control_surface.get("decision_mode"),
            "continue_native": control_surface.get("continue_native"),
            "clarify": control_surface.get("clarify"),
            "pause": control_surface.get("pause"),
            "handoff": control_surface.get("handoff"),
            "fallback": control_surface.get("fallback"),
            "resume_posture": control_surface.get("resume_posture"),
            "next_recommended_action": control_surface.get("next_recommended_action") or primary_action,
        },
        "delegation_contract": {
            "selected_executor": delegation_contract.get("selected_executor"),
            "resume_expectation": delegation_contract.get("resume_expectation"),
            "handoff_reason_code": delegation_contract.get("handoff_reason_code"),
            "fallback_reason_code": delegation_contract.get("fallback_reason_code"),
        },
    }


def _tool_workflow_plan_snapshot(
    *,
    planner_family: object,
    selected_strategy: object,
    selected_actions: list[object],
    workflow_plan: dict[str, object],
) -> dict[str, object]:
    if workflow_plan:
        return dict(workflow_plan)
    selected_action_names = [str(item) for item in selected_actions if item not in {None, ""}]
    stage_tools = {
        "explore": ["repo_map", "find_files", "search", "outline", "read"],
        "edit": ["patch_preview", "structured_patch", "diff_preview"],
        "verify": ["verify", "tool_trace"],
    }
    workflow_stages: dict[str, object] = {}
    daily_driver_tools: list[str] = []
    for stage_name, required_tools in stage_tools.items():
        selected = stage_name in selected_action_names
        workflow_stages[stage_name] = {
            "selected": selected,
            "required_tools": list(required_tools),
            "projection_required": selected,
        }
        if selected:
            for tool_name in required_tools:
                if tool_name not in daily_driver_tools:
                    daily_driver_tools.append(tool_name)
    return {
        "format": "agent_orchestrator.native_tool_workflow_plan.v1"
        if planner_family == "native"
        else "agent_orchestrator.compatibility_tool_workflow_plan.v1",
        "planner_family": planner_family,
        "selected_strategy": selected_strategy,
        "workflow_stage_order": [stage for stage in ("explore", "edit", "verify") if stage in selected_action_names],
        "workflow_stages": workflow_stages,
        "daily_driver_path": {
            "tools": daily_driver_tools,
            "selected_stage_count": len([item for item in workflow_stages.values() if item.get("selected") is True]),
        },
        "workflow_projection_required": True,
    }


def derive_session_continuity_outline_summary(
    *,
    continuity: dict[str, object],
    planner_family: object,
) -> dict[str, object]:
    program_posture = (
        continuity.get("program_posture", {})
        if isinstance(continuity.get("program_posture"), dict)
        else {}
    )
    operator_control = (
        continuity.get("operator_control", {})
        if isinstance(continuity.get("operator_control"), dict)
        else {}
    )
    session_productization_surface = (
        continuity.get("session_productization_surface", {})
        if isinstance(continuity.get("session_productization_surface"), dict)
        else {}
    )
    long_horizon_posture = (
        continuity.get("long_horizon_posture", {})
        if isinstance(continuity.get("long_horizon_posture"), dict)
        else {}
    )
    delegation_contract = (
        continuity.get("delegation_contract", {})
        if isinstance(continuity.get("delegation_contract"), dict)
        else {}
    )
    if not continuity and not program_posture and not operator_control:
        return {}
    return {
        "format": "agent_orchestrator.session_continuity_outline.v1",
        "planner_family": planner_family,
        "resume_kind": continuity.get("resume_kind"),
        "goal": program_posture.get("program_goal"),
        "active_milestone": program_posture.get("active_milestone"),
        "ready_next_units": list(program_posture.get("ready_next_units", []))
        if isinstance(program_posture.get("ready_next_units"), list)
        else [],
        "blocked_units": list(program_posture.get("blocked_units", []))
        if isinstance(program_posture.get("blocked_units"), list)
        else [],
        "next_recommended_action": operator_control.get("next_recommended_action"),
        "clarify_pause_state": operator_control.get("clarify_pause_state"),
        "approval_pause_state": operator_control.get("approval_pause_state"),
        "compaction_stage": continuity.get("compaction_stage"),
        "resume_expectation": delegation_contract.get("resume_expectation"),
        "autonomy_posture": {
            **(
                session_productization_surface.get("autonomy_posture", {})
                if isinstance(session_productization_surface.get("autonomy_posture"), dict)
                else {}
            ),
            "resume_posture": (
                session_productization_surface.get("autonomy_posture", {}).get("resume_posture")
                if isinstance(session_productization_surface.get("autonomy_posture"), dict)
                else long_horizon_posture.get("resume_posture")
            ),
            "pause_expected": operator_control.get("approval_pause_state")
            or operator_control.get("clarify_pause_state"),
            "handoff_expected": delegation_contract.get("handoff_reason_code") is not None,
            "fallback_expected": delegation_contract.get("fallback_reason_code") is not None,
        },
    }


def derive_planner_closure_posture_summary(
    *,
    planner_decision: dict[str, object],
    continuity: dict[str, object],
) -> dict[str, object]:
    planner_decision = planner_decision if isinstance(planner_decision, dict) else {}
    continuity = continuity if isinstance(continuity, dict) else {}
    selected_actions = (
        [str(item) for item in planner_decision.get("selected_actions", []) if item not in {None, ""}]
        if isinstance(planner_decision.get("selected_actions"), list)
        else []
    )
    control_surface = (
        planner_decision.get("control_surface", {})
        if isinstance(planner_decision.get("control_surface"), dict)
        else {}
    )
    autonomy_posture = (
        continuity.get("autonomy_posture", {})
        if isinstance(continuity.get("autonomy_posture"), dict)
        else {}
    )
    operator_control = (
        continuity.get("operator_control", {})
        if isinstance(continuity.get("operator_control"), dict)
        else {}
    )
    milestone_verification = (
        continuity.get("milestone_verification", {})
        if isinstance(continuity.get("milestone_verification"), dict)
        else {}
    )
    long_horizon_posture = (
        continuity.get("long_horizon_posture", {})
        if isinstance(continuity.get("long_horizon_posture"), dict)
        else {}
    )
    if not planner_decision and not continuity:
        return {}
    verify_selected = "verify" in selected_actions
    return {
        "format": "agent_orchestrator.planner_closure_posture.v1",
        "planner_family": planner_decision.get("planner_family"),
        "selected_strategy": planner_decision.get("selected_execution_strategy"),
        "verify_selected": verify_selected,
        "closure_mode": (
            "handoff"
            if control_surface.get("handoff")
            else "fallback"
            if control_surface.get("fallback")
            else "approval_pause"
            if control_surface.get("pause")
            else "planner_complete"
            if selected_actions and not verify_selected
            else "verify"
            if verify_selected
            else "continue_native"
        ),
        "next_recommended_action": operator_control.get("next_recommended_action")
        or control_surface.get("next_recommended_action")
        or planner_decision.get("primary_action"),
        "runbook_recovery_lane": operator_control.get("runbook_recovery_lane"),
        "verification_status": milestone_verification.get("verification_status"),
        "resume_posture": autonomy_posture.get("resume_posture") or long_horizon_posture.get("resume_posture"),
        "resume_expectation": operator_control.get("resume_expectation"),
        "pause_expected": bool(autonomy_posture.get("pause_expected")),
        "handoff_expected": bool(autonomy_posture.get("handoff_expected")),
        "fallback_expected": bool(autonomy_posture.get("fallback_expected")),
    }


def infer_resume_posture(
    *,
    current_status: object,
    human_required: bool,
    resume_expectation: object,
    resume_kind: object = None,
) -> str:
    if isinstance(resume_kind, str):
        inferred = _resume_posture_from_resume_kind(resume_kind)
        if inferred is not None:
            return inferred
    if human_required or str(current_status) in {"awaiting_human", "approval_blocked", "awaiting_human_confirmation"}:
        return "approval_reentry"
    inferred = _resume_posture_from_expectation(resume_expectation, approval_pause_state=human_required)
    if inferred is not None:
        return inferred
    if str(current_status) in {"drafting", "review_pending", "planned"}:
        return "fresh_entry"
    return "same_task_resume"


def _resume_posture_from_resume_kind(resume_kind: object) -> str | None:
    if resume_kind == "approval_resume":
        return "approval_reentry"
    if resume_kind == "resume_if_same_task":
        return "same_task_resume"
    if resume_kind == "fresh":
        return "fresh_entry"
    return None


def _resume_posture_from_expectation(
    resume_expectation: object,
    *,
    approval_pause_state: bool,
) -> str | None:
    if approval_pause_state or resume_expectation == "approval_pause":
        return "approval_reentry"
    if resume_expectation in {"continue_native", "handoff"}:
        return "same_task_resume"
    if resume_expectation is None:
        return "fresh_entry"
    return None
