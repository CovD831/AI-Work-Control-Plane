# Coding Agent Goal Spec

## Goal Text

Use the following short-form text for goal mode:

> 在保留现有 control plane、approval、memory、run_store、UI 与总体分层架构前提下，将当前 coding agent 演进为一个以 while-loop 为核心、具备完整 Context Engineering 能力的 governed execution runtime。该 runtime 必须在主路径中落地 Write、Select、Compact、Isolate 四类上下文机制：Session-level Scratchpads 与 Persistent Memory 分离；LLM 调用前支持 Deterministic、Model-driven、Retrieval-based 三类上下文选择；Observation 必须先结构化并在必要时裁剪、去重、压缩后再进入主上下文；Compact 必须支持 Observation Masking、轻量 Compaction 与高占用时的 LLM Summarization；Isolate 必须支持子代理或等价隔离执行。系统还必须能从项目根目录 `.env.local` 读取真实 LLM 配置，并在受治理约束下通过真实调用完成至少一类真实任务。完成标准以本文件中的终止条件与严格验收标准为准，剩余工作只能是增强优化而非核心缺口。

## Scope

This goal is specifically about converging the coding-agent runtime into a governed, resumable, context-engineered execution kernel.

It is not a mandate to rewrite the entire repository.

The following architectural boundaries must be preserved:

- `control plane` remains the source of truth for durable governance state,
- `approval` stays externally inspectable and enforceable,
- `memory` remains explicit system memory rather than hidden model-only state,
- `run_store` and runtime evidence remain durable and auditable,
- `UI` and governance surfaces remain compatible with runtime evolution,
- the overall repository layering is evolved incrementally rather than replaced wholesale.

## Core Runtime Contract

The target runtime should converge around this loop:

`Step Planning -> Context Write -> Context Select -> Action -> Structured Observation -> Context Compact/Isolate -> Next-Step Decision`

The point of the work is not to optimize individual helpers indefinitely.

The point is to make this loop the stable, governed core of the coding-agent runtime.

## Required Context Engineering Capabilities

### 1. Write

The runtime must distinguish between:

- `Session-level Write`: writes transient working state into session-scoped `Scratchpads`,
- `Persistent Write`: writes long-term-value information into explicit external `Memory`.

Session-level Write should be used for:

- intermediate reasoning traces that need structured carry-forward,
- temporary plans,
- working notes,
- task-local data that should survive within the session but not become long-term memory.

Persistent Write should be used for:

- user preferences,
- durable task facts,
- stable project rules,
- long-lived knowledge worth reuse across runs or sessions.

Current implementation progress note:

- the coding-agent runtime now writes a session-scoped runtime-context scratchpad entry during execution,
- that scratchpad currently captures planner-context trace plus a compacted observation window,
- the runtime also now emits a bounded persistent memory record for the turn so session-local runtime facts begin to flow into explicit external memory rather than remaining only in transient payload state.

### 2. Select

Before each LLM call, the runtime must dynamically choose the most relevant context from available sources.

It must support at least:

- `Deterministic Select`: rule-driven context loading such as `AGENTS.md`, system constraints, task contracts, and governance-required context,
- `Model-driven Select`: model-assisted selection when candidate context is too large or too ambiguous for purely fixed rules,
- `Retrieval-based Select`: similarity- or search-based retrieval from `Memory`, `RAG`, `Scratchpads`, or equivalent stores.

Current implementation progress note:

- the coding-agent runtime now performs an explicit main-path context-selection step before execution payload assembly,
- `Deterministic Select` currently includes fixed runtime governance context, session context, task contract, and bounded repository candidate-path signals,
- `Retrieval-based Select` currently uses `MemoryStore.search()` against the active requirement and records the selected memory ids in both payload and scratchpad state,
- `Model-driven Select` now exists as an optional OpenAI-compatible selector that activates only when the candidate set is broad enough and configuration is available; on failure or missing config it falls back safely to deterministic and retrieval-based selection.

### 3. Compact

The runtime must support staged context compaction:

1. full preservation of `Thought`, `Action`, and `Observation`,
2. `Observation Masking` for older observations while keeping the most recent N observations intact,
3. lightweight compaction without LLM calls,
4. higher-threshold `LLM Summarization`.

Lightweight compaction must include at least:

- aggressive masking of low-value historical material,
- trimming overly long code blocks,
- removing redundant logs,
- cleaning meaningless blank-line noise,
- merging duplicate tool outputs.

`System Prompt` is never compacted, replaced, masked, or summarized.

Current implementation progress note:

- the coding-agent runtime now exposes an explicit `compaction_state` in its main payload,
- compaction now reports stage, masked-observation count, preserve-recent window, light-compaction status, summarization-trigger status, and an explicit `system_prompt_compacted=false` guarantee,
- current stages include `full_fidelity`, `observation_masking`, `light_compaction`, and `summarization_ready`,
- the runtime now also supports optional OpenAI-compatible LLM summarization at the high-water mark, with automatic safe fallback to a local summary when configuration or transport is unavailable.

### 4. Isolate

The runtime must support isolating complex subproblems into a child agent or equivalent isolated execution unit.

This is not just parallelism.

It must serve as a deliberate context-isolation and context-digestion mechanism so the primary runtime loop does not absorb unnecessary raw detail.

Current implementation progress note:

- the coding-agent runtime now exposes an explicit `isolation_state` contract in its main payload and scratchpad state,
- a real isolation helper now digests broad target-path / patch-plan / model-selected context into a smaller `digest` payload before reinjection,
- current strategies include `inline_context` and `subtask_digest`,
- this is an initial isolation path and not yet a fully generalized child-agent graph execution system.

### 5. Structured Observation

All tool-returned `Observation` must be structured before entering the main runtime context.

That structured processing layer must be able to:

- classify the observation,
- annotate source and type,
- summarize payload,
- enforce size boundaries,
- trim or deduplicate when necessary,
- decide what enters main context versus external artifacts.

Current implementation progress note:

- the coding-agent runtime now routes execution-step observations through a shared structured-observation transformation,
- that transformation trims long strings, deduplicates repeated list entries, and produces masked historical observation windows for resume and compressed-context payloads,
- this is an initial lightweight compaction layer rather than the full target-state compaction system.

## Real LLM Requirement

The system must support real LLM-backed task execution, not only mocks or synthetic fixtures.

The expected local configuration source is:

- project-root `.env.local`

At minimum, the runtime and its test harness must support the existing OpenAI-compatible configuration path exposed through:

- `AO_SLOTFILL_API_KEY`
- `AO_SLOTFILL_BASE_URL`
- `AO_SLOTFILL_MODEL`
- optional timeout configuration

Real LLM usage must satisfy all of the following:

- it must be able to enter an actual coding-agent runtime path,
- it must be able to complete at least one real task class,
- it must remain governed by the same approval/evidence/recovery/context pipeline contracts,
- it must not be limited to a trivial adapter connectivity smoke test.

## Termination Conditions

The goal is complete only when all of the following are true:

1. the runtime has a stable explicit `while-loop` or `step-loop` core and no longer depends on scattered hard-coded staged glue for its primary control flow,
2. `Write`, `Select`, `Compact`, and `Isolate` all exist in the actual runtime main path rather than only in design notes or placeholder interfaces,
3. `Session-level Write` and `Persistent Write` are separated by contract, storage target, and intended use,
4. `Scratchpads` can carry session-scoped notes, temporary plans, and intermediate structured state for later steps,
5. persistent `Memory` can carry cross-run or cross-session facts such as user preferences and durable rules,
6. every LLM call goes through an explicit context-selection step,
7. `Deterministic Select`, `Model-driven Select`, and `Retrieval-based Select` each have real code paths and trigger conditions,
8. raw tool outputs no longer flow straight into main context without structured observation processing,
9. observation processing supports typed structure, source annotation, length control, and optional trimming or deduplication,
10. staged compaction includes full preservation, observation masking, lightweight compaction, and threshold-based LLM summarization,
11. `System Prompt` is never compacted or summarized,
12. `Isolate` has at least one real runnable path that materially reduces main-context pressure,
13. resume and recovery can restore or reconstruct the necessary scratchpad, memory, observation-window, and summary state,
14. the runtime can load real LLM configuration from project-root `.env.local`,
15. real LLM calls can participate in at least one genuine task loop inside the coding-agent runtime,
16. at least one end-to-end real task can be completed through real LLM calls with auditable outputs,
17. real LLM paths remain subject to governance surfaces including approvals, artifacts, event summaries, and recovery state,
18. no-config or missing-config cases degrade safely through skip, fallback, or explicit error without breaking default test flows,
19. architecture docs, code, and tests agree on what is complete,
20. any remaining work is enhancement-only rather than a missing target-mode core capability.

## Strict Acceptance Criteria

### Architecture Acceptance

The implementation must prove:

- a clearly identifiable runtime main loop,
- explicit context-pipeline contracts or stages,
- clear module boundaries for scratchpads, persistent memory, observation processing, selection, compaction, and isolation,
- runtime progression organized around context handling and next-step decisions rather than a fixed `explore/edit/verify` chain alone.

### Write Acceptance

The implementation must prove:

- a concrete session-level write contract,
- scratchpad write/read behavior,
- a concrete persistent-write contract,
- persistent memory boundaries that reject temporary execution noise,
- tests showing scratchpad and persistent memory are both readable and not confused with one another.

### Select Acceptance

The implementation must prove:

- deterministic selection of fixed required context,
- model-driven selection when candidate context is too broad,
- retrieval-based selection from memory-like stores,
- non-trivial trigger logic for the three selection modes,
- tests covering all three modes.

### Observation Acceptance

The implementation must prove:

- all tool output enters a structured observation layer first,
- structured observations carry at least `kind`, `source`, `summary`, and payload or equivalent fields,
- observations can be trimmed, deduplicated, or externalized before entering main context,
- tests proving long or redundant raw tool output is not injected unchanged.

### Compact Acceptance

The implementation must prove:

- compaction thresholds or switching rules,
- observation masking for older history,
- preservation of the most recent N observations,
- lightweight compaction before LLM summarization,
- summarization only at higher thresholds,
- traceability from summaries back to replaced history,
- tests covering masking, lightweight compaction, summarization, and system-prompt immutability.

### Isolate Acceptance

The implementation must prove:

- at least one real isolate path,
- a clear input/output contract for isolation,
- reinjection of isolated results into main context in reduced form,
- tests proving that the primary context receives digested results instead of full duplicated raw sub-context.

### Recovery And Governance Acceptance

The implementation must prove:

- recoverable execution after interruption,
- inspectable governance surfaces for writes, selection, compaction, and isolation decisions,
- no loss of approval, artifact, event-summary, or execution-history fidelity,
- tests proving recovery behavior.

### Real LLM Acceptance

The implementation must prove:

- project-root `.env.local` configuration is actually usable,
- a real-LLM integration path exists and is repeatable,
- real-LLM tests are opt-in and do not contaminate default unit-test regression,
- missing config leads to skip or explicit safe failure,
- at least one real task test goes beyond adapter connectivity,
- the real task path feeds model output through structured observation and into the runtime main path,
- governance surfaces can still observe results from the real-LLM path,
- documentation explains enablement, boundaries, and safety expectations for these tests.

Current verification boundary:

- real-LLM integration tests are intentionally opt-in and should skip when project-root `.env.local` or process environment does not provide usable `AO_SLOTFILL_*` values,
- when configuration exists but outbound requests are unavailable in the current environment, tests should skip rather than fail unrelated default regression flows,
- the runtime-level real-LLM integration path is expected to surface its results through the same scratchpad, artifact, event-summary, execution-history, compaction, and approval-compatible payload surfaces used by non-LLM runs,
- real-LLM intent refinement is governed as a bounded planning/refinement step and does not bypass the runtime's existing action, verification, or recovery contracts.

### Test Acceptance

The following categories must exist and pass:

- runtime main regression,
- scratchpad write/read tests,
- persistent memory write/read tests,
- deterministic select tests,
- model-driven select tests,
- retrieval-based select tests,
- structured observation tests,
- observation masking tests,
- lightweight compaction tests,
- summarization-trigger tests,
- isolate-path tests,
- real-llm integration tests,
- resume/recovery tests.

### Documentation Acceptance

The documentation must prove:

- the runtime contract is described accurately,
- the repository state and plan state are consistent,
- termination conditions are explicit,
- real-LLM usage via `.env.local` and its testing boundaries are documented.

## Not Complete If

The goal is not complete if any of the following remain true:

- only docs exist but not main-path code,
- only interfaces or dataclasses exist without real dispatch,
- context selection still mostly concatenates everything,
- observations still largely enter context raw,
- compaction exists only as an idea without thresholds and runtime behavior,
- isolation exists only as a concept without a real path,
- scratchpads and persistent memory remain semantically mixed,
- only happy-path tests exist while selection/compaction/recovery paths remain weak,
- `.env.local` can be read but no real task runs,
- only an adapter smoke test exists without runtime-level real-LLM execution,
- real-LLM validation is one-off manual checking instead of repeatable integration testing,
- real-LLM execution bypasses governance,
- remaining gaps are still target-mode core capabilities disguised as future optimization.

## Explicit Non-Goals

The goal does not require:

- a fully generalized multi-agent graph runtime,
- every external tool ecosystem integration,
- turning every select decision into model-driven selection,
- theoretically optimal compaction quality,
- a repository-wide control-plane rewrite,
- permanent verbatim preservation of all historical context in the main loop.
