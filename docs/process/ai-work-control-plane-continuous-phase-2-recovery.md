# AI Work Control Plane Continuous Phase 2: Recovery Semantics

## Goal

Make interruption, delegated failure, human approval, compliance blocking, provider fallback, and execution blockers visible through recovery metadata.

## Implementation Plan

- Extend recovery semantics with interruption-aware and gate-authority fields.
- Keep approval resolution record-only.
- Keep memory writes limited to durable provenance-backed outcomes.

## Targeted Tests

- `pytest tests/test_team.py tests/test_cli.py tests/test_planning_support.py tests/test_control_plane.py -q`
