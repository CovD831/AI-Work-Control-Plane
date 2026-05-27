# AI Work Control Plane Real-Task Dogfood Plan

## Purpose

This is the next long-cycle plan after the frozen AI Work Control Plane baseline.

The goal is to prove the control plane against broader real local work instead of reframing the product again. The control plane already owns durable state, context, strategy, topology, approval, run ledger, recovery telemetry, runtime fidelity summaries, evidence bundles, and memory candidates. This track turns that architecture into measured dogfood evidence.

## Product Boundary

In scope:

- Expand real-task evidence cases beyond the current small v1.x sample.
- Add reportable recovery, compliance, runtime fidelity, postmortem, and cost/latency signals.
- Keep evidence local, deterministic, and usable without external network or provider auth.
- Refresh evidence report and trend artifacts from the committed case source.
- Use only targeted tests during implementation phases.
- Run full `pytest` and `team check-compliance` only at final convergence.

Out of scope:

- Another product reframe.
- A full Codex/Claude provider bridge.
- Persistent provider session ownership.
- React Flow editing.
- Plugin marketplace packaging.
- Automatic external memory writes.

## Target Shape

After this track, the repository should show a measured local operator workflow:

```text
RealTaskCase
  -> PlanSession
  -> Workspace / Program Index
  -> Recovery Recommendation
  -> Runtime Fidelity Summary
  -> EvidenceBundle
  -> Postmortem Signals
  -> Evidence Trend
```

The useful end state is not just "tests pass." It is that a maintainer can inspect the evidence report and understand:

- which real-task categories were exercised,
- whether each task produced an approved plan and linked execution,
- whether the recovery recommendation was actionable,
- whether compliance and docs sync were represented,
- whether runtime/provider limitations stayed explicit,
- whether postmortem and cost/latency placeholders are ready for real measurements.

## Phases

### Phase 0: Baseline And Plan Seal

Write this master plan and a phase plan for baseline sealing. Confirm the next work is evidence expansion, not reframe or provider-bridge expansion.

Targeted tests:

- `pytest tests/test_docs_process.py tests/test_evidence.py -q`

### Phase 1: Evidence Schema And Report Metrics

Extend the workflow evidence payload with real-task metadata, postmortem signals, recovery coverage, runtime fidelity coverage, compliance blocking coverage, and cost/latency readiness. Keep the existing schema version and command compatibility.

Targeted tests:

- `pytest tests/test_evidence.py tests/test_cli.py -q`

### Phase 2: Real-Task Case Matrix

Expand `docs/process/evidence-cases.json` to cover standard implementation, follow-up recovery, high-risk migration, parallel validation, UI workflow, compliance blocking, runtime fidelity, and interruption recovery.

Targeted tests:

- `pytest tests/test_evidence.py -q`

### Phase 3: Evidence Artifact Refresh

Regenerate local machine-readable evidence, markdown evidence report, and trend report from the committed real-task cases.

Targeted tests:

- `pytest tests/test_evidence.py tests/test_cli.py -q`

### Phase 4: Canonical Documentation Sync

Update roadmap/backlog/process docs so the next-stage baseline is visible in operator-facing documentation.

Targeted tests:

- `pytest tests/test_docs_process.py tests/test_planning_support.py -q`

### Phase 5: Final Convergence

Run final gates and record completion state.

Final gates:

```bash
pytest
env PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
env PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
env PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
git status --short
```

## Acceptance

This track is complete when:

- The real-task matrix has at least eight local cases.
- Evidence report shows recovery, runtime fidelity, compliance, postmortem, and cost/latency sections.
- Trend report compares the expanded evidence capture against a baseline capture.
- Control-plane docs say the next completed layer is real-task dogfood evidence, not another architecture migration.
- Full tests and compliance pass at final convergence.
