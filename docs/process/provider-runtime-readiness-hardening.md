# Provider / Runtime Readiness Hardening

This goal hardens provider/runtime diagnosis for the native product surface. It does not create a provider marketplace, plugin ecosystem, public release, or modify local proxy/agent configuration.

## Stable Operator Entry

Use:

```bash
agent-orchestrator product diagnose
agent-orchestrator product posture
```

The pretty output is intended to be enough for an operator to decide readiness without reading raw JSON.

## Readiness Matrix

`agent_orchestrator.runtime_readiness_matrix.v1` covers:

- `mock` local fallback
- provider CLI runtimes: `codex`, `claude`
- direct API readiness: `direct_api_codex`, `direct_api_claude`

Each row records:

- command availability
- auth/config status
- available/degraded mode
- fallback runtime
- redaction-safe fix hint
- smoke command

## Release Candidate Verdict

The setup diagnosis exposes:

- `release_candidate_ready_with_external_cli`
- `release_candidate_ready_with_mock_only`
- `not_release_candidate_ready`

`install_release_candidate_ready=true` means the current product can proceed with local install/smoke validation using at least the mock fallback, and optionally external CLI runtimes when available.

## Redaction Safety

The readiness surface reports only availability, command names, detail strings, and environment variable names such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. It must not print secret values.

## Fix Plan and Smoke Commands

`product diagnose` includes:

- `fix_plan` for degraded runtimes
- `smoke_commands` to re-check after fixes
- mock fallback command for product smoke

## Cross-Surface Projection

The runtime readiness verdict is consumed by:

- `product diagnose` pretty output
- `product posture`
- `native_product_ux` in DashboardService
- `native_product_ux` in evidence bundle
