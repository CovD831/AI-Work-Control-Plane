# Agent Evolution Phase 1: Decision Externalization

## Goal

Expand the existing decision contract so the system records not only the selected route, but also candidate options, rejected alternatives, and the reasons behind those choices.

This phase improves explainability without changing the current control-plane authority or execution semantics.

## Scope

- extend routing output with candidate mode information
- extend execution decision artifacts with candidate routes and rejected alternatives
- keep all new fields additive and backward-compatible
- keep current execution outcomes unchanged

## Non-Goals

- no new review roles
- no message schema redesign
- no recovery search tree yet
- no LangGraph or A2A integration work

## Implementation Steps

1. Extend `RoutingDecision` to include explicit mode candidates and selection rationale.
2. Extend `DecisionArtifact.route` to record route candidates and rejected alternatives.
3. Extend `DecisionArtifact.reroute_policy` to record rejected reroute alternatives where applicable.
4. Add or update targeted tests for routing, orchestrator, and control-plane serialization.

## Acceptance Criteria

- router output includes a selected mode plus explicit candidate modes
- candidate modes include rationale that explains why they were considered
- decision artifacts include the selected route plus rejected route alternatives
- decision artifacts remain serializable and backward-compatible through run persistence
- current orchestration behavior still passes existing targeted tests

## Targeted Tests

```bash
pytest tests/test_routing.py tests/test_orchestrator.py tests/test_control_plane.py -q
```

## Exit Condition

Advance to Phase 2 only after targeted tests pass and the new decision fields are visible in persisted artifacts.
