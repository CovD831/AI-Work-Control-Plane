# v1.x Evidence Report

## Summary

- schema_version: 1.0
- reportable_format: agent_orchestrator.workflow_evidence.v1
- case_count: 4
- average_benefit_score: 7.50
- team_cases_with_execution_run: 2
- direct_runs_without_plan_metadata: 4

## Scenario Aggregates

- followup: cases=1, average_benefit_score=6.00, max_benefit_score=6
- high_risk: cases=1, average_benefit_score=6.00, max_benefit_score=6
- parallel: cases=1, average_benefit_score=9.00, max_benefit_score=9
- standard: cases=1, average_benefit_score=9.00, max_benefit_score=9

## Signal Counts

- provenance_present: 2
- provenance_matches_plan_session: 2
- recovery_guidance_present: 4
- doc_sync_present: 4
- fallback_present: 0

## Cases

- standard_plan_artifact: scenario=standard, benefit_score=9
- followup_checklist_recovery: scenario=followup, benefit_score=6
- high_risk_auth_migration: scenario=high_risk, benefit_score=6
- parallel_validation_modules: scenario=parallel, benefit_score=9
