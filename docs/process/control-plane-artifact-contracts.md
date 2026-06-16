# Control Plane Artifact Contracts

- agent_orchestrator.workspace_state.v1
- agent_orchestrator.context_packet.v1
- agent_orchestrator.strategy_decision.v1
- agent_orchestrator.approval_item.v1
- agent_orchestrator.evidence_bundle.v1
- agent_orchestrator.provider_evidence_summary.v1
- agent_orchestrator.governance_bundle.v1
- agent_orchestrator.governance_bundle_inspection.v1
- native_tool_workflow_surface
- native_tool_productization_surface
- adapter_productization_surface
- comparative_native_tool_summary
- comparative_adapter_summary
- session_productization_surface
- workflow_continuity
- session_continuity.comparative_benchmark
- session_continuity.comparative_benchmark_digest
- operator_posture_digest
- clarify_boundary_digest
- session_planner_decision
- planner_closure_posture
- session_continuity_outline
- comparative_session_posture_summary
- comparative_session_continuity_summary
- comparative_native_closure_summary
- autonomy_posture
- resume_expectation
- resume_posture
- session_posture_cases
- workflow_resume_ready
- workflow_projection_visible
- workflow_recovery_aligned
- productization_case_count
- continuity_snapshot
- compacted_context_summary
- recovery_contract
- shared_contract_alignment
- shared_productization_contract_ready
- daily_driver_main_path_ready
- comparison_posture_basis
- comparison_proof_strength
- comparative_daily_driver_summary
- comparative_completion_summary
- daily_driver_repeatability_tier
- independent_daily_driver_repo_task_families_proven
- external_comparison_harness_surface
- stronger_task_families
- repo_task_acceptance_families_proven
- daily_driver_repo_task_families_proven
- broader_repeatability_gap_families

Evidence comparison or trend surfaces should preserve these names as stable cross-surface contract markers.

For session productization specifically, downstream projections should treat `workflow_continuity`, `workflow_resume_ready`, `workflow_projection_visible`, and `workflow_recovery_aligned` as first-class continuity markers rather than optional narrative-only hints.

## Canonical Vs Projection Boundary

Canonical contracts are the control-plane artifacts documented in this file.

`team roles`, work-graph trees, pretty summaries, runbook guidance, and UI panels are projections over those contracts and must not become a second durable state source.

Unknown fields must be ignored by downstream readers so productization surfaces can evolve without breaking old consumers.
