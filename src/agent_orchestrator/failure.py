"""Failure detection and reroute decisions for whole-run upgrades.

This router only supports full-run escalation between modes. It does not
attempt partial DAG rollback, branch splitting, or multi-path replay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from agent_orchestrator.jobs import JobStatus
from agent_orchestrator.policies import OrchestrationMode

FailureAction = Literal["retry_same_mode", "upgrade_mode", "partial_rescue", "abort"]


@dataclass(frozen=True, slots=True)
class FailureSignal:
    action: FailureAction
    next_mode: OrchestrationMode | None
    work_unit_ids: list[str] = field(default_factory=list)
    root_cause_work_unit_ids: list[str] = field(default_factory=list)
    affected_work_unit_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    confidence: float = 0.5

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "next_mode": self.next_mode.value if self.next_mode else None,
            "work_unit_ids": self.work_unit_ids,
            "root_cause_work_unit_ids": self.root_cause_work_unit_ids,
            "affected_work_unit_ids": self.affected_work_unit_ids,
            "reasons": self.reasons,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class FailureDecision:
    action: FailureAction
    next_mode: OrchestrationMode | None
    work_unit_ids: list[str] = field(default_factory=list)
    root_cause_work_unit_ids: list[str] = field(default_factory=list)
    affected_work_unit_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    confidence: float = 0.5

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "next_mode": self.next_mode.value if self.next_mode else None,
            "work_unit_ids": self.work_unit_ids,
            "root_cause_work_unit_ids": self.root_cause_work_unit_ids,
            "affected_work_unit_ids": self.affected_work_unit_ids,
            "reasons": self.reasons,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class FailureRouter:
    """Inspect a completed run and decide whether to upgrade the whole run."""

    max_auto_upgrades: int = 1

    def inspect(self, run: object) -> FailureDecision:
        mode = self._mode(run)
        reasons: list[str] = []
        high_risk_review = False
        root_cause_work_unit_ids: list[str] = []
        affected_work_unit_ids: list[str] = []
        dependency_map = _dependency_map(run)

        def add_unique(items: list[str], value: str) -> None:
            if value not in items:
                items.append(value)

        for result in getattr(run, "results", []):
            if result.status == "failed":
                reasons.append(f"work unit {result.work_unit_id} failed")
                add_unique(root_cause_work_unit_ids, result.work_unit_id)
            if getattr(result, "recovery_origin_status", None) == "failed":
                reasons.append(f"work unit {result.work_unit_id} was rescued from failure")
            if result.status == "rescued" and mode != OrchestrationMode.SUCCESS_FIRST:
                reasons.append(f"work unit {result.work_unit_id} required rescue")
                add_unique(root_cause_work_unit_ids, result.work_unit_id)
            review_result = getattr(result, "review_result", None)
            if review_result and review_result.verdict == "needs_attention":
                severities = [finding.severity for finding in review_result.findings]
                if any(severity in {"high", "critical"} for severity in severities):
                    high_risk_review = True
                    reasons.append(f"work unit {result.work_unit_id} review needs_attention")
                    add_unique(root_cause_work_unit_ids, result.work_unit_id)
            if getattr(result, "recovery_origin_status", None) == "failed":
                add_unique(root_cause_work_unit_ids, result.work_unit_id)

        for job in getattr(run, "jobs", []):
            if getattr(job, "status", None) == "failed":
                reasons.append(f"job {job.id} failed")
            if self._non_zero_exit(job):
                reasons.append(f"job {job.id} exited non-zero")

        if getattr(run, "final_state", None) == "blocked":
            reasons.append("orchestrator blocked")
        if not getattr(run, "accepted", False):
            reasons.append("run not accepted")

        if not reasons:
            return FailureDecision(
                action="abort",
                next_mode=None,
                work_unit_ids=[],
                root_cause_work_unit_ids=[],
                affected_work_unit_ids=[],
                reasons=["no reroute needed"],
                confidence=0.5,
            )

        if root_cause_work_unit_ids:
            affected_work_unit_ids = _expand_downstream(root_cause_work_unit_ids, dependency_map)
            return FailureDecision(
                action="partial_rescue",
                next_mode=None,
                work_unit_ids=[*root_cause_work_unit_ids, *[unit_id for unit_id in affected_work_unit_ids if unit_id not in root_cause_work_unit_ids]],
                root_cause_work_unit_ids=root_cause_work_unit_ids,
                affected_work_unit_ids=affected_work_unit_ids,
                reasons=reasons,
                confidence=0.85,
            )

        next_mode = self.choose_next_mode(mode, self._signal(mode, reasons, high_risk_review))
        if next_mode is None:
            return FailureDecision(
                action="abort",
                next_mode=None,
                work_unit_ids=[],
                root_cause_work_unit_ids=[],
                affected_work_unit_ids=[],
                reasons=reasons or ["no reroute needed"],
                confidence=0.5,
            )

        if high_risk_review or any("failed" in reason for reason in reasons):
            action: FailureAction = "upgrade_mode"
        else:
            action = "retry_same_mode"
        return FailureDecision(
            action=action,
            next_mode=next_mode,
            work_unit_ids=[],
            root_cause_work_unit_ids=[],
            affected_work_unit_ids=[],
            reasons=reasons,
            confidence=0.8 if reasons else 0.5,
        )

    def choose_next_mode(
        self,
        current_mode: OrchestrationMode,
        failure_signal: FailureSignal,
    ) -> OrchestrationMode | None:
        if current_mode == OrchestrationMode.COST_FIRST:
            return OrchestrationMode.SPEED_FIRST
        if current_mode == OrchestrationMode.SPEED_FIRST:
            return OrchestrationMode.SUCCESS_FIRST
        return None

    def _signal(
        self,
        current_mode: OrchestrationMode,
        reasons: list[str],
        high_risk_review: bool,
    ) -> FailureSignal:
        next_mode = self.choose_next_mode(current_mode, FailureSignal(action="abort", next_mode=None))
        action: FailureAction = "upgrade_mode" if next_mode else "abort"
        return FailureSignal(
            action=action,
            next_mode=next_mode,
            work_unit_ids=[],
            root_cause_work_unit_ids=[],
            affected_work_unit_ids=[],
            reasons=reasons,
            confidence=0.9 if high_risk_review else 0.6,
        )

    @staticmethod
    def _mode(run: object) -> OrchestrationMode:
        policy = getattr(run, "policy", None)
        if policy and getattr(policy, "mode", None):
            return policy.mode
        raise ValueError("Run missing policy mode.")

    @staticmethod
    def _non_zero_exit(job: object) -> bool:
        exit_code = getattr(job, "exit_code", None)
        return exit_code not in (None, 0)


def _dependency_map(run: object) -> dict[str, list[str]]:
    work_units = getattr(run, "work_units", [])
    mapping: dict[str, list[str]] = {}
    for work_unit in work_units:
        for dependency in getattr(work_unit, "depends_on", []):
            mapping.setdefault(dependency, []).append(work_unit.id)
    return mapping


def _expand_downstream(root_ids: list[str], dependency_map: dict[str, list[str]]) -> list[str]:
    affected: list[str] = []
    queue = list(root_ids)
    while queue:
        current = queue.pop(0)
        for downstream in dependency_map.get(current, []):
            if downstream not in affected and downstream not in root_ids:
                affected.append(downstream)
                queue.append(downstream)
    return affected
