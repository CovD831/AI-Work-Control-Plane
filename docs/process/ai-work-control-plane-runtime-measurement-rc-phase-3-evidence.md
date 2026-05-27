# AI Work Control Plane Runtime Measurement RC Phase 3: Evidence

## Goal

Connect runtime measurement facts to workflow evidence reports and trends.

## Work Items

- Add runtime measurement metrics to evidence summary/report payloads.
- Render measured vs placeholder runtime cases in evidence markdown.
- Add runtime measurement deltas to trend markdown.
- Regenerate real-task JSON evidence, evidence report, and evidence trend.

## Targeted Tests

```bash
pytest tests/test_evidence.py tests/test_cli.py -q
```
