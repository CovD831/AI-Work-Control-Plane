# External OpenCode Same-Contract Harness Goal Summary

## One-Paragraph Goal

把当前已经 internally proven 的 native daily-driver repeatability，从“内部 5 类 repo task family 已证明”推进到“可以和 OpenCode 在同一任务合同、同一任务族、同一 evidence surface 下做外部对比”。本 goal 只追求同合同 case pack、最小 OpenCode runner adapter、comparative evidence report 和 operator decision 被做实；它不追求完整 OpenCode 产品集成，也不追求立即追平 OpenCode 的 TUI / provider / plugin / install / release 生态。

## Required Parts

1. `P0 Same-Contract Case Pack`
   复用当前 5 类 daily-driver repo task family，固定输入、预期输出、verify / stop 标准，产出 native 与 OpenCode 双方都能运行的 case contract。
2. `P1 OpenCode Runner Adapter`
   建立最小外部 runner adapter，能执行同一 case pack，并输出 runtime payload、workspace index 等价摘要、CLI / operator summary 等价摘要、failure / pause / recovery reason。
3. `P2 Comparative Evidence Report`
   对比 native vs OpenCode 的 pass / pause / fail、recovery quality、evidence completeness、operator readability、cost / latency 可得性。
4. `P3 Operator Decision`
   基于对比证据判断下一步是继续追 OpenCode 生态能力，还是转向 native 平台 productization / TUI / provider / install release。

## Completion Standard

只有当以下条件同时成立，这个 goal 才算完成：

- 5 类 daily-driver repo task family 都有 same-contract case；
- 每个 case 都固定输入、预期输出、verify / stop 标准和 evidence surface；
- native 与 OpenCode 至少能在同一 contract schema 下产出可比 run record；
- OpenCode runner adapter 明确记录 pass / pause / fail、failure / pause / recovery reason；
- comparative report 明确区分真实 agent 能力差距、产品厚度差距和生态规模差距；
- operator 能据此做出继续追 OpenCode 生态或转向 native productization 的决策；
- 不得把本 goal 扩大为完整 OpenCode 集成、全面外部 benchmark 平台或 native 产品化实现。

## Current Evidence Baseline

- 起点：`goal-mode-daily-driver-repeatability` 已将 native daily-driver repo-task repeatability 内部证明为完成状态。
- 复用任务族：docs update、single-file repair、multi-file operator surface / CLI projection、test-driven small feature、failure / clarify / approval pause path。
- 复用 evidence surface：runtime payload、workspace index、CLI / operator summary、verify / stop、failure / pause / recovery reason。
- 下一层证据重点：不是证明 native 能跑，而是证明 native 与 OpenCode 在同一合同下如何差异化。

## Detail File

完整目标意图、case contract、runner adapter 最小边界、comparative report 结构、operator decision 标准、防止局部最优迭代的约束与非目标见：

[goal-mode-external-opencode-harness.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-external-opencode-harness.md)
