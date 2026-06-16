# v1.0 Candidate Freeze Plan

## Summary

This document records the continuous v1.0 candidate freeze run. Each phase starts by adding its phase plan here, runs only targeted tests during the phase, and automatically proceeds when the targeted tests pass. Full `pytest`, final `team setup`, final compliance, and commit happen only at the final gate.

## Execution Rules

- Continue automatically between phases when targeted tests pass.
- Pause only for network access, privilege escalation, destructive actions, product-direction changes, or a test failure whose fix would expand the release-candidate scope.
- Keep v1.x CLI-first and local-first.
- Do not expand v1.x into a provider bridge, persistent session manager, or plugin marketplace.
- Keep `docs/process/v1x-release-readiness.md` as the canonical short process document; put detailed candidate checklist material in a separate non-canonical document.

## Final Acceptance

- Phase-targeted tests pass at the end of each phase.
- Evidence report and trend are regenerated from committed cases.
- `team setup --runtime command --format json` reports honest readiness and release readiness.
- Runtime measurement readiness is visible in `team setup --runtime command --format json`.
- Full `pytest` passes.
- `team check-compliance` passes.
- `git status --short` is clean after the final commit.

## Phase 1 Plan: Candidate Audit and Stage Plan Mechanism

- Establish this freeze plan as the running phase log.
- Confirm the baseline is `f0a3ada Complete v1.x hardening candidate prep` with a clean worktree.
- Preserve existing public CLI behavior.
- Run docs/process targeted tests only.

Phase 1 targeted test:

```bash
pytest tests/test_docs_process.py tests/test_planning_support.py -q
```

Phase 1 result:

- Targeted test passed: `24 passed`.

## Phase 2 Plan: Release Readiness Checklist Placement

- Keep `docs/process/v1x-release-readiness.md` as the canonical short process document.
- Add `docs/process/v1-candidate-release-checklist.md` for detailed pre-release checks.
- Link README, operator runbook, and roadmap to the detailed candidate checklist.
- Preserve local-only release claims and avoid bridge/session-manager/plugin-marketplace promises.

Phase 2 targeted test:

```bash
pytest tests/test_docs_process.py tests/test_planning_support.py tests/test_team.py -q
```

Phase 2 result:

- Targeted test passed: `125 passed`.

## Phase 3 Plan: Provider Smoke and Runtime Limits

- Run provider health with `--refresh` to capture current local `codex`, `claude`, and `mock` states.
- Run `team setup --runtime command --format json` to confirm readiness remains honest.
- Keep runtime limitation language explicit: local command runtime and job controls, not a provider-native session bridge.
- Run runtime/provider targeted tests only.

Phase 3 targeted test:

```bash
pytest tests/test_command.py tests/test_jobs.py tests/test_tmux_runtime.py -q
```

Phase 3 result:

- `health --refresh --format json` reported `codex` available as `codex-cli 0.133.0-alpha.1`, `claude` available as `2.1.150 (Claude Code)`, and `mock` available.
- `team setup --runtime command --format json` reported readiness and release_readiness as true.
- Targeted test passed: `32 passed`.

## Phase 4 Plan: Evidence Freeze

- Regenerate evidence report and machine-readable evidence from `docs/process/evidence-cases.json`.
- Regenerate the evidence trend from a current benchmark baseline and the real-task evidence payload.
- Confirm the report keeps planning, rescue, runtime limitation, and fixed-template advantage conclusions.
- Confirm the trend keeps `current_version_assessment`, `current_is_better`, improvement signals, and limitation signals.
- Confirm the trend also keeps the `Comparative Proof Strength` section for direct-proof and repeatability posture.
- Run evidence/CLI targeted tests only.

Phase 4 targeted test:

```bash
pytest tests/test_evidence.py tests/test_cli.py -q
```

Phase 4 result:

- Regenerated `docs/process/v1x-evidence-report.md`.
- Regenerated `.agent_orchestrator/evidence/real-tasks.json`.
- Regenerated `docs/process/v1x-evidence-trend.md`.
- Confirmed report includes planning, rescue, runtime limitation, and fixed-template advantage conclusions.
- Confirmed trend includes current-version assessment, current-is-better verdict, improvement signals, and limitation signals.
- Confirmed trend also includes the `Comparative Proof Strength` section.
- Targeted test passed: `81 passed`.

## Phase 5 Plan: CLI Quickstart Dry Run

- Run the README quickstart commands from an operator perspective.
- Validate that setup/readiness output, evidence command paths, and next-step guidance are understandable.
- Make only release-blocking CLI or docs corrections if the dry run exposes friction.
- Run CLI UX and docs/process targeted tests.

Phase 5 targeted tests:

```bash
pytest tests/test_cli.py tests/test_cli_presenters.py -q
pytest tests/test_docs_process.py tests/test_planning_support.py -q
```

Phase 5 dry-run notes:

- `health` and `team setup` ran successfully and showed readable readiness summaries.
- README direct smoke command initially missed the required `run` subcommand; corrected the quickstart command.
- Corrected direct smoke command completed successfully with `mode=cost_first`.
- Governed workflow quickstart ran through `team start`, `summary`, `next`, `runbook`, `execute`, and `inspect-execution` with clear next-step guidance.

Phase 5 result:

- CLI UX targeted test passed: `84 passed`.
- Docs/process targeted test passed: `24 passed`.

## Phase 6 Plan: Final Candidate Gate

- Run full `pytest`.
- Run `team setup --runtime command --format json` and confirm readiness/release_readiness stay true.
- Run `team check-compliance`.
- Check `git status --short`.
- If all gates pass, commit with `Prepare v1.0 candidate freeze`.

Phase 6 result:

- Full test suite passed: `338 passed`.
- `team setup --runtime command --format json` reported readiness and release_readiness as true.
- `team check-compliance` passed with no blocking reasons.
- Final candidate freeze changes were ready for commit.

## RC1 Phase 1 Plan: Version Baseline and Tag Availability

- Baseline commit is `331c783 Prepare v1.0 candidate freeze`.
- Target package version is `1.0.0rc1`.
- Target local annotated tag is `v1.0.0-rc.1`.
- Confirmed the worktree was clean before starting RC1.
- Confirmed `v1.0.0-rc.1` did not already exist before starting RC1.
- Keep public CLI behavior unchanged in this phase.
- Continue automatically after targeted tests pass.

RC1 Phase 1 targeted test:

```bash
pytest tests/test_docs_process.py tests/test_planning_support.py -q
```

RC1 Phase 1 result:

- Targeted test passed: `24 passed`.

## RC1 Phase 2 Plan: Package Version Sync

- Update `pyproject.toml` package version from `0.1.0` to `1.0.0rc1`.
- Update tests that assert the release_readiness package version.
- Update candidate checklist wording so `1.0.0rc1` package version and `v1.0.0-rc.1` tag label are both explicit.
- Keep `docs/process/v1x-release-readiness.md` as the canonical short process document.

RC1 Phase 2 targeted test:

```bash
pytest tests/test_cli.py tests/test_docs_process.py tests/test_planning_support.py -q
```

RC1 Phase 2 result:

- Package version updated to `1.0.0rc1`.
- Candidate checklist now distinguishes package version `1.0.0rc1` from tag label `v1.0.0-rc.1`.
- Targeted test passed: `97 passed`.

## RC1 Phase 3 Plan: README and Runbook Command Audit

- Audit README and operator runbook for direct task examples that omit the `run` subcommand.
- Correct release-blocking command drift only.
- Keep the CLI command surface unchanged.
- Run CLI docs/UX targeted tests.

RC1 Phase 3 targeted test:

```bash
pytest tests/test_cli.py tests/test_cli_presenters.py tests/test_docs_process.py -q
```

RC1 Phase 3 result:

- Corrected README direct task examples to use the `run` subcommand.
- Confirmed no README/operator-runbook direct task examples still omit `run`.
- Targeted test passed: `94 passed`.

## RC1 Phase 4 Plan: Evidence and Provider Smoke

- Run live provider health with `--refresh`.
- Run `team setup --runtime command --format json`.
- Regenerate evidence report, real-task JSON payload, and evidence trend.
- Confirm evidence report and trend keep RC-critical conclusion fields.
- Keep runtime limitations explicit and unchanged.
- Run runtime/provider and evidence/CLI targeted tests.

RC1 Phase 4 targeted tests:

```bash
pytest tests/test_command.py tests/test_jobs.py tests/test_tmux_runtime.py -q
pytest tests/test_evidence.py tests/test_cli.py -q
```

RC1 Phase 4 result:

- Provider health reported `codex`, `claude`, and `mock` available.
- `team setup --runtime command --format json` reported package version `1.0.0rc1` and release_readiness true.
- Evidence report and trend were regenerated from current committed cases and benchmark comparison.
- Confirmed RC-critical evidence conclusion fields remain present.

## Runtime Measurement RC Track

After the Real-Task Dogfood Evidence Track, the runtime-measurement readiness line adds a local measurement gate before RC tagging:

- `team runtime inspect <job_id> --format json` must expose `runtime_measurement`.
- `team setup --runtime command --format json` must expose `runtime_measurement` and `release_readiness.checklist.runtime_measurement`.
- Evidence report and trend must include runtime measurement metrics.
- Provider token/cost remains placeholder unless reported by a runtime; this does not block RC by itself.
- This is measurement readiness, not provider bridge readiness.
- Runtime/provider targeted test passed: `32 passed`.
- Evidence/CLI targeted test passed: `81 passed`.

## RC1 Phase 5 Plan: Final Gate, Commit, and Local Tag

- Run full `pytest`.
- Run `team setup --runtime command --format json`.
- Run `team check-compliance`.
- Confirm worktree status before commit.
- Commit with `Prepare v1.0.0-rc.1`.
- Create local annotated tag `v1.0.0-rc.1`.
- Confirm final worktree is clean and the tag exists.

RC1 Phase 5 final gate:

```bash
pytest
PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
git status --short
```

RC1 Phase 5 result:

- Full test suite passed: `338 passed`.
- `team setup --runtime command --format json` reported package version `1.0.0rc1`, readiness true, and release_readiness true.
- `team check-compliance` passed with no blocking reasons.
- Ready to commit `Prepare v1.0.0-rc.1` and create local annotated tag `v1.0.0-rc.1`.

## RC2 Phase 1 Plan: Codex Pilot Seal

- Preserve the existing `v1.0.0-rc.1` tag as historical release-candidate evidence.
- Seal the post-rc.1 Codex Runtime Pilot and v1 candidate hardening follow-up as `v1.0.0-rc.2`.
- Update the package version to `1.0.0rc2`.
- Add `docs/releases/v1.0.0-rc.2.md` and `docs/process/v1.0.0-rc.2-evidence-packet.md`.
- Keep the scope fixed: runtime measurement and Codex pilot evidence consumption, not provider bridge readiness.
- Run the targeted docs/CLI version checks before final gates.

RC2 Phase 1 targeted test:

```bash
pytest tests/test_cli.py tests/test_docs_process.py -q
```

RC2 Phase 1 result:

- Targeted test passed: `107 passed`.

## RC2 Phase 2 Plan: Final Gate, Commit, and Local Tag

- Run full `pytest`.
- Run `team setup --runtime command --format json`.
- Run `team workspace-status --format json`.
- Run `team evidence-gates --format json`.
- Run `team check-compliance`.
- Confirm `git status --short`.
- Commit with `Prepare v1.0.0-rc.2`.
- Create local annotated tag `v1.0.0-rc.2`.

RC2 Phase 2 final gate:

```bash
pytest
PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json
PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
git status --short
```

RC2 Phase 2 result:

- Full test suite passed: `421 passed`.
- `team setup --runtime command --format json` reported package version `1.0.0rc2`, readiness true, release_readiness true, runtime measurement `measured`, provider evidence summary format `agent_orchestrator.provider_evidence_summary.v1`, and `rc_blocking: false`.
- `team workspace-status --format json` exited 0 and returned `agent_orchestrator.workspace_index.v1` with provider evidence summary format `agent_orchestrator.provider_evidence_summary.v1`.
- `team evidence-gates --format json` exited 0 and returned status `ready` with provider evidence summary format `agent_orchestrator.provider_evidence_summary.v1`.
- `team check-compliance` passed with no blocking reasons.
- Ready to commit `Prepare v1.0.0-rc.2` and create local annotated tag `v1.0.0-rc.2`.

## RC2 External Evaluation Result

- External clone path: `/private/tmp/agent-orchestrator-rc2-eval-20260528`.
- `v1.0.0-rc.2` resolved to commit `45051c98760823749fa5574ed72a6d168fbe2d06`.
- Setup, workspace status, evidence gates, and compliance all exited 0.
- Fresh clone runtime measurement was honestly `unavailable` because no job history existed, while the measurement surface and provider evidence summary remained present and non-blocking.
- Fake Codex pilot evidence was consumed by workspace status and evidence gates through `agent_orchestrator.provider_evidence_summary.v1`.
- Dogfood exposed a documentation blocker: README skipped `team draft-ready` and `team submit-review` before `team approve`.
- Decision: preserve rc.2 as evaluated, do not promote it, and prepare rc.3 as a documentation-blocker fix only.

## RC3 Phase 1 Plan: Quickstart Blocker Fix

- Update README governed workflow quickstart to include `team draft-ready` and `team submit-review`.
- Update package version to `1.0.0rc3`.
- Add `docs/releases/v1.0.0-rc.3.md` and `docs/process/v1.0.0-rc.3-evidence-packet.md`.
- Record the rc.2 external evaluation in `docs/process/ai-work-control-plane-rc2-external-evaluation-dogfood.md`.
- Keep runtime and provider boundaries unchanged.

RC3 Phase 1 targeted test:

```bash
pytest tests/test_cli.py tests/test_docs_process.py -q
```

RC3 Phase 1 result:

- Targeted test passed: `107 passed`.

## RC3 Phase 2 Plan: Final Gate, Commit, and Local Tag

- Run full `pytest`.
- Run `team setup --runtime command --format json`.
- Run `team workspace-status --format json`.
- Run `team evidence-gates --format json`.
- Run `team check-compliance`.
- Confirm `git status --short`.
- Commit with `Prepare v1.0.0-rc.3`.
- Create local annotated tag `v1.0.0-rc.3`.

RC3 Phase 2 final gate:

```bash
pytest
PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json
PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
git status --short
```

RC3 Phase 2 result:

- Full test suite passed: `421 passed`.
- `team setup --runtime command --format json` reported package version `1.0.0rc3`, readiness true, release_readiness true, runtime measurement `measured`, provider evidence summary format `agent_orchestrator.provider_evidence_summary.v1`, and `rc_blocking: false`.
- `team workspace-status --format json` exited 0 and returned `agent_orchestrator.workspace_index.v1` with provider evidence summary format `agent_orchestrator.provider_evidence_summary.v1`.
- `team evidence-gates --format json` exited 0 and returned status `ready` with provider evidence summary format `agent_orchestrator.provider_evidence_summary.v1`.
- `team check-compliance` passed with no blocking reasons.
- Ready to commit `Prepare v1.0.0-rc.3` and create local annotated tag `v1.0.0-rc.3`.
