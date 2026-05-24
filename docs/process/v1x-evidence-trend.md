# v1.x Evidence Trend

## Summary

- baseline_cases: 4
- current_cases: 5
- average_benefit_score_delta: +0.30
- execution_run_delta: +1
- direct_without_plan_metadata_delta: +1
- current_version_assessment: better

## Version Assessment

- current_is_better: yes
- improvement_signals: average_benefit_score_delta=+0.30, execution_run_delta=+1, positive_team_advantage_delta=+7.
- limitation_signals: direct_without_plan_metadata_delta=+1; compare this with case_count_delta before treating it as a regression.

## Scenario Aggregates

- followup: cases_delta=+0, average_benefit_score_delta=+0, max_benefit_score_delta=+0
- high_risk: cases_delta=+0, average_benefit_score_delta=+0, max_benefit_score_delta=+0
- parallel: cases_delta=+0, average_benefit_score_delta=+0, max_benefit_score_delta=+0
- standard: cases_delta=+1, average_benefit_score_delta=+0, max_benefit_score_delta=+0

## Signal Deltas

- doc_sync_present: +1
- fallback_present: +0
- provenance_matches_plan_session: +1
- provenance_present: +1
- recovery_guidance_present: +1

## Team Advantage Deltas

- approved_plan_artifact: +1
- doc_sync_snapshot: +1
- execution_provenance: +1
- fallback_signal_surface: +1
- linked_execution_run: +1
- provider_runtime_selection: +1
- recovery_guidance: +1

## Direct Limitation Deltas

- no_approved_plan_artifact: +1
- no_plan_session_provenance: +1

## Interpretation

- positive score, execution-run, and team-advantage deltas favor the current capture; flat deltas mean the comparison shape stayed stable.
- treat team advantage deltas and direct limitation deltas together when judging whether governance-first orchestration is improving.
