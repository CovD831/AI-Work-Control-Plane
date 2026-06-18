# Coding Agent Execution Goal

## Goal Intent

本 goal 的目的，是把当前仓库的执行层做成一个真正能承担开发任务的 coding agent 主路径，而不是只保留治理壳和局部 helper。

这里的“能承担开发任务”不是泛泛地指会调用模型，而是指它能在同一个受治理语义下完成下面这条链路：

- 接收明确任务
- 选择合适上下文
- 找到相关代码与文件
- 形成可执行编辑意图
- 应用补丁或文件修改
- 运行验证
- 处理失败与恢复
- 在审批暂停后继续推进
- 把事实投影到 operator 可见面

本 goal 必须防止陷入“工具越来越多、文档越来越漂亮、但任务闭环没有变强”的局部最优。

## Target Outcome

完成后，当前项目与 `research_repos/opencode/` 的差距应主要体现在：

1. 产品厚度与 UI 丰富度。
2. 更大的 agent 生态和插件生态。
3. 更广泛的通用交互体验。

而不应主要卡在：

1. 执行闭环不稳定。
2. 编辑和验证不能形成主链路。
3. 恢复语义不清晰。
4. 审批暂停后无法继续。
5. 结果事实无法稳定投影到用户可见面。

## Scope Boundary

本 goal 只包含以下四个实现部分，且都必须完成：

### P0 Execution Loop

建立稳定的执行闭环：

- 任务进入时能生成明确的 execution request
- 能读取工作区和相关上下文
- 能形成执行步骤
- 能推进到下一步而不是只停在计划
- 能产出结构化 observations 或等价事实

必须完成：

- 任务执行主链路可以跨过一次以上步骤；
- 执行状态可以被持久化；
- 失败时能给出明确阻塞或恢复建议；
- 至少一个真实任务类可以通过该闭环推进到完成或明确停止。

### P1 Editing And Verification

让修改与验证进入主链路，而不是只是存在于 helper 中。

必须完成：

- 文件读取、搜索、目录探索、补丁应用、命令验证都能在主路径上协同工作；
- 修改后的结果可以被验证；
- 验证失败能回到可继续的修复动作；
- 变化结果有可追踪的 artifact、diff、或等价记录。

### P2 Recovery And Approval

让暂停、恢复、审批和回放成为正式执行语义。

必须完成：

- approval pause 能在需要时阻断高风险动作；
- resume 能从明确状态继续，而不是重跑一切；
- execution state store 或等价机制能保存恢复所需事实；
- 恢复前后的状态差异是可见的；
- 恢复动作不会破坏 control plane 的边界与审计语义。

### P3 Operator Visibility

让执行事实能被 operator 直接看见和判断。

必须完成：

- CLI summary 能显示当前执行进度、修改结果与阻塞原因；
- UI 或 workspace index 至少一个面能显示恢复姿态或执行结果；
- runtime payload / workspace index / CLI summary 至少两个面共享同一事实链；
- 用户能区分“正在执行”“已暂停”“可恢复”“已完成”“已停止”。

## Global Stopping Criteria

只有以下条件全部满足，goal 才能停止：

1. `P0`、`P1`、`P2`、`P3` 四部分都已完成。
2. 至少一类真实开发任务可以在当前执行层里稳定跑通闭环。
3. 编辑、验证、审批、恢复、投影都不再只是局部 helper，而是主链路语义。
4. 与 `opencode` 的差距已经主要是产品厚度，而不是执行能力基础面。
5. 相关文档、代码和测试可以互相对照，说明这个能力不是一次性演示。
6. 不得继续把目标扩展为：
   - 全面追平 `opencode` 的所有 UI / 插件 / 生态能力
   - 大规模重构整个仓库结构
   - 为了更漂亮的抽象继续拆分执行层
   - 做与执行闭环无关的产品化扩张

## Phase Acceptance Criteria

### P0 Acceptance

`P0` 只有在以下条件全部满足时才算完成：

1. 执行主链路能从 request 进入到多步推进。
2. 执行过程能产出结构化状态或事实。
3. 状态可以持久化，且可被后续步骤读取。
4. 真实任务不会只停留在“计划已生成”。
5. 存在测试或等价直接验证。

### P1 Acceptance

`P1` 只有在以下条件全部满足时才算完成：

1. 文件修改或补丁应用真实进入主链路。
2. 验证动作真实执行，而不是只记录预期。
3. 验证失败可进入修复或重试闭环。
4. 修改结果能以 artifact、diff、日志或等价形式追踪。
5. 存在测试或等价直接验证。

### P2 Acceptance

`P2` 只有在以下条件全部满足时才算完成：

1. 审批暂停可以阻断高风险动作。
2. 恢复继续可以从明确状态继续推进。
3. 恢复语义有明确状态存储支撑。
4. 恢复前后事实能在记录中区分。
5. 存在测试或等价直接验证。

### P3 Acceptance

`P3` 只有在以下条件全部满足时才算完成：

1. CLI / UI / workspace index 至少两个面能看到同一执行链。
2. 阻塞、完成、暂停、恢复等状态可区分。
3. operator 无需翻源码就能判断执行是否还在可控范围内。
4. 事实投影与运行状态一致，不互相打架。
5. 存在测试或等价直接验证。

## Anti-Local-Optimum Guardrail

以下情况一旦成立，就应停止当前 goal，而不是继续局部优化：

1. 核心闭环已经成立，但后续工作主要变成增加更多工具名。
2. 代码已经能完成任务，但继续优化只是让抽象更漂亮。
3. 继续工作主要是在做 UI 漂亮化、命名统一化或目录重排。
4. 当前能力已经足够支撑真实开发任务，剩余差距主要是产品厚度。

如果剩余工作大多属于下面这些，应进入下一个 goal，而不是继续本 goal：

- 更强的通用 agent 生态
- 更大的插件系统
- 更厚的产品界面
- 更广泛的任务类型覆盖
- 更深的性能优化

## File-Level Verification Targets

以下不是唯一文件名要求，但 goal 完成时必须能在当前仓库中找到等价实现证据。

### P0 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/execution/`
- `src/agent_orchestrator/execution/runtime.py`
- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `src/agent_orchestrator/execution/coding_components.py`
- `tests/`
- 必要文档

文件层验收标准：

- 执行主链路真实存在
- 多步语义真实存在
- 状态不是临时变量

### P1 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/execution/native_tools.py`
- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `src/agent_orchestrator/execution/coding_components.py`
- `tests/`
- 必要文档

文件层验收标准：

- 修改与验证是主链路的一部分
- 工具调用不是只定义不使用
- 验证失败有可追踪的恢复出口

### P2 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/execution/state_store.py`
- `src/agent_orchestrator/control_plane_approvals.py`
- `src/agent_orchestrator/control_plane_runtime.py`
- `src/agent_orchestrator/control_plane_recovery.py`
- `tests/`
- 必要文档

文件层验收标准：

- resume 和 approval pause 有明确语义
- 恢复状态可读
- 不只是概念设计

### P3 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/cli_team.py`
- `src/agent_orchestrator/cli_presenters.py`
- `src/agent_orchestrator/ui_server.py`
- `src/agent_orchestrator/ui_service.py`
- `src/agent_orchestrator/control_plane_workspace.py`
- `tests/`
- 必要文档

文件层验收标准：

- operator 可见面真实展示执行状态
- 至少两个 surface 可对照同一事实链
- 恢复姿态或阻塞原因可见

## Required Verification Evidence

goal 完成前，必须至少具备以下一种或多种直接证据组合：

- 自动化测试
- 集成测试
- CLI 级运行验证
- runtime / workspace / recovery 状态直接检查
- artifact / evidence 输出证明
- UI / summary 投影检查

不能只用以下弱证据宣布完成：

- “看起来已经能跑”
- 只有 helper 存在但主链路没接入
- 只写文档没落代码
- 只提升抽象层次但没有真实任务闭环
- 只修局部失败而没有形成可停止的终点

## Explicit Non-Goals

以下内容不是本 goal 的完成要求，禁止无限扩展进去：

- 全面追平 `research_repos/opencode/` 的全部 UI、插件和生态
- 建完整 IDE / editor 产品
- 做完整 benchmark 平台产品
- 做与执行闭环无关的大规模架构重写
- 把所有 coding task 类型一次性覆盖完
- 继续在核心闭环成立后做无限局部打磨

