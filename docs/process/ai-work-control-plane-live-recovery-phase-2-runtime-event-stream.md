# AI Work Control Plane Live Recovery Phase 2: Runtime Event Stream

## Goal

Add a read-only runtime event stream artifact for recovery telemetry without implementing a full provider bridge.

## Work Items

- Add `agent_orchestrator.runtime_event_stream.v1`.
- Record runtime mode, command/job intent, tool intent, result status, failure reason, fallback reason, degraded capability reason, usage/cost placeholder, and artifact refs.
- Source events from existing plan, run, delegated job, approval, and provider/runtime metadata.
- Keep `direct_api` records-only; it cannot bypass approved-plan execution gates.

## Targeted Tests

```bash
pytest tests/test_messages.py tests/test_team.py tests/test_cli.py tests/test_control_plane.py -q
```

## Result

Pending targeted validation.
