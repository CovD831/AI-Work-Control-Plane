## Stage 2 Plan

### Goal

Upgrade `MockClaudePlanner.clarify()` from a string wrapper into a deterministic contract builder that extracts structured task signals and produces a richer `TaskContract`.

### Scope

- Add rule-based signal extraction helpers.
- Build `ContractDraft` from extracted signals.
- Map the draft into a richer `TaskContract`.
- Keep the planner deterministic and preserve current control-plane compatibility.

### Acceptance Criteria

- `clarify()` captures explicit constraints, non-goals, and scope hints from common requirement patterns.
- `clarify()` infers a task type and expected artifacts for basic task categories.
- `clarify()` records risk signals and produces a risk level from those signals.
- Existing orchestrator flows still pass targeted regression tests.

### Tests

- Add unit tests for clarify behavior on constrained refactor tasks.
- Add unit tests for high-risk task classification and artifact inference.
- Add unit tests for investigation tasks producing non-patch artifacts.
- Re-run targeted adapter and orchestrator tests after implementation.
