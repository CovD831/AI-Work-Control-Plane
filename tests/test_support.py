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
    (root / "src" / "agent_orchestrator" / "__init__.py").write_text('"""package"""\n', encoding="utf-8")
    (root / "src" / "agent_orchestrator" / "stub.py").write_text(
        '"""Stub module."""\n\nfrom __future__ import annotations\n\n# DEPS: __future__\n# RESPONSIBILITY: Provide a compliant module for minimal process-doc test fixtures.\n# MODULE: tests\n# ---\n\nVALUE = 1\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# temp\n\n- 长周期主执行计划\n- agent-team-operator-runbook.md\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "长周期主执行计划.md").write_text(
        "# 长周期主执行计划\n\n- 文档同步 / compliance / hook blocking\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "agent-orchestrator-implementation-process.md").write_text(
        "# Agent Orchestrator Product Process\n\n- hook-based compliance checks\n",
        encoding="utf-8",
    )
    (root / "docs" / "architecture").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "architecture" / "决策核心-执行拓扑-运行时分层说明.md").write_text(
        "# 决策核心-执行拓扑-运行时分层说明\n\n- 决策核心\n",
        encoding="utf-8",
    )
    (root / "docs" / "process" / "agent-team-operator-runbook.md").write_text(
        "# Agent Team Operator Runbook\n\n"
        "- team summary\n"
        "- team next\n"
        "- team runbook\n"
        "- team resume\n"
        "- team inspect-blockers\n"
        "- team inspect-execution\n"
        "- team retry-review\n"
        "- team retry-adversarial-review\n"
        "- team check-compliance\n"
        "- topology_reason\n"
        "- fallback_reason\n"
        "- fallback_detail\n",
        encoding="utf-8",
    )
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=root / "plans"),
        project_root=root,
    )
    team.refresh_documentation_sync()
