# Native Coding Agent Phase 5 Native-Only Dogfood Track

## Scope

This phase proves at least one bounded real task chain can close through the native coding runtime path.

It does not claim native mode is already the default for every task class.

It exists to prevent the upgrade from stopping at kernel structure without whole-system proof.

## Goal

- prove one native-only repository task chain end to end,
- make the proof consumable through control-plane and UI surfaces,
- pin approval pause and resume behavior as part of the proof,
- ensure the proof is artifact-backed rather than summary-only.

The current default proof bundle is intentionally stronger than a single happy-path chain.

It must preserve three pinned native proof chains in default evidence output:

- `approval_pause_resume_complete`
- `verify_failure_exhausted_recovery_block`
- `verify_failure_repair_resume_success`

## Required Task Shape

The first native dogfood task chain must include all of the following:

1. a bounded internal repository task under the current workspace,
2. repository exploration and explicit context selection,
3. at least one approval pause,
4. at least one `approval_resume` continuation,
5. verification output with externalized artifact evidence,
6. runtime event summary visibility,
7. workspace index visibility,
8. UI execution summary visibility,
9. explicit native-only proof that no external coding agent executed the core implementation loop.

## Implementation Steps

1. Reuse the governed native coding runtime path rather than injecting synthetic external-agent success.
2. Promote the existing runtime proof surface into a stable acceptance-oriented object.
3. Pin one end-to-end test chain that drives:
   - pause on approval,
   - resume after approval,
   - verification completion,
   - artifact recording,
   - runtime event stream projection,
   - workspace index projection,
   - UI operator summary projection.
4. Pin one blocked recovery chain that drives:
   - persisted verify failure state,
   - governed `approval_resume`,
   - exhausted recovery classification,
   - control-plane-visible block state,
   - runtime event stream, workspace index, and UI summary projection.
5. Pin one repair-success chain that drives:
   - persisted verify failure state,
   - remaining retry budget,
   - governed `approval_resume`,
   - repaired re-verification success,
   - artifact, runtime event stream, workspace index, and UI summary projection.
6. Keep the control plane as the only trusted state and artifact source during the proof.
7. Record remaining friction as native-kernel gaps rather than bypassing the chain.

## Acceptance Criteria

Phase 5 is complete only when all of the following are true:

1. at least one bounded real task chain completes through native runtime mode,
2. the chain includes approval pause and governed resume,
3. the chain emits artifact and runtime-event evidence,
4. the workspace index exposes the resulting native-task proof,
5. the UI operator summary exposes the same native-task proof,
6. default evidence/report output preserves success, blocked-recovery, and repair-success proof chains together,
7. the proof explicitly states that external coding agents were not required for the core execution loop.

## Targeted Tests

```bash
pytest tests/test_docs_process.py tests/test_coding_agent_runtime.py tests/test_control_plane.py tests/test_ui_service.py -q
```

## Output Of This Phase

After this phase, later work should be judged against one question:

Can the repository show a real governed native-only task chain, with pause/resume, artifact evidence, recovery continuity, workspace visibility, and UI visibility, without relying on an external coding agent as the main executor?

Default proof is stronger when the answer is demonstrated through the pinned three-chain bundle rather than only one successful run.
