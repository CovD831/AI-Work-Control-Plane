# 执行平面深度解析

## 执行平面概览

执行平面是项目的早期核心，负责实际执行智能体工作。它采用**三层分离架构**：

```
┌─────────────────────────────────────────────────────────────┐
│                    执行平面 (Execution Plane)                │
├─────────────────────────────────────────────────────────────┤
│  决策核心层 (Decision Core)                                  │
│  - 职责：决定"该不该做、怎么做、做到什么程度才能继续往下走"      │
│  - 模块：planning.py, guards.py, planning_support.py        │
├─────────────────────────────────────────────────────────────┤
│  执行拓扑层 (Execution Topology)                             │
│  - 职责：决定"任务用什么 agent 协作形态来完成"                 │
│  - 模块：orchestrator.py, tasks.py, work_graph.py           │
├─────────────────────────────────────────────────────────────┤
│  Provider / Runtime 层                                      │
│  - 职责：决定"具体由谁执行，以及怎样把执行过程跑起来并记录下来" │
│  - 模块：command.py, adapters.py, jobs.py                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 第一层：决策核心层 (Decision Core)

### 核心职责
决定"该不该做、怎么做、做到什么程度才能继续往下走"

### 核心模块

#### 1. planning.py - 计划会话管理

**数据结构：**
```python
@dataclass
class PlanSession:
    session_id: str
    status: PlanSessionStatus  # intake_chat, draft_ready, adversarial_review, etc.
    rounds: list[Round]
    gaps: list[Gap]
    approved_plan: dict | None
    execution_contract: ExecutionContract | None
```

**状态机：**
```
intake_chat -> draft_ready -> adversarial_review -> awaiting_human_confirmation 
-> approved_for_execution -> executing -> accepted
```

**核心方法：**
- `create_session()` - 创建计划会话
- `submit_review()` - 提交审查
- `approve_plan()` - 批准计划
- `execute_plan()` - 执行计划

#### 2. guards.py - 权限守卫

**核心功能：**
- `validate_execution_gate()` - 验证执行门禁
- `validate_artifact_write()` - 验证制品写入权限
- `validate_role_state_action()` - 验证角色操作权限

**执行门禁逻辑：**
```python
def validate_execution_gate(contract: ExecutionContract) -> bool:
    """验证执行合约是否满足执行条件"""
    # 检查合约是否完整
    # 检查是否获得批准
    # 检查是否满足合规要求
    return is_valid
```

#### 3. planning_support.py - 合规检查和会话指导

**核心功能：**
- `build_compliance_status_for_session()` - 构建会话合规状态
- `build_session_guidance()` - 构建会话指导
- `build_document_context_package()` - 构建文档上下文包

**合规检查内容：**
- 必需文档存在性
- 工作流文档引用
- 操作手册信号
- 执行来源匹配
- 上下文快照存在性

### 数据流转

```
用户需求 -> PlanSession -> RoundController -> GapClosure 
-> ApprovedPlan -> ExecutionContract -> 执行
```

---

## 第二层：执行拓扑层 (Execution Topology)

### 核心职责
决定"任务用什么 agent 协作形态来完成"

### 核心模块

#### 1. orchestrator.py - 端到端编排管道

**核心数据结构：**
```python
@dataclass
class Orchestrator:
    planner: PlannerAdapter          # 计划适配器
    decomposer: DecomposerAdapter    # 分解适配器
    worker: WorkerAdapter            # 工作器适配器
    reviewer: ReviewRescueAdapter    # 审查救援适配器
    router: PolicyRouter             # 策略路由器
    failure_router: FailureRouter    # 失败路由器
    run_store: RunStore              # 运行存储
```

**核心方法：**
```python
def start_run(
    self,
    requirement: str,
    mode: OrchestrationMode | None = OrchestrationMode.SUCCESS_FIRST,
    reroute: bool = True,
    parent_run_id: str | None = None,
    agent_enabled: bool | None = None,
    depth: int | None = None,
    review_policy_override: str | None = None,
    provider_health_snapshot: dict[str, object] | None = None,
) -> OrchestrationRunHandle:
    """启动编排运行"""
    # 1. 路由决策
    routing_decision = self.router.route(requirement)
    policy = get_policy(routing_decision.mode)
    
    # 2. 创建运行
    run = OrchestrationRun(...)
    self._store_run(run)
    
    # 3. 后台执行
    thread = threading.Thread(target=self._background_run, ...)
    thread.start()
    
    return OrchestrationRunHandle(...)
```

**执行流程：**
```
start_run() -> 路由决策 -> 创建运行 -> 后台执行 -> poll_run()
```

#### 2. tasks.py - 任务合约和工作单元

**核心数据结构：**
```python
@dataclass
class TaskContract:
    goal: str
    non_goals: list[str]
    context: str
    inputs: list[str]
    outputs: list[str]
    acceptance_criteria: list[str]
    risk_level: RiskLevel
    parallelizable: bool
    owner_type: str
    max_depth: int
    failure_policy: str

@dataclass
class WorkUnit:
    goal: str
    context: str
    inputs: list[str]
    outputs: list[str]
    acceptance_criteria: list[str]
    risk_level: RiskLevel
    parallelizable: bool
    owner_type: str
    max_depth: int
    failure_policy: str
    provider_hint: str
    depends_on: list[str]

@dataclass
class ExecutionContract:
    goal: str
    work_units: list[WorkUnit]
    topology: TopologyName
    policy: PolicyProfile
```

#### 3. work_graph.py - 持久化工作图

**核心功能：**
- `build_initial_work_graph()` - 构建初始工作图
- `next_executable_node()` - 获取下一个可执行节点
- `WorkGraphStore` - 工作图持久化存储

**工作图结构：**
```python
@dataclass
class WorkGraphNode:
    node_id: str
    work_unit: WorkUnit
    status: NodeStatus  # pending, ready, running, completed, failed
    dependencies: list[str]
    results: list[WorkUnitResult]
```

#### 4. topology.py - 执行拓扑助手

**拓扑类型：**
- `solo` - 单智能体执行
- `team` - 多智能体协作
- `team_with_adversarial_review` - 带对抗性审查的团队
- `cluster` - 集群模式

**构建拓扑：**
```python
def build_execution_topology(
    contract: ExecutionContract,
    work_graph: WorkGraph,
) -> ExecutionTopology:
    """构建执行拓扑"""
    # 根据合约和工作图构建拓扑
    return topology
```

### 数据流转

```
ExecutionContract -> WorkGraph -> ExecutionTopology -> 执行调度
```

---

## 第三层：Provider / Runtime 层

### 核心职责
决定"具体由谁执行，以及怎样把执行过程跑起来并记录下来"

### 核心模块

#### 1. adapters.py - 适配器接口和实现

**适配器接口：**
```python
class PlannerAdapter(Protocol):
    """将模糊需求转换为清晰的任务合约"""
    def clarify(self, requirement: str, policy: PolicyProfile) -> TaskContract:

class DecomposerAdapter(Protocol):
    """将清晰的任务合约分解为可执行的工作单元"""
    def decompose(self, contract: TaskContract, policy: PolicyProfile) -> list[WorkUnit]:

class WorkerAdapter(Protocol):
    """执行单个工作单元"""
    def execute(self, work_unit: WorkUnit, policy: PolicyProfile) -> WorkUnitResult:

class ReviewRescueAdapter(Protocol):
    """审查或救援工作者输出"""
    def review_or_rescue(
        self,
        work_unit: WorkUnit,
        result: WorkUnitResult,
        policy: PolicyProfile,
    ) -> WorkUnitResult:
```

**实现类：**
- `MockClaudePlanner` - 模拟 Claude 计划（用于测试）
- `MockClaudeDecomposer` - 模拟 Claude 分解
- `MockCodexWorker` - 模拟 Codex 工作
- `MockClaudeReviewRescue` - 模拟 Claude 审查救援

#### 2. command.py - 命令执行和 CLI 适配

**核心数据结构：**
```python
@dataclass
class CommandSpec:
    command: list[str]
    env: dict[str, str] | None = None

@dataclass
class CommandResult:
    command: list[str]
    exit_code: int | None
    stdout: str
    stderr: str
    error: str | None = None

class ProviderSession(Protocol):
    session_id: str
    thread_id: str
    
    def poll(self) -> CommandResult | None:
    def wait(self, timeout: int | None = None) -> CommandResult:
    def send(self, message: str) -> dict[str, Any]:
    def cancel(self) -> dict[str, Any]:
```

**适配器实现：**
- `ClaudeCodeAdapter` - Claude Code CLI 适配
- `CodexCliAdapter` - Codex CLI 适配
- `SubprocessCommandRunner` - 子进程命令运行器
- `SubprocessCommandSession` - 子进程命令会话

#### 3. jobs.py - 作业生命周期管理

**核心数据结构：**
```python
@dataclass
class AgentJob:
    job_id: str
    request: JobRequest
    result: JobResult | None
    status: str  # queued, running, completed, failed
    created_at: str
    updated_at: str

@dataclass
class JobRequest:
    provider: Provider
    command: list[str]
    env: dict[str, str] | None
    timeout: int | None
    metadata: dict[str, object]

@dataclass
class JobResult:
    status: str
    exit_code: int | None
    stdout: str
    stderr: str
    error: str | None
    duration_ms: int | None
    provider_metadata: dict[str, object]
```

**运行时类型：**
- `InMemoryJobRuntime` - 内存作业运行时（用于测试）
- `FileJobRuntime` - 文件作业运行时（用于持久化）
- `CommandJobRuntime` - 命令作业运行时（用于真实执行）

### 数据流转

```
WorkUnit -> JobRequest -> AgentJob -> CommandResult -> WorkUnitResult
```

---

## 完整执行流程

### 1. 启动阶段

```python
# 用户发起请求
orchestrator.start_run(
    requirement="实现一个功能",
    mode=OrchestrationMode.SUCCESS_FIRST
)

# 路由决策
routing_decision = router.route(requirement)
policy = get_policy(routing_decision.mode)

# 创建运行
run = OrchestrationRun(
    run_id="run-12345678",
    requirement="实现一个功能",
    initial_mode=routing_decision.mode,
    final_mode=policy.mode,
    ...
)
```

### 2. 计划阶段

```python
# 计划适配器澄清需求
task_contract = planner.clarify(requirement, policy)

# 分解适配器分解任务
work_units = decomposer.decompose(task_contract, policy)

# 构建执行合约
execution_contract = ExecutionContract(
    goal=requirement,
    work_units=work_units,
    topology=topology,
    policy=policy,
)
```

### 3. 执行阶段

```python
# 构建工作图
work_graph = build_initial_work_graph(work_units)

# 获取下一个可执行节点
next_node = next_executable_node(work_graph)

# 工作器执行
result = worker.execute(next_node.work_unit, policy)

# 审查救援
review_result = reviewer.review_or_rescue(
    next_node.work_unit, result, policy
)
```

### 4. 完成阶段

```python
# 记录结果
run.results.append(review_result)

# 更新状态
run.status = "completed"

# 持久化
run_store.save(run)
```

---

## 关键设计模式

### 1. 适配器模式

**应用场景：** Provider 集成

**优势：**
- 核心逻辑不依赖具体 Provider
- 可以用 Mock 适配器测试
- 可以轻松添加新 Provider

**实现：**
```python
# 接口
class WorkerAdapter(Protocol):
    def execute(self, work_unit: WorkUnit, policy: PolicyProfile) -> WorkUnitResult:

# 实现
class MockCodexWorker:
    def execute(self, work_unit: WorkUnit, policy: PolicyProfile) -> WorkUnitResult:
        # 模拟执行
        return WorkUnitResult(...)

class CodexCliAdapter:
    def execute(self, work_unit: WorkUnit, policy: PolicyProfile) -> WorkUnitResult:
        # 真实执行
        result = subprocess.run(["codex", ...])
        return WorkUnitResult(...)
```

### 2. 状态机模式

**应用场景：** 计划会话管理

**优势：**
- 状态流转清晰
- 支持恢复和审计
- 可预测性强

**实现：**
```python
PlanSessionStatus = Literal[
    "intake_chat",
    "draft_ready",
    "adversarial_review",
    "awaiting_human_confirmation",
    "approved_for_execution",
    "executing",
    "accepted",
]

# 状态流转
def transition_status(current: PlanSessionStatus, action: str) -> PlanSessionStatus:
    if current == "intake_chat" and action == "submit_draft":
        return "draft_ready"
    elif current == "draft_ready" and action == "start_review":
        return "adversarial_review"
    # ...
```

### 3. 策略模式

**应用场景：** 策略路由

**优势：**
- 灵活配置
- 可扩展性强
- 可测试性好

**实现：**
```python
OrchestrationMode = Literal[
    "success_first",
    "speed_first",
    "cost_first",
    "auto",
]

def get_policy(mode: OrchestrationMode) -> PolicyProfile:
    if mode == "success_first":
        return PolicyProfile(
            review_required=True,
            rescue_enabled=True,
            max_depth=3,
            ...
        )
    elif mode == "speed_first":
        return PolicyProfile(
            review_required=False,
            rescue_enabled=False,
            max_depth=1,
            ...
        )
```

### 4. 事件溯源模式

**应用场景：** 审计追踪

**优势：**
- 完整的状态变更历史
- 支持恢复和审计
- 可追溯性强

**实现：**
```python
@dataclass
class OrchestrationRun:
    events: list[dict]  # 事件日志
    
    def add_event(self, event_type: str, data: dict):
        self.events.append({
            "event": event_type,
            "timestamp": now_iso(),
            "data": data,
        })

# 使用
run.add_event("run_queued", {"run_id": run.run_id})
run.add_event("run_started", {"run_id": run.run_id})
run.add_event("run_completed", {"run_id": run.run_id, "result": "success"})
```

---

## 协作形态详解

### 1. Solo 模式

**场景：** 简单任务，单智能体执行

**流程：**
```
用户需求 -> TaskContract -> WorkUnit -> Worker -> Result
```

**特点：**
- 无需协作
- 执行快速
- 适合简单任务

### 2. Team 模式

**场景：** 复杂任务，多智能体协作

**流程：**
```
用户需求 -> TaskContract -> WorkUnits -> Worker1, Worker2, ... -> Results -> Reviewer -> FinalResult
```

**特点：**
- 并行执行
- 任务分解
- 适合复杂任务

### 3. Team with Adversarial Review 模式

**场景：** 高风险任务，需要对抗性审查

**流程：**
```
用户需求 -> TaskContract -> WorkUnits -> Workers -> AdversarialReviewer -> Revision -> FinalResult
```

**特点：**
- 对抗性审查
- 质疑和补全
- 适合高风险任务

### 4. Cluster 模式

**场景：** 大规模任务，集群执行

**流程：**
```
用户需求 -> TaskContract -> WorkUnits -> Cluster1, Cluster2, ... -> Results -> Aggregator -> FinalResult
```

**特点：**
- 分布式执行
- 结果聚合
- 适合大规模任务

---

## 失败处理机制

### 1. 失败路由 (FailureRouter)

**功能：** 根据失败类型决定重新路由策略

**失败类型：**
- Provider 失败 - 切换 Provider
- 超时失败 - 重试或降低复杂度
- 权限失败 - 请求权限或跳过

**路由策略：**
```python
def route_failure(failure: FailureSignal) -> FailureDecision:
    if failure.type == "provider_failed":
        return FailureDecision(
            action="reroute",
            target_mode="cost_first",
            reason="Provider failed, switching to cost_first mode"
        )
    elif failure.type == "timeout":
        return FailureDecision(
            action="retry",
            target_mode=None,
            reason="Timeout, retrying with same mode"
        )
```

### 2. 救援适配器 (ReviewRescueAdapter)

**功能：** 救援失败的工作单元

**救援策略：**
- 重试 - 使用相同参数重试
- 降级 - 使用更简单的参数重试
- 跳过 - 跳过失败的工作单元

**实现：**
```python
def review_or_rescue(
    self,
    work_unit: WorkUnit,
    result: WorkUnitResult,
    policy: PolicyProfile,
) -> WorkUnitResult:
    if result.status == "failed":
        if policy.rescue_enabled:
            # 救援策略
            return self.rescue(work_unit, result, policy)
        else:
            # 直接返回失败结果
            return result
    else:
        # 审查成功结果
        return self.review(work_unit, result, policy)
```

---

## 测试策略

### 1. 单元测试

**测试单个模块功能：**
```python
def test_planner_clarify():
    planner = MockClaudePlanner()
    contract = planner.clarify("实现一个功能", policy)
    assert contract.goal == "实现一个功能"
    assert contract.risk_level in ["low", "medium", "high"]
```

### 2. 集成测试

**测试模块间交互：**
```python
def test_orchestrator_start_run():
    orchestrator = Orchestrator(
        planner=MockClaudePlanner(),
        decomposer=MockClaudeDecomposer(),
        worker=MockCodexWorker(),
        reviewer=MockClaudeReviewRescue(),
    )
    handle = orchestrator.start_run("实现一个功能")
    assert handle.status == "queued"
```

### 3. CLI 测试

**测试命令行接口：**
```python
def test_cli_start_run():
    result = subprocess.run(
        ["python", "-m", "agent_orchestrator.cli", "run", "实现一个功能"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "run_id" in result.stdout
```

---

## 总结

执行平面是项目的核心执行引擎，通过三层分离架构实现了：

1. **决策核心层** - 决定"该不该做、怎么做"
2. **执行拓扑层** - 决定"用什么协作形态"
3. **Provider/Runtime层** - 决定"具体由谁执行"

**关键设计：**
- 适配器模式 - 支持多种 Provider
- 状态机模式 - 管理状态流转
- 策略模式 - 支持不同优先级
- 事件溯源 - 完整审计追踪

**协作形态：**
- Solo - 单智能体执行
- Team - 多智能体协作
- Team with Adversarial Review - 对抗性审查
- Cluster - 集群执行

**失败处理：**
- FailureRouter - 失败路由
- ReviewRescueAdapter - 救援适配器

这个执行平面为后来的控制平面奠定了坚实的基础，提供了可靠的执行能力。
