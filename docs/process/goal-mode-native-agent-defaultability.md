# Native Coding Agent Defaultability And Real-Task Acceptance Goal

## Goal Intent

本 goal 不是继续做差距分析，也不是只做一条 happy path 演示。

本 goal 要把当前仓库中的 native coding agent，从“已经具备核心执行闭环”推进到“在本框架内可作为主执行器默认承担一类真实 coding task，并能用可审计证据证明自己不再主要依赖 external coding agent 才能完成工作”。

同时，仍然必须保留 external coding agent 的热插拔能力，使 external agent 成为：

- fallback executor
- specialized handoff target
- comparative benchmark path

而不是隐藏的默认依赖。

## Target Outcome

完成后，项目相对 `research_repos/opencode/` 的差距，不再是“有 native agent 雏形，但主执行能力仍偏早期”，而要收敛到下面这个层级：

- 在本项目最核心的 coding task 主路径上，native agent 已经具备可默认使用的真实执行能力；
- 与 `opencode` 相比，仍然落后于工具广度、交互产品厚度、插件生态和通用任务覆盖面；
- 但在“治理原生 + 审批恢复 + 证据外化 + native/external 协作”的目标方向上，已经缩小到“核心任务可同代际竞争，平台广度仍落后”的程度。

为了避免主观表述，本 goal 完成后，native agent 至少要把与 `opencode` 的差距缩小到以下范围：

1. 在至少一类真实仓库任务上，不再需要 external agent 才能完成端到端闭环。
2. 在该任务类上，native path 成为默认推荐主路径，而不是实验分支。
3. 真实执行证据可在 control plane、workspace index、UI summary、artifact/evidence 中被一致看到。
4. external agent 的价值主要收敛为 fallback / handoff / 对照，不再是 native path 成功的隐性前提。

## Scope Boundary

本 goal 只包含以下四个实现部分，且都必须完成：

### P0 Native Default Path Promotion

把 native coding agent 提升为至少一类任务的默认主执行路径。

必须完成：

- 明确一类任务边界，例如仓库内受限代码修改/修复/文档联动类任务
- 在 task routing / strategy / runtime 里让该类任务默认优先走 native path
- 明确保留 external handoff / fallback 条件
- 能在 runtime metadata 和 UI/CLI summary 中看见“为什么选择 native 或 external”

### P1 Real-Task Acceptance Bundle

把 native coding agent 的能力证明从“结构闭环存在”升级为“真实任务验收成立”。

必须完成：

- 设计并固定一个 native-only real-task acceptance bundle
- 至少包含成功链、阻塞链、修复恢复链三类真实链路
- 每条链路都要经过控制平面，而不是绕过治理直接执行
- 形成稳定 evidence，可被后续 release/readiness 复用

### P2 Native/External Operating Boundary Hardening

把 native agent 和 external agent 的协作边界从“都能接”推进到“什么时候默认 native，什么时候必须 handoff external，什么时候允许 fallback”的可执行契约。

必须完成：

- 明确 native preferred / external preferred / governed fallback 三类边界
- 在 adapter/runtime/planner 文档与代码里形成一致语义
- 对 handoff 和 fallback 提供证据与原因码，而不是隐式切换
- 确保不因为追求 native 默认而破坏热插拔架构

### P3 Learning Loop Externalization Foundation

把 native agent 的执行经验外化成可读、可检索、可维护、可复用的资产。

必须完成：

- 保存会话与工具轨迹到结构化存储
- 维护 `Memory` / `User` / `Skill` / `SessionDB` 的可读与可检索资产
- 引入后台复盘 `Nudge`，决定哪些事实进 Memory、哪些流程变 Skill、哪些决策应形成 policy / heuristic asset
- 为 Curator 维护 Skill 库提供状态、元数据、合并 / 归档 / 修补依据
- 为后续 `Trajectory -> Prompt / Policy / Skill` 优化准备结构化数据，而不是直接跳到 RL / GEPA

## Global Stopping Criteria

只有以下条件全部满足，goal 才能停止：

1. `P0`、`P1`、`P2`、`P3` 四部分都已完成。
2. 至少一类真实任务已由 native agent 作为默认主路径完成端到端执行。
3. 已存在稳定的三链路 acceptance bundle：
   - 成功链
   - 阻塞链
   - 修复恢复成功链
4. 每条链路都能在以下至少三类位置看到一致证据：
   - artifact / evidence
   - runtime event / session state
   - workspace index / dashboard
   - UI summary / CLI summary
5. 经验外化闭环已能把执行轨迹稳定写入会话存储，并能反向生成可读资产。
6. external agent 仍可热插拔接入，且 handoff/fallback 不是被删掉，而是被明确治理。
7. 已更新详细文档，说明：
   - 哪类任务 native 默认执行
   - 哪类任务 external 更适合
   - fallback / handoff 的停止边界
   - trajectory / memory / skill / session 资产如何外化与复用
8. 本轮工作没有继续无限扩张到：
   - 全面追平 `opencode` 全工具面
   - 做完整产品化 UI
   - 做多任务类全面 benchmark
   - 做与 defaultability 无关的大规模重构

若以上任一项不满足，则 goal 不能视为完成。

## Phase Acceptance Criteria

### P0 Acceptance

`P0` 只有在以下条件全部满足时才算完成：

1. 至少定义出一类“native 默认”的真实任务类型。
2. 该任务类型在 task router / planner / runtime 主链路中默认进入 native path。
3. external path 没有被删除，而是保留为显式 handoff/fallback。
4. runtime metadata、session snapshot、CLI 或 UI summary 中能看到路径选择结果。
5. 存在测试或等价直接验证，证明默认路径选择真实生效，而不是只改文案。

### P1 Acceptance

`P1` 只有在以下条件全部满足时才算完成：

1. 固定一个 native real-task acceptance bundle。
2. bundle 至少包含三条链路：
   - native 成功链
   - native 阻塞/等待链
   - native 修复恢复成功链
3. 三条链路都经过真实治理语义：
   - approval pause / resume
   - verify
   - artifact/evidence
   - recovery continuity
4. bundle 结果能被 control plane、workspace index、UI/CLI summary 消费。
5. 存在自动化测试或等价高信号验证，证明这三条链路长期可回归。

### P3 Acceptance

`P3` 只有在以下条件全部满足时才算完成：

1. 执行轨迹可稳定保存到结构化存储，且可按 session / task / tool / outcome 检索。
2. `Memory` / `User` / `Skill` / `SessionDB` 至少三类资产已形成明确写入规则。
3. `Nudge` 能区分事实、流程、policy / heuristic 三类复盘结果。
4. `Curator` 具备 Skill 合并、归档、修补的元数据基础。
5. 已存在 `Trajectory -> Skill` 或 `Trajectory -> Memory` 的可回归样例或等价验证。
6. 明确把 RL / GEPA 保留为后续 goal，不作为当前 goal 的完成条件。

## Current Implementation Seal

当前工作树已将以下边界固化为正式执行语义，而不只是文档愿景：

- `native_preferred`: `DIRECT_FIX` / `GENERAL_CODING` / `DOCS` 这类 bounded repository task 默认走 native path。
- `external_preferred`: migration、high-risk、需要显式 human confirmation 的任务默认进入 external/handoff path。
- `fallback_governed`: investigation 等尚未升为 native 默认的任务保留 governed fallback 语义。

当前正式原因字段：

- `selection_reason`
- `handoff_reason_code`
- `fallback_reason_code`
- `default_path`
- `operating_boundary`

当前 learning-loop 基础资产已经有稳定写入落点：

- `MemoryStore`: `native_trajectory` / `native_learning`
- `KnowledgeStore`: `lessons` / `skills`
- `SessionRuntime`: `trajectories`

当前 `Nudge` / curator-ready 语义通过结构化 `skills` knowledge payload 固化，约定：

- facts -> `Memory`
- procedures -> `Skill`
- decision/policy heuristics -> curator metadata

### P2 Acceptance

`P2` 只有在以下条件全部满足时才算完成：

1. native preferred / external preferred / fallback 三类边界已被明确定义。
2. planner / adapter / runtime / docs 至少在其中三个面上保持一致。
3. handoff 或 fallback 会产出原因码、metadata 或等价证据。
4. external agent 仍能通过统一契约接入，不因 native 默认化而退化。
5. 存在测试或等价直接验证，证明协作边界是执行语义，不只是文档描述。

## File-Level Verification Targets

以下不是唯一文件名要求，但 goal 完成时必须能在当前仓库中找到等价实现证据。

### P0 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/intake/`
- `src/agent_orchestrator/strategy/`
- `src/agent_orchestrator/execution/`
- `src/agent_orchestrator/cli.py`
- `src/agent_orchestrator/ui_service.py`
- 相关 tests
- 必要文档

文件层验收标准：

- native 默认路由规则清晰
- external fallback/handoff 条件清晰
- 执行选择结果可被投影到用户可见面

### P1 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/execution/`
- `src/agent_orchestrator/session_runtime.py`
- `src/agent_orchestrator/ui_service.py`
- `tests/`
- `docs/process/native-coding-agent-dogfood-evidence.md`
- 必要的新 goal/phase 文档

文件层验收标准：

- 三链路 acceptance bundle 有稳定落点
- evidence 不是一次性日志，而是可回归的证明对象
- UI / workspace / session 投影至少部分共享同一证据来源

### P3 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/memory.py`
- `src/agent_orchestrator/session/`
- `src/agent_orchestrator/roles.py`
- `src/agent_orchestrator/evidence.py`
- `tests/`
- 必要文档

文件层验收标准：

- 轨迹存储和资产写入有稳定格式
- 记忆 / 技能 / 会话数据能被读取和复用
- Curator 或等价维护机制有明确输入输出
- 不依赖手工整理才能形成可复用资产

### P2 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/execution/models.py`
- `src/agent_orchestrator/strategy/`
- `src/agent_orchestrator/execution/`
- `src/agent_orchestrator/adapters.py`
- 相关 tests
- 必要文档

文件层验收标准：

- native/external 边界在代码中可识别
- fallback/handoff 原因有正式字段或等价契约
- external 热插拔能力未被 native 默认化破坏

## Required Verification Evidence

goal 完成前，必须至少具备以下证据组合中的多项：

- 自动化测试
- 集成测试
- CLI 级验证
- session state / runtime metadata 直接检查
- artifact / evidence 直接检查
- workspace index / UI summary 投影检查

不能只用以下弱证据宣布完成：

- “native 看起来已经能跑”
- 单次人工 happy path 演示
- 只有代码没有投影
- 只有文档没有实现
- 只有默认声明没有真实 acceptance bundle

## Explicit Non-Goals

以下内容不是本 goal 的完成要求，禁止无限扩展进去：

- 全面追平 `opencode` 的所有工具、session UX、插件市场和产品表面
- 一次性覆盖所有 coding task 类型
- 做完整 benchmark 平台
- 做与 native 默认化无关的大规模目录或抽象重构
- 为追求“更像成熟产品”而持续进行无边界命名、封装、界面打磨
- 直接进入 RL / GEPA / 权重内化主线

## Anti-Local-Optimum Guardrail

为防止 goal 掉入无限局部优化，一旦满足以下条件，就应停止：

1. `P0/P1/P2/P3` 都已满足各自验收标准。
2. 至少一类真实任务已可默认走 native path 并成功闭环。
3. 三链路 acceptance bundle 已稳定存在并可回归。
4. 经验外化闭环已稳定运行，且后续资产整理主要交给 Curator，而不是人工临时整理。
5. external hot-plug 能力仍保留且边界清晰。
6. 与 `opencode` 的差距已收敛到：
   - 核心任务主路径可竞争
   - 平台广度、工具广度、产品厚度仍明显落后

如果此时剩余工作主要变成下面这些内容，则必须停下，归入下一个 goal：

- 扩更多工具
- 覆盖更多任务类型
- 做更强交互/UI/IDE 体验
- 做更大规模生态插件能力
- 做更完整 benchmark 或性能优化
- 直接进入 RL / GEPA 训练或权重级内化

## Goal-Mode Short Form

建议用于 goal 模式的短文本如下：

让 native coding agent 在至少一类真实仓库任务上成为默认主执行路径，并完成可回归的三链路 real-task acceptance bundle（成功/阻塞/修复恢复成功），同时把执行经验外化为可读可复用资产（Memory / User / Skill / SessionDB / Trajectory / Nudge / Curator-ready），并保留 external coding agent 热插拔与 governed fallback/handoff。完成标准、阶段验收、文件级验收与停止条件详见 `docs/process/goal-mode-native-agent-defaultability.md`。
