# Agent Orchestrator

Agent Orchestrator is an AI Work Control Plane for long-cycle local agent work.

中文说明入口：

- 分层说明见 [docs/architecture/决策核心-执行拓扑-运行时分层说明.md](/Users/abab/Desktop/Agent-Orchestratoar/docs/architecture/决策核心-执行拓扑-运行时分层说明.md)
- 上下文地图见 [docs/process/context-map.md](/Users/abab/Desktop/Agent-Orchestratoar/docs/process/context-map.md)
- 架构决策记录见 [docs/decisions/](/Users/abab/Desktop/Agent-Orchestratoar/docs/decisions/)
- 长周期执行章程见 [docs/process/长周期主执行计划.md](/Users/abab/Desktop/Agent-Orchestratoar/docs/process/长周期主执行计划.md)
- operator 操作说明见 [docs/process/agent-team-operator-runbook.md](/Users/abab/Desktop/Agent-Orchestratoar/docs/process/agent-team-operator-runbook.md)
- 后续实现默认按 `AI Work Control Plane -> 决策核心层 + 执行拓扑层 + Provider / Runtime 层` 来归类
- 当前仓库的默认目标是先做到 `internal default`，并按“验证通过后自动进入下一段”的长周期方式持续推进

It keeps the existing orchestration engine, but the project center of gravity moves upward to external work governance:

- `WorkspaceState`
- `ContextPacket`
- `StrategyDecision`
- `ExecutionTopologySnapshot`
- `ApprovalItem`
- `EvidenceBundle`
- `MemoryRecord`

The older two product layers remain as implementation layers under that control plane:

- `Planning Governance Layer`
  - generates plans
  - runs fixed dual-model adversarial plan review before execution
  - persists plan files, checklists, and resume state
  - emits decision verdicts with topology/provider recommendations
  - enforces documentation and process synchronization
- `Execution Strategy Layer`
  - turns approved plans into routed execution
  - decides review/rescue/replay/reroute behavior
  - drives pluggable execution backends
  - emits explainable run artifacts with approved-plan provenance

```text
task input
  -> planning governance loop
      -> decision verdict + approved plan artifact
          -> execution strategy layer
              -> pluggable execution backends
                  -> explainable run artifacts + synchronized docs
```

The system is intentionally not trying to win by rebuilding every bridge, session runtime, provider shell, or model-internal planning behavior. Its value comes from durable external state: context compression, evidence, approval, memory provenance, recovery semantics, and recoverable plan state. In the short term, explicit orchestration still solves real work; in the medium term, the control plane governs that orchestration; in the long term, orchestration may be internalized by stronger model runtimes, while state, evidence, approvals, memory, and recovery stay outside the model as auditable system responsibilities.

## 5-Minute CLI Quickstart

Run from the repository root. The quickstart is CLI-first and uses the default local/mock-safe path unless you explicitly choose a command provider.

```bash
cd /Users/abab/Desktop/Agent-Orchestratoar
PYTHONPATH=src python -m agent_orchestrator.cli health
PYTHONPATH=src python -m agent_orchestrator.cli team setup
PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status
PYTHONPATH=src python -m agent_orchestrator.cli team context-packet --query "current task"
```

Start a governed planning session, inspect the next operator action, and approve only after required gaps are closed:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli team start "Build a persisted plan artifact for a routine implementation task"
PYTHONPATH=src python -m agent_orchestrator.cli team summary <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team next <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team runbook <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team revise <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team approve <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team execute <session-id>
PYTHONPATH=src python -m agent_orchestrator.cli team inspect-execution <session-id>
```

For a direct smoke run, keep the same CLI entrypoint and let `auto` choose the policy profile:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli run "Review this workspace and report the next hardening step" --mode auto
```

Before calling a candidate ready, capture the local release signals:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli evidence report \
  --case-file docs/process/evidence-cases.json \
  --output docs/process/v1x-evidence-report.md \
  --json-output .agent_orchestrator/evidence/real-tasks.json
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
```

Use `docs/process/v1-candidate-release-checklist.md` as the detailed v1.0 candidate checklist; `docs/process/v1x-release-readiness.md` stays the short canonical process document used by compliance refresh.

## Product Shape

The intended v1 product shape is:

- a local-first CLI tool
- optimized for the author's real workflows before broader generalization
- shaped as an AI Work Control Plane before it is an agent-role product
- built around pluggable providers, bridges, runtimes, and job backends
- centered on plan governance before code execution
- centered on explainable strategy decisions during execution
- backed by enforced documentation synchronization and hook-based compliance checks

In practice, a user gives the CLI a task plus optional strategy constraints, and the system returns:

- a persisted plan artifact
- a decision verdict describing approval status, topology choice, and provider/runtime choice
- a shared `ExecutionContract` schema used by both approved-plan sessions and direct runs
- a decision verdict that can record provider fallback when a preferred reviewer/runtime is unavailable
- review rounds and checklist progress
- an approved execution-ready plan
- routing and execution choices
- review/rescue/replay/reroute decisions
- a structured run record describing why the system chose that path
- synchronized documentation updates and compliance results
- a workspace state snapshot, context packet, topology snapshot, approval queue, evidence bundle, and memory provenance
- direct-run artifacts that also carry entrypoint and provenance metadata
- direct-run artifacts that also carry an approved-plan-style execution contract, including topology and provider recommendations

The v1 product is not a bridge product, a tmux/session manager, a provider-specific orchestration shell, or a classically human org chart. Those concerns remain plugin boundaries below the work control plane.

## Provider Runtime Modes

Provider / Runtime behavior is explicit and auditable:

- `cli_inherit` is the default for implementation and rescue work. It uses the local `codex` / `claude` CLI, including user auth, global config, project config, and provider-native rules.
- `cli_isolated` runs CLI jobs with a repository-owned runtime home under `.agent_orchestrator/runtime-homes/`, so global rule inheritance is bounded and visible in job metadata.
- `direct_api` is for low-side-effect governance roles such as planning, review, adversarial review, and summarization. It reads `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` from the environment, reports only masked readiness, and does not provide a local file-editing tool loop.

`team setup` and `health --refresh` report CLI availability, runtime modes, masked direct API readiness, and provider fallback details without storing API keys.

## Modes

- `success_first`: strongest policy profile with required review and conservative rescue/escalation behavior.
- `speed_first`: thinner planning, aggressive parallelism, and risk-based review.
- `cost_first`: shallow planning, limited parallelism, and rescue only on failure.
- `auto`: deterministic heuristic routing to one of the three modes.

## Core Value

The unique part of this repository is the combination of:

- adversarial plan review before code execution
- persisted plan artifacts with checklist and resume state
- strategy decisions for route/review/rescue/replay/reroute
- explainable execution artifacts
- enforced document/code synchronization through hooks and loopback checks

LLM providers, bridges, command runtimes, job stores, and background execution are expected to be pluggable modules around those cores.

## V1 Success Criteria

The first product-quality version should be able to:

- accept a real coding or review task through the CLI
- run a rule-driven plan governance loop before execution
- persist plan files into the project and resume them after interruption
- choose among `success_first`, `speed_first`, `cost_first`, or `auto` strategy behavior
- drive at least one replaceable execution backend without changing strategy semantics
- emit a run artifact that explains the chosen route, review intensity, rescue behavior, and escalation path
- enforce project rules with hook-based checks instead of prompt-only discipline
- keep global maps, module manifests, and file-level declarations in sync with code changes
- justify why the system performs better than a fixed, one-size-fits-all workflow for at least a small set of real tasks

## Current Capabilities

- Clarifies fuzzy requirements into a task contract.
- Runs a fixed dual-model planning loop: author draft, adversarial review, decision verdict.
- Persists plan sessions, review rounds, checklist state, and resume metadata for the `team` workflow.
- Exposes session-centric operator guidance through `team summary`, `team next`, and `team runbook`.
- Exposes task-pool visibility through `team task list`, `team task next`, and `team task done`.
- Exposes role-contract discipline through `team roles`.
- Records execution context policy (`fresh`, `resume`, `resume_if_same_task`) in execution metadata.
- Persists lightweight knowledge artifacts through `team inspect-knowledge`.
- Builds agent-ready canonical documentation packages through `team inspect-docs`, using stable doc ids and current doc-sync status.
- Builds AI-native context packets through `team context-packet`; packets compress docs and memory but do not choose strategy.
- Persists workspace snapshots through `team workspace-status` at `.agent_orchestrator/workspace/index.json`.
- Exposes read-only topology snapshots through `team topology inspect`.
- Exposes human intervention and approval records through `team approvals list` / `team approvals resolve`.
- Exposes gate summaries through `team evidence-gates`.
- Exposes runtime fidelity through `team runtime inspect <job_id>`, provider session snapshots, and operation receipts without claiming ownership of persistent provider sessions.
- Records durable architecture decisions under `docs/decisions/` so session knowledge can graduate into canonical ADRs.
- Surfaces approval state, human-intervention reason, runtime health, and usage/cost placeholders in operator payloads.
- Standardizes worker/subagent handoffs with `SUMMARY / CHANGES / EVIDENCE / RISKS / BLOCKERS` so parent sessions consume bounded evidence instead of full child transcripts.
- Exposes gate evidence summaries, task timelines, setup doctor JSON contracts, and lightweight diagnostics through existing team/setup/status surfaces.
- Decomposes the approved plan into execution-ready work units.
- Executes approved team plans from approved-plan artifacts rather than re-deriving from the raw requirement.
- Routes execution through a policy profile.
- Sends failed, uncertain, or high-risk work to review/rescue paths.
- Tracks task state transitions and observability events.
- Tracks agent jobs through a separate `JobRuntime` lifecycle.
- Models structured review findings for pluggable review adapters.
- Supports work-unit partial rescue and dependency-aware replay before whole-run reroute.
- Enforces a narrow compliance gate around required workflow docs, operator-runbook signals, and plan artifact persistence.
- Persists product roadmap and process supervision documents in-project.

## Product Layers And Plugins

The intended module boundary is:

- `Planning Governance Layer`
  - plan authoring
  - reviewer and adversarial reviewer loops
  - plan artifact persistence
  - checklist tracking
  - task pool and next executable task visibility
  - role contracts and required outputs
  - resume metadata
  - documentation synchronization checks
- `Execution Strategy Layer`
  - policy, routing, failure semantics, rescue/escalation, explainability
- `Execution Plugins`
  - provider adapters, bridge adapters, command/runtime backends, job stores
- `Observability / Governance`
  - run evidence, plan review evidence, hook failures, and audit-friendly traces

Execution plugins may use local commands, hosted APIs, bridge tools, or mock runtimes. Both product layers should remain valid even as those plugins change.

中文补充：

- `AI Work Control Plane` 是新的上层产品重心，负责状态、上下文、策略、拓扑、审批、证据、记忆和恢复
- `agent team` 应归到“执行拓扑层”，不是整个产品本体
- `claude / codex / command runtime` 应归到 “Provider / Runtime 层”
- `PlanSession / RoundController / DecisionVerdict / execution gating` 应归到“决策核心层”
- 短期靠显式编排完成真实工作；中期由 control plane 管住编排；长期即使编排被模型逐步内化，状态、证据、审批、记忆和恢复仍保留在系统外部

## Execution Backends

The current repository includes a guarded local command runtime. The default remains `mock`, so tests and basic runs do not require Claude Code or Codex CLI.

Check local provider availability:

```bash
python -m agent_orchestrator.cli health
python -m agent_orchestrator.cli run "Implement multiple independent modules in parallel" --mode auto
```

The health output includes `codex`, `claude`, and `mock` provider records with binary, availability, detail, and recommended fallback fields. Command-runtime runs record this health snapshot in run/session metadata.

Provider health uses a two-tier cache:

- L1 in-process memory cache for repeated checks in the same CLI/server process.
- L2 local JSON cache at `.agent_orchestrator/cache/provider-health.json` for repeated CLI invocations.

Refresh live status when needed:

```bash
python -m agent_orchestrator.cli health --refresh
python -m agent_orchestrator.cli health --cache-ttl 300
```

Run through the command runtime:

```bash
python -m agent_orchestrator.cli run "Review this workspace" --runtime command --provider claude
python -m agent_orchestrator.cli run "Implement the task" --runtime command --provider codex
```

Review policy can be recorded through a controlled override:

```bash
python -m agent_orchestrator.cli run "Build with strict review" --review-policy adversarial
python -m agent_orchestrator.cli team execute <session-id> --review-policy required-human
```

Allowed values are `auto`, `standard`, `adversarial`, and `required-human`; `auto` preserves default policy behavior.

The command runtime records stdout, stderr, exit code, command arguments, and error details in job records. It is intentionally not the main product value and does not aim to replace specialized background session managers, bridge plugins, or provider-native continuation systems.

## Failure Handling

Whole-run failure rerouting is enabled by default with `--reroute on`.

- `cost_first` can upgrade to `speed_first`, then to `success_first`.
- `speed_first` can upgrade to `success_first`.
- `success_first` records failures, but does not auto-upgrade further.
- The system upgrades at most once per request and always reruns the whole task.
- Failed or high-risk `work units` are retried locally before rerunning the whole task.
- Dependency replay can rerun affected downstream units before stronger escalation.

Run results keep `attempts`, `reroute_history`, `failure_decision`, `partial_rescue_results`, `recovered_work_unit_ids`, `dependency_rescue_results`, and `replayed_work_unit_ids` so you can inspect what the system decided and why.

## Run

```bash
python -m agent_orchestrator.cli run "Build a dashboard with tests" --mode success_first
```

Or after installing the package:

```bash
agent-orchestrator run "Build a dashboard with tests" --mode speed_first
```

## Test

For quick local feedback, skip the slower CLI/team integration scenarios:

```bash
pytest -m "not slow_integration"
```

Before stage closeout or release readiness, run the full suite:

```bash
pytest
```

## Hook Setup

Install the repository-managed git hooks:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli install-hooks
```

The installed `pre-commit` hook runs:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
```

Repair canonical process docs and inspect remaining compliance actions:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli team refresh-docs
PYTHONPATH=src python -m agent_orchestrator.cli team repair-compliance
```

## Evidence Reports

Capture built-in or real-task workflow evidence:

```bash
python -m agent_orchestrator.cli evidence benchmark --output .agent_orchestrator/evidence/workflow.json
python -m agent_orchestrator.cli evidence capture --case-file cases.json --output .agent_orchestrator/evidence/real-tasks.json
python -m agent_orchestrator.cli evidence report --output docs/process/v1x-evidence-report.md
python -m agent_orchestrator.cli evidence report --case-file docs/process/evidence-cases.json --output docs/process/v1x-evidence-report.md --json-output .agent_orchestrator/evidence/real-tasks.json
```

Case files are JSON lists with `label`, `requirement`, `scenario_type`, `mode`, `risk_profile`, `operator_goal`, `expected_signals`, and `runtime_expectation`. The committed matrix in `docs/process/evidence-cases.json` covers standard implementation, follow-up recovery, high-risk migration, parallel validation, UI workflow, compliance blocking, runtime fidelity, and interruption recovery.

Evidence reports include real-task dogfood metrics for recovery coverage, runtime fidelity coverage, compliance blocking coverage, postmortem readiness, and cost/latency readiness. Cost/latency values remain placeholders until a provider/runtime supplies trustworthy measurements.

## Release Readiness

Before calling a build release-ready, check:

1. version sync in `pyproject.toml`
2. targeted tests for the touched stage
3. evidence report/trend outputs
4. compliance status from `team check-compliance`

The CLI does not pretend to be a package marketplace or plugin installer; it only reports local readiness honestly.

## Agent Team Console

Start the local operator console:

```bash
python -m agent_orchestrator.cli ui
```

The console surfaces session status, governance signals, execution provenance, review policy, fallback snapshots, compliance snapshots, event/message timelines, work graph state, job logs, follow-up send, and cancel controls.

## Real Integrations

The current workers are deterministic mock adapters plus a conservative local command backend. Real Claude Code, Codex, or other LLM integrations should plug into the adapter interfaces in `agent_orchestrator.adapters` rather than redefine the product layers.
