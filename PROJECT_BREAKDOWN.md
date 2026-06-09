# AI-Work-Control-Plane 项目拆解讲解

## 项目概况

**项目规模：**
- Python 代码：**21,910 行**（src/agent_orchestrator/）
- 文档：**193 个 Markdown 文件**
- 测试：**20+ 个测试文件**
- 版本：**v1.0.0** 稳定版

**一句话描述：**
一个用于长期周期智能体工作的本地优先 AI 控制平面系统，实现工作流程的显式编排、状态追踪和审计。

---

## 核心架构：三层分离设计

这个项目最大的设计亮点是**三层分离架构**，这是 AI 辅助开发时的关键决策。

### 第一层：决策核心层 (Decision Core)

**职责：** 决定"该不该做、怎么做、做到什么程度才能继续往下走"

**核心模块：**
- `planning.py` - 计划会话管理、合规门禁、执行握手
- `planning_support.py` - 合规检查、会话指导、文档上下文快照
- `guards.py` - 硬权限守卫、制品写入验证、执行门禁
- `control_plane.py` - 工作空间、上下文包、策略决策、拓扑快照构建

**关键概念：**
```
用户需求 → 计划会话 → 审查 → 人类批准 → 执行门禁 → 执行
```

**状态机流程：**
```
intake_chat → draft_ready → adversarial_review → awaiting_human_confirmation 
→ approved_for_execution → executing → accepted
```

### 第二层：执行拓扑层 (Execution Topology)

**职责：** 决定"任务用什么 agent 协作形态来完成"

**核心模块：**
- `orchestrator.py` - 端到端自适应编排管道
- `tasks.py` - 任务合约、工作单元、执行合约
- `work_graph.py` - 持久化工作图、可执行节点调度
- `topology.py` - 执行拓扑助手

**协作形态：**
- `solo` - 单智能体执行
- `team` - 多智能体协作
- `team_with_adversarial_review` - 带对抗性审查的团队
- `cluster` - 集群模式

### 第三层：Provider / Runtime 层

**职责：** 决定"具体由谁执行，以及怎样把执行过程跑起来并记录下来"

**核心模块：**
- `command.py` - 命令执行、Claude/Codex 适配器
- `adapters.py` - 适配器接口和确定性 MVP 实现
- `jobs.py` - 持久化作业生命周期模型
- `control_plane_runtime.py` - 运行时事件流、提供者会话快照

**运行时模式：**
- `cli_inherit` - 使用本地 Claude/Codex CLI 行为
- `cli_isolated` - 使用仓库拥有的运行时主目录
- `direct_api` - 直接 API 就绪检查（低副作用治理角色）

---

## 关键设计模式

### 1. 状态机模式

**文件：** `state_machine.py`

```python
# 任务状态流转
PENDING → READY → RUNNING → COMPLETED/FAILED
```

**应用场景：**
- 计划会话状态管理
- 任务执行状态追踪
- 工作单元生命周期

### 2. 策略模式

**文件：** `policies.py`, `routing.py`

**策略类型：**
- `success_first` - 成功优先（默认）
- `speed_first` - 速度优先
- `cost_first` - 成本优先
- `auto` - 自动选择

**路由决策：**
```python
routing_decision = router.route(requirement)
policy = get_policy(routing_decision.mode)
```

### 3. 适配器模式

**文件：** `adapters.py`, `command.py`

**适配器接口：**
- `PlannerAdapter` - 计划适配器
- `DecomposerAdapter` - 分解适配器
- `WorkerAdapter` - 工作器适配器
- `ReviewRescueAdapter` - 审查救援适配器

**实现：**
- `MockClaudePlanner` - 模拟 Claude 计划
- `ClaudeCodeAdapter` - Claude Code CLI 适配
- `CodexCliAdapter` - Codex CLI 适配

### 4. 事件溯源模式

**文件：** `events.py`, `observability.py`

```python
# 事件存储
EventStore → 事件日志 → 状态重建
```

**应用场景：**
- 编排运行事件追踪
- 状态变更审计
- 恢复时间线构建

### 5. 门禁模式

**文件：** `guards.py`, `control_plane_approvals.py`

**门禁类型：**
- 执行门禁 - 验证执行合约
- 制品写入门禁 - 验证制品写入权限
- 角色状态门禁 - 验证角色操作权限

**审批流程：**
```python
ApprovalItem → ApprovalStore → resolve_approval_item()
```

---

## 核心数据流

### 1. 工作空间状态流

```
WorkspaceState → ContextPacket → StrategyDecision → ExecutionTopologySnapshot
→ ApprovalItem → EvidenceBundle → MemoryRecord
```

### 2. 计划会话流

```
用户需求 → PlanSession → RoundController → GapClosure 
→ ApprovedPlan → ExecutionContract → 执行
```

### 3. 执行流

```
TaskContract → WorkUnit → AgentJob → CommandResult 
→ ExecutionProof → EvidenceBundle
```

---

## 关键制品 (Artifacts)

### 1. 上下文包 (ContextPacket)

**作用：** 压缩任务上下文，供智能体工作

**包含：**
- 文档上下文快照
- 会话指导命令
- 合规状态
- 工作空间状态

### 2. 执行拓扑快照 (ExecutionTopologySnapshot)

**作用：** 只读执行拓扑

**包含：**
- 任务池
- 角色合约
- 工作器交接
- 运行时/作业表面

### 3. 证据束 (EvidenceBundle)

**作用：** 真实任务度量、恢复覆盖、运行时保真度

**包含：**
- 真实任务指标
- 合规阻塞
- 恢复准备
- 运行时测量增量

### 4. 内存记录 (MemoryRecord)

**作用：** 内存溯源、新鲜度、置信度

**包含：**
- 内存提升
- 外部缓存状态
- 置信度评分

---

## 治理与合规

### 1. 合规检查

**命令：** `team check-compliance`

**检查项：**
- 必需文档存在性
- 工作流文档引用
- 操作手册信号
- 执行来源匹配
- 上下文快照存在性
- 交接包存在性
- 源文件头合约
- 过程文档同步

### 2. 证据门禁

**命令：** `team evidence-gates`

**门禁类型：**
- 准备门禁 - 证据支持的发布决策
- 运行时健康门禁
- 工具清单门禁

### 3. 治理束

**命令：** `team governance-bundle`

**功能：**
- 导出治理束
- 检查治理束
- 可移植治理导出

---

## CLI 接口设计

### 主要命令

```bash
# 健康检查
PYTHONPATH=src python -m agent_orchestrator.cli health

# 团队设置
PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json

# 工作空间状态
PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json

# 证据门禁
PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json

# 开始会话
PYTHONPATH=src python -m agent_orchestrator.cli team start "Build a persisted plan artifact"

# 检查合规
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
```

### 会话管理命令

```bash
# 查看摘要
team summary <session-id>

# 下一步
team next <session-id>

# 草稿就绪
team draft-ready <session-id>

# 提交审查
team submit-review <session-id>

# 批准
team approve <session-id>

# 执行
team execute <session-id>

# 检查执行
team inspect-execution <session-id>
```

---

## UI 架构

### 操作员控制台

**技术栈：** FastAPI + Uvicorn

**功能：**
- 会话管理
- 治理信号
- 执行溯源
- 运行时/作业状态
- 证据支持的准备

**模块：**
- `ui_server.py` - FastAPI 应用
- `ui_service.py` - 服务助手

---

## 测试策略

### 测试文件

- `test_orchestrator.py` - 编排器测试
- `test_planning.py` - 计划测试
- `test_control_plane.py` - 控制平面测试
- `test_cli.py` - CLI 测试
- `test_evidence.py` - 证据测试
- `test_jobs.py` - 作业测试

### 测试类型

1. **单元测试** - 单个模块功能
2. **集成测试** - 模块间交互
3. **CLI 测试** - 命令行接口

---

## 代码组织

### 源码结构

```
src/agent_orchestrator/
├── __init__.py              # 包初始化，导出核心类
├── orchestrator.py          # 端到端编排管道
├── planning.py              # 计划会话管理
├── planning_support.py      # 合规检查、会话指导
├── control_plane.py         # 控制平面制品构建
├── control_plane_*.py       # 控制平面子模块
├── adapters.py              # 适配器接口
├── command.py               # 命令执行、CLI 适配
├── jobs.py                  # 作业生命周期
├── tasks.py                 # 任务合约
├── work_graph.py            # 工作图
├── guards.py                # 权限守卫
├── evidence.py              # 证据管理
├── memory.py                # 内存管理
├── events.py                # 事件存储
├── policies.py              # 策略配置
├── routing.py               # 路由决策
├── cli.py                   # CLI 主入口
├── cli_team.py              # 团队命令
├── cli_evidence.py          # 证据命令
├── cli_jobs.py              # 作业命令
├── ui_server.py             # UI 服务器
└── ui_service.py            # UI 服务
```

---

## 关键设计决策

### 1. 状态与模型分离

**决策：** 将工作空间状态、上下文、审批、证据和恢复状态与模型解耦

**原因：**
- 可检查性 - 人类可以审查所有状态
- 可恢复性 - 系统可以从任意点恢复
- 可审计性 - 所有操作都有记录

### 2. 显式编排

**决策：** 采用显式编排而不是隐式编排

**原因：**
- 透明性 - 每一步都可见
- 可控性 - 人类可以在任何点介入
- 可预测性 - 状态流转是确定的

### 3. 治理优先

**决策：** 将治理作为核心功能而不是附加功能

**原因：**
- 合规性 - 满足企业级要求
- 安全性 - 防止未授权操作
- 可追溯性 - 所有操作都有记录

### 4. 可插拔架构

**决策：** 采用可插拔的执行拓扑和 Provider/Runtime

**原因：**
- 灵活性 - 可以根据需求选择不同配置
- 可扩展性 - 可以轻松添加新的 Provider
- 可维护性 - 模块化设计易于维护

---

## 技术亮点

### 1. 上下文压缩

**实现：** `planning_support.py` 中的 `build_document_context_package`

**功能：** 将文档、变更、记忆、风险压缩成最小充分上下文

### 2. 对抗性审查

**实现：** `planning.py` 中的审查流程

**功能：** Lead 与 adversarial reviewer 围绕同一计划质疑和补全

### 3. 恢复时间线

**实现：** `control_plane_recovery.py`

**功能：** 构建恢复时间线和恢复建议

### 4. 运行时测量

**实现：** `control_plane_runtime.py`

**功能：** 追踪命令开始/结束时间、持续时间、退出码、提供者/运行时元数据

---

## 面试准备要点

### 项目描述（简历用）

> **AI-Work-Control-Plane** - 本地优先的 AI 工作控制平面
>
> - 设计并实现 AI 工作控制平面架构，将工作流状态与模型解耦，支持可检查、可恢复、可审计的工作管理
> - 构建显式编排引擎，实现规划-审查-审批-执行的完整工作流状态机
> - 开发策略路由系统，支持 success_first、speed_first、cost_first 和 auto 四种策略模式
> - 实现本地命令运行时，支持命令执行、持续时间测量、退出状态和元数据追踪
> - 构建合规检查、证据门禁、运行时监控等完整治理框架

### 技术关键词

- **架构设计** - 三层分离架构、控制平面、状态机
- **设计模式** - 状态机、策略、适配器、事件溯源、门禁
- **工程实践** - 测试驱动开发、CI/CD、版本管理、文档即代码
- **技术栈** - Python、FastAPI、Pytest、状态管理

### 常见面试问题

1. **为什么选择三层分离架构？**
   - 关注点分离 - 决策、协作、执行独立演进
   - 可维护性 - 每层可以独立测试和替换
   - 可扩展性 - 可以轻松添加新的协作形态或 Provider

2. **如何实现状态管理？**
   - 状态机模式 - 明确的状态流转
   - 事件溯源 - 完整的状态变更历史
   - 持久化存储 - 支持恢复和审计

3. **如何保证系统安全？**
   - 门禁机制 - 执行前验证
   - 权限守卫 - 角色级权限控制
   - 审计日志 - 完整的操作记录

4. **如何处理失败？**
   - 失败路由 - 自动重新路由
   - 救援适配器 - 自动救援失败任务
   - 恢复时间线 - 支持从任意点恢复

---

## 总结

这个项目展示了：

1. **架构设计能力** - 清晰的三层分离架构
2. **工程实践能力** - 完整的测试、文档、CI/CD
3. **系统思维能力** - 考虑治理、合规、审计
4. **AI 辅助开发能力** - 与 AI 协作完成复杂系统

这是一个很好的全栈项目，涵盖了架构设计、系统开发、测试、文档等多个方面。
