# AI Work Control Plane Dogfood Evidence

## Scenario

On 2026-05-27, the repository ran the control-plane chain against itself as the continuous hardening dogfood scenario:

```text
WorkspaceState -> ContextPacket -> StrategyDecision -> ExecutionTopologySnapshot -> ApprovalItem/EvidenceBundle -> MemoryRecord
```

## Evidence

- `team workspace-status --format json` produced `agent_orchestrator.workspace_state.v1` with current plans, runs, jobs, dirty state, memory digest, and optional explore_cache status.
- `team context-packet --query "AI Work Control Plane continuous dogfood" --changed-file src/agent_orchestrator/control_plane.py --format json` produced `agent_orchestrator.context_packet.v1` with selected canonical docs, fresh doc-sync status, memory records, and no stale warnings.
- `team topology inspect plan-66a657a8 --format json` produced `agent_orchestrator.execution_topology_snapshot.v1` with read-only state/context/strategy/review/evidence/memory nodes.
- The embedded `StrategyDecision` kept `executes=false`, carried `control_plane_focus=state_context_strategy_topology_approval_evidence_memory_recovery`, and exposed `recovery_policy.execution_gate_authority=approved_plan_gate`.
- `team evidence-gates --format json` produced `agent_orchestrator.evidence_bundle.v1` with compliance passed, local evidence report present, and memory recommendations marked `auto_write=false`.

## Result

The dogfood chain confirms that this repository can use the AI Work Control Plane as its own operator surface without replacing existing orchestration. Explicit orchestration remains the execution capability; state, context, strategy, topology, approvals, evidence, memory, and recovery remain external auditable artifacts.
