# AI Work Control Plane Phase 7: Dogfood Scenario

## Goal

Pin one complete AI Work Control Plane pipeline as the minimum regression scenario.

## Implementation Plan

- Use a real PlanSession to generate workspace state, context packet, strategy decision, topology snapshot, approval/evidence, and memory records.
- Ensure blocked sessions create approval items without bypassing execution gates.
- Ensure approval resolution writes event + memory and later snapshots observe the resolved approval state.
- Document this dogfood scenario as the acceptance line for future control-plane changes.

## Targeted Tests

- `pytest tests/test_control_plane.py tests/test_team.py tests/test_cli.py tests/test_docs_process.py -q`

## Exit Criteria

- The dogfood test covers the full artifact chain.
- Future control-plane changes must keep this scenario passing.
