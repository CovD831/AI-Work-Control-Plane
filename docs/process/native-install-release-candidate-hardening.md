# Native Install Release-Candidate Hardening

This local RC gate is a product-readiness check, not a public release. It aggregates product posture, provider/runtime readiness, authoritative OpenCode evidence closure, documentation presence, declared focused tests, and smoke commands into `pass`, `degraded`, or `fail`.

## Operator path

Generate an operator-readable report and JSON artifact:

```bash
agent-orchestrator product rc-report --format pretty --output .agent_orchestrator/release-candidate/report.json
agent-orchestrator product rc-report --format json
agent-orchestrator product diagnose --format pretty
agent-orchestrator product smoke --format json
```

A `pass` verdict means local mock/runtime posture, evidence closure, docs, and command surfaces are present. `degraded` means a local RC path exists but one or more external runtimes or authoritative comparison details remain partial. `fail` means the operator should stop before treating the build as a release candidate.

## Validation branches

- CLI: `product diagnose`, `product smoke`, `product evidence`, and `product rc-report` must be readable without raw JSON.
- Service/UI: dashboard health, session detail, and evidence bundle expose the RC verdict and blockers.
- Artifact: the report includes available runtimes, degraded fallback paths, smoke commands, focused test commands, known limitations, and rollback/cleanup notes.

## Known limitations and non-goals

This does not publish to a package registry, build marketplace/provider/plugin ecosystem integration, or perform public release automation. It must not modify AiMaMi or local proxy configuration. Provider CLI/API auth can remain degraded while mock fallback provides a local RC path.

## Rollback and cleanup

Delete generated `.agent_orchestrator/release-candidate/` report artifacts if validation is abandoned. Rerun `agent-orchestrator product diagnose --refresh` after changing provider CLI/auth setup. Use the mock smoke path while external runtimes are repaired.

## Executable validation pipeline

`product rc-report` is the static gate. `product rc-validate` turns the declared smoke/test path into a validation run record. In `--dry-run` mode every command is preserved with `status=not_run`, `exit_status=not_applicable`, timestamps, and `reason=dry_run_validation_not_executed`; this is the safe default for handoff and CI planning. Without `--dry-run`, the command is executed from the repo root and the artifact records command, exit status, started/ended timestamps, duration, and bounded stdout/stderr summaries.

```bash
agent-orchestrator product rc-validate --dry-run --output .agent_orchestrator/release-candidate/validation.json
agent-orchestrator product rc-validate --skip-tests --timeout 60 --output .agent_orchestrator/release-candidate/smoke-validation.json
```

Stop conditions: any failed or unavailable command makes validation `fail`; dry-run/non-execution makes validation `degraded`; successful executed commands with no gate warnings can pass.

## Operator release bundle

`product rc-bundle` combines the static report, validation run, docs status, smoke/test commands, known limitations, rollback/cleanup, blockers, and warnings into the operator handoff artifact surfaced by Dashboard/UI and evidence bundle.

```bash
agent-orchestrator product rc-bundle \
  --validation .agent_orchestrator/release-candidate/validation.json \
  --output .agent_orchestrator/release-candidate/bundle.json
```

Bundle verdict semantics: `fail` means stop before local RC handoff; `degraded` means the handoff is useful but includes dry-run validation, runtime degradation, or partial evidence; `pass` means the declared local RC path has executed cleanly and no blockers/warnings remain.

## Native RC Dogfood Adoption Loop

The local RC bundle is now consumable by `agent-orchestrator product rc-adopt` and `agent-orchestrator product rc-adoption-report`.
The adoption ledger format is `agent_orchestrator.native_rc_adoption_ledger.v1`; each run records the fixed `repo_change_lane`, `validation_lane`, and `recovery_lane` with RC bundle refs, validation refs, runtime command/action payloads, workspace impact, standardized pause/recovery reason, operator decision, and next action. Dry runs are explicitly marked `not_run` and unavailable artifacts are reported as `missing`/`unavailable` rather than pass.
