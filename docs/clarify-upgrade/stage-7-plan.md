## Stage 7 Plan

### Goal

Persist clarify provenance and unresolved slots on the final task contract so slot-filling behavior is observable in runs and artifacts.

### Scope

- Extend `TaskContract` with provenance and unresolved-slot fields.
- Populate those fields from the clarify pipeline.
- Preserve backward-compatible serialization.

### Acceptance Criteria

- `TaskContract` records `slot_sources`, `unknown_slots`, and slot-fill warnings.
- Legacy payloads still deserialize with safe defaults.
- Clarify results expose which slots came from rules vs. LLM and which remained unresolved.

### Tests

- Add round-trip tests for new provenance fields.
- Add a planner test proving slot provenance and unknown slots are persisted on the contract.
