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
from agent_orchestrator.cli_common import FORMAT_CHOICES, emit_json as _emit_json, json_only as _json_only
from agent_orchestrator.cli_evidence import run_evidence_command
from agent_orchestrator.cli_jobs import run_job_command
from agent_orchestrator.cli_presenters import (
    print_team_next as _print_team_next_presenter,
    print_team_runbook as _print_team_runbook_presenter,
    print_team_summary as _print_team_summary_presenter,
    pick_primary_action as _pick_primary_action,
    print_approval_queue_summary as _print_approval_queue_summary_presenter,
    print_approval_resolution_summary as _print_approval_resolution_summary_presenter,
    print_blocker_session_summary as _print_blocker_session_summary_presenter,
    print_context_packet_summary as _print_context_packet_summary_presenter,
    print_docs_context_summary as _print_docs_context_summary_presenter,
    print_docs_index_summary as _print_docs_index_summary_presenter,
    print_evidence_bundle_summary as _print_evidence_bundle_summary_presenter,
    print_handoff_summary as _print_handoff_summary_presenter,
    print_provider_session_snapshot_summary as _print_provider_session_snapshot_summary_presenter,
    print_execution_session_summary as _print_execution_session_summary_presenter,
    print_topology_snapshot_summary as _print_topology_snapshot_summary_presenter,
    print_workspace_state_summary as _print_workspace_state_summary_presenter,
    status_summary as _status_summary,
    summary_bool as _summary_bool,
    summary_list as _summary_list,
    summary_text as _summary_text,
    team_next_alternatives as _team_next_alternatives,
    team_display_context as _team_display_context,
)
from agent_orchestrator.command import CommandJobRuntime, ProviderHealthCheck, RuntimeModeRouter, direct_api_auth_status
from agent_orchestrator.control_plane import (
    build_approval_queue,
    build_context_packet,
    build_evidence_bundle,
    build_execution_topology_snapshot,
    build_provider_session_snapshot,
    build_recovery_recommendation,
    build_workspace_index,
    build_workspace_state_snapshot,
    resolve_approval_item,
)
from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.policies import OrchestrationMode
from agent_orchestrator.planning import PlanStore, TeamOrchestrator, build_operator_runbook
from agent_orchestrator.planning_support import repair_missing_source_headers
from agent_orchestrator.roles import role_contracts
from agent_orchestrator.run_store import RunStore


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

    ui_parser = subparsers.add_parser("ui", help="Start the local Agent Team Console dashboard.")
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

    team_roles = team_subparsers.add_parser("roles", help="Show role contracts and skill discipline.")
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
        team = _build_team_orchestrator(args.runtime, getattr(args, "provider", None), args.plans_root, args.runs_root)
        health_snapshot = _provider_health_snapshot() if args.runtime == "command" else None
        if args.team_command == "start":
            _emit_json(
                team.start(
                    args.requirement,
                    review_policy_override=getattr(args, "review_policy", "auto"),
                    provider_health_snapshot=health_snapshot,
                ).to_dict(),
                args,
            )
            return
        if args.team_command == "status":
            _emit_json(team.status(args.session_id).to_dict(), args)
            return
        if args.team_command == "summary":
            session = team.status(args.session_id)
            if _json_only(args):
                _emit_json(session.to_dict(), args)
            else:
                _print_team_summary(session)
            return
        if args.team_command == "roles":
            payload = _team_role_contract_payload()
            if not _json_only(args):
                _print_team_role_contracts(payload)
            _emit_json(payload, args)
            return
        if args.team_command == "next":
            session = team.status(args.session_id)
            if _json_only(args):
                payload = session.to_dict()
                payload["recovery_recommendation"] = build_recovery_recommendation(session)
                _emit_json(payload, args)
            else:
                _print_team_next(session, args)
            return
        if args.team_command == "task":
            if args.task_command == "list":
                payload = team.task_list(args.session_id)
            elif args.task_command == "next":
                payload = team.task_next(args.session_id)
            elif args.task_command == "done":
                payload = team.task_done(args.session_id, args.task_id)
            else:
                parser.error("a team task subcommand is required")
            if not _json_only(args):
                _print_team_task_payload(payload)
            _emit_json(payload, args)
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
        if args.team_command == "refresh-docs":
            print(json.dumps(team.refresh_documentation_sync(), ensure_ascii=False, indent=2))
            return
        if args.team_command == "repair-compliance":
            changed_files = list(getattr(args, "changed_file", []) or [])
            refresh_payload = team.refresh_documentation_sync()
            header_repair = (
                repair_missing_source_headers(Path.cwd(), changed_files=changed_files)
                if getattr(args, "fix_headers", False)
                else {"changed_files": [], "required_actions": [], "remaining_warnings": []}
            )
            compliance = (
                team.check_session_compliance(args.session_id, changed_files=changed_files)
                if args.session_id
                else team.check_compliance(changed_files=changed_files)
            )
            payload = {
                "refresh_results": refresh_payload.get("refresh_results", []),
                "header_repair": header_repair,
                "doc_sync": refresh_payload,
                "compliance": compliance,
                "required_actions": compliance.get("required_actions", []),
                "remaining_warnings": compliance.get("warnings", []),
                "recommended_commands": compliance.get("recommended_commands", []),
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            if compliance.get("blocking"):
                raise SystemExit(1)
            return
        if args.team_command == "retry-review":
            print(json.dumps(team.retry_review(args.session_id).to_dict(), ensure_ascii=False, indent=2))
            return
        if args.team_command == "retry-adversarial-review":
            print(json.dumps(team.retry_adversarial_review(args.session_id).to_dict(), ensure_ascii=False, indent=2))
            return
        if args.team_command == "chat":
            print(json.dumps(team.chat_with_lead(args.session_id, message=args.message).to_dict(), ensure_ascii=False, indent=2))
            return
        if args.team_command == "draft-ready":
            print(json.dumps(team.mark_draft_ready(args.session_id).to_dict(), ensure_ascii=False, indent=2))
            return
        if args.team_command == "submit-review":
            print(json.dumps(team.submit_draft_for_review(args.session_id).to_dict(), ensure_ascii=False, indent=2))
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
            print(
                json.dumps(
                    team.execute(
                        args.session_id,
                        mode,
                        review_policy_override=getattr(args, "review_policy", "auto"),
                        provider_health_snapshot=health_snapshot,
                        context_policy=getattr(args, "context_policy", "resume_if_same_task"),
                    ).to_dict(),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        if args.team_command == "setup":
            payload = _team_setup_snapshot(team, args)
            if not _json_only(args):
                _print_team_setup_summary(payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        if args.team_command == "inspect-execution":
            payload = team.inspect_execution(args.session_id)
            if not _json_only(args):
                _print_execution_session_summary(payload)
            _emit_json(payload, args)
            return
        if args.team_command == "inspect-blockers":
            payload = team.inspect_blockers(args.session_id)
            if not _json_only(args):
                _print_blocker_session_summary(payload)
            _emit_json(payload, args)
            return
        if args.team_command == "inspect-knowledge":
            payload = team.inspect_knowledge(args.session_id)
            if not _json_only(args):
                _print_knowledge_summary(payload)
            _emit_json(payload, args)
            return
        if args.team_command == "inspect-handoff":
            payload = team.inspect_handoff(args.session_id, limit=getattr(args, "limit", 10))
            if not _json_only(args):
                _print_handoff_summary(payload)
            _emit_json(payload, args)
            return
        if args.team_command == "inspect-docs":
            payload = team.inspect_docs(
                query=getattr(args, "query", ""),
                changed_files=list(getattr(args, "changed_file", []) or []),
                include_all=bool(getattr(args, "all", False)),
            )
            if not _json_only(args):
                _print_docs_context_summary(payload)
            _emit_json(payload, args)
            return
        if args.team_command == "docs-index":
            payload = team.docs_index(
                query=getattr(args, "query", ""),
                changed_files=list(getattr(args, "changed_file", []) or []),
            )
            if not _json_only(args):
                _print_docs_index_summary(payload)
            _emit_json(payload, args)
            return
        if args.team_command == "workspace-status":
            payload = build_workspace_index(
                Path.cwd(),
                plans_root=getattr(args, "plans_root", ".agent_orchestrator/plans"),
                runs_root=getattr(args, "runs_root", ".agent_orchestrator/runs"),
                jobs_root=getattr(args, "jobs_root", ".agent_orchestrator/jobs"),
                approvals_root=getattr(args, "approvals_root", ".agent_orchestrator/approvals"),
                provider_health=health_snapshot,
            )
            if not _json_only(args):
                _print_workspace_state_summary(payload)
            _emit_json(payload, args)
            return
        if args.team_command == "runtime":
            if args.runtime_command != "inspect":
                parser.error("a team runtime subcommand is required")
            payload = build_provider_session_snapshot(
                args.job_id,
                Path.cwd(),
                jobs_root=getattr(args, "jobs_root", ".agent_orchestrator/jobs"),
            )
            if not _json_only(args):
                _print_provider_session_snapshot_summary(payload)
            _emit_json(payload, args)
            return
        if args.team_command == "context-packet":
            payload = build_context_packet(
                Path.cwd(),
                query=getattr(args, "query", ""),
                changed_files=list(getattr(args, "changed_file", []) or []),
                jobs_root=getattr(args, "jobs_root", ".agent_orchestrator/jobs"),
            )
            if not _json_only(args):
                _print_context_packet_summary(payload)
            _emit_json(payload, args)
            return
        if args.team_command == "topology":
            if args.topology_command != "inspect":
                parser.error("a team topology subcommand is required")
            session = team.status(args.session_id)
            payload = build_execution_topology_snapshot(
                session,
                plans_root=getattr(args, "plans_root", ".agent_orchestrator/plans"),
                approvals_root=getattr(args, "approvals_root", ".agent_orchestrator/approvals"),
                project_root=Path.cwd(),
            )
            if not _json_only(args):
                _print_topology_snapshot_summary(payload)
            _emit_json(payload, args)
            return
        if args.team_command == "approvals":
            if args.approvals_command == "list":
                payload = build_approval_queue(
                    Path.cwd(),
                    plans_root=getattr(args, "plans_root", ".agent_orchestrator/plans"),
                    approvals_root=getattr(args, "approvals_root", ".agent_orchestrator/approvals"),
                )
                if not _json_only(args):
                    _print_approval_queue_summary(payload)
                _emit_json(payload, args)
                return
            if args.approvals_command == "resolve":
                payload = resolve_approval_item(
                    args.approval_id,
                    status=args.status,
                    reason=args.reason,
                    actor=getattr(args, "actor", "human"),
                    project_root=Path.cwd(),
                    plans_root=getattr(args, "plans_root", ".agent_orchestrator/plans"),
                    approvals_root=getattr(args, "approvals_root", ".agent_orchestrator/approvals"),
                )
                if not _json_only(args):
                    _print_approval_resolution_summary(payload)
                _emit_json(payload, args)
                return
            parser.error("a team approvals subcommand is required")
        if args.team_command == "evidence-gates":
            compliance = team.check_compliance()
            payload = build_evidence_bundle(Path.cwd(), compliance=compliance)
            if not _json_only(args):
                _print_evidence_bundle_summary(payload)
            _emit_json(payload, args)
            return
        parser.error("a team subcommand is required")

    if run_job_command(args):
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
            review_policy_override=getattr(args, "review_policy", "auto"),
            provider_health_snapshot=_provider_health_snapshot() if args.runtime == "command" else None,
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
            review_policy_override=getattr(args, "review_policy", "auto"),
            provider_health_snapshot=_provider_health_snapshot() if args.runtime == "command" else None,
        )
        print(json.dumps(handle.to_dict(), ensure_ascii=False, indent=2))
    else:
        run = orchestrator.run(
            args.requirement,
            mode,
            reroute=args.reroute == "on",
            agent_enabled=_parse_agent_flag(args.agent),
            depth=args.depth,
            review_policy_override=getattr(args, "review_policy", "auto"),
            provider_health_snapshot=_provider_health_snapshot() if args.runtime == "command" else None,
        )
        _print_run_summary(run)
        print(json.dumps(run.to_dict(), ensure_ascii=False, indent=2))


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
    print(f"Agent Team Console: http://{host}:{port}")
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


def _print_docs_context_summary(payload: dict[str, object]) -> None:
    _print_docs_context_summary_presenter(payload)


def _print_handoff_summary(payload: dict[str, object]) -> None:
    _print_handoff_summary_presenter(payload)


def _print_provider_session_snapshot_summary(payload: dict[str, object]) -> None:
    _print_provider_session_snapshot_summary_presenter(payload)


def _print_docs_index_summary(payload: dict[str, object]) -> None:
    _print_docs_index_summary_presenter(payload)


def _print_workspace_state_summary(payload: dict[str, object]) -> None:
    _print_workspace_state_summary_presenter(payload)


def _print_context_packet_summary(payload: dict[str, object]) -> None:
    _print_context_packet_summary_presenter(payload)


def _print_topology_snapshot_summary(payload: dict[str, object]) -> None:
    _print_topology_snapshot_summary_presenter(payload)


def _print_approval_queue_summary(payload: dict[str, object]) -> None:
    _print_approval_queue_summary_presenter(payload)


def _print_approval_resolution_summary(payload: dict[str, object]) -> None:
    _print_approval_resolution_summary_presenter(payload)


def _print_evidence_bundle_summary(payload: dict[str, object]) -> None:
    _print_evidence_bundle_summary_presenter(payload)


def _print_team_task_payload(payload: dict[str, object]) -> None:
    print(f"session: {payload.get('session_id')}")
    tasks = payload.get("tasks")
    if isinstance(tasks, list):
        for task in tasks:
            if not isinstance(task, dict):
                continue
            blocked_by = task.get("blocked_by", [])
            blocked_text = f" blocked_by={','.join(str(item) for item in blocked_by)}" if blocked_by else ""
            print(
                "task: "
                f"{task.get('id')} status={task.get('status')} owner={task.get('owner')} "
                f"next_action={task.get('next_action')} title={task.get('title')}{blocked_text}"
            )
    next_task = payload.get("next_executable_task")
    if isinstance(next_task, dict):
        print(
            "next_task: "
            f"{next_task.get('id')} action={next_task.get('next_action')} title={next_task.get('title')}"
        )
    elif payload.get("blocked"):
        blocked_by = payload.get("blocked_by", [])
        print(f"blocked_by: {', '.join(str(item) for item in blocked_by) if blocked_by else 'none'}")


def _team_role_contract_payload() -> dict[str, object]:
    contracts = [contract.to_dict() for contract in role_contracts()]
    return {
        "roles": contracts,
        "contract_count": len(contracts),
        "skill_discipline": "role contracts bind allowed actions, forbidden actions, required outputs, and command refs",
    }


def _print_team_role_contracts(payload: dict[str, object]) -> None:
    print(f"role_contracts: {payload.get('contract_count', 0)}")
    for contract in payload.get("roles", []):
        if not isinstance(contract, dict):
            continue
        print(
            "role: "
            f"{contract.get('role')} runtime_mode={contract.get('runtime_mode')} "
            f"allowed={','.join(str(item) for item in contract.get('allowed_actions', []))} "
            f"required_outputs={','.join(str(item) for item in contract.get('required_outputs', []))}"
        )


def _print_knowledge_summary(payload: dict[str, object]) -> None:
    print(f"session: {payload.get('session_id')}")
    counts = payload.get("counts", {}) if isinstance(payload.get("counts"), dict) else {}
    print(
        "knowledge: "
        f"decisions={counts.get('decisions', 0)} lessons={counts.get('lessons', 0)} "
        f"workflow_notes={counts.get('workflow_notes', 0)}"
    )
    for record in payload.get("knowledge", [])[:5]:
        if isinstance(record, dict):
            print(f"- {record.get('artifact_type')}: {record.get('summary')}")


def _team_setup_snapshot(team: TeamOrchestrator, args: argparse.Namespace) -> dict[str, object]:
    project_root = Path.cwd()
    health_snapshot = _provider_health_snapshot(refresh=args.runtime == "command")
    doc_sync = team.refresh_documentation_sync()
    compliance = team.check_compliance()
    agent_config = AgentConfigStore().read()
    role_profiles = _role_profile_snapshot(agent_config)
    readiness = _build_setup_readiness(project_root, health_snapshot, doc_sync, compliance, role_profiles=role_profiles)
    runtime_measurement = _runtime_measurement_readiness(project_root)
    return {
        "contract": {
            "format": "agent_orchestrator.setup_doctor.v1",
            "json_pure": True,
            "pretty_output": "human-readable summary; automation should consume --format json",
        },
        "provider_health": health_snapshot,
        "runtime_modes": _runtime_mode_contract(),
        "role_profiles": role_profiles,
        "doc_sync": doc_sync,
        "compliance": compliance,
        "readiness": readiness,
        "runtime_measurement": runtime_measurement,
        "release_readiness": _build_release_readiness(project_root, health_snapshot, doc_sync, compliance, readiness, runtime_measurement),
        "stable_fields": [
            "contract",
            "provider_health",
            "runtime_modes",
            "role_profiles",
            "doc_sync",
            "compliance",
            "readiness",
            "runtime_measurement",
            "release_readiness",
            "recommended_commands",
        ],
        "recommended_commands": [
            "python -m agent_orchestrator.cli team check-compliance",
            "python -m agent_orchestrator.cli team refresh-docs",
            "python -m agent_orchestrator.cli health --format json",
        ],
    }


def _print_team_setup_summary(payload: dict[str, object]) -> None:
    readiness = payload.get("readiness", {}) if isinstance(payload.get("readiness"), dict) else {}
    release = payload.get("release_readiness", {}) if isinstance(payload.get("release_readiness"), dict) else {}
    compliance = readiness.get("compliance_status", {}) if isinstance(readiness.get("compliance_status"), dict) else {}
    provider_states = readiness.get("provider_states", []) if isinstance(readiness.get("provider_states"), list) else []
    role_profiles = payload.get("role_profiles", []) if isinstance(payload.get("role_profiles"), list) else []
    checklist = release.get("checklist", {}) if isinstance(release.get("checklist"), dict) else {}
    available = [str(item.get("provider")) for item in provider_states if isinstance(item, dict) and item.get("available")]
    unavailable = [
        str(item.get("provider"))
        for item in provider_states
        if isinstance(item, dict) and not item.get("available")
    ]
    print(
        "setup: "
        f"ready={'yes' if readiness.get('ready') else 'no'} "
        f"release_ready={'yes' if release.get('ready') else 'no'} "
        f"compliance={'blocked' if compliance.get('blocking') else 'ok'}"
    )
    print(f"providers: available={','.join(available) if available else 'none'} unavailable={','.join(unavailable) if unavailable else 'none'}")
    if role_profiles:
        modes = sorted({str(item.get("runtime_mode")) for item in role_profiles if isinstance(item, dict)})
        print(f"runtime_modes: {','.join(modes)}")
    if checklist:
        checklist_text = ", ".join(
            f"{key}={'ok' if value else 'missing'}"
            for key, value in checklist.items()
        )
        print(f"release_checklist: {checklist_text}")
    commands = payload.get("recommended_commands", []) if isinstance(payload.get("recommended_commands"), list) else []
    if commands:
        print(f"next_command: {commands[0]}")


def _build_release_readiness(
    project_root: Path,
    health_snapshot: dict[str, object],
    doc_sync: dict[str, object],
    compliance: dict[str, object],
    readiness: dict[str, object],
    runtime_measurement: dict[str, object] | None = None,
) -> dict[str, object]:
    warnings = list(readiness.get("compliance_status", {}).get("warnings", [])) if isinstance(readiness.get("compliance_status"), dict) else []
    blocking_reasons = list(readiness.get("compliance_status", {}).get("blocking_reasons", [])) if isinstance(readiness.get("compliance_status"), dict) else []
    provider_states = list(readiness.get("provider_states", [])) if isinstance(readiness.get("provider_states"), list) else []
    version_sync = {
        "package_version": _project_version(),
        "version_file_present": (project_root / "pyproject.toml").exists(),
        "version_note": "project metadata is declared in pyproject.toml; no plugin-style distribution is implied",
    }
    evidence_state = {
        "benchmark_report_present": (project_root / "docs" / "process" / "v1x-evidence-report.md").exists(),
        "trend_report_present": (project_root / "docs" / "process" / "v1x-evidence-trend.md").exists(),
        "evidence_cases_present": (project_root / "docs" / "process" / "evidence-cases.json").exists(),
    }
    gate_evidence = _build_gate_evidence_summary(project_root, compliance, evidence_state)
    runtime_measurement = runtime_measurement or _runtime_measurement_readiness(project_root)
    checklist = {
        "version_sync": bool(version_sync["version_file_present"]),
        "tests": "pytest" in " ".join(_release_readiness_commands()),
        "evidence": all(evidence_state.values()),
        "compliance": not blocking_reasons,
        "gate_evidence": bool(gate_evidence.get("available", False)),
        "runtime_measurement": bool(runtime_measurement.get("measurement_surface_available", False)),
    }
    return {
        "project_root": str(project_root),
        "ready": bool(readiness.get("ready", False)) and not blocking_reasons,
        "version_sync": version_sync,
        "provider_states": provider_states,
        "evidence_state": evidence_state,
        "gate_evidence": gate_evidence,
        "runtime_measurement": runtime_measurement,
        "checklist": checklist,
        "warnings": warnings,
        "blocking_reasons": blocking_reasons,
        "recommended_commands": _release_readiness_commands(),
    }



def _build_gate_evidence_summary(
    project_root: Path,
    compliance: dict[str, object],
    evidence_state: dict[str, object],
) -> dict[str, object]:
    gates = [
        {
            "name": "targeted_tests",
            "command": "phase-specific pytest slice",
            "cwd": str(project_root),
            "exit_code": None,
            "duration_seconds": None,
            "summary": "recorded per implementation phase; run only the phase targeted test before final convergence",
            "artifact_path": None,
            "status": "planned",
        },
        {
            "name": "full_tests",
            "command": "pytest",
            "cwd": str(project_root),
            "exit_code": None,
            "duration_seconds": None,
            "summary": "reserved for final convergence",
            "artifact_path": None,
            "status": "planned",
        },
        {
            "name": "compliance",
            "command": "env PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance",
            "cwd": str(project_root),
            "exit_code": 1 if bool(compliance.get("blocking", False)) else 0,
            "duration_seconds": None,
            "summary": "blocked" if bool(compliance.get("blocking", False)) else "passed or warning-only",
            "artifact_path": None,
            "status": "failed" if bool(compliance.get("blocking", False)) else "passed",
        },
        {
            "name": "evidence_report",
            "command": "python -m agent_orchestrator.cli evidence report --output docs/process/v1x-evidence-report.md",
            "cwd": str(project_root),
            "exit_code": 0 if bool(evidence_state.get("benchmark_report_present", False)) else None,
            "duration_seconds": None,
            "summary": "local markdown evidence report present" if bool(evidence_state.get("benchmark_report_present", False)) else "local markdown evidence report missing",
            "artifact_path": "docs/process/v1x-evidence-report.md",
            "status": "passed" if bool(evidence_state.get("benchmark_report_present", False)) else "missing",
        },
    ]
    return {
        "available": True,
        "format": "agent_orchestrator.gate_evidence.v1",
        "log_policy": "large logs stay in artifact_path; setup and release readiness show summaries only",
        "gates": gates,
        "latest": gates[-1],
    }

def _release_readiness_commands() -> list[str]:
    return [
        "python -m agent_orchestrator.cli team check-compliance",
        "python -m agent_orchestrator.cli team refresh-docs",
        "python -m agent_orchestrator.cli evidence report --output docs/process/v1x-evidence-report.md",
        "pytest",
    ]


def _project_version() -> str:
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        return "unknown"
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    return "unknown"


def _build_setup_readiness(
    project_root: Path,
    health_snapshot: dict[str, object],
    doc_sync: dict[str, object],
    compliance: dict[str, object],
    *,
    role_profiles: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    providers = health_snapshot.get("providers", []) if isinstance(health_snapshot.get("providers"), list) else []
    provider_states = []
    for item in providers:
        if not isinstance(item, dict):
            continue
        provider_states.append(
            {
                "provider": item.get("provider"),
                "available": bool(item.get("available", False)),
                "binary": item.get("binary"),
                "recommended_fallback": item.get("recommended_fallback"),
                "detail": item.get("detail"),
            }
        )
    warnings = [str(item) for item in compliance.get("warnings", [])] if isinstance(compliance.get("warnings"), list) else []
    blocking_reasons = [str(item) for item in compliance.get("blocking_reasons", [])] if isinstance(compliance.get("blocking_reasons"), list) else []
    ready = not blocking_reasons and not warnings
    return {
        "project_root": str(project_root),
        "ready": ready,
        "provider_states": provider_states,
        "runtime_mode_states": _runtime_mode_contract(),
        "role_profiles": role_profiles or [],
        "masked_key_readiness": _masked_key_readiness(),
        "doc_sync_status": {
            "missing_docs": list(doc_sync.get("missing_docs", [])) if isinstance(doc_sync.get("missing_docs"), list) else [],
            "stale_docs": list(doc_sync.get("stale_docs", [])) if isinstance(doc_sync.get("stale_docs"), list) else [],
            "header_contract_violations": list(doc_sync.get("header_contract_violations", [])) if isinstance(doc_sync.get("header_contract_violations"), list) else [],
        },
        "compliance_status": {
            "blocking": bool(compliance.get("blocking", False)),
            "warnings": warnings,
            "blocking_reasons": blocking_reasons,
            "required_actions": list(compliance.get("required_actions", [])) if isinstance(compliance.get("required_actions"), list) else [],
            "recommended_commands": list(compliance.get("recommended_commands", [])) if isinstance(compliance.get("recommended_commands"), list) else [],
        },
    }


def _runtime_measurement_readiness(project_root: Path) -> dict[str, object]:
    jobs_root = project_root / ".agent_orchestrator" / "jobs"
    jobs = []
    if jobs_root.exists():
        for path in sorted(jobs_root.glob("job-*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(payload, dict):
                jobs.append(payload)
    measurements = [
        job.get("runtime_measurement", {})
        for job in jobs
        if isinstance(job.get("runtime_measurement", {}), dict)
    ]
    measured = [item for item in measurements if item.get("measurement_status") == "measured"]
    placeholder = [item for item in measurements if item.get("measurement_status") == "placeholder"]
    unavailable = [item for item in measurements if item.get("measurement_status") == "unavailable"]
    command_duration = [item for item in measurements if item.get("duration_seconds") is not None]
    degraded = [item for item in measurements if item.get("degraded_reason")]
    return {
        "format": "agent_orchestrator.runtime_measurement_readiness.v1",
        "measurement_surface_available": True,
        "job_count": len(jobs),
        "measurement_count": len(measurements),
        "measured_count": len(measured),
        "placeholder_count": len(placeholder),
        "unavailable_count": len(unavailable),
        "command_duration_available_count": len(command_duration),
        "degraded_runtime_count": len(degraded),
        "measurement_status": "measured" if measured else "placeholder" if placeholder or jobs else "unavailable",
        "rc_blocking": False,
        "rc_blockers": [],
        "policy": "runtime measurement is required as a surface; provider token/cost remains placeholder unless reported by runtime",
    }



def _masked_key_readiness() -> dict[str, object]:
    import os

    keys = {
        "openai": os.environ.get("OPENAI_API_KEY"),
        "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
    }
    return {
        provider: {
            "present": bool(value),
            "masked": _mask_secret(value) if value else None,
            "source": "env" if value else "missing",
        }
        for provider, value in keys.items()
    }


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "****"
    return f"{value[:3]}…{value[-4:]}"

def _role_profile_snapshot(agent_config: object) -> list[dict[str, object]]:
    profiles = getattr(agent_config, "profiles", {})
    if not isinstance(profiles, dict):
        return []
    return [
        {
            "role": role,
            "provider": profile.provider,
            "model": profile.model,
            "runtime_mode": profile.runtime_mode,
            "sandbox": profile.sandbox,
            "enabled": profile.enabled,
        }
        for role, profile in sorted(profiles.items())
    ]


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
    if primary_action == "mark_draft_ready":
        return (
            "python -m agent_orchestrator.cli team draft-ready "
            f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "submit_review":
        return (
            "python -m agent_orchestrator.cli team submit-review "
            f"{session_id} --plans-root {plans_root} --runs-root {runs_root}"
        )
    if primary_action == "lead_chat":
        return (
            "python -m agent_orchestrator.cli team chat "
            f"{session_id} --message \"clarify the plan\" --plans-root {plans_root} --runs-root {runs_root}"
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
