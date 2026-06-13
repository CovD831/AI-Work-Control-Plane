from agent_orchestrator.intake import (
    ClarifyPolicy,
    ExecutionMode,
    IntentIntake,
    TaskKind,
    TaskRouter,
)
from agent_orchestrator import OrchestrationMode, get_policy
from agent_orchestrator.adapters import MockClaudePlanner


def test_task_router_routes_direct_fix_to_legacy_with_light_or_skip_clarify() -> None:
    router = TaskRouter()

    result = router.route("Fix the login button click handler in src/ui/login.tsx.")

    assert result.task_kind == TaskKind.DIRECT_FIX
    assert result.execution_mode == ExecutionMode.CODING_AGENT
    assert result.clarify_policy in {ClarifyPolicy.SKIP, ClarifyPolicy.LIGHT}
    assert result.needs_repo_context is True


def test_task_router_routes_investigation_requests() -> None:
    router = TaskRouter()

    result = router.route("Investigate why the planning session stalls and summarize the root cause.")

    assert result.task_kind == TaskKind.INVESTIGATION
    assert result.execution_mode == ExecutionMode.LEGACY
    assert result.clarify_policy in {ClarifyPolicy.LIGHT, ClarifyPolicy.DEEP}


def test_task_router_routes_migration_to_deep_clarify_and_confirmation() -> None:
    router = TaskRouter()

    result = router.route("Migrate the auth database schema without breaking login and payment flows.")

    assert result.task_kind == TaskKind.MIGRATION
    assert result.execution_mode == ExecutionMode.LEGACY
    assert result.clarify_policy == ClarifyPolicy.DEEP
    assert result.requires_human_confirmation is True
    assert result.risk_level == "high"


def test_task_router_routes_docs_tasks() -> None:
    router = TaskRouter()

    result = router.route("Document how the control plane approval flow works for the team.")

    assert result.task_kind == TaskKind.DOCS
    assert result.execution_mode == ExecutionMode.CODING_AGENT
    assert result.needs_repo_context is True


def test_task_router_routes_question_only_requests_to_no_execution() -> None:
    router = TaskRouter()

    result = router.route("How does the planning governance snapshot differ from the control plane state?")

    assert result.task_kind == TaskKind.QUESTION_ONLY
    assert result.execution_mode == ExecutionMode.NO_EXECUTION
    assert result.clarify_policy == ClarifyPolicy.SKIP
    assert result.needs_repo_context is False


def test_intent_intake_only_runs_clarify_when_policy_requires_it() -> None:
    planner = MockClaudePlanner()
    router = TaskRouter()
    intake = IntentIntake(planner)
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)

    question_route = router.route("How does the governance snapshot work?")
    question_result = intake.intake("How does the governance snapshot work?", question_route, policy)
    assert question_result.task_contract is None

    migration_route = router.route("Migrate the auth schema without breaking login.")
    migration_result = intake.intake("Migrate the auth schema without breaking login.", migration_route, policy)
    assert migration_result.task_contract is not None
