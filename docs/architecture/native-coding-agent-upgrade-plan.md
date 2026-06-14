# Native Coding Agent Upgrade Plan

## Goal Text

Use the following short-form text for goal mode:

> 目标：在保留现有 AI Work Control Plane、决策核心层、执行拓扑层、approval、evidence、memory provenance、recovery 与 UI 可观察面的前提下，把当前仓库升级为一个不依赖 opencode、codex 等外部 coding agent 也能推进真实项目任务的 native coding agent 闭环；升级重点是把现有 coding runtime 收敛成 governed execution kernel，以稳定 step-loop 为核心，在主路径落地 Context Write / Select / Structured Observation / Compact / Isolate / Verify / Repair / Resume，并原生消费和回写 control-plane artifacts。执行详情与分阶段约束以 [native-coding-agent-upgrade-plan.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/architecture/native-coding-agent-upgrade-plan.md) 为准，每个 phase 开始前必须先写对应 `docs/process/` phase plan。验收目标：当前项目作为一个整体，在 native runtime 模式下可以通过多层协作独立完成至少一类真实开发任务，从任务进入、上下文组装、执行、验证、失败修复、审批阻塞、恢复继续到 evidence/memory/UI 投影形成完整闭环。验收标准：1. 默认主路径不依赖 opencode、codex 等外部 coding agent 才能完成该任务类；2. runtime 具有稳定明确的 step-loop 核心，而不是仅靠局部阶段胶水推进；3. 每次模型参与步骤都经过显式 Context Select 与 Structured Observation 处理，并在需要时进入 Compact/Isolate；4. Verify/Repair/Resume 能在真实失败场景下闭环；5. control plane 仍然是 state、approval、evidence、recovery、memory 的唯一可信记录源；6. 至少一条真实任务链路有可审计 artifacts、event summaries、recovery state 与 evidence 证明。禁止把仅补局部能力、仅优化单个 helper、或仅接回外部 coding agent 视为完成。

## Purpose

This document defines the upgrade plan for turning the repository into a self-sufficient native coding-agent system.

It is intentionally split into:

- a short `goal mode` text for constrained surfaces,
- a detailed architecture and execution plan for implementation.

The plan treats the repository as one integrated system rather than as a standalone runtime comparison exercise.

## Architectural Position

This plan follows the current canonical layering:

- `AI Work Control Plane` remains the top-level product surface and durable system of record,
- `决策核心层` continues to own execution eligibility, planning governance, risk boundaries, and continuation rules,
- `执行拓扑层` continues to own collaboration shape such as `solo`, `team`, or future richer forms,
- `Provider / Runtime 层` continues to own concrete model/tool/runtime backends,
- the new `native coding agent kernel` becomes the governed execution core that connects topology intent to concrete runtime action.

The native coding agent is therefore:

- not a replacement for the control plane,
- not merely another external provider adapter,
- not the same thing as execution topology,
- not a product reframe away from governance-first architecture.

It is the repository's own execution kernel for coding work.

## Current State Summary

As of the current repository state:

- the project already has a strong governance loop,
- the control-plane artifact pipeline is explicit,
- planning governance, approvals, evidence, recovery, and memory provenance are already first-class,
- a real coding runtime already exists,
- the coding runtime already includes session continuity, bounded edits, verification seams, compaction state, isolation state, runtime events, and resume-aware execution state.

However, the repository still falls short of being a strong native-only coding-agent workhorse.

The main gap is not missing governance.

The main gap is that the native coding runtime is not yet mature enough to act as the default long-horizon coding engine without relying on external coding agents for execution strength.

## Repository-Level Comparison Vs OpenCode

Compared as whole systems:

### Areas Where This Repository Is Stronger

- stronger governance and artifact externalization,
- stronger approval, evidence, and recovery framing,
- clearer system-of-record discipline,
- better long-horizon operator visibility,
- better architectural separation between durable truth and runtime execution.

### Areas Where OpenCode Is Stronger

- more mature native coding-agent execution loop,
- more productized session continuation,
- cleaner provider and protocol abstraction for coding execution,
- stronger out-of-the-box context digestion and task completion behavior,
- closer to default daily-driver status for coding work.

### Practical Conclusion

This repository already has the better outer operating system.

It still needs a stronger inner execution kernel.

That is the purpose of this plan.

## Upgrade Objective

The repository should become capable of the following without requiring OpenCode, Codex, or similar external coding agents as the main executor:

1. accept a real project task through the existing governed surfaces,
2. produce or consume the right control-plane artifacts,
3. run a native coding-agent execution loop,
4. perform repo exploration, context assembly, edit selection, verification, repair, and continuation,
5. pause on approvals or evidence gaps when needed,
6. resume from persisted state without losing context-engineering continuity,
7. complete at least one real development-task class through the native runtime alone.

External coding agents may still be supported as optional execution capabilities, but they must no longer be required for main-path closure.

## Goal-Mode Acceptance Guardrail

When this plan is used in goal mode, success must be judged against whole-system closure rather than isolated runtime improvements.

The work is not complete if it only:

- improves a helper without strengthening main-path closure,
- adds a partial runtime feature without proving end-to-end task completion,
- improves documentation without changing executable system capability,
- keeps external coding agents as the real dependency while labeling native mode as complete.

The work is complete only when the repository can demonstrate governed native-only closure for at least one real task class with auditable outputs.

## Non-Negotiable Invariants

The following must remain true throughout the upgrade:

- the control plane remains the system of record,
- approvals remain externally inspectable and enforceable,
- evidence remains durable and operator-visible,
- recovery state remains reconstructable,
- memory remains explicit rather than hidden in transient model state,
- execution topology remains a separate concern from provider/runtime binding,
- no second canonical state source is introduced,
- native runtime evolution must strengthen rather than bypass governance surfaces.

## Main Gaps To Close

### Gap 1: Step-Loop Maturity

The runtime has stage-kernel behavior, but it still needs to converge into a more stable and expressive step-loop that can sustain real project work beyond bounded edit flows.

### Gap 2: Main-Path Context Engineering

`Write`, `Select`, `Structured Observation`, `Compact`, and `Isolate` exist in partial or evolving form, but they are not yet strong enough as a fully productized main-path contract.

### Gap 3: Native Verify/Repair Closure

Verification exists, but the broader loop from failure to diagnosis to repair to re-verification is still not strong enough for native-only default use.

### Gap 4: Isolation And Subtask Digestion

The runtime needs a more practical isolate path so complex subproblems do not overload the primary context loop.

### Gap 5: Whole-System Defaultability

The repository still needs proof that the native runtime can drive real repository work through existing control-plane, decision, topology, and recovery surfaces without external coding-agent dependence.

## Target Architecture

The target whole-system execution shape is:

`Task Intake -> Control-Plane Artifacts -> Decision Constraints -> Topology Choice -> Native Coding Agent Kernel -> Runtime Actions -> Structured Observations -> Evidence / Recovery / Memory / UI Projections`

The target kernel loop is:

`Step Planning -> Context Write -> Context Select -> Action -> Structured Observation -> Context Compact/Isolate -> Verify/Repair Decision -> Continue / Pause / Finish`

## Phase Sequence

Each phase should begin with a short phase plan under `docs/process/` before implementation.

Each phase should run only targeted tests until the phase acceptance bar is met.

Full `pytest` and final compliance should run only at the final convergence gate.

### Phase 0: Baseline And Closure Contract

Goal:

- define the current native-runtime closure boundary precisely,
- establish the canonical closure metrics for native-only execution,
- prevent the project from overclaiming native completeness before the runtime is ready.

Implementation:

- write a short phase plan for native closure baseline,
- define native-only closure criteria and task classes,
- document the current external-agent dependency boundary,
- add or update tests that assert the existence of canonical docs and goal text.

Acceptance:

- a phase plan exists,
- native closure criteria are explicit,
- the repository has a stable document to point goal-mode execution at.

Suggested targeted tests:

```bash
pytest tests/test_docs_process.py -q
```

### Phase 1: Kernel Boundary Hardening

Goal:

- make the native coding runtime an explicit governed execution kernel rather than an implicit execution helper cluster.

Implementation:

- define the kernel contract in code and docs,
- separate kernel inputs from control-plane artifacts, topology decisions, and low-level runtime effects,
- narrow and stabilize execution payload boundaries,
- ensure resume state maps cleanly to kernel loop semantics.

Acceptance:

- the runtime has a clearly identifiable kernel contract,
- kernel inputs and outputs are explicit,
- control-plane and runtime responsibilities are not blurred.

Suggested targeted tests:

```bash
pytest tests/test_cli.py tests/test_control_plane.py tests/test_team.py -q
```

### Phase 2: Step-Loop Convergence

Goal:

- converge the runtime around a true step-loop rather than a bounded staged execution skeleton.

Implementation:

- unify next-step planning and outcome dispatch,
- make continuation decisions explicit at every loop boundary,
- reduce leftover stage-specific glue that prevents richer long-horizon behavior,
- ensure pause, block, retry, accept, and finish semantics are loop-native.

Acceptance:

- the runtime has a stable loop core,
- next-step decisions are explicit and inspectable,
- the kernel is no longer primarily shaped as a fixed explore/edit/verify chain.

Suggested targeted tests:

```bash
pytest tests/test_coding_agent_runtime.py tests/test_execution_runtime.py -q
```

### Phase 3: Context Engineering Main-Path Hardening

Goal:

- make `Write`, `Select`, `Structured Observation`, `Compact`, and `Isolate` true main-path contracts for every model-participating loop.

Implementation:

- harden scratchpad vs persistent memory separation,
- ensure every LLM call passes explicit context selection,
- strengthen observation structure, trimming, deduplication, and artifact externalization,
- strengthen compaction thresholds and summary traceability,
- strengthen isolate input/output and reinjection behavior.

Acceptance:

- all five context-engineering capabilities are real main-path behavior,
- tests prove they are not just payload decoration,
- runtime state can be resumed with sufficient context continuity.

Suggested targeted tests:

```bash
pytest tests/test_coding_agent_runtime.py tests/test_memory.py tests/test_control_plane.py -q
```

### Phase 4: Verify/Repair/Resume Closure

Goal:

- make native execution robust enough to survive failed checks, partial progress, and interruption without falling back to external coding-agent strength.

Implementation:

- strengthen repair-loop semantics,
- add clearer failure classification and recovery-path choice,
- ensure approval pauses, evidence blocks, and retryable failures are distinguished,
- improve runtime-to-recovery projection fidelity.

Acceptance:

- failed native runs can classify, repair, retry, or pause coherently,
- recovery surfaces reflect kernel state faithfully,
- interrupted execution can resume with meaningful continuity.

Suggested targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_team.py tests/test_coding_agent_runtime.py -q
```

### Phase 5: Native-Only Dogfood Track

Goal:

- prove that the repository can advance real work through native runtime mode alone.

Implementation:

- define one or more bounded real task classes,
- run those tasks through the native runtime path,
- record artifacts, evidence, runtime summaries, and recovery behavior,
- document remaining pain points as native-kernel gaps rather than hiding them behind external-agent success.

Acceptance:

- at least one real task class completes natively,
- operator-visible evidence exists,
- the repository can describe where native mode is already defaultable and where it is not.

Suggested targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py -q
```

### Phase 6: Optional External-Agent Repositioning

Goal:

- keep OpenCode, Codex, or other external coding agents as optional capability providers rather than closure dependencies.

Implementation:

- formalize external-agent runtime boundaries,
- clarify when native mode is default and when external mode is enhancement-only,
- keep plugin seams but prevent architectural confusion about system ownership.

Acceptance:

- external-agent support remains available,
- native mode remains the default closure target,
- documentation clearly distinguishes optional augmentation from required execution.

Suggested targeted tests:

```bash
pytest tests/test_cli.py tests/test_control_plane.py tests/test_team.py -q
```

## Final Convergence Criteria

This upgrade plan is complete only when all of the following are true:

1. the repository can execute at least one real development-task class natively through the governed runtime,
2. the native runtime is strong enough to serve as the default closure path for bounded internal repository work,
3. approvals, evidence, memory, recovery, and UI projections remain intact and trustworthy,
4. native runtime behavior is inspectable through control-plane artifacts rather than hidden in opaque runtime state,
5. external coding agents are optional accelerators rather than mandatory execution crutches,
6. remaining gaps are quality or breadth gaps rather than core closure gaps.

## Suggested Working Pattern

When using this plan in practice:

1. paste the `Goal Text` into goal mode,
2. treat this document as the detailed execution contract,
3. create a short phase plan before each implementation phase,
4. run only targeted tests during the phase,
5. advance only after the phase acceptance bar is met,
6. reserve full regression and compliance for final convergence.

## Immediate Next Step

The best next step is:

- write `Phase 0` as a short process plan,
- define the native-only closure baseline,
- identify the first real task class that the repository must complete without OpenCode or Codex.
