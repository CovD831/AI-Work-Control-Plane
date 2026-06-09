# Agent Evolution Phase 3: Multi-Role Review System

## Goal

Turn the current fixed review flow into a clearer multi-role review system with an explicit aggregated review summary.

This phase does not change approval authority. It makes the output of reviewer roles more structured and easier to reason about in later phases.

## Scope

- add a structured review aggregation summary to the decision verdict
- preserve the current `reviewer` and `adversarial_reviewer` runtime flow
- expose per-role review outcomes, severity mix, and aggregate verdict signals
- keep all additions backward-compatible

## Non-Goals

- no review committee or voting yet
- no routing changes
- no recovery search changes
- no autonomy changes for roles

## Implementation Steps

1. Extend `DecisionVerdict` with a structured review summary field.
2. Aggregate current review rounds by role and verdict.
3. Record severity distribution and blocking/non-blocking findings in the aggregated summary.
4. Add tests for verdict serialization and team review aggregation.

## Acceptance Criteria

- decision verdicts include a structured review summary
- the review summary records the participating roles and their verdicts
- the review summary records finding severity distribution and blocking review count
- existing review and approval behavior remains unchanged
- targeted tests for review, team flow, and CLI output pass

## Targeted Tests

```bash
pytest tests/test_review.py tests/test_team.py tests/test_cli.py -q
```

## Exit Condition

Advance to Phase 4 only after targeted tests pass and review aggregation is visible in persisted decision verdicts.
