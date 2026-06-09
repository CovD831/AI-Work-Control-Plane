## Stage 11 Plan

### Goal

Upgrade control-plane decomposition from a fixed legacy pipeline into task-type-aware work-unit templates that consume richer task-contract signals.

### Scope

- Add decomposition templates for investigation, refactor/feature/bugfix, migration, and docs-style tasks.
- Shape work-unit outputs and dependencies from `task_type`, `constraints`, `target_scope`, and `risk_signals`.
- Keep the public `decompose()` interface unchanged.

### Acceptance Criteria

- Investigation tasks decompose into evidence/findings style work units.
- Migration tasks add rollback/validation-specific work units.
- Docs tasks avoid code-implementation defaults.
- Existing generic implementation paths still work for baseline cases.

### Tests

- Add unit tests for investigation, migration, and docs task decomposition shapes.
- Re-run targeted adapter/orchestrator tests after implementation.
