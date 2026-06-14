# Native Coding Agent Dogfood Evidence

## Summary

This repository now has a pinned native coding-agent dogfood baseline for one bounded internal repository task class:

`bounded_internal_repo_task`

The task class is:

- local to this workspace,
- executed through `coding_agent` runtime mode,
- governed by control-plane artifacts,
- explicitly native-only rather than delegated to an external coding agent,
- evidence-backed across runtime, workspace index, runtime event stream, and UI execution summary surfaces.

It also now has a pinned long-horizon program-execution proof for one governed native multi-milestone workstream shape:

`multi_milestone_program_execution`

## Pinned Proof Chains

### Scenario A: Approval Pause -> Resume -> Complete

Keyword: `approval_pause_resume_complete`

Pinned chain:

```text
ExecutionRequest
  -> Context Select
  -> Explore / Edit / Verify step-loop
  -> Edit approval pause
  -> approval_resume
  -> Verify approval pause
  -> approval_resume
  -> Verification artifact
  -> Runtime Event Stream
  -> Workspace Index
  -> UI Execution Summary
```

Current proof:

- native runtime only: `true`
- external coding agent required: `false`
- closure status: `completed`
- artifact evidence: present
- runtime event evidence: present

### Scenario B: Verify Failure -> Exhausted Recovery -> Blocked

Keyword: `verify_failure_exhausted_recovery_block`

Pinned chain:

```text
Persisted failure state
  -> approval_resume
  -> Verify stage classification
  -> exhausted_recovery block
  -> Runtime Event Stream
  -> Recovery Timeline
  -> Workspace Index
  -> UI Execution Summary
```

Current proof:

- repair summary persisted with retry budget
- recovery action: `human_review`
- closure status: `blocked`
- control-plane recovery surfaces remain the source of truth

### Scenario C: Verify Failure -> Repair Resume -> Re-Verify Success

Keyword: `verify_failure_repair_resume_success`

Pinned chain:

```text
Persisted failure state
  -> approval_resume
  -> remaining retry budget applied
  -> verify retry
  -> repaired verification success
  -> verification artifact
  -> Runtime Event Stream
  -> Workspace Index
  -> UI Execution Summary
```

Current proof:

- repair continuity preserved through resume state
- re-verify succeeds natively
- closure status: `completed`
- artifact and runtime-event evidence remain visible after repair

### Scenario D: Explore -> Edit -> Verify -> Checkpoint -> Continue

Keyword: `multi_milestone_program_execution`

Pinned chain:

```text
Persisted program state
  -> explore milestone recorded
  -> edit milestone recorded
  -> verify milestone recorded
  -> checkpoint artifact
  -> continue_program recovery guidance
  -> Runtime Event Stream
  -> Recovery Recommendation
  -> Topology Snapshot
  -> Workspace Index
  -> UI Execution Summary
```

Current proof:

- multi-milestone program posture is preserved through runtime continuity
- checkpoint-ready continue guidance is visible in recovery surfaces
- topology, recovery, workspace, and UI share the same program contract vocabulary
- closure status: `completed`

## Evidence Surfaces

The pinned native dogfood baseline is currently visible through:

- `agent_orchestrator.native_task_proof.v1`
- `agent_orchestrator.native_runtime_closure.v1`
- `agent_orchestrator.native_repo_task_acceptance.v1`
- `agent_orchestrator.program_execution_proof.v1`
- `payload.artifact_summary`
- `payload.event_summary`
- `payload.resume_context`
- `agent_orchestrator.runtime_event_stream.v1`
- `agent_orchestrator.recovery_recommendation.v1`
- `agent_orchestrator.execution_topology_snapshot.v1`
- `agent_orchestrator.workspace_index.v1`
- UI `operator_summary.execution_runtime_summary`

The runtime-closure snapshot rolls the native proof into six explicit checks:

- native-only execution,
- stable step-loop,
- explicit context select plus structured observation,
- verify/repair/resume closure,
- control-plane state authority,
- auditable artifacts and visible recovery surfaces.

The stronger repo-task acceptance signal is now also part of the default dogfood-surface projection chain:

- runtime event stream must carry `native_repo_task_acceptance`,
- workspace index must carry `execution_artifact_summary.native_repo_task_acceptance`,
- UI execution summary must expose `repo_task_acceptance_ready`,
- operator summary now classifies closure strength as `runtime_closure_only` or `repo_task_acceptance_ready`.

The long-horizon program-execution signal is now also part of the default dogfood proof chain:

- runtime continuity must expose `program_posture`, `delegation_contract`, `program_continuity`, `milestone_verification`, and `operator_control`,
- recovery recommendation must expose the same program contract as a recovery-facing projection,
- topology snapshot must expose the same program contract as an execution-path projection,
- workspace index and UI execution summary must remain compatible with the same program vocabulary,
- comparative benchmark now tracks `same_program_contract_cases` and shared evidence surfaces including `recovery_recommendation` and `topology_snapshot`.

The current native-defaultability seal also adds explicit path-selection evidence:

- `default_path` identifies whether the task class defaults to `native` or `external`,
- `operating_boundary` records `native_preferred`, `external_preferred`, or `fallback_governed`,
- `selection_reason` is visible in runtime payloads and UI summaries,
- `handoff_reason_code` / `fallback_reason_code` make handoff and fallback governed rather than implicit.

The learning-loop foundation is now also externally visible:

- `SessionRuntime/trajectories` stores trajectory records per session,
- `MemoryStore` stores `native_trajectory` and `native_learning` records,
- `KnowledgeStore` stores curator-ready `lessons` and `skills` assets,
- the payload includes nudge-ready metadata for turning trajectory evidence into reusable assets.

The stronger repo-task acceptance snapshot is stricter:

- it expects real changed code under `src/agent_orchestrator/` or `ui_frontend/`,
- it expects verification command evidence,
- it expects operator-visible artifacts,
- and it expects repo-facing surface updates such as docs or compliance-visible changes.

The newer complex repo-task acceptance snapshot is stricter again:

- it expects multiple target paths rather than a single bounded edit,
- it expects multiple applied mutations across code and repo-facing surfaces,
- it expects verification over more than one code target,
- and it expects native exploration trace evidence from multiple exploration tools, such as `repo_map` or a `glob`/`search`/`read` chain.

Current native dogfood proves both the runtime/kernel closure layer and one multi-milestone native program-execution evidence chain. It should not be overread as full real repository task acceptance unless those stronger checks also pass.

## Boundary

This dogfood evidence does not claim:

- native closure for every task class,
- autonomous repair breadth for all failure kinds,
- external-agent parity for long-horizon coding strength,
- provider bridge completeness.

It does prove that the current repository can already demonstrate one governed native-only internal repository task class across success, blocked recovery, and repair-success chains without using OpenCode, Codex, or another external coding agent as the main executor.

It also proves that the current repository can demonstrate one governed native multi-milestone workstream shape with checkpoint/continue semantics and shared program-level evidence across runtime, recovery, topology, workspace, and UI projections.
