# Agent Orchestrator

Agent Orchestrator is an **AI Work Control Plane for long-cycle local agent work**. It keeps plans, context, execution topology, approvals, evidence, memory provenance, runtime measurements, and recovery state outside the model so they can be inspected, resumed, and audited.

Current status: **Runtime Measurement + Codex Pilot Evidence Ready for `v1.0.0-rc.3` evaluation**.

Current workflow target: **internal default** for the author's local long-cycle agent work.

This repository is not trying to be a provider-native bridge, a persistent provider session owner, a tmux replacement, or a human-org-chart agent simulator. The product center is the control plane above those runtimes.

Explicit orchestration may become less visible over time, while state, evidence, approvals, memory, and recovery stay outside the model as auditable system responsibilities.

## What It Does

- Turns fuzzy work into governed plan sessions with persisted artifacts.
- Runs explicit planning, review, approval, and execution stages.
- Tracks workspace state, context packets, topology snapshots, approval records, evidence bundles, memory provenance, and runtime events.
- Routes work through strategy profiles such as `success_first`, `speed_first`, `cost_first`, and `auto`.
- Supports local command-runtime jobs with measured duration, exit status, provider/runtime metadata, degraded reasons, and operation receipts.
- Reports release readiness through setup, compliance, evidence, workspace, and gate surfaces.

## Current RC Boundary

The current candidate is **measurement-ready**, not provider bridge-ready.

Runtime measurement reports local facts when they exist:

- command start/end timestamps
- duration
- exit code
- provider and runtime mode
- provider availability
- degraded reasons
- operation receipts

Token and cost fields remain placeholders unless a runtime reports trustworthy values directly. That is intentional and is not an RC blocker for this track.

## Quickstart

Run commands from the repository root:

```bash
cd /Users/abab/Desktop/Agent-Orchestratoar
PYTHONPATH=src python -m agent_orchestrator.cli health
PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json
PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
```

Start and inspect a governed work session:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli team start "Build a persisted plan artifact for a routine implementation task"
PYTHONPATH=src python -m agent_orchestrator.cli team summary <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team next <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team draft-ready <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team submit-review <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team approve <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team execute <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team inspect-execution <session-id>
```

Run a direct task through the policy router:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli run "Review this workspace and report the next hardening step" --mode auto
```

## Release Checks

Before calling a candidate ready, run:

```bash
pytest
PYTHONPATH=src python -m agent_orchestrator.cli team setup --runtime command --format json
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
```

The current release checklist is [docs/process/v1-candidate-release-checklist.md](docs/process/v1-candidate-release-checklist.md). The short canonical readiness process is [docs/process/v1x-release-readiness.md](docs/process/v1x-release-readiness.md).

RC packaging docs:

- [v1.0.0-rc.3 release notes](docs/releases/v1.0.0-rc.3.md)
- [v1.0.0-rc.3 evidence packet](docs/process/v1.0.0-rc.3-evidence-packet.md)

## Product Layers

The project is organized as:

- **AI Work Control Plane**: workspace state, context packets, strategy decisions, topology snapshots, approvals, evidence, memory provenance, and recovery.
- **Decision Core**: plan sessions, review rounds, decision verdicts, compliance gates, and execution contracts.
- **Execution Topology**: task pools, role contracts, worker handoffs, runtime/job surfaces, and operator guidance.
- **Provider / Runtime Layer**: local command runtime, CLI inheritance/isolation modes, direct API readiness checks, and future replaceable adapters.

中文说明入口：

- [决策核心 / 执行拓扑 / 运行时分层说明](docs/architecture/决策核心-执行拓扑-运行时分层说明.md)
- [上下文地图](docs/process/context-map.md)
- [长周期主执行计划](docs/process/长周期主执行计划.md)
- [Operator Runbook](docs/process/agent-team-operator-runbook.md)
- [Architecture Decision Records](docs/decisions/)

默认执行节奏：按长周期主计划推进，验证通过后自动进入下一段。

## Main CLI Surfaces

- `team setup`: provider health, runtime measurement readiness, doc sync, compliance, and release readiness.
- `team workspace-status`: workspace snapshot and control-plane state.
- `team context-packet`: compressed task context for agent work.
- `team topology inspect`: read-only execution topology snapshot.
- `team approvals list` / `team approvals resolve`: approval queue inspection and resolution.
- `team evidence-gates`: readiness gates for evidence-backed release decisions.
- `team runtime inspect <job-id>`: runtime measurement, operation receipts, and degraded runtime details.
- `evidence report` / `evidence trend`: evidence metrics, runtime measurement metrics, and deltas.

## Provider Runtime Modes

- `cli_inherit`: use local `codex` / `claude` CLI behavior, including user auth and project/global configuration.
- `cli_isolated`: run CLI jobs with a repository-owned runtime home under `.agent_orchestrator/runtime-homes/`.
- `direct_api`: report masked API readiness for low-side-effect governance roles such as planning, review, and summarization.

`team setup` and `health --refresh` report local readiness without storing API keys.

## Evidence

Refresh evidence reports with:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli evidence report \
  --case-file docs/process/evidence-cases.json \
  --output docs/process/v1x-evidence-report.md \
  --json-output .agent_orchestrator/evidence/real-tasks.json
```

Evidence reports cover real-task dogfood metrics, recovery coverage, runtime fidelity, compliance blocking, postmortem readiness, and runtime measurement deltas. Cost and token values remain placeholders until provider/runtime integrations report them directly.

## UI

Start the local operator console:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli ui
```

The console is a local operator surface for sessions, governance signals, execution provenance, runtime/job state, and evidence-backed readiness.

## Development

For quick feedback:

```bash
pytest -m "not slow_integration"
```

For final stage closeout:

```bash
pytest
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
```

Install repository-managed hooks:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli install-hooks
```
