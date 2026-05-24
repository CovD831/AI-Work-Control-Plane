from agent_orchestrator.jobs import JobRequest
from agent_orchestrator.tmux_runtime import TmuxJobRuntime


class _FakeTmuxRunner:
    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.sessions = []
        self.messages = []
        self.killed = []

    def available(self) -> bool:
        return self._available

    def new_session(self, session_name: str, command: str, *, cwd: str) -> None:
        self.sessions.append((session_name, command, cwd))

    def send_keys(self, session_name: str, message: str) -> None:
        self.messages.append((session_name, message))

    def capture_pane(self, session_name: str) -> str:
        return f"pane output from {session_name}"

    def kill_session(self, session_name: str) -> None:
        self.killed.append(session_name)


def _request(tmp_path) -> JobRequest:
    return JobRequest(
        task_id="task-1",
        provider="codex",
        kind="implementation",
        prompt="Build UI",
        cwd=str(tmp_path),
    )


def test_tmux_runtime_starts_attachable_job(tmp_path) -> None:
    runner = _FakeTmuxRunner()
    runtime = TmuxJobRuntime(root=tmp_path / "jobs", runner=runner)

    job = runtime.start(_request(tmp_path))

    assert job.status == "running"
    assert job.phase == "working"
    assert job.metadata["attach_available"] is True
    assert job.metadata["terminal_ref"] == f"tmux:agent-{job.id}"
    assert runner.sessions[0][0] == f"agent-{job.id}"


def test_tmux_runtime_reports_unavailable_tmux_as_failed_job(tmp_path) -> None:
    runtime = TmuxJobRuntime(root=tmp_path / "jobs", runner=_FakeTmuxRunner(available=False))

    job = runtime.start(_request(tmp_path))

    assert job.status == "failed"
    assert job.metadata["attach_available"] is False
    assert job.error == "tmux not found"


def test_tmux_runtime_send_status_and_cancel(tmp_path) -> None:
    runner = _FakeTmuxRunner()
    runtime = TmuxJobRuntime(root=tmp_path / "jobs", runner=runner)
    job = runtime.start(_request(tmp_path))

    sent = runtime.send(job.id, "continue")
    status = runtime.status(job.id)
    cancelled = runtime.cancel(job.id)

    assert sent.messages == ["continue"]
    assert "pane output" in status.stdout
    assert cancelled.status == "cancelled"
    assert runner.messages == [(f"agent-{job.id}", "continue")]
    assert runner.killed == [f"agent-{job.id}"]
