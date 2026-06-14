# Native Coding Agent Phase 2 Step-Loop Convergence

## Scope

This phase converges the current coding runtime around a clearer explicit step-loop contract.

This phase does not need to solve every long-horizon execution limitation.

It exists to stop loop semantics from remaining scattered across:

- stage-specific glue,
- loosely related payload fields,
- partial resume traces,
- and operator-visible summaries that imply a loop without exposing one stable loop contract.

## Goal

- define one explicit step-loop contract for the native coding runtime,
- make loop progression easier to inspect as one coherent object,
- preserve existing stage behavior while reducing semantic scatter,
- provide a stable foundation for later verify/repair/resume hardening.

## Required Code Anchors

This phase is grounded in the current step-related seams:

- `src/agent_orchestrator/execution/coding_agent_runtime.py`
- `src/agent_orchestrator/execution/models.py`
- existing payload fields:
  - `planner_context_trace`
  - `next_stage_proposals`
  - `stage_selection_trace`
  - `action_selection_trace`
  - `next_step_contract`

## Phase Rule

The runtime is not considered step-loop converged merely because it contains a `while` loop.

This phase requires the loop to become a stable inspectable contract rather than only an implementation detail.

## Implementation Steps

1. Define a single `step_loop_contract` surface in the runtime output.
2. Make that contract summarize:
   - loop model,
   - current status,
   - current or terminal stage,
   - loop trace references,
   - continue/pause/block/complete disposition,
   - whether resume is expected or supported.
3. Ensure the contract is derived from existing runtime loop facts rather than introducing a second control flow.
4. Ensure operator-visible or evidence-visible projections can reference this contract later without re-deriving loop semantics from scattered fields.

## Acceptance Criteria

Phase 2 is complete only when all of the following are true:

1. the runtime exposes one explicit `step_loop_contract`,
2. the contract summarizes the loop without replacing existing detailed traces,
3. the contract works for completed, paused, and blocked outcomes,
4. the contract remains compatible with persisted resume state,
5. tests prove the contract is present and aligned with actual runtime behavior.

## Targeted Tests

```bash
pytest tests/test_coding_agent_runtime.py tests/test_ui_service.py tests/test_control_plane.py -q
```

## Output Of This Phase

After this phase, later work should be judged against one question:

Does the runtime expose one stable step-loop contract that makes progression, pause, block, completion, and resume semantics easier to reason about than the previous scattered trace-only shape?
