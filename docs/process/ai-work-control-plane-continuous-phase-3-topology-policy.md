# AI Work Control Plane Continuous Phase 3: Topology Policy

## Goal

Broaden topology policy explanations without making topology snapshots mutable.

## Implementation Plan

- Surface task size, risk, parallelism, dependency shape, review policy, and provider fallback signals.
- Keep `StrategyDecision.executes` false.
- Keep `ExecutionTopologySnapshot` read-only and linked to approval, evidence, and memory.

## Targeted Tests

- `pytest tests/test_team.py tests/test_cli.py tests/test_actions.py tests/test_control_plane.py -q`
