# Coding Agent Phase 2 Plan

## Objective

Phase 2 replaces the repository's old decomposition-first framing with an explicit strategy layer.

The key architectural change is:

- task routing decides **what kind of request this is**,
- intent intake decides **how much clarification is needed**,
- strategy planning decides **how this task should be executed**,
- legacy decomposition is retained only as a compatibility expander for work-unit generation.

## Why Phase 2 Exists

After Phase 1, the repository already had:

- task routing,
- adaptive clarify entry,
- execution runtime abstraction,
- legacy runtime compatibility.

However, one important coupling still remained:

- the old `decompose` path still implicitly acted as both strategy selector and execution expander.

That design is too rigid for a coding agent because:

- strategy should be chosen before full task expansion,
- execution strategies are broader than fixed work-unit templates,
- future execution runtimes may not use the current work-unit expansion shape at all,
- governance should reason about high-level strategy separately from low-level template shape.

Phase 2 therefore adds an explicit strategy layer.

## Architectural Decision

From this phase onward, the repository distinguishes three separate responsibilities:

### 1. Task Routing

Implemented by the intake layer.

Responsibilities:

- classify request type,
- determine clarify depth,
- determine whether the request is executable,
- determine whether the request requires human confirmation.

### 2. Strategy Planning

Implemented by the strategy layer.

Responsibilities:

- select high-level execution strategy,
- explain why that strategy was chosen,
- preserve future room for dynamic execution planning,
- provide a stable seam between intake and execution.

### 3. Compatibility Expansion

Implemented by the current legacy decomposition logic.

Responsibilities:

- expand a strategy-compatible contract into work units,
- preserve existing pipeline behavior,
- serve as a backward-compatible bridge until the future execution layer no longer depends on template decomposition.

## New Phase 2 Artifacts

Phase 2 introduces:

- `src/agent_orchestrator/strategy/models.py`
- `src/agent_orchestrator/strategy/planner.py`
- `src/agent_orchestrator/strategy/__init__.py`

### New Models

- `ExecutionStrategy`
- `StrategyCandidate`
- `ExecutionPlan`

### New Planner

- `StrategyPlanner`
- `CompatibilityStrategyPlanner`

The compatibility planner keeps the current `decompose` implementation behind a strategy layer, rather than letting `decompose` remain the architectural center.

## Current Strategy Set

Phase 2 establishes the following strategy vocabulary:

- `direct_edit`
- `explore_then_edit`
- `investigation_only`
- `migration_guarded`
- `docs_sync`
- `need_human_confirmation`

These strategy names are intentionally broader than the legacy decomposition shapes such as:

- `general_pipeline`
- `investigation_pipeline`
- `migration_pipeline`
- `risk_trimmed_pipeline`

That distinction is important:

- strategy is the high-level execution choice,
- legacy decomposition shape is a compatibility implementation detail.

## Integration Points

### Orchestrator

`src/agent_orchestrator/orchestrator.py` now plans through the strategy layer before executing work units.

Instead of directly doing:

- clarify
- decompose
- execute

the execution path now does:

- clarify
- strategy planning
- compatibility expansion
- execute

### Team Planning Flow

`src/agent_orchestrator/planning.py` also now consumes strategy planning before turning results into planning subtasks.

This keeps the planning/governance path aligned with the same architectural seam used by the direct execution path.

### CLI

Phase 1 already routed CLI entry through intake.

Phase 2 keeps that arrangement and ensures the downstream execution path is now strategy-aware rather than decomposition-first.

## What Phase 2 Does Not Yet Do

Phase 2 still does **not** provide:

- dynamic execution graphs,
- repo exploration,
- repair/retry loops,
- durable agent sessions,
- a new non-legacy coding execution runtime.

Those are later phases.

## Acceptance Criteria

Phase 2 is complete when:

- a dedicated strategy layer exists,
- task routing and strategy planning are distinct concepts in code,
- the old decomposition path is no longer the architectural entry for execution planning,
- orchestrator and planning flows both consume the strategy layer,
- legacy decomposition remains functional only as a compatibility expander,
- targeted regression tests pass without breaking governance/control-plane behavior.

## Targeted Regression Coverage

Phase 2 should be verified with:

```bash
pytest tests/test_strategy_planner.py tests/test_cli.py tests/test_adapters.py tests/test_control_plane.py tests/test_ui_service.py -q
```
