# Native Coding Agent Phase 0 Baseline

## Scope

This phase defines the closure baseline for the native coding agent upgrade.

It does not attempt to improve the runtime yet.

It exists to prevent the repository from drifting into local optimizations without a clear whole-system completion bar.

## Goal

- define what counts as native-only closure,
- define which real task class will be used as the first acceptance target,
- define what still counts as external-agent dependence,
- establish the evidence expected before Phase 1 implementation begins.

## Implementation Steps

1. Record the canonical native-only closure definition:
   the repository must complete at least one real development-task class through the governed native runtime path without requiring OpenCode, Codex, or another external coding agent as the default executor.

2. Record the first acceptance task class:
   a bounded internal repository development task inside this workspace that requires repository exploration, one or more code edits under `src/agent_orchestrator/` or `ui_frontend/`, at least one verification command, and operator-visible artifacts.

3. Record required closure stages for that task class:
   intake, context assembly, execution, verification, repair-or-pause decision, resume if interrupted, evidence projection, memory projection, and recovery visibility.

4. Record the first concrete acceptance-task shape:
   a real repository maintenance or hardening change that updates code plus its surrounding canonical docs or compliance-visible surfaces, so the native runtime must coordinate code, verification, and repository-facing artifacts rather than only apply an isolated patch.

5. Record disallowed completion shortcuts:
   external coding-agent handoff as the real executor, manual JSON patching of state to advance the flow, helper-only improvements without end-to-end task proof, or documentation-only convergence without runtime capability change.

6. Record baseline proof requirements:
   explicit artifact path or artifact class, runtime event summary visibility, recovery state visibility, evidence or memory projection visibility, and evidence that the native runtime performed the core execution work.

7. Record the minimum proof bundle for the first acceptance task:
   changed code, verification result, artifact or event summary, recovery-visible state even when no interruption occurs, and a clear statement that no external coding agent executed the core implementation loop.

8. Record the default native proof-chain bundle that later phases must preserve in default evidence/report output:
   `approval_pause_resume_complete`, `verify_failure_exhausted_recovery_block`, and `verify_failure_repair_resume_success`.

9. Record the role of the three proof chains:
   success-chain proof for governed approval pause/resume completion, blocked-chain proof for exhausted verify recovery with human handoff, and repair-success proof for verify failure closed by remaining retry budget plus governed resume.

## Acceptance Criteria

Phase 0 is complete only when all of the following are true:

1. the native-only closure target is explicitly documented,
2. the first real task class for acceptance is explicitly documented,
3. the first concrete acceptance-task shape is explicitly documented,
4. external-agent dependence is explicitly defined so success cannot be overclaimed,
5. prohibited shortcuts are explicitly documented,
6. the baseline proof bundle is explicitly documented,
7. the default three-chain native proof bundle is explicitly documented,
8. the phase provides a stable baseline for later phase implementation and review.

## Targeted Tests

```bash
pytest tests/test_docs_process.py -q
```

## Output Of This Phase

After this phase, later phases should be judged against one question:

Can the repository, as a whole system, complete the designated real task class through the native governed runtime without requiring an external coding agent as the main executor?

The default answer must remain backed by three explicit native proof chains in reportable evidence:

- `approval_pause_resume_complete`
- `verify_failure_exhausted_recovery_block`
- `verify_failure_repair_resume_success`
