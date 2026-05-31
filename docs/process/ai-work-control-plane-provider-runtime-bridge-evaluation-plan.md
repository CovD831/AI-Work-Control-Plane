# AI Work Control Plane Provider Runtime Bridge Evaluation Plan

## Purpose

This track evaluates how real provider runtimes should plug into the AI Work Control Plane after `v1.0.0-rc.1`.

The previous Runtime Bridge Fidelity Track made existing jobs inspectable through provider session snapshots, runtime operation receipts, runtime event streams, recovery recommendations, workspace status, evidence gates, and UI summaries. This track does not repeat that work. It asks the next question: which real Codex / Claude runtime capabilities are stable enough to model as adapter capabilities, and which must remain observed, unavailable, placeholder, or provider-owned.

## Product Boundary

In scope:

- Evaluate Codex CLI, Claude Code, current command runtime, file/mock runtime, direct API runtime, and tmux runtime as provider/runtime candidates.
- Produce a capability matrix for start, resume, send, cancel, status, logs, artifacts, session identity, cwd/workspace, exit code, usage/cost, permissions, and structured output.
- Define ownership boundaries between AI-Work-Control-Plane and provider runtimes.
- Draft a minimal `ProviderRuntimeAdapter` contract for a later implementation track.
- Select one provider pilot candidate with a narrow next-stage acceptance line.

Out of scope:

- Full provider-native bridge implementation.
- Persistent provider session ownership by AI-Work-Control-Plane.
- Provider ping-pong loops.
- Direct-API patch engine.
- Plugin marketplace packaging.
- Making real provider calls mandatory for tests or release readiness.

## Evidence Rules

- CLI help/version output is treated as observed local capability evidence.
- Existing source contracts are treated as current implementation evidence.
- Live provider calls are non-deterministic and must not become required release gates.
- Token/cost values remain placeholder unless a provider runtime reports them directly.
- Session IDs and thread IDs are references, not ownership claims.

## Phase Plan

### Phase 0: Track Plan & Boundary Freeze

Create this plan and a boundary note that ties the new evaluation work to the completed Runtime Bridge Fidelity and Runtime Measurement RC tracks.

Targeted validation:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
```

### Phase 1: Capability Matrix

Record observed provider/runtime capabilities for:

- `mock` / `FileJobRuntime`
- `CommandJobRuntime`
- `CodexCliAdapter`
- `ClaudeCodeAdapter`
- `DirectApiJobRuntime`
- `TmuxJobRuntime`
- local Codex CLI
- local Claude Code

Targeted validation:

```bash
pytest tests/test_command.py tests/test_jobs.py tests/test_tmux_runtime.py -q
```

### Phase 2: Ownership Boundary

Document which fields AI-Work-Control-Plane owns, which fields are provider-owned, and which fields are explicitly observed or placeholder.

Candidate output:

```text
JobRecord -> ProviderRuntimeCapability -> ProviderSessionRef
  -> RuntimeMeasurement -> OperationReceipt -> EvidenceBundle
```

Targeted validation:

```bash
pytest tests/test_control_plane.py tests/test_cli.py -q
```

### Phase 3: Adapter Contract Draft

Draft a minimal provider runtime adapter contract that can be implemented later without changing control-plane semantics.

Candidate stable fields:

- `runtime_id`
- `provider`
- `capabilities`
- `start`
- `status`
- `result`
- `send`
- `cancel`
- `session_ref`
- `operation_receipts`
- `measurement`
- `degraded_reason`

Targeted validation:

```bash
pytest tests/test_command.py tests/test_control_plane.py tests/test_cli.py -q
```

### Phase 4: Pilot Candidate Selection

Choose either Codex or Claude for the next implementation pilot. The pilot should prove one minimal real-provider loop without expanding into a full bridge.

Candidate acceptance line:

```text
start real provider task
  -> persist session/job metadata
  -> inspect runtime fidelity
  -> record measured/placeholder/unavailable fields honestly
  -> evidence gates consume the result
```

## Completion Bar

This track is complete when the repository can answer:

- Which provider runtime capabilities are observed today?
- Which capabilities are safe to model as an adapter contract?
- Which capabilities remain provider-owned or unavailable?
- Which provider should be piloted next, and what is the smallest honest pilot loop?

