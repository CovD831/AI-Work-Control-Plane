# AI Work Control Plane Reference Rescreen

调研日期：2026-05-27

本地来源：

- `research_repos/HiveWard` at `2194e0d`
- `research_repos/wanman` at `e351f89`
- `research_repos/slark` at `73e63d2`
- `research_repos/CodeWhale` at `e92702f`
- `research_repos/codex-orchestrator` at `ddc1de4`
- `research_repos/codex-plugin-cc` at `807e03a`
- `research_repos/cc-plugin-codex` at `35728fe`
- `research_repos/eigent` at `e21a999`
- `research_repos/cmux` at `28b0a78`
- `research_repos/multica` at `e351f89`

## Why This Rescreen Exists

项目重心已经从“显式 agent 编排器”上移为 **AI Work Control Plane**。因此参考项目不再按“谁的 agent 编排更多”来筛，而是按它们是否能补强系统外部的长期工作控制面：

```text
PlanSession -> WorkspaceState -> ContextPacket -> StrategyDecision
  -> ExecutionTopologySnapshot -> ApprovalItem -> EvidenceBundle -> MemoryRecord
```

新的判断标准是：谁能帮助本仓库更好地管理状态、上下文、策略、拓扑、审批、证据、记忆和恢复；谁只适合作为下层 runtime / provider / bridge；谁会把产品重新拉回“人类公司组织图”或“tmux 会话管理器”。

## Rescreen Matrix

| Reference | New control-plane value | Borrow now | Keep below the line |
| --- | --- | --- | --- |
| HiveWard | 最接近上层 control-plane 产品形态：company/workspace scope、blueprint、approval inbox、run ledger、history、runtime boundary。 | 借鉴 workspace/program scope、approval inbox、run ledger、blueprint/run-state 语言，以及“真实执行归 runtime，产品层只管理状态和治理”的边界。 | 不急着复制 React Flow / 画布编辑器；不把 Agent Company 人类组织隐喻变成主产品叙事。 |
| wanman | 最适合作为未来 runtime supervisor 参考：JSON-RPC supervisor、message/context/task/artifact store、per-agent worktree、per-agent `$HOME`。 | 借鉴 supervisor boundary、context/task/artifact stores、runtime isolation、artifact quality/naming、lifecycle metadata。 | 24/7 agent matrix 不作为产品核心；CEO/devops/marketing 角色剧场不进入 control plane 顶层。 |
| slark | 最适合作为 workflow/status/knowledge loop 参考：唯一状态源、workflow YAML、approval step、Scribe lessons/decisions、Evaluator/Coach。 | 借鉴唯一状态源、workflow run 状态机、lessons/decisions 晋升为 MemoryRecord 的审批路径、Facilitator -> template 的长期方向。 | 不现在构建完整 Team OS / chat room / workflow marketplace。 |
| CodeWhale | 最适合作为单 agent runtime 体验和恢复语义参考：Plan/Agent/YOLO mode、doctor JSON、session resume/fork、MCP validate、model auto-routing。 | 借鉴 `doctor --json`、session resume/fork 语言、MCP/provider health、model routing 作为 StrategyDecision hint。 | 不把 TUI/API/SDK-first 变成主线；memory 不能替代本仓库有 provenance 的 MemoryRecord。 |
| codex-orchestrator | 最适合作为 JobRuntime observability 参考：tmux jobs、capture/send/attach/watch、jobs JSON、prompt dry-run、CODEBASE_MAP 注入。 | 借鉴 background job status/result/send/capture 形状、token/files/summary metadata、prompt preview、context map 注入。 | 不把 tmux session manager 变成产品核心。 |
| codex-plugin-cc / cc-plugin-codex | 最适合作为 provider bridge grammar 参考：review/adversarial-review/rescue/setup/status/result/cancel。 | 借鉴 read-only review vs mutating rescue、honest setup/degraded capability、background status/result command grammar。 | 不做 provider ping-pong；review gate 必须有成本和循环保护。 |
| Eigent | 最适合作为真实 dogfood case 参考：本地部署、MCP 工具、HITL、报告生成、Slack/外部动作。 | 借鉴端到端 evidence cases、MCP tool inventory、任务卡住或不确定时触发 human-in-the-loop。 | 不追 cloud workforce 平台和通用企业自动化。 |
| cmux / multica | 当前本地 checkout 只有 shallow `.git` 元数据，没有可读 README/源码信号。 | 暂不吸收。 | 需要重新 fetch/clone 后再判断。 |

## Strongest New Lessons

1. **Workspace / Program 必须压过 session。** HiveWard 和 slark 都说明，长期工作不能只围绕一次 chat 或一次 run。Control plane 需要一个稳定的 workspace/program index，能把 active plan、context packet、topology snapshot、approval inbox、evidence bundle、memory records 串起来。

2. **Approval inbox 应成为一等入口。** HiveWard 的 inbox 和 slark 的 approval step 都说明，人工判断点不该只是日志里的状态。`team approvals` 现在应继续稳定；下一步应把 approval item 和 run/work unit/provider job/evidence 明确绑定。

3. **Run ledger 比“agent 是否跑完”更重要。** HiveWard 的 run records、codex-orchestrator 的 jobs JSON、wanman 的 stores 都指向同一个方向：control plane 要记录每个执行节点的输入、输出、状态、证据、成本/用量占位、fallback 和恢复线索。

4. **Runtime boundary 要更硬。** wanman 和 HiveWard 都把真实执行放在 runtime/supervisor 里。对本仓库来说，`cli_inherit`、`cli_isolated`、`direct_api` 都应继续是下层 provider/runtime 能力；`StrategyDecision` 只解释和决策，`executes` 继续是 `False`。

5. **Memory 需要 promotion workflow。** slark 的 Scribe / decisions / lessons 提醒我们：MemoryRecord 不能自动吞 transient status。只有带 provenance 的 durable outcome 才能晋升，最好带 approval 或至少 evidence bundle 引用。

6. **Doctor / health / inventory 要成为 control-plane 输入。** CodeWhale 的 `doctor --json`、MCP validate、codex-orchestrator health、Eigent MCP inventory 都可以汇入 provider/runtime health，而不是散落在 setup 文档里。

## What To Build Next

这次重筛后，下一轮大更新不应是“更多 agent 角色”，而应是 **Control Plane Operations Track**：

1. **Workspace / Program Index v2**
   - 把 PlanSession、WorkspaceState、ContextPacket、StrategyDecision、ExecutionTopologySnapshot、ApprovalItem、EvidenceBundle、MemoryRecord 放入一个可查询索引。
   - CLI/UI 默认从索引读取当前现场，而不是让 operator 在多个命令间拼图。

2. **Approval Inbox + Run Ledger**
   - 让 approval item 显式链接 plan、work unit、provider job、evidence 和 recommended action。
   - 让 run ledger 记录 interrupted、failed、awaiting human、compliance blocking、provider fallback 等恢复语义。

3. **Topology Blueprint Snapshot**
   - 借鉴 HiveWard blueprint 和 slark workflow YAML，但先只做只读 export/snapshot。
   - 节点可以覆盖 implementation、review、rescue、summary、condition、approval、evidence。

4. **Memory Promotion Workflow**
   - 借鉴 slark Scribe：把 evidence-backed decisions/lessons 晋升为 MemoryRecord。
   - 保持 provenance、base commit、source artifacts、approval/evidence refs。

5. **Runtime Health + Tool Inventory**
   - 借鉴 CodeWhale doctor、wanman supervisor stores、Eigent MCP inventory。
   - 把 provider availability、runtime mode、MCP tools、setup/degraded capability、usage/cost placeholder 汇入 StrategyDecision 和 EvidenceBundle。

Operations Track 完成后，下一轮参考吸收应进入 **Live Recovery Track**：继续借鉴 runtime-health honesty、job observability 和 dogfood evidence，但表达为 Recovery Timeline、Runtime Event Stream、Recovery Recommendation、resume hints 和 evidence-backed memory promotion，而不是继续堆叠显式 agent choreography。

## Do Not Absorb

- 不复制完整 Agent Company 人类组织图。
- 不现在做 React Flow 拓扑编辑器。
- 不把 tmux / supervisor / provider bridge 做成产品核心。
- 不让 direct_api 绕过 approved-plan gate。
- 不把 provider-private memory 当作本仓库 MemoryRecord。
- 不让 automatic review gate 形成 Claude/Codex 循环。

## Bottom Line

`research_repos` 在新方向下仍然有价值，但价值分层更清楚：

- HiveWard 给产品层：workspace、blueprint、approval inbox、run ledger、runtime boundary。
- wanman 给 runtime 层：supervisor、stores、isolated worktree/home。
- slark 给知识演化层：workflow state、approval step、lessons/decisions promotion。
- CodeWhale 给单 agent 体验层：doctor、resume/fork、model routing、MCP validation。
- codex-orchestrator 和 plugin repos 给执行/bridge 层：job observability、review/rescue grammar。
- Eigent 给 dogfood evidence：真实多工具任务、HITL、MCP inventory。

因此，项目下一步应继续沿着 `WorkspaceState -> ContextPacket -> StrategyDecision` 往外扩，不回到“显式 agent 编排器越复杂越好”的旧主线。
