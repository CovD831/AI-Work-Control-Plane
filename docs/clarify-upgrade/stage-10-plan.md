## Stage 10 Plan

### Goal

Introduce explicit decomposition-candidate models so control-plane decomposition can evolve from a fixed template list into candidate work graphs without breaking the current orchestrator interface.

### Scope

- Add `DecompositionCandidate` and candidate-score metadata.
- Add internal helpers to serialize candidate work units and selected strategy details.
- Preserve the public `decompose(contract, policy) -> list[WorkUnit]` interface for now.

### Acceptance Criteria

- Candidate models exist and round-trip correctly.
- `MockClaudeDecomposer` can package the current decomposition result as a selected candidate without changing returned work units.
- Existing orchestrator behavior remains unchanged.

### Tests

- Add unit tests for candidate model round-trip.
- Add unit tests proving the current decomposition result can be wrapped as a selected candidate.
- Re-run targeted adapter/orchestrator tests after implementation.
