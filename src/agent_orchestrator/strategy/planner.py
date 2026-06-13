"""Strategy planning abstractions and compatibility implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from agent_orchestrator.adapters import DecomposerAdapter
from agent_orchestrator.intake.models import TaskKind, TaskRouterResult
from agent_orchestrator.policies import PolicyProfile
from agent_orchestrator.strategy.models import ExecutionPlan, ExecutionStrategy, StrategyCandidate
from agent_orchestrator.tasks import TaskContract


class StrategyPlanner(Protocol):
    """Selects an execution strategy and produces an execution plan."""

    def plan(
        self,
        contract: TaskContract,
        policy: PolicyProfile,
        *,
        route: TaskRouterResult | None = None,
    ) -> ExecutionPlan:
        """Return the selected execution plan for the contract."""


@dataclass(slots=True)
class CompatibilityStrategyPlanner:
    """Phase-2 bridge that keeps old decompose behavior behind a strategy layer."""

    expander: DecomposerAdapter
    last_plan: ExecutionPlan | None = field(default=None, init=False, repr=False)

    def plan(
        self,
        contract: TaskContract,
        policy: PolicyProfile,
        *,
        route: TaskRouterResult | None = None,
    ) -> ExecutionPlan:
        strategy = _select_strategy(contract, policy, route=route)
        strategy_reasons = _strategy_reasons(strategy, contract, policy, route=route)
        work_units = self.expander.decompose(contract, policy)

        compatibility_candidates = [
            StrategyCandidate(
                strategy=strategy,
                score=int(candidate.score),
                selected=bool(candidate.selected),
                reasons=[str(item) for item in candidate.rationale_items] or [str(item) for item in candidate.rationale],
                metadata={
                    "legacy_strategy": candidate.strategy,
                    "shape": candidate.graph_metadata.get("shape"),
                    "score_breakdown": dict(candidate.score_breakdown),
                },
            )
            for candidate in getattr(self.expander, "last_candidates", [])
        ]
        if not compatibility_candidates:
            compatibility_candidates = [
                StrategyCandidate(
                    strategy=strategy,
                    score=len(work_units),
                    selected=True,
                    reasons=list(strategy_reasons),
                    metadata={"source": "compatibility_default"},
                )
            ]

        plan = ExecutionPlan(
            strategy=strategy,
            contract=contract,
            work_units=work_units,
            reasons=strategy_reasons,
            candidates=compatibility_candidates,
            compatibility_metadata={
                "legacy_decompose_used": True,
                "legacy_candidate_count": len(getattr(self.expander, "last_candidates", [])),
                "task_type": contract.task_type,
            },
        )
        self.last_plan = plan
        return plan


def _select_strategy(
    contract: TaskContract,
    policy: PolicyProfile,
    *,
    route: TaskRouterResult | None,
) -> ExecutionStrategy:
    if route and route.task_kind == TaskKind.MIGRATION:
        return ExecutionStrategy.MIGRATION_GUARDED
    if route and route.task_kind == TaskKind.INVESTIGATION:
        return ExecutionStrategy.INVESTIGATION_ONLY
    if route and route.task_kind == TaskKind.DOCS:
        return ExecutionStrategy.DOCS_SYNC
    if contract.task_type == "migration":
        return ExecutionStrategy.MIGRATION_GUARDED
    if contract.task_type == "investigation":
        return ExecutionStrategy.INVESTIGATION_ONLY
    if contract.task_type == "docs":
        return ExecutionStrategy.DOCS_SYNC
    if route and route.requires_human_confirmation:
        return ExecutionStrategy.NEED_HUMAN_CONFIRMATION
    if route and route.scope_confidence == "medium":
        return ExecutionStrategy.EXPLORE_THEN_EDIT
    if contract.risk_level == "high" and not contract.target_scope:
        return ExecutionStrategy.EXPLORE_THEN_EDIT
    return ExecutionStrategy.DIRECT_EDIT


def _strategy_reasons(
    strategy: ExecutionStrategy,
    contract: TaskContract,
    policy: PolicyProfile,
    *,
    route: TaskRouterResult | None,
) -> list[str]:
    reasons: list[str] = []
    if route:
        reasons.extend(route.reasons)
    if strategy == ExecutionStrategy.NEED_HUMAN_CONFIRMATION:
        reasons.append("Route requires human confirmation before active execution.")
    elif strategy == ExecutionStrategy.MIGRATION_GUARDED:
        reasons.append("Migration-style work requires guarded planning and rollback-aware execution.")
    elif strategy == ExecutionStrategy.INVESTIGATION_ONLY:
        reasons.append("Investigation-style work should prioritize evidence gathering before implementation.")
    elif strategy == ExecutionStrategy.DOCS_SYNC:
        reasons.append("Documentation work should sync source behavior and written guidance.")
    elif strategy == ExecutionStrategy.EXPLORE_THEN_EDIT:
        reasons.append("Scope confidence is incomplete, so exploration should precede editing.")
    else:
        reasons.append("Task has enough structure to proceed toward direct editing.")
    if policy.review_required is True:
        reasons.append("Policy requires strong review coverage.")
    return reasons
