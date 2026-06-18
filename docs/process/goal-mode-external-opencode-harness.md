# External OpenCode Same-Contract Harness Goal

## Goal Intent

本 goal 的目的，是把当前已经 internally proven 的 native daily-driver repeatability，推进到“可与 OpenCode 做同合同、同任务族、同 evidence surface 的外部对比”。

这里的外部对比不是泛泛地问“OpenCode 好不好”，也不是立刻做完整产品集成；它只回答一个 operator 决策问题：

> 在相同 repo task family、相同 case contract、相同 evidence surface 下，native 与 OpenCode 的差距到底是 agent 能力差距、产品厚度差距，还是生态规模差距？

因此，本 goal 的核心不是新增更多 native 能力，而是把已有 native repeatability 变成 comparison-grade evidence：

- 同一 case pack；
- 同一输入与预期输出；
- 同一 verify / stop 标准；
- 同一 pass / pause / fail 语义；
- 同一 runtime payload / workspace index / CLI summary evidence surface；
- 同一 failure / pause / recovery reason 记录；
- 最后形成 operator 可读的 comparative evidence report。

本 goal 必须避免变成 OpenCode 生态追逐、TUI 产品化、provider 集成或安装发布工程。那些可以成为后续决策结果，但不是本 goal 的实现范围。

## Target Outcome

完成后，当前项目应从：

- native daily-driver repeatability 已内部证明；
- 5 类 daily-driver repo task family 已有内部 evidence；
- OpenCode 差距仍停留在定性判断；
- operator 还不能确认差距来自 agent 能力、产品厚度还是生态规模；

推进到：

- 5 类任务族被封装成 same-contract case pack；
- native / OpenCode 可运行同一 contract；
- OpenCode runner adapter 能输出等价 evidence surface；
- native vs OpenCode 的 pass / pause / fail 与 recovery quality 可对照；
- comparative evidence report 能明确归因差距类型；
- operator 能决定继续追 OpenCode 生态，或转向 native productization / TUI / provider / install release。

## Current Baseline

本 goal 的前置基线来自 `goal-mode-daily-driver-repeatability`：

- `P0` 已完成：native catalog 覆盖 5 类 daily-driver repo task family。
- `P1` 已完成：native harness 已记录 runtime payload / workspace index / CLI summary contract outputs，以及 pass / pause / fail / recovery reasons。
- `P2` 已完成：native daily-driver runner artifact 已把 case matrix 与 harness 连接为可复用 runner evidence。
- `P3` 已完成：上一阶段 gap report 已判断剩余关键缺口是 external OpenCode harness 与产品 / 生态厚度。

本 goal 不重新证明 native repeatability；它复用该结论作为 external comparison 的输入。

## Scope Boundary

本 goal 只包含以下四个实现部分，且都必须完成。

### P0 Same-Contract Case Pack

复用当前 5 类 daily-driver repo task family，形成 native / OpenCode 双方都能运行的 case contract。

任务族必须覆盖：

1. `docs_update`
   文档更新、计划同步、summary / detail 对照。
2. `single_file_repair`
   单文件代码修复或小范围行为修复。
3. `multi_file_operator_surface`
   多文件 operator surface / CLI projection / artifact consistency 修复。
4. `test_driven_small_feature`
   测试驱动的小功能补齐或 contract hardening。
5. `failure_clarify_approval_path`
   failure、clarify、approval pause、resume 或 stop 路径任务。

每个 case contract 必须固定：

- `case_id`
- `task_family`
- `repo_state_ref` 或等价 workspace baseline
- `input_prompt`
- `allowed_files` / `expected_touch_scope`
- `expected_outputs`
- `verify_command` 或 `manual_verify_contract`
- `stop_condition`
- `pause_condition`
- `failure_condition`
- `required_evidence_surface`
- `native_runner_entry`
- `opencode_runner_entry`
- `comparison_notes`

P0 不要求新增更多任务族；新增任务族会稀释对比质量。

### P1 OpenCode Runner Adapter

建立最小外部 runner adapter，让 OpenCode 能执行同一 case pack，并输出与 native 可比的 run record。

P1 不追求完整产品集成，只要求最小可比输出：

- `runtime_payload`
  - command / prompt / model 或 provider 可得信息；
  - started / ended / duration 可得信息；
  - exit status 或 run status；
  - touched files 或可得 diff summary。
- `workspace_index_summary`
  - changed files；
  - created artifacts；
  - verify commands；
  - equivalent repo state summary。
- `operator_summary`
  - user-facing outcome；
  - pass / pause / fail；
  - next action；
  - verification evidence。
- `failure_pause_recovery_reason`
  - failure reason；
  - pause reason；
  - recovery action；
  - stop reason；
  - unavailable reason when OpenCode cannot expose a field。

Adapter 输出必须允许字段缺失，但字段缺失必须显式记录为 `unavailable`，不能静默省略。这样才能区分能力缺失与 evidence surface 缺失。

### P2 Comparative Evidence Report

产出 native vs OpenCode 的 comparison-grade evidence report。

报告至少包含以下维度：

- `case_result`
  - native pass / pause / fail；
  - OpenCode pass / pause / fail；
  - verify / stop 是否一致。
- `recovery_quality`
  - 是否能识别 failure；
  - 是否能提出下一步；
  - 是否能 resume；
  - 是否避免破坏 workspace。
- `evidence_completeness`
  - runtime payload 完整度；
  - workspace index 等价摘要完整度；
  - CLI / operator summary 可读性；
  - verify evidence 可追溯性。
- `operator_readability`
  - operator 是否能不用读完整 transcript 就判断结果；
  - pause / fail / recovery reason 是否语义化；
  - next action 是否明确。
- `cost_latency_availability`
  - cost 是否可得；
  - latency 是否可得；
  - token / model / provider 信息是否可得；
  - 不可得时是否清楚标记 unavailable。
- `gap_classification`
  - `agent_capability_gap`：同合同下任务完成能力、修复质量、验证质量的真实差距；
  - `product_thickness_gap`：TUI、operator UX、summary presentation、install / release 体验差距；
  - `ecosystem_gap`：provider、plugin、community、external integration、benchmark 生态差距；
  - `instrumentation_gap`：能力可能存在，但 evidence surface 无法等价导出的差距。

P2 的输出必须避免把所有 OpenCode 强项都归为 agent 能力，也避免把 native 缺少 TUI 误判为任务执行能力不足。

### P3 Operator Decision

基于 P2 report 给出 operator decision。

决策必须落在以下路径之一：

1. `continue_opencode_ecosystem_chase`
   当 OpenCode 在同合同任务完成、recovery quality 或 evidence completeness 上显著领先，且差距不能通过轻量 adapter / product layer 弥补。
2. `native_productization_next`
   当 native 在同合同任务执行上基本不弱，主要差距来自 TUI、operator readability、provider、install release 或生态厚度。
3. `instrumentation_first`
   当对比结果主要受 evidence surface 不等价影响，尚不能判断真实 agent 能力差距。
4. `mixed_strategy`
   当不同任务族显示不同差距，需要按任务族分流：部分追 OpenCode，部分 native productization。

P3 必须给出：

- recommended path；
- reason；
- evidence pointers；
- next 1-3 concrete moves；
- explicit non-moves。

## Same-Contract Case Pack Shape

建议 case pack 使用以下逻辑 shape；具体可落地为 JSON、YAML 或 Python fixture，但字段语义必须保持稳定。

```json
{
  "contract_version": "external_opencode_same_contract.v1",
  "cases": [
    {
      "case_id": "docs_update_001",
      "task_family": "docs_update",
      "repo_state_ref": "<commit-or-fixture-ref>",
      "input_prompt": "<fixed task prompt>",
      "expected_touch_scope": ["docs/process/**"],
      "expected_outputs": ["updated summary", "updated detail", "cross-link intact"],
      "verify_command": "<command-or-null>",
      "manual_verify_contract": ["summary references detail", "P0-P3 present"],
      "stop_condition": "verify passes or explicit documented stop reason",
      "pause_condition": "approval/network/missing-context required",
      "failure_condition": "wrong files changed, no verify, or no stop reason",
      "required_evidence_surface": [
        "runtime_payload",
        "workspace_index_summary",
        "operator_summary",
        "failure_pause_recovery_reason"
      ],
      "native_runner_entry": "<native command or artifact entry>",
      "opencode_runner_entry": "<opencode adapter command>",
      "comparison_notes": "same prompt and same verify/stop standard"
    }
  ]
}
```

## OpenCode Run Record Shape

OpenCode adapter 至少应输出以下 run record。字段不可得时，必须填 `unavailable` 和原因。

```json
{
  "run_record_version": "opencode_external_runner_record.v1",
  "runner": "opencode",
  "case_id": "docs_update_001",
  "task_family": "docs_update",
  "status": "pass|pause|fail|stop",
  "runtime_payload": {
    "command": "unavailable|...",
    "model": "unavailable|...",
    "provider": "unavailable|...",
    "started_at": "unavailable|...",
    "ended_at": "unavailable|...",
    "duration_ms": "unavailable|...",
    "exit_status": "unavailable|..."
  },
  "workspace_index_summary": {
    "changed_files": [],
    "created_artifacts": [],
    "verify_commands": [],
    "diff_summary": "unavailable|..."
  },
  "operator_summary": {
    "outcome": "...",
    "verification": "...",
    "next_action": "...",
    "readability_notes": "..."
  },
  "failure_pause_recovery_reason": {
    "failure_reason": "none|...",
    "pause_reason": "none|...",
    "recovery_reason": "none|...",
    "stop_reason": "none|...",
    "unavailable_fields": []
  }
}
```

## Comparative Report Shape

Comparative report 应至少包含：

```json
{
  "report_version": "native_vs_opencode_comparative_evidence.v1",
  "case_pack_version": "external_opencode_same_contract.v1",
  "summary_verdict": "...",
  "case_results": [
    {
      "case_id": "docs_update_001",
      "task_family": "docs_update",
      "native_status": "pass|pause|fail|stop",
      "opencode_status": "pass|pause|fail|stop",
      "recovery_quality_delta": "native_better|opencode_better|equivalent|inconclusive",
      "evidence_completeness_delta": "native_better|opencode_better|equivalent|inconclusive",
      "operator_readability_delta": "native_better|opencode_better|equivalent|inconclusive",
      "cost_latency_availability_delta": "native_better|opencode_better|equivalent|inconclusive",
      "gap_classification": ["agent_capability_gap|product_thickness_gap|ecosystem_gap|instrumentation_gap"],
      "evidence_pointers": []
    }
  ],
  "operator_decision": {
    "recommended_path": "continue_opencode_ecosystem_chase|native_productization_next|instrumentation_first|mixed_strategy",
    "reason": "...",
    "next_moves": [],
    "non_moves": []
  }
}
```

## Global Stopping Criteria

只有以下条件全部满足，goal 才能停止：

1. `P0`、`P1`、`P2`、`P3` 四部分都已完成。
2. 5 类 daily-driver repo task family 都有 same-contract case。
3. 每个 case 都固定 input、expected output、verify / stop 标准。
4. native 与 OpenCode 都能产出同 schema 或可映射 schema 的 run record。
5. OpenCode runner adapter 至少输出 runtime payload、workspace index summary、operator summary、failure / pause / recovery reason；不可得字段显式标记。
6. comparative report 对每个 case 给出 pass / pause / fail 或 stop 结果。
7. comparative report 明确区分 agent capability gap、product thickness gap、ecosystem gap、instrumentation gap。
8. P3 给出 operator decision 和 next moves / non-moves。
9. 不再把本 goal 扩大为完整 TUI、完整 provider、完整 OpenCode 产品集成、安装发布或社区生态建设。

## Phase Acceptance Criteria

### P0 Acceptance

`P0` 只有在以下条件全部满足时才算完成：

1. 5 类 daily-driver task family 均被纳入 case pack。
2. 每类至少 1 个 same-contract case。
3. 每个 case 都有固定 input prompt。
4. 每个 case 都有 expected outputs。
5. 每个 case 都有 verify command 或 manual verify contract。
6. 每个 case 都有 stop / pause / failure condition。
7. 每个 case 都声明 required evidence surface。
8. case pack 可被 native 与 OpenCode runner 引用。

### P1 Acceptance

`P1` 只有在以下条件全部满足时才算完成：

1. 存在最小 OpenCode runner adapter。
2. adapter 能读取 P0 case pack。
3. adapter 能启动或记录 OpenCode 对 case 的执行。
4. adapter 输出 run record。
5. run record 包含 runtime payload。
6. run record 包含 workspace index summary。
7. run record 包含 CLI / operator summary 等价摘要。
8. run record 包含 failure / pause / recovery reason。
9. 不可得字段被显式标记为 unavailable。

### P2 Acceptance

`P2` 只有在以下条件全部满足时才算完成：

1. comparative evidence report 使用 P0 case pack 与 P1 run records。
2. 每个 case 都有 native vs OpenCode status 对照。
3. 每个 case 都有 recovery quality 对照。
4. 每个 case 都有 evidence completeness 对照。
5. 每个 case 都有 operator readability 对照。
6. cost / latency 可得性被记录；不可得时显式标记。
7. 差距被分类为 agent capability、product thickness、ecosystem 或 instrumentation。
8. report 能被 operator 直接阅读，而不是只能读 raw transcript。

### P3 Acceptance

`P3` 只有在以下条件全部满足时才算完成：

1. 给出 recommended path。
2. recommended path 只能是 continue_opencode_ecosystem_chase、native_productization_next、instrumentation_first 或 mixed_strategy 之一。
3. 决策理由引用 P2 evidence。
4. 给出 next 1-3 concrete moves。
5. 给出 explicit non-moves。
6. 明确说明差距到底主要是 agent 能力、产品厚度、生态规模还是 instrumentation 不等价。

## Anti-Local-Optimum Guardrail

以下情况一旦成立，就应停止当前 goal，而不是继续局部优化：

1. case pack 已覆盖 5 类任务族，但后续只是增加更多 case 数量。
2. OpenCode adapter 已能输出可比 run record，但后续只是追求完整产品集成。
3. comparative report 已能做 operator decision，但后续只是润色报告表现。
4. 证据已经说明差距主要来自 TUI / provider / plugin / install / release，却继续在本 goal 内做产品化。
5. 证据已经说明差距主要来自 agent capability，却继续用 operator summary 包装回避。
6. 证据主要受 instrumentation 不等价影响，却继续做主观能力判断。

如果剩余工作大多属于下面这些，应进入下一个 goal，而不是继续本 goal：

- native TUI / Desktop / Web productization；
- provider abstraction 或 model marketplace；
- install / release / packaging；
- plugin ecosystem；
- full OpenCode integration；
- broader external benchmark platform；
- community / docs site / distribution。

## File-Level Verification Targets

以下不是唯一文件名要求，但 goal 完成时必须能在当前仓库中找到等价实现证据。

### P0 File-Level Evidence

应能看到：

- same-contract case pack；
- 5 类 task family；
- fixed prompt / expected output / verify or stop；
- native / OpenCode runner entry；
- required evidence surface。

推荐落地区域：

- `docs/process/evidence-cases.json`
- `docs/process/goal-mode-external-opencode-harness.md`
- `tests/`
- `src/agent_orchestrator/`

### P1 File-Level Evidence

应能看到：

- OpenCode runner adapter；
- OpenCode run record schema；
- unavailable field handling；
- runtime payload / workspace index summary / operator summary / failure reason 输出。

### P2 File-Level Evidence

应能看到：

- native vs OpenCode comparison report；
- pass / pause / fail table；
- recovery quality delta；
- evidence completeness delta；
- operator readability delta；
- cost / latency availability；
- gap classification。

### P3 File-Level Evidence

应能看到：

- operator decision；
- recommended path；
- evidence pointers；
- next moves；
- non-moves。

## Non-Goals

本 goal 明确不包含：

- 完整追平 OpenCode TUI；
- 构建完整 provider / plugin ecosystem；
- 做 native 安装发布；
- 做完整 OpenCode 产品集成；
- 做大规模 benchmark 平台；
- 重新证明 native daily-driver repeatability；
- 为了更多字段而扩展 evidence schema；
- 把 OpenCode 的生态优势误写成 agent 能力优势；
- 把 native 的产品厚度缺口误写成 agent 能力不足。

## Final Operator Question

本 goal 完成时，只需要回答一个问题：

> 在同一任务合同与 evidence surface 下，native 与 OpenCode 的剩余差距主要是什么；下一步应该追 OpenCode 生态，还是推进 native productization？
