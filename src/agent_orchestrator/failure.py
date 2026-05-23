"""Failure detection and reroute decisions for whole-run upgrades.

This router only supports full-run escalation between modes. It does not
attempt partial DAG rollback, branch splitting, or multi-path replay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from agent_orchestrator.jobs import JobStatus
from agent_orchestrator.policies import OrchestrationMode, get_policy

FailureAction = Literal["retry_same_mode", "upgrade_mode", "partial_rescue", "abort"]
UpgradeKind = Literal["depth_upgrade", "mode_upgrade", "abort"]


@dataclass(frozen=True, slots=True)
class FailureSignal:
    action: FailureAction
    next_mode: OrchestrationMode | None
    next_agent_enabled: bool | None = None
    next_depth: int | None = None
    upgrade_kind: UpgradeKind = "abort"
    work_unit_ids: list[str] = field(default_factory=list)
    root_cause_work_unit_ids: list[str] = field(default_factory=list)
    affected_work_unit_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    confidence: float = 0.5

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "next_mode": self.next_mode.value if self.next_mode else None,
            "next_agent_enabled": self.next_agent_enabled,
            "next_depth": self.next_depth,
            "upgrade_kind": self.upgrade_kind,
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
    next_agent_enabled: bool | None = None
    next_depth: int | None = None
    upgrade_kind: UpgradeKind = "abort"
    work_unit_ids: list[str] = field(default_factory=list)
    root_cause_work_unit_ids: list[str] = field(default_factory=list)
    affected_work_unit_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    confidence: float = 0.5

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "next_mode": self.next_mode.value if self.next_mode else None,
            "next_agent_enabled": self.next_agent_enabled,
            "next_depth": self.next_depth,
            "upgrade_kind": self.upgrade_kind,
            "work_unit_ids": self.work_unit_ids,
            "root_cause_work_unit_ids": self.root_cause_work_unit_ids,
            "affected_work_unit_ids": self.affected_work_unit_ids,
            "reasons": self.reasons,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class FailureRouter:
    """Inspect a completed run and decide whether to upgrade the whole run."""

    max_auto_upgrades: int = 3

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
                next_agent_enabled=None,
                next_depth=None,
                upgrade_kind="abort",
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
                next_agent_enabled=None,
                next_depth=None,
                upgrade_kind="abort",
                work_unit_ids=[*root_cause_work_unit_ids, *[unit_id for unit_id in affected_work_unit_ids if unit_id not in root_cause_work_unit_ids]],
                root_cause_work_unit_ids=root_cause_work_unit_ids,
                affected_work_unit_ids=affected_work_unit_ids,
                reasons=reasons,
                confidence=0.85,
            )

        signal = self._signal(run, reasons, high_risk_review)
        if signal.next_mode is None:
            return FailureDecision(
                action="abort",
                next_mode=None,
                next_agent_enabled=None,
                next_depth=None,
                upgrade_kind="abort",
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
            next_mode=signal.next_mode,
            next_agent_enabled=signal.next_agent_enabled,
            next_depth=signal.next_depth,
            upgrade_kind=signal.upgrade_kind,
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
        run: object,
        reasons: list[str],
        high_risk_review: bool,
    ) -> FailureSignal:
        current_mode = self._mode(run)
        policy = getattr(run, "policy", None)
        current_depth = int(getattr(policy, "topology_depth", 0) or 0)
        current_agent_enabled = bool(getattr(policy, "agent_enabled", False))
        target = self._choose_next_topology(current_mode, current_agent_enabled, current_depth)
        next_mode = target["mode"] if target else None
        action: FailureAction = "upgrade_mode" if next_mode else "abort"
        return FailureSignal(
            action=action,
            next_mode=next_mode,
            next_agent_enabled=target["agent_enabled"] if target else None,
            next_depth=target["depth"] if target else None,
            upgrade_kind=target["upgrade_kind"] if target else "abort",
            work_unit_ids=[],
            root_cause_work_unit_ids=[],
            affected_work_unit_ids=[],
            reasons=reasons,
            confidence=0.9 if high_risk_review else 0.6,
        )

    def _choose_next_topology(
        self,
        current_mode: OrchestrationMode,
        current_agent_enabled: bool,
        current_depth: int,
    ) -> dict[str, object] | None:
        current_policy = get_policy(current_mode, agent_enabled=current_agent_enabled, depth=current_depth)
        mode_cap = get_policy(current_mode).topology_depth

        if current_policy.agent_enabled and current_policy.topology_depth < mode_cap:
            return {
                "mode": current_mode,
                "agent_enabled": True,
                "depth": current_policy.topology_depth + 1,
                "upgrade_kind": "depth_upgrade",
            }

        next_mode = self.choose_next_mode(
            current_mode,
            FailureSignal(action="abort", next_mode=None),
        )
        if next_mode is None:
            return None
        next_policy = get_policy(next_mode)
        return {
            "mode": next_mode,
            "agent_enabled": next_policy.agent_enabled,
            "depth": next_policy.topology_depth,
            "upgrade_kind": "mode_upgrade",
        }

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
