from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _repo_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_context_map_doc_exists_and_mentions_codebase_map_style_orientation() -> None:
    text = _repo_text("docs/process/context-map.md")

    assert "docs/process/project-index.md" in text
    assert "docs/process/root-map.md" in text
    assert "docs/process/module-manifest.md" in text
    assert "docs/architecture/coding-agent-goal-spec.md" in text
    assert "docs/architecture/native-coding-agent-upgrade-plan.md" in text
    assert "docs/process/native-coding-agent-phase-0-baseline.md" in text
    assert "cli_inherit" in text
    assert "direct_api" in text
    assert "agent_orchestrator.docs_context.v1" in text
    assert "AI Work Control Plane artifact pipeline" in text
    assert "team workspace-status" in text


def test_native_closure_docs_are_canonical_and_define_baseline_contract() -> None:
    project_index = _repo_text("docs/process/project-index.md")
    root_map = _repo_text("docs/process/root-map.md")
    context_map = _repo_text("docs/process/context-map.md")
    upgrade_plan = _repo_text("docs/architecture/native-coding-agent-upgrade-plan.md")
    phase0 = _repo_text("docs/process/native-coding-agent-phase-0-baseline.md")
    phase1 = _repo_text("docs/process/native-coding-agent-phase-1-kernel-boundary.md")
    phase2 = _repo_text("docs/process/native-coding-agent-phase-2-step-loop-convergence.md")
    phase3 = _repo_text("docs/process/native-coding-agent-phase-3-context-engineering-main-path.md")
    phase4 = _repo_text("docs/process/native-coding-agent-phase-4-verify-repair-resume.md")
    phase5 = _repo_text("docs/process/native-coding-agent-phase-5-native-dogfood-track.md")
    closure_audit = _repo_text("docs/process/native-coding-agent-closure-audit.md")

    assert "docs/architecture/native-coding-agent-upgrade-plan.md" in project_index
    assert "docs/process/native-coding-agent-phase-0-baseline.md" in project_index
    assert "docs/process/native-coding-agent-phase-1-kernel-boundary.md" in project_index
    assert "docs/process/native-coding-agent-phase-2-step-loop-convergence.md" in project_index
    assert "docs/process/native-coding-agent-phase-3-context-engineering-main-path.md" in project_index
    assert "docs/process/native-coding-agent-phase-4-verify-repair-resume.md" in project_index
    assert "docs/process/native-coding-agent-phase-5-native-dogfood-track.md" in project_index
    assert "docs/process/native-coding-agent-closure-audit.md" in project_index
    assert "docs/architecture/native-coding-agent-upgrade-plan.md" in root_map
    assert "docs/process/native-coding-agent-phase-0-baseline.md" in root_map
    assert "docs/process/native-coding-agent-phase-1-kernel-boundary.md" in root_map
    assert "docs/process/native-coding-agent-phase-2-step-loop-convergence.md" in root_map
    assert "docs/process/native-coding-agent-phase-4-verify-repair-resume.md" in root_map
    assert "docs/process/native-coding-agent-phase-5-native-dogfood-track.md" in root_map
    assert "docs/process/native-coding-agent-phase-1-kernel-boundary.md" in context_map
    assert "docs/process/native-coding-agent-phase-2-step-loop-convergence.md" in context_map
    assert "docs/process/native-coding-agent-phase-4-verify-repair-resume.md" in context_map
    assert "docs/process/native-coding-agent-phase-5-native-dogfood-track.md" in context_map

    assert "goal mode" in upgrade_plan
    assert "Goal-Mode Acceptance Guardrail" in upgrade_plan
    assert "governed native-only closure" in upgrade_plan

    assert "native-only closure" in phase0
    assert "one or more code edits under `src/agent_orchestrator/` or `ui_frontend/`" in phase0
    assert "canonical docs or compliance-visible surfaces" in phase0
    assert "no external coding agent executed the core implementation loop" in phase0
    assert "approval_pause_resume_complete" in phase0
    assert "verify_failure_exhausted_recovery_block" in phase0
    assert "verify_failure_repair_resume_success" in phase0

    assert "native coding agent kernel" in phase1
    assert "`src/agent_orchestrator/execution/runtime.py`" in phase1
    assert "Kernel Input Contract" in phase1
    assert "Kernel Output Contract" in phase1
    assert "What Must Stay Outside The Kernel" in phase1

    assert "step_loop_contract" in phase2
    assert "loop semantics" in phase2
    assert "`planner_context_trace`" in phase2
    assert "`next_step_contract`" in phase2

    assert "context_engineering_contract" in phase3
    assert "Write`, `Select`, `Structured Observation`, `Compact`, and `Isolate`" in phase3
    assert "scratchpad_entries" in phase3
    assert "structured_observations" in phase3
    assert "resume_context" in phase3

    assert "real verification failure" in phase4
    assert "repair summary output with attempt history and retry budget" in phase4
    assert "governed resume path" in phase4
    assert "control-plane projection" in phase4
    assert "UI execution summary visibility" in phase4

    assert "native-only repository task chain" in phase5
    assert "approval pause" in phase5
    assert "`approval_resume` continuation" in phase5
    assert "workspace index visibility" in phase5
    assert "UI execution summary visibility" in phase5
    assert "verify_failure_exhausted_recovery_block" in phase5
    assert "verify_failure_repair_resume_success" in phase5
    assert "three-chain bundle" in phase5

    assert "not yet complete for the full upgrade objective" in closure_audit
    assert "strongly evidenced" in closure_audit
    assert "medium to strong" in closure_audit
    assert "yes, for at least one bounded internal repository task class, with strong evidence" in closure_audit
    assert "no, not yet" in closure_audit


def test_goal_mode_coding_agent_execution_docs_define_completion_contract() -> None:
    project_index = _repo_text("docs/process/project-index.md")
    goal_summary = _repo_text("docs/process/goal-mode-coding-agent-execution-summary.md")
    goal_detail = _repo_text("docs/process/goal-mode-coding-agent-execution.md")
    goal_audit = _repo_text("docs/process/goal-mode-coding-agent-execution-closure-audit.md")

    assert "docs/process/goal-mode-coding-agent-execution-summary.md" in project_index
    assert "docs/process/goal-mode-coding-agent-execution.md" in project_index
    assert "docs/process/goal-mode-coding-agent-execution-closure-audit.md" in project_index

    assert "P0 Execution Loop" in goal_summary
    assert "P1 Editing And Verification" in goal_summary
    assert "P2 Recovery And Approval" in goal_summary
    assert "P3 Operator Visibility" in goal_summary
    assert "goal-mode-coding-agent-execution.md" in goal_summary

    assert "Global Stopping Criteria" in goal_detail
    assert "Phase Acceptance Criteria" in goal_detail
    assert "Anti-Local-Optimum Guardrail" in goal_detail
    assert "File-Level Verification Targets" in goal_detail
    assert "Required Verification Evidence" in goal_detail

    assert "P0 Execution Loop" in goal_audit
    assert "P1 Editing And Verification" in goal_audit
    assert "P2 Recovery And Approval" in goal_audit
    assert "P3 Operator Visibility" in goal_audit
    assert "Status: `strongly evidenced`" in goal_audit
    assert "Current conclusion: `complete for this goal`" in goal_audit
    assert "team.execute(..., execution_mode=\"native\")" in goal_audit
    assert "resume_from_state" in goal_audit
    assert "agent_orchestrator.execution_fact_chain.v1" in goal_audit
    assert "test_team_resume_can_complete_native_execution_after_both_approvals" in goal_audit
    assert "test_team_resume_command_can_complete_native_execution_after_both_approvals" in goal_audit
    assert "test_dashboard_resume_session_can_complete_native_execution_after_both_approvals" in goal_audit
    assert "test_workspace_index_records_execution_artifact_summary_from_coding_runtime" in goal_audit
    assert "The answer is:" in goal_audit
    assert "`yes`" in goal_audit


def test_native_agent_coverage_expansion_docs_pin_benchmark_and_recovery_semantics() -> None:
    summary = _repo_text("docs/process/goal-mode-native-agent-coverage-expansion-summary.md")
    detail = _repo_text("docs/process/goal-mode-native-agent-coverage-expansion.md")
    audit = _repo_text("docs/process/goal-mode-native-agent-coverage-expansion-closure-audit.md")

    assert "investigation_to_edit_verify" in summary
    assert "multi_file_helper_or_compliance_repair" in summary
    assert "comparative_acceptance_bundle_ready" in summary
    assert "learning_consumed" in summary
    assert "exploration_ambiguity_or_scope_drift" in summary
    assert "continue/inspect" in summary
    assert "scope_realign" in summary
    assert "fallback/handoff" in summary

    assert "success rate" in detail or "success rate" in detail.lower()
    assert "blocked rate" in detail
    assert "verification cost" in detail
    assert "human intervention frequency" in detail

    assert "P0 Native Default Coverage Expansion" in audit
    assert "P1 Comparative Benchmark And Coverage Evidence" in audit
    assert "P2 Recovery Breadth Hardening" in audit
    assert "P3 Learning Asset Consumption Loop" in audit
    assert "Current conclusion: `complete for this goal`" in audit
    assert "governed_fallback_hot_plug_preserved" in audit
    assert "learning assets are consumed in a real router decision" in audit


def test_long_cycle_plan_declares_auto_continue_protocol() -> None:
    text = Path("docs/process/长周期主执行计划.md").read_text(encoding="utf-8")

    assert "验证通过后自动进入下一段" in text
    assert "普通进展汇报不构成停点" in text
    assert "不再按“小计划一轮轮确认”运行" in text


def test_ai_work_control_plane_master_plan_declares_artifact_pipeline() -> None:
    text = Path("docs/process/ai-work-control-plane-master-plan.md").read_text(encoding="utf-8")

    assert "AI Work Control Plane" in text
    assert "WorkspaceState -> ContextPacket -> StrategyDecision -> ExecutionTopologySnapshot" in text
    assert "原有编排不舍弃" in text
    assert "长期允许编排逐步被模型内化" in text
    assert "Contract Hardening + Dogfood" in text
    assert "PlanSession -> WorkspaceState -> ContextPacket -> StrategyDecision" in text


def test_control_plane_artifact_contracts_document_stable_formats() -> None:
    text = Path("docs/process/control-plane-artifact-contracts.md").read_text(encoding="utf-8")

    assert "agent_orchestrator.workspace_state.v1" in text
    assert "agent_orchestrator.context_packet.v1" in text
    assert "agent_orchestrator.strategy_decision.v1" in text
    assert "agent_orchestrator.approval_item.v1" in text
    assert "agent_orchestrator.evidence_bundle.v1" in text
    assert "agent_orchestrator.provider_evidence_summary.v1" in text
    assert "agent_orchestrator.governance_bundle.v1" in text
    assert "agent_orchestrator.governance_bundle_inspection.v1" in text
    assert "native_tool_workflow_surface" in text
    assert "native_tool_productization_surface" in text
    assert "adapter_productization_surface" in text
    assert "comparative_native_tool_summary" in text
    assert "comparative_adapter_summary" in text
    assert "comparative_daily_driver_summary" in text
    assert "comparative_completion_summary" in text
    assert "session_productization_surface" in text
    assert "workflow_continuity" in text
    assert "operator_posture_digest" in text
    assert "clarify_boundary_digest" in text
    assert "session_planner_decision" in text
    assert "session_continuity_outline" in text
    assert "comparative_session_posture_summary" in text
    assert "comparative_session_continuity_summary" in text
    assert "workflow_resume_ready" in text
    assert "workflow_projection_visible" in text
    assert "autonomy_posture" in text
    assert "resume_expectation" in text
    assert "resume_posture" in text
    assert "session_posture_cases" in text
    assert "productization_case_count" in text
    assert "continuity_snapshot" in text
    assert "compacted_context_summary" in text
    assert "recovery_contract" in text
    assert "shared_contract_alignment" in text
    assert "shared_productization_contract_ready" in text
    assert "daily_driver_main_path_ready" in text
    assert "comparison_posture_basis" in text
    assert "comparison_proof_strength" in text
    assert "daily_driver_repeatability_tier" in text
    assert "daily_driver_repeatability_harness" in text
    assert "daily_driver_case_matrix" in text
    assert "independent_daily_driver_repo_task_families_proven" in text
    assert "external_comparison_harness_surface" in text
    assert "stronger_task_families" in text
    assert "repo_task_acceptance_families_proven" in text
    assert "daily_driver_repo_task_families_proven" in text
    assert "broader_repeatability_gap_families" in text
    assert "Evidence comparison or trend surfaces" in text
    assert "Unknown fields must be ignored" in text


def test_release_readiness_mentions_provider_evidence_summary() -> None:
    text = Path("docs/process/v1x-release-readiness.md").read_text(encoding="utf-8")

    assert "agent_orchestrator.provider_evidence_summary.v1" in text
    assert "agent_orchestrator.governance_bundle.v1" in text
    assert "without claiming provider session ownership" in text


def test_evidence_freeze_docs_require_trend_proof_strength_visibility() -> None:
    checklist = _repo_text("docs/process/v1-candidate-release-checklist.md")
    freeze_plan = _repo_text("docs/process/v1-candidate-freeze-plan.md")
    phase_plan = _repo_text("docs/process/v1x-upgrade-phase-plan.md")
    trend = _repo_text("docs/process/v1x-evidence-trend.md")
    hardening = _repo_text("docs/process/v1x-hardening-workflow-report.md")
    artifact_refresh = _repo_text("docs/process/ai-work-control-plane-real-task-dogfood-phase-3-artifact-refresh.md")
    runbook = _repo_text("docs/process/agent-team-operator-runbook.md")

    assert "Comparative Proof Strength" in checklist
    assert "Comparative Proof Strength" in freeze_plan
    assert "Comparative Proof Strength" in phase_plan
    assert "repeatability posture" in checklist
    assert "direct-proof and repeatability posture" in freeze_plan
    assert "proof-strength posture" in phase_plan
    assert "## Comparative Proof Strength" in trend
    assert "baseline_direct_proof_status:" in trend
    assert "current_repeatability_status:" in trend
    assert "Comparative Proof Strength" in hardening
    assert "Comparative Proof Strength" in artifact_refresh
    assert "Comparative Proof Strength" in runbook
    assert "repeatability posture" in runbook
    assert "evidence compare" in runbook
    assert "current_version_assessment" in runbook


def test_control_plane_dogfood_evidence_records_real_chain() -> None:
    text = Path("docs/process/ai-work-control-plane-dogfood-evidence.md").read_text(encoding="utf-8")

    assert "WorkspaceState -> ContextPacket -> StrategyDecision -> ExecutionTopologySnapshot" in text
    assert "agent_orchestrator.workspace_state.v1" in text
    assert "agent_orchestrator.context_packet.v1" in text
    assert "agent_orchestrator.execution_topology_snapshot.v1" in text
    assert "control_plane_focus=state_context_strategy_topology_approval_evidence_memory_recovery" in text
    assert "auto_write=false" in text


def test_native_coding_agent_dogfood_evidence_records_task_class_and_three_proof_scenarios() -> None:
    text = Path("docs/process/native-coding-agent-dogfood-evidence.md").read_text(encoding="utf-8")
    runbook = Path("docs/process/agent-team-operator-runbook.md").read_text(encoding="utf-8")
    process = Path("docs/process/agent-orchestrator-implementation-process.md").read_text(encoding="utf-8")

    assert "bounded_internal_repo_task" in text
    assert "approval_pause_resume_complete" in text
    assert "verify_failure_exhausted_recovery_block" in text
    assert "verify_failure_repair_resume_success" in text
    assert "multi_milestone_program_execution" in text
    assert "agent_orchestrator.native_task_proof.v1" in text
    assert "agent_orchestrator.native_runtime_closure.v1" in text
    assert "agent_orchestrator.native_repo_task_acceptance.v1" in text
    assert "agent_orchestrator.program_execution_proof.v1" in text
    assert "native_tool_workflow_surface" in text
    assert "native_tool_productization_surface" in text
    assert "adapter_productization_surface" in text
    assert "comparative_adapter_summary" in text
    assert "session_productization_surface" in text
    assert "workflow_continuity" in text
    assert "operator_posture_digest" in text
    assert "clarify_boundary_digest" in text
    assert "session_planner_decision" in text
    assert "session_continuity_outline" in text
    assert "comparative_session_posture_summary" in text
    assert "comparative_session_continuity_summary" in text
    assert "workflow_resume_ready" in text
    assert "workflow_projection_visible" in text
    assert "autonomy_posture" in text
    assert "resume_expectation" in text
    assert "resume_posture" in text
    assert "session_posture_cases" in text
    assert "productization_case_count" in text
    assert "continuity_snapshot" in text
    assert "compacted_context_summary" in text
    assert "recovery_contract" in text
    assert "shared_contract_alignment" in text
    assert "shared_productization_contract_ready" in text
    assert "session_productization_surface" in text
    assert "native_tool_usage" in text
    assert "daily_driver_main_path_ready" in text
    assert "daily_driver_main_path_ready_cases" in text
    assert "comparison_posture" in text
    assert "comparison_posture_basis" in text
    assert "comparison_proof_strength" in text
    assert "comparative_daily_driver_summary" in text
    assert "comparative_completion_summary" in text
    assert "daily_driver_repeatability_tier" in text
    assert "daily_driver_repeatability_harness" in text
    assert "daily_driver_case_matrix" in text
    assert "independent_daily_driver_repo_task_families_proven" in text
    assert "stronger_task_families" in text
    assert "broader_repeatability_gap_families" in text
    assert "multiple stronger direct-proof families" in text
    assert "evidence trend reports" in text
    assert "agent_orchestrator.runtime_event_stream.v1" in text
    assert "agent_orchestrator.workspace_index.v1" in text
    assert "agent_orchestrator.recovery_recommendation.v1" in text
    assert "agent_orchestrator.execution_topology_snapshot.v1" in text
    assert "stable step-loop" in text
    assert "explicit context select plus structured observation" in text
    assert "multi-milestone native program-execution evidence chain" in text
    assert "native-coding-agent-dogfood-evidence.md" in runbook
    assert "native coding-agent dogfood baseline" in process


def test_native_agent_productization_goal_summary_mentions_shared_productization_readiness() -> None:
    text = Path("docs/process/goal-mode-native-agent-productization-summary.md").read_text(encoding="utf-8")

    assert "shared_contract_alignment" in text
    assert "shared_productization_contract_ready" in text
    assert "native_tool_workflow_surface" in text
    assert "native_tool_productization_surface" in text
    assert "session_planner_decision" in text
    assert "session_continuity_outline" in text
    assert "comparative_session_posture_summary" in text
    assert "autonomy_posture" in text
    assert "resume_expectation" in text
    assert "resume_posture" in text
    assert "session_posture_cases" in text
    assert "adapter_productization_surface" in text
    assert "comparative_adapter_summary" in text
    assert "productization_case_count" in text
    assert "native_tool_usage" in text
    assert "daily_driver_main_path_ready" in text
    assert "comparison_posture" in text
    assert "comparison_posture_basis" in text
    assert "comparison_proof_strength" in text
    assert "stronger_task_families" in text
    assert "repo_task_acceptance_families_proven" in text
    assert "daily_driver_repo_task_families_proven" in text
    assert "broader_repeatability_gap_families" in text
    assert "broader daily-driver family" in text


def test_native_agent_productization_closure_audit_tracks_current_strength_and_remaining_gap() -> None:
    project_index = _repo_text("docs/process/project-index.md")
    audit = _repo_text("docs/process/goal-mode-native-agent-productization-closure-audit.md")

    assert "docs/process/goal-mode-native-agent-productization-closure-audit.md" in project_index
    assert "P0 Native Tool Surface Expansion" in audit
    assert "P1 Native Planner Independence" in audit
    assert "P2 Session Productization And Long-Horizon Continuity" in audit
    assert "P3 Unified Native/External Adapter Ecosystem" in audit
    assert "File-Level Verification Targets Audit" in audit
    assert "Required Verification Evidence Audit" in audit
    assert "src/agent_orchestrator/execution/native_tools.py" in audit
    assert "tests/test_cli_presenters.py" in audit
    assert "native_tool_workflow_surface" in audit
    assert "native_tool_productization_surface" in audit
    assert "adapter_productization_surface" in audit
    assert "comparative_adapter_summary" in audit
    assert "comparative_daily_driver_summary" in audit
    assert "comparative_completion_summary" in audit
    assert "session_productization_surface" in audit
    assert "comparative_session_posture_summary" in audit
    assert "workflow_continuity" in audit
    assert "workflow-stage continuity" in audit
    assert "operator_posture_digest" in Path("docs/process/control-plane-artifact-contracts.md").read_text(encoding="utf-8")
    assert "workflow_continuity" in Path("docs/process/control-plane-artifact-contracts.md").read_text(encoding="utf-8")
    assert "workflow_projection_visible" in Path("docs/process/control-plane-artifact-contracts.md").read_text(encoding="utf-8")
    assert "clarify_boundary_digest" in Path("docs/process/control-plane-artifact-contracts.md").read_text(encoding="utf-8")
    assert "daily_driver_main_path_ready" in audit
    assert "comparison_posture" in audit
    assert "comparison_proof_strength" in audit
    assert "productization_case_count" in audit
    assert "multiple stronger direct-proof families proven" in audit
    assert "multiple stronger direct-proof families exist" in audit
    assert "six independent daily-driver families" in audit
    assert "broadly_proven_on_internal_repo_task_slice" in audit
    assert "Current conclusion: `not yet complete for this goal`" in audit
    assert "yes, with strong evidence" in audit
    assert "`no, not yet`" in audit


def test_daily_driver_repeatability_goal_docs_define_multi_family_acceptance_contract() -> None:
    project_index = _repo_text("docs/process/project-index.md")
    summary = _repo_text("docs/process/goal-mode-daily-driver-repeatability-summary.md")
    detail = _repo_text("docs/process/goal-mode-daily-driver-repeatability.md")

    assert "docs/process/goal-mode-daily-driver-repeatability-summary.md" in project_index
    assert "docs/process/goal-mode-daily-driver-repeatability.md" in project_index

    assert "P0 Multi-Task Baseline" in summary
    assert "P1 Repeatability Harness" in summary
    assert "P2 Daily Driver Acceptance" in summary
    assert "P3 Gap Report vs OpenCode" in summary
    assert "至少 3 类真实 repo 任务通过" in summary
    assert "runtime payload / workspace index / CLI summary" in summary
    assert "Current Evidence Snapshot" in summary
    assert "P0 complete" in summary
    assert "P1 complete" in summary
    assert "P2 complete" in summary
    assert "P3 complete" in summary
    assert "agent_orchestrator.daily_driver_runner_artifact.v1" in summary

    assert "文档更新任务" in detail
    assert "单文件代码修复" in detail
    assert "多文件 operator surface / CLI 投影修复" in detail
    assert "测试驱动的小功能补齐" in detail
    assert "failure / clarify / approval pause 路径任务" in detail
    assert "同一类任务可重复跑" in detail
    assert "每次输出 runtime payload" in detail
    assert "每次输出 workspace index" in detail
    assert "每次输出 CLI summary" in detail
    assert "每个 case 都有 verify 或明确 stop" in detail
    assert "不能只用 mock case" in detail
    assert "native tool surface" in detail
    assert "planner" in detail
    assert "adapter fact" in detail
    assert "TUI" in detail
    assert "插件生态" in detail
    assert "外部 opencode harness" in detail
    assert "canonical daily-driver runner artifact" in detail
    assert "Required Verification Evidence" in detail
    assert "Explicit Non-Goals" in detail
    assert "Current Operator Readout" in detail
    assert "Operator Gap Report" in detail
    assert "still missing" in detail
    assert "next best move" in detail


def test_control_plane_reference_rescreen_maps_research_repos_to_new_direction() -> None:
    text = Path("docs/research/control-plane-reference-rescreen.md").read_text(encoding="utf-8")
    context_map = Path("docs/process/context-map.md").read_text(encoding="utf-8")

    for project in (
        "HiveWard",
        "wanman",
        "slark",
        "CodeWhale",
        "codex-orchestrator",
        "codex-plugin-cc",
        "cc-plugin-codex",
        "Eigent",
    ):
        assert project in text

    assert "PlanSession -> WorkspaceState -> ContextPacket -> StrategyDecision" in text
    assert "approval inbox" in text
    assert "run ledger" in text
    assert "runtime boundary" in text
    assert "Workspace / Program Index v2" in text
    assert "Topology Blueprint Snapshot" in text
    assert "Memory Promotion Workflow" in text
    assert "docs/research/control-plane-reference-rescreen.md" in context_map


def test_process_doc_declares_long_plan_driven_execution() -> None:
    text = Path("docs/process/agent-orchestrator-implementation-process.md").read_text(encoding="utf-8")

    assert "主计划驱动" in text
    assert "不再把每次实现包装成新的独立小计划" in text
    assert "验证通过后自动进入下一段" in text


def test_readme_points_to_continuous_internal_default_workflow() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "面向长周期本地 coding agent 的可靠性控制平面" in text
    assert "内部默认工作流" in text
    assert "长周期主执行计划" in text
    assert "验证通过后自动进入下一段" in text
    assert "状态、证据、审批、记忆和恢复仍然应该留在模型之外" in text


def test_continuous_control_plane_hardening_plan_declares_phase_protocol() -> None:
    text = Path("docs/process/ai-work-control-plane-continuous-hardening-plan.md").read_text(encoding="utf-8")

    assert "short term: use explicit orchestration" in text
    assert "medium term: let the control plane govern orchestration" in text
    assert "long term: allow orchestration to be internalized by model runtimes" in text
    assert "Run targeted tests during phases" in text
    assert "Run full `pytest` and `team check-compliance` only at final convergence" in text

    for phase in range(8):
        assert Path(f"docs/process/ai-work-control-plane-continuous-phase-{phase}-" + {
            0: "baseline.md",
            1: "operator-entry.md",
            2: "recovery.md",
            3: "topology-policy.md",
            4: "compliance-sync.md",
            5: "direct-api-tool-recording.md",
            6: "dogfood.md",
            7: "final-convergence.md",
        }[phase]).exists()


def test_operations_track_plan_declares_operator_control_plane_surface() -> None:
    text = Path("docs/process/ai-work-control-plane-operations-track-plan.md").read_text(encoding="utf-8")
    phase0 = Path("docs/process/ai-work-control-plane-operations-phase-0-baseline.md").read_text(encoding="utf-8")
    context_map = Path("docs/process/context-map.md").read_text(encoding="utf-8")
    master = Path("docs/process/ai-work-control-plane-master-plan.md").read_text(encoding="utf-8")
    runbook = Path("docs/process/agent-team-operator-runbook.md").read_text(encoding="utf-8")

    assert "PlanSession -> WorkspaceState -> ContextPacket -> StrategyDecision" in text
    assert "ApprovalInbox -> RunLedger" in text
    assert "Workspace / Program Index v2" in text
    assert "MemoryPromotion" in text
    assert "StrategyDecision.executes` stays `False" in text
    assert "pytest tests/test_docs_process.py tests/test_planning_support.py -q" in phase0
    assert "AI Work Control Plane Operations Track" in context_map
    assert "Workspace / Program Index v2 + Approval Inbox + Run Ledger" in master
    assert "Operations Track" in runbook


def test_operations_dogfood_evidence_pins_complete_chain() -> None:
    text = Path("docs/process/ai-work-control-plane-operations-dogfood-evidence.md").read_text(encoding="utf-8")
    master = Path("docs/process/ai-work-control-plane-master-plan.md").read_text(encoding="utf-8")
    runbook = Path("docs/process/agent-team-operator-runbook.md").read_text(encoding="utf-8")

    assert "Workspace / Program Index v2" in text
    assert "Topology Blueprint Snapshot" in text
    assert "Approval Inbox" in text
    assert "Run Ledger" in text
    assert "Memory Candidate" in text
    assert "agent_orchestrator.workspace_index.v1" in text
    assert "agent_orchestrator.run_ledger.v1" in text
    assert "auto_write=false" in text
    assert "ai-work-control-plane-operations-dogfood-evidence.md" in master
    assert "ai-work-control-plane-operations-dogfood-evidence.md" in runbook


def test_live_recovery_track_plan_and_dogfood_evidence_pin_recovery_chain() -> None:
    plan = Path("docs/process/ai-work-control-plane-live-recovery-track-plan.md").read_text(encoding="utf-8")
    phase0 = Path("docs/process/ai-work-control-plane-live-recovery-phase-0-baseline.md").read_text(encoding="utf-8")
    evidence = Path("docs/process/ai-work-control-plane-live-recovery-dogfood-evidence.md").read_text(encoding="utf-8")
    master = Path("docs/process/ai-work-control-plane-master-plan.md").read_text(encoding="utf-8")
    runbook = Path("docs/process/agent-team-operator-runbook.md").read_text(encoding="utf-8")

    assert "Recovery Timeline" in plan
    assert "Runtime Event Stream" in plan
    assert "Recovery Recommendation" in plan
    assert "pytest tests/test_docs_process.py tests/test_planning_support.py -q" in phase0
    assert "PlanSession" in evidence
    assert "agent_orchestrator.recovery_timeline.v1" in evidence
    assert "agent_orchestrator.runtime_event_stream.v1" in evidence
    assert "agent_orchestrator.recovery_recommendation.v1" in evidence
    assert "awaiting-human / approval" in evidence
    assert "compliance blocking" in evidence
    assert "provider/runtime degraded or fallback" in evidence
    assert "ai-work-control-plane-live-recovery-dogfood-evidence.md" in master
    assert "ai-work-control-plane-live-recovery-dogfood-evidence.md" in runbook


def test_operator_runbook_doc_covers_happy_path_and_recovery() -> None:
    text = Path("docs/process/agent-team-operator-runbook.md").read_text(encoding="utf-8")

    assert "team start" in text
    assert "team status" in text
    assert "team next" in text
    assert "team roles" in text
    assert "team inspect-knowledge" in text
    assert "team inspect-docs" in text
    assert "team workspace-status" in text
    assert "team context-packet" in text
    assert "team topology inspect" in text
    assert "team approvals list" in text
    assert "team evidence-gates" in text
    assert "approval_state" in text
    assert "required outputs" in text
    assert "team revise" in text
    assert "team approve" in text
    assert "team execute" in text
    assert "retry-review" in text
    assert "retry-adversarial-review" in text
    assert "topology_reason" in text
    assert "fallback_reason" in text
    assert "fallback_detail" in text
    assert "场景 A" in text
    assert "场景 B" in text
    assert "场景 C" in text
    assert "不要直接编辑底层 JSON" in text


def test_decision_docs_exist_and_use_required_headings() -> None:
    decisions_root = Path("docs/decisions")
    required = [
        "0001-documentation-as-runtime-context.md",
        "0002-handoff-packet-contract.md",
        "0003-canonical-docs-vs-derived-views.md",
        "0004-ai-work-control-plane-reframe.md",
    ]

    for name in required:
        text = (decisions_root / name).read_text(encoding="utf-8")
        for heading in ("## Status", "## Context", "## Decision", "## Consequences", "## Related Commands"):
            assert heading in text


def test_readme_points_to_hook_installation_workflow() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "install-hooks" in text
    assert "team check-compliance" in text
    assert "docs/decisions/" in text


def test_readme_uses_health_subcommand_example() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "python -m agent_orchestrator.cli health" in text
    assert "python -m agent_orchestrator.cli --health" not in text


def test_process_doc_reflects_basic_documentation_gate_progress() -> None:
    text = Path("docs/process/agent-orchestrator-implementation-process.md").read_text(encoding="utf-8")

    assert "`in_progress - basic gate active`" in text
    assert "`in_progress - basic refresh and compliance checks active`" in text
    assert "`in_progress - changed-file scoped pre-commit gate active`" in text
    assert "team check-compliance" in text


def test_agent_evolution_phase_docs_exist_through_phase_7() -> None:
    master = Path("docs/process/agent-evolution-master-plan.md").read_text(encoding="utf-8")
    phase7 = Path("docs/process/agent-evolution-phase-7-semi-autonomous-role-contracts.md").read_text(encoding="utf-8")
    phase75 = Path("docs/process/agent-evolution-phase-7-5-surface-convergence.md").read_text(encoding="utf-8")

    assert "Phase 7: Semi-Autonomous Role Contracts" in master
    assert "Phase 7.5: Surface Convergence" in master
    assert "pytest tests/test_team.py tests/test_messages.py tests/test_work_graph.py -q" in master
    assert "pytest tests/test_docs_process.py -q" in master
    assert "Semi-Autonomous Role Contracts" in phase7
    assert "structured inputs and outputs" in phase7
    assert "pytest tests/test_actions.py tests/test_cli.py tests/test_work_graph.py -q" in phase7
    assert "Surface Convergence" in phase75
    assert "canonical contracts" in phase75
    assert "projection surfaces" in phase75


def test_control_plane_artifact_contracts_define_canonical_vs_projection_boundary() -> None:
    text = Path("docs/process/control-plane-artifact-contracts.md").read_text(encoding="utf-8")

    assert "## Canonical Vs Projection Boundary" in text
    assert "Canonical contracts are the control-plane artifacts documented in this file." in text
    assert "`team roles`, work-graph trees, pretty summaries, runbook guidance, and UI panels are projections" in text
    assert "must not become a second durable state source" in text


def test_operator_runbook_and_process_doc_define_surface_convergence_rule() -> None:
    runbook = Path("docs/process/agent-team-operator-runbook.md").read_text(encoding="utf-8")
    process = Path("docs/process/agent-orchestrator-implementation-process.md").read_text(encoding="utf-8")

    assert "operator projection" in runbook
    assert "不是新的 durable state" in runbook
    assert "surface convergence" in process
    assert "canonical contracts" in process


def test_agent_evolution_master_plan_declares_phase_first_protocol() -> None:
    text = Path("docs/process/agent-evolution-master-plan.md").read_text(encoding="utf-8")

    assert "the control plane remains the system of record" in text
    assert "Every phase must start with a short phase plan" in text
    assert "Advance to the next phase only after targeted tests pass" in text
    assert "Phase 0: Current-State Baseline" in text
    assert "Phase 8: LangGraph Execution Runtime Pilot" in text
    assert "Phase 9: A2A-Style Interop Adapter" in text


def test_agent_evolution_phase_0_baseline_declares_acceptance_criteria() -> None:
    text = Path("docs/process/agent-evolution-phase-0-baseline.md").read_text(encoding="utf-8")

    assert "What is the system today?" in text
    assert "What is it not?" in text
    assert "no runtime behavior changes" in text
    assert "canonical docs state that the current system is governance-first and workflow-governed" in text
    assert "current execution layer has multi-role semantics but is not yet a high-autonomy multi-agent system" in text
    assert "pytest tests/test_docs_process.py -q" in text


def test_architecture_doc_describes_current_execution_layer_as_workflow_governed() -> None:
    text = Path("docs/architecture/决策核心-执行拓扑-运行时分层说明.md").read_text(encoding="utf-8")

    assert "以工作流治理为核心、带有多角色语义和有限 agent 分工的 orchestration runtime" in text
    assert "它也不是高自治 multi-agent system" in text
    assert "先结构化协作对象" in text
    assert "再外显决策候选与裁决理由" in text


def test_process_doc_links_agent_evolution_plan_protocol() -> None:
    text = Path("docs/process/agent-orchestrator-implementation-process.md").read_text(encoding="utf-8")

    assert "当前执行层更接近 `单编排器 + 多角色语义 + 持久化工作流`" in text
    assert "当前执行层还不是高自治、多中心协商式的 multi-agent system" in text
    assert "docs/process/agent-evolution-master-plan.md" in text
    assert "targeted tests 通过后进入下一 phase" in text
    assert "--changed-file" in text
    assert "Missing plan/checklist/review-round persistence is now blocked" in text
    assert "visible reviewer fallback policy" in text
    assert "fallback source, reason, detail, and preferred reviewer" in text
    assert "structured topology rationale" in text
    assert "operator-runbook signal compliance" in text
    assert "Operator runbook drift for topology and provider fallback signals is now blocked" in text
    assert "Checklist ownership is now explicit on persisted plan items" in text
    assert "cli_inherit" in text
    assert "cli_isolated" in text
    assert "direct_api" in text
    assert "No hook-based compliance checks are active." not in text


def test_hook_script_exists_and_runs_compliance_gate() -> None:
    text = Path("scripts/git-hooks/pre-commit").read_text(encoding="utf-8")

    assert "team check-compliance" in text
    assert "PYTHONPATH=src" in text
    assert "root-map.md" not in text
    assert "has_compliance_input" in text
    assert "exit 0" in text
    assert "managed hook marker missing" in text


def test_hook_script_scopes_changed_file_checks_to_compliance_inputs() -> None:
    text = Path("scripts/git-hooks/pre-commit").read_text(encoding="utf-8")

    assert "case \"$file\" in" in text
    assert "src/agent_orchestrator/*.py" in text
    assert "docs/process/*.md" in text
    assert "docs/architecture/*.md" in text
    assert "README.md" in text
    assert "*)" in text
    assert "continue" in text
    assert "git diff --cached --name-only -z" in text
    assert "changed_args+=(--changed-file=\"$file\")" in text
    assert '"${changed_args[@]}"' in text


def test_native_productization_install_release_doc_exists() -> None:
    assert Path("docs/process/native-productization-after-instrumentation-install-release.md").exists()


def test_native_operator_ux_tui_deepening_doc_exists() -> None:
    assert Path("docs/process/native-operator-ux-tui-deepening.md").exists()


def test_native_install_release_candidate_hardening_doc_exists() -> None:
    text = Path("docs/process/native-install-release-candidate-hardening.md").read_text(encoding="utf-8")
    assert "rc-validate" in text
    assert "rc-bundle" in text


def test_provider_runtime_readiness_hardening_doc_exists() -> None:
    assert Path("docs/process/provider-runtime-readiness-hardening.md").exists()



def test_native_rc_to_dogfood_adoption_doc_declares_cli_and_schema() -> None:
    text = Path("docs/process/goal-mode-native-rc-to-dogfood-adoption.md").read_text(encoding="utf-8")
    assert "repo_change_lane" in text
    assert "validation_lane" in text
    assert "recovery_lane" in text
    assert "rc-adopt" in text
    assert "rc-adoption-report" in text
    assert "agent_orchestrator.native_rc_adoption_ledger.v1" in text
