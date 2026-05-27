# AI Work Control Plane Runtime Measurement RC Phase 4: Readiness

## Goal

Make runtime measurement visible in RC readiness documentation and operator guidance.

## Work Items

- Update candidate checklist and freeze plan with runtime measurement gates.
- Document that runtime measurement is not provider bridge readiness.
- Keep `team setup --runtime command --format json` as the machine-readable readiness surface.
- Sync README and operator runbook language.

## Targeted Tests

```bash
pytest tests/test_cli.py tests/test_cli_presenters.py tests/test_docs_process.py tests/test_planning_support.py -q
```
