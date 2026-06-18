# Goal Mode: Native RC to Dogfood Adoption Loop

## One-Paragraph Goal

把当前 native release-candidate validation / operator bundle 从“可生成、可移交的本地 RC 证据包”推进到“真实 dogfood adoption loop”：让 operator 能用同一套 RC bundle 启动、跟踪、复盘 3 条真实本地日常任务链路，并把每条链路的 adoption decision、runtime choice、pause/recovery、workspace impact、validation drift、operator friction 反写到统一 adoption ledger / dashboard / evidence bundle。这个 goal 要比前两个 RC goal 更大：它不是再加一个静态报告，而是把 RC 证据包变成可反复使用的本地试运行流程；但仍不做公开 release、不做 provider marketplace/plugin/install 生态、不修改 AiMaMi 或本地代理配置。

## Required Parts

### P0 Adoption Case Pack / Ledger

保持当前 daily-driver 思路，不扩到大规模 benchmark；新增一个 native RC dogfood adoption case pack，固定 3 条本地 adoption lanes：

1. **repo_change_lane**：小型真实代码/文档变更，要求 workspace diff 可审阅。
2. **validation_lane**：运行或 dry-run RC validation，并判断是否可继续 handoff。
3. **recovery_lane**：模拟或使用已有 pause/failure/degraded runtime 状态，验证 recovery reason 与 next action 是否可读。

每条 adoption record 至少包含：case_id、lane、started_at、ended_at、duration_ms、input_requirement、runtime_choice、commands_or_actions、workspace_impact、rc_bundle_ref、validation_ref、outcome、pause_or_failure_reason、recovery_action、operator_decision、next_action。

### P1 RC Bundle Consumption Path

建立从现有 `product rc-report` / `product rc-validate` / `product rc-bundle` 到 dogfood adoption 的消费路径：

- 允许 CLI 启动 adoption dry-run 与 artifact 写入。
- 每条 adoption record 都必须引用当次 RC bundle verdict 与 validation verdict。
- 显式区分 `available`、`unavailable`、`not_run`、`not_applicable`、`missing`，并带 reason。
- 如果没有真实执行，则必须明确 dry-run / unavailable 原因，不能伪装成 pass。

### P2 Operator Adoption Report

生成 operator-readable adoption report，不能只输出 raw JSON。报告必须回答：

- 这 3 条 lane 是否足够支撑本地 dogfood？
- 当前 blocker 是 agent capability、product thickness、runtime/provider setup、instrumentation/evidence，还是 operator workflow friction？
- 哪些 lane 可以继续、哪些必须停止、哪些可以降级继续？
- workspace impact 是否可审阅？
- RC bundle 与 adoption 结果是否发生 drift？例如 RC bundle 是 degraded，但 adoption lane 仍可继续，或 RC bundle pass 但 lane fail。

### P3 Surface Projection

把 adoption summary 投射到至少三个 surface：

- CLI：新增或扩展 `agent-orchestrator product rc-adopt` / `rc-adoption-report` 类命令。
- Dashboard/UI service：health 或 session detail 能看到 adoption verdict、lane count、blockers、next action。
- evidence bundle：暴露 `native_rc_adoption` 或等价字段，包含 operator-readable summary 和 artifact refs。

### P4 Docs / Tests / Validation

补齐文档和测试，覆盖：

- adoption case pack / ledger schema；
- CLI pretty/json 输出；
- dry-run 与 unavailable 语义；
- dashboard/evidence projection；
- report 中 blocker classification；
- 至少一个 CLI smoke 证明 artifact 能生成。

## Completion Standard

只有当以下条件同时成立，这个 goal 才算完成：

1. 固定 3 条 adoption lane 均能生成 adoption record；
2. 每条 record 都引用 RC bundle / validation verdict，或明确记录 missing/unavailable reason；
3. runtime payload 至少包含 command/action、started_at、ended_at、duration_ms、status；
4. workspace impact 至少包含 changed_files / no_change / unavailable reason；
5. operator summary 能不读 raw transcript 判断 continue / stop / degrade；
6. pause/failure/recovery reason 被标准化；
7. adoption report 明确分类 gap：agent_capability / product_thickness / runtime_provider_setup / instrumentation_evidence / operator_workflow_friction / none；
8. dashboard 或 UI service 与 evidence bundle 都能看到 adoption verdict 与 next action；
9. tests 覆盖核心 schema、CLI、projection、docs；
10. 不修改 AiMaMi、本地代理配置，不做公开发布或安装生态。

## Non-Goals

- 不扩展到完整 OpenCode 产品集成；
- 不做真实 package registry 发布；
- 不做 provider marketplace / plugin ecosystem；
- 不要求 TUI 完整交互；
- 不要求真实外部 provider 成功，只要求 degraded/unavailable 语义准确；
- 不修改 AiMaMi/local proxy config。

## Suggested Implementation Shape

### Module Surface

优先在 `src/agent_orchestrator/native_productization.py` 继续扩展，避免过早拆模块；如文件过大，可新增 `native_adoption.py`，但要保持 CLI/control-plane import 不形成循环。

建议新增常量：

- `RC_ADOPTION_RECORD_VERSION = "agent_orchestrator.native_rc_adoption_record.v1"`
- `RC_ADOPTION_LEDGER_VERSION = "agent_orchestrator.native_rc_adoption_ledger.v1"`
- `RC_ADOPTION_REPORT_VERSION = "agent_orchestrator.native_rc_adoption_report.v1"`

建议新增函数：

- `build_rc_adoption_case_pack()`
- `run_rc_adoption(...)`
- `build_rc_adoption_report(...)`
- `write_rc_adoption_ledger(path, payload)`
- `write_rc_adoption_report(path, payload)`

### CLI Shape

建议命令：

```bash
agent-orchestrator product rc-adopt --dry-run --output .agent_orchestrator/release-candidate/adoption-ledger.json
agent-orchestrator product rc-adoption-report \
  --ledger .agent_orchestrator/release-candidate/adoption-ledger.json \
  --output .agent_orchestrator/release-candidate/adoption-report.json
```

Pretty output至少包含：verdict、lane summary、blockers、gap classification、workspace impact、next action、artifact path。

### Projection Shape

在 `build_product_ux_snapshot`、`build_evidence_bundle`、`DashboardService.health()` / `get_session()` 中投射 compact summary，而不是塞完整 transcript：

```json
{
  "native_rc_adoption": {
    "format": "agent_orchestrator.native_rc_adoption_summary.v1",
    "verdict": "pass|degraded|fail",
    "lane_count": 3,
    "completed_lane_count": 0,
    "dry_run": true,
    "gap_classification": "operator_workflow_friction",
    "blockers": [],
    "next_action": "run rc-adopt without dry-run for repo_change_lane"
  }
}
```

## Validation Hints

Run focused tests first, not full suite by default:

```bash
pytest -q tests/test_native_productization.py -k "adoption or release_candidate"
pytest -q tests/test_cli.py -k "rc_adopt or rc_adoption or product"
pytest -q tests/test_ui_service.py -k "native_product_ux or adoption"
pytest -q tests/test_control_plane.py -k "native_product_ux or adoption"
pytest -q tests/test_docs_process.py -k "adoption or release_candidate"
```

CLI smoke examples:

```bash
PYTHONPATH=src python -m agent_orchestrator.cli product rc-adopt --dry-run --format pretty --output /tmp/native-rc-adoption-ledger.json
PYTHONPATH=src python -m agent_orchestrator.cli product rc-adoption-report --ledger /tmp/native-rc-adoption-ledger.json --format pretty --output /tmp/native-rc-adoption-report.json
```

## Current Context Notes

Previous completed goals already added:

- native RC static report / gate: `product rc-report`;
- executable/dry-run validation: `product rc-validate`;
- operator handoff bundle: `product rc-bundle`;
- Dashboard/evidence projections for native release candidate and release bundle;
- docs at `docs/process/native-install-release-candidate-hardening.md`.

This goal should consume those surfaces instead of replacing them. If current code has uncommitted broader changes, avoid destructive git operations and only modify relevant files.
