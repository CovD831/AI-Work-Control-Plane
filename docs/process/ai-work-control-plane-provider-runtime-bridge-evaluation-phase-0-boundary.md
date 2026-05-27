# AI Work Control Plane Provider Runtime Bridge Evaluation Phase 0: Boundary Freeze

## Goal

Freeze the next-stage boundary after `v1.0.0-rc.1`: evaluate provider runtime bridge capability without implementing or claiming a full provider bridge.

## Current Baseline

The repository already has:

- `JobRuntime`, `FileJobRuntime`, `CommandJobRuntime`, `DirectApiJobRuntime`, and `TmuxJobRuntime`.
- `ProviderAdapter` implementations for Codex CLI and Claude Code command invocation.
- `ProviderSessionSnapshot` as a read-only fidelity artifact.
- `RuntimeOperationReceipt` for send/cancel/terminal/missing-session outcomes.
- `RuntimeMeasurement` and release-readiness reporting.
- `team runtime inspect <job_id>` as the read-only operator entrypoint.
- Workspace/evidence/UI summaries that consume runtime fidelity.

This means the next track should not reimplement runtime fidelity. It should evaluate provider-native capability and decide what a future adapter can safely promise.

## Boundary

Agent Orchestrator owns:

- job id
- task id
- provider label
- runtime mode
- command args
- cwd
- timestamps
- exit code when locally observed
- stdout/stderr capture when locally observed
- degraded reason
- operation receipts
- release/evidence readiness interpretation

Provider runtimes own:

- model-internal state
- provider-native conversation state
- provider-native session continuity guarantees
- token/cost truth
- provider-specific permissions and tool semantics
- provider-specific resume/send/cancel behavior beyond what is observed locally

## Phase 0 Evidence

Observed local CLI versions:

- Codex CLI: `codex-cli 0.133.0-alpha.1`
- Claude Code: `2.1.152 (Claude Code)`

Observed current source contracts:

- `src/agent_orchestrator/jobs.py`: local job lifecycle, operation receipts, runtime measurement payloads.
- `src/agent_orchestrator/command.py`: command runner, provider adapters, command runtime, direct API runtime.
- `src/agent_orchestrator/control_plane.py`: provider session snapshot, runtime event stream, evidence/runtime fidelity summaries.

Live provider call note:

- A `claude -p --output-format json "respond with ok"` smoke was attempted during evaluation and had to be stopped because it did not return promptly in the current environment.
- This reinforces the rule that live provider calls are useful pilot evidence but must not become required deterministic gates for this evaluation track.

## Result

Phase 0 is complete when this boundary document and the track plan are committed, and compliance remains non-blocking.

