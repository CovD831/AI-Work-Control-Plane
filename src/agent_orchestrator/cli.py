"""Command line interface for the orchestration MVP."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, argparse, json, pathlib, shutil
# RESPONSIBILITY: Parse CLI commands and delegate presentation-safe orchestration actions.
# MODULE: interface
# ---


import argparse
import json
import shutil
from pathlib import Path

from agent_orchestrator.adapters import RuntimeProviderAdapter, RuntimeProviderReviewRescueAdapter
from agent_orchestrator.cli_presenters import (
    print_team_next as _print_team_next_presenter,
    print_team_runbook as _print_team_runbook_presenter,
    print_team_summary as _print_team_summary_presenter,
    pick_primary_action as _pick_primary_action,
    print_blocker_session_summary as _print_blocker_session_summary_presenter,
    print_execution_session_summary as _print_execution_session_summary_presenter,
    status_summary as _status_summary,
    summary_bool as _summary_bool,
    summary_list as _summary_list,
    summary_text as _summary_text,
    team_next_alternatives as _team_next_alternatives,
    team_display_context as _team_display_context,
)
from agent_orchestrator.command import CommandJobRuntime, ProviderHealthCheck
from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.policies import OrchestrationMode
from agent_orchestrator.planning import PlanStore, TeamOrchestrator, build_operator_runbook
from agent_orchestrator.run_store import RunStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Agent Orchestrator MVP.")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run an orchestration request.")
    run_parser.add_argument("requirement", help="Fuzzy requirement to orchestrate.")
    run_parser.add_argument(
        "--mode",
        choices=["auto", *[mode.value for mode in OrchestrationMode]],
        default=OrchestrationMode.SUCCESS_FIRST.value,
        help="Policy mode to use.",
    )
    run_parser.add_argument(
        "--runtime",
        choices=["mock", "command"],
        default="mock",
        help="Runtime to use. Defaults to mock so local Claude/Codex are not required.",
    )
    run_parser.add_argument(
        "--reroute",
        choices=["on", "off"],
        default="on",
        help="Enable automatic failure rerouting.",
    )
    run_parser.add_argument(
        "--provider",
        choices=["codex", "claude"],
        help="Provider to use with --runtime command.",
    )
    run_parser.add_argument("--agent", choices=["on", "off"], default=None, help="Enable or disable agent topology.")
    run_parser.add_argument("--depth", type=int, choices=[0, 1, 2, 3], default=None, help="Override agent topology depth.")
    run_parser.add_argument(
        "--async",
        dest="async_run",
        action="store_true",
        help="Start the orchestration and return a run handle immediately.",
    )

    start_parser = subparsers.add_parser("start", help="Start an orchestration run asynchronously.")
    start_parser.add_argument("requirement", help="Fuzzy requirement to orchestrate.")
    start_parser.add_argument(
        "--mode",
        choices=["auto", *[mode.value for mode in OrchestrationMode]],
        default=OrchestrationMode.SUCCESS_FIRST.value,
        help="Policy mode to use.",
    )
    start_parser.add_argument("--reroute", choices=["on", "off"], default="on", help="Enable automatic failure rerouting.")
    start_parser.add_argument("--runtime", choices=["mock", "command"], default="mock")
    start_parser.add_argument("--provider", choices=["codex", "claude"])
    start_parser.add_argument("--agent", choices=["on", "off"], default=None)
    start_parser.add_argument("--depth", type=int, choices=[0, 1, 2, 3], default=None)

    poll_run_parser = subparsers.add_parser("poll-run", help="Inspect a stored orchestration run.")
    poll_run_parser.add_argument("run_id")

    poll_attempt_parser = subparsers.add_parser("poll-attempt", help="Inspect a stored orchestration attempt.")
    poll_attempt_parser.add_argument("run_id")
    poll_attempt_parser.add_argument("attempt_id")

    resume_parser = subparsers.add_parser("resume", help="Resume a stored orchestration run.")
    resume_parser.add_argument("run_id")

    reroute_parser = subparsers.add_parser("reroute", help="Create a rerouted orchestration attempt.")
    reroute_parser.add_argument("run_id")
    reroute_parser.add_argument("--target-mode", choices=[mode.value for mode in OrchestrationMode])

    lock_parser = subparsers.add_parser("lock-status", help="Inspect a run lock.")
    lock_parser.add_argument("run_id", help="Run id to inspect.")
    lock_parser.add_argument("--root", default=".agent_orchestrator/runs", help="Run store root.")

    status_parser = subparsers.add_parser("status", help="Show job status.")
    status_parser.add_argument("job_id", help="Job id to inspect.")
    status_parser.add_argument("--root", default=".agent_orchestrator/jobs", help="Job store root.")

    result_parser = subparsers.add_parser("result", help="Show job result.")
    result_parser.add_argument("job_id", help="Job id to inspect.")
    result_parser.add_argument("--root", default=".agent_orchestrator/jobs", help="Job store root.")

    send_parser = subparsers.add_parser("send", help="Send a follow-up message to a job.")
    send_parser.add_argument("job_id", help="Job id to update.")
    send_parser.add_argument("message", help="Follow-up message.")
    send_parser.add_argument("--root", default=".agent_orchestrator/jobs", help="Job store root.")

    cancel_parser = subparsers.add_parser("cancel", help="Cancel a job.")
    cancel_parser.add_argument("job_id", help="Job id to cancel.")
    cancel_parser.add_argument("--root", default=".agent_orchestrator/jobs", help="Job store root.")

    health_parser = subparsers.add_parser("health", help="Check local provider availability.")

    install_hooks_parser = subparsers.add_parser("install-hooks", help="Install repository-managed git hooks.")
    install_hooks_parser.add_argument("--root", default=".", help="Repository root that contains .git/ and scripts/git-hooks/.")

    team_parser = subparsers.add_parser("team", help="Run planning-governance team workflows.")
    team_subparsers = team_parser.add_subparsers(dest="team_command")

    team_start = team_subparsers.add_parser("start", help="Create and review a plan session.")
    team_start.add_argument("requirement", help="Requirement to plan.")
    team_start.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_start.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_start.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_start.add_argument("--provider", choices=["codex", "claude"])

    team_status = team_subparsers.add_parser("status", help="Inspect a plan session.")
    team_status.add_argument("session_id")
    team_status.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_status.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_status.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_status.add_argument("--provider", choices=["codex", "claude"])

    team_summary = team_subparsers.add_parser("summary", help="Show a human-readable plan session summary.")
    team_summary.add_argument("session_id")
    team_summary.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_summary.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_summary.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_summary.add_argument("--provider", choices=["codex", "claude"])

    team_next = team_subparsers.add_parser("next", help="Show the next recommended team command.")
    team_next.add_argument("session_id")
    team_next.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_next.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_next.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_next.add_argument("--provider", choices=["codex", "claude"])

    team_runbook = team_subparsers.add_parser("runbook", help="Show operator guidance for the current plan session.")
    team_runbook.add_argument("session_id")
    team_runbook.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_runbook.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_runbook.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_runbook.add_argument("--provider", choices=["codex", "claude"])

    team_check_compliance = team_subparsers.add_parser(
        "check-compliance",
        help="Run compliance checks for the current project or a specific plan session.",
    )
    team_check_compliance.add_argument("session_id", nargs="?")
    team_check_compliance.add_argument("--changed-file", action="append", default=[])
    team_check_compliance.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_check_compliance.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_check_compliance.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_check_compliance.add_argument("--provider", choices=["codex", "claude"])

    team_retry_review = team_subparsers.add_parser("retry-review", help="Retry a failed delegated review round.")
    team_retry_review.add_argument("session_id")
    team_retry_review.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_retry_review.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_retry_review.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_retry_review.add_argument("--provider", choices=["codex", "claude"])

    team_retry_adversarial_review = team_subparsers.add_parser(
        "retry-adversarial-review",
        help="Retry a failed delegated adversarial review round.",
    )
    team_retry_adversarial_review.add_argument("session_id")
    team_retry_adversarial_review.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_retry_adversarial_review.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_retry_adversarial_review.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_retry_adversarial_review.add_argument("--provider", choices=["codex", "claude"])

    team_resume = team_subparsers.add_parser("resume", help="Resume a plan session.")
    team_resume.add_argument("session_id")
    team_resume.add_argument("--apply", action="store_true", help="Apply the recommended resume action when it is safe to do so.")
    team_resume.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_resume.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_resume.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_resume.add_argument("--provider", choices=["codex", "claude"])

    team_approve = team_subparsers.add_parser("approve", help="Approve a reviewed plan session.")
    team_approve.add_argument("session_id")
    team_approve.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_approve.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_approve.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_approve.add_argument("--provider", choices=["codex", "claude"])

    team_revise = team_subparsers.add_parser("revise", help="Revise a plan session by closing gaps.")
    team_revise.add_argument("session_id")
    team_revise.add_argument("--summary", required=True)
    team_revise.add_argument("--close-gap", action="append", default=[])
    team_revise.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_revise.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_revise.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_revise.add_argument("--provider", choices=["codex", "claude"])

    team_execute = team_subparsers.add_parser("execute", help="Execute an approved plan session.")
    team_execute.add_argument("session_id")
    team_execute.add_argument(
        "--mode",
        choices=["auto", *[mode.value for mode in OrchestrationMode]],
        default=OrchestrationMode.SUCCESS_FIRST.value,
    )
    team_execute.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_execute.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_execute.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_execute.add_argument("--provider", choices=["codex", "claude"])

    team_inspect_execution = team_subparsers.add_parser(
        "inspect-execution",
        help="Show the linked execution run for a completed or in-progress plan session.",
    )
    team_inspect_execution.add_argument("session_id")
    team_inspect_execution.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_inspect_execution.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_inspect_execution.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_inspect_execution.add_argument("--provider", choices=["codex", "claude"])

    team_inspect_blockers = team_subparsers.add_parser(
        "inspect-blockers",
        help="Show a structured blocker summary for a blocked or recovery-oriented plan session.",
    )
    team_inspect_blockers.add_argument("session_id")
    team_inspect_blockers.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_inspect_blockers.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_inspect_blockers.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_inspect_blockers.add_argument("--provider", choices=["codex", "claude"])
    args = parser.parse_args()

    if args.command == "health":
        health = ProviderHealthCheck()
        print(
            json.dumps(
                {
                    "providers": [
                        health.check("codex").to_dict(),
                        health.check("claude").to_dict(),
                    ]
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "install-hooks":
        _install_git_hooks(Path(args.root))
        return

    if args.command == "team":
        team = _build_team_orchestrator(args.runtime, getattr(args, "provider", None), args.plans_root, args.runs_root)
        if args.team_command == "start":
            print(json.dumps(team.start(args.requirement).to_dict(), ensure_ascii=False, indent=2))
            return
        if args.team_command == "status":
            print(json.dumps(team.status(args.session_id).to_dict(), ensure_ascii=False, indent=2))
            return
        if args.team_command == "summary":
            _print_team_summary(team.status(args.session_id))
            return
        if args.team_command == "next":
            _print_team_next(team.status(args.session_id), args)
            return
        if args.team_command == "runbook":
            _print_team_runbook(team.status(args.session_id))
            return
        if args.team_command == "check-compliance":
            changed_files = list(getattr(args, "changed_file", []) or [])
            payload = (
                team.check_session_compliance(args.session_id, changed_files=changed_files)
                if args.session_id
                else team.check_compliance(changed_files=changed_files)
            )
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            if payload.get("blocking"):
                raise SystemExit(1)
            return
        if args.team_command == "retry-review":
            print(json.dumps(team.retry_review(args.session_id).to_dict(), ensure_ascii=False, indent=2))
            return
        if args.team_command == "retry-adversarial-review":
            print(json.dumps(team.retry_adversarial_review(args.session_id).to_dict(), ensure_ascii=False, indent=2))
            return
        if args.team_command == "resume":
            print(json.dumps(team.resume(args.session_id, apply=getattr(args, "apply", False)).to_dict(), ensure_ascii=False, indent=2))
            return
        if args.team_command == "approve":
            print(json.dumps(team.approve(args.session_id).to_dict(), ensure_ascii=False, indent=2))
            return
        if args.team_command == "revise":
            print(
                json.dumps(
                    team.revise(args.session_id, summary=args.summary, closed_gap_ids=list(args.close_gap)).to_dict(),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        if args.team_command == "execute":
            mode = None if args.mode == "auto" else OrchestrationMode(args.mode)
            print(json.dumps(team.execute(args.session_id, mode).to_dict(), ensure_ascii=False, indent=2))
            return
        if args.team_command == "inspect-execution":
            payload = team.inspect_execution(args.session_id)
            _print_execution_session_summary(payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        if args.team_command == "inspect-blockers":
            payload = team.inspect_blockers(args.session_id)
            _print_blocker_session_summary(payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        parser.error("a team subcommand is required")

    if args.command == "status":
        runtime = CommandJobRuntime(root=Path(args.root))
        print(json.dumps(runtime.status(args.job_id).to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "result":
        runtime = CommandJobRuntime(root=Path(args.root))
        print(json.dumps(runtime.result(args.job_id).to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "send":
        runtime = CommandJobRuntime(root=Path(args.root))
        print(json.dumps(runtime.send(args.job_id, args.message).to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "cancel":
        runtime = CommandJobRuntime(root=Path(args.root))
        print(json.dumps(runtime.cancel(args.job_id).to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "start":
        orchestrator = _build_orchestrator(args.runtime, args.provider)
        mode = None if args.mode == "auto" else OrchestrationMode(args.mode)
        handle = orchestrator.start_run(
            args.requirement,
            mode,
            reroute=args.reroute == "on",
            agent_enabled=_parse_agent_flag(args.agent),
            depth=args.depth,
        )
        print(json.dumps(handle.to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "poll-run":
        orchestrator = _build_orchestrator("mock", None)
        print(json.dumps(orchestrator.poll_run(args.run_id).to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "poll-attempt":
        orchestrator = _build_orchestrator("mock", None)
        print(json.dumps(orchestrator.poll_attempt(args.run_id, args.attempt_id).to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "resume":
        orchestrator = _build_orchestrator("mock", None)
        print(json.dumps(orchestrator.resume_run(args.run_id).to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "reroute":
        orchestrator = _build_orchestrator("mock", None)
        target_mode = OrchestrationMode(args.target_mode) if args.target_mode else None
        print(json.dumps(orchestrator.reroute_run(args.run_id, target_mode).to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "lock-status":
        orchestrator = Orchestrator(run_store=RunStore(root=Path(args.root)))
        print(json.dumps(orchestrator.poll_run(args.run_id).lock_status, ensure_ascii=False, indent=2))
        return

    if args.command is None:
        parser.error("a subcommand is required")

    orchestrator = _build_orchestrator(args.runtime, args.provider)
    mode = None if args.mode == "auto" else OrchestrationMode(args.mode)
    if getattr(args, "async_run", False):
        handle = orchestrator.start_run(
            args.requirement,
            mode,
            reroute=args.reroute == "on",
            agent_enabled=_parse_agent_flag(args.agent),
            depth=args.depth,
        )
        print(json.dumps(handle.to_dict(), ensure_ascii=False, indent=2))
    else:
        run = orchestrator.run(
            args.requirement,
            mode,
            reroute=args.reroute == "on",
            agent_enabled=_parse_agent_flag(args.agent),
            depth=args.depth,
        )
        _print_run_summary(run)
        print(json.dumps(run.to_dict(), ensure_ascii=False, indent=2))


def _build_orchestrator(runtime: str, provider: str | None) -> Orchestrator:
    if runtime == "mock":
        return Orchestrator()

    command_runtime = CommandJobRuntime()
    worker_default_provider = provider or "codex"
    reviewer_default_provider = provider or "claude"
    return Orchestrator(
        worker=RuntimeProviderAdapter(
            runtime=command_runtime,
            default_provider=worker_default_provider,
            kind="implementation",
        ),
        reviewer=RuntimeProviderReviewRescueAdapter(
            runtime=command_runtime,
            default_provider=reviewer_default_provider,
        )
    )


def _build_team_orchestrator(runtime: str, provider: str | None, plans_root: str, runs_root: str) -> TeamOrchestrator:
    orchestrator = _build_orchestrator(runtime, provider)
    plans_path = Path(plans_root)
    runs_path = Path(runs_root)
    orchestrator.run_store = RunStore(root=runs_path)
    project_root = Path.cwd()
    for candidate in (plans_path.parent, runs_path.parent):
        if candidate == Path("."):
            continue
        if (candidate / "README.md").exists() or (candidate / "docs" / "process").exists():
            project_root = candidate
            break
    return TeamOrchestrator(
        orchestrator=orchestrator,
        store=PlanStore(root=plans_path),
        project_root=project_root,
    )


def _install_git_hooks(repo_root: Path) -> None:
    hooks_source_dir = repo_root / "scripts" / "git-hooks"
    git_hooks_dir = repo_root / ".git" / "hooks"
    if not hooks_source_dir.exists():
        raise FileNotFoundError(f"Hook source directory not found: {hooks_source_dir}")
    if not git_hooks_dir.exists():
        raise FileNotFoundError(f"Git hooks directory not found: {git_hooks_dir}")

    installed: list[Path] = []
    for source in sorted(path for path in hooks_source_dir.iterdir() if path.is_file()):
        target = git_hooks_dir / source.name
        shutil.copyfile(source, target)
        target.chmod(0o755)
        installed.append(target)

    marker_dir = repo_root / ".agent_orchestrator"
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker_path = marker_dir / "hooks.json"
    marker_path.write_text(
        json.dumps(
            {
                "managed_hooks_enabled": True,
                "installed_hooks": [path.name for path in installed],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    for path in installed:
        print(f"Installed git hook: {path}")
    print(f"Recorded managed hook marker: {marker_path}")


def _print_run_summary(run: object) -> None:
    initial_mode = getattr(run, "initial_mode", None)
    final_mode = getattr(run, "final_mode", None)
    attempts = getattr(run, "attempts", [])
    reroute_history = getattr(run, "reroute_history", [])
    policy = getattr(run, "policy", None)
    dependency_rescue_count = sum(len(getattr(attempt, "replayed_work_unit_ids", [])) for attempt in attempts)
    dependency_rescue_success = any(
        getattr(attempt, "replayed_work_unit_ids", []) and getattr(attempt, "accepted", False)
        for attempt in attempts
    )

    if dependency_rescue_count:
        print(
            "dependency_rescue: "
            f"work_units={dependency_rescue_count} "
            f"accepted={str(dependency_rescue_success).lower()}"
        )

    if initial_mode and final_mode and initial_mode != final_mode:
        last = reroute_history[-1] if reroute_history else {}
        reasons = ", ".join(last.get("reasons", [])) if isinstance(last, dict) else ""
        upgrade_kind = last.get("upgrade_kind", "") if isinstance(last, dict) else ""
        print(
            "rerouted: "
            f"{initial_mode.value} -> {final_mode.value} "
            f"(attempts={len(attempts)}"
            + (f", upgrade={upgrade_kind}" if upgrade_kind else "")
            + (f", reasons={reasons}" if reasons else "")
            + ")"
        )
    elif reroute_history:
        last = reroute_history[-1]
        reasons = ", ".join(last.get("reasons", [])) if isinstance(last, dict) else ""
        upgrade_kind = last.get("upgrade_kind", "") if isinstance(last, dict) else ""
        print(
            "rerouted: "
            f"{initial_mode.value if initial_mode else 'unknown'} -> {final_mode.value if final_mode else 'unknown'} "
            f"(attempts={len(attempts)}"
            + (f", upgrade={upgrade_kind}" if upgrade_kind else "")
            + (f", reasons={reasons}" if reasons else "")
            + ")"
        )
    else:
        agent_status = getattr(policy, "agent_enabled", None)
        topology_depth = getattr(policy, "topology_depth", None)
        detail = ""
        if agent_status is not None and topology_depth is not None:
            detail = f" agent={'on' if agent_status else 'off'} depth={topology_depth}"
        print(f"completed: mode={final_mode.value if final_mode else 'unknown'} attempts={len(attempts)}{detail}")

    decision_artifact = getattr(run, "decision_artifact", None)
    if decision_artifact:
        route = decision_artifact.route.get("selected_mode", "unknown")
        route_source = decision_artifact.route.get("source", "unknown")
        review = decision_artifact.review_level.get("policy", "unknown")
        stop_reason = decision_artifact.stop_reason
        print(f"decision: route={route} route_source={route_source} review={review} stop={stop_reason}")

    metadata = getattr(run, "metadata", {}) or {}
    execution_contract = metadata.get("execution_contract", {}) if isinstance(metadata, dict) else {}
    if isinstance(execution_contract, dict) and execution_contract:
        print(
            "execution_contract: "
            f"source={execution_contract.get('source', 'unknown')} "
            f"goal={execution_contract.get('goal', 'unknown')}"
        )


def _print_team_summary(session: object) -> None:
    _print_team_summary_presenter(session, pick_primary_action=_pick_primary_action)


def _print_team_next(session: object, args: argparse.Namespace) -> None:
    _print_team_next_presenter(
        session,
        pick_primary_action=_pick_primary_action,
        build_team_next_command=_build_team_next_command,
        team_next_alternatives=_team_next_alternatives,
        args=args,
    )


def _print_team_runbook(session: object) -> None:
    _print_team_runbook_presenter(
        session,
        pick_primary_action=_pick_primary_action,
        build_operator_runbook=build_operator_runbook,
    )


def _print_execution_session_summary(payload: dict[str, object]) -> None:
    _print_execution_session_summary_presenter(payload)


def _print_blocker_session_summary(payload: dict[str, object]) -> None:
    _print_blocker_session_summary_presenter(payload)


def _build_team_next_command(
    payload: dict[str, object],
    primary_action: str,
    failed_jobs: list[dict[str, object]],
    args: argparse.Namespace,
) -> str:
    session_id = str(payload.get("id"))
    plans_root = str(args.plans_root)
    runs_root = str(args.runs_root)
    status_summary = _status_summary(payload)

    if primary_action == "inspect_delegated_job" and failed_jobs:
        failed_job = failed_jobs[0]
        if str(failed_job.get("provider")) == "claude":
            if str(failed_job.get("round_type")) in {"adversarial_review", "adversarial_review_retry"}:
                return (
                    "python -m agent_orchestrator.cli team retry-adversarial-review "
                    f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
                )
            return (
                "python -m agent_orchestrator.cli team retry-review "
                f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
            )
        job_id = str(failed_job.get("job_id"))
        jobs_root = (
            payload.get("doc_sync", {}).get("jobs_root")
            if isinstance(payload.get("doc_sync"), dict)
            else ".agent_orchestrator/jobs"
        )
        return f"python -m agent_orchestrator.cli status {job_id} --root {jobs_root}"
    if primary_action == "revise":
        return (
            "python -m agent_orchestrator.cli team revise "
            f"{session_id} --summary \"close required gaps\" --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "approve":
        return (
            "python -m agent_orchestrator.cli team approve "
            f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "execute":
        if not _summary_bool(status_summary, "approved_plan_ready"):
            return (
                "python -m agent_orchestrator.cli team status "
                f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
            )
        return (
            "python -m agent_orchestrator.cli team execute "
            f"{session_id} --mode success_first --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "human_decision":
        return (
            "python -m agent_orchestrator.cli team summary "
            f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "inspect_compliance":
        return (
            "python -m agent_orchestrator.cli team check-compliance "
            f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "inspect_execution":
        return (
            "python -m agent_orchestrator.cli team inspect-execution "
            f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
        )
    return (
        "python -m agent_orchestrator.cli team status "
        f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
    )
def _parse_agent_flag(value: str | None) -> bool | None:
    if value is None:
        return None
    return value == "on"


if __name__ == "__main__":
    main()
