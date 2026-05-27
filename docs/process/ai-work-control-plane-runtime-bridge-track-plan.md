# AI Work Control Plane Runtime Bridge Fidelity Track

## Purpose

This track closes the gap after Live Recovery: the control plane can explain how to recover, and now it must expose provider/runtime session fidelity clearly enough for an operator to trust the recovery path.

The product remains an AI Work Control Plane. This track does not build a full provider bridge, persistent session manager, React Flow editor, direct-API patch engine, or provider ping-pong loop.

Pinned chain:

```text
JobRecord -> ProviderSessionSnapshot -> RuntimeOperationReceipt
  -> RuntimeEventStream -> RecoveryRecommendation
  -> WorkspaceStatus / EvidenceBundle / UI
```

## Execution Protocol

- Each phase starts with a short phase note in `docs/process/`.
- During implementation, run only that phase's targeted tests.
- Continue automatically after targeted tests pass.
- Run full `pytest` and `team check-compliance` only at final convergence.
- Keep every schema additive and backward-compatible.

## Phase Plan

### Phase 0: Baseline

Record the track and make Runtime Bridge Fidelity the next major line after Live Recovery.

Targeted tests:

```bash
pytest tests/test_docs_process.py tests/test_planning_support.py -q
```

### Phase 1: Provider Session Snapshot

Add `agent_orchestrator.provider_session_snapshot.v1` from existing job records and live command-runtime metadata.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_command.py tests/test_jobs.py -q
```

### Phase 2: Runtime Operation Receipt

Normalize send/cancel/terminal/missing-session/auth/provider-unavailable outcomes into `agent_orchestrator.runtime_operation_receipt.v1` while preserving existing `operation`, `follow_up`, and `cancel` payloads.

Targeted tests:

```bash
pytest tests/test_command.py tests/test_jobs.py tests/test_ui_service.py -q
```

### Phase 3: Runtime Event Stream + Recovery

Extend runtime events and recovery recommendations with session liveness, operation receipts, attachability, continuation support, degraded reason, and recovery-safe next command.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_cli_presenters.py -q
```

### Phase 4: Operator CLI

Add `team runtime inspect <job_id> --format json` as the read-only operator entry for provider session snapshots.

Targeted tests:

```bash
pytest tests/test_cli.py tests/test_cli_presenters.py -q
```

### Phase 5: Workspace, Evidence, UI

Expose runtime fidelity summaries through workspace status, evidence gates, and UI service job payloads.

Targeted tests:

```bash
pytest tests/test_ui_service.py tests/test_team.py tests/test_messages.py -q
```

### Phase 6: Dogfood

Record local scenarios: completed job, running job, terminal send, cancelled job, missing session after process restart, auth-required direct API, and provider unavailable/fallback.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_docs_process.py -q
```

### Phase 7: Final Convergence

Run full validation, update canonical docs, and record final status.

Final commands:

```bash
pytest
env PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
env PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
env PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
git status --short
```

## Completion Bar

The track is complete when an operator can inspect runtime fidelity from control-plane artifacts without manually stitching together job JSON, logs, parsed payloads, provider health, and recovery recommendations.
