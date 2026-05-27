# AI Work Control Plane Provider Runtime Bridge Evaluation Phase 4: Pilot Selection

## Goal

Select the next implementation pilot after the provider runtime bridge evaluation track.

The pilot should be narrow enough to preserve the current control-plane boundary while proving one real provider loop with better adapter evidence than the current generic command runtime.

## Recommendation

Choose **Codex Runtime Pilot** as the first implementation pilot.

Claude Code should remain the second pilot candidate after Codex has proven the adapter contract path.

## Why Codex First

Codex is the better first pilot for this repository because:

- It is closest to the current self-use workflow.
- `codex exec` explicitly supports non-interactive runs.
- `codex exec --json` can emit JSONL events that are better suited to runtime event ingestion than plain stdout.
- `codex exec --output-schema` can support structured result contracts.
- `codex exec --output-last-message` can provide a stable artifact path for final response capture.
- `codex resume` and `codex exec resume` expose non-interactive continuation surfaces that can be evaluated without claiming ownership up front.
- Existing `CodexCliAdapter` already builds a command-runtime path, so a pilot can be additive rather than a rewrite.

## Why Claude Second

Claude Code is also a strong candidate, but should follow Codex because:

- It exposes rich session flags: `--resume`, `--continue`, `--session-id`, and `--fork-session`.
- It exposes `--output-format json` and `--output-format stream-json`.
- It exposes `--input-format stream-json`, which may eventually support a stronger send/continuation story.
- It exposes `claude agents --json` for inspecting background sessions.
- A local smoke during this evaluation did not return promptly in the current environment, so live-call behavior should be isolated in a later pilot with stricter timeout/degradation handling.

## Codex Pilot Scope

The next implementation track should not build a full bridge. It should add one narrow adapter path:

```text
Codex exec JSON pilot
  -> start non-interactive task
  -> capture JSONL events or final-message artifact
  -> persist ProviderSessionRef as observed/provider-owned
  -> classify runtime measurement
  -> expose ProviderSessionSnapshot
  -> evidence gates consume the job
```

## Codex Pilot Acceptance Line

The pilot is complete when:

- A Codex non-interactive job can be started through the existing orchestration/runtime path.
- The job persists a command, cwd, timestamps, exit code, stdout/stderr or JSONL event artifact, and final message artifact when configured.
- `team runtime inspect <job_id> --format json` reports session/ref fields without claiming provider-native ownership.
- Unsupported send/cancel paths produce honest operation receipts.
- Runtime measurement distinguishes measured, placeholder, and unavailable facts.
- Evidence gates and workspace status consume the job without provider-specific branching.
- Tests use fake runners/fixtures, not live Codex calls.

## Explicit Non-Goals

- Do not make Codex the only provider.
- Do not require live Codex calls in CI or release gates.
- Do not claim persistent Codex session ownership.
- Do not implement provider-native send/cancel until a separate pilot proves it.
- Do not estimate token/cost from local logs.

## Next Track Name

Recommended next implementation track:

```text
AI Work Control Plane Codex Runtime Pilot
```

## Phase 4 Result

Provider Runtime Bridge Evaluation selects Codex as the first pilot and preserves Claude as the second candidate.

