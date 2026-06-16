# Native Agent Coverage Expansion Goal Closure Audit

## Purpose

This document audits the current repository state against:

- [goal-mode-native-agent-coverage-expansion.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-native-agent-coverage-expansion.md)

It is intentionally stricter than a progress summary.

The only question it answers is:

Can the current repository already prove the exact stopping condition of the coverage-expansion goal?

## Audit Scope

This audit evaluates:

1. `P0 Native Default Coverage Expansion`
2. `P1 Comparative Benchmark And Coverage Evidence`
3. `P2 Recovery Breadth Hardening`
4. `P3 Learning Asset Consumption Loop`
5. The global stopping criteria
6. The completion-standard bullets

Status vocabulary used in this audit:

- `strongly evidenced`
- `weakly evidenced`
- `incomplete`
- `contradicted`

## Primary Evidence

Primary implementation evidence:

- [src/agent_orchestrator/intake/models.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/intake/models.py)
- [src/agent_orchestrator/intake/task_router.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/intake/task_router.py)
- [src/agent_orchestrator/execution/coding_agent_runtime.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/execution/coding_agent_runtime.py)
- [src/agent_orchestrator/evidence.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/evidence.py)
- [src/agent_orchestrator/planning.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/planning.py)
- [src/agent_orchestrator/control_plane_workspace.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/control_plane_workspace.py)
- [src/agent_orchestrator/control_plane_artifacts.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/control_plane_artifacts.py)
- [src/agent_orchestrator/ui_service.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/ui_service.py)
- [src/agent_orchestrator/cli_presenters.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/cli_presenters.py)

Primary verification evidence:

- [tests/test_task_router.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_task_router.py)
- [tests/test_memory.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_memory.py)
- [tests/test_coding_agent_runtime.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_coding_agent_runtime.py)
- [tests/test_control_plane.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_control_plane.py)
- [tests/test_ui_service.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_ui_service.py)
- [tests/test_strategy_planner.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_strategy_planner.py)
- [tests/test_cli_presenters.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_cli_presenters.py)
- [tests/test_evidence.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_evidence.py)
- [tests/test_team.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_team.py)

Goal framing references:

- [docs/process/goal-mode-native-agent-coverage-expansion-summary.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-native-agent-coverage-expansion-summary.md)
- [docs/process/native-coding-agent-dogfood-evidence.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/native-coding-agent-dogfood-evidence.md)

## Requirement Audit

### P0 Native Default Coverage Expansion

Status: `strongly evidenced`

Why:

- the router now projects three native coverage classes: `bounded_internal_repo_task`, `investigation_to_edit_verify`, and `multi_file_helper_or_compliance_repair`.
- two of those classes are the new goal-specific expansions: learning-backed investigation followthrough and bounded multi-file helper or compliance repair.
- route results now preserve `native_coverage_class`, `selection_reason`, `fallback_reason_code`, and `handoff_reason_code`, so native defaultability and governed escape hatches stay visible together.
- runtime, workspace, UI, CLI, and evidence layers all project the selected native coverage class instead of leaving it implicit inside router code.

Primary proof:

- [tests/test_task_router.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_task_router.py): `test_task_router_routes_investigation_requests_to_native_when_learning_assets_exist`
- [tests/test_task_router.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_task_router.py): `test_task_router_routes_investigation_requests_to_governed_fallback_without_learning_assets`
- [tests/test_task_router.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_task_router.py): `test_task_router_routes_multi_file_helper_or_compliance_repair_to_native`
- [tests/test_coding_agent_runtime.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_coding_agent_runtime.py)
- [tests/test_control_plane.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_control_plane.py): `test_workspace_index_records_execution_artifact_summary_from_coding_runtime`

Goal-criteria mapping:

- at least two new real task classes enter the native path by default: evidenced
- task router and runtime main path carry those classes: evidenced
- external fallback and handoff remain explicit and governed: evidenced
- user-visible surfaces show why the task entered native: evidenced
- tests prove the behavior rather than only documenting it: evidenced

Residual risk:

- the new classes are still bounded and evidence-oriented rather than broad open-ended engineering categories, which is acceptable for this goal.

### P1 Comparative Benchmark And Coverage Evidence

Status: `strongly evidenced`

Why:

- the benchmark layer now fixes a reusable bundle instead of a single happy-path demo.
- comparative summaries now report native vs external deltas for success, blocked, recovery, verification cost, and human intervention.
- the comparative benchmark payload is shared across workspace index, UI/CLI summaries, runtime payload, and evidence report surfaces.
- repo-task acceptance capture now uses native-only execution where required and preserves governed fallback semantics for non-native cases.

Primary proof:

- [tests/test_evidence.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_evidence.py)
- [tests/test_control_plane.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_control_plane.py)
- [tests/test_cli_presenters.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_cli_presenters.py)
- [src/agent_orchestrator/evidence.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/evidence.py)
- [src/agent_orchestrator/control_plane_workspace.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/control_plane_workspace.py)

Goal-criteria mapping:

- stable multi-task benchmark bundle exists: evidenced
- native and external are compared on multiple governance dimensions: evidenced
- benchmark includes blocked, recovery, and intervention semantics: evidenced
- benchmark is consumed by multiple evidence surfaces: evidenced
- automated tests pin the bundle behavior: evidenced

Residual risk:

- verification cost is still partially placeholder-based at provider-cost granularity, but measured local verification duration and case counting are already included, which is sufficient for this goal's comparative scope.

### P2 Recovery Breadth Hardening

Status: `strongly evidenced`

Why:

- `exploration_ambiguity_or_scope_drift` is now treated as a first-class recovery shape rather than an incidental string.
- recovery semantics formally project `continue_allowed`, `scope_realign_required`, `fallback_allowed`, `handoff_allowed`, `remaining_budget_preserved`, and `resume_continuity_required`.
- CLI and team status now show those semantics so the operator can distinguish continue, inspect, realign, fallback, and handoff outcomes.
- the new recovery shape extends breadth without removing the earlier governed repair, retry, pause, and block semantics.

Primary proof:

- [tests/test_team.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_team.py): `test_team_status_reports_scope_realign_recovery_semantics_for_ambiguity_drift`
- [tests/test_cli_presenters.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_cli_presenters.py)
- [src/agent_orchestrator/planning.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/planning.py)
- [docs/process/goal-mode-native-agent-coverage-expansion-summary.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-native-agent-coverage-expansion-summary.md)

Goal-criteria mapping:

- at least one new failure shape is formally added: evidenced
- continue, block, fallback, and handoff boundaries are explicit: evidenced
- remaining budget and resume continuity are preserved as first-class fields: evidenced
- governed external escape paths remain available without becoming implicit default rescue: evidenced
- code and tests, not just docs, define the new recovery breadth: evidenced

Residual risk:

- current breadth is intentionally narrow to one added failure family rather than a large failure taxonomy, which matches the goal boundary.

### P3 Learning Asset Consumption Loop

Status: `strongly evidenced`

Why:

- router decisions now read `native_trajectory` and `native_learning` records directly from `MemoryStore`.
- learning consumption is not only internal; it is projected via `learning_consumed` and `learning_source_count` into runtime and control-plane artifacts.
- the learning-backed investigation route is a concrete `Trajectory -> Router decision` example that changes native-path treatment when evidence exists.
- the implementation distinguishes reusable native learning hints from unconditional long-term policy, because route selection still keeps explicit fallback and risk boundaries.

Primary proof:

- [tests/test_memory.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_memory.py)
- [tests/test_task_router.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_task_router.py)
- [src/agent_orchestrator/intake/task_router.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/intake/task_router.py)
- [src/agent_orchestrator/ui_service.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/ui_service.py)

Goal-criteria mapping:

- router consumes learning assets: evidenced
- trajectory-backed decision sample exists and is regression-tested: evidenced
- write/read boundaries remain distinct enough to avoid turning all memory into permanent policy: evidenced
- learning consumption affects route choice and explanation surfaces: evidenced
- stronger autonomous optimization remains out of scope: evidenced by goal docs and current implementation scope

Residual risk:

- planner-side learning consumption is still lighter than router-side consumption, but the goal only requires one real decision layer to consume the asset.

## Completion Standard Audit

### 1. Native default path covers at least three real repository task classes, with two newly added in this goal

Status: `strongly evidenced`

Why:

- `bounded_internal_repo_task` remains the baseline proven class.
- `investigation_to_edit_verify` and `multi_file_helper_or_compliance_repair` are now explicit additional native coverage classes and are surfaced beyond the router.

Proof:

- [tests/test_task_router.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_task_router.py)
- [docs/process/goal-mode-native-agent-coverage-expansion-summary.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-native-agent-coverage-expansion-summary.md)

### 2. Stable comparative acceptance and benchmark bundle exists

Status: `strongly evidenced`

Why:

- comparative benchmark summary is built from stable capture logic and pinned by tests.
- native-only repo acceptance capture and mixed native/external comparative cases coexist inside the same governed evidence bundle.

Proof:

- [tests/test_evidence.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_evidence.py)
- [src/agent_orchestrator/evidence.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/evidence.py)

### 3. Learning assets are consumed by a real routing or planning decision

Status: `strongly evidenced`

Why:

- `TaskRouter` changes treatment of investigation requests when trajectory or native-learning evidence is present.

Proof:

- [tests/test_memory.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_memory.py)
- [tests/test_task_router.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_task_router.py)

### 4. External agent remains hot-pluggable and fallback or handoff stays governed

Status: `strongly evidenced`

Why:

- route results still emit explicit `fallback_reason_code` and `handoff_reason_code`.
- comparative evidence explicitly asserts `governed_fallback_hot_plug_preserved`.
- benchmark capture no longer forces native execution onto non-native scenarios, preserving the governed external path.

Proof:

- [tests/test_evidence.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_evidence.py)
- [src/agent_orchestrator/intake/task_router.py](/Users/abab/Desktop/AI-Work-Control-Plane/src/agent_orchestrator/intake/task_router.py)

### 5. Documentation, evidence, workspace index, runtime or session state, and UI or CLI summary share consistent evidence

Status: `strongly evidenced`

Why:

- the same coverage, benchmark, and learning-consumption facts are projected into runtime payload, workspace index, UI execution summary, CLI execution summary, and docs assertions.
- `comparative_benchmark.shared_evidence_surface` and `execution_fact_chain.shared_surface_refs` make those shared surfaces explicit instead of implied.

Proof:

- [tests/test_control_plane.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_control_plane.py)
- [tests/test_ui_service.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_ui_service.py)
- [tests/test_cli_presenters.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_cli_presenters.py)
- [tests/test_docs_process.py](/Users/abab/Desktop/AI-Work-Control-Plane/tests/test_docs_process.py)

## Overall Conclusion

Current conclusion: `complete for this goal`

Why:

1. `P0`, `P1`, `P2`, and `P3` all have implementation evidence, automated verification, and user-visible projections.
2. native coverage now spans three repository-task classes, including two new classes added by this goal.
3. comparative benchmark evidence is no longer a one-off narrative artifact; it is a stable shared bundle with native and external comparison fields.
4. learning assets are consumed in a real router decision, not merely stored.
5. external fallback and handoff remain governed and hot-pluggable rather than being removed to make native numbers look better.

## What This Goal Does Not Claim

- it does not claim native now covers all repository-task families.
- it does not claim benchmarking has become a full standalone product.
- it does not claim planner-side learning is already a comprehensive automatic optimization loop.

Those are explicitly left for later goals and do not block completion of this one.

## Decision Use

If the question is:

Can the repository now prove that native defaultability has expanded beyond a single bounded task class, with comparative benchmark evidence, broader recovery semantics, and real learning-asset consumption?

The answer is:

`yes`
