from agent_orchestrator.policies import OrchestrationMode
from agent_orchestrator.routing import PolicyRouter


def test_router_selects_success_first_for_high_risk() -> None:
    decision = PolicyRouter().route("Need to change auth and payment handling")

    assert decision.mode == OrchestrationMode.SUCCESS_FIRST
    assert decision.profile.risk == "high"
    assert decision.confidence >= 0.9


def test_router_selects_success_first_for_high_ambiguity() -> None:
    decision = PolicyRouter().route("帮我优化一下")

    assert decision.mode == OrchestrationMode.SUCCESS_FIRST
    assert decision.profile.ambiguity == "high"


def test_router_selects_speed_first_for_parallel_work() -> None:
    decision = PolicyRouter().route("Implement multiple independent modules in parallel")

    assert decision.mode == OrchestrationMode.SPEED_FIRST
    assert decision.profile.parallelism == "high"


def test_router_selects_cost_first_for_simple_low_risk_work() -> None:
    decision = PolicyRouter().route("Fix a small button label")

    assert decision.mode == OrchestrationMode.COST_FIRST
    assert decision.profile.ambiguity == "low"
    assert decision.profile.risk == "low"


def test_router_risk_wins_over_speed_signal() -> None:
    decision = PolicyRouter().route("Urgent auth refactor today")

    assert decision.mode == OrchestrationMode.SUCCESS_FIRST
    assert "High risk forces success_first." in decision.reasons
