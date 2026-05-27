# v1.x Release Readiness

- version sync lives in `pyproject.toml`
- `team setup` reports provider health, doc sync, compliance, and release readiness
- evidence output is local markdown under `docs/process/`
- full readiness still depends on targeted tests and final compliance
- gate evidence summaries use `agent_orchestrator.gate_evidence.v1` and keep large logs in artifact paths
- setup doctor JSON uses `agent_orchestrator.setup_doctor.v1` for UI and automation consumers
- workspace state snapshots use `agent_orchestrator.workspace_state.v1` and persist `.agent_orchestrator/workspace/index.json`
- context packets use `agent_orchestrator.context_packet.v1` and do not choose strategy
- execution topology snapshots use `agent_orchestrator.execution_topology_snapshot.v1` as read-only graphs
- approval items use `agent_orchestrator.approval_item.v1` and resolution never bypasses execution gates
- evidence bundles use `agent_orchestrator.evidence_bundle.v1` for gate summaries
- control-plane artifact contracts are documented in `docs/process/control-plane-artifact-contracts.md`
- approval reason codes and evidence memory recommendations are part of the stable control-plane contract
- documentation context packages use `agent_orchestrator.docs_context.v1` and include selected canonical docs only
- docs context snapshots use `agent_orchestrator.docs_context_snapshot.v1` for session handoff
- handoff packets use `agent_orchestrator.handoff_packet.v1` for structured communication
- docs index results use `agent_orchestrator.docs_index.v1` for local reverse lookup
- this repository does not promise plugin-marketplace style distribution
