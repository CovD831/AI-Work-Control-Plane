# Provider 边界审计清单

## 目的

这份清单用于回答一个核心问题：

**这个项目的哪些能力属于 `Codex` / `Claude Code` 这类 coding agent 本体，哪些能力应该明确保留在外部 control plane？**

判断标准如下：

- 如果一个能力主要服务于**当前这一次 provider session 的思考和执行**，它更容易和 provider 重合。
- 如果一个能力在**跨 session、跨阶段、跨 provider、跨恢复流程**时仍然必须存在，它更适合保留在 control plane。

## 当前结论

当前仓库已经有比较强的 control-plane 骨架，但仍存在一批**边界偏模糊**的字段和叙事。

更准确的定位应该是：

> 本项目不与 coding agent 竞争“如何规划和执行一次任务”，而是提供这些 agent 之上的外部治理层，负责长期状态、审批、证据、恢复和可观测性。

## 一、建议保留

这些内容是项目最值得保留、也最不容易被 provider 完全吃掉的部分。

### 1. Workspace / Program 级状态

保留原因：

- provider 只拥有自己的 session
- control plane 应拥有长期 program state

代表能力：

- `WorkspaceState`
- `workspace_index`
- `run_ledger`
- `provider_session_ref`

### 2. 审批与门禁

保留原因：

- provider 会做命令级 approval
- 但项目级 approval、evidence gate、人工接管点仍然应该是外部系统职责

代表能力：

- `ApprovalItem`
- `approval_queue`
- `evidence_gates`
- `compliance_snapshot`

### 3. 恢复与续跑

保留原因：

- provider 可以恢复自己的会话
- 但跨阶段恢复、恢复建议、恢复前阻塞分析更适合在 control plane 外部保存

代表能力：

- `RecoveryTimeline`
- `RuntimeEventStream`
- `RecoveryRecommendation`
- `resume_hint`

### 4. 运行时事实与可观测性

保留原因：

- provider 有自己的日志
- control plane 需要结构化、可消费、可归档的运行事实

代表能力：

- `runtime_measurement`
- `operation_receipt`
- `provider_session_snapshot`
- `provider_evidence_summary`

### 5. 带 provenance 的 memory

保留原因：

- provider 的上下文窗口不是长期项目记忆系统
- control plane 可以维护带来源和新鲜度的长期记忆记录

代表能力：

- `MemoryRecord`
- `memory_digest`
- `external_cache_status`

## 二、建议降级

这些内容不是完全没价值，但不应该再作为主卖点，更适合作为辅助字段或内部实现细节。

### 1. `StrategyDecision`

问题：

- 当前名字很容易让人联想到“替 agent 做 planning”
- 如果内部包含太多 `next_goal`、执行建议、验证步骤，就会和 provider 的 planning 重合

建议：

- 保留 artifact，但弱化“策略制定器”的叙事
- 在外部表达上，把它更多讲成：
  - 当前约束摘要
  - 执行门禁摘要
  - 恢复方向摘要
  - provider/runtime 选择摘要

### 2. `ExecutionTopologySnapshot`

问题：

- 如果强调 team / role / reviewer flow，本质上很像 orchestration spectacle

建议：

- 对外少讲“拓扑设计”
- 对内保留为只读编译视图
- 对外改讲“执行路径快照”或“执行结构快照”

### 3. 显式 review / adversarial review round

问题：

- 大公司 agent 会越来越多地内建 review/self-review/sub-agent review
- 显式 reviewer 角色越重，越容易显得你在重复造 agent workflow

建议：

- 保留 gate 语义
- 降低人格化角色叙事
- 从“谁来审”转向“为什么这里需要审”

### 4. role-heavy 叙事

问题：

- `state_keeper`、`context_compressor`、`strategist`、`topology_compiler` 这类命名在架构上可以保留
- 但如果在 README/面试里讲太多，会让项目看起来像“角色编排框架”

建议：

- 在对外叙事里减少 role-centered 表达
- 强调 artifact-centered 和 governance-centered 表达

## 三、建议重命名或改表达

这些内容最容易和 coding agent 自带 planning 重合，建议逐步改表达。

### 1. `next_goal`

问题：

- 非常像 provider session 内部的下一步思考

建议替代表达：

- `approved_objective`
- `current_checkpoint_objective`
- `resume_objective`

### 2. `validation_plan`

问题：

- 很像 agent 自己写的执行前小计划

建议替代表达：

- `required_verification_gates`
- `verification_requirements`
- `evidence_requirements`

### 3. `Decision Core`

问题：

- 容易让人误以为这是在替 agent 做思考核心

建议替代表达：

- `Governance Layer`
- `Execution Governance`
- `Approval And Evidence Layer`

### 4. `Execution Topology`

问题：

- 容易让人联想到 multi-agent orchestration

建议替代表达：

- `Execution Structure`
- `Execution Path`
- `Execution Snapshot`

## 四、建议删除候选

这些内容不一定要立刻删代码，但应该从 README、面试稿、项目定位里退出主舞台。

### 1. org chart 风格角色故事

原因：

- 它和 provider 本体的 agent workflow 越来越容易重合
- 也会冲淡 control-plane 项目的边界

### 2. 把 review / rescue 当成“多 agent 戏份”

原因：

- 更像 orchestrator 展示
- 不像治理层展示

### 3. 过多强调“下一步怎么做”

原因：

- 这是 provider 非常擅长内化的部分
- control plane 更应该强调“为什么允许做、做到什么算完成、失败后怎么恢复”

## 五、推荐的对外边界表述

### 最稳的一句话

> 我不是在和 Codex 或 Claude Code 竞争谁更会规划和写代码，我做的是它们之上的外部治理层，把长周期任务里的状态、审批、证据、恢复和运行事实从单次 agent 会话里抽出来。

### 推荐分层

#### 1. Provider Runtime Layer

负责：

- 本地 `codex` / `claude` CLI
- provider session
- sandbox / command execution
- 原始输出

#### 2. Execution Fact Layer

负责：

- task attempt
- runtime measurement
- operation receipt
- failure reason
- checkpoint
- provider session ref

#### 3. Governance Layer

负责：

- project objective
- approval state
- evidence bundle
- recovery recommendation
- workspace/program state
- memory provenance

## 六、建议的下一步改造顺序

### 第一批：先改叙事，不先大改 schema

- README
- 面试稿
- roadmap / study map

### 第二批：改容易误导的字段名或展示名

- `next_goal`
- `validation_plan`
- `Decision Core`
- `Execution Topology`

### 第三批：缩 role-centered surface

- `team roles`
- UI 里的角色分层展示
- review / adversarial review 的人格化术语

## 七、本轮建议结论

如果只用一句话总结本轮边界调整方向：

> 把“替 agent 想下一步”的部分降级，把“记录 agent 之外必须长期存在的事实和约束”的部分抬到项目中心。
