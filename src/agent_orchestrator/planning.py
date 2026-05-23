"""Planning governance models and team orchestration helpers."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, dataclasses, json, pathlib, tempfile, typing, uuid
# RESPONSIBILITY: 待补充
# MODULE: 待确定
# ---


import json
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal
from uuid import uuid4

from agent_orchestrator.jobs import FileJobRuntime, JobRequest, JobRuntime
from agent_orchestrator.command import ProviderHealthCheck, ProviderStatus
from agent_orchestrator.orchestrator import Orchestrator
from agent_orchestrator.policies import OrchestrationMode, get_policy
from agent_orchestrator.review import Finding, ReviewResult
from agent_orchestrator.tasks import ExecutionContract
from agent_orchestrator.topology import TopologyName

TeamRole = Literal["lead", "build", "review"]
GapStatus = Literal["open", "acknowledged", "closed"]
PlanSessionStatus = Literal[
    "drafting",
    "in_review",
    "needs_revision",
    "approved_for_execution",
    "executing",
    "accepted",
    "needs_followup",
    "blocked",
    "awaiting_human",
]
GateVerdict = Literal["approved", "needs_revision", "blocked", "accepted", "needs_followup"]
ApprovalStatus = Literal["approved", "needs_revision", "blocked", "accepted", "needs_followup"]
RoundType = Literal[
    "authoring",
    "review",
    "review_retry",
    "adversarial_review",
    "adversarial_review_retry",
    "revision",
    "approval",
]


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


@dataclass(slots=True)
class PlanSubtask:
    title: str
    expected_outputs: list[str]
    gate_conditions: list[str]
    owner: TeamRole = "build"
    id: str = field(default_factory=lambda: _new_id("subtask"))

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "expected_outputs": self.expected_outputs,
            "gate_conditions": self.gate_conditions,
            "owner": self.owner,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PlanSubtask":
        return cls(
            title=str(data["title"]),
            expected_outputs=list(data.get("expected_outputs", [])),
            gate_conditions=list(data.get("gate_conditions", [])),
            owner=data.get("owner", "build"),
            id=str(data["id"]),
        )


@dataclass(slots=True)
class StructuredPlanBrief:
    goal: str
    constraints: list[str]
    subtasks: list[PlanSubtask]
    acceptance_criteria: list[str]
    open_questions: list[str]
    risks: list[str]
    checklist_summary: list[str]
    execution_intent: str = ""
    topology_recommendation: dict[str, object] = field(default_factory=dict)
    provider_recommendation: dict[str, object] = field(default_factory=dict)
    decision_rationale: list[str] = field(default_factory=list)
    review_disputes: list[str] = field(default_factory=list)
    gating_requirements: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "goal": self.goal,
            "constraints": self.constraints,
            "subtasks": [subtask.to_dict() for subtask in self.subtasks],
            "acceptance_criteria": self.acceptance_criteria,
            "open_questions": self.open_questions,
            "risks": self.risks,
            "checklist_summary": self.checklist_summary,
            "execution_intent": self.execution_intent,
            "topology_recommendation": self.topology_recommendation,
            "provider_recommendation": self.provider_recommendation,
            "decision_rationale": self.decision_rationale,
            "review_disputes": self.review_disputes,
            "gating_requirements": self.gating_requirements,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "StructuredPlanBrief":
        return cls(
            goal=str(data.get("goal", "")),
            constraints=[str(item) for item in data.get("constraints", [])],
            subtasks=[PlanSubtask.from_dict(item) for item in data.get("subtasks", [])],
            acceptance_criteria=[str(item) for item in data.get("acceptance_criteria", [])],
            open_questions=[str(item) for item in data.get("open_questions", [])],
            risks=[str(item) for item in data.get("risks", [])],
            checklist_summary=[str(item) for item in data.get("checklist_summary", [])],
            execution_intent=str(data.get("execution_intent", "")),
            topology_recommendation=dict(data.get("topology_recommendation", {})),
            provider_recommendation=dict(data.get("provider_recommendation", {})),
            decision_rationale=[str(item) for item in data.get("decision_rationale", [])],
            review_disputes=[str(item) for item in data.get("review_disputes", [])],
            gating_requirements=[str(item) for item in data.get("gating_requirements", [])],
        )


@dataclass(slots=True)
class DecisionVerdict:
    approval_status: ApprovalStatus
    required_gaps: list[dict[str, object]]
    followup_gaps: list[dict[str, object]]
    selected_topology: TopologyName
    selected_provider_runtime: dict[str, object]
    rationale: list[str]

    def __getitem__(self, key: str) -> object:
        return self.to_dict()[key]

    def to_dict(self) -> dict[str, object]:
        return {
            "approval_status": self.approval_status,
            "required_gaps": self.required_gaps,
            "followup_gaps": self.followup_gaps,
            "selected_topology": self.selected_topology,
            "selected_provider_runtime": self.selected_provider_runtime,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "DecisionVerdict":
        return cls(
            approval_status=data.get("approval_status", "needs_revision"),
            required_gaps=list(data.get("required_gaps", [])),
            followup_gaps=list(data.get("followup_gaps", [])),
            selected_topology=data.get("selected_topology", "team"),
            selected_provider_runtime=dict(data.get("selected_provider_runtime", {})),
            rationale=[str(item) for item in data.get("rationale", [])],
        )


@dataclass(slots=True, frozen=True)
class ProcessDocumentSpec:
    path: str
    title: str
    bullets: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.bullets, tuple):
            object.__setattr__(self, "bullets", tuple(self.bullets))

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "title": self.title,
            "bullets": list(self.bullets),
        }

    def render_markdown(self) -> str:
        lines = [f"# {self.title}", ""]
        lines.extend(f"- {bullet}" for bullet in self.bullets)
        lines.append("")
        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, path: str, text: str) -> "ProcessDocumentSpec":
        raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not raw_lines:
            raise ValueError("document is empty")
        heading = raw_lines[0]
        if not heading.startswith("# "):
            raise ValueError("document must start with a markdown heading")
        bullets: list[str] = []
        for line in raw_lines[1:]:
            if not line.startswith("- "):
                raise ValueError("document must use bullet lines for its structure")
            bullets.append(line[2:].strip())
        if not bullets:
            raise ValueError("document must define at least one bullet")
        return cls(path=path, title=heading[2:].strip(), bullets=tuple(bullets))


@dataclass(slots=True, frozen=True)
class ProcessDocumentationBundle:
    root_map: ProcessDocumentSpec
    module_manifest: ProcessDocumentSpec
    file_header_contract: ProcessDocumentSpec

    def iter_specs(self) -> list[tuple[str, ProcessDocumentSpec]]:
        return [
            ("root_map", self.root_map),
            ("module_manifest", self.module_manifest),
            ("file_header_contract", self.file_header_contract),
        ]


@dataclass(slots=True)
class PlanChecklistItem:
    label: str
    owner: TeamRole = "lead"
    completed: bool = False
    id: str = field(default_factory=lambda: _new_id("check"))

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "label": self.label, "owner": self.owner, "completed": self.completed}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PlanChecklistItem":
        return cls(
            label=str(data["label"]),
            owner=data.get("owner", "lead"),
            completed=bool(data.get("completed", False)),
            id=str(data["id"]),
        )


@dataclass(slots=True)
class PlanGap:
    title: str
    severity: str
    recommendation: str
    required: bool = True
    status: GapStatus = "open"
    finding_round_id: str | None = None
    id: str = field(default_factory=lambda: _new_id("gap"))

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "recommendation": self.recommendation,
            "required": self.required,
            "status": self.status,
            "finding_round_id": self.finding_round_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PlanGap":
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            severity=str(data["severity"]),
            recommendation=str(data.get("recommendation", "")),
            required=bool(data.get("required", True)),
            status=data.get("status", "open"),
            finding_round_id=data.get("finding_round_id"),
        )


@dataclass(slots=True)
class PlanResumeState:
    current_phase: str
    active_round_id: str | None
    pending_role: TeamRole
    submitted_at: str | None = None
    approved_at: str | None = None
    linked_execution_run_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "current_phase": self.current_phase,
            "active_round_id": self.active_round_id,
            "pending_role": self.pending_role,
            "submitted_at": self.submitted_at,
            "approved_at": self.approved_at,
            "linked_execution_run_id": self.linked_execution_run_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PlanResumeState":
        return cls(
            current_phase=str(data["current_phase"]),
            active_round_id=data.get("active_round_id"),
            pending_role=data.get("pending_role", "lead"),
            submitted_at=data.get("submitted_at"),
            approved_at=data.get("approved_at"),
            linked_execution_run_id=data.get("linked_execution_run_id"),
        )


@dataclass(slots=True)
class PlanReviewRound:
    round_type: RoundType
    role: TeamRole
    summary: str
    id: str = field(default_factory=lambda: _new_id("round"))
    review_result: ReviewResult | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "round_type": self.round_type,
            "role": self.role,
            "summary": self.summary,
            "review_result": self.review_result.to_dict() if self.review_result else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PlanReviewRound":
        review_payload = data.get("review_result")
        review_result = None
        if review_payload:
            review_result = ReviewResult(
                verdict=review_payload["verdict"],
                summary=str(review_payload["summary"]),
                findings=[
                    Finding(
                        severity=finding["severity"],
                        title=str(finding["title"]),
                        body=str(finding["body"]),
                        file=str(finding["file"]),
                        line_start=int(finding["line_start"]),
                        line_end=int(finding["line_end"]),
                        confidence=float(finding["confidence"]),
                        recommendation=str(finding["recommendation"]),
                    )
                    for finding in review_payload.get("findings", [])
                ],
                next_steps=list(review_payload.get("next_steps", [])),
            )
        return cls(
            id=str(data["id"]),
            round_type=data["round_type"],
            role=data["role"],
            summary=str(data["summary"]),
            review_result=review_result,
        )


@dataclass(slots=True, frozen=True)
class RoundOutcome:
    status: PlanSessionStatus
    gate_verdict: GateVerdict


@dataclass(slots=True)
class RoundController:
    def derive_post_review_outcome(self, findings: list[Finding]) -> RoundOutcome:
        if any(finding.severity == "critical" for finding in findings):
            return RoundOutcome(status="awaiting_human", gate_verdict="blocked")
        if any(finding.severity == "high" for finding in findings):
            return RoundOutcome(status="blocked", gate_verdict="blocked")
        if findings:
            return RoundOutcome(status="needs_revision", gate_verdict="needs_revision")
        return RoundOutcome(status="approved_for_execution", gate_verdict="approved")

    def validate_approve(self, session: "PlanSession") -> None:
        if session.status == "approved_for_execution":
            raise ValueError("team approve cannot re-approve a plan that is already approved")
        if session.status != "needs_revision" or session.gate_verdict != "needs_revision":
            raise ValueError("team approve requires a needs_revision plan session before approval")
        if session.resume.current_phase != "in_review" or session.resume.pending_role != "lead":
            raise ValueError("team approve requires the lead review handoff to be active")
        if not _checklist_item_completed(session.checklist, "Review round completed"):
            raise ValueError("team approve requires the review round completed checklist item")
        if any(gap.required and gap.status != "closed" for gap in session.gaps):
            raise ValueError("team approve requires all open gaps to be closed before approval")

    def validate_execute(self, session: "PlanSession") -> None:
        if session.gate_verdict != "approved" or session.status != "approved_for_execution":
            raise ValueError("team execute requires an approved plan session before execution")
        if session.resume.current_phase != "approved":
            raise ValueError("team execute requires a session in the approved phase before execution")
        if not _checklist_item_completed(session.checklist, "Execution approved"):
            raise ValueError("team execute requires the Execution approved checklist item")

    def normalize_resume(self, session: "PlanSession") -> "PlanSession":
        if (
            session.status == "executing"
            and session.resume.linked_execution_run_id
            and session.gate_verdict == "approved"
        ):
            session.resume.current_phase = "executing"
            session.resume.pending_role = "build"
            return session
        if session.status == "needs_revision":
            active_round_id = session.review_rounds[-1].id if session.review_rounds else None
            session.resume.current_phase = "in_review"
            session.resume.pending_role = "lead"
            session.resume.active_round_id = active_round_id
            return session
        if session.status == "approved_for_execution":
            if session.gate_verdict != "approved":
                raise ValueError("inconsistent approved session: verdict must be approved")
            if session.resume.current_phase not in {"approved", "drafting", "executing", "in_review"}:
                raise ValueError("inconsistent approved session: unexpected resume phase")
            session.resume.current_phase = "approved"
            session.resume.pending_role = "lead"
            return session
        if session.status == "executing":
            if session.gate_verdict != "approved":
                raise ValueError("inconsistent executing session: verdict must remain approved before completion")
            session.resume.current_phase = "executing"
            session.resume.pending_role = "build"
            return session
        if session.status in {"accepted", "needs_followup"}:
            session.resume.current_phase = session.status
            session.resume.pending_role = "lead"
            return session
        if session.status in {"blocked", "awaiting_human"}:
            session.resume.pending_role = "lead"
            return session
        return session

    def validate_revision(self, session: "PlanSession", closed_gap_ids: list[str]) -> None:
        if session.status != "needs_revision" or session.gate_verdict != "needs_revision":
            raise ValueError("team revise requires a needs_revision plan session")
        if not closed_gap_ids:
            raise ValueError("team revise requires at least one gap to close")
        known_gap_ids = {gap.id for gap in session.gaps}
        open_gap_ids = {gap.id for gap in session.gaps if gap.status != "closed"}
        unknown_gap_ids = [gap_id for gap_id in closed_gap_ids if gap_id not in known_gap_ids]
        if unknown_gap_ids:
            raise ValueError(f"team revise cannot close unknown gap ids: {', '.join(unknown_gap_ids)}")
        matched_open_gap_ids = [gap_id for gap_id in closed_gap_ids if gap_id in open_gap_ids]
        if not matched_open_gap_ids:
            raise ValueError("team revise requires at least one open gap to close")


@dataclass(slots=True)
class PlanSession:
    id: str
    requirement: str
    stage_target: str
    status: PlanSessionStatus
    lead_brief: str
    structured_brief: StructuredPlanBrief
    subtasks: list[PlanSubtask]
    gaps: list[PlanGap]
    approved_plan: dict[str, object] | None
    review_rounds: list[PlanReviewRound]
    checklist: list[PlanChecklistItem]
    resume: PlanResumeState
    gate_verdict: GateVerdict | None
    decision_verdict: DecisionVerdict | None = None
    doc_sync: dict[str, object] | None = None
    compliance: dict[str, object] | None = None

    @classmethod
    def new(cls, *, requirement: str, stage_target: str) -> "PlanSession":
        return cls(
            id=_new_id("plan"),
            requirement=requirement,
            stage_target=stage_target,
            status="drafting",
            lead_brief="",
            structured_brief=StructuredPlanBrief(
                goal="",
                constraints=[],
                subtasks=[],
                acceptance_criteria=[],
                open_questions=[],
                risks=[],
                checklist_summary=[],
            ),
            subtasks=[],
            gaps=[],
            approved_plan=None,
            review_rounds=[],
            checklist=[],
            resume=PlanResumeState(current_phase="drafting", active_round_id=None, pending_role="lead"),
            gate_verdict=None,
            decision_verdict=None,
            doc_sync=None,
            compliance=None,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "requirement": self.requirement,
            "stage_target": self.stage_target,
            "status": self.status,
            "lead_brief": self.lead_brief,
            "structured_brief": self.structured_brief.to_dict(),
            "subtasks": [subtask.to_dict() for subtask in self.subtasks],
            "gaps": [gap.to_dict() for gap in self.gaps],
            "approved_plan": self.approved_plan,
            "review_rounds": [round_.to_dict() for round_ in self.review_rounds],
            "checklist": [item.to_dict() for item in self.checklist],
            "resume": self.resume.to_dict(),
            "gate_verdict": self.gate_verdict,
            "decision_verdict": self.decision_verdict.to_dict() if self.decision_verdict else None,
            "status_summary": _build_status_summary(self),
            "doc_sync": self.doc_sync,
            "compliance": self.compliance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PlanSession":
        subtasks = [PlanSubtask.from_dict(item) for item in data.get("subtasks", [])]
        checklist = [PlanChecklistItem.from_dict(item) for item in data.get("checklist", [])]
        structured_brief_payload = data.get("structured_brief")
        structured_brief = (
            StructuredPlanBrief.from_dict(structured_brief_payload)
            if structured_brief_payload
            else _hydrate_legacy_structured_brief(data, subtasks, checklist)
        )
        return cls(
            id=str(data["id"]),
            requirement=str(data["requirement"]),
            stage_target=str(data["stage_target"]),
            status=data["status"],
            lead_brief=str(data.get("lead_brief", "")),
            structured_brief=structured_brief,
            subtasks=subtasks,
            gaps=[PlanGap.from_dict(item) for item in data.get("gaps", [])],
            approved_plan=data.get("approved_plan"),
            review_rounds=[PlanReviewRound.from_dict(item) for item in data.get("review_rounds", [])],
            checklist=checklist,
            resume=PlanResumeState.from_dict(data["resume"]),
            gate_verdict=data.get("gate_verdict"),
            decision_verdict=DecisionVerdict.from_dict(data["decision_verdict"]) if data.get("decision_verdict") else None,
            doc_sync=data.get("doc_sync"),
            compliance=data.get("compliance"),
        )


def _hydrate_legacy_structured_brief(
    data: dict[str, object],
    subtasks: list[PlanSubtask],
    checklist: list[PlanChecklistItem],
) -> StructuredPlanBrief:
    lead_brief = str(data.get("lead_brief", "")).strip()
    requirement = str(data.get("requirement", "")).strip()
    goal = requirement
    if lead_brief.startswith("Lead target:"):
        goal = lead_brief.split(":", 1)[1].strip() or requirement
    elif lead_brief:
        goal = lead_brief
    acceptance_criteria = _dedupe_preserve_order(
        gate_condition
        for subtask in subtasks
        for gate_condition in subtask.gate_conditions
    )
    checklist_summary = [
        f"{item.label} [{item.owner}]: {'done' if item.completed else 'pending'}"
        for item in checklist
    ]
    return StructuredPlanBrief(
        goal=goal,
        constraints=[],
        subtasks=subtasks,
        acceptance_criteria=acceptance_criteria,
        open_questions=[],
        risks=[],
        checklist_summary=checklist_summary,
        execution_intent="Turn the approved plan into the execution contract without going back to the raw requirement.",
    )


def _dedupe_preserve_order(items: list[str] | Any) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        value = str(item)
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


@dataclass(slots=True)
class PlanStore:
    root: Path | str = ".agent_orchestrator/plans"

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write_session(self, session: PlanSession) -> None:
        session_dir = self.root / session.id
        rounds_dir = session_dir / "rounds"
        rounds_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(session_dir / "session.json", session.to_dict())
        self._write_json(session_dir / "checklist.json", {"items": [item.to_dict() for item in session.checklist]})
        self._write_json(
            session_dir / "verdict.json",
            {
                "gate_verdict": session.gate_verdict,
                "status": session.status,
                "execution_run_id": session.resume.linked_execution_run_id,
                "decision_verdict": session.decision_verdict.to_dict() if session.decision_verdict else None,
            },
        )
        for index, round_ in enumerate(session.review_rounds, start=1):
            self._write_json(rounds_dir / f"round-{index:03d}.json", round_.to_dict())

    def read_session(self, session_id: str) -> PlanSession:
        session_dir = self.root / session_id
        payload = json.loads((session_dir / "session.json").read_text(encoding="utf-8"))
        return PlanSession.from_dict(payload)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(payload, ensure_ascii=False, indent=2)
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)


@dataclass(slots=True)
class TeamOrchestrator:
    orchestrator: Orchestrator
    store: PlanStore = field(default_factory=PlanStore)
    stage_target: str = "Stage 2: Planning Governance Skeleton"
    runtime: JobRuntime = field(default_factory=FileJobRuntime)
    round_controller: RoundController = field(default_factory=RoundController)
    project_root: Path | str = field(default_factory=Path.cwd)
    provider_health_check: Any = field(default_factory=ProviderHealthCheck)

    def __post_init__(self) -> None:
        self.project_root = Path(self.project_root)

    def start(self, requirement: str) -> PlanSession:
        policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
        contract = self.orchestrator.planner.clarify(requirement, policy)
        work_units = self.orchestrator.decomposer.decompose(contract, policy)
        session = PlanSession.new(requirement=requirement, stage_target=self.stage_target)
        session.doc_sync = self._build_doc_sync_status()
        session.compliance = self._build_compliance_status(session.doc_sync)
        session.lead_brief = f"Lead target: {contract.goal}"
        session.subtasks = [
            PlanSubtask(
                title=work_unit.goal,
                expected_outputs=work_unit.outputs,
                gate_conditions=work_unit.acceptance_criteria,
            )
            for work_unit in work_units
        ]
        session.structured_brief = StructuredPlanBrief(
            goal=contract.goal,
            constraints=[],
            subtasks=session.subtasks,
            acceptance_criteria=_dedupe_preserve_order(
                gate_condition
                for subtask in session.subtasks
                for gate_condition in subtask.gate_conditions
            ),
            open_questions=[],
            risks=[],
            checklist_summary=[],
            execution_intent="Use the approved plan as the execution contract source of truth.",
            topology_recommendation=_recommend_topology(policy, requirement, session.subtasks),
            provider_recommendation=_recommend_provider_runtime(self.runtime),
            decision_rationale=[],
            review_disputes=[],
            gating_requirements=[
                "Required gaps must be closed before execution.",
                "Execution must start from the approved plan, not from the raw requirement.",
            ],
        )
        session.checklist = [
            PlanChecklistItem(label="Lead brief persisted", owner="lead", completed=True),
            PlanChecklistItem(label="Review round completed", owner="review", completed=False),
            PlanChecklistItem(label="Execution approved", owner="lead", completed=False),
        ]
        research_provider = "claude" if self.runtime.__class__.__name__ == "CommandJobRuntime" else "mock"
        preferred_review_provider = "claude"
        review_provider_status = self._review_provider_status(preferred_review_provider)
        verdict_review_provider = preferred_review_provider if review_provider_status.available else "mock"
        runtime_review_provider = verdict_review_provider
        if (
            verdict_review_provider == "mock"
            and self.runtime.__class__.__name__ == "CommandJobRuntime"
            and hasattr(self.runtime, "adapters")
        ):
            runtime_review_provider = "claude" if "claude" in getattr(self.runtime, "adapters", {}) else verdict_review_provider
        session.structured_brief.provider_recommendation = _recommend_provider_runtime(
            self.runtime,
            reviewer_provider=verdict_review_provider,
            fallback_from=preferred_review_provider,
            fallback_reason="reviewer_unavailable" if verdict_review_provider != preferred_review_provider else None,
            fallback_detail=review_provider_status.detail if verdict_review_provider != preferred_review_provider else None,
        )

        lead_job = self.runtime.start(
            JobRequest(
                task_id=session.id,
                provider=research_provider,
                kind="research",
                prompt=f"Lead planning round: {requirement}",
                cwd=str(Path.cwd()),
                metadata={"stage_target": self.stage_target, "role": "lead"},
            )
        )
        if hasattr(self.runtime, "complete"):
            lead_job = getattr(self.runtime, "complete")(
                lead_job.id,
                summary=f"Lead planning round completed for {session.id}.",
                stdout=session.lead_brief,
                parsed_payload={"lead_brief": session.lead_brief},
                phase="done",
            )
        author_round = PlanReviewRound(
            round_type="authoring",
            role="lead",
            summary=(
                f"Lead selected stage target {self.stage_target} and drafted {len(session.subtasks)} subtasks "
                f"via {lead_job.provider} job {lead_job.id}."
            ),
        )
        review_result = _review_plan(requirement, session)
        review_job = self.runtime.start(
            JobRequest(
                task_id=session.id,
                provider=runtime_review_provider,
                kind="review",
                prompt=f"Review planning round: {requirement}",
                cwd=str(Path.cwd()),
                metadata={"stage_target": self.stage_target, "role": "review"},
            )
        )
        if hasattr(self.runtime, "complete"):
            review_job = getattr(self.runtime, "complete")(
                review_job.id,
                summary=f"Review round completed for {session.id}.",
                stdout=review_result.summary,
                parsed_payload={"review_result": review_result.to_dict()},
                phase="reviewing",
            )
        review_round = PlanReviewRound(
            round_type="review",
            role="review",
            summary=f"{review_result.summary} via {review_job.provider} review job {review_job.id}.",
            review_result=review_result,
        )
        adversarial_result = _adversarial_review_plan(requirement, session)
        adversarial_job = self.runtime.start(
            JobRequest(
                task_id=session.id,
                provider=runtime_review_provider,
                kind="adversarial_review",
                prompt=f"Adversarial review planning round: {requirement}",
                cwd=str(Path.cwd()),
                metadata={"stage_target": self.stage_target, "role": "review", "round_type": "adversarial_review"},
            )
        )
        if hasattr(self.runtime, "complete"):
            adversarial_job = getattr(self.runtime, "complete")(
                adversarial_job.id,
                summary=f"Adversarial review round completed for {session.id}.",
                stdout=adversarial_result.summary,
                parsed_payload={"review_result": adversarial_result.to_dict()},
                phase="reviewing",
            )
        adversarial_round = PlanReviewRound(
            round_type="adversarial_review",
            role="review",
            summary=f"{adversarial_result.summary} via {adversarial_job.provider} adversarial_review job {adversarial_job.id}.",
            review_result=adversarial_result,
        )
        session.review_rounds = [author_round, review_round, adversarial_round]
        session.resume.active_round_id = adversarial_round.id
        session.resume.current_phase = "in_review"
        session.resume.pending_role = "lead"
        session.checklist[1].completed = True

        all_findings = [
            finding
            for round_ in session.review_rounds
            if round_.review_result
            for finding in round_.review_result.findings
        ]
        session.gaps = _build_plan_gaps(session.review_rounds)

        outcome = self.round_controller.derive_post_review_outcome(all_findings)
        session.status = outcome.status
        session.gate_verdict = outcome.gate_verdict
        if outcome.status == "approved_for_execution":
            session.resume.current_phase = "approved"
            session.resume.approved_at = "approved"
            session.checklist[2].completed = True
            session.approved_plan = _build_approved_plan(session)

        session.structured_brief.risks = _summarize_plan_risks(all_findings)
        session.structured_brief.review_disputes = _summarize_review_disputes(session.review_rounds)
        session.structured_brief.decision_rationale = _build_decision_rationale(requirement, session, policy)
        session.structured_brief.checklist_summary = _build_checklist_summary(session.checklist)
        session.decision_verdict = _build_decision_verdict(session, runtime=self.runtime)
        if session.approved_plan is not None:
            session.approved_plan = _build_approved_plan(session)

        self.store.write_session(session)
        return session

    def refresh_documentation_sync(self) -> dict[str, object]:
        bundle = _canonical_process_documentation_bundle(self.project_root)
        refresh_results: list[dict[str, object]] = []
        for name, spec in bundle.iter_specs():
            path = self.project_root / spec.path
            expected = spec.render_markdown()
            current = path.read_text(encoding="utf-8") if path.exists() else None
            if current != expected:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(expected, encoding="utf-8")
                refresh_status = "created" if current is None else "updated"
            else:
                refresh_status = "unchanged"
            refresh_results.append(
                {
                    "name": name,
                    "path": spec.path,
                    "status": refresh_status,
                }
            )
        snapshot = _build_doc_sync_status_for_project(self.project_root, self.runtime, refresh_results=refresh_results)
        return snapshot

    def _review_provider(self) -> str:
        return self._review_provider_status("claude").provider

    def _review_provider_status(self, provider: str) -> ProviderStatus:
        if self.runtime.__class__.__name__ != "CommandJobRuntime":
            return ProviderStatus(provider=provider, available=True, detail="mock runtime uses deterministic reviewer")
        checker = self.provider_health_check
        status = checker(provider) if callable(checker) else checker.check(provider)
        if status.available:
            return status
        return ProviderStatus(provider="mock", available=False, detail=status.detail)

    def status(self, session_id: str) -> PlanSession:
        session = self.store.read_session(session_id)
        session.doc_sync = self._build_doc_sync_status()
        session.compliance = _build_compliance_status_for_session(
            project_root=self.project_root,
            doc_sync=session.doc_sync,
            session=session,
            run_store=self.orchestrator.run_store,
            plans_root=self.store.root,
        )
        session = _reconcile_linked_execution_state(session, self.orchestrator.run_store)
        session.structured_brief.checklist_summary = _build_checklist_summary(session.checklist)
        return session

    def resume(self, session_id: str, apply: bool = False) -> PlanSession:
        session = self.store.read_session(session_id)
        session.doc_sync = self._build_doc_sync_status()
        session.compliance = _build_compliance_status_for_session(
            project_root=self.project_root,
            doc_sync=session.doc_sync,
            session=session,
            run_store=self.orchestrator.run_store,
            plans_root=self.store.root,
        )
        session = _reconcile_linked_execution_state(session, self.orchestrator.run_store)
        normalized = self.round_controller.normalize_resume(session)
        normalized.structured_brief.checklist_summary = _build_checklist_summary(normalized.checklist)
        if apply:
            return _resume_apply_action(self, normalized)
        return normalized

    def approve(self, session_id: str) -> PlanSession:
        session = self.store.read_session(session_id)
        session.doc_sync = self._build_doc_sync_status()
        session.compliance = _build_compliance_status_for_session(
            project_root=self.project_root,
            doc_sync=session.doc_sync,
            session=session,
            run_store=self.orchestrator.run_store,
            plans_root=self.store.root,
        )
        _validate_compliance_ready(session)
        self.round_controller.validate_approve(session)
        session.status = "approved_for_execution"
        session.gate_verdict = "approved"
        session.resume.current_phase = "approved"
        session.resume.approved_at = "approved"
        session.checklist[2].completed = True
        approval_round = PlanReviewRound(
            round_type="approval",
            role="lead",
            summary="Lead approved the revised plan for execution.",
        )
        session.review_rounds.append(approval_round)
        session.resume.active_round_id = approval_round.id
        session.structured_brief.decision_rationale = _build_decision_rationale(session.requirement, session, get_policy(OrchestrationMode.SUCCESS_FIRST))
        session.decision_verdict = _build_decision_verdict(session, runtime=self.runtime)
        session.approved_plan = _build_approved_plan(session)
        session.structured_brief.checklist_summary = _build_checklist_summary(session.checklist)
        session.doc_sync = self.refresh_documentation_sync()
        session.compliance = _build_compliance_status_for_session(
            project_root=self.project_root,
            doc_sync=session.doc_sync,
            session=session,
            run_store=self.orchestrator.run_store,
            plans_root=self.store.root,
        )
        self.store.write_session(session)
        return session

    def revise(self, session_id: str, *, summary: str, closed_gap_ids: list[str]) -> PlanSession:
        session = self.store.read_session(session_id)
        session.doc_sync = self._build_doc_sync_status()
        session.compliance = _build_compliance_status_for_session(
            project_root=self.project_root,
            doc_sync=session.doc_sync,
            session=session,
            run_store=self.orchestrator.run_store,
            plans_root=self.store.root,
        )
        self.round_controller.validate_revision(session, closed_gap_ids)
        closed_ids = set(closed_gap_ids)
        for gap in session.gaps:
            if gap.id in closed_ids:
                gap.status = "closed"
        revision_round = PlanReviewRound(
            round_type="revision",
            role="lead",
            summary=summary,
        )
        session.review_rounds.append(revision_round)
        session.resume.active_round_id = revision_round.id
        session.resume.current_phase = "in_review"
        session.resume.pending_role = "lead"
        session.decision_verdict = _build_decision_verdict(session, runtime=self.runtime)
        session.structured_brief.checklist_summary = _build_checklist_summary(session.checklist)
        self.store.write_session(session)
        return session

    def execute(self, session_id: str, mode: OrchestrationMode | None = OrchestrationMode.SUCCESS_FIRST) -> PlanSession:
        session = self.store.read_session(session_id)
        session.doc_sync = self._build_doc_sync_status()
        session.compliance = _build_compliance_status_for_session(
            project_root=self.project_root,
            doc_sync=session.doc_sync,
            session=session,
            run_store=self.orchestrator.run_store,
            plans_root=self.store.root,
        )
        _validate_compliance_ready(session)
        self.round_controller.validate_execute(session)
        if session.approved_plan is None:
            raise ValueError("team execute requires an approved plan artifact before execution")

        self.orchestrator.run_store.__post_init__()
        session.status = "executing"
        session.resume.current_phase = "executing"
        session.resume.pending_role = "build"
        self.store.write_session(session)

        execution_requirement = session.approved_plan["goal"] if session.approved_plan else session.requirement
        run = self.orchestrator.run(execution_requirement, mode)
        payload = run.to_dict()
        metadata = dict(payload.get("metadata", {}))
        provenance = dict(metadata.get("provenance", {}))
        provenance.update(
            {
                "plan_session_id": session.id,
                "approved_plan_goal": execution_requirement,
                "selected_topology": session.decision_verdict.selected_topology if session.decision_verdict else None,
                "selected_provider_runtime": session.decision_verdict.selected_provider_runtime if session.decision_verdict else {},
                "decision_rationale": session.decision_verdict.rationale if session.decision_verdict else [],
            }
        )
        metadata.update(
            {
                "approved_plan": session.approved_plan,
                "plan_session_id": session.id,
                "approved_plan_summary": {
                    "session_id": session.id,
                    "goal": session.approved_plan.get("goal") if session.approved_plan else execution_requirement,
                    "selected_topology": session.decision_verdict.selected_topology if session.decision_verdict else None,
                    "selected_provider_runtime": session.decision_verdict.selected_provider_runtime if session.decision_verdict else {},
                },
                "provenance": provenance,
            }
        )
        payload["metadata"] = metadata
        self.orchestrator.run_store.write(run.run_id, payload)
        session.resume.linked_execution_run_id = run.run_id
        lead_verdict = _finalize_execution(session, run)
        session.gate_verdict = lead_verdict
        session.status = lead_verdict
        session.resume.current_phase = lead_verdict
        session.resume.pending_role = "lead"
        session.decision_verdict = _build_decision_verdict(session, runtime=self.runtime, approval_status=lead_verdict)
        session.approved_plan = _build_approved_plan(session)
        session.structured_brief.checklist_summary = _build_checklist_summary(session.checklist)
        session.doc_sync = self.refresh_documentation_sync()
        session.compliance = _build_compliance_status_for_session(
            project_root=self.project_root,
            doc_sync=session.doc_sync,
            session=session,
            run_store=self.orchestrator.run_store,
            plans_root=self.store.root,
        )
        self.store.write_session(session)
        return session

    def inspect_execution(self, session_id: str) -> dict[str, object]:
        session = self.store.read_session(session_id)
        run_id = session.resume.linked_execution_run_id
        if not run_id:
            raise ValueError("team inspect-execution requires a session with a linked execution run")
        if not self.orchestrator.run_store.exists(run_id):
            raise ValueError("team inspect-execution could not find the linked execution run artifact")
        session.doc_sync = self._build_doc_sync_status()
        session.compliance = _build_compliance_status_for_session(
            project_root=self.project_root,
            doc_sync=session.doc_sync,
            session=session,
            run_store=self.orchestrator.run_store,
            plans_root=self.store.root,
        )
        session = _reconcile_linked_execution_state(session, self.orchestrator.run_store)
        payload = self.orchestrator.run_store.read(run_id)
        if isinstance(payload, dict):
            payload["session_summary"] = _build_execution_session_summary(session, payload)
        return payload

    def inspect_blockers(self, session_id: str) -> dict[str, object]:
        session = self.store.read_session(session_id)
        session.doc_sync = self._build_doc_sync_status()
        session.compliance = _build_compliance_status_for_session(
            project_root=self.project_root,
            doc_sync=session.doc_sync,
            session=session,
            run_store=self.orchestrator.run_store,
            plans_root=self.store.root,
        )
        session = _reconcile_linked_execution_state(session, self.orchestrator.run_store)
        payload = session.to_dict()
        payload["blocker_summary"] = _build_blocker_session_summary(session)
        if session.resume.linked_execution_run_id and self.orchestrator.run_store.exists(session.resume.linked_execution_run_id):
            payload["linked_execution_run"] = {
                "run_id": session.resume.linked_execution_run_id,
                "exists": True,
            }
        return payload

    def _build_doc_sync_status(self) -> dict[str, object]:
        return _build_doc_sync_status_for_project(self.project_root, self.runtime)

    def _build_compliance_status(
        self,
        doc_sync: dict[str, object] | None,
        *,
        changed_files: list[str] | None = None,
    ) -> dict[str, object]:
        return _build_compliance_status_for_session(
            project_root=self.project_root,
            doc_sync=doc_sync,
            plans_root=self.store.root,
            changed_files=changed_files,
        )

    def check_compliance(self, changed_files: list[str] | None = None) -> dict[str, object]:
        doc_sync = _build_doc_sync_status_for_project(
            self.project_root,
            self.runtime,
            changed_files=changed_files,
        )
        return _build_compliance_status_for_session(
            project_root=self.project_root,
            doc_sync=doc_sync,
            plans_root=self.store.root,
            changed_files=changed_files,
        )

    def check_session_compliance(self, session_id: str, changed_files: list[str] | None = None) -> dict[str, object]:
        session = self.store.read_session(session_id)
        doc_sync = _build_doc_sync_status_for_project(
            self.project_root,
            self.runtime,
            changed_files=changed_files,
        )
        return _build_compliance_status_for_session(
            project_root=self.project_root,
            doc_sync=doc_sync,
            session=session,
            run_store=self.orchestrator.run_store,
            plans_root=self.store.root,
            changed_files=changed_files,
        )


def _canonical_process_documentation_bundle(project_root: Path) -> ProcessDocumentationBundle:
    module_entries = _collect_module_manifest_entries(project_root)
    module_manifest_bullets: tuple[str, ...] = ("file-header contract", "root map")
    if module_entries:
        module_manifest_bullets = (*module_manifest_bullets, *module_entries)
    root_map_entries = _collect_root_map_entries(project_root)
    return ProcessDocumentationBundle(
        root_map=ProcessDocumentSpec(
            path="docs/process/root-map.md",
            title="Root Map",
            bullets=("module manifests", "file-header contract", "compliance checks", *root_map_entries),
        ),
        module_manifest=ProcessDocumentSpec(
            path="docs/process/module-manifest.md",
            title="Module Manifest",
            bullets=module_manifest_bullets,
        ),
        file_header_contract=ProcessDocumentSpec(
            path="docs/process/file-header-contract.md",
            title="File Header Contract",
            bullets=("required header fields", "module manifest linkage"),
        ),
    )


def _build_doc_sync_status_for_project(
    project_root: Path,
    runtime: JobRuntime,
    *,
    refresh_results: list[dict[str, object]] | None = None,
    changed_files: list[str] | None = None,
) -> dict[str, object]:
    required_docs = [
        "README.md",
        "docs/process/长周期主执行计划.md",
        "docs/process/agent-orchestrator-implementation-process.md",
        "docs/architecture/决策核心-执行拓扑-运行时分层说明.md",
        "docs/process/root-map.md",
        "docs/process/module-manifest.md",
        "docs/process/file-header-contract.md",
    ]
    missing = [relative_path for relative_path in required_docs if not (project_root / relative_path).exists()]
    jobs_root = str(getattr(runtime, "root", "")) if hasattr(runtime, "root") else ""
    header_contract_violations = _scan_source_file_headers(project_root, changed_files=changed_files)

    document_statuses: dict[str, dict[str, object]] = {}
    stale_docs: list[dict[str, object]] = []
    bundle = _canonical_process_documentation_bundle(project_root)
    for name, spec in bundle.iter_specs():
        path = project_root / spec.path
        expected = spec.to_dict()
        if not path.exists():
            status = {
                "name": name,
                "path": spec.path,
                "status": "missing",
                "expected": expected,
                "actual": None,
            }
            document_statuses[name] = status
            stale_docs.append(status)
            continue
        text = path.read_text(encoding="utf-8")
        try:
            actual_spec = ProcessDocumentSpec.from_markdown(spec.path, text)
        except ValueError as exc:
            status = {
                "name": name,
                "path": spec.path,
                "status": "stale",
                "expected": expected,
                "actual": None,
                "reason": str(exc),
            }
            document_statuses[name] = status
            stale_docs.append(status)
            continue
        if actual_spec.title != spec.title or actual_spec.bullets != spec.bullets:
            status = {
                "name": name,
                "path": spec.path,
                "status": "stale",
                "expected": expected,
                "actual": actual_spec.to_dict(),
                "reason": "document content does not match canonical structure",
            }
            document_statuses[name] = status
            stale_docs.append(status)
            continue
        document_statuses[name] = {
            "name": name,
            "path": spec.path,
            "status": "passed",
            "expected": expected,
            "actual": actual_spec.to_dict(),
        }

    payload: dict[str, object] = {
        "project_root": str(project_root),
        "jobs_root": jobs_root,
        "required_docs_checked": len(required_docs),
        "missing_docs": missing,
        "stale_docs": stale_docs,
        "header_contract_violations": header_contract_violations,
        "documents": document_statuses,
    }
    if refresh_results is not None:
        payload["refresh_results"] = refresh_results
    if changed_files is not None:
        payload["changed_files"] = list(changed_files)
    return payload


def _scan_source_file_headers(project_root: Path, *, changed_files: list[str] | None = None) -> list[str]:
    source_root = project_root / "src" / "agent_orchestrator"
    if not source_root.exists():
        return []

    selected_paths: set[Path] | None = None
    if changed_files:
        selected_paths = set()
        for item in changed_files:
            changed_path = project_root / item
            if changed_path.suffix == ".py" and changed_path.parent == source_root:
                selected_paths.add(changed_path)

    violations: list[str] = []
    for path in sorted(source_root.glob("*.py")):
        if selected_paths is not None and path not in selected_paths:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            violations.append(f"header contract violation: {path.relative_to(project_root)} is empty")
            continue
        docstring_end_index = _find_module_docstring_end(lines)
        if docstring_end_index is None:
            violations.append(
                f"header contract violation: {path.relative_to(project_root)} missing module docstring header"
            )
            continue
        nonempty_after_docstring = [line.strip() for line in lines[docstring_end_index + 1 :] if line.strip()]
        if path.name == "__init__.py":
            continue
        if not nonempty_after_docstring:
            violations.append(
                f"header contract violation: {path.relative_to(project_root)} missing required module manifest linkage"
            )
            continue
        if nonempty_after_docstring[0] != "from __future__ import annotations":
            violations.append(
                f"header contract violation: {path.relative_to(project_root)} missing `from __future__ import annotations`"
            )
    return violations


def _find_module_docstring_end(lines: list[str]) -> int | None:
    if not lines:
        return None
    first = lines[0].strip()
    if not first.startswith('"""'):
        return None
    if first.count('"""') >= 2 and first != '"""':
        return 0
    for index, line in enumerate(lines[1:], start=1):
        if '"""' in line:
            return index
    return None


def _collect_module_manifest_entries(project_root: Path) -> tuple[str, ...]:
    source_root = project_root / "src" / "agent_orchestrator"
    if not source_root.exists():
        return ()

    entries: list[str] = []
    for path in sorted(source_root.glob("*.py")):
        if path.name == "__init__.py":
            continue
        summary = _extract_module_summary(path)
        entries.append(f"`{path.name}`: {summary}")
    return tuple(entries)


def _collect_root_map_entries(project_root: Path) -> tuple[str, ...]:
    entries: list[str] = []
    package_root = project_root / "src" / "agent_orchestrator"
    if package_root.exists():
        entries.append("`src/agent_orchestrator/`: primary Python package")

    docs_root = project_root / "docs" / "process"
    if docs_root.exists():
        impl_process = docs_root / "agent-orchestrator-implementation-process.md"
        runbook = docs_root / "agent-team-operator-runbook.md"
        if impl_process.exists():
            entries.append("`docs/process/agent-orchestrator-implementation-process.md`: implementation supervision source of truth")
        if runbook.exists():
            entries.append("`docs/process/agent-team-operator-runbook.md`: operator workflow recovery guide")
    return tuple(entries)


def _extract_module_summary(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    end_index = _find_module_docstring_end(lines)
    if end_index is None:
        return "Missing module docstring."
    docstring_lines = lines[: end_index + 1]
    text = "\n".join(docstring_lines).strip()
    if text.startswith('"""'):
        text = text[3:]
    if text.endswith('"""'):
        text = text[:-3]
    cleaned = " ".join(line.strip() for line in text.splitlines()).strip()
    return cleaned or "Undocumented module."


def _manifest_entry_paths(spec: ProcessDocumentSpec) -> set[str]:
    module_paths: set[str] = set()
    for bullet in spec.bullets:
        stripped = str(bullet)
        if not stripped.startswith("`"):
            continue
        if "`:" not in stripped:
            continue
        module_paths.add(stripped.split("`:", 1)[0].strip("`"))
    return module_paths


def _build_compliance_status_for_session(
    *,
    project_root: Path,
    doc_sync: dict[str, object] | None,
    session: PlanSession | None = None,
    run_store: Any | None = None,
    plans_root: Path | str | None = None,
    changed_files: list[str] | None = None,
) -> dict[str, object]:
    missing_docs = list(doc_sync.get("missing_docs", [])) if isinstance(doc_sync, dict) else []
    stale_docs = list(doc_sync.get("stale_docs", [])) if isinstance(doc_sync, dict) else []
    header_contract_violations = (
        list(doc_sync.get("header_contract_violations", []))
        if isinstance(doc_sync, dict)
        else []
    )
    blocking_reasons: list[str] = []
    if missing_docs:
        blocking_reasons.append("missing required docs: " + ", ".join(str(item) for item in missing_docs))
    if stale_docs:
        stale_names = [str(item.get("path", item.get("name", "unknown"))) for item in stale_docs if isinstance(item, dict)]
        blocking_reasons.append("stale document structure: " + ", ".join(stale_names))
    if header_contract_violations:
        blocking_reasons.extend(str(item) for item in header_contract_violations)

    if not missing_docs and not stale_docs:
        readme_path = project_root / "README.md"
        readme_text = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
        if "agent-team-operator-runbook.md" not in readme_text:
            blocking_reasons.append("README missing operator runbook link")

        long_plan_path = project_root / "docs" / "process" / "长周期主执行计划.md"
        long_plan_text = long_plan_path.read_text(encoding="utf-8") if long_plan_path.exists() else ""
        if "文档同步 / compliance / hook blocking" not in long_plan_text:
            blocking_reasons.append("long-cycle plan missing happy-path compliance clause")

        impl_process_path = project_root / "docs" / "process" / "agent-orchestrator-implementation-process.md"
        impl_process_text = impl_process_path.read_text(encoding="utf-8") if impl_process_path.exists() else ""
        if "hook-based compliance checks" not in impl_process_text:
            blocking_reasons.append("implementation process doc missing compliance hook language")

        runbook_path = project_root / "docs" / "process" / "agent-team-operator-runbook.md"
        runbook_text = runbook_path.read_text(encoding="utf-8") if runbook_path.exists() else ""
        required_runbook_signals = ["topology_reason", "fallback_reason", "fallback_detail"]
        if any(signal not in runbook_text for signal in required_runbook_signals):
            blocking_reasons.append("operator runbook missing topology/fallback signals")
        required_guidance_commands = [
            "team summary",
            "team next",
            "team runbook",
            "team resume",
            "team inspect-blockers",
            "team inspect-execution",
            "team retry-review",
            "team retry-adversarial-review",
            "team check-compliance",
        ]
        if any(command not in runbook_text for command in required_guidance_commands):
            blocking_reasons.append("operator runbook missing canonical guidance commands")

        root_map_path = project_root / "docs" / "process" / "root-map.md"
        root_map_text = root_map_path.read_text(encoding="utf-8") if root_map_path.exists() else ""
        if "module manifests" not in root_map_text:
            blocking_reasons.append("root map missing module manifest linkage")

        manifest_path = project_root / "docs" / "process" / "module-manifest.md"
        manifest_text = manifest_path.read_text(encoding="utf-8") if manifest_path.exists() else ""
        if "file-header contract" not in manifest_text:
            blocking_reasons.append("module manifest missing file-header contract linkage")
        else:
            try:
                manifest_spec = ProcessDocumentSpec.from_markdown("docs/process/module-manifest.md", manifest_text)
            except ValueError:
                manifest_spec = None
            if manifest_spec is not None:
                documented_modules = _manifest_entry_paths(manifest_spec)
                actual_modules = {
                    path.name
                    for path in (project_root / "src" / "agent_orchestrator").glob("*.py")
                    if path.name != "__init__.py"
                }
                if documented_modules != actual_modules:
                    blocking_reasons.append(
                        "module manifest coverage mismatch: documented modules do not match source modules"
                    )

        header_contract_path = project_root / "docs" / "process" / "file-header-contract.md"
        header_contract_text = header_contract_path.read_text(encoding="utf-8") if header_contract_path.exists() else ""
        if "required header fields" not in header_contract_text:
            blocking_reasons.append("file-header contract missing required header fields")

    if session is not None and session.resume.linked_execution_run_id and run_store is not None:
        try:
            payload = run_store.read(session.resume.linked_execution_run_id)
        except Exception:
            payload = {}
        metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
        linked_session_id = metadata.get("plan_session_id")
        approved_plan = metadata.get("approved_plan", {})
        if linked_session_id != session.id:
            blocking_reasons.append("run provenance mismatch: linked run session id does not match current plan session")
        if isinstance(approved_plan, dict) and approved_plan.get("session_id") != session.id:
            blocking_reasons.append("run provenance mismatch: approved plan session id does not match current plan session")

    if session is not None and plans_root is not None:
        session_dir = Path(plans_root) / session.id
        if not (session_dir / "checklist.json").exists():
            blocking_reasons.append("missing plan artifact snapshot: checklist.json")
        if not (session_dir / "verdict.json").exists():
            blocking_reasons.append("missing plan artifact snapshot: verdict.json")
        rounds_dir = session_dir / "rounds"
        expected_round_files = [f"round-{index:03d}.json" for index, _ in enumerate(session.review_rounds, start=1)]
        if not rounds_dir.exists() or any(not (rounds_dir / name).exists() for name in expected_round_files):
            blocking_reasons.append("review round snapshots are incomplete")

    return {
        "status": "blocked" if blocking_reasons else "passed",
        "blocking": bool(blocking_reasons),
        "checks": [
            {
                "name": "required_docs_present",
                "status": "failed" if missing_docs else "passed",
                "details": "missing required docs" if missing_docs else "required docs present",
            },
            {
                "name": "docs_reference_current_workflow",
                "status": "failed"
                if any(
                    reason in blocking_reasons
                    for reason in [
                        "README missing operator runbook link",
                        "long-cycle plan missing happy-path compliance clause",
                        "implementation process doc missing compliance hook language",
                    ]
                )
                else "passed",
                "details": "workflow docs mention operator runbook and compliance gates",
            },
            {
                "name": "operator_runbook_signals_current",
                "status": "failed"
                if "operator runbook missing topology/fallback signals" in blocking_reasons
                else "passed",
                "details": "operator runbook documents topology and provider fallback signals",
            },
            {
                "name": "operator_runbook_guidance_current",
                "status": "failed"
                if "operator runbook missing canonical guidance commands" in blocking_reasons
                else "passed",
                "details": "operator runbook documents canonical session guidance commands",
            },
            {
                "name": "execution_provenance_matches_session",
                "status": "failed" if any("run provenance mismatch" in reason for reason in blocking_reasons) else "passed",
                "details": "linked execution run matches the current plan session",
            },
            {
                "name": "source_file_headers_match_contract",
                "status": "failed" if header_contract_violations else "passed",
                "details": "python source files expose the required module header contract",
            },
        ],
        "blocking_reasons": blocking_reasons,
        "changed_files": list(changed_files or []),
    }


def _select_retry_provider(session: PlanSession, runtime_status: Any) -> str:
    configured = session.structured_brief.provider_recommendation.get("reviewer")
    if isinstance(configured, str) and configured:
        return configured
    provider = getattr(runtime_status, "provider", None)
    if isinstance(provider, str) and provider:
        return provider
    return "mock"


def _reconcile_linked_execution_state(session: PlanSession, run_store: Any | None) -> PlanSession:
    if session.status != "executing" or not session.resume.linked_execution_run_id or run_store is None:
        return session
    try:
        payload = run_store.read(session.resume.linked_execution_run_id)
    except Exception:
        payload = {}
    if not isinstance(payload, dict) or not payload:
        return session
    run_status = str(payload.get("status", ""))
    if run_status not in {"completed", "blocked", "failed", "cancelled"}:
        return session
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}
    approved_plan = metadata.get("approved_plan", {}) if isinstance(metadata.get("approved_plan"), dict) else {}
    if approved_plan and approved_plan.get("session_id") not in {None, session.id}:
        return session

    if run_status == "completed":
        session.status = _finalize_execution_from_payload(session, payload)
        session.gate_verdict = session.status
        session.resume.current_phase = session.status
        session.resume.pending_role = "lead"
        if session.decision_verdict is not None:
            session.decision_verdict = DecisionVerdict(
                approval_status=session.status,
                required_gaps=[gap.to_dict() for gap in session.gaps if gap.required and gap.status != "closed"],
                followup_gaps=[gap.to_dict() for gap in session.gaps if not gap.required and gap.status != "closed"],
                selected_topology=session.decision_verdict.selected_topology,
                selected_provider_runtime=session.decision_verdict.selected_provider_runtime,
                rationale=session.decision_verdict.rationale,
            )
        return session

    session.status = "blocked"
    session.gate_verdict = "blocked"
    session.resume.current_phase = "blocked"
    session.resume.pending_role = "lead"
    if session.decision_verdict is not None:
        session.decision_verdict = DecisionVerdict(
            approval_status="blocked",
            required_gaps=[gap.to_dict() for gap in session.gaps if gap.required and gap.status != "closed"],
            followup_gaps=[gap.to_dict() for gap in session.gaps if not gap.required and gap.status != "closed"],
            selected_topology=session.decision_verdict.selected_topology,
            selected_provider_runtime=session.decision_verdict.selected_provider_runtime,
            rationale=session.decision_verdict.rationale,
        )
    return session


def _finalize_execution_from_payload(session: PlanSession, payload: dict[str, object]) -> Literal["accepted", "needs_followup", "blocked"]:
    findings = [
        finding
        for round_ in session.review_rounds
        if round_.review_result
        for finding in round_.review_result.findings
    ]
    if any(finding.severity in {"high", "critical"} for finding in findings):
        return "blocked"
    if any(finding.severity in {"low", "medium"} for finding in findings):
        return "needs_followup"
    return "accepted" if bool(payload.get("accepted", False)) else "blocked"


def _execution_block_detail(session: PlanSession) -> str | None:
    if not session.compliance or not isinstance(session.compliance, dict):
        return None
    reasons = [str(item) for item in session.compliance.get("blocking_reasons", [])]
    if any("run provenance mismatch" in reason for reason in reasons):
        return "provenance_mismatch"
    if session.resume.linked_execution_run_id and session.status == "blocked":
        return "run_blocked"
    return None


@dataclass(frozen=True, slots=True)
class SessionGuidance:
    session_id: str
    primary_action: str
    primary_reason: str
    resume_action: str
    resume_reason: str
    block_source: str | None
    block_detail: str | None
    recommended_commands: list[str]
    recovery_actions: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "primary_action": self.primary_action,
            "primary_reason": self.primary_reason,
            "resume_action": self.resume_action,
            "resume_reason": self.resume_reason,
            "block_source": self.block_source,
            "block_detail": self.block_detail,
            "recommended_commands": list(self.recommended_commands),
            "recovery_actions": list(self.recovery_actions),
        }


BLOCK_SOURCES = {"compliance", "delegated_job", "execution_run", "review", "awaiting_human"}


def build_session_guidance(session: PlanSession) -> SessionGuidance:
    required_open = [gap for gap in session.gaps if gap.required and gap.status != "closed"]
    optional_open = [gap for gap in session.gaps if not gap.required and gap.status != "closed"]
    compliance_blocking_reasons = _compliance_blocking_reasons(session)
    delegated_jobs, delegated_job_failed, delegated_job_provider = _collect_delegated_jobs(session)

    primary_action = "inspect_session"
    primary_reason = "inspect the current session state before continuing"
    resume_action = "inspect_session"
    resume_reason = "manual_inspection_required"
    block_source: str | None = None
    block_detail: str | None = None
    recovery_actions: list[str] = []

    if compliance_blocking_reasons:
        block_source = "compliance"
        primary_action = "inspect_compliance"
        primary_reason = "compliance is blocking the workflow; restore required docs before approval or execution"
        resume_action = "inspect_compliance"
        resume_reason = "compliance_blocking"
        recovery_actions = ["inspect_compliance"]
    elif delegated_job_failed and delegated_job_provider == "claude":
        block_source = "delegated_job"
        if _has_failed_delegated_family(delegated_jobs, {"adversarial_review", "adversarial_review_retry"}):
            block_detail = "failed_adversarial_review_job"
            primary_action = "retry_adversarial_review"
            resume_action = "retry_adversarial_review"
            resume_reason = "failed_adversarial_review_job"
            recovery_actions = ["inspect_delegated_job", "retry_adversarial_review", "revise_plan"]
        else:
            block_detail = "failed_review_job"
            primary_action = "retry_review"
            resume_action = "retry_review"
            resume_reason = "failed_review_job"
            recovery_actions = ["inspect_delegated_job", "retry_review", "revise_plan"]
        primary_reason = "delegated job failed; inspect the failed Claude job before deciding whether to revise or retry"
    elif delegated_job_failed:
        block_source = "delegated_job"
        block_detail = "failed_delegated_job"
        primary_action = "inspect_delegated_job"
        primary_reason = "delegated job failed; inspect the failed job before continuing"
        resume_action = "inspect_delegated_job"
        resume_reason = "failed_delegated_job"
        recovery_actions = ["inspect_delegated_job", "revise_plan"]
    elif session.status == "needs_revision" and required_open:
        block_source = "review"
        primary_action = "revise"
        primary_reason = f"{len(required_open)} required gaps are still open; revise the plan before approval"
        resume_action = "revise"
        resume_reason = "required_gaps_open"
    elif session.status == "needs_revision":
        primary_action = "approve"
        primary_reason = "all required gaps are closed; approval is now allowed"
        resume_action = "approve"
        resume_reason = "required_gaps_closed"
    elif session.status == "approved_for_execution":
        primary_action = "execute"
        primary_reason = "plan is approved; execution is the next valid action"
        resume_action = "execute"
        resume_reason = "approved_plan_ready"
    elif session.status == "executing":
        primary_action = "wait_for_execution"
        primary_reason = "execution is in progress; wait for completion or inspect the linked run"
        resume_action = "wait_for_execution"
        resume_reason = "execution_in_progress"
    elif session.status in {"accepted", "needs_followup"}:
        primary_action = "inspect_execution"
        primary_reason = "execution completed; inspect the linked run and any follow-up guidance"
        resume_action = "inspect_execution"
        resume_reason = "execution_completed"
    elif session.status == "awaiting_human":
        block_source = "awaiting_human"
        primary_action = "human_decision"
        primary_reason = "human confirmation is required before the workflow can continue"
        resume_action = "human_decision"
        resume_reason = "human_confirmation_required"
        recovery_actions = ["human_decision"]
    elif session.status == "blocked":
        primary_action = "inspect_blockers"
        resume_action = "inspect_blockers"
        resume_reason = "review_blocked"
        recovery_actions = ["inspect_blockers"]
        if session.resume.linked_execution_run_id and not required_open:
            block_source = "execution_run"
            block_detail = _execution_block_detail(session) or "run_blocked"
            primary_reason = "execution ended in a blocked state; inspect the linked run before changing the plan"
            recovery_actions = ["inspect_blockers", "inspect_execution"]
            if block_detail == "provenance_mismatch":
                recovery_actions.append("inspect_compliance")
        else:
            block_source = "review"
            primary_reason = "the workflow is blocked; inspect blocking review findings"

    commands = _guidance_commands(session.id, primary_action, resume_action, recovery_actions)
    return SessionGuidance(
        session_id=session.id,
        primary_action=primary_action,
        primary_reason=primary_reason,
        resume_action=resume_action,
        resume_reason=resume_reason,
        block_source=block_source,
        block_detail=block_detail,
        recommended_commands=commands,
        recovery_actions=recovery_actions,
    )


def _guidance_commands(
    session_id: str,
    primary_action: str,
    resume_action: str,
    recovery_actions: list[str],
) -> list[str]:
    actions = [primary_action]
    if resume_action not in actions:
        actions.append(resume_action)
    for action in recovery_actions:
        if action not in actions:
            actions.append(action)
    commands: list[str] = []
    for action in actions:
        command = _resume_guidance_command(session_id, action)
        if command not in commands:
            commands.append(command)
    return commands


def _compliance_blocking_reasons(session: PlanSession) -> list[str]:
    if not isinstance(session.compliance, dict):
        return []
    return [str(item) for item in session.compliance.get("blocking_reasons", [])]


def _collect_delegated_jobs(session: PlanSession) -> tuple[list[dict[str, object]], bool, str | None]:
    delegated_jobs: list[dict[str, object]] = []
    delegated_job_failed = False
    delegated_job_provider = None
    latest_round_by_family: dict[str, PlanReviewRound] = {}
    for round_ in session.review_rounds:
        family = _delegated_round_family(round_.round_type)
        if family:
            latest_round_by_family[family] = round_

    for round_ in session.review_rounds:
        summary = round_.summary
        if " job " not in summary:
            continue
        job_status = "completed"
        job_summary = summary
        job_error = None
        job_id = summary.split("job ")[-1].rstrip(".")
        runtime_status = _read_delegated_job_status(session, job_id)
        if runtime_status:
            job_status = runtime_status.status
            job_summary = runtime_status.summary or summary
            job_error = runtime_status.error
            provider = runtime_status.provider
            if runtime_status.status == "failed" and latest_round_by_family.get(_delegated_round_family(round_.round_type) or "") is round_:
                delegated_job_failed = True
        else:
            provider = "claude" if "claude" in summary else "mock"
        if job_status == "failed" and latest_round_by_family.get(_delegated_round_family(round_.round_type) or "") is round_ and delegated_job_provider is None:
            delegated_job_provider = provider
        delegated_jobs.append(
            {
                "round_type": round_.round_type,
                "provider": provider,
                "job_id": job_id,
                "status": job_status,
                "summary": job_summary,
                "error": job_error,
            }
        )
    return delegated_jobs, delegated_job_failed, delegated_job_provider


def _has_failed_delegated_family(delegated_jobs: list[dict[str, object]], round_types: set[str]) -> bool:
    return any(
        str(job.get("round_type")) in round_types and str(job.get("status")) == "failed"
        for job in delegated_jobs
    )


def _build_execution_session_summary(session: PlanSession, payload: dict[str, object]) -> dict[str, object]:
    guidance = build_session_guidance(session)
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}
    provenance = metadata.get("provenance", {}) if isinstance(metadata.get("provenance"), dict) else {}
    approved_plan_summary = (
        metadata.get("approved_plan_summary", {})
        if isinstance(metadata.get("approved_plan_summary"), dict)
        else {}
    )
    compliance = session.compliance if isinstance(session.compliance, dict) else {}
    blocking_reasons = [str(item) for item in compliance.get("blocking_reasons", [])]
    outcome = "accepted" if bool(payload.get("accepted", False)) else str(payload.get("status", "unknown"))
    if session.status == "needs_followup":
        outcome = "needs_followup"
    if session.status == "blocked":
        detail = _execution_block_detail(session)
        if detail == "provenance_mismatch":
            outcome = "blocked_provenance_mismatch"
        elif detail == "run_blocked":
            outcome = "blocked_execution_run"
    return {
        "session_id": session.id,
        "run_id": session.resume.linked_execution_run_id,
        "session_status": session.status,
        "outcome": outcome,
        "goal": approved_plan_summary.get("goal") or provenance.get("approved_plan_goal") or session.requirement,
        "selected_topology": approved_plan_summary.get("selected_topology") or provenance.get("selected_topology"),
        "selected_provider_runtime": approved_plan_summary.get("selected_provider_runtime") or provenance.get("selected_provider_runtime"),
        "blocking_reasons": blocking_reasons,
        "primary_action": guidance.primary_action,
        "primary_reason": guidance.primary_reason,
        "resume_action": guidance.resume_action,
        "resume_reason": guidance.resume_reason,
        "recommended_commands": guidance.recommended_commands,
    }


def _build_blocker_session_summary(session: PlanSession) -> dict[str, object]:
    status_summary = _build_status_summary(session)
    guidance = build_session_guidance(session)

    evidence: dict[str, object] = {
        "required_open_gaps": int(status_summary.get("open_required_gaps", 0)),
        "optional_open_followups": int(status_summary.get("open_optional_followups", 0)),
    }
    delegated_jobs = status_summary.get("delegated_jobs", [])
    failed_jobs = [
        job for job in delegated_jobs if isinstance(job, dict) and str(job.get("status")) == "failed"
    ]
    if failed_jobs:
        failed_job = failed_jobs[0]
        evidence["failed_job"] = {
            "job_id": failed_job.get("job_id"),
            "provider": failed_job.get("provider"),
            "round_type": failed_job.get("round_type"),
            "error": failed_job.get("error"),
        }
    if session.resume.linked_execution_run_id:
        evidence["linked_execution_run_id"] = session.resume.linked_execution_run_id
    if isinstance(session.compliance, dict):
        compliance_blocking_reasons = [str(item) for item in session.compliance.get("blocking_reasons", [])]
        if compliance_blocking_reasons:
            evidence["compliance_blocking_reasons"] = compliance_blocking_reasons

    return {
        "session_id": session.id,
        "session_status": session.status,
        "block_source": guidance.block_source,
        "block_detail": guidance.block_detail,
        "primary_action": guidance.primary_action,
        "primary_reason": guidance.primary_reason,
        "resume_action": guidance.resume_action,
        "resume_reason": guidance.resume_reason,
        "blocking_reasons": [str(item) for item in status_summary.get("blocking_reasons", [])],
        "recommended_commands": guidance.recommended_commands,
        "recovery_actions": guidance.recovery_actions,
        "evidence": evidence,
    }


def _observed_failure_provider(runtime_status: Any, session: PlanSession) -> str | None:
    provider = getattr(runtime_status, "provider", None)
    if isinstance(provider, str) and provider:
        return provider
    configured = session.structured_brief.provider_recommendation.get("reviewer")
    if isinstance(configured, str) and configured:
        return configured
    return None


def _planned_recovery_provider(session: PlanSession, runtime_status: Any) -> str | None:
    provider = _select_retry_provider(session, runtime_status)
    return provider if isinstance(provider, str) and provider else None


def _recovery_policy_for_session(
    session: PlanSession,
    *,
    preferred_round_type: str | None = None,
    provider_mode: str = "observed",
) -> dict[str, str | None]:
    recommendation = session.structured_brief.provider_recommendation
    reviewer = recommendation.get("reviewer")
    fallback_from = recommendation.get("fallback_from")
    fallback_reason = recommendation.get("fallback_reason")
    fallback_detail = recommendation.get("fallback_detail")
    latest_review = _latest_round(session.review_rounds, "review")
    latest_adversarial = _latest_round(session.review_rounds, "adversarial_review")
    candidate_order: list[tuple[str, PlanReviewRound | None]] = []
    if preferred_round_type == "review":
        candidate_order = [("review", latest_review), ("adversarial_review", latest_adversarial)]
    elif preferred_round_type == "adversarial_review":
        candidate_order = [("adversarial_review", latest_adversarial), ("review", latest_review)]
    else:
        candidate_order = [("adversarial_review", latest_adversarial), ("review", latest_review)]
    for round_type, round_ in candidate_order:
        if round_ is None:
            continue
        job_id = _extract_job_id(round_.summary)
        runtime_status = _read_delegated_job_status(session, job_id) if job_id else None
        if runtime_status is not None and runtime_status.status == "failed":
            if provider_mode == "planned":
                provider = _planned_recovery_provider(session, runtime_status)
            else:
                provider = _observed_failure_provider(runtime_status, session)
            return {
                "round_type": round_type,
                "provider": provider,
                "fallback_from": str(fallback_from) if isinstance(fallback_from, str) else None,
                "fallback_reason": str(fallback_reason) if isinstance(fallback_reason, str) else None,
                "fallback_detail": str(fallback_detail) if isinstance(fallback_detail, str) else None,
            }
    return {
        "round_type": None,
        "provider": str(reviewer) if isinstance(reviewer, str) else None,
        "fallback_from": str(fallback_from) if isinstance(fallback_from, str) else None,
        "fallback_reason": str(fallback_reason) if isinstance(fallback_reason, str) else None,
        "fallback_detail": str(fallback_detail) if isinstance(fallback_detail, str) else None,
    }


def _resume_apply_action(team: TeamOrchestrator, session: PlanSession) -> PlanSession:
    guidance = build_session_guidance(session)
    action = guidance.resume_action
    inspect_only_actions = {
        "inspect_execution",
        "inspect_compliance",
        "human_decision",
        "wait_for_execution",
        "inspect_blockers",
        "inspect_delegated_job",
        "inspect_session",
        "revise",
    }
    if action in inspect_only_actions:
        next_command = _resume_guidance_command(session.id, action)
        reason = guidance.resume_reason
        raise ValueError(
            f"team resume --apply cannot auto-apply resume action '{action}' "
            f"(reason: {reason}); next command: {next_command}"
        )
    if action == "approve":
        resumed = team.approve(session.id)
        resumed.structured_brief.checklist_summary = _build_checklist_summary(resumed.checklist)
        return resumed
    if action == "execute":
        resumed = team.execute(session.id, OrchestrationMode.SUCCESS_FIRST)
        resumed.structured_brief.checklist_summary = _build_checklist_summary(resumed.checklist)
        return resumed
    if action == "retry_review":
        return team.retry_review(session.id)
    if action == "retry_adversarial_review":
        return team.retry_adversarial_review(session.id)
    return session


def _resume_guidance_command(session_id: str, action: str) -> str:
    if action == "retry_review":
        return f"python -m agent_orchestrator.cli team retry-review {session_id}"
    if action == "retry_adversarial_review":
        return f"python -m agent_orchestrator.cli team retry-adversarial-review {session_id}"
    if action in {"revise", "revise_plan"}:
        return f"python -m agent_orchestrator.cli team revise {session_id} --summary \"close required gaps\""
    if action == "approve":
        return f"python -m agent_orchestrator.cli team approve {session_id}"
    if action == "execute":
        return f"python -m agent_orchestrator.cli team execute {session_id} --mode success_first"
    if action == "inspect_execution":
        return f"python -m agent_orchestrator.cli team inspect-execution {session_id}"
    if action == "inspect_blockers":
        return f"python -m agent_orchestrator.cli team inspect-blockers {session_id}"
    if action == "inspect_compliance":
        return f"python -m agent_orchestrator.cli team check-compliance {session_id}"
    if action == "human_decision":
        return f"python -m agent_orchestrator.cli team summary {session_id}"
    if action == "wait_for_execution":
        return f"python -m agent_orchestrator.cli team status {session_id}"
    if action == "inspect_delegated_job":
        return f"python -m agent_orchestrator.cli team inspect-blockers {session_id}"
    if action == "revise":
        return f"python -m agent_orchestrator.cli team next {session_id}"
    return f"python -m agent_orchestrator.cli team summary {session_id}"

def _team_retry_review(self: TeamOrchestrator, session_id: str) -> PlanSession:
    session = self.store.read_session(session_id)
    review_round = _latest_round(session.review_rounds, "review")
    if review_round is None:
        raise ValueError("team retry-review requires an existing review round")
    review_job_id = _extract_job_id(review_round.summary)
    runtime_status = _read_delegated_job_status(session, review_job_id) if review_job_id else None
    if runtime_status is None or runtime_status.status != "failed":
        raise ValueError("team retry-review requires a failed delegated review job")

    review_provider = _select_retry_provider(session, runtime_status)
    review_result = _review_plan(session.requirement, session)
    review_job = self.runtime.start(
        JobRequest(
            task_id=session.id,
            provider=review_provider,
            kind="review",
            prompt=f"Retry review planning round: {session.requirement}",
            cwd=str(Path.cwd()),
            metadata={"stage_target": self.stage_target, "role": "review", "round_type": "review_retry"},
        )
    )
    if hasattr(self.runtime, "complete"):
        review_job = getattr(self.runtime, "complete")(
            review_job.id,
            summary=f"Retry review round completed for {session.id}.",
            stdout=review_result.summary,
            parsed_payload={"review_result": review_result.to_dict()},
            phase="reviewing",
        )

    retry_round = PlanReviewRound(
        round_type="review_retry",
        role="review",
        summary=f"{review_result.summary} via {review_job.provider} review job {review_job.id}.",
        review_result=review_result,
    )
    session.review_rounds.append(retry_round)
    session.resume.active_round_id = retry_round.id
    session.resume.current_phase = "in_review"
    session.resume.pending_role = "lead"
    session.checklist[1].completed = True

    all_findings = [
        finding
        for round_ in session.review_rounds
        if round_.review_result and round_.round_type != "review"
        for finding in round_.review_result.findings
    ]
    if review_result.findings:
        all_findings.extend(review_result.findings)
    session.gaps = _build_plan_gaps([round_ for round_ in session.review_rounds if round_.round_type != "review"] + [retry_round])

    outcome = self.round_controller.derive_post_review_outcome(all_findings)
    session.status = outcome.status
    session.gate_verdict = outcome.gate_verdict
    if outcome.status == "approved_for_execution":
        session.resume.current_phase = "approved"
        session.resume.approved_at = "approved"
        session.checklist[2].completed = True
    else:
        session.checklist[2].completed = False

    session.structured_brief.risks = _summarize_plan_risks(all_findings)
    session.structured_brief.checklist_summary = _build_checklist_summary(session.checklist)
    self.store.write_session(session)
    return session


def _team_retry_adversarial_review(self: TeamOrchestrator, session_id: str) -> PlanSession:
    session = self.store.read_session(session_id)
    adversarial_round = _latest_round(session.review_rounds, "adversarial_review")
    if adversarial_round is None:
        raise ValueError("team retry-adversarial-review requires an existing adversarial review round")
    job_id = _extract_job_id(adversarial_round.summary)
    runtime_status = _read_delegated_job_status(session, job_id) if job_id else None
    if runtime_status is None or runtime_status.status != "failed":
        raise ValueError("team retry-adversarial-review requires a failed delegated adversarial review job")

    review_provider = _select_retry_provider(session, runtime_status)
    adversarial_result = _adversarial_review_plan(session.requirement, session)
    retry_job = self.runtime.start(
        JobRequest(
            task_id=session.id,
            provider=review_provider,
            kind="adversarial_review",
            prompt=f"Retry adversarial review planning round: {session.requirement}",
            cwd=str(Path.cwd()),
            metadata={"stage_target": self.stage_target, "role": "review", "round_type": "adversarial_review_retry"},
        )
    )
    if hasattr(self.runtime, "complete"):
        retry_job = getattr(self.runtime, "complete")(
            retry_job.id,
            summary=f"Retry adversarial review round completed for {session.id}.",
            stdout=adversarial_result.summary,
            parsed_payload={"review_result": adversarial_result.to_dict()},
            phase="reviewing",
        )

    retry_round = PlanReviewRound(
        round_type="adversarial_review_retry",
        role="review",
        summary=f"{adversarial_result.summary} via {retry_job.provider} adversarial_review job {retry_job.id}.",
        review_result=adversarial_result,
    )
    session.review_rounds.append(retry_round)
    session.resume.active_round_id = retry_round.id
    session.resume.current_phase = "in_review"
    session.resume.pending_role = "lead"
    session.checklist[1].completed = True

    all_findings = [
        finding
        for round_ in session.review_rounds
        if round_.review_result and round_.round_type != "adversarial_review"
        for finding in round_.review_result.findings
    ]
    if adversarial_result.findings:
        all_findings.extend(adversarial_result.findings)
    session.gaps = _build_plan_gaps(
        [round_ for round_ in session.review_rounds if round_.round_type != "adversarial_review"] + [retry_round]
    )

    outcome = self.round_controller.derive_post_review_outcome(all_findings)
    session.status = outcome.status
    session.gate_verdict = outcome.gate_verdict
    if outcome.status == "approved_for_execution":
        session.resume.current_phase = "approved"
        session.resume.approved_at = "approved"
        session.checklist[2].completed = True
    else:
        session.checklist[2].completed = False

    session.structured_brief.risks = _summarize_plan_risks(all_findings)
    session.structured_brief.checklist_summary = _build_checklist_summary(session.checklist)
    self.store.write_session(session)
    return session


TeamOrchestrator.retry_review = _team_retry_review
TeamOrchestrator.retry_adversarial_review = _team_retry_adversarial_review


def _review_plan(requirement: str, session: PlanSession) -> ReviewResult:
    lowered = requirement.lower()
    if "architecture direction" in lowered or "stage transition" in lowered:
        return ReviewResult(
            verdict="needs_attention",
            summary="Strategic drift requires human confirmation.",
            findings=[
                Finding(
                    severity="critical",
                    title="Human escalation required",
                    body="This requirement implies roadmap, stage, or architecture direction change.",
                    file="docs/roadmap/agent-orchestrator-master-roadmap.md",
                    line_start=1,
                    line_end=1,
                    confidence=0.95,
                    recommendation="Escalate to the human before allowing plan execution.",
                )
            ],
            next_steps=["Request human decision."],
        )
    if "auth" in lowered or "migration" in lowered or "roadmap drift" in lowered:
        return ReviewResult(
            verdict="needs_attention",
            summary="High-risk review findings block execution.",
            findings=[
                Finding(
                    severity="high",
                    title="Roadmap-sensitive high-risk change",
                    body="The plan touches a high-risk area and should not execute without a stronger decision.",
                    file="docs/process/agent-orchestrator-implementation-process.md",
                    line_start=1,
                    line_end=1,
                    confidence=0.9,
                    recommendation="Revise or escalate before execution.",
                )
            ],
            next_steps=["Revise the plan or escalate."],
        )
    if "followup" in lowered:
        return ReviewResult(
            verdict="needs_attention",
            summary="Plan is usable, but follow-up items should be tracked before or after execution.",
            findings=[
                Finding(
                    severity="medium",
                    title="Follow-up checklist needed",
                    body="The plan is acceptable but leaves non-blocking follow-up items open.",
                    file="docs/process/agent-orchestrator-implementation-process.md",
                    line_start=1,
                    line_end=1,
                    confidence=0.8,
                    recommendation="Track the follow-up in the checklist and let the lead approve explicitly.",
                )
            ],
            next_steps=["Lead approval required after acknowledging follow-up."],
        )
    return ReviewResult(verdict="approve", summary="Plan review passed.", next_steps=["Proceed to execution approval."])


def _adversarial_review_plan(requirement: str, session: PlanSession) -> ReviewResult:
    lowered = requirement.lower()
    if "adversarial challenge" in lowered:
        return ReviewResult(
            verdict="needs_attention",
            summary="Adversarial review found a non-blocking planning weakness.",
            findings=[
                Finding(
                    severity="medium",
                    title="Adversarial round requests stronger exit conditions",
                    body="The plan is plausible, but its gate conditions are not yet explicit enough for autonomous execution.",
                    file="docs/process/agent-orchestrator-implementation-process.md",
                    line_start=1,
                    line_end=1,
                    confidence=0.85,
                    recommendation="Tighten round exit conditions before approval.",
                )
            ],
            next_steps=["Revise the plan and resubmit to lead approval."],
        )
    return ReviewResult(
        verdict="approve",
        summary="Adversarial review found no additional issues.",
        next_steps=["Proceed with the lead verdict."],
    )


def _finalize_execution(session: PlanSession, run: Any) -> Literal["accepted", "needs_followup", "blocked"]:
    findings = [
        finding
        for round_ in session.review_rounds
        if round_.review_result
        for finding in round_.review_result.findings
    ]
    if any(finding.severity in {"high", "critical"} for finding in findings):
        return "blocked"
    if any(finding.severity in {"low", "medium"} for finding in findings):
        return "needs_followup"
    return "accepted" if getattr(run, "accepted", False) else "blocked"


def _summarize_plan_risks(findings: list[Finding]) -> list[str]:
    return _dedupe_preserve_order(
        f"{finding.severity}: {finding.title}"
        for finding in findings
    )


def _build_plan_gaps(review_rounds: list[PlanReviewRound]) -> list[PlanGap]:
    gaps: list[PlanGap] = []
    for round_ in review_rounds:
        if not round_.review_result:
            continue
        for finding in round_.review_result.findings:
            gaps.append(
                PlanGap(
                    title=finding.title,
                    severity=finding.severity,
                    recommendation=finding.recommendation,
                    required=finding.severity in {"high", "critical"} or "adversarial" in finding.title.lower(),
                    finding_round_id=round_.id,
                )
            )
    return gaps


def _build_approved_plan(session: PlanSession) -> dict[str, object]:
    return {
        "session_id": session.id,
        "goal": session.structured_brief.goal or session.requirement,
        "subtasks": [subtask.to_dict() for subtask in session.structured_brief.subtasks],
        "acceptance_criteria": list(session.structured_brief.acceptance_criteria),
        "open_followups": [gap.to_dict() for gap in session.gaps if gap.status != "closed"],
        "decision_verdict": session.decision_verdict.to_dict() if session.decision_verdict else None,
        "execution_contract": _build_plan_execution_contract(session),
        "gating": {
            "status": session.status,
            "gate_verdict": session.gate_verdict,
            "approved_at": session.resume.approved_at,
        },
    }


def _build_checklist_summary(checklist: list[PlanChecklistItem]) -> list[str]:
    return [
        f"{item.label} [{item.owner}]: {'done' if item.completed else 'pending'}"
        for item in checklist
    ]


def _build_plan_execution_contract(session: PlanSession) -> dict[str, object]:
    decision_verdict = session.decision_verdict.to_dict() if session.decision_verdict else {}
    provider_recommendation = dict(decision_verdict.get("selected_provider_runtime", {}))
    return ExecutionContract(
        source="approved_plan_session",
        goal=session.structured_brief.goal or session.requirement,
        acceptance_criteria=list(session.structured_brief.acceptance_criteria),
        topology={
            "selected_topology": decision_verdict.get("selected_topology"),
            "selected_mode": "success_first",
            "provider_flow": [provider_recommendation.get("reviewer"), provider_recommendation.get("author"), provider_recommendation.get("reviewer")]
            if decision_verdict.get("selected_topology") == "team_with_adversarial_review"
            else [provider_recommendation.get("author")],
            "work_unit_count": len(session.structured_brief.subtasks),
        },
        provider_recommendation=provider_recommendation,
        gating={
            "contract_source": "approved_plan_session",
            "review_required": True,
        },
    ).to_dict()


def _recommend_topology(policy: Any, requirement: str, subtasks: list[PlanSubtask]) -> dict[str, object]:
    lowered = requirement.lower()
    if not policy.agent_enabled:
        recommended: TopologyName = "solo"
        reason = "policy disables agent topology, so execution should stay solo."
    elif "tiny" in lowered or len(subtasks) <= 1:
        recommended = "team"
        reason = "small scope can use the standard team topology without adversarial depth."
    else:
        recommended = "team_with_adversarial_review"
        reason = "multi-step work benefits from team execution with adversarial review."
    return {
        "recommended_topology": recommended,
        "available_topologies": ["solo", "team", "team_with_adversarial_review"],
        "selection_reason": reason,
        "subtask_count": len(subtasks),
        "agent_enabled": policy.agent_enabled,
    }


def _recommend_provider_runtime(
    runtime: JobRuntime,
    *,
    reviewer_provider: str = "claude",
    fallback_from: str | None = None,
    fallback_reason: str | None = None,
    fallback_detail: str | None = None,
) -> dict[str, object]:
    recommendation = {
        "author": "codex",
        "reviewer": reviewer_provider,
        "runtime": "command" if runtime.__class__.__name__ == "CommandJobRuntime" else "mock",
    }
    if fallback_from is not None and fallback_from != reviewer_provider:
        recommendation["fallback_from"] = fallback_from
        recommendation["preferred_reviewer"] = fallback_from
    if fallback_reason is not None:
        recommendation["fallback_reason"] = fallback_reason
    if fallback_detail is not None:
        recommendation["fallback_detail"] = fallback_detail
    return recommendation


def _summarize_review_disputes(review_rounds: list[PlanReviewRound]) -> list[str]:
    disputes: list[str] = []
    for round_ in review_rounds:
        if round_.round_type != "adversarial_review" or round_.review_result is None:
            continue
        for finding in round_.review_result.findings:
            disputes.append(f"{finding.severity}: {finding.title}")
    return disputes


def _build_decision_rationale(requirement: str, session: PlanSession, policy: Any) -> list[str]:
    rationale = [
        "Decision core keeps the approved plan as the execution entrypoint.",
        f"Selected mode preference is {policy.mode.value}.",
    ]
    topology = session.structured_brief.topology_recommendation.get("recommended_topology")
    if topology:
        rationale.append(f"Recommended topology is {topology}.")
    if session.gaps:
        rationale.append(f"Plan currently tracks {len(session.gaps)} review gap(s).")
    if "followup" in requirement.lower():
        rationale.append("Follow-up findings are tracked without blocking execution.")
    reviewer_provider = session.structured_brief.provider_recommendation.get("reviewer")
    if reviewer_provider == "mock" and session.structured_brief.provider_recommendation.get("runtime") == "command":
        rationale.append("claude unavailable; reviewer fallback downgraded to mock.")
    return rationale


def _normalize_approval_status(session: PlanSession) -> ApprovalStatus:
    if session.status == "approved_for_execution":
        return "approved"
    if session.status in {"accepted", "needs_followup", "blocked"}:
        return session.status
    if session.gate_verdict in {"approved", "accepted", "needs_followup", "blocked"}:
        return "approved" if session.gate_verdict == "approved" else session.gate_verdict
    return "needs_revision"


def _build_decision_verdict(
    session: PlanSession,
    *,
    runtime: JobRuntime,
    approval_status: ApprovalStatus | None = None,
) -> DecisionVerdict:
    return DecisionVerdict(
        approval_status=approval_status or _normalize_approval_status(session),
        required_gaps=[gap.to_dict() for gap in session.gaps if gap.required and gap.status != "closed"],
        followup_gaps=[gap.to_dict() for gap in session.gaps if not gap.required and gap.status != "closed"],
        selected_topology=session.structured_brief.topology_recommendation.get("recommended_topology", "team"),
        selected_provider_runtime=session.structured_brief.provider_recommendation or _recommend_provider_runtime(runtime),
        rationale=list(
            session.structured_brief.decision_rationale
            or _build_decision_rationale(session.requirement, session, get_policy(OrchestrationMode.SUCCESS_FIRST))
        ),
    )


def build_operator_runbook(session: PlanSession) -> list[str]:
    status_summary = _build_status_summary(session)
    guidance = build_session_guidance(session)
    required_open = int(status_summary.get("open_required_gaps", 0))
    optional_open = int(status_summary.get("open_optional_followups", 0))
    delegated_jobs = status_summary.get("delegated_jobs", [])
    failed_jobs = [job for job in delegated_jobs if job.get("status") == "failed"]
    compliance_blocking_reasons = _compliance_blocking_reasons(session)

    if guidance.block_source == "compliance":
        detail = compliance_blocking_reasons[0]
        return [
            f"Inspect the compliance blocker: {detail}.",
            f"Run `{guidance.recommended_commands[0]}` after restoring the required workflow docs.",
            "Re-run `team summary` or `team runbook` to confirm the canonical guidance is unblocked.",
        ]

    if guidance.block_source == "delegated_job" and failed_jobs:
        failed_job = failed_jobs[0]
        is_claude = str(failed_job.get("provider")) == "claude"
        if is_claude and guidance.block_detail == "failed_adversarial_review_job":
            return [
                "Inspect the failed delegated Claude adversarial review job.",
                f"Retry the delegated adversarial review with `{guidance.recommended_commands[0]}` if the failure was transient.",
                "Switch to `team revise` if the failure uncovered a real planning gap.",
            ]
        if is_claude:
            return [
                "Inspect the failed delegated Claude review job.",
                f"Retry the delegated review with `{guidance.recommended_commands[0]}` if the failure was transient.",
                "Switch to `team revise` if the failure uncovered a real planning gap.",
            ]
        return [
            "Inspect the failed delegated job with `status <job_id>` before taking any other action.",
            "Use `team revise` if the failure means the plan itself needs changes.",
            "Re-run `team summary` after recovery so the next allowed action is explicit again.",
        ]

    if session.status == "needs_revision":
        steps = [
            f"Close every required gap with `{guidance.recommended_commands[0]}`.",
            "Re-run `team summary` or `team next` to confirm approval is now allowed.",
            "Use `team approve` only after required gaps are closed.",
        ]
        if optional_open:
            steps.append("Track optional follow-up items separately; they do not block approval unless you decide to promote them.")
        return steps

    if session.status == "approved_for_execution":
        return [
            f"Run `{guidance.recommended_commands[0]}` to start execution from the approved plan.",
            "Use `team status` or `team summary` if you need to confirm the session is still in the approved phase.",
            "Inspect the linked execution run after execution starts if you need deeper provenance or result details.",
        ]

    if session.status == "executing":
        return [
            "Wait for execution to finish before taking another planning action.",
            "Use `team status` to confirm the session is still executing.",
            "Inspect the linked execution run if you need more detail than the session summary provides.",
        ]

    if session.status in {"accepted", "needs_followup"}:
        steps = [
            f"Inspect the linked execution run with `{guidance.recommended_commands[0]}` to confirm provenance, outputs, and final acceptance state.",
            "Use `team summary` to review the final planning status alongside the execution result.",
            "Avoid restarting planning from the raw requirement unless a new requirement is opened.",
        ]
        if session.status == "needs_followup" or optional_open:
            steps[1] = "Use `team summary` to review the remaining follow-up items alongside the execution result."
        return steps

    if session.status == "awaiting_human":
        return [
            "Pause autonomous progress and gather the blocking strategic question for the human.",
            "Use `team summary` to review why human confirmation is required.",
            "Resume the workflow only after the human decision is reflected in the plan direction.",
        ]

    if session.status == "blocked":
        if guidance.block_source == "execution_run":
            if guidance.block_detail == "provenance_mismatch":
                return [
                    "Inspect the linked execution provenance before trusting the blocked session state.",
                    f"Use `{guidance.recommended_commands[0]}` and `team inspect-execution` together to resolve the run/session mismatch.",
                    "Do not resume planning or execution until the provenance mismatch is corrected.",
                ]
            return [
                "Inspect the linked execution run to identify why execution ended in a blocked state.",
                f"Use `{guidance.recommended_commands[0]}` and `team summary` together before deciding whether the plan or execution path should change.",
                "Resume planning only after the execution-side blocker is understood and reflected in the session direction.",
            ]
        step = "Close required review blockers before trying to approve or execute again."
        if required_open:
            step = f"Close the {required_open} required gap(s) before trying to approve or execute again."
        return [
            "Inspect the blocking review findings and identify whether the issue is product, policy, or execution related.",
            step,
            "Re-run `team summary` after each fix so the next valid action is explicit.",
        ]

    return [
        "Use `team status` to inspect the current session state.",
        "Use `team next` to retrieve the next recommended command.",
        "Avoid editing stored JSON directly; continue only through the standard `team` commands.",
    ]


def _build_status_summary(session: PlanSession) -> dict[str, object]:
    required_open = [gap for gap in session.gaps if gap.required and gap.status != "closed"]
    optional_open = [gap for gap in session.gaps if not gap.required and gap.status != "closed"]
    blocking_reasons: list[str] = []
    compliance_blocking_reasons = _compliance_blocking_reasons(session)
    delegated_jobs, delegated_job_failed, delegated_job_provider = _collect_delegated_jobs(session)
    guidance = build_session_guidance(session)
    next_actions = [guidance.primary_action]
    if guidance.resume_action not in next_actions:
        next_actions.append(guidance.resume_action)

    if compliance_blocking_reasons:
        blocking_reasons.extend(compliance_blocking_reasons)
    elif delegated_job_failed:
        blocking_reasons.append("at least one delegated job failed")
    elif session.status == "needs_revision" and required_open:
        blocking_reasons.append(f"{len(required_open)} required gaps remain open")

    preferred_recovery_round_type = None
    recovery_provider_mode = "observed"
    if guidance.resume_action == "retry_review":
        preferred_recovery_round_type = "review"
        recovery_provider_mode = "planned"
    elif guidance.resume_action == "retry_adversarial_review":
        preferred_recovery_round_type = "adversarial_review"
        recovery_provider_mode = "planned"
    recovery_policy = _recovery_policy_for_session(
        session,
        preferred_round_type=preferred_recovery_round_type,
        provider_mode=recovery_provider_mode,
    )

    return {
        "phase": session.resume.current_phase,
        "pending_role": session.resume.pending_role,
        "open_required_gaps": len(required_open),
        "open_optional_followups": len(optional_open),
        "next_actions": next_actions,
        "next_action_message": guidance.primary_reason,
        "primary_action": guidance.primary_action,
        "primary_reason": guidance.primary_reason,
        "recommended_commands": guidance.recommended_commands,
        "recovery_actions": guidance.recovery_actions,
        "recovery_round_type": recovery_policy.get("round_type"),
        "recovery_provider": recovery_policy.get("provider"),
        "recovery_provider_fallback_from": recovery_policy.get("fallback_from"),
        "recovery_provider_fallback_reason": recovery_policy.get("fallback_reason"),
        "recovery_provider_fallback_detail": recovery_policy.get("fallback_detail"),
        "blocking_reasons": blocking_reasons,
        "block_source": guidance.block_source,
        "block_detail": guidance.block_detail,
        "resume_action": guidance.resume_action,
        "resume_reason": guidance.resume_reason,
        "delegated_jobs": delegated_jobs,
        "selected_topology": session.decision_verdict.selected_topology if session.decision_verdict else None,
        "topology_reason": session.structured_brief.topology_recommendation.get("selection_reason"),
        "decision_rationale": session.decision_verdict.rationale if session.decision_verdict else [],
        "approved_plan_ready": bool(session.approved_plan),
        "approved_plan_source": session.approved_plan.get("execution_contract", {}).get("source") if session.approved_plan else None,
    }


def _read_delegated_job_status(session: PlanSession, job_id: str):
    jobs_root = session.doc_sync.get("jobs_root") if session.doc_sync else None
    if not jobs_root:
        return None
    try:
        runtime = FileJobRuntime(root=jobs_root)
        return runtime.status(job_id)
    except Exception:
        return None


def _extract_job_id(summary: str) -> str | None:
    if " job " not in summary:
        return None
    return summary.split("job ")[-1].rstrip(".")


def _latest_round(rounds: list[PlanReviewRound], round_family: str) -> PlanReviewRound | None:
    latest = None
    for round_ in rounds:
        if _delegated_round_family(round_.round_type) == round_family:
            latest = round_
    return latest


def _delegated_round_family(round_type: str) -> str | None:
    if round_type in {"review", "review_retry"}:
        return "review"
    if round_type in {"adversarial_review", "adversarial_review_retry"}:
        return "adversarial_review"
    return None


def _checklist_item_completed(checklist: list[PlanChecklistItem], label: str) -> bool:
    return any(item.label == label and item.completed for item in checklist)


def _validate_compliance_ready(session: PlanSession) -> None:
    if isinstance(session.compliance, dict) and session.compliance.get("blocking"):
        reasons = [str(item) for item in session.compliance.get("blocking_reasons", [])]
        detail = "; ".join(reasons) if reasons else "compliance checks failed"
        raise ValueError(f"team action blocked by compliance: {detail}")
