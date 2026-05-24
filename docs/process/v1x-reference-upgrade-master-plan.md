# v1.x Reference Upgrade Master Plan

## Purpose

This plan turns targeted lessons from local reference projects into staged upgrades for Agent Orchestrator.

The goal is not to become a bridge product, session manager, or plugin marketplace. The goal is to strengthen the existing product shape:

- Planning Governance Layer
- Execution Strategy Layer
- Documentation / Evidence / Console operations

All implementation work remains mapped to the repository's three Chinese implementation layers:

- `决策核心层`
- `执行拓扑层`
- `Provider / Runtime 层`

## Execution Protocol

- Each implementation stage must start by updating or appending a stage plan in this document.
- During a stage, run only targeted tests for the touched subsystem.
- When targeted tests pass, continue directly to the next stage without waiting for additional confirmation.
- Run the full test suite and full compliance gate only at the final convergence stage.
- Do not pull additional external repositories unless a stage explicitly needs source-level comparison beyond the already cloned local references.
- Preserve current public CLI behavior unless a stage explicitly documents the new interface.

## Reference Project Advantage Matrix

| Reference project | Strength to borrow | Local product landing zone | Layer mapping | Boundary |
| --- | --- | --- | --- | --- |
| `research_repos/codex-orchestrator` | Background tmux jobs, `status/capture/send/watch/attach`, durable job metadata, output capture, codebase map injection | Job runtime ergonomics, operator console job cards, terminal refs, log excerpts, context-map prompt support | 执行拓扑层 + Provider / Runtime 层 | Borrow lifecycle and observability ideas, not a full session-manager product |
| `research_repos/codex-plugin-cc` | Plugin bundle structure, install/update/uninstall scripts, semantic-version alignment, honest limitation reporting | Packaging docs, setup diagnostics, version/readiness checks, release readiness checklist | Provider / Runtime 层 | Borrow distribution discipline, not host-specific plugin assumptions |
| `research_repos/cc-plugin-codex` | Reverse companion plugin, Codex-native skill bundle, install verification, explicit unavailable hook limitation | Cross-provider readiness, setup command language, limitation sections in docs | Provider / Runtime 层 | Borrow clarity around degraded capability, not runtime-specific hooks |
| OpenAI `codex-plugin-cc` pattern represented by local plugin docs | Productized `review`, `adversarial-review`, `rescue`, `status`, `result`, `cancel`, `setup` verbs | Standard action taxonomy for team sessions, direct job commands, review/rescue gates | 决策核心层 + 执行拓扑层 | Borrow action grammar and UX, keep local governance-first semantics |
| Current Agent Orchestrator | Persisted plan sessions, adversarial gap closure, approved-plan execution contract, compliance and evidence reports | Unique product core that reference projects do not replace | 决策核心层 | Keep as differentiator and avoid reducing the project to runtime wrappers |

## Frozen Product Boundaries

In scope:

- Stronger job lifecycle observability and recovery signals.
- Standard review/rescue/setup/status/result/cancel action semantics.
- Context maps and documentation sync that help agents resume quickly.
- Packaging and setup diagnostics that honestly report unavailable providers or hooks.
- Evidence reports that show governance and execution benefits.

Out of scope:

- Replacing tmux, Codex CLI, Claude Code, or provider-native session systems.
- Becoming a standalone plugin marketplace.
- Making the UI the primary product surface; CLI remains first-class.
- Pulling broad external dependencies to imitate reference projects.

## Staged Upgrade Track

### Stage 0: Reference Alignment And Baseline Freeze

Goal:

- Establish this matrix and freeze boundaries before feature work.
- Confirm current targeted test baseline.

Implementation changes:

- Add this plan as the reference upgrade master plan.
- Link the plan from process/roadmap docs where appropriate.
- Record that local references are sufficient unless a later phase requires deeper comparison.

Targeted test:

- `pytest tests/test_jobs.py tests/test_tmux_runtime.py tests/test_ui_service.py tests/test_ui_server.py tests/test_evidence.py tests/test_cli.py -q`

Pass criteria:

- Targeted baseline passes.
- Plan clearly maps borrowed ideas to local layers and boundaries.

### Stage 1: Job Operations And Observability

Goal:

- Borrow the useful job lifecycle ergonomics from `codex-orchestrator` without becoming a full session manager.

Implementation changes:

- Standardize job metadata for terminal refs, attach availability, last seen time, and log excerpts.
- Ensure send/cancel operations expose accepted, unsupported, missing, unavailable, and terminal outcomes.
- Surface those fields consistently in CLI and Console job cards.

Targeted test:

- `pytest tests/test_jobs.py tests/test_tmux_runtime.py tests/test_ui_service.py tests/test_ui_server.py tests/test_cli.py -q`

Pass criteria:

- Job commands and UI payloads expose stable lifecycle/operation signals.
- Mock/file defaults remain stable.

### Stage 2: Review / Rescue / Setup Action Grammar

Goal:

- Turn reference plugin verbs into a local, governance-first action grammar.

Implementation changes:

- Normalize operator-facing actions around review, adversarial review, rescue, status, result, cancel, and setup/readiness.
- Keep approved-plan and required-gap gates authoritative.
- Add setup/readiness output that reports provider limitations honestly.

Targeted test:

- `pytest tests/test_actions.py tests/test_team.py tests/test_cli.py tests/test_command.py -q`

Pass criteria:

- Action availability remains status-aware.
- Readiness/setup output distinguishes available, fallback, unsupported, and unavailable states.

### Stage 3: Context Map And Documentation Recovery

Goal:

- Borrow `CODEBASE_MAP`-style context recovery while preserving existing root-map/module-manifest/header contracts.

Implementation changes:

- Make canonical docs explain which context artifact to use for agent orientation.
- Add or refresh a concise codebase navigation artifact if existing root/module docs are insufficient.
- Keep document refresh and compliance commands as the source of truth.

Targeted test:

- `pytest tests/test_planning_support.py tests/test_docs_process.py tests/test_cli.py -q`

Pass criteria:

- Canonical docs refresh cleanly.
- Compliance can detect stale or missing context docs without noisy broad rewrites.

### Stage 4: Packaging, Setup, And Version Discipline

Goal:

- Borrow plugin-repo install/update/version discipline without turning this repository into a plugin product.

Implementation changes:

- Document local install/update/setup expectations.
- Add setup diagnostics or readiness summaries for provider/runtime dependencies if not already covered.
- Add a release-readiness checklist covering version sync, tests, evidence, and compliance.
- Keep the CLI honest about what it can install, update, and verify locally.

Targeted test:

- `pytest tests/test_cli.py tests/test_command.py tests/test_docs_process.py -q`

Pass criteria:

- Setup/readiness documentation matches CLI behavior.
- Version/release checklist is explicit and honest about limitations.
### Stage 5: Evidence And Product Explanation

Goal:

- Prove why governance-first orchestration is useful compared with fixed-template workflows.

Implementation changes:

- Strengthen evidence cases and trend reports around planning quality, rescue quality, and runtime limitations.
- Update README/runbook with the reference-informed workflow story.

Targeted test:

- `pytest tests/test_evidence.py tests/test_cli.py tests/test_docs_process.py -q`

Pass criteria:

- Evidence reports remain schema-compatible.
- Docs explain advantages and limitations without overstating provider/runtime completeness.

### Stage 6: Final Convergence Gate

Goal:

- Verify the full repository and synchronize process docs.

Final tests:

- `pytest`
- `PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance`
- `git status --short`

Pass criteria:

- Full tests pass.
- Compliance passes.
- Working tree only contains intended staged upgrade changes.
