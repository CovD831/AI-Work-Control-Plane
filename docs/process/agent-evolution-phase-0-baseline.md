# Agent Evolution Phase 0: Current-State Baseline

## Goal

Lock the current architectural baseline before changing execution semantics.

This phase answers three questions:

1. What is the system today?
2. What is it not?
3. What stable boundaries must later phases preserve?

## Scope

- record the current system identity in canonical process docs
- define the current execution layer as workflow-governed, not fully autonomous multi-agent collaboration
- pin the execution protocol for future phases: phase plan first, targeted tests, advance only on green

## Non-Goals

- no runtime behavior changes
- no message schema changes
- no routing or recovery logic changes
- no LangGraph or A2A integration work yet

## Implementation Steps

1. Add the master evolution plan with ordered phases and targeted tests.
2. Add this Phase 0 plan with explicit scope and acceptance criteria.
3. Update canonical architecture/process docs so they describe the current execution layer accurately.
4. Add doc tests that enforce the new baseline language.

## Acceptance Criteria

- canonical docs state that the current system is governance-first and workflow-governed
- canonical docs state that the current execution layer has multi-role semantics but is not yet a high-autonomy multi-agent system
- canonical docs state that the control plane remains the system of record
- canonical docs state that every later phase requires a phase plan plus targeted tests before advancement
- `tests/test_docs_process.py` contains assertions that pin this baseline

## Targeted Tests

```bash
pytest tests/test_docs_process.py -q
```

## Exit Condition

Advance to Phase 1 only after the targeted test passes and the baseline language is committed in docs.
