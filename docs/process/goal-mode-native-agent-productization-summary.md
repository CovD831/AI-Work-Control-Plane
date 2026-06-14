# Native Agent Productization Goal Summary

## One-Paragraph Goal

下一阶段 goal 的核心，不再是继续证明 native path 在更多 bounded task 上可用，而是把当前已经具备默认执行能力的 native coding agent，继续推进成更接近 `research_repos/opencode/` 水平的“可日常使用”的 general coding agent product。目标是围绕 tool surface、native planner、session productization 与 native/external unified adapter ecosystem 四个面，缩小当前项目在产品厚度、工具深度与长期任务完成能力上的差距，同时保留现有 governance、approval、evidence、recovery 与 hot-pluggable external fallback/handoff 优势。

## Four Required Parts

1. `P0 Tool Surface`
   扩 native agent 的读/搜/补丁/验证工具面，使其更像真实 coding copilot，而不只是 bounded execution kernel。
2. `P1 Native Planner`
   把当前 planner 从 compatibility-heavy 路径继续推进成原生 planner，能更独立地决定 explore / clarify / edit / verify / pause / handoff。
3. `P2 Session Productization`
   强化长任务 session 的 compaction、resume、cost/runtime metadata、operator-visible continuity，使 native path 更接近日常主执行器。
4. `P3 Unified Adapter Ecosystem`
   把 native/external 执行统一到更完整的 adapter contract / capability surface 下，保留 governed fallback/handoff，但减少体系割裂。

## Completion Standard

只有当以下条件同时成立，这个 goal 才算完成：

- native path 的工具深度、planner 自主性、session continuity、adapter 一致性都出现真实提升；
- 至少一类比当前更长、更复杂的真实仓库任务能主要依赖 native path 闭环，而不只是 bounded happy-path；
- 与 `opencode` 的差距被明确收敛到“平台广度仍落后，但 daily-driver 主路径已更接近同代际”；
- comparative benchmark、workspace index、runtime/session、UI/CLI summary 与文档能共享同一类 productization 证据；
- external agent 仍可热插拔接入，且 fallback / handoff 继续受治理。

## Shared Evidence Note

完成判定还要求 `session_continuity`、`runtime_cost`、`native_tool_usage`、`planner decision evidence`、`adapter capability surface` 和 `comparative benchmark shared_evidence_surface` 能在 runtime payload / workspace index / UI summary / CLI summary / 文档之间互相对应，而不是只在单点可见。

## Detail File

完整 goal 细节、阶段验收、文件级验收与停止条件见：

[goal-mode-native-agent-productization.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-native-agent-productization.md)
