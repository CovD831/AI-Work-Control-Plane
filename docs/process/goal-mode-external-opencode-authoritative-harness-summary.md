# External OpenCode Authoritative Harness Goal Summary

## One-Paragraph Goal

把当前 external OpenCode same-contract harness 从“最小可比记录 + `instrumentation_first` 结论”推进到“authoritative 外部 harness”：同一 5 类 daily-driver case pack 能真实驱动 OpenCode 执行，稳定采集 runtime payload、workspace index、operator summary、failure / pause / recovery reason，并产出可复核的 native vs OpenCode comparative report。这个 goal 不扩 case 数、不做完整 OpenCode 产品集成、不追 TUI / provider / plugin / install / release 生态；它只关闭或坐实 instrumentation gap，让 operator 能判断剩余差距到底是 agent 能力、产品厚度还是生态规模。

## Required Parts

1. `P0 Authoritative Case Runner`
   保持当前 5 类 same-contract case pack 不变，建立能真实执行 OpenCode 的 runner path，并记录 command、exit、duration、workspace changes。
2. `P1 Evidence Surface Normalization`
   将 native 与 OpenCode run record 归一到同一 comparison schema，显式区分 available、unavailable、missing、not_applicable 与 reason。
3. `P2 Real Comparative Report`
   基于真实执行记录对比 pass / pause / fail、recovery quality、evidence completeness、operator readability、cost / latency availability。
4. `P3 Instrumentation Decision Closure`
   判断 `instrumentation_first` 是否可以关闭；若不能关闭，必须坐实还缺哪些 authoritative fields；若能关闭，再判断真实 agent capability gap、product thickness gap 或 ecosystem gap。

## Completion Standard

只有当以下条件同时成立，这个 goal 才算完成：

- 5 类现有 case pack 均通过 authoritative runner 产生 OpenCode run record；
- 每条 OpenCode run record 都来自真实命令执行或明确记录不可执行原因；
- runtime payload 至少包含 command、exit_status、started_at、ended_at、duration_ms；
- workspace index summary 至少包含 changed files 或明确的 no-change / unavailable reason；
- operator summary 能让人不读 raw transcript 判断 outcome、verify / stop、next action；
- failure / pause / recovery reason 被标准化；
- comparative report 明确说明 instrumentation gap 是 closed、partially_closed 还是 still_blocking；
- operator decision 不再只停在默认 `instrumentation_first`，除非 evidence 证明 instrumentation 仍是 blocker。

## Detail File

完整目标意图、阶段验收、authoritative runner 边界、normalization contract、comparative report 与 operator decision 标准见：

[goal-mode-external-opencode-authoritative-harness.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-external-opencode-authoritative-harness.md)

## Current Implementation Note

Implementation now includes normalized records and authoritative reports. Smoke commands remain `instrumentation_still_blocking`; only runs marked with `--authoritative-runner` can close instrumentation.
