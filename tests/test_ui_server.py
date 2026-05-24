from fastapi.testclient import TestClient

from agent_orchestrator import Orchestrator
from agent_orchestrator.jobs import FileJobRuntime, JobRequest
from agent_orchestrator.planning import PlanStore, TeamOrchestrator
from agent_orchestrator.run_store import RunStore
from agent_orchestrator.ui_server import create_app
from agent_orchestrator.ui_service import DashboardService


def _client(tmp_path, runtime: FileJobRuntime | None = None):
    runtime = runtime or FileJobRuntime(root=tmp_path / "jobs")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=runtime,
        project_root=tmp_path,
    )
    team.orchestrator.run_store = RunStore(root=tmp_path / "runs")
    service = DashboardService(
        team=team,
        plans_root=tmp_path / "plans",
        runs_root=tmp_path / "runs",
        jobs_root=tmp_path / "jobs",
        job_runtime=runtime,
    )
    return TestClient(create_app(service)), service


def test_global_stream_returns_event_stream_frames(tmp_path) -> None:
    runtime = FileJobRuntime(root=tmp_path / "jobs")
    client, service = _client(tmp_path, runtime=runtime)
    session = service.create_session("Build dashboard")
    job = runtime.start(
        JobRequest(
            task_id="ui-stream-job",
            provider="mock",
            kind="review",
            prompt="stream",
            cwd=str(tmp_path),
        )
    )
    runtime.complete(job.id, summary="done", stdout="ok")

    response = client.get("/api/stream?once=true")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: orchestration_event" in response.text
    assert "event: team_message" in response.text
    assert "event: job_update" in response.text


def test_session_stream_returns_session_scoped_frames(tmp_path) -> None:
    runtime = FileJobRuntime(root=tmp_path / "jobs")
    client, service = _client(tmp_path, runtime=runtime)
    session = service.create_session("Build dashboard")
    job = runtime.start(
        JobRequest(
            task_id=f"{session['id']}:review",
            provider="mock",
            kind="review",
            prompt="stream",
            cwd=str(tmp_path),
        )
    )
    runtime.complete(job.id, summary="done", stdout="ok")

    response = client.get(f"/api/sessions/{session['id']}/stream?once=true")

    assert response.status_code == 200
    assert "team_message" in response.text
    assert "job_update" in response.text
    assert str(session["id"]) in response.text


def test_memory_search_endpoint_returns_records(tmp_path) -> None:
    client, service = _client(tmp_path)
    service.create_session("Build dashboard")

    response = client.get("/api/memory/search?q=dashboard")

    assert response.status_code == 200
    assert response.json()["records"]


def test_index_contains_operator_and_job_control_mounts(tmp_path) -> None:
    client, _service = _client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert 'id="operator-summary"' in response.text
    assert 'id="job-actions"' in response.text
