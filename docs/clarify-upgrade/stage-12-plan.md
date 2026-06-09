## Stage 12 Plan

### Goal

Add lightweight multi-candidate control-plane decomposition so the system can compare alternative work-graph shapes instead of committing to a single template path.

### Scope

- Generate at least two rule-based decomposition candidates where meaningful.
- Score candidates on contract coverage, validation coverage, and risk isolation.
- Select one candidate while retaining rejected alternatives for inspection.

### Acceptance Criteria

- `MockClaudeDecomposer` records multiple candidates for team-mode tasks.
- A selected candidate is marked explicitly and returned through `last_candidates`.
- Riskier tasks prefer safer graphs; lean tasks can prefer simpler graphs.

### Tests

- Add unit tests proving multiple candidates are emitted and scored.
- Add unit tests proving migration tasks prefer the safer candidate.
- Re-run targeted adapter/orchestrator tests after implementation.
