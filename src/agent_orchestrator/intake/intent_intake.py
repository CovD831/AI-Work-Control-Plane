"""Intent-intake bridge for optional clarify entry."""

from __future__ import annotations

from agent_orchestrator.adapters import PlannerAdapter
from agent_orchestrator.intake.models import ClarifyPolicy, IntentIntakeResult, TaskRouterResult
from agent_orchestrator.policies import PolicyProfile


class IntentIntake:
    """Conditionally upgrades a raw request into a structured task contract."""

    def __init__(self, planner: PlannerAdapter) -> None:
        self.planner = planner

    def intake(self, requirement: str, route: TaskRouterResult, policy: PolicyProfile) -> IntentIntakeResult:
        normalized_requirement = " ".join(requirement.strip().split())
        task_contract = None
        if route.clarify_policy != ClarifyPolicy.SKIP:
            task_contract = self.planner.clarify(normalized_requirement, policy).to_dict()
        return IntentIntakeResult(
            raw_requirement=requirement,
            normalized_requirement=normalized_requirement,
            clarify_policy=route.clarify_policy,
            task_kind=route.task_kind,
            execution_mode=route.execution_mode,
            risk_level=route.risk_level,
            scope_confidence=route.scope_confidence,
            requires_human_confirmation=route.requires_human_confirmation,
            reasons=list(route.reasons),
            task_contract=task_contract,
        )
