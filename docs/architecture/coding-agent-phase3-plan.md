# Coding Agent Phase 3 Plan

## Objective

Phase 3 introduces a durable session layer for the new coding-agent architecture.

The architectural change in this phase is:

- intake still decides whether a request is executable,
- clarify still runs only when the route requires it,
- strategy planning still chooses how execution should proceed,
- session runtime now owns execution continuity across turns,
- legacy orchestration remains the executor behind the new session seam.

This phase does not build the new coding runtime yet. It prepares the execution stack so Phase 4 can replace legacy execution without having to invent session semantics at the same time.

## Why Phase 3 Exists

After Phase 2, the repository already has:

- a task-router seam,
- adaptive clarify intake,
- a strategy layer,
- a legacy execution runtime wrapper.

What it still lacks is a durable concept of:

- "this is the same agent session",
- "this is a new turn within that session",
- "this execution used this context snapshot",
- "this run can be resumed from this prior session state".

Without that seam, later coding-agent work would still be trapped inside a direct call stack:

- CLI request
- planner clarify
- strategy compatibility expansion
- orchestration run

That stack is acceptable for the legacy path, but it is too weak for a real coding agent that needs continuity, resumability, and operator-visible context boundaries.

## Architectural Decision

Phase 3 adds a session layer without moving control-plane ownership.

The repository will therefore distinguish:

### 1. Control-Plane Truth

Still owned by existing run and plan artifacts.

Responsibilities:

- durable operator-visible state,
- approvals,
- evidence,
- recovery,
- linked execution provenance.

### 2. Session Runtime Semantics

New in this phase.

Responsibilities:

- create session ids,
- create turn ids,
- snapshot the active execution context,
- track linked execution runs,
- support fresh versus resume-oriented turns.

### 3. Execution Compatibility

Still owned by the legacy execution runtime during Phase 3.

Responsibilities:

- accept sessionized execution requests,
- run the existing orchestration flow,
- report result metadata back to the session runtime.

## Phase 3 Deliverables

Phase 3 should introduce:

- `src/agent_orchestrator/session/models.py`
- `src/agent_orchestrator/session/runtime.py`
- `src/agent_orchestrator/session/__init__.py`
- `tests/test_session_runtime.py`

It will also likely require small, controlled updates to:

- `src/agent_orchestrator/execution/models.py`
- `src/agent_orchestrator/execution/legacy_runtime.py`
- `src/agent_orchestrator/cli.py`
- selected presenter or summary surfaces that expose execution metadata

## New Core Models

### `AgentSession`

Represents the durable identity for a coding-agent interaction.

Initial fields should include:

- `session_id`
- `status`
- `created_at`
- `updated_at`
- `current_turn_id`
- `turn_ids`
- `origin`
- `metadata`

Purpose:

- lets future runtimes attach multiple execution turns to one logical agent session,
- creates a stable anchor for resume and continuity,
- keeps session semantics separate from provider-native conversation state.

### `SessionTurn`

Represents one execution-triggering user turn or system continuation.

Initial fields should include:

- `turn_id`
- `session_id`
- `requirement`
- `status`
- `route`
- `clarify_summary`
- `strategy_summary`
- `linked_run_id`
- `resume_from_turn_id`
- `context_snapshot_id`
- `metadata`

Purpose:

- records the boundary between turns,
- stores the structured decision path taken before execution,
- gives governance surfaces a direct explanation of why this turn ran the way it did.

### `ContextSnapshot`

Represents the structured execution context in force for one turn.

Initial fields should include:

- `snapshot_id`
- `session_id`
- `turn_id`
- `task_contract`
- `selected_execution_strategy`
- `compatibility_metadata`
- `resume_kind`
- `metadata`

Purpose:

- preserves the pre-execution state that later phases will feed into repo exploration and verification,
- prevents hidden coupling between ephemeral model context and durable runtime state,
- gives future resume logic something concrete to reload.

### `ExecutionActivity`

Represents a linked execution event recorded by the session runtime.

Initial fields should include:

- `activity_id`
- `session_id`
- `turn_id`
- `runtime_name`
- `linked_run_id`
- `status`
- `accepted`
- `summary`
- `metadata`

Purpose:

- records how a turn mapped to an actual runtime invocation,
- provides a stable bridge from session history to legacy run artifacts,
- prepares the event shape later phases can normalize for governance.

## Session Runtime Responsibilities

`SessionRuntime` should begin as a compatibility shell, not as a fully durable database-backed subsystem.

The first implementation should support:

1. `start_session(...)`
2. `start_turn(...)`
3. `record_activity(...)`
4. `complete_turn(...)`
5. `attach_run_result(...)`
6. `get_session(...)`
7. `get_turn(...)`

The runtime may initially persist through simple repository artifacts or an in-memory-plus-file pattern consistent with the rest of the project. The important constraint is that it must not create a competing truth source to the control plane.

## Integration Plan

### CLI Integration

The CLI `run` and `start` path should evolve from:

- route
- optional clarify
- legacy execution runtime

to:

- route
- optional clarify
- strategy planning or strategy-ready payload derivation
- session runtime `start_session/start_turn`
- legacy execution runtime
- session runtime activity/result attachment

The CLI should still return the same user-facing behavior unless session metadata is being added to the payload.

### Execution Request Integration

`ExecutionRequest` should be extended with session-oriented fields such as:

- `session_id`
- `turn_id`
- `context_snapshot`
- `resume_kind`

These additions must remain optional enough that existing compatibility tests can be updated incrementally.

### Legacy Runtime Integration

`LegacyExecutionRuntime` should remain the executor, but it should accept the new request metadata and surface it back in `ExecutionResult`.

The goal is not to redesign legacy orchestration, only to make it session-aware.

### Governance Integration

Governance and summary layers should gain read-only visibility into:

- active session id,
- triggering turn id,
- linked run id,
- whether the turn was fresh or resumed,
- selected execution strategy from the context snapshot.

This visibility should appear in the existing payloads or summary dictionaries that already describe clarify and decomposition/strategy state.

## Explicit Non-Goals

Phase 3 must not drift into:

- repo exploration,
- code-edit execution loops,
- verification loops,
- repair loops,
- external agent protocol bridges,
- multi-agent coding execution.

Those belong to later phases.

## Implementation Order

### Step 1: Define Session Models

- create session dataclasses,
- add `to_dict` helpers,
- keep fields narrow and composable,
- avoid provider-specific assumptions.

### Step 2: Add Session Runtime

- implement the compatibility runtime,
- create session and turn records,
- attach context snapshots and execution activities,
- make serialization deterministic for tests.

### Step 3: Thread Session Metadata Through Execution

- extend execution request and result contracts,
- update CLI entry glue,
- keep no-execution routes unchanged.

### Step 4: Expose Minimal Session Summaries

- add session metadata to relevant payloads,
- preserve existing summary shapes where possible,
- avoid breaking team-governance workflows.

### Step 5: Verify With Targeted Tests

- unit-test session model/runtime behavior,
- regression-test CLI compatibility,
- regression-test governance/control-plane surfaces that inspect execution summaries.

## Acceptance Criteria

Phase 3 is complete when:

- a dedicated `session` package exists,
- execution requests can carry session and turn identity,
- each execution turn records route, clarify, strategy, and linked run context,
- the legacy runtime can participate in a sessionized execution path,
- existing governance surfaces can read the new metadata without becoming the source of truth,
- targeted regression tests pass.

## Targeted Test Slice

Phase 3 should be verified with at least:

```bash
pytest tests/test_session_runtime.py tests/test_execution_runtime_legacy.py tests/test_cli.py tests/test_control_plane.py tests/test_ui_service.py -q
```

If Phase 3 touches strategy summaries, also include:

```bash
pytest tests/test_strategy_planner.py -q
```

## Goal-Mode Readiness

This plan is ready for goal mode because it now fixes:

- the package boundary,
- the required new models,
- the exact compatibility seam,
- the intended CLI and runtime integration points,
- the test slice,
- the non-goals that prevent accidental Phase 4 spillover.

## Proposed Goal Objective

Recommended next scoped goal:

> Complete Phase 3 of the coding-agent architecture refactor: add session-layer foundations, define AgentSession / SessionTurn / ContextSnapshot / ExecutionActivity abstractions, connect execution requests to session semantics, and preserve control/governance behavior through targeted regression coverage.
