# AI Work Control Plane Phase 4: Approval Governance Reason Codes

## Goal

Make approval queue entries auditable through stable reason codes.

## Implementation Plan

- Add `reason_code` to `ApprovalItem`.
- Generate codes for blocked sessions, human decisions, compliance blockers, provider fallback, rescue/reroute, dirty overlap, and optional external cache state.
- Hydrate old approval payloads by inferring a safe reason code.
- Group pretty approval output by reason code.

## Targeted Tests

- `pytest tests/test_control_plane.py tests/test_cli.py tests/test_events.py tests/test_memory.py -q`

## Exit Criteria

- JSON approval items expose `reason_code`.
- Legacy approval payloads remain readable.
- Resolving approvals still only records event/memory and does not execute gated work.
