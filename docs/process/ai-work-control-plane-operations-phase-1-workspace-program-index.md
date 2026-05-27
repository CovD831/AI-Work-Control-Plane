# AI Work Control Plane Operations Phase 1: Workspace / Program Index v2

## Goal

Make `.agent_orchestrator/workspace/index.json` the operator's current-site index, not only a lifecycle ref file.

## Work

- Keep `agent_orchestrator.workspace_index.v1` backward-compatible.
- Add optional fields: `program`, `active_artifacts`, `recent_artifacts`, `open_approvals`, `recent_runs`, `memory_candidates`, and `provider_runtime_health`.
- Make `team workspace-status --format json` return the index payload while preserving the nested `workspace_state`.
- Let the UI read the same index as a read-only control-plane artifact.

## Targeted Test

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_ui_service.py -q
```

## Result

Pending targeted validation.
