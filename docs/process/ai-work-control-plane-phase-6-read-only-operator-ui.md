# AI Work Control Plane Phase 6: Read-Only Operator UI Surfaces

## Goal

Expose stable control-plane state in the operator console without adding mutations.

## Implementation Plan

- Keep UI payloads read-only.
- Include workspace state, strategy decision, topology snapshot, approval queue, and evidence gates in the session detail payload.
- Render compact status summaries only; do not add approval resolve UI or graph editing.
- Keep empty/no-approval/external-cache-unavailable states displayable.

## Targeted Tests

- `pytest tests/test_ui_service.py tests/test_ui_server.py -q`

## Exit Criteria

- UI service payload consumes stable control-plane JSON schema.
- Frontend displays read-only strategy/topology/approval/evidence summaries.
