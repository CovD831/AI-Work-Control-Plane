# AI Work Control Plane Continuous Hardening Plan

## Purpose

Keep the product center on AI Work Control Plane, not explicit agent choreography. Explicit `agent team` orchestration remains useful for real work now, but it is governed by external state, context, strategy, topology, approvals, evidence, memory, and recovery.

Long-term principle:

- short term: use explicit orchestration to ship real local work
- medium term: let the control plane govern orchestration
- long term: allow orchestration to be internalized by model runtimes while state, evidence, approvals, memory, and recovery remain external system artifacts

## Execution Protocol

- Write a short phase plan before each phase.
- Run targeted tests during phases.
- Continue automatically when targeted tests pass.
- Run full `pytest` and `team check-compliance` only at final convergence.
- Stop only for destructive operations, provider credential/network blockers, or product-direction conflicts.

## Phases

1. Phase 0: close the reframe baseline and pin the long-term principle.
2. Phase 1: make control-plane status the default operator narrative.
3. Phase 2: harden interruption-aware recovery semantics.
4. Phase 3: broaden topology policy signals.
5. Phase 4: harden scoped documentation and compliance synchronization.
6. Phase 5: record direct-api tool-loop intent without adding a patch engine.
7. Phase 6: dogfood the full artifact chain on this repository.
8. Phase 7: run full convergence gates and update progress docs.
