# Native Agent Program Execution Goal

## Goal Intent

本 goal 的重点，不再是继续把 native coding agent 做得更像一个“单 session、单任务”的 daily-driver coding copilot。

上一阶段已经把 native path 从“可用的 governed coding kernel”推进到“更接近可日常使用的 productized coding agent”。下一阶段要解决的是另一层差距：

- native path 是否能够稳定推进更长链、更分阶段、带里程碑与恢复点的真实仓库 workstream，
- 而不只是把一次 coding task 做完。

因此，本 goal 的目标不是做一个 fully autonomous multi-agent platform，也不是一次性补齐所有 program-management 产品表面，而是把当前项目与更成熟 program-execution agent 之间的差距，从：

- “native 主路径已经像一个 daily-driver coding agent，但仍主要围绕单任务闭环”

收敛到：

- “native 主路径已经开始像一个 governed 的 long-horizon program executor，能够围绕 work graph、milestone、delegation boundary、artifact continuity 与 operator control 持续推进真实仓库工作流”

## Target Outcome

完成后，项目相对上一阶段的提升应主要体现在：

1. native path 不再只擅长单次 task closure，而是能推进至少一类 multi-milestone 的真实仓库 workstream。
2. planner 不再只决定一次 task 的 explore/edit/verify 路径，也能决定 milestone ordering、dependency gating、pause boundary 与 delegation boundary。
3. session continuity 不再只体现为 resume/repair continuity，也体现为 program-level execution memory。
4. operator surface 不再只显示“当前执行状态”，还显示“当前 program posture、已完成里程碑、下一 owned unit、阻塞原因与恢复路径”。
5. native / external executor 不再只是共享 execution contract，也更接近共享 program-level delegation contract。

完成后，项目与更成熟 program-execution system 的差距应主要剩在：

1. 更厚的多代理生态与更广的 executor 类型。
2. 更完整的 IDE / GUI / backlog / collaboration 产品层。
3. 更强的跨仓库、跨会话、跨人员 program management 能力。

而不应继续主要卡在：

1. native path 只能处理单次 bounded task。
2. 长任务只能靠 session 文本续跑，而不是结构化 artifact continuity。
3. operator 很难看出 program 当前做到哪里、下一步谁执行、为什么停。
4. native / external 在长任务 delegation 上像两套不同体系。

## Scope Boundary

本 goal 只包含以下四个实现部分，且都必须完成：

### P0 Long-Horizon Work Graph

把 native path 从“单 task execution loop”推进到“能显式管理 work graph / milestone / dependency / checkpoint 的 program execution 主路径”。

必须完成：

- 引入 program-level work unit、milestone 或等价结构；
- 能表达至少一种 `explore -> edit -> verify -> checkpoint -> continue` 的长链形态；
- 对 dependency、blocked state、ready-next-unit 或等价状态有原生表示；
- 至少一类真实仓库 workstream 因此可以主要依赖 native path 推进。

### P1 Delegated Subtask Contract

把 planner/runtime 从“为单任务选择执行策略”推进到“能为 program 内多个 work unit 决定 ownership 与 delegation boundary”。

必须完成：

- planner 能决定当前 work unit 应由 native 继续执行、暂停澄清、等待 approval、还是 handoff/fallback；
- 对 delegation decision 保留 reason、boundary、required artifact、resume contract；
- external executor 继续可热插拔接入；
- 至少一个 program scenario 能证明 native/external delegation 属于同一 governed contract，而不是临时分叉逻辑。

### P2 Artifact-Backed Execution Memory

把 session continuity 从“turn/session resume”推进到“program-level artifact continuity”。

必须完成：

- 记录 program goal、active milestone、completed milestone、open assumptions、verification state、recovery hints 或等价结构；
- compaction/resume 后仍能恢复 program 当前姿态，而不只是恢复最近一轮执行；
- program memory 可被 planner、runtime、workspace index、UI/CLI summary 中至少多个面消费；
- 至少一类失败/恢复链条能证明 artifact continuity 真实参与后续推进。

### P3 Operator-Facing Program Control

把 operator surface 从“看当前 session 状态”推进到“看当前 program 的推进姿态与可操作恢复路径”。

必须完成：

- `team summary`、`team next`、`team runbook`、workspace index、UI summary 中至少多个面显示 program posture；
- operator 可见当前 milestone progress、next owned unit、delegation boundary、recovery lane 或等价信息；
- 这些 surface 继续是 canonical state 的 projection，而不是第二套 durable state；
- comparative evidence、文档与 operator surfaces 之间存在共享 program-level 语义。

## Global Stopping Criteria

只有以下条件全部满足，goal 才能停止：

1. `P0`、`P1`、`P2`、`P3` 四部分都已完成。
2. native path 已能主要依赖自身推进至少一类 multi-milestone 的真实仓库 workstream。
3. planner 已体现出围绕 work graph / milestone / delegation boundary 的原生决策能力。
4. session continuity 已真实升级为 artifact-backed program continuity，而不只是 bounded resume。
5. operator-visible surface 已能说明：
   - 当前 program 做到哪里
   - 下一步由谁执行
   - 为什么暂停、阻塞或切换
   - 如何恢复
6. native / external executor 在 long-horizon delegation 上更统一，但 external hot-plug 未被破坏。
7. comparative benchmark、workspace index、runtime/session、UI/CLI summary 与文档共享同一类 long-horizon program evidence。
8. 没有无限扩张到：
   - 完整 backlog/project management 系统
   - fully autonomous multi-agent society
   - 全面追平所有成熟 agent IDE / cloud product 表面
   - 与 program-execution goal 无关的大规模重构

## Phase Acceptance Criteria

### P0 Acceptance

`P0` 只有在以下条件全部满足时才算完成：

1. 代码中存在 work graph、milestone、checkpoint、dependency 或等价 program-level execution structure。
2. 这些结构进入真实主链路，而不是只作为文档或 helper。
3. 至少一类真实仓库任务被表达为 multi-step / multi-milestone workstream。
4. blocked / ready / completed / next-unit 或等价状态可被 runtime 或 workspace/operator surface 看到。
5. 存在测试或等价高信号验证。

### P1 Acceptance

`P1` 只有在以下条件全部满足时才算完成：

1. planner 能围绕 work unit ownership 与 delegation boundary 做原生决策。
2. decision evidence 至少保留 selected executor、reason、boundary、required artifacts、resume expectation 或等价字段。
3. native continue / approval pause / clarify pause / fallback / handoff 至少多个分支被真实接入。
4. 至少一个 scenario 证明 native/external delegation 在同一 governed contract 下工作。
5. 存在测试或等价高信号验证。

### P2 Acceptance

`P2` 只有在以下条件全部满足时才算完成：

1. artifact-backed execution memory 记录了 program-level continuity，而不只是最后一步执行摘要。
2. compaction / resume 后能恢复 active milestone、completed milestones、open blockers 或等价 program posture。
3. planner、runtime、workspace index、UI/CLI summary 中至少多个面消费这些 continuity artifact。
4. 至少一个恢复样例证明 continuity artifact 真实参与恢复，而不是只被展示。
5. 存在测试或等价高信号验证。

### P3 Acceptance

`P3` 只有在以下条件全部满足时才算完成：

1. operator-visible surfaces 出现 program posture、milestone progress、next unit、delegation/recovery lane 或等价信号。
2. `team summary`、`team next`、`team runbook` 中至少多个面能在不展开底层大日志的情况下说明 program 当前可执行建议。
3. workspace/UI/CLI/doc/evidence 至少多个面共享同一 program-level 词汇与语义。
4. 这些 surface 仍然是 projection，不引入第二 durable state。
5. 存在测试或等价高信号验证。

### Shared Program-Execution Evidence Contract

为避免“代码里有 program 状态，但各 surface 语义漂移”，本 goal 下列 evidence surface 应被视为同一组 long-horizon program-execution contract 的不同投影：

1. runtime payload
2. session snapshot / session continuity artifact
3. workspace index
4. `team summary`
5. `team next`
6. `team runbook`
7. UI execution summary
8. CLI execution summary
9. 文档与 comparative evidence narrative

至少应共享并可互相对应以下几类字段或等价证据：

- `program_posture`
  - `program_goal`
  - `active_milestone`
  - `completed_milestones`
  - `ready_next_units`
  - `blocked_units`
- `delegation_contract`
  - `selected_executor`
  - `ownership_boundary`
  - `handoff_reason_code`
  - `fallback_reason_code`
  - `required_handoff_artifacts`
- `program_continuity`
  - `resume_supported`
  - `resume_kind`
  - `compaction_stage`
  - `continuity_artifact_status`
  - `latest_recovery_hint`
- `milestone_verification`
  - `verification_status`
  - `remaining_checks`
  - `checkpoint_ready`
- `operator_control`
  - `next_recommended_action`
  - `runbook_recovery_lane`
  - `approval_pause_state`
  - `clarify_pause_state`
- `comparative_program_benchmark`
  - `same_program_contract`
  - `same_evidence_surface`
  - `native_vs_external_executor_comparison`

如果这些 surface 之间只能看到局部字段、命名互不对应、或 program posture 只能在单点出现，则不能视为满足本 goal 的 shared evidence 要求。

## File-Level Verification Targets

以下不是唯一文件名要求，但 goal 完成时必须能在当前仓库中找到等价实现证据。

### P0 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/planning.py`
- `src/agent_orchestrator/execution/`
- `src/agent_orchestrator/session/`
- `src/agent_orchestrator/control_plane_workspace.py`
- `tests/`
- 必要文档

### P1 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/strategy/`
- `src/agent_orchestrator/execution/models.py`
- `src/agent_orchestrator/intake/`
- `src/agent_orchestrator/control_plane_runtime.py`
- `tests/`
- 必要文档

### P2 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/session/runtime.py`
- `src/agent_orchestrator/session/models.py`
- `src/agent_orchestrator/control_plane_artifacts.py`
- `src/agent_orchestrator/evidence.py`
- `tests/`
- 必要文档

### P3 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/cli_team.py`
- `src/agent_orchestrator/cli_presenters.py`
- `src/agent_orchestrator/ui_service.py`
- `src/agent_orchestrator/control_plane_workspace.py`
- `docs/process/agent-team-operator-runbook.md`
- `tests/`

## Required Verification Evidence

goal 完成前，必须至少具备以下一种或多种直接证据组合：

- 自动化测试
- 集成测试
- CLI 级 program-state 验证
- workspace / UI / CLI projection 检查
- comparative benchmark 或等价 evidence narrative
- session continuity artifact 与 recovery 路径检查

不能只用以下弱证据宣布完成：

- 新增了 program/milestone 字段但没有主路径消费
- 文档里出现了长任务术语
- operator surface 显示了静态文案但不反映真实状态
- 只有单次 happy-path 成功，没有 checkpoint / resume / recovery 证据
- external handoff 仍是旁路逻辑，只是名称看起来统一

## Validation Commands

goal 完成前，应该至少能提供一组等价于以下层级的高信号验证命令：

```bash
pytest tests/test_strategy_planner.py tests/test_control_plane.py tests/test_session_runtime.py -q
pytest tests/test_cli.py tests/test_cli_presenters.py tests/test_ui_service.py -q
pytest tests/test_evidence.py tests/test_task_router.py tests/test_team.py -q
```

如果实现落点变化，也必须保留等价强度的验证，而不能只做局部 helper 测试。

## Explicit Non-Goals

以下内容不是本 goal 的完成要求，禁止无限扩展进去：

- 完整 backlog / issue / roadmap 管理产品
- fully autonomous agent swarm
- 全量 IDE 插件生态或远程协作平台
- 所有任务类都进入 program execution
- 与 long-horizon execution 无关的大规模 runtime 重写

## Goal-Mode Short Form

建议给调度层或摘要层使用的短文本：

把当前已接近日常可用的 native coding agent，继续推进成更接近 governed long-horizon `program executor` 的主执行路径：围绕 work graph、delegated subtask contract、artifact-backed execution memory 与 operator-facing program control 四个面，让 native path 能稳定推进至少一类 multi-milestone 的真实仓库 workstream，同时保留 approval、evidence、recovery 与 hot-pluggable external fallback/handoff 优势。完整验收、共享 evidence contract、文件级证据与停止条件见 `docs/process/goal-mode-native-agent-program-execution.md`。
