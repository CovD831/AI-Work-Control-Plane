## Stage 5 Plan

### Goal

Wire the slot-filling path to a real OpenAI-compatible direct API client using `AO_SLOTFILL_*` environment variables and a custom base URL, while preserving deterministic fallback.

### Scope

- Add env-driven slot-fill client configuration.
- Add an OpenAI-compatible HTTP client for structured slot filling.
- Auto-enable the slot filler when required env vars are present.
- Keep clarify deterministic when env config is absent or the API result is unusable.

### Acceptance Criteria

- `MockClaudePlanner()` can auto-configure a real slot filler from environment variables.
- The slot filler calls a custom base URL with bearer auth and the configured model.
- Structured JSON responses are parsed into `SlotFillResult`.
- Invalid payloads or missing env config fall back cleanly without breaking clarify.

### Tests

- Add unit tests for env-based slot filler configuration.
- Add unit tests for parsing an OpenAI-compatible structured response.
- Add unit tests for graceful fallback on malformed response payloads.
- Re-run targeted adapter and orchestrator tests after implementation.
