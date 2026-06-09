# AI-Work-Control-Plane 项目拆解讲解（更新版）

## 项目演变历程

这个项目经历了两个重要阶段：

### 阶段一：三层决策架构（早期）
- **决策核心层** - 决定"该不该做、怎么做"
- **执行拓扑层** - 决定"用什么协作形态"
- **Provider/Runtime层** - 决定"具体由谁执行"

### 阶段二：长周期任务控制平面（当前）
- **AI Work Control Plane** - 长周期本地智能体工作的控制平面
- **核心转变**：从"显式编排"转向"控制平面"

---

## 核心转变：从编排到控制平面

### 为什么要做这个转变？

**背景：**
- 模型运行时会内化更多规划、委派、审查和工具使用行为
- 如果产品的唯一价值是可见的编排，那么随着模型变强，产品会变得冗余
- 持久价值在于模型智能周围的外部工作系统：状态、上下文压缩、策略溯源、拓扑追踪、审批、证据、内存和恢复

**转变逻辑：**
```
短期：靠显式编排解决真实工作
中期：用 control plane 管住编排
长期：允许编排逐步被模型内化，但状态、证据、审批、内存和恢复仍留在系统外部
```

### 新的产品核心：制品管道

**核心制品流：**
```
WorkspaceState -> ContextPacket -> StrategyDecision -> ExecutionTopologySnapshot 
-> ApprovalItem -> EvidenceBundle -> MemoryRecord
```

**每个制品的作用：**

1. **WorkspaceStateSnapshot** - 记录当前项目现场
   - 会话、运行、作业、证据、审批
   - 提供者健康、脏文件、内存摘要
   - 可选外部缓存状态

2. **ContextPacket** - 压缩上下文供模型使用
   - 选择性文档、变更文件、内存记录
   - 过期警告
   - 不选择策略，只提供最小充分上下文

3. **StrategyDecision** - 记录下一步目标和理由
   - 下一步目标、理由、权衡、风险
   - 验证计划
   - 不执行，只记录决策

4. **ExecutionTopologySnapshot** - 只读执行拓扑图
   - 状态/上下文/策略/管理槽/工作者/审查/救援/审批/证据/内存
   - 编译后的只读视图

5. **ApprovalItem** - 人类干预作为一等公民
   - 阻塞或有风险的状态
   - 持久化且可审计
   - 不绕过执行门禁

6. **EvidenceBundle** - 标准化门禁摘要
   - 测试、合规、设置、证据报告状态
   - 推荐内存写入，不自动同步外部缓存

7. **MemoryRecord** - 内存溯源和新鲜度
   - 来源、新鲜度、置信度
   - 可选 explore_cache 状态

---

## AI 原生角色模型

**角色是制品转换器，不是人类公司头衔：**

- `state_keeper` - 工作空间存储 -> WorkspaceStateSnapshot
- `context_compressor` - 文档/内存/变更文件 -> ContextPacket
- `strategist` - 上下文和状态 -> StrategyDecision
- `topology_compiler` - 策略/计划/工作图 -> ExecutionTopologySnapshot
- `approval_gate` - 阻塞或有风险状态 -> ApprovalItem
- `evidence_recorder` - 本地门禁 -> EvidenceBundle
- `memory_curator` - 证据和结果 -> MemoryRecord

**关键区别：**
- 不是 CEO/Leader/Employee 的人类公司组织架构
- 是制品转换器，每个角色负责将输入转换为特定制品

---

## 长周期任务的核心能力

### 1. 可恢复的 Planning Governance

**目标：** 把决策核心从"能拦截"推进到"能裁决、能修订、能恢复、能继续"

**实现：**
- 固定双模型 author/reviewer 对抗审查
- `DecisionVerdict` - 决策裁决
- `team revise` - 修订命令
- gap closure - 间隙关闭
- required gap / optional follow-up 区分
- `resume` 的恢复语义
- `status` 的下一步动作提示

**状态机流程：**
```
start -> needs_revision -> revise -> approve -> execute
```

**退出条件：**
- 一个 session 可以完整走完上述流程
- 中断后能恢复
- 不再需要手工改 session 字段推进流程

### 2. Claude Delegation 作为默认协作者

**目标：** 降低人工盯防 review / adversarial review 的频率

**实现：**
- team review / adversarial review 默认可接 `claude`
- delegated job 的状态可见
- delegated job 失败时给出明确下一步建议
- 保留 `mock` 与 `command + claude` 可切换能力

**退出条件：**
- 可以稳定使用 `command + claude` 跑 team review
- 不需要翻底层 job 文件才能判断下一步

### 3. Approved Plan 驱动 Execution

**目标：** 摆脱 execution 仍然从 raw requirement 起跑的旧路径

**实现：**
- approved plan 成为 execution 正式输入
- execution provenance 记录 selected topology / provider/runtime / decision rationale
- run artifact 记录 approved-plan provenance
- team execution 与 direct execution 明确区分

**退出条件：**
- team execution 都能追溯到 approved plan
- run artifact 中清楚记录来源 session 和 approved plan

### 4. 默认内部开发工作流

**目标：** 把当前仓库切换到"默认用这套系统推进自己"

**推荐 happy path：**
```bash
team start
team status
team revise
team approve
team execute
```

**退出条件：**
- 不需要频繁打开 JSON 文件理解当前状态
- 大多数当前仓库任务都能按 happy path 连续推进
- 人工确认降到里程碑级别，而不是每个小动作都确认

---

## Live Recovery Track（长周期任务的核心）

### 核心制品链

```
Workspace / Program Index v2
  -> Run Ledger
  -> Recovery Timeline
  -> Runtime Event Stream
  -> Recovery Recommendation
  -> Operator Resume Command
  -> Evidence-backed Memory Promotion
```

### 关键能力

1. **Recovery Timeline Artifact** - 恢复时间线
   - 状态：started, checkpointed, awaiting_human, approval_blocked, evidence_blocked, compliance_blocked, provider_degraded, runtime_failed, interrupted, recovery_ready, completed

2. **Runtime Event Stream** - 运行时事件流
   - 运行时模式、命令/作业意图、工具意图
   - 结果状态、失败原因、降级原因
   - 使用/成本占位符、制品引用

3. **Recovery Recommendation Engine** - 恢复建议引擎
   - 当前阻塞原因
   - 最安全的下一步操作员命令
   - 所需审批或证据
   - 可恢复的制品引用
   - 是否可以恢复执行
   - 是否需要人类决策
   - 是否必须先修复合规

4. **Workspace Status Recovery Dashboard** - 工作空间状态恢复仪表板
   - recovery_timeline
   - runtime_events
   - recovery_recommendation
   - blocking_summary
   - resume_hint
   - last_checkpoint

5. **Evidence And Memory Loop** - 证据和内存循环
   - EvidenceBundle 引用恢复时间线和运行时事件流
   - 内存候选扩展：恢复模式、运行时降级说明、审批延迟说明、合规阻塞说明
   - 不自动写入临时状态

---

## Real-Task Dogfood Evidence Track（真实任务验证）

### 目标

扩展已提交的证据矩阵，报告：
- 恢复覆盖度
- 运行时保真度覆盖度
- 合规阻塞覆盖度
- 事后准备
- 成本/延迟就绪

### 关键理念

**证据优先：** 在深入特定于提供者的桥接行为之前，先本地验证哪些运行时差距重要。

### 最终验证结果

**2026-05-27 通过：**
- `pytest`: 414 passed
- `team check-compliance`: status passed, blocking false
- `team workspace-status --format json`: 返回 `agent_orchestrator.workspace_index.v1`
- `team evidence-gates --format json`: 返回 `agent_orchestrator.evidence_bundle.v1`
- `git status --short`: 脏树包含预期的 Real-Task Dogfood Evidence Track 文件

---

## 与早期三层架构的关系

### 早期三层架构（保留但降级）

1. **决策核心层** - 仍然存在，但不再是产品核心
   - PlanSession
   - RoundController
   - gap closure
   - approved-plan gate

2. **执行拓扑层** - 仍然存在，但成为可热插拔的执行能力
   - TeamOrchestrator
   - team chat / review / adversarial review / revision round 工作流
   - task pool / next executable task

3. **Provider/Runtime层** - 仍然存在，但成为可热插拔的执行后端
   - ClaudeCodeAdapter
   - CodexCliAdapter
   - CommandJobRuntime
   - FileJobRuntime

### 新的产品重心

**AI Work Control Plane** 不是要取代三层架构，而是在其之上构建一个更高的控制平面：

- 三层架构成为实现层
- 控制平面成为产品核心
- 编排成为可审计、可恢复、可替换的 runtime 能力

---

## 面试准备要点（更新版）

### 项目描述（简历用）

> **AI-Work-Control-Plane** - 长周期本地智能体工作的 AI 控制平面
>
> - 设计并实现 AI Work Control Plane 架构，将显式编排重构为控制平面下的可审计、可恢复执行能力
> - 构建制品管道：WorkspaceState -> ContextPacket -> StrategyDecision -> ExecutionTopologySnapshot -> ApprovalItem -> EvidenceBundle -> MemoryRecord
> - 实现长周期任务恢复能力：Recovery Timeline、Runtime Event Stream、Recovery Recommendation
> - 开发证据优先的真实任务验证框架：恢复覆盖度、运行时保真度、合规阻塞、事后准备
> - 构建 AI 原生角色模型：制品转换器而非人类公司组织架构

### 技术关键词（更新版）

- **架构演进** - 从显式编排到控制平面
- **制品管道** - 7 个核心制品的构建和流转
- **长周期恢复** - 恢复时间线、事件流、建议引擎
- **证据优先** - 真实任务验证、覆盖度报告
- **AI 原生角色** - 制品转换器模型

### 常见面试问题（更新版）

1. **为什么从三层架构转向控制平面？**
   - 模型会内化更多编排能力，产品价值需要转移到外部系统
   - 状态、证据、审批、内存和恢复是持久价值
   - 控制平面提供可检查、可恢复、可审计的工作管理

2. **制品管道是如何设计的？**
   - 7 个制品逐步构建，每个制品有明确职责
   - 不选择策略，只提供最小充分上下文
   - 所有制品都是可审计的，支持恢复

3. **长周期任务恢复是如何实现的？**
   - Recovery Timeline - 追踪状态变迁
   - Runtime Event Stream - 记录运行时事实
   - Recovery Recommendation - 生成恢复建议
   - 证据优先验证 - 确保恢复能力可靠

4. **如何验证控制平面的有效性？**
   - 真实任务 Dogfood - 在自己身上使用
   - 证据矩阵 - 恢复覆盖度、运行时保真度、合规阻塞
   - 最终验证 - pytest、合规检查、工作空间状态

---

## 总结

这个项目的演变展示了：

1. **架构演进能力** - 从显式编排到控制平面的思维转变
2. **系统思维能力** - 理解模型内化趋势，提前布局持久价值
3. **工程实践能力** - 制品管道、恢复能力、证据验证的完整实现
4. **AI 边界思考** - 明确哪些应该留在系统外部，哪些可以被模型内化

这是一个很好的展示架构思维和系统设计能力的项目。
