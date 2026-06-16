"""Formatting helpers for CLI session and execution output."""

from __future__ import annotations

# DEPS: __future__, json, typing
# RESPONSIBILITY: Format operator-facing CLI summaries without mutating orchestration state.
# MODULE: interface
# ---

import json
from typing import Any

from agent_orchestrator.execution.models import derive_adapter_capability_summary, derive_adapter_productization_surface
from agent_orchestrator.productization_surface import (
    build_comparative_adapter_summary,
    build_comparative_completion_summary,
    build_comparative_daily_driver_summary,
    build_comparative_native_tool_summary,
    build_comparative_planner_candidate_summary,
    build_comparative_session_posture_summary,
    build_comparative_session_continuity_summary,
    build_comparative_daily_driver_benchmark,
    build_runtime_comparative_benchmark_digest,
    build_shared_productization_surface,
    derive_clarify_boundary_digest,
    derive_operator_planner_digest,
    derive_operator_tool_digest,
    derive_native_tool_productization_surface,
)
from agent_orchestrator.control_plane_posture import (
    derive_planner_closure_posture_summary,
    derive_session_continuity_outline_summary,
    derive_session_planner_decision_summary,
)
from agent_orchestrator.session.productization import derive_session_productization_surface

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


def _derived_planner_autonomy_surface(planner_shared: dict[str, object]) -> dict[str, object]:
    autonomy_surface = summary_dict(planner_shared, "autonomy_surface")
    if autonomy_surface:
        return autonomy_surface
    selected_actions = [str(item) for item in summary_list(planner_shared, "selected_actions")]
    if not selected_actions:
        return {}
    action_priority = {action: index for index, action in enumerate(selected_actions)}
    route_intent = summary_dict(planner_shared, "route_planner_intent")
    planner_family = summary_text(planner_shared, "planner_family", "native")
    return {
        "format": "agent_orchestrator.native_planner_autonomy_surface.v1"
        if planner_family == "native"
        else "agent_orchestrator.compatibility_planner_autonomy_surface.v1",
        "decision_mode": "native_first_autonomous" if planner_family == "native" else "compatibility_guided",
        "primary_action": selected_actions[0] if selected_actions else None,
        "selected_action_count": len(selected_actions),
        "actions": {
            "clarify": {"selected": "clarify" in selected_actions},
            "pause": {"selected": "approval_pause" in selected_actions or bool(route_intent.get("pause"))},
            "handoff": {"selected": "handoff_external" in selected_actions},
            "fallback": {"selected": "fallback_external" in selected_actions},
            "explore": {"selected": "explore" in selected_actions, "priority_index": action_priority.get("explore")},
            "edit": {"selected": "edit" in selected_actions, "priority_index": action_priority.get("edit")},
            "verify": {"selected": "verify" in selected_actions, "priority_index": action_priority.get("verify")},
        },
    }


def _derived_native_tool_productization_surface(
    native_tool_surface: dict[str, object],
    tool_usage: dict[str, object],
) -> dict[str, object]:
    surface = summary_dict(native_tool_surface, "tool_productization_surface")
    workflow_surface = summary_dict(native_tool_surface, "workflow_surface")
    if not workflow_surface:
        workflow_surface = {
            "explore": {
                "tools": ["repo_map", "search", "read"],
                "purpose": "bounded repository discovery and candidate scoping",
            },
            "edit": {
                "tools": ["patch_preview", "structured_patch", "diff_preview"],
                "purpose": "preview-first bounded mutation and diff review",
            },
            "verify": {
                "tools": ["verify", "tool_trace"],
                "purpose": "governed verification and trace-backed recovery",
            },
            "daily_driver_path": {
                "tools": [
                    "repo_map",
                    "search",
                    "read",
                    "patch_preview",
                    "structured_patch",
                    "diff_preview",
                    "verify",
                ],
                "purpose": "native-first repo task loop from exploration through verification",
            },
        }
    derived_surface = derive_native_tool_productization_surface(
        native_tool_surface={
            "daily_driver_readiness": summary_dict(native_tool_surface, "daily_driver_readiness"),
            "governance": summary_dict(native_tool_surface, "governance"),
            "tools": [object() for _ in range(int(tool_usage.get("tool_count", 0) or 0))],
        },
        native_tool_trace={
            "trace": [{"tool": item} for item in summary_list(tool_usage, "recent_tools")]
        },
        native_tool_productization_surface=surface,
    )
    if not surface:
        if "workflow_surface" not in derived_surface:
            derived_surface["workflow_surface"] = workflow_surface
        return derived_surface
    merged_surface = dict(surface)
    merged_surface["tool_count"] = surface.get("tool_count", derived_surface.get("tool_count"))
    merged_surface["trace_count"] = surface.get("trace_count", derived_surface.get("trace_count"))
    merged_surface["recent_tools"] = surface.get("recent_tools", summary_list(tool_usage, "recent_tools"))
    merged_surface["tooling_posture"] = surface.get("tooling_posture", derived_surface.get("tooling_posture"))
    merged_surface["operator_visibility_ready"] = surface.get(
        "operator_visibility_ready",
        derived_surface.get("operator_visibility_ready"),
    )
    merged_surface["usage_visibility_ready"] = surface.get(
        "usage_visibility_ready",
        derived_surface.get("usage_visibility_ready"),
    )
    merged_surface["readiness"] = {
        **summary_dict(derived_surface, "readiness"),
        **summary_dict(surface, "readiness"),
        "bounded_read_search_ready": summary_dict(surface, "readiness").get("bounded_read_search_ready")
        if "bounded_read_search_ready" in summary_dict(surface, "readiness")
        else summary_dict(derived_surface, "readiness").get("bounded_read_search_ready"),
        "glob_ready": summary_dict(surface, "readiness").get("glob_ready")
        if "glob_ready" in summary_dict(surface, "readiness")
        else summary_dict(derived_surface, "readiness").get("glob_ready"),
        "structured_patch_ready": summary_dict(surface, "readiness").get("structured_patch_ready")
        if "structured_patch_ready" in summary_dict(surface, "readiness")
        else summary_dict(derived_surface, "readiness").get("structured_patch_ready"),
    }
    if "workflow_surface" not in merged_surface:
        merged_surface["workflow_surface"] = workflow_surface
    if "shared_evidence_surface" not in merged_surface:
        merged_surface["shared_evidence_surface"] = derived_surface.get("shared_evidence_surface")
    return merged_surface


def _native_tool_readiness_with_fallback(source: dict[str, object]) -> dict[str, object]:
    readiness = summary_dict(source, "daily_driver_readiness") or summary_dict(source, "readiness")
    bounded_read_search_ready = readiness.get("bounded_read_search_ready")
    if bounded_read_search_ready is None:
        bounded_read_search_ready = readiness.get("repo_exploration_ready")
    glob_ready = readiness.get("glob_ready")
    if glob_ready is None:
        glob_ready = readiness.get("repo_exploration_ready")
    structured_patch_ready = readiness.get("structured_patch_ready")
    if structured_patch_ready is None:
        structured_patch_ready = readiness.get("patch_preview_ready")
    return {
        **readiness,
        "bounded_read_search_ready": bounded_read_search_ready,
        "glob_ready": glob_ready,
        "structured_patch_ready": structured_patch_ready,
    }


def _derived_adapter_productization_surface(
    adapter_shared: dict[str, object],
    adapter_capability: dict[str, object],
) -> dict[str, object]:
    surface = summary_dict(adapter_shared, "adapter_productization_surface")
    if surface:
        return surface
    normalized_shared = {
        **{
            "adapter_family": summary_text(adapter_capability, "adapter_family"),
            "agent_kind": summary_text(adapter_capability, "agent_kind"),
            "comparison_mode": summary_text(adapter_capability, "comparison_mode"),
            "hot_plug_supported": adapter_capability.get("hot_plug_supported"),
            "fallback_governed": adapter_capability.get("fallback_governed"),
            "approval_required": adapter_capability.get("approval_required"),
            "approval_pause_supported": adapter_capability.get("approval_pause_supported"),
            "recovery_contract": summary_dict(adapter_capability, "shared_contract_recovery_contract"),
            "shared_contract_format": summary_text(adapter_capability, "shared_contract_format"),
            "shared_contract_resume_supported": adapter_capability.get("shared_contract_resume_supported"),
        },
        **dict(adapter_shared),
    }
    if not summary_dict(normalized_shared, "recovery_contract"):
        normalized_shared["recovery_contract"] = summary_dict(
            adapter_capability,
            "shared_contract_recovery_contract",
        )
    if normalized_shared.get("fallback_governed") is None:
        normalized_shared["fallback_governed"] = adapter_capability.get("fallback_governed")
    if normalized_shared.get("hot_plug_supported") is None:
        normalized_shared["hot_plug_supported"] = adapter_capability.get("hot_plug_supported")
    if normalized_shared.get("shared_contract_resume_supported") is None:
        normalized_shared["shared_contract_resume_supported"] = adapter_capability.get(
            "shared_contract_resume_supported"
        )
    return derive_adapter_productization_surface(adapter_shared_contract=normalized_shared)
def recovery_category(summary: dict[str, object]) -> str:
    semantics = summary_dict(summary, "recovery_semantics")
    category = summary_text(semantics, "category")
    if category:
        return category

    action = summary_text(summary, "resume_action") or summary_text(summary, "primary_action")
    block_source = summary_text(summary, "block_source")
    resume_reason = summary_text(summary, "resume_reason")
    if action in {"retry_review", "retry_adversarial_review"}:
        return "retry"
    if action == "clarify" or resume_reason == "clarify_scope":
        return "scope_realign"
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
        "clarify": "clarify missing scope before resuming native execution",
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
        if "continue_allowed" in semantics:
            parts.append(f"continue_allowed={'yes' if summary_bool(semantics, 'continue_allowed') else 'no'}")
        if "scope_realign_required" in semantics and summary_bool(semantics, "scope_realign_required"):
            parts.append("scope_realign_required=yes")
        if "fallback_allowed" in semantics:
            parts.append(f"fallback_allowed={'yes' if summary_bool(semantics, 'fallback_allowed') else 'no'}")
        if "handoff_allowed" in semantics:
            parts.append(f"handoff_allowed={'yes' if summary_bool(semantics, 'handoff_allowed') else 'no'}")
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
    route_planner_intent = summary_dict(strategy, "route_planner_intent")
    if route_planner_intent:
        priority = ",".join(str(item) for item in summary_list(route_planner_intent, "priority"))
        print(
            f"{prefix}_planner_intent: "
            f"explore={summary_bool(route_planner_intent, 'explore')} "
            f"clarify={summary_bool(route_planner_intent, 'clarify')} "
            f"edit={summary_bool(route_planner_intent, 'edit')} "
            f"verify={summary_bool(route_planner_intent, 'verify')} "
            f"pause={summary_bool(route_planner_intent, 'pause')} "
            f"handoff={summary_bool(route_planner_intent, 'handoff')} "
            f"fallback={summary_bool(route_planner_intent, 'fallback')} "
            f"native_first={summary_bool(route_planner_intent, 'native_first')} "
            f"priority={priority or 'none'}"
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
    adapter_shared_contract = summary_dict(strategy, "adapter_shared_contract")
    if adapter_shared_contract:
        evidence_outputs = ",".join(str(item) for item in summary_list(adapter_shared_contract, "evidence_outputs"))
        recovery_surfaces = ",".join(str(item) for item in summary_list(adapter_shared_contract, "recovery_surfaces"))
        print(
            f"{prefix}_adapter_shared_contract: "
            f"format={summary_text(adapter_shared_contract, 'format')} "
            f"comparison_mode={summary_text(adapter_shared_contract, 'comparison_mode')} "
            f"default_path={summary_text(adapter_shared_contract, 'default_path')} "
            f"boundary={summary_text(adapter_shared_contract, 'operating_boundary')} "
            f"approval_required={summary_bool(adapter_shared_contract, 'approval_required')} "
            f"hot_plug_supported={summary_bool(adapter_shared_contract, 'hot_plug_supported')} "
            f"evidence_outputs={evidence_outputs or 'none'} "
            f"recovery_surfaces={recovery_surfaces or 'none'}"
        )
    program_continuity = summary_dict(strategy, "program_continuity")
    if program_continuity:
        print(
            f"{prefix}_program_continuity: "
            f"resume_supported={summary_bool(program_continuity, 'resume_supported')} "
            f"resume_kind={summary_text(program_continuity, 'resume_kind')} "
            f"continuity_status={summary_text(program_continuity, 'continuity_artifact_status')} "
            f"recovery_hint={summary_text(program_continuity, 'latest_recovery_hint')}"
        )
    milestone_verification = summary_dict(strategy, "milestone_verification")
    if milestone_verification:
        print(
            f"{prefix}_milestone_verification: "
            f"status={summary_text(milestone_verification, 'verification_status')} "
            f"checkpoint_ready={summary_bool(milestone_verification, 'checkpoint_ready')} "
            f"remaining_checks={len(summary_list(milestone_verification, 'remaining_checks'))}"
        )
    operator_control = summary_dict(strategy, "operator_control")
    if operator_control:
        print(
            f"{prefix}_operator_control: "
            f"next_action={summary_text(operator_control, 'next_recommended_action')} "
            f"recovery_lane={summary_text(operator_control, 'runbook_recovery_lane')} "
            f"approval_pause={summary_bool(operator_control, 'approval_pause_state')} "
            f"clarify_pause={summary_bool(operator_control, 'clarify_pause_state')}"
        )
    usage_cost = summary_dict(status, "usage_cost")
    if usage_cost:
        print(
            f"{prefix}_usage_cost: "
            f"measurement_status={summary_text(usage_cost, 'measurement_status')} "
            f"source={summary_text(usage_cost, 'source')}"
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
    tool_usage = summary_dict(summary, "native_tool_usage")
    tool_productization_surface = _derived_native_tool_productization_surface(
        summary_dict(summary, "native_tool_surface"),
        tool_usage,
    ) if tool_usage else {}
    native_tool_surface = summary_dict(summary, "native_tool_surface")
    planner_decision = summary_dict(summary, "session_planner_decision")
    planner_control_surface = summary_dict(summary, "planner_control_surface")
    continuity_outline = summary_dict(summary, "session_continuity_outline")
    planner_closure_posture = summary_dict(summary, "planner_closure_posture")
    adapter_productization_surface = _derived_adapter_productization_surface(
        summary_dict(summary, "adapter_shared_contract"),
        summary_dict(summary, "adapter_capability"),
    )
    if continuity:
        productization_surface = derive_session_productization_surface(continuity)
        print(
            "session_continuity: "
            f"resume_supported={continuity.get('resume_supported')} "
            f"resume_kind={continuity.get('resume_kind')} "
            f"compaction_stage={continuity.get('compaction_stage')} "
            f"runtime_duration_seconds={continuity.get('runtime_duration_seconds')} "
            f"usage_cost_status={continuity.get('usage_cost_measurement_status')}"
        )
        resume_contract = summary_dict(continuity, "resume_contract")
        if not resume_contract:
            operator_continuity = summary_dict(productization_surface, "operator_continuity")
            program_posture = summary_dict(continuity, "program_posture")
            resume_contract = {
                "resume_kind": continuity.get("resume_kind") or operator_continuity.get("resume_expectation"),
                "current_stage": program_posture.get("active_milestone"),
                "program_posture": program_posture,
                "native_tool_usage": tool_usage,
            }
        if resume_contract:
            recent = ",".join(str(item) for item in summary_list(summary_dict(resume_contract, "native_tool_usage"), "recent_tools"))
            print(
                "resume_contract: "
                f"resume_kind={resume_contract.get('resume_kind')} "
                f"stage={resume_contract.get('current_stage')} "
                f"step_id={resume_contract.get('current_step_id')} "
                f"active={summary_dict(resume_contract, 'program_posture').get('active_milestone')} "
                f"trace_count={summary_dict(resume_contract, 'native_tool_usage').get('trace_count')} "
                f"recent={recent or 'none'}"
            )
        if planner_decision:
            print(
                "session_planner_decision: "
                f"format={planner_decision.get('format')} "
                f"planner_family={planner_decision.get('planner_family')} "
                f"strategy={planner_decision.get('selected_execution_strategy')} "
                f"primary={planner_decision.get('primary_action')} "
                f"owner={planner_decision.get('selected_owner')} "
                f"candidates={planner_decision.get('candidate_count')} "
                f"governed_alternatives={len(planner_decision.get('planner_governed_alternatives', [])) if isinstance(planner_decision.get('planner_governed_alternatives'), list) else 0}"
                )
            autonomy_posture = summary_dict(planner_decision, "autonomy_posture")
            delegation_contract = summary_dict(planner_decision, "delegation_contract")
            tool_workflow_plan = summary_dict(planner_decision, "tool_workflow_plan")
            if autonomy_posture or delegation_contract:
                print(
                    "session_planner_posture: "
                    f"pause_expected={autonomy_posture.get('pause_expected')} "
                    f"handoff_expected={autonomy_posture.get('handoff_expected')} "
                    f"fallback_expected={autonomy_posture.get('fallback_expected')} "
                    f"clarify_pause={autonomy_posture.get('clarify_pause_state')} "
                    f"approval_pause={autonomy_posture.get('approval_pause_state')} "
                    f"resume_expectation={delegation_contract.get('resume_expectation')}"
                )
            if tool_workflow_plan:
                daily_driver = ",".join(str(item) for item in summary_list(summary_dict(tool_workflow_plan, "daily_driver_path"), "tools"))
                workflow_stages = summary_dict(tool_workflow_plan, "workflow_stages")
                print(
                    "session_planner_workflow: "
                    f"format={tool_workflow_plan.get('format')} "
                    f"projection_required={tool_workflow_plan.get('workflow_projection_required')} "
                    f"explore_selected={summary_dict(workflow_stages, 'explore').get('selected')} "
                    f"edit_selected={summary_dict(workflow_stages, 'edit').get('selected')} "
                    f"verify_selected={summary_dict(workflow_stages, 'verify').get('selected')} "
                    f"daily_driver={daily_driver or 'none'}"
                )
        if planner_control_surface:
            print(
                "session_planner_control_surface: "
                f"format={planner_control_surface.get('format')} "
                f"decision_mode={planner_control_surface.get('decision_mode')} "
                f"continue_native={planner_control_surface.get('continue_native')} "
                f"clarify={planner_control_surface.get('clarify')} "
                f"pause={planner_control_surface.get('pause')} "
                f"handoff={planner_control_surface.get('handoff')} "
                f"fallback={planner_control_surface.get('fallback')} "
                f"resume_posture={planner_control_surface.get('resume_posture')}"
            )
        if continuity_outline:
            print(
                "session_continuity_outline: "
                f"format={continuity_outline.get('format')} "
                f"planner_family={continuity_outline.get('planner_family')} "
                f"resume_kind={continuity_outline.get('resume_kind')} "
                f"goal={continuity_outline.get('goal')} "
                f"active={continuity_outline.get('active_milestone')} "
                f"next={continuity_outline.get('next_recommended_action')}"
            )
            outline_posture = summary_dict(continuity_outline, "autonomy_posture")
            if outline_posture or continuity_outline.get("resume_expectation") is not None:
                print(
                    "session_continuity_posture: "
                    f"pause_expected={outline_posture.get('pause_expected')} "
                    f"handoff_expected={outline_posture.get('handoff_expected')} "
                    f"fallback_expected={outline_posture.get('fallback_expected')} "
                    f"resume_expectation={continuity_outline.get('resume_expectation')}"
                )
        if not planner_closure_posture and (planner_decision or continuity):
            planner_closure_posture = derive_planner_closure_posture_summary(
                planner_decision=planner_decision,
                continuity=continuity,
            )
        if planner_closure_posture:
            print(
                "planner_closure_posture: "
                f"mode={planner_closure_posture.get('closure_mode')} "
                f"verify_selected={planner_closure_posture.get('verify_selected')} "
                f"verification_status={planner_closure_posture.get('verification_status')} "
                f"next_action={planner_closure_posture.get('next_recommended_action')} "
                f"resume_posture={planner_closure_posture.get('resume_posture')}"
            )
        continuity_snapshot = summary_dict(continuity, "continuity_snapshot")
        if continuity_snapshot:
            program_digest = summary_dict(continuity_snapshot, "program_digest")
            compaction_digest = summary_dict(continuity_snapshot, "compaction_digest")
            print(
                "continuity_snapshot: "
                f"status={continuity_snapshot.get('snapshot_status')} "
                f"artifact_backed={continuity_snapshot.get('artifact_backed')} "
                f"goal={program_digest.get('program_goal')} "
                f"active={program_digest.get('active_milestone')} "
                f"pending={program_digest.get('pending_followup_count')} "
                f"compaction={compaction_digest.get('compaction_stage')}"
            )
        daily_driver = summary_dict(continuity, "daily_driver_readiness")
        if daily_driver:
            print(
                "daily_driver_readiness: "
                f"tool_surface={daily_driver.get('tool_surface_ready')} "
                f"planner={daily_driver.get('planner_ready')} "
                f"session={daily_driver.get('session_ready')} "
                f"adapter={daily_driver.get('adapter_ready')} "
                f"shared_productization={daily_driver.get('shared_productization_ready')} "
                f"long_chain={daily_driver.get('long_chain_task_ready')} "
                f"main_path={daily_driver.get('daily_driver_main_path_ready')} "
                f"gap={daily_driver.get('open_product_gap')}"
            )
        if productization_surface:
            readiness = summary_dict(productization_surface, "continuity_readiness")
            operator_continuity = summary_dict(productization_surface, "operator_continuity")
            operator_posture_digest = summary_dict(productization_surface, "operator_posture_digest")
            shared_productization_surface = build_shared_productization_surface(
                session_productization_surface=productization_surface,
                native_tool_productization_surface=tool_productization_surface,
                native_tool_workflow_surface=summary_dict(tool_productization_surface, "workflow_surface")
                or summary_dict(native_tool_surface, "workflow_surface"),
                adapter_productization_surface=adapter_productization_surface,
                planner_decision=planner_decision,
                continuity_outline=continuity_outline,
                planner_closure_posture=planner_closure_posture,
                runtime_cost=summary_dict(continuity, "runtime_cost"),
                native_tool_usage=tool_usage,
                adapter_capability_surface=summary_dict(summary, "adapter_capability_surface"),
                comparative_shared_evidence_surface=summary_list(continuity, "shared_evidence_surface"),
            )
            print(
                "session_productization_surface: "
                f"format={productization_surface.get('format')} "
                f"status={productization_surface.get('continuity_status')} "
                f"resume_ready={readiness.get('resume_ready')} "
                f"runtime_cost_ready={readiness.get('runtime_cost_ready')} "
                f"compaction_ready={readiness.get('compaction_ready')} "
                f"recovery_ready={readiness.get('recovery_ready')} "
                f"next_action={operator_continuity.get('next_recommended_action')}"
            )
            comparative_digest = summary_dict(productization_surface, "comparative_benchmark_digest")
            if comparative_digest:
                print(
                    "session_comparative_digest: "
                    f"comparison_status={comparative_digest.get('comparison_status')} "
                    f"comparison_grade_status={comparative_digest.get('comparison_grade_status')} "
                    f"external_harness_status={comparative_digest.get('external_harness_status')} "
                    f"daily_driver_main_path_ready={comparative_digest.get('daily_driver_main_path_ready')}"
                )
            autonomy_posture = summary_dict(productization_surface, "autonomy_posture")
            if autonomy_posture:
                print(
                    "session_productization_posture: "
                    f"pause_expected={autonomy_posture.get('pause_expected')} "
                    f"handoff_expected={autonomy_posture.get('handoff_expected')} "
                    f"fallback_expected={autonomy_posture.get('fallback_expected')} "
                    f"resume_posture={autonomy_posture.get('resume_posture')}"
                )
            if operator_posture_digest:
                print(
                    "operator_posture_digest: "
                    f"status={operator_posture_digest.get('continuity_status') or productization_surface.get('continuity_status')} "
                    f"compaction_stage={operator_posture_digest.get('compaction_stage')} "
                    f"compaction_pressure={operator_posture_digest.get('compaction_pressure')} "
                    f"next_action={operator_posture_digest.get('next_recommended_action')} "
                    f"recovery_lane={operator_posture_digest.get('runbook_recovery_lane')} "
                    f"resume_expectation={operator_posture_digest.get('resume_expectation')} "
                    f"resume_posture={operator_posture_digest.get('resume_posture')} "
                    f"alternatives={','.join(str(item.get('action')) for item in operator_posture_digest.get('planner_governed_alternatives', []) if isinstance(item, dict) and item.get('action')) if isinstance(operator_posture_digest.get('planner_governed_alternatives'), list) and operator_posture_digest.get('planner_governed_alternatives') else 'none'}"
                )
            operator_planner_digest = derive_operator_planner_digest(
                planner_decision=planner_decision,
                planner_closure_posture=planner_closure_posture,
                continuity_outline=continuity,
            )
            if operator_planner_digest:
                print(
                    "operator_planner_digest: "
                    f"primary={operator_planner_digest.get('primary_action')} "
                    f"executor={operator_planner_digest.get('selected_executor')} "
                    f"mode={operator_planner_digest.get('closure_mode')} "
                    f"next_action={operator_planner_digest.get('next_recommended_action')} "
                    f"resume_expectation={operator_planner_digest.get('resume_expectation')} "
                    f"resume_posture={operator_planner_digest.get('resume_posture')} "
                    f"pause_expected={operator_planner_digest.get('pause_expected')} "
                    f"handoff_expected={operator_planner_digest.get('handoff_expected')} "
                    f"fallback_expected={operator_planner_digest.get('fallback_expected')} "
                    f"requires_confirmation={operator_planner_digest.get('requires_human_confirmation')}"
                )
            operator_tool_digest = derive_operator_tool_digest(
                native_tool_productization_surface=tool_productization_surface,
                native_tool_workflow_surface=summary_dict(tool_productization_surface, "workflow_surface")
                or summary_dict(native_tool_surface, "workflow_surface"),
            )
            if operator_tool_digest:
                print(
                    "operator_tool_digest: "
                    f"posture={operator_tool_digest.get('tooling_posture')} "
                    f"recent={','.join(str(item) for item in operator_tool_digest.get('recent_tools', [])) if isinstance(operator_tool_digest.get('recent_tools'), list) and operator_tool_digest.get('recent_tools') else 'none'} "
                    f"explore={','.join(str(item) for item in operator_tool_digest.get('explore_tools', [])) if isinstance(operator_tool_digest.get('explore_tools'), list) and operator_tool_digest.get('explore_tools') else 'none'} "
                    f"edit={','.join(str(item) for item in operator_tool_digest.get('edit_tools', [])) if isinstance(operator_tool_digest.get('edit_tools'), list) and operator_tool_digest.get('edit_tools') else 'none'} "
                    f"verify={','.join(str(item) for item in operator_tool_digest.get('verify_tools', [])) if isinstance(operator_tool_digest.get('verify_tools'), list) and operator_tool_digest.get('verify_tools') else 'none'}"
                )
            print(
                "shared_productization_surface: "
                f"format={shared_productization_surface.get('format')} "
                f"status={shared_productization_surface.get('surface_status')} "
                f"shared_ready={shared_productization_surface.get('shared_productization_contract_ready')} "
                f"session_ready={summary_dict(shared_productization_surface, 'contract_readiness').get('session_ready')} "
                f"tool_ready={summary_dict(shared_productization_surface, 'contract_readiness').get('tool_ready')} "
                f"adapter_ready={summary_dict(shared_productization_surface, 'contract_readiness').get('adapter_ready')} "
                f"planner_ready={summary_dict(shared_productization_surface, 'contract_readiness').get('planner_ready')}"
            )
    if tool_usage:
        recent = ",".join(str(item) for item in tool_usage.get("recent_tools", [])) if isinstance(tool_usage.get("recent_tools"), list) else ""
        print(
            "native_tool_usage: "
            f"tool_count={tool_usage.get('tool_count')} "
            f"trace_count={tool_usage.get('trace_count')} "
            f"recent={recent or 'none'}"
        )
        if tool_productization_surface:
            readiness = _native_tool_readiness_with_fallback(tool_productization_surface)
            print(
                "native_tool_productization_surface: "
                f"format={tool_productization_surface.get('format')} "
                f"posture={tool_productization_surface.get('tooling_posture')} "
                f"operator_visible={tool_productization_surface.get('operator_visibility_ready')} "
                f"read_search={readiness.get('bounded_read_search_ready')} "
                f"glob={readiness.get('glob_ready')} "
                f"patch={readiness.get('structured_patch_ready')} "
                f"verify={readiness.get('verification_ready')}"
            )
    if native_tool_surface:
        readiness = _native_tool_readiness_with_fallback(native_tool_surface)
        capability_profile = summary_dict(native_tool_surface, "capability_profile")
        workflow_surface = summary_dict(tool_productization_surface, "workflow_surface") or summary_dict(native_tool_surface, "workflow_surface")
        print(
            "native_tool_surface: "
            f"format={native_tool_surface.get('format')} "
            f"repo_exploration_ready={readiness.get('repo_exploration_ready')} "
            f"glob_ready={readiness.get('glob_ready')} "
            f"structured_patch_ready={readiness.get('structured_patch_ready')} "
            f"patch_preview_ready={readiness.get('patch_preview_ready')} "
            f"diff_preview_ready={readiness.get('diff_preview_ready')} "
            f"verification_ready={readiness.get('verification_ready')}"
        )
        if workflow_surface:
            daily_driver_path = summary_dict(workflow_surface, "daily_driver_path")
            workflow_surface_format = (
                summary_dict(tool_productization_surface, "format")
                or summary_dict(native_tool_surface, "workflow_surface").get("format")
                if isinstance(summary_dict(native_tool_surface, "workflow_surface"), dict)
                else None
            )
            print(
                "native_tool_workflow_surface: "
                f"format={workflow_surface_format}"
            )
            print(
                "native_tool_workflow: "
                f"explore={','.join(str(item) for item in summary_list(summary_dict(workflow_surface, 'explore'), 'tools')) or 'none'} "
                f"edit={','.join(str(item) for item in summary_list(summary_dict(workflow_surface, 'edit'), 'tools')) or 'none'} "
                f"verify={','.join(str(item) for item in summary_list(summary_dict(workflow_surface, 'verify'), 'tools')) or 'none'} "
                f"daily_driver={','.join(str(item) for item in summary_list(daily_driver_path, 'tools')) or 'none'}"
            )
        if capability_profile:
            patch_preview = summary_dict(capability_profile, "patch_preview")
            structured_patch = summary_dict(capability_profile, "structured_patch")
            diff_preview = summary_dict(capability_profile, "diff_preview")
            verify = summary_dict(capability_profile, "verify")
            print(
                "native_tool_capabilities: "
                f"patch_preview={patch_preview.get('purpose')} "
                f"structured_patch={structured_patch.get('purpose')} "
                f"diff_preview={diff_preview.get('purpose')} "
                f"verify={verify.get('purpose')}"
            )
    planner_shared = summary_dict(summary, "planner_shared_contract")
    if planner_shared:
        actions = ",".join(str(item) for item in planner_shared.get("selected_actions", [])) if isinstance(planner_shared.get("selected_actions"), list) else ""
        candidates = ",".join(str(item) for item in planner_shared.get("decision_candidates", [])) if isinstance(planner_shared.get("decision_candidates"), list) else ""
        route_intent = summary_dict(planner_shared, "route_planner_intent")
        decision_boundary = summary_dict(planner_shared, "decision_boundary")
        posture = summary_dict(planner_shared, "route_intent_alignment")
        autonomy_surface = _derived_planner_autonomy_surface(planner_shared)
        print(
            "planner_shared_contract: "
            f"family={planner_shared.get('planner_family')} "
            f"format={planner_shared.get('format')} "
            f"strategy={planner_shared.get('selected_strategy')} "
            f"owner={planner_shared.get('selected_owner')} "
            f"native_work_units={planner_shared.get('native_work_units')} "
            f"actions={actions or 'none'} "
            f"route_intent={','.join(str(item) for item in route_intent.get('priority', [])) if isinstance(route_intent.get('priority'), list) and route_intent.get('priority') else 'none'}"
        )
        print(
            "planner_decision_surface: "
            f"candidates={candidates or 'none'} "
            f"task_type={decision_boundary.get('task_type')} "
            f"risk={decision_boundary.get('risk_level')} "
            f"route_task_kind={decision_boundary.get('route_task_kind')} "
            f"requires_confirmation={decision_boundary.get('requires_human_confirmation')} "
            f"intent_alignment_explore={posture.get('explore')} "
            f"intent_alignment_verify={posture.get('verify')}"
        )
        if autonomy_surface:
            autonomy_actions = summary_dict(autonomy_surface, "actions")
            print(
                "planner_autonomy_surface: "
                f"format={autonomy_surface.get('format')} "
                f"mode={autonomy_surface.get('decision_mode')} "
                f"primary={autonomy_surface.get('primary_action')} "
                f"clarify={summary_dict(autonomy_actions, 'clarify').get('selected')} "
                f"pause={summary_dict(autonomy_actions, 'pause').get('selected')} "
                f"handoff={summary_dict(autonomy_actions, 'handoff').get('selected')} "
                f"fallback={summary_dict(autonomy_actions, 'fallback').get('selected')}"
            )
        autonomy_boundary = summary_dict(planner_shared, "autonomy_boundary")
        planner_reasoning = summary_dict(planner_shared, "planner_reasoning")
        if autonomy_boundary or planner_reasoning:
            print(
                "planner_autonomy_boundary: "
                f"native_first={planner_reasoning.get('native_first', autonomy_boundary.get('native_first'))} "
                f"clarify={autonomy_boundary.get('requires_clarify')} "
                f"pause={autonomy_boundary.get('requires_pause')} "
                f"handoff={autonomy_boundary.get('requires_handoff')} "
                f"fallback={autonomy_boundary.get('requires_fallback')} "
                f"explore={autonomy_boundary.get('requires_explore')} "
                f"edit={autonomy_boundary.get('requires_edit')} "
                f"verify={autonomy_boundary.get('requires_verify')}"
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
            f"recovery_surfaces={recovery_surfaces or 'none'} "
            f"shared_evidence_surface={','.join(str(item) for item in adapter_capability.get('shared_evidence_surface', [])) if isinstance(adapter_capability.get('shared_evidence_surface'), list) and adapter_capability.get('shared_evidence_surface') else 'none'}"
        )
        recovery_contract = summary_dict(adapter_capability, "shared_contract_recovery_contract")
        if recovery_contract:
            print(
                "adapter_recovery_contract: "
                f"continue_allowed={recovery_contract.get('continue_allowed')} "
                f"scope_realign_required={recovery_contract.get('scope_realign_required')} "
                f"fallback_allowed={recovery_contract.get('fallback_allowed')} "
                f"handoff_allowed={recovery_contract.get('handoff_allowed')} "
                f"remaining_budget_preserved={recovery_contract.get('remaining_budget_preserved')} "
                f"resume_continuity_required={recovery_contract.get('resume_continuity_required')}"
            )
    adapter_shared = summary_dict(summary, "adapter_shared_contract")
    if adapter_shared:
        adapter_productization_surface = _derived_adapter_productization_surface(
            adapter_shared,
            adapter_capability,
        )
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
        print(
            "adapter_shared_contract_surface: "
            f"shared_contract_format={adapter_shared.get('shared_contract_format')} "
            f"shared_contract_resume_supported={adapter_shared.get('shared_contract_resume_supported')} "
            f"fallback_governed={adapter_shared.get('fallback_governed')}"
        )
        print(
            "adapter_productization_surface: "
            f"format={adapter_productization_surface.get('format')} "
            f"status={adapter_productization_surface.get('surface_status')} "
            f"comparison_mode={adapter_productization_surface.get('comparison_mode')} "
            f"hot_plug_supported={adapter_productization_surface.get('hot_plug_supported')} "
            f"fallback_governed={adapter_productization_surface.get('fallback_governed')} "
            f"resume_supported={adapter_productization_surface.get('resume_contract_supported')} "
            f"recovery_ready={adapter_productization_surface.get('governed_recovery_ready')}"
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
    evidence = summary_dict(summary, "evidence")
    clarify_pause = summary_dict(evidence, "clarify_pause")
    if clarify_pause:
        print(
            "clarify_boundary: "
            f"strategy={summary_text(clarify_pause, 'selected_strategy', 'clarify_then_edit')} "
            f"source={summary_text(clarify_pause, 'pause_reason', 'planner_control_surface')} "
            f"next={summary_text(clarify_pause, 'next_action', 'clarify')}"
        )
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
        alignment = benchmark.get("shared_contract_alignment", {}) if isinstance(benchmark.get("shared_contract_alignment"), dict) else {}
        print(
            "comparative_benchmark: "
            f"native_default={benchmark.get('native_default_path', False)} "
            f"bundle_ready={benchmark.get('comparative_acceptance_bundle_ready', False)} "
            f"acceptance_ready={benchmark.get('native_repo_task_acceptance_ready', False)} "
            f"complex_acceptance_ready={benchmark.get('native_complex_repo_task_acceptance_ready', False)} "
            f"long_chain_ready={benchmark.get('long_chain_native_first_ready', False)} "
            f"daily_driver_ready={benchmark.get('daily_driver_main_path_ready', False)} "
            f"task_class={benchmark.get('native_task_class')} "
            f"coverage_class={benchmark.get('native_coverage_class')} "
            f"learning_consumed={benchmark.get('learning_consumed', False)} "
            f"shared_surface={shared or 'none'}"
        )
        if alignment:
            print(
                "comparative_contract_alignment: "
                f"session={alignment.get('session_continuity_ready')} "
                f"runtime_cost={alignment.get('runtime_cost_ready')} "
                f"tool_usage={alignment.get('native_tool_usage_ready')} "
                f"planner={alignment.get('planner_evidence_ready')} "
                f"adapter={alignment.get('adapter_contract_ready')}"
            )
        print(
            f"comparative_shared_productization_contract_ready: {benchmark.get('shared_productization_contract_ready')}"
        )
    benchmark_digest = (
        payload.get("comparative_benchmark_digest", {})
        if isinstance(payload.get("comparative_benchmark_digest"), dict)
        else {}
    )
    if not benchmark_digest and benchmark:
        benchmark_digest = build_runtime_comparative_benchmark_digest(benchmark)
        if benchmark_digest:
            shared = ",".join(str(item) for item in benchmark_digest.get("shared_evidence_surface", [])) if isinstance(benchmark_digest.get("shared_evidence_surface"), list) else ""
            remaining = ",".join(str(item) for item in benchmark_digest.get("remaining_gap_classes", [])) if isinstance(benchmark_digest.get("remaining_gap_classes"), list) else ""
        print(
            "comparative_benchmark_digest: "
            f"cases={benchmark_digest.get('case_count')} "
            f"productization_cases={benchmark_digest.get('productization_case_count')} "
            f"comparison_status={benchmark_digest.get('comparison_status')} "
            f"direct_proof={benchmark_digest.get('direct_proof_status')} "
            f"repeatability={benchmark_digest.get('repeatability_status')} "
            f"daily_driver_repeatability_tier={benchmark_digest.get('daily_driver_repeatability_tier')} "
            f"daily_driver_cases={benchmark_digest.get('daily_driver_main_path_ready_cases')} "
            f"comparison_grade_status={benchmark_digest.get('comparison_grade_status')} "
            f"external_harness_status={benchmark_digest.get('external_harness_status')} "
            f"required_shared_surface_count={benchmark_digest.get('external_harness_required_shared_surface_count')} "
            f"required_external_artifact_count={benchmark_digest.get('external_harness_required_external_artifact_count')} "
            f"missing_external_artifact_count={benchmark_digest.get('external_harness_missing_external_artifact_count')} "
            f"session_posture_cases={benchmark_digest.get('session_posture_cases')} "
                f"remaining_gaps={remaining or 'none'} "
                f"shared_surface={shared or 'none'}"
            )
        if (
            benchmark_digest.get("operator_posture_next_recommended_action") is not None
            or benchmark_digest.get("operator_posture_resume_expectation") is not None
            or benchmark_digest.get("operator_posture_resume_posture") is not None
        ):
            print(
                "comparative_operator_posture_digest: "
                f"next_action={benchmark_digest.get('operator_posture_next_recommended_action')} "
                f"recovery_lane={benchmark_digest.get('operator_posture_recovery_lane')} "
                f"resume_expectation={benchmark_digest.get('operator_posture_resume_expectation')} "
                f"resume_posture={benchmark_digest.get('operator_posture_resume_posture')} "
                f"approval_boundary_active={benchmark_digest.get('operator_posture_approval_boundary_active')} "
                f"compaction_stage={benchmark_digest.get('operator_posture_compaction_stage')} "
                f"compaction_pressure={benchmark_digest.get('operator_posture_compaction_pressure')} "
                f"alternatives={','.join(str(item.get('action')) for item in benchmark_digest.get('operator_posture_governed_alternatives', []) if isinstance(item, dict) and item.get('action')) if isinstance(benchmark_digest.get('operator_posture_governed_alternatives'), list) and benchmark_digest.get('operator_posture_governed_alternatives') else 'none'}"
            )
        operator_tool_digest = summary_dict(benchmark, "operator_tool_digest")
        if not operator_tool_digest:
            operator_tool_digest = derive_operator_tool_digest(
                native_tool_productization_surface=summary_dict(benchmark, "native_tool_productization_surface"),
                native_tool_workflow_surface=summary_dict(benchmark, "native_tool_workflow_surface"),
            )
        if operator_tool_digest:
            print(
                "comparative_operator_tool_digest: "
                f"posture={operator_tool_digest.get('tooling_posture')} "
                f"recent={','.join(str(item) for item in operator_tool_digest.get('recent_tools', [])) if isinstance(operator_tool_digest.get('recent_tools'), list) and operator_tool_digest.get('recent_tools') else 'none'} "
                f"explore={','.join(str(item) for item in operator_tool_digest.get('explore_tools', [])) if isinstance(operator_tool_digest.get('explore_tools'), list) and operator_tool_digest.get('explore_tools') else 'none'} "
                f"edit={','.join(str(item) for item in operator_tool_digest.get('edit_tools', [])) if isinstance(operator_tool_digest.get('edit_tools'), list) and operator_tool_digest.get('edit_tools') else 'none'} "
                f"verify={','.join(str(item) for item in operator_tool_digest.get('verify_tools', [])) if isinstance(operator_tool_digest.get('verify_tools'), list) and operator_tool_digest.get('verify_tools') else 'none'}"
            )
        operator_planner_digest = summary_dict(benchmark, "operator_planner_digest")
        if operator_planner_digest:
            print(
                "comparative_operator_planner_digest: "
                f"primary={operator_planner_digest.get('primary_action')} "
                f"executor={operator_planner_digest.get('selected_executor')} "
                f"mode={operator_planner_digest.get('closure_mode')} "
                f"next_action={operator_planner_digest.get('next_recommended_action')} "
                f"resume_expectation={operator_planner_digest.get('resume_expectation')} "
                f"resume_posture={operator_planner_digest.get('resume_posture')} "
                f"pause_expected={operator_planner_digest.get('pause_expected')} "
                f"handoff_expected={operator_planner_digest.get('handoff_expected')} "
                f"fallback_expected={operator_planner_digest.get('fallback_expected')} "
                f"requires_confirmation={operator_planner_digest.get('requires_human_confirmation')} "
                f"decision_mode={operator_planner_digest.get('decision_mode')} "
                f"candidates={operator_planner_digest.get('candidate_count')} "
                f"governed_alternatives={operator_planner_digest.get('governed_alternative_count')} "
                f"autonomy_actions={','.join(str(item) for item in operator_planner_digest.get('autonomy_selected_actions', [])) if isinstance(operator_planner_digest.get('autonomy_selected_actions'), list) and operator_planner_digest.get('autonomy_selected_actions') else 'none'}"
            )
        comparative_planner_autonomy_summary = (
            benchmark.get("comparative_planner_autonomy_summary", {})
            if isinstance(benchmark.get("comparative_planner_autonomy_summary"), dict)
            else {}
        )
        if comparative_planner_autonomy_summary:
            autonomy_boundary = summary_dict(comparative_planner_autonomy_summary, "autonomy_boundary")
            print(
                "comparative_planner_autonomy_summary: "
                f"native_first={comparative_planner_autonomy_summary.get('native_first')} "
                f"primary={comparative_planner_autonomy_summary.get('primary_action')} "
                f"clarify={autonomy_boundary.get('requires_clarify')} "
                f"pause={autonomy_boundary.get('requires_pause')} "
                f"handoff={autonomy_boundary.get('requires_handoff')} "
                f"fallback={autonomy_boundary.get('requires_fallback')} "
                f"explore={autonomy_boundary.get('requires_explore')} "
                f"edit={autonomy_boundary.get('requires_edit')} "
                f"verify={autonomy_boundary.get('requires_verify')} "
                f"next_action={comparative_planner_autonomy_summary.get('next_recommended_action')}"
            )
        proof_strength = benchmark.get("comparison_proof_strength", {}) if isinstance(benchmark.get("comparison_proof_strength"), dict) else {}
        if benchmark_digest.get("planner_closure_mode") or benchmark_digest.get("planner_next_recommended_action"):
            print(
                "comparative_planner_closure: "
                f"mode={benchmark_digest.get('planner_closure_mode')} "
                f"next_action={benchmark_digest.get('planner_next_recommended_action')} "
                f"resume_posture={benchmark_digest.get('planner_resume_posture')} "
                f"verify_selected={benchmark_digest.get('planner_verify_selected')} "
                f"verification_status={benchmark_digest.get('planner_verification_status')}"
            )
        comparative_native_tool_summary = (
            payload.get("comparative_native_tool_summary", {})
            if isinstance(payload.get("comparative_native_tool_summary"), dict)
            else benchmark.get("comparative_native_tool_summary", {})
            if isinstance(benchmark.get("comparative_native_tool_summary"), dict)
            else {}
        )
        if not comparative_native_tool_summary:
            fallback_tool_surface = (
                payload.get("native_tool_surface", {})
                if isinstance(payload.get("native_tool_surface"), dict)
                else payload.get("execution_artifact_summary", {}).get("native_tool_surface", {})
                if isinstance(payload.get("execution_artifact_summary"), dict)
                and isinstance(payload.get("execution_artifact_summary", {}).get("native_tool_surface"), dict)
                else {}
            )
            fallback_tool_usage = (
                payload.get("native_tool_usage", {})
                if isinstance(payload.get("native_tool_usage"), dict)
                else payload.get("execution_artifact_summary", {}).get("native_tool_usage", {})
                if isinstance(payload.get("execution_artifact_summary"), dict)
                and isinstance(payload.get("execution_artifact_summary", {}).get("native_tool_usage"), dict)
                else {}
            )
            fallback_tool_productization_surface = _derived_native_tool_productization_surface(
                fallback_tool_surface,
                fallback_tool_usage,
            )
            comparative_native_tool_summary = build_comparative_native_tool_summary(
                native_tool_productization_surface=(
                    payload.get("native_tool_productization_surface", {})
                    if isinstance(payload.get("native_tool_productization_surface"), dict)
                    else payload.get("execution_artifact_summary", {}).get("native_tool_productization_surface", {})
                    if isinstance(payload.get("execution_artifact_summary"), dict)
                    and isinstance(payload.get("execution_artifact_summary", {}).get("native_tool_productization_surface"), dict)
                    else fallback_tool_productization_surface
                ),
                native_tool_workflow_surface=(
                    payload.get("native_tool_workflow_surface", {})
                    if isinstance(payload.get("native_tool_workflow_surface"), dict)
                    else payload.get("execution_artifact_summary", {}).get("native_tool_workflow_surface", {})
                    if isinstance(payload.get("execution_artifact_summary"), dict)
                    and isinstance(payload.get("execution_artifact_summary", {}).get("native_tool_workflow_surface"), dict)
                    else summary_dict(fallback_tool_productization_surface, "workflow_surface")
                ),
            )
        if comparative_native_tool_summary:
            print(
                "comparative_native_tool_summary: "
                f"posture={comparative_native_tool_summary.get('tooling_posture')} "
                f"read_search={comparative_native_tool_summary.get('bounded_read_search_ready')} "
                f"patch={comparative_native_tool_summary.get('structured_patch_ready')} "
                f"verify={comparative_native_tool_summary.get('verification_ready')} "
                f"daily_driver={','.join(str(item) for item in comparative_native_tool_summary.get('daily_driver_tools', [])) if isinstance(comparative_native_tool_summary.get('daily_driver_tools'), list) and comparative_native_tool_summary.get('daily_driver_tools') else 'none'}"
            )
        comparative_adapter_summary = (
            payload.get("comparative_adapter_summary", {})
            if isinstance(payload.get("comparative_adapter_summary"), dict)
            else benchmark.get("comparative_adapter_summary", {})
            if isinstance(benchmark.get("comparative_adapter_summary"), dict)
            else {}
        )
        if not comparative_adapter_summary:
            fallback_adapter_shared_contract = (
                payload.get("adapter_shared_contract", {})
                if isinstance(payload.get("adapter_shared_contract"), dict)
                else payload.get("execution_artifact_summary", {}).get("adapter_shared_contract", {})
                if isinstance(payload.get("execution_artifact_summary"), dict)
                and isinstance(payload.get("execution_artifact_summary", {}).get("adapter_shared_contract"), dict)
                else {}
            )
            fallback_adapter_capability_surface = (
                payload.get("adapter_capability_surface", {})
                if isinstance(payload.get("adapter_capability_surface"), dict)
                else payload.get("adapter_capability", {})
                if isinstance(payload.get("adapter_capability"), dict)
                else payload.get("execution_artifact_summary", {}).get("adapter_capability_surface", {})
                if isinstance(payload.get("execution_artifact_summary"), dict)
                and isinstance(payload.get("execution_artifact_summary", {}).get("adapter_capability_surface"), dict)
                else payload.get("execution_artifact_summary", {}).get("adapter_capability", {})
                if isinstance(payload.get("execution_artifact_summary"), dict)
                and isinstance(payload.get("execution_artifact_summary", {}).get("adapter_capability"), dict)
                else {}
            )
            fallback_adapter_productization_surface = (
                payload.get("adapter_productization_surface", {})
                if isinstance(payload.get("adapter_productization_surface"), dict)
                else payload.get("execution_artifact_summary", {}).get("adapter_productization_surface", {})
                if isinstance(payload.get("execution_artifact_summary"), dict)
                and isinstance(payload.get("execution_artifact_summary", {}).get("adapter_productization_surface"), dict)
                else derive_adapter_productization_surface(
                    adapter_shared_contract=fallback_adapter_shared_contract,
                )
            )
            comparative_adapter_summary = build_comparative_adapter_summary(
                adapter_productization_surface=fallback_adapter_productization_surface,
                adapter_shared_contract=fallback_adapter_shared_contract,
                adapter_capability_surface=(
                    fallback_adapter_capability_surface
                    or derive_adapter_capability_summary(
                        adapter_capability_surface=fallback_adapter_capability_surface,
                    )
                ),
            )
        if comparative_adapter_summary:
            print(
                "comparative_adapter_summary: "
                f"status={comparative_adapter_summary.get('surface_status')} "
                f"comparison_mode={comparative_adapter_summary.get('comparison_mode')} "
                f"hot_plug={comparative_adapter_summary.get('hot_plug_supported')} "
                f"fallback_governed={comparative_adapter_summary.get('fallback_governed')} "
                f"resume_supported={comparative_adapter_summary.get('resume_contract_supported')} "
                f"recovery_ready={comparative_adapter_summary.get('governed_recovery_ready')} "
                f"default_path={comparative_adapter_summary.get('default_path')} "
                f"boundary={comparative_adapter_summary.get('ownership_boundary')} "
                f"unified_contract={comparative_adapter_summary.get('unified_adapter_contract_ready')}"
            )
        adapter_capability = (
            payload.get("adapter_capability", {})
            if isinstance(payload.get("adapter_capability"), dict)
            else payload.get("execution_artifact_summary", {}).get("adapter_capability", {})
            if isinstance(payload.get("execution_artifact_summary"), dict)
            and isinstance(payload.get("execution_artifact_summary", {}).get("adapter_capability"), dict)
            else {}
        )
        if adapter_capability:
            evidence_outputs = ",".join(str(item) for item in adapter_capability.get("evidence_outputs", [])) if isinstance(adapter_capability.get("evidence_outputs"), list) else ""
            recovery_surfaces = ",".join(str(item) for item in adapter_capability.get("recovery_surfaces", [])) if isinstance(adapter_capability.get("recovery_surfaces"), list) else ""
            shared_evidence_surface = ",".join(str(item) for item in adapter_capability.get("shared_evidence_surface", [])) if isinstance(adapter_capability.get("shared_evidence_surface"), list) else ""
            print(
                "adapter_capability: "
                f"format={adapter_capability.get('format')} "
                f"comparison_mode={adapter_capability.get('comparison_mode')} "
                f"hot_plug_supported={adapter_capability.get('hot_plug_supported')} "
                f"evidence_outputs={evidence_outputs or 'none'} "
                f"recovery_surfaces={recovery_surfaces or 'none'} "
                f"shared_evidence_surface={shared_evidence_surface or 'none'}"
            )
        continuity = (
            payload.get("execution_artifact_summary", {}).get("session_continuity", {})
            if isinstance(payload.get("execution_artifact_summary"), dict)
            and isinstance(payload.get("execution_artifact_summary", {}).get("session_continuity"), dict)
            else {}
        )
        fallback_planner_decision = (
            payload.get("session_planner_decision", {})
            if isinstance(payload.get("session_planner_decision"), dict)
            else payload.get("planner_decision", {})
            if isinstance(payload.get("planner_decision"), dict)
            else payload.get("execution_artifact_summary", {}).get("planner_decision", {})
            if isinstance(payload.get("execution_artifact_summary"), dict)
            and isinstance(payload.get("execution_artifact_summary", {}).get("planner_decision"), dict)
            else derive_session_planner_decision_summary(
                planner_shared=(
                    payload.get("execution_artifact_summary", {}).get("planner_shared_contract", {})
                    if isinstance(payload.get("execution_artifact_summary"), dict)
                    and isinstance(payload.get("execution_artifact_summary", {}).get("planner_shared_contract"), dict)
                    else {}
                ),
                adapter_shared=(
                    payload.get("execution_artifact_summary", {}).get("adapter_shared_contract", {})
                    if isinstance(payload.get("execution_artifact_summary"), dict)
                    and isinstance(payload.get("execution_artifact_summary", {}).get("adapter_shared_contract"), dict)
                    else {}
                ),
            )
        )
        fallback_continuity_outline = (
            payload.get("session_continuity_outline", {})
            if isinstance(payload.get("session_continuity_outline"), dict)
            else payload.get("continuity_outline", {})
            if isinstance(payload.get("continuity_outline"), dict)
            else payload.get("execution_artifact_summary", {}).get("continuity_outline", {})
            if isinstance(payload.get("execution_artifact_summary"), dict)
            and isinstance(payload.get("execution_artifact_summary", {}).get("continuity_outline"), dict)
            else derive_session_continuity_outline_summary(
                continuity=continuity,
                planner_family=fallback_planner_decision.get("planner_family"),
            )
        )
        comparative_session_posture_summary = (
            payload.get("comparative_session_posture_summary", {})
            if isinstance(payload.get("comparative_session_posture_summary"), dict)
            else {}
        )
        derived_comparative_session_posture_summary = build_comparative_session_posture_summary(
            session_productization_surface=(
                payload.get("session_productization_surface", {})
                if isinstance(payload.get("session_productization_surface"), dict)
                else continuity.get("session_productization_surface", {})
                if isinstance(continuity.get("session_productization_surface"), dict)
                else {}
            ),
            planner_decision=fallback_planner_decision,
            continuity_outline=fallback_continuity_outline,
        )
        if not comparative_session_posture_summary:
            comparative_session_posture_summary = derived_comparative_session_posture_summary
        elif derived_comparative_session_posture_summary:
            comparative_session_posture_summary = {
                **derived_comparative_session_posture_summary,
                **comparative_session_posture_summary,
            }
        planner_tool_workflow_plan = summary_dict(fallback_planner_decision, "tool_workflow_plan")
        planner_workflow_stages = summary_dict(planner_tool_workflow_plan, "workflow_stages")
        selected_workflow_stages = [
            stage_name
            for stage_name in ("explore", "edit", "verify")
            if summary_dict(planner_workflow_stages, stage_name).get("selected") is True
        ]
        inferred_workflow_stage = comparative_session_posture_summary.get("next_recommended_action")
        if inferred_workflow_stage not in {"explore", "edit", "verify"}:
            inferred_workflow_stage = selected_workflow_stages[0] if selected_workflow_stages else None
        comparative_session_posture_summary = {
            **comparative_session_posture_summary,
            "workflow_active_stage": (
                comparative_session_posture_summary.get("workflow_active_stage")
                if comparative_session_posture_summary.get("workflow_active_stage") is not None
                else inferred_workflow_stage
            ),
            "selected_workflow_stages": (
                comparative_session_posture_summary.get("selected_workflow_stages")
                if isinstance(comparative_session_posture_summary.get("selected_workflow_stages"), list)
                and comparative_session_posture_summary.get("selected_workflow_stages")
                else selected_workflow_stages
            ),
            "workflow_projection_ready": (
                comparative_session_posture_summary.get("workflow_projection_ready")
                if comparative_session_posture_summary.get("workflow_projection_ready") is not None
                else (
                    planner_tool_workflow_plan.get("workflow_projection_required") is True
                    and planner_tool_workflow_plan.get("format") == "agent_orchestrator.native_tool_workflow_plan.v1"
                    and bool(selected_workflow_stages)
                )
            ),
        }
        if comparative_session_posture_summary:
            print(
                "comparative_session_posture_summary: "
                f"primary={comparative_session_posture_summary.get('primary_action')} "
                f"pause_expected={comparative_session_posture_summary.get('pause_expected')} "
                f"handoff_expected={comparative_session_posture_summary.get('handoff_expected')} "
                f"fallback_expected={comparative_session_posture_summary.get('fallback_expected')} "
                f"clarify_pause={comparative_session_posture_summary.get('clarify_pause_state')} "
                f"approval_pause={comparative_session_posture_summary.get('approval_pause_state')} "
                f"resume_expectation={comparative_session_posture_summary.get('resume_expectation')} "
                f"resume_posture={comparative_session_posture_summary.get('resume_posture')} "
                f"workflow_stage={comparative_session_posture_summary.get('workflow_active_stage')} "
                f"workflow_projection_ready={comparative_session_posture_summary.get('workflow_projection_ready')} "
                f"next_action={comparative_session_posture_summary.get('next_recommended_action')}"
            )
        comparative_planner_candidate_summary = (
            payload.get("comparative_planner_candidate_summary", {})
            if isinstance(payload.get("comparative_planner_candidate_summary"), dict)
            else benchmark.get("comparative_planner_candidate_summary", {})
            if isinstance(benchmark.get("comparative_planner_candidate_summary"), dict)
            else {}
        )
        if not comparative_planner_candidate_summary:
            comparative_planner_candidate_summary = build_comparative_planner_candidate_summary(
                planner_shared_contract=(
                    payload.get("execution_artifact_summary", {}).get("planner_shared_contract", {})
                    if isinstance(payload.get("execution_artifact_summary"), dict)
                    and isinstance(payload.get("execution_artifact_summary", {}).get("planner_shared_contract"), dict)
                    else {}
                ),
                operator_planner_digest=(
                    payload.get("operator_planner_digest", {})
                    if isinstance(payload.get("operator_planner_digest"), dict)
                    else benchmark.get("operator_planner_digest", {})
                    if isinstance(benchmark.get("operator_planner_digest"), dict)
                    else derive_operator_planner_digest(
                        planner_decision=fallback_planner_decision,
                        planner_closure_posture=(
                            benchmark.get("planner_closure_posture", {})
                            if isinstance(benchmark.get("planner_closure_posture"), dict)
                            else {}
                        ),
                        continuity_outline=fallback_continuity_outline,
                    )
                ),
            )
        if comparative_planner_candidate_summary:
            print(
                "comparative_planner_candidate_summary: "
                f"native_first={comparative_planner_candidate_summary.get('native_first')} "
                f"selected={comparative_planner_candidate_summary.get('selected_strategy')} "
                f"candidates={len(comparative_planner_candidate_summary.get('decision_candidates', [])) if isinstance(comparative_planner_candidate_summary.get('decision_candidates'), list) else 0} "
                f"governed_alternatives={len(comparative_planner_candidate_summary.get('governed_alternatives', [])) if isinstance(comparative_planner_candidate_summary.get('governed_alternatives'), list) else 0} "
                f"boundary={comparative_planner_candidate_summary.get('decision_boundary', {}).get('task_type') if isinstance(comparative_planner_candidate_summary.get('decision_boundary'), dict) else None}:{comparative_planner_candidate_summary.get('decision_boundary', {}).get('risk_level') if isinstance(comparative_planner_candidate_summary.get('decision_boundary'), dict) else None} "
                f"reason={comparative_planner_candidate_summary.get('planner_reasoning', {}).get('primary_action') if isinstance(comparative_planner_candidate_summary.get('planner_reasoning'), dict) else None} "
                f"decision_mode={comparative_planner_candidate_summary.get('autonomy_surface', {}).get('decision_mode') if isinstance(comparative_planner_candidate_summary.get('autonomy_surface'), dict) else None} "
                f"autonomy_actions={','.join(str(item) for item in comparative_planner_candidate_summary.get('action_coverage', {}).get('autonomy_selected_actions', [])) if isinstance(comparative_planner_candidate_summary.get('action_coverage'), dict) and isinstance(comparative_planner_candidate_summary.get('action_coverage', {}).get('autonomy_selected_actions'), list) and comparative_planner_candidate_summary.get('action_coverage', {}).get('autonomy_selected_actions') else 'none'}"
            )
        comparative_session_continuity_summary = (
            payload.get("comparative_session_continuity_summary", {})
            if isinstance(payload.get("comparative_session_continuity_summary"), dict)
            else benchmark.get("comparative_session_continuity_summary", {})
            if isinstance(benchmark.get("comparative_session_continuity_summary"), dict)
            else {}
        )
        derived_comparative_session_continuity_summary = build_comparative_session_continuity_summary(
            session_productization_surface=(
                payload.get("session_productization_surface", {})
                if isinstance(payload.get("session_productization_surface"), dict)
                else continuity.get("session_productization_surface", {})
                if isinstance(continuity.get("session_productization_surface"), dict)
                else {}
            ),
            continuity_outline=fallback_continuity_outline,
            comparative_shared_evidence_surface=(
                benchmark.get("shared_evidence_surface", [])
                if isinstance(benchmark.get("shared_evidence_surface"), list)
                else []
            ),
        )
        if not comparative_session_continuity_summary:
            comparative_session_continuity_summary = derived_comparative_session_continuity_summary
        elif derived_comparative_session_continuity_summary:
            comparative_session_continuity_summary = {
                **derived_comparative_session_continuity_summary,
                **comparative_session_continuity_summary,
            }
        inferred_continuity_workflow_stage = comparative_session_continuity_summary.get("next_recommended_action")
        if inferred_continuity_workflow_stage not in {"explore", "edit", "verify"}:
            inferred_continuity_workflow_stage = (
                comparative_session_posture_summary.get("workflow_active_stage")
                if comparative_session_posture_summary.get("workflow_active_stage") in {"explore", "edit", "verify"}
                else selected_workflow_stages[0]
                if selected_workflow_stages
                else None
            )
        comparative_session_continuity_summary = {
            **comparative_session_continuity_summary,
            "workflow_active_stage": (
                comparative_session_continuity_summary.get("workflow_active_stage")
                if comparative_session_continuity_summary.get("workflow_active_stage") is not None
                else inferred_continuity_workflow_stage
            ),
            "selected_workflow_stages": (
                comparative_session_continuity_summary.get("selected_workflow_stages")
                if isinstance(comparative_session_continuity_summary.get("selected_workflow_stages"), list)
                and comparative_session_continuity_summary.get("selected_workflow_stages")
                else selected_workflow_stages
            ),
            "workflow_resume_ready": (
                comparative_session_continuity_summary.get("workflow_resume_ready")
                if comparative_session_continuity_summary.get("workflow_resume_ready") is not None
                else bool(comparative_session_continuity_summary.get("resume_ready")) and bool(selected_workflow_stages)
            ),
            "workflow_projection_visible": (
                comparative_session_continuity_summary.get("workflow_projection_visible")
                if comparative_session_continuity_summary.get("workflow_projection_visible") is not None
                else bool(planner_tool_workflow_plan)
            ),
            "workflow_recovery_aligned": (
                comparative_session_continuity_summary.get("workflow_recovery_aligned")
                if comparative_session_continuity_summary.get("workflow_recovery_aligned") is not None
                else inferred_continuity_workflow_stage in {None, *selected_workflow_stages}
            ),
        }
        if comparative_session_continuity_summary:
            runtime_cost_provenance = summary_dict(
                comparative_session_continuity_summary,
                "runtime_cost_provenance",
            )
            print(
                "comparative_session_continuity_summary: "
                f"status={comparative_session_continuity_summary.get('continuity_status')} "
                f"resume_supported={comparative_session_continuity_summary.get('resume_supported')} "
                f"resume_kind={comparative_session_continuity_summary.get('resume_kind')} "
                f"resume_ready={comparative_session_continuity_summary.get('resume_ready')} "
                f"resume_posture={comparative_session_continuity_summary.get('resume_posture')} "
                f"recovery_active={comparative_session_continuity_summary.get('recovery_active')} "
                f"approval_boundary_active={comparative_session_continuity_summary.get('approval_boundary_active')} "
                f"governed_pause_resume_ready={comparative_session_continuity_summary.get('governed_pause_resume_ready')} "
                f"verification_resume_ready={comparative_session_continuity_summary.get('verification_resume_ready')} "
                f"compaction_stage={comparative_session_continuity_summary.get('compaction_stage')} "
                f"compaction_pressure={comparative_session_continuity_summary.get('compaction_pressure')} "
                f"context_pressure={comparative_session_continuity_summary.get('context_pressure')} "
                f"summarization_ready={comparative_session_continuity_summary.get('summarization_ready')} "
                f"runtime_duration_seconds={comparative_session_continuity_summary.get('runtime_duration_seconds')} "
                f"usage_cost_status={comparative_session_continuity_summary.get('usage_cost_measurement_status')} "
                f"duration_source={runtime_cost_provenance.get('duration_source')} "
                f"workflow_stage={comparative_session_continuity_summary.get('workflow_active_stage')} "
                f"workflow_resume_ready={comparative_session_continuity_summary.get('workflow_resume_ready')} "
                f"workflow_projection_visible={comparative_session_continuity_summary.get('workflow_projection_visible')} "
                f"workflow_recovery_aligned={comparative_session_continuity_summary.get('workflow_recovery_aligned')} "
                f"next_action={comparative_session_continuity_summary.get('next_recommended_action')}"
            )
        comparative_native_closure_summary = (
            payload.get("comparative_native_closure_summary", {})
            if isinstance(payload.get("comparative_native_closure_summary"), dict)
            else benchmark.get("comparative_native_closure_summary", {})
            if isinstance(benchmark.get("comparative_native_closure_summary"), dict)
            else {}
        )
        if comparative_native_closure_summary:
            print(
                "comparative_native_closure_summary: "
                f"native_runtime_only={comparative_native_closure_summary.get('native_runtime_only')} "
                f"closure_status={comparative_native_closure_summary.get('closure_status')} "
                f"verification_status={comparative_native_closure_summary.get('verification_status')} "
                f"repair_outcome={comparative_native_closure_summary.get('repair_outcome')} "
                f"proof_ready={comparative_native_closure_summary.get('proof_ready')} "
                f"proof_scenario={comparative_native_closure_summary.get('proof_scenario')}"
            )
        comparative_daily_driver_summary = build_comparative_daily_driver_summary(
            proof_strength=proof_strength,
            benchmark_digest=benchmark_digest,
            comparative_benchmark=benchmark,
        )
        if comparative_daily_driver_summary:
            print(
                "comparative_daily_driver_summary: "
                f"status={comparative_daily_driver_summary.get('comparison_status')} "
                f"tier={comparative_daily_driver_summary.get('daily_driver_repeatability_tier')} "
                f"families={comparative_daily_driver_summary.get('independent_daily_driver_repo_task_family_count')} "
                f"direct={comparative_daily_driver_summary.get('direct_proof_status')} "
                f"repeatability={comparative_daily_driver_summary.get('repeatability_status')}"
            )
        comparative_completion_summary = build_comparative_completion_summary(
            benchmark_digest=benchmark_digest,
            comparative_benchmark=benchmark,
        )
        if comparative_completion_summary:
            print(
                "comparative_completion_summary: "
                f"completion_ready={comparative_completion_summary.get('completion_ready')} "
                f"human_audit_required={comparative_completion_summary.get('human_audit_required')} "
                f"comparison_status={comparative_completion_summary.get('comparison_status')} "
                f"grade_status={comparative_completion_summary.get('comparison_grade_status')} "
                f"blocking_gap={comparative_completion_summary.get('blocking_gap')} "
                f"operator_action={comparative_completion_summary.get('operator_action')}"
            )
    posture = benchmark.get("comparison_posture", {}) if isinstance(benchmark.get("comparison_posture"), dict) else {}
    if posture:
        gaps = ",".join(str(item) for item in posture.get("remaining_gap_classes", [])) if isinstance(posture.get("remaining_gap_classes"), list) else ""
        print(
            "comparative_posture: "
                f"status={posture.get('status')} "
                f"confidence={posture.get('confidence')} "
                f"foundation_gap_remaining={posture.get('foundation_gap_remaining')} "
                f"remaining_gaps={gaps or 'none'}"
            )
        posture_basis = benchmark.get("comparison_posture_basis", {}) if isinstance(benchmark.get("comparison_posture_basis"), dict) else {}
        if posture_basis:
            refs = ",".join(str(item) for item in posture_basis.get("basis_surface_refs", [])) if isinstance(posture_basis.get("basis_surface_refs"), list) else ""
            limits = ",".join(str(item) for item in posture_basis.get("comparison_limitations", [])) if isinstance(posture_basis.get("comparison_limitations"), list) else ""
            print(
                "comparative_posture_basis: "
                f"shared_productization_ready={posture_basis.get('shared_productization_contract_ready')} "
                f"daily_driver_case_ready={posture_basis.get('long_chain_daily_driver_case_ready', posture_basis.get('daily_driver_main_path_ready'))} "
                f"evidence_scope={posture_basis.get('evidence_scope')} "
                f"basis_refs={refs or 'none'} "
                f"limitations={limits or 'none'}"
            )
        if proof_strength:
            limits = ",".join(str(item) for item in proof_strength.get("proof_limitations", [])) if isinstance(proof_strength.get("proof_limitations"), list) else ""
            stronger_families = ",".join(str(item) for item in proof_strength.get("stronger_task_families", [])) if isinstance(proof_strength.get("stronger_task_families"), list) else ""
            repo_task_families = ",".join(str(item) for item in proof_strength.get("repo_task_acceptance_families_proven", [])) if isinstance(proof_strength.get("repo_task_acceptance_families_proven"), list) else ""
            daily_driver_families = ",".join(str(item) for item in proof_strength.get("daily_driver_repo_task_families_proven", [])) if isinstance(proof_strength.get("daily_driver_repo_task_families_proven"), list) else ""
            independent_daily_driver_families = ",".join(str(item) for item in proof_strength.get("independent_daily_driver_repo_task_families_proven", [])) if isinstance(proof_strength.get("independent_daily_driver_repo_task_families_proven"), list) else ""
            broader_gap_families = ",".join(str(item) for item in proof_strength.get("broader_repeatability_gap_families", [])) if isinstance(proof_strength.get("broader_repeatability_gap_families"), list) else ""
            print(
                "comparative_proof_strength: "
                f"direct_proof={proof_strength.get('direct_proof_status')} "
                f"repeatability={proof_strength.get('repeatability_status')} "
                f"repeatability_ready={proof_strength.get('repeatability_ready')} "
                f"daily_driver_repeatability_tier={proof_strength.get('daily_driver_repeatability_tier')} "
                f"stronger_task_families={proof_strength.get('stronger_task_family_count')} "
                f"broader_task_families={proof_strength.get('broader_task_family_count')} "
                f"stronger_family_names={stronger_families or 'none'} "
                f"repo_task_acceptance_family_count={proof_strength.get('repo_task_acceptance_family_count')} "
                f"repo_task_acceptance_families={repo_task_families or 'none'} "
                f"daily_driver_repo_task_family_count={proof_strength.get('daily_driver_repo_task_family_count')} "
                f"daily_driver_repo_task_families={daily_driver_families or 'none'} "
                f"independent_daily_driver_repo_task_family_count={proof_strength.get('independent_daily_driver_repo_task_family_count')} "
                f"independent_daily_driver_repo_task_families={independent_daily_driver_families or 'none'} "
                f"broader_repeatability_gap_families={broader_gap_families or 'none'} "
                f"limitations={limits or 'none'}"
            )
            daily_driver_benchmark = build_comparative_daily_driver_benchmark(proof_strength)
            if daily_driver_benchmark:
                print(f"comparative_daily_driver_benchmark: {daily_driver_benchmark}")
        comparison_grade = benchmark.get("comparison_grade_assessment", {}) if isinstance(benchmark.get("comparison_grade_assessment"), dict) else {}
        if comparison_grade:
            print(
                "comparative_grade_assessment: "
                f"status={comparison_grade.get('status')} "
                f"comparison_grade_ready={comparison_grade.get('comparison_grade_ready')} "
                f"internal_repeatability_ready={comparison_grade.get('internal_repeatability_ready')} "
                f"external_harness_ready={comparison_grade.get('external_harness_ready')} "
                f"blocking_gap={comparison_grade.get('blocking_gap')}"
            )
        harness_surface = (
            benchmark.get("external_comparison_harness_surface", {})
            if isinstance(benchmark.get("external_comparison_harness_surface"), dict)
            else comparison_grade.get("external_comparison_harness_surface", {})
            if isinstance(comparison_grade.get("external_comparison_harness_surface"), dict)
            else {}
        )
        if harness_surface:
            requirements = (
                harness_surface.get("requirements", {})
                if isinstance(harness_surface.get("requirements"), dict)
                else {}
            )
            missing_external_artifacts = ",".join(
                str(item)
                for item in requirements.get("missing_external_artifacts", [])
            ) if isinstance(requirements.get("missing_external_artifacts"), list) else ""
            print(
                "comparative_harness_surface: "
                f"format={harness_surface.get('format')} "
                f"status={harness_surface.get('harness_status')} "
                f"authoritative={harness_surface.get('authoritative')} "
                f"next_milestone={harness_surface.get('next_evidence_milestone')} "
                f"operator_action={harness_surface.get('operator_action')} "
                f"missing_external_artifacts={missing_external_artifacts or 'none'}"
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
        evidence = exploration.get("exploration_evidence", {}) if isinstance(exploration.get("exploration_evidence"), dict) else {}
        if evidence:
            shared = ",".join(str(item) for item in evidence.get("shared_evidence_surface", [])) if isinstance(evidence.get("shared_evidence_surface"), list) else ""
            read_paths = ",".join(str(item) for item in evidence.get("read_paths", [])) if isinstance(evidence.get("read_paths"), list) else ""
            search_paths = ",".join(str(item) for item in evidence.get("search_match_paths", [])) if isinstance(evidence.get("search_match_paths"), list) else ""
            print(
                "native_exploration_evidence: "
                f"reason={evidence.get('candidate_reason')} "
                f"search_matches={evidence.get('search_match_count')} "
                f"read_records={evidence.get('read_record_count')} "
                f"search_paths={search_paths or 'none'} "
                f"read_paths={read_paths or 'none'} "
                f"shared_surface={shared or 'none'}"
            )
    evidence_summary = payload.get("execution_artifact_summary", {}) if isinstance(payload.get("execution_artifact_summary"), dict) else {}
    fact_chain = payload.get("execution_fact_chain", {}) if isinstance(payload.get("execution_fact_chain"), dict) else {}
    if fact_chain:
        print(
            "execution_fact_chain: "
            f"status={fact_chain.get('current_status')} "
            f"stage={fact_chain.get('active_stage')} "
            f"verification={fact_chain.get('verification_status')} "
            f"approval_pause={fact_chain.get('approval_pause_state')} "
            f"resume_supported={fact_chain.get('resume_supported')} "
            f"next_action={fact_chain.get('next_recommended_action')} "
            f"closure={fact_chain.get('closure_status')}"
        )
    clarify_boundary_digest = (
        payload.get("clarify_boundary_digest", {})
        if isinstance(payload.get("clarify_boundary_digest"), dict)
        else {}
    )
    if clarify_boundary_digest:
        print(
            "clarify_boundary_digest: "
            f"status={clarify_boundary_digest.get('status')} "
            f"strategy={clarify_boundary_digest.get('selected_execution_strategy')} "
            f"next_action={clarify_boundary_digest.get('next_recommended_action')} "
            f"resume_expectation={clarify_boundary_digest.get('resume_expectation')} "
            f"recovery_lane={clarify_boundary_digest.get('recovery_lane')}"
        )
    approval_boundary_digest = (
        payload.get("approval_boundary_digest", {})
        if isinstance(payload.get("approval_boundary_digest"), dict)
        else {}
    )
    if approval_boundary_digest:
        print(
            "approval_boundary_digest: "
            f"status={approval_boundary_digest.get('status')} "
            f"strategy={approval_boundary_digest.get('selected_execution_strategy')} "
            f"next_action={approval_boundary_digest.get('next_recommended_action')} "
            f"resume_expectation={approval_boundary_digest.get('resume_expectation')} "
            f"recovery_lane={approval_boundary_digest.get('recovery_lane')}"
        )
    if evidence_summary:
        continuity = evidence_summary.get("session_continuity", {}) if isinstance(evidence_summary.get("session_continuity"), dict) else {}
        tool_usage = evidence_summary.get("native_tool_usage", {}) if isinstance(evidence_summary.get("native_tool_usage"), dict) else {}
        runtime_cost = evidence_summary.get("runtime_cost", {}) if isinstance(evidence_summary.get("runtime_cost"), dict) else {}
        planner_shared = evidence_summary.get("planner_shared_contract", {}) if isinstance(evidence_summary.get("planner_shared_contract"), dict) else {}
        adapter_shared = evidence_summary.get("adapter_shared_contract", {}) if isinstance(evidence_summary.get("adapter_shared_contract"), dict) else {}
        native_tool_surface = evidence_summary.get("native_tool_surface", {}) if isinstance(evidence_summary.get("native_tool_surface"), dict) else {}
        if continuity:
            productization_surface = derive_session_productization_surface(continuity)
            planner_decision = evidence_summary.get("planner_decision", {}) if isinstance(evidence_summary.get("planner_decision"), dict) else {}
            continuity_outline = evidence_summary.get("continuity_outline", {}) if isinstance(evidence_summary.get("continuity_outline"), dict) else {}
            planner_closure_posture = (
                evidence_summary.get("planner_closure_posture", {})
                if isinstance(evidence_summary.get("planner_closure_posture"), dict)
                else {}
            )
            if not planner_decision:
                planner_decision = derive_session_planner_decision_summary(
                    planner_shared=planner_shared,
                    adapter_shared=adapter_shared,
                )
            if not continuity_outline:
                continuity_outline = derive_session_continuity_outline_summary(
                    continuity=continuity,
                    planner_family=planner_shared.get("planner_family"),
                )
            if not planner_closure_posture and (planner_decision or continuity):
                planner_closure_posture = derive_planner_closure_posture_summary(
                    planner_decision=planner_decision,
                    continuity=continuity,
                )
            tool_productization_surface = _derived_native_tool_productization_surface(
                native_tool_surface,
                tool_usage,
            )
            adapter_productization_surface = _derived_adapter_productization_surface(
                adapter_shared,
                evidence_summary.get("adapter_capability", {}) if isinstance(evidence_summary.get("adapter_capability"), dict) else {},
            )
            shared_productization_surface = build_shared_productization_surface(
                session_productization_surface=productization_surface,
                native_tool_productization_surface=tool_productization_surface,
                native_tool_workflow_surface=summary_dict(tool_productization_surface, "workflow_surface")
                or summary_dict(native_tool_surface, "workflow_surface"),
                adapter_productization_surface=adapter_productization_surface,
                planner_decision=planner_decision,
                continuity_outline=continuity_outline,
                comparative_shared_evidence_surface=summary_list(continuity, "shared_evidence_surface"),
            )
            print(
                "session_continuity: "
                f"resume_supported={continuity.get('resume_supported')} "
                f"compaction_stage={continuity.get('compaction_stage')} "
                f"summarization_triggered={continuity.get('summarization_triggered')} "
                f"resume_kind={continuity.get('resume_kind')}"
            )
            continuity_snapshot = continuity.get("continuity_snapshot", {}) if isinstance(continuity.get("continuity_snapshot"), dict) else {}
            if continuity_snapshot:
                program_digest = continuity_snapshot.get("program_digest", {}) if isinstance(continuity_snapshot.get("program_digest"), dict) else {}
                compaction_digest = continuity_snapshot.get("compaction_digest", {}) if isinstance(continuity_snapshot.get("compaction_digest"), dict) else {}
                print(
                    "continuity_snapshot: "
                    f"status={continuity_snapshot.get('snapshot_status')} "
                    f"artifact_backed={continuity_snapshot.get('artifact_backed')} "
                    f"goal={program_digest.get('program_goal')} "
                    f"active={program_digest.get('active_milestone')} "
                    f"pending={program_digest.get('pending_followup_count')} "
                    f"compaction={compaction_digest.get('compaction_stage')}"
                )
            daily_driver = continuity.get("daily_driver_readiness", {}) if isinstance(continuity.get("daily_driver_readiness"), dict) else {}
            if daily_driver:
                print(
                    "daily_driver_readiness: "
                    f"tool_surface={daily_driver.get('tool_surface_ready')} "
                    f"planner={daily_driver.get('planner_ready')} "
                    f"session={daily_driver.get('session_ready')} "
                    f"adapter={daily_driver.get('adapter_ready')} "
                    f"shared_productization={daily_driver.get('shared_productization_ready')} "
                    f"long_chain={daily_driver.get('long_chain_task_ready')} "
                    f"main_path={daily_driver.get('daily_driver_main_path_ready')} "
                    f"gap={daily_driver.get('open_product_gap')}"
                )
            if productization_surface:
                readiness = productization_surface.get("continuity_readiness", {}) if isinstance(productization_surface.get("continuity_readiness"), dict) else {}
                operator_continuity = productization_surface.get("operator_continuity", {}) if isinstance(productization_surface.get("operator_continuity"), dict) else {}
                operator_posture_digest = productization_surface.get("operator_posture_digest", {}) if isinstance(productization_surface.get("operator_posture_digest"), dict) else {}
                shared_productization_surface = build_shared_productization_surface(
                    session_productization_surface=productization_surface,
                    native_tool_productization_surface=tool_productization_surface,
                    native_tool_workflow_surface=summary_dict(tool_productization_surface, "workflow_surface")
                    or summary_dict(native_tool_surface, "workflow_surface"),
                    adapter_productization_surface=adapter_productization_surface,
                    planner_decision=planner_decision,
                    continuity_outline=continuity_outline,
                    planner_closure_posture=planner_closure_posture,
                    runtime_cost=summary_dict(continuity, "runtime_cost"),
                    native_tool_usage=tool_usage,
                    adapter_capability_surface=summary_dict(evidence_summary, "adapter_capability_surface"),
                    comparative_shared_evidence_surface=summary_list(continuity, "shared_evidence_surface"),
                )
                print(
                    "session_productization_surface: "
                    f"format={productization_surface.get('format')} "
                    f"status={productization_surface.get('continuity_status')} "
                    f"resume_ready={readiness.get('resume_ready')} "
                    f"runtime_cost_ready={readiness.get('runtime_cost_ready')} "
                    f"compaction_ready={readiness.get('compaction_ready')} "
                    f"recovery_ready={readiness.get('recovery_ready')} "
                    f"next_action={operator_continuity.get('next_recommended_action')}"
                )
                autonomy_posture = summary_dict(productization_surface, "autonomy_posture")
                if autonomy_posture:
                    print(
                        "session_productization_posture: "
                        f"pause_expected={autonomy_posture.get('pause_expected')} "
                        f"handoff_expected={autonomy_posture.get('handoff_expected')} "
                        f"fallback_expected={autonomy_posture.get('fallback_expected')} "
                        f"resume_posture={autonomy_posture.get('resume_posture')}"
                    )
                if operator_posture_digest:
                    print(
                        "operator_posture_digest: "
                        f"status={operator_posture_digest.get('continuity_status') or productization_surface.get('continuity_status')} "
                        f"compaction_stage={operator_posture_digest.get('compaction_stage')} "
                        f"compaction_pressure={operator_posture_digest.get('compaction_pressure')} "
                        f"next_action={operator_posture_digest.get('next_recommended_action')} "
                        f"recovery_lane={operator_posture_digest.get('runbook_recovery_lane')} "
                        f"resume_expectation={operator_posture_digest.get('resume_expectation')} "
                        f"resume_posture={operator_posture_digest.get('resume_posture')} "
                        f"alternatives={','.join(str(item.get('action')) for item in operator_posture_digest.get('planner_governed_alternatives', []) if isinstance(item, dict) and item.get('action')) if isinstance(operator_posture_digest.get('planner_governed_alternatives'), list) and operator_posture_digest.get('planner_governed_alternatives') else 'none'}"
                    )
                operator_planner_digest = derive_operator_planner_digest(
                    planner_decision=planner_decision,
                    planner_closure_posture=planner_closure_posture,
                    continuity_outline=continuity_outline,
                )
                if operator_planner_digest:
                    print(
                        "operator_planner_digest: "
                        f"primary={operator_planner_digest.get('primary_action')} "
                        f"executor={operator_planner_digest.get('selected_executor')} "
                        f"mode={operator_planner_digest.get('closure_mode')} "
                        f"next_action={operator_planner_digest.get('next_recommended_action')} "
                        f"resume_expectation={operator_planner_digest.get('resume_expectation')} "
                        f"resume_posture={operator_planner_digest.get('resume_posture')} "
                        f"pause_expected={operator_planner_digest.get('pause_expected')} "
                        f"handoff_expected={operator_planner_digest.get('handoff_expected')} "
                        f"fallback_expected={operator_planner_digest.get('fallback_expected')} "
                        f"requires_confirmation={operator_planner_digest.get('requires_human_confirmation')}"
                    )
                operator_tool_digest = derive_operator_tool_digest(
                    native_tool_productization_surface=tool_productization_surface,
                    native_tool_workflow_surface=summary_dict(tool_productization_surface, "workflow_surface")
                    or summary_dict(native_tool_surface, "workflow_surface"),
                )
                if operator_tool_digest:
                    print(
                        "operator_tool_digest: "
                        f"posture={operator_tool_digest.get('tooling_posture')} "
                        f"recent={','.join(str(item) for item in operator_tool_digest.get('recent_tools', [])) if isinstance(operator_tool_digest.get('recent_tools'), list) and operator_tool_digest.get('recent_tools') else 'none'} "
                        f"explore={','.join(str(item) for item in operator_tool_digest.get('explore_tools', [])) if isinstance(operator_tool_digest.get('explore_tools'), list) and operator_tool_digest.get('explore_tools') else 'none'} "
                        f"edit={','.join(str(item) for item in operator_tool_digest.get('edit_tools', [])) if isinstance(operator_tool_digest.get('edit_tools'), list) and operator_tool_digest.get('edit_tools') else 'none'} "
                        f"verify={','.join(str(item) for item in operator_tool_digest.get('verify_tools', [])) if isinstance(operator_tool_digest.get('verify_tools'), list) and operator_tool_digest.get('verify_tools') else 'none'}"
                    )
                print(
                    "shared_productization_surface: "
                    f"format={shared_productization_surface.get('format')} "
                    f"status={shared_productization_surface.get('surface_status')} "
                    f"shared_ready={shared_productization_surface.get('shared_productization_contract_ready')} "
                    f"session_ready={summary_dict(shared_productization_surface, 'contract_readiness').get('session_ready')} "
                    f"tool_ready={summary_dict(shared_productization_surface, 'contract_readiness').get('tool_ready')} "
                    f"adapter_ready={summary_dict(shared_productization_surface, 'contract_readiness').get('adapter_ready')} "
                    f"planner_ready={summary_dict(shared_productization_surface, 'contract_readiness').get('planner_ready')}"
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
            compacted_context = evidence_summary.get("compacted_context_summary", {}) if isinstance(evidence_summary.get("compacted_context_summary"), dict) else {}
            if compacted_context:
                print(
                    "compacted_context: "
                    f"objective={compacted_context.get('objective')} "
                    f"status={compacted_context.get('current_status')} "
                    f"compaction_stage={compacted_context.get('compaction_stage')} "
                    f"masked={compacted_context.get('masked_observation_count')} "
                    f"pending_steps={compacted_context.get('pending_step_count')} "
                    f"recovery_hint={compacted_context.get('latest_recovery_hint')}"
                )
            resume_contract = continuity.get("resume_contract", {}) if isinstance(continuity.get("resume_contract"), dict) else {}
            if not resume_contract:
                resume_contract = evidence_summary.get("resume_contract", {}) if isinstance(evidence_summary.get("resume_contract"), dict) else {}
            if not resume_contract and continuity:
                productization_surface = continuity.get("session_productization_surface", {}) if isinstance(continuity.get("session_productization_surface"), dict) else {}
                operator_continuity = productization_surface.get("operator_continuity", {}) if isinstance(productization_surface.get("operator_continuity"), dict) else {}
                program_posture = continuity.get("program_posture", {}) if isinstance(continuity.get("program_posture"), dict) else {}
                resume_contract = {
                    "resume_kind": continuity.get("resume_kind") or operator_continuity.get("resume_expectation"),
                    "current_stage": program_posture.get("active_milestone"),
                    "current_step_id": None,
                    "program_posture": program_posture,
                    "native_tool_usage": tool_usage,
                }
            if resume_contract:
                recent = ",".join(str(item) for item in resume_contract.get("native_tool_usage", {}).get("recent_tools", [])) if isinstance(resume_contract.get("native_tool_usage"), dict) and isinstance(resume_contract.get("native_tool_usage", {}).get("recent_tools"), list) else ""
                print(
                    "resume_contract: "
                    f"resume_kind={resume_contract.get('resume_kind')} "
                    f"stage={resume_contract.get('current_stage')} "
                    f"step_id={resume_contract.get('current_step_id')} "
                    f"active={resume_contract.get('program_posture', {}).get('active_milestone') if isinstance(resume_contract.get('program_posture'), dict) else None} "
                    f"trace_count={resume_contract.get('native_tool_usage', {}).get('trace_count') if isinstance(resume_contract.get('native_tool_usage'), dict) else None} "
                    f"recent={recent or 'none'}"
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
            if tool_productization_surface:
                readiness = _native_tool_readiness_with_fallback(tool_productization_surface)
                print(
                    "native_tool_productization_surface: "
                    f"format={tool_productization_surface.get('format')} "
                    f"posture={tool_productization_surface.get('tooling_posture')} "
                    f"operator_visible={tool_productization_surface.get('operator_visibility_ready')} "
                    f"read_search={readiness.get('bounded_read_search_ready')} "
                    f"glob={readiness.get('glob_ready')} "
                    f"patch={readiness.get('structured_patch_ready')} "
                    f"verify={readiness.get('verification_ready')}"
                )
        if native_tool_surface:
            readiness = _native_tool_readiness_with_fallback(native_tool_surface)
            capability_profile = native_tool_surface.get("capability_profile", {}) if isinstance(native_tool_surface.get("capability_profile"), dict) else {}
            workflow_surface = summary_dict(tool_productization_surface, "workflow_surface") or summary_dict(native_tool_surface, "workflow_surface")
            print(
                "native_tool_surface: "
                f"format={native_tool_surface.get('format')} "
                f"repo_exploration_ready={readiness.get('repo_exploration_ready')} "
                f"glob_ready={readiness.get('glob_ready')} "
                f"structured_patch_ready={readiness.get('structured_patch_ready')} "
                f"patch_preview_ready={readiness.get('patch_preview_ready')} "
                f"diff_preview_ready={readiness.get('diff_preview_ready')} "
                f"verification_ready={readiness.get('verification_ready')}"
            )
            if workflow_surface:
                daily_driver_path = summary_dict(workflow_surface, "daily_driver_path")
                workflow_surface_format = (
                    tool_productization_surface.get("format")
                    or summary_dict(native_tool_surface, "workflow_surface").get("format")
                    if isinstance(summary_dict(native_tool_surface, "workflow_surface"), dict)
                    else None
                )
                print(
                    "native_tool_workflow_surface: "
                    f"format={workflow_surface_format}"
                )
                print(
                    "native_tool_workflow: "
                    f"explore={','.join(str(item) for item in summary_list(summary_dict(workflow_surface, 'explore'), 'tools')) or 'none'} "
                    f"edit={','.join(str(item) for item in summary_list(summary_dict(workflow_surface, 'edit'), 'tools')) or 'none'} "
                    f"verify={','.join(str(item) for item in summary_list(summary_dict(workflow_surface, 'verify'), 'tools')) or 'none'} "
                    f"daily_driver={','.join(str(item) for item in summary_list(daily_driver_path, 'tools')) or 'none'}"
                )
            if capability_profile:
                patch_preview = capability_profile.get("patch_preview", {}) if isinstance(capability_profile.get("patch_preview"), dict) else {}
                structured_patch = capability_profile.get("structured_patch", {}) if isinstance(capability_profile.get("structured_patch"), dict) else {}
                diff_preview = capability_profile.get("diff_preview", {}) if isinstance(capability_profile.get("diff_preview"), dict) else {}
                verify = capability_profile.get("verify", {}) if isinstance(capability_profile.get("verify"), dict) else {}
                print(
                    "native_tool_capabilities: "
                    f"patch_preview={patch_preview.get('purpose')} "
                    f"structured_patch={structured_patch.get('purpose')} "
                    f"diff_preview={diff_preview.get('purpose')} "
                    f"verify={verify.get('purpose')}"
                )
        if planner_shared:
            actions = ",".join(str(item) for item in planner_shared.get("selected_actions", [])) if isinstance(planner_shared.get("selected_actions"), list) else ""
            candidates = ",".join(str(item) for item in planner_shared.get("decision_candidates", [])) if isinstance(planner_shared.get("decision_candidates"), list) else ""
            route_intent = planner_shared.get("route_planner_intent", {}) if isinstance(planner_shared.get("route_planner_intent"), dict) else {}
            decision_boundary = planner_shared.get("decision_boundary", {}) if isinstance(planner_shared.get("decision_boundary"), dict) else {}
            posture = planner_shared.get("route_intent_alignment", {}) if isinstance(planner_shared.get("route_intent_alignment"), dict) else {}
            autonomy_surface = _derived_planner_autonomy_surface(planner_shared)
            print(
                "planner_shared_contract: "
                f"family={planner_shared.get('planner_family')} "
                f"format={planner_shared.get('format')} "
                f"strategy={planner_shared.get('selected_strategy')} "
                f"owner={planner_shared.get('selected_owner')} "
                f"native_work_units={planner_shared.get('native_work_units')} "
                f"actions={actions or 'none'} "
                f"route_intent={','.join(str(item) for item in route_intent.get('priority', [])) if isinstance(route_intent.get('priority'), list) and route_intent.get('priority') else 'none'}"
            )
            print(
                "planner_decision_surface: "
                f"candidates={candidates or 'none'} "
                f"task_type={decision_boundary.get('task_type')} "
                f"risk={decision_boundary.get('risk_level')} "
                f"route_task_kind={decision_boundary.get('route_task_kind')} "
                f"requires_confirmation={decision_boundary.get('requires_human_confirmation')} "
                f"intent_alignment_explore={posture.get('explore')} "
                f"intent_alignment_verify={posture.get('verify')}"
            )
            if autonomy_surface:
                autonomy_actions = summary_dict(autonomy_surface, "actions")
                print(
                    "planner_autonomy_surface: "
                    f"format={autonomy_surface.get('format')} "
                    f"mode={autonomy_surface.get('decision_mode')} "
                    f"primary={autonomy_surface.get('primary_action')} "
                    f"clarify={summary_dict(autonomy_actions, 'clarify').get('selected')} "
                    f"pause={summary_dict(autonomy_actions, 'pause').get('selected')} "
                    f"handoff={summary_dict(autonomy_actions, 'handoff').get('selected')} "
                    f"fallback={summary_dict(autonomy_actions, 'fallback').get('selected')}"
                )
            autonomy_boundary = summary_dict(planner_shared, "autonomy_boundary")
            planner_reasoning = summary_dict(planner_shared, "planner_reasoning")
            if autonomy_boundary or planner_reasoning:
                print(
                    "planner_autonomy_boundary: "
                    f"native_first={planner_reasoning.get('native_first', autonomy_boundary.get('native_first'))} "
                    f"clarify={autonomy_boundary.get('requires_clarify')} "
                    f"pause={autonomy_boundary.get('requires_pause')} "
                    f"handoff={autonomy_boundary.get('requires_handoff')} "
                    f"fallback={autonomy_boundary.get('requires_fallback')} "
                    f"explore={autonomy_boundary.get('requires_explore')} "
                    f"edit={autonomy_boundary.get('requires_edit')} "
                    f"verify={autonomy_boundary.get('requires_verify')}"
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
            print(
                "adapter_productization_surface: "
                f"format={adapter_productization_surface.get('format')} "
                f"status={adapter_productization_surface.get('surface_status')} "
                f"comparison_mode={adapter_productization_surface.get('comparison_mode')} "
                f"hot_plug_supported={adapter_productization_surface.get('hot_plug_supported')} "
                f"fallback_governed={adapter_productization_surface.get('fallback_governed')} "
                f"resume_supported={adapter_productization_surface.get('resume_contract_supported')} "
                f"recovery_ready={adapter_productization_surface.get('governed_recovery_ready')}"
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
    planner = payload.get("session_planner_decision", {}) if isinstance(payload.get("session_planner_decision"), dict) else {}
    continuity = payload.get("session_continuity_outline", {}) if isinstance(payload.get("session_continuity_outline"), dict) else {}
    planner_posture = planner.get("autonomy_posture", {}) if isinstance(planner.get("autonomy_posture"), dict) else {}
    continuity_posture = continuity.get("autonomy_posture", {}) if isinstance(continuity.get("autonomy_posture"), dict) else {}
    if planner_posture or continuity_posture:
        print(
            "session_posture: "
            f"pause_expected={planner_posture.get('pause_expected')} "
            f"handoff_expected={planner_posture.get('handoff_expected')} "
            f"fallback_expected={planner_posture.get('fallback_expected')} "
            f"resume_posture={continuity_posture.get('resume_posture')}"
        )
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
