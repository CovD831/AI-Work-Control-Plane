# Goal Mode Template Summary

## One-Paragraph Goal

把 `[当前能力 / 当前状态]` 推进到 `[目标能力 / 可验收状态]`。本 goal 只追求 `[核心闭环 / 核心能力]` 被做实：`[关键动作 1]`、`[关键动作 2]`、`[关键动作 3]`、`[关键动作 4]`。它不追求 `[明确排除的大产品化目标]`，只追求让 `[目标路径 / 目标模块]` 足够可用、可回归、可验收。

## Required Parts

1. `P0 [Foundation / Baseline]`
   建立最小但真实的基础链路。
2. `P1 [Main Capability]`
   把核心能力接入主链路，而不是停留在 helper 或 demo。
3. `P2 [Recovery / Governance / Edge Case]`
   让失败、暂停、恢复、审批或边界情况成为正式语义。
4. `P3 [Operator Visibility / Evidence]`
   让结果、状态和下一步能被 operator 直接判断。

## Completion Standard

只有当以下条件同时成立，这个 goal 才算完成：

- 至少一类真实任务可以稳定通过本 goal 的主链路，而不是只停留在接口存在或 demo 跑通；
- 任务过程中可以明确看到输入、关键动作、状态变化和输出结果；
- 失败、暂停、恢复或边界情况有明确语义，不会破坏既有 control plane 约束；
- CLI / UI / workspace index / runtime payload / docs 至少两个面能看到同一条事实链；
- 已有直接验证或等价测试证明主链路真实生效。

## Detail File

完整目标意图、终止条件、阶段验收标准、防止局部最优迭代的约束、文件级验证目标与非目标见：

[goal-mode-template-detail.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-template-detail.md)

