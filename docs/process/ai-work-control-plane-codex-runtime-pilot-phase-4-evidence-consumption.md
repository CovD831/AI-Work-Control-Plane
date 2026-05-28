# AI Work Control Plane Codex Runtime Pilot Phase 4: Evidence Consumption

## Goal

Make the Codex Runtime Pilot evidence visible through existing control-plane consumption surfaces without turning those surfaces into Codex-specific branches.

The evidence path is:

```text
codex exec --json
  -> job parsed payload
  -> ProviderSessionRef / CodexExecJson
  -> ProviderEvidenceSummary
  -> workspace-status / evidence-gates / setup readiness
```

## Implementation

- Add `agent_orchestrator.provider_evidence_summary.v1`.
- Summarize recent job records for provider-owned refs, Codex JSON event counts, malformed event counts, final-message artifact capture, and provider-reported usage.
- Surface the summary through:
  - `team workspace-status --format json`
  - `team evidence-gates --format json`
  - `team setup --runtime command --format json`
- Keep session ownership explicit:
  - `provider_owned_ref_count` counts observed provider-owned refs.
  - `session_ownership_claim` remains `provider_owned` or `none`.
  - No field claims persistent Agent Orchestrator ownership of a Codex session.

## Boundary

- This phase does not add provider-native resume, send, or cancel.
- This phase does not require live Codex calls.
- This phase does not estimate token or cost from logs.
- Usage/cost is `measured` only when a provider payload reports usage directly; otherwise it remains `placeholder`.

## Validation

Targeted validation:

```bash
pytest tests/test_control_plane.py::test_workspace_index_summarizes_codex_pilot_provider_evidence tests/test_control_plane.py::test_evidence_bundle_reports_gate_evidence_shape tests/test_cli.py::test_team_setup_json_mode_remains_machine_readable -q
```

Observed targeted validation:

- `pytest tests/test_control_plane.py::test_workspace_index_summarizes_codex_pilot_provider_evidence tests/test_control_plane.py::test_evidence_bundle_reports_gate_evidence_shape tests/test_cli.py::test_team_setup_json_mode_remains_machine_readable -q`: 3 passed.
- `pytest tests/test_command.py tests/test_control_plane.py tests/test_cli.py -q`: 132 passed.
- `pytest tests/test_control_plane.py tests/test_cli.py tests/test_team.py -q`: 219 passed.
- CLI consumption coverage now includes fake Codex pilot jobs in `team setup --format json`, `team workspace-status --format json`, and `team evidence-gates --format json`.

Final convergence validation:

```bash
pytest
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
```

## Result

Phase 4 is complete:

- Fake Codex pilot jobs contribute provider evidence to setup readiness, workspace status, and evidence gates.
- `ProviderEvidenceSummary` counts provider-owned refs, Codex JSON events, malformed events, final-message artifact capture, and provider-reported usage without creating Codex-specific control-plane branches.
- The summary keeps the session boundary explicit with `session_ownership_claim: provider_owned` only when the observed ref itself is provider-owned.
