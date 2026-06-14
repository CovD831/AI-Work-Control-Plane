# Native Coding Agent Coverage Expansion And Stable Defaultability Goal

## Goal Intent

本 goal 不是重复证明 native coding agent 在单一 bounded repo task 上已经能跑通。

本 goal 要把当前仓库中的 native coding agent，从“在一类真实任务上已经成为默认主执行路径”推进到“在第二类、第三类真实仓库任务上也能稳定成为默认主执行路径，并具备可比较、可回归、可学习优化的默认化覆盖能力”。

这意味着本 goal 的重点不再是证明 native path 是否存在，而是证明：

- native defaultability 不再是单点成功，
- native / external 的边界不只是静态规则，而是能被真实 evidence 和 learning asset 持续校正，
- external coding agent 继续保留为 governed fallback / handoff / comparative benchmark path，
- 但 native path 已开始在更广的真实任务类上成为默认主执行器。

## Target Outcome

完成后，项目相对 `research_repos/opencode/` 的差距，应从：

- “在一类 bounded task 上 native 主路径成立”

缩小到：

- “在多类真实仓库任务上 native 主路径已具备稳定默认覆盖能力，且能用 benchmark、recovery 结果和 learning consumption 证明自己在持续变强”

为了避免主观表述，本 goal 完成后，native agent 至少要把与 `opencode` 的差距收敛到以下范围：

1. native 默认路径不只覆盖单一 bounded repo edit/docs task，而是至少覆盖第二类与第三类真实仓库任务。
2. native 与 external 的选择不只由静态规则决定，而是开始受 evidence 与 reusable learning assets 影响。
3. benchmark 能比较 native / external 在成功、阻塞、恢复、成本与人工介入上的差异，而不是只展示单次 native happy path。
4. recovery 能从“证明可恢复”推进到“在更多 failure shape 上稳定恢复”。

## Scope Boundary

本 goal 只包含以下四个实现部分，且都必须完成：

### P0 Native Default Coverage Expansion

把当前 native 默认路径从单类 task 扩展到至少两类新增真实仓库任务。

必须完成：

- 明确第二类任务边界，例如 `investigation -> edit -> verify`
- 明确第三类任务边界，例如 bounded multi-file repair / helper implementation / compliance-linked code fix
- 在 task routing / strategy / runtime 主链路中让这些任务默认优先进入 native path
- 保留 external handoff / fallback 条件，并继续投影原因码
- 在 runtime metadata、session snapshot、CLI 或 UI summary 中能看见“新增任务类为什么进入 native”

当前实现约定：

- `INVESTIGATION` 在存在 learning-backed bounded path 证据时，默认进入 `native_preferred`，并由 planner 选择 `EXPLORE_THEN_EDIT`。
- bounded multi-file helper/compliance repair 通过 comparative benchmark bundle 固定为新增 native coverage case，而不是一次性演示。

### P1 Comparative Benchmark And Coverage Evidence

把 native defaultability 的证明从“单类任务成立”推进到“多类任务相对 external 可比较”。

必须完成：

- 固定一个多任务类 benchmark bundle
- 至少比较 native 与 external 在以下维度中的多个：
  - success rate
  - blocked rate
  - repair / resume success rate
  - verification cost
  - human intervention frequency
- benchmark 结果必须进入 control plane、workspace index、evidence report 或 UI summary 中至少两个面
- 形成稳定 evidence，可被后续 release/readiness 复用

### P2 Recovery Breadth Hardening

把当前 recovery 能力从“成功/阻塞/修复恢复成功三链路存在”推进到“在更多 failure shape 上仍能稳定恢复或明确停止”。

必须完成：

- 扩展至少一类新的 recovery 失败形态，例如 exploration ambiguity、partial edit drift、multi-file verify mismatch、approval-interrupted continuation
- 为这些 failure shape 明确 native continue / block / handoff / fallback 契约
- 对恢复动作保留原因码、remaining budget、resume continuity 与 evidence 投影
- 不因为扩 recovery 而破坏当前 bounded default path 的稳定性

当前新增 failure shape：

- `exploration_ambiguity_or_scope_drift`
- 语义：可以继续探索则 `continue/inspect`，需要重新收敛目标则 `scope_realign`，高风险时仍允许 governed `fallback/handoff`

### P3 Learning Asset Consumption Loop

把当前已经能写出的 trajectory / memory / skill / curator-ready 资产，从“可存储”推进到“可被下次路由或规划消费”。

必须完成：

- planner、router 或 strategy 至少一个面能读取 learning asset
- 明确哪些 asset 可以影响默认路径选择，哪些只能影响解释或建议
- 形成至少一个 `Trajectory -> Router/Planner decision` 的可回归样例
- 保持 facts / procedures / policy-heuristic 的边界，不把短期噪声直接写成长期默认规则

当前消费点：

- `TaskRouter.native_learning_store` 会读取 `native_trajectory` / `native_learning` 记录，并把 learning-backed evidence 用于真实 native path 选择。

## Global Stopping Criteria

只有以下条件全部满足，goal 才能停止：

1. `P0`、`P1`、`P2`、`P3` 四部分都已完成。
2. native 默认路径已至少覆盖三类真实仓库任务，其中两类是本 goal 新增覆盖。
3. 已存在稳定的 comparative acceptance / benchmark bundle，而不只是单条 native 证明链。
4. 每类新增任务至少有以下三类中的一致证据：
   - artifact / evidence
   - runtime event / session state
   - workspace index / dashboard
   - UI summary / CLI summary
5. learning asset 不只被写入，还至少被一次真实路由或规划决策消费。
6. external agent 仍可热插拔接入，且 fallback/handoff 仍受治理。
7. 已更新详细文档，说明：
   - 哪些新增任务类 native 默认执行
   - benchmark 如何比较 native 与 external
   - recovery 在哪些 failure shape 上扩展
   - learning asset 如何被消费而不污染默认策略
8. 本轮工作没有继续无限扩张到：
   - 覆盖所有 coding task 类型
   - 建完整 benchmark 平台产品
   - 做与 coverage expansion 无关的大规模重构
   - 追求通用 agent 全面自治

若以上任一项不满足，则 goal 不能视为完成。

## Phase Acceptance Criteria

### P0 Acceptance

`P0` 只有在以下条件全部满足时才算完成：

1. 至少新增两类真实任务被定义为 native 默认覆盖范围。
2. 这些任务类在 task router / planner / runtime 主链路中默认进入 native path。
3. external path 没有被删除，而是保留为显式 handoff/fallback。
4. runtime metadata、session snapshot、CLI 或 UI summary 中能看到新增任务类的路径选择结果。
5. 存在测试或等价直接验证，证明新增 default coverage 真实生效，而不是只改文案。

### P1 Acceptance

`P1` 只有在以下条件全部满足时才算完成：

1. 固定一个多任务类 benchmark bundle。
2. bundle 至少覆盖 native / external 在多个任务类上的比较结果。
3. benchmark 不只展示最终状态，还包含 blocked / recovery / human intervention 等治理语义。
4. benchmark 结果能被 control plane、workspace index、UI/CLI summary 或 evidence report 消费。
5. 存在自动化测试或等价高信号验证，证明 benchmark bundle 长期可回归。

### P2 Acceptance

`P2` 只有在以下条件全部满足时才算完成：

1. 至少新增一类 recovery failure shape 被正式纳入恢复语义。
2. 对该 failure shape，continue / block / fallback / handoff 边界已被清晰定义。
3. 恢复动作会产出原因码、remaining budget、resume continuity 或等价证据。
4. external handoff 仍可用，但不是隐式兜底。
5. 存在测试或等价直接验证，证明新增 recovery breadth 是执行语义而不是文档描述。

### P3 Acceptance

`P3` 只有在以下条件全部满足时才算完成：

1. planner、router 或 strategy 至少一个面能消费 learning asset。
2. `Trajectory -> Router/Planner decision` 至少存在一个真实、可回归样例。
3. `Memory` / `Skill` / `SessionDB` 的消费边界与写入边界保持一致，不混淆短期噪声与长期规则。
4. `Nudge` / curator-ready 元数据能区分事实、流程、policy / heuristic 三类复盘结果。
5. 明确把更强的自动优化、RL、GEPA 留到后续 goal，不作为本 goal 的完成条件。

## File-Level Verification Targets

以下不是唯一文件名要求，但 goal 完成时必须能在当前仓库中找到等价实现证据。

### P0 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/intake/`
- `src/agent_orchestrator/strategy/`
- `src/agent_orchestrator/execution/`
- `src/agent_orchestrator/ui_service.py`
- 相关 tests
- 必要文档

文件层验收标准：

- 新增 native 默认覆盖任务类清晰
- fallback/handoff 条件清晰
- 执行选择结果可被投影到用户可见面

### P1 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/evidence.py`
- `src/agent_orchestrator/control_plane_workspace.py`
- `src/agent_orchestrator/ui_service.py`
- `tests/`
- 必要 benchmark / dogfood 文档

文件层验收标准：

- benchmark bundle 有稳定落点
- native / external 比较结果不是一次性日志
- 多个消费面至少部分共享同一证据来源

### P2 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/execution/`
- `src/agent_orchestrator/session/`
- `src/agent_orchestrator/evidence.py`
- `tests/`
- 必要 recovery 文档

文件层验收标准：

- 新 failure shape 的恢复语义在代码中可识别
- block / fallback / handoff 原因有正式字段或等价契约
- recovery continuity 未被破坏

### P3 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/memory.py`
- `src/agent_orchestrator/session/`
- `src/agent_orchestrator/strategy/`
- `src/agent_orchestrator/intake/`
- `tests/`
- 必要文档

文件层验收标准：

- learning asset 的读取和消费有稳定格式
- 记忆 / 技能 / 会话资产不只可写，也可被复用
- curator-ready 资产能影响后续执行建议或默认路径选择

## Required Verification Evidence

goal 完成前，必须至少具备以下证据组合中的多项：

- 自动化测试
- 集成测试
- benchmark capture / evidence report
- CLI 级验证
- session state / runtime metadata 直接检查
- artifact / evidence 直接检查
- workspace index / UI summary 投影检查

不能只用以下弱证据宣布完成：

- “native 覆盖看起来更多了”
- 单次人工 happy path 演示
- 只有 benchmark 文档没有执行语义
- 只有 asset 存储没有被消费
- 只有新增路由声明没有真实 acceptance / benchmark bundle

## Explicit Non-Goals

以下内容不是本 goal 的完成要求，禁止无限扩展进去：

- 一次性覆盖所有 coding task 类型
- 做完整 benchmark 平台产品
- 全面追平 `opencode` 的所有工具、UI、插件生态和产品表面
- 让 learning loop 直接演化为完整自动策略训练系统
- 做与 coverage expansion 无关的大规模目录或抽象重构
