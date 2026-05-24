from agent_orchestrator import Orchestrator
from agent_orchestrator.ideation import run_ideation
from agent_orchestrator.memory import MemoryStore
from agent_orchestrator.messages import MessageStore
from agent_orchestrator.planning import PlanStore, TeamOrchestrator
from agent_orchestrator.roles import DEFAULT_AGENT_ROLES


def test_run_ideation_writes_proponent_skeptic_and_synthesis_messages(tmp_path) -> None:
    store = MessageStore(tmp_path / "messages")

    round_ = run_ideation(requirement="Build a dashboard", session_id="plan-1", message_store=store)
    messages = store.list_for_session("plan-1")

    assert len(round_.message_ids) == 5
    assert {message["from_role"] for message in messages} >= {"lead", "proponent", "skeptic"}
    assert any(message["to_role"] == "planner" for message in messages)


def test_team_ideate_creates_drafting_session_with_memory(tmp_path) -> None:
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )

    session = team.ideate("Build a dashboard")

    assert session.status == "drafting"
    assert session.resume.current_phase == "ideation"
    assert session.structured_brief.decision_rationale
    assert MessageStore(tmp_path / "messages").list_for_session(session.id)
    assert MemoryStore(tmp_path / "memory").query(session_id=session.id, namespace="ideation")


def test_ideation_roles_are_registered() -> None:
    assert DEFAULT_AGENT_ROLES["proponent"].layer == "decision"
    assert DEFAULT_AGENT_ROLES["skeptic"].layer == "decision"
