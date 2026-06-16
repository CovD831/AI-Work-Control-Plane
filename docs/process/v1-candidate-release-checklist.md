# v1.0 Final Release Checklist

Use this checklist after the v1.x hardening evidence is current and before calling the final build `v1.0.0`. The Python package version and local git tag both use `v1.0.0` / `1.0.0`. The canonical release-readiness process document remains `docs/process/v1x-release-readiness.md`; this file is the detailed operator checklist.

## Version Sync

- Confirm `pyproject.toml` carries `1.0.0` for `v1.0.0`.
- Confirm README and process docs do not claim a distribution shape beyond the local package state.
- Do not imply plugin-marketplace or external distribution support.

## Provider / Runtime Health

- Run `PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json`.
- Confirm `codex`, `claude`, and `mock` provider states are visible.
- Confirm unavailable real providers report honest fallback detail.
- Treat provider health as PATH/cache dependent; use `health --refresh` when validating the current machine.
- Confirm `release_readiness.runtime_measurement` is present.
- Confirm `release_readiness.checklist.runtime_measurement` is true.
- Confirm `runtime_measurement.provider_evidence_summary` is present; Codex pilot evidence may be summarized there, but provider-owned refs do not imply AI-Work-Control-Plane session ownership.
- Treat runtime measurement as local command/runtime evidence, not provider-native bridge readiness.

## Evidence Freeze

- Keep `docs/process/evidence-cases.json` as the committed case source.
- Regenerate `docs/process/v1x-evidence-report.md` and `.agent_orchestrator/evidence/real-tasks.json` from the committed cases.
- Regenerate `docs/process/v1x-evidence-trend.md` from a saved baseline/current comparison.
- Confirm report conclusions cover `planning_quality`, `rescue_quality`, `runtime_limitation`, and `fixed_template_advantage`.
- Confirm trend output includes `current_version_assessment`, `current_is_better`, improvement signals, and limitation signals.
- Confirm trend output also includes the `Comparative Proof Strength` section so direct-proof status and repeatability posture changes remain operator-visible.

## Workflow Regression Evidence

- Inspect `docs/process/v1x-hardening-workflow-report.md`.
- Confirm at least one start/next/execute/inspect-execution path is recorded.
- Confirm at least one friction/fix path is recorded.
- Confirm runtime/provider limitations remain explicit.
- Confirm evidence report and trend include runtime measurement metrics and measured-vs-placeholder language.

## Targeted Tests

- Docs/process: `pytest tests/test_docs_process.py tests/test_planning_support.py tests/test_team.py -q`
- Runtime/provider: `pytest tests/test_command.py tests/test_jobs.py tests/test_tmux_runtime.py -q`
- Evidence/CLI: `pytest tests/test_evidence.py tests/test_cli.py -q`
- CLI UX: `pytest tests/test_cli.py tests/test_cli_presenters.py -q`

## Final Gate

- Run full `pytest`.
- Run `PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json`.
- Run `PYTHONPATH=src python -m agent_orchestrator.cli team governance-bundle export --output .agent_orchestrator/governance/v1.0.0-final-bundle.json --query "v1.0.0 final release seal" --format json`.
- Run `PYTHONPATH=src python -m agent_orchestrator.cli team governance-bundle inspect .agent_orchestrator/governance/v1.0.0-final-bundle.json --format json`.
- Confirm governance bundle inspection reports `complete: true`, `auditable: true`, and `blocking: false`.
- Run `PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance`.
- Confirm `git status --short` is clean after the final commit.

## Known Runtime Limitations

- v1.x command runtime captures stdout, stderr, exit code, and local job lifecycle state.
- `send` and `cancel` are local session/job controls, not a guarantee of provider-native interactive session support.
- v1.x remains a guarded local runtime, not a full Codex/Claude bridge or persistent session manager.
- Runtime measurement records local timestamps, duration, exit code, provider availability, degraded reasons, and operation receipts when available; token/cost values remain placeholder unless reported by a provider runtime.
- Codex Runtime Pilot evidence is consumed through provider evidence summaries and remains opt-in, fake-runner-testable, and provider-owned at the session boundary.
- Governance bundle export/inspect is the v1 externalization proof; it is a portable review artifact, not a provider session control surface.
