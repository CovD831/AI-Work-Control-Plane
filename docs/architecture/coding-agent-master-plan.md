# Coding Agent Master Plan

## Objective

This plan evolves the repository from a governance-first orchestration runtime into a complete coding-agent system.

The target product is:

> a coding agent with structured intake, adaptive clarify, execution strategy selection, durable session/runtime handling, governed code execution, and operator-visible recovery/evidence surfaces.

This master plan assumes Phase 1 has already been completed:

- lightweight task routing exists,
- clarify has been repositioned as conditional intent intake,
- the legacy execution path is wrapped as a runtime,
- the CLI main path already enters through the new skeleton.

Everything below focuses on the next phases required to turn that skeleton into a real coding agent.

## Non-Negotiable Invariants

These invariants must hold across every phase:

- the control plane remains the source of truth for durable state, approvals, evidence, recovery, and operator-visible summaries,
- the governance plane must remain auditable and must not be replaced by transient model-only state,
- the repository must not introduce a second canonical state source outside control-plane artifacts,
- new execution/runtime behavior must be layered behind explicit abstractions rather than fused back into old direct orchestration flows,
- each phase must be verifiable through targeted tests before the next phase begins.

## End-State Architecture

The long-term system is composed of six cooperating layers.

### 1. Intake Layer

Responsibilities:

- classify incoming work,
- determine whether the request is executable,
- determine whether clarify is needed,
- determine the required clarify depth,
- produce a structured intent envelope before strategy or execution.

Primary objects:

- `TaskRouter`
- `TaskRouterResult`
- `IntentIntake`
- `IntentIntakeResult`

### 2. Strategy Layer

Responsibilities:

- convert intake results into execution strategies,
- choose between direct edit, explore-first, investigation, migration-guarded, docs-sync, or other future modes,
- optionally expand strategy into bounded execution activities or subtask graphs,
- replace the current rigid decompose template system.

Primary objects:

- `StrategyPlanner`
- `ExecutionStrategy`
- `ExecutionPlan`
- `ExecutionActivity`

### 3. Session Layer

Responsibilities:

- own durable agent session semantics,
- record turn boundaries,
- manage context snapshots and execution continuity,
- support interruption and resume,
- isolate runtime history from transient provider-turn state.

Primary objects:

- `AgentSession`
- `SessionTurn`
- `ContextSnapshot`
- `SessionRuntime`

### 4. Execution Layer

Responsibilities:

- explore repository context,
- select relevant files and symbols,
- apply edits,
- run commands and tests,
- respond to failures,
- iterate toward completion,
- support multiple execution runtimes including legacy compatibility.

Primary objects:

- `ExecutionRuntime`
- `RepoExplorer`
- `ContextBuilder`
- `EditExecutor`
- `CommandRunner`
- `VerifyLoop`
- `RepairLoop`

### 5. Governance Layer

Responsibilities:

- retain control-plane truth,
- enforce approval/recovery/evidence semantics,
- summarize execution state for operators,
- audit strategy, runtime behavior, and recovery state.

Primary modules:

- `control_plane.py`
- `planning.py`
- `planning_governance.py`
- `ui_service.py`

### 6. Interop Layer

Responsibilities:

- expose bounded adapters to alternate runtimes, providers, and future agent ecosystems,
- integrate future plugins, protocol bridges, or external agent runtimes without becoming the system of record.

This layer is explicitly later-phase work.

## Architectural Repositioning Of Existing Assets

### Assets To Preserve And Continue Building On

- current control plane and artifact contracts,
- governance snapshot generation,
- approval/evidence/recovery summaries,
- dashboard and operator surfaces,
- clarify-state logic from `adapters.py`,
- task/risk/scope/artifact extraction patterns,
- test coverage around orchestration, governance, and UI surfaces.

### Assets To Reposition

- current `decompose` logic:
  keep temporarily, but move it from “primary routing and task splitting mechanism” to “legacy strategy expansion path”.
- current orchestrator execution path:
  preserve as `legacy execution runtime`, not as the long-term execution design.

### Assets To Build Fresh

- strategy layer,
- session runtime,
- coding execution loop,
- repository exploration and verification loops,
- structured execution event contracts for governance consumption.

## Phase Sequence

## Current Status Checkpoint

At the current repository state:

- Phase 1 is complete,
- Phase 2 is complete,
- Phase 3 is complete,
- Phase 4 is complete in MVP form,
- Phase 5 is complete in bounded repair-loop form,
- Phase 6 is complete for first-pass governance/runtime summary integration.

The repository has now also moved beyond the earlier report-first checkpoint that originally motivated the execution-closure phase.

The `coding_agent` runtime can now:

- apply bounded direct edits inside workspace-root guardrails,
- route edit and verification side effects through a unified `ActionExecutor`,
- classify action risk and block boundary violations before side effects occur,
- interrupt on approval gates and resume from persisted execution state,
- externalize large verification and repository-exploration outputs as execution artifacts,
- emit step-level runtime events and structured execution-history summaries for governance surfaces,
- advance through an explicit stage-cursor execution kernel with persisted resume contracts,
- restore continuation state such as applied changes, recent observations, verification summaries, repair summaries, and planned verification commands,
- let continuation state influence verification command reuse, remaining retry budget, and blocked-versus-rerun selection for resumed verification.

This means the repository already contains an early governed coding runtime rather than only a planning-and-reporting backend.

However, one important gap still remains before clarify-value measurement is meaningful:

- the runtime now has explicit stage planning/dispatch seams plus persisted planner-context traces, approval-aware pause/block selection, and candidate-based next-stage proposals that begin to use continuation history and verify/edit/explore evidence ranking through shared generation/ranking strategy entrypoints, registry-like ranking dispatch, shared proposal-level builders, registry-like stage generators, and emerging per-stage strategy objects that now also build proposals, stage plans, execution dispatch, selected-candidate ranking flow, and stage-level outcome dispatch through a more stable strategy-map structure, with simpler explore/terminal execution semantics plus shared continue-stage semantics, edit pause/block/apply, and verify pause/blocked-resume/terminal outcomes beginning to collapse into shared executor meanings, while verify terminal acceptance/completion decisions also begin to collapse into shared semantic helpers, and those shared execution helpers now begin to route through a lower-level shared stage-outcome builder and stage-owned outcome-semantics namespaces now used by both edit and verify, with stage plans now explicitly carrying stage-strategy context and proposal/candidate/ranking construction now also accepting explicit strategy context so planning/execution paths reuse the same stage contract instead of re-looking it up, while edit/verify strategies now directly binding the core stage execution functions instead of going through transitional wrappers, plus shared candidate/template helpers, including path-vs-terminal, advance-vs-complete, complete-vs-retry, block-vs-retry, and approval/history semantic builders, with initial context-driven candidate synthesis now appearing in verify plus low-risk edit/explore terminal paths, but is still primarily shaped as a bounded staged kernel rather than a richer dynamic step loop,
- context compression and prompt-facing long-horizon state management are still limited,
- the execution abstraction has not yet fully converged on a unified resumable runtime contract across future runtime variants,
- broader long-horizon task behavior and tool-ecosystem expansion remain incomplete.

That means the architectural numbering alone would misleadingly suggest that only evaluation and packaging remain.

To reflect the actual engineering state, the plan now inserts an explicit execution-closure phase before clarify-value measurement.

## Phase 2: Strategy Layer Replacement

### Goal

Replace the current rigid `decompose` role with a real strategy layer that selects how a task should be executed before any heavy execution begins.

### Scope

- add a `strategy` package,
- define `ExecutionStrategy` and `ExecutionPlan`,
- separate task routing from strategy selection,
- downgrade existing `decompose` into a compatibility implementation,
- support at least these strategies:
  - `direct_edit`
  - `explore_then_edit`
  - `investigation_only`
  - `migration_guarded`
  - `docs_sync`
  - `need_human_confirmation`

### Out Of Scope

- repo exploration implementation,
- autonomous repair loops,
- full session runtime.

### Acceptance Criteria

- a new strategy abstraction exists,
- the CLI run path can derive a strategy from intake,
- `decompose` is no longer treated as the first strategy/routing system,
- targeted strategy tests pass,
- existing governance flows remain green.

### Suggested Tests

```bash
pytest tests/test_task_router.py tests/test_adapters.py tests/test_cli.py -q
```

## Phase 3: Session Runtime Foundations

### Goal

Introduce a durable agent session layer so coding execution can run as a session-driven system rather than a direct planner/executor call stack.

### Scope

- add `session` package,
- define `AgentSession`, `SessionTurn`, and `ContextSnapshot`,
- establish execution activity recording,
- connect session semantics to execution requests,
- create interruption/resume primitives for the new execution path.

### Out Of Scope

- full autonomous repair,
- external protocol bridges,
- multi-agent coordination.

### Acceptance Criteria

- execution requests can be tied to a session identifier,
- session state records turns and context snapshots,
- resume semantics exist for the new execution path,
- governance surfaces can read session metadata without replacing control-plane truth.

### Suggested Tests

```bash
pytest tests/test_control_plane.py tests/test_ui_service.py tests/test_cli.py -q
```

### Implementation Tracks

Phase 3 should be executed in four bounded tracks so the repository gains session semantics without destabilizing the current governance path.

#### Track 3.1: Session Domain Models

- add `src/agent_orchestrator/session/models.py`,
- define `AgentSession`,
- define `SessionTurn`,
- define `ContextSnapshot`,
- define `ExecutionActivity`,
- define a small status vocabulary for session and turn lifecycle.

The first cut should prefer immutable or append-only style structures so governance can trust the recorded history.

#### Track 3.2: Session Runtime Compatibility Shell

- add `src/agent_orchestrator/session/runtime.py`,
- define `SessionRuntime` abstraction,
- implement an in-repo compatibility runtime that can:
  - create a session for a new execution request,
  - append a turn for each CLI execution request,
  - attach intake and strategy summaries,
  - record linked orchestration run ids when the legacy runtime executes.

This track should not replace the control plane as the durable record. It should provide a structured session seam that points back to control-plane artifacts.

#### Track 3.3: Execution Request Sessionization

- extend execution-side request metadata so requests can carry:
  - `session_id`,
  - `turn_id`,
  - session origin metadata,
  - resume intent metadata.
- update the CLI entry path so `run` and `start` create or reuse session context before entering the execution runtime,
- keep `team` flows unchanged unless they need to read session metadata.

#### Track 3.4: Governance Visibility

- expose minimal session metadata in summaries and payloads,
- ensure governance snapshots can explain:
  - which session a run belongs to,
  - which turn triggered execution,
  - whether the current request was fresh or resume-oriented,
  - which context snapshot was active.

This is a visibility upgrade, not a control-plane rewrite.

### Exit Criteria For Goal Mode

Phase 3 is detailed enough for goal-mode execution only when all of the following are true:

- the exact new package boundary is documented,
- the new objects are named and scoped,
- the first integration seams into CLI and execution runtime are identified,
- test slices are separated into unit coverage and regression coverage,
- explicit non-goals prevent accidental drift into Phase 4 runtime implementation.

### Recommended Goal Breakdown

If Phase 3 is run through goal mode, it should be pursued as one scoped goal with the following internal order:

1. create session models and serialization helpers,
2. add the compatibility `SessionRuntime`,
3. thread session metadata through execution requests/results,
4. expose session summaries to existing governance surfaces,
5. run targeted regression coverage.

## Phase 4: Coding Execution Runtime MVP

### Goal

Build the first non-legacy execution runtime that can complete a bounded coding task through repository exploration, editing, validation, and minimal retry handling.

### Scope

- add `RepoExplorer`,
- add `ContextBuilder`,
- add `EditExecutor`,
- add `CommandRunner`,
- add initial `VerifyLoop`,
- implement one concrete `CodingAgentExecutionRuntime`,
- keep `LegacyExecutionRuntime` as fallback.

### Out Of Scope

- advanced branching search,
- multi-agent subtask execution,
- UI productization of every runtime event.

### Acceptance Criteria

- a coding task can execute through the new runtime instead of legacy,
- the runtime can inspect repo context before editing,
- the runtime can run at least targeted verification after edits,
- the CLI can select between `legacy` and `coding_agent` runtime modes,
- compatibility paths still remain available.

### Suggested Tests

```bash
pytest tests/test_cli.py tests/test_control_plane.py tests/test_ui_service.py -q
```

## Phase 5: Verification And Repair Loop

### Goal

Upgrade the MVP runtime into a real coding loop that reacts to command failures, test failures, and patch mismatches rather than stopping at first-pass execution.

### Scope

- structured verification results,
- repair/retry policy,
- bounded retry budget,
- execution-memory recording for attempted fixes,
- recovery recommendation integration with governance.

### Acceptance Criteria

- failed execution attempts can trigger bounded repair,
- verification artifacts are captured structurally,
- recovery surfaces explain why a run stopped or retried,
- operator summaries expose execution attempts and repair outcomes.

### Suggested Tests

```bash
pytest tests/test_control_plane.py tests/test_ui_service.py tests/test_cli.py -q
```

## Phase 6: Governance And Execution Convergence

### Goal

Make the new runtime a first-class citizen of the governance plane so approval, evidence, recovery, and operator tooling work equally well for the coding-agent runtime and the legacy runtime.

### Scope

- execution event schema normalization,
- evidence integration,
- recovery summary integration,
- runtime health reporting for the new runtime,
- approval and gating surfaces for coding-agent strategies.

### Acceptance Criteria

- control-plane summaries reflect the new runtime,
- recovery and evidence pipelines accept new execution artifacts,
- operator UI and CLI can explain both runtime modes consistently.

### Suggested Tests

```bash
pytest tests/test_control_plane.py tests/test_ui_service.py tests/test_docs_process.py -q
```

## Phase 7: Execution Closure And Task Completion

### Goal

Upgrade the current early governed `coding_agent` runtime into a fuller task-completing execution runtime that can continue iterating until the bounded task is done or explicitly blocked.

### Scope

- deepen the current edit/apply/verify path into a more explicit step-loop kernel,
- strengthen post-edit verification and recovery behavior,
- add bounded completion-loop state that distinguishes:
  - planned edits
  - applied edits
  - verification after edits
  - blocked completion states
- improve context compression and execution-state reuse across longer tasks,
- unify resume-oriented runtime contracts so future runtime variants share the same interruption model,
- preserve the governance/control-plane truth while exposing stronger execution provenance.

### Acceptance Criteria

- the `coding_agent` runtime can continue from its current governed edit path into a clearer step-oriented completion loop,
- execution results continue to distinguish proposed, applied, verified, and blocked work,
- verification and recovery behavior remain explicit after applied edits,
- blocked states explain whether failure happened before or after edit application,
- execution state and artifact references support stronger long-horizon continuation,
- governance/operator summaries remain consistent with the stronger execution loop.

### Suggested Tests

```bash
pytest tests/test_coding_agent_runtime.py tests/test_cli.py tests/test_control_plane.py tests/test_ui_service.py -q
```

## Phase 8: Clarify Value Measurement

### Goal

Verify whether adaptive clarify actually improves coding-agent performance, especially for ambiguous or risky tasks.

### Scope

- define evaluation slices,
- compare:
  - `direct`
  - `light_intake`
  - `adaptive_clarify`
- track:
  - success rate,
  - verification pass rate,
  - retry count,
  - token cost,
  - step count,
  - human-escalation rate.

### Acceptance Criteria

- the repository contains a documented evaluation protocol,
- there is evidence for where clarify helps,
- clarify remains an explicit policy decision rather than a superstition.

### Entry Criteria

Phase 8 should not begin until Phase 7 is complete enough that the repository has a genuine task-completing coding-agent runtime. Otherwise the clarify experiment would mostly measure runtime incompleteness rather than intake-policy value.

## Phase 9: Product Packaging And Portfolio Readiness

### Goal

Package the project as a coherent coding-agent system suitable for demo, portfolio use, and internship discussion.

### Scope

- architecture diagrams,
- standard demo scenarios,
- runtime comparison story,
- project narrative refresh,
- concise technical summary of the system’s differentiators.

### Acceptance Criteria

- a new reader can understand the project in under two minutes,
- the coding-agent architecture can be demonstrated through one or two reproducible workflows,
- the project story clearly distinguishes control plane, strategy layer, and execution runtime.

## Execution Protocol

Each phase should follow the same execution protocol:

1. write or update a phase plan under `docs/architecture/` or `docs/process/`,
2. define scope and non-goals,
3. implement only the current phase,
4. run targeted tests for the current phase,
5. update architecture docs when boundaries materially change,
6. run full `pytest` only at major convergence points,
7. do not introduce a second state source outside control-plane artifacts.

## Completion Bar

This master plan is complete when:

- the system has a real coding-agent execution runtime,
- that runtime can actually complete a bounded coding task through edit application and verification,
- task routing and clarify are adaptive rather than hardwired,
- strategy selection is explicit and no longer fused into rigid template decomposition,
- session semantics are durable and resume-aware,
- governance remains the system of record,
- legacy workflow execution still exists only as a compatibility mode rather than the architectural center.
