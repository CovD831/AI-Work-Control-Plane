# Native Coding Agent Implementation Goal

## Goal Intent

本目标不是继续做差距分析，而是把当前仓库中的 native coding agent 从“已有执行雏形的治理内核”推进到“真实可工作的 first-party coding agent”，并继续保留 external coding agent 的热插拔支持。

目标范围严格限定为三个实现部分：

1. `P0 原生工具面实现`
2. `P1 原生 planner 实现`
3. `P2 原生/外部 agent 统一适配层实现`

本 goal 的完成标准不是“写出方案”或“补一些原型代码”，而是这三个部分都在当前工作树里以真实代码、集成路径、必要文档和直接验证结果落地。

## Target Outcome

完成后，项目与 `research_repos/opencode/` 的差距应从：

- “治理能力强，但 native coding agent 明显早期”

缩小到：

- “在 coding agent 核心闭环上已进入同一代际，但在工具丰富度、生态规模、交互产品厚度上仍落后于 `opencode`”

这意味着实现完成后，当前仓库必须至少具备以下能力闭环：

- 真实 repo understanding
- 真实 planner decision making
- 真实 edit / patch / verify execution
- approval pause 与 recovery continuation
- native agent 与 external agent 的统一治理契约

## Scope Boundary

只做以下三部分，且必须都完成：

### P0 原生工具面实现

至少实现并接入以下五类原生工具能力：

- `read`
- `search`
- `glob`
- `structured_patch`
- `verify`

这些能力必须：

- 被 native runtime 主路径真实使用
- 具备治理边界
- 支持 approval hook
- 产生 artifact / evidence
- 与 control plane 的状态、恢复、审计语义兼容

### P1 原生 Planner 实现

将主 native path 上的 planning 决策升级为真正的 native planner，使其能决定至少这些行为：

- `explore`
- `clarify`
- `edit`
- `verify`
- `approval pause`
- `handoff external agent`

planner 必须进入现有的：

- state
- recovery
- runtime metadata
- evidence

体系，而不是只在局部辅助逻辑里存在。

### P2 原生/外部 Agent 统一适配层实现

实现共享 adapter contract，让：

- first-party native coding agent
- external hot-pluggable coding agents

在同一治理语义下接入，包括：

- execution contract
- runtime metadata
- approval semantics
- evidence outputs
- recovery surfaces

要求是“代码中的统一契约”，不是纯文档约定。

## Global Stopping Criteria

只有以下条件全部满足，goal 才能停止：

1. `P0`、`P1`、`P2` 三部分都已完成。
2. 每一部分都已有当前工作树中的直接证据证明已接入主链路。
3. 每一部分都已有测试或等价验证，证明不是“代码存在但未被使用”。
4. 相关文档已更新，足以说明 native coding agent 如何在 control plane 下工作。
5. 最终总结只包含三段：
   - `P0`
   - `P1`
   - `P2`
6. 不再继续扩展到与这三部分无关的大规模重构、体验优化、生态扩张或无限细化。

若以上任一项未满足，则 goal 不能视为完成。

## Phase Acceptance Criteria

### P0 Acceptance

`P0` 只有在以下条件全部满足时才算完成：

1. 五类工具能力 `read/search/glob/structured_patch/verify` 都存在于代码中。
2. 这些能力都不是孤立 helper，而是 native runtime 主路径可调用能力。
3. 至少一个真实 native execution path 会根据任务实际使用这些工具中的多个能力。
4. 工具调用带有治理边界或审批语义，不是裸执行。
5. 工具调用能产出 artifact、evidence、或等价运行记录。
6. 存在测试或等价直接验证，覆盖这些能力的集成使用，而不只是单函数存在性。

### P1 Acceptance

`P1` 只有在以下条件全部满足时才算完成：

1. native path 的 planner 不再主要充当 compatibility bridge。
2. planner 能根据任务与上下文做出真实策略分流，而不是固定落到旧分解流程。
3. planner 决策至少覆盖：
   - `explore`
   - `clarify`
   - `edit`
   - `verify`
   - `approval pause`
   - `handoff external agent`
4. planner 决策会进入 runtime metadata、state、recovery 或 evidence 之一以上的正式链路。
5. 存在测试或等价直接验证，证明 planner 决策影响了真实执行路径。

### P2 Acceptance

`P2` 只有在以下条件全部满足时才算完成：

1. native agent 与 external agent 在代码中共享一个真实 adapter contract。
2. 共享的不是空接口，而是至少包含 execution、metadata、approval、evidence、recovery 中的大部分正式语义。
3. native agent 和 external agent 两条路径都能落到这个统一契约上。
4. 存在测试或等价直接验证，证明两类 agent 在统一治理语义下工作，而不是仅名称对齐。

## File-Level Verification Targets

下面这些不是强制唯一文件名，但 goal 完成时必须能在当前仓库中找到与之等价的实现证据。

### P0 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/execution/`
- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `src/agent_orchestrator/execution/coding_components.py`
- 相关 tests 文件
- 必要文档文件

文件层验收标准：

- runtime 主路径调用关系清晰
- 工具不是只定义不使用
- tests 覆盖主路径而不是只测 helper

### P1 File-Level Evidence

应能在以下区域看到真实实现或替换：

- `src/agent_orchestrator/strategy/`
- `src/agent_orchestrator/intake/`
- `src/agent_orchestrator/execution/`
- 相关 tests 文件
- 必要文档文件

文件层验收标准：

- planner 的原生决策逻辑是主路径的一部分
- compatibility-only 逻辑不再主导 native path
- tests 能证明不同任务会触发不同策略行为

### P2 File-Level Evidence

应能在以下区域看到真实实现或等价落点：

- `src/agent_orchestrator/adapters.py`
- `src/agent_orchestrator/execution/`
- `src/agent_orchestrator/orchestrator.py`
- 相关 tests 文件
- 必要文档文件

文件层验收标准：

- unified adapter contract 在代码中可识别
- native / external 两类路径都接入这个契约
- governance / approval / evidence / recovery 语义至少部分共享且被验证

## Required Verification Evidence

goal 完成前，必须至少具备以下一种或多种直接证据组合：

- 自动化测试
- 集成测试
- CLI 级运行验证
- artifact / evidence 输出证明
- runtime metadata / recovery state 的直接检查

不能只用以下弱证据宣布完成：

- 代码看起来合理
- 文件数量增加
- 新增接口但没有主路径接入
- 只写文档没有实现
- 只写实现没有验证

## Explicit Non-Goals

以下内容不是本 goal 的完成要求，禁止无限扩展进去：

- 全面追平 `opencode` 的所有工具、UI、插件生态和产品表面
- 做完整的通用平台化重构
- 做与 `P0/P1/P2` 无关的大规模目录迁移
- 进行无限的体验打磨或命名优化
- 在已有核心闭环成立后继续做无边界局部最优迭代

## Anti-Local-Optimum Guardrail

为防止 goal 掉入无限局部优化，一旦满足以下条件，就应停止而不是继续打磨：

1. `P0/P1/P2` 都已满足各自验收标准。
2. 所有必需验证证据都已存在。
3. 与 `opencode` 的差距已收敛到“核心闭环同代际，产品厚度仍落后”的程度。
4. 后续剩余工作主要变成：
   - 更多工具扩展
   - 更多 UI/UX 打磨
   - 更多生态接入
   - 更多非阻塞型重构

如果已经进入上述状态，则这些工作应属于下一个 goal，而不是继续拉长当前 goal。

## Goal-Mode Short Form

建议短文本指向本文件：

实现当前仓库的 first-party native coding agent，使其在保留 external coding agent 热插拔支持的前提下，完成 `P0 原生工具面`、`P1 原生 planner`、`P2 原生/外部 agent 统一适配层` 三部分的真实落地。必须以代码、主链路接入、文档和直接验证结果完成，不接受停留在分析、方案、原型或局部重构。完成标准、终止条件、分阶段验收标准、文件级验证目标和防止无限局部最优迭代的约束，详见 `docs/process/goal-mode-native-agent-implementation.md`。
