# AI Work Control Plane Codex Runtime Pilot Plan

## Purpose

This track turns the Provider Runtime Bridge Evaluation recommendation into one narrow Codex runtime pilot.

The goal is not a full Codex bridge. The goal is to prove that a Codex non-interactive execution path can provide better structured runtime evidence while preserving the AI Work Control Plane boundary.

## Scope

- Add an opt-in Codex pilot path for `codex exec --json`.
- Capture final-message artifacts through `--output-last-message` when configured.
- Parse Codex JSONL output into a bounded payload.
- Persist provider-owned `ProviderSessionRef` metadata when observed.
- Surface that ref through `team runtime inspect` via `ProviderSessionSnapshot`.
- Keep token/cost placeholder unless Codex reports usage directly.
- Test with fake runners and fixtures only.

## Out Of Scope

- Live Codex calls in tests or release gates.
- Persistent Codex session ownership.
- Provider-native send/cancel guarantees.
- Codex as the only provider.
- Token/cost estimation from logs.

## Phase Plan

### Phase 0: Pilot Plan

Record this plan and preserve the full-bridge boundary.

### Phase 1: Fixture + Parser

Add JSONL parsing for `codex exec --json` output and final-message artifact capture.

Targeted tests:

```bash
pytest tests/test_command.py -q
```

### Phase 2: Adapter Command Shape

Make `CodexCliAdapter` opt into `--json` and `--output-last-message` only when request metadata enables the pilot.

Targeted tests:

```bash
pytest tests/test_command.py -q
```

### Phase 3: Job Metadata + Runtime Inspect

Persist `codex_exec_json` payloads and provider-owned refs in job records, then expose `provider_session_ref` through provider session snapshots.

Targeted tests:

```bash
pytest tests/test_command.py tests/test_control_plane.py tests/test_cli.py -q
```

### Phase 4: Evidence Consumption

Verify workspace and evidence surfaces consume the pilot job through existing runtime fidelity paths without Codex-specific control-plane branching.

Result artifact:

- `docs/process/ai-work-control-plane-codex-runtime-pilot-phase-4-evidence-consumption.md`

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_team.py -q
```

### Phase 5: Final Convergence

Record pilot evidence and run final validation.

Result artifact:

- `docs/process/ai-work-control-plane-codex-runtime-pilot-phase-5-final-convergence.md`

Final commands:

```bash
pytest
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
git status --short
```

## Completion Bar

The track is complete when fake Codex runner tests prove:

```text
codex exec --json
  -> parsed JSONL / final message
  -> job payload
  -> ProviderSessionRef
  -> team runtime inspect
  -> workspace/evidence consumption
```

without claiming provider-native session ownership or live-provider determinism.

## Post-Pilot v1 Final Externalization Hardening

After the Codex Runtime Pilot closes, the next stage is to prove that governance is externally portable, not just locally visible.

This stage adds a portable bundle path:

```text
workspace-status / context-packet / evidence-gates / approvals / provider evidence
  -> team governance-bundle export
  -> saved agent_orchestrator.governance_bundle.v1
  -> team governance-bundle inspect
  -> offline completeness, auditability, and boundary verdict
```

Result artifact:

- `docs/process/ai-work-control-plane-v1-final-externalization-hardening.md`

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_docs_process.py -q
```

Final commands:

```bash
pytest
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
```

This is the bar for saying the system has reached an externalized governance shape: an external reviewer can receive a read-only JSON bundle, inspect it without a live workspace, and see the runtime/provider boundaries without asking the orchestrator to resume or own a provider session.
