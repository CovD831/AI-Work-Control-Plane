# AI Work Control Plane Phase 1: Artifact Contract Hardening

## Goal

Turn the v1 control-plane artifacts into documented contracts with stable fields and legacy hydration coverage.

## Implementation Plan

- Add `docs/process/control-plane-artifact-contracts.md`.
- Pin minimum stable fields for workspace state, context packet, strategy decision, topology snapshot, approval item, evidence bundle, and memory record.
- Add golden fixture payloads for empty workspace, active session topology, blocked approval, resolved approval, and evidence bundle.
- Add targeted tests that validate fixture formats and live builder payloads.

## Targeted Tests

- `pytest tests/test_control_plane.py tests/test_memory.py tests/test_docs_process.py -q`

## Exit Criteria

- Every control-plane artifact has a documented producer, consumer, lifecycle, compatibility rule, and minimum field set.
- Fixtures and tests reject missing `format` fields or broken legacy hydration.
