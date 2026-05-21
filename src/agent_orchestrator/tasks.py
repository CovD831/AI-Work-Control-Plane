"""Task contract and result models for the orchestration pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

from agent_orchestrator.failure import FailureDecision, FailureSignal
from agent_orchestrator.jobs import AgentJob
from agent_orchestrator.policies import OrchestrationMode, PolicyProfile
from agent_orchestrator.routing import RoutingDecision, TaskProfile
from agent_orchestrator.review import Finding, ReviewResult

RiskLevel = Literal["low", "medium", "high"]
OwnerType = Literal["claude_team", "codex_swarm", "single_worker"]
FailurePolicy = Literal["retry", "split", "escalate", "rescue"]
ResultStatus = Literal["succeeded", "failed", "rescued"]


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


@dataclass(slots=True)
class TaskContract:
    goal: str
    non_goals: list[str]
    context: str
    inputs: list[str]
    outputs: list[str]
    acceptance_criteria: list[str]
    risk_level: RiskLevel
    parallelizable: bool
    owner_type: OwnerType
    max_depth: int
    failure_policy: FailurePolicy
    dependencies: list[dict[str, object]] = field(default_factory=list)
    id: str = field(default_factory=lambda: _new_id("task"))

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "goal": self.goal,
            "non_goals": self.non_goals,
            "context": self.context,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "acceptance_criteria": self.acceptance_criteria,
            "risk_level": self.risk_level,
            "parallelizable": self.parallelizable,
            "owner_type": self.owner_type,
            "max_depth": self.max_depth,
            "failure_policy": self.failure_policy,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "TaskContract":
        return cls(
            goal=str(data["goal"]),
            non_goals=list(data.get("non_goals", [])),
            context=str(data["context"]),
            inputs=list(data.get("inputs", [])),
            outputs=list(data.get("outputs", [])),
            acceptance_criteria=list(data.get("acceptance_criteria", [])),
            risk_level=data["risk_level"],
            parallelizable=bool(data["parallelizable"]),
            owner_type=data["owner_type"],
            max_depth=int(data["max_depth"]),
            failure_policy=data["failure_policy"],
            dependencies=list(data.get("dependencies", [])),
            id=str(data["id"]),
        )


@dataclass(slots=True)
class WorkUnit:
    goal: str
    context: str
    inputs: list[str]
    outputs: list[str]
    acceptance_criteria: list[str]
    risk_level: RiskLevel
    parallelizable: bool
    owner_type: OwnerType
    max_depth: int
    failure_policy: FailurePolicy
    depends_on: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: _new_id("work"))

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "goal": self.goal,
            "context": self.context,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "acceptance_criteria": self.acceptance_criteria,
            "risk_level": self.risk_level,
            "parallelizable": self.parallelizable,
            "owner_type": self.owner_type,
            "max_depth": self.max_depth,
            "failure_policy": self.failure_policy,
            "depends_on": self.depends_on,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "WorkUnit":
        return cls(
            goal=str(data["goal"]),
            context=str(data["context"]),
            inputs=list(data.get("inputs", [])),
            outputs=list(data.get("outputs", [])),
            acceptance_criteria=list(data.get("acceptance_criteria", [])),
            risk_level=data["risk_level"],
            parallelizable=bool(data["parallelizable"]),
            owner_type=data["owner_type"],
            max_depth=int(data["max_depth"]),
            failure_policy=data["failure_policy"],
            depends_on=list(data.get("depends_on", [])),
            id=str(data["id"]),
        )


@dataclass(slots=True)
class WorkUnitResult:
    work_unit_id: str
    status: ResultStatus
    summary: str
    patch: str | None
    tests: list[str]
    needs_rescue: bool
    job_id: str | None = None
    job_ids: list[str] = field(default_factory=list)
    job_status: str | None = None
    job_phase: str | None = None
    job_lifecycle: list[dict[str, object]] = field(default_factory=list)
    review_result: ReviewResult | None = None
    recovery_origin_status: ResultStatus | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "work_unit_id": self.work_unit_id,
            "status": self.status,
            "summary": self.summary,
            "patch": self.patch,
            "tests": self.tests,
            "needs_rescue": self.needs_rescue,
            "job_id": self.job_id,
            "job_ids": self.job_ids,
            "job_status": self.job_status,
            "job_phase": self.job_phase,
            "job_lifecycle": self.job_lifecycle,
            "review_result": self.review_result.to_dict() if self.review_result else None,
            "recovery_origin_status": self.recovery_origin_status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "WorkUnitResult":
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
            work_unit_id=str(data["work_unit_id"]),
            status=data["status"],
            summary=str(data["summary"]),
            patch=data.get("patch"),
            tests=list(data.get("tests", [])),
            needs_rescue=bool(data["needs_rescue"]),
            job_id=data.get("job_id"),
            job_ids=list(data.get("job_ids", [])),
            job_status=data.get("job_status"),
            job_phase=data.get("job_phase"),
            job_lifecycle=list(data.get("job_lifecycle", [])),
            review_result=review_result,
            recovery_origin_status=data.get("recovery_origin_status"),
        )


@dataclass(slots=True)
class OrchestrationAttempt:
    attempt_id: str
    run_id: str | None
    parent_run_id: str | None
    parent_attempt_id: str | None
    policy: PolicyProfile
    contract: TaskContract
    work_units: list[WorkUnit]
    results: list[WorkUnitResult]
    accepted: bool
    final_state: str | None
    status: str
    events: list[dict[str, object]]
    jobs: list[AgentJob] = field(default_factory=list)
    routing_decision: RoutingDecision | None = None
    failure_signal: FailureSignal | None = None
    failure_decision: FailureDecision | None = None
    dependency_rescue_results: list[WorkUnitResult] = field(default_factory=list)
    partial_rescue_results: list[WorkUnitResult] = field(default_factory=list)
    replayed_work_unit_ids: list[str] = field(default_factory=list)
    recovered_work_unit_ids: list[str] = field(default_factory=list)
    attempt_index: int = 0
    job_ids: list[str] = field(default_factory=list)
    job_status_summary: dict[str, int] = field(default_factory=dict)
    current_mode: OrchestrationMode | None = None
    lineage: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "attempt_id": self.attempt_id,
            "run_id": self.run_id,
            "parent_run_id": self.parent_run_id,
            "parent_attempt_id": self.parent_attempt_id,
            "policy": self.policy.to_dict(),
            "contract": self.contract.to_dict(),
            "work_units": [unit.to_dict() for unit in self.work_units],
            "results": [result.to_dict() for result in self.results],
            "accepted": self.accepted,
            "final_state": self.final_state,
            "status": self.status,
            "events": self.events,
            "jobs": [job.to_dict() for job in self.jobs],
            "routing_decision": self.routing_decision.to_dict() if self.routing_decision else None,
            "failure_signal": self.failure_signal.to_dict() if self.failure_signal else None,
            "failure_decision": self.failure_decision.to_dict() if self.failure_decision else None,
            "dependency_rescue_results": [result.to_dict() for result in self.dependency_rescue_results],
            "partial_rescue_results": [result.to_dict() for result in self.partial_rescue_results],
            "replayed_work_unit_ids": self.replayed_work_unit_ids,
            "recovered_work_unit_ids": self.recovered_work_unit_ids,
            "attempt_index": self.attempt_index,
            "job_ids": self.job_ids,
            "job_status_summary": self.job_status_summary,
            "current_mode": self.current_mode.value if self.current_mode else None,
            "lineage": self.lineage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "OrchestrationAttempt":
        policy = PolicyProfile(
            mode=OrchestrationMode(data["policy"]["mode"]),
            max_depth=int(data["policy"]["max_depth"]),
            planner_agents=int(data["policy"]["planner_agents"]),
            review_required=data["policy"]["review_required"],
            rescue_enabled=bool(data["policy"]["rescue_enabled"]),
            rescue_policy=str(data["policy"]["rescue_policy"]),
            parallelism=data["policy"]["parallelism"],
        )
        routing_decision = None
        if data.get("routing_decision"):
            routing_decision_payload = data["routing_decision"]
            profile_payload = routing_decision_payload["profile"]
            routing_decision = RoutingDecision(
                mode=OrchestrationMode(routing_decision_payload["mode"]),
                profile=TaskProfile(
                    ambiguity=str(profile_payload["ambiguity"]),
                    risk=str(profile_payload["risk"]),
                    complexity=str(profile_payload["complexity"]),
                    parallelism=str(profile_payload["parallelism"]),
                    cost_pressure=str(profile_payload["cost_pressure"]),
                    latency_pressure=str(profile_payload["latency_pressure"]),
                    recommended_mode=OrchestrationMode(profile_payload["recommended_mode"]),
                    reasons=list(profile_payload.get("reasons", [])),
                ),
                policy=PolicyProfile(
                    mode=OrchestrationMode(routing_decision_payload["policy"]["mode"]),
                    max_depth=int(routing_decision_payload["policy"]["max_depth"]),
                    planner_agents=int(routing_decision_payload["policy"]["planner_agents"]),
                    review_required=routing_decision_payload["policy"]["review_required"],
                    rescue_enabled=bool(routing_decision_payload["policy"]["rescue_enabled"]),
                    rescue_policy=str(routing_decision_payload["policy"]["rescue_policy"]),
                    parallelism=routing_decision_payload["policy"]["parallelism"],
                ),
                reasons=list(routing_decision_payload.get("reasons", [])),
                confidence=float(routing_decision_payload.get("confidence", 0.5)),
            )
        failure_signal = None
        if data.get("failure_signal"):
            failure_signal_payload = data["failure_signal"]
            failure_signal = FailureSignal(
                action=failure_signal_payload["action"],
                next_mode=OrchestrationMode(failure_signal_payload["next_mode"]) if failure_signal_payload.get("next_mode") else None,
                work_unit_ids=list(failure_signal_payload.get("work_unit_ids", [])),
                root_cause_work_unit_ids=list(failure_signal_payload.get("root_cause_work_unit_ids", [])),
                affected_work_unit_ids=list(failure_signal_payload.get("affected_work_unit_ids", [])),
                reasons=list(failure_signal_payload.get("reasons", [])),
                confidence=float(failure_signal_payload.get("confidence", 0.5)),
            )
        failure_decision = None
        if data.get("failure_decision"):
            failure_decision_payload = data["failure_decision"]
            failure_decision = FailureDecision(
                action=failure_decision_payload["action"],
                next_mode=OrchestrationMode(failure_decision_payload["next_mode"]) if failure_decision_payload.get("next_mode") else None,
                work_unit_ids=list(failure_decision_payload.get("work_unit_ids", [])),
                root_cause_work_unit_ids=list(failure_decision_payload.get("root_cause_work_unit_ids", [])),
                affected_work_unit_ids=list(failure_decision_payload.get("affected_work_unit_ids", [])),
                reasons=list(failure_decision_payload.get("reasons", [])),
                confidence=float(failure_decision_payload.get("confidence", 0.5)),
            )
        return cls(
            attempt_id=str(data["attempt_id"]),
            run_id=data.get("run_id"),
            parent_run_id=data.get("parent_run_id"),
            parent_attempt_id=data.get("parent_attempt_id"),
            policy=policy,
            contract=TaskContract.from_dict(data["contract"]),
            work_units=[WorkUnit.from_dict(unit) for unit in data.get("work_units", [])],
            results=[WorkUnitResult.from_dict(result) for result in data.get("results", [])],
            accepted=bool(data["accepted"]),
            final_state=data.get("final_state"),
            status=str(data["status"]),
            events=list(data.get("events", [])),
            jobs=[AgentJob.from_dict(job) for job in data.get("jobs", [])],
            routing_decision=routing_decision,
            failure_signal=failure_signal,
            failure_decision=failure_decision,
            dependency_rescue_results=[WorkUnitResult.from_dict(result) for result in data.get("dependency_rescue_results", [])],
            partial_rescue_results=[WorkUnitResult.from_dict(result) for result in data.get("partial_rescue_results", [])],
            replayed_work_unit_ids=list(data.get("replayed_work_unit_ids", [])),
            recovered_work_unit_ids=list(data.get("recovered_work_unit_ids", [])),
            attempt_index=int(data.get("attempt_index", 0)),
            job_ids=list(data.get("job_ids", [])),
            job_status_summary=dict(data.get("job_status_summary", {})),
            current_mode=OrchestrationMode(data["current_mode"]) if data.get("current_mode") else None,
            lineage=list(data.get("lineage", [])),
        )


@dataclass(slots=True)
class OrchestrationRun:
    run_id: str
    parent_run_id: str | None
    requirement: str
    initial_mode: OrchestrationMode | None
    final_mode: OrchestrationMode
    attempts: list[OrchestrationAttempt]
    reroute_history: list[dict[str, object]]
    accepted: bool
    final_state: str | None
    status: str
    reroute_enabled: bool
    events: list[dict[str, object]]
    jobs: list[AgentJob] = field(default_factory=list)
    routing_decision: RoutingDecision | None = None
    policy: PolicyProfile | None = None
    contract: TaskContract | None = None
    work_units: list[WorkUnit] = field(default_factory=list)
    results: list[WorkUnitResult] = field(default_factory=list)
    job_ids: list[str] = field(default_factory=list)
    job_status_summary: dict[str, int] = field(default_factory=dict)
    active_attempt_id: str | None = None
    lineage: list[dict[str, object]] = field(default_factory=list)
    lock_status: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "parent_run_id": self.parent_run_id,
            "requirement": self.requirement,
            "initial_mode": self.initial_mode.value if self.initial_mode else None,
            "final_mode": self.final_mode.value,
            "policy": self.policy.to_dict() if self.policy else None,
            "contract": self.contract.to_dict() if self.contract else None,
            "work_units": [unit.to_dict() for unit in self.work_units],
            "results": [result.to_dict() for result in self.results],
            "accepted": self.accepted,
            "final_state": self.final_state,
            "status": self.status,
            "reroute_enabled": self.reroute_enabled,
            "events": self.events,
            "jobs": [job.to_dict() for job in self.jobs],
            "job_ids": self.job_ids,
            "job_status_summary": self.job_status_summary,
            "routing_decision": self.routing_decision.to_dict() if self.routing_decision else None,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "reroute_history": self.reroute_history,
            "active_attempt_id": self.active_attempt_id,
            "lineage": self.lineage,
            "lock_status": self.lock_status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "OrchestrationRun":
        routing_decision = None
        if data.get("routing_decision"):
            routing_payload = data["routing_decision"]
            profile_payload = routing_payload["profile"]
            routing_decision = RoutingDecision(
                mode=OrchestrationMode(routing_payload["mode"]),
                profile=TaskProfile(
                    ambiguity=str(profile_payload["ambiguity"]),
                    risk=str(profile_payload["risk"]),
                    complexity=str(profile_payload["complexity"]),
                    parallelism=str(profile_payload["parallelism"]),
                    cost_pressure=str(profile_payload["cost_pressure"]),
                    latency_pressure=str(profile_payload["latency_pressure"]),
                    recommended_mode=OrchestrationMode(profile_payload["recommended_mode"]),
                    reasons=list(profile_payload.get("reasons", [])),
                ),
                policy=PolicyProfile(
                    mode=OrchestrationMode(routing_payload["policy"]["mode"]),
                    max_depth=int(routing_payload["policy"]["max_depth"]),
                    planner_agents=int(routing_payload["policy"]["planner_agents"]),
                    review_required=routing_payload["policy"]["review_required"],
                    rescue_enabled=bool(routing_payload["policy"]["rescue_enabled"]),
                    rescue_policy=str(routing_payload["policy"]["rescue_policy"]),
                    parallelism=routing_payload["policy"]["parallelism"],
                ),
                reasons=list(routing_payload.get("reasons", [])),
                confidence=float(routing_payload.get("confidence", 0.5)),
            )
        return cls(
            run_id=str(data["run_id"]),
            parent_run_id=data.get("parent_run_id"),
            requirement=str(data.get("requirement", "")),
            initial_mode=OrchestrationMode(data["initial_mode"]) if data.get("initial_mode") else None,
            final_mode=OrchestrationMode(data["final_mode"]),
            attempts=[OrchestrationAttempt.from_dict(attempt) for attempt in data.get("attempts", [])],
            reroute_history=list(data.get("reroute_history", [])),
            accepted=bool(data["accepted"]),
            final_state=data.get("final_state"),
            status=str(data["status"]),
            reroute_enabled=bool(data.get("reroute_enabled", True)),
            events=list(data.get("events", [])),
            jobs=[AgentJob.from_dict(job) for job in data.get("jobs", [])],
            routing_decision=routing_decision,
            policy=PolicyProfile(
                mode=OrchestrationMode(data["policy"]["mode"]),
                max_depth=int(data["policy"]["max_depth"]),
                planner_agents=int(data["policy"]["planner_agents"]),
                review_required=data["policy"]["review_required"],
                rescue_enabled=bool(data["policy"]["rescue_enabled"]),
                rescue_policy=str(data["policy"]["rescue_policy"]),
                parallelism=data["policy"]["parallelism"],
            ) if data.get("policy") else None,
            contract=TaskContract.from_dict(data["contract"]) if data.get("contract") else None,
            work_units=[WorkUnit.from_dict(unit) for unit in data.get("work_units", [])],
            results=[WorkUnitResult.from_dict(result) for result in data.get("results", [])],
            job_ids=list(data.get("job_ids", [])),
            job_status_summary=dict(data.get("job_status_summary", {})),
            active_attempt_id=data.get("active_attempt_id"),
            lineage=list(data.get("lineage", [])),
            lock_status=data.get("lock_status"),
        )


@dataclass(slots=True)
class OrchestrationRunHandle:
    run_id: str
    status: str
    active_attempt_id: str | None
    job_ids: list[str]
    final_mode: OrchestrationMode | None = None
    parent_run_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "active_attempt_id": self.active_attempt_id,
            "job_ids": self.job_ids,
            "final_mode": self.final_mode.value if self.final_mode else None,
            "parent_run_id": self.parent_run_id,
        }


@dataclass(slots=True)
class OrchestrationAttemptHandle:
    run_id: str
    attempt_id: str
    status: str
    job_ids: list[str]
    current_mode: OrchestrationMode | None = None
    parent_attempt_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "attempt_id": self.attempt_id,
            "status": self.status,
            "job_ids": self.job_ids,
            "current_mode": self.current_mode.value if self.current_mode else None,
            "parent_attempt_id": self.parent_attempt_id,
        }
