# v1.x Evidence Report

## Summary

- schema_version: 1.0
- reportable_format: agent_orchestrator.workflow_evidence.v1
- case_count: 5
- average_benefit_score: 7.80
- team_cases_with_execution_run: 3
- direct_runs_without_plan_metadata: 5

## Conclusion Summary

- planning_quality: 3/5 cases produced an approved plan artifact across scenarios: followup, high_risk, parallel, standard.
- rescue_quality: 5/5 cases carried next-step or recovery guidance for the operator.
- runtime_limitation: 0/5 cases showed provider fallback signals; v1.x evidence validates command-runtime selection/provenance, not a full provider bridge or persistent session manager.
- fixed_template_advantage: 3/5 cases matched execution provenance to the plan session while 5 direct runs lacked approved-plan metadata.

## Scenario Aggregates

- followup: cases=1, average_benefit_score=6.00, max_benefit_score=6
- high_risk: cases=1, average_benefit_score=6.00, max_benefit_score=6
- parallel: cases=1, average_benefit_score=9.00, max_benefit_score=9
- standard: cases=2, average_benefit_score=9.00, max_benefit_score=9

## Signal Counts

- provenance_present: 3
- provenance_matches_plan_session: 3
- recovery_guidance_present: 5
- doc_sync_present: 5
- fallback_present: 0

## Cases

- standard_plan_artifact: scenario=standard, benefit_score=9
- followup_checklist_recovery: scenario=followup, benefit_score=6
- high_risk_auth_migration: scenario=high_risk, benefit_score=6
- parallel_validation_modules: scenario=parallel, benefit_score=9
- cli_workflow_hardening: scenario=standard, benefit_score=9

## Takeaways

- governance-first cases surfaced 3 linked execution runs out of 5 cases.
- direct runs without plan metadata: 5.
- when provenance, recovery guidance, and doc sync appear together, the workflow is easier to explain than a fixed-template run.
