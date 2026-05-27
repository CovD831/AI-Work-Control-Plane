# AI Work Control Plane Real-Task Dogfood Phase 4: Documentation Sync

## Goal

Make the expanded real-task dogfood layer visible in canonical process and roadmap docs.

## Work Items

- Update the master control-plane plan with the Real-Task Dogfood track.
- Move completed evidence expansion items out of the backlog.
- Document the expanded case-file metadata shape in the README.
- Keep runtime limitations explicit.

## Targeted Tests

```bash
pytest tests/test_docs_process.py tests/test_planning_support.py -q
```

## Exit Criteria

- Canonical docs describe the expanded evidence baseline.
- Docs still pass process checks.
