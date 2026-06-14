# Native Coding Agent Phase 1 Kernel Boundary

## Scope

This phase defines the `native coding agent kernel` as an explicit governed execution boundary inside the current repository.

This phase does not attempt to complete the full native runtime upgrade.

It exists to prevent later implementation from collapsing back into:

- ad hoc runtime helpers,
- provider-first execution wiring,
- topology/runtime boundary blur,
- or control-plane bypass through implicit runtime state.

## Goal

- define the kernel as the repository's governed execution core for coding work,
- define the kernel's upstream inputs from existing repository layers,
- define the kernel's downstream outputs into existing control-plane and session surfaces,
- define what belongs inside the kernel versus outside it,
- define the targeted tests that later implementation must keep green while evolving the kernel.

## Architectural Position

Within the current repository layering:

- `AI Work Control Plane` remains the system of record and product surface,
- `决策核心层` decides whether execution may proceed and under what constraints,
- `执行拓扑层` decides the collaboration shape,
- `Provider / Runtime 层` owns concrete model/tool/job backends,
- the `native coding agent kernel` sits between topology intent and runtime effects as the governed execution core for coding work.

The kernel is therefore:

- not a replacement for the control plane,
- not identical to execution topology,
- not identical to a concrete provider or CLI adapter,
- not allowed to become a second durable state authority.

## Required Code Anchors

This phase is grounded in the current code seams:

- `src/agent_orchestrator/execution/runtime.py`
- `src/agent_orchestrator/execution/models.py`
- `src/agent_orchestrator/session/runtime.py`
- `src/agent_orchestrator/control_plane_runtime.py`
- `src/agent_orchestrator/execution/coding_agent_runtime.py`

Later implementation may evolve these seams, but it must preserve the Phase 1 contract.

## Kernel Input Contract

The kernel must treat the following as upstream inputs rather than internally re-derived truths:

1. execution objective and route outcome from `ExecutionRequest`,
2. task/strategy intent from approved or routed execution context,
3. session continuity from `SessionRuntime` and context snapshots,
4. governance constraints derived from control-plane and decision-core artifacts,
5. topology-selected collaboration intent, if any,
6. provider/runtime availability as bounded runtime capability input rather than system truth.

The kernel may enrich these inputs for execution, but it must not redefine their authoritative meaning.

## Kernel Output Contract

The kernel must produce outputs that can be projected back into existing repository surfaces:

1. structured execution results and step decisions,
2. structured observations and artifact references,
3. resume-compatible execution state,
4. runtime-event-compatible summaries,
5. recovery-visible status and next-step hints,
6. memory-eligible facts separated from transient scratchpad state,
7. approval-visible pause or block states when execution cannot continue autonomously.

The kernel must not rely on opaque internal progress that cannot be surfaced through these channels.

## Boundary Rules

### What Belongs Inside The Kernel

- step planning and next-step decision logic,
- context write/select/compact/isolate behavior for execution,
- action dispatch selection,
- structured observation handling,
- verify/repair/continue decision semantics,
- runtime-local transient scratchpad state,
- resumable per-turn execution state.

### What Must Stay Outside The Kernel

- canonical durable control-plane truth,
- approval queue ownership,
- evidence bundle ownership,
- workspace state ownership,
- topology choice as a product-level decision,
- provider session ownership,
- raw job backend ownership.

## First Implementation Constraints

Phase 1 implementation must preserve these rules:

1. the kernel consumes `ExecutionRequest`-style inputs rather than pulling arbitrary repository truth directly,
2. the kernel returns structured results rather than only side-effecting files or jobs,
3. session continuity remains mediated through `SessionRuntime`,
4. runtime-event and recovery surfaces remain projections of kernel-visible facts,
5. provider/runtime adapters remain replaceable and do not become the execution brain,
6. topology decisions remain inputs to execution rather than hidden runtime heuristics.

## Acceptance Criteria

Phase 1 is complete only when all of the following are true:

1. the kernel is explicitly defined in docs as a governed execution boundary,
2. upstream input ownership is explicitly documented,
3. downstream output obligations are explicitly documented,
4. inside-vs-outside boundary rules are explicitly documented,
5. the current code anchors are explicitly named,
6. the phase leaves a stable contract for Phase 2 step-loop convergence work.

## Targeted Tests

```bash
pytest tests/test_docs_process.py -q
```

## Output Of This Phase

After this phase, later work should be judged against one question:

Does a proposed runtime change make the repository's native coding kernel more explicit, more governed, and more compatible with control-plane projection surfaces, or does it push execution logic back into scattered glue and implicit ownership?
