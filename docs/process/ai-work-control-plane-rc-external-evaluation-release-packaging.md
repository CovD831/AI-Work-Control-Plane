# AI Work Control Plane RC External Evaluation & Release Packaging

This track packages the `v1.0.0-rc.1` candidate for external evaluation. It does not add product scope. The goal is to prove that the pushed tag can be cloned outside the working repository, inspected with the documented readiness commands, and explained with release notes that preserve the runtime boundary.

## Scope

- Validate the pushed `v1.0.0-rc.1` tag from a clean external clone.
- Record the RC evidence packet with exact commit, tag, commands, and outcomes.
- Publish release notes that describe the candidate honestly.
- Keep the product claim at runtime measurement readiness, not provider bridge readiness.

## Out Of Scope

- Provider-native bridge implementation.
- Persistent provider session ownership.
- Plugin marketplace packaging.
- New runtime semantics beyond the existing command-runtime measurement surface.

## External Evaluation

Evaluation date: 2026-05-28 Asia/Shanghai.

External clone path:

```text
/private/tmp/agent-orchestrator-rc1-eval
```

Source:

```text
git clone --branch v1.0.0-rc.1 /Users/abab/Desktop/AI-Work-Control-Plane /private/tmp/agent-orchestrator-rc1-eval
```

Resolved candidate commit:

```text
3180c4455b09c5ae0b418732323f411b2eeff835
```

Validation commands:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json
PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
```

Observed results:

- `team setup --runtime command --format json` exited 0.
- `release_readiness.ready` was true.
- `release_readiness.checklist.runtime_measurement` was true.
- `runtime_measurement.measurement_surface_available` was true.
- `runtime_measurement.rc_blocking` was false.
- `team workspace-status --format json` exited 0 and reported a clean workspace state.
- `team evidence-gates --format json` exited 0 and reported `status: ready`.
- `team check-compliance` exited 0 and reported `status: passed`, `blocking: false`.

External-clone nuance:

- A fresh clone has no local job history, so setup reports `runtime_measurement.measurement_status: unavailable` until jobs exist in that clone.
- This is expected. The RC requirement is that the measurement surface exists, readiness explains the gap, and the gap is not RC blocking.
- Prior runtime-measurement convergence on the working repository proved the measured path with existing job evidence.

## Release Packaging Result

The candidate is ready to be presented as:

```text
v1.0.0-rc.1
Runtime Measurement Ready for evaluation
```

The release notes are recorded in:

```text
docs/releases/v1.0.0-rc.1.md
```

The evidence packet is recorded in:

```text
docs/process/v1.0.0-rc.1-evidence-packet.md
```

