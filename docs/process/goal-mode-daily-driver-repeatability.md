# Daily Driver Repo Task Repeatability Goal

## Goal Intent

本 goal 的目的，是把当前已经打通的 native coding-agent 平台能力，从“单类真实任务可验收”推进到“多类 repo 任务可重复稳定跑通”，而不是继续加字段、做更厚的产品皮肤或扩大无关生态。

这里的“日常可用”不是泛泛地指能跑几个 demo，而是指它能在同一个受治理语义下，重复完成下面这条链路：

- 接收真实 repo 任务；
- 选择合适上下文；
- 进入多类任务族基线；
- 执行并产出 runtime payload / workspace index / CLI summary；
- 处理 failure、clarify、approval pause、resume；
- 通过 verify 或明确 stop 收口；
- 把同一条事实链投影到 operator 可见面；
- 让后续对比 OpenCode 时，主要差距落在产品厚度和生态。

本 goal 必须防止陷入“指标漂亮、文档完整、但真实 repo 任务不能稳定重复”的局部最优。

## Target Outcome

完成后，当前项目应从：

- 单类真实任务可验收；
- 任务闭环可通，但重复性不足；
- failure / clarify / approval pause 的路径还不够系统；
- 与 OpenCode 的差距仍容易被描述成基础 agent 能力不足；

推进到：

- 多类真实 repo 任务可以重复跑通；
- repeatability harness 能稳定输出同合同产物；
- 失败、暂停、恢复、澄清都有语义化记录；
- 与 OpenCode 的差距主要是 TUI、插件生态、provider、安装发行和外部 benchmark。

## Current Operator Readout

- `P0`: complete. The catalog covers 5 task families with real repo cases and a readable case matrix.
- `P1`: complete. The harness records runtime_payload / workspace_index / CLI_summary contract outputs plus pass / pause / fail / recovery reasons.
- `P2`: complete. `agent_orchestrator.daily_driver_runner_artifact.v1` connects the case matrix and harness into a reusable runner artifact with runner status, family count, per-family steps, contract outputs, and next external step.
- `P3`: complete. The operator gap report says the remaining gap is external OpenCode harness plus TUI / plugin / provider / installation / release thickness.
- status: daily-driver repo-task repeatability is internally proven for this goal; comparison-grade OpenCode evidence belongs to the next external harness goal.

## Scope Boundary

本 goal 只包含以下四个实现部分，且都必须完成。

### P0 Multi-Task Baseline

选 3~5 类真实 repo 任务，形成可重复的基线集合。

建议任务族：

- 文档更新任务；
- 单文件代码修复；
- 多文件 operator surface / CLI 投影修复；
- 测试驱动的小功能补齐；
- failure / clarify / approval pause 路径任务。

必须完成：

- 每类至少 1 个真实 repo case；
- 每个 case 有输入、执行、验证和 evidence；
- 不能只用 mock case；
- 任务结果能稳定复现；
- 至少一类 case 可以明确 stop 或明确 verify 成功。
- 同时产出 case matrix，明确每类任务的输入、执行、验证和 evidence 标记。

### P1 Repeatability Harness

建立内部 repeatability harness，让同类任务可以重复跑。

必须完成：

- 同一类任务可重复跑；
- 每次输出 runtime payload；
- 每次输出 workspace index；
- 每次输出 CLI summary；
- 记录通过、暂停、失败、恢复原因；
- 记录 contract 要能为后续对比 OpenCode 复用。

### P2 Daily Driver Acceptance

定义 daily-driver-ready 的验收标准，并确保可检查。

必须完成：

- 至少 3 类任务通过；
- 每类至少 1 个真实 repo case；
- 每个 case 都有 verify 或明确 stop；
- 失败必须带下一步语义；
- approval pause / clarify / resume / stop 至少一种边界语义真实出现；
- 验收不是单次演示，而是可回归的条件集合。

### P3 Gap Report vs OpenCode

产出 operator 可读的差距报告。

必须完成：

- 已经不差的部分：
  - native tool surface；
  - planner；
  - evidence；
  - adapter fact；
- 仍然差的部分：
  - TUI；
  - 插件生态；
  - provider；
  - 安装发行；
  - 外部 benchmark；
- 给出是否应该做外部 opencode harness 的下一步判断。

### Operator Gap Report

- already strong:
  - native tool surface / planner / evidence / adapter fact
  - repeatability case matrix
  - shared runtime payload / workspace index / CLI summary contract
  - canonical daily-driver runner artifact (`agent_orchestrator.daily_driver_runner_artifact.v1`) tying matrix + harness into replayable operator evidence
- still missing outside this goal:
  - external OpenCode harness
  - TUI / plugin ecosystem / provider / installation / release thickness
- next best move:
  - build the external same-contract OpenCode harness only if comparison-grade evidence is required

## Global Stopping Criteria

只有以下条件全部满足，goal 才能停止：

1. `P0`、`P1`、`P2`、`P3` 四部分都已完成。
2. 至少 3 类真实 repo 任务可以重复跑通。
3. 每类至少 1 个真实 repo case。
4. 每个 case 都有 verify 或明确 stop。
5. failure、clarify、approval pause、resume、stop 至少一种边界语义有真实证据。
6. runtime payload、workspace index、CLI summary、artifact、docs 至少两个面能看到同一事实链。
7. 相关文档、代码和测试可以互相对照，说明这不是一次性演示。
8. 不得继续把目标扩展为：
   - 全面追平 OpenCode 的 TUI / Desktop / Web / plugin / release / community 能力；
   - 大规模重构整个仓库结构；
   - 为了更漂亮的抽象继续拆分执行层；
   - 做与 repeatability / daily-driver 核心无关的产品化扩张。

## Phase Acceptance Criteria

### P0 Acceptance

`P0` 只有在以下条件全部满足时才算完成：

1. 至少 3 类真实 repo 任务被定义。
2. 每类至少 1 个真实 case。
3. 每个 case 都有输入、执行、验证和 evidence。
4. 至少一个 case 能明确 verify 或明确 stop。
5. 存在测试、CLI 命令或等价直接验证。

### P1 Acceptance

`P1` 只有在以下条件全部满足时才算完成：

1. harness 可重复跑同类任务。
2. 每次运行都能输出 runtime payload。
3. 每次运行都能输出 workspace index。
4. 每次运行都能输出 CLI summary。
5. 通过、暂停、失败、恢复原因可被记录。
6. 存在测试、CLI 命令或等价直接验证。

### P2 Acceptance

`P2` 只有在以下条件全部满足时才算完成：

1. 至少 3 类任务通过。
2. 每类至少 1 个真实 repo case。
3. 每个 case 都有 verify 或明确 stop。
4. 失败必须有下一步语义。
5. 至少一种边界语义真实出现：failure、clarify、approval pause、resume、stop。
6. 存在测试、CLI 命令或等价直接验证。

### P3 Acceptance

`P3` 只有在以下条件全部满足时才算完成：

1. gap report 清楚列出已经不差的部分。
2. gap report 清楚列出仍然差的部分。
3. operator 能据此判断下一步是否该做外部 opencode harness。
4. runtime payload / workspace index / CLI summary / docs 至少两个面能对照同一事实链。
5. 存在测试、CLI 命令或等价直接验证。

## Anti-Local-Optimum Guardrail

以下情况一旦成立，就应停止当前 goal，而不是继续局部优化：

1. 多任务族已经能稳定跑通，但后续工作主要变成增加更多字段名或漂亮摘要。
2. harness 已经能重复跑，但继续优化只是让报表更厚。
3. daily-driver-ready 已经成立，但后续工作主要变成追平 OpenCode 的 UI / 插件 / 生态细节。
4. 当前能力已经足够支撑日常真实 repo 任务，剩余差距主要是产品厚度和生态规模。
5. 新增工作无法直接映射到 `P0`、`P1`、`P2`、`P3` 中至少一项验收标准。

如果剩余工作大多属于下面这些，应进入下一个 goal，而不是继续本 goal：

- 更厚的 TUI / Desktop / Web；
- 更大的插件或 provider 生态；
- 安装、发布、官网、社区；
- 外部 benchmark 体系；
- 更深的泛化或长期性能优化。

## File-Level Verification Targets

以下不是唯一文件名要求，但 goal 完成时必须能在当前仓库中找到等价实现证据。

### P0 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `docs/process/evidence-cases.json`
- `tests/`
- `src/agent_orchestrator/execution/`
- 必要文档

文件层验收标准：

- 多任务族真实存在；
- 每个 case 有输入、执行、验证和 evidence；
- 不是 mock-only；
- 可重复验证。
- case matrix 可读。

### P1 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/cli_presenters.py`
- `src/agent_orchestrator/control_plane_workspace.py`
- `src/agent_orchestrator/execution/runtime.py`
- `tests/`
- 必要文档

文件层验收标准：

- runtime payload / workspace index / CLI summary 有一致合同；
- 同类任务可重复跑；
- 失败、暂停、恢复原因可见。

### P2 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/control_plane_recovery.py`
- `src/agent_orchestrator/control_plane_runtime.py`
- `src/agent_orchestrator/control_plane_approvals.py`
- `tests/`
- 必要文档

文件层验收标准：

- failure / clarify / approval pause / resume / stop 至少一种边界语义真实出现；
- 下一步语义可读；
- 不是一次性演示。

### P3 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `docs/process/`
- `src/agent_orchestrator/cli_presenters.py`
- `src/agent_orchestrator/ui_service.py`
- `src/agent_orchestrator/control_plane_workspace.py`
- `tests/`
- 必要文档

文件层验收标准：

- gap report 明确；
- operator 可读；
- 至少两个 surface 能对照同一事实链；
- 下一步判断可执行。

## Required Verification Evidence

goal 完成前，必须至少具备以下一种或多种直接证据组合：

- 自动化测试；
- 集成测试；
- CLI 级运行验证；
- runtime / workspace / recovery 状态直接检查；
- artifact / evidence 输出证明；
- 文档与实现/测试之间的交叉引用。

不能只用以下弱证据宣布完成：

- “看起来已经能跑”；
- 只有 helper 存在但主链路没接入；
- 只写文档没落代码；
- 只提升抽象层次但没有真实任务闭环；
- 只修局部失败而没有形成可重复的终点；
- 单个 mock 测试通过但没有证明主路径；
- 把未验证的后续工作写成已经完成。

## Explicit Non-Goals

以下内容不是本 goal 的完成要求，禁止无限扩展进去：

1. 全面追平 OpenCode 的 TUI / Desktop / Web。
2. 大规模插件生态或 marketplace 建设。
3. 全量 provider 集成和发行体系重做。
4. 与 daily-driver repeatability 无关的架构重构。
