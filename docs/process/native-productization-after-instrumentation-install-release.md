# Native Productization Install / Release Readiness

## Install

- From repo root: `pip install -e .`
- For UI extras, if needed: `pip install -e '.[ui]'`

## Start

- Product posture: `agent-orchestrator product posture`
- Provider/runtime diagnosis: `agent-orchestrator product diagnose`
- Daily-driver smoke: `agent-orchestrator product smoke`
- Evidence consumption: `agent-orchestrator product evidence`

## Smoke Test

Recommended verification:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli product posture --format json
PYTHONPATH=src python -m agent_orchestrator.cli product diagnose --format json
PYTHONPATH=src python -m agent_orchestrator.cli product evidence --format json
```

Expected output:

- operator-readable product posture
- provider/runtime availability with fix hints
- authoritative comparison summary with instrumentation closure
- next action without raw JSON inspection

## Known Limitations

- Full desktop/web productization is out of scope.
- Provider auth may still be degraded outside the mock path.
- External OpenCode comparison depends on a working OpenCode runtime.

## Release Checklist

- product posture command returns readable summary
- provider/runtime diagnosis is redaction-safe
- evidence summary includes authoritative comparison
- smoke command returns a deterministic operator summary
- tests pass

## Rollback / Cleanup

- Remove `.agent_orchestrator/runs/*.json` artifacts if a smoke run needs reset.
- Re-run `agent-orchestrator product diagnose` after fixing provider auth or command availability.
