# AI Work Control Plane Live Recovery Phase 1: Recovery Timeline

## Goal

Add a read-only recovery timeline artifact so operator commands can explain long-cycle recovery state without manually stitching together sessions, approvals, evidence, and run ledger entries.

## Work Items

- Add `agent_orchestrator.recovery_timeline.v1`.
- Build timeline entries from PlanSession, Run Ledger, Approval Inbox, Evidence Bundle, provider fallback, and compliance state.
- Surface timeline references in `team summary`, `team next`, and `team runbook` without changing existing command names.
- Keep the artifact read-only and additive.

## Targeted Tests

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_cli_presenters.py tests/test_team.py -q
```

## Result

Pending targeted validation.
