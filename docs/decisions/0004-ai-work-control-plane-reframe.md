# ADR 0004: AI Work Control Plane Reframe

## Status

Accepted

## Context

The project began as an explicit agent orchestration system. That remains useful today, but model runtimes will internalize more planning, delegation, review, and tool-use behavior over time. A product whose only value is visible orchestration risks becoming redundant.

The durable value is the external work system around model intelligence: state, context compression, strategy provenance, topology trace, approvals, evidence, memory, and recovery.

## Decision

Reframe AI-Work-Control-Plane as an **AI Work Control Plane for long-cycle local agent work**.

The canonical artifact pipeline is:

```text
WorkspaceState -> ContextPacket -> StrategyDecision -> ExecutionTopologySnapshot -> ApprovalItem -> EvidenceBundle -> MemoryRecord
```

Existing planning governance, team topology, job runtime, and provider integrations are retained as implementation layers under the control plane. AI-native roles are artifact transformers such as `state_keeper`, `context_compressor`, `strategist`, `topology_compiler`, `approval_gate`, `evidence_recorder`, and `memory_curator`; they are not a classically human company org chart.

The time horizon is explicit: short-term work still relies on visible orchestration, medium-term work is governed by the control plane, and long-term orchestration may be internalized by stronger models. Durable state, evidence, approvals, memory, and recovery remain external system responsibilities.

## Consequences

- Future feature work should strengthen external state, evidence, approvals, memory provenance, and recovery before adding more agent-role spectacle.
- `agent team` remains important, but it is no longer the whole product identity.
- Explicit orchestration can shrink over time, but audit-friendly control-plane artifacts must not disappear into model-private reasoning.
- CLI JSON contracts for control-plane artifacts are public operator surfaces.
- UI should consume stable schemas and stay read-only for topology until the artifact model settles.
- explore_cache is optional memory infrastructure; local `MemoryStore` remains the required baseline.

## Related Commands

- `python -m agent_orchestrator.cli team workspace-status`
- `python -m agent_orchestrator.cli team context-packet --query "<task>"`
- `python -m agent_orchestrator.cli team topology inspect <session_id>`
- `python -m agent_orchestrator.cli team approvals list`
- `python -m agent_orchestrator.cli team evidence-gates`
