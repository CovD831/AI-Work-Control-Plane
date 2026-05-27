# AI Work Control Plane Operations Track Plan

## Purpose

This track moves the current AI Work Control Plane from an artifact pipeline into the default operator work surface.

The center is no longer richer explicit agent choreography. The center is a durable control plane for long-cycle local AI work:

```text
PlanSession -> WorkspaceState -> ContextPacket -> StrategyDecision
  -> ExecutionTopologySnapshot -> ApprovalInbox -> RunLedger
  -> EvidenceBundle -> MemoryPromotion
```

Explicit `agent team` orchestration remains the lower execution capability. The control plane owns state, context, strategy, topology, approvals, evidence, memory promotion, recovery, runtime health, and operator continuity.

## Execution Protocol

- Each phase starts with a short phase plan in `docs/process/`.
- During implementation, run only that phase's targeted tests.
- If targeted tests pass, continue to the next phase without waiting for confirmation.
- Run full `pytest` and `team check-compliance` only at final convergence.
- Keep all existing `team` commands compatible; new fields are optional and additive.
- Do not build a React Flow editor, full provider bridge, full direct-API patch engine, or provider ping-pong loop.
- `StrategyDecision.executes` stays `False`; execution remains controlled by the approved-plan gate and runtime layer.

## Phase Plan

### Phase 0: Operations Track Baseline

Record this track, link the reference rescreen into canonical docs, and make the next line explicit: `Workspace / Program Index v2 + Approval Inbox + Run Ledger`.

Targeted tests:

```bash
pytest tests/test_docs_process.py tests/test_planning_support.py -q
```

### Phase 1: Workspace / Program Index v2

Extend `agent_orchestrator.workspace_index.v1` with optional operator-current-state fields: `program`, `active_artifacts`, `recent_artifacts`, `open_approvals`, `recent_runs`, `memory_candidates`, and `provider_runtime_health`.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_ui_service.py -q
```

### Phase 2: Approval Inbox Hardening

Treat approvals as an inbox with summary counts, reason distribution, stable recommended commands, and optional refs to plan, topology, run, job, evidence, and memory candidate artifacts.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_team.py -q
```

### Phase 3: Run Ledger

Add read-only `agent_orchestrator.run_ledger.v1` for long-cycle recovery across plan sessions, runs, delegated jobs, approvals, evidence, provider fallback, and compliance blocking.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_cli_presenters.py tests/test_team.py -q
```

### Phase 4: Topology Blueprint Snapshot

Extend `ExecutionTopologySnapshot` with optional read-only blueprint fields: nodes, edges, lanes, approval points, evidence points, and runtime boundaries.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_actions.py tests/test_cli.py -q
```

### Phase 5: Memory Promotion Workflow

Add evidence-backed memory candidates without auto-writing durable memory. Only provenance-bearing candidates can be promoted.

Targeted tests:

```bash
pytest tests/test_memory.py tests/test_control_plane.py tests/test_cli.py tests/test_planning_support.py -q
```

### Phase 6: Runtime Health + Tool Inventory

Surface provider/runtime health, MCP/tool inventory placeholders, setup/degraded state, and usage/cost placeholders as control-plane inputs.

Targeted tests:

```bash
pytest tests/test_messages.py tests/test_control_plane.py tests/test_cli.py tests/test_team.py -q
```

### Phase 7: Dogfood Operations Scenario

Run the repository through the new operations chain and record the result in process evidence.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_team.py tests/test_cli.py tests/test_docs_process.py -q
```

### Phase 8: Final Convergence

Refresh docs and run full gates:

```bash
pytest
env PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
env PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
env PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
git status --short
```

## Reference Rescreen Landing

The reference rescreen is now treated as input to this track:

- HiveWard informs workspace/program, blueprint, approval inbox, run ledger, and runtime boundary.
- wanman informs supervisor/store/runtime isolation boundaries.
- slark informs workflow state, approval steps, and lessons/decisions promotion.
- CodeWhale informs doctor JSON, resume/fork language, model routing, and MCP validation.
- codex-orchestrator informs job observability and context-map prompt support.
- plugin repos inform read-only review, mutating rescue, setup/status/result grammar, and honest degraded capability.
- Eigent informs real dogfood cases, HITL, and MCP/tool inventory.

## Completion Bar

The track is complete when the operator can use `team workspace-status`, `team approvals`, `team topology inspect`, `team evidence-gates`, `team summary`, `team next`, and `team runbook` to understand current state, approval needs, run history, evidence, memory candidates, runtime health, and recovery path without manually stitching lower-level files together.

## Implementation Result

Operations Track implementation is complete through Phase 7:

- Workspace / Program Index v2 is the `team workspace-status --format json` payload and keeps nested `workspace_state` for compatibility.
- Approval Inbox adds optional refs and inbox summary while keeping resolve records-only.
- Run Ledger records recovery-relevant plan, run, job, approval, evidence, and fallback state as `agent_orchestrator.run_ledger.v1`.
- Topology Snapshot exports a read-only blueprint view with lanes, approval points, evidence points, and runtime boundaries.
- Evidence Bundle exposes memory promotion candidates, runtime health, tool inventory, and usage/cost placeholders while keeping `auto_write=false`.
- Dogfood evidence is recorded in `docs/process/ai-work-control-plane-operations-dogfood-evidence.md`.

Final convergence is tracked in `docs/process/ai-work-control-plane-operations-phase-8-final-convergence.md`.
