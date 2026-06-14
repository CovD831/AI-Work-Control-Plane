# Native Coding Agent Phase 3 Context Engineering Main-Path Hardening

## Scope

This phase makes context engineering a first-class main-path contract inside the native coding runtime.

It does not attempt to solve every future child-agent or long-horizon orchestration problem.

It exists to stop `Write`, `Select`, `Structured Observation`, `Compact`, and `Isolate` from remaining partially present as:

- payload decoration after execution,
- helper-local behavior without one shared contract,
- traces that are inspectable but not required,
- or resume-adjacent data that is not clearly tied back to per-step execution semantics.

## Goal

- make `Context Write` explicit for each model-participating loop,
- make `Context Select` mandatory rather than best-effort,
- make `Structured Observation` a required post-action surface,
- make `Compact` traceable as a governed context-shaping decision,
- make `Isolate` explicit when complexity exceeds the primary loop budget,
- preserve resume continuity across these context-engineering surfaces.

## Required Code Anchors

This phase is grounded in the current context-engineering seams:

- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `src/agent_orchestrator/memory.py`
- `src/agent_orchestrator/session/runtime.py`
- current runtime payload fields:
  - `context_selection`
  - `scratchpad_entries`
  - `structured_observations`
  - `compaction_state`
  - `compressed_context`
  - `isolation_state`
  - `resume_context`

## Phase Rule

The runtime is not considered context-engineering hardened merely because these fields exist somewhere in the payload.

This phase requires them to behave as one explicit main-path contract for every model-participating loop.

## Implementation Steps

1. Define one `context_engineering_contract` surface in the runtime output.
2. Make that contract summarize:
   - write surfaces used for the current loop,
   - context-selection requirement and chosen inputs,
   - structured-observation requirement and produced records,
   - compaction decision state and traceability,
   - isolation decision state and reinjection semantics,
   - resume continuity expectations for the same context-engineering state.
3. Ensure `Context Write` clearly separates:
   - session scratchpad state,
   - persistent memory projection,
   - transient loop-local context.
4. Ensure every model-participating step can be explained through explicit:
   - context selection,
   - structured observation,
   - next-step or resume continuity.
5. Ensure compaction and isolation remain governed loop decisions rather than hidden helper behavior.

## Acceptance Criteria

Phase 3 is complete only when all of the following are true:

1. the runtime exposes one explicit `context_engineering_contract`,
2. `Write`, `Select`, `Structured Observation`, `Compact`, and `Isolate` are summarized as required main-path behavior,
3. the contract distinguishes scratchpad, memory, and transient loop context clearly,
4. the contract stays compatible with resume state and recovery projection,
5. tests prove the contract is not merely derived documentation after the fact.

## Targeted Tests

```bash
pytest tests/test_coding_agent_runtime.py tests/test_memory.py tests/test_control_plane.py -q
```

## Output Of This Phase

After this phase, later work should be judged against one question:

Can every model-participating loop in the native runtime be explained through one stable context-engineering contract, rather than by piecing together scattered payload fields and helper-local behavior?
