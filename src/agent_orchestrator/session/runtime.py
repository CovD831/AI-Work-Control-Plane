"""Compatibility session runtime for the coding-agent architecture."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from agent_orchestrator.control_plane_posture import (
    derive_session_continuity_outline_from_contract,
)
from agent_orchestrator.productization_surface import (
    build_comparative_completion_summary,
    build_runtime_comparative_benchmark_digest,
)
from agent_orchestrator.session.productization import derive_session_productization_surface
from agent_orchestrator.session.models import (
    AgentSession,
    ContextSnapshot,
    ExecutionActivity,
    SessionTurn,
    TrajectoryRecord,
    new_activity_id,
    new_session_id,
    new_snapshot_id,
    new_turn_id,
)


class SessionRuntime:
    """Owns session and turn continuity without replacing control-plane truth."""

    def __init__(self, root: Path | str = ".agent_orchestrator/agent_sessions") -> None:
        self.root = Path(root)

    def start_session(
        self,
        *,
        origin: str,
        metadata: dict[str, object] | None = None,
        session_id: str | None = None,
    ) -> AgentSession:
        now = _utcnow()
        session = AgentSession(
            session_id=session_id or new_session_id(),
            status="active",
            created_at=now,
            updated_at=now,
            current_turn_id=None,
            turn_ids=[],
            origin=origin,
            metadata=dict(metadata or {}),
        )
        self._write_json(self._session_dir(session.session_id) / "session.json", session.to_dict())
        return session

    def get_session(self, session_id: str) -> AgentSession:
        return AgentSession.from_dict(self._read_json(self._session_dir(session_id) / "session.json"))

    def start_turn(
        self,
        *,
        session_id: str,
        requirement: str,
        route: dict[str, object],
        clarify_summary: dict[str, object],
        strategy_summary: dict[str, object],
        task_contract: dict[str, object],
        compatibility_metadata: dict[str, object],
        selected_execution_strategy: str,
        planner_family: str,
        resume_kind: str = "fresh",
        resume_from_turn_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> tuple[AgentSession, SessionTurn, ContextSnapshot]:
        session = self.get_session(session_id)
        turn_id = new_turn_id()
        snapshot_id = new_snapshot_id()
        session_continuity_contract = _session_continuity_contract_snapshot(
            requirement=requirement,
            task_contract=task_contract,
            route=route,
            clarify_summary=clarify_summary,
            strategy_summary=strategy_summary,
            selected_execution_strategy=selected_execution_strategy,
            planner_family=planner_family,
            resume_kind=resume_kind,
        )
        snapshot = ContextSnapshot(
            snapshot_id=snapshot_id,
            session_id=session_id,
            turn_id=turn_id,
            task_contract=dict(task_contract),
            selected_execution_strategy=selected_execution_strategy,
            planner_family=planner_family,
            compatibility_metadata=dict(compatibility_metadata),
            resume_kind=resume_kind,
            planner_decision=_planner_decision_snapshot(
                strategy_summary=strategy_summary,
                route=route,
                planner_family=planner_family,
                selected_execution_strategy=selected_execution_strategy,
            ),
            continuity_outline=_continuity_outline_snapshot(
                requirement=requirement,
                task_contract=task_contract,
                route=route,
                clarify_summary=clarify_summary,
                strategy_summary=strategy_summary,
                selected_execution_strategy=selected_execution_strategy,
                resume_kind=resume_kind,
                planner_family=planner_family,
            ),
            session_continuity_contract=session_continuity_contract,
            session_productization_surface=derive_session_productization_surface(session_continuity_contract),
            comparative_benchmark=dict(session_continuity_contract.get("comparative_benchmark", {}))
            if isinstance(session_continuity_contract.get("comparative_benchmark"), dict)
            else {},
            comparative_benchmark_digest=dict(session_continuity_contract.get("comparative_benchmark_digest", {}))
            if isinstance(session_continuity_contract.get("comparative_benchmark_digest"), dict)
            else {},
            compacted_context_summary=_compacted_context_summary_snapshot(
                requirement=requirement,
                task_contract=task_contract,
                strategy_summary=strategy_summary,
                resume_kind=resume_kind,
            ),
            metadata=dict(metadata or {}),
        )
        turn = SessionTurn(
            turn_id=turn_id,
            session_id=session_id,
            requirement=requirement,
            status="prepared",
            route=dict(route),
            clarify_summary=dict(clarify_summary),
            strategy_summary=dict(strategy_summary),
            linked_run_id=None,
            resume_from_turn_id=resume_from_turn_id,
            context_snapshot_id=snapshot_id,
            metadata=dict(metadata or {}),
        )
        updated_session = replace(
            session,
            updated_at=_utcnow(),
            current_turn_id=turn_id,
            turn_ids=[*session.turn_ids, turn_id],
        )
        session_dir = self._session_dir(session_id)
        self._write_json(session_dir / "session.json", updated_session.to_dict())
        self._write_json(session_dir / "turns" / f"{turn_id}.json", turn.to_dict())
        self._write_json(session_dir / "snapshots" / f"{snapshot_id}.json", snapshot.to_dict())
        return updated_session, turn, snapshot

    def get_turn(self, session_id: str, turn_id: str) -> SessionTurn:
        return SessionTurn.from_dict(self._read_json(self._session_dir(session_id) / "turns" / f"{turn_id}.json"))

    def get_snapshot(self, session_id: str, snapshot_id: str) -> ContextSnapshot:
        return ContextSnapshot.from_dict(self._read_json(self._session_dir(session_id) / "snapshots" / f"{snapshot_id}.json"))

    def record_activity(
        self,
        *,
        session_id: str,
        turn_id: str,
        runtime_name: str,
        linked_run_id: str | None,
        status: str,
        accepted: bool | None,
        summary: str,
        metadata: dict[str, object] | None = None,
    ) -> ExecutionActivity:
        activity = ExecutionActivity(
            activity_id=new_activity_id(),
            session_id=session_id,
            turn_id=turn_id,
            runtime_name=runtime_name,
            linked_run_id=linked_run_id,
            status=status,
            accepted=accepted,
            summary=summary,
            metadata=dict(metadata or {}),
        )
        self._write_json(
            self._session_dir(session_id) / "activities" / f"{activity.activity_id}.json",
            activity.to_dict(),
        )
        return activity

    def attach_run_result(
        self,
        *,
        session_id: str,
        turn_id: str,
        linked_run_id: str | None,
        status: str,
        accepted: bool | None,
        runtime_name: str,
        payload: dict[str, object],
    ) -> SessionTurn:
        turn = self.get_turn(session_id, turn_id)
        snapshot = self.get_snapshot(session_id, turn.context_snapshot_id) if turn.context_snapshot_id else None
        updated_turn = replace(
            turn,
            status="completed" if status == "completed" else status,
            linked_run_id=linked_run_id,
            metadata={**turn.metadata, "last_result": dict(payload)},
        )
        self._write_json(self._session_dir(session_id) / "turns" / f"{turn_id}.json", updated_turn.to_dict())
        if snapshot is not None:
            merged_continuity_contract = _merge_session_continuity_contract(
                snapshot.session_continuity_contract,
                payload=payload,
            )
            merged_continuity_outline = _merge_continuity_outline(
                snapshot.continuity_outline,
                continuity_contract=merged_continuity_contract,
                planner_family=snapshot.planner_family,
            )
            updated_snapshot = replace(
                snapshot,
                continuity_outline=merged_continuity_outline,
                session_continuity_contract=merged_continuity_contract,
                session_productization_surface=derive_session_productization_surface(merged_continuity_contract),
                comparative_benchmark=(
                    dict(merged_continuity_contract.get("comparative_benchmark", {}))
                    if isinstance(merged_continuity_contract.get("comparative_benchmark"), dict)
                    else snapshot.comparative_benchmark
                ),
                comparative_benchmark_digest=_merge_comparative_benchmark_digest(
                    snapshot.comparative_benchmark_digest,
                    payload=payload,
                ),
                compacted_context_summary=_merge_compacted_context_summary(
                    snapshot.compacted_context_summary,
                    payload=payload,
                    fallback_goal=snapshot.task_contract.get("goal") if isinstance(snapshot.task_contract, dict) else None,
                ),
            )
            self._write_json(
                self._session_dir(session_id) / "snapshots" / f"{updated_snapshot.snapshot_id}.json",
                updated_snapshot.to_dict(),
            )
        self.record_activity(
            session_id=session_id,
            turn_id=turn_id,
            runtime_name=runtime_name,
            linked_run_id=linked_run_id,
            status=status,
            accepted=accepted,
            summary=f"Runtime {runtime_name} finished with status={status}",
            metadata={"result_keys": sorted(payload.keys())},
        )
        return updated_turn

    def complete_turn(self, *, session_id: str, turn_id: str, status: str) -> SessionTurn:
        turn = self.get_turn(session_id, turn_id)
        updated_turn = replace(turn, status=status)
        self._write_json(self._session_dir(session_id) / "turns" / f"{turn_id}.json", updated_turn.to_dict())
        return updated_turn

    def record_trajectory(
        self,
        *,
        session_id: str,
        turn_id: str,
        task_class: str,
        path_selection: dict[str, object],
        stage: str,
        outcome: str,
        summary: str,
        evidence_refs: list[str] | None = None,
        asset_refs: list[str] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> TrajectoryRecord:
        trajectory = TrajectoryRecord(
            trajectory_id=f"trajectory-{new_activity_id().split('-', 1)[-1]}",
            session_id=session_id,
            turn_id=turn_id,
            task_class=task_class,
            path_selection=dict(path_selection),
            stage=stage,
            outcome=outcome,
            summary=summary,
            evidence_refs=list(evidence_refs or []),
            asset_refs=list(asset_refs or []),
            metadata=dict(metadata or {}),
        )
        self._write_json(self._session_dir(session_id) / "trajectories" / f"{trajectory.trajectory_id}.json", trajectory.to_dict())
        return trajectory

    def latest_turn(self, session_id: str) -> SessionTurn | None:
        session = self.get_session(session_id)
        if not session.current_turn_id:
            return None
        return self.get_turn(session_id, session.current_turn_id)

    def _session_dir(self, session_id: str) -> Path:
        return self.root / session_id

    def _read_json(self, path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _planner_decision_snapshot(
    *,
    strategy_summary: dict[str, object],
    route: dict[str, object],
    planner_family: str,
    selected_execution_strategy: str,
) -> dict[str, object]:
    decision_evidence = (
        strategy_summary.get("decision_evidence", {})
        if isinstance(strategy_summary.get("decision_evidence"), dict)
        else {}
    )
    planner_actions = [
        str(item)
        for item in strategy_summary.get("planner_actions", [])
        if item not in {None, ""}
    ] if isinstance(strategy_summary.get("planner_actions"), list) else []
    route_intent = (
        route.get("planner_intent", {})
        if isinstance(route.get("planner_intent"), dict)
        else decision_evidence.get("decision_boundary", {}).get("route_planner_intent", {})
        if isinstance(decision_evidence.get("decision_boundary"), dict)
        else {}
    )
    decision_boundary = (
        decision_evidence.get("decision_boundary", {})
        if isinstance(decision_evidence.get("decision_boundary"), dict)
        else {}
    )
    autonomy_surface = (
        decision_evidence.get("autonomy_surface", {})
        if isinstance(decision_evidence.get("autonomy_surface"), dict)
        else {}
    )
    control_surface = (
        decision_evidence.get("control_surface", {})
        if isinstance(decision_evidence.get("control_surface"), dict)
        else {}
    )
    delegation_contract = (
        decision_evidence.get("delegation_contract", {})
        if isinstance(decision_evidence.get("delegation_contract"), dict)
        else {}
    )
    operator_control = (
        decision_evidence.get("operator_control", {})
        if isinstance(decision_evidence.get("operator_control"), dict)
        else {}
    )
    primary_action = (
        autonomy_surface.get("primary_action")
    ) or (planner_actions[0] if planner_actions else None)
    if primary_action is None:
        primary_action = _default_next_action(
            selected_execution_strategy=selected_execution_strategy,
            route_intent=route_intent,
        )
    pause_expected = bool(decision_evidence.get("posture", {}).get("pause_expected")) if isinstance(decision_evidence.get("posture"), dict) else False
    handoff_expected = bool(decision_evidence.get("posture", {}).get("handoff_expected")) if isinstance(decision_evidence.get("posture"), dict) else False
    fallback_expected = bool(decision_evidence.get("posture", {}).get("fallback_expected")) if isinstance(decision_evidence.get("posture"), dict) else False
    planner_governed_alternatives = _planner_governed_alternatives_snapshot(decision_evidence)
    candidate_evidence = (
        [dict(item) for item in decision_evidence.get("decision_candidate_evidence", []) if isinstance(item, dict)]
        if isinstance(decision_evidence.get("decision_candidate_evidence"), list)
        else []
    )
    action_coverage = _planner_action_coverage_snapshot(
        selected_actions=planner_actions,
        autonomy_surface=autonomy_surface,
        candidate_evidence=candidate_evidence,
        planner_governed_alternatives=planner_governed_alternatives,
    )
    return {
        "format": "agent_orchestrator.session_planner_snapshot.v1",
        "planner_family": planner_family,
        "selected_execution_strategy": selected_execution_strategy,
        "selected_actions": planner_actions,
        "primary_action": primary_action,
        "selected_owner": decision_evidence.get("selected_owner") or ("native" if planner_family == "native" else "compatibility"),
        "operating_boundary": strategy_summary.get("operating_boundary"),
        "selection_reason": strategy_summary.get("selection_reason"),
        "route_planner_intent": dict(route_intent) if isinstance(route_intent, dict) else {},
        "decision_evidence_format": decision_evidence.get("format"),
        "decision_boundary": {
            "task_type": decision_boundary.get("task_type"),
            "risk_level": decision_boundary.get("risk_level"),
            "route_task_kind": decision_boundary.get("route_task_kind"),
            "requires_human_confirmation": decision_boundary.get("requires_human_confirmation"),
        },
        "decision_candidates": list(decision_evidence.get("decision_candidates", []))
        if isinstance(decision_evidence.get("decision_candidates"), list)
        else [],
        "decision_candidate_evidence": candidate_evidence,
        "candidate_count": len(candidate_evidence),
        "selected_candidate_count": len([item for item in candidate_evidence if item.get("selected")]),
        "selected_candidate": next(
            (dict(item) for item in candidate_evidence if item.get("selected")),
            {},
        ),
        "planner_reasoning": (
            dict(decision_evidence.get("planner_reasoning", {}))
            if isinstance(decision_evidence.get("planner_reasoning"), dict)
            else {}
        ),
        "planner_independence": (
            dict(decision_evidence.get("planner_independence", {}))
            if isinstance(decision_evidence.get("planner_independence"), dict)
            else {}
        ),
        "tool_workflow_plan": (
            dict(decision_evidence.get("tool_workflow_plan", {}))
            if isinstance(decision_evidence.get("tool_workflow_plan"), dict)
            else {}
        ),
        "autonomy_surface": dict(autonomy_surface),
        "autonomy_posture": {
            "primary_action": primary_action,
            "pause_expected": pause_expected,
            "handoff_expected": handoff_expected,
            "fallback_expected": fallback_expected,
            "clarify_pause_state": bool(operator_control.get("clarify_pause_state")) or bool(route_intent.get("clarify")),
            "approval_pause_state": bool(operator_control.get("approval_pause_state")) or bool(route_intent.get("pause")),
        },
        "planner_governed_alternatives": planner_governed_alternatives,
        "action_coverage": action_coverage,
        "control_surface": {
            "format": control_surface.get("format") or "agent_orchestrator.session_planner_control_surface.v1",
            "planner_family": planner_family,
            "decision_mode": control_surface.get("decision_mode") or ("native_first_autonomous" if planner_family == "native" else "compatibility_guided"),
            "continue_native": bool(control_surface.get("continue_native")) if "continue_native" in control_surface else planner_family == "native" and selected_execution_strategy != "external_handoff",
            "clarify": bool(control_surface.get("clarify")) if "clarify" in control_surface else bool(route_intent.get("clarify")) or bool(operator_control.get("clarify_pause_state")),
            "pause": bool(control_surface.get("pause")) if "pause" in control_surface else bool(pause_expected) or bool(operator_control.get("approval_pause_state")) or bool(route_intent.get("pause")),
            "handoff": bool(control_surface.get("handoff")) if "handoff" in control_surface else bool(handoff_expected),
            "fallback": bool(control_surface.get("fallback")) if "fallback" in control_surface else bool(fallback_expected),
            "resume_posture": control_surface.get("resume_posture") or delegation_contract.get("resume_expectation"),
            "next_recommended_action": control_surface.get("next_recommended_action") or primary_action,
        },
        "delegation_contract": {
            "selected_executor": delegation_contract.get("selected_executor"),
            "resume_expectation": delegation_contract.get("resume_expectation"),
            "handoff_reason_code": delegation_contract.get("handoff_reason_code"),
            "fallback_reason_code": delegation_contract.get("fallback_reason_code"),
        },
    }


def _continuity_outline_snapshot(
    *,
    requirement: str,
    task_contract: dict[str, object],
    route: dict[str, object],
    clarify_summary: dict[str, object],
    strategy_summary: dict[str, object],
    selected_execution_strategy: str,
    resume_kind: str,
    planner_family: str,
) -> dict[str, object]:
    decision_evidence = (
        strategy_summary.get("decision_evidence", {})
        if isinstance(strategy_summary.get("decision_evidence"), dict)
        else {}
    )
    program_posture = (
        decision_evidence.get("program_posture", {})
        if isinstance(decision_evidence.get("program_posture"), dict)
        else {}
    )
    operator_control = (
        decision_evidence.get("operator_control", {})
        if isinstance(decision_evidence.get("operator_control"), dict)
        else {}
    )
    delegation_contract = (
        decision_evidence.get("delegation_contract", {})
        if isinstance(decision_evidence.get("delegation_contract"), dict)
        else {}
    )
    autonomy_surface = (
        decision_evidence.get("autonomy_surface", {})
        if isinstance(decision_evidence.get("autonomy_surface"), dict)
        else {}
    )
    control_surface = (
        decision_evidence.get("control_surface", {})
        if isinstance(decision_evidence.get("control_surface"), dict)
        else {}
    )
    route_intent = (
        route.get("planner_intent", {})
        if isinstance(route.get("planner_intent"), dict)
        else {}
    )
    primary_action = (
        autonomy_surface.get("primary_action")
        or operator_control.get("next_recommended_action")
        or _default_next_action(
            selected_execution_strategy=str(strategy_summary.get("selected_execution_strategy") or ""),
            route_intent=route_intent,
        )
    )
    pause_expected = bool(decision_evidence.get("posture", {}).get("pause_expected")) if isinstance(decision_evidence.get("posture"), dict) else False
    handoff_expected = bool(decision_evidence.get("posture", {}).get("handoff_expected")) if isinstance(decision_evidence.get("posture"), dict) else False
    fallback_expected = bool(decision_evidence.get("posture", {}).get("fallback_expected")) if isinstance(decision_evidence.get("posture"), dict) else False
    planner_governed_alternatives = _planner_governed_alternatives_snapshot(decision_evidence)
    return {
        "format": "agent_orchestrator.session_continuity_outline.v1",
        "planner_family": planner_family,
        "resume_kind": resume_kind,
        "goal": task_contract.get("goal") or requirement,
        "active_milestone": program_posture.get("active_milestone") or task_contract.get("goal") or requirement,
        "ready_next_units": list(program_posture.get("ready_next_units", []))
        if isinstance(program_posture.get("ready_next_units"), list)
        else [],
        "blocked_units": list(program_posture.get("blocked_units", []))
        if isinstance(program_posture.get("blocked_units"), list)
        else [],
        "next_recommended_action": primary_action,
        "clarify_pause_state": bool(operator_control.get("clarify_pause_state"))
        or bool(route_intent.get("clarify"))
        or bool(clarify_summary.get("needs_clarification")),
        "approval_pause_state": bool(operator_control.get("approval_pause_state"))
        or bool(route_intent.get("pause")),
        "compaction_stage": "fresh_turn",
        "resume_expectation": delegation_contract.get("resume_expectation") if isinstance(delegation_contract, dict) else None,
        "planner_governed_alternatives": planner_governed_alternatives,
        "autonomy_posture": {
            "primary_action": primary_action,
            "pause_expected": pause_expected,
            "handoff_expected": handoff_expected,
            "fallback_expected": fallback_expected,
        },
        "control_surface": {
            "format": control_surface.get("format") or "agent_orchestrator.session_continuity_control_surface.v1",
            "planner_family": planner_family,
            "decision_mode": control_surface.get("decision_mode") or ("native_first_autonomous" if planner_family == "native" else "compatibility_guided"),
            "continue_native": bool(control_surface.get("continue_native")) if "continue_native" in control_surface else planner_family == "native" and selected_execution_strategy != "external_handoff",
            "clarify": bool(control_surface.get("clarify")) if "clarify" in control_surface else bool(route_intent.get("clarify")) or bool(clarify_summary.get("needs_clarification")),
            "pause": bool(control_surface.get("pause")) if "pause" in control_surface else bool(pause_expected) or bool(operator_control.get("approval_pause_state")) or bool(route_intent.get("pause")),
            "handoff": bool(control_surface.get("handoff")) if "handoff" in control_surface else bool(handoff_expected),
            "fallback": bool(control_surface.get("fallback")) if "fallback" in control_surface else bool(fallback_expected),
            "resume_posture": control_surface.get("resume_posture") or delegation_contract.get("resume_expectation"),
            "next_recommended_action": control_surface.get("next_recommended_action") or primary_action,
        },
    }


def _fallback_tool_workflow_plan(
    *,
    planner_family: str,
    selected_execution_strategy: str,
    selected_actions: list[object],
) -> dict[str, object]:
    resolved_selected_actions = [
        str(item)
        for item in selected_actions
        if isinstance(item, str) and item in {"explore", "edit", "verify"}
    ]
    workflow_stages: dict[str, object] = {}
    daily_driver_tools: list[str] = []
    for stage_name, required_tools in {
        "explore": ["repo_map", "find_files", "search", "outline", "read"],
        "edit": ["patch_preview", "structured_patch", "diff_preview"],
        "verify": ["verify", "tool_trace"],
    }.items():
        selected = stage_name in resolved_selected_actions
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
        "selected_strategy": selected_execution_strategy,
        "workflow_stage_order": [
            stage_name for stage_name in ("explore", "edit", "verify") if stage_name in resolved_selected_actions
        ],
        "workflow_stages": workflow_stages,
        "daily_driver_path": {
            "tools": daily_driver_tools,
            "selected_stage_count": len([item for item in workflow_stages.values() if item.get("selected") is True]),
        },
        "workflow_projection_required": True,
    }


def _workflow_continuity_snapshot(
    *,
    planner_decision: dict[str, object],
    continuity_outline: dict[str, object],
    planner_family: str,
    selected_execution_strategy: str,
    resume_kind: str,
    latest_recovery_hint: str,
) -> dict[str, object]:
    tool_workflow_plan = (
        dict(planner_decision.get("tool_workflow_plan", {}))
        if isinstance(planner_decision.get("tool_workflow_plan"), dict)
        and planner_decision.get("tool_workflow_plan")
        else _fallback_tool_workflow_plan(
            planner_family=planner_family,
            selected_execution_strategy=selected_execution_strategy,
            selected_actions=(
                list(planner_decision.get("selected_actions", []))
                if isinstance(planner_decision.get("selected_actions"), list)
                else []
            ),
        )
    )
    workflow_stages = (
        tool_workflow_plan.get("workflow_stages", {})
        if isinstance(tool_workflow_plan.get("workflow_stages"), dict)
        else {}
    )
    selected_workflow_stages = [
        stage_name
        for stage_name in ("explore", "edit", "verify")
        if isinstance(workflow_stages.get(stage_name), dict) and workflow_stages.get(stage_name, {}).get("selected") is True
    ]
    active_stage = continuity_outline.get("next_recommended_action")
    if active_stage not in {"explore", "edit", "verify"}:
        active_stage = selected_workflow_stages[0] if selected_workflow_stages else None
    return {
        "format": "agent_orchestrator.session_workflow_continuity.v1",
        "resume_kind": resume_kind,
        "active_stage": active_stage,
        "selected_workflow_stages": selected_workflow_stages,
        "tool_workflow_plan": tool_workflow_plan,
        "workflow_projection_ready": (
            tool_workflow_plan.get("format") == "agent_orchestrator.native_tool_workflow_plan.v1"
            and tool_workflow_plan.get("workflow_projection_required") is True
            and all(
                isinstance(workflow_stages.get(stage_name), dict)
                and workflow_stages.get(stage_name, {}).get("selected") is True
                for stage_name in selected_workflow_stages
            )
        ),
        "resume_alignment": {
            "resume_kind": resume_kind,
            "resume_posture": continuity_outline.get("control_surface", {}).get("resume_posture")
            if isinstance(continuity_outline.get("control_surface"), dict)
            else None,
            "resume_expectation": continuity_outline.get("resume_expectation"),
            "aligned": bool(selected_workflow_stages),
        },
        "recovery_alignment": {
            "recovery_active": False,
            "runbook_recovery_lane": continuity_outline.get("control_surface", {}).get("next_recommended_action")
            if isinstance(continuity_outline.get("control_surface"), dict)
            else None,
            "latest_recovery_hint": latest_recovery_hint,
            "aligned": True,
        },
        "shared_evidence_surface": [
            "session_snapshot",
            "session_continuity",
            "session_productization_surface",
            "compacted_context_summary",
        ],
    }


def _session_continuity_contract_snapshot(
    *,
    requirement: str,
    task_contract: dict[str, object],
    route: dict[str, object],
    clarify_summary: dict[str, object],
    strategy_summary: dict[str, object],
    selected_execution_strategy: str,
    planner_family: str,
    resume_kind: str,
) -> dict[str, object]:
    pending_comparative_benchmark = _runtime_evidence_pending_comparative_benchmark()
    pending_comparative_benchmark_digest = build_runtime_comparative_benchmark_digest(
        pending_comparative_benchmark
    )
    planner_decision = _planner_decision_snapshot(
        strategy_summary=strategy_summary,
        route=route,
        planner_family=planner_family,
        selected_execution_strategy=selected_execution_strategy,
    )
    continuity_outline = _continuity_outline_snapshot(
        requirement=requirement,
        task_contract=task_contract,
        route=route,
        clarify_summary=clarify_summary,
        strategy_summary=strategy_summary,
        selected_execution_strategy=selected_execution_strategy,
        resume_kind=resume_kind,
        planner_family=planner_family,
    )
    delegation_contract = (
        planner_decision.get("delegation_contract", {})
        if isinstance(planner_decision.get("delegation_contract"), dict)
        else {}
    )
    autonomy_posture = (
        planner_decision.get("autonomy_posture", {})
        if isinstance(planner_decision.get("autonomy_posture"), dict)
        else {}
    )
    planner_governed_alternatives = _planner_governed_alternatives_snapshot(
        strategy_summary.get("decision_evidence", {})
        if isinstance(strategy_summary.get("decision_evidence"), dict)
        else {}
    )
    program_goal = task_contract.get("goal") or requirement
    active_milestone = continuity_outline.get("active_milestone") or program_goal
    ready_next_units = continuity_outline.get("ready_next_units", [])
    blocked_units = continuity_outline.get("blocked_units", [])
    latest_recovery_hint = (
        f"Resume with {continuity_outline.get('next_recommended_action')}"
        if continuity_outline.get("next_recommended_action")
        else "Use the next planned work unit and preserve verification evidence."
    )
    workflow_continuity = _workflow_continuity_snapshot(
        planner_decision=planner_decision,
        continuity_outline=continuity_outline,
        planner_family=planner_family,
        selected_execution_strategy=selected_execution_strategy,
        resume_kind=resume_kind,
        latest_recovery_hint=latest_recovery_hint,
    )
    return {
        "format": "agent_orchestrator.session_continuity_contract.v1",
        "resume_supported": True,
        "resume_kind": resume_kind,
        "compaction_stage": "fresh_turn",
        "runtime_duration_seconds": None,
        "usage_cost_measurement_status": "not_yet_measured",
        "runtime_cost_provenance": {
            "format": "agent_orchestrator.runtime_cost_provenance.v1",
            "duration_source": "session_snapshot_pending_runtime",
            "cost_source": "session_snapshot_pending_runtime",
        },
        "shared_evidence_surface": [
            "session_snapshot",
            "runtime_payload",
            "workspace_index",
            "ui_execution_summary",
            "cli_execution_summary",
            "docs_evidence",
        ],
        "workflow_continuity": workflow_continuity,
        "latest_recovery_hint": latest_recovery_hint,
        "continuity_snapshot": {
            "format": "agent_orchestrator.session_continuity_snapshot.v1",
            "artifact_backed": True,
            "snapshot_status": "ready",
            "resume_anchor": {
                "resume_kind": resume_kind,
                "planned_verification_command_present": False,
                "recent_observation_count": 0,
                "repair_summary_present": False,
            },
            "program_digest": {
                "program_goal": program_goal,
                "active_milestone": active_milestone,
                "completed_milestone_count": 0,
                "pending_followup_count": len(ready_next_units) if isinstance(ready_next_units, list) else 0,
                "blocked_unit_count": len(blocked_units) if isinstance(blocked_units, list) else 0,
            },
            "compaction_digest": {
                "compaction_stage": "fresh_turn",
                "masked_observation_count": 0,
                "summarization_triggered": False,
                "summarization_ready": False,
            },
            "runtime_cost": {
                "runtime_duration_seconds": None,
                "usage_cost_measurement_status": "not_yet_measured",
            },
            "runtime_cost_provenance": {
                "format": "agent_orchestrator.runtime_cost_provenance.v1",
                "duration_source": "session_snapshot_pending_runtime",
                "cost_source": "session_snapshot_pending_runtime",
            },
            "continuity_pressure": {
                "format": "agent_orchestrator.continuity_pressure.v1",
                "observation_pressure": 0,
                "compaction_pressure": "fresh_turn",
                "pending_followup_count": len(ready_next_units) if isinstance(ready_next_units, list) else 0,
                "blocked_unit_count": len(blocked_units) if isinstance(blocked_units, list) else 0,
                "summarization_pressure": False,
                "pressure_level": "low",
            },
            "shared_evidence_surface": [
                "session_snapshot",
                "runtime_payload",
                "workspace_index",
                "ui_execution_summary",
                "cli_execution_summary",
                "docs_evidence",
            ],
        },
        "continuity_pressure": {
            "format": "agent_orchestrator.continuity_pressure.v1",
            "observation_pressure": 0,
            "compaction_pressure": "fresh_turn",
            "pending_followup_count": len(ready_next_units) if isinstance(ready_next_units, list) else 0,
            "blocked_unit_count": len(blocked_units) if isinstance(blocked_units, list) else 0,
            "summarization_pressure": False,
            "pressure_level": "low",
        },
        "long_horizon_posture": {
            "resume_ready": True,
            "recovery_active": False,
            "verification_resume_ready": False,
            "context_pressure": False,
            "summarization_ready": False,
            "pending_followup_count": len(ready_next_units) if isinstance(ready_next_units, list) else 0,
            "resume_posture": (
                "approval_reentry"
                if resume_kind == "approval_resume"
                else "same_task_resume"
                if resume_kind in {"resume_if_same_task", "planner_continue"}
                else "fresh_entry"
            ),
        },
        "program_posture": {
            "program_goal": program_goal,
            "active_milestone": active_milestone,
            "completed_milestones": [],
            "ready_next_units": list(ready_next_units) if isinstance(ready_next_units, list) else [],
            "blocked_units": list(blocked_units) if isinstance(blocked_units, list) else [],
        },
        "delegation_contract": dict(delegation_contract),
        "program_continuity": {
            "resume_supported": True,
            "resume_kind": resume_kind,
            "compaction_stage": "fresh_turn",
            "continuity_artifact_status": "session_snapshot_ready",
            "latest_recovery_hint": latest_recovery_hint,
        },
        "daily_driver_readiness": {
            "tool_surface_ready": False,
            "planner_ready": bool(planner_decision.get("format")),
            "session_ready": True,
            "adapter_ready": bool(delegation_contract.get("selected_executor")),
            "shared_productization_ready": False,
            "long_chain_task_ready": False,
            "daily_driver_main_path_ready": False,
            "open_product_gap": "runtime_evidence_pending",
        },
        "comparative_benchmark": pending_comparative_benchmark,
        "comparative_benchmark_digest": pending_comparative_benchmark_digest,
        "comparative_completion_summary": build_comparative_completion_summary(
            benchmark_digest=pending_comparative_benchmark_digest,
            comparative_benchmark=pending_comparative_benchmark,
        ),
        "milestone_verification": {
            "verification_status": "pending" if "verify" in planner_decision.get("selected_actions", []) else "not_planned",
            "remaining_checks": list(task_contract.get("acceptance_criteria", []))
            if isinstance(task_contract.get("acceptance_criteria"), list)
            else [],
            "checkpoint_ready": False,
        },
        "operator_control": {
            "next_recommended_action": continuity_outline.get("next_recommended_action"),
            "runbook_recovery_lane": (
                "approval_pause"
                if autonomy_posture.get("approval_pause_state")
                else "clarify_pause"
                if autonomy_posture.get("clarify_pause_state")
                else "continue_native"
            ),
            "approval_pause_state": autonomy_posture.get("approval_pause_state"),
            "clarify_pause_state": autonomy_posture.get("clarify_pause_state"),
            "resume_expectation": delegation_contract.get("resume_expectation"),
            "resume_posture": (
                "approval_reentry"
                if resume_kind == "approval_resume"
                else "same_task_resume"
                if resume_kind in {"resume_if_same_task", "planner_continue"}
                else "fresh_entry"
            ),
            "planner_governed_alternatives": planner_governed_alternatives,
        },
        "autonomy_posture": {
            **dict(autonomy_posture),
            "resume_posture": (
                "approval_reentry"
                if resume_kind == "approval_resume"
                else "same_task_resume"
                if resume_kind in {"resume_if_same_task", "planner_continue"}
                else "fresh_entry"
            ),
            "planner_governed_alternatives": planner_governed_alternatives,
        },
    }


def _planner_governed_alternatives_snapshot(decision_evidence: dict[str, object]) -> list[dict[str, object]]:
    if not isinstance(decision_evidence, dict):
        return []
    candidates = (
        decision_evidence.get("decision_candidate_evidence", [])
        if isinstance(decision_evidence.get("decision_candidate_evidence"), list)
        else []
    )
    governed: list[dict[str, object]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        strategy = str(candidate.get("strategy") or "").strip()
        if strategy not in {"need_human_confirmation", "external_handoff", "fallback_external"}:
            continue
        metadata = candidate.get("metadata", {}) if isinstance(candidate.get("metadata"), dict) else {}
        action = (
            "need_human_confirmation"
            if strategy == "need_human_confirmation"
            else "handoff_external"
            if strategy == "external_handoff"
            else "fallback_external"
        )
        governed.append(
            {
                "action": action,
                "strategy": strategy,
                "selected": bool(candidate.get("selected")),
                "reason": metadata.get("reason"),
                "requires_human_confirmation": metadata.get("requires_human_confirmation"),
            }
        )
    return governed


def _planner_action_coverage_snapshot(
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
    autonomy_selected = [
        name
        for name, payload in autonomy_actions.items()
        if isinstance(name, str) and isinstance(payload, dict) and payload.get("selected") is True
    ]
    return {
        "selected_action_count": len(selected),
        "selected_actions": selected,
        "autonomy_selected_action_count": len(autonomy_selected),
        "autonomy_selected_actions": autonomy_selected,
        "candidate_count": len(candidate_evidence),
        "candidate_strategies": [
            str(item.get("strategy"))
            for item in candidate_evidence
            if isinstance(item, dict) and item.get("strategy")
        ],
        "governed_alternative_count": len(planner_governed_alternatives),
        "governed_alternative_strategies": [
            str(item.get("strategy"))
            for item in planner_governed_alternatives
            if isinstance(item, dict) and item.get("strategy")
        ],
    }


def _compacted_context_summary_snapshot(
    *,
    requirement: str,
    task_contract: dict[str, object],
    strategy_summary: dict[str, object],
    resume_kind: str,
) -> dict[str, object]:
    goal = task_contract.get("goal") or requirement
    decision_evidence = (
        strategy_summary.get("decision_evidence", {})
        if isinstance(strategy_summary.get("decision_evidence"), dict)
        else {}
    )
    program_posture = (
        decision_evidence.get("program_posture", {})
        if isinstance(decision_evidence.get("program_posture"), dict)
        else {}
    )
    blocked_units = (
        program_posture.get("blocked_units", [])
        if isinstance(program_posture.get("blocked_units"), list)
        else []
    )
    ready_next_units = (
        program_posture.get("ready_next_units", [])
        if isinstance(program_posture.get("ready_next_units"), list)
        else []
    )
    latest_recovery_hint = (
        f"Resume with {ready_next_units[0]}"
        if ready_next_units
        else "Use the next planned work unit and preserve verification evidence."
    )
    return {
        "objective": goal,
        "current_status": "blocked" if blocked_units else "prepared",
        "compaction_stage": "fresh_turn",
        "masked_observation_count": 0,
        "pending_step_count": len(ready_next_units),
        "latest_recovery_hint": latest_recovery_hint,
        "resume_kind": resume_kind,
    }


def _merge_session_continuity_contract(
    existing: dict[str, object],
    *,
    payload: dict[str, object],
) -> dict[str, object]:
    runtime_contract = (
        payload.get("session_continuity_contract", {})
        if isinstance(payload.get("session_continuity_contract"), dict)
        else {}
    )
    merged = dict(existing)
    if runtime_contract:
        for key, value in runtime_contract.items():
            if isinstance(value, dict):
                merged[key] = dict(value)
            elif isinstance(value, list):
                merged[key] = list(value)
            else:
                merged[key] = value
    comparative_digest = (
        payload.get("comparative_benchmark_digest", {})
        if isinstance(payload.get("comparative_benchmark_digest"), dict)
        else {}
    )
    benchmark = (
        payload.get("comparative_benchmark", {})
        if isinstance(payload.get("comparative_benchmark"), dict)
        else {}
    )
    if isinstance(benchmark.get("comparison_posture"), dict):
        comparative_digest = build_runtime_comparative_benchmark_digest(benchmark)
        merged["comparative_benchmark"] = dict(benchmark)
    if comparative_digest:
        merged["comparative_benchmark_digest"] = dict(comparative_digest)
    comparative_completion_summary = (
        runtime_contract.get("comparative_completion_summary", {})
        if isinstance(runtime_contract.get("comparative_completion_summary"), dict)
        else {}
    )
    if not comparative_completion_summary and benchmark:
        comparative_completion_summary = build_comparative_completion_summary(
            benchmark_digest=comparative_digest,
            comparative_benchmark=benchmark,
        )
    if comparative_completion_summary:
        merged["comparative_completion_summary"] = dict(comparative_completion_summary)
    session_productization_surface = (
        runtime_contract.get("session_productization_surface", {})
        if isinstance(runtime_contract.get("session_productization_surface"), dict)
        else {}
    )
    operator_continuity = (
        session_productization_surface.get("operator_continuity", {})
        if isinstance(session_productization_surface.get("operator_continuity"), dict)
        else {}
    )
    if operator_continuity:
        merged_operator_control = dict(merged.get("operator_control", {})) if isinstance(merged.get("operator_control"), dict) else {}
        for key in ("next_recommended_action", "runbook_recovery_lane", "approval_pause_state", "clarify_pause_state", "resume_expectation", "resume_posture"):
            if operator_continuity.get(key) is not None:
                merged_operator_control[key] = operator_continuity.get(key)
        if merged_operator_control:
            merged["operator_control"] = merged_operator_control
        if operator_continuity.get("resume_expectation") is not None:
            merged_delegation_contract = (
                dict(merged.get("delegation_contract", {}))
                if isinstance(merged.get("delegation_contract"), dict)
                else {}
            )
            merged_delegation_contract["resume_expectation"] = operator_continuity.get("resume_expectation")
            merged["delegation_contract"] = merged_delegation_contract
    workflow_continuity = (
        runtime_contract.get("workflow_continuity", {})
        if isinstance(runtime_contract.get("workflow_continuity"), dict)
        else {}
    )
    if not workflow_continuity:
        workflow_continuity = (
            session_productization_surface.get("workflow_continuity", {})
            if isinstance(session_productization_surface.get("workflow_continuity"), dict)
            else {}
        )
    if workflow_continuity:
        merged["workflow_continuity"] = dict(workflow_continuity)
    compacted_context_summary = _merge_compacted_context_summary(
        {},
        payload=payload,
        fallback_goal=None,
    )
    if compacted_context_summary:
        compaction_stage = compacted_context_summary.get("compaction_stage")
        latest_recovery_hint = compacted_context_summary.get("latest_recovery_hint")
        resume_kind = compacted_context_summary.get("resume_kind")
        pending_step_count = compacted_context_summary.get("pending_step_count")
        masked_observation_count = compacted_context_summary.get("masked_observation_count", 0)
        if compaction_stage is not None:
            merged["compaction_stage"] = compaction_stage
        if latest_recovery_hint:
            merged["latest_recovery_hint"] = latest_recovery_hint
        if resume_kind:
            merged["resume_kind"] = resume_kind
        continuity_snapshot = (
            dict(merged.get("continuity_snapshot", {}))
            if isinstance(merged.get("continuity_snapshot"), dict)
            else {}
        )
        if continuity_snapshot:
            program_digest = (
                dict(continuity_snapshot.get("program_digest", {}))
                if isinstance(continuity_snapshot.get("program_digest"), dict)
                else {}
            )
            if pending_step_count is not None:
                program_digest["pending_followup_count"] = pending_step_count
            continuity_snapshot["program_digest"] = program_digest
            continuity_snapshot["compaction_digest"] = {
                **(
                    dict(continuity_snapshot.get("compaction_digest", {}))
                    if isinstance(continuity_snapshot.get("compaction_digest"), dict)
                    else {}
                ),
                "compaction_stage": compaction_stage,
                "masked_observation_count": masked_observation_count,
                "summarization_triggered": compaction_stage not in {None, "fresh_turn", "full_fidelity"},
                "summarization_ready": compaction_stage == "summarization_ready",
            }
            continuity_snapshot["continuity_pressure"] = {
                **(
                    dict(continuity_snapshot.get("continuity_pressure", {}))
                    if isinstance(continuity_snapshot.get("continuity_pressure"), dict)
                    else {}
                ),
                "compaction_pressure": compaction_stage or continuity_snapshot.get("continuity_pressure", {}).get("compaction_pressure")
                if isinstance(continuity_snapshot.get("continuity_pressure"), dict)
                else compaction_stage,
                "pending_followup_count": pending_step_count if pending_step_count is not None else continuity_snapshot.get("continuity_pressure", {}).get("pending_followup_count")
                if isinstance(continuity_snapshot.get("continuity_pressure"), dict)
                else pending_step_count,
                "summarization_pressure": compaction_stage == "summarization_ready",
            }
            merged["continuity_snapshot"] = continuity_snapshot
        continuity_pressure = (
            dict(merged.get("continuity_pressure", {}))
            if isinstance(merged.get("continuity_pressure"), dict)
            else {}
        )
        if continuity_pressure:
            continuity_pressure["compaction_pressure"] = compaction_stage or continuity_pressure.get("compaction_pressure")
            if pending_step_count is not None:
                continuity_pressure["pending_followup_count"] = pending_step_count
            continuity_pressure["summarization_pressure"] = compaction_stage == "summarization_ready"
            merged["continuity_pressure"] = continuity_pressure
        long_horizon_posture = (
            dict(merged.get("long_horizon_posture", {}))
            if isinstance(merged.get("long_horizon_posture"), dict)
            else {}
        )
        if long_horizon_posture:
            long_horizon_posture["context_pressure"] = bool(
                compaction_stage not in {None, "fresh_turn", "full_fidelity"} or masked_observation_count
            )
            long_horizon_posture["summarization_ready"] = compaction_stage == "summarization_ready"
            if pending_step_count is not None:
                long_horizon_posture["pending_followup_count"] = pending_step_count
            merged["long_horizon_posture"] = long_horizon_posture
        program_continuity = (
            dict(merged.get("program_continuity", {}))
            if isinstance(merged.get("program_continuity"), dict)
            else {}
        )
        if program_continuity:
            if compaction_stage is not None:
                program_continuity["compaction_stage"] = compaction_stage
            if latest_recovery_hint:
                program_continuity["latest_recovery_hint"] = latest_recovery_hint
            if resume_kind:
                program_continuity["resume_kind"] = resume_kind
            merged["program_continuity"] = program_continuity
    if "shared_evidence_surface" in merged and isinstance(merged["shared_evidence_surface"], list):
        merged["shared_evidence_surface"] = list(dict.fromkeys([*existing.get("shared_evidence_surface", []), *merged["shared_evidence_surface"]]))
    return merged


def _merge_compacted_context_summary(
    existing: dict[str, object],
    *,
    payload: dict[str, object],
    fallback_goal: str | None,
) -> dict[str, object]:
    compacted = (
        payload.get("compacted_context_summary", {})
        if isinstance(payload.get("compacted_context_summary"), dict)
        else {}
    )
    if compacted:
        return dict(compacted)
    compressed_context = (
        payload.get("compressed_context", {})
        if isinstance(payload.get("compressed_context"), dict)
        else {}
    )
    if compressed_context:
        return {
            "objective": compressed_context.get("objective") or fallback_goal,
            "current_status": compressed_context.get("current_status"),
            "compaction_stage": compressed_context.get("compaction_stage") or compressed_context.get("stage"),
            "masked_observation_count": compressed_context.get("masked_observation_count", compressed_context.get("masked_count", 0)),
            "pending_step_count": compressed_context.get("pending_step_count", len(compressed_context.get("pending_steps", [])) if isinstance(compressed_context.get("pending_steps"), list) else 0),
            "latest_recovery_hint": compressed_context.get("latest_recovery_hint"),
            "resume_kind": compressed_context.get("resume_kind"),
        }
    return dict(existing)


def _merge_continuity_outline(
    existing: dict[str, object],
    *,
    continuity_contract: dict[str, object],
    planner_family: str,
) -> dict[str, object]:
    if not continuity_contract:
        return dict(existing)
    derived = derive_session_continuity_outline_from_contract(
        continuity_contract=continuity_contract,
        planner_family=planner_family,
    )
    if not derived:
        return dict(existing)
    merged = dict(existing)
    for key, value in derived.items():
        if isinstance(value, dict):
            merged[key] = dict(value)
        elif isinstance(value, list):
            merged[key] = list(value)
        else:
            merged[key] = value
    return merged


def _merge_comparative_benchmark_digest(
    existing: dict[str, object],
    *,
    payload: dict[str, object],
) -> dict[str, object]:
    benchmark = (
        payload.get("comparative_benchmark", {})
        if isinstance(payload.get("comparative_benchmark"), dict)
        else {}
    )
    if isinstance(benchmark.get("comparison_posture"), dict):
        return build_runtime_comparative_benchmark_digest(benchmark)
    digest = (
        payload.get("comparative_benchmark_digest", {})
        if isinstance(payload.get("comparative_benchmark_digest"), dict)
        else {}
    )
    if digest:
        return dict(digest)
    return dict(existing)


def _runtime_evidence_pending_comparative_benchmark() -> dict[str, object]:
    return {
        "format": "agent_orchestrator.comparative_benchmark_summary.v1",
        "native_default_path": None,
        "case_count": 0,
        "productization_case_count": 0,
        "daily_driver_main_path_ready": False,
        "daily_driver_main_path_ready_cases": 0,
        "shared_productization_contract_ready": False,
        "shared_contract_alignment": {
            "session_posture_cases": 1,
        },
        "comparison_posture_basis": {
            "daily_driver_main_path_ready_cases": 0,
            "evidence_scope": "runtime_evidence_pending",
            "comparison_limitations": [
                "runtime_or_workspace_benchmark_not_projected",
            ],
        },
        "comparison_posture": {
            "status": "runtime_evidence_pending",
            "confidence": "runtime_evidence_pending",
            "foundation_gap_remaining": True,
            "remaining_gap_classes": [
                "runtime_evidence_pending",
                "external_comparison_harness",
            ],
        },
        "comparison_proof_strength": {
            "direct_proof_status": "runtime_evidence_pending",
            "repeatability_status": "runtime_evidence_pending",
            "repeatability_ready": False,
            "stronger_task_family_count": 0,
            "broader_task_family_count": 0,
            "stronger_task_families": [],
            "repo_task_acceptance_families_proven": [],
            "daily_driver_repo_task_families_proven": [],
            "daily_driver_repo_task_family_count": 0,
            "broader_repeatability_gap_families": [],
            "planner_candidate_status": "runtime_evidence_pending",
            "adapter_unification_status": "runtime_evidence_pending",
        },
        "comparison_grade_assessment": {
            "status": "runtime_evidence_pending",
            "comparison_grade_ready": False,
            "external_harness_ready": False,
            "blocking_gap": "runtime_evidence_pending",
        },
        "external_comparison_harness_surface": {
            "harness_status": "runtime_evidence_pending",
            "operator_action": "wait_for_runtime_or_workspace_benchmark_projection",
            "next_evidence_milestone": "runtime_or_workspace_benchmark_projection",
            "requirements": {
                "required_shared_surfaces": [],
                "required_external_artifacts": [],
                "missing_external_artifacts": [],
            },
        },
        "shared_evidence_surface": [
            "session_snapshot",
            "session_continuity",
            "session_productization_surface",
            "compacted_context_summary",
        ],
    }


def _default_next_action(
    *,
    selected_execution_strategy: str,
    route_intent: dict[str, object],
) -> str | None:
    for action in ("clarify", "explore", "edit", "verify", "handoff", "fallback"):
        if route_intent.get(action):
            return action
    strategy = selected_execution_strategy.strip().lower()
    if "clarify" in strategy:
        return "clarify"
    if "explore" in strategy or "investigation" in strategy:
        return "explore"
    if "handoff" in strategy:
        return "handoff"
    if "fallback" in strategy:
        return "fallback"
    if strategy:
        return "edit"
    return None
