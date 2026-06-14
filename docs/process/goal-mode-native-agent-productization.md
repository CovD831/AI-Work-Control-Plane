# Native Coding Agent Productization And OpenCode Gap Convergence Goal

## Goal Intent

本 goal 的重点，不再是继续扩一两个 bounded task coverage case。

上一阶段已经把 native coding agent 从“单点成功”推进到“多类真实仓库任务上的默认覆盖能力”。下一阶段要解决的是另一个问题：

- native agent 是否开始接近一个可日常使用的 productized coding agent，
- 而不只是一个治理很强、但工具面和长任务能力仍偏窄的 governed execution kernel。

因此，本 goal 的目标不是全面复制 `research_repos/opencode/`，而是把当前项目与它之间的差距，从：

- “核心治理强，但 native agent 仍偏 bounded / early-mid maturity”

收敛到：

- “平台广度、生态与交互产品面仍落后，但 native 主执行器已经更接近 daily-driver 级别，并在工具深度、planner 独立性、session continuity 与 adapter 一致性上进入更接近同代际的区间”

## Target Outcome

完成后，项目相对 `research_repos/opencode/` 的差距，应主要剩在：

1. 更大规模的工具/插件生态。
2. 更厚的 session / IDE / product UX。
3. 更广的通用任务与多代理生态。

而不应继续主要卡在以下基础面：

1. native tool surface 过窄。
2. planner 仍明显依赖 compatibility bridge。
3. session continuity 只适合 bounded recovery，不适合更长链任务。
4. native / external 在 adapter 能力上像两套系统。

## Scope Boundary

本 goal 只包含以下四个实现部分，且都必须完成：

### P0 Native Tool Surface Expansion

把 native coding agent 从“有执行闭环”推进到“有更像 coding copilot 的工具厚度”。

必须完成：

- 扩展更强的 read / search / glob / patch / verify 能力；
- 让 native path 在无强 target 时也能更自然地进行仓库探索；
- 增强 edit / patch 的表达力，但保持 governed 与 auditable；
- 至少一类新增较复杂真实任务要因为这些工具面提升而更适合 native path。

### P1 Native Planner Independence

把 planner 从“已有策略层”推进到“更原生、更少 compatibility 依赖的 planner”。

必须完成：

- planner 能更明确决定：
  - when to explore
  - when to clarify
  - when to edit
  - when to verify
  - when to pause
  - when to handoff/fallback
- 降低“仅借壳 legacy decomposition”的比重；
- 对 planner decision 保留 candidate / reason / boundary / evidence；
- 形成至少一个比当前更长链的 `Planner -> Runtime -> Recovery` 可回归样例。

### P2 Session Productization And Long-Horizon Continuity

把 session 从“bounded closure 可恢复”推进到“更像可日常使用的长任务 session”。

必须完成：

- 改善 compaction / continuity / resume / cost-runtime metadata；
- 强化 operator-visible session continuity；
- 对较长链任务保留更稳定的 context reduction 与 resume contract；
- 在 UI/CLI summary 与 workspace index 中明确投影：
  - session continuity
  - compacted context state
  - runtime/cost metadata
  - current long-horizon recovery posture

### P3 Unified Native/External Adapter Ecosystem

把 native / external 从“能共存”推进到“共用一套更完整的 execution adapter contract”。

必须完成：

- 明确 native-first adapter surface；
- external adapter 继续保留 hot-plug；
- 共享 capability / governance / approval / evidence / recovery semantics；
- 让 native / external 的 comparative benchmark 更接近“同一 contract 下的两种 executor”，而不是两个分裂世界。

## Global Stopping Criteria

只有以下条件全部满足，goal 才能停止：

1. `P0`、`P1`、`P2`、`P3` 四部分都已完成。
2. native 工具面已经明显强于上一阶段的 bounded kernel 状态。
3. planner 已出现更明显的 native-first 独立性，而不再主要体现为 compatibility bridge。
4. 至少一类比当前更长、更复杂的真实仓库任务可主要依赖 native path 闭环。
5. session continuity / compaction / runtime-cost metadata 已进入多个 operator-visible surface。
6. native / external adapter 协作边界更统一，但 external hot-plug 未被破坏。
7. 与 `opencode` 的差距已明确收敛到：
   - 主执行器日常可用性更接近同代际；
   - 但工具生态、插件、产品厚度仍明显落后。
8. 没有无限扩张到：
   - 全面追平 `opencode` 全部产品表面
   - 做完整 IDE / 插件市场
   - 一次性覆盖所有 coding task 类型
   - 做与 productization gap 无关的大规模重构

## Phase Acceptance Criteria

### P0 Acceptance

`P0` 只有在以下条件全部满足时才算完成：

1. native tool surface 至少在多个面真实扩展：
   - read/search
   - patch/edit
   - verify
   - repo exploration
2. 这些能力进入真实主链路，而不只是 helper 存在。
3. 至少一个较复杂 task class 因此获得更强 native 默认能力。
4. UI/CLI/runtime/evidence 至少两个面能看到新的工具面证据。
5. 存在测试或等价高信号验证。

### P1 Acceptance

`P1` 只有在以下条件全部满足时才算完成：

1. planner 原生决策能力增强。
2. compatibility-only 行为被显式减少或被更清楚包裹。
3. planner decision 有明确 reason / boundary / candidate / evidence 输出。
4. 至少一条更长链任务证明 planner 不只是形式存在。
5. 存在测试或等价高信号验证。

### P2 Acceptance

`P2` 只有在以下条件全部满足时才算完成：

1. session continuity 不只支持 bounded recovery，也支持更长任务的 compact / resume。
2. runtime/cost/session metadata 进入 operator-visible surface。
3. 当前 session posture 在 workspace index / UI/CLI summary 中更可见。
4. 没有因长任务 continuity 增强而破坏现有 recovery 语义。
5. 存在测试或等价高信号验证。

### P3 Acceptance

`P3` 只有在以下条件全部满足时才算完成：

1. native / external adapter contract 更统一。
2. governance / approval / evidence / recovery 语义在两个 executor 面前更一致。
3. comparative benchmark 可以更自然地比较两者，而不依赖分裂 schema。
4. external hot-plug 仍可用。
5. 存在测试或等价高信号验证。

### Shared Productization Evidence Contract

为避免“代码里有字段，但产品证据没有共享语义”，本 goal 下列 evidence surface 应被视为同一组 productization contract 的不同投影：

1. runtime payload
2. workspace index
3. UI execution summary
4. CLI execution summary
5. 文档与 evidence narrative

至少应共享并可互相对应以下几类字段或等价证据：

- `session_continuity`
  - `resume_supported`
  - `resume_kind`
  - `compaction_stage`
  - `latest_recovery_hint`
- `runtime_cost`
  - `duration_seconds`
  - `usage_cost_measurement_status`
- `native_tool_usage`
  - `tool_count`
  - `trace_count`
  - `recent_tools`
- `planner decision evidence`
  - `agent_orchestrator.native_planner_decision.v1`
  - selected strategy / decision boundary / native work-unit ownership
- `adapter capability surface`
  - `agent_orchestrator.adapter_capability_surface.v1`
  - governance
  - evidence outputs
  - recovery surfaces
  - `comparison_mode=same_contract_two_executors`
- `comparative benchmark`
  - `shared_evidence_surface`
  - `runtime_event_stream`
  - `workspace_index`
  - `ui_execution_summary`
  - `cli_execution_summary`
  - `evidence_report`

如果这些 surface 之间只能看到局部、互不对应、或语义漂移的字段，则不能视为满足本 goal 的 productization evidence 要求。

## File-Level Verification Targets

以下不是唯一文件名要求，但 goal 完成时必须能在当前仓库中找到等价实现证据。

### P0 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/execution/`
- `src/agent_orchestrator/execution/native_tools.py`
- `src/agent_orchestrator/intake/`
- `tests/`
- 必要文档

### P1 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/strategy/`
- `src/agent_orchestrator/intake/`
- `src/agent_orchestrator/execution/`
- `tests/`
- 必要文档

### P2 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/session/`
- `src/agent_orchestrator/ui_service.py`
- `src/agent_orchestrator/control_plane_workspace.py`
- `src/agent_orchestrator/cli_presenters.py`
- `tests/`
- 必要文档

### P3 File-Level Evidence

应能在以下区域看到真实实现或接入：

- `src/agent_orchestrator/execution/models.py`
- `src/agent_orchestrator/execution/`
- `src/agent_orchestrator/strategy/`
- `src/agent_orchestrator/evidence.py`
- `tests/`
- 必要文档

## Required Verification Evidence

goal 完成前，必须至少具备以下证据组合中的多项：

- 自动化测试
- 集成测试
- CLI 级验证
- runtime/session 直接检查
- workspace index / UI summary / CLI summary 投影检查
- benchmark capture / compare / trend evidence
- artifact / evidence 直接检查
- shared field projection check
  - runtime payload / workspace index / UI summary / CLI summary / docs 对同一 productization contract 的投影应能互相对照

不能只用以下弱证据宣布完成：

- “native agent 看起来更强了”
- 单次人工长任务演示
- 只有 benchmark 文档没有执行语义
- 只有工具 helper 没有真实主链消费
- 只有更复杂 planner 文案没有可回归样例

## Explicit Non-Goals

以下内容不是本 goal 的完成要求，禁止无限扩展进去：

- 全面追平 `opencode` 的所有工具、UI、插件生态和产品表面
- 做完整 IDE / editor product
- 做完整 benchmark 平台产品
- 做与 productization gap 无关的大规模重构
- 一次性覆盖全部 coding task 类型
- 直接进入 RL / GEPA / 权重内化阶段

## Anti-Local-Optimum Guardrail

一旦满足以下条件，就应停止并进入下一个 goal，而不是继续局部优化：

1. native agent 已不再主要卡在工具面、planner 独立性、session continuity、adapter 一致性这四类基础问题。
2. 新增更长链真实任务已有稳定 native 证明链。
3. external hot-plug 仍清晰可用。
4. 与 `opencode` 的剩余差距主要变成：
   - 平台广度
   - 插件生态
   - IDE / UX 厚度
   - 更大范围通用任务覆盖

如果此时剩余工作主要变成以下内容，则必须停下并进入下一 goal：

- 加更多零散工具
- 做更强 UI / IDE / editor polish
- 做插件市场
- 做大规模多代理生态
- 做性能/成本极限优化

## Goal-Mode Short Form

建议用于 goal 模式的短文本如下：

把当前已具备多类默认覆盖能力的 native coding agent，继续推进成更接近 `opencode` 水平的 daily-driver coding agent：围绕 tool surface、native planner、session productization 与 unified native/external adapter ecosystem 四个面，缩小产品厚度与长期任务能力差距，同时保留 governance、approval、evidence、recovery 与 hot-pluggable external fallback/handoff 优势。完整验收、文件级证据与停止条件见 `docs/process/goal-mode-native-agent-productization.md`。
