# AI Work Control Plane

面向长周期本地 coding agent 的可靠性控制平面。

## 定位

- 内部默认工作流以 native coding agent 为主执行路径，但状态、证据、审批、记忆和恢复仍然应该留在模型之外。
- 当前仓库按主计划驱动，不再把每次实现包装成新的独立小计划。
- 长周期主执行计划要求验证通过后自动进入下一段，普通进展汇报不构成停点。

## 常用命令

- `python -m agent_orchestrator.cli health`
- `python -m agent_orchestrator.cli install-hooks`
- `python -m agent_orchestrator.cli team check-compliance`
- `python -m agent_orchestrator.cli team workspace-status`

## 关键文档

- `docs/process/长周期主执行计划.md`
- `docs/process/agent-team-operator-runbook.md`
- `docs/process/agent-orchestrator-implementation-process.md`
- `docs/decisions/`

## 说明

- `install-hooks` 用于接入 hook-based compliance checks。
- `team check-compliance` 是 canonical docs / changed-file / hook gate 的统一入口。
