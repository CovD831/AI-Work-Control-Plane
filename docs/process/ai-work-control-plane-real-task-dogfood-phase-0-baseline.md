# AI Work Control Plane Real-Task Dogfood Phase 0: Baseline

## Goal

Seal the next-stage plan and keep the work focused on measured real-task dogfood.

## Work Items

- Add the Real-Task Dogfood master plan.
- Confirm the track starts after the frozen control-plane baseline.
- Keep this phase documentation-only.
- Run targeted docs/evidence tests before moving to Phase 1.

## Targeted Tests

```bash
pytest tests/test_docs_process.py tests/test_evidence.py -q
```

## Exit Criteria

- The phase plan exists.
- The master plan names scope, phases, target shape, and final gates.
- Targeted tests pass.
