import pytest

from agent_orchestrator import OrchestrationMode, get_policy
from agent_orchestrator.adapters import ContractDraft, MockClaudePlanner, SlotFillResult


@pytest.mark.parametrize(
    ("requirement", "filled_slots", "expected_task_type", "expected_unknown_subset"),
    [
        (
            "Look into this and tell me what is wrong.",
            {
                "task_type": "investigation",
                "expected_artifacts": ["analysis note", "findings", "recommendation"],
                "user_intent_summary": "Investigate the issue and explain what is wrong.",
            },
            "investigation",
            {"target_scope"},
        ),
        (
            "Clean this up but keep behavior the same.",
            {
                "task_type": "refactor",
                "expected_artifacts": ["patch", "tests", "validation notes"],
                "user_intent_summary": "Refactor the current implementation without changing behavior.",
            },
            "refactor",
            {"target_scope"},
        ),
        (
            "Document how this works for the team.",
            {
                "task_type": "docs",
                "expected_artifacts": ["docs patch", "validation notes"],
                "user_intent_summary": "Document the current behavior for the team.",
            },
            "docs",
            {"target_scope"},
        ),
    ],
)
def test_clarify_ambiguous_eval_cases(
    requirement: str,
    filled_slots: dict[str, object],
    expected_task_type: str,
    expected_unknown_subset: set[str],
) -> None:
    def fill_slots(draft: ContractDraft, policy: object) -> SlotFillResult:
        return SlotFillResult(filled_slots=filled_slots)

    planner = MockClaudePlanner(slot_filler=fill_slots)
    contract = planner.clarify(requirement, get_policy(OrchestrationMode.COST_FIRST))

    assert contract.task_type == expected_task_type
    assert contract.slot_sources.get("task_type") == "llm"
    assert expected_unknown_subset.issubset(set(contract.unknown_slots))
    assert contract.user_intent_summary
    assert contract.expected_artifacts


def test_clarify_ambiguous_eval_shows_rule_only_gap_without_slot_fill() -> None:
    planner = MockClaudePlanner(slot_filler=None)
    contract = planner.clarify("Look into this and tell me what is wrong.", get_policy(OrchestrationMode.COST_FIRST))

    assert contract.task_type == "implementation"
    assert "task_type" in contract.unknown_slots
    assert "target_scope" in contract.unknown_slots
