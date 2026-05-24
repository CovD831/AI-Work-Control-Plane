from fastapi.testclient import TestClient

from agent_orchestrator import Orchestrator
from agent_orchestrator.jobs import FileJobRuntime
from agent_orchestrator.planning import PlanStore, TeamOrchestrator
from agent_orchestrator.run_store import RunStore
from agent_orchestrator.ui_server import create_app
from agent_orchestrator.ui_service import DashboardService


def _client(tmp_path):
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=FileJobRuntime(root=tmp_path / "jobs"),
        project_root=tmp_path,
    )
    team.orchestrator.run_store = RunStore(root=tmp_path / "runs")
    service = DashboardService(
        team=team,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
    )
    return TestClient(create_app(service)), service


def test_global_stream_returns_event_stream_frames(tmp_path) -> None:
    client, service = _client(tmp_path)
    service.create_session("Build dashboard")

    response = client.get("/api/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: orchestration_event" in response.text
    assert "event: team_message" in response.text


def test_session_stream_returns_session_scoped_frames(tmp_path) -> None:
    client, service = _client(tmp_path)
    session = service.create_session("Build dashboard")

    response = client.get(f"/api/sessions/{session['id']}/stream")

    assert response.status_code == 200
    assert "team_message" in response.text
    assert str(session["id"]) in response.text


def test_memory_search_endpoint_returns_records(tmp_path) -> None:
    client, service = _client(tmp_path)
    service.create_session("Build dashboard")

    response = client.get("/api/memory/search?q=dashboard")

    assert response.status_code == 200
    assert response.json()["records"]
