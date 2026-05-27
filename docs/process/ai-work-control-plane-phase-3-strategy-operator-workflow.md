# AI Work Control Plane Phase 3: StrategyDecision Operator Workflow

## Goal

Make StrategyDecision visible in normal operator workflow surfaces.

## Implementation Plan

- Add a deterministic `strategy_decision` summary to session status output.
- Show the strategy next goal, rationale, risks, and validation plan in `team summary`.
- Use the strategy next goal in `team next` without executing anything.
- Show a control-plane strategy section in `team runbook`.

## Targeted Tests

- `pytest tests/test_cli.py tests/test_team.py tests/test_cli_presenters.py -q`

## Exit Criteria

- JSON remains pure and pretty output remains human-readable.
- StrategyDecision is visible without requiring `team topology inspect`.
