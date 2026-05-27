# AI Work Control Plane Operations Phase 5: Memory Promotion Workflow

## Goal

Turn evidence-to-memory from a write suggestion into an explicit promotion workflow.

## Work

- Keep `EvidenceBundle.memory_recommendation.auto_write=false`.
- Add memory promotion candidates for durable outcome, decision, lesson, recovery note, and provider/runtime health note.
- Require provenance for every promotable candidate.
- Do not automatically write durable `MemoryRecord` from transient status.

## Targeted Test

```bash
pytest tests/test_memory.py tests/test_control_plane.py tests/test_cli.py tests/test_planning_support.py -q
```

## Result

Pending targeted validation.
