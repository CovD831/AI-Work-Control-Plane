# AI Work Control Plane Live Recovery Phase 4: Workspace Recovery Dashboard

## Goal

Make `team workspace-status --format json` the default read-only recovery dashboard for the current workspace.

## Work Items

- Add optional `recovery_timeline`, `runtime_events`, `recovery_recommendation`, `blocking_summary`, `resume_hint`, and `last_checkpoint` fields to the workspace index payload.
- Keep the nested `workspace_state` and existing Workspace / Program Index v2 fields compatible.
- Let UI service consume the same recovery summary read-only.
- Do not add mutation, approval resolution, or topology editing to the UI.

## Targeted Tests

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_ui_service.py -q
```

## Result

Pending targeted validation.
