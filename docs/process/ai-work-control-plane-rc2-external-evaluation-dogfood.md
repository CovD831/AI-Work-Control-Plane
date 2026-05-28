# AI Work Control Plane RC2 External Evaluation And Dogfood

## Goal

Validate sealed tag `v1.0.0-rc.2` outside the working repository and decide whether it can proceed toward final polish.

## External Clone

- Clone path: `/private/tmp/agent-orchestrator-rc2-eval-20260528`
- Tag: `v1.0.0-rc.2`
- Resolved commit: `45051c98760823749fa5574ed72a6d168fbe2d06`

## Verification Results

- `team setup --runtime command --format json`: exited 0.
- Fresh clone setup reported `release_readiness.ready: true`, package version `1.0.0rc2`, provider evidence summary format `agent_orchestrator.provider_evidence_summary.v1`, and `rc_blocking: false`.
- Fresh clone runtime measurement reported `measurement_status: unavailable` because no job history existed; this matched the documented boundary and did not block readiness.
- `team workspace-status --format json`: exited 0 with `agent_orchestrator.workspace_index.v1` and provider evidence summary format `agent_orchestrator.provider_evidence_summary.v1`.
- `team evidence-gates --format json`: exited 0 with `agent_orchestrator.evidence_bundle.v1`, status `ready`, and provider evidence summary format `agent_orchestrator.provider_evidence_summary.v1`.
- `team check-compliance`: exited 0 with status `passed`, `blocking: false`.

## Dogfood Results

- README-governed workflow dogfood exposed a release-blocking documentation friction: the quickstart jumped from `team next` to `team approve`.
- A fresh intake session reports primary action `mark_draft_ready`; the working command chain is `team draft-ready`, `team submit-review`, `team approve`, `team execute`, then `team inspect-execution`.
- After using the correct chain, the workflow executed successfully and linked execution run `run-4b6de1ee`.
- Fake Codex pilot job evidence was consumed by both workspace status and evidence gates with `provider_owned_ref_count: 1`, `codex_exec_json_job_count: 1`, `codex_json_event_count: 2`, and `session_ownership_claim: provider_owned`.

## Decision

`v1.0.0-rc.2` is not promoted because the README quickstart would lead an operator into an avoidable failed command.

Prepare `v1.0.0-rc.3` as a documentation-blocker fix only. No product scope expansion is required.
