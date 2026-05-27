# AI Work Control Plane Provider Runtime Bridge Evaluation Phase 3: Adapter Contract Draft

## Goal

Draft the minimal `ProviderRuntimeAdapter` contract for a later implementation track.

This is a contract draft, not a provider bridge implementation. Its purpose is to make future Codex / Claude pilots additive to the existing control plane rather than a rewrite of `JobRuntime`, `ProviderSessionSnapshot`, or runtime measurement.

## Contract Shape

```python
class ProviderRuntimeAdapter(Protocol):
    runtime_id: str
    provider: str

    def capabilities(self) -> ProviderRuntimeCapabilities: ...
    def start(self, request: ProviderRuntimeStartRequest) -> ProviderRuntimeStartResult: ...
    def status(self, ref: ProviderSessionRef) -> ProviderRuntimeStatus: ...
    def result(self, ref: ProviderSessionRef) -> ProviderRuntimeResult: ...
    def send(self, ref: ProviderSessionRef, message: str) -> ProviderRuntimeOperationReceipt: ...
    def cancel(self, ref: ProviderSessionRef) -> ProviderRuntimeOperationReceipt: ...
```

The contract should sit below the existing `JobRuntime` surface. `JobRuntime` remains the durable local lifecycle API used by orchestration and control-plane surfaces.

## Capability Status Values

Every capability must report one of:

- `supported_by_adapter`: implemented and tested in the adapter.
- `observed_from_provider`: visible in provider CLI/API evidence but not integrated as an adapter guarantee.
- `records_only`: Agent Orchestrator records a local event but cannot prove provider-native behavior.
- `provider_owned`: provider controls the behavior; Agent Orchestrator can store references only.
- `placeholder`: field exists but has no trustworthy value yet.
- `unavailable`: not exposed or not supported in the current path.
- `unknown`: not evaluated.

Boolean capability flags are not enough. A future adapter must preserve these status values so release readiness can stay honest.

## Core Data Shapes

### ProviderRuntimeCapabilities

Stable fields:

- `format`: `agent_orchestrator.provider_runtime_capabilities.v1`
- `runtime_id`
- `provider`
- `start`
- `resume`
- `send`
- `cancel`
- `status`
- `result`
- `logs`
- `artifacts`
- `session_ref`
- `cwd`
- `exit_code`
- `structured_output`
- `usage_cost`
- `permission_model`
- `notes`
- `observed_from`

### ProviderSessionRef

Stable fields:

- `format`: `agent_orchestrator.provider_session_ref.v1`
- `job_id`
- `provider`
- `runtime_id`
- `session_id`
- `thread_id`
- `cwd`
- `pid`
- `command`
- `provider_owned`
- `continuation_guarantee`
- `created_at`

Rule: `session_id` and `thread_id` are references. They are not proof that Agent Orchestrator owns a provider-native session.

### ProviderRuntimeMeasurement

Stable fields:

- `format`: `agent_orchestrator.provider_runtime_measurement.v1`
- `measurement_status`
- `command_started_at`
- `command_completed_at`
- `duration_seconds`
- `exit_code`
- `provider_available`
- `degraded_reason`
- `usage_cost`

Rule: command timing and exit code may be measured locally. Usage/cost remains placeholder unless provider-reported.

### ProviderRuntimeOperationReceipt

This draft reuses `agent_orchestrator.runtime_operation_receipt.v1`.

Adapter implementations may add provider evidence fields, but must keep the existing receipt fields:

- `id`
- `job_id`
- `provider`
- `runtime_mode`
- `session_id`
- `thread_id`
- `action`
- `status`
- `reason`
- `detail`
- `terminal_state`
- `records_only`
- `updated_at`

## Method Semantics

### `capabilities()`

Returns adapter capability statuses. It must not run a real provider task. It may inspect local CLI version/help, cached health, or static adapter metadata.

### `start(request)`

Starts a provider task or returns a degraded result. It must provide enough local data for an `AgentJob`:

- command or API request summary
- local started timestamp
- provider label
- runtime id
- session ref when available
- degraded reason when not available

### `status(ref)`

Returns current known status without mutating provider state. If the adapter cannot inspect the provider-native session, it must report `unavailable` or `records_only`.

### `result(ref)`

Returns final output when the provider/local process has produced one. It must preserve stdout/stderr/raw output or provider structured output for downstream parsing.

### `send(ref, message)`

Sends a follow-up only when adapter support has been proven. Otherwise it must return a receipt with `unsupported`, `session_missing`, or `records_only`.

### `cancel(ref)`

Cancels only the local process/session unless provider-native cancellation has been proven. The receipt must distinguish local cancellation from provider-native cancellation.

## Integration Rule

Future implementation should map adapter results into existing surfaces:

```text
ProviderRuntimeAdapter
  -> JobRuntime
  -> AgentJob
  -> ProviderSessionSnapshot
  -> RuntimeEventStream
  -> EvidenceBundle
  -> ReleaseReadiness
```

The control plane should not consume provider adapters directly. It should continue consuming durable local job/control-plane artifacts.

## Pilot Gate

Before any adapter becomes a default path, it must prove:

- start works in a clean repo.
- status/result are inspectable after process exit.
- send/cancel outcomes are honest when unsupported.
- runtime measurement classifies measured/placeholder/unavailable correctly.
- evidence gates can consume the job without provider-specific branching.

## Phase 3 Result

This draft is sufficient to choose a pilot provider and write an implementation plan without claiming full bridge support.

