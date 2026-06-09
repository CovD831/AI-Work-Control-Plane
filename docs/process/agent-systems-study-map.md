# Agent 项目学习地图

## 用途

这份文档是为了让你快速抓住这个仓库里最值得拿去面试讲的部分。

不要试图一次把整个仓库全背下来。你只需要围绕一个更窄的问题来学习：

**这个项目到底是怎么让一个 coding agent 变得更可恢复、更可检查、更可治理的？**

## 真正需要吃透的 5 个模块

### 1. 控制平面制品构建器

文件：
- [control_plane.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/control_plane.py)

重点理解：
- workspace state 是怎么组装出来的
- context packet 是怎么从文档和 memory 构建出来的
- strategy、topology、approval、evidence、memory 为什么要拆开

为什么重要：
- 这里是“agent 状态外部化”这条主线的核心

### 2. Team planning governance

文件：
- [planning.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/planning.py)
- [cli_team.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/cli_team.py)

重点理解：
- `PlanSession` 里到底包含什么
- 一个 session 是怎么从 draft 走到 review、approval、execution 的
- human approval 在哪一步进入系统

为什么重要：
- 这是执行层之上的治理式 planning 层

### 3. 执行编排层

文件：
- [orchestrator.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/orchestrator.py)

重点理解：
- run 是怎么异步启动的
- 为什么要有 routing、reroute 和 resume
- job id 和 attempt 是怎么被追踪的

为什么重要：
- 这里体现的是 “agent runtime control”，而不只是 artifact 打包

### 4. 运行时遥测与恢复

文件：
- [control_plane_runtime.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/control_plane_runtime.py)
- [control_plane_recovery.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/control_plane_recovery.py)

重点理解：
- runtime event stream 记录了什么
- provider session snapshot 里有什么
- recovery recommendation 是怎么生成的

为什么重要：
- 这是你投 agent 岗时最有技术辨识度的部分

### 5. 面向 operator 的产品表面

文件：
- [cli.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/cli.py)
- [ui_service.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/ui_service.py)

重点理解：
- 主要 operator command 分别是什么
- UI payload 是怎么从持久化 store 里拼出来的

为什么重要：
- 这能证明项目是可用系统，而不只是后端抽象

## 最先演示的 3 条命令

```bash
PYTHONPATH=src python -m agent_orchestrator.cli team start "创建一个带恢复能力的实现计划"
PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
```

然后再展示：

```bash
PYTHONPATH=src python -m agent_orchestrator.cli team execute <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team inspect-execution <session-id>
```

## 你应该能讲出来的主线

建议按这个顺序讲：

1. 问题不是“怎么造更多 agent”，而是“怎么让 coding agent 在长任务上安全地跑起来”。
2. 我把关键状态从模型内部挪到了稳定制品里。
3. 我加入了 approval、evidence 和 runtime telemetry，让系统可审计。
4. 我加入了 recovery surface，让任务被打断后可以继续，而不是靠猜。
5. 我把整套能力通过 CLI/UI 暴露出来，并用测试兜底。

## 你应该练熟的 5 个问题

至少把这几个问题练到不看稿也能回答：

1. 为什么 `ContextPacket` 要和 `StrategyDecision` 分开？
2. 支撑可恢复性的最小 artifact chain 是什么？
3. runtime event stream 比普通日志多记录了什么？
4. 系统在什么情况下必须要求 human approval？
5. 现在仓库里哪些是 mock，哪些是真实的 provider/runtime 能力？

## 需要诚实承认的边界

如果面试官问到，建议明确说明：

- 这个项目是 local-first、operator-centric 的
- 一些 provider integration surface 目前是有意保持轻量或 mock 的
- 当前最完整的成果主要集中在 governance、persistence、evidence 和 recovery
- 它更适合被表述成 agent reliability infrastructure，而不是通用 autonomous agent platform

## 快速自学顺序

建议按这个顺序补细节：

1. 读 `README.md`
2. 读 `docs/decisions/0004-ai-work-control-plane-reframe.md`
3. 读 `src/agent_orchestrator/control_plane.py`
4. 读 `src/agent_orchestrator/orchestrator.py`
5. 读 `src/agent_orchestrator/control_plane_runtime.py`
6. 跑 `pytest -q`
7. 跑一条 CLI happy path，然后检查生成的 artifact

## 面试目标

你不需要把自己讲成“发明了所有 agent infrastructure 的人”。

你需要让人感觉你是这样的人：

- 发现了 agent workflow 里的真实可靠性问题
- 围绕这个问题设计了清晰的 artifact boundary
- 实现了持久化控制表面
- 能诚实讲清楚设计取舍和当前边界
