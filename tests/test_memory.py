from agent_orchestrator import Orchestrator
from agent_orchestrator.memory import KnowledgeStore, MemoryStore
from agent_orchestrator.planning import PlanStore, TeamOrchestrator


def test_memory_store_appends_and_queries_records(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory")

    store.append(
        namespace="plan_session",
        session_id="plan-1",
        record_type="session_snapshot",
        role="lead",
        provider="decision_core",
        summary="snapshot",
    )
    store.append(
        namespace="operator_action",
        session_id="plan-1",
        record_type="action",
        role="lead",
        provider="dashboard",
        summary="execute",
    )

    assert len(store.query(session_id="plan-1")) == 2
    assert store.query(namespace="operator_action")[0]["summary"] == "execute"
    assert store.query(provider="decision_core")[0]["record_type"] == "session_snapshot"


def test_memory_store_search_scores_summary_and_payload(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory")
    store.append(
        namespace="postmortem",
        session_id="plan-1",
        record_type="postmortem",
        summary="Dashboard execution failed because provider auth expired",
        payload={"provider": "claude"},
    )
    store.append(
        namespace="plan_session",
        session_id="plan-2",
        record_type="session_snapshot",
        summary="Unrelated work",
    )

    results = store.search("dashboard provider auth")

    assert len(results) == 1
    assert results[0]["session_id"] == "plan-1"


def test_plan_store_writes_session_snapshot_memory(tmp_path) -> None:
    team = TeamOrchestrator(
        orchestrator=Orchestrator(),
        store=PlanStore(root=tmp_path / "plans"),
        project_root=tmp_path,
    )

    session = team.start("Build a persisted plan artifact")
    records = MemoryStore(tmp_path / "memory").query(session_id=session.id)

    assert records
    assert any(record["record_type"] == "session_snapshot" for record in records)


def test_knowledge_store_appends_type_scoped_jsonl(tmp_path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge")

    store.append(session_id="plan-1", artifact_type="decisions", summary="approved", payload={"status": "approved"})
    store.append(session_id="plan-1", artifact_type="lessons", summary="validated")

    records = store.query(session_id="plan-1")

    assert {record["artifact_type"] for record in records} == {"decisions", "lessons"}
    assert (tmp_path / "knowledge" / "decisions.jsonl").exists()


def test_memory_store_can_query_native_learning_assets_by_namespace_and_type(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory")
    store.append(
        namespace="native_trajectory",
        session_id="session-1",
        record_type="trajectory",
        summary="verify_failure_repair_resume_success",
        payload={"task_class": "bounded_internal_repo_task"},
    )
    store.append(
        namespace="native_learning",
        session_id="session-1",
        record_type="memory",
        summary="bounded edits default to native path",
        payload={"fallback_reason_code": "native_runtime_unavailable"},
    )

    assert store.query(namespace="native_trajectory")[0]["record_type"] == "trajectory"
    assert store.query(record_type="memory")[0]["namespace"] == "native_learning"
    assert store.search("bounded native path")[0]["namespace"] == "native_learning"


def test_router_can_consume_native_learning_assets(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory")
    store.append(
        namespace="native_trajectory",
        session_id="session-2",
        record_type="trajectory",
        summary="investigation to edit verify",
        payload={"path_selection": {"default_path": "native"}},
    )
    router = __import__("agent_orchestrator.intake.task_router", fromlist=["TaskRouter"]).TaskRouter()
    router.native_learning_store = store

    result = router.route("Investigate why the queue stalls and summarize the root cause.")

    assert result.default_path == "native"
    assert result.learning_consumed is True
    assert result.native_coverage_class == "investigation_to_edit_verify"
