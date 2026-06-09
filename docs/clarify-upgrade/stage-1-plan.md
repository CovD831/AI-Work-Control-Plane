## Stage 1 Plan

### Goal

Introduce the internal contract-draft model and extend `TaskContract` with backward-compatible structured fields so later clarify upgrades have stable types to build on.

### Scope

- Add internal draft/fill dataclasses for clarify pipeline work.
- Extend `TaskContract` with optional structured fields and serialization support.
- Preserve existing planner and orchestrator behavior.

### Acceptance Criteria

- Existing `TaskContract` payloads still deserialize without errors.
- New `TaskContract` fields have safe defaults and round-trip through `to_dict()` / `from_dict()`.
- Internal clarify draft models exist and are importable within the adapter module.
- Current orchestrator tests that depend on the old planner behavior still pass unchanged.

### Tests

- Add unit tests covering `TaskContract` backward-compatible deserialization.
- Add unit tests covering `TaskContract` round-trip with structured clarify fields populated.
- Add unit tests covering internal clarify draft model defaults.
- Run targeted adapter/task/orchestrator tests after implementation.
