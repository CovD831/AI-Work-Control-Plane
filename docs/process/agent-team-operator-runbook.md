# Agent Team Operator Runbook

## 目的

这份文档只回答一个问题：

> 当你准备让 `agent team` 持续推进主计划时，下一步应该运行什么标准命令。

它面向 operator，而不是面向底层实现。

默认原则：

- 优先通过 `team` 命令继续推进
- 优先看 `team summary`、`team next`、`team runbook`
- 不要直接编辑底层 JSON
- 先看 decision core 的裁决，再看执行层细节

## Happy Path

标准 happy path：

1. `team start`
2. `team status`
3. `team next`
4. `team revise`
5. `team approve`
6. `team execute`

推荐用法：

```bash
python -m agent_orchestrator.cli team start "Build a persisted plan artifact"
python -m agent_orchestrator.cli team summary <session_id>
python -m agent_orchestrator.cli team next <session_id>
python -m agent_orchestrator.cli team runbook <session_id>
```

判断标准：

- 只看标准命令输出，就知道当前状态和下一步动作
- `team next` 给出下一条建议命令
- `team runbook` 给出当前状态下的操作步骤
- 输出里能看到 `selected_topology` 和决策理由摘要
- `summary`、`next`、`runbook` 输出里能看到 `topology_reason`
- 当 preferred reviewer 不可用时，decision verdict 会记录 provider fallback
- provider fallback 输出应包含 `fallback_reason` 和 `fallback_detail`
- direct `run` 的 summary 现在也会展示 `route_source` 和 execution contract 摘要

## 状态解释

### `needs_revision`

表示当前 session 还不能直接 approve。

操作顺序：

1. 用 `team summary` 看 required gap 和 optional follow-up。
2. 用 `team revise` 关闭 required gaps。
3. 再跑一次 `team next` 或 `team runbook`。
4. 只有在 required gaps 都关闭后，才运行 `team approve`。

### `approved_for_execution`

表示 planning governance 已经允许 execution。

操作顺序：

1. 用 `team execute` 启动执行。
2. 如需确认状态，先看 `team status` 或 `team summary`。
3. 如需 deeper provenance，再去看 linked execution run。
4. 执行默认从 approved plan 起跑，而不是从 raw requirement 重新起跑。

### `awaiting_human`

表示当前问题已触碰主计划边界、架构方向或阶段切换，不能再默认自治推进。

操作顺序：

1. 停止自动推进。
2. 用 `team summary` 整理阻塞原因。
3. 等待人类确认方向后再恢复。

## 委派失败恢复

如果 review 或 adversarial review 的 delegated job 失败，先不要翻底层存储。

标准恢复入口：

- `team summary`
- `team next`
- `team runbook`
- `team retry-review`
- `team retry-adversarial-review`
- `team resume`

推荐顺序：

1. 先看 `team summary`。
2. 再看 `team next`，确认推荐恢复命令。
3. 再看 `team runbook`，确认是临时故障还是计划本身要修。
4. 如果是临时失败，用 `retry-review` 或 `retry-adversarial-review`。
5. 如果失败暴露的是计划缺口，回到 `team revise`。

## 标准验收场景

### 场景 A

目标：

- session 进入 `needs_revision`
- 关闭 required gaps
- 然后 `approve`
- 然后 `execute`

最小验收：

- 不打开底层文件，也知道何时 revise、何时 approve、何时 execute

### 场景 B

目标：

- review 或 adversarial review 委派失败
- 通过 `summary/next/runbook/retry/resume` 完成恢复

最小验收：

- 不手翻 jobs/plans store，也知道下一步恢复动作

### 场景 C

目标：

- approved plan 驱动 execution
- run artifact 能追溯来源 session
- run artifact 能追溯 selected topology 和 selected provider/runtime

最小验收：

- 可以通过 session 和 linked run 判断执行从哪个 approved plan 来
- 可以通过 `team next`/`team runbook` 理解当前决策核心推荐的执行拓扑

## 日常操作建议

- 每次新任务先从 `team start` 开始，不要跳过 planning session。
- 每次准备继续时先看 `team summary` 或 `team next`。
- 每次状态不清楚时优先跑 `team runbook`。
- 每次 delegated job 失败时优先走标准命令恢复，不要直接编辑底层 JSON。
- 每次 happy path 验证通过后，再推进主计划的下一实现段。
