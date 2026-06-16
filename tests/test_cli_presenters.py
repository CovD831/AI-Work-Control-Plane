# DEPS: agent_orchestrator, argparse, pytest
# RESPONSIBILITY: 验证 CLI 展示层格式化与推荐动作输出
# MODULE: tests
# ---

import argparse

from agent_orchestrator.cli_presenters import (
    pick_primary_action,
    print_blocker_session_summary,
    print_workspace_state_summary,
    print_handoff_summary,
    print_execution_session_summary,
    print_team_next,
    print_team_runbook,
    print_team_summary,
    team_display_context,
    team_next_alternatives,
)


class _FakeSession:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, object]:
        return self._payload


def _team_payload(
    *,
    session_id: str = "session-123",
    status: str = "needs_revision",
    status_summary: dict[str, object] | None = None,
    doc_sync: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": session_id,
        "status": status,
        "status_summary": status_summary or {},
        "doc_sync": doc_sync or {},
    }


def test_pick_primary_action_prefers_delegated_job_inspection() -> None:
    action = pick_primary_action(["approve", "inspect_delegated_job", "execute"])

    assert action == "inspect_delegated_job"


def test_team_next_alternatives_excludes_primary_action() -> None:
    alternatives = team_next_alternatives(
        {
            "recovery_actions": ["inspect_delegated_job", "retry_review", "inspect_compliance"],
        },
        "inspect_delegated_job",
    )

    assert alternatives == ["retry_review", "inspect_compliance"]


def test_print_handoff_summary_reports_latest_packet(capsys) -> None:
    print_handoff_summary(
        {
            "session_id": "plan-1",
            "packet_count": 1,
            "latest_packet": {
                "packet": {
                    "from_role": "lead",
                    "to_role": "runtime",
                    "summary": "Execute approved plan",
                    "docs_context_snapshot_id": "docsctx-123",
                    "recommended_commands": ["python -m agent_orchestrator.cli team inspect-execution plan-1"],
                }
            },
        }
    )

    out = capsys.readouterr().out
    assert "handoff: plan-1" in out
    assert "latest_packet: lead->runtime snapshot=docsctx-123" in out
    assert "recommended_commands: python -m agent_orchestrator.cli team inspect-execution plan-1" in out


def test_team_display_context_uses_fallback_primary_action_and_collects_failed_jobs() -> None:
    payload = _team_payload(
        status_summary={
            "delegated_jobs": [
                {"provider": "claude", "job_id": "job-1", "status": "failed"},
                {"provider": "codex", "job_id": "job-2", "status": "completed"},
            ],
            "next_actions": ["approve", "execute"],
            "next_action_message": "review is complete",
            "recommended_commands": ["python -m agent_orchestrator.cli team approve session-123"],
        }
    )

    context = team_display_context(payload, pick_primary_action=pick_primary_action)

    assert context["primary_action"] == "approve"
    assert context["primary_reason"] == "review is complete"
    assert context["failed_jobs"] == [{"provider": "claude", "job_id": "job-1", "status": "failed"}]
    assert context["recommended_commands"] == ["python -m agent_orchestrator.cli team approve session-123"]


def test_print_team_summary_reports_topology_and_failed_job(capsys) -> None:
    session = _FakeSession(
        _team_payload(
            status_summary={
                "phase": "review",
                "pending_role": "reviewer",
                "next_actions": ["inspect_delegated_job"],
                "next_action_message": "review job failed",
                "topology_reason": "parallel review is required",
                "blocking_reasons": ["reviewer unavailable"],
                "recovery_actions": ["inspect_delegated_job", "retry_review"],
                "recovery_provider": "claude",
                "recovery_round_type": "review",
                "recovery_provider_mode": "planned",
                "recovery_provider_fallback_from": "codex",
                "recovery_provider_fallback_reason": "preferred_unavailable",
                "recovery_provider_fallback_detail": "claude auth missing",
                "resume_action": "retry_review",
                "resume_reason": "failed_review_job",
                "block_source": "delegated_job",
                "block_detail": "failed_review_job",
                "recovery_semantics": {
                    "category": "retry",
                    "auto_apply_allowed": True,
                    "human_escalation_required": False,
                },
                "recommended_commands": [
                    "python -m agent_orchestrator.cli team retry-review session-123",
                    "python -m agent_orchestrator.cli team inspect-blockers session-123",
                ],
                "delegated_jobs": [
                    {
                        "provider": "claude",
                        "job_id": "job-77",
                        "status": "failed",
                    }
                ],
            }
        )
    )

    print_team_summary(session, pick_primary_action=pick_primary_action)
    out = capsys.readouterr().out

    assert "session: session-123" in out
    assert "status: needs_revision (phase=review, pending_role=reviewer)" in out
    assert "next: inspect_delegated_job" in out
    assert "message: review job failed" in out
    assert "topology_reason: parallel review is required" in out
    assert "blocking: reviewer unavailable" in out
    assert "recovery: inspect_delegated_job -> retry_review" in out
    assert "recovery_provider: claude (round=review, mode=planned, fallback_from=codex" in out
    assert "resume: retry_review (reason=failed_review_job)" in out
    assert "recovery_guidance: mode=retry; resume_action=retry_review; reason=failed_review_job; block=delegated_job/failed_review_job; auto_apply=yes" in out
    assert "recovery_steps: inspect_delegated_job=inspect failed delegated job evidence -> retry_review=retry delegated review" in out
    assert "recovery_commands: python -m agent_orchestrator.cli team retry-review session-123 | python -m agent_orchestrator.cli team inspect-blockers session-123" in out
    assert "failed_job: claude job-77" in out


def test_print_team_next_prefers_recommended_command_and_lists_alternatives(capsys) -> None:
    session = _FakeSession(
        _team_payload(
            status_summary={
                "next_actions": ["approve"],
                "primary_reason": "all required gaps are closed",
                "recommended_commands": ["python -m agent_orchestrator.cli team approve session-123"],
                "recovery_actions": ["approve", "inspect_execution"],
                "open_required_gaps": 0,
                "open_optional_followups": 1,
                "selected_topology": "team",
                "topology_reason": "standard topology is sufficient",
            }
        )
    )
    args = argparse.Namespace(plans_root=".agent_orchestrator/plans", runs_root=".agent_orchestrator/runs")

    print_team_next(
        session,
        pick_primary_action=pick_primary_action,
        build_team_next_command=lambda payload, action, failed_jobs, parsed_args: "unexpected",
        team_next_alternatives=team_next_alternatives,
        args=args,
    )
    out = capsys.readouterr().out

    assert "action: approve" in out
    assert "reason: all required gaps are closed" in out
    assert "next_command: python -m agent_orchestrator.cli team approve session-123" in out
    assert "alternatives: inspect_execution" in out
    assert "context: required_gaps=0 optional_followups=1 delegated_failures=0" in out
    assert "selected_topology: team" in out
    assert "topology_reason: standard topology is sufficient" in out


def test_print_team_next_reports_rerun_recovery_guidance(capsys) -> None:
    session = _FakeSession(
        _team_payload(
            status="blocked",
            status_summary={
                "primary_action": "inspect_blockers",
                "primary_reason": "execution ended in a blocked state; inspect before re-running execution",
                "next_actions": ["inspect_blockers"],
                "recommended_commands": [
                    "python -m agent_orchestrator.cli team inspect-blockers session-123",
                    "python -m agent_orchestrator.cli team inspect-execution session-123",
                ],
                "recovery_actions": ["inspect_blockers", "inspect_execution"],
                "resume_action": "inspect_blockers",
                "resume_reason": "review_blocked",
                "block_source": "execution_run",
                "block_detail": "run_blocked",
                "recovery_semantics": {
                    "category": "inspect_before_rerun",
                    "auto_apply_allowed": False,
                    "human_escalation_required": False,
                },
            },
        )
    )
    args = argparse.Namespace(plans_root=".agent_orchestrator/plans", runs_root=".agent_orchestrator/runs")

    print_team_next(
        session,
        pick_primary_action=pick_primary_action,
        build_team_next_command=lambda payload, action, failed_jobs, parsed_args: "unexpected",
        team_next_alternatives=team_next_alternatives,
        args=args,
    )
    out = capsys.readouterr().out

    assert "action: inspect_blockers" in out
    assert "recovery_guidance: mode=re-run; resume_action=inspect_blockers; reason=review_blocked; block=execution_run/run_blocked; auto_apply=no; inspect before re-running execution" in out
    assert "recovery_steps: inspect_blockers=inspect blockers before resume or re-run -> inspect_execution=inspect linked execution run before resume or re-run" in out
    assert "recovery_commands: python -m agent_orchestrator.cli team inspect-blockers session-123 | python -m agent_orchestrator.cli team inspect-execution session-123" in out


def test_print_team_next_reports_scope_realign_recovery_guidance(capsys) -> None:
    session = _FakeSession(
        _team_payload(
            status="blocked",
            status_summary={
                "primary_action": "inspect_blockers",
                "primary_reason": "exploration ambiguity requires scope realignment before continuing execution",
                "next_actions": ["inspect_blockers"],
                "recommended_commands": [
                    "python -m agent_orchestrator.cli team inspect-blockers session-123",
                ],
                "recovery_actions": ["inspect_blockers", "inspect_execution"],
                "resume_action": "inspect_blockers",
                "resume_reason": "exploration_scope_drift",
                "block_source": "execution_run",
                "block_detail": "exploration_ambiguity_or_scope_drift",
                "recovery_semantics": {
                    "category": "scope_realign",
                    "auto_apply_allowed": False,
                    "human_escalation_required": False,
                    "continue_allowed": True,
                    "scope_realign_required": True,
                    "fallback_allowed": True,
                    "handoff_allowed": False,
                },
            },
        )
    )
    args = argparse.Namespace(plans_root=".agent_orchestrator/plans", runs_root=".agent_orchestrator/runs")

    print_team_next(
        session,
        pick_primary_action=pick_primary_action,
        build_team_next_command=lambda payload, action, failed_jobs, parsed_args: "unexpected",
        team_next_alternatives=team_next_alternatives,
        args=args,
    )
    out = capsys.readouterr().out

    assert "action: inspect_blockers" in out
    assert "recovery_guidance: mode=realign; resume_action=inspect_blockers; reason=exploration_scope_drift; block=execution_run/exploration_ambiguity_or_scope_drift; auto_apply=no; continue_allowed=yes; scope_realign_required=yes; fallback_allowed=yes; handoff_allowed=no" in out


def test_print_team_next_reports_warning_only_compliance_context(capsys) -> None:
    session = _FakeSession(
        _team_payload(
            status="approved_for_execution",
            status_summary={
                "next_actions": ["inspect_compliance"],
                "primary_reason": "non-blocking compliance warnings exist; review them before the next changed-file update",
                "recommended_commands": ["python -m agent_orchestrator.cli team check-compliance session-123"],
                "recovery_actions": ["inspect_compliance"],
                "open_required_gaps": 0,
                "open_optional_followups": 0,
                "warnings": ["header contract warning: src/agent_orchestrator/legacy.py has placeholder `RESPONSIBILITY` value"],
                "baseline_warnings": ["README missing operator runbook link"],
            },
        )
    )
    args = argparse.Namespace(plans_root=".agent_orchestrator/plans", runs_root=".agent_orchestrator/runs")

    print_team_next(
        session,
        pick_primary_action=pick_primary_action,
        build_team_next_command=lambda payload, action, failed_jobs, parsed_args: "unexpected",
        team_next_alternatives=team_next_alternatives,
        args=args,
    )
    out = capsys.readouterr().out

    assert "action: inspect_compliance" in out
    assert "warnings: header contract warning: src/agent_orchestrator/legacy.py has placeholder `RESPONSIBILITY` value" in out
    assert "baseline_warnings: README missing operator runbook link" in out


def test_print_team_runbook_includes_recommended_command_and_steps(capsys) -> None:
    session = _FakeSession(
        _team_payload(
            status="approved_for_execution",
            status_summary={
                "phase": "approved",
                "next_actions": ["execute"],
                "primary_reason": "plan is ready to execute",
                "recommended_commands": ["python -m agent_orchestrator.cli team execute session-123 --mode success_first"],
                "selected_topology": "team",
                "topology_reason": "work can proceed without adversarial depth",
                "decision_rationale": ["approved plan exists", "no blocking gaps remain"],
                "strategy_decision": {
                    "format": "agent_orchestrator.strategy_decision.v1",
                    "next_goal": "Execute approved plan",
                    "recommended_action": "execute",
                    "control_plane_focus": "state_context_strategy_topology_approval_evidence_memory_recovery",
                    "topology_policy": {"selection_reason": "work can proceed without adversarial depth"},
                    "recovery_policy": {"recovery_actions": ["execute"]},
                    "rationale": ["approved plan exists"],
                    "validation_plan": ["targeted tests first"],
                    "route_planner_intent": {
                        "explore": False,
                        "clarify": False,
                        "edit": True,
                        "verify": True,
                        "pause": False,
                        "handoff": False,
                        "fallback": False,
                        "native_first": True,
                        "priority": ["execute", "verify"],
                    },
                    "adapter_shared_contract": {
                        "format": "agent_orchestrator.adapter_shared_contract.v1",
                        "comparison_mode": "same_contract_two_executors",
                        "default_path": "native",
                        "operating_boundary": "native_preferred",
                        "approval_required": False,
                        "hot_plug_supported": True,
                        "evidence_outputs": ["strategy_decision", "run_ledger", "evidence_bundle"],
                        "recovery_surfaces": ["plan_session", "approval_state", "recovery_timeline"],
                    },
                    "program_continuity": {
                        "resume_supported": True,
                        "resume_kind": "execute",
                        "continuity_artifact_status": "projected",
                        "latest_recovery_hint": "plan is ready to execute",
                    },
                    "milestone_verification": {
                        "verification_status": "pending",
                        "remaining_checks": ["targeted tests first"],
                        "checkpoint_ready": False,
                    },
                    "operator_control": {
                        "next_recommended_action": "execute",
                        "runbook_recovery_lane": "approved_plan_ready",
                        "approval_pause_state": False,
                        "clarify_pause_state": False,
                    },
                    "executes": False,
                },
                "usage_cost": {
                    "measurement_status": "placeholder",
                    "source": "control_plane_placeholder",
                },
            },
        )
    )

    print_team_runbook(
        session,
        pick_primary_action=pick_primary_action,
        build_operator_runbook=lambda current_session: [
            f"Execute approved plan for {current_session.to_dict()['id']}",
            "Inspect the execution record after completion",
        ],
    )
    out = capsys.readouterr().out

    assert "status: approved_for_execution" in out
    assert "phase: approved" in out
    assert "next: execute" in out
    assert "reason: plan is ready to execute" in out
    assert "next_command: python -m agent_orchestrator.cli team execute session-123 --mode success_first" in out
    assert "decision_rationale: approved plan exists | no blocking gaps remain" in out
    assert "control_plane_governance: Execute approved plan" in out
    assert "control_plane_governance_focus: state_context_strategy_topology_approval_evidence_memory_recovery" in out
    assert "control_plane_governance_topology_policy: work can proceed without adversarial depth" in out
    assert "control_plane_governance_recovery_policy: execute" in out
    assert "control_plane_governance_verification: targeted tests first" in out
    assert "control_plane_governance_planner_intent: explore=False clarify=False edit=True verify=True pause=False handoff=False fallback=False native_first=True priority=execute,verify" in out
    assert "control_plane_governance_adapter_shared_contract: format=agent_orchestrator.adapter_shared_contract.v1 comparison_mode=same_contract_two_executors default_path=native boundary=native_preferred approval_required=False hot_plug_supported=True evidence_outputs=strategy_decision,run_ledger,evidence_bundle recovery_surfaces=plan_session,approval_state,recovery_timeline" in out
    assert "control_plane_governance_program_continuity: resume_supported=True resume_kind=execute continuity_status=projected recovery_hint=plan is ready to execute" in out
    assert "control_plane_governance_milestone_verification: status=pending checkpoint_ready=False remaining_checks=1" in out
    assert "control_plane_governance_operator_control: next_action=execute recovery_lane=approved_plan_ready approval_pause=False clarify_pause=False" in out
    assert "control_plane_governance_usage_cost: measurement_status=placeholder source=control_plane_placeholder" in out
    assert "operator_runbook:" in out
    assert "1. Execute approved plan for session-123" in out
    assert "2. Inspect the execution record after completion" in out


def test_print_workspace_state_summary_reports_comparative_benchmark_and_learning_consumption(capsys) -> None:
    print_workspace_state_summary(
        {
            "format": "agent_orchestrator.workspace_index.v1",
            "workspace_state": {
                "format": "agent_orchestrator.workspace_state.v1",
                "project_root": "/tmp/demo",
                "plans": [],
                "runs": [],
                "jobs": [],
                "approvals": [],
                "dirty_state": {"dirty": False, "count": 0},
                "external_cache": {"status": "disabled"},
            },
            "program": {"name": "demo", "active_plan_count": 1, "open_approval_count": 0},
            "comparative_benchmark": {
                "format": "agent_orchestrator.comparative_benchmark_summary.v1",
                "native_default_path": True,
                "comparative_acceptance_bundle_ready": False,
                "native_repo_task_acceptance_ready": False,
                "native_complex_repo_task_acceptance_ready": False,
                "long_chain_native_first_ready": False,
                "native_task_class": "bounded_internal_repo_task",
                "native_coverage_class": "investigation_to_edit_verify",
                "learning_consumed": True,
                "shared_contract_alignment": {
                    "session_continuity_ready": True,
                    "runtime_cost_ready": True,
                    "native_tool_usage_ready": True,
                    "planner_evidence_ready": True,
                    "adapter_contract_ready": True,
                },
                "shared_productization_contract_ready": True,
                "comparison_posture_basis": {
                    "shared_productization_contract_ready": True,
                    "long_chain_daily_driver_case_ready": False,
                    "evidence_scope": "bounded_internal_evidence_only",
                    "basis_surface_refs": [
                        "shared_contract_alignment",
                        "shared_productization_contract_ready",
                    ],
                    "comparison_limitations": [
                        "no_authoritative_external_opencode_harness",
                    ],
                },
                "comparison_proof_strength": {
                    "direct_proof_status": "foundational_productization_only",
                    "repeatability_status": "not_yet_proven",
                    "repeatability_ready": False,
                    "stronger_task_family_count": 0,
                    "broader_task_family_count": 0,
                    "stronger_task_families": [],
                    "repo_task_acceptance_families_proven": [
                        "compliance_process_repo_task",
                        "helper_implementation_repo_task",
                        "long_chain_native_first_repo_task",
                        "multi_file_operator_surface_repo_task",
                    ],
                    "repo_task_acceptance_family_count": 4,
                    "daily_driver_repo_task_families_proven": [
                        "compliance_process_repo_task",
                        "helper_implementation_repo_task",
                        "long_chain_native_first_repo_task",
                        "multi_file_operator_surface_repo_task",
                    ],
                    "daily_driver_repo_task_family_count": 4,
                    "broader_repeatability_gap_families": [
                        "multi_family_daily_driver_repo_tasks",
                    ],
                    "proof_limitations": [
                        "single_stronger_long_chain_repo_task_family",
                        "no_repeatable_multi_family_daily_driver_proof",
                    ],
                },
                "comparison_posture": {
                    "status": "shared_productization_ready_but_daily_driver_proof_gap_remaining",
                    "confidence": "bounded_internal_evidence_only",
                    "foundation_gap_remaining": False,
                    "remaining_gap_classes": [
                        "long_chain_repo_closure_repeatability",
                        "multi_family_daily_driver_repeatability",
                        "platform_breadth",
                        "plugin_ecosystem",
                        "wider_general_task_coverage",
                        ],
                    },
                    "planner_closure_posture": {
                        "format": "agent_orchestrator.planner_closure_posture.v1",
                        "closure_mode": "approval_pause",
                        "next_recommended_action": "verify",
                        "resume_posture": None,
                        "verify_selected": None,
                        "verification_status": None,
                    },
                    "comparative_session_posture_summary": {
                        "format": "agent_orchestrator.comparative_session_posture_summary.v1",
                        "primary_action": "explore",
                        "pause_expected": True,
                        "handoff_expected": False,
                        "fallback_expected": False,
                        "clarify_pause_state": False,
                        "approval_pause_state": True,
                        "resume_expectation": "approval_pause",
                        "resume_posture": None,
                        "next_recommended_action": "verify",
                        "runbook_recovery_lane": "rerun_verify",
                        "compaction_stage": "light_compaction",
                        "compaction_pressure": None,
                    },
                        "comparison_grade_assessment": {
                            "status": "internal_productization_ready_but_repeatability_or_external_gap_remaining",
                            "comparison_grade_ready": False,
                        "internal_repeatability_ready": False,
                        "external_harness_ready": False,
                    "blocking_gap": "no_authoritative_external_opencode_harness",
                },
                    "external_comparison_harness_surface": {
                        "format": "agent_orchestrator.external_comparison_harness_surface.v1",
                        "harness_status": "missing_authoritative_opencode_harness",
                    "authoritative": False,
                    "next_evidence_milestone": "authoritative_opencode_case_harness",
                    "operator_action": "maintain_human_audit_until_external_harness_ready",
                    "requirements": {
                        "missing_external_artifacts": [
                            "authoritative_opencode_case_harness",
                            "same_contract_executor_comparison",
                            "governed_recovery_and_cost_comparison",
                            ],
                        },
                    },
                    "operator_tool_digest": {
                        "format": "agent_orchestrator.operator_tool_digest.v1",
                        "tooling_posture": "daily_driver_ready",
                        "recent_tools": ["repo_map", "search", "read"],
                        "explore_tools": ["repo_map", "search", "read"],
                        "edit_tools": ["patch_preview", "structured_patch", "diff_preview"],
                        "verify_tools": ["verify", "tool_trace"],
                        "daily_driver_tools": [
                            "repo_map",
                            "search",
                            "read",
                            "patch_preview",
                            "structured_patch",
                            "diff_preview",
                            "verify",
                        ],
                    },
                    "comparative_planner_autonomy_summary": {
                        "format": "agent_orchestrator.comparative_planner_autonomy_summary.v1",
                        "planner_family": "native",
                        "selected_strategy": "explore_then_edit",
                        "selected_owner": "native",
                        "primary_action": "explore",
                        "native_first": True,
                        "autonomy_boundary": {
                            "native_first": True,
                            "requires_clarify": False,
                            "requires_pause": False,
                            "requires_handoff": False,
                            "requires_fallback": False,
                            "requires_explore": True,
                            "requires_edit": True,
                            "requires_verify": True,
                        },
                        "planner_reasoning": {
                            "native_first": True,
                            "primary_action": "explore",
                            "requires_edit": True,
                            "requires_verify": True,
                        },
                        "autonomy_surface": {
                            "format": "agent_orchestrator.native_planner_autonomy_surface.v1",
                            "decision_mode": "native_first_autonomous",
                            "primary_action": "explore",
                            "selected_action_count": 3,
                        },
                        "decision_boundary": {
                            "task_type": "direct_fix",
                            "risk_level": "medium",
                            "route_task_kind": "DIRECT_FIX",
                            "requires_human_confirmation": False,
                        },
                        "next_recommended_action": "verify",
                        "resume_posture": None,
                        "summary": "native-first planner stays on explore/edit/verify while avoiding clarify/pause/handoff/fallback",
                        "shared_evidence_surface": [
                            "runtime_payload",
                            "workspace_index",
                            "ui_execution_summary",
                            "cli_execution_summary",
                            "evidence_report",
                        ],
                    },
                    "comparative_session_continuity_summary": {
                        "format": "agent_orchestrator.comparative_session_continuity_summary.v1",
                        "continuity_status": "ready",
                        "resume_supported": True,
                        "resume_kind": None,
                        "resume_ready": True,
                        "resume_posture": "same_task_resume",
                        "recovery_ready": True,
                        "recovery_active": False,
                        "verification_resume_ready": False,
                        "compaction_ready": True,
                        "compaction_stage": "light_compaction",
                        "compaction_pressure": "light_compaction",
                        "context_pressure": True,
                        "summarization_ready": False,
                        "pressure_visible": True,
                        "pending_followup_count": 2,
                        "runtime_cost_ready": True,
                        "runtime_duration_seconds": 0.8,
                        "usage_cost_measurement_status": "placeholder",
                        "runtime_cost_provenance": {
                            "format": "agent_orchestrator.runtime_cost_provenance.v1",
                            "duration_source": "native_tool_trace",
                        },
                        "next_recommended_action": "verify",
                        "runbook_recovery_lane": "rerun_verify",
                        "latest_recovery_hint": "retry verify after review",
                        "planner_governed_alternatives": [],
                        "summary": "status=ready",
                        "shared_evidence_surface": [
                            "runtime_event_stream",
                            "session_continuity",
                            "session_productization_surface",
                            "runtime_cost",
                            "runtime_cost_provenance",
                            "workspace_index",
                            "ui_execution_summary",
                            "cli_execution_summary",
                            "evidence_report",
                        ],
                    },
                    "comparative_native_closure_summary": {
                        "format": "agent_orchestrator.comparative_native_closure_summary.v1",
                        "native_runtime_only": True,
                        "external_coding_agent_required": False,
                        "task_class": "bounded_internal_repo_task",
                        "proof_scenario": "approval_pause_resume_complete",
                        "closure_status": "blocked",
                        "artifact_count": 1,
                        "event_count": 9,
                        "verification_status": "pending",
                        "verification_failure_kind": None,
                        "repair_outcome": None,
                        "recovery_action": "verify",
                        "recovery_reason": "rerun_verify",
                        "proof_ready": False,
                        "summary": "native_runtime_only=True",
                        "shared_evidence_surface": [
                            "runtime_payload",
                            "native_task_proof",
                            "verification",
                            "recovery_summary",
                            "workspace_index",
                            "ui_execution_summary",
                            "cli_execution_summary",
                            "evidence_report",
                        ],
                    },
                    "shared_evidence_surface": [
                    "runtime_event_stream",
                    "session_continuity",
                    "session_productization_surface",
                    "planner_closure_posture",
                    "native_tool_productization_surface",
                    "adapter_productization_surface",
                    "adapter_capability_surface",
                    "workspace_index",
                    "ui_execution_summary",
                    "cli_execution_summary",
                    "adapter_shared_contract",
                    "planner_shared_contract",
                    "evidence_report",
                ],
            },
            "native_exploration": {
                "existing_path_count": 1,
                "candidate_path_count": 3,
                "file_count": 12,
                "repo_map_directory_count": 4,
                "candidate_reason": "search_matches",
                "selected_candidates": ["src/app.py", "README.md"],
                "exploration_evidence": {
                    "format": "agent_orchestrator.native_exploration_evidence.v1",
                    "candidate_reason": "search_matches",
                    "search_match_count": 2,
                    "read_record_count": 2,
                    "search_match_paths": ["src/app.py", "README.md"],
                    "read_paths": ["src/app.py", "README.md"],
                    "shared_evidence_surface": [
                        "runtime_payload",
                        "workspace_index",
                        "ui_execution_summary",
                        "cli_execution_summary",
                    ],
                },
            },
            "execution_artifact_summary": {
                "session_continuity": {
                    "resume_supported": True,
                    "compaction_stage": "light_compaction",
                    "summarization_triggered": False,
                    "runtime_duration_seconds": 0.8,
                    "usage_cost_measurement_status": "placeholder",
                    "continuity_snapshot": {
                        "format": "agent_orchestrator.session_continuity_snapshot.v1",
                        "snapshot_status": "ready",
                        "artifact_backed": True,
                        "program_digest": {
                            "program_goal": "Ship dashboard",
                            "active_milestone": "verify",
                            "pending_followup_count": 2,
                        },
                        "compaction_digest": {
                            "compaction_stage": "light_compaction",
                        },
                    },
                "session_productization_surface": {
                    "format": "agent_orchestrator.session_productization_surface.v1",
                    "continuity_status": "ready",
                    "continuity_readiness": {
                        "resume_ready": True,
                            "runtime_cost_ready": True,
                            "compaction_ready": True,
                            "recovery_ready": True,
                        },
                        "operator_continuity": {
                            "next_recommended_action": "verify",
                        },
                    },
                    "shared_evidence_surface": [
                        "runtime_payload",
                        "workspace_index",
                        "ui_execution_summary",
                        "cli_execution_summary",
                        "docs_evidence",
                    ],
                    "long_horizon_posture": {
                        "resume_ready": True,
                        "recovery_active": False,
                        "verification_resume_ready": False,
                        "context_pressure": True,
                        "summarization_ready": False,
                        "resume_posture": "same_task_resume",
                    },
                    "program_posture": {
                        "program_goal": "Ship dashboard",
                        "active_milestone": "verify",
                        "completed_milestones": ["explore", "edit"],
                        "ready_next_units": ["checkpoint", "continue"],
                        "blocked_units": [],
                    },
                        "program_continuity": {
                            "resume_supported": True,
                            "resume_kind": None,
                            "compaction_stage": "light_compaction",
                            "continuity_artifact_status": "ready",
                        "latest_recovery_hint": None,
                        "repo_task_acceptance_ready": False,
                        "complex_repo_task_acceptance_ready": False,
                        "long_chain_native_first_ready": False,
                        "closure_strength": "runtime_closure_only",
                            "shared_evidence_surface": [
                                "runtime_payload",
                                "workspace_index",
                                "ui_execution_summary",
                                "cli_execution_summary",
                                "docs_evidence",
                            ],
                        },
                        "daily_driver_readiness": {
                            "tool_surface_ready": True,
                            "planner_ready": True,
                            "session_ready": True,
                            "adapter_ready": True,
                            "shared_productization_ready": True,
                            "long_chain_task_ready": False,
                            "daily_driver_main_path_ready": False,
                            "open_product_gap": "long_chain_repo_closure_not_yet_proven",
                        },
                        "delegation_contract": {
                            "selected_executor": "native",
                            "ownership_boundary": "native_preferred",
                            "handoff_reason_code": None,
                            "fallback_reason_code": None,
                        "required_handoff_artifacts": ["execution_result", "structured_observations"],
                    },
                    "milestone_verification": {
                        "verification_status": "pending",
                        "checkpoint_ready": False,
                        "remaining_checks": ["pytest -q"],
                    },
                    "operator_control": {
                        "next_recommended_action": "verify",
                        "runbook_recovery_lane": "rerun_verify",
                        "approval_pause_state": True,
                        "clarify_pause_state": False,
                    },
                },
                "runtime_cost": {
                    "duration_seconds": 0.8,
                    "usage_cost_measurement_status": "placeholder",
                },
                "compacted_context_summary": {
                    "objective": "Ship dashboard",
                    "current_status": "blocked",
                    "compaction_stage": "light_compaction",
                    "masked_observation_count": 1,
                    "pending_step_count": 2,
                    "latest_recovery_hint": "retry verify after review",
                },
                "native_tool_usage": {
                    "tool_count": 9,
                    "trace_count": 4,
                    "recent_tools": ["repo_map", "diff_preview", "verify"],
                },
                    "native_tool_surface": {
                        "format": "agent_orchestrator.native_tool_surface.v1",
                        "daily_driver_readiness": {
                            "repo_exploration_ready": True,
                            "structured_patch_ready": True,
                            "patch_preview_ready": True,
                            "diff_preview_ready": True,
                            "verification_ready": True,
                        },
                        "capability_profile": {
                            "patch_preview": {"purpose": "pre-apply bounded mutation preview for operator-visible review"},
                            "structured_patch": {"purpose": "auditable bounded mutations with preview evidence"},
                            "diff_preview": {"purpose": "governed bounded change preview for operator-visible review"},
                            "verify": {"purpose": "governed command verification"},
                        },
                    },
                    "adapter_capability": {
                        "format": "agent_orchestrator.adapter_capability_surface.v1",
                        "comparison_mode": "same_contract_two_executors",
                        "hot_plug_supported": True,
                        "evidence_outputs": ["execution_result", "runtime_event_stream"],
                        "recovery_surfaces": ["state_store", "resume_contract"],
                        "shared_contract_recovery_contract": {
                            "continue_allowed": True,
                            "scope_realign_required": False,
                            "fallback_allowed": True,
                            "handoff_allowed": True,
                            "remaining_budget_preserved": True,
                            "resume_continuity_required": True,
                        },
                        "shared_evidence_surface": [
                            "runtime_payload",
                            "workspace_index",
                            "ui_execution_summary",
                            "cli_execution_summary",
                            "evidence_report",
                        ],
                    },
                    "adapter_shared_contract": {
                        "adapter_family": "native_first_party",
                    "agent_kind": "coding_agent",
                    "default_path": "native",
                    "operating_boundary": "native_preferred",
                    "comparison_mode": "same_contract_two_executors",
                    "hot_plug_supported": True,
                    "fallback_governed": True,
                    "approval_required": True,
                    "shared_contract_format": "agent_orchestrator.adapter_shared_contract.v1",
                    "shared_contract_resume_supported": True,
                    "evidence_outputs": ["execution_result", "structured_observations"],
                    "recovery_surfaces": ["state_store", "resume_contract"],
                    "recovery_contract": {
                        "continue_allowed": True,
                        "scope_realign_required": False,
                        "fallback_allowed": True,
                        "handoff_allowed": True,
                        "remaining_budget_preserved": True,
                        "resume_continuity_required": True,
                    },
                },
                    "planner_shared_contract": {
                        "planner_family": "native",
                        "format": "agent_orchestrator.native_planner_decision.v1",
                        "selected_strategy": "explore_then_edit",
                        "selected_owner": "native",
                        "native_work_units": True,
                        "selected_actions": ["explore", "edit", "verify"],
                        "decision_candidates": ["explore_then_edit", "direct_edit"],
                        "autonomy_surface": {
                            "format": "agent_orchestrator.native_planner_autonomy_surface.v1",
                            "decision_mode": "native_first_autonomous",
                            "primary_action": "explore",
                            "selected_action_count": 3,
                            "actions": {
                                "explore": {"selected": True},
                                "clarify": {"selected": False},
                                "edit": {"selected": True},
                                "verify": {"selected": True},
                                "pause": {"selected": False},
                                "handoff": {"selected": False},
                                "fallback": {"selected": False},
                            },
                        },
                        "autonomy_boundary": {
                            "native_first": True,
                            "requires_clarify": False,
                            "requires_pause": False,
                            "requires_handoff": False,
                            "requires_fallback": False,
                            "requires_explore": True,
                            "requires_edit": True,
                            "requires_verify": True,
                        },
                        "planner_reasoning": {
                            "native_first": True,
                            "primary_action": "explore",
                            "requires_edit": True,
                            "requires_verify": True,
                        },
                        "decision_boundary": {
                            "task_type": "direct_fix",
                            "risk_level": "medium",
                            "route_task_kind": "DIRECT_FIX",
                        "requires_human_confirmation": False,
                    },
                    "route_intent_alignment": {
                        "explore": True,
                        "verify": True,
                    },
                    "route_planner_intent": {
                        "priority": ["explore", "edit", "verify"],
                    },
                },
            },
            "execution_fact_chain": {
                "format": "agent_orchestrator.execution_fact_chain.v1",
                "current_status": "blocked",
                "active_stage": "verify",
                "verification_status": "failed",
                "approval_pause_state": True,
                "resume_supported": True,
                "next_recommended_action": "human_review",
                "closure_status": "blocked",
            },
            "clarify_boundary_digest": {
                "format": "agent_orchestrator.clarify_boundary_digest.v1",
                "status": "planner_clarify_boundary",
                "selected_execution_strategy": "clarify_then_edit",
                "next_recommended_action": "clarify_scope",
                "resume_expectation": "clarify_scope",
                "recovery_lane": "continue_native",
            },
            "approval_boundary_digest": {
                "format": "agent_orchestrator.approval_boundary_digest.v1",
                "status": "planner_approval_boundary",
                "selected_execution_strategy": "need_human_confirmation",
                "next_recommended_action": "human_review",
                "resume_expectation": "approval_pause",
                "recovery_lane": "approval_pause",
            },
            "learning_consumption_ready": True,
        }
    )

    out = capsys.readouterr().out

    assert "workspace_index: agent_orchestrator.workspace_index.v1" in out
    assert "comparative_benchmark: native_default=True bundle_ready=False acceptance_ready=False complex_acceptance_ready=False long_chain_ready=False daily_driver_ready=False task_class=bounded_internal_repo_task coverage_class=investigation_to_edit_verify learning_consumed=True shared_surface=runtime_event_stream,session_continuity,session_productization_surface,planner_closure_posture,native_tool_productization_surface,adapter_productization_surface,adapter_capability_surface,workspace_index,ui_execution_summary,cli_execution_summary,adapter_shared_contract,planner_shared_contract,evidence_report" in out
    assert "comparative_contract_alignment: session=True runtime_cost=True tool_usage=True planner=True adapter=True" in out
    assert "comparative_shared_productization_contract_ready: True" in out
    assert "comparative_benchmark_digest: cases=None productization_cases=None comparison_status=shared_productization_ready_but_daily_driver_proof_gap_remaining direct_proof=foundational_productization_only repeatability=not_yet_proven daily_driver_repeatability_tier=None daily_driver_cases=None comparison_grade_status=internal_productization_ready_but_repeatability_or_external_gap_remaining external_harness_status=missing_authoritative_opencode_harness required_shared_surface_count=None required_external_artifact_count=None missing_external_artifact_count=None session_posture_cases=None remaining_gaps=long_chain_repo_closure_repeatability,multi_family_daily_driver_repeatability,platform_breadth,plugin_ecosystem,wider_general_task_coverage shared_surface=runtime_event_stream,session_continuity,session_productization_surface,planner_closure_posture,native_tool_productization_surface,adapter_productization_surface,adapter_capability_surface,workspace_index,ui_execution_summary,cli_execution_summary,adapter_shared_contract,planner_shared_contract,evidence_report" in out
    assert "comparative_planner_closure: mode=approval_pause next_action=verify resume_posture=None verify_selected=None verification_status=None" in out
    assert "comparative_native_tool_summary: posture=daily_driver_ready read_search=True patch=True verify=True daily_driver=repo_map,search,read,patch_preview,structured_patch,diff_preview,verify" in out
    assert "comparative_adapter_summary: status=same_contract_two_executors_governed comparison_mode=same_contract_two_executors hot_plug=True fallback_governed=True resume_supported=True recovery_ready=True default_path=native boundary=native_preferred unified_contract=False" in out
    assert "comparative_session_posture_summary: primary=explore" in out
    assert "workflow_stage=verify" in out
    assert "workflow_projection_ready=True" in out
    assert "comparative_session_continuity_summary: status=ready" in out
    assert "resume_posture=same_task_resume" in out
    assert "runtime_duration_seconds=0.8" in out
    assert "duration_source=native_tool_trace" in out
    assert "workflow_resume_ready=True" in out
    assert "workflow_projection_visible=True" in out
    assert "workflow_recovery_aligned=True" in out
    assert "comparative_native_closure_summary: native_runtime_only=True closure_status=blocked verification_status=pending repair_outcome=None proof_ready=False proof_scenario=approval_pause_resume_complete" in out
    assert "comparative_operator_posture_digest: next_action=verify recovery_lane=rerun_verify resume_expectation=approval_pause resume_posture=None approval_boundary_active=None" in out
    assert "comparative_planner_autonomy_summary: native_first=True primary=explore clarify=False pause=False handoff=False fallback=False explore=True edit=True verify=True next_action=verify" in out
    assert "comparative_planner_candidate_summary: native_first=True selected=explore_then_edit candidates=" in out
    assert "decision_mode=" in out
    assert "autonomy_actions=" in out
    assert "alternatives=none" in out
    assert "comparative_operator_tool_digest: posture=daily_driver_ready" in out
    assert "comparative_posture_basis: shared_productization_ready=True daily_driver_case_ready=False evidence_scope=bounded_internal_evidence_only basis_refs=shared_contract_alignment,shared_productization_contract_ready limitations=no_authoritative_external_opencode_harness" in out
    assert "comparative_proof_strength: direct_proof=foundational_productization_only repeatability=not_yet_proven repeatability_ready=False daily_driver_repeatability_tier=None stronger_task_families=0 broader_task_families=0 stronger_family_names=none repo_task_acceptance_family_count=4 repo_task_acceptance_families=compliance_process_repo_task,helper_implementation_repo_task,long_chain_native_first_repo_task,multi_file_operator_surface_repo_task daily_driver_repo_task_family_count=4 daily_driver_repo_task_families=compliance_process_repo_task,helper_implementation_repo_task,long_chain_native_first_repo_task,multi_file_operator_surface_repo_task independent_daily_driver_repo_task_family_count=None independent_daily_driver_repo_task_families=none broader_repeatability_gap_families=multi_family_daily_driver_repo_tasks limitations=single_stronger_long_chain_repo_task_family,no_repeatable_multi_family_daily_driver_proof" in out
    assert "comparative_posture: status=shared_productization_ready_but_daily_driver_proof_gap_remaining confidence=bounded_internal_evidence_only foundation_gap_remaining=False remaining_gaps=long_chain_repo_closure_repeatability,multi_family_daily_driver_repeatability,platform_breadth,plugin_ecosystem,wider_general_task_coverage" in out
    assert "execution_fact_chain: status=blocked stage=verify verification=failed approval_pause=True resume_supported=True next_action=human_review closure=blocked" in out
    assert "clarify_boundary_digest: status=planner_clarify_boundary strategy=clarify_then_edit next_action=clarify_scope resume_expectation=clarify_scope recovery_lane=continue_native" in out
    assert "approval_boundary_digest: status=planner_approval_boundary strategy=need_human_confirmation next_action=human_review resume_expectation=approval_pause recovery_lane=approval_pause" in out
    assert "comparative_grade_assessment: status=internal_productization_ready_but_repeatability_or_external_gap_remaining comparison_grade_ready=False internal_repeatability_ready=False external_harness_ready=False blocking_gap=no_authoritative_external_opencode_harness" in out
    assert "comparative_harness_surface: format=agent_orchestrator.external_comparison_harness_surface.v1 status=missing_authoritative_opencode_harness authoritative=False next_milestone=authoritative_opencode_case_harness operator_action=maintain_human_audit_until_external_harness_ready missing_external_artifacts=authoritative_opencode_case_harness,same_contract_executor_comparison,governed_recovery_and_cost_comparison" in out
    assert "native_exploration: existing=1 candidates=3 files=12 repo_map_dirs=4 reason=search_matches selected=src/app.py,README.md" in out
    assert "native_exploration_evidence: reason=search_matches search_matches=2 read_records=2 search_paths=src/app.py,README.md read_paths=src/app.py,README.md shared_surface=runtime_payload,workspace_index,ui_execution_summary,cli_execution_summary" in out
    assert "session_continuity: resume_supported=True compaction_stage=light_compaction summarization_triggered=False resume_kind=None" in out
    assert "continuity_snapshot: status=ready artifact_backed=True goal=Ship dashboard active=verify pending=2 compaction=light_compaction" in out
    assert "daily_driver_readiness: tool_surface=True planner=True session=True adapter=True shared_productization=True long_chain=False main_path=False gap=long_chain_repo_closure_not_yet_proven" in out
    assert "session_productization_surface: format=agent_orchestrator.session_productization_surface.v1 status=ready resume_ready=True runtime_cost_ready=True compaction_ready=True recovery_ready=True next_action=verify" in out
    assert "operator_posture_digest: status=" in out
    assert "compaction_stage=light_compaction" in out
    assert "resume_posture=None alternatives=none" in out
    assert "operator_tool_digest: posture=daily_driver_ready" in out
    assert "operator_planner_digest: primary=" in out
    assert "shared_productization_surface: format=agent_orchestrator.shared_productization_surface.v1 status=shared_productization_contract_ready shared_ready=True session_ready=True tool_ready=True adapter_ready=True planner_ready=True" in out
    assert "native_tool_workflow: explore=repo_map,search,read edit=patch_preview,structured_patch,diff_preview verify=verify,tool_trace daily_driver=repo_map,search,read,patch_preview,structured_patch,diff_preview,verify" in out
    assert "native_tool_workflow_surface" in out
    assert "long_horizon_posture: resume_ready=True recovery_active=False verification_resume_ready=False context_pressure=True summarization_ready=False" in out
    assert "program_posture: goal=Ship dashboard active_milestone=verify completed=explore,edit ready=checkpoint,continue blocked=none" in out
    assert "delegation_contract: executor=native boundary=native_preferred handoff_reason=None fallback_reason=None artifacts=execution_result,structured_observations" in out
    assert "milestone_verification: status=pending checkpoint_ready=False remaining=pytest -q" in out
    assert "operator_control: next_action=verify recovery_lane=rerun_verify approval_pause=True clarify_pause=False" in out
    assert "runtime_cost: duration_seconds=0.8 usage_cost_status=placeholder" in out
    assert "compacted_context: objective=Ship dashboard status=blocked compaction_stage=light_compaction masked=1 pending_steps=2 recovery_hint=retry verify after review" in out
    assert "native_tool_usage: tool_count=9 trace_count=4 recent=repo_map,diff_preview,verify" in out
    assert "native_tool_surface: format=agent_orchestrator.native_tool_surface.v1 repo_exploration_ready=True glob_ready=True structured_patch_ready=True patch_preview_ready=True diff_preview_ready=True verification_ready=True" in out
    assert "native_tool_productization_surface: format=agent_orchestrator.native_tool_productization_surface.compat.v1 posture=daily_driver_ready operator_visible=True read_search=True glob=True patch=True verify=True" in out
    assert "native_tool_capabilities: patch_preview=pre-apply bounded mutation preview for operator-visible review structured_patch=auditable bounded mutations with preview evidence diff_preview=governed bounded change preview for operator-visible review verify=governed command verification" in out
    assert "planner_shared_contract: family=native format=agent_orchestrator.native_planner_decision.v1 strategy=explore_then_edit owner=native native_work_units=True actions=explore,edit,verify route_intent=explore,edit,verify" in out
    assert "planner_autonomy_surface: format=agent_orchestrator.native_planner_autonomy_surface.v1 mode=native_first_autonomous primary=explore clarify=False pause=False handoff=False fallback=False" in out
    assert "planner_autonomy_boundary: native_first=True clarify=False pause=False handoff=False fallback=False explore=True edit=True verify=True" in out
    assert "planner_decision_surface: candidates=explore_then_edit,direct_edit task_type=direct_fix risk=medium route_task_kind=DIRECT_FIX requires_confirmation=False intent_alignment_explore=True intent_alignment_verify=True" in out
    assert "adapter_capability: format=agent_orchestrator.adapter_capability_surface.v1 comparison_mode=same_contract_two_executors hot_plug_supported=True evidence_outputs=execution_result,runtime_event_stream recovery_surfaces=state_store,resume_contract shared_evidence_surface=runtime_payload,workspace_index,ui_execution_summary,cli_execution_summary,evidence_report" in out
    assert "adapter_shared_contract: family=native_first_party kind=coding_agent default_path=native boundary=native_preferred comparison_mode=same_contract_two_executors hot_plug_supported=True approval_required=True evidence_outputs=execution_result,structured_observations recovery_surfaces=state_store,resume_contract" in out
    assert "adapter_productization_surface: format=agent_orchestrator.adapter_productization_surface.compat.v1 status=same_contract_two_executors_governed comparison_mode=same_contract_two_executors hot_plug_supported=True fallback_governed=True resume_supported=True recovery_ready=True" in out
    assert "learning_consumption: yes" in out


def test_print_execution_session_summary_reports_structured_fields(capsys) -> None:
    print_execution_session_summary(
        {
            "session_summary": {
                "session_id": "session-123",
                "run_id": "run-456",
                "outcome": "needs_followup",
                "goal": "Ship dashboard",
                "selected_topology": "team",
                "selected_provider_runtime": {"provider": "codex", "runtime": "command"},
                "clarify_summary": {
                    "task_type": "investigation",
                    "slot_sources": {"task_type": "llm", "goal": "rule"},
                    "unknown_slots": ["target_scope", "risk_signals"],
                    "slot_fill_warnings": ["slot_fill_response_partial"],
                },
                "decomposition_summary": {
                    "selected_strategy": "migration_pipeline",
                    "selected_shape": "migration_pipeline",
                    "selected_score": 42,
                    "candidate_count": 2,
                    "rejected_strategies": ["risk_trimmed_pipeline"],
                },
                "execution_context_policy": {
                    "policy": "resume_if_same_task",
                    "resume_target": "run-456",
                    "stop_reason": "execution_completed",
                },
                "session_continuity": {
                    "resume_supported": True,
                    "resume_kind": "fresh",
                    "compaction_stage": "light_compaction",
                    "runtime_duration_seconds": 1.25,
                    "usage_cost_measurement_status": "placeholder",
                    "continuity_snapshot": {
                        "format": "agent_orchestrator.session_continuity_snapshot.v1",
                        "snapshot_status": "ready",
                        "artifact_backed": True,
                        "program_digest": {
                            "program_goal": "Ship dashboard",
                            "active_milestone": "verify",
                            "pending_followup_count": 1,
                        },
                        "compaction_digest": {
                            "compaction_stage": "light_compaction",
                        },
                    },
                    "session_productization_surface": {
                        "format": "agent_orchestrator.session_productization_surface.v1",
                        "continuity_status": "ready",
                        "continuity_readiness": {
                            "resume_ready": True,
                            "runtime_cost_ready": True,
                            "compaction_ready": True,
                            "recovery_ready": False,
                        },
                    "operator_continuity": {
                        "next_recommended_action": "inspect_execution",
                    },
                    "autonomy_posture": {
                        "pause_expected": False,
                        "handoff_expected": False,
                        "fallback_expected": False,
                        "resume_posture": "same_task_resume",
                    },
                },
                },
                "session_planner_decision": {
                    "format": "agent_orchestrator.session_planner_snapshot.v1",
                    "planner_family": "native",
                    "selected_execution_strategy": "explore_then_edit",
                    "primary_action": "explore",
                    "selected_owner": "native",
                    "autonomy_posture": {
                        "pause_expected": False,
                        "handoff_expected": False,
                        "fallback_expected": False,
                        "clarify_pause_state": False,
                        "approval_pause_state": False,
                    },
                    "delegation_contract": {
                        "resume_expectation": "resume_if_same_task",
                    },
                    "tool_workflow_plan": {
                        "format": "agent_orchestrator.native_tool_workflow_plan.v1",
                        "workflow_projection_required": True,
                        "workflow_stages": {
                            "explore": {"selected": True},
                            "edit": {"selected": True},
                            "verify": {"selected": True},
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
                        },
                    },
                },
                "planner_control_surface": {
                    "format": "agent_orchestrator.session_planner_control_surface.v1",
                    "decision_mode": "native_first_autonomous",
                    "continue_native": True,
                    "clarify": False,
                    "pause": False,
                    "handoff": False,
                    "fallback": False,
                    "resume_posture": "continue_native",
                    "next_recommended_action": "explore",
                },
                "session_continuity_outline": {
                    "format": "agent_orchestrator.session_continuity_outline.v1",
                    "planner_family": "native",
                    "resume_kind": "fresh",
                    "goal": "Ship dashboard",
                    "active_milestone": "verify",
                    "next_recommended_action": "inspect_execution",
                    "resume_expectation": "resume_if_same_task",
                    "autonomy_posture": {
                        "pause_expected": False,
                        "handoff_expected": False,
                        "fallback_expected": False,
                    },
                },
                "native_tool_usage": {
                    "tool_count": 9,
                    "trace_count": 5,
                    "recent_tools": ["search", "diff_preview", "verify"],
                },
                "native_tool_surface": {
                    "format": "agent_orchestrator.native_tool_surface.v1",
                    "daily_driver_readiness": {
                        "repo_exploration_ready": True,
                        "structured_patch_ready": True,
                        "patch_preview_ready": True,
                        "diff_preview_ready": True,
                        "verification_ready": True,
                    },
                    "capability_profile": {
                        "patch_preview": {"purpose": "pre-apply bounded mutation preview for operator-visible review"},
                        "structured_patch": {"purpose": "auditable bounded mutations with preview evidence"},
                        "diff_preview": {"purpose": "governed bounded change preview for operator-visible review"},
                        "verify": {"purpose": "governed command verification"},
                    },
                },
                    "planner_shared_contract": {
                        "planner_family": "native",
                        "format": "agent_orchestrator.native_planner_decision.v1",
                        "selected_strategy": "explore_then_edit",
                        "selected_owner": "native",
                        "native_work_units": True,
                        "selected_actions": ["explore", "edit", "verify"],
                        "decision_candidates": ["explore_then_edit", "direct_edit"],
                        "autonomy_surface": {
                            "format": "agent_orchestrator.native_planner_autonomy_surface.v1",
                            "decision_mode": "native_first_autonomous",
                            "primary_action": "explore",
                            "selected_action_count": 3,
                            "actions": {
                                "explore": {"selected": True},
                                "clarify": {"selected": False},
                                "edit": {"selected": True},
                                "verify": {"selected": True},
                                "pause": {"selected": False},
                                "handoff": {"selected": False},
                                "fallback": {"selected": False},
                            },
                        },
                        "decision_boundary": {
                            "task_type": "direct_fix",
                            "risk_level": "medium",
                            "route_task_kind": "DIRECT_FIX",
                        "requires_human_confirmation": False,
                    },
                    "route_intent_alignment": {
                        "explore": True,
                        "verify": True,
                    },
                    "route_planner_intent": {
                        "priority": ["explore", "edit", "verify"],
                    },
                },
                "adapter_capability": {
                    "format": "agent_orchestrator.adapter_capability_surface.v1",
                    "comparison_mode": "same_contract_two_executors",
                    "hot_plug_supported": True,
                    "evidence_outputs": ["execution_result", "runtime_event_stream"],
                    "recovery_surfaces": ["state_store", "resume_contract"],
                    "shared_contract_recovery_contract": {
                        "continue_allowed": True,
                        "scope_realign_required": False,
                        "fallback_allowed": True,
                        "handoff_allowed": True,
                        "remaining_budget_preserved": True,
                        "resume_continuity_required": True,
                    },
                },
                "adapter_shared_contract": {
                    "adapter_family": "native_first_party",
                    "agent_kind": "coding_agent",
                    "default_path": "native",
                    "operating_boundary": "native_preferred",
                    "comparison_mode": "same_contract_two_executors",
                    "hot_plug_supported": True,
                    "fallback_governed": True,
                    "approval_required": True,
                    "shared_contract_format": "agent_orchestrator.adapter_shared_contract.v1",
                    "shared_contract_resume_supported": True,
                    "evidence_outputs": ["execution_result", "runtime_event_stream"],
                    "recovery_surfaces": ["state_store", "resume_contract"],
                },
                "blocking_reasons": ["migration check pending"],
                "warnings": ["header contract warning: src/agent_orchestrator/legacy.py has placeholder `RESPONSIBILITY` value"],
                "primary_action": "inspect_execution",
                "primary_reason": "review the execution outcome before continuing",
                "resume_action": "inspect_execution",
                "resume_reason": "execution_completed",
                "recommended_commands": [
                    "python -m agent_orchestrator.cli team inspect-execution session-123",
                ],
            }
        }
    )
    out = capsys.readouterr().out

    assert "session: session-123" in out
    assert "run: run-456" in out
    assert "execution_outcome: needs_followup" in out
    assert "goal: Ship dashboard" in out
    assert "selected_topology: team" in out
    assert 'selected_provider_runtime: {"provider": "codex", "runtime": "command"}' in out
    assert "clarify: task_type=investigation slot_sources=goal=rule,task_type=llm unknown_slots=target_scope,risk_signals warnings=slot_fill_response_partial" in out
    assert "decompose: selected=migration_pipeline shape=migration_pipeline score=42 candidate_count=2 rejected=risk_trimmed_pipeline" in out
    assert "execution_context_policy: policy=resume_if_same_task resume_target=run-456 stop_reason=execution_completed" in out
    assert "session_continuity: resume_supported=True resume_kind=fresh compaction_stage=light_compaction runtime_duration_seconds=1.25 usage_cost_status=placeholder" in out
    assert "session_planner_decision: format=agent_orchestrator.session_planner_snapshot.v1 planner_family=native strategy=explore_then_edit primary=explore owner=native candidates=" in out
    assert "session_planner_posture: pause_expected=False handoff_expected=False fallback_expected=False clarify_pause=False approval_pause=False resume_expectation=resume_if_same_task" in out
    assert "session_planner_workflow: format=agent_orchestrator.native_tool_workflow_plan.v1 projection_required=True explore_selected=True edit_selected=True verify_selected=True" in out
    assert "session_planner_control_surface: format=agent_orchestrator.session_planner_control_surface.v1 decision_mode=native_first_autonomous continue_native=True clarify=False pause=False handoff=False fallback=False resume_posture=continue_native" in out
    assert "session_continuity_outline: format=agent_orchestrator.session_continuity_outline.v1 planner_family=native resume_kind=fresh goal=Ship dashboard active=verify next=inspect_execution" in out
    assert "planner_closure_posture:" not in out or "next_action=inspect_execution" in out
    assert "session_continuity_posture: pause_expected=False handoff_expected=False fallback_expected=False resume_expectation=resume_if_same_task" in out
    assert "continuity_snapshot: status=ready artifact_backed=True goal=Ship dashboard active=verify pending=1 compaction=light_compaction" in out
    assert "session_productization_surface: format=agent_orchestrator.session_productization_surface.v1 status=ready resume_ready=True runtime_cost_ready=True compaction_ready=True recovery_ready=False next_action=inspect_execution" in out
    assert "session_productization_posture: pause_expected=False handoff_expected=False fallback_expected=False resume_posture=same_task_resume" in out
    assert "operator_posture_digest: status=ready compaction_stage=light_compaction" in out
    assert "resume_posture=None alternatives=none" in out
    assert "operator_tool_digest: posture=daily_driver_ready" in out
    assert "native_tool_usage: tool_count=9 trace_count=5 recent=search,diff_preview,verify" in out
    assert "native_tool_surface: format=agent_orchestrator.native_tool_surface.v1 repo_exploration_ready=True glob_ready=True structured_patch_ready=True patch_preview_ready=True diff_preview_ready=True verification_ready=True" in out
    assert "native_tool_workflow: explore=repo_map,search,read edit=patch_preview,structured_patch,diff_preview verify=verify,tool_trace daily_driver=repo_map,search,read,patch_preview,structured_patch,diff_preview,verify" in out
    assert "native_tool_workflow_surface" in out
    assert "native_tool_productization_surface: format=agent_orchestrator.native_tool_productization_surface.compat.v1 posture=daily_driver_ready operator_visible=True read_search=True glob=True patch=True verify=True" in out
    assert "native_tool_capabilities: patch_preview=pre-apply bounded mutation preview for operator-visible review structured_patch=auditable bounded mutations with preview evidence diff_preview=governed bounded change preview for operator-visible review verify=governed command verification" in out
    assert "planner_shared_contract: family=native format=agent_orchestrator.native_planner_decision.v1 strategy=explore_then_edit owner=native native_work_units=True actions=explore,edit,verify route_intent=explore,edit,verify" in out
    assert "planner_decision_surface: candidates=explore_then_edit,direct_edit task_type=direct_fix risk=medium route_task_kind=DIRECT_FIX requires_confirmation=False intent_alignment_explore=True intent_alignment_verify=True" in out


def test_print_execution_session_summary_reports_planner_closure_posture(capsys) -> None:
    print_execution_session_summary(
        {
            "session_summary": {
                "session_id": "session-321",
                "run_id": "run-654",
                "outcome": "completed",
                "goal": "Ship dashboard",
                "session_continuity": {
                    "resume_supported": True,
                    "resume_kind": "fresh",
                    "compaction_stage": "light_compaction",
                    "runtime_duration_seconds": 1.0,
                    "usage_cost_measurement_status": "placeholder",
                },
                "planner_closure_posture": {
                    "format": "agent_orchestrator.planner_closure_posture.v1",
                    "closure_mode": "planner_complete",
                    "verify_selected": False,
                    "verification_status": "passed",
                    "next_recommended_action": "inspect_execution",
                    "resume_posture": "same_task_resume",
                },
            }
        }
    )
    out = capsys.readouterr().out

    assert "planner_closure_posture: mode=planner_complete verify_selected=False verification_status=passed next_action=inspect_execution resume_posture=same_task_resume" in out


def test_print_blocker_session_summary_reports_resume_guidance(capsys) -> None:
    print_blocker_session_summary(
        {
            "blocker_summary": {
                "session_id": "session-123",
                "session_status": "blocked",
                "block_source": "compliance",
                "block_detail": "module manifest is stale",
                "resume_action": "inspect_compliance",
                "resume_reason": "doc drift detected",
                "primary_reason": "fix compliance issues before continuing",
                "blocking_reasons": ["module manifest mismatch"],
                "recovery_actions": ["inspect_compliance"],
                "recommended_commands": [
                    "python -m agent_orchestrator.cli team check-compliance session-123",
                ],
            }
        }
    )
    out = capsys.readouterr().out

    assert "session: session-123" in out
    assert "session_status: blocked" in out
    assert "block_source: compliance" in out
    assert "block_detail: module manifest is stale" in out
    assert "resume_action: inspect_compliance" in out
    assert "resume_reason: doc drift detected" in out
    assert "message: fix compliance issues before continuing" in out
    assert "blocking: module manifest mismatch" in out
    assert "recovery_guidance: mode=inspect; resume_action=inspect_compliance; reason=doc drift detected; block=compliance" in out
    assert "recovery_steps: inspect_compliance=inspect compliance blockers or warnings" in out
    assert "recommended_commands: python -m agent_orchestrator.cli team check-compliance session-123" in out


def test_print_blocker_session_summary_reports_warning_details(capsys) -> None:
    print_blocker_session_summary(
        {
            "blocker_summary": {
                "session_id": "session-123",
                "session_status": "approved_for_execution",
                "block_source": "",
                "resume_action": "inspect_session",
                "resume_reason": "compliance_warning_only",
                "primary_reason": "non-blocking compliance warnings exist; review them before the next changed-file update",
                "blocking_reasons": ["1 non-blocking compliance warning(s) remain"],
                "warnings": ["header contract warning: src/agent_orchestrator/legacy.py has placeholder `RESPONSIBILITY` value"],
                "baseline_warnings": ["README missing operator runbook link"],
                "recommended_commands": [
                    "python -m agent_orchestrator.cli team check-compliance session-123",
                ],
            }
        }
    )
    out = capsys.readouterr().out

    assert "warnings: header contract warning: src/agent_orchestrator/legacy.py has placeholder `RESPONSIBILITY` value" in out
    assert "baseline_warnings: README missing operator runbook link" in out


def test_print_blocker_session_summary_reports_clarify_boundary(capsys) -> None:
    print_blocker_session_summary(
        {
            "blocker_summary": {
                "session_id": "session-123",
                "session_status": "blocked",
                "block_source": "execution_run",
                "block_detail": "clarify_scope",
                "resume_action": "clarify",
                "resume_reason": "clarify_scope",
                "primary_reason": "native execution paused on a planner clarification boundary; inspect the linked run and clarify the missing scope before resuming",
                "recovery_actions": ["inspect_execution", "clarify"],
                "recovery_semantics": {
                    "category": "scope_realign",
                    "auto_apply_allowed": False,
                    "continue_allowed": False,
                    "scope_realign_required": True,
                    "fallback_allowed": True,
                    "handoff_allowed": False,
                },
                "evidence": {
                    "linked_execution_run_id": "run-123",
                    "clarify_pause": {
                        "selected_strategy": "clarify_then_edit",
                        "pause_reason": "planner_control_surface",
                        "next_action": "clarify",
                    },
                },
                "recommended_commands": [
                    "python -m agent_orchestrator.cli team chat session-123 --message \"clarify the missing scope for approved execution\"",
                    "python -m agent_orchestrator.cli team inspect-execution session-123",
                ],
            }
        }
    )
    out = capsys.readouterr().out

    assert "resume_action: clarify" in out
    assert "resume_reason: clarify_scope" in out
    assert "recovery_guidance: mode=realign; resume_action=clarify; reason=clarify_scope; block=execution_run/clarify_scope; auto_apply=no; continue_allowed=no; scope_realign_required=yes; fallback_allowed=yes; handoff_allowed=no" in out
    assert "clarify_boundary: strategy=clarify_then_edit source=planner_control_surface next=clarify" in out
    assert 'recommended_commands: python -m agent_orchestrator.cli team chat session-123 --message "clarify the missing scope for approved execution" | python -m agent_orchestrator.cli team inspect-execution session-123' in out
