# Native Productization After Instrumentation Closure Goal Summary

## One-Paragraph Goal

把当前已经完成 authoritative OpenCode comparison harness 之后的结论，推进到 native 平台 productization：既然 same-contract / authoritative path 已经能区分 smoke runner 与 authoritative runner，并能在 authoritative path 下关闭 instrumentation gap，下一步不再继续扩 harness schema，而是把 native daily-driver 做成 operator 真正可日用的产品入口。本 goal 只追求 operator product surface、daily-driver CLI / TUI entry、provider / runtime setup diagnosis、install / release readiness、evidence consumption 被做实；它不追求完整 Desktop/Web、插件生态、provider marketplace 或大规模社区发行。

## Required Parts

1. `P0 Operator Product Surface`
   让 operator 能从一个入口看到 active goal、run status、evidence、provider posture、next action。
2. `P1 Daily-Driver CLI / TUI Entry`
   提供最小可日用入口：启动任务、查看状态、查看 evidence、继续或停止。
3. `P2 Provider / Runtime Setup Diagnosis`
   明确 OpenAI / Codex / Claude / local mock 等 runtime 的配置状态、可用性和修复建议。
4. `P3 Install / Release Readiness`
   给出本地安装、启动、smoke test、release checklist 的可复现路径。
5. `P4 Evidence Consumption`
   把 daily-driver repeatability 与 authoritative OpenCode comparison 结论转成 operator 可读 report，而不是只停留在 raw JSON。

## Completion Standard

只有当以下条件同时成立，这个 goal 才算完成：

- operator 能从一个稳定入口看到 native 当前状态；
- 能运行一个 daily-driver task 或 smoke task；
- 能看到 evidence summary 和 next action；
- provider / runtime setup 有诊断与修复建议；
- install / start / smoke test 路径可复现；
- authoritative OpenCode comparison 的结论能被 operator 消费；
- 最终明确下一步是 TUI 深化、provider 扩展、install release，还是回头补 agent capability。

## Detail File

完整目标意图、阶段验收、停止条件、防止局部最优扩张的 guardrail、文件级验证目标和非目标见：

[goal-mode-native-productization-after-instrumentation.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-native-productization-after-instrumentation.md)
