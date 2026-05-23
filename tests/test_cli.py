# DEPS: agent_orchestrator, datetime, json, os, pathlib, pytest
# RESPONSIBILITY: 待补充
# MODULE: 待确定
# ---

import json
import os
from pathlib import Path
from datetime import UTC, datetime
import pytest

from agent_orchestrator import OrchestrationMode
from agent_orchestrator.command import CommandResult
from agent_orchestrator.cli import _print_run_summary
from agent_orchestrator.jobs import FileJobRuntime, JobRequest
from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.routing import PolicyRouter


def _write_minimal_process_docs(root: Path) -> None:
    (root / "docs" / "process").mkdir(parents=True, exist_ok=True)
    (root / "src" / "agent_orchestrator").mkdir(parents=True, exist_ok=True)
    (root / "src" / "agent_orchestrator" / "__init__.py").write_text('"""package"""\n', encoding="utf-8")
    (root / "README.md").write_text(
        "# temp\n\n- 长周期主执行计划\n- agent-team-operator-runbook.md\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "长周期主执行计划.md").write_text(
        "# 长周期主执行计划\n\n- 文档同步 / compliance / hook blocking\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "agent-orchestrator-implementation-process.md").write_text(
        "# Agent Orchestrator Product Process\n\n- hook-based compliance checks\n",
        encoding="utf-8",
    )
    (root / "docs" / "architecture").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "architecture" / "决策核心-执行拓扑-运行时分层说明.md").write_text(
        "# 决策核心-执行拓扑-运行时分层说明\n\n- 决策核心\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "agent-team-operator-runbook.md").write_text(
        "# Agent Team Operator Runbook\n\n- team next\n- topology_reason\n- fallback_reason\n- fallback_detail\n",
        encoding="utf-8",
    )
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=root / "plans"),
        project_root=root,
    )
    team.refresh_documentation_sync()


class _FakeClaudeRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def spawn(self, command: list[str], *, cwd: str, env: dict[str, str] | None = None):
        self.commands.append(command)
        return None

    def run(self, command: list[str], *, cwd: str, env: dict[str, str] | None = None) -> CommandResult:
        self.commands.append(command)
        if "--version" in command:
            return CommandResult(command=command, exit_code=0, stdout="claude 1.0.0\n", stderr="")
        return CommandResult(
            command=command,
            exit_code=0,
            stdout=json.dumps({"result": "Claude review complete", "is_error": False}),
            stderr="",
        )


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
    assert "upgrade=mode_upgrade" in out


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
    assert payload["reroute_history"][0]["upgrade_kind"] == "mode_upgrade"
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
            agent=None,
            depth=None,
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


def test_print_run_summary_reports_agent_depth(capsys) -> None:
    run = Orchestrator().run("Build dashboard", OrchestrationMode.SUCCESS_FIRST, depth=2)

    _print_run_summary(run)
    out = capsys.readouterr().out

    assert "agent=on" in out
    assert "depth=2" in out


def test_print_run_summary_reports_depth_upgrade(capsys) -> None:
    run = Orchestrator().run("Fail the auth migration", OrchestrationMode.SUCCESS_FIRST, depth=1)

    _print_run_summary(run)
    out = capsys.readouterr().out

    assert "rerouted:" in out
    assert "upgrade=depth_upgrade" in out


def test_print_run_summary_reports_decision_contract(capsys) -> None:
    run = Orchestrator().run("Build dashboard", OrchestrationMode.SUCCESS_FIRST)

    _print_run_summary(run)
    out = capsys.readouterr().out

    assert "decision:" in out
    assert "route=success_first" in out
    assert "review=required" in out
    assert "route_source=explicit_mode" in out
    assert "execution_contract:" in out
    assert "source=approved_plan_style_direct_run" in out
    assert "goal=Build dashboard" in out


def test_print_run_summary_reports_router_source_and_execution_contract(capsys) -> None:
    run = Orchestrator().run("Implement multiple independent modules in parallel", None)

    _print_run_summary(run)
    out = capsys.readouterr().out

    assert "route_source=router" in out
    assert "execution_contract:" in out


def test_poll_run_command_returns_execution_contract_metadata(tmp_path, capsys) -> None:
    from agent_orchestrator import cli

    orchestrator = Orchestrator()
    orchestrator.run_store.root = tmp_path
    run = orchestrator.run("Build dashboard", OrchestrationMode.SUCCESS_FIRST)

    original_build = cli._build_orchestrator
    original_parse = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_orchestrator = lambda runtime, provider: orchestrator
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="poll-run",
            run_id=run.run_id,
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["metadata"]["entrypoint"] == "direct_run"
        assert payload["metadata"]["execution_contract"]["source"] == "approved_plan_style_direct_run"
    finally:
        cli._build_orchestrator = original_build
        cli.argparse.ArgumentParser.parse_args = original_parse


def test_team_status_command_round_trips_session(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Build a persisted plan artifact")

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="status",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["id"] == session.id
        assert payload["status"] == "approved_for_execution"
        assert payload["structured_brief"]["goal"]
        assert payload["structured_brief"]["subtasks"]
        assert payload["status_summary"]["next_actions"] == ["execute"]
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_resume_command_normalizes_session_state(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Build plan with adversarial challenge")
    session.resume.current_phase = "drafting"
    session.resume.pending_role = "build"
    team.store.write_session(session)

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="resume",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["resume"]["current_phase"] == "in_review"
        assert payload["resume"]["pending_role"] == "lead"
        assert "revise" in payload["status_summary"]["next_actions"]
        assert payload["status_summary"]["resume_action"] == "revise"
        assert payload["status_summary"]["resume_reason"] == "required_gaps_open"
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_revise_command_closes_required_gap(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Build plan with adversarial challenge")
    gap_id = session.gaps[0].id

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="revise",
            session_id=session.id,
            summary="closed required gap",
            close_gap=[gap_id],
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["review_rounds"][-1]["round_type"] == "revision"
        assert payload["gaps"][0]["status"] == "closed"
        assert "approve" in payload["status_summary"]["next_actions"]
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_status_command_reports_claude_job_summary(tmp_path, capsys) -> None:
    from agent_orchestrator import cli

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args

    class _FakeTeam:
        def status(self, session_id: str):
            return type(
                "FakeSession",
                (),
                {
                    "to_dict": lambda self: {
                        "id": session_id,
                        "status": "needs_revision",
                        "structured_brief": {"goal": "g", "subtasks": []},
                        "status_summary": {
                            "next_actions": ["revise"],
                            "delegated_jobs": [
                                {
                                    "provider": "claude",
                                    "kind": "review",
                                    "status": "completed",
                                    "summary": "Claude review complete",
                                }
                            ],
                        },
                    }
                },
            )()

    try:
        cli._build_team_orchestrator = lambda runtime, provider, plans_root, runs_root: _FakeTeam()
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="status",
            session_id="plan-1",
            requirement=None,
            mode="success_first",
            runtime="command",
            reroute="on",
            provider="claude",
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["status_summary"]["delegated_jobs"][0]["provider"] == "claude"
        assert payload["status_summary"]["delegated_jobs"][0]["status"] == "completed"
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_summary_command_reports_primary_next_step(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Build plan with adversarial challenge")

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="summary",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert f"session: {session.id}" in out
        assert "status: needs_revision" in out
        assert "next: revise" in out
        assert "topology_reason:" in out
        assert "blocking:" in out
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_summary_command_prioritizes_failed_claude_job(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.jobs import FileJobRuntime
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    runtime = FileJobRuntime(root=tmp_path / "jobs")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=runtime,
    )
    session = team.start("Build a persisted plan artifact")
    review_round = session.review_rounds[1]
    review_job_id = review_round.summary.split("job ")[-1].rstrip(".")
    runtime.fail(review_job_id, summary="review failed", error="claude auth failed")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="summary",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="command",
            reroute="on",
            provider="claude",
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "next: retry_review" in out
        assert f"failed_job: claude {review_job_id}" in out
        assert "inspect the failed Claude job" in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_summary_command_reports_execute_for_approved_session(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Build a persisted plan artifact")

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="summary",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "status: approved_for_execution" in out
        assert "next: execute" in out
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_summary_command_reports_human_decision_for_awaiting_human_session(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Architecture direction change for stage transition")

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="summary",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "status: awaiting_human" in out
        assert "next: human_decision" in out
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_next_command_reports_revise_command(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Build plan with adversarial challenge")

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="next",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "next_command: python -m agent_orchestrator.cli team revise" in out
        assert session.id in out
        assert "--summary" in out
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_next_command_reports_execute_command(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Build a persisted plan artifact")

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="next",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "next_command: python -m agent_orchestrator.cli team execute" in out
        assert "--mode success_first" in out
        assert "alternatives: none" in out
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_next_command_reports_failed_job_inspection_first(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.jobs import FileJobRuntime
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    runtime = FileJobRuntime(root=tmp_path / "jobs")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=runtime,
    )
    session = team.start("Build a persisted plan artifact")
    review_round = session.review_rounds[1]
    review_job_id = review_round.summary.split("job ")[-1].rstrip(".")
    runtime.fail(review_job_id, summary="review failed", error="claude auth failed")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="next",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="command",
            reroute="on",
            provider="claude",
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "next_command: python -m agent_orchestrator.cli team retry-review" in out
        assert session.id in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_summary_command_reports_recovery_actions_for_failed_claude_job(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.jobs import FileJobRuntime
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    runtime = FileJobRuntime(root=tmp_path / "jobs")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=runtime,
    )
    session = team.start("Build a persisted plan artifact")
    review_round = session.review_rounds[1]
    review_job_id = review_round.summary.split("job ")[-1].rstrip(".")
    runtime.fail(review_job_id, summary="review failed", error="claude auth failed")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="summary",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="command",
            reroute="on",
            provider="claude",
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "recovery: inspect_delegated_job -> retry_review -> revise_plan" in out
        assert "recovery_provider: claude (round=review)" in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_summary_command_reports_fallback_recovery_provider_policy(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.command import ClaudeCodeAdapter, CommandJobRuntime, ProviderStatus
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    runtime = CommandJobRuntime(
        root=tmp_path / "jobs",
        runner=_FakeClaudeRunner(),
        adapters={"claude": ClaudeCodeAdapter()},
    )
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=runtime,
    )
    team.provider_health_check = lambda provider: ProviderStatus(
        provider=provider,
        available=False,
        detail=f"{provider} unavailable",
    ) if provider == "claude" else ProviderStatus(provider=provider, available=True, detail="ok")
    session = team.start("Build a persisted plan artifact")
    review_round = session.review_rounds[1]
    review_job_id = review_round.summary.split("job ")[-1].rstrip(".")
    runtime.fail(review_job_id, summary="review failed", error="claude auth failed")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="summary",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="command",
            reroute="on",
            provider="claude",
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "recovery_provider: mock (round=review, fallback_from=claude," in out
        assert "fallback_reason=reviewer_unavailable" in out
        assert "fallback_detail=claude unavailable" in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_retry_review_command_round_trips_session(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.jobs import FileJobRuntime
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    runtime = FileJobRuntime(root=tmp_path / "jobs")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=runtime,
    )
    session = team.start("Build a persisted plan artifact")
    review_round = session.review_rounds[1]
    review_job_id = review_round.summary.split("job ")[-1].rstrip(".")
    runtime.fail(review_job_id, summary="review failed", error="claude auth failed")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="retry-review",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="command",
            reroute="on",
            provider="claude",
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["review_rounds"][-1]["round_type"] == "review_retry"
        assert "inspect_delegated_job" not in payload["status_summary"]["next_actions"]
        assert payload["status_summary"]["recovery_actions"] == []
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_next_command_reports_retry_review_command_for_failed_claude_job(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.jobs import FileJobRuntime
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    runtime = FileJobRuntime(root=tmp_path / "jobs")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=runtime,
    )
    session = team.start("Build a persisted plan artifact")
    review_round = session.review_rounds[1]
    review_job_id = review_round.summary.split("job ")[-1].rstrip(".")
    runtime.fail(review_job_id, summary="review failed", error="claude auth failed")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="next",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="command",
            reroute="on",
            provider="claude",
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "team retry-review" in out
        assert session.id in out
        assert "alternatives: inspect_delegated_job, revise_plan" in out
        assert "context: required_gaps=0 optional_followups=0 delegated_failures=1" in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_resume_command_can_apply_execution_reentry(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    team.orchestrator.run_store.root = tmp_path / "runs"
    session = team.start("Build a persisted plan artifact")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="resume",
            session_id=session.id,
            apply=True,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] in {"accepted", "needs_followup"}
        assert payload["resume"]["linked_execution_run_id"] is not None
        assert payload["status_summary"]["resume_reason"] == "execution_completed"
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_resume_command_can_apply_approval_reentry(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Build plan with adversarial challenge")
    revised = team.revise(session.id, summary="Closed adversarial gap", closed_gap_ids=[session.gaps[0].id])

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="resume",
            session_id=revised.id,
            apply=True,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "approved_for_execution"
        assert payload["gate_verdict"] == "approved"
        assert payload["review_rounds"][-1]["round_type"] == "approval"
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_resume_command_rejects_apply_for_revision_state(tmp_path) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Build plan with adversarial challenge")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="resume",
            session_id=session.id,
            apply=True,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        with pytest.raises(ValueError, match="cannot auto-apply resume action 'revise'"):
            cli.main()
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_resume_command_rejects_apply_for_completed_execution_state(tmp_path) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    team.orchestrator.run_store.root = tmp_path / "runs"
    session = team.start("Build a persisted plan artifact")
    executed = team.execute(session.id, OrchestrationMode.SUCCESS_FIRST)

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="resume",
            session_id=executed.id,
            apply=True,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        with pytest.raises(ValueError, match="cannot auto-apply resume action 'inspect_execution'"):
            cli.main()
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_resume_command_reconciles_completed_linked_run_from_executing_session(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    team.orchestrator.run_store.root = tmp_path / "runs"
    session = team.start("Build a persisted plan artifact")
    executed = team.execute(session.id, OrchestrationMode.SUCCESS_FIRST)
    executed.status = "executing"
    executed.gate_verdict = "approved"
    executed.resume.current_phase = "executing"
    executed.resume.pending_role = "build"
    team.store.write_session(executed)

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="resume",
            session_id=executed.id,
            apply=False,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "accepted"
        assert payload["status_summary"]["resume_action"] == "inspect_execution"
        assert payload["resume"]["current_phase"] == "accepted"
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_next_command_reports_runbook_for_revision_session(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Build plan with adversarial challenge")

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="next",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "next_command: python -m agent_orchestrator.cli team revise" in out
        assert "alternatives: none" in out
        assert "context: required_gaps=1 optional_followups=0 delegated_failures=0" in out
        assert "selected_topology:" in out
        assert "topology_reason:" in out
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_retry_adversarial_review_command_round_trips_session(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.jobs import FileJobRuntime
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    runtime = FileJobRuntime(root=tmp_path / "jobs")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=runtime,
    )
    session = team.start("Build a persisted plan artifact")
    adversarial_round = session.review_rounds[2]
    job_id = adversarial_round.summary.split("job ")[-1].rstrip(".")
    runtime.fail(job_id, summary="adversarial failed", error="claude auth failed")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="retry-adversarial-review",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="command",
            reroute="on",
            provider="claude",
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["review_rounds"][-1]["round_type"] == "adversarial_review_retry"
        assert payload["status_summary"]["recovery_actions"] == []
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_next_command_reports_retry_adversarial_review_command_for_failed_claude_job(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.jobs import FileJobRuntime
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    runtime = FileJobRuntime(root=tmp_path / "jobs")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=runtime,
    )
    session = team.start("Build a persisted plan artifact")
    adversarial_round = session.review_rounds[2]
    job_id = adversarial_round.summary.split("job ")[-1].rstrip(".")
    runtime.fail(job_id, summary="adversarial failed", error="claude auth failed")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="next",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="command",
            reroute="on",
            provider="claude",
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "team retry-adversarial-review" in out
        assert session.id in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_runbook_command_reports_revision_workflow(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Build plan with adversarial challenge")

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="runbook",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert f"session: {session.id}" in out
        assert "operator_runbook:" in out
        assert "selected_topology:" in out
        assert "topology_reason:" in out
        assert "decision_rationale:" in out
        assert "1. Close every required gap with `python -m agent_orchestrator.cli team revise" in out
        assert "2. Re-run `team summary` or `team next` to confirm approval is now allowed." in out
        assert "3. Use `team approve` only after required gaps are closed." in out
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_next_command_reports_execution_inspection_after_completion(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    team.orchestrator.run_store.root = tmp_path / "runs"
    session = team.start("Build a persisted plan artifact")
    executed = team.execute(session.id, OrchestrationMode.SUCCESS_FIRST)

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="next",
            session_id=executed.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "action: inspect_execution" in out
        assert "next_command: python -m agent_orchestrator.cli team inspect-execution" in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_inspect_execution_command_reports_linked_run_payload(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    team.orchestrator.run_store.root = tmp_path / "runs"
    session = team.start("Build a persisted plan artifact")
    executed = team.execute(session.id, OrchestrationMode.SUCCESS_FIRST)

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="inspect-execution",
            session_id=executed.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "execution_outcome: accepted" in out
        assert "goal:" in out
        assert "selected_topology:" in out
        payload = json.loads(out[out.index('{\n  "run_id"'):])
        assert payload["run_id"] == executed.resume.linked_execution_run_id
        assert payload["metadata"]["approved_plan"]["session_id"] == executed.id
        assert payload["metadata"]["provenance"]["plan_session_id"] == executed.id
        assert payload["session_summary"]["outcome"] == "accepted"
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_inspect_execution_command_rejects_session_without_linked_run(tmp_path) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    session = team.start("Build a persisted plan artifact")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="inspect-execution",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        with pytest.raises(ValueError, match="linked execution run"):
            cli.main()
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_runbook_command_reports_execution_followup_after_completion(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    team.orchestrator.run_store.root = tmp_path / "runs"
    session = team.approve(team.start("Build plan with followup checklist").id)
    executed = team.execute(session.id, OrchestrationMode.SUCCESS_FIRST)

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="runbook",
            session_id=executed.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "operator_runbook:" in out
        assert "Inspect the linked execution run with `python -m agent_orchestrator.cli team inspect-execution" in out
        assert "follow-up" in out or "followup" in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_runbook_command_reports_execution_blocked_recovery(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    team.orchestrator.run_store.root = tmp_path / "runs"
    session = team.start("Build a persisted plan artifact")
    executed = team.execute(session.id, OrchestrationMode.SUCCESS_FIRST)

    run_path = tmp_path / "runs" / f"{executed.resume.linked_execution_run_id}.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    payload["status"] = "blocked"
    payload["accepted"] = False
    run_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    executed.status = "executing"
    executed.gate_verdict = "approved"
    executed.resume.current_phase = "executing"
    executed.resume.pending_role = "build"
    team.store.write_session(executed)

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="runbook",
            session_id=executed.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "operator_runbook:" in out
        assert "Inspect the linked execution run" in out
        assert "blocked state" in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_runbook_command_reports_execution_provenance_mismatch_recovery(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    team.orchestrator.run_store.root = tmp_path / "runs"
    session = team.start("Build a persisted plan artifact")
    executed = team.execute(session.id, OrchestrationMode.SUCCESS_FIRST)

    run_path = tmp_path / "runs" / f"{executed.resume.linked_execution_run_id}.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    payload["metadata"]["plan_session_id"] = "plan-wrong"
    payload["status"] = "blocked"
    payload["accepted"] = False
    run_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    executed.status = "executing"
    executed.gate_verdict = "approved"
    executed.resume.current_phase = "executing"
    executed.resume.pending_role = "build"
    team.store.write_session(executed)

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="runbook",
            session_id=executed.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "Inspect the compliance blocker" in out
        assert "run/session mismatch" in out or "mismatch" in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_runbook_command_reports_failed_delegation_recovery(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.jobs import FileJobRuntime
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    runtime = FileJobRuntime(root=tmp_path / "jobs")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=runtime,
    )
    session = team.start("Build a persisted plan artifact")
    review_round = session.review_rounds[1]
    review_job_id = review_round.summary.split("job ")[-1].rstrip(".")
    runtime.fail(review_job_id, summary="review failed", error="claude auth failed")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="runbook",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="command",
            reroute="on",
            provider="claude",
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "operator_runbook:" in out
        assert "1. Inspect the failed delegated Claude review job." in out
        assert "2. Retry the delegated review with `python -m agent_orchestrator.cli team retry-review" in out
        assert "3. Switch to `team revise` if the failure uncovered a real planning gap." in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_summary_command_reports_compliance_blocking(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    (tmp_path / "README.md").write_text("# temp\n", encoding="utf-8")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )
    session = team.start("Build a persisted plan artifact")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="summary",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "next: inspect_compliance" in out
        assert "missing required docs" in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_runbook_command_reports_compliance_recovery(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    (tmp_path / "README.md").write_text("# temp\n", encoding="utf-8")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )
    session = team.start("Build a persisted plan artifact")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="runbook",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "operator_runbook:" in out
        assert "1. Use `team status` to inspect the current session state." not in out
        assert "required docs" in out or "Inspect the blocking review findings" in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_next_command_reports_compliance_check_for_blocking_session(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    (tmp_path / "README.md").write_text("# temp\n", encoding="utf-8")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )
    session = team.start("Build a persisted plan artifact")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="next",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "action: inspect_compliance" in out
        assert "next_command: python -m agent_orchestrator.cli team check-compliance" in out
        assert session.id in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_inspect_blockers_command_prints_execution_blocker_summary(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    _write_minimal_process_docs(tmp_path)
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )
    team.orchestrator.run_store.root = tmp_path / "runs"
    session = team.start("Build a persisted plan artifact")
    executed = team.execute(session.id, OrchestrationMode.SUCCESS_FIRST)

    run_path = tmp_path / "runs" / f"{executed.resume.linked_execution_run_id}.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    payload["status"] = "blocked"
    payload["accepted"] = False
    run_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    executed.status = "executing"
    executed.gate_verdict = "approved"
    executed.resume.current_phase = "executing"
    executed.resume.pending_role = "build"
    team.store.write_session(executed)

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="inspect-blockers",
            session_id=executed.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert f"session: {executed.id}" in out
        assert "block_source: execution_run" in out
        assert "block_detail: run_blocked" in out
        assert "resume_action: inspect_blockers" in out
        assert f"team inspect-blockers {executed.id}" in out
        json_payload = json.loads(out[out.index("{"):])
        assert json_payload["blocker_summary"]["block_source"] == "execution_run"
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_inspect_blockers_command_prints_delegated_job_summary(tmp_path, capsys) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.jobs import FileJobRuntime
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    _write_minimal_process_docs(tmp_path)
    runtime = FileJobRuntime(root=tmp_path / "jobs")
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
        runtime=runtime,
    )
    session = team.start("Build a persisted plan artifact")
    review_round = session.review_rounds[1]
    review_job_id = review_round.summary.split("job ")[-1].rstrip(".")
    runtime.fail(review_job_id, summary="review failed", error="claude auth failed")

    original_build_team = cli._build_team_orchestrator
    original_parse_args = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: team
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="inspect-blockers",
            session_id=session.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        out = capsys.readouterr().out
        assert "block_source: delegated_job" in out
        assert "resume_action: retry_review" in out
        assert f"team inspect-blockers {session.id}" in out
    finally:
        cli._build_team_orchestrator = original_build_team
        cli.argparse.ArgumentParser.parse_args = original_parse_args


def test_team_check_compliance_command_reports_blocking_failure(tmp_path, capsys) -> None:
    from agent_orchestrator import cli

    (tmp_path / "README.md").write_text("# temp\n", encoding="utf-8")

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="check-compliance",
            session_id=None,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        with pytest.raises(SystemExit, match="1"):
            cli.main()
        out = capsys.readouterr().out
        assert "\"status\": \"blocked\"" in out
        assert "missing required docs" in out
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_check_compliance_command_passes_changed_files_to_team(tmp_path, capsys) -> None:
    from agent_orchestrator import cli

    captured: dict[str, object] = {}

    class _FakeTeam:
        def check_compliance(self, changed_files=None):
            captured["changed_files"] = changed_files
            return {"status": "passed", "blocking": False, "checks": [], "blocking_reasons": []}

    original_build = cli._build_team_orchestrator
    original_parse = cli.argparse.ArgumentParser.parse_args
    try:
        cli._build_team_orchestrator = lambda runtime_name, provider, plans_root, runs_root: _FakeTeam()
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="check-compliance",
            session_id=None,
            changed_file=["src/agent_orchestrator/planning.py", "docs/process/root-map.md"],
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "passed"
        assert captured["changed_files"] == [
            "src/agent_orchestrator/planning.py",
            "docs/process/root-map.md",
        ]
    finally:
        cli._build_team_orchestrator = original_build
        cli.argparse.ArgumentParser.parse_args = original_parse


def test_install_hooks_command_installs_pre_commit_script(tmp_path, capsys) -> None:
    from agent_orchestrator import cli

    repo_root = tmp_path / "repo"
    git_hooks = repo_root / ".git" / "hooks"
    scripts_dir = repo_root / "scripts" / "git-hooks"
    git_hooks.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    source_hook = scripts_dir / "pre-commit"
    source_hook.write_text("#!/bin/sh\necho hook\n", encoding="utf-8")

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="install-hooks",
            root=str(repo_root),
        )
        cli.main()
        out = capsys.readouterr().out
        installed = git_hooks / "pre-commit"
        assert installed.exists()
        assert installed.read_text(encoding="utf-8") == source_hook.read_text(encoding="utf-8")
        assert "Installed git hook" in out
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_start_command_exposes_structured_brief(tmp_path, capsys) -> None:
    from agent_orchestrator import cli

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="start",
            session_id=None,
            requirement="Build a persisted plan artifact",
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        cli.main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["structured_brief"]["goal"]
        assert payload["structured_brief"]["acceptance_criteria"]
    finally:
        cli.argparse.ArgumentParser.parse_args = original


def test_team_execute_command_rejects_unapproved_session(tmp_path) -> None:
    from agent_orchestrator import cli
    from agent_orchestrator.planning import PlanStore, TeamOrchestrator

    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
    )
    blocked = team.start("Auth migration with roadmap drift")

    original = cli.argparse.ArgumentParser.parse_args
    try:
        cli.argparse.ArgumentParser.parse_args = lambda self: cli.argparse.Namespace(
            command="team",
            team_command="execute",
            session_id=blocked.id,
            requirement=None,
            mode="success_first",
            runtime="mock",
            reroute="on",
            provider=None,
            agent=None,
            depth=None,
            plans_root=str(tmp_path / "plans"),
            runs_root=str(tmp_path / "runs"),
        )
        with pytest.raises(ValueError, match="approved plan"):
            cli.main()
    finally:
        cli.argparse.ArgumentParser.parse_args = original
