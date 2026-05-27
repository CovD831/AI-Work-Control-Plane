# AI Work Control Plane Live Recovery Phase 0: Baseline

## Goal

Start the Live Recovery Track without changing CLI compatibility or widening provider/runtime scope.

This phase only establishes the plan and synchronizes canonical docs. Implementation starts in Phase 1.

## Work Items

- Add the Live Recovery Track master plan.
- Mark the next major gap as richer live recovery telemetry, provider/runtime bridge fidelity, and broader real-task dogfood coverage.
- Keep Operations Track as the baseline operator surface.
- Keep explicit orchestration below the control plane.

## Targeted Tests

```bash
pytest tests/test_docs_process.py tests/test_planning_support.py -q
```

## Result

Pending targeted validation.
