"""Formatting helpers for CLI session and execution output."""

from __future__ import annotations

# DEPS: __future__, json, typing
# RESPONSIBILITY: Format operator-facing CLI summaries without mutating orchestration state.
# MODULE: interface
# ---

import json
from typing import Any


def status_summary(payload: dict[str, object]) -> dict[str, object]:
    summary = payload.get("status_summary", {})
    return summary if isinstance(summary, dict) else {}


def blocker_summary(payload: dict[str, object]) -> dict[str, object]:
    summary = payload.get("blocker_summary", {})
    return summary if isinstance(summary, dict) else {}


def execution_session_summary(payload: dict[str, object]) -> dict[str, object]:
    summary = payload.get("session_summary", {})
    return summary if isinstance(summary, dict) else {}


def summary_list(summary: dict[str, object], key: str) -> list[object]:
    value = summary.get(key, [])
    return value if isinstance(value, list) else []


def summary_text(summary: dict[str, object], key: str, default: str = "") -> str:
    value = summary.get(key, default)
    return default if value is None else str(value)


def summary_bool(summary: dict[str, object], key: str, default: bool = False) -> bool:
    value = summary.get(key, default)
    return bool(value)


def summary_dict(summary: dict[str, object], key: str) -> dict[str, object]:
    value = summary.get(key, {})
    return value if isinstance(value, dict) else {}


def recovery_category(summary: dict[str, object]) -> str:
    semantics = summary_dict(summary, "recovery_semantics")
    category = summary_text(semantics, "category")
    if category:
        return category

    action = summary_text(summary, "resume_action") or summary_text(summary, "primary_action")
    block_source = summary_text(summary, "block_source")
    if action in {"retry_review", "retry_adversarial_review"}:
        return "retry"
    if action in {"approve", "execute"}:
        return "resume"
    if action == "human_decision":
        return "escalate"
    if block_source == "execution_run":
        return "inspect_before_rerun"
    recovery_actions = {str(action) for action in summary_list(summary, "recovery_actions")}
    if recovery_actions & {"retry_review", "retry_adversarial_review"}:
        return "retry"
    if "human_decision" in recovery_actions:
        return "escalate"
    if "inspect_execution" in recovery_actions and "inspect_blockers" in recovery_actions:
        return "inspect_before_rerun"
    if any(action.startswith("inspect_") for action in recovery_actions):
        return "inspect"
    if action in {"inspect_compliance", "inspect_blockers", "inspect_delegated_job", "inspect_execution"}:
        return "inspect"
    return ""


def recovery_action_description(action: str) -> str:
    descriptions = {
        "inspect_delegated_job": "inspect failed delegated job evidence",
        "retry_review": "retry delegated review",
        "retry_adversarial_review": "retry delegated adversarial review",
        "revise_plan": "revise plan or escalate manually if retry is unsafe",
        "revise": "revise plan and close required gaps",
        "approve": "resume by approving the reviewed plan",
        "execute": "resume by running approved execution",
        "inspect_execution": "inspect linked execution run before resume or re-run",
        "inspect_blockers": "inspect blockers before resume or re-run",
        "inspect_compliance": "inspect compliance blockers or warnings",
        "human_decision": "escalate for human decision",
        "wait_for_execution": "wait or inspect the linked run",
        "inspect_session": "inspect session state",
    }
    return descriptions.get(action, "inspect session state before continuing")


def recovery_guidance(summary: dict[str, object]) -> str:
    category = recovery_category(summary)
    recovery_actions = summary_list(summary, "recovery_actions")
    resume_action = summary_text(summary, "resume_action") or summary_text(summary, "primary_action")
    if not category and not recovery_actions and not resume_action:
        return ""

    mode_labels = {
        "inspect_before_rerun": "re-run",
        "retry": "retry",
        "resume": "resume",
        "escalate": "escalate",
        "inspect": "inspect",
        "scope_realign": "realign",
        "manual": "manual",
    }
    mode = mode_labels.get(category, category or "manual")
    parts = [f"mode={mode}"]
    if resume_action:
        parts.append(f"resume_action={resume_action}")
    resume_reason = summary_text(summary, "resume_reason")
    if resume_reason:
        parts.append(f"reason={resume_reason}")
    block_source = summary_text(summary, "block_source")
    block_detail = summary_text(summary, "block_detail")
    if block_source and block_detail:
        parts.append(f"block={block_source}/{block_detail}")
    elif block_source:
        parts.append(f"block={block_source}")

    semantics = summary_dict(summary, "recovery_semantics")
    if semantics:
        if "auto_apply_allowed" in semantics:
            parts.append(f"auto_apply={'yes' if summary_bool(semantics, 'auto_apply_allowed') else 'no'}")
        if summary_bool(semantics, "human_escalation_required"):
            parts.append("human_escalation_required=yes")
    elif category == "escalate":
        parts.append("human_escalation_required=yes")
    if category == "inspect_before_rerun":
        parts.append("inspect before re-running execution")
    return "; ".join(parts)


def recovery_steps(summary: dict[str, object]) -> str:
    actions = [str(action) for action in summary_list(summary, "recovery_actions")]
    if not actions and recovery_category(summary):
        action = summary_text(summary, "resume_action") or summary_text(summary, "primary_action")
        if action:
            actions = [action]
    if not actions:
        return ""
    return " -> ".join(f"{action}={recovery_action_description(action)}" for action in actions)


def print_recovery_details(
    summary: dict[str, object],
    *,
    include_commands: bool = False,
    include_resume: bool = True,
) -> None:
    resume_action = summary_text(summary, "resume_action")
    resume_reason = summary_text(summary, "resume_reason")
    if include_resume and resume_action:
        detail = f"resume: {resume_action}"
        if resume_reason:
            detail += f" (reason={resume_reason})"
        print(detail)

    guidance = recovery_guidance(summary)
    if guidance:
        print(f"recovery_guidance: {guidance}")
    steps = recovery_steps(summary)
    if steps:
        print(f"recovery_steps: {steps}")
    if include_commands:
        commands = summary_list(summary, "recommended_commands")
        if commands:
            print(f"recovery_commands: {' | '.join(str(command) for command in commands)}")


def print_recovery_timeline(status_summary: dict[str, object], *, prefix: str = "recovery_timeline") -> None:
    timeline = summary_dict(status_summary, "recovery_timeline")
    if not timeline:
        return
    current = summary_text(timeline, "current_status")
    entry_count = timeline.get("entry_count", 0)
    if current:
        print(f"{prefix}: current={current} entries={entry_count}")
    resume_hint = summary_text(timeline, "resume_hint")
    if resume_hint:
        print(f"{prefix}_resume_hint: {resume_hint}")
    blocking = summary_dict(timeline, "blocking_summary")
    if blocking:
        print(
            f"{prefix}_blocking: "
            f"{'yes' if summary_bool(blocking, 'blocking') else 'no'}"
        )


def print_strategy_decision(status: dict[str, object], *, prefix: str = "governance") -> None:
    strategy = summary_dict(status, "strategy_decision")
    if not strategy:
        return
    objective = (
        summary_text(strategy, "current_checkpoint_objective")
        or summary_text(strategy, "next_goal", "unknown")
    )
    print(f"{prefix}: {objective}")
    focus = summary_text(strategy, "control_plane_focus")
    if focus:
        print(f"{prefix}_focus: {focus}")
    action = summary_text(strategy, "recommended_action")
    if action:
        print(f"{prefix}_action: {action}")
    topology_policy = summary_dict(strategy, "topology_policy")
    if topology_policy:
        reason = summary_text(topology_policy, "selection_reason") or summary_text(strategy, "topology_reason")
        if reason:
            print(f"{prefix}_topology_policy: {reason}")
    recovery_policy = summary_dict(strategy, "recovery_policy")
    if recovery_policy:
        recovery_actions = summary_list(recovery_policy, "recovery_actions")
        if recovery_actions:
            print(f"{prefix}_recovery_policy: {' -> '.join(str(item) for item in recovery_actions)}")
    rationale = summary_list(strategy, "rationale")
    if rationale:
        print(f"{prefix}_rationale: {' | '.join(str(item) for item in rationale)}")
    risks = summary_list(strategy, "risks")
    if risks:
        print(f"{prefix}_risks: {' | '.join(str(item) for item in risks)}")
    verification = summary_list(strategy, "verification_requirements") or summary_list(strategy, "validation_plan")
    if verification:
        print(f"{prefix}_verification: {' | '.join(str(item) for item in verification)}")
    program_posture = summary_dict(strategy, "program_posture")
    if program_posture:
        print(
            f"{prefix}_program_posture: "
            f"goal={summary_text(program_posture, 'program_goal')} "
            f"active_milestone={summary_text(program_posture, 'active_milestone')} "
            f"ready_next_units={len(summary_list(program_posture, 'ready_next_units'))} "
            f"blocked_units={len(summary_list(program_posture, 'blocked_units'))}"
        )
    delegation_contract = summary_dict(strategy, "delegation_contract")
    if delegation_contract:
        print(
            f"{prefix}_delegation: "
            f"executor={summary_text(delegation_contract, 'selected_executor')} "
            f"boundary={summary_text(delegation_contract, 'ownership_boundary')} "
            f"handoff_reason={summary_text(delegation_contract, 'handoff_reason_code')} "
            f"fallback_reason={summary_text(delegation_contract, 'fallback_reason_code')}"
        )


def team_display_context(payload: dict[str, object], *, pick_primary_action: Any) -> dict[str, object]:
    summary = status_summary(payload)
    delegated_jobs = summary_list(summary, "delegated_jobs")
    failed_jobs = [
        job
        for job in delegated_jobs
        if isinstance(job, dict) and str(job.get("status")) == "failed"
    ]
    next_actions = [str(action) for action in summary_list(summary, "next_actions")]
    primary_action = summary_text(summary, "primary_action") or pick_primary_action(next_actions)
    primary_reason = summary_text(summary, "primary_reason") or summary_text(
        summary,
        "next_action_message",
        "inspect the current session state before continuing",
    )
    recommended_commands = [str(command) for command in summary_list(summary, "recommended_commands")]
    return {
        "status_summary": summary,
        "delegated_jobs": delegated_jobs,
        "failed_jobs": failed_jobs,
        "next_actions": next_actions,
        "primary_action": primary_action,
        "primary_reason": primary_reason,
        "recommended_commands": recommended_commands,
    }


def team_next_alternatives(status_summary: dict[str, object], primary_action: str) -> list[str]:
    recovery_actions = [str(action) for action in summary_list(status_summary, "recovery_actions")]
    return [action for action in recovery_actions if action != primary_action]


def pick_primary_action(actions: list[str]) -> str:
    priority = [
        "inspect_delegated_job",
        "inspect_compliance",
        "revise",
        "approve",
        "execute",
        "inspect_execution",
        "human_decision",
    ]
    for action in priority:
        if action in actions:
            return action
    return actions[0] if actions else "inspect_session"


def print_execution_session_summary(payload: dict[str, object]) -> None:
    summary = execution_session_summary(payload)
    if not summary:
        return
    print(f"session: {summary_text(summary, 'session_id')}")
    print(f"run: {summary_text(summary, 'run_id')}")
    print(f"execution_outcome: {summary_text(summary, 'outcome')}")
    goal = summary_text(summary, "goal")
    if goal:
        print(f"goal: {goal}")
    selected_topology = summary_text(summary, "selected_topology")
    if selected_topology:
        print(f"selected_topology: {selected_topology}")
    selected_provider_runtime = summary.get("selected_provider_runtime")
    if selected_provider_runtime:
        print(f"selected_provider_runtime: {json.dumps(selected_provider_runtime, ensure_ascii=False)}")
    clarify_summary = summary_dict(summary, "clarify_summary")
    if clarify_summary:
        print(_format_clarify_summary(clarify_summary))
    decomposition_summary = summary_dict(summary, "decomposition_summary")
    if decomposition_summary:
        print(_format_decomposition_summary(decomposition_summary))
    context_policy = summary.get("execution_context_policy")
    if isinstance(context_policy, dict) and context_policy:
        print(
            "execution_context_policy: "
            f"policy={context_policy.get('policy')} "
            f"resume_target={context_policy.get('resume_target')} "
            f"stop_reason={context_policy.get('stop_reason')}"
        )
    continuity = summary_dict(summary, "session_continuity")
    if continuity:
        print(
            "session_continuity: "
            f"resume_supported={continuity.get('resume_supported')} "
            f"resume_kind={continuity.get('resume_kind')} "
            f"compaction_stage={continuity.get('compaction_stage')} "
            f"runtime_duration_seconds={continuity.get('runtime_duration_seconds')} "
            f"usage_cost_status={continuity.get('usage_cost_measurement_status')}"
        )
    tool_usage = summary_dict(summary, "native_tool_usage")
    if tool_usage:
        recent = ",".join(str(item) for item in tool_usage.get("recent_tools", [])) if isinstance(tool_usage.get("recent_tools"), list) else ""
        print(
            "native_tool_usage: "
            f"tool_count={tool_usage.get('tool_count')} "
            f"trace_count={tool_usage.get('trace_count')} "
            f"recent={recent or 'none'}"
        )
    adapter_capability = summary_dict(summary, "adapter_capability")
    if adapter_capability:
        evidence_outputs = ",".join(str(item) for item in adapter_capability.get("evidence_outputs", [])) if isinstance(adapter_capability.get("evidence_outputs"), list) else ""
        recovery_surfaces = ",".join(str(item) for item in adapter_capability.get("recovery_surfaces", [])) if isinstance(adapter_capability.get("recovery_surfaces"), list) else ""
        print(
            "adapter_capability: "
            f"format={adapter_capability.get('format')} "
            f"comparison_mode={adapter_capability.get('comparison_mode')} "
            f"hot_plug_supported={adapter_capability.get('hot_plug_supported')} "
            f"evidence_outputs={evidence_outputs or 'none'} "
            f"recovery_surfaces={recovery_surfaces or 'none'}"
        )
    adapter_shared = summary_dict(summary, "adapter_shared_contract")
    if adapter_shared:
        evidence_outputs = ",".join(str(item) for item in adapter_shared.get("evidence_outputs", [])) if isinstance(adapter_shared.get("evidence_outputs"), list) else ""
        recovery_surfaces = ",".join(str(item) for item in adapter_shared.get("recovery_surfaces", [])) if isinstance(adapter_shared.get("recovery_surfaces"), list) else ""
        print(
            "adapter_shared_contract: "
            f"family={adapter_shared.get('adapter_family')} "
            f"kind={adapter_shared.get('agent_kind')} "
            f"default_path={adapter_shared.get('default_path')} "
            f"boundary={adapter_shared.get('operating_boundary')} "
            f"comparison_mode={adapter_shared.get('comparison_mode')} "
            f"hot_plug_supported={adapter_shared.get('hot_plug_supported')} "
            f"approval_required={adapter_shared.get('approval_required')} "
            f"evidence_outputs={evidence_outputs or 'none'} "
            f"recovery_surfaces={recovery_surfaces or 'none'}"
        )
    blocking_reasons = summary_list(summary, "blocking_reasons")
    if blocking_reasons:
        print(f"blocking: {'; '.join(str(reason) for reason in blocking_reasons)}")
    warnings = summary_list(summary, "warnings")
    if warnings:
        print(f"warnings: {'; '.join(str(reason) for reason in warnings)}")
    baseline_warnings = summary_list(summary, "baseline_warnings")
    if baseline_warnings:
        print(f"baseline_warnings: {'; '.join(str(reason) for reason in baseline_warnings)}")
    primary_action = summary_text(summary, "primary_action")
    if primary_action:
        print(f"primary_action: {primary_action}")
    primary_reason = summary_text(summary, "primary_reason")
    if primary_reason:
        print(f"primary_reason: {primary_reason}")
    print_recovery_details(summary, include_commands=False)
    recommended_commands = summary_list(summary, "recommended_commands")
    if recommended_commands:
        print(f"recommended_commands: {' | '.join(str(command) for command in recommended_commands)}")


def _format_clarify_summary(summary: dict[str, object]) -> str:
    task_type = summary_text(summary, "task_type", "unknown")
    slot_sources = summary_dict(summary, "slot_sources")
    slot_source_text = ",".join(f"{key}={value}" for key, value in sorted(slot_sources.items())) if slot_sources else "none"
    unknown_slots = summary_list(summary, "unknown_slots")
    unknown_text = ",".join(str(item) for item in unknown_slots) if unknown_slots else "none"
    warnings = summary_list(summary, "slot_fill_warnings")
    warning_text = "; ".join(str(item) for item in warnings) if warnings else "none"
    return (
        "clarify: "
        f"task_type={task_type} "
        f"slot_sources={slot_source_text} "
        f"unknown_slots={unknown_text} "
        f"warnings={warning_text}"
    )


def _format_decomposition_summary(summary: dict[str, object]) -> str:
    strategy = summary_text(summary, "selected_strategy", "unknown")
    shape = summary_text(summary, "selected_shape", "unknown")
    score = summary_text(summary, "selected_score", "unknown")
    candidate_count = summary_text(summary, "candidate_count", "0")
    rejected = summary_list(summary, "rejected_strategies")
    rejected_text = ",".join(str(item) for item in rejected) if rejected else "none"
    return (
        "decompose: "
        f"selected={strategy} "
        f"shape={shape} "
        f"score={score} "
        f"candidate_count={candidate_count} "
        f"rejected={rejected_text}"
    )


def print_blocker_session_summary(payload: dict[str, object]) -> None:
    summary = blocker_summary(payload)
    if not summary:
        return
    print(f"session: {summary_text(summary, 'session_id')}")
    print(f"session_status: {summary_text(summary, 'session_status')}")
    print(f"block_source: {summary_text(summary, 'block_source')}")
    block_detail = summary_text(summary, "block_detail")
    if block_detail:
        print(f"block_detail: {block_detail}")
    print(f"resume_action: {summary_text(summary, 'resume_action')}")
    print(f"resume_reason: {summary_text(summary, 'resume_reason')}")
    primary_reason = summary_text(summary, "primary_reason")
    if primary_reason:
        print(f"message: {primary_reason}")
    blocking_reasons = summary_list(summary, "blocking_reasons")
    if blocking_reasons:
        print(f"blocking: {'; '.join(str(reason) for reason in blocking_reasons)}")
    warnings = summary_list(summary, "warnings")
    if warnings:
        print(f"warnings: {'; '.join(str(reason) for reason in warnings)}")
    print_recovery_details(summary, include_commands=False, include_resume=False)
    baseline_warnings = summary_list(summary, "baseline_warnings")
    if baseline_warnings:
        print(f"baseline_warnings: {'; '.join(str(reason) for reason in baseline_warnings)}")
    recommended_commands = summary_list(summary, "recommended_commands")
    if recommended_commands:
        print(f"recommended_commands: {' | '.join(str(command) for command in recommended_commands)}")


def print_docs_context_summary(payload: dict[str, object]) -> None:
    print(f"docs_context: {payload.get('format', 'unknown')}")
    query = payload.get("query")
    if query:
        print(f"query: {query}")
    selected = payload.get("selected_doc_ids", [])
    if isinstance(selected, list):
        print(f"selected_docs: {', '.join(str(item) for item in selected) if selected else 'none'}")
    documents = payload.get("documents", [])
    if isinstance(documents, list):
        for document in documents:
            if not isinstance(document, dict):
                continue
            print(
                "doc: "
                f"{document.get('id')} "
                f"status={document.get('status')} "
                f"fresh={str(bool(document.get('fresh'))).lower()} "
                f"path={document.get('path')} "
                f"relevance={document.get('relevance')}"
            )
    doc_sync = payload.get("doc_sync")
    if isinstance(doc_sync, dict):
        missing = doc_sync.get("missing_docs", [])
        stale = doc_sync.get("stale_docs", [])
        if missing:
            print(f"missing_docs: {'; '.join(str(item) for item in missing)}")
        if stale:
            print(f"stale_docs: {len(stale)}")
    commands = payload.get("recommended_commands", [])
    if isinstance(commands, list) and commands:
        print(f"recommended_commands: {' | '.join(str(command) for command in commands)}")


def print_handoff_summary(payload: dict[str, object]) -> None:
    print(f"handoff: {payload.get('session_id')}")
    print(f"packet_count: {payload.get('packet_count', 0)}")
    latest = payload.get("latest_packet")
    if not isinstance(latest, dict):
        return
    packet = latest.get("packet")
    if not isinstance(packet, dict):
        return
    print(
        "latest_packet: "
        f"{packet.get('from_role')}->{packet.get('to_role')} "
        f"snapshot={packet.get('docs_context_snapshot_id') or 'none'}"
    )
    summary = packet.get("summary")
    if summary:
        print(f"summary: {summary}")
    commands = packet.get("recommended_commands", [])
    if isinstance(commands, list) and commands:
        print(f"recommended_commands: {' | '.join(str(command) for command in commands)}")


def print_docs_index_summary(payload: dict[str, object]) -> None:
    print(f"docs_index: {payload.get('format', 'unknown')}")
    query = payload.get("query")
    if query:
        print(f"query: {query}")
    docs = payload.get("matched_docs", [])
    decisions = payload.get("matched_decisions", [])
    tests = payload.get("matched_tests", [])
    print(
        "matches: "
        f"docs={len(docs) if isinstance(docs, list) else 0} "
        f"decisions={len(decisions) if isinstance(decisions, list) else 0} "
        f"tests={len(tests) if isinstance(tests, list) else 0}"
    )
    command = payload.get("recommended_context_command")
    if command:
        print(f"recommended_context_command: {command}")


def print_workspace_state_summary(payload: dict[str, object]) -> None:
    workspace_state = payload.get("workspace_state") if isinstance(payload.get("workspace_state"), dict) else payload
    print(f"workspace_state: {workspace_state.get('format', payload.get('format', 'unknown'))}")
    if payload.get("format") == "agent_orchestrator.workspace_index.v1":
        print(f"workspace_index: {payload.get('format')}")
    print(f"project_root: {workspace_state.get('project_root')}")
    plans = workspace_state.get("plans", [])
    runs = workspace_state.get("runs", [])
    jobs = workspace_state.get("jobs", [])
    approvals = workspace_state.get("approvals", [])
    print(
        "counts: "
        f"plans={len(plans) if isinstance(plans, list) else 0} "
        f"runs={len(runs) if isinstance(runs, list) else 0} "
        f"jobs={len(jobs) if isinstance(jobs, list) else 0} "
        f"approvals={len(approvals) if isinstance(approvals, list) else 0}"
    )
    dirty = workspace_state.get("dirty_state", {}) if isinstance(workspace_state.get("dirty_state"), dict) else {}
    print(f"dirty: {'yes' if dirty.get('dirty') else 'no'} count={dirty.get('count', 0)}")
    cache = workspace_state.get("external_cache", {}) if isinstance(workspace_state.get("external_cache"), dict) else {}
    print(f"external_cache: {cache.get('status', 'unknown')}")
    program = payload.get("program", {}) if isinstance(payload.get("program"), dict) else {}
    if program:
        print(
            "program: "
            f"name={program.get('name')} active_plans={program.get('active_plan_count', 0)} "
            f"open_approvals={program.get('open_approval_count', 0)}"
        )
    benchmark = payload.get("comparative_benchmark", {}) if isinstance(payload.get("comparative_benchmark"), dict) else {}
    if benchmark:
        shared = ",".join(str(item) for item in benchmark.get("shared_evidence_surface", [])) if isinstance(benchmark.get("shared_evidence_surface"), list) else ""
        print(
            "comparative_benchmark: "
            f"native_default={benchmark.get('native_default_path', False)} "
            f"acceptance_ready={benchmark.get('native_repo_task_acceptance_ready', False)} "
            f"complex_acceptance_ready={benchmark.get('native_complex_repo_task_acceptance_ready', False)} "
            f"task_class={benchmark.get('native_task_class')} "
            f"shared_surface={shared or 'none'}"
        )
    exploration = payload.get("native_exploration", {}) if isinstance(payload.get("native_exploration"), dict) else {}
    if exploration:
        selected = ",".join(str(item) for item in exploration.get("selected_candidates", [])) if isinstance(exploration.get("selected_candidates"), list) else ""
        print(
            "native_exploration: "
            f"existing={exploration.get('existing_path_count', 0)} "
            f"candidates={exploration.get('candidate_path_count', 0)} "
            f"files={exploration.get('file_count')} "
            f"repo_map_dirs={exploration.get('repo_map_directory_count')} "
            f"reason={exploration.get('candidate_reason')} "
            f"selected={selected or 'none'}"
        )
    evidence_summary = payload.get("execution_artifact_summary", {}) if isinstance(payload.get("execution_artifact_summary"), dict) else {}
    if evidence_summary:
        continuity = evidence_summary.get("session_continuity", {}) if isinstance(evidence_summary.get("session_continuity"), dict) else {}
        tool_usage = evidence_summary.get("native_tool_usage", {}) if isinstance(evidence_summary.get("native_tool_usage"), dict) else {}
        runtime_cost = evidence_summary.get("runtime_cost", {}) if isinstance(evidence_summary.get("runtime_cost"), dict) else {}
        planner_shared = evidence_summary.get("planner_shared_contract", {}) if isinstance(evidence_summary.get("planner_shared_contract"), dict) else {}
        adapter_shared = evidence_summary.get("adapter_shared_contract", {}) if isinstance(evidence_summary.get("adapter_shared_contract"), dict) else {}
        if continuity:
            print(
                "session_continuity: "
                f"resume_supported={continuity.get('resume_supported')} "
                f"compaction_stage={continuity.get('compaction_stage')} "
                f"summarization_triggered={continuity.get('summarization_triggered')} "
                f"resume_kind={continuity.get('resume_kind')}"
            )
            posture = continuity.get("long_horizon_posture", {}) if isinstance(continuity.get("long_horizon_posture"), dict) else {}
            if posture:
                print(
                    "long_horizon_posture: "
                    f"resume_ready={posture.get('resume_ready')} "
                    f"recovery_active={posture.get('recovery_active')} "
                    f"verification_resume_ready={posture.get('verification_resume_ready')} "
                    f"context_pressure={posture.get('context_pressure')} "
                    f"summarization_ready={posture.get('summarization_ready')}"
                )
            program_posture = continuity.get("program_posture", {}) if isinstance(continuity.get("program_posture"), dict) else {}
            if program_posture:
                completed = ",".join(str(item) for item in program_posture.get("completed_milestones", [])) if isinstance(program_posture.get("completed_milestones"), list) else ""
                ready = ",".join(str(item) for item in program_posture.get("ready_next_units", [])) if isinstance(program_posture.get("ready_next_units"), list) else ""
                blocked = ",".join(str(item) for item in program_posture.get("blocked_units", [])) if isinstance(program_posture.get("blocked_units"), list) else ""
                print(
                    "program_posture: "
                    f"goal={program_posture.get('program_goal')} "
                    f"active_milestone={program_posture.get('active_milestone')} "
                    f"completed={completed or 'none'} "
                    f"ready={ready or 'none'} "
                    f"blocked={blocked or 'none'}"
                )
            delegation_contract = continuity.get("delegation_contract", {}) if isinstance(continuity.get("delegation_contract"), dict) else {}
            if delegation_contract:
                required = ",".join(str(item) for item in delegation_contract.get("required_handoff_artifacts", [])) if isinstance(delegation_contract.get("required_handoff_artifacts"), list) else ""
                print(
                    "delegation_contract: "
                    f"executor={delegation_contract.get('selected_executor')} "
                    f"boundary={delegation_contract.get('ownership_boundary')} "
                    f"handoff_reason={delegation_contract.get('handoff_reason_code')} "
                    f"fallback_reason={delegation_contract.get('fallback_reason_code')} "
                    f"artifacts={required or 'none'}"
                )
            milestone_verification = continuity.get("milestone_verification", {}) if isinstance(continuity.get("milestone_verification"), dict) else {}
            if milestone_verification:
                remaining = ",".join(str(item) for item in milestone_verification.get("remaining_checks", [])) if isinstance(milestone_verification.get("remaining_checks"), list) else ""
                print(
                    "milestone_verification: "
                    f"status={milestone_verification.get('verification_status')} "
                    f"checkpoint_ready={milestone_verification.get('checkpoint_ready')} "
                    f"remaining={remaining or 'none'}"
                )
            operator_control = continuity.get("operator_control", {}) if isinstance(continuity.get("operator_control"), dict) else {}
            if operator_control:
                print(
                    "operator_control: "
                    f"next_action={operator_control.get('next_recommended_action')} "
                    f"recovery_lane={operator_control.get('runbook_recovery_lane')} "
                    f"approval_pause={operator_control.get('approval_pause_state')} "
                    f"clarify_pause={operator_control.get('clarify_pause_state')}"
                )
        if runtime_cost:
            print(
                "runtime_cost: "
                f"duration_seconds={runtime_cost.get('duration_seconds')} "
                f"usage_cost_status={runtime_cost.get('usage_cost_measurement_status')}"
            )
        if tool_usage:
            recent = ",".join(str(item) for item in tool_usage.get("recent_tools", [])) if isinstance(tool_usage.get("recent_tools"), list) else ""
            print(
                "native_tool_usage: "
                f"tool_count={tool_usage.get('tool_count')} "
                f"trace_count={tool_usage.get('trace_count')} "
                f"recent={recent or 'none'}"
            )
        if planner_shared:
            actions = ",".join(str(item) for item in planner_shared.get("selected_actions", [])) if isinstance(planner_shared.get("selected_actions"), list) else ""
            print(
                "planner_shared_contract: "
                f"family={planner_shared.get('planner_family')} "
                f"format={planner_shared.get('format')} "
                f"strategy={planner_shared.get('selected_strategy')} "
                f"owner={planner_shared.get('selected_owner')} "
                f"native_work_units={planner_shared.get('native_work_units')} "
                f"actions={actions or 'none'}"
            )
        if adapter_shared:
            evidence_outputs = ",".join(str(item) for item in adapter_shared.get("evidence_outputs", [])) if isinstance(adapter_shared.get("evidence_outputs"), list) else ""
            recovery_surfaces = ",".join(str(item) for item in adapter_shared.get("recovery_surfaces", [])) if isinstance(adapter_shared.get("recovery_surfaces"), list) else ""
            print(
                "adapter_shared_contract: "
                f"family={adapter_shared.get('adapter_family')} "
                f"kind={adapter_shared.get('agent_kind')} "
                f"default_path={adapter_shared.get('default_path')} "
                f"boundary={adapter_shared.get('operating_boundary')} "
                f"comparison_mode={adapter_shared.get('comparison_mode')} "
                f"hot_plug_supported={adapter_shared.get('hot_plug_supported')} "
                f"approval_required={adapter_shared.get('approval_required')} "
                f"evidence_outputs={evidence_outputs or 'none'} "
                f"recovery_surfaces={recovery_surfaces or 'none'}"
            )
    learning_consumption = payload.get("learning_consumption_ready")
    if learning_consumption is None and isinstance(evidence_summary, dict):
        learning_consumption = bool(evidence_summary.get("native_task_proof"))
    print(f"learning_consumption: {'yes' if learning_consumption else 'no'}")


def print_context_packet_summary(payload: dict[str, object]) -> None:
    print(f"context_packet: {payload.get('format', 'unknown')}")
    query = payload.get("query")
    if query:
        print(f"query: {query}")
    docs_context = payload.get("docs_context", {}) if isinstance(payload.get("docs_context"), dict) else {}
    selected = docs_context.get("selected_doc_ids", [])
    print(f"selected_docs: {', '.join(str(item) for item in selected) if isinstance(selected, list) and selected else 'none'}")
    memories = payload.get("memory_records", [])
    print(f"memory_records: {len(memories) if isinstance(memories, list) else 0}")
    warnings = payload.get("stale_warnings", [])
    if isinstance(warnings, list) and warnings:
        print(f"stale_warnings: {'; '.join(str(item) for item in warnings)}")


def print_provider_session_snapshot_summary(payload: dict[str, object]) -> None:
    print(f"provider_session_snapshot: {payload.get('format', 'unknown')}")
    print(f"job: {payload.get('job_id')} status={payload.get('status')} provider={payload.get('provider')}")
    liveness = payload.get("liveness", {}) if isinstance(payload.get("liveness"), dict) else {}
    print(
        "liveness: "
        f"state={liveness.get('state', 'unknown')} "
        f"terminal={liveness.get('terminal', False)} "
        f"last_seen={liveness.get('last_seen_at')}"
    )
    support = payload.get("operation_support", {}) if isinstance(payload.get("operation_support"), dict) else {}
    if support:
        print(
            "operation_support: "
            f"send={support.get('send')} cancel={support.get('cancel')} "
            f"attach={support.get('attach')} continue={support.get('continue')}"
        )
    receipt = payload.get("last_operation_receipt") if isinstance(payload.get("last_operation_receipt"), dict) else None
    if receipt:
        print(
            "last_receipt: "
            f"action={receipt.get('action')} status={receipt.get('status')} reason={receipt.get('reason')}"
        )
    command = payload.get("recommended_recovery_command")
    if command:
        print(f"recommended_recovery_command: {command}")


def print_topology_snapshot_summary(payload: dict[str, object]) -> None:
    print(f"topology_snapshot: {payload.get('format', 'unknown')}")
    print(f"session: {payload.get('session_id')}")
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    print(f"graph: nodes={len(nodes) if isinstance(nodes, list) else 0} edges={len(edges) if isinstance(edges, list) else 0}")
    strategy = payload.get("strategy_decision", {}) if isinstance(payload.get("strategy_decision"), dict) else {}
    checkpoint_objective = strategy.get("current_checkpoint_objective") or strategy.get("next_goal")
    if checkpoint_objective:
        print(f"current_checkpoint_objective: {checkpoint_objective}")
    approvals = payload.get("approval_queue", {}) if isinstance(payload.get("approval_queue"), dict) else {}
    counts = approvals.get("counts", {}) if isinstance(approvals.get("counts"), dict) else {}
    print(f"pending_approvals: {counts.get('pending', 0)}")


def print_approval_queue_summary(payload: dict[str, object]) -> None:
    print(f"approval_queue: {payload.get('format', 'unknown')}")
    counts = payload.get("counts", {}) if isinstance(payload.get("counts"), dict) else {}
    print(
        "counts: "
        f"pending={counts.get('pending', 0)} "
        f"approved={counts.get('approved', 0)} "
        f"rejected={counts.get('rejected', 0)} "
        f"resolved={counts.get('resolved', 0)}"
        )
    inbox = payload.get("inbox_summary", {}) if isinstance(payload.get("inbox_summary"), dict) else {}
    if inbox:
        print(
            "inbox: "
            f"pending={inbox.get('pending_count', 0)} "
            f"resolved={inbox.get('resolved_count', 0)} "
            f"blocking={inbox.get('blocking_count', 0)}"
        )
        command = inbox.get("recommended_next_command")
        if command:
            print(f"recommended_next_command: {command}")
    for item in payload.get("items", [])[:10]:
        if isinstance(item, dict):
            print(
                "approval: "
                f"{item.get('id')} code={item.get('reason_code')} status={item.get('status')} "
                f"scope={item.get('scope')} action={item.get('recommended_action')} "
                f"reason={item.get('reason')}"
            )
    grouped: dict[str, int] = {}
    for item in payload.get("items", []):
        if isinstance(item, dict):
            code = str(item.get("reason_code") or "unknown")
            grouped[code] = grouped.get(code, 0) + 1
    if grouped:
        print("reason_codes: " + " ".join(f"{code}={count}" for code, count in sorted(grouped.items())))


def print_approval_resolution_summary(payload: dict[str, object]) -> None:
    item = payload.get("resolved_item", {}) if isinstance(payload.get("resolved_item"), dict) else {}
    print(f"approval_resolved: {item.get('id')} status={item.get('status')}")
    reason = item.get("resolution_reason")
    if reason:
        print(f"reason: {reason}")
    print(f"mutation_policy: {payload.get('mutation_policy')}")


def print_evidence_bundle_summary(payload: dict[str, object]) -> None:
    print(f"evidence_bundle: {payload.get('format', 'unknown')}")
    print(f"status: {payload.get('status')}")
    gate = payload.get("gate_evidence", {}) if isinstance(payload.get("gate_evidence"), dict) else {}
    gates = gate.get("gates", []) if isinstance(gate.get("gates"), list) else []
    for item in gates:
        if isinstance(item, dict):
            print(f"gate: {item.get('name')} status={item.get('status')} command={item.get('command')}")


def print_team_summary(session: object, *, pick_primary_action: Any) -> None:
    payload = session.to_dict()
    context = team_display_context(payload, pick_primary_action=pick_primary_action)
    status = context["status_summary"]
    delegated_jobs = context["delegated_jobs"]
    failed_jobs = context["failed_jobs"]

    print(f"session: {payload.get('id')}")
    print(
        "status: "
        f"{payload.get('status')} "
        f"(phase={summary_text(status, 'phase', 'unknown')}, pending_role={summary_text(status, 'pending_role', 'unknown')})"
    )
    print(f"next: {context['primary_action']}")
    print(f"message: {context['primary_reason']}")
    topology_reason = summary_text(status, "topology_reason")
    if topology_reason:
        print(f"topology_reason: {topology_reason}")
    print_strategy_decision(status)

    blocking_reasons = summary_list(status, "blocking_reasons")
    if blocking_reasons:
        print(f"blocking: {'; '.join(str(reason) for reason in blocking_reasons)}")
    warnings = summary_list(status, "warnings")
    if warnings:
        print(f"warnings: {'; '.join(str(reason) for reason in warnings)}")
    baseline_warnings = summary_list(status, "baseline_warnings")
    if baseline_warnings:
        print(f"baseline_warnings: {'; '.join(str(reason) for reason in baseline_warnings)}")
    diagnostics = summary_dict(status, "diagnostics")
    if diagnostics:
        print(f"diagnostics: {summary_text(diagnostics, 'summary', 'none')}")

    recovery_actions = summary_list(status, "recovery_actions")
    if recovery_actions:
        print(f"recovery: {' -> '.join(str(action) for action in recovery_actions)}")
    recovery_provider = summary_text(status, "recovery_provider")
    recovery_round_type = summary_text(status, "recovery_round_type")
    recovery_provider_mode = summary_text(status, "recovery_provider_mode")
    recovery_fallback = summary_text(status, "recovery_provider_fallback_from")
    recovery_fallback_reason = summary_text(status, "recovery_provider_fallback_reason")
    recovery_fallback_detail = summary_text(status, "recovery_provider_fallback_detail")
    if recovery_provider and recovery_round_type:
        detail = f"recovery_provider: {recovery_provider} (round={recovery_round_type}"
        if recovery_provider_mode:
            detail += f", mode={recovery_provider_mode}"
        if recovery_fallback and recovery_fallback != recovery_provider:
            detail += f", fallback_from={recovery_fallback}"
        if recovery_fallback_reason:
            detail += f", fallback_reason={recovery_fallback_reason}"
        if recovery_fallback_detail:
            detail += f", fallback_detail={recovery_fallback_detail}"
        detail += ")"
        print(detail)
    print_recovery_details(status, include_commands=True)
    print_recovery_timeline(status)

    if failed_jobs:
        first_failed = failed_jobs[0]
        print(f"failed_job: {first_failed.get('provider')} {first_failed.get('job_id')}")
    elif delegated_jobs:
        print(f"delegated_jobs: {len(delegated_jobs)} completed")


def print_team_next(
    session: object,
    *,
    pick_primary_action: Any,
    build_team_next_command: Any,
    team_next_alternatives: Any,
    args: Any,
) -> None:
    payload = session.to_dict()
    context = team_display_context(payload, pick_primary_action=pick_primary_action)
    status = context["status_summary"]
    failed_jobs = context["failed_jobs"]
    primary_action = str(context["primary_action"])
    recommended_commands = [str(command) for command in context["recommended_commands"]]
    command = recommended_commands[0] if recommended_commands else build_team_next_command(payload, primary_action, failed_jobs, args)
    alternatives = team_next_alternatives(status, primary_action)
    delegated_failures = len(failed_jobs)

    print(f"session: {payload.get('id')}")
    print(f"action: {primary_action}")
    print(f"reason: {context['primary_reason']}")
    strategy = summary_dict(status, "strategy_decision")
    if strategy:
        objective = summary_text(strategy, "current_checkpoint_objective") or summary_text(strategy, "next_goal", context["primary_reason"])
        print(f"strategy_checkpoint_objective: {objective}")
    print(f"next_command: {command}")
    next_task = status.get("next_executable_task")
    if isinstance(next_task, dict):
        print(
            "next_task: "
            f"{next_task.get('id')} action={next_task.get('next_action')} title={next_task.get('title')}"
        )
    print_recovery_details(status, include_commands=True)
    print_recovery_timeline(status)
    if alternatives:
        print(f"alternatives: {', '.join(alternatives)}")
    else:
        print("alternatives: none")
    print(
        "context: "
        f"required_gaps={status.get('open_required_gaps', 0)} "
        f"optional_followups={status.get('open_optional_followups', 0)} "
        f"delegated_failures={delegated_failures}"
    )
    warnings = summary_list(status, "warnings")
    if warnings:
        print(f"warnings: {'; '.join(str(reason) for reason in warnings)}")
    baseline_warnings = summary_list(status, "baseline_warnings")
    if baseline_warnings:
        print(f"baseline_warnings: {'; '.join(str(reason) for reason in baseline_warnings)}")
    selected_topology = summary_text(status, "selected_topology")
    if selected_topology:
        print(f"selected_topology: {selected_topology}")
    topology_reason = summary_text(status, "topology_reason")
    if topology_reason:
        print(f"topology_reason: {topology_reason}")
    print_strategy_decision(status)


def print_team_runbook(
    session: object,
    *,
    pick_primary_action: Any,
    build_operator_runbook: Any,
) -> None:
    payload = session.to_dict()
    context = team_display_context(payload, pick_primary_action=pick_primary_action)
    status = context["status_summary"]
    runbook = build_operator_runbook(session)

    print(f"session: {payload.get('id')}")
    print(f"status: {payload.get('status')}")
    print(f"phase: {summary_text(status, 'phase', 'unknown')}")
    print(f"next: {context['primary_action']}")
    primary_reason = str(context["primary_reason"])
    if primary_reason:
        print(f"reason: {primary_reason}")
    recommended_commands = context["recommended_commands"]
    if recommended_commands:
        print(f"next_command: {recommended_commands[0]}")
    warnings = summary_list(status, "warnings")
    if warnings:
        print(f"warnings: {'; '.join(str(reason) for reason in warnings)}")
    baseline_warnings = summary_list(status, "baseline_warnings")
    if baseline_warnings:
        print(f"baseline_warnings: {'; '.join(str(reason) for reason in baseline_warnings)}")
    selected_topology = summary_text(status, "selected_topology")
    if selected_topology:
        print(f"selected_topology: {selected_topology}")
    topology_reason = summary_text(status, "topology_reason")
    if topology_reason:
        print(f"topology_reason: {topology_reason}")
    decision_rationale = summary_list(status, "decision_rationale")
    if decision_rationale:
        print(f"decision_rationale: {' | '.join(str(item) for item in decision_rationale)}")
    print_strategy_decision(status, prefix="control_plane_governance")
    print_recovery_timeline(status)
    print("operator_runbook:")
    for index, step in enumerate(runbook, start=1):
        print(f"{index}. {step}")
