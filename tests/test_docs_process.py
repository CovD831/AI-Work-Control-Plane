from pathlib import Path


def test_context_map_doc_exists_and_mentions_codebase_map_style_orientation() -> None:
    text = Path("docs/process/context-map.md").read_text(encoding="utf-8")

    assert "CODEBASE_MAP-style orientation" in text
    assert "root map" in text
    assert "module manifest" in text
    assert "file-header contract" in text
    assert "cli_inherit" in text
    assert "direct_api" in text
    assert "agent_orchestrator.docs_context.v1" in text
    assert "AI Work Control Plane artifact pipeline" in text
    assert "team workspace-status" in text


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
    assert "agent_orchestrator.execution_topology_snapshot.v1" in text
    assert "agent_orchestrator.approval_item.v1" in text
    assert "agent_orchestrator.evidence_bundle.v1" in text
    assert "agent_orchestrator.provider_evidence_summary.v1" in text
    assert "agent_orchestrator.governance_bundle.v1" in text
    assert "agent_orchestrator.governance_bundle_inspection.v1" in text
    assert "Unknown fields must be ignored" in text


def test_release_readiness_mentions_provider_evidence_summary() -> None:
    text = Path("docs/process/v1x-release-readiness.md").read_text(encoding="utf-8")

    assert "agent_orchestrator.provider_evidence_summary.v1" in text
    assert "agent_orchestrator.governance_bundle.v1" in text
    assert "without claiming provider session ownership" in text


def test_control_plane_dogfood_evidence_records_real_chain() -> None:
    text = Path("docs/process/ai-work-control-plane-dogfood-evidence.md").read_text(encoding="utf-8")

    assert "WorkspaceState -> ContextPacket -> StrategyDecision -> ExecutionTopologySnapshot" in text
    assert "agent_orchestrator.workspace_state.v1" in text
    assert "agent_orchestrator.context_packet.v1" in text
    assert "agent_orchestrator.execution_topology_snapshot.v1" in text
    assert "control_plane_focus=state_context_strategy_topology_approval_evidence_memory_recovery" in text
    assert "auto_write=false" in text


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
