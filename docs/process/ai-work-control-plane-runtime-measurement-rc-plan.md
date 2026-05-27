# AI Work Control Plane Runtime Measurement & RC Readiness Plan

## Purpose

This track starts after the Real-Task Dogfood Evidence baseline. It turns runtime/cost/latency placeholders into honest local measurement surfaces for this repository, while preserving the product boundary: measurement, not a full provider bridge.

## Product Boundary

In scope:

- Record runtime measurement facts from existing local job records and command-runtime jobs.
- Distinguish measured, placeholder, and unavailable usage/cost/latency state.
- Surface runtime measurement in provider session snapshots, runtime event streams, evidence reports, and release readiness.
- Keep the work local to this repository.
- Use targeted tests during implementation and final full gates only at convergence.

Out of scope:

- Persistent provider session ownership.
- Provider-native bridge semantics.
- External repository dogfood.
- Token/cost estimation when the provider runtime does not report it.
- RC tag creation.

## Target Shape

```text
JobRecord
  -> RuntimeMeasurement
  -> ProviderSessionSnapshot
  -> RuntimeEventStream
  -> EvidenceReport / EvidenceTrend
  -> ReleaseReadiness
```

## Phases

### Phase 0: Previous Track Freeze

The Real-Task Dogfood Evidence Track is committed as the clean baseline.

### Phase 1: Runtime Measurement Schema

Add compatible runtime measurement payloads and placeholder distinction.

Targeted tests:

- `pytest tests/test_control_plane.py tests/test_evidence.py tests/test_messages.py -q`

### Phase 2: CLI Runtime Measurement Capture

Make job/runtime CLI surfaces show duration, exit code, provider/runtime mode, degraded reason, and operation support facts.

Targeted tests:

- `pytest tests/test_command.py tests/test_jobs.py tests/test_tmux_runtime.py tests/test_cli.py -q`

### Phase 3: Evidence Report And Trend Refresh

Add runtime measurement metrics to evidence reports and trends, then regenerate committed evidence artifacts.

Targeted tests:

- `pytest tests/test_evidence.py tests/test_cli.py -q`

### Phase 4: RC Readiness Surface

Expose runtime measurement readiness in release-readiness docs and `team setup --runtime command --format json`.

Targeted tests:

- `pytest tests/test_cli.py tests/test_cli_presenters.py tests/test_docs_process.py tests/test_planning_support.py -q`

### Phase 5: Final Convergence

Run full tests, setup, compliance, workspace/evidence smoke checks, and record final status.

Final gates:

```bash
pytest
env PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json
env PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
env PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
env PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
git status --short
```

## Acceptance

- Runtime measurement appears on job/runtime/evidence/setup surfaces.
- Measured and placeholder states are clearly separated.
- Evidence report and trend include runtime measurement metrics.
- Release readiness can explain runtime measurement gaps without claiming provider bridge readiness.
- Full tests and compliance pass at final convergence.
