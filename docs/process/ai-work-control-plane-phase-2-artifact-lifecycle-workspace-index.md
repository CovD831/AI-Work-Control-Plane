# AI Work Control Plane Phase 2: Artifact Lifecycle + Workspace Index

## Goal

Make recent control-plane artifact generation visible through `.agent_orchestrator/workspace/index.json`.

## Implementation Plan

- Keep `team workspace-status` as the workspace index writer.
- Record lifecycle references for workspace state, context packet, strategy decision, topology snapshot, and evidence bundle.
- Keep context packets non-strategic and topology snapshots read-only.
- Treat stale warnings and optional external cache unavailable as state, not failure.

## Targeted Tests

- `pytest tests/test_control_plane.py tests/test_cli.py -q`

## Exit Criteria

- Workspace index remains backward-compatible for `WorkspaceIndexStore.read()`.
- Recent artifact refs contain format, digest, timestamps, and short summaries.
