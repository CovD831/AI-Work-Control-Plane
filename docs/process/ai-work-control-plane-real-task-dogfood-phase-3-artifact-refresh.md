# AI Work Control Plane Real-Task Dogfood Phase 3: Artifact Refresh

## Goal

Regenerate the committed evidence artifacts from the expanded real-task case matrix.

## Work Items

- Capture current real-task evidence JSON from `docs/process/evidence-cases.json`.
- Regenerate `docs/process/v1x-evidence-report.md`.
- Regenerate `docs/process/v1x-evidence-trend.md` by comparing the stable built-in benchmark capture against the expanded real-task capture.
- Keep generated machine-readable evidence in `.agent_orchestrator/evidence/real-tasks.json`.

## Targeted Tests

```bash
pytest tests/test_evidence.py tests/test_cli.py -q
```

## Exit Criteria

- Report and trend include real-task dogfood metrics.
- Evidence commands still pass CLI tests.
