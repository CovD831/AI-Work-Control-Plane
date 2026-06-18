# Agent Orchestrator Product Process

## 执行方式

- 主计划驱动。
- 不再把每次实现包装成新的独立小计划。
- 验证通过后自动进入下一段。
- targeted tests 通过后进入下一 phase。
- 当前执行层更接近 `单编排器 + 多角色语义 + 持久化工作流`。
- 当前执行层还不是高自治、多中心协商式的 multi-agent system。
- surface convergence 以 canonical contracts 为中心，projection surfaces 不是新的 durable state。

## 当前过程状态

- `in_progress - basic gate active`
- `in_progress - basic refresh and compliance checks active`
- `in_progress - changed-file scoped pre-commit gate active`
- `team check-compliance`

## 关键约束

- Missing plan/checklist/review-round persistence is now blocked.
- visible reviewer fallback policy 必须存在，并记录 fallback source, reason, detail, and preferred reviewer。
- structured topology rationale 必须可见。
- operator-runbook signal compliance 必须通过。
- Operator runbook drift for topology and provider fallback signals is now blocked.
- Checklist ownership is now explicit on persisted plan items.
- hook-based compliance checks 已激活，旧的“未启用”表述不应再保留。

## 运行模式

- `cli_inherit`
- `cli_isolated`
- `direct_api`

## 当前阶段认知

- native coding-agent dogfood baseline
- 当前执行层更接近 workflow-governed orchestration runtime，而不是高自治 agent federation。
- docs/process/agent-evolution-master-plan.md 是后续演进协议。
- targetted tests 通过后进入下一 phase。
- `--changed-file` 是 compliance / docs drift 的最小作用域输入。
