# AI Work Control Plane Provider Runtime Bridge Evaluation Phase 2: Ownership Boundary

## Goal

Define field-level ownership before drafting a provider runtime adapter contract.

The control plane should make provider runtimes inspectable without absorbing provider-owned state. This document separates owned facts, observed facts, provider-owned facts, placeholders, and unavailable facts.

## Ownership Categories

### Agent Orchestrator Owned

These fields are created or interpreted by Agent Orchestrator and can be used in stable local contracts:

| Field | Owner | Notes |
| --- | --- | --- |
| `job_id` | Agent Orchestrator | Local durable job identity. |
| `task_id` | Agent Orchestrator | Local task/work-unit identity. |
| `provider` | Agent Orchestrator | Local label such as `codex`, `claude`, or `mock`. |
| `kind` | Agent Orchestrator | Local job kind: research, implementation, review, adversarial review, rescue. |
| `runtime_mode` | Agent Orchestrator | Local execution mode: `cli_inherit`, `cli_isolated`, `direct_api`. |
| `cwd` | Agent Orchestrator | Requested working directory. |
| `command` | Agent Orchestrator | Command argv built by the adapter. |
| `created_at` / `started_at` / `completed_at` | Agent Orchestrator | Local lifecycle timestamps. |
| `status` / `phase` | Agent Orchestrator | Local lifecycle interpretation. |
| `stdout` / `stderr` / `raw_output` | Agent Orchestrator | Captured local process output. |
| `exit_code` | Agent Orchestrator | Local process exit code when available. |
| `runtime_measurement` | Agent Orchestrator | Local measured/placeholder/unavailable classification. |
| `operation_receipts` | Agent Orchestrator | Local records of send/cancel/terminal operations. |
| `degraded_reason` | Agent Orchestrator | Local explanation assembled from errors, fallback, provider health, or missing capability. |

### Observed Provider Facts

These fields can be recorded when a runtime exposes them, but Agent Orchestrator must not treat them as owned:

| Field | Status | Notes |
| --- | --- | --- |
| `session_id` | observed reference | May come from a local process session or provider CLI option. It is not a continuity guarantee. |
| `thread_id` | observed reference | Same as `session_id`; safe as a pointer, not ownership. |
| provider CLI version | observed | Useful for evidence, not a stable provider API contract. |
| provider health | observed | PATH/auth/config dependent. |
| provider structured output | observed | JSON/JSONL shapes can drift by provider version. |
| provider resume command | observed | CLI availability does not prove adapter-owned continuation semantics. |
| provider background agent list | observed | Claude `agents --json` is inspectable but not yet integrated. |

### Provider-Owned Facts

These fields remain provider-owned unless a future adapter proves otherwise:

| Field | Owner | Notes |
| --- | --- | --- |
| model internal state | provider | Never owned by Agent Orchestrator. |
| provider-native conversation continuity | provider | Can be referenced only through provider-supported resume/session features. |
| provider-native tool execution semantics | provider | Agent Orchestrator records local permissions but cannot redefine provider behavior. |
| provider-native send/cancel guarantees | provider | Current send/cancel are local operation receipts unless proven by a pilot. |
| token usage | provider | Placeholder unless provider reports it. |
| cost | provider | Placeholder unless provider reports it. |
| remote/cloud task state | provider | Out of scope unless a future adapter adds an explicit contract. |

### Placeholder Fields

These fields may exist in payloads but must remain explicitly placeholder without runtime-reported data:

- `usage_cost.input_tokens`
- `usage_cost.output_tokens`
- `usage_cost.estimated_cost_usd`
- provider-native session liveness after local process restart
- direct API token/cost for fakeable local clients

### Unavailable Fields

These fields should be reported as unavailable rather than inferred:

- provider-native send support for non-interactive Codex CLI
- provider-native cancel support for non-interactive Codex CLI
- provider-native send support for non-interactive Claude `-p` outside stream-json or agent flows
- durable provider session ownership by Agent Orchestrator
- provider cost when no runtime-reported value is present

## Adapter Boundary Rule

A future `ProviderRuntimeAdapter` may expose capability metadata, but capabilities must distinguish:

```text
supported_by_adapter
observed_from_provider
records_only
provider_owned
placeholder
unavailable
```

This keeps the control plane honest when a provider CLI exposes a command but the local adapter has not integrated it.

## Runtime Measurement Rule

Runtime measurement stays local:

```text
command_started_at + command_completed_at + exit_code => measured
started_at without terminal facts => placeholder
no local job facts => unavailable
```

Usage/cost is independent:

```text
provider-reported usage/cost => measured
missing provider usage/cost => placeholder
```

## Operation Receipt Rule

`RuntimeOperationReceipt` records operator/runtime interaction. It does not prove that a provider-native conversation received, applied, or persisted the operation unless a future adapter can cite provider evidence.

Current safe receipt meanings:

- `accepted`: accepted by local runtime path.
- `already_terminal`: local job was terminal.
- `session_missing`: no live local session was attached.
- `unsupported`: adapter/runtime does not expose the operation.
- `auth_required`: provider auth blocked the operation.
- `provider_unavailable`: provider binary/service was unavailable.

## Phase 2 Result

The next adapter contract should use these ownership categories directly rather than flattening everything into boolean support.

