# AI Work Control Plane Runtime Measurement RC Phase 1: Schema

## Goal

Define a compatible runtime measurement payload for job, runtime, control-plane, and evidence consumers.

## Work Items

- Add runtime measurement facts to persisted job payloads.
- Derive measurement for older jobs from existing timestamps, exit code, status, and metadata.
- Add `measurement_status` with `measured`, `placeholder`, and `unavailable`.
- Keep usage/cost values placeholder unless a runtime explicitly reports real values.
- Surface the payload from provider session snapshots and runtime event streams.

## Targeted Tests

```bash
pytest tests/test_control_plane.py tests/test_evidence.py tests/test_messages.py -q
```
