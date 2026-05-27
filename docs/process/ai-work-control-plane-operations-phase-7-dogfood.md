# AI Work Control Plane Operations Phase 7: Dogfood

## Goal

Pin the complete operations chain as the default way this repository should observe itself.

## Work

- Record the dogfood chain from PlanSession through workspace index, context, strategy, topology blueprint, approval inbox, run ledger, evidence, and memory candidates.
- Write dogfood evidence to `docs/process/ai-work-control-plane-operations-dogfood-evidence.md`.
- Keep the scenario local-only and dependency-free.

## Targeted Test

```bash
pytest tests/test_control_plane.py tests/test_team.py tests/test_cli.py tests/test_docs_process.py -q
```

## Result

Pending targeted validation.
