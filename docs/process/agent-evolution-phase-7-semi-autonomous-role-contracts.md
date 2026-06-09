# Agent Evolution Phase 7: Semi-Autonomous Role Contracts

## Goal

Turn static role slots into semi-autonomous role contracts so each role advertises not only allowed actions, but also how it is expected to collaborate, escalate, and report local state.

## Scope

- extend role contracts with structured inputs and outputs
- declare bounded semi-autonomous capabilities for blockers, alternatives, requests for information, and reflections
- expose role contract capabilities through operator-facing role payloads and work-graph views
- keep execution routing and approval gates unchanged

## Non-Goals

- no runtime autonomy loop
- no external A2A adapter yet
- no LangGraph runtime pilot yet

## Implementation Steps

1. Extend `RoleContract` with semi-autonomous collaboration metadata.
2. Define stable capability defaults per role in the existing role registry.
3. Surface the new contract fields in `team roles` payloads.
4. Attach relevant role contract summaries to work-graph nodes so operators can inspect autonomy boundaries in context.
5. Add targeted tests for role contracts, CLI output, and work-graph payload shape.

## Acceptance Criteria

- every exported role contract includes structured input/output and collaboration capability metadata
- builder, reviewer, rescue, and governance roles expose distinct semi-autonomous capability profiles
- work-graph plan trees surface the owner role contract for each node
- the change is additive and does not alter approval or execution gate behavior
- targeted tests pass

## Targeted Tests

```bash
pytest tests/test_actions.py tests/test_cli.py tests/test_work_graph.py -q
```

## Exit Condition

Advance beyond Phase 7 only after the semi-autonomous role contract metadata is visible in role exports and work-graph inspection payloads, and the targeted tests pass.
