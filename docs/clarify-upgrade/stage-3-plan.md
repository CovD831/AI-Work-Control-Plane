## Stage 3 Plan

### Goal

Introduce ambiguity assessment and a gated slot-fill interface so `clarify()` can selectively request structured completion without turning the planner into a freeform black box.

### Scope

- Add draft assessment for missing and uncertain slots.
- Add an optional slot-filler adapter interface.
- Add validation and merge rules for slot-filled results.
- Preserve deterministic fallback when no slot filler is configured or the fill result is invalid.

### Acceptance Criteria

- Deterministic clarify still works without a slot filler.
- Ambiguous or under-specified drafts can trigger a slot-filler callback.
- Slot fill merge preserves locked rule-extracted fields such as explicit scope and non-goals.
- Invalid or partial slot-fill output falls back cleanly to deterministic draft data.

### Tests

- Add a unit test proving no slot filler is required for normal clarify flow.
- Add a unit test proving ambiguous input triggers slot filling.
- Add a unit test proving locked fields cannot be overwritten by slot fill output.
- Re-run targeted adapter and orchestrator tests after implementation.
