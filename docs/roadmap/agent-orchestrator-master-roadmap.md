# Agent Orchestrator Master Roadmap

## Summary

This roadmap now defines the path from an orchestration-centered MVP to the intended v1 product: an **AI Work Control Plane** for long-cycle local agent work.

The new top-level product sequence is:

```text
WorkspaceState -> ContextPacket -> StrategyDecision -> ExecutionTopologySnapshot -> ApprovalItem -> EvidenceBundle -> MemoryRecord
```

The earlier orchestration layers remain, but they now sit underneath that control plane:

- `Planning Governance Layer`
- `Execution Strategy Layer`

中文分层补充：

在当前 roadmap 语义之下，仓库实现还应额外按三层理解：

- `决策核心层`
- `执行拓扑层`
- `Provider / Runtime 层`

对应中文说明见：

- [决策核心-执行拓扑-运行时分层说明](/Users/abab/Desktop/Agent-Orchestratoar/docs/architecture/决策核心-执行拓扑-运行时分层说明.md)

其中：

- `agent team` 属于执行拓扑层
- `claude / codex / command runtime` 属于 Provider / Runtime 层
- planning governance 与 execution strategy 的规则语义应尽量收敛在决策核心层

The roadmap is organized as **4 product stages** plus the AI Work Control Plane migration. Execution strategy remains essential, but it now lives inside a larger product whose default behavior is: `workspace state -> compressed context -> strategy -> topology -> approval/evidence/memory -> orchestration runtime`.

## Final Product Shape

The target product is:

- a local CLI tool as the only first-class v1 product surface
- optimized for the author's real workflows before broader external packaging
- centered on durable external work state rather than model-internal planning alone
- centered on plan governance before execution
- centered on strategy decisions during execution
- able to call replaceable provider, bridge, runtime, and job-backend plugins
- able to emit structured run artifacts and synchronized documentation updates
- able to enforce project rules through hooks and loopback checks, not prompt guidance alone

The product is explicitly **not** trying to become:

- a full bridge product
- a full session manager or tmux orchestrator
- a provider-specific shell that wins on runtime features alone
- a classically human company org chart with CEO/employee roleplay as the core abstraction

## Current State

- The project already has a strategy-oriented control plane built around `mode + agent_enabled + depth + provider_flow`.
- Failure handling already includes depth-first escalation, partial rescue, and dependency-aware replay behavior.
- Early decision contract work exists for execution artifacts.
- The repository now has a basic planning governance loop with persisted plan sessions, dual-model review rounds, gap closure, approval gating, and approved-plan-linked execution handoff.
- Narrow documentation synchronization and hook-based compliance checks now exist for the internal-default workflow, but broader coverage and harder enforcement are still incomplete.
- The old roadmap view overfit the execution strategy line and understated planning governance as a product layer.
- The new risk is overfitting explicit agent orchestration; the control-plane migration moves durable value into state, context, approvals, evidence, memory provenance, and recovery.

## AI Work Control Plane Migration

The project now treats `agent team` and provider runtimes as execution capabilities under a higher artifact pipeline:

- `WorkspaceStateSnapshot` records the current project现场: sessions, runs, jobs, evidence, approvals, provider health, dirty files, memory digest, and optional external cache status.
- `ContextPacket` compresses selected docs, changed files, memory records, and stale warnings for model use without choosing strategy.
- `StrategyDecision` records the next goal, rationale, tradeoffs, risks, and validation plan without executing.
- `ExecutionTopologySnapshot` is a read-only graph over state/context/strategy/manager slots/workers/review/rescue/approval/evidence/memory.
- `ApprovalItem` makes human intervention durable and auditable without bypassing execution gates.
- `EvidenceBundle` standardizes gate summaries for tests, compliance, setup, and evidence reports.
- `MemoryRecord` carries provenance, freshness, confidence, and optional explore_cache status.

The first implementation remains CLI-first through `team workspace-status`, `team context-packet`, `team topology inspect`, `team approvals`, and `team evidence-gates`.

The Phase 6+ hardening track turns that first implementation into a durable protocol: artifact contracts are documented, workspace index references recent artifacts, StrategyDecision appears in normal operator workflow, approvals carry reason codes, evidence bundles recommend memory writes, UI remains read-only, and a dogfood scenario pins the full chain.

The long-term direction is not to keep making explicit agent choreography more elaborate forever. Short term, orchestration remains the practical execution mechanism; medium term, the control plane governs it; long term, more orchestration can move into model runtimes while external state, approvals, evidence, memory provenance, and recovery stay as stable system artifacts.

The Operations Track now makes that direction operator-visible: `team workspace-status` returns Workspace / Program Index v2, approvals are treated as an inbox, topology snapshots export read-only blueprint views, run ledger records recovery state, evidence bundles expose memory promotion candidates, and runtime health/tool inventory remain control-plane inputs rather than execution shortcuts.

The Live Recovery Track added Recovery Timeline, Runtime Event Stream, Recovery Recommendation, resume hints, and evidence-backed memory promotion. It closes the gap between "I can inspect the control plane" and "I can safely resume a long-running task from the control plane."

The next major update is the Runtime Bridge Fidelity Track: Provider Session Snapshot, Runtime Operation Receipt, extended Runtime Event Stream, `team runtime inspect`, and read-only workspace/evidence/UI runtime fidelity summaries. It closes the gap between "the control plane recommends recovery" and "the operator can trust what the provider/runtime session actually supports."

The current post-baseline update is the Real-Task Dogfood Evidence Track. It expands the committed evidence matrix and reports recovery coverage, runtime fidelity coverage, compliance blocking coverage, postmortem readiness, and cost/latency readiness. This is deliberately evidence-first: deepen provider-specific bridge behavior only after local dogfood shows which runtime gaps matter.

## Product Architecture

### Planning Governance Layer
- plan authoring
- reviewer and adversarial reviewer loops
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
- author/reviewer/adversarial-reviewer roles are modeled
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

- [v1.x Reference Upgrade Master Plan](/Users/abab/Desktop/Agent-Orchestratoar/docs/process/v1x-reference-upgrade-master-plan.md)

Status: **completed for the v1.x reference-informed upgrade scope**.

The completed upgrade borrows targeted strengths from local reference repositories while preserving Agent Orchestrator's boundaries: it strengthens job observability, review/rescue/setup action grammar, context recovery, packaging discipline, and evidence reporting without turning the product into a bridge, session manager, or plugin marketplace.

## v1.x Convergence

The repository now extends the completed v1 baseline with:

- fallback-aware provider health snapshots for `codex`, `claude`, and `mock`
- controlled review policy CLI overrides that preserve `auto` defaults
- evidence CLI commands for built-in benchmarks, real task case files, and markdown phase reports
- expanded real-task dogfood reports with recovery, runtime fidelity, compliance blocking, postmortem, and cost/latency readiness metrics
- an expanded Agent Team Console for provenance, governance, review policy, fallback, compliance, events, messages, work graph, and job controls
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

- [v1.0 Candidate Release Checklist](/Users/abab/Desktop/Agent-Orchestratoar/docs/process/v1-candidate-release-checklist.md)
- [v1.x Release Readiness](/Users/abab/Desktop/Agent-Orchestratoar/docs/process/v1x-release-readiness.md) remains the short canonical process document.

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
