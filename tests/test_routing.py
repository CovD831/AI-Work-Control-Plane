from agent_orchestrator.policies import OrchestrationMode
from agent_orchestrator.routing import PolicyRouter
from agent_orchestrator.topology import build_execution_topology


def test_router_selects_success_first_for_high_risk() -> None:
    decision = PolicyRouter().route("Need to change auth and payment handling")

    assert decision.mode == OrchestrationMode.SUCCESS_FIRST
    assert decision.profile.risk == "high"
    assert decision.candidates
    assert any(candidate["mode"] == "success_first" and candidate["selected"] is True for candidate in decision.candidates)
    assert decision.consensus["selected_mode"] == "success_first"
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
    assert any(item["mode"] == "speed_first" for item in decision.rejected_alternatives)


def test_router_exposes_candidate_rationales_for_all_modes() -> None:
    decision = PolicyRouter().route("Implement multiple independent modules in parallel")

    assert {candidate["mode"] for candidate in decision.candidates} == {"success_first", "speed_first", "cost_first"}
    assert all(candidate["rationale"] for candidate in decision.candidates)
    assert all("score" in candidate for candidate in decision.candidates)
    assert any(candidate["mode"] == "speed_first" and candidate["selected"] is True for candidate in decision.candidates)
    assert decision.consensus["runner_up_mode"] in {"success_first", "cost_first"}
    assert decision.consensus["disagreement_level"] in {"low", "medium", "high"}


def test_topology_defaults_match_mode_strength() -> None:
    success = build_execution_topology(OrchestrationMode.SUCCESS_FIRST.value)
    speed = build_execution_topology(OrchestrationMode.SPEED_FIRST.value)
    cost = build_execution_topology(OrchestrationMode.COST_FIRST.value)

    assert success.depth == 3
    assert success.provider_flow == ("claude", "codex", "claude")
    assert speed.depth == 2
    assert speed.provider_flow == ("claude", "codex")
    assert cost.depth == 0
    assert cost.provider_flow == ()
