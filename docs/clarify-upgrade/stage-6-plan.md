## Stage 6 Plan

### Goal

Add a project-local place to configure slot-filler credentials without committing secrets to the repository.

### Scope

- Support reading `AO_SLOTFILL_*` from a local env file in the project root.
- Commit a `.env.example` template.
- Ignore the local secrets file in git.

### Acceptance Criteria

- `EnvSlotFillConfig.from_env()` can read values from a project-local env file.
- Explicit process environment variables still override file-based values.
- The repository contains a committed example file but does not track real secrets.

### Tests

- Add a test proving `.env.local` values are loaded.
- Add a test proving process environment variables override `.env.local`.
