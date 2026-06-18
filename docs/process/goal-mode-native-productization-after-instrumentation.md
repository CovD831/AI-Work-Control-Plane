# Native Productization After Instrumentation Closure Goal

## Goal Intent

本 goal 的目的，是在 authoritative OpenCode comparison harness 已经建立之后，把注意力从“继续证明能对比”转向“native 平台 productization”。

前一阶段已经完成：

- same-contract 5-family case pack；
- minimal OpenCode runner adapter；
- authoritative normalized record；
- authoritative comparative report；
- smoke runner 与 authoritative runner 的区分；
- instrumentation gap 可以被关闭或坐实。

因此，本 goal 不再继续扩展 OpenCode harness schema，也不再增加更多 benchmark case。它要回答的是：

> 如果 native 在同合同能力上已经足以进入日常使用，operator 还缺什么产品入口、运行诊断、安装路径和 evidence consumption，才能真的把它当 daily-driver 使用？

本 goal 的核心是让 native 平台被 operator 稳定启动、观察、恢复、判断和复现。

## Target Outcome

完成后，当前项目应从：

- native 能力和 evidence 已经存在，但入口分散；
- authoritative comparison 结论主要存在于 JSON 和测试里；
- operator 需要知道很多内部命令才能判断状态；
- provider / runtime setup 可用性不够一屏可读；
- install / start / smoke test 路径还不够像 release candidate；

推进到：

- operator 有一个稳定入口查看当前 native product posture；
- 能从 CLI 或最小 TUI 启动 daily-driver / smoke task；
- 能查看 run status、evidence summary、provider diagnosis、next action；
- 能消费 authoritative OpenCode comparison 结论；
- 能按 install / release checklist 复现本地启动与 smoke test；
- 下一步 product decision 明确落到 TUI 深化、provider 扩展、install release 或 agent capability repair。

## Scope Boundary

本 goal 包含五个部分，且都必须完成。

### P0 Operator Product Surface

建立 operator 可读的 product surface。

必须完成：

- 一个稳定入口显示 native product posture；
- 至少包含：
  - active / latest goal posture；
  - run status；
  - provider / runtime posture；
  - evidence summary；
  - authoritative comparison summary；
  - next action；
  - blocker / recovery reason；
- 输出不要求漂亮，但必须 operator-readable；
- 不要求完整 TUI，只要求能被日常使用。

### P1 Daily-Driver CLI / TUI Entry

建立最小 daily-driver 入口。

必须完成：

- 能启动一个 smoke task 或 daily-driver task；
- 能查看任务状态；
- 能查看 evidence summary；
- 能继续、停止或明确下一步；
- 至少通过 CLI 完成；如有 TUI，只做 read-only 或 minimal action surface；
- 不要求完整 Desktop / Web 产品。

### P2 Provider / Runtime Setup Diagnosis

建立 provider / runtime setup 诊断。

必须完成：

- 检查 local mock；
- 检查 Codex / OpenAI / Claude 或当前项目支持的 runtime；
- 输出 auth / config / command availability / degraded mode；
- 输出 operator-readable fix hints；
- 不泄漏 secret；
- setup diagnosis 能被 P0 surface 消费。

### P3 Install / Release Readiness

建立最小 install / release readiness。

必须完成：

- 本地安装说明；
- 启动命令；
- smoke test 命令；
- expected output；
- known limitations；
- release checklist；
- rollback / cleanup hints；
- 不要求真实发布到 package registry。

### P4 Evidence Consumption

把 evidence 从 raw JSON 转成 operator 可消费的报告。

必须完成：

- daily-driver repeatability summary 可读；
- authoritative OpenCode comparison summary 可读；
- instrumentation closure 状态可读；
- native productization next step 可读；
- operator 不需要读 raw JSON 就能知道：
  - 当前 native 是否可日用；
  - OpenCode 差距是什么；
  - 下一步该做什么。

## Global Stopping Criteria

只有以下条件全部满足，goal 才能停止：

1. `P0` 到 `P4` 全部完成。
2. operator 能通过一个稳定入口看到 native product posture。
3. 至少一个 smoke / daily-driver task 可运行或明确停止。
4. provider / runtime setup diagnosis 可执行并输出修复建议。
5. install / start / smoke test 文档可复现。
6. authoritative OpenCode comparison 结论能以 operator-readable summary 消费。
7. evidence summary、runtime status、provider posture、next action 至少两个 surface 能对照同一事实链。
8. 明确给出下一步 product decision。
9. 不扩大为完整 Desktop / Web / plugin ecosystem / provider marketplace / public release。

## Phase Acceptance Criteria

### P0 Acceptance

`P0` 只有在以下条件全部满足时才算完成：

1. 存在 product posture 输出入口。
2. 输出包含 run status、provider posture、evidence summary、next action。
3. 输出能引用 authoritative comparison conclusion。
4. blocker / recovery reason 可见。
5. 存在测试、CLI 命令或等价直接验证。

### P1 Acceptance

`P1` 只有在以下条件全部满足时才算完成：

1. 能启动 smoke / daily-driver task。
2. 能查看 status。
3. 能查看 evidence summary。
4. 能继续 / 停止 / 给出 next action 中至少一种。
5. 存在测试、CLI 命令或等价直接验证。

### P2 Acceptance

`P2` 只有在以下条件全部满足时才算完成：

1. provider / runtime setup diagnosis 可执行。
2. local mock 状态可见。
3. 至少一个外部 runtime 的可用性或不可用原因可见。
4. secret 不泄漏。
5. degraded mode / fix hint 可见。
6. 存在测试、CLI 命令或等价直接验证。

### P3 Acceptance

`P3` 只有在以下条件全部满足时才算完成：

1. install instructions 存在。
2. start command 存在。
3. smoke test command 存在。
4. expected output 存在。
5. release checklist 存在。
6. known limitations 存在。
7. 存在文档测试或等价验证。

### P4 Acceptance

`P4` 只有在以下条件全部满足时才算完成：

1. daily-driver repeatability 结论可读。
2. authoritative OpenCode comparison 结论可读。
3. instrumentation closure 状态可读。
4. native productization next step 可读。
5. operator 不需要 raw JSON 即可判断 next move。
6. 存在测试、CLI 命令或等价直接验证。

## Anti-Local-Optimum Guardrail

以下情况一旦成立，就应停止当前 goal，而不是继续局部优化：

1. operator 已能启动、观察、诊断、消费 evidence，但继续只是让 UI 更漂亮。
2. install / smoke test 已可复现，但继续只是包装更多发行渠道。
3. provider diagnosis 已能说明可用性和修复建议，但继续变成 provider marketplace。
4. authoritative comparison 已能被消费，但继续扩 benchmark case。
5. native product decision 已明确，但继续在本 goal 内做下一阶段产品开发。

如果剩余工作主要属于下面这些，应进入后续 goal：

- 完整 TUI / Desktop / Web；
- provider marketplace；
- plugin ecosystem；
- public package release；
- community docs site；
- 更多外部 benchmark；
- 深度 agent capability repair。

## File-Level Verification Targets

以下不是唯一文件名要求，但 goal 完成时必须能找到等价实现证据。

### P0 File-Level Evidence

推荐区域：

- `src/agent_orchestrator/cli.py`
- `src/agent_orchestrator/cli_presenters.py`
- `src/agent_orchestrator/productization_surface.py`
- `tests/test_cli.py`
- `tests/test_cli_presenters.py`

验收标准：product posture 能被 operator 读取。

### P1 File-Level Evidence

推荐区域：

- `src/agent_orchestrator/cli.py`
- `src/agent_orchestrator/execution/`
- `src/agent_orchestrator/ui_service.py`
- `tests/test_coding_agent_runtime.py`
- `tests/test_ui_service.py`

验收标准：smoke / daily-driver task 能启动并查看状态。

### P2 File-Level Evidence

推荐区域：

- `src/agent_orchestrator/command.py`
- `src/agent_orchestrator/agent_config.py`
- `src/agent_orchestrator/cli.py`
- `tests/test_cli.py`

验收标准：provider / runtime setup diagnosis 可执行且不泄漏 secret。

### P3 File-Level Evidence

推荐区域：

- `README.md`
- `docs/process/goal-mode-native-productization-after-instrumentation.md`
- `docs/process/project-index.md`
- `docs/process/context-map.md`
- `tests/test_docs_process.py`

验收标准：install / start / smoke test / release checklist 可读可复现。

### P4 File-Level Evidence

推荐区域：

- `src/agent_orchestrator/opencode_harness.py`
- `src/agent_orchestrator/evidence.py`
- `src/agent_orchestrator/cli_evidence.py`
- `docs/process/external-opencode-same-contract-cases.json`
- `tests/test_evidence.py`

验收标准：daily-driver 与 authoritative comparison 结论能被 operator-readable report 消费。

## Non-Goals

本 goal 明确不包含：

- 完整 OpenCode clone；
- 完整 Desktop / Web；
- 插件生态；
- provider marketplace；
- 公共 registry 发布；
- 大规模 benchmark 平台；
- 重新证明 native daily-driver repeatability；
- 继续扩 authoritative harness schema；
- 在没有 product posture 的情况下继续堆更多内部 evidence。

## Final Operator Question

本 goal 完成时，只需要回答：

> native daily-driver 现在是否能被 operator 稳定启动、观察、诊断、恢复和消费 evidence；下一步应该深化 TUI、扩 provider、做 install release，还是回头补 agent capability？

## Current Implementation Note

Native productization now has a stable CLI entrypoint and release-readiness note:

- `agent-orchestrator product posture` shows the operator-facing product posture, latest run status, provider/runtime posture, evidence summary, authoritative OpenCode comparison summary, blocker/recovery reason, and next action.
- `agent-orchestrator product diagnose` shows setup diagnosis for mock and configured external runtimes with redaction-safe fix hints.
- `agent-orchestrator product smoke` runs a minimal native daily-driver smoke and emits an operator summary with outcome, verify/stop, next action, and readability.
- `agent-orchestrator product evidence` turns daily-driver repeatability and authoritative OpenCode comparison into an operator-readable evidence consumption summary.
- Install/start/smoke/release readiness is documented in `docs/process/native-productization-after-instrumentation-install-release.md`.

The product decision after instrumentation closure is `instrumentation_closed_native_productization_next`: keep the native daily-driver path, advance operator UX / TUI / provider / install-release work next, and do not keep expanding the OpenCode harness schema in this goal.
