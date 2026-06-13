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
    )

    assert updated_session.current_turn_id == turn.turn_id
    assert turn.context_snapshot_id == snapshot.snapshot_id
    assert snapshot.selected_execution_strategy == "direct_edit"

    updated_turn = runtime.attach_run_result(
        session_id=session.session_id,
        turn_id=turn.turn_id,
        linked_run_id="run-123",
        status="completed",
        accepted=True,
        runtime_name="legacy",
        payload={"run_id": "run-123"},
    )

    assert updated_turn.linked_run_id == "run-123"
    assert runtime.latest_turn(session.session_id) is not None


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
        resume_kind="fresh",
    )

    reloaded_session = runtime.get_session(session.session_id)
    reloaded_turn = runtime.get_turn(session.session_id, turn.turn_id)
    reloaded_snapshot = runtime.get_snapshot(session.session_id, snapshot.snapshot_id)

    assert reloaded_session.session_id == session.session_id
    assert reloaded_turn.turn_id == turn.turn_id
    assert reloaded_snapshot.snapshot_id == snapshot.snapshot_id
