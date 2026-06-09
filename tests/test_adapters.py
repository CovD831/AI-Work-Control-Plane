from agent_orchestrator import OrchestrationMode, get_policy
import json

from agent_orchestrator.adapters import (
    ContractDraft,
    DecompositionCandidate,
    EnvSlotFillConfig,
    ExtractedSignals,
    MockClaudeDecomposer,
    MockClaudePlanner,
    OpenAICompatibleSlotFiller,
    SlotFillResult,
)
from agent_orchestrator.tasks import TaskContract, WorkUnit


def test_task_contract_from_dict_supports_legacy_payload() -> None:
    payload = {
        "id": "task-1",
        "goal": "Build dashboard",
        "non_goals": ["Do not add auth"],
        "context": "ctx",
        "inputs": ["Build dashboard"],
        "outputs": ["task tree"],
        "acceptance_criteria": ["done"],
        "risk_level": "low",
        "parallelizable": True,
        "owner_type": "claude_team",
        "max_depth": 3,
        "failure_policy": "rescue",
        "dependencies": [],
    }

    contract = TaskContract.from_dict(payload)

    assert contract.task_type == "implementation"
    assert contract.constraints == []
    assert contract.assumptions == []
    assert contract.target_scope == []
    assert contract.expected_artifacts == []
    assert contract.risk_signals == []
    assert contract.user_intent_summary == ""
    assert contract.raw_requirement == ""
    assert contract.slot_sources == {}
    assert contract.unknown_slots == []
    assert contract.slot_fill_warnings == []


def test_task_contract_round_trips_structured_fields() -> None:
    contract = TaskContract(
        goal="Improve clarify behavior",
        non_goals=["Do not touch execute"],
        context="ctx",
        inputs=["requirement"],
        outputs=["patch", "tests"],
        acceptance_criteria=["contract captures constraints"],
        risk_level="medium",
        parallelizable=True,
        owner_type="claude_team",
        max_depth=3,
        failure_policy="rescue",
        task_type="refactor",
        constraints=["Only modify clarify path"],
        assumptions=["planner remains deterministic by default"],
        target_scope=["src/agent_orchestrator/planning.py", "planner.clarify"],
        expected_artifacts=["patch", "tests", "validation notes"],
        risk_signals=["Touches downstream decomposition behavior"],
        user_intent_summary="Formalize clarify output into a richer task contract.",
        raw_requirement="formalize clarify",
        slot_sources={"goal": "rule", "task_type": "llm"},
        unknown_slots=["target_scope"],
        slot_fill_warnings=["slot_fill_response_partial"],
    )

    restored = TaskContract.from_dict(contract.to_dict())

    assert restored.task_type == "refactor"
    assert restored.constraints == ["Only modify clarify path"]
    assert restored.assumptions == ["planner remains deterministic by default"]
    assert restored.target_scope == ["src/agent_orchestrator/planning.py", "planner.clarify"]
    assert restored.expected_artifacts == ["patch", "tests", "validation notes"]
    assert restored.risk_signals == ["Touches downstream decomposition behavior"]
    assert restored.user_intent_summary == "Formalize clarify output into a richer task contract."
    assert restored.raw_requirement == "formalize clarify"
    assert restored.slot_sources == {"goal": "rule", "task_type": "llm"}
    assert restored.unknown_slots == ["target_scope"]
    assert restored.slot_fill_warnings == ["slot_fill_response_partial"]


def test_clarify_draft_models_default_to_empty_slot_state() -> None:
    signals = ExtractedSignals(raw_requirement="improve clarify")
    draft = ContractDraft(raw_requirement="improve clarify")
    fill = SlotFillResult()

    assert signals.explicit_paths == []
    assert signals.explicit_constraints == []
    assert draft.missing_slots == []
    assert draft.uncertain_slots == []
    assert draft.slot_sources == {}
    assert fill.filled_slots == {}
    assert fill.unknown_slots == []
    assert fill.warnings == []


def test_mock_claude_planner_extracts_constraints_scope_and_task_type() -> None:
    planner = MockClaudePlanner()
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)

    contract = planner.clarify(
        "Only modify src/agent_orchestrator/planning.py and planner.clarify; do not change review or execute behavior. "
        "Refactor the clarify logic into a more formal task contract.",
        policy,
    )

    assert contract.task_type == "refactor"
    assert "Only modify src/agent_orchestrator/planning.py and planner.clarify" in contract.constraints
    assert "Do not change review or execute behavior" in contract.non_goals
    assert "src/agent_orchestrator/planning.py" in contract.target_scope
    assert "planner.clarify" in contract.target_scope
    assert "patch" in contract.expected_artifacts
    assert "tests" in contract.expected_artifacts
    assert contract.raw_requirement.startswith("Only modify src/agent_orchestrator/planning.py")


def test_mock_claude_planner_marks_high_risk_migration_work() -> None:
    planner = MockClaudePlanner()
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)

    contract = planner.clarify(
        "Plan an auth migration for the payment service without breaking existing login flows.",
        policy,
    )

    assert contract.task_type == "migration"
    assert contract.risk_level == "high"
    assert "Touches authentication behavior" in contract.risk_signals
    assert "Touches payment behavior" in contract.risk_signals
    assert "migration plan" in contract.expected_artifacts
    assert "rollback notes" in contract.expected_artifacts


def test_mock_claude_planner_investigation_outputs_analysis_artifacts() -> None:
    planner = MockClaudePlanner()
    policy = get_policy(OrchestrationMode.COST_FIRST)

    contract = planner.clarify(
        "Investigate why the planning session stalls and summarize the root cause without changing production code.",
        policy,
    )

    assert contract.task_type == "investigation"
    assert contract.expected_artifacts == ["analysis note", "findings", "recommendation"]
    assert contract.outputs == ["analysis note", "findings", "recommendation"]
    assert "Without changing production code" in contract.non_goals


def test_mock_claude_planner_does_not_require_slot_filler_for_normal_flow() -> None:
    planner = MockClaudePlanner()
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)

    contract = planner.clarify("Refactor auth integration safely.", policy)

    assert contract.goal == "Refactor auth integration safely."
    assert contract.task_type == "refactor"


def test_mock_claude_planner_uses_slot_filler_for_ambiguous_input() -> None:
    calls: list[ContractDraft] = []

    def fill_slots(draft: ContractDraft, policy: object) -> SlotFillResult:
        calls.append(draft)
        return SlotFillResult(
            filled_slots={
                "task_type": "investigation",
                "expected_artifacts": ["analysis note", "findings", "recommendation"],
                "acceptance_criteria": [
                    "Findings describe the issue",
                    "Recommendation explains the next action",
                ],
            },
            unknown_slots=["target_scope"],
        )

    planner = MockClaudePlanner(slot_filler=fill_slots)
    policy = get_policy(OrchestrationMode.COST_FIRST)

    contract = planner.clarify("Look into this and tell me what is wrong.", policy)

    assert len(calls) == 1
    assert contract.task_type == "investigation"
    assert contract.expected_artifacts == ["analysis note", "findings", "recommendation"]
    assert contract.slot_sources["task_type"] == "llm"
    assert "target_scope" in contract.unknown_slots


def test_mock_claude_planner_preserves_locked_fields_during_slot_fill() -> None:
    def fill_slots(draft: ContractDraft, policy: object) -> SlotFillResult:
        return SlotFillResult(
            filled_slots={
                "target_scope": ["src/elsewhere.py"],
                "non_goals": ["Do not change review behavior", "Do not change execute behavior"],
                "task_type": "refactor",
            }
        )

    planner = MockClaudePlanner(slot_filler=fill_slots)
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)

    contract = planner.clarify(
        "Only modify src/agent_orchestrator/planning.py and planner.clarify; do not change review behavior.",
        policy,
    )

    assert "src/agent_orchestrator/planning.py" in contract.target_scope
    assert "src/elsewhere.py" not in contract.target_scope


def test_mock_claude_decomposer_uses_investigation_artifacts_for_direct_execution() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    policy = get_policy(OrchestrationMode.COST_FIRST)
    contract = planner.clarify(
        "Investigate why the planning session stalls and summarize the root cause without changing production code.",
        policy,
    )

    work_units = decomposer.decompose(contract, policy)

    assert len(work_units) == 1
    assert work_units[0].outputs == ["analysis note", "findings", "recommendation"]
    assert any(item.startswith("non_goal: Without changing production code") for item in work_units[0].inputs)


def test_mock_claude_decomposer_passes_constraints_and_scope_into_team_context() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    contract = planner.clarify(
        "Only modify src/agent_orchestrator/planning.py and planner.clarify; do not change review behavior. "
        "Refactor the clarify logic into a more formal task contract.",
        policy,
    )

    work_units = decomposer.decompose(contract, policy)

    assert len(work_units) == 3
    assert "constraint: Only modify src/agent_orchestrator/planning.py and planner.clarify" in work_units[0].inputs
    assert "scope: src/agent_orchestrator/planning.py" in work_units[0].inputs
    assert work_units[1].outputs == ["patch", "tests", "validation notes"]
    assert work_units[1].goal == "Implement the constrained change set"


def test_decomposition_candidate_round_trips_work_units() -> None:
    candidate = DecompositionCandidate(
        name="candidate-a",
        strategy="task_type_template",
        rationale=["Prefer a task-type specific template."],
        work_units=[
            WorkUnit(
                goal="Inspect scope",
                context="ctx",
                inputs=["goal"],
                outputs=["notes"],
                acceptance_criteria=["finish"],
                risk_level="low",
                parallelizable=False,
                owner_type="single_worker",
                max_depth=1,
                failure_policy="retry",
                provider_hint="codex",
                depends_on=[],
                id="work-1",
            )
        ],
        score=3,
        selected=True,
        graph_metadata={"shape": "single"},
    )

    restored = DecompositionCandidate.from_dict(candidate.to_dict())

    assert restored.name == "candidate-a"
    assert restored.strategy == "task_type_template"
    assert restored.selected is True
    assert restored.graph_metadata == {"shape": "single"}
    assert len(restored.work_units) == 1
    assert restored.work_units[0].goal == "Inspect scope"


def test_mock_claude_decomposer_records_selected_candidate_for_current_pipeline() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    contract = planner.clarify("Refactor auth integration safely.", policy)

    work_units = decomposer.decompose(contract, policy)

    assert len(work_units) == 3
    assert len(decomposer.last_candidates) >= 2
    candidate = decomposer.last_candidates[0]
    assert candidate.selected is True
    assert candidate.strategy == "general_pipeline"
    assert candidate.graph_metadata["shape"] == "general_pipeline"
    assert [unit.id for unit in candidate.work_units] == [unit.id for unit in work_units]


def test_mock_claude_decomposer_builds_investigation_team_pipeline() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    contract = planner.clarify(
        "Investigate why the planning session stalls and summarize the root cause without changing production code.",
        policy,
    )

    work_units = decomposer.decompose(contract, policy)

    assert len(work_units) == 3
    assert work_units[0].goal == "Trace the issue scope and collect evidence"
    assert work_units[1].goal == "Synthesize investigation findings and recommendation"
    assert work_units[1].outputs == ["analysis note", "findings", "recommendation"]
    assert work_units[2].goal == "Validate investigation completeness"


def test_mock_claude_decomposer_builds_migration_pipeline_with_rollback_step() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    contract = planner.clarify(
        "Plan an auth migration for the payment service without breaking existing login flows.",
        policy,
    )

    work_units = decomposer.decompose(contract, policy)

    assert len(work_units) == 4
    assert work_units[0].goal == "Plan the migration scope and safety checks"
    assert work_units[1].goal == "Implement the migration change set"
    assert work_units[2].goal == "Validate rollback and compatibility safeguards"
    assert work_units[3].goal == "Validate merge readiness"
    assert work_units[2].outputs == ["rollback notes", "compatibility notes"]


def test_mock_claude_decomposer_builds_docs_pipeline_without_patch_default() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    contract = planner.clarify("Document how the planning control flow works for the team.", policy)

    work_units = decomposer.decompose(contract, policy)

    assert len(work_units) == 3
    assert work_units[0].goal == "Inspect the current behavior and source references"
    assert work_units[1].goal == "Draft the requested documentation update"
    assert work_units[1].outputs == ["docs patch", "validation notes"]


def test_mock_claude_decomposer_emits_multiple_candidates_for_team_tasks() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    contract = planner.clarify("Refactor auth integration safely.", policy)

    work_units = decomposer.decompose(contract, policy)

    assert len(work_units) == 3
    assert len(decomposer.last_candidates) >= 2
    assert sum(1 for candidate in decomposer.last_candidates if candidate.selected) == 1
    assert any(candidate.strategy == "risk_trimmed_pipeline" for candidate in decomposer.last_candidates)
    assert any(candidate.strategy == "general_pipeline" for candidate in decomposer.last_candidates)


def test_mock_claude_decomposer_prefers_safer_candidate_for_migration_tasks() -> None:
    planner = MockClaudePlanner()
    decomposer = MockClaudeDecomposer()
    policy = get_policy(OrchestrationMode.SUCCESS_FIRST)
    contract = planner.clarify(
        "Plan an auth migration for the payment service without breaking existing login flows.",
        policy,
    )

    work_units = decomposer.decompose(contract, policy)

    selected = next(candidate for candidate in decomposer.last_candidates if candidate.selected)
    assert selected.strategy == "migration_pipeline"
    assert selected.score >= max(candidate.score for candidate in decomposer.last_candidates if candidate is not selected)
    assert work_units[-1].goal == "Validate merge readiness"


def test_env_slot_fill_config_reads_custom_env(monkeypatch) -> None:
    monkeypatch.setenv("AO_SLOTFILL_API_KEY", "secret-key")
    monkeypatch.setenv("AO_SLOTFILL_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("AO_SLOTFILL_MODEL", "gpt-test")

    config = EnvSlotFillConfig.from_env()

    assert config is not None
    assert config.api_key == "secret-key"
    assert config.base_url == "https://example.invalid/v1"
    assert config.model == "gpt-test"


def test_env_slot_fill_config_reads_project_env_file(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "AO_SLOTFILL_API_KEY=file-key\n"
        "AO_SLOTFILL_BASE_URL=https://file.example/v1\n"
        "AO_SLOTFILL_MODEL=file-model\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("AO_SLOTFILL_API_KEY", raising=False)
    monkeypatch.delenv("AO_SLOTFILL_BASE_URL", raising=False)
    monkeypatch.delenv("AO_SLOTFILL_MODEL", raising=False)

    config = EnvSlotFillConfig.from_env(project_root=tmp_path)

    assert config is not None
    assert config.api_key == "file-key"
    assert config.base_url == "https://file.example/v1"
    assert config.model == "file-model"


def test_env_slot_fill_config_prefers_process_env_over_project_file(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "AO_SLOTFILL_API_KEY=file-key\n"
        "AO_SLOTFILL_BASE_URL=https://file.example/v1\n"
        "AO_SLOTFILL_MODEL=file-model\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AO_SLOTFILL_API_KEY", "env-key")
    monkeypatch.setenv("AO_SLOTFILL_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("AO_SLOTFILL_MODEL", "env-model")

    config = EnvSlotFillConfig.from_env(project_root=tmp_path)

    assert config is not None
    assert config.api_key == "env-key"
    assert config.base_url == "https://env.example/v1"
    assert config.model == "env-model"


def test_openai_compatible_slot_filler_parses_structured_response() -> None:
    seen: dict[str, object] = {}

    def fake_transport(request_url: str, payload: dict[str, object], headers: dict[str, str], timeout_seconds: int) -> dict[str, object]:
        seen["url"] = request_url
        seen["payload"] = payload
        seen["headers"] = headers
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "goal": "Investigate the issue and summarize findings.",
                                "task_type": "investigation",
                                "expected_artifacts": ["analysis note", "findings", "recommendation"],
                                "acceptance_criteria": ["Describe the issue", "Provide a recommendation"],
                                "unknown_slots": ["target_scope"],
                            }
                        )
                    }
                }
            ]
        }

    filler = OpenAICompatibleSlotFiller(
        config=EnvSlotFillConfig(api_key="secret-key", base_url="https://example.invalid/v1", model="gpt-test"),
        transport=fake_transport,
    )
    result = filler(
        ContractDraft(
            raw_requirement="Look into this and tell me what is wrong.",
            goal="Look into this and tell me what is wrong.",
            missing_slots=["expected_artifacts"],
            uncertain_slots=["task_type"],
        ),
        get_policy(OrchestrationMode.COST_FIRST),
    )

    assert seen["url"] == "https://example.invalid/v1/chat/completions"
    assert seen["headers"] == {"Authorization": "Bearer secret-key", "Content-Type": "application/json"}
    assert result.filled_slots["task_type"] == "investigation"
    assert result.unknown_slots == ["target_scope"]


def test_openai_compatible_slot_filler_returns_warning_on_malformed_response() -> None:
    def fake_transport(request_url: str, payload: dict[str, object], headers: dict[str, str], timeout_seconds: int) -> dict[str, object]:
        return {"choices": [{"message": {"content": "not json"}}]}

    filler = OpenAICompatibleSlotFiller(
        config=EnvSlotFillConfig(api_key="secret-key", base_url="https://example.invalid/v1", model="gpt-test"),
        transport=fake_transport,
    )
    result = filler(
        ContractDraft(
            raw_requirement="Look into this and tell me what is wrong.",
            goal="Look into this and tell me what is wrong.",
            missing_slots=["expected_artifacts"],
            uncertain_slots=["task_type"],
        ),
        get_policy(OrchestrationMode.COST_FIRST),
    )

    assert result.filled_slots == {}
    assert result.warnings


def test_openai_compatible_slot_filler_whitelists_and_normalizes_slots() -> None:
    def fake_transport(request_url: str, payload: dict[str, object], headers: dict[str, str], timeout_seconds: int) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "task_type": "analysis",
                                "goal": "Investigate the issue.",
                                "expected_artifacts": [],
                                "constraints": ["should be ignored"],
                                "policy": {"mode": "ignored"},
                                "unknown_slots": ["target_scope", "bad_slot"],
                            }
                        )
                    }
                }
            ]
        }

    filler = OpenAICompatibleSlotFiller(
        config=EnvSlotFillConfig(api_key="secret-key", base_url="https://example.invalid/v1", model="gpt-test"),
        transport=fake_transport,
    )
    result = filler(
        ContractDraft(
            raw_requirement="Look into this and tell me what is wrong.",
            goal="Look into this and tell me what is wrong.",
            missing_slots=["expected_artifacts"],
            uncertain_slots=["task_type", "target_scope"],
        ),
        get_policy(OrchestrationMode.COST_FIRST),
    )

    assert result.filled_slots == {
        "task_type": "investigation",
        "goal": "Investigate the issue.",
    }
    assert result.unknown_slots == ["target_scope"]


def test_mock_claude_planner_ignores_invalid_slot_fill_task_type() -> None:
    def fill_slots(draft: ContractDraft, policy: object) -> SlotFillResult:
        return SlotFillResult(
            filled_slots={
                "task_type": "nonsense",
                "expected_artifacts": ["analysis note", "findings", "recommendation"],
            }
        )

    planner = MockClaudePlanner(slot_filler=fill_slots)
    policy = get_policy(OrchestrationMode.COST_FIRST)

    contract = planner.clarify("Look into this and tell me what is wrong.", policy)

    assert contract.task_type == "implementation"
    assert contract.expected_artifacts == ["analysis note", "findings", "recommendation"]


def test_openai_compatible_slot_filler_normalizes_expected_artifact_aliases() -> None:
    def fake_transport(request_url: str, payload: dict[str, object], headers: dict[str, str], timeout_seconds: int) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "task_type": "investigation",
                                "expected_artifacts": ["Investigation report", "Root cause summary", "Recommendation"],
                            }
                        )
                    }
                }
            ]
        }

    filler = OpenAICompatibleSlotFiller(
        config=EnvSlotFillConfig(api_key="secret-key", base_url="https://example.invalid/v1", model="gpt-test"),
        transport=fake_transport,
    )
    result = filler(
        ContractDraft(
            raw_requirement="Look into this and tell me what is wrong.",
            goal="Look into this and tell me what is wrong.",
            missing_slots=["expected_artifacts"],
            uncertain_slots=["task_type"],
        ),
        get_policy(OrchestrationMode.COST_FIRST),
    )

    assert result.filled_slots["expected_artifacts"] == ["analysis note", "findings", "recommendation"]
