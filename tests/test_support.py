# DEPS: agent_orchestrator, pathlib
# RESPONSIBILITY: Share test fixtures for process documentation scaffolding.
# MODULE: tests
# ---

from pathlib import Path

from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.planning import PlanStore, TeamOrchestrator


def write_minimal_process_docs(root: Path) -> None:
    (root / "docs" / "process").mkdir(parents=True, exist_ok=True)
    (root / "src" / "agent_orchestrator").mkdir(parents=True, exist_ok=True)
    package_init = root / "src" / "agent_orchestrator" / "__init__.py"
    if not package_init.exists():
        package_init.write_text('"""package"""\n', encoding="utf-8")
    (root / "src" / "agent_orchestrator" / "stub.py").write_text(
        '"""Stub module."""\n\nfrom __future__ import annotations\n\n# DEPS: __future__\n# RESPONSIBILITY: Provide a compliant module for minimal process-doc test fixtures.\n# MODULE: tests\n# ---\n\nVALUE = 1\n',
        encoding="utf-8",
    )
    (root / "src" / "agent_orchestrator" / "compliance_signal.py").write_text(
        '"""Compliance-visible stub module."""\n\nfrom __future__ import annotations\n\n# DEPS: __future__\n# RESPONSIBILITY: Provide a compliance-visible Python surface for native repo-task acceptance fixtures.\n# MODULE: tests\n# ---\n\nFLAG = 0\n',
        encoding="utf-8",
    )
    (root / "src" / "agent_orchestrator" / "summary_helper.py").write_text(
        '"""Helper summary stub."""\n\nfrom __future__ import annotations\n\n# DEPS: __future__\n# RESPONSIBILITY: Provide a helper implementation surface for native repo-task acceptance fixtures.\n# MODULE: tests\n# ---\n\n\ndef build_summary() -> dict[str, object]:\n    return {"status": "stub"}\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# temp\n\n- 长周期主执行计划\n- agent-team-operator-runbook.md\n- docs/decisions/\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "长周期主执行计划.md").write_text(
        "# 长周期主执行计划\n\n- 文档同步 / compliance / hook blocking\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "root-map.md").write_text(
        "# Root Map\n\n"
        "- module manifests\n"
        "- file-header contract\n"
        "- compliance checks\n"
        "- context map\n"
        "- `src/agent_orchestrator/`: primary Python package\n"
        "- `docs/process/project-index.md`: canonical reading order and recent update index\n"
        "- `docs/process/context-map.md`: canonical docs and artifact map\n"
        "- `docs/process/agent-orchestrator-implementation-process.md`: implementation supervision source of truth\n"
        "- `docs/process/agent-team-operator-runbook.md`: operator workflow recovery guide\n"
        "- `docs/process/agent-evolution-master-plan.md`: future evolution source of truth\n"
        "- `docs/architecture/native-coding-agent-upgrade-plan.md`: native coding-agent closure target and phase roadmap\n"
        "- `docs/process/native-coding-agent-phase-0-baseline.md`: native closure baseline and first proof contract\n"
        "- `docs/process/native-coding-agent-phase-1-kernel-boundary.md`: native governed kernel boundary hardening\n"
        "- `docs/process/native-coding-agent-phase-2-step-loop-convergence.md`: native step-loop convergence phase\n"
        "- `docs/process/native-coding-agent-phase-4-verify-repair-resume.md`: native verify-repair-resume closure phase\n"
        "- `docs/process/native-coding-agent-phase-5-native-dogfood-track.md`: native dogfood evidence phase\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "context-map.md").write_text(
        "# Context Map\n\n"
        "- CODEBASE_MAP-style orientation for the Agent Orchestrator repository\n"
        "- root map\n"
        "- project index\n"
        "- module manifest\n"
        "- file-header contract\n"
        "- compliance checks\n"
        "- `docs/process/root-map.md`: compact repository entry map\n"
        "- `docs/process/project-index.md`: canonical reading order and recent update index\n"
        "- `docs/process/module-manifest.md`: module responsibility and dependency map\n"
        "- `docs/architecture/coding-agent-goal-spec.md`: governed coding-agent runtime goal spec\n"
        "- `docs/architecture/native-coding-agent-upgrade-plan.md`: native coding-agent closure target and phase contract\n"
        "- `docs/process/native-coding-agent-phase-0-baseline.md`: closure baseline and proof-bundle contract\n"
        "- `docs/process/native-coding-agent-phase-1-kernel-boundary.md`: governed kernel boundary hardening\n"
        "- `docs/process/native-coding-agent-phase-2-step-loop-convergence.md`: step-loop convergence contract\n"
        "- `docs/process/native-coding-agent-phase-4-verify-repair-resume.md`: verify-repair-resume closure contract\n"
        "- `docs/process/native-coding-agent-phase-5-native-dogfood-track.md`: native dogfood evidence track\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "module-manifest.md").write_text(
        "# Module Manifest\n\n- src/agent_orchestrator/\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "project-index.md").write_text(
        "# Project Index\n\n"
        "- docs/process/root-map.md\n"
        "- docs/process/context-map.md\n"
        "- docs/architecture/native-coding-agent-upgrade-plan.md\n"
        "- docs/process/goal-mode-native-agent-productization-closure-audit.md\n"
        "- docs/process/native-coding-agent-phase-0-baseline.md\n"
        "- docs/process/native-coding-agent-phase-1-kernel-boundary.md\n"
        "- docs/process/native-coding-agent-phase-2-step-loop-convergence.md\n"
        "- docs/process/native-coding-agent-phase-4-verify-repair-resume.md\n"
        "- docs/process/native-coding-agent-phase-5-native-dogfood-track.md\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "agent-orchestrator-implementation-process.md").write_text(
        "# Agent Orchestrator Product Process\n\n- hook-based compliance checks\n- native coding-agent dogfood baseline\n- docs/decisions/\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "control-plane-artifact-contracts.md").write_text(
        "# Control Plane Artifact Contracts\n\n- session_continuity\n- runtime_cost\n- native_tool_usage\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "native-coding-agent-dogfood-evidence.md").write_text(
        "# Native Coding Agent Dogfood Evidence\n\n"
        "native coding-agent dogfood baseline\n"
        "- bounded_internal_repo_task\n"
        "- approval_pause_resume_complete\n"
        "- verify_failure_exhausted_recovery_block\n"
        "- verify_failure_repair_resume_success\n"
        "- multi_milestone_program_execution\n"
        "- agent_orchestrator.native_task_proof.v1\n"
        "- agent_orchestrator.native_runtime_closure.v1\n"
        "- agent_orchestrator.native_repo_task_acceptance.v1\n"
        "- agent_orchestrator.program_execution_proof.v1\n"
        "- native_tool_workflow_surface\n"
        "- native_tool_productization_surface\n"
        "- adapter_productization_surface\n"
        "- session_productization_surface\n"
        "- session_planner_decision\n"
        "- session_continuity_outline\n"
        "- autonomy_posture\n"
        "- resume_expectation\n"
        "- resume_posture\n"
        "- session_posture_cases\n"
        "- productization_case_count\n"
        "- continuity_snapshot\n"
        "- compacted_context_summary\n"
        "- recovery_contract\n"
        "- shared_contract_alignment\n"
        "- shared_productization_contract_ready\n"
        "- native_tool_usage\n"
        "- daily_driver_main_path_ready\n"
        "- daily_driver_main_path_ready_cases\n"
        "- comparison_posture\n"
        "- comparison_posture_basis\n"
        "- comparison_proof_strength\n"
        "- stronger_task_families\n"
        "- broader_repeatability_gap_families\n"
        "- multiple stronger direct-proof families\n"
        "- evidence trend reports\n"
        "- agent_orchestrator.runtime_event_stream.v1\n"
        "- agent_orchestrator.workspace_index.v1\n"
        "- agent_orchestrator.recovery_recommendation.v1\n"
        "- agent_orchestrator.execution_topology_snapshot.v1\n"
        "- stable step-loop\n"
        "- explicit context select plus structured observation\n"
        "- multi-milestone native program-execution evidence chain\n",
        encoding="utf-8",
    )
    (root / "docs" / "architecture").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "architecture" / "coding-agent-goal-spec.md").write_text(
        "# Coding Agent Goal Spec\n\n- governed execution runtime\n",
        encoding="utf-8",
    )
    (root / "docs" / "architecture" / "native-coding-agent-upgrade-plan.md").write_text(
        "# Native Coding Agent Upgrade Plan\n\n- native closure\n",
        encoding="utf-8",
    )
    (root / "docs" / "architecture" / "决策核心-执行拓扑-运行时分层说明.md").write_text(
        "# 决策核心-执行拓扑-运行时分层说明\n\n- 决策核心\n",
        encoding="utf-8",
    )
    for name in [
        "native-coding-agent-phase-0-baseline.md",
        "native-coding-agent-phase-1-kernel-boundary.md",
        "native-coding-agent-phase-2-step-loop-convergence.md",
        "native-coding-agent-phase-4-verify-repair-resume.md",
        "native-coding-agent-phase-5-native-dogfood-track.md",
    ]:
        (root / "docs" / "process" / name).write_text(
            f"# {name}\n\n- native phase fixture\n",
            encoding="utf-8",
        )
    (root / "docs" / "process" / "agent-team-operator-runbook.md").write_text(
        "# 治理控制台操作手册\n\n"
        "- team summary\n"
        "- team next\n"
        "- team runbook\n"
        "- team resume\n"
        "- team roles\n"
        "- lead\n"
        "- planner\n"
        "- reviewer\n"
        "- adversarial_reviewer\n"
        "- builder\n"
        "- validator\n"
        "- rescue\n"
        "- runtime\n"
        "- state_keeper\n"
        "- context_compressor\n"
        "- strategist\n"
        "- topology_compiler\n"
        "- evidence_recorder\n"
        "- memory_curator\n"
        "- approval_gate\n"
        "- team status\n"
        "- team next\n"
        "- team inspect-blockers\n"
        "- team start\n"
        "- team chat\n"
        "- team draft-ready\n"
        "- team task next\n"
        "- team submit-review\n"
        "- team retry-review\n"
        "- team task list\n"
        "- team retry-adversarial-review\n"
        "- team execute\n"
        "- team inspect-blockers\n"
        "- team inspect-docs\n"
        "- team inspect-handoff\n"
        "- team docs-index\n"
        "- native-coding-agent-dogfood-evidence.md\n"
        "- team workspace-status\n"
        "- team context-packet\n"
        "- team topology inspect\n"
        "- team approvals list\n"
        "- team approvals resolve\n"
        "- team evidence-gates\n"
        "- team inspect-execution\n"
        "- team retry-review\n"
        "- team retry-adversarial-review\n"
        "- team check-compliance\n"
        "- team setup\n"
        "- team inspect-knowledge\n"
        "- topology_reason\n"
        "- fallback_reason\n"
        "- fallback_detail\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "ai-work-control-plane-master-plan.md").write_text(
        "# AI Work Control Plane Master Plan\n\n"
        "- AI Work Control Plane\n"
        "- WorkspaceState -> ContextPacket -> StrategyDecision -> ExecutionTopologySnapshot -> ApprovalItem -> EvidenceBundle -> MemoryRecord\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "control-plane-artifact-contracts.md").write_text(
        "# Control Plane Artifact Contracts\n\n"
        "- agent_orchestrator.workspace_state.v1\n"
        "- agent_orchestrator.context_packet.v1\n"
        "- agent_orchestrator.strategy_decision.v1\n"
        "- agent_orchestrator.approval_item.v1\n"
        "- agent_orchestrator.evidence_bundle.v1\n",
        encoding="utf-8",
    )
    decisions_dir = root / "docs" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    for name in [
        "0001-documentation-as-runtime-context.md",
        "0002-handoff-packet-contract.md",
        "0003-canonical-docs-vs-derived-views.md",
        "0004-ai-work-control-plane-reframe.md",
    ]:
        (decisions_dir / name).write_text(
            "# Test ADR\n\n"
            "## Status\n\nAccepted\n\n"
            "## Context\n\nTest context.\n\n"
            "## Decision\n\nTest decision.\n\n"
            "## Consequences\n\nTest consequence.\n\n"
            "## Related Commands\n\n- python -m agent_orchestrator.cli team check-compliance\n",
            encoding="utf-8",
        )
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=root / "plans"),
        project_root=root,
    )
    team.refresh_documentation_sync()


def start_reviewed_session(team: TeamOrchestrator, requirement: str, **start_kwargs):
    session = team.start(requirement, **start_kwargs)
    session = team.mark_draft_ready(session.id)
    return team.submit_draft_for_review(session.id)


def start_approved_session(team: TeamOrchestrator, requirement: str, **start_kwargs):
    session = start_reviewed_session(team, requirement, **start_kwargs)
    required_open = [gap.id for gap in session.gaps if gap.required and gap.status != "closed"]
    if required_open:
        session = team.revise(session.id, summary="Close required test gaps", closed_gap_ids=required_open)
    if session.status != "approved_for_execution":
        session = team.approve(session.id)
    return session


def start_executed_session(team: TeamOrchestrator, requirement: str, mode=None, **start_kwargs):
    session = start_approved_session(team, requirement, **start_kwargs)
    return team.execute(session.id, mode)
