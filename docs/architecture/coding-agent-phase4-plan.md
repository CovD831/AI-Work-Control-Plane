# Coding Agent Phase 4 Plan

## Objective

Phase 4 introduces the first real non-legacy coding-agent execution runtime.

The architectural change in this phase is:

- intake still classifies the task,
- clarify still runs only when route policy requires it,
- strategy still selects how the task should be approached,
- session runtime still owns turn continuity,
- execution can now choose between:
  - `legacy`
  - `coding_agent`

This phase is the first time the repository gains a true execution backend that does not simply hand off to the old orchestration loop.

## Completion Note

Phase 4 is complete in the repository, but this document should now be read as a historical Phase 4 architecture record rather than a full description of the repository's current execution capabilities.

What Phase 4 delivered:

- a real `coding_agent` runtime path,
- direct repo exploration,
- context assembly,
- runtime selection through CLI routing,
- structured verification output seams.

What Phase 4 explicitly did **not** finish:

- real edit application,
- post-edit completion loops,
- proof that code changes were actually applied.

That remaining work is now tracked as a separate later phase in the master plan so the repository state and the architecture documents do not overclaim runtime completeness.

Repository checkpoint update:

- the repository has since moved beyond these original MVP assumptions,
- bounded real edit application now exists,
- approval gating and resume are now part of live execution behavior,
- execution state persistence, artifact externalization, and step-level runtime events are now present,
- a stage-cursor execution kernel and explicit next-step contracts now exist,
- continuation-aware resume now restores applied changes, verification context, repair summaries, and planned verification commands,
- candidate selection now also reuses explicit stage-strategy context on the main planning path, reducing leftover ranking glue from the earlier stage-registry transition,
- edit and verify stage execution now also dispatch outcome semantics through strategy-level helpers, reducing direct outcome-field plumbing inside the stage executors themselves,
- the remaining gaps are mainly around richer step-loop behavior, stronger context compression, and broader long-horizon completion logic.

## Why Phase 4 Exists

After Phase 3, the repository already has:

- intake,
- clarify,
- strategy planning,
- durable session seams,
- a legacy execution runtime compatibility wrapper.

What it still lacks is a real coding-agent runtime that can:

- inspect repository context before execution,
- build a structured context package,
- produce a bounded implementation/edit intent,
- run verification commands or checks,
- return a structured execution result without going through the old work-unit orchestration path.

Without that, the project still has an execution abstraction but only one real executor.

## Architectural Decision

Phase 4 adds a new execution path behind the existing execution abstraction.

The repository will therefore distinguish:

### 1. Legacy Runtime

Purpose:

- preserve current orchestration behavior,
- remain available as compatibility fallback,
- continue serving governance-sensitive existing flows.

### 2. Coding-Agent Runtime MVP

Purpose:

- explore the repo directly,
- assemble execution context directly,
- produce a bounded execution plan directly,
- run a minimal verification pass directly,
- report its work as a structured execution payload.

This runtime should be intentionally narrow in its first cut. It is acceptable for Phase 4 to prefer safe reporting and verification over aggressive autonomous edits.

## Phase 4 Deliverables

Phase 4 should introduce:

- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `src/agent_orchestrator/execution/coding_components.py`
- targeted tests for coding-agent runtime selection and behavior

It will also likely require small, controlled updates to:

- `src/agent_orchestrator/execution/__init__.py`
- `src/agent_orchestrator/cli.py`
- `src/agent_orchestrator/intake/task_router.py`
- existing tests that currently assume all executable tasks route to `legacy`

## New Phase 4 Components

### `RepoExplorer`

Responsibilities:

- inspect the repository root,
- identify likely relevant files from explicit path hints,
- gather a small bounded file/sample summary,
- expose a deterministic exploration report for tests.

The first cut should be lightweight and local-only. It does not need symbol indexing or advanced semantic search yet.

### `ContextBuilder`

Responsibilities:

- combine route, clarify, strategy, session snapshot, and repo exploration,
- produce a compact execution context package,
- record the context boundaries used by the runtime.

### `EditExecutor`

Responsibilities:

- define the seam where direct edits will later happen,
- in Phase 4 MVP, generate or record a bounded implementation intent and optional patch plan,
- avoid pretending to have applied real edits when no real edit occurred.

The first implementation may be report-first rather than patch-first, as long as the seam is real and the output is structured.

Repository checkpoint:

- this was the original Phase 4 stopping point,
- `EditExecutor` began as a bounded implementation-intent and patch-planning seam,
- the current repository has since evolved beyond this checkpoint and now applies bounded edits through the governed execution path.

### `CommandRunner`

Responsibilities:

- run minimal local verification commands when appropriate,
- normalize result payloads,
- remain bounded and deterministic in tests.

This phase should reuse the existing command abstraction rather than introducing another process runner.

### `VerifyLoop`

Responsibilities:

- interpret verification output,
- summarize whether verification passed, failed, or was skipped,
- expose structured verification artifacts in the runtime result.

This phase does not include repair/retry loops. It only establishes the verification seam.

## Runtime Behavior

The first `coding_agent` runtime should support a bounded synchronous execution path:

1. read the session/context snapshot from the request
2. explore the repository
3. build an execution context package
4. derive a minimal implementation/edit intent
5. run a bounded verification step when safe
6. return a structured `ExecutionResult`

Async behavior may remain a thin compatibility wrapper if needed, but sync execution must be real.

## CLI Integration

CLI execution should now be able to choose runtime based on route and explicit selection.

Phase 4 should allow:

- `legacy` for compatibility-sensitive tasks,
- `coding_agent` for direct-fix and general-coding tasks that do not require the old decomposition-driven flow,
- `legacy` fallback for migration or confirmation-sensitive tasks in the first MVP.

This can be implemented through explicit runtime selection logic without rewriting the intake layer.

## Explicit Non-Goals

Phase 4 must not drift into:

- autonomous repair loops,
- advanced branching search,
- multi-agent execution graphs,
- external protocol bridges,
- replacing control-plane truth,
- pretending to have edited files when no real edit has occurred.

## Acceptance Criteria

Phase 4 is complete when:

- a new `coding_agent` runtime exists behind the execution abstraction,
- CLI execution can select between `legacy` and `coding_agent`,
- the coding-agent runtime performs direct repo exploration and context assembly,
- the runtime returns structured verification information,
- governance/control-plane behavior remains compatible for existing flows,
- targeted regression tests pass.

Clarification:

- Phase 4 completeness does **not** mean the runtime is already a full task-completing coding loop,
- it means the repository gained a real non-legacy execution backend with the right seams in place for later closure work,
- later repository work has already filled in part of that closure path, but the fully mature target-mode runtime still remains a later evolution.

## Targeted Test Slice

Phase 4 should be verified with at least:

```bash
pytest tests/test_coding_agent_runtime.py tests/test_task_router.py tests/test_cli.py tests/test_control_plane.py tests/test_ui_service.py -q
```

If execution payload shape changes materially, also include:

```bash
pytest tests/test_execution_runtime_legacy.py tests/test_cli_presenters.py -q
```
