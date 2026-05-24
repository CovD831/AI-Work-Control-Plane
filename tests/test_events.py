from agent_orchestrator.events import EventStore
from agent_orchestrator import Orchestrator
from agent_orchestrator.planning import PlanStore, TeamOrchestrator


def test_event_store_appends_and_lists_recent_events(tmp_path) -> None:
    store = EventStore(tmp_path / "events")

    store.append(type="session.updated", scope="session", scope_id="plan-1", message="updated")
    store.append(type="action.completed", scope="session", scope_id="plan-2", message="executed")

    recent = store.list_recent()

    assert [event["scope_id"] for event in recent] == ["plan-2", "plan-1"]
    assert recent[0]["type"] == "action.completed"


def test_event_store_filters_by_session_payload(tmp_path) -> None:
    store = EventStore(tmp_path / "events")

    store.append(type="run.updated", scope="run", scope_id="run-1", message="run", payload={"plan_session_id": "plan-1"})
    store.append(type="session.updated", scope="session", scope_id="plan-2", message="other")

    events = store.list_for_session("plan-1")

    assert len(events) == 1
    assert events[0]["scope_id"] == "run-1"


def test_plan_store_writes_session_update_event(tmp_path) -> None:
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )

    session = team.start("Build a persisted plan artifact")
    events = EventStore(tmp_path / "events").list_for_session(session.id)

    assert events
    assert any(event["type"] == "session.updated" for event in events)
