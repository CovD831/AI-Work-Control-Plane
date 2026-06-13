# Coding Agent Target-Mode Evolution Plan

## Objective

This document defines how the current repository should evolve from the existing Phase 4/5 coding-agent runtime into the target mode needed for a real governed coding agent.

The target mode is:

> a coding-agent runtime where execution is step-based, side effects are centrally governed, long-context work is structurally managed, approvals can interrupt execution safely, and the control plane remains the system of record for evidence, recovery, and operator visibility.

This plan is intentionally grounded in the current repository state. It does not assume a greenfield rewrite.

## Why A New Plan Is Needed

The repository already contains important pieces of the target architecture:

- a real `coding_agent` execution path,
- a separate control-plane artifact/evidence system,
- approval persistence,
- runtime event summaries,
- memory and knowledge stores,
- orchestration and durable run storage.

However, the current `coding_agent` runtime is still shaped more like a bounded execution pipeline with growing step semantics than a fully general coding-agent runtime loop.

Today the core flow is effectively:

`explore -> build context -> build intent -> apply -> verify`

That shape was appropriate for the MVP phase, but it becomes a limiting factor for:

- approval-aware interruption,
- step-level recovery,
- structured context compression,
- large-result externalization,
- unified action auditing,
- future multi-step or multi-agent execution.

The required next step is therefore not a repository-wide rewrite. It is a focused evolution of the execution layer plus a tighter connection between execution and the existing control-plane surfaces.

## Target-Mode Principles

The following principles should guide all implementation work.

### 1. Execution Owns The Agent Loop

The execution runtime should own the live coding loop:

`build step context -> choose action -> execute action -> capture observation -> decide next step`

This loop must not be simulated by a one-shot pipeline once the runtime becomes stateful.

### 2. Control Plane Remains The Source Of Truth

Durable truth must continue to live in control-plane artifacts, approvals, run storage, evidence bundles, and memory records.

Execution may generate and consume runtime state, but it must not create an alternate canonical state store outside existing governance structures.

### 3. Models Propose; Runtime Decides

Any action with side effects must be proposed by the execution runtime but accepted, blocked, or gated by explicit runtime policies and control-plane approvals.

This especially applies to:

- writing files,
- replacing existing content,
- deleting content,
- running commands,
- reading sensitive paths,
- invoking future external tools.

### 4. Context Management Must Be Structural

Long-running tasks must not depend on naive transcript growth.

The runtime should preserve:

- recent steps,
- summarized historical steps,
- paired action/result structure,
- externalized large artifacts,
- promoted memory facts.

### 5. Recovery Must Happen At Step Granularity

Durable run storage is already present in the repository, but target mode requires recovery at the step/action level rather than only at the top-level run boundary.

## Current-State Assessment

The current repository is already well-positioned for this work.

### Strengths Already Present

- `ExecutionRuntime` gives a clean runtime abstraction seam.
- `CodingAgentExecutionRuntime` already exists as a separate runtime.
- `control_plane_approvals.py` already models durable approval items.
- `control_plane_runtime.py` already exposes runtime event summaries and liveness views.
- `memory.py` already provides append-only memory and knowledge stores.
- `orchestrator.py` and `run_store.py` already provide durable orchestration/run handling.
- execution models now include step, action, observation, approval, and artifact-reference primitives.
- side-effecting edit and verification paths now converge through a unified `ActionExecutor`.
- approval can now block live execution and resume from persisted execution state.
- execution artifacts are now externalized for repository exploration and command output.
- step-level execution events and execution-history summaries are now visible to governance surfaces.
- the coding runtime now advances through an explicit stage-cursor kernel rather than only nested pipeline conditionals.
- stage planning and stage execution are now separated by explicit kernel planning/dispatch structures rather than a single stage-branching block.
- planner context is now materialized per stage so selection traces carry explicit decision inputs such as resume kind, route risk, operation paths, target paths, and remaining retry budget.
- approval requirements, approval resolution state, and action feasibility are now pulled into planner context so stage selection can explicitly choose `advance`, `pause`, or `block`.
- next-stage proposals are now explicit runtime planning artifacts, so the planner records not only the current-stage disposition but also the proposed next hop for each kernel step.
- next-stage proposals now carry candidate sets plus the selected candidate, so the runtime records both enumerated options and the chosen next hop for each kernel step.
- proposal construction itself now also begins to route through a shared proposal-level builder, so selected-candidate semantics are no longer reassembled ad hoc at each proposal callsite.
- stage-specific candidate generation now also begins to route through a registry-like generator entrypoint, reducing direct stage-dispatch branching inside proposal construction.
- candidate generation now begins to consume continuation history such as applied-change count, recent observations, verification status, and repair outcome rather than depending only on a fixed stage template.
- candidate selection now begins to rank verify-stage options using observation and repair signals when continuation history is strong enough, rather than always taking the first templated candidate.
- candidate selection now also begins to rank low-risk prepare-only edit options using observation and feasibility signals, extending evidence-driven next-hop choice beyond verification.
- candidate selection now also begins to rank low-risk explore options using repo/ctx observations, allowing evidence-driven completion of read-only paths without always entering edit.
- stage-specific ranking rules are now routed through a more unified candidate-ranking strategy entrypoint, and that ranking dispatch now also begins to use registry-like strategy lookup rather than only stage-specific branching.
- selected-candidate ranking now also accepts explicit stage-strategy context from proposal construction, so candidate selection no longer needs to rediscover ranking behavior from stage-only lookup on the main planning path.
- edit/verify execution now also enters pause/block/continue/complete outcomes through strategy-level helper methods, so stage executors rely less on raw outcome-field plumbing and more directly on the stage contract they are dispatching through.
- next-stage candidate generation now also begins to route through a shared strategy entrypoint, even though stage-specific candidate templates still exist underneath.
- candidate construction itself now begins to share helper-level structure, reducing repeated per-stage candidate boilerplate even though higher-level stage templates still remain.
- repeated two-candidate stage patterns now begin to share helper-level template construction, reducing duplicated “primary path vs fallback path” boilerplate across stages.
- those repeated patterns now also begin to share higher-level “path vs terminal path”, “advance vs complete”, “complete vs retry”, and “block vs retry” helpers, making candidate templates read more like planning intent than raw object assembly.
- approval-gated and history-satisfied candidate patterns now also begin to use semantic builders, so stage templates increasingly describe planning intent directly instead of assembling raw candidate details.
- verify-stage terminal candidates now begin to synthesize candidate identity and rationale from planner context rather than relying only on fixed literal templates.
- edit-stage terminal completion candidates now also begin to synthesize identity and rationale from planner context in low-risk prepare-only paths, rather than always reusing a single fixed terminal template.
- explore-stage terminal completion candidates now also begin to synthesize identity and rationale from planner context in low-risk read-only paths, rather than always reusing a single fixed terminal template.
- persisted continuation state now includes compressed context, next-step contracts, resume context, applied changes, and recent observations.
- verification resume can now reuse planned verification commands and remaining retry budget from persisted execution state.
- exhausted verification recovery can now directly select a blocked continuation path instead of blindly rerunning verification.

### Gaps Between Current State And Target Mode

- the execution runtime is now kernelized behind explicit stage planning, dispatch, planner-context traces, approval-aware pause/block selection, and candidate-based next-stage proposals that increasingly use continuation history plus verify/edit/explore evidence ranking through shared generation/ranking strategy entrypoints, registry-like ranking dispatch, shared proposal-level builders, registry-like stage generators, and emerging per-stage strategy objects that now also build proposals, stage plans, execution dispatch, selected-candidate ranking flow, and stage-level outcome dispatch through a more stable strategy-map structure, with simpler explore/terminal execution semantics plus shared continue-stage semantics, edit pause/block/apply, and verify pause/blocked-resume/terminal outcomes beginning to collapse into shared executor meanings, while verify terminal acceptance/completion decisions also begin to collapse into shared semantic helpers, and those shared execution helpers now begin to route through a lower-level shared stage-outcome builder and stage-owned outcome-semantics namespaces now used by both edit and verify, with stage plans now explicitly carrying stage-strategy context and proposal/candidate/ranking construction now also accepting explicit strategy context so planning/execution paths reuse the same stage contract instead of re-looking it up, while edit/verify strategies now directly binding the core stage execution functions instead of going through transitional wrappers, plus shared candidate/template helpers, including path-vs-terminal, advance-vs-complete, complete-vs-retry, block-vs-retry, and approval/history semantic builders, with initial context-driven candidate synthesis now appearing in verify plus low-risk edit/explore terminal paths, but it still advances through a fixed three-stage flow rather than a more flexible dynamic step planner,
- context packaging is static rather than layered and compressible,
- recovery is now materially better at step level, but broader planner inputs, step selection, and action selection are still narrow and runtime-specific,
- broader tool/action ecosystems and richer completion behavior are still intentionally narrow.

## Progress Since Initial Draft

Since this plan was first written, several target-mode foundation pieces have already landed in code:

- explicit `ExecutionStep`, `ActionRequest`, `ActionResult`, `ObservationRecord`, `PendingApprovalState`, and `ArtifactReference` models,
- a unified `ActionExecutor` used by edit application and verification execution,
- approval gating that can return blocked execution results and resume after approval resolution,
- persisted execution state and resume contracts for live execution continuation,
- artifact externalization for verification output and repository exploration,
- step-level runtime event emission plus structured execution-history summaries for operator surfaces.
- a stage-cursor execution kernel that can resume from persisted stage boundaries,
- explicit stage planning and dispatch seams that separate stage selection from stage execution,
- persisted planner-context traces that make step and action selection inputs visible to control-plane recovery and operator inspection,
- compressed execution context plus explicit next-step contracts,
- persisted resume context containing recent observations, verification summaries, repair summaries, and planned verification commands,
- continuation-aware verification behavior that can reuse prior verification commands, consume remaining retry budget, and directly block when retries are exhausted.

This means the document should now be read as a next-stage evolution plan built on top of those foundations, not as a proposal for a runtime that is still entirely future-state.

## What Should Change And What Should Not

### What Should Not Be Rewritten

The following areas should be preserved and extended, not replaced:

- control-plane artifact contracts,
- approval persistence model,
- event stream generation,
- memory and knowledge stores,
- orchestration/run storage,
- governance-facing UI and summaries.

### What Must Evolve

The main architectural evolution should happen inside `src/agent_orchestrator/execution/`.

In practical terms, the repository should move:

- from a fixed execution pipeline,
- to a step-based runtime kernel with governed action execution.

This is an execution-layer refactor, but not an execution-layer-only change. Some control-plane interfaces must be connected more directly into live execution.

## Architecture Changes Required

## 1. Introduce A Unified Action Execution Gateway

### Problem

The original code allowed side effects to happen inside specialized components such as edit application and verification execution.

That makes it difficult to apply one consistent policy for:

- workspace restrictions,
- risk classification,
- approval gating,
- audit logging,
- artifact externalization,
- structured failure handling.

### Change

Add a new execution-layer component such as:

- `ActionExecutor`, or
- `ToolExecutor`

This component should become the only path for action execution.

Repository checkpoint:

- this gateway now exists as `ActionExecutor`,
- remaining work is to broaden its coverage and make it the clearer universal runtime action boundary.

### Responsibilities

- validate action type and parameters,
- enforce workspace/path boundaries,
- classify action risk,
- create approval requests when needed,
- execute allowed actions,
- normalize action results,
- externalize oversized outputs,
- emit structured step/action events.

### Expected Impact

This is the key change that turns execution from “components that happen to do side effects” into “a governed runtime that performs actions”.

## 2. Replace Pipeline-Style Runtime Flow With Step-Based Runtime Flow

### Problem

`CodingAgentExecutionRuntime` currently performs a bounded sequence of operations and returns a single payload.

That shape is too rigid for:

- pending approvals,
- multi-step repair loops,
- explicit observation history,
- resumable execution.

### Change

Restructure `CodingAgentExecutionRuntime` into a loop that advances through discrete steps.

The conceptual loop should be:

1. load session/run/step context
2. construct current execution view
3. propose next action
4. execute action through the action gateway
5. record observation and artifacts
6. decide whether to continue, pause, block, or complete

### Expected Impact

This allows approvals, compression, retries, and recovery to become natural runtime behavior instead of exceptional cases layered on top.

## 3. Add First-Class Step, Action, And Observation Models

### Problem

The current execution models are adequate for an MVP result payload but too coarse for target-mode runtime behavior.

### Change

Extend `execution/models.py` with explicit runtime primitives such as:

- `ExecutionStep`
- `ActionRequest`
- `ActionResult`
- `ObservationRecord`
- `PendingApprovalState`
- `ArtifactReference`

The exact names may differ, but the structure should allow the runtime to persist and replay state safely.

### Expected Impact

This provides the data model foundation for resumability, structural context compression, and operator-visible traces.

## 4. Convert Approval Into A Live Execution Gate

### Problem

Approval persistence already existed, but target mode requires approval to be treated as a durable execution-time state transition everywhere it matters.

### Change

When a high-risk action is proposed, execution should:

1. create an approval item,
2. persist the pending step/action state,
3. return a blocked or awaiting-approval execution result,
4. resume from that point when approval is resolved.

### Initial High-Risk Action Set

- file mutation,
- command execution,
- overwrite-style replacement,
- future delete operations.

### Expected Impact

This turns approval from a reporting feature into a true runtime governance mechanism.

## 5. Externalize Large Results And Feed Back Summaries

### Problem

Large logs, wide file scans, and future tool results will quickly overwhelm execution payloads and prompt context if handled inline.

### Change

Add a standard mechanism where large results are:

- written to a durable artifact location,
- returned as summarized observations,
- referenced by artifact ids/paths in execution state.

### First Targets

- command stdout/stderr,
- repository exploration listings,
- future diff or patch previews.

Repository checkpoint:

- command output and repository exploration listings are already externalized,
- future diff, patch, and richer tool outputs should follow the same pattern.

### Expected Impact

This makes the runtime compatible with long-running tasks and controlled context growth.

## 6. Introduce Structural Context Governance

### Problem

The current context builder produces a static context package, but target mode needs layered context that can be compressed without breaking execution meaning.

### Change

Split runtime context into layers:

- task objective and constraints,
- current step context,
- recent observations,
- summarized history,
- promoted memory facts,
- artifact references.

Compression must preserve action/result pairing and never cut a causal chain in the middle.

### Expected Impact

This lays the groundwork for stable long-horizon coding behavior.

## 7. Add Step-Level Persistence And Recovery

### Problem

The repository already supports durable runs, and step-level recovery inside execution is now partially in place, but it remains underpowered for richer long-horizon loops.

### Change

Persist execution progress at a finer granularity, including:

- current step id,
- pending action,
- pending approval state,
- recent observations,
- artifact references,
- last successful verification state.

### Expected Impact

Resume becomes a continuation of execution state, not a best-effort restart.

## 8. Make Runtime Events Execution-Time Native

### Problem

The current runtime event stream is useful, but much of it is derived after the fact from stored artifacts.

### Change

Execution should emit structured events during runtime progression, such as:

- `step_started`
- `action_requested`
- `approval_requested`
- `action_completed`
- `artifact_externalized`
- `context_compressed`
- `verification_failed`
- `run_blocked`
- `run_completed`

### Expected Impact

This makes control-plane runtime visibility more faithful to actual execution behavior and reduces ambiguity during recovery or audit.

## Execution-Layer Changes Versus Cross-Layer Changes

One recurring design question is whether the required improvements belong only in the execution layer.

The answer is:

> most of the implementation belongs in execution, but the execution layer must be rewired to use control-plane governance as part of live runtime flow.

### Primarily Execution-Layer Work

- step loop implementation,
- action gateway,
- action/result/observation models,
- large-result handling,
- context packaging and compression,
- repair-loop state handling.

### Cross-Layer Integration Work

- approval creation and resume,
- runtime event emission,
- memory promotion,
- artifact registration,
- step-level recovery state persistence.

### Work That Should Stay Largely Unchanged

- top-level orchestration framing,
- existing control-plane artifact contracts,
- current UI and summary surfaces,
- governance-first repository positioning.

## Recommended Implementation Sequence

### Phase A: Action Gateway And Runtime Data Model

Introduce the unified action execution gateway and explicit step/action/observation models.

Primary files likely affected:

- `src/agent_orchestrator/execution/models.py`
- `src/agent_orchestrator/execution/coding_components.py`
- `src/agent_orchestrator/execution/coding_agent_runtime.py`

### Phase B: Step-Based Runtime Refactor

Refactor `CodingAgentExecutionRuntime` from pipeline execution into a step loop using the new action gateway.

Primary files likely affected:

- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `src/agent_orchestrator/execution/runtime.py`
- supporting tests

### Phase C: Approval And Event Integration

Connect execution to approval persistence and runtime event emission during live execution.

Primary files likely affected:

- `src/agent_orchestrator/control_plane_approvals.py`
- `src/agent_orchestrator/control_plane_runtime.py`
- execution runtime files

### Phase D: Artifact Externalization And Context Governance

Add large-result externalization, summarized observation feedback, and layered context compression.

Primary files likely affected:

- `src/agent_orchestrator/execution/coding_components.py`
- `src/agent_orchestrator/control_plane_artifacts.py`
- `src/agent_orchestrator/memory.py`

### Phase E: Step-Level Recovery And Measurement

Persist step-level execution state, then add mechanism and end-to-end evaluation slices for the new runtime.

Primary files likely affected:

- `src/agent_orchestrator/session/runtime.py`
- `src/agent_orchestrator/run_store.py`
- execution runtime files
- targeted tests

## Suggested Near-Term File Priorities

If implementation starts immediately, the highest-value file sequence is:

1. `src/agent_orchestrator/execution/models.py`
2. `src/agent_orchestrator/execution/coding_components.py`
3. `src/agent_orchestrator/execution/coding_agent_runtime.py`
4. `src/agent_orchestrator/control_plane_approvals.py`
5. `src/agent_orchestrator/control_plane_runtime.py`

## Verification Strategy

This evolution should not be considered complete based only on architecture changes. Each phase should be verified with targeted tests.

At minimum, verification should cover:

- action risk classification,
- workspace boundary enforcement,
- approval interruption and resume behavior,
- large-result externalization,
- structural context retention,
- step-level recovery,
- event emission integrity,
- runtime result compatibility where required.

## Acceptance Standard For Target Mode

The repository has meaningfully entered target mode when all of the following are true:

- the coding-agent runtime is step-based rather than only pipeline-based,
- all side effects flow through a unified governed execution gateway,
- high-risk actions can pause on approval and resume safely,
- large runtime outputs are externalized and summarized,
- context growth is managed structurally rather than by naive accumulation,
- step-level execution state can be recovered,
- control-plane views reflect live runtime progression rather than only post hoc summaries.

Until then, the repository should be treated as having strong target-mode foundations, but not yet target-mode runtime closure.
