## Stage 4 Plan

### Goal

Make `MockClaudeDecomposer` consume the richer task contract so downstream work units reflect task type, scope, constraints, and expected artifacts.

### Scope

- Build structured context packets from the contract.
- Adjust direct execution work units to match task type outputs.
- Adjust team-mode work units to consume contract constraints, scope, and expected artifacts.
- Preserve current orchestrator control-flow expectations.

### Acceptance Criteria

- Investigation contracts decompose into analysis-oriented work units instead of patch-oriented defaults.
- Work unit inputs include contract constraints and target scope when available.
- Team-mode implementation units use contract expected artifacts instead of hard-coded patch outputs.
- Targeted orchestrator regressions still pass.

### Tests

- Add unit tests for direct investigation decomposition.
- Add unit tests for team decomposition consuming constraints and scope.
- Re-run targeted adapter and orchestrator tests after implementation.
