# Native Agent Platform Gap Goal Summary

## One-Paragraph Goal

把当前项目的 native coding-agent 从“已经具备受治理的执行闭环”推进到“更接近成熟通用 coding-agent 平台的核心能力层”。本 goal 只追求缩小与 `research_repos/opencode/` 的关键基础差距：native tool surface、repository understanding、native planner、native/external agent adapter、operator evidence。它不追求全面追平 `opencode` 的 UI、插件生态、桌面端、Web 端、发行体系和社区规模，只追求让当前项目的 governance-native agent platform 足够可用、可回归、可验收。

## Current Progress Snapshot

- `P0` 已有真实工具/执行链路基础，关键事实可进入 runtime / workspace / CLI 投影。
- `P1` 已有 repository understanding 和单目标推断能力，能支撑不带显式路径的真实代码编辑任务。
- `P2` 已有 native planner 的 next-action 语义，能输出 explore / clarify / edit / verify / pause / handoff / stop。
- `P3` 已有 shared adapter execution fact，native 与 external/legacy 运行事实可通过同一治理链路投影。

## Remaining Gap vs OpenCode

当前剩余差距主要不在“能不能做代码任务”，而在：

1. 更厚的产品面：TUI / Desktop / Web / docs site / release / marketplace / distribution；
2. 更大的生态面：插件、subagent、provider、社区与安装发行能力；
3. 更广的长期面：更多任务类型覆盖、更强性能、更少回归。

也就是说，当前项目和 `opencode` 的主要差距已经从“基础平台能力缺失”收敛到“产品厚度和生态规模”。

## Required Parts

1. `P0 Native Tool Surface`
   扩展 read/search/glob/patch/diff/verify 等核心工具面，让 native agent 能处理更真实的代码修改任务。
2. `P1 Repository Understanding`
   让上下文选择、目标文件发现和代码关系探索进入主链路，而不是只依赖浅层文件列表或显式目标。
3. `P2 Native Planner`
   把 planner 从 compatibility-heavy routing 推进到能明确决定 explore、clarify、edit、verify、pause、handoff 的 native execution planner。
4. `P3 Unified Agent Adapter Evidence`
   让 native agent 与外部 coding agent 共享同一套治理、审批、证据、恢复和 operator 可见事实链。

## Completion Standard

只有当以下条件同时成立，这个 goal 才算完成：

- 至少一类真实代码修改任务可以稳定通过增强后的 native tool surface 和 repository understanding 主链路；
- 任务过程中可以明确看到上下文发现、工具选择、编辑动作、验证结果和 planner 决策；
- native planner 能给出明确的 explore / clarify / edit / verify / pause / handoff 决策，而不是只包装旧分解逻辑；
- native agent 与至少一个外部 agent adapter 或 adapter contract 能投影到同一条治理事实链；
- 已有自动化测试、CLI 验证或 runtime/workspace artifact 证明主链路真实生效。

## Detail File

完整目标意图、终止条件、阶段验收标准、防止局部最优迭代的约束、文件级验证目标与非目标见：

[goal-mode-native-agent-platform-gap.md](/Users/abab/Desktop/AI-Work-Control-Plane/docs/process/goal-mode-native-agent-platform-gap.md)
