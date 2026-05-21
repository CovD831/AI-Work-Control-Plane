"""Command line interface for the orchestration MVP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_orchestrator.adapters import RuntimeProviderAdapter
from agent_orchestrator.command import CommandJobRuntime, ProviderHealthCheck
from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.policies import OrchestrationMode
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
        handle = orchestrator.start_run(args.requirement, mode, reroute=args.reroute == "on")
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
        handle = orchestrator.start_run(args.requirement, mode, reroute=args.reroute == "on")
        print(json.dumps(handle.to_dict(), ensure_ascii=False, indent=2))
    else:
        run = orchestrator.run(args.requirement, mode, reroute=args.reroute == "on")
        _print_run_summary(run)
        print(json.dumps(run.to_dict(), ensure_ascii=False, indent=2))


def _build_orchestrator(runtime: str, provider: str | None) -> Orchestrator:
    if runtime == "mock":
        return Orchestrator()

    command_runtime = CommandJobRuntime()
    selected_provider = provider or "codex"
    kind = "review" if selected_provider == "claude" else "implementation"
    return Orchestrator(
        worker=RuntimeProviderAdapter(
            runtime=command_runtime,
            provider=selected_provider,
            kind=kind,
        )
    )

def _print_run_summary(run: object) -> None:
    initial_mode = getattr(run, "initial_mode", None)
    final_mode = getattr(run, "final_mode", None)
    attempts = getattr(run, "attempts", [])
    reroute_history = getattr(run, "reroute_history", [])
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
        print(
            "rerouted: "
            f"{initial_mode.value} -> {final_mode.value} "
            f"(attempts={len(attempts)}"
            + (f", reasons={reasons}" if reasons else "")
            + ")"
        )
    else:
        print(f"completed: mode={final_mode.value if final_mode else 'unknown'} attempts={len(attempts)}")


if __name__ == "__main__":
    main()
