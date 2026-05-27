# AI Work Control Plane Live Recovery Phase 5: Evidence And Memory Loop

## Goal

Connect recovery telemetry to evidence and memory promotion without auto-writing transient status.

## Work Items

- Let EvidenceBundle reference recovery timeline and runtime event stream artifact refs when available.
- Extend memory promotion candidates with recovery pattern, runtime degradation note, approval delay note, and compliance blocking note.
- Keep `memory_recommendation.auto_write=false`.
- Require provenance on every candidate before durable MemoryRecord promotion.

## Targeted Tests

```bash
pytest tests/test_memory.py tests/test_control_plane.py tests/test_cli.py tests/test_planning_support.py -q
```

## Result

Pending targeted validation.
