"""Command line interface for the orchestration MVP."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, argparse, json, os, pathlib, shutil
# RESPONSIBILITY: Parse CLI commands and delegate presentation-safe orchestration actions.
# MODULE: interface
# ---


import argparse
import json
import shutil
from pathlib import Path

from agent_orchestrator.adapters import RuntimeProviderAdapter, RuntimeProviderReviewRescueAdapter
from agent_orchestrator.agent_config import AgentConfigStore
from agent_orchestrator.cli_common import FORMAT_CHOICES, emit_json as _emit_json
from agent_orchestrator.cli_evidence import run_evidence_command
from agent_orchestrator.cli_jobs import run_job_command
from agent_orchestrator.cli_team import TeamCommandHandlers, run_team_command
from agent_orchestrator.command import ProviderHealthCheck, RuntimeModeRouter, direct_api_auth_status
from agent_orchestrator.execution import CodingAgentExecutionRuntime, ExecutionRequest, LegacyExecutionRuntime
from agent_orchestrator.intake import ExecutionMode, IntentIntake, TaskRouter
from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.policies import OrchestrationMode, get_policy
from agent_orchestrator.planning import PlanStore, TeamOrchestrator
from agent_orchestrator.run_store import RunStore
from agent_orchestrator.session import SessionRuntime
from agent_orchestrator.strategy import NativeStrategyPlanner
from agent_orchestrator.tasks import TaskContract


REVIEW_POLICY_CHOICES = ["auto", "standard", "adversarial", "required-human"]


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
        "--review-policy",
        choices=REVIEW_POLICY_CHOICES,
        default="auto",
        help="Override the structured review policy recorded in the execution contract.",
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
    start_parser.add_argument("--review-policy", choices=REVIEW_POLICY_CHOICES, default="auto")
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
    status_parser.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    result_parser = subparsers.add_parser("result", help="Show job result.")
    result_parser.add_argument("job_id", help="Job id to inspect.")
    result_parser.add_argument("--root", default=".agent_orchestrator/jobs", help="Job store root.")
    result_parser.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    send_parser = subparsers.add_parser("send", help="Send a follow-up message to a job.")
    send_parser.add_argument("job_id", help="Job id to update.")
    send_parser.add_argument("message", help="Follow-up message.")
    send_parser.add_argument("--root", default=".agent_orchestrator/jobs", help="Job store root.")
    send_parser.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    cancel_parser = subparsers.add_parser("cancel", help="Cancel a job.")
    cancel_parser.add_argument("job_id", help="Job id to cancel.")
    cancel_parser.add_argument("--root", default=".agent_orchestrator/jobs", help="Job store root.")
    cancel_parser.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    health_parser = subparsers.add_parser("health", help="Check local provider availability.")
    health_parser.add_argument("--refresh", action="store_true", help="Bypass provider health cache and refresh live status.")
    health_parser.add_argument("--cache-ttl", type=int, default=60, help="Provider health cache TTL in seconds.")
    health_parser.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    evidence_parser = subparsers.add_parser("evidence", help="Capture workflow evidence reports.")
    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command")

    evidence_benchmark = evidence_subparsers.add_parser("benchmark", help="Run the built-in workflow evidence cases.")
    evidence_benchmark.add_argument("--output", help="Optional JSON output path.")
    evidence_benchmark.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    evidence_capture = evidence_subparsers.add_parser("capture", help="Run evidence cases from a JSON case file.")
    evidence_capture.add_argument("--case-file", required=True, help="JSON file containing real workflow evidence cases.")
    evidence_capture.add_argument("--output", required=True, help="JSON output path.")
    evidence_capture.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    evidence_report = evidence_subparsers.add_parser("report", help="Write a markdown workflow evidence report.")
    evidence_report.add_argument("--case-file", help="Optional JSON file containing workflow evidence cases.")
    evidence_report.add_argument("--output", required=True, help="Markdown output path.")
    evidence_report.add_argument("--json-output", help="Optional JSON evidence output path.")
    evidence_report.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    evidence_compare = evidence_subparsers.add_parser("compare", help="Compare two workflow evidence JSON captures.")
    evidence_compare.add_argument("--baseline", required=True, help="Baseline evidence JSON path.")
    evidence_compare.add_argument("--current", required=True, help="Current evidence JSON path.")
    evidence_compare.add_argument("--output", required=True, help="Markdown trend output path.")
    evidence_compare.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    ui_parser = subparsers.add_parser("ui", help="启动本地治理控制台。")
    ui_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    ui_parser.add_argument("--port", type=int, default=8765, help="Port to listen on.")
    ui_parser.add_argument("--plans-root", default=".agent_orchestrator/plans")
    ui_parser.add_argument("--runs-root", default=".agent_orchestrator/runs")
    ui_parser.add_argument("--jobs-root", default=".agent_orchestrator/jobs")
    ui_parser.add_argument("--runtime", choices=["mock", "command"], default="mock")
    ui_parser.add_argument("--job-runtime", choices=["mock", "tmux"], default="mock")
    ui_parser.add_argument("--provider", choices=["codex", "claude"])

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
    team_start.add_argument("--review-policy", choices=REVIEW_POLICY_CHOICES, default="auto")
    team_start.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_status = team_subparsers.add_parser("status", help="Inspect a plan session.")
    team_status.add_argument("session_id")
    team_status.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_status.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_status.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_status.add_argument("--provider", choices=["codex", "claude"])
    team_status.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_summary = team_subparsers.add_parser("summary", help="Show a human-readable plan session summary.")
    team_summary.add_argument("session_id")
    team_summary.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_summary.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_summary.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_summary.add_argument("--provider", choices=["codex", "claude"])
    team_summary.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_roles = team_subparsers.add_parser("roles", help="查看职责约束与输出要求。")
    team_roles.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_roles.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_roles.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_roles.add_argument("--provider", choices=["codex", "claude"])
    team_roles.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_next = team_subparsers.add_parser("next", help="Show the next recommended team command.")
    team_next.add_argument("session_id")
    team_next.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_next.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_next.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_next.add_argument("--provider", choices=["codex", "claude"])
    team_next.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_task = team_subparsers.add_parser("task", help="Inspect or update plan session tasks.")
    team_task_subparsers = team_task.add_subparsers(dest="task_command")
    team_task_list = team_task_subparsers.add_parser("list", help="List task-pool items for a plan session.")
    team_task_list.add_argument("session_id")
    team_task_list.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_task_list.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_task_list.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_task_list.add_argument("--provider", choices=["codex", "claude"])
    team_task_list.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")
    team_task_next = team_task_subparsers.add_parser("next", help="Show the next executable task for a plan session.")
    team_task_next.add_argument("session_id")
    team_task_next.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_task_next.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_task_next.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_task_next.add_argument("--provider", choices=["codex", "claude"])
    team_task_next.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")
    team_task_done = team_task_subparsers.add_parser("done", help="Mark a task-pool checklist task as done.")
    team_task_done.add_argument("session_id")
    team_task_done.add_argument("task_id")
    team_task_done.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_task_done.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_task_done.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_task_done.add_argument("--provider", choices=["codex", "claude"])
    team_task_done.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

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

    team_refresh_docs = team_subparsers.add_parser("refresh-docs", help="Refresh canonical process documentation.")
    team_refresh_docs.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_refresh_docs.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_refresh_docs.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_refresh_docs.add_argument("--provider", choices=["codex", "claude"])

    team_repair_compliance = team_subparsers.add_parser(
        "repair-compliance",
        help="Refresh canonical docs and show the remaining compliance status.",
    )
    team_repair_compliance.add_argument("session_id", nargs="?")
    team_repair_compliance.add_argument("--changed-file", action="append", default=[])
    team_repair_compliance.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_repair_compliance.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_repair_compliance.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_repair_compliance.add_argument("--provider", choices=["codex", "claude"])
    team_repair_compliance.add_argument("--fix-headers", action="store_true")

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

    team_chat = team_subparsers.add_parser("chat", help="Send a planning note to the lead agent.")
    team_chat.add_argument("session_id")
    team_chat.add_argument("--message", required=True)
    team_chat.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_chat.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_chat.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_chat.add_argument("--provider", choices=["codex", "claude"])

    team_draft_ready = team_subparsers.add_parser("draft-ready", help="Confirm the first draft is ready for review.")
    team_draft_ready.add_argument("session_id")
    team_draft_ready.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_draft_ready.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_draft_ready.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_draft_ready.add_argument("--provider", choices=["codex", "claude"])

    team_submit_review = team_subparsers.add_parser("submit-review", help="Submit the confirmed draft to adversarial review.")
    team_submit_review.add_argument("session_id")
    team_submit_review.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_submit_review.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_submit_review.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_submit_review.add_argument("--provider", choices=["codex", "claude"])

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
    team_execute.add_argument("--review-policy", choices=REVIEW_POLICY_CHOICES, default="auto")
    team_execute.add_argument("--context-policy", choices=["fresh", "resume", "resume_if_same_task"], default="resume_if_same_task")
    team_execute.add_argument("--execution-mode", choices=["legacy", "native"], default="native")

    team_setup = team_subparsers.add_parser("setup", help="Inspect provider/runtime and workflow readiness.")
    team_setup.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_setup.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_setup.add_argument("--jobs-root", default=".agent_orchestrator/jobs")
    team_setup.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_setup.add_argument("--provider", choices=["codex", "claude"])
    team_setup.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_inspect_execution = team_subparsers.add_parser(
        "inspect-execution",
        help="Show the linked execution run for a completed or in-progress plan session.",
    )
    team_inspect_execution.add_argument("session_id")
    team_inspect_execution.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_inspect_execution.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_inspect_execution.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_inspect_execution.add_argument("--provider", choices=["codex", "claude"])
    team_inspect_execution.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_inspect_blockers = team_subparsers.add_parser(
        "inspect-blockers",
        help="Show a structured blocker summary for a blocked or recovery-oriented plan session.",
    )
    team_inspect_blockers.add_argument("session_id")
    team_inspect_blockers.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_inspect_blockers.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_inspect_blockers.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_inspect_blockers.add_argument("--provider", choices=["codex", "claude"])
    team_inspect_blockers.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_inspect_knowledge = team_subparsers.add_parser(
        "inspect-knowledge",
        help="Show decisions, lessons, and workflow notes for a plan session.",
    )
    team_inspect_knowledge.add_argument("session_id")
    team_inspect_knowledge.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_inspect_knowledge.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_inspect_knowledge.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_inspect_knowledge.add_argument("--provider", choices=["codex", "claude"])
    team_inspect_knowledge.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_inspect_handoff = team_subparsers.add_parser(
        "inspect-handoff",
        help="Show structured handoff packets for a plan session.",
    )
    team_inspect_handoff.add_argument("session_id")
    team_inspect_handoff.add_argument("--limit", type=int, default=10)
    team_inspect_handoff.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_inspect_handoff.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_inspect_handoff.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_inspect_handoff.add_argument("--provider", choices=["codex", "claude"])
    team_inspect_handoff.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_inspect_docs = team_subparsers.add_parser(
        "inspect-docs",
        help="Build an agent-ready canonical documentation context package.",
    )
    team_inspect_docs.add_argument("--query", default="", help="Task or topic used to select relevant canonical docs.")
    team_inspect_docs.add_argument("--changed-file", action="append", default=[])
    team_inspect_docs.add_argument("--all", action="store_true", help="Include every canonical process doc.")
    team_inspect_docs.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_inspect_docs.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_inspect_docs.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_inspect_docs.add_argument("--provider", choices=["codex", "claude"])
    team_inspect_docs.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_docs_index = team_subparsers.add_parser(
        "docs-index",
        help="Find relevant canonical docs, ADRs, tests, and commands for a task.",
    )
    team_docs_index.add_argument("--query", default="")
    team_docs_index.add_argument("--changed-file", action="append", default=[])
    team_docs_index.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_docs_index.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_docs_index.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_docs_index.add_argument("--provider", choices=["codex", "claude"])
    team_docs_index.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_workspace_status = team_subparsers.add_parser(
        "workspace-status",
        help="Show the AI Work Control Plane workspace state snapshot.",
    )
    team_workspace_status.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_workspace_status.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_workspace_status.add_argument("--jobs-root", default=".agent_orchestrator/jobs")
    team_workspace_status.add_argument("--approvals-root", default=".agent_orchestrator/approvals")
    team_workspace_status.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_workspace_status.add_argument("--provider", choices=["codex", "claude"])
    team_workspace_status.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_runtime = team_subparsers.add_parser("runtime", help="Inspect runtime fidelity artifacts.")
    team_runtime_subparsers = team_runtime.add_subparsers(dest="runtime_command")
    team_runtime_inspect = team_runtime_subparsers.add_parser("inspect", help="Inspect a provider session snapshot for a job.")
    team_runtime_inspect.add_argument("job_id")
    team_runtime_inspect.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_runtime_inspect.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_runtime_inspect.add_argument("--jobs-root", default=".agent_orchestrator/jobs")
    team_runtime_inspect.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_runtime_inspect.add_argument("--provider", choices=["codex", "claude"])
    team_runtime_inspect.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_context_packet = team_subparsers.add_parser(
        "context-packet",
        help="Build an AI Work Control Plane context packet without choosing strategy.",
    )
    team_context_packet.add_argument("--query", default="")
    team_context_packet.add_argument("--changed-file", action="append", default=[])
    team_context_packet.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_context_packet.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_context_packet.add_argument("--jobs-root", default=".agent_orchestrator/jobs")
    team_context_packet.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_context_packet.add_argument("--provider", choices=["codex", "claude"])
    team_context_packet.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_topology = team_subparsers.add_parser("topology", help="Inspect AI-native execution topology artifacts.")
    team_topology_subparsers = team_topology.add_subparsers(dest="topology_command")
    team_topology_inspect = team_topology_subparsers.add_parser("inspect", help="Inspect a plan session topology snapshot.")
    team_topology_inspect.add_argument("session_id")
    team_topology_inspect.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_topology_inspect.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_topology_inspect.add_argument("--approvals-root", default=".agent_orchestrator/approvals")
    team_topology_inspect.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_topology_inspect.add_argument("--provider", choices=["codex", "claude"])
    team_topology_inspect.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_approvals = team_subparsers.add_parser("approvals", help="List or resolve control-plane approval items.")
    team_approvals_subparsers = team_approvals.add_subparsers(dest="approvals_command")
    team_approvals_list = team_approvals_subparsers.add_parser("list", help="List pending and resolved approval items.")
    team_approvals_list.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_approvals_list.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_approvals_list.add_argument("--approvals-root", default=".agent_orchestrator/approvals")
    team_approvals_list.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_approvals_list.add_argument("--provider", choices=["codex", "claude"])
    team_approvals_list.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")
    team_approvals_resolve = team_approvals_subparsers.add_parser("resolve", help="Record a human approval decision.")
    team_approvals_resolve.add_argument("approval_id")
    team_approvals_resolve.add_argument("--status", choices=["approved", "rejected", "resolved"], required=True)
    team_approvals_resolve.add_argument("--reason", required=True)
    team_approvals_resolve.add_argument("--actor", default="human")
    team_approvals_resolve.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_approvals_resolve.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_approvals_resolve.add_argument("--approvals-root", default=".agent_orchestrator/approvals")
    team_approvals_resolve.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_approvals_resolve.add_argument("--provider", choices=["codex", "claude"])
    team_approvals_resolve.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_evidence_gates = team_subparsers.add_parser(
        "evidence-gates",
        help="Show the AI Work Control Plane evidence bundle and gate summaries.",
    )
    team_evidence_gates.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_evidence_gates.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_evidence_gates.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_evidence_gates.add_argument("--provider", choices=["codex", "claude"])
    team_evidence_gates.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")

    team_governance_bundle = team_subparsers.add_parser(
        "governance-bundle",
        help="Export or inspect a portable AI Work Control Plane governance bundle.",
    )
    team_governance_bundle_subparsers = team_governance_bundle.add_subparsers(dest="governance_bundle_command")
    team_governance_bundle_export = team_governance_bundle_subparsers.add_parser("export", help="Export a portable governance bundle JSON file.")
    team_governance_bundle_export.add_argument("--output", required=True)
    team_governance_bundle_export.add_argument("--query", default="governance externalization")
    team_governance_bundle_export.add_argument("--changed-file", action="append", default=[])
    team_governance_bundle_export.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_governance_bundle_export.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_governance_bundle_export.add_argument("--jobs-root", default=".agent_orchestrator/jobs")
    team_governance_bundle_export.add_argument("--approvals-root", default=".agent_orchestrator/approvals")
    team_governance_bundle_export.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_governance_bundle_export.add_argument("--provider", choices=["codex", "claude"])
    team_governance_bundle_export.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")
    team_governance_bundle_inspect = team_governance_bundle_subparsers.add_parser("inspect", help="Inspect a governance bundle JSON file.")
    team_governance_bundle_inspect.add_argument("bundle_path")
    team_governance_bundle_inspect.add_argument("--plans-root", default=".agent_orchestrator/plans")
    team_governance_bundle_inspect.add_argument("--runs-root", default=".agent_orchestrator/runs")
    team_governance_bundle_inspect.add_argument("--runtime", choices=["mock", "command"], default="mock")
    team_governance_bundle_inspect.add_argument("--provider", choices=["codex", "claude"])
    team_governance_bundle_inspect.add_argument("--format", choices=FORMAT_CHOICES, default="pretty")
    args = parser.parse_args()

    if args.command == "health":
        _emit_json(_provider_health_snapshot(refresh=args.refresh, ttl_seconds=args.cache_ttl), args)
        return

    if args.command == "evidence":
        run_evidence_command(args)
        return

    if args.command == "ui":
        _run_ui_server(
            host=args.host,
            port=args.port,
            plans_root=args.plans_root,
            runs_root=args.runs_root,
            jobs_root=args.jobs_root,
            runtime=args.runtime,
            job_runtime=args.job_runtime,
            provider=args.provider,
        )
        return

    if args.command == "install-hooks":
        _install_git_hooks(Path(args.root))
        return

    if args.command == "team":
        run_team_command(args, parser, _team_command_handlers())
        return

    if run_job_command(args):
        return

    if args.command == "start":
        orchestrator = _build_orchestrator(args.runtime, args.provider)
        mode = None if args.mode == "auto" else OrchestrationMode(args.mode)
        result = _execute_cli_request(
            orchestrator=orchestrator,
            requirement=args.requirement,
            mode=mode,
            reroute=args.reroute == "on",
            agent_enabled=_parse_agent_flag(args.agent),
            depth=args.depth,
            review_policy_override=getattr(args, "review_policy", "auto"),
            provider_health_snapshot=_provider_health_snapshot() if args.runtime == "command" else None,
            async_run=True,
        )
        print(json.dumps(result.payload, ensure_ascii=False, indent=2))
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
        result = _execute_cli_request(
            orchestrator=orchestrator,
            requirement=args.requirement,
            mode=mode,
            reroute=args.reroute == "on",
            agent_enabled=_parse_agent_flag(args.agent),
            depth=args.depth,
            review_policy_override=getattr(args, "review_policy", "auto"),
            provider_health_snapshot=_provider_health_snapshot() if args.runtime == "command" else None,
            async_run=True,
        )
        print(json.dumps(result.payload, ensure_ascii=False, indent=2))
    else:
        result = _execute_cli_request(
            orchestrator=orchestrator,
            requirement=args.requirement,
            mode=mode,
            reroute=args.reroute == "on",
            agent_enabled=_parse_agent_flag(args.agent),
            depth=args.depth,
            review_policy_override=getattr(args, "review_policy", "auto"),
            provider_health_snapshot=_provider_health_snapshot() if args.runtime == "command" else None,
            async_run=False,
        )
        run = orchestrator.poll_run(result.run_id) if result.run_id else result.payload
        _print_run_summary(run)
        print(json.dumps(result.payload, ensure_ascii=False, indent=2))


def _build_orchestrator(runtime: str, provider: str | None) -> Orchestrator:
    agent_config = AgentConfigStore().read()
    if runtime == "mock":
        return Orchestrator()

    command_runtime = RuntimeModeRouter()
    worker_default_provider = provider or agent_config.profile("worker").provider
    reviewer_default_provider = provider or agent_config.profile("execution_reviewer").provider
    return Orchestrator(
        worker=RuntimeProviderAdapter(
            runtime=command_runtime,
            default_provider=worker_default_provider,
            kind="implementation",
            agent_config=agent_config,
        ),
        reviewer=RuntimeProviderReviewRescueAdapter(
            runtime=command_runtime,
            default_provider=reviewer_default_provider,
            agent_config=agent_config,
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
        agent_config=AgentConfigStore().read(),
    )


def _execute_cli_request(
    *,
    orchestrator: Orchestrator,
    requirement: str,
    mode: OrchestrationMode | None,
    reroute: bool,
    agent_enabled: bool | None,
    depth: int | None,
    review_policy_override: str | None,
    provider_health_snapshot: dict[str, object] | None,
    async_run: bool,
):
    router = TaskRouter()
    route = router.route(requirement)

    if route.execution_mode == ExecutionMode.NO_EXECUTION:
        payload = {
            "requirement": requirement,
            "route": route.to_dict(),
            "status": "not_executed",
            "message": "Task router classified this request as non-executable in Phase 1.",
        }
        return type("NoExecutionResult", (), {"payload": payload, "run_id": None})()

    policy = get_policy(mode or OrchestrationMode.SUCCESS_FIRST, agent_enabled=agent_enabled, depth=depth)
    intake = IntentIntake(orchestrator.planner)
    intake_result = intake.intake(requirement, route, policy)
    task_contract = TaskContract.from_dict(intake_result.task_contract) if isinstance(intake_result.task_contract, dict) else None
    strategy_planner = orchestrator.strategy_planner or NativeStrategyPlanner(orchestrator.decomposer)
    strategy_plan = strategy_planner.plan(task_contract, policy, route=route) if task_contract is not None else None
    session_runtime = SessionRuntime()
    session = session_runtime.start_session(
        origin="cli_direct",
        metadata={
            "requirement": requirement,
            "runtime_name": route.execution_mode.value,
            "execution_mode": route.execution_mode.value,
        },
    )
    clarify_summary = intake_result.to_dict()
    if isinstance(task_contract, TaskContract):
        clarify_summary["task_contract"] = task_contract.to_dict()
    strategy_summary = strategy_plan.summary() if strategy_plan is not None else {}
    session, turn, snapshot = session_runtime.start_turn(
        session_id=session.session_id,
        requirement=requirement,
        route=route.to_dict(),
        clarify_summary=clarify_summary,
        strategy_summary=strategy_summary,
        task_contract=task_contract.to_dict() if task_contract is not None else {},
        compatibility_metadata=strategy_plan.compatibility_metadata if strategy_plan is not None else {},
        selected_execution_strategy=strategy_plan.strategy.value if strategy_plan is not None else "unknown",
        planner_family=strategy_plan.planner_family if strategy_plan is not None else "native",
        metadata={
            "runtime_name": route.execution_mode.value,
            "async_requested": async_run,
        },
    )

    runtime = _select_execution_runtime(orchestrator, route.execution_mode)
    request = ExecutionRequest(
        requirement=requirement,
        route=route,
        runtime_name=runtime.name,
        mode=mode,
        reroute=reroute,
        agent_enabled=agent_enabled,
        depth=depth,
        review_policy_override=review_policy_override,
        provider_health_snapshot=provider_health_snapshot,
        task_contract=intake_result.task_contract,
        session_id=session.session_id,
        turn_id=turn.turn_id,
        context_snapshot=snapshot.to_dict(),
        resume_kind=snapshot.resume_kind,
        session_metadata={
            "origin": session.origin,
            "current_turn_id": session.current_turn_id,
        },
    )
    result = runtime.start(request) if async_run else runtime.run(request)
    session_runtime.attach_run_result(
        session_id=session.session_id,
        turn_id=turn.turn_id,
        linked_run_id=result.run_id,
        status=result.status or "unknown",
        accepted=result.accepted,
        runtime_name=result.runtime_name,
        payload=result.payload,
    )
    result.payload.setdefault("agent_session", session.to_dict())
    result.payload.setdefault("agent_turn", turn.to_dict())
    result.payload.setdefault("context_snapshot", snapshot.to_dict())
    return result


def _select_execution_runtime(orchestrator: Orchestrator, execution_mode: ExecutionMode):
    if execution_mode == ExecutionMode.CODING_AGENT:
        return CodingAgentExecutionRuntime(orchestrator)
    return LegacyExecutionRuntime(orchestrator)


def _team_command_handlers() -> TeamCommandHandlers:
    return TeamCommandHandlers(
        build_team_orchestrator=_build_team_orchestrator,
        provider_health_snapshot=_provider_health_snapshot,
        runtime_mode_contract=_runtime_mode_contract,
    )


def _run_ui_server(
    *,
    host: str,
    port: int,
    plans_root: str,
    runs_root: str,
    jobs_root: str,
    runtime: str,
    job_runtime: str,
    provider: str | None,
) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("Install UI dependencies with `pip install -e '.[ui]'` to run the dashboard.") from exc

    from agent_orchestrator.ui_server import create_app
    from agent_orchestrator.ui_service import DashboardService
    from agent_orchestrator.tmux_runtime import TmuxJobRuntime
    from agent_orchestrator.jobs import FileJobRuntime

    service = DashboardService(
        team=_build_team_orchestrator(runtime, provider, plans_root, runs_root),
        plans_root=plans_root,
        runs_root=runs_root,
        jobs_root=jobs_root,
        job_runtime=TmuxJobRuntime(root=jobs_root) if job_runtime == "tmux" else FileJobRuntime(root=jobs_root),
    )
    print(f"治理控制台: http://{host}:{port}")
    uvicorn.run(create_app(service), host=host, port=port)


def _provider_health_snapshot(*, refresh: bool = False, ttl_seconds: int = 60) -> dict[str, object]:
    health = ProviderHealthCheck(use_cache=True, ttl_seconds=ttl_seconds)
    providers = [
        health.check("codex", refresh=refresh).to_dict(),
        health.check("claude", refresh=refresh).to_dict(),
        {
            "provider": "mock",
            "available": True,
            "detail": "mock provider is always available",
            "binary": None,
            "recommended_fallback": None,
            "cache_tier": "live",
            "cached_at": None,
            "expires_at": None,
        },
    ]
    return {
        "cache": {
            "enabled": True,
            "tiers": ["memory", "disk", "live"],
            "ttl_seconds": ttl_seconds,
            "path": ".agent_orchestrator/cache/provider-health.json",
        },
        "runtime_modes": _runtime_mode_contract(),
        "direct_api_auth": [
            direct_api_auth_status("codex"),
            direct_api_auth_status("claude"),
        ],
        "providers": providers,
    }


def _runtime_mode_contract() -> list[dict[str, object]]:
    return [
        {
            "mode": "cli_inherit",
            "default": True,
            "inherits_user_config": True,
            "description": "Use local CLI auth, global config, project config, and provider-native rules.",
        },
        {
            "mode": "cli_isolated",
            "default": False,
            "inherits_user_config": False,
            "description": "Run CLI jobs with a repository-owned runtime home and auditable environment metadata.",
        },
        {
            "mode": "direct_api",
            "default": False,
            "inherits_user_config": False,
            "description": "Use API-key-backed single-turn calls for low-side-effect governance work; no local tool loop.",
        },
    ]


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
        clarify_summary = execution_contract.get("clarify_summary", {})
        if isinstance(clarify_summary, dict) and clarify_summary:
            print(_format_clarify_summary_line(clarify_summary))
        decomposition_summary = execution_contract.get("decomposition_summary", {})
        if isinstance(decomposition_summary, dict) and decomposition_summary:
            print(_format_decomposition_summary_line(decomposition_summary))


def _format_clarify_summary_line(summary: dict[str, object]) -> str:
    task_type = summary.get("task_type", "unknown")
    slot_sources = summary.get("slot_sources", {})
    slot_source_text = (
        ",".join(f"{key}={value}" for key, value in sorted(slot_sources.items()))
        if isinstance(slot_sources, dict) and slot_sources
        else "none"
    )
    unknown_slots = summary.get("unknown_slots", [])
    unknown_text = ",".join(str(item) for item in unknown_slots) if isinstance(unknown_slots, list) and unknown_slots else "none"
    warnings = summary.get("slot_fill_warnings", [])
    warning_text = "; ".join(str(item) for item in warnings) if isinstance(warnings, list) and warnings else "none"
    return (
        "clarify: "
        f"task_type={task_type} "
        f"slot_sources={slot_source_text} "
        f"unknown_slots={unknown_text} "
        f"warnings={warning_text}"
    )


def _format_decomposition_summary_line(summary: dict[str, object]) -> str:
    strategy = summary.get("selected_strategy", "unknown")
    shape = summary.get("selected_shape", "unknown")
    score = summary.get("selected_score", "unknown")
    candidate_count = summary.get("candidate_count", 0)
    rejected = summary.get("rejected_strategies", [])
    rejected_text = ",".join(str(item) for item in rejected) if isinstance(rejected, list) and rejected else "none"
    return (
        "decompose: "
        f"selected={strategy} "
        f"shape={shape} "
        f"score={score} "
        f"candidate_count={candidate_count} "
        f"rejected={rejected_text}"
    )


def _parse_agent_flag(value: str | None) -> bool | None:
    if value is None:
        return None
    return value == "on"


if __name__ == "__main__":
    main()
