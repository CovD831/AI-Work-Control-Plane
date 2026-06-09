# Agent 实习求职材料包

这份材料包的目标不是把项目包装得很满，而是帮你把它讲得**清楚、可信、边界明确**。

当前最推荐的定位是：

> 一个面向长周期本地 coding agent 的外部治理层，负责把状态、审批、证据、恢复和运行时事实外部化，让 agent 工作可恢复、可审计、可安全接管。

## 一、先讲清楚：它是否已经“完全解耦”

最推荐的诚实说法：

> 如果说的是产品定位和主能力边界，这个项目已经基本解耦完成了。它现在不再试图和 Codex、Claude Code 竞争谁更会规划、谁更会写代码，而是把自己定位成这些 coding agent 之上的外部治理层。
>
> 但如果说的是内部实现层面的完全解耦，那还没有 100% 完成。因为仓库里仍然保留了一些历史兼容字段和执行拓扑概念，比如 `StrategyDecision`、`ExecutionTopologySnapshot`、`reviewer`、`rescue` 这类内部术语。不过这些更多是协议和实现细节，不再是项目对外的主卖点。

一句更短的版本：

> 对外已经基本解耦，对内还保留少量兼容型实现术语。

## 二、简历项目描述

### 版本 A：两行版

> 设计并实现一个面向长周期本地 coding agent 的外部治理层，将 workspace state、审批门禁、证据记录、运行时事实与恢复建议外部化为可审计制品，提升 agent 工作的可恢复性与可观测性。
>
> 基于 CLI/UI、持久化 artifact pipeline 和 provider/runtime 适配层构建控制平面，支持本地 `codex` / `claude` CLI 的健康检查、任务执行观测、失败恢复与合规验证。

### 版本 B：三点版

- 设计长周期 agent 工作的外部治理架构，将 `WorkspaceState / ContextPacket / Approval / Evidence / Memory / Recovery` 等能力从模型会话中抽离为可持久化制品。
- 实现本地优先的 control plane CLI/UI，支持 workspace 状态检查、证据门禁、恢复建议、运行时观测与治理控制台。
- 打通 provider/runtime 适配与验证链路，完成本地 `Codex CLI`、`Claude Code CLI` 的健康检查与 command runtime 验证，并用回归测试覆盖关键 artifact contract 和 workflow。

### 版本 C：偏 agent 岗版本

> 核心项目：AI Work Control Plane。项目聚焦 agent reliability / governance，而不是传统 RAG 或 workflow 编排。通过外部化状态、审批、证据、运行时事实和恢复建议，让长周期 coding agent 在真实工程任务中更可恢复、更可审计、更容易被 human-in-the-loop 治理。

## 三、30 秒自我介绍

> 我做过一个叫 AI Work Control Plane 的项目。它不是再做一个 coding agent，而是做 coding agent 之上的外部治理层。我的核心思路是，把长任务里真正关键但容易丢在模型会话里的东西，比如状态、审批、证据、运行时事实和恢复建议，外部化成可持久化 artifact。这样 agent 不只是“能跑任务”，而是能在长周期工程里被检查、恢复和安全接管。

## 四、90 秒项目介绍

> 我这个项目最早有比较重的执行编排色彩，但后来我把重点收口成了 control plane。因为我觉得随着模型能力越来越强，很多显式 planning、review、tool orchestration 最终都会逐渐被 provider 自己内化；真正长期有价值的，是模型外部的工作系统。
>
> 所以我现在把这个项目定位成一个面向长周期本地 coding agent 的外部治理层。它主要解决三个问题：第一，长任务里的状态很容易散落在临时会话里，中断后很难恢复；第二，很多 agent 系统只能看到结果，看不到执行中的门禁、失败和降级；第三，人类很难在风险点上稳定介入。
>
> 我做的事情，就是把这些能力外部化成一条稳定的 artifact pipeline，比如 `WorkspaceState`、`ContextPacket`、`StrategyDecision`、`ApprovalItem`、`EvidenceBundle`、`MemoryRecord`。再往下，它通过 CLI、UI 和 provider/runtime adapter 去接住真实执行，包括本地 `Codex CLI`、`Claude Code CLI` 的健康检查和 command runtime 验证。
>
> 所以这个项目的核心价值，不是“我又造了几个 agent 角色”，而是我把长周期 agent 工作里的治理、恢复和审计能力，从模型内部挪到了系统外部。

## 五、黄金 Demo 讲稿

推荐把演示控制在 3 分钟左右。

### Demo 主线

1. `team start`

你可以这样说：

> 我先从一个真实工程任务开始，不是直接让 agent 去写代码，而是先创建一个受治理的 plan session。这样系统会先生成外部状态，而不是把一切都留在模型会话里。

2. `team workspace-status`

> 这里我展示的不是聊天记录，而是外部化后的 workspace / program state。面试官可以看到当前 session、run、job、approval、memory 和恢复相关信息，这说明系统的长期状态不依赖单次 provider session。

3. `team evidence-gates`

> 接着我会展示 evidence gate。这个步骤体现的是：系统不是“想执行就执行”，而是先检查证据、合规和门禁状态。也就是说，agent 工作在这里是被治理的。

4. `team execute`

> 然后我才让系统进入执行。这里真正的代码生成和任务推进仍然可以由底层 provider/runtime 来做，但控制权和治理信息并不属于 provider，而是属于 control plane。

5. `team runtime inspect <job-id>` 或 `ui`

> 最后我展示 runtime inspection 或治理控制台。这里可以看到 provider health、runtime measurement、degraded reason、operation receipt，以及如果任务失败或中断，系统会给出什么恢复建议。

### Demo 结尾一句话

> 所以这个项目证明的不是“我也做了个 coding agent”，而是“我把 coding agent 在长周期任务里的治理闭环补出来了”。

## 六、面试官追问“那它和 Codex / Claude Code 到底怎么分工”时怎么答

推荐答案：

> 我现在会把分工说得很明确。Codex、Claude Code 这类系统更像底层执行者和 provider session owner，它们负责具体思考、改代码、调用工具和推进单次会话。我的项目不跟它们争这个位置。
>
> 我的项目负责的是更上层的外部治理能力，比如跨 session 的 workspace/program state、approval gate、evidence bundle、provider/runtime health、recovery recommendation 和 memory provenance。也就是说，session 可以属于 provider，但 program state 应该属于 control plane。

## 七、如果被追问“那为什么还保留 StrategyDecision / Topology 这些东西”

推荐答案：

> 这是一个很好的问题。我的理解是，这些东西现在更像控制平面里的治理摘要和只读执行路径快照，而不是要替 provider 做 planning brain。它们保留的原因主要是为了把“当前为什么这样推进、当前边界是什么、当前门禁和恢复点在哪”沉淀成可检查的外部 artifact，而不是继续把这些判断埋在单次模型会话里。

## 八、最容易踩坑的说法

下面几种表达尽量不要作为开场：

- “我做了一个多 agent 编排系统。”
- “我做了很多 reviewer、rescue、adversarial reviewer 角色。”
- “这个项目本质上比 Codex/Claude Code 更完整。”
- “我主要是定方向，具体细节我不太清楚。”

更好的替代说法：

- “我做的是长周期 coding agent 的外部治理层。”
- “我重点做的是状态外部化、审批门禁、证据记录和恢复闭环。”
- “我不和 provider 竞争执行本身，而是补它们外部的治理能力。”
- “我主导了架构边界和核心模块收敛，也补了 provider/runtime 验证链路。”

## 九、最后的推荐收尾

如果面试官问你“这个项目最有价值的判断是什么”，最推荐你说：

> 我觉得最重要的判断，是意识到显式 agent 编排未必是长期壁垒，但外部治理能力一定是。因为模型会越来越会自己规划和执行，但状态、审批、证据、恢复和审计不会自然消失，它们反而会越来越重要。
