# AI Work Control Plane Real-Task Dogfood Phase 1: Evidence Schema

## Goal

Make workflow evidence report real-task dogfood quality, not only v1.x benchmark quality.

## Work Items

- Allow case files to carry risk profile, operator goal, expected signals, and runtime expectation metadata.
- Add postmortem signals to each captured case.
- Add summary/report aggregates for recovery coverage, compliance blocking coverage, runtime fidelity coverage, postmortem readiness, and cost/latency readiness.
- Render the new sections in evidence report and trend report markdown.
- Keep existing evidence commands and schema version compatible.

## Targeted Tests

```bash
pytest tests/test_evidence.py tests/test_cli.py -q
```

## Exit Criteria

- Existing evidence payload consumers still pass.
- New report sections are covered by tests.
- Trend deltas include real-task dogfood metrics.
