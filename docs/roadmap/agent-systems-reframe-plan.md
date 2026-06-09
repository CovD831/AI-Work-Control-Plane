# Agent 项目重构方案

## 目标

把 `AI-Work-Control-Plane` 从一个偏宽泛的“control plane”概念，收拢成一个更适合申请实习的**agent systems 核心项目**。

目标表述是：

> 我做了一个本地优先的 coding agent 可靠性控制平面，让长周期 agent 工作具备可恢复、可检查、可审计的外部治理能力。

## 为什么这个重构方向成立

这个仓库其实已经具备不少真实的 agent system 要素：

- 持久化的 plan session 和 execution run
- provider/runtime 抽象层
- approval 和 evidence gate
- recovery timeline 和 runtime event stream
- 带 provenance 的 memory record
- CLI 和 UI operator surface
- 较完整的自动化测试

相比一个泛化的“multi-agent framework”故事，这套叙事更强，因为它强调的是 agent 的运行可靠性，而不是角色扮演式编排。

## 新的产品中心

这个项目应该对外表现为在解决一个更具体的问题：

**问题：** coding agent 很擅长短任务，但一旦任务变长、多阶段、可中断，状态、审批、恢复和溯源信息往往都被困在临时模型会话里，系统本身无法接管。

**方案：** 把关键控制回路外部化成稳定制品：

```text
WorkspaceState
  -> ContextPacket
  -> StrategyDecision
  -> ExecutionTopologySnapshot
  -> ApprovalItem
  -> EvidenceBundle
  -> MemoryRecord
```

## 简历里最强的几个角度

建议主打这 5 个点：

1. **Agent 状态外部化**
   系统把 plan、runtime、approval、evidence、memory 等关键制品持久化到模型之外。

2. **恢复与可续跑**
   任务被打断后，系统可以根据 workspace、runtime 和 recommendation 制品继续恢复，而不是从头重来。

3. **受治理的执行流程**
   agent 执行不是直接裸跑，而是经过 plan approval、compliance 检查和 evidence readiness 门禁。

4. **Agent run 的可观测性**
   runtime event stream、operation receipt 和 provider session snapshot 让执行过程可追踪、可解释。

5. **面向 operator 的产品表面**
   这不只是后端逻辑，还包含真实可用的 CLI 与 UI 工作流。

## 面试里不要先强调什么

这些内容不要放在最前面讲：

- 没有实例支撑的抽象 `control plane` 术语
- 过多强调 org chart 风格的 multi-agent 角色设计
- 还没有完全落地的 provider bridge 愿景
- 文档很多，但没有聚焦单一 agent workflow 的深度

## 应该优先强调什么

建议你一上来就讲一条完整链路：

1. 为一个 coding task 创建受治理的 plan
2. 在执行前检查上下文和风险
3. 在已批准路径上执行
4. 记录运行时证据和失败状态
5. 在中断后安全恢复

这种讲法比概念型介绍更容易让面试官记住。

## 当前最值得补的缺口

这个仓库已经不空了，但如果要变成真正强的核心项目，还应该补这些：

1. **黄金 demo**
   需要一条打磨好的单场景流程，覆盖 `start`、`approve`、`execute`、`fail/interrupted`、`resume`。

2. **单一北极星评估**
   增加一个聚焦恢复成功率、审批阻塞准确性、evidence 完整度的评估切片。

3. **清晰的 runtime 边界说明**
   明确哪些是 mock、哪些是 provider-backed、哪些指标已经真实测量。

4. **适合面试展示的图**
   至少补 1 张架构图和 1 张 operator workflow 图。

5. **实现层面的掌控深度**
   作者需要能脱离稿子，独立讲清楚 5 个核心模块。

## 四周升级计划

### 第 1 周：收紧叙事

- 更新 README，把主叙事收紧到“agent reliability control plane”
- 增加一张 artifact flow 和 runtime boundary 架构图
- 减少过于概念化、操作感不强的术语

### 第 2 周：做一条标准 demo

- 在 `docs/process/` 下创建一个可复现的 demo 任务
- 记录预期 CLI 命令和关键输出
- 确保 demo 覆盖 workspace index、approval queue、evidence gate 和 runtime inspect

### 第 3 周：补可量化的 agent 评估

- 定义 resume readiness rate、approval-block precision、evidence completeness 等指标
- 加一个窄一点的测试或报告命令，基于 fixture 或 sample run 计算这些指标

### 第 4 周：完善面试包装

- 写一版简洁的项目简介
- 准备 3 个可以从代码展开讲的深挖模块
- 记录中断恢复和治理决策的前后对比示例

## 建议的简历表述

你后面可以把它写成：

> 搭建了一个本地优先的 coding agent 可靠性控制平面，将 agent 状态、审批、证据、运行时遥测与恢复能力外部化为可审计制品，并提供 CLI/UI operator workflow 与 424 个自动化测试来支撑长周期任务的治理与续跑。

## 判断这次重构是否成功

如果满足下面几点，就说明方向对了：

- 一个不熟悉仓库的人能在 1 分钟内复述出这是个 agent systems 项目
- 你在面试前两分钟讲的是具体工作流，而不是抽象概念
- 你能现场演示中断恢复，而不需要手动翻原始 JSON
- 这个项目给人的感觉更像“agent reliability infrastructure”，而不是“还没收束的 multi-agent framework”
