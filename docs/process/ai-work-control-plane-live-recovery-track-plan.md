# AI Work Control Plane Live Recovery Track Plan

## Summary

This track moves the AI Work Control Plane from an operator-readable surface to an operator-recoverable surface.

The product center remains the control plane, not more explicit agent choreography. Existing `agent team` orchestration stays as the lower execution capability. This track strengthens the external system artifacts that explain what happened, why work is blocked, and how an operator can safely resume long-cycle work.

Pinned chain:

```text
Workspace / Program Index v2
  -> Run Ledger
  -> Recovery Timeline
  -> Runtime Event Stream
  -> Recovery Recommendation
  -> Operator Resume Command
  -> Evidence-backed Memory Promotion
```

## Execution Protocol

- Write each phase plan in `docs/process/` before implementation.
- Run only targeted tests inside phases.
- Continue automatically after targeted tests pass.
- Run full `pytest` and `team check-compliance` only at final convergence.
- Do not add a React Flow editor, a full provider bridge, or a direct-API patch engine.
- Keep all CLI commands and v1 artifacts compatible; new fields are optional.

## Phase Plan

### Phase 0: Live Recovery Baseline

Add this plan, add the Phase 0 plan, and sync canonical process docs around the next gap: richer live recovery telemetry, provider/runtime bridge fidelity, and broader real-task dogfood coverage.

Targeted tests:

```bash
pytest tests/test_docs_process.py tests/test_planning_support.py -q
```

### Phase 1: Recovery Timeline Artifact

Add read-only `agent_orchestrator.recovery_timeline.v1` from PlanSession, Run Ledger, Approval Inbox, Evidence Bundle, provider fallback, and compliance state.

Required statuses: `started`, `checkpointed`, `awaiting_human`, `approval_blocked`, `evidence_blocked`, `compliance_blocked`, `provider_degraded`, `runtime_failed`, `interrupted`, `recovery_ready`, and `completed`.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_cli_presenters.py tests/test_team.py -q
```

### Phase 2: Runtime Event Stream

Add read-only `agent_orchestrator.runtime_event_stream.v1` for control-plane facts: runtime mode, command/job intent, tool intent, result status, failure reason, fallback reason, degraded capability reason, usage/cost placeholder, and artifact refs.

Targeted tests:

```bash
pytest tests/test_messages.py tests/test_team.py tests/test_cli.py tests/test_control_plane.py -q
```

### Phase 3: Recovery Recommendation Engine

Add a read-only recommendation builder that explains the current blocking reason, safest next operator command, required approval or evidence, recoverable artifact refs, whether execution may resume, whether human decision is required, and whether compliance must be fixed first.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_planning_support.py tests/test_team.py -q
```

### Phase 4: Workspace Status Recovery Dashboard

Make `team workspace-status --format json` expose optional recovery dashboard fields: `recovery_timeline`, `runtime_events`, `recovery_recommendation`, `blocking_summary`, `resume_hint`, and `last_checkpoint`.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_ui_service.py -q
```

### Phase 5: Evidence And Memory Loop

Let EvidenceBundle reference recovery timeline and runtime event stream. Extend memory candidates with recovery pattern, runtime degradation note, approval delay note, and compliance blocking note. Do not auto-write transient status.

Targeted tests:

```bash
pytest tests/test_memory.py tests/test_control_plane.py tests/test_cli.py tests/test_planning_support.py -q
```

### Phase 6: Dogfood Recovery Scenario

Dogfood the local recovery chain against this repository and record awaiting-human, compliance-blocking, and provider/runtime degraded or fallback scenarios.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_team.py tests/test_cli.py tests/test_docs_process.py -q
```

### Phase 7: Final Convergence

Run full validation, update canonical docs, and record final status.

Final commands:

```bash
pytest
env PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
env PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
env PYTHONPATH=src python -m agent_orchestrator.cli team next --format json
env PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
git status --short
```

## Completion Bar

The track is complete when an operator can understand the live recovery state from control-plane artifacts without manually stitching together sessions, jobs, approvals, evidence, and runtime records.

## Implementation Result

Live Recovery Track implementation is complete through Phase 6:

- Recovery Timeline records started, checkpointed, awaiting-human, approval/evidence/compliance blocked, provider degraded, runtime failed, interrupted, recovery-ready, and completed states.
- Runtime Event Stream records runtime intent/result/fallback facts without executing or bypassing approved-plan gates.
- Recovery Recommendation appears in `team next --format json` as a read-only next-step recommendation.
- `team workspace-status --format json` now exposes recovery dashboard fields: recovery timeline, runtime events, recovery recommendation, blocking summary, resume hint, and last checkpoint.
- EvidenceBundle links recovery refs and emits recovery-backed memory candidates while keeping `auto_write=false`.
- Dogfood evidence is recorded in `docs/process/ai-work-control-plane-live-recovery-dogfood-evidence.md`.

Final convergence is tracked in `docs/process/ai-work-control-plane-live-recovery-phase-7-final-convergence.md`.
