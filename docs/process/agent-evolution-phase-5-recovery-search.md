# Agent Evolution Phase 5: Recovery Search

## Goal

Upgrade recovery recommendations from a single next command into a bounded recovery search summary.

This phase keeps recovery operator-driven and read-only. It does not execute alternative branches automatically.

## Scope

- add bounded recovery branch candidates to recovery recommendations
- score and rank a small fixed set of recovery options
- expose selected branch, runner-up branch, and branch rationale
- keep execution and approval gates unchanged

## Non-Goals

- no automatic branch execution
- no deep tree expansion
- no retrieval changes yet
- no new agent autonomy yet

## Implementation Steps

1. Extend recovery recommendation with ranked branch candidates.
2. Add a fixed search summary with selected branch, runner-up branch, and disagreement level.
3. Reuse existing blocker, approval, compliance, and evidence signals as branch inputs.
4. Add tests for recovery search output and branch ranking.

## Acceptance Criteria

- recovery recommendations include explicit branch candidates
- branch candidates include score, rationale, and required evidence/approval notes
- a search summary records selected branch and runner-up branch
- recommendation remains read-only and operator-facing
- targeted tests for control-plane and team recovery flows pass

## Targeted Tests

```bash
pytest tests/test_control_plane.py tests/test_team.py tests/test_cli.py -q
```

## Exit Condition

Advance to Phase 6 only after targeted tests pass and bounded recovery search data is visible in persisted recovery recommendations.
