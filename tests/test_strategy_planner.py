from agent_orchestrator import OrchestrationMode, get_policy
from agent_orchestrator.adapters import MockClaudeDecomposer, MockClaudePlanner
from agent_orchestrator.intake import TaskRouter
from agent_orchestrator.strategy import CompatibilityStrategyPlanner, ExecutionStrategy


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
