"""Read-only execution path snapshot builder for the control plane."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, pathlib
# RESPONSIBILITY: Build read-only execution path snapshots from plan sessions and control-plane artifacts.
# MODULE: decision_core
# ---

from pathlib import Path

from agent_orchestrator.control_plane_posture import (
    derive_session_continuity_outline,
    derive_session_planner_decision,
    infer_resume_posture,
)
from agent_orchestrator.control_plane_artifacts import resolve_root as _resolve_root
from agent_orchestrator.control_plane_constants import CONTROL_PLANE_FORMATS, TOPOLOGY_NODE_TYPES
from agent_orchestrator.jobs import now_iso
from agent_orchestrator.planning import PlanSession
from agent_orchestrator.work_graph import WorkGraphStore


def build_execution_topology_snapshot(
    session: PlanSession,
    *,
    plans_root: Path | str = ".agent_orchestrator/plans",
    approvals_root: Path | str = ".agent_orchestrator/approvals",
    project_root: Path | str = ".",
) -> dict[str, object]:
    from agent_orchestrator.control_plane import (
        WorkspaceIndexStore,
        build_approval_queue,
        build_evidence_bundle,
        build_run_ledger,
        build_strategy_decision,
    )

    root = Path(project_root)
    plans_path = _resolve_root(root, plans_root)
    approvals_path = _resolve_root(root, approvals_root)
    approvals = build_approval_queue(root, plans_root=plans_path, approvals_root=approvals_path, sessions=[session])
    evidence_bundle = build_evidence_bundle(project_root)
    run_ledger = build_run_ledger(
        root,
        plans_root=plans_path,
        runs_root=root / ".agent_orchestrator" / "runs",
        jobs_root=root / ".agent_orchestrator" / "jobs",
        approvals_root=approvals_path,
        sessions=[session],
    )
    strategy = build_strategy_decision(session)
    strategy["approval_counts"] = approvals.get("counts", {})
    strategy["run_ledger_ref"] = {
        "format": run_ledger.get("format"),
        "entry_count": run_ledger.get("summary", {}).get("entry_count")
        if isinstance(run_ledger.get("summary"), dict)
        else 0,
    }
    session_planner_decision = derive_session_planner_decision(strategy)
    topology_resume_kind = (
        "approval_resume"
        if bool(session_planner_decision.get("autonomy_posture", {}).get("approval_pause_state"))
        else "fresh"
        if session.status in {"drafting", "review_pending", "planned"}
        else "resume_if_same_task"
    )
    session_continuity_outline = derive_session_continuity_outline(
        strategy,
        resume_kind=topology_resume_kind,
        resume_posture=infer_resume_posture(
            current_status=session.status,
            human_required=bool(session_planner_decision.get("autonomy_posture", {}).get("approval_pause_state")),
            resume_expectation=session_planner_decision.get("delegation_contract", {}).get("resume_expectation"),
            resume_kind=topology_resume_kind,
        ),
    )
    graph = WorkGraphStore(root=plans_path).read_optional(session.id)
    nodes: list[dict[str, object]] = [
        _topology_node("state", "workspace-state", "Workspace state", session.status),
        _topology_node("context", "context-packet", "Context packet", "available"),
        _topology_node(
            "strategy",
            "strategy-decision",
            str(strategy.get("current_checkpoint_objective") or strategy.get("next_goal")),
            "ready",
        ),
        _topology_node("manager_slot", "manager-policy", "Manager policy slot", session.status),
    ]
    if graph is not None:
        for node in graph.nodes:
            if node.kind == "subtask":
                nodes.append(_topology_node("worker", node.id, node.title, node.status, owner_role=node.owner_role))
            elif node.kind in {"review_round", "review"}:
                nodes.append(_topology_node("review", node.id, node.title, node.status, owner_role=node.owner_role))
            elif node.kind == "gap":
                nodes.append(_topology_node("approval", node.id, node.title, node.status, owner_role=node.owner_role))
    for round_ in session.review_rounds:
        nodes.append(_topology_node("review", round_.id, round_.summary or round_.round_type, "completed", owner_role=round_.role))
    for item in approvals["items"]:
        if isinstance(item, dict) and item.get("session_id") == session.id:
            nodes.append(_topology_node("approval", str(item.get("id")), str(item.get("reason")), str(item.get("status"))))
    nodes.append(_topology_node("evidence", "evidence-bundle", "Evidence gates", str(evidence_bundle.get("status"))))
    nodes.append(_topology_node("memory", "memory-records", "Memory provenance", "available"))

    edges = [
        {"from": "workspace-state", "to": "context-packet"},
        {"from": "context-packet", "to": "strategy-decision"},
        {"from": "strategy-decision", "to": "manager-policy"},
    ]
    for node in nodes:
        node_id = str(node.get("id"))
        if node_id not in {"workspace-state", "context-packet", "strategy-decision", "manager-policy"}:
            edges.append({"from": "manager-policy", "to": node_id})
    execution_contract = (
        session.approved_plan.get("execution_contract", {})
        if isinstance(session.approved_plan, dict) and isinstance(session.approved_plan.get("execution_contract"), dict)
        else {}
    )
    payload = {
        "format": CONTROL_PLANE_FORMATS["topology_snapshot"],
        "session_id": session.id,
        "fixed_node_types": list(TOPOLOGY_NODE_TYPES),
        "blueprint": _topology_blueprint(session, nodes, edges, approvals, evidence_bundle),
        "nodes": nodes,
        "edges": edges,
        "lanes": _topology_lanes(nodes),
        "approval_points": _topology_points(nodes, "approval"),
        "evidence_points": _topology_points(nodes, "evidence"),
        "runtime_boundaries": _topology_runtime_boundaries(session),
        "program_posture": strategy.get("program_posture", {}),
        "delegation_contract": strategy.get("delegation_contract", {}),
        "milestone_verification": strategy.get("milestone_verification", {}),
        "operator_control": strategy.get("operator_control", {}),
        "session_planner_decision": session_planner_decision,
        "session_continuity_outline": session_continuity_outline,
        "strategy_decision": strategy,
        "execution_contract": execution_contract,
        "approval_queue": approvals,
        "run_ledger": run_ledger,
        "evidence_bundle": evidence_bundle,
        "read_only": True,
        "created_at": now_iso(),
    }
    index = WorkspaceIndexStore(root / ".agent_orchestrator" / "workspace")
    index.record_artifact("strategy_decision", strategy)
    index.record_artifact("topology_snapshot", payload)
    return payload


def _topology_node(
    node_type: str,
    node_id: str,
    label: str,
    status: str,
    *,
    owner_role: str | None = None,
) -> dict[str, object]:
    return {
        "id": node_id,
        "type": node_type,
        "label": label,
        "status": status,
        "owner_role": owner_role,
    }


def _topology_blueprint(
    session: PlanSession,
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
    approvals: dict[str, object],
    evidence_bundle: dict[str, object],
) -> dict[str, object]:
    return {
        "id": f"blueprint:{session.id}",
        "name": session.structured_brief.goal or session.requirement,
        "read_only": True,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "approval_count": approvals.get("counts", {}).get("pending", 0)
        if isinstance(approvals.get("counts"), dict)
        else 0,
        "evidence_status": evidence_bundle.get("status"),
        "export_policy": "snapshot only; topology editing is out of scope",
    }


def _topology_lanes(nodes: list[dict[str, object]]) -> list[dict[str, object]]:
    lane_order = ["control_plane", "execution", "review", "approval", "evidence_memory"]
    lane_map = {
        "state": "control_plane",
        "context": "control_plane",
        "strategy": "control_plane",
        "manager_slot": "control_plane",
        "worker": "execution",
        "implementation": "execution",
        "rescue": "execution",
        "condition": "execution",
        "review": "review",
        "approval": "approval",
        "evidence": "evidence_memory",
        "memory": "evidence_memory",
    }
    grouped: dict[str, list[str]] = {lane: [] for lane in lane_order}
    for node in nodes:
        node_type = str(node.get("type") or "")
        lane = lane_map.get(node_type, "execution")
        grouped.setdefault(lane, []).append(str(node.get("id")))
    return [{"id": lane, "node_ids": grouped.get(lane, [])} for lane in lane_order if grouped.get(lane)]


def _topology_points(nodes: list[dict[str, object]], node_type: str) -> list[dict[str, object]]:
    return [
        {"node_id": node.get("id"), "status": node.get("status"), "label": node.get("label")}
        for node in nodes
        if node.get("type") == node_type
    ]


def _topology_runtime_boundaries(session: PlanSession) -> list[dict[str, object]]:
    provider_runtime = session.decision_verdict.selected_provider_runtime if session.decision_verdict else {}
    return [
        {
            "boundary": "strategy_to_execution",
            "executes": False,
            "authority": "approved_plan_gate",
        },
        {
            "boundary": "provider_runtime",
            "selected_provider_runtime": provider_runtime,
            "policy": "runtime executes below the control plane",
        },
    ]
