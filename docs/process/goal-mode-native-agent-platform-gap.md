# Native Agent Platform Gap Goal

## Goal Intent

本 goal 的目的，是把当前项目从“已经有受治理 native coding-agent execution kernel”推进到“更接近成熟通用 coding-agent 平台的核心能力层”，而不是只增加更多文档、字段或局部 helper。

这里的“更接近 `opencode`”不是指复制 `research_repos/opencode/` 的完整产品形态，而是指补齐当前最关键的基础差距：

- native tool surface 更像真实 coding agent；
- repository understanding 不再主要依赖浅层文件列表；
- planner 能原生决定探索、澄清、编辑、验证、暂停和移交；
- native agent 与 external agent 能共享 control-plane 治理事实；
- operator 能看到同一条可追踪事实链。

本 goal 必须防止陷入“追平 OpenCode 的所有产品面”或“持续美化抽象但主链路不变强”的局部最优。

## Target Outcome

完成后，当前项目应从：

- native execution 已经可用，但工具面仍偏窄；
- repository understanding 和目标文件发现仍偏浅；
- planner 仍带 compatibility bridge 色彩；
- native agent 与 external agent 的统一 adapter contract 尚未足够硬化；
- 与 `opencode` 的差距仍容易被描述成“通用 coding-agent 平台能力不足”；

推进到：

- native agent 能用更完整的 read/search/glob/patch/diff/verify 工具链处理真实代码任务；
- 上下文选择和代码关系探索能作为主链路事实被记录和验证；
- planner 能明确给出 explore / clarify / edit / verify / pause / handoff 决策；
- native 和 external agent 能通过同一 control-plane contract 投影治理、审批、证据和恢复事实；
- 与 `opencode` 的剩余差距主要体现在产品厚度、插件生态、UI 丰富度、安装发行和社区规模。

剩余差距应主要体现在：

1. TUI / Desktop / Web / docs site / installation / release / marketplace 等产品厚度；
2. 插件生态、subagent 生态、社区规模和广泛 provider 集成；
3. 更广泛任务类型覆盖和长期性能优化。

而不应主要卡在：

1. native agent 只能做窄 helper 级修改；
2. repository understanding 不能支撑真实代码任务；
3. planner 不能决定下一步 agent 行为；
4. native/external agent 没有统一治理事实链；
5. 相关文档、代码和测试无法互相对照。

## Scope Boundary

本 goal 只包含以下四个实现部分，且都必须完成。

### P0 Native Tool Surface

扩展 native agent 的核心工具面，让它能处理更真实的代码修改任务。

必须完成：

- read/search/glob 至少形成一条可组合的探索链路；
- patch/diff 或等价结构化编辑结果进入主链路；
- verify 不只是单个命令占位，而能记录命令、结果、失败原因和重试/停止建议；
- 工具调用结果能被 runtime artifact 或 workspace fact chain 追踪；
- 至少一个真实代码任务通过增强工具面完成或明确停止。

### P1 Repository Understanding

让上下文选择、目标文件发现和代码关系探索成为主链路事实。

必须完成：

- 在没有显式单文件目标时，agent 能基于搜索、文件类型、符号/关键词或文档线索提出候选目标；
- context assembly 能记录为什么选择这些文件或上下文；
- 目标文件发现结果能影响后续 edit / verify 决策；
- 误选、找不到目标或上下文不足时能进入 clarify、repair 或明确停止；
- 存在测试、CLI 验证或 artifact 证明 repository understanding 被真实使用。

### P2 Native Planner

把 planner 从 compatibility-heavy routing 推进到 native execution planner。

必须完成：

- planner 能输出明确的 next action：explore、clarify、edit、verify、pause、handoff、stop 中至少五类；
- planner 决策包含理由、输入事实、风险或不确定性；
- planner 决策能驱动 runtime 主链路，而不是只作为文档或旁路字段；
- planner 能在失败、上下文不足或高风险动作时选择恢复、澄清、审批或移交；
- 存在测试或等价验证证明 planner 决策真实改变执行路径。

### P3 Unified Agent Adapter Evidence

让 native agent 与 external coding agent 共享同一套 governance fact chain。

必须完成：

- 定义或硬化 native/external agent 共享的 adapter contract；
- native execution 和至少一个 external / command / mock adapter 能输出同一类 execution fact；
- approval、evidence、recovery、runtime summary 至少两个治理面能消费这类 fact；
- operator 能区分事实来源是 native 还是 external，但看到一致的状态语义；
- 不要求真实接入所有外部 agent，但 contract 必须可验证、可回归。

## Global Stopping Criteria

只有以下条件全部满足，goal 才能停止：

1. `P0`、`P1`、`P2`、`P3` 四部分都已完成。
2. 至少一类真实代码修改任务可以通过增强后的 native agent 主链路稳定跑通或明确停止。
3. native tool surface、repository understanding、native planner 和 adapter evidence 都不再只是 helper、文档或一次性 demo。
4. planner 至少能在 explore、clarify、edit、verify、pause、handoff、stop 中真实驱动五类 next action。
5. native agent 与至少一个 external / command / mock adapter 能投影到同一治理事实链。
6. CLI / UI / workspace index / runtime payload / artifact / docs 至少两个面能看到同一事实链。
7. 相关文档、代码和测试可以互相对照，说明这个能力不是一次性演示。
8. 不得继续把目标扩展为：
   - 全面追平 `opencode` 的 TUI / Desktop / Web / plugin / release / community 能力；
   - 大规模重构整个仓库结构；
   - 为了更漂亮的抽象继续拆分执行层；
   - 做与 native agent 平台核心能力无关的产品化扩张。

## Phase Acceptance Criteria

### P0 Acceptance

`P0` 只有在以下条件全部满足时才算完成：

1. read/search/glob 或等价探索工具进入主链路。
2. patch/diff 或等价结构化编辑结果进入主链路。
3. verify 记录命令、结果、失败原因和下一步建议。
4. 工具调用事实能被 runtime artifact 或 workspace fact chain 读取。
5. 存在测试、CLI 命令或等价直接验证。

### P1 Acceptance

`P1` 只有在以下条件全部满足时才算完成：

1. 没有显式单文件目标时，agent 能产生候选文件或上下文。
2. context assembly 记录选择理由。
3. repository understanding 结果能影响 edit / verify。
4. 上下文不足时能 clarify、repair 或明确停止。
5. 存在测试、CLI 命令或等价直接验证。

### P2 Acceptance

`P2` 只有在以下条件全部满足时才算完成：

1. planner 能输出至少五类 next action。
2. planner 决策包含理由、输入事实和风险/不确定性。
3. planner 决策真实驱动 runtime 路径。
4. planner 能处理失败、上下文不足或高风险动作。
5. 存在测试、CLI 命令或等价直接验证。

### P3 Acceptance

`P3` 只有在以下条件全部满足时才算完成：

1. native/external agent 共享 adapter contract 明确存在。
2. native 和至少一个 external / command / mock adapter 输出同类 execution fact。
3. approval、evidence、recovery、runtime summary 至少两个治理面能消费同类 fact。
4. operator 能看到一致状态语义，同时区分事实来源。
5. 存在测试、CLI 命令或等价直接验证。

## Anti-Local-Optimum Guardrail

以下情况一旦成立，就应停止当前 goal，而不是继续局部优化：

1. native agent 已经能完成一类更真实代码任务，但后续工作主要变成增加更多工具名或字段名。
2. planner 已经能真实驱动五类 next action，但继续优化只是让抽象更漂亮。
3. adapter contract 已经让 native/external fact chain 对齐，但继续工作主要是在追求更多 provider 接入。
4. 当前能力已经足够把差距从“基础 agent 平台能力不足”改写为“产品厚度和生态不足”。
5. 新增工作无法直接映射到 `P0`、`P1`、`P2`、`P3` 中至少一项验收标准。

如果剩余工作大多属于下面这些，应进入下一个 goal，而不是继续本 goal：

- 完整 TUI / Desktop / Web 产品化；
- 插件市场或大型 subagent 生态；
- 全量 provider 集成；
- 安装、发布、官网、社区运营；
- 大规模性能优化；
- 更漂亮但非必要的架构抽象。

## File-Level Verification Targets

以下不是唯一文件名要求，但 goal 完成时必须能在当前仓库中找到等价实现证据。

### P0 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/execution/native_tools.py`
- `src/agent_orchestrator/execution/coding_components.py`
- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `tests/`
- 必要文档

文件层验收标准：

- 工具链真实进入主链路；
- patch/diff/verify 不是只定义不使用；
- 工具结果可被 artifact 或 fact chain 读取；
- 至少一个真实代码任务可验证。

### P1 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/execution/coding_components.py`
- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `src/agent_orchestrator/intake/`
- `src/agent_orchestrator/strategy/`
- `tests/`
- 必要文档

文件层验收标准：

- 目标文件发现不只依赖显式单文件输入；
- context assembly 有选择理由；
- repository understanding 结果能影响 edit / verify。

### P2 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/strategy/planner.py`
- `src/agent_orchestrator/intake/task_router.py`
- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `src/agent_orchestrator/execution/runtime.py`
- `tests/`
- 必要文档

文件层验收标准：

- next action 类型明确；
- planner 决策真实驱动 runtime；
- 失败、上下文不足、高风险动作有不同路径。

### P3 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/adapters.py`
- `src/agent_orchestrator/execution/runtime.py`
- `src/agent_orchestrator/control_plane_runtime.py`
- `src/agent_orchestrator/control_plane_recovery.py`
- `src/agent_orchestrator/evidence.py`
- `src/agent_orchestrator/cli_presenters.py`
- `src/agent_orchestrator/ui_service.py`
- `tests/`
- 必要文档

文件层验收标准：

- native/external adapter fact contract 明确；
- 至少两个治理面消费同类 fact；
- operator 可见面能区分来源并保持一致状态语义。

## Required Verification Evidence

goal 完成前，必须至少具备以下一种或多种直接证据组合：

- 自动化测试；
- 集成测试；
- CLI 级运行验证；
- runtime / workspace / recovery 状态直接检查；
- artifact / evidence 输出证明；
- UI / summary 投影检查；
- 文档与实现/测试之间的交叉引用。

不能只用以下弱证据宣布完成：

- “看起来已经能跑”；
- 只有 helper 存在但主链路没接入；
- 只写文档没落代码；
- 只提升抽象层次但没有真实任务闭环；
- 只修局部失败而没有形成可停止的终点；
- 单个 mock 测试通过但没有证明主路径；
- 把未验证的后续工作写成已经完成；
- 把 `opencode` 的产品生态差距误当成本 goal 必须补齐的基础能力差距。

## Explicit Non-Goals

以下内容不是本 goal 的完成要求，禁止无限扩展进去：

1. 全面复刻 `research_repos/opencode/`。
2. 构建完整 TUI、Desktop、Web 或官网文档站。
3. 建立插件市场、社区生态或完整 subagent 平台。
4. 接入所有主流 provider 或外部 coding agent。
5. 大规模重构整个仓库目录结构。
6. 以产品视觉、命名统一或抽象美化替代主链路能力增强。

如果发现这些内容确实重要，应另开新的 goal，而不是把当前 goal 拖成无限迭代。

