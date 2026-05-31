# AI Work Control Plane Continuous Phase 6: Dogfood

## Goal

Pin one real repository dogfood path as the default internal workflow.

## Implementation Plan

- Exercise PlanSession -> WorkspaceState -> ContextPacket -> StrategyDecision -> TopologySnapshot -> Approval/Evidence -> MemoryRecord.
- Write dogfood evidence into process documentation.
- Keep explore_cache optional.

## Targeted Tests

- `pytest tests/test_control_plane.py tests/test_team.py tests/test_cli.py tests/test_docs_process.py -q`

## Result

- Dogfood evidence is recorded in [AI Work Control Plane Dogfood Evidence](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/ai-work-control-plane-dogfood-evidence.md).
