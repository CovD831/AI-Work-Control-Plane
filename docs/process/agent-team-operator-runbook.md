# 治理控制台操作手册

## 目的

这份文档只回答一个问题：

> 当你准备让 `agent team` 持续推进主计划时，下一步应该运行什么标准命令。

它面向 operator，而不是面向底层实现。当前项目重心已上移为 **AI Work Control Plane**：`agent team` 仍然重要，但它是 control plane 下方的执行拓扑能力。

默认原则：

- 优先通过 `team` 命令继续推进
- 优先看 `team summary`、`team next`、`team runbook`、`team roles`
- 不要直接编辑底层 JSON
- 先看 decision core 的裁决，再看执行层细节

## Happy Path

标准 happy path：

1. `team start`
2. `team chat`
3. `team draft-ready`
4. `team submit-review`
5. `team revise` 或 `team approve`
6. `team execute`
7. `team inspect-execution`
8. `team task list` / `team task next`

## AI Work Control Plane Entries

AI-native 控制面优先看 artifact，而不是模仿人类组织层级：

- `team workspace-status`：生成 `agent_orchestrator.workspace_state.v1`，并写入 `.agent_orchestrator/workspace/index.json`。
- `team context-packet --query "<task>" --changed-file <path>`：生成 `agent_orchestrator.context_packet.v1`，压缩 docs、memory、changed files 和 stale warnings，但不选择 strategy。
- `team topology inspect <session_id>`：生成只读 `agent_orchestrator.execution_topology_snapshot.v1` 执行路径快照。
- `team approvals list`：查看 `agent_orchestrator.approval_item.v1` 队列。
- `team approvals resolve <approval_id> --status resolved --reason "<why>"`：只记录人类决策，不绕过 execution gate。
- `team evidence-gates`：生成 `agent_orchestrator.evidence_bundle.v1`，汇总 tests、compliance、setup 和 evidence report gate。
- `team summary` / `team next` / `team runbook`：直接展示治理检查点摘要，不需要先打开执行路径快照才知道 control-plane 建议。

Phase 6+ control-plane hardening 增加了以下 operator 约束：

- artifact contract 以 `docs/process/control-plane-artifact-contracts.md` 为准。
- `.agent_orchestrator/workspace/index.json` 记录最近 workspace/context/strategy/topology/evidence artifact 引用。
- approval item 必须带稳定 `reason_code`。
- evidence bundle 只给 memory recommendation，不自动同步 external cache。
- UI 只读消费 control-plane JSON schema，不提供 approval resolve 或 graph edit mutation。

Operations Track 继续把默认 operator 入口上移为控制面现场：

- `.agent_orchestrator/workspace/index.json` 应成为当前 workspace/program、active artifacts、open approvals、recent runs、memory candidates 和 provider/runtime health 的索引。
- `team approvals list` 应按 inbox 理解，显示 pending/resolved/blocking、reason code distribution 和 recommended next command。
- `team topology inspect` 应提供只读执行路径 blueprint snapshot，不提供拓扑编辑。
- `team summary`、`team next`、`team runbook` 应从 run ledger 和 recovery 语义补充下一步，而不是只复述 team 编排状态。
- evidence bundle 可以产生 memory promotion candidates，但不能自动写 durable memory。
- operations dogfood 以 `docs/process/ai-work-control-plane-operations-dogfood-evidence.md` 为当前证据基准。

Live Recovery Track 在此基础上继续推进：operator 不只看到当前状态，还要能看到 Recovery Timeline、Runtime Event Stream、Recovery Recommendation、resume hint 和 last checkpoint。恢复建议仍然是只读控制面输出；真正执行继续由 approved-plan gate 和 runtime 层完成。

Live Recovery dogfood 以 `docs/process/ai-work-control-plane-live-recovery-dogfood-evidence.md` 为当前恢复证据基准，覆盖 awaiting-human / approval、compliance blocking、provider/runtime degraded or fallback 三类场景。

Runtime Bridge Fidelity Track 继续补齐 provider/runtime 会话保真度：

- `team runtime inspect <job_id>` 生成只读 `agent_orchestrator.provider_session_snapshot.v1`。
- `team runtime inspect <job_id>` 同时展示 `runtime_measurement`：本地 command start/end、duration、exit code、provider/runtime mode、degraded reason 和 operation receipts；这只是 measurement，不代表 provider-native bridge。
- runtime operation receipt 使用 `agent_orchestrator.runtime_operation_receipt.v1`，记录 send/cancel/terminal/missing-session/auth/provider-unavailable 等结果。
- Runtime Event Stream 应包含 session liveness、operation receipts、attachability、continuation support、degraded reason 和 recovery-safe next command。
- workspace status、evidence gates 和 UI 只读消费 runtime fidelity 摘要，不拥有 provider 会话，也不绕过 approved-plan gate。

Runtime Bridge dogfood 以 `docs/process/ai-work-control-plane-runtime-bridge-dogfood-evidence.md` 为当前运行时保真度证据基准。

## Responsibility Contracts

`team roles` 是职责契约的标准入口。它不是为了模拟公司组织架构，而是为了说明不同治理职责、执行职责和 artifact 职责分别有哪些 runtime mode、allowed actions、forbidden actions、required outputs、structured inputs、structured outputs、semi-autonomous collaboration capabilities 和 command refs。

当前会看到的职责包括：

- 会话治理：`lead`
- 计划职责：`planner`
- 质量审查：`reviewer`
- 风险挑战：`adversarial_reviewer`
- 执行任务：`builder`
- 执行验证：`validator`
- 恢复处理：`rescue`
- 运行时：`runtime`
- 以及 AI-native artifact 转换职责 `state_keeper`、`context_compressor`、`strategist`、`topology_compiler`、`evidence_recorder`、`memory_curator`、`approval_gate`

- 会话治理 `lead`：`team status`、`team next`、`team inspect-blockers`
- state_keeper: `team workspace-status`
- context_compressor: `team context-packet`、`team inspect-docs`、`team docs-index`
- strategist: `team topology inspect`
- topology_compiler: `team topology inspect`
- evidence_recorder: `team evidence-gates`、`team setup`、`team check-compliance`
- memory_curator: `team inspect-knowledge`、`team context-packet`
- approval_gate: `team approvals list`、`team approvals resolve`
- 计划职责 `planner`：`team start`、`team chat`、`team draft-ready`、`team task next`
- 质量审查 `reviewer`：`team submit-review`、`team retry-review`、`team task list`
- 风险挑战 `adversarial_reviewer`：`team submit-review`、`team retry-adversarial-review`
- 执行任务 `builder`：`team execute`、`team inspect-execution`
- 执行验证 `validator`：`team inspect-execution`、`team task next`
- 恢复处理 `rescue`：`team inspect-blockers`、`team retry-review`、`team retry-adversarial-review`
- 运行时 `runtime`：`team inspect-execution`

阅读原则：

- 先把它看成“职责边界和允许动作说明”，不要先把它看成一套需要拟人化运作的组织架构
- 真正长期稳定的对象仍然是 artifact、gate、evidence、recovery 和 runtime facts

推荐用法：

```bash
python -m agent_orchestrator.cli team start "Build a persisted plan artifact"
python -m agent_orchestrator.cli team chat <session_id> --message "补充约束或确认方向"
python -m agent_orchestrator.cli team draft-ready <session_id>
python -m agent_orchestrator.cli team submit-review <session_id>
python -m agent_orchestrator.cli team summary <session_id>
python -m agent_orchestrator.cli team next <session_id>
python -m agent_orchestrator.cli team runbook <session_id>
python -m agent_orchestrator.cli team workspace-status
python -m agent_orchestrator.cli team context-packet --query "Build a persisted plan artifact"
python -m agent_orchestrator.cli team topology inspect <session_id>
python -m agent_orchestrator.cli team approvals list
python -m agent_orchestrator.cli team evidence-gates
```

收口边界：

- `team roles`、plan tree、Console summary 和 UI 面板都属于 operator projection，不是新的 durable state。
- 如果 `team roles` 和 work-graph 里出现更丰富的结构化字段，应优先把它理解为“解释和检查边界更清楚了”，而不是“系统已经进入高自治多 agent runtime”。
- 真正机器契约优先回看 `docs/process/control-plane-artifact-contracts.md` 中定义的 control-plane artifacts。

判断标准：

- 只看标准命令输出，就知道当前状态和下一步动作
- `team next` 给出下一条建议命令
- `team runbook` 给出当前状态下的操作步骤
- 输出里能看到 `selected_topology` 和决策理由摘要
- `summary`、`next`、`runbook` 输出里能看到 `topology_reason`
- 当 preferred reviewer 不可用时，decision verdict 会记录 provider fallback
- provider fallback 输出应包含 `fallback_reason` 和 `fallback_detail`
- direct `run` 的 summary 现在也会展示 `route_source` 和 execution contract 摘要
- Provider / Runtime 会标明 `cli_inherit`、`cli_isolated` 或 `direct_api`
- `direct_api` 只用于 planning / review / summarization 这类低副作用角色；implementation / rescue 默认仍走 CLI worker
- API key 只通过环境变量读取，setup/health 只展示 masked readiness

## Provider / Runtime 模式

- `cli_inherit`：默认 CLI 模式，继承本机 Codex / Claude Code 登录状态、全局规则、项目规则和 provider 原生命令能力。
- `cli_isolated`：CLI 隔离模式，每个 job 使用 `.agent_orchestrator/runtime-homes/<job-id>/` 作为 HOME，并在 job metadata 中记录 effective home、config source 和 sandbox。
- `direct_api`：API key 模式，只用于单轮治理型任务；没有本地工具循环、不会直接改文件，也不会把 API key 写入 job JSON、日志或 evidence。

推荐策略：

1. 计划、审查、证据总结优先看 `direct_api` 的干净控制面。
2. 真正修改代码的 worker / rescue 优先用 `cli_inherit` 或 `cli_isolated`。
3. 当输出里出现 provider fallback，先看 `fallback_reason` / `fallback_detail`，再决定是否重试或切换 runtime mode。

## 状态解释

### `intake_chat`

表示用户正在和计划主控 Lead 澄清需求。`team start` 只创建首版草案和可读消息，不会自动进入 review。

操作顺序：

1. 用 `team chat` 继续补充约束、边界、偏好。
2. 用 `team summary` 或 Console 查看当前草案。
3. 当第一版计划可以被审查时，运行 `team draft-ready`。

### `draft_ready`

表示用户已经确认第一版计划可以进入审查，但审查尚未开始。

操作顺序：

1. 如需继续补充，回到 `team chat`。
2. 如确认进入下一阶段，运行 `team submit-review`。
3. `submit-review` 会触发 reviewer 和 adversarial reviewer，但不会自动 approve。

### `awaiting_human_confirmation`

表示 review / adversarial review 已完成，系统正在等人类补充或批准。

操作顺序：

1. 用 `team summary` 查看 review findings 和 gaps。
2. 如果 required gaps 存在，用 `team revise` 补充并关闭。
3. 如果 required gaps 已关闭，运行 `team approve`。
4. `team approve` 之后才允许 `team execute`。

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
4. 优先使用 `team inspect-execution` 查看 linked execution run，而不是手动翻 run store。
5. 执行默认从 approved plan 起跑，而不是从 raw requirement 重新起跑。

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
- `team roles`
- `team retry-review`
- `team retry-adversarial-review`
- `team resume`
- `team inspect-blockers`
- `team inspect-docs`
- `team inspect-handoff`
- `team docs-index`
- `team workspace-status`
- `team context-packet`
- `team topology inspect`
- `team approvals list`
- `team approvals resolve`
- `team evidence-gates`
- `team check-compliance`
- `team refresh-docs`
- `team repair-compliance`

推荐顺序：

1. 先看 `team summary`。
2. 再看 `team next`，确认推荐恢复命令。
3. 再看 `team runbook`，确认是临时故障还是计划本身要修。
4. 如果是临时失败，用 `retry-review` 或 `retry-adversarial-review`。
5. 如果失败暴露的是计划缺口，回到 `team revise`。


## Worker / Subagent Result Contract

并行 worker、explorer、reviewer、verifier 的交付必须使用固定五段格式，父流程只整合这些摘要和证据，不要求粘贴完整子会话：

```text
SUMMARY: one paragraph describing what was done and what happened
CHANGES: files modified with one-line descriptions, or None
EVIDENCE: path:line-range citations, commands, gate summaries, or artifact paths
RISKS: concrete risks or follow-up checks the parent should consider
BLOCKERS: what stopped the worker, or None
```

使用规则：

- explorer / reviewer 默认只读，`CHANGES` 应为 `None`。
- implementer 必须列出实际改动文件，并在 `EVIDENCE` 中放 targeted test 或检查结果。
- verifier 不修复失败，只在 `RISKS` / `BLOCKERS` 中记录失败断言、命令和下一步候选。
- 父 session 的 `team summary`、`team next`、`team runbook` 只消费结构化 evidence、risks、blockers 和 artifact path，避免把大日志放进 operator 输出。
- 如果 worker 输出缺少这些段落，恢复建议优先要求重新整理结果，而不是直接继续执行。

## v1.x 操作入口

- 用 `health` 查看 `codex`、`claude`、`mock` 的 binary、available、detail 和 recommended fallback。
- 用 `team setup` 查看 provider/runtime 就绪状态、doc sync 和 compliance 摘要，并获取推荐下一步命令。
- 自动化和 UI 必须消费 `team setup --format json` 的 `agent_orchestrator.setup_doctor.v1` contract，不解析 pretty 文本。
- 用 `team inspect-docs --query "<task>" --changed-file <path>` 生成 `agent_orchestrator.docs_context.v1` 文档上下文包，供 agent 在动手前读取最新 canonical docs。
- 用 `team inspect-handoff <session_id>` 查看最近的 `agent_orchestrator.handoff_packet.v1` 交接包。
- 用 `team docs-index --query "<task>" --changed-file <path>` 反查相关 canonical docs、ADR、测试和推荐命令。
- 用 `team workspace-status` 查看当前 workspace state、dirty files、plans/runs/jobs、approvals、memory digest 和 optional explore_cache 状态。
- 用 `team context-packet --query "<task>"` 生成 control-plane context packet；它只压缩上下文，不替模型或 strategy 做决策。
- 用 `team topology inspect <session_id>` 查看 read-only execution topology snapshot。
- 用 `team approvals list` / `team approvals resolve` 记录人类介入决策；resolve 只写 event/memory，不自动执行 gated work。
- 用 `team evidence-gates` 查看 `agent_orchestrator.evidence_bundle.v1`。
- 用 `docs/decisions/` 查看 ADR，确认文档上下文、handoff packet、canonical docs 与 derived views 的边界。
- 用 `--review-policy auto|standard|adversarial|required-human` 记录受控 review policy；默认 `auto` 不改变原策略。
- 用 `evidence benchmark/capture/report` 生成 JSON evidence 和 markdown 阶段报告。
- 用 `docs/process/evidence-cases.json` 作为可提交的真实任务样本库，并生成 `docs/process/v1x-evidence-report.md`。
- 用 `team refresh-docs` 刷新 canonical process docs。
- 用 `team repair-compliance` 先刷新 docs，再查看 remaining warnings、required actions 和 recommended commands。
- 用 `team setup` 查看 release_readiness，确认 version_sync、tests、evidence 和 compliance 的收尾状态。
- 用 `ui` 打开治理控制台，检查 provenance、review policy、fallback、compliance、event/message timeline、work graph 和 job log。
- 对运行中的 job，可用 CLI 或 Console 执行 `send` / `cancel`，并查看 terminal_ref、last log excerpt 和 last_seen_at。

## 真实案例与证据路径

Phase 5 发布候选收尾时，operator 不需要猜测“真实工作流证据”在哪里。优先按下面的固定路径检查：

- 工作流回归记录：`docs/process/v1x-hardening-workflow-report.md`
  - Phase 1 记录了 `Harden CLI setup summary for release readiness` 的 start/next/execute/inspect-execution 路径。
  - Phase 1 也记录了 `Build plan with followup checklist and recovery guidance` 暴露的 runbook wording friction，以及对应修复。
  - Phase 3 记录了 provider health、command-runtime stdout/stderr/exit-code、fallback、send/cancel 的验证边界。
- 可提交真实任务样本：`docs/process/evidence-cases.json`
  - `standard_plan_artifact`
  - `followup_checklist_recovery`
  - `high_risk_auth_migration`
  - `parallel_validation_modules`
- 当前 evidence 汇总：`docs/process/v1x-evidence-report.md`
  - 检查 `case_count`、`average_benefit_score`、`team_cases_with_execution_run`、`provenance_present`、`recovery_guidance_present`。
- evidence 趋势：`docs/process/v1x-evidence-trend.md`
  - 检查平均收益、execution run、direct-run limitation 和 team advantage delta 是否退化。
- 本地 JSON 输出默认位置：`.agent_orchestrator/evidence/real-tasks.json`
  - 这是 evidence report 命令的机器可读输出，不需要手工编辑。
- v1.0 candidate checklist：`docs/process/v1-candidate-release-checklist.md`
  - 这是详细发布前检查单；`docs/process/v1x-release-readiness.md` 保持 canonical 简表。

推荐复现命令：

```bash
PYTHONPATH=src python -m agent_orchestrator.cli evidence report \
  --case-file docs/process/evidence-cases.json \
  --output docs/process/v1x-evidence-report.md \
  --json-output .agent_orchestrator/evidence/real-tasks.json
PYTHONPATH=src python -m agent_orchestrator.cli team setup
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
```

验收口径：

- runbook 只指向可提交文档和可再生成的 local evidence，不要求外部服务。
- evidence cases 覆盖 standard、followup、high_risk、parallel 四类场景。
- `v1x-hardening-workflow-report.md` 记录真实 friction 和修复，不只记录 happy path。
- 发布候选判断以 `team setup` 的 release_readiness、candidate checklist、evidence report、targeted tests 和 compliance 共同为准。
- 发布候选还要检查 `team setup --runtime command --format json` 中的 `release_readiness.runtime_measurement` 和 `release_readiness.checklist.runtime_measurement`；token/cost placeholder 本身不阻塞 RC，除非 provider runtime 声称可上报却缺失。

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
- 可以通过 `team inspect-execution` 直接查看 linked execution run，而不是先抄 `run_id`

## 日常操作建议

- 每次新任务先从 `team start` 开始，不要跳过 planning session。
- 每次准备继续时先看 `team summary` 或 `team next`。
- 每次需要确认可执行工作项时看 `team task next`。
- 每次角色边界不清楚时看 `team roles`。
- 每次状态不清楚时优先跑 `team runbook`。
- 每次 delegated job 失败时优先走标准命令恢复，不要直接编辑底层 JSON。
- 每次 execution 完成后优先跑 `team inspect-execution` 看 provenance 和结果。
- 每次需要查看阶段沉淀时跑 `team inspect-knowledge`，它只读取 `.agent_orchestrator/knowledge/*.jsonl`。
- `team summary` / Console payload 中的 `approval_state`、`human_intervention_reason`、`runtime_health`、`usage_cost` 是统一审批和观测入口；`usage_cost` 目前是 placeholder，除非 provider runtime 明确上报真实用量。
- 每次 happy path 验证通过后，再推进主计划的下一实现段。
