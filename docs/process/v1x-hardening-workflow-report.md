# v1.x Hardening Workflow Report

## Phase 1 Real Workflow Regression

- baseline commit: `563574d Implement v1.x reference-informed upgrade plan`
- workflow 1: `Harden CLI setup summary for release readiness` completed through start/next/execute/inspect-execution
- workflow 2: `Build plan with followup checklist and recovery guidance` exposed a runbook wording friction when required gaps were already closed but status remained `needs_revision`
- fix: runbook now says to approve the reviewed plan instead of saying approval closes required gaps

## Console Visibility

- Console service/API targeted tests remain the validation path for session detail, governance, runbook, jobs, and stream payloads
- Console remains operator visibility, not a required execution entrypoint

## Phase 3 Runtime / Provider Validation

- validation date: 2026-05-24
- candidate smoke date: 2026-05-25
- CLI health path: `PYTHONPATH=src python -m agent_orchestrator.cli health --refresh --format json`
  - verified live provider snapshot contains `codex`, `claude`, and `mock`
  - current local result: `codex` available with `codex-cli 0.133.0-alpha.1`; `claude` available with `2.1.150 (Claude Code)`; `mock` always available
  - equivalent team readiness path: `PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json` refreshes command-runtime health and reports provider states, doc sync, compliance, and release readiness
- unavailable-provider behavior: controlled PATH validation with `env PATH=/usr/bin:/bin PYTHONPATH=src /opt/anaconda3/bin/python -m agent_orchestrator.cli health --refresh --format json` returned `codex not found` with recommended fallback `claude`, `claude not found` with recommended fallback `codex`, and `mock` available
- command-runtime result handling: existing `tests/test_command.py` coverage verifies successful stdout/raw output/exit code capture, non-zero exit failure with stderr/error preservation, missing command and spawn/poll/finalize exceptions, Claude JSON envelope parsing, auth-prompt detection, and Codex command generation
- fallback coverage: existing `tests/test_team.py` coverage records reviewer fallback when Claude is unavailable, author fallback when Codex is unavailable, status fallback recovery fields, and retry-review consistency; a focused provider-health test now pins missing-binary fallback fields for `codex`/`claude`/`mock`
- send/cancel coverage and limitation:
  - `tests/test_command.py`, `tests/test_jobs.py`, and `tests/test_tmux_runtime.py` cover accepted send/cancel payloads, terminal `already_terminal` payloads, tmux send/cancel behavior, and readable failed/cancelled job results
  - v1.x command runtime still uses subprocess session handles, not a complete provider bridge/session manager; `send` records/normalizes follow-up metadata for the attached session abstraction and `cancel` terminates or marks the local session, but this is not a guarantee that Codex/Claude CLI support rich interactive follow-up delivery

## Friction Register

- CLI: approval-ready `needs_revision` sessions needed clearer runbook wording; fixed in hardening phase
- Console: no blocker found in current service/server payload tests
- Runtime: Phase 3 health, fallback, stdout/stderr/exit-code, and send/cancel behavior validated through CLI probes and focused tests; remaining limitation is lack of a full Codex/Claude bridge/session manager
- Docs/Evidence: deferred to evidence and release-candidate phases
