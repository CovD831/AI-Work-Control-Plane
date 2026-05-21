"""Adapter interfaces and deterministic MVP implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import sleep
from typing import Any, Protocol, cast

from agent_orchestrator.jobs import AgentJob, InMemoryJobRuntime, JobRequest, JobRuntime
from agent_orchestrator.policies import OrchestrationMode, PolicyProfile
from agent_orchestrator.review import Finding, ReviewResult
from agent_orchestrator.tasks import RiskLevel, TaskContract, WorkUnit, WorkUnitResult


class PlannerAdapter(Protocol):
    """Turns fuzzy requirements into a clarified task contract."""

    def clarify(self, requirement: str, policy: PolicyProfile) -> TaskContract:
        """Create a task contract from a user requirement."""


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

    def clarify(self, requirement: str, policy: PolicyProfile) -> TaskContract:
        goal = requirement.strip()
        if not goal:
            goal = "Clarify and implement the requested change"

        return TaskContract(
            goal=goal,
            non_goals=["Do not recurse beyond the selected policy depth"],
            context=(
                "Use the success-first parent architecture and downgrade behavior "
                "through policy when requested."
            ),
            inputs=[goal],
            outputs=["task tree", "worker results", "review summary"],
            acceptance_criteria=[
                "Requirement is represented as executable work units",
                "Worker results include tests or validation notes",
                "Failures are routed according to policy",
            ],
            risk_level=_infer_risk(goal),
            parallelizable=True,
            owner_type="claude_team",
            max_depth=policy.max_depth,
            failure_policy="rescue" if policy.rescue_enabled else "retry",
        )


@dataclass(slots=True)
class MockClaudeDecomposer:
    """MVP decomposer that models Claude team-style division of labor."""

    def decompose(self, contract: TaskContract, policy: PolicyProfile) -> list[WorkUnit]:
        context = f"{contract.context} {contract.goal}"
        base_units = [
            WorkUnit(
                goal="Define task contract and acceptance criteria",
                context=context,
                inputs=contract.inputs,
                outputs=["contract"],
                acceptance_criteria=["Contract has goal, constraints, and acceptance criteria"],
                risk_level="medium",
                parallelizable=True,
                owner_type="codex_swarm",
                max_depth=contract.max_depth,
                failure_policy=contract.failure_policy,
                depends_on=[],
            ),
            WorkUnit(
                goal="Implement worker execution path",
                context=context,
                inputs=["task contract"],
                outputs=["patch", "validation notes"],
                acceptance_criteria=["Worker returns a structured result"],
                risk_level=contract.risk_level,
                parallelizable=True,
                owner_type="codex_swarm",
                max_depth=contract.max_depth,
                failure_policy=contract.failure_policy,
                depends_on=[],
            ),
            WorkUnit(
                goal="Validate merge readiness",
                context=context,
                inputs=["worker results"],
                outputs=["review summary"],
                acceptance_criteria=["Review determines whether output is acceptable"],
                risk_level="high" if policy.review_required is True else "medium",
                parallelizable=False,
                owner_type="claude_team",
                max_depth=contract.max_depth,
                failure_policy="rescue",
                depends_on=[],
            ),
        ]

        base_units[1].depends_on = [base_units[0].id]
        base_units[2].depends_on = [base_units[1].id]

        if policy.parallelism == "limited":
            return base_units[:1]
        if policy.parallelism == "aggressive":
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
                    depends_on=[base_units[1].id],
                )
            return base_units + [compatibility]
        return base_units


@dataclass(slots=True)
class MockCodexWorker:
    """MVP Codex-style worker that simulates deterministic implementation."""

    runtime: JobRuntime = field(default_factory=InMemoryJobRuntime)

    def execute(self, work_unit: WorkUnit, policy: PolicyProfile) -> WorkUnitResult:
        job = self.runtime.start(
            JobRequest(
                task_id=work_unit.id,
                provider="codex",
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
        if result.status == "failed" and policy.rescue_enabled:
            job = self.runtime.start(
                JobRequest(
                    task_id=work_unit.id,
                    provider="claude",
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
                    provider="claude",
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
    lowered = goal.lower()
    if any(token in lowered for token in ["migration", "security", "payment", "auth"]):
        return "high"
    if any(token in lowered for token in ["refactor", "integration", "parallel"]):
        return "medium"
    return "low"


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
    provider: str
    kind: str
    poll_interval_seconds: float = 0.01
    poll_attempts: int = 200

    def execute(self, work_unit: WorkUnit, policy: PolicyProfile) -> WorkUnitResult:
        job = self.runtime.start(
            JobRequest(
                task_id=work_unit.id,
                provider=self.provider,  # type: ignore[arg-type]
                kind=self.kind,  # type: ignore[arg-type]
                prompt=work_unit.goal,
                cwd=str(Path.cwd()),
                model=None,
                max_depth=policy.max_depth,
                metadata={
                    "context": work_unit.context,
                    "inputs": work_unit.inputs,
                    "outputs": work_unit.outputs,
                    "acceptance_criteria": work_unit.acceptance_criteria,
                },
            )
        )

        completed_job = self.runtime.status(job.id)
        for _ in range(self.poll_attempts):
            if completed_job.status in {"completed", "failed", "cancelled"}:
                break
            sleep(self.poll_interval_seconds)
            completed_job = self.runtime.status(job.id)

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
    return {
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


def _merge_job_ids(result: WorkUnitResult, job: AgentJob) -> list[str]:
    existing = list(result.job_ids)
    if job.id in existing:
        return existing
    return [*existing, job.id]
