# AI Work Control Plane Live Recovery Dogfood Evidence

## Summary

This repository now dogfoods Live Recovery Track as its own recovery control plane.

Pinned chain:

```text
PlanSession
  -> Workspace / Program Index v2
  -> Run Ledger
  -> Runtime Event Stream
  -> Recovery Timeline
  -> Recovery Recommendation
  -> EvidenceBundle
  -> Memory Candidate
```

## Local Evidence

- `team workspace-status --format json` returns `agent_orchestrator.workspace_index.v1` with `recovery_timeline`, `runtime_events`, `recovery_recommendation`, `blocking_summary`, `resume_hint`, and `last_checkpoint`.
- `agent_orchestrator.recovery_timeline.v1` records `started`, `checkpointed`, `awaiting_human`, `approval_blocked`, `evidence_blocked`, `compliance_blocked`, `provider_degraded`, `runtime_failed`, `interrupted`, `recovery_ready`, and `completed` as the status catalog.
- `agent_orchestrator.runtime_event_stream.v1` records runtime intent/result/fallback facts only. It does not execute tools or bypass the approved-plan gate.
- `team next --format json` returns `agent_orchestrator.recovery_recommendation.v1` as a read-only next-step recommendation.
- `agent_orchestrator.evidence_bundle.v1` links recovery refs and emits evidence-backed memory candidates while keeping `auto_write=false`.

## Recovery Scenarios

### Scenario A: Awaiting Human / Approval

Keyword: awaiting-human / approval.

An awaiting-human PlanSession produces:

- recovery timeline status: `awaiting_human`
- recommendation: `human_decision_required=true`
- approval/evidence requirement: `approval_required=true`
- resume hint: human decision or approval resolution

### Scenario B: Compliance Blocking

Keyword: compliance blocking.

A compliance-blocked PlanSession produces:

- recovery timeline status: `compliance_blocked`
- recommendation: `compliance_must_be_fixed_first=true`
- approval/evidence requirement: `compliance_required=true`
- memory candidate: `compliance_blocking_note`

### Scenario C: Provider / Runtime Degraded Or Fallback

Keyword: provider/runtime degraded or fallback.

A degraded provider/runtime record produces:

- runtime event status: `provider_degraded` or failed delegated job
- recovery timeline status: `provider_degraded` or `runtime_failed`
- memory candidate: `runtime_degradation_note`
- mutation policy: records-only; execution remains gated by approved plans

## Boundary

Live Recovery Track does not add a React Flow editor, a full provider bridge, or a direct-API patch engine. Explicit orchestration remains the lower execution capability; the control plane owns state, evidence, approvals, memory provenance, and recovery.
