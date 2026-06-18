# Daily Driver Repo Task Repeatability Goal Summary

## One-Paragraph Goal

把当前已经打通的 native coding-agent 平台能力，从“单类真实任务可验收”推进到“多类真实 repo 任务可重复稳定跑通”。本 goal 只追求多任务族基线、repeatability harness、daily-driver-ready 验收和 OpenCode 差距报告被做实：文档更新、单文件修复、多文件 operator surface / CLI 投影修复、测试驱动小功能补齐、failure / clarify / approval pause 路径任务都要能被真实输入、执行、验证和留痕。它不追求继续加字段或做更厚的产品表面，只追求证明当前 native agent 已经足够支撑日常使用。

## Required Parts

1. `P0 Multi-Task Baseline`
   选 3~5 类真实 repo 任务，每类至少 1 个真实 case，补齐输入、执行、验证和 evidence，并形成 case matrix。
2. `P1 Repeatability Harness`
   建立内部 harness，同一类任务可重复跑，并输出 runtime payload / workspace index / CLI summary。
3. `P2 Daily Driver Acceptance`
   定义 daily-driver-ready 标准，至少 3 类任务通过，失败必须有明确下一步语义。
4. `P3 Gap Report vs OpenCode`
   产出 operator 可读差距报告，明确哪些已经不差，哪些仍是产品厚度和生态差距。

## Completion Standard

只有当以下条件同时成立，这个 goal 才算完成：

- 至少 3 类真实 repo 任务通过；
- 每类至少 1 个真实 repo case；
- 每个 case 都有 verify 或明确 stop；
- 不能只靠 mock；
- 失败必须有下一步语义；
- runtime payload / workspace index / CLI summary 至少两个面能看到同一条事实链；
- 已有直接验证或等价测试证明 repeatability harness 和多任务族基线真实生效。

## Current Evidence Snapshot

- P0 complete: the evidence catalog now covers the 5 requested task families through real repo cases: docs update (`standard_plan_artifact`, `followup_checklist_recovery`, `cli_workflow_hardening`), single-file/repair path (`repair_resume_success`), multi-file operator surface (`repo_task_acceptance*`), test-driven feature/program execution (`multi_milestone_program_execution`), and failure / clarify / approval pause (`compliance_blocking_recovery`, `interrupted_task_resume`).
- P1 complete: repeatability harness is emitted as `agent_orchestrator.daily_driver_repeatability_harness.v1`, with runtime payload / workspace index / CLI summary contract outputs and pass / pause / fail / recovery reason fields.
- P2 complete: `agent_orchestrator.daily_driver_runner_artifact.v1` ties the matrix and harness into a reusable runner shape with runner status, family count, per-family steps, contract outputs, and next external step.
- P3 complete: operator-readable gap report keeps the strategic remaining gap at external OpenCode harness plus TUI / plugin / provider / installation / release thickness, not base native agent capability.
- verdict: daily-driver repo-task repeatability is internally proven for the requested scope; the next goal should be an external same-contract OpenCode harness if comparison-grade evidence is required.

## Detail File

完整目标意图、阶段验收标准、防止局部最优迭代的约束、文件级验证目标与非目标见：

[goal-mode-daily-driver-repeatability.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-daily-driver-repeatability.md)
