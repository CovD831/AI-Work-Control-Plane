from agent_orchestrator import OrchestrationMode, get_policy
from agent_orchestrator.adapters import MockClaudeDecomposer, MockClaudePlanner
from agent_orchestrator.intake import TaskRouter
from agent_orchestrator.strategy import CompatibilityStrategyPlanner, ExecutionStrategy, NativeStrategyPlanner


def test_strategy_planner_selects_migration_guarded_for_migrations() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    strategy_planner = CompatibilityStrategyPlanner(decomposer)
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    route = TaskRouter().route("Migrate the auth schema without breaking login or payment flows.")
    contract = planner.clarify("Migrate the auth schema without breaking login or payment flows.", policy)

    plan = strategy_planner.plan(contract, policy, route=route)

    assert plan.strategy == ExecutionStrategy.MIGRATION_GUARDED
    assert plan.work_units
    assert plan.compatibility_metadata["legacy_decompose_used"] is True
    assert plan.candidates


def test_strategy_planner_selects_investigation_only_for_investigations() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    strategy_planner = CompatibilityStrategyPlanner(decomposer)
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    route = TaskRouter().route("Investigate why the queue stalls and summarize the root cause.")
    contract = planner.clarify("Investigate why the queue stalls and summarize the root cause.", policy)

    plan = strategy_planner.plan(contract, policy, route=route)

    assert plan.strategy == ExecutionStrategy.INVESTIGATION_ONLY
    assert plan.work_units[0].goal == "Trace the issue scope and collect evidence"


def test_native_strategy_planner_promotes_investigation_to_explore_then_edit() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    strategy_planner = NativeStrategyPlanner(decomposer)
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    route = TaskRouter().route("Investigate why the queue stalls and summarize the root cause.")
    contract = planner.clarify("Investigate why the queue stalls and summarize the root cause.", policy)

    plan = strategy_planner.plan(contract, policy, route=route)

    assert plan.strategy == ExecutionStrategy.EXPLORE_THEN_EDIT
    assert "resume_learning" in plan.planner_actions
    assert plan.compatibility_metadata["legacy_reference_only"] is True
    assert plan.decision_evidence["planner_family"] == "native"
    assert plan.decision_evidence["native_work_units"] is True
    assert plan.decision_evidence["selected_actions"] == ["explore", "edit", "verify", "resume_learning"]
    assert plan.decision_evidence["selected_owner"] == "native"
    assert plan.decision_evidence["posture"]["explore_first"] is True
    assert plan.decision_evidence["posture"]["verify_planned"] is True
    assert plan.decision_evidence["program_posture"]["program_goal"] == contract.goal
    assert plan.decision_evidence["program_posture"]["ready_next_units"]
    assert plan.decision_evidence["delegation_contract"]["selected_executor"] == "native"
    assert plan.decision_evidence["milestone_verification"]["verification_status"] == "pending"
    assert plan.decision_evidence["operator_control"]["next_recommended_action"] == "explore"
    assert [unit.goal for unit in plan.work_units] == [
        f"Explore repository context for: {contract.goal}",
        f"Prepare or apply bounded edits for: {contract.goal}",
        f"Verify closure for: {contract.goal}",
    ]


def test_strategy_planner_can_select_direct_edit_for_structured_fix_requests() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    strategy_planner = CompatibilityStrategyPlanner(decomposer)
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    route = TaskRouter().route("Fix the click handler in src/ui/login.tsx.")
    contract = planner.clarify("Fix the click handler in src/ui/login.tsx.", policy)

    plan = strategy_planner.plan(contract, policy, route=route)

    assert plan.strategy == ExecutionStrategy.DIRECT_EDIT
    assert plan.work_units
    assert any(candidate.selected for candidate in plan.candidates)


def test_native_strategy_planner_marks_main_path_as_native() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    strategy_planner = NativeStrategyPlanner(decomposer)
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    route = TaskRouter().route("Fix the click handler in src/ui/login.tsx.")
    contract = planner.clarify("Fix the click handler in src/ui/login.tsx.", policy)

    plan = strategy_planner.plan(contract, policy, route=route)

    assert plan.strategy == ExecutionStrategy.DIRECT_EDIT
    assert plan.compatibility_metadata["legacy_decompose_used"] is False
    assert plan.planner_family == "native"
    assert plan.planner_actions == ["edit", "verify"]
    assert plan.operating_boundary == "native_preferred"
    assert plan.selection_reason
    assert plan.fallback_reason_code == "native_runtime_unavailable"
    assert plan.decision_evidence["format"] == "agent_orchestrator.native_planner_decision.v1"
    assert plan.decision_evidence["selected_strategy"] == "direct_edit"
    assert plan.decision_evidence["selected_actions"] == ["edit", "verify"]
    assert plan.decision_evidence["selected_owner"] == "native"
    assert plan.decision_evidence["posture"]["explore_first"] is False
    assert plan.decision_evidence["program_posture"]["active_milestone"] == f"Prepare or apply bounded edits for: {contract.goal}"
    assert plan.decision_evidence["delegation_contract"]["resume_expectation"] == "continue_native"
    assert plan.work_units[0].goal == f"Prepare or apply bounded edits for: {contract.goal}"
    assert plan.work_units[1].goal == f"Verify closure for: {contract.goal}"


def test_native_strategy_planner_can_choose_external_handoff_for_high_risk_work() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    strategy_planner = NativeStrategyPlanner(decomposer)
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    route = TaskRouter().route("Fix the auth payment permission flow in the database migration path.")
    contract = planner.clarify("Fix the auth payment permission flow in the database migration path.", policy)

    plan = strategy_planner.plan(contract, policy, route=route)

    assert plan.strategy in {ExecutionStrategy.MIGRATION_GUARDED, ExecutionStrategy.EXTERNAL_HANDOFF}
    assert plan.operating_boundary == "external_preferred"
    assert plan.handoff_reason_code == "risk_exceeds_native_bounded_path"
    if plan.strategy == ExecutionStrategy.EXTERNAL_HANDOFF:
        assert "handoff_external" in plan.planner_actions
        assert plan.work_units[0].goal.startswith("Handoff high-risk task:")
        assert plan.decision_evidence["decision_boundary"]["requires_human_confirmation"] is True
        assert plan.decision_evidence["selected_owner"] == "external"
        assert plan.decision_evidence["posture"]["handoff_expected"] is True
        assert "native_boundary_exceeded" in plan.decision_evidence["program_posture"]["blocked_units"]
        assert plan.decision_evidence["delegation_contract"]["selected_executor"] == "external"


def test_native_strategy_planner_uses_clarify_step_for_deep_clarify_routes() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    strategy_planner = NativeStrategyPlanner(decomposer)
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    route = TaskRouter().route("Refactor auth integration safely.")
    contract = planner.clarify("Refactor auth integration safely.", policy)

    plan = strategy_planner.plan(contract, policy, route=route)

    assert plan.strategy == ExecutionStrategy.CLARIFY_THEN_EDIT
    assert plan.planner_actions == ["clarify", "explore", "edit", "verify"]
    assert [unit.goal for unit in plan.work_units][:3] == [
        f"Explore repository context for: {contract.goal}",
        f"Clarify execution boundary for: {contract.goal}",
        f"Prepare or apply bounded edits for: {contract.goal}",
    ]
    assert plan.decision_evidence["decision_boundary"]["risk_level"] == "high"
    assert plan.decision_evidence["posture"]["clarify_first"] is True
    assert plan.decision_evidence["posture"]["pause_expected"] is True
    assert plan.decision_evidence["operator_control"]["clarify_pause_state"] is True
