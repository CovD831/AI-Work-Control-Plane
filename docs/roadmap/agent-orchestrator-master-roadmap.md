# AI-Work-Control-Plane Master Roadmap

## 概要

这份 roadmap 定义了项目从“以编排为中心的 MVP”走向目标形态的路径：一个面向长周期本地 agent 工作的 **AI Work Control Plane**。

当前的顶层产品链路是：

```text
WorkspaceState -> ContextPacket -> StrategyDecision -> ExecutionTopologySnapshot -> ApprovalItem -> EvidenceBundle -> MemoryRecord
```

原有编排能力并未消失，但它们已经下沉到控制平面之下：

- `Planning Governance Layer`
- `Execution Strategy Layer`

在当前 roadmap 语义下，仓库实现更适合按三层理解：

- `决策核心层`
- `执行拓扑层`
- `Provider / Runtime 层`

对应中文说明见：

- [决策核心-执行拓扑-运行时分层说明](/Users/abab/Desktop/AI-Work-Control-Plane/docs/architecture/决策核心-执行拓扑-运行时分层说明.md)

其中：

- `agent team` 属于执行拓扑层
- `claude / codex / command runtime` 属于 Provider / Runtime 层
- planning governance 与 execution strategy 的规则语义应尽量收敛在决策核心层

这份 roadmap 由 **4 个产品阶段** 加上 AI Work Control Plane 迁移线组成。执行策略仍然重要，但它已经只是更大产品中的一层；默认路径应是：`workspace state -> compressed context -> strategy -> topology -> approval/evidence/memory -> orchestration runtime`。

## 目标形态

目标产品应当：

- 以本地 CLI 作为 v1 的一等入口
- 先服务作者自己的真实工作流，再考虑更广泛包装
- 以可持久的外部工作状态为中心，而不是只依赖模型内部 planning
- 在执行前突出 plan governance
- 在执行中突出治理摘要与策略选择
- 可以调用可替换的 provider、bridge、runtime 和 job backend plugin
- 能输出结构化 run artifact 和同步后的文档更新
- 通过 hook 和 loopback check 约束项目规则，而不是只靠 prompt 提醒

这个产品明确**不**打算变成：

- 一个完整 bridge 产品
- 一个完整 session manager 或 tmux orchestrator
- 一个靠 runtime 特性取胜的 provider-specific shell
- 一个以 CEO/employee roleplay 为核心抽象的人类组织架构系统

## 当前状态

- 项目已经有一个围绕 `mode + agent_enabled + depth + provider_flow` 组织的控制平面骨架。
- 失败处理已经覆盖 depth-first escalation、partial rescue 和 dependency-aware replay。
- 执行制品已经具备早期 decision contract。
- 仓库已经有基本的 planning governance 闭环，包括持久 plan session、双模型审查轮、gap closure、approval gate 和 approved-plan-linked execution handoff。
- 面向内部默认工作流的文档同步与 hook-based compliance check 已经存在，但覆盖面和强制性还不够。
- 旧 roadmap 过度强调 execution strategy，低估了 planning governance 作为产品层的价值。
- 当前真正的风险，是项目继续向显式 agent orchestration 倾斜；control-plane migration 的目标正是把长期价值转移到 state、context、approval、evidence、memory provenance 和 recovery。

## AI Work Control Plane 迁移

项目现在把 `agent team` 和 provider runtime 都视为更高层制品链路下方的执行能力：

- `WorkspaceStateSnapshot` 记录当前项目现场：session、run、job、evidence、approval、provider health、dirty files、memory digest 和可选 external cache 状态。
- `ContextPacket` 为模型压缩选中的文档、改动文件、memory record 和 stale warning，但不在这一层替模型做策略。
- `StrategyDecision` 记录下一阶段目标、理由、权衡、风险和验证要求，但不直接执行。
- `ExecutionTopologySnapshot` 是围绕 state/context/strategy/manager slots/workers/review/rescue/approval/evidence/memory 的只读执行路径图。
- `ApprovalItem` 让人工介入成为持久且可审计的状态，而不是绕开执行门禁。
- `EvidenceBundle` 统一 tests、compliance、setup 和 evidence report 的门禁摘要。
- `MemoryRecord` 携带 provenance、freshness、confidence 和可选的 explore_cache 状态。

第一阶段实现仍然坚持 CLI-first，通过 `team workspace-status`、`team context-packet`、`team topology inspect`、`team approvals` 和 `team evidence-gates` 暴露能力。

Phase 6+ hardening track 会把这套实现固化成稳定协议：artifact contract 有文档、有测试，workspace index 引用 recent artifact，StrategyDecision 出现在正常 operator 工作流里，approval 携带 reason code，evidence bundle 给出 memory write 建议，UI 保持只读，并用 dogfood 场景钉住全链路。

长期方向不是无止境地把显式 agent 编排做得更复杂。短期内 orchestration 仍是现实执行机制；中期由 control plane 管住它；长期可以把更多 orchestration 内化进 model runtime，但 external state、approval、evidence、memory provenance 和 recovery 仍然留在系统外部。

The Operations Track now makes that direction operator-visible: `team workspace-status` returns Workspace / Program Index v2, approvals are treated as an inbox, topology snapshots export read-only blueprint views, run ledger records recovery state, evidence bundles expose memory promotion candidates, and runtime health/tool inventory remain control-plane inputs rather than execution shortcuts.

The Live Recovery Track added Recovery Timeline, Runtime Event Stream, Recovery Recommendation, resume hints, and evidence-backed memory promotion. It closes the gap between "I can inspect the control plane" and "I can safely resume a long-running task from the control plane."

The next major update is the Runtime Bridge Fidelity Track: Provider Session Snapshot, Runtime Operation Receipt, extended Runtime Event Stream, `team runtime inspect`, and read-only workspace/evidence/UI runtime fidelity summaries. It closes the gap between "the control plane recommends recovery" and "the operator can trust what the provider/runtime session actually supports."

The current post-baseline update is the Real-Task Dogfood Evidence Track. It expands the committed evidence matrix and reports recovery coverage, runtime fidelity coverage, compliance blocking coverage, postmortem readiness, and cost/latency readiness. This is deliberately evidence-first: deepen provider-specific bridge behavior only after local dogfood shows which runtime gaps matter.

## Product Architecture

### Planning Governance Layer
- plan authoring
- 质量审查与风险挑战门禁
- rule-driven review rounds
- gap-list closure logic
- plan artifact persistence
- checklist tracking
- resume state and interruption recovery
- documentation synchronization verification

### Execution Strategy Layer
- task/risk/dependency/failure/budget signals
- route/review/rescue/replay/reroute decisions
- execution plugins
- explainable execution artifacts

### Compliance And Synchronization Layer
- global codebase map
- module manifests
- file-header contracts
- hook-based policy checks
- automatic map refresh after task completion

## Product Stages

### Stage 1: Product Backbone Rewrite
**Outcome**
The project is redefined as a dual-layer product with one source of truth for product shape, stages, and supervision.

**Done when**
- README, roadmap, and process describe the same dual-layer system
- planning governance and execution strategy are both first-class
- the old single-line strategy-only narrative is gone

### Stage 2: Planning Governance Skeleton
**Outcome**
Tasks enter a rule-driven plan loop before execution begins.

**Done when**
- plan sessions can be created, persisted, resumed, and tracked
- 审查与风险挑战门禁能够被建模并持久化
- checklist and review-round state exist as durable artifacts
- execution no longer conceptually starts from raw requirement alone

### Stage 3: Fractal Documentation And Hard Sync
**Outcome**
Code, module docs, file headers, and the global map are forced into sync.

**Done when**
- root map, module manifests, and file-level contracts are defined
- AI can enter from any file and recover context through the declared document structure
- code changes trigger loopback checks for header and doc correctness
- task completion refreshes the global map

### Stage 4: Hook Enforcement And End-to-End Product Convergence
**Outcome**
The full product path is enforceable end-to-end.

**Done when**
- hook checks block violations at write time or commit time
- approved plans feed the execution strategy layer
- execution results feed documentation synchronization
- the product can prove it is better than fixed-template workflows through both planning quality and execution quality

## Stage Plan

### Stage 1: Product Backbone Rewrite
**Goal**
Replace the previous single-line strategy-engine product story with a dual-layer orchestration system story.

**Main Changes**
- Rewrite product definition around `Planning Governance Layer + Execution Strategy Layer`.
- Make planning governance the default entry path for tasks.
- Upgrade process supervision to track both layers explicitly.

**Acceptance**
- README, roadmap, and process are aligned.
- No second competing roadmap/process truth remains.

### Stage 2: Planning Governance Skeleton
**Goal**
Create the minimal planning governance system needed to gate execution.

**Main Changes**
- Add plan session concepts, review rounds, gap-list tracking, and resume metadata.
- Persist plans into a fixed in-project directory with checklist status.
- Define rule-driven round control and approval/exit conditions.

**Acceptance**
- A task can create a persisted plan artifact before execution.
- Plan review state survives session interruption.

### Stage 3: Fractal Documentation And Hard Sync
**Goal**
Make context and documentation synchronization enforceable instead of advisory.

**Main Changes**
- Define root map, module manifest, and file header contract formats.
- Add loopback checks after code changes.
- Add automatic global map refresh on task completion.

**Acceptance**
- A code change can be rejected for documentation mismatch.
- Global and module-level context artifacts stay in sync with code.

### Stage 4: Hook Enforcement And End-to-End Product Convergence
**Goal**
Hook the planning layer, execution layer, and documentation layer into one enforceable workflow.

**Main Changes**
- Add hook-based compliance checks.
- Feed approved plans into execution strategy.
- Feed execution results into sync/update checks.
- Benchmark product value across planning quality and execution outcomes.

**Acceptance**
- Violating code/doc/process rules can be blocked automatically.
- The full workflow can run from task input to synchronized completion.

## Transition Notes

The previous `4 stages / 7 iterations` view is superseded by this dual-layer roadmap.

Useful carryovers remain:
- decision contract work in the execution layer
- explainable run artifacts
- plugin boundary cleanup
- guardrails and benchmark thinking

But those now sit under the larger product, not as the whole product.

## Risks

- Planning governance may sprawl unless round rules and approval criteria stay explicit.
- Fractal documentation can become maintenance burden if hook enforcement is weak or noisy.
- Hook checks may create too much friction if not scoped carefully.
- Execution strategy work may stall if plan artifacts are not well-shaped enough to consume.
- The system may overfit the author's workflow and require later simplification for outside users.

## Exit Criteria

The roadmap is complete when:

- the dual-layer product shape is explicit and coherent
- task execution is conceptually and operationally gated by planning governance
- plans are persisted, resumable, and checklist-driven
- documentation and code synchronization are enforced, not merely suggested
- execution decisions remain explainable and plugin-driven
- benchmark evidence shows the combined product is worth keeping in its reduced but stricter form


## v1.x Reference-Informed Upgrade Track

The v1.x backlog was organized by a reference-informed master plan:

- [v1.x Reference Upgrade Master Plan](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/v1x-reference-upgrade-master-plan.md)

Status: **completed for the v1.x reference-informed upgrade scope**.

The completed upgrade borrows targeted strengths from local reference repositories while preserving AI-Work-Control-Plane's boundaries: it strengthens job observability, review/rescue/setup action grammar, context recovery, packaging discipline, and evidence reporting without turning the product into a bridge, session manager, or plugin marketplace.

## v1.x Convergence

The repository now extends the completed v1 baseline with:

- fallback-aware provider health snapshots for `codex`, `claude`, and `mock`
- controlled review policy CLI overrides that preserve `auto` defaults
- evidence CLI commands for built-in benchmarks, real task case files, and markdown phase reports
- expanded real-task dogfood reports with recovery, runtime fidelity, compliance blocking, postmortem, and cost/latency readiness metrics
- an expanded governance console for provenance, governance, review policy, fallback, compliance, events, messages, work graph, and job controls
- NUL-delimited hook staged-file handling for paths containing spaces
- `team refresh-docs` and `team repair-compliance` repair commands
- CLI/UI runtime ergonomics for terminal refs, attach availability, last log excerpts, last seen timestamps, send, and cancel
- `team setup` release-readiness snapshots covering version sync, tests, evidence, and compliance

## v1.x Release Readiness

Release readiness is deliberately local and honest:

- `pyproject.toml` carries the version marker for the current package build
- `team setup` surfaces provider health, doc sync, compliance, and release readiness
- evidence reports and trend reports are generated as local markdown artifacts
- no plugin-marketplace or external distribution promise is implied

Pre-release checklist source of truth:

- [v1.0 Candidate Release Checklist](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/v1-candidate-release-checklist.md)
- [v1.x Release Readiness](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/v1x-release-readiness.md) remains the short canonical process document.

## v1.0 Candidate Remaining Hardening

The reference-informed upgrade is complete, but the v1.0 candidate should stay open until the following release-candidate hardening items are closed:

- Run and record the Phase 5 targeted suite: `pytest tests/test_docs_process.py tests/test_planning_support.py tests/test_team.py -q`.
- Run final `team check-compliance` after any docs/evidence refresh.
- Freeze the committed evidence paths: `docs/process/evidence-cases.json`, `docs/process/v1x-evidence-report.md`, and `docs/process/v1x-evidence-trend.md`.
- Confirm the committed evidence matrix still covers standard, follow-up, high-risk, parallel, UI workflow, compliance blocking, runtime fidelity, and interruption recovery cases.
- Re-check `docs/process/v1x-hardening-workflow-report.md` so the candidate carries both happy-path and friction/fix evidence.
- Confirm `team setup` still reports version sync, provider/runtime health, evidence status, tests, and compliance in the release_readiness snapshot.
- Keep the runtime limitation explicit: v1.x has a guarded command runtime and job controls, not a full Codex/Claude bridge or persistent session manager.

2026-05-28 follow-up result:

- Codex Runtime Pilot Phase 4/5 was committed as a checkpoint.
- Evidence report and trend were regenerated from `docs/process/evidence-cases.json` and stayed stable.
- Phase 5 targeted suite passed: `pytest tests/test_docs_process.py tests/test_planning_support.py tests/test_team.py -q` reported 150 passed.
- `team setup --runtime command --format json` reported package version `1.0.0rc1`, release readiness true, `codex`/`claude`/`mock` visible, runtime measurement `measured`, and provider evidence summary format `agent_orchestrator.provider_evidence_summary.v1`; this follow-up is now being sealed as `v1.0.0-rc.2` with package version `1.0.0rc2`.
- `team check-compliance` passed with `blocking: false`.

RC2 external evaluation result:

- `v1.0.0-rc.2` passed setup, workspace status, evidence gates, compliance, and Codex pilot evidence-consumption checks in an external clone.
- Dogfood found one README quickstart blocker: the governed workflow skipped `team draft-ready` and `team submit-review` before `team approve`.
- Prepare `v1.0.0-rc.3` as a documentation-blocker fix only.
