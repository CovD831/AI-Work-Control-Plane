# AI Work Control Plane Runtime Bridge Dogfood Evidence

## Summary

This repository now dogfoods Runtime Bridge Fidelity as the next control-plane layer after Live Recovery.

The pinned runtime chain is:

```text
JobRecord -> ProviderSessionSnapshot -> RuntimeOperationReceipt
  -> RuntimeEventStream -> RecoveryRecommendation
  -> WorkspaceStatus / EvidenceBundle / UI
```

## Local Scenarios

- Completed job: provider session snapshot reports terminal liveness and terminal-safe operation support.
- Running job: provider session snapshot keeps session/thread/runtime-mode fields visible from the job record.
- Terminal send: runtime operation receipts preserve `already_terminal` without mutating execution state.
- Cancelled job: cancel receipts remain records-only and attached to the job payload.
- Missing session after restart: snapshots report `session_missing`/`missing` rather than claiming a live bridge.
- Auth-required direct API: runtime events preserve auth-required state without persisting secrets.
- Provider unavailable or fallback: runtime event stream carries degraded reason and recovery-safe next command.

## Evidence Commands

Targeted validation used:

```bash
pytest tests/test_command.py tests/test_jobs.py -q
pytest tests/test_control_plane.py tests/test_cli.py tests/test_cli_presenters.py -q
pytest tests/test_ui_service.py tests/test_team.py tests/test_messages.py -q
```

## Boundary

Runtime Bridge Fidelity is still a control-plane surface. It does not own long-lived provider sessions, does not replace Codex/Claude CLIs, and does not bypass approved-plan execution gates.
