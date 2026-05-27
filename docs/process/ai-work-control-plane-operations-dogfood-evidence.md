# AI Work Control Plane Operations Dogfood Evidence

## Scenario

This repository now dogfoods the Operations Track as its own current-site control plane.

The pinned chain is:

```text
PlanSession
  -> Workspace / Program Index v2
  -> ContextPacket
  -> StrategyDecision
  -> Topology Blueprint Snapshot
  -> Approval Inbox
  -> Run Ledger
  -> EvidenceBundle
  -> Memory Candidate
```

## Evidence

- `team workspace-status --format json` now returns `agent_orchestrator.workspace_index.v1` with nested `agent_orchestrator.workspace_state.v1`, `program`, `active_artifacts`, `open_approvals`, `recent_runs`, `memory_candidates`, and `provider_runtime_health`.
- `team topology inspect <session_id> --format json` returns `agent_orchestrator.execution_topology_snapshot.v1` with read-only `blueprint`, `lanes`, `approval_points`, `evidence_points`, `runtime_boundaries`, `strategy_decision`, `approval_queue`, `run_ledger`, and `evidence_bundle`.
- `team approvals list --format json` returns an inbox summary with pending/resolved/blocking counts, reason code distribution, and a recommended next command.
- `agent_orchestrator.run_ledger.v1` records recovery-ready, awaiting-human, compliance-blocking, provider-fallback, failed, interrupted, and completed states as read-only recovery evidence.
- `agent_orchestrator.evidence_bundle.v1` carries runtime health, tool inventory, usage/cost placeholders, and memory promotion candidates while keeping `auto_write=false`.

## Result

The control plane now owns the operator view of current work. Explicit `agent team` orchestration remains the execution capability below the control plane; state, context, strategy, topology, approvals, run history, evidence, memory promotion, runtime health, and recovery stay in auditable external artifacts.
