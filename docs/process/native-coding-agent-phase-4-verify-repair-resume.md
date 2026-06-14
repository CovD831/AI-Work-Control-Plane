# Native Coding Agent Phase 4 Verify-Repair-Resume Closure

## Scope

This phase proves the native coding runtime can survive a real verification failure and still project a governed recovery path.

It does not require full autonomous repair breadth across every failure class.

It exists to ensure verify, repair, pause, block, and resume are part of one auditable loop rather than separate local behaviors.

## Goal

- make verify failure a first-class native loop outcome,
- prove repair and resume state remain externally inspectable,
- distinguish retryable failure from exhausted-recovery block,
- ensure control-plane and UI projections stay aligned with runtime recovery facts.

## Required Failure Shape

The first closure proof for this phase must include all of the following:

1. a real verification failure with structured failure classification,
2. repair summary output with attempt history and retry budget,
3. persisted resume context carrying verification and repair continuity,
4. a governed resume path that either retries coherently or blocks without rerunning when recovery is exhausted,
5. control-plane projection of the resulting recovery state,
6. UI execution summary visibility for the resulting recovery action,
7. proof that the control plane remains the single source of truth for the recovery chain.

## Implementation Steps

1. Reuse the native coding runtime verify path rather than introducing synthetic recovery-only payloads.
2. Pin one real failure-driven chain in tests:
   - verification fails,
   - repair summary is persisted,
   - resume context preserves continuity,
   - later resume reflects retry or exhausted-recovery semantics,
   - control-plane and UI surfaces expose the same recovery interpretation.
3. Keep runtime-native proof and recovery-native proof aligned so later dogfood tasks can cite both.
4. Record remaining repair weaknesses as kernel gaps rather than masking them behind external-agent execution.

## Acceptance Criteria

Phase 4 is complete only when all of the following are true:

1. a real verification failure path is covered through runtime state,
2. repair summary and retry budget are persisted and inspectable,
3. resume behavior is coherent for the chosen failure scenario,
4. control-plane artifacts expose the resulting recovery state,
5. UI execution summary exposes the same recovery action and failure interpretation,
6. the proof stays native-only and does not rely on an external coding agent to recover.

## Targeted Tests

```bash
pytest tests/test_docs_process.py tests/test_coding_agent_runtime.py tests/test_control_plane.py tests/test_ui_service.py -q
```

## Output Of This Phase

After this phase, later work should be judged against one question:

Can the repository show a real native verify-failure chain, with persisted repair state and governed resume or block semantics, through runtime, control-plane, and UI surfaces?
