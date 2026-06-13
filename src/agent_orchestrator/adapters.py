"""Adapter interfaces and deterministic MVP implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
from time import sleep
from typing import Any, Protocol, cast
from urllib import error, request as urlrequest

from agent_orchestrator.agent_config import AgentConfig, AgentProfile
from agent_orchestrator.jobs import AgentJob, InMemoryJobRuntime, JobRequest, JobRuntime
from agent_orchestrator.policies import OrchestrationMode, PolicyProfile
from agent_orchestrator.review import Finding, ReviewResult
from agent_orchestrator.tasks import RiskLevel, TaskContract, WorkUnit, WorkUnitResult


@dataclass(slots=True)
class ExtractedSignals:
    raw_requirement: str
    explicit_paths: list[str] = field(default_factory=list)
    explicit_symbols: list[str] = field(default_factory=list)
    explicit_constraints: list[str] = field(default_factory=list)
    explicit_non_goals: list[str] = field(default_factory=list)
    artifact_hints: list[str] = field(default_factory=list)
    risk_hints: list[str] = field(default_factory=list)
    task_hints: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ClarifySourceFrame:
    raw_requirement: str = ""
    normalized_requirement: str = ""


@dataclass(slots=True)
class ClarifyIntentFrame:
    goal: str = ""
    intent_summary: str = ""
    task_type: str = "implementation"
    constraints: list[str] = field(default_factory=list)
    non_goals: list[str] = field(default_factory=list)
    target_scope: list[str] = field(default_factory=list)
    expected_artifacts: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ClarifyControlFrame:
    risk_signals: list[str] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    uncertain_slots: list[str] = field(default_factory=list)
    slot_sources: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ClarifyState:
    source: ClarifySourceFrame
    intent: ClarifyIntentFrame
    control: ClarifyControlFrame


@dataclass(slots=True)
class ContractDraft:
    raw_requirement: str = ""
    normalized_requirement: str = ""
    goal: str = ""
    intent_summary: str = ""
    task_type: str = "implementation"
    constraints: list[str] = field(default_factory=list)
    non_goals: list[str] = field(default_factory=list)
    target_scope: list[str] = field(default_factory=list)
    expected_artifacts: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    risk_signals: list[str] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    uncertain_slots: list[str] = field(default_factory=list)
    slot_sources: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class DecompositionCandidate:
    name: str
    strategy: str
    rationale: list[str]
    work_units: list[WorkUnit]
    score: int = 0
    selected: bool = False
    score_breakdown: dict[str, int] = field(default_factory=dict)
    rationale_items: list[str] = field(default_factory=list)
    explanation_blocks: list[dict[str, object]] = field(default_factory=list)
    graph_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "strategy": self.strategy,
            "rationale": list(self.rationale),
            "work_units": [work_unit.to_dict() for work_unit in self.work_units],
            "score": self.score,
            "selected": self.selected,
            "score_breakdown": dict(self.score_breakdown),
            "rationale_items": list(self.rationale_items),
            "explanation_blocks": [dict(block) for block in self.explanation_blocks],
            "graph_metadata": dict(self.graph_metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "DecompositionCandidate":
        return cls(
            name=str(data.get("name", "")),
            strategy=str(data.get("strategy", "")),
            rationale=[str(item) for item in data.get("rationale", [])],
            work_units=[
                WorkUnit.from_dict(item)
                for item in data.get("work_units", [])
                if isinstance(item, dict)
            ],
            score=int(data.get("score", 0)),
            selected=bool(data.get("selected", False)),
            score_breakdown={str(key): int(value) for key, value in dict(data.get("score_breakdown", {})).items()},
            rationale_items=[str(item) for item in data.get("rationale_items", [])],
            explanation_blocks=[dict(item) for item in data.get("explanation_blocks", []) if isinstance(item, dict)],
            graph_metadata=dict(data.get("graph_metadata", {})),
        )


@dataclass(slots=True)
class DecompositionExplanationBlock:
    dimension: str
    points: int
    reasons: list[str]


@dataclass(slots=True)
class DecompositionSignalFrame:
    task_family: str
    execution_shape: str
    verification_intensity: str
    coordination_cost: str
    scope_cardinality: int
    artifact_count: int
    risk_signal_count: int
    dependency_pressure: str
    rollback_required: bool


@dataclass(slots=True)
class DecompositionStructureProfile:
    task_family: str
    execution_shape: str
    parallelism: str
    topology_depth: int
    has_dependencies: bool
    scope_cardinality: int


@dataclass(slots=True)
class DecompositionSafetyProfile:
    risk_level: str
    verification_intensity: str
    rollback_required: bool
    risk_signal_count: int
    review_required: str


@dataclass(slots=True)
class DecompositionCoordinationProfile:
    coordination_cost: str
    dependency_pressure: str
    scope_cardinality: int
    artifact_count: int
    has_dependencies: bool


@dataclass(slots=True)
class DecompositionArtifactProfile:
    artifact_count: int
    primary_artifacts: list[str] = field(default_factory=list)
    implementation_outputs: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DecompositionProfile:
    structure: DecompositionStructureProfile
    safety: DecompositionSafetyProfile
    coordination: DecompositionCoordinationProfile
    artifact: DecompositionArtifactProfile


@dataclass(slots=True)
class SlotFillResult:
    filled_slots: dict[str, Any] = field(default_factory=dict)
    unknown_slots: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_model_payload: dict[str, Any] = field(default_factory=dict)


ALLOWED_SLOT_FILL_FIELDS = {
    "goal",
    "user_intent_summary",
    "task_type",
    "expected_artifacts",
    "acceptance_criteria",
    "assumptions",
    "risk_signals",
}
ALLOWED_UNKNOWN_SLOTS = ALLOWED_SLOT_FILL_FIELDS | {"target_scope"}
TASK_TYPE_ALIASES = {
    "analysis": "investigation",
    "analyze": "investigation",
    "investigate": "investigation",
    "bug_fix": "bugfix",
    "bug-fix": "bugfix",
    "documentation": "docs",
    "tests": "test_only",
}
VALID_TASK_TYPES = {"implementation", "bugfix", "feature", "refactor", "migration", "investigation", "docs", "test_only"}
ARTIFACT_ALIASES = {
    "investigation report": "analysis note",
    "analysis report": "analysis note",
    "report": "analysis note",
    "root cause summary": "findings",
    "root cause analysis": "findings",
    "findings summary": "findings",
    "recommendation": "recommendation",
    "recommendations": "recommendation",
    "test plan": "tests",
    "test coverage": "tests",
    "documentation patch": "docs patch",
    "doc patch": "docs patch",
    "rollback guidance": "rollback notes",
}


@dataclass(frozen=True, slots=True)
class EnvSlotFillConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int = 30

    @classmethod
    def from_env(cls, *, project_root: Path | None = None) -> "EnvSlotFillConfig" | None:
        file_values = _load_project_env_file(project_root)
        api_key = os.environ.get("AO_SLOTFILL_API_KEY", file_values.get("AO_SLOTFILL_API_KEY", "")).strip()
        base_url = os.environ.get("AO_SLOTFILL_BASE_URL", file_values.get("AO_SLOTFILL_BASE_URL", "")).strip()
        model = os.environ.get("AO_SLOTFILL_MODEL", file_values.get("AO_SLOTFILL_MODEL", "")).strip()
        timeout_raw = os.environ.get(
            "AO_SLOTFILL_TIMEOUT_SECONDS",
            file_values.get("AO_SLOTFILL_TIMEOUT_SECONDS", ""),
        ).strip()
        if not api_key or not base_url or not model:
            return None
        timeout_seconds = int(timeout_raw) if timeout_raw.isdigit() else 30
        return cls(api_key=api_key, base_url=base_url.rstrip("/"), model=model, timeout_seconds=timeout_seconds)


def _default_slot_filler() -> "SlotFillerAdapter | None":
    config = EnvSlotFillConfig.from_env()
    if config is None:
        return None
    return OpenAICompatibleSlotFiller(config=config)


class PlannerAdapter(Protocol):
    """Turns fuzzy requirements into a clarified task contract."""

    def clarify(self, requirement: str, policy: PolicyProfile) -> TaskContract:
        """Create a task contract from a user requirement."""


class SlotFillerAdapter(Protocol):
    """Fills missing or uncertain contract draft slots."""

    def __call__(self, draft: ContractDraft, policy: PolicyProfile) -> SlotFillResult:
        """Return structured slot-fill data for the given draft."""


class DecomposerAdapter(Protocol):
    """Splits a clarified task contract into executable work units."""

    def decompose(self, contract: TaskContract, policy: PolicyProfile) -> list[WorkUnit]:
        """Create executable work units."""


class WorkerAdapter(Protocol):
    """Executes a single work unit."""

    def execute(self, work_unit: WorkUnit, policy: PolicyProfile) -> WorkUnitResult:
        """Execute a work unit and return a result."""


class ReviewRescueAdapter(Protocol):
    """Reviews or rescues worker output."""

    def review_or_rescue(
        self,
        work_unit: WorkUnit,
        result: WorkUnitResult,
        policy: PolicyProfile,
    ) -> WorkUnitResult:
        """Review successful output or rescue failed output."""


@dataclass(slots=True)
class MockClaudePlanner:
    """MVP Claude-style planner that produces stable task contracts."""

    slot_filler: SlotFillerAdapter | None = field(default_factory=_default_slot_filler)

    def clarify(self, requirement: str, policy: PolicyProfile) -> TaskContract:
        normalized_requirement = _normalize_requirement(requirement)
        signals = _extract_signals(normalized_requirement)
        state = _build_clarify_state(signals, normalized_requirement=normalized_requirement)
        state = _assess_clarify_state(state, signals)
        draft = _clarify_state_to_draft(state)
        fill_result = SlotFillResult()
        if self.slot_filler and _needs_slot_fill(state):
            fill_result = self.slot_filler(draft, policy)
            draft = _merge_slot_fill_result(draft, fill_result)
            state = _clarify_state_from_draft(draft)
        topology = policy.execution_topology
        non_goals = list(state.intent.non_goals)
        if not topology.agent_enabled:
            context = "Run through the control plane without spawning agent topology."
            non_goals.append("Do not recurse into agent delegation when agent mode is disabled")
        else:
            context = (
                "Use the success-first parent architecture and downgrade behavior "
                f"through policy when requested. Provider flow: {' -> '.join(topology.provider_flow)}."
            )
            non_goals.append("Do not recurse beyond the selected policy depth")

        if state.intent.target_scope:
            context = f"{context} Scope hints: {', '.join(state.intent.target_scope)}."
        if state.intent.constraints:
            context = f"{context} Constraints: {'; '.join(state.intent.constraints)}."

        outputs = list(state.intent.expected_artifacts) if state.intent.expected_artifacts else ["task tree", "worker results", "review summary"]
        inputs = [state.intent.goal]
        if state.intent.constraints:
            inputs.extend(f"constraint: {item}" for item in state.intent.constraints)
        if state.intent.target_scope:
            inputs.extend(f"scope: {item}" for item in state.intent.target_scope)

        return TaskContract(
            goal=state.intent.goal,
            non_goals=_dedupe_preserve_order(non_goals),
            context=context,
            inputs=inputs,
            outputs=outputs,
            acceptance_criteria=list(state.intent.acceptance_criteria),
            risk_level=_collapse_risk_level(state.control.risk_signals),
            parallelizable=state.intent.task_type not in {"migration", "investigation"},
            owner_type="claude_team",
            max_depth=policy.max_depth,
            failure_policy="rescue" if policy.rescue_enabled else "retry",
            task_type=state.intent.task_type,
            constraints=list(state.intent.constraints),
            assumptions=list(state.intent.assumptions),
            target_scope=list(state.intent.target_scope),
            expected_artifacts=list(state.intent.expected_artifacts),
            risk_signals=list(state.control.risk_signals),
            user_intent_summary=state.intent.intent_summary,
            raw_requirement=state.source.normalized_requirement,
            slot_sources=dict(state.control.slot_sources),
            unknown_slots=_dedupe_preserve_order([*state.control.missing_slots, *state.control.uncertain_slots, *fill_result.unknown_slots]),
            slot_fill_warnings=list(fill_result.warnings),
        )


@dataclass(slots=True)
class MockClaudeDecomposer:
    """MVP decomposer that models Claude team-style division of labor."""

    last_candidates: list[DecompositionCandidate] = field(default_factory=list, init=False, repr=False)

    def decompose(self, contract: TaskContract, policy: PolicyProfile) -> list[WorkUnit]:
        candidates = _build_decomposition_candidates(contract, policy)
        selected = _select_decomposition_candidate(candidates, contract, policy)
        self.last_candidates = selected
        chosen = next(candidate for candidate in selected if candidate.selected)
        return chosen.work_units


@dataclass(slots=True)
class MockCodexWorker:
    """MVP Codex-style worker that simulates deterministic implementation."""

    runtime: JobRuntime = field(default_factory=InMemoryJobRuntime)

    def execute(self, work_unit: WorkUnit, policy: PolicyProfile) -> WorkUnitResult:
        provider = _work_unit_provider(work_unit, default="codex")
        job = self.runtime.start(
            JobRequest(
                task_id=work_unit.id,
                provider=provider,
                kind="implementation",
                prompt=work_unit.goal,
                cwd=str(Path.cwd()),
                max_depth=policy.max_depth,
                metadata={
                    "context": work_unit.context,
                    "inputs": work_unit.inputs,
                    "outputs": work_unit.outputs,
                    "acceptance_criteria": work_unit.acceptance_criteria,
                },
            )
        )

        lowered = f"{work_unit.goal} {work_unit.context} {' '.join(work_unit.inputs)}".lower()
        if "fail" in lowered:
            failed_job = _runtime_fail(
                self.runtime,
                job.id,
                summary=f"Worker hit a simulated execution failure in {job.id}.",
                error="Simulated execution failure.",
                stdout=f"Simulated failure for prompt: {work_unit.goal}",
                parsed_payload={"request": {"work_unit_id": work_unit.id}},
            )
            return WorkUnitResult(
                work_unit_id=work_unit.id,
                status="failed",
                summary=failed_job.summary or f"Worker hit a simulated execution failure in {job.id}.",
                patch=None,
                tests=["not run"],
                needs_rescue=True,
                job_id=failed_job.id,
                job_ids=[failed_job.id],
                job_status=failed_job.status,
                job_phase=failed_job.phase,
                job_lifecycle=[_job_ref(failed_job)],
            )

        completed_job = _runtime_complete(
            self.runtime,
            job.id,
            summary=f"Completed via {job.id}: {work_unit.goal}",
            stdout=f"Completed prompt: {work_unit.goal}",
            parsed_payload={"request": {"work_unit_id": work_unit.id}},
        )
        return WorkUnitResult(
            work_unit_id=work_unit.id,
            status="succeeded",
            summary=completed_job.summary or f"Completed via {job.id}: {work_unit.goal}",
            patch=f"mock-patch-for-{work_unit.id}",
            tests=["mock validation passed"],
            needs_rescue=False,
            job_id=completed_job.id,
            job_ids=[completed_job.id],
            job_status=completed_job.status,
            job_phase=completed_job.phase,
            job_lifecycle=[_job_ref(completed_job)],
        )


@dataclass(slots=True)
class MockClaudeReviewRescue:
    """MVP Claude-style review/rescue team."""

    runtime: JobRuntime = field(default_factory=InMemoryJobRuntime)

    def review_or_rescue(
        self,
        work_unit: WorkUnit,
        result: WorkUnitResult,
        policy: PolicyProfile,
    ) -> WorkUnitResult:
        review_provider = _review_provider(policy)
        if result.status == "failed" and policy.rescue_enabled:
            job = self.runtime.start(
                JobRequest(
                    task_id=work_unit.id,
                    provider=review_provider,
                    kind="rescue",
                    prompt=f"Rescue failed work unit: {work_unit.goal}",
                    cwd=str(Path.cwd()),
                    max_depth=policy.max_depth,
                    failure_reason=result.summary,
                )
            )
            rescued_job = _runtime_complete(
                self.runtime,
                job.id,
                summary=f"Rescued via {job.id}: {work_unit.goal}",
                stdout=f"Rescue completed for: {work_unit.goal}",
                parsed_payload={"request": {"work_unit_id": work_unit.id, "origin_status": result.status}},
            )
            return WorkUnitResult(
                work_unit_id=work_unit.id,
                status="rescued",
                summary=rescued_job.summary or f"Rescued via {job.id}: {work_unit.goal}",
                patch=result.patch or f"rescued-patch-for-{work_unit.id}",
                tests=["rescue validation passed"],
                needs_rescue=False,
                job_id=rescued_job.id,
                job_ids=_merge_job_ids(result, rescued_job),
                job_status=rescued_job.status,
                job_phase=rescued_job.phase,
                job_lifecycle=[*result.job_lifecycle, _job_ref(rescued_job)],
                recovery_origin_status=result.status,
            )

        if _should_review(work_unit, policy):
            job = self.runtime.start(
                JobRequest(
                    task_id=work_unit.id,
                    provider=review_provider,
                    kind="review",
                    prompt=f"Review work unit result: {work_unit.goal}",
                    cwd=str(Path.cwd()),
                    max_depth=policy.max_depth,
                )
            )
            review_result = _build_review_result(work_unit, result, policy)
            reviewed_job = _runtime_complete(
                self.runtime,
                job.id,
                summary=f"Reviewed by Claude team via {job.id}: {result.summary}",
                stdout=f"Review completed for: {work_unit.goal}",
                parsed_payload={
                    "request": {"work_unit_id": work_unit.id},
                    "review_result": review_result.to_dict(),
                },
                phase="reviewing",
            )
            return WorkUnitResult(
                work_unit_id=work_unit.id,
                status=result.status,
                summary=reviewed_job.summary or f"Reviewed by Claude team via {job.id}: {result.summary}",
                patch=result.patch,
                tests=[*result.tests, "review passed"],
                needs_rescue=False,
                job_id=reviewed_job.id,
                job_ids=_merge_job_ids(result, reviewed_job),
                job_status=reviewed_job.status,
                job_phase=reviewed_job.phase,
                job_lifecycle=[*result.job_lifecycle, _job_ref(reviewed_job)],
                review_result=review_result,
            )

        return result


def _infer_risk(goal: str) -> RiskLevel:
    return _collapse_risk_level(_infer_risk_signals_from_rules(goal))


def _normalize_requirement(requirement: str) -> str:
    normalized = " ".join(requirement.strip().split())
    if not normalized:
        return "Clarify and implement the requested change"
    return normalized


def _extract_signals(requirement: str) -> ExtractedSignals:
    return ExtractedSignals(
        raw_requirement=requirement,
        explicit_paths=_extract_explicit_paths(requirement),
        explicit_symbols=_extract_explicit_symbols(requirement),
        explicit_constraints=_extract_explicit_constraints(requirement),
        explicit_non_goals=_extract_explicit_non_goals(requirement),
        artifact_hints=_extract_artifact_hints(requirement),
        risk_hints=_infer_risk_signals_from_rules(requirement),
        task_hints=_infer_task_hints(requirement),
    )


def _build_clarify_state(
    signals: ExtractedSignals,
    *,
    normalized_requirement: str,
) -> ClarifyState:
    task_type = _infer_task_type_from_rules(signals)
    raw_requirement = signals.raw_requirement
    goal = normalized_requirement
    target_scope = _dedupe_preserve_order([*signals.explicit_paths, *signals.explicit_symbols])
    constraints = _dedupe_preserve_order(signals.explicit_constraints)
    non_goals = _dedupe_preserve_order(signals.explicit_non_goals)
    expected_artifacts = _infer_expected_artifacts_from_rules(task_type, signals.artifact_hints)
    risk_signals = _dedupe_preserve_order(signals.risk_hints)
    assumptions: list[str] = []
    if not target_scope:
        assumptions.append("Target scope must be inferred from repository context if execution requires file selection.")
    source = ClarifySourceFrame(raw_requirement=raw_requirement, normalized_requirement=normalized_requirement)
    intent = ClarifyIntentFrame(
        goal=goal,
        intent_summary=_build_intent_summary(normalized_requirement, task_type),
        task_type=task_type,
        constraints=constraints,
        non_goals=non_goals,
        target_scope=target_scope,
        expected_artifacts=expected_artifacts,
        acceptance_criteria=_build_acceptance_criteria(task_type),
        assumptions=assumptions,
    )
    control = ClarifyControlFrame(
        risk_signals=risk_signals,
        slot_sources={
            "goal": "rule",
            "intent_summary": "rule",
            "task_type": "rule",
            "constraints": "rule" if constraints else "default",
            "non_goals": "rule" if non_goals else "default",
            "target_scope": "rule" if target_scope else "default",
            "expected_artifacts": "rule",
            "acceptance_criteria": "rule",
            "assumptions": "rule" if assumptions else "default",
            "risk_signals": "rule" if risk_signals else "default",
        },
    )
    return ClarifyState(source=source, intent=intent, control=control)


def _assess_clarify_state(state: ClarifyState, signals: ExtractedSignals) -> ClarifyState:
    state.control.missing_slots = []
    state.control.uncertain_slots = []
    if not state.intent.goal:
        state.control.missing_slots.append("goal")
    if state.intent.task_type == "implementation":
        state.control.uncertain_slots.append("task_type")
    if not state.intent.target_scope:
        state.control.uncertain_slots.append("target_scope")
    if not state.intent.expected_artifacts:
        state.control.missing_slots.append("expected_artifacts")
    if not state.intent.acceptance_criteria:
        state.control.missing_slots.append("acceptance_criteria")
    if _looks_ambiguous(signals.raw_requirement):
        state.control.uncertain_slots.append("user_intent_summary")
    state.control.missing_slots = _dedupe_preserve_order(state.control.missing_slots)
    state.control.uncertain_slots = _dedupe_preserve_order(state.control.uncertain_slots)
    return state


def _needs_slot_fill(state: ClarifyState) -> bool:
    return bool(state.control.missing_slots or state.control.uncertain_slots)


def _clarify_state_to_draft(state: ClarifyState) -> ContractDraft:
    draft = ContractDraft(
        raw_requirement=state.source.raw_requirement,
        normalized_requirement=state.source.normalized_requirement,
        goal=state.intent.goal,
        intent_summary=state.intent.intent_summary,
        task_type=state.intent.task_type,
        constraints=list(state.intent.constraints),
        non_goals=list(state.intent.non_goals),
        target_scope=list(state.intent.target_scope),
        expected_artifacts=list(state.intent.expected_artifacts),
        acceptance_criteria=list(state.intent.acceptance_criteria),
        assumptions=list(state.intent.assumptions),
        risk_signals=list(state.control.risk_signals),
    )
    draft.missing_slots = list(state.control.missing_slots)
    draft.uncertain_slots = list(state.control.uncertain_slots)
    draft.slot_sources = dict(state.control.slot_sources)
    return draft


def _clarify_state_from_draft(draft: ContractDraft) -> ClarifyState:
    return ClarifyState(
        source=ClarifySourceFrame(raw_requirement=draft.raw_requirement, normalized_requirement=draft.normalized_requirement),
        intent=ClarifyIntentFrame(
            goal=draft.goal,
            intent_summary=draft.intent_summary,
            task_type=draft.task_type,
            constraints=list(draft.constraints),
            non_goals=list(draft.non_goals),
            target_scope=list(draft.target_scope),
            expected_artifacts=list(draft.expected_artifacts),
            acceptance_criteria=list(draft.acceptance_criteria),
            assumptions=list(draft.assumptions),
        ),
        control=ClarifyControlFrame(
            risk_signals=list(draft.risk_signals),
            missing_slots=list(draft.missing_slots),
            uncertain_slots=list(draft.uncertain_slots),
            slot_sources=dict(draft.slot_sources),
        ),
    )


def _merge_slot_fill_result(draft: ContractDraft, fill_result: SlotFillResult) -> ContractDraft:
    locked_slots = {"constraints", "non_goals", "target_scope"}
    for field_name, value in fill_result.filled_slots.items():
        if field_name in locked_slots or field_name not in ALLOWED_SLOT_FILL_FIELDS:
            continue
        if field_name == "goal" and isinstance(value, str) and value.strip():
            draft.goal = value.strip()
            draft.slot_sources[field_name] = "llm"
            continue
        if field_name == "user_intent_summary" and isinstance(value, str) and value.strip():
            draft.intent_summary = value.strip()
            draft.slot_sources[field_name] = "llm"
            continue
        if field_name == "task_type" and isinstance(value, str):
            normalized_task_type = _normalize_task_type(value)
            if normalized_task_type is None:
                continue
            draft.task_type = normalized_task_type
            draft.slot_sources[field_name] = "llm"
            continue
        if field_name in {"expected_artifacts", "acceptance_criteria", "assumptions", "risk_signals"} and isinstance(value, list):
            cleaned = _dedupe_preserve_order([str(item) for item in value])
            if cleaned:
                setattr(draft, field_name, cleaned)
                draft.slot_sources[field_name] = "llm"
    draft.missing_slots = [slot for slot in draft.missing_slots if slot not in fill_result.filled_slots]
    draft.uncertain_slots = [slot for slot in draft.uncertain_slots if slot not in fill_result.filled_slots]
    return draft


TransportFn = Any


@dataclass(slots=True)
class OpenAICompatibleSlotFiller:
    config: EnvSlotFillConfig
    transport: TransportFn | None = None

    def __call__(self, draft: ContractDraft, policy: PolicyProfile) -> SlotFillResult:
        payload = self._build_payload(draft, policy)
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        request_url = f"{self.config.base_url}/chat/completions"
        try:
            response = self._transport()(request_url, payload, headers, self.config.timeout_seconds)
        except Exception as exc:
            return SlotFillResult(warnings=[f"slot_fill_request_failed: {exc}"])
        parsed = self._parse_response(response)
        if parsed is None:
            return SlotFillResult(warnings=["slot_fill_response_invalid"], raw_model_payload=response if isinstance(response, dict) else {})
        return parsed

    def _build_payload(self, draft: ContractDraft, policy: PolicyProfile) -> dict[str, object]:
        prompt = {
            "raw_requirement": draft.raw_requirement,
            "normalized_requirement": draft.normalized_requirement,
            "locked_slots": {
                "constraints": draft.constraints,
                "non_goals": draft.non_goals,
                "target_scope": draft.target_scope,
            },
            "candidate_slots": {
                "goal": draft.goal,
                "user_intent_summary": draft.intent_summary,
                "task_type": draft.task_type,
                "expected_artifacts": draft.expected_artifacts,
                "acceptance_criteria": draft.acceptance_criteria,
                "assumptions": draft.assumptions,
                "risk_signals": draft.risk_signals,
            },
            "missing_slots": draft.missing_slots,
            "uncertain_slots": draft.uncertain_slots,
            "policy": {
                "mode": policy.mode.value,
                "max_depth": policy.max_depth,
                "parallelism": policy.parallelism,
            },
            "allowed_output_slots": sorted(ALLOWED_SLOT_FILL_FIELDS),
            "allowed_unknown_slots": sorted(ALLOWED_UNKNOWN_SLOTS),
            "task_type_enum": sorted(VALID_TASK_TYPES - {"implementation"}) + ["implementation"],
        }
        system_message = (
            "You fill missing or uncertain task-contract slots. Return a single JSON object only. "
            "Preserve locked_slots exactly. Never return constraints, non_goals, target_scope, policy, raw_requirement, "
            "missing_slots, uncertain_slots, or slot_sources. Only return allowed_output_slots plus unknown_slots. "
            "task_type must be one of task_type_enum. Do not invent file paths, modules, or constraints. "
            "If a requested slot is uncertain, omit it and list it in unknown_slots."
        )
        user_message = json.dumps(prompt, ensure_ascii=False, indent=2)
        return {
            "model": self.config.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0,
        }

    def _transport(self) -> TransportFn:
        return self.transport or _default_openai_compatible_transport

    def _parse_response(self, payload: dict[str, object]) -> SlotFillResult | None:
        content = _extract_openai_message_content(payload)
        if not content:
            return None
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return SlotFillResult(warnings=["slot_fill_response_not_json"], raw_model_payload=payload)
        if not isinstance(data, dict):
            return None
        filled_slots: dict[str, Any] = {}
        for key, value in data.items():
            if key == "unknown_slots" or key not in ALLOWED_SLOT_FILL_FIELDS:
                continue
            if key == "task_type":
                normalized_task_type = _normalize_task_type(value)
                if normalized_task_type is not None:
                    filled_slots[key] = normalized_task_type
                continue
            if key == "goal" and isinstance(value, str) and value.strip():
                filled_slots[key] = value.strip()
                continue
            if key == "user_intent_summary" and isinstance(value, str) and value.strip():
                filled_slots[key] = value.strip()
                continue
            if key in {"expected_artifacts", "acceptance_criteria", "assumptions", "risk_signals"} and isinstance(value, list):
                cleaned_values = [str(item) for item in value if str(item).strip()]
                if key == "expected_artifacts":
                    cleaned = _normalize_expected_artifacts(cleaned_values)
                else:
                    cleaned = _dedupe_preserve_order(cleaned_values)
                if cleaned:
                    filled_slots[key] = cleaned
        unknown_slots = []
        if isinstance(data.get("unknown_slots"), list):
            unknown_slots = [str(item) for item in data["unknown_slots"] if str(item) in ALLOWED_UNKNOWN_SLOTS]
        return SlotFillResult(
            filled_slots=filled_slots,
            unknown_slots=unknown_slots,
            warnings=[],
            raw_model_payload=payload,
        )


def _build_legacy_decomposition_candidate(contract: TaskContract, policy: PolicyProfile) -> DecompositionCandidate:
    profile = _build_decomposition_profile(contract, policy)
    signals = _decomposition_signal_view(profile)
    context = _build_decomposition_context(contract)
    structured_inputs = _build_decomposition_inputs(contract)
    implementation_outputs = list(contract.expected_artifacts) if contract.expected_artifacts else ["patch", "validation notes"]
    flow = policy.provider_flow
    if not policy.agent_enabled or policy.topology_depth == 0:
        work_units = [
            WorkUnit(
                goal=_build_direct_execution_goal(contract),
                context=context,
                inputs=structured_inputs,
                outputs=implementation_outputs,
                acceptance_criteria=_build_direct_execution_acceptance(contract),
                risk_level=contract.risk_level,
                parallelizable=False,
                owner_type="single_worker",
                max_depth=contract.max_depth,
                failure_policy=contract.failure_policy,
                provider_hint="codex",
                depends_on=[],
            )
        ]
        return DecompositionCandidate(
            name="direct_execution",
            strategy="legacy_direct_execution",
            rationale=[
                "Agent topology is disabled, so the control plane emits a single direct-execution unit.",
                f"Signal profile: {signals.execution_shape} / {signals.coordination_cost} / {signals.verification_intensity}.",
            ],
            work_units=work_units,
            score=1,
            selected=True,
            score_breakdown={"shape": 1},
            rationale_items=["shape: direct execution when agent topology is disabled (+1)"],
            graph_metadata={
                "task_type": contract.task_type,
                "topology_depth": 0,
                "shape": "single_node",
                "profiles": _decomposition_profile_metadata(profile),
                "legacy_signals": _decomposition_signal_metadata(signals),
            },
        )

    base_units, shape = _build_task_type_template_units(
        contract,
        policy,
        context=context,
        structured_inputs=structured_inputs,
        implementation_outputs=implementation_outputs,
    )

    selected_units = list(base_units)
    if policy.topology_depth <= 1 or policy.parallelism == "limited":
        selected_units = base_units[:1]
        shape = f"{shape}_trimmed_contract_only"
    elif policy.topology_depth == 2:
        selected_units = base_units[:2]
        shape = f"{shape}_trimmed_execute"
    elif policy.parallelism == "aggressive":
        compatibility = WorkUnit(
            goal="Run speculative compatibility check",
            context=context,
            inputs=["worker results"],
            outputs=["compatibility notes"],
            acceptance_criteria=["Compatibility risks are listed"],
            risk_level="low",
            parallelizable=True,
            owner_type="codex_swarm",
            max_depth=contract.max_depth,
            failure_policy="retry",
            provider_hint=_flow_provider(flow, 1, fallback="codex"),
            depends_on=[base_units[1].id],
        )
        selected_units = base_units + [compatibility]
        shape = f"{shape}_plus_compatibility"

    score_card = _score_decomposition_shape(selected_units, contract, policy, profile)
    return DecompositionCandidate(
        name="legacy_team_pipeline",
        strategy=shape,
        rationale=[
            "The current control-plane decomposition expands a fixed contract -> execute -> review pipeline.",
            "Topology depth and parallelism trim or extend the fixed pipeline shape.",
            f"Signal profile: {signals.execution_shape} / {signals.coordination_cost} / {signals.verification_intensity}.",
        ],
        work_units=selected_units,
        score=score_card.total,
        selected=True,
        score_breakdown=score_card.breakdown,
        rationale_items=score_card.rationale_items,
        explanation_blocks=[
            {
                "dimension": block.dimension,
                "points": block.points,
                "reasons": list(block.reasons),
            }
            for block in score_card.explanation_blocks
        ],
        graph_metadata={
            "task_type": contract.task_type,
            "topology_depth": policy.topology_depth,
            "parallelism": policy.parallelism,
            "shape": shape,
            "profiles": _decomposition_profile_metadata(profile),
            "legacy_signals": _decomposition_signal_metadata(signals),
            "score_breakdown": score_card.breakdown,
            "score_rationale": score_card.rationale_items,
        },
    )


def _build_decomposition_candidates(contract: TaskContract, policy: PolicyProfile) -> list[DecompositionCandidate]:
    primary = _build_legacy_decomposition_candidate(contract, policy)
    if not policy.agent_enabled or policy.topology_depth == 0:
        return [primary]
    trimmed_units = primary.work_units[:-1] if len(primary.work_units) > 2 else list(primary.work_units)
    trimmed = DecompositionCandidate(
        name=f"{primary.name}_trimmed",
        strategy="risk_trimmed_pipeline",
        rationale=[
            "A leaner candidate trims later-stage validation to reduce coordination cost.",
            "This candidate is useful for lower-risk or speed-leaning scenarios.",
        ],
        work_units=trimmed_units,
        score=0,
        selected=False,
        score_breakdown={},
        rationale_items=[
            "coordination: trimmed candidate removes later-stage validation to reduce cost (-4)"
        ],
        explanation_blocks=[
            {
                "dimension": "coordination",
                "points": -4,
                "reasons": ["trimmed candidate removes later-stage validation to reduce cost"],
            }
        ],
        graph_metadata={**primary.graph_metadata, "shape": f"{primary.graph_metadata.get('shape', 'pipeline')}_trimmed"},
    )
    return [primary, trimmed]


def _select_decomposition_candidate(
    candidates: list[DecompositionCandidate],
    contract: TaskContract,
    policy: PolicyProfile,
) -> list[DecompositionCandidate]:
    scored = []
    best_score: int | None = None
    best_index = 0
    for index, candidate in enumerate(candidates):
        score_card = _score_decomposition_candidate(candidate, contract, policy)
        candidate.score = score_card.total
        candidate.score_breakdown = score_card.breakdown
        candidate.rationale_items = score_card.rationale_items
        candidate.graph_metadata["score_breakdown"] = score_card.breakdown
        candidate.graph_metadata["score_rationale"] = score_card.rationale_items
        candidate.selected = False
        scored.append(candidate)
        if best_score is None or score_card.total > best_score:
            best_score = score_card.total
            best_index = index
    scored[best_index].selected = True
    return scored


@dataclass(slots=True)
class DecompositionScoreCard:
    total: int
    breakdown: dict[str, int]
    rationale_items: list[str]
    explanation_blocks: list[DecompositionExplanationBlock] = field(default_factory=list)


def _new_score_state() -> tuple[dict[str, int], dict[str, list[str]], list[str]]:
    return {}, {"structure": [], "safety": [], "coordination": [], "artifact": []}, []


def _record_score(
    breakdown: dict[str, int],
    reasons: dict[str, list[str]],
    dimension: str,
    points: int,
    reason: str | None = None,
) -> None:
    dimension = _canonical_score_dimension(dimension)
    if points == 0:
        return
    breakdown[dimension] = breakdown.get(dimension, 0) + points
    if reason:
        reasons.setdefault(dimension, []).append(reason)


def _build_score_card(
    breakdown: dict[str, int],
    reasons: dict[str, list[str]],
) -> DecompositionScoreCard:
    explanation_blocks = build_decomposition_explanation_blocks(breakdown, reasons)
    rationale_items = _explanation_blocks_to_rationale(explanation_blocks)
    return DecompositionScoreCard(
        total=sum(breakdown.values()),
        breakdown=breakdown,
        rationale_items=rationale_items,
        explanation_blocks=explanation_blocks,
    )


def _canonicalize_score_card(score_card: DecompositionScoreCard) -> DecompositionScoreCard:
    breakdown: dict[str, int] = {}
    reasons: dict[str, list[str]] = {"structure": [], "safety": [], "coordination": [], "artifact": []}
    for dimension, points in score_card.breakdown.items():
        canonical_dimension = _canonical_score_dimension(dimension)
        breakdown[canonical_dimension] = breakdown.get(canonical_dimension, 0) + points
    for item in score_card.rationale_items:
        if ":" in item:
            prefix, detail = item.split(":", 1)
            canonical_dimension = _canonical_score_dimension(prefix.strip())
            reasons.setdefault(canonical_dimension, []).append(detail.strip())
        else:
            reasons.setdefault("coordination", []).append(item)
    explanation_blocks = [
        DecompositionExplanationBlock(
            dimension=dimension,
            points=points,
            reasons=list(reasons.get(dimension, [])),
        )
        for dimension, points in breakdown.items()
        if points != 0
    ]
    rationale_items = [
        f"{block.dimension}: {', '.join(block.reasons) if block.reasons else 'no explanation available'} ({block.points:+d})"
        for block in explanation_blocks
    ]
    if not rationale_items:
        rationale_items.append("No scoring signals were triggered; defaulting to neutral score.")
    return DecompositionScoreCard(
        total=score_card.total,
        breakdown=breakdown,
        rationale_items=rationale_items,
        explanation_blocks=explanation_blocks,
    )


def _canonical_score_dimension(dimension: str) -> str:
    if dimension in {"structure", "shape", "dependency"}:
        return "structure"
    if dimension in {"safety", "review", "task_type"}:
        return "safety"
    if dimension == "artifact":
        return "artifact"
    return "coordination"


def build_decomposition_explanation_blocks(
    breakdown: dict[str, int],
    reasons: dict[str, list[str]],
) -> list[DecompositionExplanationBlock]:
    blocks = [
        DecompositionExplanationBlock(
            dimension=dimension,
            points=points,
            reasons=list(reasons.get(dimension, [])),
        )
        for dimension, points in breakdown.items()
        if points != 0
    ]
    if blocks:
        return blocks
    return [DecompositionExplanationBlock(dimension="coordination", points=0, reasons=["No scoring signals were triggered; defaulting to neutral score."])]


def _explanation_blocks_to_rationale(blocks: list[DecompositionExplanationBlock]) -> list[str]:
    rationale_items = [
        f"{block.dimension}: {', '.join(block.reasons) if block.reasons else 'no explanation available'} ({block.points:+d})"
        for block in blocks
        if block.points != 0
    ]
    if rationale_items:
        return rationale_items
    return ["No scoring signals were triggered; defaulting to neutral score."]


def _score_decomposition_candidate(
    candidate: DecompositionCandidate,
    contract: TaskContract,
    policy: PolicyProfile,
) -> DecompositionScoreCard:
    profiles = candidate.graph_metadata.get("profiles")
    profile_payload = profiles if isinstance(profiles, dict) else {}
    breakdown: dict[str, int] = {}
    rationale_items: list[str] = []

    def add(bucket: str, points: int, reason: str | None = None) -> None:
        if points == 0:
            return
        breakdown[bucket] = breakdown.get(bucket, 0) + points
        if reason:
            rationale_items.append(f"{bucket}: {reason} ({points:+d})")

    score = 0
    work_unit_count = len(candidate.work_units)
    add("shape", work_unit_count * 5, f"{work_unit_count} work units")
    if any("review summary" in unit.outputs for unit in candidate.work_units):
        add("safety", 8, "includes review summary output")
    if any(unit.depends_on for unit in candidate.work_units):
        add("structure", 4, "has dependent work units")
    if contract.risk_level == "high":
        add("safety", work_unit_count * 3, f"high risk contract across {work_unit_count} units")
        if any("rollback" in " ".join(unit.outputs).lower() for unit in candidate.work_units):
            add("safety", 10, "rollback coverage present")
    elif contract.risk_level == "low":
        penalty = -max(0, work_unit_count - 2) * 2
        add("safety", penalty, "low risk favors leaner unit counts")
    if contract.task_type == "migration" and any("rollback" in " ".join(unit.outputs).lower() for unit in candidate.work_units):
        add("safety", 12, "migration candidate covers rollback")
    if contract.task_type == "investigation" and any("findings" in unit.outputs for unit in candidate.work_units):
        add("artifact", 6, "investigation candidate produces findings")
    if policy.parallelism == "aggressive" and work_unit_count > 2:
        add("structure", 2, "aggressive parallelism favors broader pipelines")
    if candidate.strategy == "risk_trimmed_pipeline":
        add("shape", -4, "trimmed pipeline is cheaper but less complete")
    safety_payload = profile_payload.get("safety")
    if isinstance(safety_payload, dict):
        verification_intensity = str(safety_payload.get("verification_intensity", "medium"))
        rollback_required = bool(safety_payload.get("rollback_required", False))
        review_required = str(safety_payload.get("review_required", "risk_based"))
        if verification_intensity == "high":
            add("safety", 5, "high verification intensity")
        elif verification_intensity == "medium":
            add("safety", 2, "medium verification intensity")
        if rollback_required:
            add("safety", 3, "rollback required")
        if review_required == "always":
            add("safety", 2, "review always required")
    coordination_payload = profile_payload.get("coordination")
    if isinstance(coordination_payload, dict):
        coordination_cost = str(coordination_payload.get("coordination_cost", "medium"))
        dependency_pressure = str(coordination_payload.get("dependency_pressure", "medium"))
        if coordination_cost == "high":
            add("coordination", 4, "high coordination cost")
        elif coordination_cost == "low":
            add("coordination", -1, "low coordination cost")
        if dependency_pressure == "high":
            add("coordination", 2, "high dependency pressure")
    structure_payload = profile_payload.get("structure")
    if isinstance(structure_payload, dict):
        topology_depth = int(structure_payload.get("topology_depth", policy.topology_depth))
        if topology_depth >= 3:
            add("structure", 1, "deeper topology")
        elif topology_depth == 0:
            add("structure", -1, "flat topology")
        if bool(structure_payload.get("has_dependencies", False)):
            add("structure", 1, "dependencies present")
    artifact_payload = profile_payload.get("artifact")
    if isinstance(artifact_payload, dict):
        artifact_count = int(artifact_payload.get("artifact_count", 0))
        if artifact_count >= 3:
            add("artifact", 1, "multiple expected artifacts")
    score = sum(breakdown.values())
    if not rationale_items:
        rationale_items.append("No scoring signals were triggered; defaulting to neutral score.")
    return _canonicalize_score_card(DecompositionScoreCard(total=score, breakdown=breakdown, rationale_items=rationale_items))


def _score_decomposition_shape(
    work_units: list[WorkUnit],
    contract: TaskContract,
    policy: PolicyProfile,
    profile: DecompositionProfile,
) -> DecompositionScoreCard:
    breakdown: dict[str, int] = {}
    rationale_items: list[str] = []

    def add(bucket: str, points: int, reason: str | None = None) -> None:
        if points == 0:
            return
        breakdown[bucket] = breakdown.get(bucket, 0) + points
        if reason:
            rationale_items.append(f"{bucket}: {reason} ({points:+d})")

    add("shape", len(work_units) * 5, f"{len(work_units)} work units")
    safety = profile.safety
    coordination = profile.coordination
    structure = profile.structure
    if safety.verification_intensity == "high":
        add("safety", 6, "high verification intensity")
    elif safety.verification_intensity == "medium":
        add("safety", 3, "medium verification intensity")
    if coordination.coordination_cost == "high":
        add("coordination", 4, "high coordination cost")
    elif coordination.coordination_cost == "low":
        add("coordination", -1, "low coordination cost")
    if safety.rollback_required:
        add("safety", 5, "rollback required")
    if coordination.dependency_pressure == "high":
        add("coordination", 3, "high dependency pressure")
    if structure.task_family == "analysis":
        add("structure", 1, "analysis task family")
    if contract.task_type == "migration":
        add("safety", 4, "migration task family")
    if policy.parallelism == "aggressive" and len(work_units) > 2:
        add("structure", 2, "aggressive parallelism with multi-step pipeline")
    score = sum(breakdown.values())
    if not rationale_items:
        rationale_items.append("No scoring signals were triggered; defaulting to neutral score.")
    return _canonicalize_score_card(DecompositionScoreCard(total=score, breakdown=breakdown, rationale_items=rationale_items))


def _build_task_type_template_units(
    contract: TaskContract,
    policy: PolicyProfile,
    *,
    context: str,
    structured_inputs: list[str],
    implementation_outputs: list[str],
) -> tuple[list[WorkUnit], str]:
    if contract.task_type == "investigation":
        return _build_investigation_template_units(contract, policy, context=context, structured_inputs=structured_inputs), "investigation_pipeline"
    if contract.task_type == "migration":
        return _build_migration_template_units(contract, policy, context=context, structured_inputs=structured_inputs, implementation_outputs=implementation_outputs), "migration_pipeline"
    if contract.task_type == "docs":
        return _build_docs_template_units(contract, policy, context=context, structured_inputs=structured_inputs, implementation_outputs=implementation_outputs), "docs_pipeline"
    return _build_general_template_units(contract, policy, context=context, structured_inputs=structured_inputs, implementation_outputs=implementation_outputs), "general_pipeline"


def _build_general_template_units(
    contract: TaskContract,
    policy: PolicyProfile,
    *,
    context: str,
    structured_inputs: list[str],
    implementation_outputs: list[str],
) -> list[WorkUnit]:
    flow = policy.provider_flow
    base_units = [
        WorkUnit(
            goal="Define task contract and acceptance criteria",
            context=context,
            inputs=structured_inputs,
            outputs=["contract"],
            acceptance_criteria=["Contract has goal, constraints, and acceptance criteria"],
            risk_level="medium",
            parallelizable=True,
            owner_type="codex_swarm",
            max_depth=contract.max_depth,
            failure_policy=contract.failure_policy,
            provider_hint=_flow_provider(flow, 0, fallback="claude"),
            depends_on=[],
        ),
        WorkUnit(
            goal="Implement the constrained change set",
            context=context,
            inputs=["task contract", *structured_inputs],
            outputs=implementation_outputs,
            acceptance_criteria=_build_team_execution_acceptance(contract),
            risk_level=contract.risk_level,
            parallelizable=True,
            owner_type="codex_swarm",
            max_depth=contract.max_depth,
            failure_policy=contract.failure_policy,
            provider_hint=_flow_provider(flow, 1, fallback="codex"),
            depends_on=[],
        ),
        WorkUnit(
            goal="Validate merge readiness",
            context=context,
            inputs=["worker results", *[f"risk_signal: {item}" for item in contract.risk_signals]],
            outputs=["review summary"],
            acceptance_criteria=["Review determines whether output is acceptable"],
            risk_level="high" if policy.review_required is True else "medium",
            parallelizable=False,
            owner_type="claude_team",
            max_depth=contract.max_depth,
            failure_policy="rescue",
            provider_hint=_flow_provider(flow, 2, fallback="claude"),
            depends_on=[],
        ),
    ]
    base_units[1].depends_on = [base_units[0].id]
    base_units[2].depends_on = [base_units[1].id]
    return base_units


def _build_investigation_template_units(
    contract: TaskContract,
    policy: PolicyProfile,
    *,
    context: str,
    structured_inputs: list[str],
) -> list[WorkUnit]:
    flow = policy.provider_flow
    base_units = [
        WorkUnit(
            goal="Trace the issue scope and collect evidence",
            context=context,
            inputs=structured_inputs,
            outputs=["evidence notes", "scope notes"],
            acceptance_criteria=["Collected evidence is relevant to the reported issue"],
            risk_level=contract.risk_level,
            parallelizable=True,
            owner_type="codex_swarm",
            max_depth=contract.max_depth,
            failure_policy=contract.failure_policy,
            provider_hint=_flow_provider(flow, 0, fallback="claude"),
            depends_on=[],
        ),
        WorkUnit(
            goal="Synthesize investigation findings and recommendation",
            context=context,
            inputs=["evidence notes", *structured_inputs],
            outputs=["analysis note", "findings", "recommendation"],
            acceptance_criteria=_build_team_execution_acceptance(contract),
            risk_level=contract.risk_level,
            parallelizable=False,
            owner_type="codex_swarm",
            max_depth=contract.max_depth,
            failure_policy=contract.failure_policy,
            provider_hint=_flow_provider(flow, 1, fallback="codex"),
            depends_on=[],
        ),
        WorkUnit(
            goal="Validate investigation completeness",
            context=context,
            inputs=["findings", "recommendation"],
            outputs=["review summary"],
            acceptance_criteria=["Review confirms the findings are actionable and bounded by evidence"],
            risk_level="medium",
            parallelizable=False,
            owner_type="claude_team",
            max_depth=contract.max_depth,
            failure_policy="rescue",
            provider_hint=_flow_provider(flow, 2, fallback="claude"),
            depends_on=[],
        ),
    ]
    base_units[1].depends_on = [base_units[0].id]
    base_units[2].depends_on = [base_units[1].id]
    return base_units


def _build_migration_template_units(
    contract: TaskContract,
    policy: PolicyProfile,
    *,
    context: str,
    structured_inputs: list[str],
    implementation_outputs: list[str],
) -> list[WorkUnit]:
    flow = policy.provider_flow
    base_units = [
        WorkUnit(
            goal="Plan the migration scope and safety checks",
            context=context,
            inputs=structured_inputs,
            outputs=["migration plan", "validation checklist"],
            acceptance_criteria=["Migration plan identifies scope, safety checks, and validation guardrails"],
            risk_level="high",
            parallelizable=False,
            owner_type="codex_swarm",
            max_depth=contract.max_depth,
            failure_policy=contract.failure_policy,
            provider_hint=_flow_provider(flow, 0, fallback="claude"),
            depends_on=[],
        ),
        WorkUnit(
            goal="Implement the migration change set",
            context=context,
            inputs=["migration plan", *structured_inputs],
            outputs=implementation_outputs,
            acceptance_criteria=_build_team_execution_acceptance(contract),
            risk_level=contract.risk_level,
            parallelizable=False,
            owner_type="codex_swarm",
            max_depth=contract.max_depth,
            failure_policy=contract.failure_policy,
            provider_hint=_flow_provider(flow, 1, fallback="codex"),
            depends_on=[],
        ),
        WorkUnit(
            goal="Validate rollback and compatibility safeguards",
            context=context,
            inputs=["migration plan", "worker results"],
            outputs=["rollback notes", "compatibility notes"],
            acceptance_criteria=["Rollback path and compatibility risks are explicitly documented"],
            risk_level="high",
            parallelizable=False,
            owner_type="claude_team",
            max_depth=contract.max_depth,
            failure_policy="rescue",
            provider_hint=_flow_provider(flow, 2, fallback="claude"),
            depends_on=[],
        ),
        WorkUnit(
            goal="Validate merge readiness",
            context=context,
            inputs=["rollback notes", "compatibility notes"],
            outputs=["review summary"],
            acceptance_criteria=["Review determines whether migration output is acceptable"],
            risk_level="high",
            parallelizable=False,
            owner_type="claude_team",
            max_depth=contract.max_depth,
            failure_policy="rescue",
            provider_hint=_flow_provider(flow, 2, fallback="claude"),
            depends_on=[],
        ),
    ]
    base_units[1].depends_on = [base_units[0].id]
    base_units[2].depends_on = [base_units[1].id]
    base_units[3].depends_on = [base_units[2].id]
    return base_units


def _build_docs_template_units(
    contract: TaskContract,
    policy: PolicyProfile,
    *,
    context: str,
    structured_inputs: list[str],
    implementation_outputs: list[str],
) -> list[WorkUnit]:
    flow = policy.provider_flow
    base_units = [
        WorkUnit(
            goal="Inspect the current behavior and source references",
            context=context,
            inputs=structured_inputs,
            outputs=["source notes"],
            acceptance_criteria=["Source notes identify the behavior the documentation must describe"],
            risk_level=contract.risk_level,
            parallelizable=True,
            owner_type="codex_swarm",
            max_depth=contract.max_depth,
            failure_policy=contract.failure_policy,
            provider_hint=_flow_provider(flow, 0, fallback="claude"),
            depends_on=[],
        ),
        WorkUnit(
            goal="Draft the requested documentation update",
            context=context,
            inputs=["source notes", *structured_inputs],
            outputs=implementation_outputs,
            acceptance_criteria=_build_team_execution_acceptance(contract),
            risk_level=contract.risk_level,
            parallelizable=True,
            owner_type="codex_swarm",
            max_depth=contract.max_depth,
            failure_policy=contract.failure_policy,
            provider_hint=_flow_provider(flow, 1, fallback="codex"),
            depends_on=[],
        ),
        WorkUnit(
            goal="Validate documentation consistency",
            context=context,
            inputs=["docs patch", "validation notes"],
            outputs=["review summary"],
            acceptance_criteria=["Review confirms the documentation matches the referenced behavior"],
            risk_level="medium",
            parallelizable=False,
            owner_type="claude_team",
            max_depth=contract.max_depth,
            failure_policy="rescue",
            provider_hint=_flow_provider(flow, 2, fallback="claude"),
            depends_on=[],
        ),
    ]
    base_units[1].depends_on = [base_units[0].id]
    base_units[2].depends_on = [base_units[1].id]
    return base_units


def _build_decomposition_profile(contract: TaskContract, policy: PolicyProfile) -> DecompositionProfile:
    scope_cardinality = len(contract.target_scope) + len(contract.constraints)
    artifact_count = len(contract.expected_artifacts)
    risk_signal_count = len(contract.risk_signals)
    has_dependencies = bool(contract.dependencies)
    rollback_required = contract.task_type == "migration" or any("rollback" in artifact.lower() for artifact in contract.expected_artifacts)
    task_family = contract.task_type if contract.task_type != "implementation" else ("analysis" if contract.risk_level == "high" else "general")
    execution_shape = _infer_decomposition_shape(contract.task_type, rollback_required, policy.parallelism)
    verification_intensity = "low"
    if contract.risk_level == "high" or policy.review_required is True or risk_signal_count >= 2:
        verification_intensity = "high"
    elif contract.risk_level == "medium" or artifact_count >= 3 or policy.review_required == "risk_based":
        verification_intensity = "medium"
    coordination_cost = "low"
    if scope_cardinality >= 3 or has_dependencies or contract.task_type in {"migration", "investigation"}:
        coordination_cost = "high"
    elif scope_cardinality >= 1 or artifact_count >= 2:
        coordination_cost = "medium"
    dependency_pressure = "high" if has_dependencies or scope_cardinality >= 3 else "medium" if scope_cardinality >= 1 else "low"
    review_required = "always" if policy.review_required is True else "risk_based" if policy.review_required == "risk_based" else "default"
    return DecompositionProfile(
        structure=DecompositionStructureProfile(
            task_family=task_family,
            execution_shape=execution_shape,
            parallelism=policy.parallelism,
            topology_depth=policy.topology_depth,
            has_dependencies=has_dependencies,
            scope_cardinality=scope_cardinality,
        ),
        safety=DecompositionSafetyProfile(
            risk_level=contract.risk_level,
            verification_intensity=verification_intensity,
            rollback_required=rollback_required,
            risk_signal_count=risk_signal_count,
            review_required=review_required,
        ),
        coordination=DecompositionCoordinationProfile(
            coordination_cost=coordination_cost,
            dependency_pressure=dependency_pressure,
            scope_cardinality=scope_cardinality,
            artifact_count=artifact_count,
            has_dependencies=has_dependencies,
        ),
        artifact=DecompositionArtifactProfile(
            artifact_count=artifact_count,
            primary_artifacts=list(contract.expected_artifacts),
            implementation_outputs=list(contract.expected_artifacts) if contract.expected_artifacts else ["patch", "validation notes"],
        ),
    )


def _decomposition_signal_view(profile: DecompositionProfile) -> DecompositionSignalFrame:
    return DecompositionSignalFrame(
        task_family=profile.structure.task_family,
        execution_shape=profile.structure.execution_shape,
        verification_intensity=profile.safety.verification_intensity,
        coordination_cost=profile.coordination.coordination_cost,
        scope_cardinality=profile.coordination.scope_cardinality,
        artifact_count=profile.artifact.artifact_count,
        risk_signal_count=profile.safety.risk_signal_count,
        dependency_pressure=profile.coordination.dependency_pressure,
        rollback_required=profile.safety.rollback_required,
    )


def _decomposition_signal_metadata(signals: DecompositionSignalFrame) -> dict[str, object]:
    return {
        "task_family": signals.task_family,
        "execution_shape": signals.execution_shape,
        "verification_intensity": signals.verification_intensity,
        "coordination_cost": signals.coordination_cost,
        "scope_cardinality": signals.scope_cardinality,
        "artifact_count": signals.artifact_count,
        "risk_signal_count": signals.risk_signal_count,
        "dependency_pressure": signals.dependency_pressure,
        "rollback_required": signals.rollback_required,
    }


def _decomposition_profile_metadata(profile: DecompositionProfile) -> dict[str, object]:
    return {
        "structure": {
            "task_family": profile.structure.task_family,
            "execution_shape": profile.structure.execution_shape,
            "parallelism": profile.structure.parallelism,
            "topology_depth": profile.structure.topology_depth,
            "has_dependencies": profile.structure.has_dependencies,
            "scope_cardinality": profile.structure.scope_cardinality,
        },
        "safety": {
            "risk_level": profile.safety.risk_level,
            "verification_intensity": profile.safety.verification_intensity,
            "rollback_required": profile.safety.rollback_required,
            "risk_signal_count": profile.safety.risk_signal_count,
            "review_required": profile.safety.review_required,
        },
        "coordination": {
            "coordination_cost": profile.coordination.coordination_cost,
            "dependency_pressure": profile.coordination.dependency_pressure,
            "scope_cardinality": profile.coordination.scope_cardinality,
            "artifact_count": profile.coordination.artifact_count,
            "has_dependencies": profile.coordination.has_dependencies,
        },
        "artifact": {
            "artifact_count": profile.artifact.artifact_count,
            "primary_artifacts": list(profile.artifact.primary_artifacts),
            "implementation_outputs": list(profile.artifact.implementation_outputs),
        },
    }


def _infer_decomposition_shape(task_type: str, rollback_required: bool, parallelism: str) -> str:
    if task_type == "investigation":
        return "investigation_pipeline"
    if task_type == "migration":
        return "migration_pipeline" if rollback_required else "migration_pipeline_light"
    if task_type == "docs":
        return "docs_pipeline"
    if parallelism == "aggressive":
        return "general_pipeline_parallel"
    return "general_pipeline"


def _extract_explicit_paths(requirement: str) -> list[str]:
    return _dedupe_preserve_order(re.findall(r"\b[\w./-]+\.(?:py|ts|tsx|js|jsx|json|md|yml|yaml)\b", requirement))


def _extract_explicit_symbols(requirement: str) -> list[str]:
    symbols = re.findall(r"\b[A-Za-z_][\w]*\.[A-Za-z_][\w]*\b", requirement)
    backticked = re.findall(r"`([^`]+)`", requirement)
    return _dedupe_preserve_order(symbols + [item for item in backticked if "." in item or "_" in item])


def _extract_explicit_constraints(requirement: str) -> list[str]:
    constraints: list[str] = []
    for sentence in _split_requirement(requirement):
        lowered = sentence.lower()
        if lowered.startswith("only ") or lowered.startswith("must ") or "without " in lowered:
            constraints.append(_normalize_sentence_case(sentence))
    return _dedupe_preserve_order(constraints)


def _extract_explicit_non_goals(requirement: str) -> list[str]:
    non_goals: list[str] = []
    for sentence in _split_requirement(requirement):
        lowered = sentence.lower()
        if lowered.startswith("do not ") or "don't " in lowered:
            non_goals.append(_normalize_sentence_case(sentence))
        for pattern in (r"(without changing [^.;]+)", r"(without breaking [^.;]+)"):
            match = re.search(pattern, sentence, flags=re.IGNORECASE)
            if match:
                non_goals.append(_normalize_sentence_case(match.group(1)))
    return _dedupe_preserve_order(non_goals)


def _extract_artifact_hints(requirement: str) -> list[str]:
    lowered = requirement.lower()
    hints: list[str] = []
    artifact_tokens = {
        r"\btest\b": "tests",
        r"\btests\b": "tests",
        r"\bdoc\b": "docs patch",
        r"\bdocs\b": "docs patch",
        r"\bplan\b": "migration plan",
        r"\bsummary\b": "analysis note",
        r"\banalysis\b": "analysis note",
    }
    for pattern, hint in artifact_tokens.items():
        if re.search(pattern, lowered):
            hints.append(hint)
    return _dedupe_preserve_order(hints)


def _infer_risk_signals_from_rules(requirement: str) -> list[str]:
    lowered = requirement.lower()
    signals: list[str] = []
    risk_map = {
        "migration": "Touches migration behavior",
        "security": "Touches security-sensitive behavior",
        "payment": "Touches payment behavior",
        "auth": "Touches authentication behavior",
        "login": "Touches authentication behavior",
        "parallel": "Introduces parallel execution behavior",
        "integration": "Touches integration boundaries",
        "refactor": "May shift existing implementation boundaries",
    }
    for token, signal in risk_map.items():
        if token in lowered:
            signals.append(signal)
    return _dedupe_preserve_order(signals)


def _infer_task_hints(requirement: str) -> list[str]:
    lowered = requirement.lower()
    hints: list[str] = []
    keyword_map = {
        "bugfix": ["fix", "bug", "issue"],
        "feature": ["build", "add", "implement", "create"],
        "refactor": ["refactor", "cleanup", "restructure"],
        "migration": ["migrate", "migration"],
        "investigation": ["investigate", "analyze", "diagnose", "root cause", "summarize"],
        "docs": ["document", "docs", "readme"],
        "test_only": ["test only", "tests only", "add tests"],
    }
    for hint, tokens in keyword_map.items():
        if any(token in lowered for token in tokens):
            hints.append(hint)
    return _dedupe_preserve_order(hints)


def _infer_task_type_from_rules(signals: ExtractedSignals) -> str:
    ordered = ["migration", "investigation", "refactor", "docs", "test_only", "bugfix", "feature"]
    for candidate in ordered:
        if candidate in signals.task_hints:
            return candidate
    return "implementation"


def _normalize_task_type(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    normalized = TASK_TYPE_ALIASES.get(normalized, normalized)
    if normalized in VALID_TASK_TYPES:
        return normalized
    return None


def _normalize_expected_artifacts(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        mapped = ARTIFACT_ALIASES.get(cleaned.lower(), cleaned.lower())
        normalized.append(mapped)
    return _dedupe_preserve_order(normalized)


def _infer_expected_artifacts_from_rules(task_type: str, artifact_hints: list[str]) -> list[str]:
    defaults = {
        "bugfix": ["patch", "tests", "validation notes"],
        "feature": ["patch", "tests", "validation notes"],
        "refactor": ["patch", "tests", "validation notes"],
        "migration": ["migration plan", "patch", "rollback notes"],
        "investigation": ["analysis note", "findings", "recommendation"],
        "docs": ["docs patch", "validation notes"],
        "test_only": ["tests", "validation notes"],
        "implementation": ["task tree", "worker results", "review summary"],
    }
    return _dedupe_preserve_order([*defaults.get(task_type, defaults["implementation"]), *artifact_hints])


def _build_acceptance_criteria(task_type: str) -> list[str]:
    if task_type == "investigation":
        return [
            "Findings describe the observed issue and likely root cause",
            "Recommendation explains the next action without speculative code changes",
            "Validation notes reference the evidence used for the conclusion",
        ]
    if task_type == "migration":
        return [
            "Migration work is represented as executable work units",
            "Plan includes validation or rollback guidance",
            "Failures are routed according to policy",
        ]
    return [
        "Requirement is represented as executable work units",
        "Worker results include tests or validation notes",
        "Failures are routed according to policy",
    ]


def _build_decomposition_context(contract: TaskContract) -> str:
    details: list[str] = [contract.context, contract.goal]
    if contract.task_type:
        details.append(f"Task type: {contract.task_type}.")
    if contract.target_scope:
        details.append(f"Target scope: {', '.join(contract.target_scope)}.")
    if contract.constraints:
        details.append(f"Constraints: {'; '.join(contract.constraints)}.")
    if contract.non_goals:
        details.append(f"Non-goals: {'; '.join(contract.non_goals)}.")
    return " ".join(detail for detail in details if detail)


def _build_decomposition_inputs(contract: TaskContract) -> list[str]:
    inputs = list(contract.inputs)
    inputs.extend(f"constraint: {item}" for item in contract.constraints)
    inputs.extend(f"scope: {item}" for item in contract.target_scope)
    inputs.extend(f"non_goal: {item}" for item in contract.non_goals)
    inputs.extend(f"artifact: {item}" for item in contract.expected_artifacts)
    return _dedupe_preserve_order(inputs)


def _build_direct_execution_goal(contract: TaskContract) -> str:
    if contract.task_type == "investigation":
        return "Investigate the requested issue directly and summarize findings"
    if contract.task_type == "migration":
        return "Execute the migration path directly with rollback awareness"
    return "Execute the requested change directly"


def _build_direct_execution_acceptance(contract: TaskContract) -> list[str]:
    if contract.acceptance_criteria:
        return list(contract.acceptance_criteria)
    return ["Direct execution completes without agent delegation"]


def _build_team_execution_goal(contract: TaskContract) -> str:
    if contract.task_type == "investigation":
        return "Investigate the issue and produce structured findings"
    if contract.task_type == "migration":
        return "Implement the migration path and capture rollback guidance"
    if contract.task_type == "docs":
        return "Update the requested documentation deliverables"
    return "Implement worker execution path"


def _build_team_execution_acceptance(contract: TaskContract) -> list[str]:
    if contract.acceptance_criteria:
        return list(contract.acceptance_criteria)
    return ["Worker returns a structured result"]


def _build_intent_summary(requirement: str, task_type: str) -> str:
    lowered = requirement.lower()
    if task_type == "investigation":
        return "Investigate the reported issue and summarize the most likely root cause."
    if task_type == "migration":
        return "Plan and implement the requested migration with explicit validation safeguards."
    if task_type == "refactor":
        return "Refine the targeted implementation into a cleaner, more structured change."
    if task_type == "docs":
        return "Update the requested documentation to reflect the intended behavior."
    if task_type == "test_only":
        return "Add or adjust tests to cover the requested behavior."
    if task_type == "bugfix":
        return "Fix the reported issue without regressing adjacent behavior."
    if task_type == "feature":
        return "Implement the requested feature change and validate the result."
    if lowered == "clarify and implement the requested change":
        return "Clarify and implement the requested change."
    return requirement


def _collapse_risk_level(risk_signals: list[str]) -> RiskLevel:
    joined = " ".join(risk_signals).lower()
    if any(token in joined for token in ["migration", "security", "payment", "authentication"]):
        return "high"
    if any(token in joined for token in ["parallel", "integration", "boundary", "refactor"]):
        return "medium"
    return "low"


def _looks_ambiguous(requirement: str) -> bool:
    lowered = requirement.lower()
    ambiguous_tokens = ["this", "that", "something", "look into", "maybe", "if needed", "as needed"]
    if len(lowered.split()) <= 8:
        return True
    return any(token in lowered for token in ambiguous_tokens)


def _default_openai_compatible_transport(
    request_url: str,
    payload: dict[str, object],
    headers: dict[str, str],
    timeout_seconds: int,
) -> dict[str, object]:
    body = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(request_url, data=body, headers=headers, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"http {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(str(exc.reason) or "request failed") from exc
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError("non-object response payload")
    return data


def _load_project_env_file(project_root: Path | None = None) -> dict[str, str]:
    root = project_root or Path.cwd()
    for candidate in (root / ".env.local", root / ".env"):
        values = _parse_simple_env_file(candidate)
        if values:
            return values
    return {}


def _parse_simple_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            values[key] = value
    return values


def _extract_openai_message_content(payload: dict[str, object]) -> str:
    choices = payload.get("choices", [])
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message", {})
    if not isinstance(message, dict):
        return ""
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                text_parts.append(str(item["text"]))
        return "\n".join(text_parts)
    return ""


def _split_requirement(requirement: str) -> list[str]:
    return [segment.strip(" ;,.") for segment in re.split(r";|\n|(?<=[a-z])\.\s+", requirement) if segment.strip(" ;,.")]


def _normalize_sentence_case(sentence: str) -> str:
    normalized = sentence.strip(" ;,.")
    if not normalized:
        return normalized
    return normalized[0].upper() + normalized[1:]


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _should_review(work_unit: WorkUnit, policy: PolicyProfile) -> bool:
    if policy.review_required is True:
        return True
    if policy.review_required == "risk_based":
        return work_unit.risk_level in {"medium", "high"}
    return False


def _build_review_result(work_unit: WorkUnit, result: WorkUnitResult, policy: PolicyProfile) -> ReviewResult:
    lowered = f"{work_unit.goal} {work_unit.context} {result.summary}".lower()
    if policy.mode != OrchestrationMode.SUCCESS_FIRST and any(token in lowered for token in ["security", "auth", "payment", "migration"]):
        return ReviewResult(
            verdict="needs_attention",
            summary="High-risk findings require escalation.",
            findings=[
                Finding(
                    severity="high",
                    title="Escalate to stronger mode",
                    body="This work unit touches a high-risk area and should be rerun in a stronger mode.",
                    file="orchestrator",
                    line_start=1,
                    line_end=1,
                    confidence=0.9,
                    recommendation="Upgrade to success_first and rerun the task.",
                )
            ],
            next_steps=["Upgrade orchestration mode and rerun the task."],
        )

    return ReviewResult(verdict="approve", summary="Review passed.", next_steps=["Continue as planned."])


@dataclass(slots=True)
class RuntimeProviderAdapter:
    """Executes work units through a concrete provider-backed JobRuntime."""

    runtime: JobRuntime
    kind: str
    default_provider: str = "codex"
    poll_interval_seconds: float = 0.01
    poll_attempts: int = 200
    provider_health_check: Any | None = None
    agent_config: AgentConfig = field(default_factory=AgentConfig.defaults)

    def execute(self, work_unit: WorkUnit, policy: PolicyProfile) -> WorkUnitResult:
        profile = self.agent_config.profile("worker")
        provider_selection = _provider_selection(
            work_unit,
            default=profile.provider or self.default_provider,
            runtime=self.runtime,
            provider_health_check=self.provider_health_check,
            fallback_source="runtime_provider_adapter",
        )
        provider = provider_selection["actual_provider"]
        prompt = _profile_prompt(profile, work_unit.goal, work_unit=work_unit)
        job = self.runtime.start(
            JobRequest(
                task_id=work_unit.id,
                provider=provider,  # type: ignore[arg-type]
                kind=self.kind,  # type: ignore[arg-type]
                prompt=prompt,
                cwd=str(Path.cwd()),
                model=profile.model,
                reasoning_effort=profile.reasoning_effort,  # type: ignore[arg-type]
                sandbox=profile.sandbox,  # type: ignore[arg-type]
                runtime_mode=profile.runtime_mode,
                max_depth=policy.max_depth,
                metadata={
                    "context": work_unit.context,
                    "inputs": work_unit.inputs,
                    "outputs": work_unit.outputs,
                    "acceptance_criteria": work_unit.acceptance_criteria,
                    "provider_runtime": provider_selection,
                },
            )
        )

        completed_job = self.runtime.status(job.id)
        for _ in range(self.poll_attempts):
            if completed_job.status in {"completed", "failed", "cancelled"}:
                break
            sleep(self.poll_interval_seconds)
            completed_job = self.runtime.status(job.id)

        if completed_job.status == "running":
            completed_job = _runtime_fail(
                self.runtime,
                job.id,
                summary="Provider job timed out while still running.",
                error=(
                    "Provider job exceeded the polling window without reaching a terminal status."
                ),
                parsed_payload={
                    "request": {"work_unit_id": work_unit.id},
                    "timeout": {
                        "poll_attempts": self.poll_attempts,
                        "poll_interval_seconds": self.poll_interval_seconds,
                    },
                },
            )

        if completed_job.status == "failed":
            return WorkUnitResult(
                work_unit_id=work_unit.id,
                status="failed",
                summary=completed_job.error or completed_job.summary or "Provider job failed.",
                patch=None,
                tests=["provider command failed"],
                needs_rescue=True,
                job_id=completed_job.id,
                job_ids=[completed_job.id],
                job_status=completed_job.status,
                job_phase=completed_job.phase,
                job_lifecycle=[_job_ref(completed_job)],
            )
        if completed_job.status == "cancelled":
            return WorkUnitResult(
                work_unit_id=work_unit.id,
                status="failed",
                summary=completed_job.summary or "Provider job was cancelled.",
                patch=None,
                tests=["provider command cancelled"],
                needs_rescue=True,
                job_id=completed_job.id,
                job_ids=[completed_job.id],
                job_status=completed_job.status,
                job_phase=completed_job.phase,
                job_lifecycle=[_job_ref(completed_job)],
            )

        return WorkUnitResult(
            work_unit_id=work_unit.id,
            status="succeeded",
            summary=completed_job.summary or "Provider job completed.",
            patch=None,
            tests=["provider command completed"],
            needs_rescue=False,
            job_id=completed_job.id,
            job_ids=[completed_job.id],
            job_status=completed_job.status,
            job_phase=completed_job.phase,
            job_lifecycle=[_job_ref(completed_job)],
        )


@dataclass(slots=True)
class RuntimeProviderReviewRescueAdapter:
    """Executes review/rescue work units through a command-backed runtime."""

    runtime: JobRuntime
    default_provider: str = "claude"
    poll_interval_seconds: float = 0.01
    poll_attempts: int = 200
    provider_health_check: Any | None = None
    agent_config: AgentConfig = field(default_factory=AgentConfig.defaults)

    def review_or_rescue(
        self,
        work_unit: WorkUnit,
        result: WorkUnitResult,
        policy: PolicyProfile,
    ) -> WorkUnitResult:
        kind = "rescue" if result.status == "failed" and policy.rescue_enabled else "review"
        profile = self.agent_config.profile("rescue" if kind == "rescue" else "execution_reviewer")
        provider_selection = _provider_selection(
            work_unit,
            default=profile.provider or self.default_provider,
            runtime=self.runtime,
            provider_health_check=self.provider_health_check,
            fallback_source="runtime_provider_review_rescue_adapter",
        )
        provider = provider_selection["actual_provider"]
        failure_reason = result.summary if kind == "rescue" else None
        prompt = _profile_prompt(
            profile,
            f"{kind.title()} work unit: {work_unit.goal}",
            work_unit=work_unit,
            origin_status=result.status,
        )
        job = self.runtime.start(
            JobRequest(
                task_id=work_unit.id,
                provider=provider,  # type: ignore[arg-type]
                kind=kind,  # type: ignore[arg-type]
                prompt=prompt,
                cwd=str(Path.cwd()),
                model=profile.model,
                reasoning_effort=profile.reasoning_effort,  # type: ignore[arg-type]
                sandbox=profile.sandbox,  # type: ignore[arg-type]
                runtime_mode=profile.runtime_mode,
                max_depth=policy.max_depth,
                failure_reason=failure_reason,
                metadata={
                    "context": work_unit.context,
                    "inputs": work_unit.inputs,
                    "outputs": work_unit.outputs,
                    "acceptance_criteria": work_unit.acceptance_criteria,
                    "origin_status": result.status,
                    "provider_runtime": provider_selection,
                },
            )
        )

        completed_job = self.runtime.status(job.id)
        for _ in range(self.poll_attempts):
            if completed_job.status in {"completed", "failed", "cancelled"}:
                break
            sleep(self.poll_interval_seconds)
            completed_job = self.runtime.status(job.id)

        if completed_job.status == "running":
            completed_job = _runtime_fail(
                self.runtime,
                job.id,
                summary=f"Provider {kind} job timed out while still running.",
                error=(
                    f"Provider {kind} job exceeded the polling window without reaching a terminal status."
                ),
                parsed_payload={
                    "request": {"work_unit_id": work_unit.id},
                    "timeout": {
                        "poll_attempts": self.poll_attempts,
                        "poll_interval_seconds": self.poll_interval_seconds,
                        "kind": kind,
                    },
                },
            )

        if completed_job.status in {"failed", "cancelled"}:
            return WorkUnitResult(
                work_unit_id=work_unit.id,
                status="failed",
                summary=completed_job.error or completed_job.summary or "Provider review job failed.",
                patch=result.patch,
                tests=[*result.tests, f"{kind} failed"],
                needs_rescue=True,
                job_id=completed_job.id,
                job_ids=[completed_job.id, *result.job_ids],
                job_status=completed_job.status,
                job_phase=completed_job.phase,
                job_lifecycle=[*result.job_lifecycle, _job_ref(completed_job)],
                recovery_origin_status=result.status if result.status != "failed" else result.recovery_origin_status,
            )

        parsed_review = _parse_provider_review_payload(completed_job.parsed_payload)
        if kind == "review" and parsed_review is None:
            parsed_review = ReviewResult(
                verdict="approve",
                summary=completed_job.summary or f"Reviewed by provider {provider}.",
                next_steps=["Continue as planned."],
            )
        if kind == "rescue" and policy.rescue_enabled:
            return WorkUnitResult(
                work_unit_id=work_unit.id,
                status="rescued",
                summary=completed_job.summary or f"Rescued via {job.id}: {work_unit.goal}",
                patch=result.patch or f"rescued-patch-for-{work_unit.id}",
                tests=[*result.tests, "rescue validation passed"],
                needs_rescue=False,
                job_id=completed_job.id,
                job_ids=[completed_job.id, *result.job_ids],
                job_status=completed_job.status,
                job_phase=completed_job.phase,
                job_lifecycle=[*result.job_lifecycle, _job_ref(completed_job)],
                recovery_origin_status=result.status,
            )

        return WorkUnitResult(
            work_unit_id=work_unit.id,
            status=result.status,
            summary=completed_job.summary or f"Reviewed by provider {provider}: {result.summary}",
            patch=result.patch,
            tests=[*result.tests, "review passed"],
            needs_rescue=False,
            job_id=completed_job.id,
            job_ids=[completed_job.id, *result.job_ids],
            job_status=completed_job.status,
            job_phase=completed_job.phase,
            job_lifecycle=[*result.job_lifecycle, _job_ref(completed_job)],
            review_result=parsed_review,
            recovery_origin_status=result.recovery_origin_status,
        )


def _runtime_complete(
    runtime: JobRuntime,
    job_id: str,
    *,
    summary: str,
    stdout: str | None = None,
    parsed_payload: dict[str, Any] | None = None,
    phase: str = "done",
) -> AgentJob:
    complete = getattr(runtime, "complete", None)
    if callable(complete):
        return cast(
            AgentJob,
            complete(
                job_id,
                summary=summary,
                stdout=stdout,
                raw_output=stdout,
                parsed_payload=parsed_payload,
                phase=phase,
            ),
        )
    return runtime.status(job_id)


def _runtime_fail(
    runtime: JobRuntime,
    job_id: str,
    *,
    summary: str,
    error: str,
    stdout: str | None = None,
    parsed_payload: dict[str, Any] | None = None,
) -> AgentJob:
    fail = getattr(runtime, "fail", None)
    if callable(fail):
        return cast(
            AgentJob,
            fail(
                job_id,
                summary=summary,
                error=error,
                stdout=stdout,
                raw_output=stdout,
                parsed_payload=parsed_payload,
            ),
        )
    return runtime.status(job_id)


def _job_ref(job: AgentJob) -> dict[str, object]:
    payload = {
        "job_id": job.id,
        "provider": job.provider,
        "kind": job.kind,
        "status": job.status,
        "phase": job.phase,
        "session_id": job.session_id,
        "thread_id": job.thread_id,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }
    provider_runtime = job.metadata.get("provider_runtime")
    if isinstance(provider_runtime, dict):
        payload["provider_runtime"] = dict(provider_runtime)
    return payload


def _merge_job_ids(result: WorkUnitResult, job: AgentJob) -> list[str]:
    existing = list(result.job_ids)
    if job.id in existing:
        return existing
    return [*existing, job.id]


def _flow_provider(flow: tuple[str, ...], index: int, *, fallback: str) -> str:
    if index < len(flow):
        return flow[index]
    return fallback


def _profile_prompt(profile: AgentProfile, default_prompt: str, **context: object) -> str:
    return profile.render_prompt(default_prompt, **context)


def _work_unit_provider(work_unit: WorkUnit, *, default: str) -> str:
    return str(_provider_selection(work_unit, default=default)["actual_provider"])


def _provider_selection(
    work_unit: WorkUnit,
    *,
    default: str,
    runtime: JobRuntime | None = None,
    provider_health_check: Any | None = None,
    fallback_source: str = "runtime_provider_adapter",
) -> dict[str, object]:
    preferred = work_unit.provider_hint or default
    if preferred not in {"claude", "codex", "mock"}:
        actual = _fallback_provider(default=default, runtime=runtime, provider_health_check=provider_health_check)
        return {
            "preferred_provider": preferred,
            "actual_provider": actual,
            "fallback_source": fallback_source,
            "fallback_reason": "unsupported_provider_hint",
            "fallback_detail": f"Provider hint '{preferred}' is unsupported by the runtime adapter; using '{actual}'.",
        }

    status = _provider_runtime_status(preferred, runtime=runtime, provider_health_check=provider_health_check)
    if status["available"]:
        return {
            "preferred_provider": preferred,
            "actual_provider": preferred,
            "fallback_source": None,
            "fallback_reason": None,
            "fallback_detail": None,
        }

    actual = _fallback_provider(
        default=default,
        runtime=runtime,
        provider_health_check=provider_health_check,
        exclude={preferred},
    )
    fallback_reason = str(status["reason"])
    if actual == preferred:
        detail = f"Preferred provider '{preferred}' is unavailable: {status['detail']}; no fallback provider was available."
    else:
        detail = f"Preferred provider '{preferred}' is unavailable: {status['detail']}; using '{actual}'."
    return {
        "preferred_provider": preferred,
        "actual_provider": actual,
        "fallback_source": fallback_source,
        "fallback_reason": fallback_reason,
        "fallback_detail": detail,
    }


def _fallback_provider(
    *,
    default: str,
    runtime: JobRuntime | None,
    provider_health_check: Any | None,
    exclude: set[str] | None = None,
) -> str:
    excluded = exclude or set()
    configured = _configured_runtime_providers(runtime)
    candidates = [default, "codex", "claude", "mock"]
    for candidate in candidates:
        if candidate in excluded or candidate not in configured:
            continue
        status = _provider_runtime_status(candidate, runtime=runtime, provider_health_check=provider_health_check)
        if status["available"]:
            return candidate
    return default


def _configured_runtime_providers(runtime: JobRuntime | None) -> set[str]:
    adapters = getattr(runtime, "adapters", None)
    if isinstance(adapters, dict):
        return {str(provider) for provider in adapters}
    return {"claude", "codex", "mock"}


def _provider_runtime_status(
    provider: str,
    *,
    runtime: JobRuntime | None,
    provider_health_check: Any | None,
) -> dict[str, object]:
    if provider not in {"claude", "codex", "mock"}:
        return {"available": False, "reason": "unsupported_provider_hint", "detail": f"{provider} is unsupported"}
    if provider not in _configured_runtime_providers(runtime):
        return {"available": False, "reason": "adapter_missing", "detail": f"{provider} runtime adapter unavailable"}
    if provider_health_check is None:
        return {"available": True, "reason": None, "detail": "provider availability was not health-checked"}
    try:
        status = provider_health_check(provider) if callable(provider_health_check) else provider_health_check.check(provider)
    except Exception as exc:
        return {"available": False, "reason": "provider_unavailable", "detail": str(exc) or type(exc).__name__}
    available = bool(getattr(status, "available", False))
    detail = str(getattr(status, "detail", "provider unavailable"))
    return {
        "available": available,
        "reason": None if available else "provider_unavailable",
        "detail": detail,
    }


def _review_provider(policy: PolicyProfile) -> str:
    if policy.provider_flow:
        last = policy.provider_flow[-1]
        if last in {"claude", "codex"}:
            return last
    return "claude"


def _parse_provider_review_payload(payload: dict[str, Any] | None) -> ReviewResult | None:
    if not payload:
        return None
    review_payload = payload.get("review_result")
    if not review_payload:
        return None
    return ReviewResult(
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
