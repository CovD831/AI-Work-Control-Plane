from agent_orchestrator import OrchestrationMode, get_policy
from agent_orchestrator.adapters import ContractDraft, EnvSlotFillConfig, OpenAICompatibleSlotFiller
from agent_orchestrator.execution import CodingAgentExecutionRuntime, ExecutionRequest
from agent_orchestrator.intake import ClarifyPolicy, ExecutionMode, TaskKind, TaskRouterResult
from agent_orchestrator.orchestrator import Orchestrator

import pytest


def _real_llm_config_or_skip() -> EnvSlotFillConfig:
    config = EnvSlotFillConfig.from_env()
    if config is None:
        pytest.skip("real-llm config not available from project-root .env.local or environment")
    return config


def _coding_route() -> TaskRouterResult:
    return TaskRouterResult(
        task_kind=TaskKind.DIRECT_FIX,
        clarify_policy=ClarifyPolicy.LIGHT,
        execution_mode=ExecutionMode.CODING_AGENT,
        ambiguity_level="low",
        risk_level="medium",
        scope_confidence="high",
        needs_repo_context=True,
        requires_human_confirmation=False,
        reasons=["real llm integration test"],
    )


def test_real_llm_slotfill_uses_project_env_local_configuration() -> None:
    config = _real_llm_config_or_skip()

    assert config.api_key
    assert config.base_url
    assert config.model


def test_real_llm_slotfill_completes_real_task_contract_fill() -> None:
    config = _real_llm_config_or_skip()
    slot_filler = OpenAICompatibleSlotFiller(config=config)
    draft = ContractDraft(
        raw_requirement="Refactor the CLI argument parsing in src/agent_orchestrator/cli.py without changing runtime selection behavior.",
        normalized_requirement="Refactor CLI argument parsing without changing runtime selection behavior.",
        goal="",
        intent_summary="",
        task_type="implementation",
        constraints=["Do not change runtime selection behavior."],
        non_goals=["Do not rewrite the entire CLI module."],
        target_scope=["src/agent_orchestrator/cli.py"],
        expected_artifacts=[],
        acceptance_criteria=[],
        assumptions=[],
        risk_signals=[],
        missing_slots=["goal", "user_intent_summary", "expected_artifacts", "acceptance_criteria"],
        uncertain_slots=["task_type"],
    )

    result = slot_filler(draft, get_policy(OrchestrationMode.SUCCESS_FIRST))

    if result.warnings:
        pytest.skip(f"real-llm request unavailable in this environment: {result.warnings[0]}")
    assert result.filled_slots
    assert result.filled_slots.get("goal")
    assert result.filled_slots.get("user_intent_summary")
    assert isinstance(result.raw_model_payload, dict)


def test_real_llm_runtime_refines_main_path_edit_intent() -> None:
    _real_llm_config_or_skip()
    runtime = CodingAgentExecutionRuntime(orchestrator=Orchestrator())
    request = ExecutionRequest(
        requirement="Inspect and propose a bounded fix plan for the CLI argument parsing in src/agent_orchestrator/cli.py.",
        route=_coding_route(),
        runtime_name="coding_agent",
        mode=OrchestrationMode.SUCCESS_FIRST,
        session_id="real-llm-runtime-session",
        turn_id="real-llm-runtime-turn",
        context_snapshot={"snapshot_id": "real-llm-runtime"},
        task_contract={
            "id": "real-llm-runtime-task",
            "goal": "Produce a bounded fix plan for CLI argument parsing",
            "non_goals": ["Do not rewrite the full CLI module."],
            "context": "Use repository context and keep runtime selection behavior stable.",
            "inputs": ["CLI argument parsing request"],
            "outputs": ["bounded patch plan"],
            "acceptance_criteria": [
                "The runtime returns a structured edit intent.",
                "The returned target path stays within repository candidates.",
            ],
            "risk_level": "medium",
            "parallelizable": False,
            "owner_type": "single_worker",
            "max_depth": 1,
            "failure_policy": "retry",
        },
    )

    result = runtime.run(request)
    refinement = result.payload.get("llm_assisted_intent") or {}
    if not refinement.get("used_model"):
        pytest.skip(f"real-llm runtime request unavailable in this environment: {refinement.get('reason', 'unknown')}")
    assert result.status == "completed"
    assert result.accepted is True
    assert refinement["applied"] is True
    assert result.payload["edit_intent"]["mode"] == "report_first"
    assert result.payload["edit_intent"]["target_paths"]
    assert "src/agent_orchestrator/cli.py" in result.payload["repo_report"]["candidate_paths"]
    assert "src/agent_orchestrator/cli.py" in result.payload["edit_intent"]["target_paths"]
    assert result.payload["context_selection"]["deterministic"]["strategy"] == "fixed_runtime_sources"
    assert "model_driven" in result.payload["context_selection"]
    assert result.payload["scratchpad_entries"][0]["kind"] == "runtime_context"
    assert result.payload["artifact_summary"]["artifact_count"] >= 1
    assert result.payload["event_summary"]["event_count"] >= 1
    assert result.payload["execution_history_summary"]["status"] == "completed"
    assert result.payload["compaction_state"]["system_prompt_compacted"] is False
