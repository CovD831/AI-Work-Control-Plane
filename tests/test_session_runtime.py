from agent_orchestrator.session import SessionRuntime


def test_session_runtime_records_turn_snapshot_and_activity(tmp_path) -> None:
    runtime = SessionRuntime(tmp_path / "agent_sessions")
    session = runtime.start_session(origin="cli_direct", metadata={"entry": "test"})

    updated_session, turn, snapshot = runtime.start_turn(
        session_id=session.session_id,
        requirement="Fix the login button click handler.",
        route={"task_kind": "direct_fix", "execution_mode": "legacy"},
        clarify_summary={"task_type": "implementation"},
        strategy_summary={"selected_execution_strategy": "direct_edit"},
        task_contract={"goal": "Fix handler"},
        compatibility_metadata={"legacy_decompose_used": True},
        selected_execution_strategy="direct_edit",
        planner_family="native",
    )

    assert updated_session.current_turn_id == turn.turn_id
    assert turn.context_snapshot_id == snapshot.snapshot_id
    assert snapshot.selected_execution_strategy == "direct_edit"
    assert snapshot.planner_family == "native"
    assert snapshot.planner_decision["format"] == "agent_orchestrator.session_planner_snapshot.v1"
    assert snapshot.planner_decision["selected_execution_strategy"] == "direct_edit"
    assert snapshot.planner_decision["autonomy_posture"]["pause_expected"] is False
    assert snapshot.planner_decision["control_surface"]["format"] == "agent_orchestrator.session_planner_control_surface.v1"
    assert snapshot.planner_decision["control_surface"]["continue_native"] is True
    assert snapshot.planner_decision["control_surface"]["next_recommended_action"] == "edit"
    assert snapshot.planner_decision["delegation_contract"]["resume_expectation"] is None
    assert snapshot.continuity_outline["format"] == "agent_orchestrator.session_continuity_outline.v1"
    assert snapshot.continuity_outline["goal"] == "Fix handler"
    assert snapshot.continuity_outline["next_recommended_action"] == "edit"
    assert snapshot.continuity_outline["autonomy_posture"]["handoff_expected"] is False
    assert snapshot.session_continuity_contract["format"] == "agent_orchestrator.session_continuity_contract.v1"
    assert snapshot.session_continuity_contract["resume_supported"] is True
    assert snapshot.session_continuity_contract["workflow_continuity"]["format"] == (
        "agent_orchestrator.session_workflow_continuity.v1"
    )
    assert snapshot.session_continuity_contract["workflow_continuity"]["selected_workflow_stages"] == []
    assert snapshot.session_productization_surface["format"] in {
        "agent_orchestrator.session_productization_surface.compat.v1",
        "agent_orchestrator.session_productization_surface.v1",
    }
    assert snapshot.session_continuity_contract["comparative_benchmark_digest"]["comparison_status"] == (
        "runtime_evidence_pending"
    )
    assert snapshot.session_continuity_contract["comparative_benchmark_digest"]["remaining_gap_classes"] == [
        "runtime_evidence_pending",
        "external_comparison_harness",
    ]
    assert snapshot.session_continuity_contract["comparative_benchmark_digest"]["evidence_scope"] == (
        "runtime_evidence_pending"
    )
    assert snapshot.session_continuity_contract["comparative_benchmark_digest"]["session_posture_cases"] == 1
    assert snapshot.session_continuity_contract["comparative_benchmark"]["comparison_posture"]["status"] == (
        "runtime_evidence_pending"
    )
    assert snapshot.comparative_benchmark["comparison_posture"]["status"] == "runtime_evidence_pending"
    assert snapshot.session_continuity_contract["comparative_completion_summary"]["format"] == "agent_orchestrator.comparative_completion_summary.v1"
    assert snapshot.comparative_benchmark_digest["comparison_status"] == "runtime_evidence_pending"
    assert snapshot.comparative_benchmark_digest["external_harness_operator_action"] == (
        "wait_for_runtime_or_workspace_benchmark_projection"
    )
    assert snapshot.compacted_context_summary["objective"] == "Fix handler"
    assert snapshot.compacted_context_summary["compaction_stage"] == "fresh_turn"

    updated_turn = runtime.attach_run_result(
        session_id=session.session_id,
        turn_id=turn.turn_id,
        linked_run_id="run-123",
        status="completed",
        accepted=True,
        runtime_name="legacy",
        payload={
            "run_id": "run-123",
            "session_continuity_contract": {
                "format": "agent_orchestrator.session_continuity_contract.v1",
                "resume_supported": True,
                "resume_kind": "resume_if_same_task",
                "compaction_stage": "light_compaction",
                "runtime_duration_seconds": 0.4,
                "usage_cost_measurement_status": "placeholder",
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
                        "next_recommended_action": "verify",
                        "resume_expectation": "resume_if_same_task",
                    },
                },
            },
            "compacted_context_summary": {
                "objective": "Fix handler",
                "current_status": "completed",
                "compaction_stage": "light_compaction",
                "masked_observation_count": 1,
                "pending_step_count": 0,
                "latest_recovery_hint": "verify complete",
            },
            "comparative_benchmark": {
                "comparison_posture": {
                    "status": "shared_productization_ready_but_daily_driver_proof_gap_remaining",
                    "confidence": "bounded_internal_evidence_only",
                    "foundation_gap_remaining": False,
                    "remaining_gap_classes": [
                        "long_chain_repo_closure_repeatability",
                        "multi_family_daily_driver_repeatability",
                        "platform_breadth",
                    ],
                },
                "comparison_posture_basis": {
                    "shared_productization_contract_ready": True,
                    "daily_driver_main_path_ready_cases": 0,
                    "planner_candidate_surface_ready": True,
                    "unified_adapter_contract_ready": True,
                    "evidence_scope": "bounded_internal_evidence_only",
                    "comparison_limitations": [
                        "no_authoritative_external_opencode_harness",
                    ],
                },
                "comparison_proof_strength": {
                    "direct_proof_status": "foundational_productization_only",
                    "repeatability_status": "not_yet_proven",
                    "planner_candidate_status": "native_first_candidate_surface_ready",
                    "adapter_unification_status": "same_contract_adapter_surface_ready",
                    "stronger_task_families": [],
                    "repo_task_acceptance_families_proven": [],
                    "daily_driver_repo_task_families_proven": [],
                    "daily_driver_repo_task_family_count": 0,
                    "broader_repeatability_gap_families": [
                        "multi_family_daily_driver_repo_tasks",
                    ],
                },
                "comparison_grade_assessment": {
                    "status": "internal_productization_ready_but_repeatability_or_external_gap_remaining",
                    "comparison_grade_ready": False,
                    "external_harness_ready": False,
                    "blocking_gap": "no_authoritative_external_opencode_harness",
                },
                "external_comparison_harness_surface": {
                    "harness_status": "missing_authoritative_opencode_harness",
                    "next_evidence_milestone": "authoritative_opencode_case_harness",
                    "operator_action": "maintain_human_audit_until_external_harness_ready",
                    "requirements": {
                        "required_shared_surfaces": [
                            "runtime_event_stream",
                            "session_continuity",
                            "workspace_index",
                        ],
                        "required_external_artifacts": [
                            "authoritative_opencode_case_harness",
                        ],
                        "missing_external_artifacts": [
                            "authoritative_opencode_case_harness",
                        ],
                    },
                },
                "shared_contract_alignment": {
                    "session_posture_cases": 1,
                },
                "shared_evidence_surface": [
                    "runtime_event_stream",
                    "session_continuity",
                    "workspace_index",
                ],
                "daily_driver_main_path_ready": False,
            },
        },
    )

    assert updated_turn.linked_run_id == "run-123"
    updated_snapshot = runtime.get_snapshot(session.session_id, snapshot.snapshot_id)
    assert updated_snapshot.session_continuity_contract["compaction_stage"] == "light_compaction"
    assert updated_snapshot.session_continuity_contract["comparative_benchmark_digest"]["comparison_status"] == (
        "shared_productization_ready_but_daily_driver_proof_gap_remaining"
    )
    assert updated_snapshot.session_continuity_contract["comparative_benchmark_digest"]["remaining_gap_classes"] == [
        "long_chain_repo_closure_repeatability",
        "multi_family_daily_driver_repeatability",
        "platform_breadth",
    ]
    assert updated_snapshot.session_continuity_contract["comparative_benchmark_digest"]["planner_candidate_surface_ready"] is True
    assert updated_snapshot.session_continuity_contract["comparative_benchmark_digest"]["unified_adapter_contract_ready"] is True
    assert updated_snapshot.session_continuity_contract["comparative_benchmark"]["comparison_posture"]["status"] == (
        "shared_productization_ready_but_daily_driver_proof_gap_remaining"
    )
    assert updated_snapshot.session_continuity_contract["comparative_benchmark"]["comparison_posture_basis"][
        "planner_candidate_surface_ready"
    ] is True
    assert updated_snapshot.continuity_outline["resume_kind"] == "resume_if_same_task"
    assert updated_snapshot.continuity_outline["compaction_stage"] == "light_compaction"
    assert updated_snapshot.continuity_outline["next_recommended_action"] == "verify"
    assert updated_snapshot.continuity_outline["resume_expectation"] == "resume_if_same_task"
    assert updated_snapshot.continuity_outline["autonomy_posture"]["resume_posture"] == "same_task_resume"
    assert updated_snapshot.session_productization_surface["format"] == "agent_orchestrator.session_productization_surface.v1"
    assert updated_snapshot.session_continuity_contract["workflow_continuity"]["active_stage"] == "verify"
    assert updated_snapshot.session_productization_surface["workflow_continuity"]["workflow_projection_ready"] is True
    assert updated_snapshot.session_productization_surface["operator_posture_digest"]["workflow_active_stage"] == "verify"
    assert updated_snapshot.session_productization_surface["comparative_benchmark_digest"]["external_harness_status"] == (
        "missing_authoritative_opencode_harness"
    )
    assert updated_snapshot.session_continuity_contract["comparative_completion_summary"]["completion_ready"] is False
    assert updated_snapshot.session_productization_surface["operator_continuity"]["next_recommended_action"] == "verify"
    assert updated_snapshot.comparative_benchmark_digest["comparison_status"] == (
        "shared_productization_ready_but_daily_driver_proof_gap_remaining"
    )
    assert updated_snapshot.comparative_benchmark["comparison_proof_strength"]["adapter_unification_status"] == (
        "same_contract_adapter_surface_ready"
    )
    assert updated_snapshot.comparative_benchmark_digest["external_harness_operator_action"] == (
        "maintain_human_audit_until_external_harness_ready"
    )
    assert updated_snapshot.comparative_benchmark_digest["broader_repeatability_gap_families"] == [
        "multi_family_daily_driver_repo_tasks"
    ]
    assert updated_snapshot.comparative_benchmark_digest["external_harness_status"] == (
        "missing_authoritative_opencode_harness"
    )
    assert updated_snapshot.compacted_context_summary["current_status"] == "completed"
    assert runtime.latest_turn(session.session_id) is not None


def test_session_runtime_merges_compressed_context_into_continuity_contract(tmp_path) -> None:
    runtime = SessionRuntime(tmp_path / "agent_sessions")
    session = runtime.start_session(origin="cli_direct")
    _, turn, snapshot = runtime.start_turn(
        session_id=session.session_id,
        requirement="Repair verification flow and preserve resume posture.",
        route={"task_kind": "direct_fix", "execution_mode": "coding_agent"},
        clarify_summary={"task_type": "implementation", "needs_clarification": False},
        strategy_summary={
            "selected_execution_strategy": "explore_then_edit",
            "planner_actions": ["explore", "edit", "verify", "resume_learning"],
            "decision_evidence": {
                "format": "agent_orchestrator.native_planner_decision.v1",
                "program_posture": {
                    "active_milestone": "Explore verification failure",
                    "ready_next_units": ["explore", "edit"],
                    "blocked_units": [],
                },
                "operator_control": {
                    "next_recommended_action": "explore",
                    "approval_pause_state": False,
                    "clarify_pause_state": False,
                },
                "delegation_contract": {
                    "selected_executor": "native",
                    "resume_expectation": "resume_if_same_task",
                },
                "autonomy_surface": {
                    "primary_action": "explore",
                },
            },
        },
        task_contract={"goal": "Repair verification flow"},
        compatibility_metadata={"legacy_decompose_used": False},
        selected_execution_strategy="explore_then_edit",
        planner_family="native",
    )

    runtime.attach_run_result(
        session_id=session.session_id,
        turn_id=turn.turn_id,
        linked_run_id="run-refresh",
        status="completed",
        accepted=True,
        runtime_name="coding_agent",
        payload={
            "compressed_context": {
                "objective": "Repair verification flow",
                "current_status": "summarized",
                "compaction_stage": "summarization_ready",
                "masked_observation_count": 2,
                "pending_step_count": 1,
                "latest_recovery_hint": "resume with verify",
                "resume_kind": "resume_if_same_task",
            }
        },
    )

    updated_snapshot = runtime.get_snapshot(session.session_id, snapshot.snapshot_id)

    assert updated_snapshot.session_continuity_contract["compaction_stage"] == "summarization_ready"
    assert updated_snapshot.session_continuity_contract["latest_recovery_hint"] == "resume with verify"
    assert updated_snapshot.session_continuity_contract["resume_kind"] == "resume_if_same_task"
    assert updated_snapshot.continuity_outline["compaction_stage"] == "summarization_ready"
    assert updated_snapshot.continuity_outline["resume_kind"] == "resume_if_same_task"
    assert updated_snapshot.continuity_outline["next_recommended_action"] == "explore"
    assert updated_snapshot.continuity_outline["autonomy_posture"]["resume_posture"] == "same_task_resume"
    assert updated_snapshot.session_productization_surface["continuity_readiness"]["compaction_ready"] is True


def test_session_runtime_refreshes_continuity_outline_from_runtime_contract(tmp_path) -> None:
    runtime = SessionRuntime(tmp_path / "agent_sessions")
    session = runtime.start_session(origin="cli_direct")

    _, turn, snapshot = runtime.start_turn(
        session_id=session.session_id,
        requirement="Repair verification flow and preserve resume posture.",
        route={"task_kind": "direct_fix", "execution_mode": "coding_agent"},
        clarify_summary={"task_type": "implementation", "needs_clarification": False},
        strategy_summary={
            "selected_execution_strategy": "explore_then_edit",
            "planner_actions": ["explore", "edit", "verify", "resume_learning"],
            "decision_evidence": {
                "format": "agent_orchestrator.native_planner_decision.v1",
                "program_posture": {
                    "active_milestone": "Explore verification failure",
                    "ready_next_units": ["explore", "edit"],
                    "blocked_units": [],
                },
                "operator_control": {
                    "next_recommended_action": "explore",
                    "approval_pause_state": False,
                    "clarify_pause_state": False,
                },
                "delegation_contract": {
                    "selected_executor": "native",
                    "resume_expectation": "resume_if_same_task",
                },
                "autonomy_surface": {
                    "primary_action": "explore",
                },
            },
        },
        task_contract={"goal": "Repair verification flow"},
        compatibility_metadata={"legacy_decompose_used": False},
        selected_execution_strategy="explore_then_edit",
        planner_family="native",
    )

    assert snapshot.continuity_outline["next_recommended_action"] == "explore"
    assert snapshot.continuity_outline["compaction_stage"] == "fresh_turn"

    runtime.attach_run_result(
        session_id=session.session_id,
        turn_id=turn.turn_id,
        linked_run_id="run-refresh",
        status="completed",
        accepted=True,
        runtime_name="coding_agent",
        payload={
            "session_continuity_contract": {
                "format": "agent_orchestrator.session_continuity_contract.v1",
                "resume_supported": True,
                "resume_kind": "approval_resume",
                "compaction_stage": "summarization_ready",
                "runtime_duration_seconds": 8.2,
                "usage_cost_measurement_status": "measured",
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
                "operator_control": {
                    "next_recommended_action": "verify",
                    "runbook_recovery_lane": "repair_then_verify",
                    "approval_pause_state": True,
                    "clarify_pause_state": False,
                    "resume_expectation": "approval_pause",
                    "resume_posture": "approval_reentry",
                },
                "autonomy_posture": {
                    "pause_expected": True,
                    "handoff_expected": False,
                    "fallback_expected": False,
                    "resume_posture": "approval_reentry",
                },
                "program_posture": {
                    "program_goal": "Repair verification flow",
                    "active_milestone": "Verify repaired flow",
                    "completed_milestones": ["explore", "edit"],
                    "ready_next_units": ["verify"],
                    "blocked_units": ["await_approval"],
                },
                "delegation_contract": {
                    "selected_executor": "native",
                    "resume_expectation": "approval_pause",
                },
                "session_productization_surface": {
                    "format": "agent_orchestrator.session_productization_surface.v1",
                    "operator_continuity": {
                        "next_recommended_action": "verify",
                        "resume_expectation": "approval_pause",
                        "resume_posture": "approval_reentry",
                    },
                    "autonomy_posture": {
                        "resume_posture": "approval_reentry",
                    },
                },
            },
        },
    )

    updated_snapshot = runtime.get_snapshot(session.session_id, snapshot.snapshot_id)

    assert updated_snapshot.continuity_outline["resume_kind"] == "approval_resume"
    assert updated_snapshot.continuity_outline["compaction_stage"] == "summarization_ready"
    assert updated_snapshot.continuity_outline["active_milestone"] == "Verify repaired flow"
    assert updated_snapshot.continuity_outline["ready_next_units"] == ["verify"]
    assert updated_snapshot.continuity_outline["blocked_units"] == ["await_approval"]
    assert updated_snapshot.continuity_outline["next_recommended_action"] == "verify"
    assert updated_snapshot.continuity_outline["approval_pause_state"] is True
    assert updated_snapshot.continuity_outline["resume_expectation"] == "approval_pause"
    assert updated_snapshot.continuity_outline["autonomy_posture"]["resume_posture"] == "approval_reentry"
    assert updated_snapshot.session_productization_surface["workflow_continuity"]["active_stage"] == "verify"


def test_session_runtime_promotes_surface_only_workflow_continuity_into_contract(tmp_path) -> None:
    runtime = SessionRuntime(tmp_path / "agent_sessions")
    session = runtime.start_session(origin="cli_direct")
    _, turn, snapshot = runtime.start_turn(
        session_id=session.session_id,
        requirement="Preserve workflow continuity.",
        route={"task_kind": "direct_fix", "execution_mode": "coding_agent"},
        clarify_summary={"task_type": "implementation"},
        strategy_summary={"selected_execution_strategy": "explore_then_edit"},
        task_contract={"goal": "Preserve workflow continuity"},
        compatibility_metadata={},
        selected_execution_strategy="explore_then_edit",
        planner_family="native",
    )

    runtime.attach_run_result(
        session_id=session.session_id,
        turn_id=turn.turn_id,
        linked_run_id="run-workflow-surface",
        status="completed",
        accepted=True,
        runtime_name="coding_agent",
        payload={
            "session_continuity_contract": {
                "format": "agent_orchestrator.session_continuity_contract.v1",
                "resume_supported": True,
                "session_productization_surface": {
                    "format": "agent_orchestrator.session_productization_surface.v1",
                    "workflow_continuity": {
                        "format": "agent_orchestrator.session_workflow_continuity.v1",
                        "active_stage": "edit",
                        "selected_workflow_stages": ["explore", "edit"],
                        "workflow_projection_ready": True,
                    },
                },
            }
        },
    )

    updated_snapshot = runtime.get_snapshot(session.session_id, snapshot.snapshot_id)
    assert updated_snapshot.session_continuity_contract["workflow_continuity"]["active_stage"] == "edit"


def test_session_runtime_can_reload_written_records(tmp_path) -> None:
    runtime = SessionRuntime(tmp_path / "agent_sessions")
    session = runtime.start_session(origin="cli_direct")
    _, turn, snapshot = runtime.start_turn(
        session_id=session.session_id,
        requirement="Investigate queue stalls.",
        route={"task_kind": "investigation", "execution_mode": "legacy"},
        clarify_summary={"task_type": "investigation"},
        strategy_summary={"selected_execution_strategy": "investigation_only"},
        task_contract={"goal": "Investigate queue"},
        compatibility_metadata={},
        selected_execution_strategy="investigation_only",
        planner_family="native",
        resume_kind="fresh",
    )

    reloaded_session = runtime.get_session(session.session_id)
    reloaded_turn = runtime.get_turn(session.session_id, turn.turn_id)
    reloaded_snapshot = runtime.get_snapshot(session.session_id, snapshot.snapshot_id)

    assert reloaded_session.session_id == session.session_id
    assert reloaded_turn.turn_id == turn.turn_id
    assert reloaded_snapshot.snapshot_id == snapshot.snapshot_id
    assert reloaded_snapshot.planner_family == "native"
    assert reloaded_snapshot.planner_decision["format"] == "agent_orchestrator.session_planner_snapshot.v1"
    assert reloaded_snapshot.continuity_outline["resume_kind"] == "fresh"


def test_session_runtime_records_trajectory_with_path_selection_metadata(tmp_path) -> None:
    runtime = SessionRuntime(tmp_path / "agent_sessions")
    session = runtime.start_session(origin="cli_direct")
    _, turn, _ = runtime.start_turn(
        session_id=session.session_id,
        requirement="Investigate queue stalls.",
        route={"task_kind": "investigation", "execution_mode": "legacy", "default_path": "native"},
        clarify_summary={"task_type": "investigation"},
        strategy_summary={"selected_execution_strategy": "explore_then_edit"},
        task_contract={"goal": "Investigate queue"},
        compatibility_metadata={},
        selected_execution_strategy="explore_then_edit",
        planner_family="native",
    )

    trajectory = runtime.record_trajectory(
        session_id=session.session_id,
        turn_id=turn.turn_id,
        task_class="investigation_to_edit",
        path_selection={"default_path": "native", "selection_reason": "learning-backed"},
        stage="explore_then_edit",
        outcome="blocked",
        summary="scope drift requires realignment",
        metadata={"failure_shape": "exploration_ambiguity_or_scope_drift"},
    )

    assert trajectory.path_selection["default_path"] == "native"
    assert trajectory.metadata["failure_shape"] == "exploration_ambiguity_or_scope_drift"


def test_session_runtime_derives_planner_and_continuity_outline_for_clarify_pause(tmp_path) -> None:
    runtime = SessionRuntime(tmp_path / "agent_sessions")
    session = runtime.start_session(origin="cli_direct")
    _, _, snapshot = runtime.start_turn(
        session_id=session.session_id,
        requirement="Refactor auth integration safely.",
        route={
            "task_kind": "migration",
            "execution_mode": "coding_agent",
            "planner_intent": {"clarify": True, "pause": True, "edit": False},
        },
        clarify_summary={"needs_clarification": True, "task_type": "migration"},
        strategy_summary={
            "selected_execution_strategy": "clarify_then_edit",
            "planner_actions": ["clarify", "explore", "edit", "verify"],
            "selection_reason": "Need explicit clarification before editing.",
            "decision_evidence": {
                "format": "agent_orchestrator.native_planner_decision.v1",
                "selected_owner": "native",
                "program_posture": {
                    "active_milestone": "Clarify execution boundary for: Refactor auth integration safely.",
                    "ready_next_units": ["clarify", "explore"],
                    "blocked_units": ["await_clarification"],
                },
                "operator_control": {
                    "next_recommended_action": "clarify",
                    "clarify_pause_state": True,
                    "approval_pause_state": True,
                },
                "autonomy_surface": {
                    "primary_action": "clarify",
                },
            },
        },
        task_contract={"goal": "Refactor auth integration safely."},
        compatibility_metadata={"legacy_decompose_used": False},
        selected_execution_strategy="clarify_then_edit",
        planner_family="native",
    )

    assert snapshot.planner_decision["primary_action"] == "clarify"
    assert snapshot.planner_decision["route_planner_intent"]["clarify"] is True
    assert snapshot.planner_decision["autonomy_posture"]["pause_expected"] is False
    assert snapshot.planner_decision["control_surface"]["clarify"] is True
    assert snapshot.planner_decision["control_surface"]["pause"] is True
    assert snapshot.planner_decision["control_surface"]["next_recommended_action"] == "clarify"
    assert snapshot.continuity_outline["active_milestone"].startswith("Clarify execution boundary")
    assert snapshot.continuity_outline["clarify_pause_state"] is True
    assert snapshot.continuity_outline["approval_pause_state"] is True
    assert snapshot.continuity_outline["ready_next_units"] == ["clarify", "explore"]
    assert snapshot.continuity_outline["autonomy_posture"]["pause_expected"] is False


def test_session_runtime_start_turn_preserves_planner_governed_alternatives_in_snapshot_continuity_surface(tmp_path) -> None:
    runtime = SessionRuntime(tmp_path / "agent_sessions")
    session = runtime.start_session(origin="cli_direct")
    _, _, snapshot = runtime.start_turn(
        session_id=session.session_id,
        requirement="Refactor auth integration safely.",
        route={
            "task_kind": "migration",
            "execution_mode": "coding_agent",
            "planner_intent": {"clarify": True, "pause": True},
        },
        clarify_summary={"needs_clarification": True, "task_type": "migration"},
        strategy_summary={
            "selected_execution_strategy": "clarify_then_edit",
            "planner_actions": ["clarify", "explore", "edit", "verify"],
            "selection_reason": "Need explicit clarification before editing.",
            "decision_evidence": {
                "format": "agent_orchestrator.native_planner_decision.v1",
                "selected_owner": "native",
                "delegation_contract": {
                    "selected_executor": "native",
                    "resume_expectation": "approval_pause",
                },
                "program_posture": {
                    "active_milestone": "Clarify execution boundary for: Refactor auth integration safely.",
                    "ready_next_units": ["clarify", "explore"],
                    "blocked_units": ["await_clarification"],
                },
                "operator_control": {
                    "next_recommended_action": "clarify",
                    "clarify_pause_state": True,
                    "approval_pause_state": True,
                },
                "autonomy_surface": {
                    "primary_action": "clarify",
                },
                "decision_candidate_evidence": [
                    {
                        "strategy": "clarify_then_edit",
                        "selected": True,
                        "metadata": {"selected_candidate": True},
                    },
                    {
                        "strategy": "need_human_confirmation",
                        "selected": False,
                        "metadata": {
                            "reason": "approval_boundary",
                            "requires_human_confirmation": True,
                        },
                    },
                    {
                        "strategy": "external_handoff",
                        "selected": False,
                        "metadata": {"reason": "risk_exceeds_native_bounded_path"},
                    },
                ],
            },
        },
        task_contract={"goal": "Refactor auth integration safely."},
        compatibility_metadata={"legacy_decompose_used": False},
        selected_execution_strategy="clarify_then_edit",
        planner_family="native",
    )

    assert [item["action"] for item in snapshot.planner_decision["planner_governed_alternatives"]] == [
        "need_human_confirmation",
        "handoff_external",
    ]
    assert [item["action"] for item in snapshot.continuity_outline["planner_governed_alternatives"]] == [
        "need_human_confirmation",
        "handoff_external",
    ]
    assert [
        item["action"]
        for item in snapshot.session_continuity_contract["operator_control"]["planner_governed_alternatives"]
    ] == ["need_human_confirmation", "handoff_external"]
    assert [
        item["action"]
        for item in snapshot.session_productization_surface["operator_continuity"]["planner_governed_alternatives"]
    ] == ["need_human_confirmation", "handoff_external"]
    assert "alternatives=need_human_confirmation,handoff_external" in snapshot.session_productization_surface["operator_posture_digest"]["summary"]
