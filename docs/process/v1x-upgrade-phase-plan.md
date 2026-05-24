# v1.x Upgrade Phase Plan

## Execution Protocol

- Write or update this phase plan before starting each implementation phase.
- Run only targeted tests during phases 0-5.
- Continue directly to the next phase after targeted tests pass.
- Run the full test suite and compliance gate only in phase 6.
- Keep changes scoped to the v1.x upgrade plan and required documentation synchronization.

## Phase 0: Baseline And Repo Hygiene

Goal:

- Clean local macOS noise from the working tree.
- Establish the shared phase-plan document.
- Verify the current compliance gate before feature work begins.

Implementation changes:

- Add `.DS_Store` to `.gitignore`.
- Remove existing untracked `.DS_Store` files.
- Keep functional code unchanged.

Targeted test:

- `PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance`

Pass criteria:

- Compliance command exits successfully.
- `git status --short` no longer lists `.DS_Store` files.

## Phase 1: Provider / Runtime Health And Review Policy CLI

Goal:

- Surface local provider health in a richer, fallback-aware shape.
- Allow operators to choose a controlled review policy override without changing default behavior.
- Persist command-runtime health snapshots into run and team artifacts.

Implementation changes:

- Extend provider health payloads with binary and recommended fallback fields.
- Add `--review-policy auto|standard|adversarial|required-human` to direct and team execution entrypoints.
- Thread the review policy override into execution contract metadata while preserving `auto` defaults.
- Store provider health snapshots when `--runtime command` is selected.

Targeted test:

- `pytest tests/test_cli.py tests/test_orchestrator.py tests/test_team.py -q`

Pass criteria:

- Existing CLI and team tests pass.
- New assertions confirm health shape, review policy override metadata, and command-runtime health snapshots.

## Phase 2: Evidence Real Task Suites And Auto Reports

Goal:

- Make evidence capture usable from the CLI.
- Support real task case files in addition to built-in benchmark cases.
- Produce a markdown phase report from the existing JSON evidence schema.

Implementation changes:

- Add `evidence benchmark`, `evidence capture`, and `evidence report` CLI subcommands.
- Parse JSON case files with `label`, `requirement`, `scenario_type`, and `mode`.
- Keep the existing evidence payload schema compatible.
- Add a markdown report renderer for scenario aggregates and key signals.

Targeted test:

- `pytest tests/test_evidence.py tests/test_cli.py -q`

Pass criteria:

- Evidence JSON capture remains backward compatible.
- CLI commands write JSON and markdown outputs at requested paths.

## Phase 3: Agent Team Console Operator Upgrade

Goal:

- Make the local console a fuller operator surface for sessions, governance, provenance, events, messages, work graph, and jobs.
- Use existing FastAPI/static assets and preserve route compatibility.

Implementation changes:

- Enrich session list items with status, phase, primary action, linked run, and updated timestamp fields.
- Add dashboard detail payload sections for execution provenance, review policy, fallback snapshot, compliance snapshot, event timeline, message timeline, and work graph summary.
- Render the new sections in the static UI without adding dependencies.
- Wire job log/send/cancel controls to the existing API routes.

Targeted test:

- `pytest tests/test_ui_service.py tests/test_ui_server.py -q`

Pass criteria:

- Existing UI service/server tests pass.
- New assertions confirm operator summary fields and job controls are exposed.

## Phase 4: Hook / Doc Sync Repair Commands

Goal:

- Make hook changed-file collection safe for staged paths containing spaces.
- Add explicit CLI repair commands for canonical process docs and compliance inspection.

Implementation changes:

- Update repository-managed hook script to read staged filenames with NUL delimiters.
- Add `team refresh-docs` to write canonical root map, module manifest, and file header contract.
- Add `team repair-compliance` to refresh docs and return compliance status, required actions, warnings, and recommended commands.
- Preserve non-source header behavior; repair commands do not rewrite business source headers.

Targeted test:

- `pytest tests/test_planning_support.py tests/test_team.py tests/test_cli.py -q`

Pass criteria:

- Hook script handles space-containing staged paths.
- CLI repair commands output refreshed doc sync and compliance payloads.

## Phase 5: Runtime Session Ergonomics

Goal:

- Make command and tmux jobs easier to inspect and operate from CLI and UI.
- Keep mock defaults stable and avoid building a full session manager.

Implementation changes:

- Add job card/detail fields for terminal reference, attach availability, last log excerpt, and last seen timestamp.
- Print concise CLI summaries for `status`, `result`, `send`, and `cancel` before JSON payloads.
- Surface job log excerpts and controls in the console using existing routes.
- Preserve explainable fallback/unsupported provider state for unavailable real providers.

Targeted test:

- `pytest tests/test_tmux_runtime.py tests/test_ui_service.py tests/test_cli.py -q`

Pass criteria:

- Runtime tests pass.
- UI job cards expose ergonomic fields.
- CLI job commands emit readable summaries plus JSON payloads.

## Phase 6: Docs, Compatibility, And Final Gate

Goal:

- Document the v1.x upgrade surfaces and verify the whole repository.
- Refresh canonical process docs after module/header changes.

Implementation changes:

- Update README, roadmap/backlog, and operator runbook with v1.x provider health, review policy CLI, evidence reports, console upgrades, repair commands, and runtime controls.
- Refresh canonical process docs.
- Run full test suite and final compliance gate.

Final tests:

- `pytest`
- `PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance`
- `git status --short`

Pass criteria:

- Full tests pass.
- Compliance passes.
- Working tree only contains intended v1.x changes.
