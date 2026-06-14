# Native Coding Agent Closure Audit

## Purpose

This document audits the current repository state against the native coding-agent upgrade objective.

It is intentionally stricter than a progress recap.

It exists to answer one question:

Can the repository already prove the requested native closure end state, or only a narrower but meaningful subset of it?

## Audit Scope

This audit checks the current state against the six acceptance standards in:

- `docs/architecture/native-coding-agent-upgrade-plan.md`

It treats the following as authoritative evidence:

- current runtime code and tests,
- current `docs/process/` phase plans,
- current control-plane artifact projections,
- current UI execution summary projections,
- current default evidence report outputs.

## Current Evidence Sources

Primary proof artifacts used in this audit:

- `docs/process/native-coding-agent-dogfood-evidence.md`
- `/tmp/native-evidence-report-v28.json`
- `/tmp/native-evidence-report-v28.md`
- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `src/agent_orchestrator/control_plane_artifacts.py`
- `src/agent_orchestrator/control_plane_workspace.py`
- `src/agent_orchestrator/ui_service.py`

Primary verification slices used in this audit:

```bash
pytest tests/test_evidence.py tests/test_control_plane.py tests/test_ui_service.py -q
pytest tests/test_coding_agent_runtime.py tests/test_control_plane.py tests/test_ui_service.py -q
pytest tests/test_docs_process.py -q
```

## Requirement Audit

### 1. Default main path does not require external coding agents for at least one task class

Status: `strongly evidenced`

Why:

- the default evidence bundle includes `repo_task_acceptance`,
- `repo_task_acceptance` currently shows `real_repo_task_acceptance_ready=true`,
- the same case carries `native_runtime_only=true` and `external_coding_agent_required=false`,
- the current default report contains three native proof chains without relying on OpenCode or Codex as the executor,
- stronger repo-task acceptance is now part of the default dogfood judgment chain through runtime event, workspace index, and UI projection visibility.

Primary evidence:

- `/tmp/native-evidence-report-v28.json`
- `docs/process/native-coding-agent-dogfood-evidence.md`

Residual risk:

- the proven task class is still one bounded internal repository task class, not broad daily-driver coverage.
- the stronger proof is now better for multi-file native repository chains, but it is still not broad daily-driver coverage across open-ended task families.

### 2. Runtime has a stable explicit step-loop core

Status: `strongly evidenced`

Why:

- the runtime exposes `step_loop_contract`,
- current tests cover completed, paused, blocked, and resumed loop states,
- loop semantics are no longer only implied by scattered traces.

Primary evidence:

- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `tests/test_coding_agent_runtime.py`
- `docs/process/native-coding-agent-phase-2-step-loop-convergence.md`

Residual risk:

- the loop is explicit and inspectable, but still bounded around the current repository-task shape rather than proven as a broader long-horizon engine.

### 3. Every model-participating step passes explicit Context Select and Structured Observation, with Compact/Isolate when needed

Status: `strongly evidenced for the current bounded task class`

Why:

- the runtime now exposes `context_engineering_contract`,
- `step_loop_contract` and `next_step_contract` both project `context_engineering_refs`,
- UI and evidence surfaces now show the same step-level context-engineering requirements,
- default evidence now checks `context_engineering_main_path_visible`.

Primary evidence:

- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `src/agent_orchestrator/ui_service.py`
- `src/agent_orchestrator/evidence.py`
- `/tmp/native-evidence-report-v28.md`

Residual risk:

- this is strongly proven for the current bounded native task loop, not yet for richer multi-subtask or longer-horizon coding behavior.

### 4. Verify/Repair/Resume closes in real failure scenarios

Status: `strongly evidenced`

Why:

- default evidence now preserves three pinned native proof chains:
  - `approval_pause_resume_complete`
  - `verify_failure_exhausted_recovery_block`
  - `verify_failure_repair_resume_success`
- these chains cover success, blocked recovery, and repair-success recovery,
- each chain is visible through runtime, UI, and evidence projections.

Primary evidence:

- `docs/process/native-coding-agent-dogfood-evidence.md`
- `/tmp/native-evidence-report-v28.json`
- `tests/test_ui_service.py`
- `tests/test_evidence.py`

Residual risk:

- repair breadth is still limited to the currently modeled failure classes.

### 5. Control plane remains the only trusted source for state, approval, evidence, recovery, and memory

Status: `medium to strong`

Why:

- approval, workspace index, recovery timeline, runtime event stream, and evidence surfaces remain externalized,
- `execution_artifact_summary` now preserves `context_engineering_contract` and `step_loop_context_surfaces`,
- workspace index now exposes the same context-engineering proof that runtime/UI/evidence surfaces show.

Primary evidence:

- `src/agent_orchestrator/control_plane_artifacts.py`
- `src/agent_orchestrator/control_plane_workspace.py`
- `tests/test_control_plane.py`
- local workspace index state under `.agent_orchestrator/workspace/index.json`

Residual risk:

- the runtime still produces rich payloads before projection, so the architecture claim is strongest when judging durable truth and operator/audit truth, not transient in-process values.

### 6. At least one real task chain has auditable artifacts, event summaries, recovery state, and evidence proof

Status: `strongly evidenced`

Why:

- `repo_task_acceptance` currently satisfies the stronger repository-task acceptance snapshot,
- the repo-task family now also projects a stricter multi-file complex acceptance snapshot,
- the same family of proofs is visible through event summaries, workspace index, UI execution summary, and default evidence report,
- the default dogfood-surface checks now explicitly require stronger repo-task acceptance visibility across runtime event stream, workspace index, and UI execution summary,
- repair and blocked variants also preserve recovery-visible state and event-backed proof.

Primary evidence:

- `/tmp/native-evidence-report-v28.json`
- `/tmp/native-evidence-report-v28.md`
- `tests/test_control_plane.py`
- `tests/test_ui_service.py`

Residual risk:

- only one bounded real task class is strongly proven today.
- that proof is now stronger for multi-file native repository work, but it still does not yet prove broad long-horizon daily-driver coverage.

## Overall Conclusion

Current conclusion: `not yet complete for the full upgrade objective`

Why not complete yet:

1. the repository now strongly proves a bounded native closure task class, but it does not yet strongly prove native mode as the default long-horizon coding engine for a broader class of real development work,
2. the current proof set is strongest at Phase 0 through Phase 5 bounded closure, not full repository-level defaultability,
3. comparison against mature coding agents such as OpenCode is still favorable on governance and auditability, but not yet fully favorable on native execution breadth or default daily-driver strength.

## What Is Already Strong

- governed native-only closure exists for one bounded internal repository task class,
- step-loop semantics are explicit,
- context-engineering behavior is explicit in runtime, loop, UI, evidence, and control-plane artifact summaries,
- verify/repair/resume proof is no longer limited to one happy path,
- stronger repo-task acceptance is no longer merely downstream metadata; it now participates in default evidence and operator judgment surfaces,
- stricter complex repo-task acceptance now also participates in benchmark, workspace, UI, CLI, and evidence surfaces for the multi-file native repo-task family,
- control-plane artifacts now carry the native context-engineering proof instead of only downstream summaries doing so.

## What Still Needs Stronger Proof

1. broader native task-class coverage beyond the current bounded repository acceptance case,
2. stronger proof that the same governed kernel is defaultable for longer-horizon coding work without external coding-agent strength,
3. stronger proof that isolate behavior scales beyond digest-style narrowing into more practical complex-task digestion,
4. stronger completion evidence that the current native runtime is the repository's default executor for meaningful ongoing project work, not only a proven bounded closure path.

## Decision Use

If the question is:

Can this repository already demonstrate a real governed native coding-agent closure without OpenCode or Codex?

The answer is:

`yes, for at least one bounded internal repository task class, with strong evidence`

If the question is:

Has the full upgrade objective already been proven complete?

The answer is:

`no, not yet`
