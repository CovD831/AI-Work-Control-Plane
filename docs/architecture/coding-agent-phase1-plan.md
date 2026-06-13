# Coding Agent Phase 1 Plan

## Objective

Phase 1 upgrades the current project from a planning-oriented orchestration surface into the first stable skeleton of a coding-agent system.

This phase does **not** attempt to finish the new coding agent. Instead, it creates the architectural seams needed to preserve the current control/governance stack while isolating the legacy execution flow and introducing new entry/runtime abstractions.

Phase 1 is complete when the repository supports:

- a lightweight task-routing entry before heavy planning or execution,
- an explicit execution-runtime abstraction,
- the current execution workflow wrapped as a legacy runtime mode,
- a CLI main path that enters through the new routing skeleton,
- existing control/governance behavior preserved.

## Why This Phase Exists

The current repository already contains strong assets for a future coding agent:

- structured clarify logic,
- control-plane state and artifact tracking,
- planning governance,
- approval and recovery surfaces,
- operator-facing dashboard and summaries.

The weakest part of the current architecture is the execution layer. It is still shaped around a fixed Codex/Claude workflow, which is useful as a compatibility path but not sufficient as the long-term execution runtime for a coding agent.

Phase 1 therefore focuses on **reframing the architecture without discarding working behavior**.

## Target Architecture

The long-term coding-agent system is organized into five layers:

1. `intake`
   - lightweight task routing,
   - intent intake,
   - adaptive clarify policy.
2. `strategy`
   - execution-strategy selection,
   - optional task expansion after intake,
   - future replacement for the current rigid decompose templates.
3. `session`
   - durable session state,
   - turn boundaries,
   - context snapshots,
   - recovery-aware execution coordination.
4. `execution`
   - repo exploration,
   - code editing,
   - command/test verification,
   - repair and retry loops,
   - legacy execution compatibility.
5. `governance`
   - control plane,
   - approval,
   - evidence,
   - recovery summaries,
   - UI/operator visibility.

Phase 1 only establishes the first and fourth layers as explicit seams. The session and strategy layers remain mostly skeletal in this phase.

## Current Module Mapping

### Governance / Control Plane Assets To Preserve

These modules are already strong and remain authoritative in Phase 1:

- `src/agent_orchestrator/control_plane.py`
- `src/agent_orchestrator/control_plane_*`
- `src/agent_orchestrator/planning.py`
- `src/agent_orchestrator/planning_governance.py`
- `src/agent_orchestrator/ui_service.py`
- `src/agent_orchestrator/ui_server.py`
- `src/agent_orchestrator/cli_team.py`
- `src/agent_orchestrator/cli_presenters.py`

These modules should remain the source of truth for:

- planning session state,
- governance snapshot generation,
- approval and evidence flows,
- recovery visibility,
- operator-facing summaries and dashboards.

### Existing Intake Logic To Reuse

The current clarify logic lives in:

- `src/agent_orchestrator/adapters.py`

Key reusable assets:

- `MockClaudePlanner`
- clarify-state framing and slot filling
- `TaskContract` generation

In Phase 1, this logic is **not deleted**. It is re-positioned as an `Intent Intake` capability that can be called conditionally after routing.

### Existing Strategy Logic To Retain Temporarily

The current decomposition logic also lives in:

- `src/agent_orchestrator/adapters.py`

Key current behavior:

- task-type template expansion,
- decomposition candidates,
- decomposition scoring and explanation.

In Phase 1, this logic is retained for compatibility, but it stops acting like the system's only entry strategy. It becomes a legacy strategy expander that runs after routing/intake when needed.

### Existing Execution Flow To Isolate

The current execution path is spread across:

- `src/agent_orchestrator/orchestrator.py`
- `src/agent_orchestrator/adapters.py`
- `src/agent_orchestrator/cli.py`
- provider/runtime-related modules such as `jobs.py`, `command.py`, `tmux_runtime.py`

Key current execution components:

- `MockCodexWorker`
- `MockClaudeReviewRescue`
- `RuntimeProviderAdapter`
- `RuntimeProviderReviewRescueAdapter`
- `Orchestrator`

In Phase 1, these are treated as the **legacy runtime path**. They remain usable but should no longer define the future architecture.

## Phase 1 Scope

### In Scope

- Introduce a lightweight task router before heavy clarify/decompose behavior.
- Define a new execution-runtime abstraction.
- Wrap the current execution path as `legacy` execution mode.
- Route the CLI main path through the new entry skeleton.
- Preserve current control/governance behavior.
- Add tests for the new entry abstractions and compatibility path.

### Out of Scope

- Full rewrite of the execution loop.
- Repo explorer implementation.
- Dynamic context builder.
- Repair loop.
- Multi-agent runtime.
- Major UI redesign.
- Full `decompose` rewrite.
- Full session-runtime implementation.

## Phase 1 Deliverables

### 1. New Intake Skeleton

Add a new intake package:

- `src/agent_orchestrator/intake/models.py`
- `src/agent_orchestrator/intake/task_router.py`
- `src/agent_orchestrator/intake/intent_intake.py`

Expected Phase 1 models:

- `TaskKind`
- `ClarifyPolicy`
- `ExecutionMode`
- `TaskRouterResult`
- `IntentIntakeResult`

Expected Phase 1 behavior:

- all raw CLI task requests are first inspected by `TaskRouter`,
- router decides whether clarify should be skipped, lightly applied, or deeply applied,
- router selects an execution mode,
- clarify/intake remains reusable but is no longer assumed to be mandatory.

### 2. Execution Runtime Abstraction

Add a new execution package:

- `src/agent_orchestrator/execution/models.py`
- `src/agent_orchestrator/execution/runtime.py`
- `src/agent_orchestrator/execution/legacy_runtime.py`

Expected Phase 1 abstractions:

- `ExecutionRequest`
- `ExecutionResult`
- `ExecutionRuntime`
- `LegacyExecutionRuntime`

Expected Phase 1 behavior:

- the current orchestration/execution flow can be called through the runtime abstraction,
- the CLI no longer depends directly on legacy execution implementation details.

### 3. CLI Entry Skeleton

Update:

- `src/agent_orchestrator/cli.py`

Expected Phase 1 behavior:

- `run` and `start` requests enter through task routing,
- clarify is triggered by policy rather than by default assumption,
- the execution mode determines whether the request uses legacy behavior,
- no Phase 1 behavior should break the `team` governance command family.

### 4. Compatibility-Preserving Test Coverage

Add or update tests for:

- task routing,
- clarify policy selection,
- legacy runtime compatibility,
- CLI routing path.

Expected regression coverage:

- `tests/test_adapters.py`
- `tests/test_control_plane.py`
- `tests/test_ui_service.py`
- new intake/execution tests.

## Phase 1 Design Decisions

### Decision 1: Route First, Clarify Second

Every user request should pass through a lightweight router first.

This router is intentionally cheaper and shallower than the current clarify logic. Its purpose is not to produce a full execution contract. Its purpose is to decide:

- whether this is a coding task,
- what type of task it is,
- whether clarify is needed,
- which execution mode should handle it.

### Decision 2: Keep Clarify, But Make It Conditional

Clarify remains an important asset and should not be removed.

However, Phase 1 changes its role:

- from mandatory first step,
- to adaptive intake capability.

This allows low-ambiguity tasks to avoid heavy pre-processing while preserving stronger intent structuring for migrations, investigations, or ambiguous requests.

### Decision 3: Preserve Decompose, But Downgrade Its Responsibility

The current `decompose` implementation is not deleted in Phase 1.

However, it should stop acting like:

- the primary task router,
- the universal strategy selector.

Instead, it becomes a compatibility path for strategy expansion after routing/intake.

### Decision 4: Do Not Rewrite Governance In Phase 1

The control plane and governance plane already contain the strongest differentiated value in the repository.

Phase 1 should avoid destabilizing:

- session governance,
- approval semantics,
- evidence surfaces,
- recovery views,
- operator dashboards.

The new architecture should adapt around these assets, not replace them.

## Implementation Sequence

1. Write this Phase 1 architecture document and use it as the source of truth.
2. Add intake models and router.
3. Add execution abstraction and legacy runtime wrapper.
4. Thread the CLI `run` path through the new router and optional intake.
5. Add tests and run regression checks.

## Phase 1 Acceptance Criteria

Phase 1 is accepted when all of the following are true:

- a documented Phase 1 architecture exists in the repository,
- a lightweight task router exists and classifies core task types,
- clarify is no longer assumed to be mandatory for every request,
- a new execution runtime abstraction exists,
- the current execution flow runs through `LegacyExecutionRuntime`,
- the CLI `run` path enters through the new routing skeleton,
- governance/control-plane command paths still work,
- targeted regression tests pass.

## Phase 1 Non-Goals

The following should explicitly remain unfinished at the end of this phase:

- a new autonomous coding execution loop,
- context-pack building for repository exploration,
- structured repair/retry loops,
- session-runtime durability beyond current planning/control-plane persistence,
- UI changes that depend on the future execution event model.

That unfinished state is acceptable. Phase 1 succeeds by creating the architecture seams that make those later phases practical.
