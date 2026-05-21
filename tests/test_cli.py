import json
import os
from pathlib import Path
from datetime import UTC, datetime

from agent_orchestrator import OrchestrationMode
from agent_orchestrator.cli import _print_run_summary
from agent_orchestrator.jobs import FileJobRuntime, JobRequest
from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.routing import PolicyRouter


def test_auto_mode_high_risk_routes_to_success_first() -> None:
    run = Orchestrator(router=PolicyRouter()).run("Urgent auth refactor today", None)

    assert run.routing_decision is not None
    assert run.routing_decision.mode.value == "success_first"


def test_print_run_summary_reports_reroute(capsys) -> None:
    run = Orchestrator().run("Fail the auth migration", OrchestrationMode.SPEED_FIRST)

    _print_run_summary(run)
    out = capsys.readouterr().out

    assert "rerouted:" in out
    assert "attempts=2" in out
    assert "reasons=" in out


def test_print_run_summary_reports_partial_rescue_without_reroute(capsys) -> None:
    run = Orchestrator().run("Fail task", OrchestrationMode.SUCCESS_FIRST)

    _print_run_summary(run)
    out = capsys.readouterr().out

    assert "dependency_rescue:" in out
    assert "accepted=true" in out
    assert "rerouted:" not in out


def test_run_to_dict_preserves_reroute_history() -> None:
    run = Orchestrator().run("Fail the auth migration", OrchestrationMode.SPEED_FIRST)
    payload = run.to_dict()

    assert payload["attempts"]
    assert payload["reroute_history"]
    assert payload["attempts"][0]["failure_decision"] is not None
    assert json.loads(json.dumps(payload))["final_mode"] == "success_first"


def test_run_to_dict_preserves_partial_rescue_history() -> None:
    run = Orchestrator().run("Fail task", OrchestrationMode.SUCCESS_FIRST)
    payload = run.to_dict()

    assert payload["attempts"][0]["dependency_rescue_results"]
    assert payload["attempts"][0]["replayed_work_unit_ids"]


def test_job_status_and_result_commands_round_trip(tmp_path, capsys) -> None:
    runtime = FileJobRuntime(tmp_path)
    job = runtime.start(
        JobRequest(
            task_id="work-cli",
            provider="codex",
            kind="implementation",
            prompt="CLI",
            cwd=str(tmp_path),
        )
    )
    runtime.complete(job.id, summary="cli done", stdout="ok")
    runtime.send(job.id, "ignored")

    from agent_orchestrator import cli

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="status", job_id=job.id, root=str(Path(tmp_path))
        )
        cli.main()
        status_payload = json.loads(capsys.readouterr().out)
        assert status_payload["id"] == job.id
        assert "session_id" in status_payload
        assert "thread_id" in status_payload

        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="result", job_id=job.id, root=str(Path(tmp_path))
        )
        cli.main()
        result_payload = json.loads(capsys.readouterr().out)
        assert result_payload["job_id"] == job.id
        assert result_payload["summary"] == "cli done"
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_async_run_returns_handle(tmp_path, capsys) -> None:
    from agent_orchestrator import cli

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="run",
            requirement="Build dashboard",
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            async_run=True,
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["run_id"]
        assert payload["status"] in {"queued", "running"}
        assert payload["job_ids"] == []
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_lock_status_command_reports_metadata(tmp_path, capsys) -> None:
    from agent_orchestrator import cli

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
                "reason": "cli-test",
                "started_at": datetime.now(UTC).isoformat(),
                "heartbeat_at": datetime.now(UTC).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="lock-status",
            run_id=run.run_id,
            root=str(Path(tmp_path)),
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["run_id"] == run.run_id
        assert payload["owner"] == "orchestrator"
        assert payload["reason"] == "cli-test"
        assert payload["state"] == "active"
    finally:
        cli.argparse.ArgumentParser.parse_args = original
