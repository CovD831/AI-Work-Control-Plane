# AI Work Control Plane Operations Phase 3: Run Ledger

## Goal

Add a read-only ledger that records recovery-relevant long-cycle work state across plans, runs, jobs, approvals, evidence, and provider fallback.

## Work

- Add `agent_orchestrator.run_ledger.v1`.
- Include status coverage for completed, failed, interrupted, awaiting human, compliance blocking, provider fallback, and recovery ready.
- Link the ledger into topology snapshots and workspace index artifacts.
- Keep `team summary`, `team next`, and `team runbook` compatible; they continue to surface recovery semantics already attached to session status.

## Targeted Test

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_cli_presenters.py tests/test_team.py -q
```

## Result

Pending targeted validation.
