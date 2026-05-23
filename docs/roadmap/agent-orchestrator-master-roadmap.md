# Agent Orchestrator Master Roadmap

## Summary

This roadmap defines the path from the current control-plane-oriented MVP to the intended v1 product: a local-first CLI orchestration system with two first-class layers:

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

The roadmap is organized as **4 product stages**. These stages replace the previous single-line strategy-only product narrative. Execution strategy remains essential, but it now lives inside a larger product whose default behavior is: `task -> planning governance loop -> approved plan -> execution strategy -> synchronized artifacts`.

## Final Product Shape

The target product is:

- a local CLI tool as the only first-class v1 product surface
- optimized for the author's real workflows before broader external packaging
- centered on plan governance before execution
- centered on strategy decisions during execution
- able to call replaceable provider, bridge, runtime, and job-backend plugins
- able to emit structured run artifacts and synchronized documentation updates
- able to enforce project rules through hooks and loopback checks, not prompt guidance alone

The product is explicitly **not** trying to become:

- a full bridge product
- a full session manager or tmux orchestrator
- a provider-specific shell that wins on runtime features alone

## Current State

- The project already has a strategy-oriented control plane built around `mode + agent_enabled + depth + provider_flow`.
- Failure handling already includes depth-first escalation, partial rescue, and dependency-aware replay behavior.
- Early decision contract work exists for execution artifacts.
- The repository now has a basic planning governance loop with persisted plan sessions, dual-model review rounds, gap closure, approval gating, and approved-plan-linked execution handoff.
- Narrow documentation synchronization and hook-based compliance checks now exist for the internal-default workflow, but broader coverage and harder enforcement are still incomplete.
- The old roadmap view overfit the execution strategy line and understated planning governance as a product layer.

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
