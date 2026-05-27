# AI Work Control Plane Live Recovery Phase 6: Dogfood

## Goal

Dogfood the local recovery chain against this repository and record the minimum recovery evidence set.

## Work Items

- Record the local chain from PlanSession to memory candidate.
- Pin awaiting-human / approval, compliance blocking, and provider/runtime degraded or fallback scenarios.
- Update runbook and master plan with the dogfood evidence path.
- Keep dogfood local-only; do not require network, external providers, or explore_cache.

## Targeted Tests

```bash
pytest tests/test_control_plane.py tests/test_team.py tests/test_cli.py tests/test_docs_process.py -q
```

## Result

Pending targeted validation.
