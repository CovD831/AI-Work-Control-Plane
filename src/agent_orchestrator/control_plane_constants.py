"""Stable constants for AI Work Control Plane artifacts."""
from __future__ import annotations

# DEPS: __future__
# RESPONSIBILITY: Declare stable control-plane artifact format identifiers and fixed catalogs.
# MODULE: decision_core
# ---

CONTROL_PLANE_FORMATS = {
    "workspace_index": "agent_orchestrator.workspace_index.v1",
    "workspace_state": "agent_orchestrator.workspace_state.v1",
    "context_packet": "agent_orchestrator.context_packet.v1",
    "strategy_decision": "agent_orchestrator.strategy_decision.v1",
    "topology_snapshot": "agent_orchestrator.execution_topology_snapshot.v1",
    "approval_item": "agent_orchestrator.approval_item.v1",
    "approval_queue": "agent_orchestrator.approval_queue.v1",
    "evidence_bundle": "agent_orchestrator.evidence_bundle.v1",
    "run_ledger": "agent_orchestrator.run_ledger.v1",
    "recovery_timeline": "agent_orchestrator.recovery_timeline.v1",
    "runtime_event_stream": "agent_orchestrator.runtime_event_stream.v1",
    "provider_session_snapshot": "agent_orchestrator.provider_session_snapshot.v1",
    "runtime_operation_receipt": "agent_orchestrator.runtime_operation_receipt.v1",
    "governance_bundle": "agent_orchestrator.governance_bundle.v1",
    "governance_bundle_inspection": "agent_orchestrator.governance_bundle_inspection.v1",
}

RECOVERY_TIMELINE_STATUSES = [
    "started",
    "checkpointed",
    "awaiting_human",
    "approval_blocked",
    "evidence_blocked",
    "compliance_blocked",
    "provider_degraded",
    "runtime_failed",
    "interrupted",
    "recovery_ready",
    "completed",
]

TOPOLOGY_NODE_TYPES = [
    "state",
    "context",
    "strategy",
    "manager_slot",
    "worker",
    "implementation",
    "review",
    "rescue",
    "condition",
    "approval",
    "evidence",
    "memory",
]
