"""FastAPI app for the local Agent Team Console."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, pathlib, typing
# RESPONSIBILITY: Expose dashboard API routes and static console assets.
# MODULE: interface
# ---

from pathlib import Path
import json
from typing import Any

from agent_orchestrator.ui_service import DashboardService, build_dashboard_service


def create_app(service: DashboardService | None = None) -> Any:
    try:
        from fastapi import Body, FastAPI, HTTPException
        from fastapi.responses import FileResponse
        from fastapi.responses import StreamingResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:
        raise RuntimeError("Install UI dependencies with `pip install -e '.[ui]'` to run the dashboard.") from exc

    dashboard = service or build_dashboard_service()
    app = FastAPI(title="Agent Team Console")
    static_dir = Path(__file__).with_name("ui_static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return dashboard.health()

    @app.get("/api/sessions")
    def list_sessions() -> dict[str, object]:
        return dashboard.list_sessions()

    @app.post("/api/sessions")
    def create_session(payload: dict[str, object] = Body(...)) -> dict[str, object]:
        return _call(lambda: dashboard.create_session(str(payload.get("requirement", ""))), HTTPException)

    @app.post("/api/sessions/ideate")
    def create_ideation_session(payload: dict[str, object] = Body(...)) -> dict[str, object]:
        return _call(lambda: dashboard.create_ideation_session(str(payload.get("requirement", ""))), HTTPException)

    @app.get("/api/sessions/{session_id}")
    def get_session(session_id: str) -> dict[str, object]:
        return _call(lambda: dashboard.get_session(session_id), HTTPException)

    @app.get("/api/events")
    def list_events() -> dict[str, object]:
        return dashboard.list_events()

    @app.get("/api/sessions/{session_id}/events")
    def list_session_events(session_id: str) -> dict[str, object]:
        return dashboard.list_session_events(session_id)

    @app.get("/api/memory")
    def list_memory() -> dict[str, object]:
        return dashboard.list_memory()

    @app.get("/api/memory/search")
    def search_memory(q: str = "", session_id: str | None = None) -> dict[str, object]:
        return dashboard.search_memory(q, session_id=session_id)

    @app.get("/api/sessions/{session_id}/memory")
    def list_session_memory(session_id: str) -> dict[str, object]:
        return dashboard.list_session_memory(session_id)

    @app.get("/api/messages")
    def list_messages() -> dict[str, object]:
        return dashboard.list_messages()

    @app.get("/api/sessions/{session_id}/messages")
    def list_session_messages(session_id: str) -> dict[str, object]:
        return dashboard.list_session_messages(session_id)

    @app.get("/api/stream")
    def stream_events() -> Any:
        return StreamingResponse(_sse_frames(dashboard.list_events()["events"], dashboard.list_messages()["messages"]), media_type="text/event-stream")

    @app.get("/api/sessions/{session_id}/stream")
    def stream_session_events(session_id: str) -> Any:
        return StreamingResponse(
            _sse_frames(
                dashboard.list_session_events(session_id)["events"],
                dashboard.list_session_messages(session_id)["messages"],
            ),
            media_type="text/event-stream",
        )

    @app.post("/api/sessions/{session_id}/revise")
    def revise_session(session_id: str, payload: dict[str, object] = Body(...)) -> dict[str, object]:
        closed_gap_ids = payload.get("closed_gap_ids", [])
        gap_ids = [str(item) for item in closed_gap_ids] if isinstance(closed_gap_ids, list) else []
        return _call(lambda: dashboard.revise_session(session_id, summary=str(payload.get("summary", "")), closed_gap_ids=gap_ids), HTTPException)

    @app.post("/api/sessions/{session_id}/approve")
    def approve_session(session_id: str) -> dict[str, object]:
        return _call(lambda: dashboard.approve_session(session_id), HTTPException)

    @app.post("/api/sessions/{session_id}/execute")
    def execute_session(session_id: str, payload: dict[str, object] = Body(default={})) -> dict[str, object]:
        mode = payload.get("mode") if isinstance(payload, dict) else None
        return _call(lambda: dashboard.execute_session(session_id, mode=str(mode) if mode else None), HTTPException)

    @app.post("/api/sessions/{session_id}/retry-review")
    def retry_review(session_id: str) -> dict[str, object]:
        return _call(lambda: dashboard.retry_review(session_id), HTTPException)

    @app.post("/api/sessions/{session_id}/retry-adversarial-review")
    def retry_adversarial_review(session_id: str) -> dict[str, object]:
        return _call(lambda: dashboard.retry_adversarial_review(session_id), HTTPException)

    @app.post("/api/sessions/{session_id}/resume")
    def resume_session(session_id: str, payload: dict[str, object] = Body(default={})) -> dict[str, object]:
        return _call(lambda: dashboard.resume_session(session_id, apply=bool(payload.get("apply", False))), HTTPException)

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, object]:
        return _call(lambda: dashboard.get_run(run_id), HTTPException)

    @app.get("/api/jobs")
    def list_jobs() -> dict[str, object]:
        return dashboard.list_jobs()

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, object]:
        return _call(lambda: dashboard.get_job(job_id), HTTPException)

    @app.get("/api/jobs/{job_id}/log")
    def get_job_log(job_id: str) -> dict[str, object]:
        return dashboard.get_job_log(job_id)

    @app.post("/api/jobs/{job_id}/send")
    def send_job(job_id: str, payload: dict[str, object] = Body(...)) -> dict[str, object]:
        return _call(lambda: dashboard.send_job(job_id, str(payload.get("message", ""))), HTTPException)

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str) -> dict[str, object]:
        return _call(lambda: dashboard.cancel_job(job_id), HTTPException)

    return app


def _call(fn: Any, http_exception: Any) -> Any:
    try:
        return fn()
    except KeyError as exc:
        raise http_exception(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise http_exception(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise http_exception(status_code=400, detail=str(exc)) from exc


def _sse_frames(events: object, messages: object) -> Any:
    for event in events if isinstance(events, list) else []:
        yield f"event: orchestration_event\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
    for message in messages if isinstance(messages, list) else []:
        yield f"event: team_message\ndata: {json.dumps(message, ensure_ascii=False)}\n\n"
