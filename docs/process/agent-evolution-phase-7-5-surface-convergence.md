# Agent Evolution Phase 7.5: Surface Convergence

## Goal

Converge the Phase 0-7 changes into a narrower product boundary so the repository distinguishes core runtime contracts from operator-facing projections before Phase 8 begins.

## Scope

- define which artifacts and contracts are canonical
- define which surfaces are read-only projections of canonical state
- document what Phase 7 metadata is active behavior versus inspection-only metadata
- freeze Phase 8 entry conditions around boundary clarity rather than adding new execution behavior

## Non-Goals

- no new runtime behavior
- no new role autonomy loop
- no LangGraph pilot implementation yet
- no A2A adapter implementation yet

## Implementation Steps

1. Add a convergence phase to the master evolution plan.
2. Document canonical contracts vs projection surfaces in process docs.
3. Document the implemented-vs-planned boundary for the Phase 0-7 evolution line.
4. Add tests that pin the convergence language and Phase 8 entry conditions.

## Acceptance Criteria

- the evolution plan explicitly includes a convergence phase before Phase 8
- process docs state that control-plane artifacts remain canonical and role/work-graph/CLI enrichments are projections
- Phase 7 role-contract enrichments are documented as inspection and governance metadata, not a new autonomous runtime
- targeted doc tests pass

## Targeted Tests

```bash
pytest tests/test_docs_process.py -q
```

## Exit Condition

Advance to Phase 8 only after the canonical-vs-projection boundary is explicit in docs and pinned by tests.
