## Stage 8 Plan

### Goal

Add a lightweight ambiguous-task evaluation suite for `clarify()` so slot-filling coverage can be measured across realistic under-specified requests.

### Scope

- Add representative ambiguous clarify cases.
- Assert minimum contract behavior and unresolved-slot visibility.
- Keep the suite deterministic by using stub slot fillers.

### Acceptance Criteria

- The repo contains a focused ambiguous-task clarify eval suite.
- Each case checks both produced slots and unresolved slots.
- The suite distinguishes rule-only behavior from slot-filled behavior.

### Tests

- Add parameterized eval tests for ambiguous investigation, refactor, and docs-style requests.
- Re-run targeted adapter and orchestrator tests after implementation.
