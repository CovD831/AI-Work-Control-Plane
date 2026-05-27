# AI Work Control Plane Operations Phase 2: Approval Inbox

## Goal

Treat approvals as an operator inbox, not just a raw queue.

## Work

- Keep `agent_orchestrator.approval_item.v1` backward-compatible.
- Add optional refs for plan, topology, run, job, evidence, and memory candidate artifacts.
- Add an inbox summary with pending/resolved/blocking counts, reason code distribution, and a recommended next command.
- Keep approval resolution records-only; it must not bypass the approved-plan execution gate.

## Targeted Test

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_team.py -q
```

## Result

Pending targeted validation.
