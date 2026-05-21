# Agent Orchestrator

Agent Orchestrator is an MVP implementation of a success-first orchestration framework:

```text
Claude planner team
  -> Codex parallel workers
      -> Claude review/rescue team
```

The framework implements one full parent architecture, then derives `speed_first` and `cost_first` behavior through policy instead of maintaining three separate systems.

## Modes

- `success_first`: full Claude-Codex-Claude loop with required review and rescue.
- `speed_first`: thinner planning, aggressive parallelism, risk-based review.
- `cost_first`: shallow planning, limited parallelism, rescue only on failure.
- `auto`: deterministic heuristic routing to one of the three modes.

## MVP Capabilities

- Clarifies fuzzy requirements into a task contract.
- Decomposes the contract into work units.
- Routes execution through a policy profile.
- Simulates Codex worker execution.
- Sends failed, uncertain, or high-risk work to Claude-style review/rescue.
- Tracks task state transitions and observability events.
- Tracks agent jobs through a separate `JobRuntime` lifecycle.
- Models structured review findings for future real review adapters.

## Job Runtime

MVP v2 separates task state from external agent job lifecycle. Adapters can use:

- `InMemoryJobRuntime` for deterministic tests and synchronous mock jobs.
- `FileJobRuntime` for durable local records under `.agent_orchestrator/jobs/`.
- `CommandJobRuntime` for conservative synchronous Claude/Codex command execution.

The shared lifecycle is:

```text
start -> status -> result
             ├── send
             └── cancel
```

Review and research jobs default to `read-only`; implementation and rescue jobs default to `workspace-write`.

## Real Command Integrations

MVP v3 adds a guarded command runtime for local providers. The default remains `mock`, so tests and basic runs do not require Claude Code or Codex CLI.

Check local provider availability:

```bash
python -m agent_orchestrator.cli --health
python -m agent_orchestrator.cli "Implement multiple independent modules in parallel" --mode auto
```

Run through the command runtime:

```bash
python -m agent_orchestrator.cli "Review this workspace" --runtime command --provider claude
python -m agent_orchestrator.cli "Implement the task" --runtime command --provider codex
```

The command runtime records stdout, stderr, exit code, command arguments, and error details in job records. It does not do background tmux sessions, multi-turn resume, automatic install, or fallback between providers.

## Auto Routing

When `--mode auto` is used, a deterministic `PolicyRouter` profiles the request and picks one of the three real modes. High risk or high ambiguity defaults to `success_first`; clearly parallel, low-risk work may route to `speed_first`; simple low-risk work may route to `cost_first`.

If signals conflict, risk wins first, then ambiguity, then urgency, then cost.

## MVP v5

`v5` adds whole-run failure rerouting. By default, `--reroute on` is enabled.

- `cost_first` can upgrade to `speed_first`, then to `success_first`.
- `speed_first` can upgrade to `success_first`.
- `success_first` records failures, but does not auto-upgrade further.
- The system upgrades at most once per request and always reruns the whole task.

The run result now keeps `attempts`, `reroute_history`, and `failure_decision` so you can inspect why the mode changed and what happened before the upgrade.

## MVP v6

`v6` adds work-unit level partial rescue before whole-run escalation.

- Failed or high-risk `work units` are retried locally before rerunning the whole task.
- Partial rescue runs inside the current mode and reuses existing `work_units`.
- If partial rescue succeeds, the run completes without `rerouted`.
- If partial rescue still leaves failures or high-risk findings, the system can still use the `v5` one-step upgrade path.

The run result now also keeps `partial_rescue_results` and `recovered_work_unit_ids` on each attempt.

## MVP v7

`v7` adds dependency-aware replay before whole-run escalation.

- Failed or high-risk `work units` replay their dependent downstream units.
- Dependency replay runs inside the current mode and reuses existing `work_units`.
- If dependency replay succeeds, the run completes without `rerouted`.
- If dependency replay still leaves failures or high-risk findings, the system can still use the `v6` one-step upgrade path.

The run result now also keeps `dependency_rescue_results`, `replayed_work_unit_ids`, and dependency metadata on each attempt.

## Run

```bash
python -m agent_orchestrator.cli "Build a dashboard with tests" --mode success_first
```

Or after installing the package:

```bash
agent-orchestrator "Build a dashboard with tests" --mode speed_first
```

## Test

```bash
pytest
```

## Real Integrations

The current workers are deterministic mock adapters. Real Claude Code and Codex Cloud integrations should implement the adapter interfaces in `agent_orchestrator.adapters`.
