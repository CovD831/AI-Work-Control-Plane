# AI-Work-Control-Plane 面试准备手册

这份手册不是为了让你背定义，而是为了让你在找 `agent` 相关实习时，能把这个项目讲成一个清楚、可信、有技术深度的核心项目。

建议你把整套表达分成三层：

1. 先用 30 秒讲清楚项目是什么。
2. 再用 2 分钟讲清楚它解决了什么问题、系统怎么工作。
3. 最后根据面试官追问，往架构、恢复、运行时、测试这些点深入。

## 一、30 秒版本

### 一句话介绍

> 我做了一个面向长周期 coding agent 的本地优先控制平面，把 agent 的计划、上下文、审批、证据、运行时状态和恢复信息外部化成可审计制品，让 agent 在长任务里更可恢复、更可检查、也更容易被人类治理。

### 更口语一点的版本

> 很多 agent 系统短任务跑得还可以，但一旦任务变长，状态、审批和恢复信息都容易丢在模型会话里。我这个项目做的事情，是把这些关键控制能力从模型里抽出来，放进系统外部的 artifact 和 workflow 里。

## 二、2 分钟版本

### 项目是做什么的

你可以这样讲：

> 这个项目最早确实有比较重的执行编排成分，但我后来把重点收拢成了控制平面。因为我觉得随着模型能力变强，很多显式编排最终会被模型自己内化，真正长期有价值的是模型外部的工作系统，比如状态持久化、上下文压缩、审批门禁、证据记录、运行时可观测性和中断恢复。
>
> 所以这个项目现在的核心，不是“造更多 agent 角色”，而是“让 coding agent 在长周期任务中变得可靠”。系统围绕一条 artifact pipeline 工作：`WorkspaceState -> ContextPacket -> StrategyDecision -> ExecutionTopologySnapshot -> ApprovalItem -> EvidenceBundle -> MemoryRecord`。每一种制品都承担明确职责，整体目标是让 agent 工作具备可恢复、可审计、可治理的外部控制回路。

### 它解决了什么问题

可以拆成 3 点：

1. **状态丢失**
   agent 做长任务时，中间状态经常散落在临时会话里，中断后很难恢复。

2. **执行不可见**
   很多系统只能看到最终结果，看不到过程中的决策、审批、失败和降级。

3. **人类难以介入**
   当任务有风险、需要确认、或者 evidence 不够时，系统缺少明确的人类接管点。

### 我的解决思路

> 我没有把重心放在“让 agent 更像公司组织架构”，而是把重点放在外部治理能力上。也就是说，agent 可以继续执行任务，但关键的状态、证据、审批和恢复能力必须留在模型外部，而且要有稳定 schema、CLI/UI surface 和测试兜底。

## 三、面试官最常问的基础问题

### Q1：为什么你把它叫做控制平面？

**建议回答：**

> 这个说法借用了网络里的 control plane 概念。执行平面负责“做事”，控制平面负责“决定怎么推进、是否允许推进、出了问题怎么恢复”。在这个项目里，我关心的是 agent 工作如何被治理，而不是只关心 agent 怎么跑完一次任务。

### Q2：它和普通 agent framework 有什么不同？

**建议回答：**

> 很多 agent framework 更关注角色编排、任务拆分和工具调用；这个项目更关注长周期运行时的可靠性问题。它的重点不是多造几个 agent，而是把 agent 工作里的状态、审批、证据、恢复这些能力外部化，让系统对长任务更稳定。

### Q3：这个项目最重要的转向是什么？

**建议回答：**

> 最关键的转向就是从“执行编排”转到“控制平面”。我后来意识到，显式编排本身未必是长期壁垒，因为模型会越来越会自己规划和调用工具；但外部状态、审批、证据、恢复和审计这些系统能力，不会自然消失，反而会越来越重要。

### Q4：这个项目现在更适合怎么定位？

**建议回答：**

> 我现在会把它定位成一个 `agent reliability / governance infrastructure` 项目，更具体一点，是一个面向长周期 coding agent 的本地优先控制平面。

## 四、架构问题怎么答

### Q5：项目的核心架构是什么？

**建议回答：**

> 可以分成两层看。
>
> 第一层是**控制平面**，也就是 artifact pipeline：
> `WorkspaceState -> ContextPacket -> StrategyDecision -> ExecutionTopologySnapshot -> ApprovalItem -> EvidenceBundle -> MemoryRecord`
>
> 第二层是**实现层**，包括 planning governance、execution orchestration、provider/runtime adapter、CLI/UI operator surface。
>
> 控制平面负责把关键状态和治理信息外部化；实现层负责把这些能力真正跑起来。

### Q6：为什么要拆这么多制品？

**建议回答：**

> 因为这些信息的职责不一样，如果混在一起，会导致状态和决策难以审计。比如 `ContextPacket` 只负责给模型最小充分上下文，不负责做策略选择；`StrategyDecision` 只记录下一步为什么这么做，不直接执行；`ApprovalItem` 把人类介入变成一等公民；`EvidenceBundle` 则是门禁摘要，而不是普通日志。

### Q7：为什么 `ContextPacket` 和 `StrategyDecision` 要分开？

**建议回答：**

> 这是我觉得很关键的一个边界。`ContextPacket` 是“提供信息”，`StrategyDecision` 是“基于信息做判断”。把两者拆开之后，职责更清楚，也更容易测试、复用和审计。否则你很难回答系统到底是“信息不完整”还是“决策不合理”。

### Q8：什么是 AI 原生角色模型？

**建议回答：**

> 这里的角色不是 CEO、Leader、Employee 这种人类组织映射，而是 artifact transformer。比如 `state_keeper` 负责生成状态制品，`context_compressor` 负责上下文压缩，`approval_gate` 负责审批制品，`memory_curator` 负责记忆制品。这样设计更符合 agent 系统的真实职责划分。

## 五、技术实现问题怎么答

### Q9：这个项目的核心代码你最建议看哪几块？

**建议回答：**

> 如果从面试角度看，我最建议看 5 块：
>
> 1. `src/agent_orchestrator/control_plane.py`
>    这里是 artifact builder 的核心。
> 2. `src/agent_orchestrator/planning.py`
>    这里能看 planning governance 和 session 生命周期。
> 3. `src/agent_orchestrator/orchestrator.py`
>    这里是执行编排、异步 run、reroute、resume 的核心。
> 4. `src/agent_orchestrator/control_plane_runtime.py`
>    这里能看到 runtime event stream 和 provider session snapshot。
> 5. `src/agent_orchestrator/ui_service.py`
>    这里体现 operator-facing surface 怎么从底层 store 拼装出来。

### Q10：长周期任务恢复是怎么做的？

**建议回答：**

> 恢复能力主要依赖几类制品一起工作：workspace index、run ledger、recovery timeline、runtime event stream 和 recovery recommendation。系统不会只记录“失败了”，而是尽量记录任务处在哪个阶段、因为什么阻塞、上一次 checkpoint 在哪、最安全的下一步命令是什么。这样恢复逻辑就不是靠人手工翻 JSON 猜，而是有显式 artifact 支撑。

### Q11：runtime event stream 和普通日志有什么区别？

**建议回答：**

> 普通日志更像文本记录，而 runtime event stream 是结构化制品。它记录的是运行时模式、provider、任务意图、结果状态、失败原因、降级原因、artifact 引用这些系统级事实。这样它既能给 UI/CLI 消费，也能给恢复和治理逻辑消费。

### Q12：审批在系统里扮演什么角色？

**建议回答：**

> 审批不是附属流程，而是一等制品。只要系统发现阻塞态、风险态、证据不足或者需要人类确认的场景，就会生成 `ApprovalItem`。这样 human-in-the-loop 就不是隐含的，而是有持久化记录和明确后续动作的。

### Q13：memory 在这个项目里是什么定位？

**建议回答：**

> memory 不是“把所有历史都塞给模型”，而是带 provenance 和 freshness 的可管理记忆。它更像外部工作记忆的一部分，用来支持上下文压缩、结果追踪和恢复，但不会替代控制平面的其他制品。

## 六、工程性问题怎么答

### Q14：这个项目怎么验证自己不是空架子？

**建议回答：**

> 我觉得最重要的验证有三个。
>
> 第一，它不是只有文档，仓库里有完整的 CLI、artifact builder、runtime state、UI service 和测试。
>
> 第二，它已经形成了比较稳定的 schema 和 operator workflow，而不是一堆概念命名。
>
> 第三，测试规模比较完整，我本地验证时 `pytest -q` 是 `424 passed`，说明主要控制平面能力和关键 workflow 至少在仓库内是被持续回归覆盖的。

### Q15：你们是怎么测试的？

**建议回答：**

> 测试大体分几层：artifact 和领域模型的单元测试、CLI 和 orchestration 的集成测试、UI service 的结构测试，以及流程/文档合规类测试。这样做的原因是，这个项目很多价值在于“schema 稳定”和“流程状态正确”，所以测试不只是测函数输出，也要测制品 contract 和 workflow 行为。

### Q16：你会怎么诚实地讲这个项目的边界？

**建议回答：**

> 我会明确说，这个项目现在最强的部分是 governance、state externalization、evidence、recovery 和 operator surface；它不是一个已经完全打通所有 provider 的通用 autonomous agent platform。有些 provider/runtime 能力目前仍然是轻量集成或者 mock，这部分我不会过度包装。

## 七、如果面试官追问“你个人做了什么”

这是你最需要提前准备的部分，因为你自己也提到现在对细节掌握不够深。

### 推荐回答方式

不要只说“我把控了方向”，可以改成这样：

> 我主要负责的是项目方向、核心架构边界和关键模块的收敛，尤其是从执行编排转向控制平面的这次重构。具体到实现层，我重点推进和理解的是 artifact pipeline、planning governance、runtime telemetry 和 recovery 这些主干能力。虽然仓库内容很多，我不会声称自己对每个细节都同样深入，但我能清楚解释核心模块的职责、设计动机和它们怎么协同工作。

这类回答比“我只是负责大方向”更好，因为它既诚实，也保留了 ownership。

## 八、推荐你主动强调的亮点

如果面试官给你开放发挥空间，建议优先讲这几个：

1. **从编排转向控制平面的判断**
   这体现你的产品和架构判断力。

2. **把恢复能力做成显式 artifact**
   这比普通 agent demo 更有系统味道。

3. **把审批和 evidence 变成一等能力**
   这说明你在想真实生产约束，而不是只想 agent 自主性。

4. **CLI/UI 都有 operator surface**
   这能证明项目不是只停留在库层。

5. **完整测试体系**
   这能显著降低“这个项目是不是很虚”的质疑。

## 九、推荐你少讲的点

下面这些不建议放在开头：

1. 太多抽象术语，比如一上来就讲 control plane 哲学。
2. 过多介绍人类组织架构式 agent 角色。
3. 讲太多未来愿景，而不是当前已经完成的能力。
4. 试图把仓库里每个模块都介绍一遍。

你的目标不是“证明项目特别大”，而是“证明项目特别清楚、特别真实、特别适合 agent 岗”。

## 十、最推荐的一段完整自我讲述

你可以把下面这段练熟：

> 我这个项目最开始更偏执行编排，但后来我做了一个比较关键的收敛，就是把核心转成了一个面向长周期 coding agent 的控制平面。因为我觉得未来模型会内化越来越多编排能力，但状态持久化、审批、人类接管、证据记录、运行时可观测性和中断恢复这些能力，仍然需要外部系统来承担。
>
> 所以我把项目的主线放在 artifact pipeline 上，让 `WorkspaceState`、`ContextPacket`、`StrategyDecision`、`ApprovalItem`、`EvidenceBundle`、`MemoryRecord` 这些制品分别承担明确职责。这样 agent 做长任务时，不再只是“跑一次 prompt”，而是有一个可治理、可续跑、可审计的外部工作系统。
>
> 从工程实现上，项目包含 CLI、UI、runtime event stream、recovery recommendation、plan session governance，以及比较完整的自动化测试。对我来说，这个项目最重要的价值不是“造了多少 agent”，而是把 agent 长任务运行里的可靠性问题做成了一个系统化产品。

## 十一、你接下来最该补的 3 件事

如果你要拿这个项目当核心项目，最值得马上补的是：

1. 把 `control_plane.py`、`orchestrator.py`、`control_plane_runtime.py` 这 3 个模块吃透。
2. 练熟一条 `start -> workspace-status -> evidence-gates -> execute -> inspect-execution` 的 demo。
3. 准备一个诚实版本的“哪些做完了，哪些还在边界内”的回答。

## 十二、最后提醒

面试时你不需要把自己包装成“全都懂、全都写过”。

你更需要传达的是：

- 你看到了 agent 长任务里的真实问题
- 你做了一个有架构判断的系统收敛
- 你不是停留在概念，而是落到了 artifact、workflow、CLI/UI 和测试
- 你能诚实说明边界，也能清楚说明核心价值
