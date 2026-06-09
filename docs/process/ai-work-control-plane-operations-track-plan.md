# AI Work Control Plane Operations Track Plan

## 目的

这个 track 的任务，是把当前已经存在的控制平面制品链路，推进成默认可操作的工作界面。

重点不是继续堆“更复杂的 agent 编排”，而是让 operator 可以围绕外部状态来理解和接管长周期任务：

```text
PlanSession -> WorkspaceState -> ContextPacket -> StrategyDecision
  -> ExecutionTopologySnapshot -> ApprovalInbox -> RunLedger
  -> EvidenceBundle -> MemoryPromotion
```

显式 `agent team` 编排仍然保留，但它属于下层执行能力。控制平面负责暴露状态、上下文、治理摘要、执行路径、审批、证据、记忆提升、恢复建议、运行时健康和会话连续性。

## 执行协议

- 每个 phase 先在 `docs/process/` 写短计划，再进入实现。
- 实现期间只跑该 phase 对应的 targeted tests。
- targeted tests 通过后自动进入下一 phase，不等待额外确认。
- 只有在最终收口时才跑完整 `pytest` 和 `team check-compliance`。
- 保持现有 `team` 命令兼容；新增字段应尽量可选、增量、非破坏。
- 不在这个 track 里做 React Flow 编辑器、完整 provider bridge、完整 direct-API patch engine 或 provider ping-pong loop。
- `StrategyDecision.executes` 继续保持 `False`，执行权限仍由 approved-plan gate 和 runtime 层掌握。
- 兼容性说明：`StrategyDecision.executes` stays `False`，避免把执行权限重新塞回治理摘要本身。

## Phase Plan

### Phase 0: Operations Track Baseline

Record this track, link the reference rescreen into canonical docs, and make the next line explicit: `Workspace / Program Index v2 + Approval Inbox + Run Ledger`.

Targeted tests:

```bash
pytest tests/test_docs_process.py tests/test_planning_support.py -q
```

### Phase 1: Workspace / Program Index v2

Extend `agent_orchestrator.workspace_index.v1` with optional operator-current-state fields: `program`, `active_artifacts`, `recent_artifacts`, `open_approvals`, `recent_runs`, `memory_candidates`, and `provider_runtime_health`.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_ui_service.py -q
```

### Phase 2: Approval Inbox Hardening

Treat approvals as an inbox with summary counts, reason distribution, stable recommended commands, and optional refs to plan, topology, run, job, evidence, and memory candidate artifacts.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_team.py -q
```

### Phase 3: Run Ledger

Add read-only `agent_orchestrator.run_ledger.v1` for long-cycle recovery across plan sessions, runs, delegated jobs, approvals, evidence, provider fallback, and compliance blocking.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_cli.py tests/test_cli_presenters.py tests/test_team.py -q
```

### Phase 4: Topology Blueprint Snapshot

Extend `ExecutionTopologySnapshot` with optional read-only blueprint fields: nodes, edges, lanes, approval points, evidence points, and runtime boundaries.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_actions.py tests/test_cli.py -q
```

### Phase 5: Memory Promotion Workflow

Add evidence-backed memory candidates without auto-writing durable memory. Only provenance-bearing candidates can be promoted.

Targeted tests:

```bash
pytest tests/test_memory.py tests/test_control_plane.py tests/test_cli.py tests/test_planning_support.py -q
```

### Phase 6: Runtime Health + Tool Inventory

Surface provider/runtime health, MCP/tool inventory placeholders, setup/degraded state, and usage/cost placeholders as control-plane inputs.

Targeted tests:

```bash
pytest tests/test_messages.py tests/test_control_plane.py tests/test_cli.py tests/test_team.py -q
```

### Phase 7: Dogfood Operations Scenario

Run the repository through the new operations chain and record the result in process evidence.

Targeted tests:

```bash
pytest tests/test_control_plane.py tests/test_team.py tests/test_cli.py tests/test_docs_process.py -q
```

### Phase 8: Final Convergence

Refresh docs and run full gates:

```bash
pytest
env PYTHONPATH=src python -m agent_orchestrator.cli team check-compliance
env PYTHONPATH=src python -m agent_orchestrator.cli team workspace-status --format json
env PYTHONPATH=src python -m agent_orchestrator.cli team evidence-gates --format json
git status --short
```

## Reference Rescreen Landing

The reference rescreen is now treated as input to this track:

- HiveWard informs workspace/program, blueprint, approval inbox, run ledger, and runtime boundary.
- wanman informs supervisor/store/runtime isolation boundaries.
- slark informs workflow state, approval steps, and lessons/decisions promotion.
- CodeWhale informs doctor JSON, resume/fork language, model routing, and MCP validation.
- codex-orchestrator informs job observability and context-map prompt support.
- plugin repos inform read-only review, mutating rescue, setup/status/result grammar, and honest degraded capability.
- Eigent informs real dogfood cases, HITL, and MCP/tool inventory.

## Completion Bar

The track is complete when the operator can use `team workspace-status`, `team approvals`, `team topology inspect`, `team evidence-gates`, `team summary`, `team next`, and `team runbook` to understand current state, approval needs, run history, evidence, memory candidates, runtime health, and recovery path without manually stitching lower-level files together.

## Implementation Result

Operations Track implementation is complete through Phase 7:

- Workspace / Program Index v2 is the `team workspace-status --format json` payload and keeps nested `workspace_state` for compatibility.
- Approval Inbox adds optional refs and inbox summary while keeping resolve records-only.
- Run Ledger records recovery-relevant plan, run, job, approval, evidence, and fallback state as `agent_orchestrator.run_ledger.v1`.
- Topology Snapshot exports a read-only blueprint view with lanes, approval points, evidence points, and runtime boundaries.
- Evidence Bundle exposes memory promotion candidates, runtime health, tool inventory, and usage/cost placeholders while keeping `auto_write=false`.
- Dogfood evidence is recorded in `docs/process/ai-work-control-plane-operations-dogfood-evidence.md`.

Final convergence is tracked in `docs/process/ai-work-control-plane-operations-phase-8-final-convergence.md`.
