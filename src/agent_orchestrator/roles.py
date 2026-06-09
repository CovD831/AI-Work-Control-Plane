"""Responsibility registry for governance-oriented operator views."""
from __future__ import annotations

# DEPS: __future__, dataclasses, typing
# RESPONSIBILITY: Define stable responsibility metadata used by backend work graphs and dashboard grouping.
# MODULE: decision_core
# ---

from dataclasses import dataclass, field
from typing import Literal

AgentLayer = Literal["control_plane", "decision", "execution", "review", "rescue", "runtime"]


@dataclass(frozen=True, slots=True)
class AgentRole:
    id: str
    label: str
    layer: AgentLayer
    responsibilities: list[str]
    default_provider: str
    allowed_job_kinds: list[str] = field(default_factory=list)

    @property
    def layer_label(self) -> str:
        return LAYER_LABELS[self.layer]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "layer": self.layer,
            "layer_label": self.layer_label,
            "responsibilities": list(self.responsibilities),
            "default_provider": self.default_provider,
            "allowed_job_kinds": list(self.allowed_job_kinds),
        }


@dataclass(frozen=True, slots=True)
class RoleContract:
    role: str
    runtime_mode: str
    allowed_actions: list[str]
    forbidden_actions: list[str]
    required_outputs: list[str]
    command_refs: list[str]
    structured_inputs: list[str] = field(default_factory=list)
    structured_outputs: list[str] = field(default_factory=list)
    local_state_fields: list[str] = field(default_factory=list)
    can_raise_blocker: bool = False
    can_propose_alternative: bool = False
    can_request_information: bool = False
    can_publish_reflection: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "runtime_mode": self.runtime_mode,
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "required_outputs": list(self.required_outputs),
            "command_refs": list(self.command_refs),
            "structured_inputs": list(self.structured_inputs),
            "structured_outputs": list(self.structured_outputs),
            "local_state_fields": list(self.local_state_fields),
            "can_raise_blocker": self.can_raise_blocker,
            "can_propose_alternative": self.can_propose_alternative,
            "can_request_information": self.can_request_information,
            "can_publish_reflection": self.can_publish_reflection,
        }


LAYER_LABELS: dict[AgentLayer, str] = {
    "control_plane": "控制平面层",
    "decision": "治理层",
    "execution": "执行层",
    "review": "质量门禁层",
    "rescue": "恢复层",
    "runtime": "运行时层",
}


DEFAULT_AGENT_ROLES: dict[str, AgentRole] = {
    "state_keeper": AgentRole(
        id="state_keeper",
        label="StateKeeper",
        layer="control_plane",
        responsibilities=["维护 workspace state、dirty state、provider health 和 approval 队列"],
        default_provider="control_plane",
        allowed_job_kinds=["research"],
    ),
    "context_compressor": AgentRole(
        id="context_compressor",
        label="ContextCompressor",
        layer="control_plane",
        responsibilities=["把 docs、memory、changed files 压缩成 ContextPacket"],
        default_provider="control_plane",
        allowed_job_kinds=["research"],
    ),
    "strategist": AgentRole(
        id="strategist",
        label="Strategist",
        layer="control_plane",
        responsibilities=["从 ContextPacket 生成 StrategyDecision，不直接执行"],
        default_provider="decision_core",
        allowed_job_kinds=["research"],
    ),
    "topology_compiler": AgentRole(
        id="topology_compiler",
        label="TopologyCompiler",
        layer="control_plane",
        responsibilities=["把 strategy 和 approved plan 编译成只读 ExecutionTopologySnapshot"],
        default_provider="decision_core",
        allowed_job_kinds=["research"],
    ),
    "evidence_recorder": AgentRole(
        id="evidence_recorder",
        label="EvidenceRecorder",
        layer="control_plane",
        responsibilities=["汇总 gate evidence、test/compliance/evidence report 状态"],
        default_provider="control_plane",
        allowed_job_kinds=["review"],
    ),
    "memory_curator": AgentRole(
        id="memory_curator",
        label="MemoryCurator",
        layer="control_plane",
        responsibilities=["记录带 provenance、freshness、confidence 的可复用经验"],
        default_provider="control_plane",
        allowed_job_kinds=["research"],
    ),
    "approval_gate": AgentRole(
        id="approval_gate",
        label="ApprovalGate",
        layer="control_plane",
        responsibilities=["记录人类介入项和审批结果，但不绕过执行门禁"],
        default_provider="control_plane",
        allowed_job_kinds=["review"],
    ),
    "lead": AgentRole(
        id="lead",
        label="会话治理",
        layer="decision",
        responsibilities=["协调会话状态、门禁和下一步操作建议"],
        default_provider="decision_core",
        allowed_job_kinds=["research"],
    ),
    "planner": AgentRole(
        id="planner",
        label="计划职责",
        layer="decision",
        responsibilities=["整理目标、维护计划结构和阶段边界"],
        default_provider="claude",
        allowed_job_kinds=["research"],
    ),
    "proponent": AgentRole(
        id="proponent",
        label="发散方案",
        layer="decision",
        responsibilities=["提出可执行方案和候选方向"],
        default_provider="codex",
        allowed_job_kinds=["research"],
    ),
    "skeptic": AgentRole(
        id="skeptic",
        label="反向质疑",
        layer="decision",
        responsibilities=["挑战假设、风险和遗漏"],
        default_provider="claude",
        allowed_job_kinds=["review"],
    ),
    "builder": AgentRole(
        id="builder",
        label="执行任务",
        layer="execution",
        responsibilities=["执行工作单元、产出实现结果"],
        default_provider="codex",
        allowed_job_kinds=["implementation"],
    ),
    "reviewer": AgentRole(
        id="reviewer",
        label="质量审查",
        layer="review",
        responsibilities=["检查计划和执行结果是否满足门禁要求"],
        default_provider="claude",
        allowed_job_kinds=["review"],
    ),
    "adversarial_reviewer": AgentRole(
        id="adversarial_reviewer",
        label="风险挑战",
        layer="review",
        responsibilities=["从反方视角寻找风险、遗漏和回滚问题"],
        default_provider="claude",
        allowed_job_kinds=["adversarial_review"],
    ),
    "validator": AgentRole(
        id="validator",
        label="执行验证",
        layer="execution",
        responsibilities=["验证验收条件和运行结果"],
        default_provider="codex",
        allowed_job_kinds=["review"],
    ),
    "rescue": AgentRole(
        id="rescue",
        label="恢复处理",
        layer="rescue",
        responsibilities=["处理失败、恢复路径和重试建议"],
        default_provider="claude",
        allowed_job_kinds=["rescue"],
    ),
    "runtime": AgentRole(
        id="runtime",
        label="运行时",
        layer="runtime",
        responsibilities=["承载 provider、job、terminal 执行"],
        default_provider="mock",
        allowed_job_kinds=["research", "implementation", "review", "adversarial_review", "rescue"],
    ),
}


def get_agent_role(role_id: str) -> AgentRole:
    return DEFAULT_AGENT_ROLES.get(role_id, DEFAULT_AGENT_ROLES["planner"])


def role_for_job_kind(kind: str) -> AgentRole:
    normalized = kind.replace("-", "_")
    if normalized == "implementation":
        return DEFAULT_AGENT_ROLES["builder"]
    if normalized in {"review", "review_retry"}:
        return DEFAULT_AGENT_ROLES["reviewer"]
    if normalized in {"adversarial_review", "adversarial_review_retry"}:
        return DEFAULT_AGENT_ROLES["adversarial_reviewer"]
    if normalized == "rescue":
        return DEFAULT_AGENT_ROLES["rescue"]
    if normalized == "runtime":
        return DEFAULT_AGENT_ROLES["runtime"]
    return DEFAULT_AGENT_ROLES["planner"]


def role_for_work_unit_kind(kind: str) -> AgentRole:
    normalized = kind.replace("-", "_")
    if normalized == "session":
        return DEFAULT_AGENT_ROLES["lead"]
    if normalized == "subtask":
        return DEFAULT_AGENT_ROLES["builder"]
    if normalized in {"review_round", "review"}:
        return DEFAULT_AGENT_ROLES["reviewer"]
    if normalized == "adversarial_review":
        return DEFAULT_AGENT_ROLES["adversarial_reviewer"]
    if normalized == "gap":
        return DEFAULT_AGENT_ROLES["lead"]
    if normalized == "execution_run":
        return DEFAULT_AGENT_ROLES["runtime"]
    return DEFAULT_AGENT_ROLES["planner"]


ROLE_CONTRACTS: dict[str, RoleContract] = {
    "lead": RoleContract(
        role="lead",
        runtime_mode="direct_api",
        allowed_actions=["coordinate_session", "respond_to_user"],
        forbidden_actions=["execute_work_unit", "bypass_approval_gate"],
        required_outputs=["session_brief", "next_action", "decision_summary"],
        command_refs=["team status", "team next", "team inspect-blockers"],
        structured_inputs=["plan_session", "review_summary", "approval_state"],
        structured_outputs=["session_brief", "decision_summary", "next_action"],
        local_state_fields=["session_status", "blocking_gaps", "pending_reviews"],
        can_raise_blocker=True,
        can_propose_alternative=True,
        can_request_information=True,
        can_publish_reflection=True,
    ),
    "planner": RoleContract(
        role="planner",
        runtime_mode="direct_api",
        allowed_actions=["draft_plan", "respond_to_user"],
        forbidden_actions=["execute_work_unit", "write_review_findings"],
        required_outputs=["structured_brief", "checklist", "next_executable_task"],
        command_refs=["team start", "team chat", "team draft-ready", "team task next"],
        structured_inputs=["workspace_state", "context_packet", "user_requirement"],
        structured_outputs=["structured_brief", "planning_notes", "next_executable_task"],
        local_state_fields=["goal", "open_questions", "phase_boundary"],
        can_raise_blocker=True,
        can_propose_alternative=True,
        can_request_information=True,
        can_publish_reflection=True,
    ),
    "reviewer": RoleContract(
        role="reviewer",
        runtime_mode="direct_api",
        allowed_actions=["write_review_findings"],
        forbidden_actions=["execute_work_unit", "approve_plan"],
        required_outputs=["review_findings", "required_gaps", "followup_gaps"],
        command_refs=["team submit-review", "team retry-review", "team task list"],
        structured_inputs=["approved_plan", "execution_evidence", "review_request"],
        structured_outputs=["review_findings", "verdict", "required_gaps"],
        local_state_fields=["review_focus", "severity_summary"],
        can_raise_blocker=True,
        can_propose_alternative=True,
        can_request_information=True,
        can_publish_reflection=False,
    ),
    "adversarial_reviewer": RoleContract(
        role="adversarial_reviewer",
        runtime_mode="direct_api",
        allowed_actions=["write_review_findings"],
        forbidden_actions=["execute_work_unit", "approve_plan"],
        required_outputs=["adversarial_findings", "risk_challenges", "gap_recommendations"],
        command_refs=["team submit-review", "team retry-adversarial-review"],
        structured_inputs=["approved_plan", "execution_evidence", "risk_prompt"],
        structured_outputs=["adversarial_findings", "risk_challenges", "gap_recommendations"],
        local_state_fields=["attack_surface", "failure_modes"],
        can_raise_blocker=True,
        can_propose_alternative=True,
        can_request_information=True,
        can_publish_reflection=False,
    ),
    "builder": RoleContract(
        role="builder",
        runtime_mode="cli_inherit",
        allowed_actions=["execute_work_unit"],
        forbidden_actions=["approve_plan", "write_review_findings"],
        required_outputs=["implementation_result", "targeted_validation", "changed_files"],
        command_refs=["team execute", "team inspect-execution"],
        structured_inputs=["execution_contract", "subtask_scope", "handoff_packet"],
        structured_outputs=["implementation_result", "targeted_validation", "changed_files"],
        local_state_fields=["changed_files", "validation_status", "runtime_notes"],
        can_raise_blocker=True,
        can_propose_alternative=True,
        can_request_information=True,
        can_publish_reflection=True,
    ),
    "rescue": RoleContract(
        role="rescue",
        runtime_mode="cli_inherit",
        allowed_actions=["recover_session"],
        forbidden_actions=["approve_plan", "write_review_findings"],
        required_outputs=["rescue_summary", "retry_plan", "stop_reason"],
        command_refs=["team inspect-blockers", "team retry-review", "team retry-adversarial-review"],
        structured_inputs=["recovery_recommendation", "blocked_session", "runtime_events"],
        structured_outputs=["rescue_summary", "retry_plan", "stop_reason"],
        local_state_fields=["failure_signature", "selected_recovery_branch", "retry_budget"],
        can_raise_blocker=True,
        can_propose_alternative=True,
        can_request_information=True,
        can_publish_reflection=True,
    ),
    "runtime": RoleContract(
        role="runtime",
        runtime_mode="local_artifact",
        allowed_actions=["report_run_state"],
        forbidden_actions=["approve_plan", "rewrite_decision_record"],
        required_outputs=["run_state", "runtime_events", "command_result_summary"],
        command_refs=["team inspect-execution"],
        structured_inputs=["execution_run", "provider_result", "terminal_state"],
        structured_outputs=["run_state", "runtime_events", "command_result_summary"],
        local_state_fields=["run_id", "provider_status", "last_command"],
        can_raise_blocker=True,
        can_propose_alternative=False,
        can_request_information=False,
        can_publish_reflection=False,
    ),
    "state_keeper": RoleContract(
        role="state_keeper",
        runtime_mode="local_artifact",
        allowed_actions=["build_workspace_state"],
        forbidden_actions=["execute_work_unit", "approve_plan"],
        required_outputs=["WorkspaceStateSnapshot"],
        command_refs=["team workspace-status"],
        structured_inputs=["workspace_scan", "git_status", "provider_health"],
        structured_outputs=["WorkspaceStateSnapshot"],
        local_state_fields=["dirty_files", "approval_queue", "provider_health"],
        can_raise_blocker=True,
        can_propose_alternative=False,
        can_request_information=False,
        can_publish_reflection=False,
    ),
    "context_compressor": RoleContract(
        role="context_compressor",
        runtime_mode="local_artifact",
        allowed_actions=["build_context_packet"],
        forbidden_actions=["choose_strategy", "execute_work_unit"],
        required_outputs=["ContextPacket", "stale_warnings", "source_artifacts"],
        command_refs=["team context-packet", "team inspect-docs", "team docs-index"],
        structured_inputs=["workspace_state", "selected_docs", "memory_records"],
        structured_outputs=["ContextPacket", "retrieval_assessment", "source_conflict_summary"],
        local_state_fields=["selected_doc_ids", "stale_docs", "conflicted_sources"],
        can_raise_blocker=True,
        can_propose_alternative=False,
        can_request_information=True,
        can_publish_reflection=False,
    ),
    "strategist": RoleContract(
        role="strategist",
        runtime_mode="direct_api",
        allowed_actions=["write_strategy_decision"],
        forbidden_actions=["execute_work_unit", "resolve_approval"],
        required_outputs=["StrategyDecision", "verification_requirements", "tradeoffs"],
        command_refs=["team topology inspect"],
        structured_inputs=["context_packet", "workspace_state", "routing_candidates"],
        structured_outputs=["StrategyDecision", "route_consensus", "tradeoffs"],
        local_state_fields=["selected_topology", "rejected_alternatives", "confidence"],
        can_raise_blocker=True,
        can_propose_alternative=True,
        can_request_information=True,
        can_publish_reflection=True,
    ),
    "topology_compiler": RoleContract(
        role="topology_compiler",
        runtime_mode="local_artifact",
        allowed_actions=["build_topology_snapshot"],
        forbidden_actions=["execute_work_unit", "edit_visual_canvas"],
        required_outputs=["ExecutionTopologySnapshot"],
        command_refs=["team topology inspect"],
        structured_inputs=["strategy_decision", "approved_plan", "provider_runtime_matrix"],
        structured_outputs=["ExecutionTopologySnapshot"],
        local_state_fields=["selected_topology", "runtime_bindings", "review_requirements"],
        can_raise_blocker=True,
        can_propose_alternative=False,
        can_request_information=True,
        can_publish_reflection=False,
    ),
    "evidence_recorder": RoleContract(
        role="evidence_recorder",
        runtime_mode="local_artifact",
        allowed_actions=["build_evidence_bundle"],
        forbidden_actions=["approve_plan", "execute_work_unit"],
        required_outputs=["EvidenceBundle", "gate_evidence"],
        command_refs=["team evidence-gates", "team setup", "team check-compliance"],
        structured_inputs=["review_results", "execution_result", "compliance_snapshot"],
        structured_outputs=["EvidenceBundle", "gate_evidence", "verification_summary"],
        local_state_fields=["failing_gates", "evidence_sources", "coverage_summary"],
        can_raise_blocker=True,
        can_propose_alternative=False,
        can_request_information=True,
        can_publish_reflection=False,
    ),
    "memory_curator": RoleContract(
        role="memory_curator",
        runtime_mode="local_artifact",
        allowed_actions=["record_memory_with_provenance"],
        forbidden_actions=["choose_strategy", "approve_plan"],
        required_outputs=["MemoryRecord", "provenance", "freshness"],
        command_refs=["team inspect-knowledge", "team context-packet"],
        structured_inputs=["evidence_bundle", "session_outcome", "retrieval_support"],
        structured_outputs=["MemoryRecord", "provenance", "freshness"],
        local_state_fields=["memory_candidates", "promotion_reason", "freshness_score"],
        can_raise_blocker=False,
        can_propose_alternative=False,
        can_request_information=True,
        can_publish_reflection=True,
    ),
    "approval_gate": RoleContract(
        role="approval_gate",
        runtime_mode="human_gate",
        allowed_actions=["record_approval_decision"],
        forbidden_actions=["execute_work_unit", "bypass_execution_gate"],
        required_outputs=["ApprovalItem", "resolution_event"],
        command_refs=["team approvals list", "team approvals resolve"],
        structured_inputs=["approval_item", "decision_context", "resolution_reason"],
        structured_outputs=["ApprovalItem", "resolution_event"],
        local_state_fields=["approval_state", "resolution_reason", "pending_owner"],
        can_raise_blocker=True,
        can_propose_alternative=False,
        can_request_information=True,
        can_publish_reflection=False,
    ),
    "validator": RoleContract(
        role="validator",
        runtime_mode="cli_inherit",
        allowed_actions=["validate_execution_result"],
        forbidden_actions=["approve_plan", "rewrite_review_findings"],
        required_outputs=["validation_result", "test_summary", "acceptance_status"],
        command_refs=["team inspect-execution", "team task next"],
        structured_inputs=["implementation_result", "acceptance_criteria", "targeted_tests"],
        structured_outputs=["validation_result", "test_summary", "acceptance_status"],
        local_state_fields=["failing_tests", "coverage_scope", "acceptance_state"],
        can_raise_blocker=True,
        can_propose_alternative=False,
        can_request_information=True,
        can_publish_reflection=True,
    ),
}


def role_contracts() -> list[RoleContract]:
    return [ROLE_CONTRACTS[key] for key in sorted(ROLE_CONTRACTS)]


def get_role_contract(role_id: str) -> RoleContract:
    return ROLE_CONTRACTS.get(role_id, ROLE_CONTRACTS["planner"])
