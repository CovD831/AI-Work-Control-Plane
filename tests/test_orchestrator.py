import json
import os
from datetime import UTC, datetime, timedelta

from agent_orchestrator import OrchestrationMode, Orchestrator, get_policy
from agent_orchestrator.run_store import RunStore
from agent_orchestrator.routing import PolicyRouter


def test_success_first_uses_full_parent_architecture() -> None:
    run = Orchestrator().run("Refactor auth integration", OrchestrationMode.SUCCESS_FIRST)

    assert run.accepted is True
    assert run.final_state == "accepted"
    assert run.policy.max_depth == 3
    assert run.policy.planner_agents == 4
    assert run.policy.review_required is True
    assert len(run.work_units) == 3
    assert run.work_units[1].depends_on == [run.work_units[0].id]
    assert run.work_units[2].depends_on == [run.work_units[1].id]
    assert len(run.jobs) == 6
    assert len(run.job_ids) == 6
    assert run.job_status_summary["completed"] == 6
    assert {job.kind for job in run.jobs} == {"implementation", "review"}
    assert all("review passed" in result.tests for result in run.results)
    assert all(result.job_ids for result in run.results)
    assert run.attempts and run.attempts[0].attempt_index == 0


def test_speed_first_adds_aggressive_parallelism() -> None:
    run = Orchestrator().run("Build dashboard", OrchestrationMode.SPEED_FIRST)

    assert run.accepted is True
    assert run.policy.parallelism == "aggressive"
    assert len(run.work_units) == 4


def test_cost_first_limits_work_units_and_depth() -> None:
    run = Orchestrator().run("Build dashboard", OrchestrationMode.COST_FIRST)

    assert run.accepted is True
    assert run.policy.max_depth == 1
    assert run.policy.parallelism == "limited"
    assert len(run.work_units) == 1
    assert run.results[0].tests == ["mock validation passed"]


def test_speed_first_failure_upgrades_to_success_first() -> None:
    run = Orchestrator().run("Fail the auth migration", OrchestrationMode.SPEED_FIRST)

    assert len(run.attempts) == 2
    assert run.final_mode == OrchestrationMode.SUCCESS_FIRST
    assert run.reroute_history[0]["from_mode"] == "speed_first"
    assert run.reroute_history[0]["to_mode"] == "success_first"


def test_reroute_can_be_disabled() -> None:
    run = Orchestrator().run("Fail the auth migration", OrchestrationMode.SPEED_FIRST, reroute=False)

    assert len(run.attempts) == 1
    assert run.reroute_history == []


def test_single_failed_work_unit_uses_dependency_rescue_without_upgrade() -> None:
    run = Orchestrator().run("Fail task", OrchestrationMode.SUCCESS_FIRST)

    assert len(run.attempts) == 1
    assert run.accepted is True
    assert run.reroute_history == []
    assert run.attempts[0].dependency_rescue_results
    assert run.attempts[0].replayed_work_unit_ids


def test_dependency_rescue_replays_downstream_units() -> None:
    run = Orchestrator().run("Fail auth migration", OrchestrationMode.SPEED_FIRST)

    assert run.attempts[0].replayed_work_unit_ids
    assert set(run.attempts[0].replayed_work_unit_ids) >= set(run.attempts[0].recovered_work_unit_ids)


def test_dependency_rescue_failure_then_upgrades_once() -> None:
    run = Orchestrator().run("Fail the auth migration", OrchestrationMode.COST_FIRST)

    assert run.attempts[0].dependency_rescue_results
    assert len(run.reroute_history) == 1
    assert run.reroute_history[0]["from_mode"] == "cost_first"
    assert run.reroute_history[0]["to_mode"] == "speed_first"


def test_high_risk_review_only_upgrades_once() -> None:
    run = Orchestrator().run("Fail the auth migration", OrchestrationMode.COST_FIRST)

    assert len(run.attempts) == 2
    assert run.reroute_history == [
        {
            "from_mode": "cost_first",
            "to_mode": "speed_first",
            "reasons": run.reroute_history[0]["reasons"],
            "confidence": run.reroute_history[0]["confidence"],
        }
    ]
    assert run.final_mode == OrchestrationMode.SPEED_FIRST
    assert any(
        attempt.failure_decision and attempt.failure_decision.next_mode is not None
        for attempt in run.attempts[:1]
    )


def test_policies_are_derived_from_one_interface() -> None:
    success = get_policy(OrchestrationMode.SUCCESS_FIRST)
    speed = get_policy(OrchestrationMode.SPEED_FIRST)
    cost = get_policy(OrchestrationMode.COST_FIRST)

    assert success.max_depth > speed.max_depth > cost.max_depth
    assert success.parallelism == "controlled"
    assert speed.parallelism == "aggressive"
    assert cost.parallelism == "limited"


def test_auto_mode_uses_policy_router() -> None:
    router = PolicyRouter()
    requirement = "Implement multiple independent modules in parallel"
    run = Orchestrator(router=router).run(requirement, None)

    assert run.routing_decision is not None
    assert run.routing_decision.mode.value == "speed_first"
    assert run.policy.parallelism == "aggressive"


def test_start_run_returns_handle(tmp_path) -> None:
    orchestrator = Orchestrator()
    orchestrator.run_store.root = tmp_path
    handle = orchestrator.start_run("Build dashboard", OrchestrationMode.SUCCESS_FIRST)

    assert handle.run_id
    assert handle.status in {"queued", "running"}
    assert handle.job_ids == []


def test_poll_run_round_trips_persisted_payload(tmp_path) -> None:
    orchestrator = Orchestrator()
    orchestrator.run_store.root = tmp_path
    run = orchestrator.run("Build dashboard", OrchestrationMode.SUCCESS_FIRST)
    loaded = orchestrator.poll_run(run.run_id)

    assert loaded.run_id == run.run_id
    assert loaded.final_mode == run.final_mode
    assert loaded.active_attempt_id == run.active_attempt_id


def test_lock_metadata_refreshes_and_is_readable(tmp_path) -> None:
    store = RunStore(root=tmp_path, stale_after_seconds=60)

    assert store.acquire_run_lock("run-1", owner="orchestrator", reason="test") is True
    first = store.read_run_lock("run-1")
    assert first is not None
    assert first["owner"] == "orchestrator"
    assert first["reason"] == "test"
    assert first["state"] == "active"

    heartbeat_before = first["heartbeat_at"]
    assert store.refresh_run_lock("run-1", owner="orchestrator", reason="running") is True
    second = store.read_run_lock("run-1")
    assert second is not None
    assert second["heartbeat_at"] >= heartbeat_before
    assert second["reason"] == "running"


def test_stale_lock_is_reclaimed(tmp_path) -> None:
    store = RunStore(root=tmp_path, stale_after_seconds=0.1)
    lock_path = tmp_path / "run-2.lock"
    lock_path.write_text(
        json.dumps(
            {
                "run_id": "run-2",
                "pid": os.getpid(),
                "owner": "orchestrator",
                "reason": "stale",
                "started_at": (datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
                "heartbeat_at": (datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lock_before = store.read_run_lock("run-2")
    assert lock_before is not None
    assert lock_before["stale"] is True
    assert store.acquire_run_lock("run-2", owner="orchestrator", reason="reclaim") is True
    lock_after = store.read_run_lock("run-2")
    assert lock_after is not None
    assert lock_after["stale"] is False
    assert lock_after["reason"] == "reclaim"


def test_restore_pending_runs_continues_after_restart(tmp_path) -> None:
    orchestrator = Orchestrator()
    orchestrator.run_store.root = tmp_path
    handle = orchestrator.start_run("Build dashboard", OrchestrationMode.SUCCESS_FIRST)
    assert handle.run_id

    restored = Orchestrator(run_store=orchestrator.run_store)
    run = restored.resume_run(handle.run_id)

    assert run.run_id == handle.run_id
    assert run.status in {"queued", "running", "completed", "blocked"}


def test_resume_run_is_idempotent_when_lock_held(tmp_path) -> None:
    orchestrator = Orchestrator()
    orchestrator.run_store.root = tmp_path
    handle = orchestrator.start_run("Build dashboard", OrchestrationMode.SUCCESS_FIRST)

    first = orchestrator.resume_run(handle.run_id)
    second = orchestrator.resume_run(handle.run_id)

    assert first.run_id == second.run_id
    assert first.active_attempt_id == second.active_attempt_id


def test_poll_run_works_while_lock_is_held(tmp_path) -> None:
    orchestrator = Orchestrator()
    orchestrator.run_store.root = tmp_path
    run = orchestrator.run("Build dashboard", OrchestrationMode.SUCCESS_FIRST)
    lock_path = tmp_path / f"{run.run_id}.lock"
    lock_path.write_text(
        json.dumps(
            {
                "run_id": run.run_id,
                "pid": os.getpid(),
                "owner": "orchestrator",
                "reason": "poll_test",
                "started_at": datetime.now(UTC).isoformat(),
                "heartbeat_at": datetime.now(UTC).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    polled = orchestrator.poll_run(run.run_id)

    assert polled.run_id == run.run_id
    assert polled.lock_status is not None
    assert polled.lock_status["state"] == "active"
