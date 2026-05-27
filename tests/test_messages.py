from agent_orchestrator import Orchestrator
from agent_orchestrator.jobs import FileJobRuntime
from agent_orchestrator.messages import MessageRouter, MessageStore, build_direct_api_tool_trace_payload
from agent_orchestrator.planning import PlanStore, TeamOrchestrator


def test_message_store_appends_and_queries_by_session_and_role(tmp_path) -> None:
    store = MessageStore(tmp_path / "messages")

    first = store.create(
        session_id="plan-1",
        from_role="lead",
        to_role="reviewer",
        message_type="review_request",
        content="please review",
        requires_response=True,
    )
    store.create(
        session_id="plan-1",
        from_role="reviewer",
        to_role="lead",
        message_type="review_result",
        content="approved",
    )

    assert first.id.startswith("msg-")
    assert len(store.list_for_session("plan-1")) == 2
    assert store.query(session_id="plan-1", to_role="reviewer")[0]["content"] == "please review"
    assert store.list_for_role("plan-1", "lead", direction="outbox")[0]["message_type"] == "review_request"
    assert store.list_for_session("plan-1")[0]["thread"] == "main"


def test_message_router_builds_review_request_result_and_handoff(tmp_path) -> None:
    router = MessageRouter(MessageStore(tmp_path / "messages"))

    request = router.build_review_request(session_id="plan-1", to_role="reviewer", content="review")
    result = router.build_review_result(session_id="plan-1", from_role="reviewer", content="done")
    handoff = router.build_handoff(session_id="plan-1", from_role="lead", to_role="runtime", content="execute")

    assert request.requires_response is True
    assert result.to_role == "lead"
    assert handoff.message_type == "handoff"
    assert request.thread == "review"
    assert result.thread == "review"
    assert handoff.thread == "main"
    packet = handoff.payload["handoff_packet"]
    assert packet["format"] == "agent_orchestrator.handoff_packet.v1"
    assert packet["summary"] == "execute"
    assert packet["from_role"] == "lead"
    assert packet["to_role"] == "runtime"


def test_message_router_accepts_explicit_handoff_packet(tmp_path) -> None:
    router = MessageRouter(MessageStore(tmp_path / "messages"))

    handoff = router.build_handoff(
        session_id="plan-1",
        from_role="lead",
        to_role="runtime",
        content="execute",
        handoff_packet={
            "summary": "Execute approved plan",
            "changes": ["src/example.py"],
            "evidence": ["pytest tests/test_example.py"],
            "risks": [],
            "blockers": [],
            "docs_context_snapshot_id": "docsctx-123",
            "recommended_commands": ["python -m agent_orchestrator.cli team inspect-execution plan-1"],
        },
    )

    packet = handoff.payload["handoff_packet"]
    assert packet["format"] == "agent_orchestrator.handoff_packet.v1"
    assert packet["session_id"] == "plan-1"
    assert packet["docs_context_snapshot_id"] == "docsctx-123"
    assert packet["recommended_commands"] == ["python -m agent_orchestrator.cli team inspect-execution plan-1"]


def test_direct_api_tool_trace_records_intent_without_execution(tmp_path) -> None:
    router = MessageRouter(MessageStore(tmp_path / "messages"))

    trace = router.build_direct_api_tool_trace(
        session_id="plan-1",
        provider="claude",
        tool_name="summarize_evidence",
        intent="Summarize gate evidence",
        result="Evidence summarized",
        fallback={"fallback_from": "claude", "fallback_reason": "timeout"},
    )
    payload = build_direct_api_tool_trace_payload(
        provider="codex",
        tool_name="review_plan",
        intent="Review plan",
    )

    assert trace.message_type == "direct_api_tool_trace"
    assert trace.thread == "governance"
    assert trace.payload["format"] == "agent_orchestrator.direct_api_tool_trace.v1"
    assert trace.payload["execution_policy"].startswith("record intent and result only")
    assert trace.payload["fallback"]["fallback_reason"] == "timeout"
    assert trace.payload["usage_cost"]["source"] == "placeholder"
    assert payload["runtime_mode"] == "direct_api"


def test_team_start_writes_review_messages_and_job_metadata(tmp_path) -> None:
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        runtime=FileJobRuntime(root=tmp_path / "jobs"),
        project_root=tmp_path,
    )

    session = team.start("Build a persisted plan artifact")
    session = team.mark_draft_ready(session.id)
    session = team.submit_draft_for_review(session.id)
    store = MessageStore(tmp_path / "messages")
    messages = store.list_for_session(session.id)
    review_requests = [message for message in messages if message["message_type"] == "review_request"]
    review_results = [message for message in messages if message["message_type"] == "review_result"]

    assert len(review_requests) == 2
    assert len(review_results) == 2
    assert {message["thread"] for message in review_requests} == {"review"}
    assert {message["to_role"] for message in review_requests} == {"reviewer", "adversarial_reviewer"}

    jobs = team.runtime.list_recent()
    review_jobs = [job for job in jobs if job.kind in {"review", "adversarial_review"}]

    assert review_jobs
    assert all(job.metadata.get("message_ids") for job in review_jobs)
    assert all(job.metadata.get("work_unit_id") == session.id for job in review_jobs)
