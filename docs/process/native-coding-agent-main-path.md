# Native Coding Agent Main Path

## Purpose

本文件描述当前仓库中 first-party native coding agent 的主路径接入状态，重点说明三件已经进入真实实现的能力：

1. `P0 原生工具面`
2. `P1 原生 planner`
3. `P2 原生/外部 agent 统一适配层`

它不是未来计划，而是当前工作树中已经落地的主路径说明。

## Main Path Summary

当前 native coding agent 主路径为：

`TaskRouter -> IntentIntake -> NativeStrategyPlanner -> SessionRuntime -> CodingAgentExecutionRuntime -> NativeToolbox -> Verify/Repair/Resume -> UI / Evidence / Recovery projections`

这条路径的关键点是：

- coding task 默认进入 `ExecutionMode.CODING_AGENT`
- strategy 选择优先由 `NativeStrategyPlanner` 决定，而不是由 compatibility planner 主导
- runtime 主路径通过显式 `NativeToolbox` 暴露 `read/search/glob/structured_patch/verify`
- native runtime 和 legacy/external runtime 都返回统一结构的 `UnifiedAgentAdapterContract`
- session snapshot、runtime payload、UI summary 都能看到 native planner 和 adapter contract 的结果
- route / strategy / runtime / UI 现在都能看到 `default_path`、`operating_boundary`、`selection_reason`、`handoff_reason_code`、`fallback_reason_code`

## P0 Native Tool Surface

当前原生工具面定义在：

- `src/agent_orchestrator/execution/native_tools.py`

当前显式工具包括：

- `read`
- `search`
- `glob`
- `structured_patch`
- `verify`

这些工具当前已经被接入：

- `RepoExplorer`
- `EditExecutor`
- `VerificationRunner`
- `CodingAgentExecutionRuntime`

当前主路径语义：

- `glob/search/read` 用于 repo understanding
- `structured_patch` 用于受治理的 bounded edit
- `verify` 用于受治理的 bounded verification

治理语义：

- workspace boundary policy 仍然有效
- approval hook 仍然有效
- artifact / evidence 输出仍然有效
- tool 不是绕过 control plane 的裸能力

## P1 Native Planner

当前原生 planner 定义在：

- `src/agent_orchestrator/strategy/planner.py`

当前新增能力：

- `NativeStrategyPlanner`
- `planner_family`
- `planner_actions`
- `operating_boundary`
- `selection_reason`
- `handoff_reason_code`
- `fallback_reason_code`

当前 planner 可以把主路径明确区分为至少以下行为组合：

- `edit -> verify`
- `explore -> edit -> verify`
- `clarify -> explore -> edit -> verify`
- `clarify -> approval_pause`
- `explore -> handoff_external`

当前约束：

- compatibility planner 仍然存在，用于旧路径和兼容场景
- 但 native coding runtime 主路径不再默认让 compatibility planner 主导

当前进入的正式链路：

- runtime payload 中的 `strategy_summary`
- runtime payload 中的 `planner_family`
- session snapshot 中的 `planner_family`
- UI execution runtime summary

## P2 Unified Native / External Adapter Contract

当前统一契约定义在：

- `src/agent_orchestrator/execution/models.py`

契约名称：

- `UnifiedAgentAdapterContract`

当前接入路径：

- native runtime: `CodingAgentExecutionRuntime`
- external / legacy runtime: `LegacyExecutionRuntime`

当前共享语义：

- execution contract
- runtime metadata
- path selection metadata
- approval semantics
- evidence outputs
- recovery surfaces

这意味着：

- native path 和 external path 现在已经不是完全割裂的两套 runtime shape
- 二者至少在 execution-level governance contract 上进入了同一结构

## Session And UI Projection

当前 session continuity 已经开始记录：

- `selected_execution_strategy`
- `planner_family`
- `compatibility_metadata`

当前 UI summary 已经开始展示：

- runtime name
- planner family
- adapter family
- kernel role
- context engineering and step-loop summary
- default path / operating boundary / selection reason

## P3 Learning Asset Externalization

当前 native 主路径已开始把执行经验外化为稳定资产：

- `SessionRuntime` 写入 session-scoped `trajectories`
- `MemoryStore` 写入 `native_trajectory` 与 `native_learning`
- `KnowledgeStore` 写入 curator-ready `lessons` 与 `skills`

当前约定的外化规则：

- facts -> `Memory`
- procedures -> `Skill`
- boundary/policy decisions -> curator metadata / future policy assets

## Verification Evidence

当前已有直接验证覆盖以下层级：

- runtime tests
- strategy planner tests
- legacy runtime tests
- session runtime tests
- CLI surface tests
- UI summary tests

高信号验证命令：

```bash
pytest tests/test_strategy_planner.py tests/test_execution_runtime_legacy.py tests/test_coding_agent_runtime.py -q
pytest tests/test_session_runtime.py tests/test_cli.py tests/test_ui_service.py -q -k 'planner_family or adapter_family or execute_cli_request_runs_legacy_runtime_for_coding_tasks or dashboard_summarizes_coding_agent_execution_artifacts or dashboard_lists_sessions_and_builds_detail'
```

## Boundary

当前状态仍不等于“完全完成”：

- 还不代表整个仓库已经在所有 execution/team/control-plane surfaces 上完全收敛
- 还不代表所有 docs、all-tests、all-evidence 都已完成最终收口
- 还不代表已经全面达到 `opencode` 的产品厚度

但它已经意味着：

- native tool surface 不再只是目标
- native planner 不再只是概念
- unified adapter contract 不再只是文档想法

它们都已经进入真实代码与主路径的一部分。
