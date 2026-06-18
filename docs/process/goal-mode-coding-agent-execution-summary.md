# Coding Agent Execution Goal Summary

## One-Paragraph Goal

把当前项目的执行层 coding agent 从“有控制平面和受治理工具面”推进到“可以稳定完成真实开发任务的 first-party execution path”。本 goal 只追求把开发任务的核心闭环做实：任务理解、上下文选择、工具调用、文件修改、验证、审批暂停、恢复继续、结果投影。它不追求全面追平 `research_repos/opencode/` 的产品厚度，只追求让当前项目的 native execution path 足够可用、可回归、可验收。

## Required Parts

1. `P0 Execution Loop`
   建立稳定的任务-上下文-工具-验证执行闭环。
2. `P1 Editing And Verification`
   让文件修改、补丁应用、验证与失败修复进入主链路。
3. `P2 Recovery And Approval`
   让审批暂停、恢复继续、状态回放和证据投影成为正式语义。
4. `P3 Operator Visibility`
   让 CLI / UI / workspace index 能清楚展示执行状态、改动结果和恢复姿态。

## Completion Standard

只有当以下条件同时成立，这个 goal 才算完成：

- 执行层能够稳定完成至少一类真实开发任务，而不是只停留在工具存在或 demo 跑通；
- 任务执行过程中可以明确看到上下文选择、工具使用、文件修改和验证结果；
- 审批暂停与恢复继续语义可用，并且不会破坏既有 control plane 约束；
- CLI / UI / workspace index / runtime payload 至少两个面能看到同一条执行事实链；
- 已有直接验证或等价测试证明主链路真实生效。

## Detail File

完整终止条件、验收标准、防止局部最优迭代的约束、文件级验证目标与非目标见：

[goal-mode-coding-agent-execution.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-coding-agent-execution.md)
