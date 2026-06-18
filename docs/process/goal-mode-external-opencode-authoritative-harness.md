# External OpenCode Authoritative Harness Goal

## Goal Intent

当前 external OpenCode same-contract harness 已经把 native / OpenCode 的对比从“口头差距”推进到“同合同 case pack + 最小 OpenCode run record + comparative report + operator decision”。但当前最小 adapter 仍会把 OpenCode 的 model、provider、cost、token、部分 timing 字段显式标成 `unavailable`；因此 operator decision 合理停在 `instrumentation_first`。

本 goal 的目的，是把这一层推进到 authoritative 外部 harness：不是再扩 case，不是做完整产品集成，而是让 OpenCode 侧的执行和采证足够可信，能关闭或坐实 instrumentation gap。

本 goal 完成时，operator 应能回答：

> 在同一 5 类 daily-driver repo task family、同一 case contract、同一 evidence surface 下，OpenCode 真实执行后与 native 的差距到底来自 agent capability、product thickness、ecosystem，还是 instrumentation 仍不等价？

## Target Outcome

完成后，当前项目应从：

- same-contract case pack 已存在；
- OpenCode runner record schema 已存在；
- adapter 可通过 command-template 生成最小执行记录；
- comparative report 可输出 `instrumentation_first`；
- 但 OpenCode evidence surface 仍不够 authoritative；

推进到：

- OpenCode runner 能对每个 case 真实执行或明确记录不可执行原因；
- run record 中 command / exit / duration / workspace change / summary / recovery reason 可复核；
- native 与 OpenCode 的 run record 被归一到同一 normalized comparison schema；
- comparative report 能区分 instrumentation closed / partially closed / still blocking；
- operator decision 能从 `instrumentation_first` 进入 capability / product / ecosystem 的真实判断，或证明仍必须先补 instrumentation。

## Current Baseline

已完成并可复用：

- `docs/process/external-opencode-same-contract-cases.json`
  - 5 类 same-contract cases；
  - fixed input、expected outputs、verify / stop、pause / failure conditions；
  - native / OpenCode runner entry；
  - required evidence surface。
- `src/agent_orchestrator/opencode_harness.py`
  - case pack builder；
  - native run record builder；
  - OpenCode run record builder；
  - optional command-template execution；
  - comparative report；
  - operator decision。
- CLI entrypoints：
  - `agent-orchestrator evidence case-pack`
  - `agent-orchestrator evidence native-run`
  - `agent-orchestrator evidence opencode-run`
  - `agent-orchestrator evidence external-report`
- 当前默认 operator decision：`instrumentation_first`。

## Scope Boundary

本 goal 只包含以下四部分。

### P0 Authoritative Case Runner

目标：让 OpenCode runner 对同一 case pack 形成 authoritative run records。

必须完成：

- 保持 5 类 task family 不变：
  - `docs_update`
  - `single_file_repair`
  - `multi_file_operator_surface`
  - `test_driven_small_feature`
  - `failure_clarify_approval_path`
- runner 能逐 case 执行；
- 每个 case 至少记录：
  - command；
  - started_at；
  - ended_at；
  - duration_ms；
  - exit_status；
  - stdout / stderr 摘要或 artifact pointer；
  - workspace before / after summary；
  - verification command 或 manual verify result；
  - failure / pause / stop / recovery reason。
- 如果无法真实调用 OpenCode，必须记录：
  - unavailable reason；
  - blocker type；
  - whether this blocks capability comparison；
  - next action required。

P0 不要求完整 OpenCode 产品集成；只要求 authoritative enough for comparison。

### P1 Evidence Surface Normalization

目标：将 native 与 OpenCode run record 归一为同一 comparison schema。

必须标准化：

- `runtime_payload`
  - `available`
  - `unavailable`
  - `missing`
  - `not_applicable`
  - `reason`
- `workspace_index_summary`
  - changed files；
  - no-change；
  - diff unavailable；
  - artifact pointer。
- `operator_summary`
  - outcome；
  - verify / stop；
  - next action；
  - readability rating 或 equivalent marker。
- `failure_pause_recovery_reason`
  - failure reason；
  - pause reason；
  - recovery reason；
  - stop reason；
  - unavailable reason。
- `cost_latency_availability`
  - duration；
  - model；
  - provider；
  - token；
  - cost；
  - unavailable reason。

Normalization 的目标不是让所有字段都有值，而是让缺失可解释、可比较、不可混淆。

### P2 Real Comparative Report

目标：基于 normalized run records 产出 real comparative report。

报告必须包含：

- per-case result：
  - native status；
  - OpenCode status；
  - verify / stop consistency；
  - command execution evidence；
  - workspace evidence。
- per-case deltas：
  - recovery quality delta；
  - evidence completeness delta；
  - operator readability delta；
  - cost / latency availability delta。
- instrumentation closure：
  - `closed`：字段足够判断真实能力差距；
  - `partially_closed`：部分 task family 可比，部分仍受 instrumentation 限制；
  - `still_blocking`：不能做真实能力判断。
- gap classification：
  - `agent_capability_gap`
  - `product_thickness_gap`
  - `ecosystem_gap`
  - `instrumentation_gap`

### P3 Instrumentation Decision Closure

目标：把当前默认 `instrumentation_first` 推进成明确决策。

可接受决策：

1. `instrumentation_closed_native_productization_next`
   OpenCode evidence surface 足够可比，native 执行能力不弱，主要差距是产品厚度 / TUI / provider / install release。
2. `instrumentation_closed_continue_opencode_ecosystem_chase`
   OpenCode 在真实同合同任务完成、recovery 或 operator readability 上显著领先。
3. `instrumentation_partially_closed_mixed_strategy`
   部分任务族可以判断，部分任务族仍需补采证。
4. `instrumentation_still_blocking`
   OpenCode authoritative fields 仍不足，不能做能力结论。

P3 必须给出：

- decision；
- reason；
- evidence pointers；
- next moves；
- explicit non-moves。

## Normalized Record Shape

```json
{
  "normalized_record_version": "external_opencode_authoritative_normalized_record.v1",
  "runner": "native|opencode",
  "case_id": "docs_update_001",
  "task_family": "docs_update",
  "status": "pass|pause|fail|stop|blocked",
  "runtime_payload": {
    "command": {"state": "available", "value": "..."},
    "exit_status": {"state": "available", "value": 0},
    "started_at": {"state": "available", "value": "..."},
    "ended_at": {"state": "available", "value": "..."},
    "duration_ms": {"state": "available", "value": 1234},
    "model": {"state": "unavailable", "reason": "..."},
    "provider": {"state": "unavailable", "reason": "..."},
    "cost": {"state": "unavailable", "reason": "..."}
  },
  "workspace_index_summary": {
    "state": "available|unavailable|not_applicable",
    "changed_files": [],
    "artifact_pointer": "...",
    "reason": "..."
  },
  "operator_summary": {
    "outcome": "...",
    "verify_or_stop": "verify|stop",
    "next_action": "...",
    "readability": "clear|partial|unclear"
  },
  "failure_pause_recovery_reason": {
    "failure_reason": "none|...",
    "pause_reason": "none|...",
    "recovery_reason": "none|...",
    "stop_reason": "none|..."
  }
}
```

## Global Stopping Criteria

只有以下条件全部满足，goal 才能停止：

1. `P0`、`P1`、`P2`、`P3` 全部完成。
2. 5 类 case 均有 authoritative OpenCode run record，或明确 blocker reason。
3. run record 至少包含 command、exit_status、started_at、ended_at、duration_ms。
4. workspace index summary 对每个 case 可比较，或明确 unavailable reason。
5. native / OpenCode 都能生成 normalized records。
6. comparative report 使用 normalized records，而不是只读 raw run record。
7. instrumentation closure 被明确标为 closed / partially_closed / still_blocking。
8. operator decision 不再只是默认 `instrumentation_first`，除非 evidence 明确证明 still_blocking。
9. 不扩大到完整 OpenCode 产品集成、TUI、provider、plugin、install release 或 benchmark 平台。

## Phase Acceptance Criteria

### P0 Acceptance

- runner 可逐 case 执行；
- 每个 case 有 command execution evidence；
- 每个 case 有 duration 与 exit status；
- 每个 case 有 workspace before / after 或 unavailable reason；
- 不可执行时 blocker reason 可读。

### P1 Acceptance

- native record 可 normalized；
- OpenCode record 可 normalized；
- unavailable / missing / not_applicable 明确区分；
- cost / latency 可得性被独立表达；
- failure / pause / recovery reason 被标准化。

### P2 Acceptance

- comparative report 使用 normalized records；
- 每 case 有 status delta；
- 每 case 有 evidence completeness delta；
- 每 case 有 recovery quality delta；
- 每 case 有 operator readability delta；
- report 明确 instrumentation closure。

### P3 Acceptance

- decision 是四个允许值之一；
- reason 引用 report evidence；
- next moves 1-3 个；
- non-moves 明确；
- 决策没有把 instrumentation 缺失误判成 agent 能力差距。

## Anti-Local-Optimum Guardrail

以下情况应停止当前 goal 或转入后续 goal：

1. 5 类 case 已能 authoritative compare，但继续只是在加更多 case。
2. instrumentation 已 closed，但继续留在 harness 层做产品化。
3. instrumentation still blocking 已被证明，但继续主观判断能力差距。
4. 主要差距已是 TUI / install / provider / plugin，却继续修改 runner schema。
5. 需要真实 OpenCode CLI / 环境权限，但当前环境不可用；此时只能记录 blocker，不能伪造 authoritative evidence。

## Non-Goals

本 goal 不包含：

- 完整 OpenCode clone；
- TUI / Desktop / Web；
- provider marketplace；
- plugin ecosystem；
- install / release packaging；
- 扩大到更多 benchmark suites；
- 修改 5 类 case family 范围；
- 把 unavailable 字段静默当作失败或成功。

## Current Implementation Note

The current harness now separates smoke execution from authoritative OpenCode execution:

- `agent-orchestrator evidence opencode-run --command-template ...` records command / exit / timing, but remains `instrumentation_still_blocking` because a smoke command is not proof of authoritative OpenCode behavior.
- `agent-orchestrator evidence opencode-run --command-template ... --authoritative-runner` marks the runner as authoritative and allows the normalized report to close instrumentation when required runtime fields are available.
- `agent-orchestrator evidence normalize-records` writes `external_opencode_authoritative_normalized_record.v1` records.
- `agent-orchestrator evidence authoritative-report` writes `native_vs_opencode_authoritative_comparative_evidence.v1` and reports `instrumentation_closure.status` as `closed`, `partially_closed`, or `still_blocking`.

This preserves the goal boundary: the harness can prove instrumentation closure only when the operator explicitly supplies an authoritative OpenCode runner; otherwise it records a blocker instead of pretending a smoke command is a real OpenCode comparison.
