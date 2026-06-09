## Stage 9 Plan

### Goal

Surface clarify provenance and unresolved slots in operator-facing CLI summaries for both direct runs and execution sessions.

### Scope

- Add a compact clarify summary to execution-contract metadata.
- Carry that summary into execution session payloads.
- Print clarify provenance, unresolved slots, and warnings in CLI summaries.

### Acceptance Criteria

- Direct run summaries show a clarify line when clarify provenance is present.
- Execution session summaries show the same clarify line when session metadata includes it.
- Existing summary output remains intact.

### Tests

- Add a CLI test for direct run clarify summary output.
- Add a presenter test for execution session clarify summary output.
