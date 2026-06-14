# AI-Work-Control-Plane

AI-Work-Control-Plane 是一个**面向长周期本地 coding agent 的可靠性控制平面**。它把计划、上下文、执行拓扑、审批、证据、记忆溯源、运行时测量和恢复状态放在模型之外，让多步 agent 工作可以被检查、恢复和审计。

当前状态：**`v1.0.0` 本地优先 AI Work Control Plane 正式版本已封版**。

当前工作流目标：**作为作者自身长周期 agent 工作的内部默认工作流**。

## 先读什么

如果你想最快跟上当前仓库的当前状态，建议只看这组“当前有效”的入口：

1. [Project Index](docs/process/project-index.md)
2. [README.md](README.md)
3. [Root Map](docs/process/root-map.md)
4. [Context Map](docs/process/context-map.md)
5. [Module Manifest](docs/process/module-manifest.md)
6. [Agent Orchestrator Implementation Process](docs/process/agent-orchestrator-implementation-process.md)
7. [Agent Team Operator Runbook](docs/process/agent-team-operator-runbook.md)

下面这些是补充阅读，不再作为第一优先级入口：

- [docs/process/ai-work-control-plane-master-plan.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/ai-work-control-plane-master-plan.md)
- [docs/process/agent-evolution-master-plan.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/agent-evolution-master-plan.md)
- [PROJECT_BREAKDOWN.md](/Users/abab/Desktop/AI-Work-Control-Plane/PROJECT_BREAKDOWN.md)
- [PROJECT_BREAKDOWN_V2.md](/Users/abab/Desktop/AI-Work-Control-Plane/PROJECT_BREAKDOWN_V2.md)
- [EXECUTION_PLANE_DEEP_DIVE.md](/Users/abab/Desktop/AI-Work-Control-Plane/EXECUTION_PLANE_DEEP_DIVE.md)
- [INTERVIEW_PREP.md](/Users/abab/Desktop/AI-Work-Control-Plane/INTERVIEW_PREP.md)

历史叙事和阶段材料请优先当作“演化记录”而不是当前产品定义来读。

## 为什么这是一个 Agent 项目

这个仓库更准确的理解方式是一个**agent systems 项目**，而不是一个泛化的工作流壳子：

- 它处理的是长周期 agent 工作的治理问题，而不是一次性 prompt 调用。
- 它把**控制平面职责**和 provider/runtime 执行职责拆开，让 agent 行为可检查。
- 它把**恢复、审批、证据、记忆溯源**当成一等系统能力，而不是附属日志。
- 它通过稳定的 CLI 和 UI surface 对外暴露这些能力，并且背后有测试覆盖的 artifact schema。

如果要用一句最短的话来描述它，可以说：

> 这是一个本地优先的 agent 外部治理层，用来让长任务 coding agent 具备可恢复、可审计、可安全操作的工作系统。

这个仓库并不试图成为 provider 原生桥接层、持久 provider session 持有者、tmux 替代品，也不试图和 `Codex` / `Claude Code` 竞争“谁更会规划和写代码”。它的产品核心，是这些 runtime 之上的外部治理层。

随着模型能力增强，显式编排本身未来可能会变得不那么重要；但状态、证据、审批、记忆和恢复仍然应该留在模型之外，作为可审计的系统职责。也就是说，**session 可以属于 provider，program state 应该属于 control plane**。

## 文档分层

为了减少叙事重叠，这个仓库现在把文档分成三层：

1. **Canonical**: 当前有效、应优先遵循的文档。
2. **Supplementary**: 对现状有帮助，但不是第一阅读顺序的材料。
3. **Historical**: 阶段报告、讲解稿、面试稿、旧叙事和演化记录。

如果某份文档和 README、Project Index、Context Map 的说法冲突，优先以这三份入口和实现代码为准。

## 它具体做什么

- 维护跨 session、跨阶段的 workspace / program state，而不是只依赖单次 agent 会话。
- 记录 approval、evidence、runtime measurement、operation receipt 和 recovery artifact。
- 为长任务执行提供外部 checkpoint、阻塞原因和恢复建议。
- 支持本地 command runtime job，并记录 provider/runtime 元数据与真实执行事实。
- 通过 setup、compliance、evidence、workspace 和 gate surface 报告治理状态与发布准备度。

## 推荐演示叙事

如果要用于面试或作品集展示，建议按这个顺序讲：

1. `team start` 为一个模糊工程任务创建受治理的任务上下文和外部状态。
2. `team workspace-status` 展示外部化后的 workspace 状态和恢复状态。
3. `team evidence-gates` 展示当前是否满足安全推进条件。
4. `team execute` 在已批准路径上执行任务，并持久化运行时事实和溯源信息。
5. `team runtime inspect` 或 UI 展示执行结果，以及系统如何给出恢复建议。

配套文档：

- [Agent 项目重构方案](docs/roadmap/agent-systems-reframe-plan.md)
- [Agent 项目学习地图](docs/process/agent-systems-study-map.md)
- [Provider 边界审计清单](docs/process/provider-boundary-audit.md)

## 当前 v1 边界

当前版本的定位是**测量能力已就绪**，而不是 provider bridge 已就绪。

只要本地事实存在，runtime measurement 就会记录：

- command 开始/结束时间戳
- duration
- exit code
- provider 和 runtime mode
- provider 可用性
- degraded reason
- operation receipt

除非某个 runtime 能直接提供可信的 token 和 cost 数据，否则这两个字段目前仍然是占位符。这是有意为之，并不是当前 v1 路线的阻塞项。

## 快速开始

在仓库根目录运行：

```bash
cd /Users/abab/Desktop/AI-Work-Control-Plane
PYTHONPATH=src python -m agent_orchestrator.cli health
PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json
PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
```

启动并检查一个受治理的工作会话：

```bash
PYTHONPATH=src python -m agent_orchestrator.cli team start "Build a persisted plan artifact for a routine implementation task"
PYTHONPATH=src python -m agent_orchestrator.cli team summary <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team next <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team draft-ready <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team submit-review <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team approve <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team execute <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team inspect-execution <session-id>
```

通过策略路由器直接运行一个任务：

```bash
PYTHONPATH=src python -m agent_orchestrator.cli run "Review this workspace and report the next hardening step" --mode auto
```

## 发布检查

在确认版本可发布之前，运行：

```bash
pytest
PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
PYTHONPATH=src python -m agent_orchestrator.cli team governance-bundle export --output .agent_orchestrator/governance/v1.0.0-final-bundle.json --query "v1.0.0 final release seal" --format json
PYTHONPATH=src python -m agent_orchestrator.cli team governance-bundle inspect .agent_orchestrator/governance/v1.0.0-final-bundle.json --format json
```

当前发布检查清单见 [docs/process/v1-candidate-release-checklist.md](docs/process/v1-candidate-release-checklist.md)。更短的标准化准备流程见 [docs/process/v1x-release-readiness.md](docs/process/v1x-release-readiness.md)。

发布封版相关文档：

- [v1.0.0 release notes](docs/releases/v1.0.0.md)
- [v1.0.0 evidence packet](docs/process/v1.0.0-evidence-packet.md)
- [v1.0.0-rc.3 release notes](docs/releases/v1.0.0-rc.3.md)

## 产品分层

项目当前分为以下几层：

- **治理层**：workspace state、approval、evidence、memory provenance、recovery 和 execution contract。
- **执行事实层**：runtime measurement、operation receipt、provider session snapshot、run ledger 和 failure / fallback facts。
- **Provider / Runtime 层**：本地 command runtime、CLI 继承/隔离模式、direct API readiness check，以及未来可替换的 adapter。

中文说明入口：

- [决策核心 / 执行拓扑 / 运行时分层说明](docs/architecture/决策核心-执行拓扑-运行时分层说明.md)
- [上下文地图](docs/process/context-map.md)
- [项目索引](docs/process/project-index.md)
- [Native Coding Agent Main Path](docs/process/native-coding-agent-main-path.md)
- [长周期主执行计划](docs/process/长周期主执行计划.md)
- [操作手册](docs/process/agent-team-operator-runbook.md)
- [架构决策记录](docs/decisions/)

默认执行节奏：按长周期主计划推进，验证通过后自动进入下一段。

## 主要 CLI 入口

- `team setup`：检查 provider health、runtime measurement readiness、doc sync、compliance 和发布准备度。
- `team workspace-status`：查看 workspace snapshot 和 control-plane state。
- `team context-packet`：为 agent 工作生成压缩后的任务上下文。
- `team topology inspect`：查看只读执行路径快照。
- `team approvals list` / `team approvals resolve`：查看和处理 approval queue。
- `team evidence-gates`：查看基于 evidence 的发布门禁。
- `team runtime inspect <job-id>`：查看 runtime measurement、operation receipt 和 degraded runtime 细节。
- `evidence report` / `evidence trend`：输出 evidence metric、runtime measurement metric 及其变化趋势。

## Provider Runtime 模式

- `cli_inherit`：沿用本地 `codex` / `claude` CLI 行为，包括用户鉴权和项目/全局配置。
- `cli_isolated`：在仓库自有的 `.agent_orchestrator/runtime-homes/` 下运行隔离的 CLI job。
- `direct_api`：为 planning、review、summarization 这类低副作用治理角色报告脱敏后的 API readiness。

`team setup` 和 `health --refresh` 会报告本地 readiness，但不会存储 API key。

## Evidence

用下面的命令刷新 evidence report：

```bash
PYTHONPATH=src python -m agent_orchestrator.cli evidence report \
  --case-file docs/process/evidence-cases.json \
  --output docs/process/v1x-evidence-report.md \
  --json-output .agent_orchestrator/evidence/real-tasks.json
```

evidence report 会覆盖真实任务 dogfood 指标、recovery coverage、runtime fidelity、compliance blocking、postmortem readiness 和 runtime measurement 变化。cost 和 token 数值在 provider/runtime 直接上报之前仍然保持占位。

## UI

启动本地治理控制台：

```bash
PYTHONPATH=src python -m agent_orchestrator.cli ui
```

这个治理控制台面向本地 operator，用于查看 session、governance signal、execution provenance、runtime/job state 以及 evidence-backed readiness。

## 开发

快速检查可运行：

```bash
make ci
```

在最终收尾阶段运行：

```bash
pytest
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
```

本地等价于 CI 的门禁会运行 `ruff check src tests` 和 `pytest -m "not slow_integration"`。也可以单独运行：

```bash
make lint
make test-quick
make ui-build
```

安装仓库自带的 hook：

```bash
PYTHONPATH=src python -m agent_orchestrator.cli install-hooks
```
