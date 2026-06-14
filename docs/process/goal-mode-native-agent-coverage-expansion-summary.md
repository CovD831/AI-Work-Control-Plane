# Native Agent Coverage Expansion Goal Summary

## One-Paragraph Goal

下一阶段 goal 的核心，不是重复证明 native coding agent 在单一 bounded repo task 上已经可用，而是把这种 defaultability 从“单点成功”推进到“多类真实仓库任务上的稳定覆盖”。目标是让 native path 至少再覆盖两类新增真实任务，同时用 benchmark、recovery 扩展与 learning asset consumption 证明 native 已开始成为更广任务面的默认主执行路径，而 external agent 继续保留为 governed fallback / handoff / comparative benchmark path。

## Four Required Parts

1. `P0 Coverage Expansion`
   让至少两类新增真实仓库任务默认进入 native path。
2. `P1 Comparative Benchmark`
   固定多任务类 benchmark bundle，比较 native / external 的 success、blocked、recovery、cost 与人工介入差异。
3. `P2 Recovery Breadth`
   扩展至少一类新的 failure shape，并明确 continue / block / fallback / handoff 语义。
4. `P3 Learning Consumption`
   让 trajectory / memory / skill 资产至少被 router、planner 或 strategy 的一个真实决策消费。

## Completion Standard

只有当以下条件同时成立，这个 goal 才算完成：

- native 默认路径已至少覆盖三类真实仓库任务，其中两类是本 goal 新增覆盖；
- 已存在稳定的 comparative acceptance / benchmark bundle；
- learning asset 不只被写入，还至少被一次真实路由或规划决策消费；
- external agent 仍可热插拔接入，且 fallback / handoff 继续受治理；
- 文档、evidence、workspace index、runtime/session、UI/CLI summary 至少多个面共享一致证据。

## Current Implementation Snapshot

- native 默认覆盖已从 `DIRECT_FIX` / `GENERAL_CODING` / `DOCS` 扩展到 learning-backed `INVESTIGATION -> EDIT -> VERIFY` 与 bounded multi-file helper/compliance repair evidence cases。
- comparative benchmark bundle 已固定在 `benchmark_evidence_cases()`，并新增 `investigation_to_edit` 与 `multi_file_helper_repair` 两类 coverage-expansion case。
- recovery breadth 现在显式承认 `exploration_ambiguity_or_scope_drift` failure shape，并在 recovery semantics 中投影为 `scope_realign`。
- learning asset 不再只写入：`TaskRouter` 已可消费 `MemoryStore` 中的 native trajectory / learning 资产来支持真实 native path 选择。

## Detail File

完整 goal 细节、阶段验收、文件级验收与停止条件见：

[goal-mode-native-agent-coverage-expansion.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-native-agent-coverage-expansion.md)
