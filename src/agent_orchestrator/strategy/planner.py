"""Strategy planning abstractions and compatibility implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from agent_orchestrator.adapters import DecomposerAdapter
from agent_orchestrator.intake.models import ClarifyPolicy, TaskKind, TaskRouterResult
from agent_orchestrator.policies import PolicyProfile
from agent_orchestrator.strategy.models import ExecutionPlan, ExecutionStrategy, StrategyCandidate
from agent_orchestrator.tasks import TaskContract, WorkUnit


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
            planner_family="compatibility",
            planner_actions=_planner_actions_for_strategy(strategy),
            decision_evidence=_decision_evidence(
                strategy=strategy,
                contract=contract,
                route=route,
                planner_family="compatibility",
                native_work_units=False,
                legacy_candidate_count=len(getattr(self.expander, "last_candidates", [])),
            ),
            operating_boundary=route.operating_boundary if route is not None else "fallback_governed",
            selection_reason=route.selection_reason if route is not None else "Compatibility planner maintained the current execution path.",
            handoff_reason_code=route.handoff_reason_code if route is not None else None,
            fallback_reason_code=route.fallback_reason_code if route is not None else None,
        )
        self.last_plan = plan
        return plan


@dataclass(slots=True)
class NativeStrategyPlanner:
    """Native planner for the first-party coding-agent main path."""

    expander: DecomposerAdapter
    last_plan: ExecutionPlan | None = field(default=None, init=False, repr=False)

    def plan(
        self,
        contract: TaskContract,
        policy: PolicyProfile,
        *,
        route: TaskRouterResult | None = None,
    ) -> ExecutionPlan:
        strategy = _select_native_strategy(contract, policy, route=route)
        reasons = _strategy_reasons(strategy, contract, policy, route=route)
        legacy_work_units = self.expander.decompose(contract, policy)
        work_units = _native_work_units(strategy=strategy, contract=contract, policy=policy, route=route)
        candidates = _native_candidates(strategy=strategy, contract=contract, route=route)
        compatibility_metadata = {
            "legacy_decompose_used": False,
            "legacy_candidate_count": len(getattr(self.expander, "last_candidates", [])),
            "task_type": contract.task_type,
            "native_planner": True,
            "legacy_reference_only": True,
            "native_work_unit_count": len(work_units),
            "legacy_reference_work_unit_count": len(legacy_work_units),
        }
        plan = ExecutionPlan(
            strategy=strategy,
            contract=contract,
            work_units=work_units,
            reasons=reasons,
            candidates=candidates,
            compatibility_metadata=compatibility_metadata,
            planner_family="native",
            planner_actions=_planner_actions_for_strategy(strategy),
            decision_evidence=_decision_evidence(
                strategy=strategy,
                contract=contract,
                route=route,
                planner_family="native",
                native_work_units=True,
                legacy_candidate_count=len(getattr(self.expander, "last_candidates", [])),
                legacy_reference_work_units=legacy_work_units,
            ),
            operating_boundary=route.operating_boundary if route is not None else "native_preferred",
            selection_reason=route.selection_reason if route is not None else "Native planner selected the default bounded coding path.",
            handoff_reason_code=route.handoff_reason_code if route is not None else None,
            fallback_reason_code=route.fallback_reason_code if route is not None else None,
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


def _select_native_strategy(
    contract: TaskContract,
    policy: PolicyProfile,
    *,
    route: TaskRouterResult | None,
) -> ExecutionStrategy:
    if route and route.task_kind == TaskKind.MIGRATION and route.risk_level == "high":
        return ExecutionStrategy.EXTERNAL_HANDOFF
    if route and route.requires_human_confirmation:
        return ExecutionStrategy.NEED_HUMAN_CONFIRMATION
    if route and route.task_kind == TaskKind.INVESTIGATION:
        return ExecutionStrategy.EXPLORE_THEN_EDIT
    if route and route.task_kind == TaskKind.MIGRATION:
        return ExecutionStrategy.MIGRATION_GUARDED
    if route and route.task_kind == TaskKind.DOCS:
        return ExecutionStrategy.DOCS_SYNC
    if route and route.clarify_policy == ClarifyPolicy.DEEP:
        return ExecutionStrategy.CLARIFY_THEN_EDIT
    if route and route.scope_confidence == "medium":
        return ExecutionStrategy.EXPLORE_THEN_EDIT
    if contract.risk_level == "high" and route and route.risk_level == "high":
        return ExecutionStrategy.EXTERNAL_HANDOFF
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
    elif strategy == ExecutionStrategy.CLARIFY_THEN_EDIT:
        reasons.append("The native planner requires explicit clarification before editing.")
    elif strategy == ExecutionStrategy.EXTERNAL_HANDOFF:
        reasons.append("The native planner selected an external handoff because risk exceeds the native bounded path.")
    else:
        reasons.append("Task has enough structure to proceed toward direct editing.")
    if policy.review_required is True:
        reasons.append("Policy requires strong review coverage.")
    return reasons


def _planner_actions_for_strategy(strategy: ExecutionStrategy) -> list[str]:
    if strategy == ExecutionStrategy.INVESTIGATION_ONLY:
        return ["explore", "clarify", "verify"]
    if strategy == ExecutionStrategy.MIGRATION_GUARDED:
        return ["clarify", "approval_pause", "handoff_external"]
    if strategy == ExecutionStrategy.DOCS_SYNC:
        return ["explore", "edit", "verify"]
    if strategy == ExecutionStrategy.NEED_HUMAN_CONFIRMATION:
        return ["clarify", "approval_pause"]
    if strategy == ExecutionStrategy.CLARIFY_THEN_EDIT:
        return ["clarify", "explore", "edit", "verify"]
    if strategy == ExecutionStrategy.EXTERNAL_HANDOFF:
        return ["explore", "handoff_external"]
    if strategy == ExecutionStrategy.GOVERNED_FALLBACK:
        return ["explore", "fallback_external"]
    if strategy == ExecutionStrategy.EXPLORE_THEN_EDIT:
        return ["explore", "edit", "verify", "resume_learning"]
    return ["edit", "verify"]


def _native_candidates(
    *,
    strategy: ExecutionStrategy,
    contract: TaskContract,
    route: TaskRouterResult | None,
) -> list[StrategyCandidate]:
    primary = StrategyCandidate(
        strategy=strategy,
        score=max(len(contract.acceptance_criteria), 1),
        selected=True,
        reasons=_planner_actions_for_strategy(strategy),
        metadata={
            "planner_family": "native",
            "task_type": contract.task_type,
            "route_task_kind": route.task_kind.value if route is not None else None,
        },
    )
    fallback_strategy = ExecutionStrategy.EXPLORE_THEN_EDIT if strategy != ExecutionStrategy.EXPLORE_THEN_EDIT else ExecutionStrategy.DIRECT_EDIT
    fallback = StrategyCandidate(
        strategy=fallback_strategy,
        score=max(len(contract.inputs), 1),
        selected=False,
        reasons=_planner_actions_for_strategy(fallback_strategy),
        metadata={"planner_family": "native", "fallback_candidate": True},
    )
    return [primary, fallback]


def _native_work_units(
    *,
    strategy: ExecutionStrategy,
    contract: TaskContract,
    policy: PolicyProfile,
    route: TaskRouterResult | None,
) -> list[WorkUnit]:
    owner_type = "single_worker"
    base_kwargs = {
        "risk_level": contract.risk_level,
        "parallelizable": False,
        "owner_type": owner_type,
        "max_depth": min(contract.max_depth, 1),
        "failure_policy": contract.failure_policy,
        "provider_hint": "codex",
    }
    scope_inputs = [f"scope: {item}" for item in contract.target_scope] if contract.target_scope else []
    constraint_inputs = [f"constraint: {item}" for item in contract.constraints] if contract.constraints else []
    shared_inputs = list(contract.inputs) + constraint_inputs + scope_inputs
    verify_outputs = list(contract.acceptance_criteria) or ["bounded verification result"]

    if strategy == ExecutionStrategy.EXTERNAL_HANDOFF:
        return [
            WorkUnit(
                goal=f"Handoff high-risk task: {contract.goal}",
                context=f"{contract.context} Native planner selected governed external handoff.",
                inputs=shared_inputs or [contract.goal],
                outputs=["handoff packet", "risk summary"],
                acceptance_criteria=["handoff rationale recorded", "risk boundary explained"],
                depends_on=[],
                provider_hint="claude",
                **{k: v for k, v in base_kwargs.items() if k != "provider_hint"},
            )
        ]
    if strategy == ExecutionStrategy.NEED_HUMAN_CONFIRMATION:
        return [
            WorkUnit(
                goal=f"Clarify approval boundary for: {contract.goal}",
                context=f"{contract.context} Native planner paused before editing to request human confirmation.",
                inputs=shared_inputs or [contract.goal],
                outputs=["approval clarification note"],
                acceptance_criteria=["human confirmation boundary documented"],
                depends_on=[],
                **base_kwargs,
            )
        ]

    units: list[WorkUnit] = []
    previous_id: str | None = None

    if strategy in {
        ExecutionStrategy.EXPLORE_THEN_EDIT,
        ExecutionStrategy.INVESTIGATION_ONLY,
        ExecutionStrategy.DOCS_SYNC,
        ExecutionStrategy.CLARIFY_THEN_EDIT,
        ExecutionStrategy.MIGRATION_GUARDED,
    }:
        explore = WorkUnit(
            goal=f"Explore repository context for: {contract.goal}",
            context=f"{contract.context} Gather bounded repository evidence before mutating files.",
            inputs=shared_inputs or [contract.goal],
            outputs=["repo evidence", "target shortlist"],
            acceptance_criteria=["relevant files or symbols identified"],
            depends_on=[],
            **base_kwargs,
        )
        units.append(explore)
        previous_id = explore.id

    if strategy in {
        ExecutionStrategy.CLARIFY_THEN_EDIT,
        ExecutionStrategy.MIGRATION_GUARDED,
        ExecutionStrategy.NEED_HUMAN_CONFIRMATION,
    }:
        clarify = WorkUnit(
            goal=f"Clarify execution boundary for: {contract.goal}",
            context=f"{contract.context} Resolve missing scope, approval, or rollback expectations before editing.",
            inputs=shared_inputs or [contract.goal],
            outputs=["clarified boundary", "edit preconditions"],
            acceptance_criteria=["execution boundary documented"],
            depends_on=[previous_id] if previous_id else [],
            **base_kwargs,
        )
        units.append(clarify)
        previous_id = clarify.id

    if strategy not in {ExecutionStrategy.INVESTIGATION_ONLY, ExecutionStrategy.NEED_HUMAN_CONFIRMATION, ExecutionStrategy.EXTERNAL_HANDOFF}:
        edit = WorkUnit(
            goal=f"Prepare or apply bounded edits for: {contract.goal}",
            context=f"{contract.context} Follow the native planner's selected edit path.",
            inputs=shared_inputs or [contract.goal],
            outputs=list(contract.outputs) or ["patch intent", "applied change"],
            acceptance_criteria=["edit intent recorded", *contract.acceptance_criteria[:1]] if contract.acceptance_criteria else ["edit intent recorded"],
            depends_on=[previous_id] if previous_id else [],
            **base_kwargs,
        )
        units.append(edit)
        previous_id = edit.id

    if strategy in {
        ExecutionStrategy.DIRECT_EDIT,
        ExecutionStrategy.EXPLORE_THEN_EDIT,
        ExecutionStrategy.CLARIFY_THEN_EDIT,
        ExecutionStrategy.DOCS_SYNC,
        ExecutionStrategy.MIGRATION_GUARDED,
        ExecutionStrategy.INVESTIGATION_ONLY,
    }:
        verify = WorkUnit(
            goal=f"Verify closure for: {contract.goal}",
            context=f"{contract.context} Confirm the latest bounded state and produce recovery-ready evidence.",
            inputs=verify_outputs,
            outputs=["verification status", "recovery guidance"],
            acceptance_criteria=["verification evidence recorded"],
            depends_on=[previous_id] if previous_id else [],
            **base_kwargs,
        )
        units.append(verify)

    return units or [
        WorkUnit(
            goal=contract.goal,
            context=contract.context,
            inputs=shared_inputs or [contract.goal],
            outputs=list(contract.outputs) or ["native plan"],
            acceptance_criteria=list(contract.acceptance_criteria) or ["bounded progress recorded"],
            depends_on=[],
            **base_kwargs,
        )
    ]


def _decision_evidence(
    *,
    strategy: ExecutionStrategy,
    contract: TaskContract,
    route: TaskRouterResult | None,
    planner_family: str,
    native_work_units: bool,
    legacy_candidate_count: int,
    legacy_reference_work_units: list[WorkUnit] | None = None,
) -> dict[str, object]:
    legacy_reference = legacy_reference_work_units or []
    planner_actions = _planner_actions_for_strategy(strategy)
    selected_owner = "external" if strategy == ExecutionStrategy.EXTERNAL_HANDOFF else "native"
    pause_expected = strategy in {
        ExecutionStrategy.MIGRATION_GUARDED,
        ExecutionStrategy.NEED_HUMAN_CONFIRMATION,
        ExecutionStrategy.CLARIFY_THEN_EDIT,
    }
    selected_executor = "external" if selected_owner == "external" else "native"
    ready_next_units = _planner_ready_next_units(strategy=strategy, contract=contract)
    blocked_units = _planner_blocked_units(strategy=strategy, route=route)
    required_handoff_artifacts = (
        ["handoff_packet", "risk_summary"]
        if strategy == ExecutionStrategy.EXTERNAL_HANDOFF
        else ["repo_evidence", "verification_status"]
    )
    return {
        "format": "agent_orchestrator.native_planner_decision.v1" if planner_family == "native" else "agent_orchestrator.compatibility_planner_decision.v1",
        "planner_family": planner_family,
        "selected_strategy": strategy.value,
        "selected_actions": planner_actions,
        "selected_owner": selected_owner,
        "decision_boundary": {
            "task_type": contract.task_type,
            "risk_level": contract.risk_level,
            "scope_hint_count": len(contract.target_scope),
            "unknown_slot_count": len(contract.unknown_slots),
            "route_task_kind": route.task_kind.value if route is not None else None,
            "route_risk_level": route.risk_level if route is not None else None,
            "route_scope_confidence": route.scope_confidence if route is not None else None,
            "requires_human_confirmation": route.requires_human_confirmation if route is not None else False,
        },
        "decision_candidates": [
            strategy.value,
            ExecutionStrategy.EXPLORE_THEN_EDIT.value if strategy != ExecutionStrategy.EXPLORE_THEN_EDIT else ExecutionStrategy.DIRECT_EDIT.value,
        ],
        "posture": {
            "explore_first": "explore" in planner_actions,
            "clarify_first": planner_actions[:1] == ["clarify"],
            "verify_planned": "verify" in planner_actions,
            "pause_expected": pause_expected or "approval_pause" in planner_actions,
            "handoff_expected": "handoff_external" in planner_actions,
            "fallback_expected": "fallback_external" in planner_actions,
        },
        "program_posture": {
            "program_goal": contract.goal,
            "active_milestone": ready_next_units[0] if ready_next_units else contract.goal,
            "completed_milestones": [],
            "ready_next_units": ready_next_units,
            "blocked_units": blocked_units,
        },
        "delegation_contract": {
            "selected_executor": selected_executor,
            "ownership_boundary": route.operating_boundary if route is not None else "native_preferred" if selected_executor == "native" else "external_preferred",
            "handoff_reason_code": route.handoff_reason_code if route is not None else None,
            "fallback_reason_code": route.fallback_reason_code if route is not None else None,
            "required_handoff_artifacts": required_handoff_artifacts,
            "resume_expectation": "approval_pause" if "approval_pause" in planner_actions else "handoff" if "handoff_external" in planner_actions else "continue_native",
        },
        "program_continuity": {
            "resume_supported": True,
            "resume_kind": "planner_continue",
            "compaction_stage": None,
            "continuity_artifact_status": "planner_projected",
            "latest_recovery_hint": "Use the next planned work unit and preserve verification evidence.",
        },
        "milestone_verification": {
            "verification_status": "pending" if "verify" in planner_actions else "not_planned",
            "remaining_checks": list(contract.acceptance_criteria),
            "checkpoint_ready": False,
        },
        "operator_control": {
            "next_recommended_action": planner_actions[0] if planner_actions else "inspect",
            "runbook_recovery_lane": "handoff_external" if "handoff_external" in planner_actions else "approval_pause" if "approval_pause" in planner_actions else "continue_native",
            "approval_pause_state": "approval_pause" in planner_actions,
            "clarify_pause_state": planner_actions[:1] == ["clarify"],
        },
        "native_work_units": native_work_units,
        "legacy_candidate_count": legacy_candidate_count,
        "legacy_reference_work_unit_goals": [unit.goal for unit in legacy_reference[:3]],
    }


def _planner_ready_next_units(*, strategy: ExecutionStrategy, contract: TaskContract) -> list[str]:
    action_labels = {
        "explore": f"Explore repository context for: {contract.goal}",
        "clarify": f"Clarify execution boundary for: {contract.goal}",
        "edit": f"Prepare or apply bounded edits for: {contract.goal}",
        "verify": f"Verify closure for: {contract.goal}",
        "approval_pause": f"Pause for approval on: {contract.goal}",
        "handoff_external": f"Handoff high-risk task: {contract.goal}",
        "fallback_external": f"Fallback externally for: {contract.goal}",
        "resume_learning": f"Checkpoint and continue for: {contract.goal}",
    }
    return [action_labels[action] for action in _planner_actions_for_strategy(strategy) if action in action_labels]


def _planner_blocked_units(
    *,
    strategy: ExecutionStrategy,
    route: TaskRouterResult | None,
) -> list[str]:
    blocked: list[str] = []
    if route is not None and route.requires_human_confirmation:
        blocked.append("awaiting_human_confirmation")
    if strategy == ExecutionStrategy.EXTERNAL_HANDOFF:
        blocked.append("native_boundary_exceeded")
    return blocked
