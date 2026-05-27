# v1.x Evidence Trend

## Summary

- baseline_cases: 4
- current_cases: 9
- average_benefit_score_delta: +0
- execution_run_delta: +5
- direct_without_plan_metadata_delta: +5
- current_version_assessment: better

## Version Assessment

- current_is_better: yes
- improvement_signals: average_benefit_score_delta=+0, execution_run_delta=+5, positive_team_advantage_delta=+75.
- limitation_signals: direct_without_plan_metadata_delta=+5; compare this with case_count_delta before treating it as a regression.

## Scenario Aggregates

- compliance_blocking: cases_delta=+1, average_benefit_score_delta=+17, max_benefit_score_delta=+17
- followup: cases_delta=+0, average_benefit_score_delta=+0, max_benefit_score_delta=+0
- high_risk: cases_delta=+0, average_benefit_score_delta=+0, max_benefit_score_delta=+0
- interruption_recovery: cases_delta=+1, average_benefit_score_delta=+17, max_benefit_score_delta=+17
- parallel: cases_delta=+0, average_benefit_score_delta=+0, max_benefit_score_delta=+0
- runtime_fidelity: cases_delta=+1, average_benefit_score_delta=+17, max_benefit_score_delta=+17
- standard: cases_delta=+1, average_benefit_score_delta=+0, max_benefit_score_delta=+0
- ui_workflow: cases_delta=+1, average_benefit_score_delta=+17, max_benefit_score_delta=+17

## Signal Deltas

- doc_sync_present: +5
- fallback_present: +0
- provenance_matches_plan_session: +5
- provenance_present: +5
- recovery_guidance_present: +5

## Real-Task Metric Deltas

- compliance_blocking_coverage: +1
- cost_latency_ready_cases: +5
- execution_artifact_cases: +5
- fallback_coverage: +1
- interruption_recovery_coverage: +5
- postmortem_ready_cases: +5
- recovery_recommendation_coverage: +5
- runtime_fidelity_coverage: +5

## Team Advantage Deltas

- approval_observability: +5
- approved_plan_artifact: +5
- cli_worker_default_preserved: +5
- direct_api_governance_roles: +5
- doc_sync_snapshot: +5
- execution_provenance: +5
- fallback_signal_surface: +5
- fresh_resume_policy: +5
- gate_evidence_artifact: +5
- knowledge_artifacts: +5
- linked_execution_run: +5
- provider_runtime_selection: +5
- recovery_guidance: +5
- role_contract_enforced: +5
- usage_cost_placeholder: +5

## Direct Limitation Deltas

- no_approved_plan_artifact: +5
- no_plan_session_provenance: +5

## Interpretation

- positive score, execution-run, and team-advantage deltas favor the current capture; flat deltas mean the comparison shape stayed stable.
- treat team advantage deltas and direct limitation deltas together when judging whether governance-first orchestration is improving.
