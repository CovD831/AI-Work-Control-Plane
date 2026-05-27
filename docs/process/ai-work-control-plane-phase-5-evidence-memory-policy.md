# AI Work Control Plane Phase 5: Evidence -> Memory Policy

## Goal

Connect evidence bundles to memory provenance without making external cache mandatory.

## Implementation Plan

- Add a `memory_recommendation` section to evidence bundles.
- Recommend memory writes for full gate results, compliance results, approval resolutions, and dogfood outcomes.
- Keep ordinary transient status out of memory.
- Record external cache status as `available`, `optional_unavailable`, or `skipped`.

## Targeted Tests

- `pytest tests/test_evidence.py tests/test_memory.py tests/test_control_plane.py tests/test_cli.py -q`

## Exit Criteria

- Evidence bundle JSON tells operators what should become memory.
- No evidence command auto-syncs to external cache.
