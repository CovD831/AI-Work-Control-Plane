# Agent Evolution Phase 4: Limited Multi-Path Reasoning

## Goal

Introduce bounded multi-path reasoning at selected decision points without turning the execution runtime into an open-ended search system.

This phase focuses on judgment-heavy decisions:

- route selection
- reroute escalation
- recovery recommendation summaries

## Scope

- add bounded consensus summaries to route selection
- add bounded consensus summaries to reroute policy decisions
- keep selection deterministic and backward-compatible
- record disagreement explicitly when alternatives remain plausible

## Non-Goals

- no tree search yet
- no dynamic branch execution
- no review committee voting yet
- no retrieval changes yet

## Implementation Steps

1. Extend routing candidates with comparative scoring and disagreement level.
2. Add a route consensus summary to routing decisions.
3. Add a reroute consensus summary to decision artifacts.
4. Add tests for route consensus, reroute consensus, and round-trip serialization.

## Acceptance Criteria

- routing decisions expose a bounded consensus summary
- consensus summary records selected mode, runner-up mode, and disagreement level
- decision artifacts expose reroute consensus data alongside reroute policy
- current orchestration behavior remains deterministic
- targeted tests for routing, orchestrator, and team flow pass

## Targeted Tests

```bash
pytest tests/test_routing.py tests/test_orchestrator.py tests/test_team.py -q
```

## Exit Condition

Advance to Phase 5 only after targeted tests pass and bounded multi-path summaries are visible in persisted run artifacts.
