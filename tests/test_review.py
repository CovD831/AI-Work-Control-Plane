import pytest

from agent_orchestrator.review import Finding, ReviewResult
from agent_orchestrator.planning import DecisionVerdict


def test_review_result_can_approve_without_findings() -> None:
    result = ReviewResult(verdict="approve", summary="Looks good.")

    assert result.to_dict() == {
        "verdict": "approve",
        "summary": "Looks good.",
        "findings": [],
        "next_steps": [],
    }


def test_review_result_can_request_attention_with_findings() -> None:
    finding = Finding(
        severity="high",
        title="Missing validation",
        body="Input reaches storage without validation.",
        file="src/app.py",
        line_start=10,
        line_end=12,
        confidence=0.9,
        recommendation="Validate input before persistence.",
    )
    result = ReviewResult(
        verdict="needs_attention",
        summary="One issue found.",
        findings=[finding],
        next_steps=["Route to rescue if policy allows."],
    )

    assert result.to_dict()["findings"][0]["severity"] == "high"


def test_review_result_rejects_invalid_verdict_findings_combination() -> None:
    finding = Finding(
        severity="low",
        title="Tiny issue",
        body="Issue body.",
        file="src/app.py",
        line_start=1,
        line_end=1,
        confidence=0.5,
        recommendation="Fix later.",
    )

    with pytest.raises(ValueError):
        ReviewResult(verdict="approve", summary="Approved?", findings=[finding])

    with pytest.raises(ValueError):
        ReviewResult(verdict="needs_attention", summary="Missing findings.")


def test_decision_verdict_round_trip_preserves_review_summary() -> None:
    verdict = DecisionVerdict(
        approval_status="approved",
        required_gaps=[],
        followup_gaps=[],
        selected_topology="team",
        selected_provider_runtime={"reviewer": "claude"},
        rationale=["review completed"],
        review_summary={
            "review_roles": ["review", "review"],
            "review_round_count": 2,
            "blocking_review_count": 1,
            "non_blocking_review_count": 1,
            "aggregate_verdict": "needs_attention",
            "severity_counts": {"low": 0, "medium": 1, "high": 0, "critical": 0},
            "reviews": [{"role": "review", "verdict": "needs_attention"}],
        },
    )

    restored = DecisionVerdict.from_dict(verdict.to_dict())

    assert restored.review_summary["aggregate_verdict"] == "needs_attention"
    assert restored.review_summary["review_round_count"] == 2
