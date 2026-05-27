# v1.x Evidence Report

## Summary

- schema_version: 1.0
- reportable_format: agent_orchestrator.workflow_evidence.v1
- case_count: 9
- average_benefit_score: 17.00
- team_cases_with_execution_run: 9
- direct_runs_without_plan_metadata: 9

## Conclusion Summary

- planning_quality: 9/9 cases produced an approved plan artifact across scenarios: compliance_blocking, followup, high_risk, interruption_recovery, parallel, runtime_fidelity, standard, ui_workflow.
- rescue_quality: 9/9 cases carried next-step or recovery guidance for the operator.
- runtime_limitation: 0/9 cases showed provider fallback signals; v1.x evidence validates command-runtime selection/provenance, not a full provider bridge or persistent session manager.
- fixed_template_advantage: 9/9 cases matched execution provenance to the plan session while 9 direct runs lacked approved-plan metadata.

## Scenario Aggregates

- compliance_blocking: cases=1, average_benefit_score=17.00, max_benefit_score=17
- followup: cases=1, average_benefit_score=17.00, max_benefit_score=17
- high_risk: cases=1, average_benefit_score=17.00, max_benefit_score=17
- interruption_recovery: cases=1, average_benefit_score=17.00, max_benefit_score=17
- parallel: cases=1, average_benefit_score=17.00, max_benefit_score=17
- runtime_fidelity: cases=1, average_benefit_score=17.00, max_benefit_score=17
- standard: cases=2, average_benefit_score=17.00, max_benefit_score=17
- ui_workflow: cases=1, average_benefit_score=17.00, max_benefit_score=17

## Signal Counts

- provenance_present: 9
- provenance_matches_plan_session: 9
- recovery_guidance_present: 9
- doc_sync_present: 9
- fallback_present: 0

## Real-Task Dogfood Metrics

- recovery_recommendation_coverage: 9
- runtime_fidelity_coverage: 9
- compliance_blocking_coverage: 1
- postmortem_ready_cases: 9
- cost_latency_ready_cases: 9

## Runtime Measurement Metrics

- measured_runtime_cases: 9
- placeholder_runtime_cases: 0
- provider_available_cases: 0
- degraded_runtime_cases: 0
- command_duration_available_cases: 9
- rc_readiness_blockers: 0

## Cases

- standard_plan_artifact: scenario=standard, benefit_score=17
  - postmortem: matched_expected_signals=4, runtime_fidelity=True, cost_latency_ready=True
  - runtime_measurement: status=measured, duration_available=True, jobs=6
- followup_checklist_recovery: scenario=followup, benefit_score=17
  - postmortem: matched_expected_signals=4, runtime_fidelity=True, cost_latency_ready=True
  - runtime_measurement: status=measured, duration_available=True, jobs=6
- high_risk_auth_migration: scenario=high_risk, benefit_score=17
  - postmortem: matched_expected_signals=4, runtime_fidelity=True, cost_latency_ready=True
  - runtime_measurement: status=measured, duration_available=True, jobs=6
- parallel_validation_modules: scenario=parallel, benefit_score=17
  - postmortem: matched_expected_signals=4, runtime_fidelity=True, cost_latency_ready=True
  - runtime_measurement: status=measured, duration_available=True, jobs=4
- cli_workflow_hardening: scenario=standard, benefit_score=17
  - postmortem: matched_expected_signals=4, runtime_fidelity=True, cost_latency_ready=True
  - runtime_measurement: status=measured, duration_available=True, jobs=6
- ui_operator_console_flow: scenario=ui_workflow, benefit_score=17
  - postmortem: matched_expected_signals=4, runtime_fidelity=True, cost_latency_ready=True
  - runtime_measurement: status=measured, duration_available=True, jobs=6
- compliance_blocking_recovery: scenario=compliance_blocking, benefit_score=17
  - postmortem: matched_expected_signals=4, runtime_fidelity=True, cost_latency_ready=True
  - runtime_measurement: status=measured, duration_available=True, jobs=6
- runtime_fidelity_inspection: scenario=runtime_fidelity, benefit_score=17
  - postmortem: matched_expected_signals=4, runtime_fidelity=True, cost_latency_ready=True
  - runtime_measurement: status=measured, duration_available=True, jobs=6
- interrupted_task_resume: scenario=interruption_recovery, benefit_score=17
  - postmortem: matched_expected_signals=4, runtime_fidelity=True, cost_latency_ready=True
  - runtime_measurement: status=measured, duration_available=True, jobs=6

## Takeaways

- governance-first cases surfaced 9 linked execution runs out of 9 cases.
- direct runs without plan metadata: 9.
- when provenance, recovery guidance, and doc sync appear together, the workflow is easier to explain than a fixed-template run.
