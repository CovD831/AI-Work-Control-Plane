"""Service helpers for the local governance console."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, json, pathlib, typing
# RESPONSIBILITY: Build structured dashboard payloads from persisted plan, run, and job stores.
# MODULE: interface
# ---

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_orchestrator.actions import assert_session_action_allowed, build_session_actions, primary_action_from_registry
from agent_orchestrator.agent_config import AgentConfig, AgentConfigStore
from agent_orchestrator.command import ProviderHealthCheck
from agent_orchestrator.control_plane import (
    build_approval_queue,
    build_evidence_bundle,
    build_execution_topology_snapshot,
    build_provider_session_snapshot,
    build_workspace_index,
    build_workspace_state_snapshot,
)
from agent_orchestrator.control_plane_posture import (
    derive_planner_closure_posture_summary,
    derive_session_continuity_outline_summary,
    derive_session_planner_decision_summary,
)
from agent_orchestrator.events import EventStore
from agent_orchestrator.execution.models import (
    derive_adapter_capability_summary,
    derive_adapter_productization_surface,
)
from agent_orchestrator.jobs import FileJobRuntime
from agent_orchestrator.native_productization import build_product_ux_snapshot, build_rc_adoption_report, build_release_candidate_report, build_release_operator_bundle, run_rc_adoption
from agent_orchestrator.memory import MemoryStore
from agent_orchestrator.messages import MessageStore
from agent_orchestrator.planning import TeamOrchestrator, build_operator_runbook
from agent_orchestrator.planning_governance import get_governance_status
from agent_orchestrator.policies import OrchestrationMode
from agent_orchestrator.productization_surface import (
    build_comparative_adapter_summary,
    build_comparative_completion_summary,
    build_comparative_daily_driver_summary,
    build_comparative_native_closure_summary,
    build_comparative_native_tool_summary,
    build_comparative_planner_candidate_summary,
    build_comparative_planner_autonomy_summary,
    build_comparative_session_continuity_summary,
    build_comparative_session_posture_summary,
    build_comparative_daily_driver_benchmark,
    build_runtime_comparative_benchmark_digest,
    build_shared_productization_surface,
    derive_approval_boundary_digest,
    derive_clarify_boundary_digest,
    derive_operator_planner_digest,
    derive_operator_tool_digest,
    derive_native_tool_productization_surface,
)
from agent_orchestrator.roles import DEFAULT_AGENT_ROLES, get_agent_role, role_for_job_kind
from agent_orchestrator.run_store import RunStore
from agent_orchestrator.session.productization import derive_session_productization_surface
from agent_orchestrator.tmux_runtime import TmuxJobRuntime
from agent_orchestrator.work_graph import WorkGraphStore, WorkUnitGraph, graph_to_plan_tree, schedulable_nodes


TIMELINE_STEPS = [
    ("intake_chat", "沟通"),
    ("draft_ready", "初稿"),
    ("adversarial_review", "风险挑战"),
    ("awaiting_human_confirmation", "确认"),
    ("needs_revision", "修订"),
    ("approved_for_execution", "已批准"),
    ("executing", "执行"),
    ("accepted", "验收"),
]

ROLE_GROUPS = [
    ("control_plane", "控制平面层"),
    ("decision", "治理层"),
    ("execution", "执行层"),
    ("review", "质量门禁层"),
    ("rescue", "恢复层"),
    ("runtime", "运行时层"),
]


class DashboardService:
    def __init__(
        self,
        *,
        team: TeamOrchestrator,
        plans_root: Path | str = ".agent_orchestrator/plans",
        runs_root: Path | str = ".agent_orchestrator/runs",
        jobs_root: Path | str = ".agent_orchestrator/jobs",
        health_check: ProviderHealthCheck | None = None,
        job_runtime: FileJobRuntime | None = None,
    ) -> None:
        self.team = team
        self.plans_root = Path(plans_root)
        self.runs_root = Path(runs_root)
        self.jobs_root = Path(jobs_root)
        self.project_root = Path(getattr(team, "project_root", Path.cwd()))
        self.run_store = RunStore(root=self.runs_root)
        self.job_runtime = job_runtime or FileJobRuntime(root=self.jobs_root)
        self.event_store = EventStore(root=self.plans_root.parent / "events")
        self.memory_store = MemoryStore(root=self.plans_root.parent / "memory")
        self.message_store = MessageStore(root=self.plans_root.parent / "messages")
        self.health_check = health_check or ProviderHealthCheck(use_cache=True)
        self.agent_config_store = AgentConfigStore(self.plans_root.parent / "agent-config.json")
        self.team.agent_config = self.agent_config_store.read()
        _apply_agent_config_to_orchestrator(self.team.orchestrator, self.team.agent_config)

    def health(self) -> dict[str, object]:
        providers = [self.health_check.check(provider).to_dict() for provider in ("codex", "claude")]
        providers.append({"provider": "mock", "available": True, "detail": "mock provider is always available"})
        provider_health = {"providers": providers, "runtime_modes": [], "direct_api_auth": []}
        product_ux = build_product_ux_snapshot(
            provider_health_snapshot=provider_health,
            runs_root=self.runs_root,
            project_root=self.project_root,
        )
        return {
            "providers": providers,
            "job_runtime": self.job_runtime.__class__.__name__,
            "native_product_ux": product_ux,
            "release_candidate": product_ux.get("release_candidate", {}) if isinstance(product_ux, dict) else {},
            "release_bundle": product_ux.get("release_bundle", {}) if isinstance(product_ux, dict) else {},
            "native_rc_adoption": product_ux.get("native_rc_adoption", {}) if isinstance(product_ux, dict) else {},
        }

    def get_agent_config(self) -> dict[str, object]:
        return self.agent_config_store.read().to_dict()

    def update_agent_config(self, payload: dict[str, object]) -> dict[str, object]:
        config = AgentConfig.from_dict(payload)
        self.agent_config_store.write(config)
        self.team.agent_config = config
        _apply_agent_config_to_orchestrator(self.team.orchestrator, config)
        return config.to_dict()

    def list_sessions(self) -> dict[str, object]:
        sessions = []
        for path in sorted(self.plans_root.glob("*/session.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            payload = _read_json(path)
            if not isinstance(payload, dict):
                continue
            sessions.append(_session_list_item(payload, path))
        return {"sessions": sessions}

    def get_session(self, session_id: str) -> dict[str, object]:
        session = self.team.status(session_id)
        payload = session.to_dict()
        linked_run = None
        run_id = session.resume.linked_execution_run_id
        if run_id and self.run_store.exists(run_id):
            linked_run = self.run_store.read(run_id)
        graph = WorkGraphStore(self.plans_root).read_optional(session_id)
        messages = self.message_store.list_for_session(session_id, limit=50)
        workspace_state = build_workspace_state_snapshot(
            self.project_root,
            plans_root=self.plans_root,
            runs_root=self.runs_root,
            jobs_root=self.jobs_root,
            approvals_root=self.plans_root.parent / "approvals",
            write_index=False,
        )
        workspace_index = build_workspace_index(
            self.project_root,
            plans_root=self.plans_root,
            runs_root=self.runs_root,
            jobs_root=self.jobs_root,
            approvals_root=self.plans_root.parent / "approvals",
        )
        topology_snapshot = build_execution_topology_snapshot(
            session,
            plans_root=self.plans_root,
            approvals_root=self.plans_root.parent / "approvals",
            project_root=self.project_root,
        )
        approval_queue = build_approval_queue(
            self.project_root,
            plans_root=self.plans_root,
            approvals_root=self.plans_root.parent / "approvals",
            sessions=[session],
        )
        evidence_bundle = build_evidence_bundle(
            self.project_root,
            compliance=session.compliance if isinstance(session.compliance, dict) else None,
        )
        product_ux = build_product_ux_snapshot(
            runs_root=self.runs_root,
            project_root=self.project_root,
        )
        release_candidate = build_release_candidate_report(runs_root=self.runs_root, project_root=self.project_root)
        release_bundle = build_release_operator_bundle(runs_root=self.runs_root, project_root=self.project_root)
        native_rc_adoption = build_rc_adoption_report(run_rc_adoption(runs_root=self.runs_root, project_root=self.project_root, dry_run=True)).get("summary", {})
        return {
            "session": payload,
            "timeline": _build_timeline(payload),
            "plan_tree": graph_to_plan_tree(graph) if graph else _build_plan_tree(payload, linked_run),
            "work_graph": _work_graph_payload(graph) if graph else None,
            "evidence_summary": _build_evidence_summary(payload, linked_run, self.memory_store.query(session_id=session_id, limit=20)),
            "next_action": _build_next_action(payload),
            "actions": build_session_actions(payload),
            "events": self.event_store.list_for_session(session_id, limit=20),
            "messages": _build_message_summary(messages),
            "runbook": build_operator_runbook(session),
            "agent_cards": _build_agent_cards(payload),
            "role_groups": _build_role_groups(payload, graph, messages),
            "governance_summary": _build_governance_summary(payload),
            "operator_summary": _build_operator_summary(payload, linked_run, graph, messages, workspace_index, product_ux),
            "native_product_ux": product_ux,
            "native_release_candidate": release_candidate,
            "native_release_bundle": release_bundle,
            "native_rc_adoption": native_rc_adoption,
            "control_plane": {
                "read_only": True,
                "workspace_index": workspace_index,
                "workspace_state": workspace_state,
                "strategy_decision": topology_snapshot.get("strategy_decision", {}),
                "topology_snapshot": topology_snapshot,
                "approval_queue": approval_queue,
                "evidence_bundle": evidence_bundle,
            },
            "linked_execution": linked_run,
        }

    def create_session(self, requirement: str) -> dict[str, object]:
        payload = self.team.start(requirement).to_dict()
        self._record_action("create_session", str(payload.get("id")), payload)
        return payload

    def chat_with_lead(self, session_id: str, *, message: str) -> dict[str, object]:
        assert_session_action_allowed(self.team.status(session_id).to_dict(), "lead_chat", {"message": message})
        payload = self.team.chat_with_lead(session_id, message=message).to_dict()
        self._record_action("lead_chat", session_id, payload)
        return payload

    def mark_draft_ready(self, session_id: str) -> dict[str, object]:
        assert_session_action_allowed(self.team.status(session_id).to_dict(), "mark_draft_ready")
        payload = self.team.mark_draft_ready(session_id).to_dict()
        self._record_action("mark_draft_ready", session_id, payload)
        return payload

    def submit_draft_for_review(self, session_id: str) -> dict[str, object]:
        assert_session_action_allowed(self.team.status(session_id).to_dict(), "submit_review")
        payload = self.team.submit_draft_for_review(session_id).to_dict()
        self._record_action("submit_review", session_id, payload)
        return payload

    def create_ideation_session(self, requirement: str) -> dict[str, object]:
        payload = self.team.ideate(requirement).to_dict()
        self._record_action("ideate", str(payload.get("id")), payload)
        return payload

    def revise_session(self, session_id: str, *, summary: str, closed_gap_ids: list[str] | None = None) -> dict[str, object]:
        assert_session_action_allowed(
            self.team.status(session_id).to_dict(),
            "revise",
            {"summary": summary, "closed_gap_ids": closed_gap_ids or []},
        )
        payload = self.team.revise(session_id, summary=summary, closed_gap_ids=closed_gap_ids or []).to_dict()
        self._record_action("revise", session_id, payload)
        return payload

    def approve_session(self, session_id: str) -> dict[str, object]:
        assert_session_action_allowed(self.team.status(session_id).to_dict(), "approve")
        payload = self.team.approve(session_id).to_dict()
        self._record_action("approve", session_id, payload)
        return payload

    def execute_session(self, session_id: str, *, mode: str | None = None) -> dict[str, object]:
        assert_session_action_allowed(self.team.status(session_id).to_dict(), "execute", {"mode": mode} if mode else {})
        selected_mode = None if mode in {None, "auto"} else OrchestrationMode(str(mode))
        payload = self.team.execute(session_id, selected_mode, execution_mode="native").to_dict()
        self._record_action("execute", session_id, payload)
        return payload

    def retry_review(self, session_id: str) -> dict[str, object]:
        assert_session_action_allowed(self.team.status(session_id).to_dict(), "retry_review")
        payload = self.team.retry_review(session_id).to_dict()
        self._record_action("retry_review", session_id, payload)
        return payload

    def retry_adversarial_review(self, session_id: str) -> dict[str, object]:
        assert_session_action_allowed(self.team.status(session_id).to_dict(), "retry_adversarial_review")
        payload = self.team.retry_adversarial_review(session_id).to_dict()
        self._record_action("retry_adversarial_review", session_id, payload)
        return payload

    def resume_session(self, session_id: str, *, apply: bool = False) -> dict[str, object]:
        assert_session_action_allowed(self.team.status(session_id).to_dict(), "resume")
        payload = self.team.resume(session_id, apply=apply).to_dict()
        self._record_action("resume", session_id, payload)
        return payload

    def list_events(self, *, limit: int = 100) -> dict[str, object]:
        return {"events": self.event_store.list_recent(limit=limit)}

    def list_session_events(self, session_id: str, *, limit: int = 100) -> dict[str, object]:
        return {"events": self.event_store.list_for_session(session_id, limit=limit)}

    def list_memory(self, *, limit: int = 100) -> dict[str, object]:
        return {"records": self.memory_store.query(limit=limit)}

    def list_session_memory(self, session_id: str, *, limit: int = 100) -> dict[str, object]:
        return {"records": self.memory_store.query(session_id=session_id, limit=limit)}

    def search_memory(self, query: str, *, session_id: str | None = None, limit: int = 5) -> dict[str, object]:
        return {"records": self.memory_store.search(query, session_id=session_id, limit=limit)}

    def list_messages(self, *, limit: int = 100) -> dict[str, object]:
        return {"messages": self.message_store.query(limit=limit)}

    def list_session_messages(self, session_id: str, *, limit: int = 100) -> dict[str, object]:
        return {"messages": self.message_store.list_for_session(session_id, limit=limit)}

    def get_run(self, run_id: str) -> dict[str, object]:
        return self.run_store.read(run_id)

    def list_jobs(self) -> dict[str, object]:
        return {"jobs": [_job_card(job.to_dict(), self.jobs_root) for job in self.job_runtime.list_recent()]}

    def get_job(self, job_id: str) -> dict[str, object]:
        card = _job_card(self.job_runtime.status(job_id).to_dict(), self.jobs_root)
        card["runtime_fidelity"] = build_provider_session_snapshot(job_id, Path.cwd(), jobs_root=self.jobs_root)
        return card

    def get_job_log(self, job_id: str) -> dict[str, object]:
        path = self.jobs_root / f"{job_id}.log"
        return {"job_id": job_id, "log": path.read_text(encoding="utf-8") if path.exists() else ""}

    def get_job_terminal_snapshot(self, job_id: str) -> dict[str, object]:
        job = self.job_runtime.status(job_id)
        card = _job_card(job.to_dict(), self.jobs_root)
        return {
            "job_id": card["id"],
            "status": card["status"],
            "phase": card["phase"],
            "provider": card["provider"],
            "model": card["model"],
            "kind": card["kind"],
            "terminal_ref": card["terminal_ref"],
            "attach_available": card["attach_available"],
            "stdout": card["stdout"] or "",
            "summary": card["summary"],
            "last_seen_at": card["last_seen_at"],
        }

    def send_job(self, job_id: str, message: str) -> dict[str, object]:
        try:
            return _job_card(self.job_runtime.send(job_id, message).to_dict(), self.jobs_root)
        except KeyError:
            return _missing_job_operation(job_id, "send")

    def send_job_terminal_input(self, job_id: str, message: str) -> dict[str, object]:
        return self.send_job(job_id, message)

    def cancel_job(self, job_id: str) -> dict[str, object]:
        try:
            return _job_card(self.job_runtime.cancel(job_id).to_dict(), self.jobs_root)
        except KeyError:
            return _missing_job_operation(job_id, "cancel")

    def reconnect_job_terminal(self, job_id: str) -> dict[str, object]:
        return self.get_job_terminal_snapshot(job_id)

    def _record_action(self, action: str, session_id: str, payload: dict[str, object]) -> None:
        self.event_store.append(
            type="action.completed",
            scope="session",
            scope_id=session_id,
            message=f"Dashboard action {action} completed for {session_id}.",
            payload={"session_id": session_id, "action": action, "status": payload.get("status")},
        )
        self.memory_store.append(
            namespace="operator_action",
            session_id=session_id,
            record_type="action",
            role="lead",
            provider="dashboard",
            summary=f"Action {action} completed with status {payload.get('status')}.",
            payload={"action": action, "status": payload.get("status")},
        )


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _apply_agent_config_to_orchestrator(orchestrator: Any, config: AgentConfig) -> None:
    for adapter in (getattr(orchestrator, "worker", None), getattr(orchestrator, "reviewer", None)):
        if hasattr(adapter, "agent_config"):
            adapter.agent_config = config


def _work_graph_payload(graph: WorkUnitGraph) -> dict[str, object]:
    payload = graph.to_dict()
    payload["schedulable_nodes"] = schedulable_nodes(graph)
    return payload


def _session_list_item(payload: dict[str, object], path: Path) -> dict[str, object]:
    summary = get_governance_status(payload)
    resume = payload.get("resume", {}) if isinstance(payload.get("resume"), dict) else {}
    brief = payload.get("structured_brief", {}) if isinstance(payload.get("structured_brief"), dict) else {}
    return {
        "id": payload.get("id"),
        "requirement": payload.get("requirement"),
        "goal": brief.get("goal") or payload.get("requirement"),
        "status": payload.get("status"),
        "phase": summary.get("phase") or resume.get("current_phase"),
        "primary_action": summary.get("primary_action"),
        "updated_at": path.stat().st_mtime,
        "linked_execution_run_id": resume.get("linked_execution_run_id"),
    }


def _build_next_action(payload: dict[str, object]) -> dict[str, object]:
    return primary_action_from_registry(payload)


def _build_timeline(payload: dict[str, object]) -> list[dict[str, object]]:
    status = str(payload.get("status", "drafting"))
    resume = payload.get("resume", {}) if isinstance(payload.get("resume"), dict) else {}
    phase = str(resume.get("current_phase") or status)
    if status in {"blocked", "awaiting_human", "needs_followup"}:
        extra_label = status.replace("_", " ").title()
        steps = [*TIMELINE_STEPS, (status, extra_label)]
    else:
        steps = TIMELINE_STEPS
    active_index = next((index for index, (key, _) in enumerate(steps) if key in {status, phase}), 0)
    return [
        {
            "key": key,
            "label": label,
            "state": "active" if index == active_index else "done" if index < active_index else "pending",
        }
        for index, (key, label) in enumerate(steps)
    ]


def _build_plan_tree(payload: dict[str, object], linked_run: dict[str, object] | None) -> dict[str, object]:
    brief = payload.get("structured_brief", {}) if isinstance(payload.get("structured_brief"), dict) else {}
    subtasks = brief.get("subtasks", []) if isinstance(brief.get("subtasks"), list) else []
    gaps = payload.get("gaps", []) if isinstance(payload.get("gaps"), list) else []
    rounds = payload.get("review_rounds", []) if isinstance(payload.get("review_rounds"), list) else []
    status = str(payload.get("status") or "unknown")
    root = {
        "id": str(payload.get("id") or "session"),
        "label": brief.get("goal") or payload.get("requirement") or "当前计划",
        "kind": "session",
        "status": status,
        "state": _node_state(status),
        "summary": payload.get("requirement") or "",
        "related_agent_ids": [card.get("id") for card in _build_agent_cards(payload) if card.get("id")],
        "children": [],
    }

    children: list[dict[str, object]] = []
    children.extend(_subtask_node(item, index) for index, item in enumerate(subtasks, start=1) if isinstance(item, dict))
    children.extend(_gap_node(item, index) for index, item in enumerate(gaps, start=1) if isinstance(item, dict))
    children.extend(_round_node(item, index) for index, item in enumerate(rounds, start=1) if isinstance(item, dict))
    if linked_run:
        children.append(_execution_node(linked_run))
    root["children"] = children
    return root


def _subtask_node(item: dict[str, object], index: int) -> dict[str, object]:
    return {
        "id": str(item.get("id") or f"subtask-{index}"),
        "label": item.get("title") or f"子任务 {index}",
        "kind": "subtask",
        "status": "planned",
        "state": "planned",
        "summary": " / ".join(str(value) for value in item.get("expected_outputs", []) if value) if isinstance(item.get("expected_outputs"), list) else "",
        "related_agent_ids": [],
        "children": [],
    }


def _gap_node(item: dict[str, object], index: int) -> dict[str, object]:
    required = bool(item.get("required", True))
    status = str(item.get("status") or "open")
    return {
        "id": str(item.get("id") or f"gap-{index}"),
        "label": item.get("title") or f"缺口 {index}",
        "kind": "gap",
        "status": status,
        "state": "blocked" if required and status != "closed" else "done" if status == "closed" else "followup",
        "summary": item.get("recommendation") or "",
        "related_agent_ids": [],
        "children": [],
    }


def _round_node(item: dict[str, object], index: int) -> dict[str, object]:
    round_type = str(item.get("round_type") or f"round-{index}")
    job_id = _extract_job_id(str(item.get("summary") or ""))
    return {
        "id": str(item.get("id") or f"round-{index}"),
        "label": _round_label(round_type),
        "kind": "review_round",
        "status": round_type,
        "state": "done",
        "summary": item.get("summary") or "",
        "related_agent_ids": [job_id] if job_id else [],
        "children": [],
    }


def _execution_node(linked_run: dict[str, object]) -> dict[str, object]:
    status = str(linked_run.get("status") or "unknown")
    execution_summary = _linked_execution_summary(linked_run)
    summary_parts = [
        str(linked_run.get("summary") or linked_run.get("final_mode") or ""),
        f"runtime={execution_summary.get('runtime_name')}" if execution_summary.get("runtime_name") else "",
        f"verify={execution_summary.get('verification_status')}" if execution_summary.get("verification_status") else "",
    ]
    return {
        "id": str(linked_run.get("run_id") or "linked-run"),
        "label": "执行运行",
        "kind": "execution_run",
        "status": status,
        "state": _node_state(status),
        "summary": " ".join(part for part in summary_parts if part),
        "related_agent_ids": [],
        "children": [],
    }


def _node_state(status: str) -> str:
    if status in {"accepted", "completed", "approved_for_execution"}:
        return "done"
    if status in {"blocked", "failed", "needs_revision"}:
        return "blocked"
    if status in {"needs_followup"}:
        return "followup"
    if status in {"executing", "running", "working", "in_review"}:
        return "running"
    return "planned"


def _round_label(round_type: str) -> str:
    labels = {
        "authoring": "计划起草",
        "review": "计划审核",
        "review_retry": "审核重试",
        "adversarial_review": "风险挑战",
        "adversarial_review_retry": "风险挑战重试",
        "revision": "计划修订",
        "approval": "批准门禁",
    }
    return labels.get(round_type, round_type.replace("_", " "))


def _extract_job_id(summary: str) -> str | None:
    for token in reversed(summary.replace(".", " ").split()):
        if token.startswith("job-"):
            return token
    return None


def _build_agent_cards(payload: dict[str, object]) -> list[dict[str, object]]:
    summary = get_governance_status(payload)
    jobs = summary.get("delegated_jobs", []) if isinstance(summary.get("delegated_jobs"), list) else []
    cards = [_session_lead_card(payload)]
    cards.extend(_delegated_job_card(job) for job in jobs if isinstance(job, dict))
    cards.append(_runtime_card(payload))
    return cards


def _delegated_job_card(job: dict[str, object]) -> dict[str, object]:
    role, role_label, layer, layer_label = _role_for_round(str(job.get("round_type") or "delegated"))
    metadata = job.get("metadata", {}) if isinstance(job.get("metadata"), dict) else {}
    return {
        "id": job.get("job_id"),
        "provider": job.get("provider") or "mock",
        "model": job.get("model"),
        "kind": job.get("round_type") or "delegated",
        "status": job.get("status") or "unknown",
        "phase": "failed" if job.get("status") == "failed" else "done",
        "summary": job.get("summary") or "",
        "error": job.get("error"),
        "role": role,
        "role_label": role_label,
        "layer": layer,
        "layer_label": layer_label,
        "current_action": job.get("summary") or job.get("error") or "等待委派任务更新",
        "terminal_ref": metadata.get("terminal_ref"),
        "attach_available": bool(metadata.get("attach_available", False)),
    }


def _session_lead_card(payload: dict[str, object]) -> dict[str, object]:
    summary = get_governance_status(payload)
    return {
        "id": payload.get("id"),
        "provider": "decision_core",
        "model": None,
        "kind": "session_lead",
        "status": payload.get("status") or "unknown",
        "phase": summary.get("phase") or payload.get("status") or "unknown",
        "summary": summary.get("primary_reason") or summary.get("next_action_message") or payload.get("requirement") or "",
        "error": None,
        "role": "lead",
        "role_label": "会话治理",
        "layer": "decision",
        "layer_label": "治理层",
        "current_action": summary.get("primary_reason") or summary.get("next_action_message") or "协调会话状态、门禁与下一步动作",
        "terminal_ref": None,
        "attach_available": False,
    }


def _runtime_card(payload: dict[str, object]) -> dict[str, object]:
    verdict = payload.get("decision_verdict", {}) if isinstance(payload.get("decision_verdict"), dict) else {}
    provider_runtime = (
        verdict.get("selected_provider_runtime", {})
        if isinstance(verdict.get("selected_provider_runtime"), dict)
        else {}
    )
    runtime = str(provider_runtime.get("runtime") or provider_runtime.get("worker") or "mock")
    return {
        "id": f"{payload.get('id')}-runtime",
        "provider": runtime,
        "model": provider_runtime.get("author_model"),
        "kind": "runtime",
        "status": payload.get("status") or "unknown",
        "phase": "runtime",
        "summary": _format_provider_runtime(provider_runtime) or "等待 provider/runtime 选择",
        "error": None,
        "role": "runtime",
        "role_label": "运行时",
        "layer": "runtime",
        "layer_label": "运行时层",
        "current_action": _format_provider_runtime(provider_runtime) or "承载底层 provider/job 执行",
        "terminal_ref": None,
        "attach_available": False,
    }


def _build_role_groups(
    payload: dict[str, object],
    graph: WorkUnitGraph | None = None,
    messages: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    cards = _build_graph_agent_cards(payload, graph) if graph else _build_agent_cards(payload)
    cards = _attach_message_counts(cards, messages or [])
    grouped = []
    for layer, label in ROLE_GROUPS:
        layer_cards = [card for card in cards if card.get("layer") == layer]
        grouped.append(
            {
                "layer": layer,
                "layer_label": label,
                "cards": layer_cards,
                "count": len(layer_cards),
            }
        )
    return grouped


def _build_message_summary(messages: list[dict[str, object]]) -> dict[str, object]:
    threads: dict[str, int] = {}
    for message in messages:
        thread = str(message.get("thread") or "main")
        threads[thread] = threads.get(thread, 0) + 1
    return {
        "count": len(messages),
        "items": messages[:20],
        "latest": messages[0] if messages else None,
        "threads": threads,
    }


def _attach_message_counts(cards: list[dict[str, object]], messages: list[dict[str, object]]) -> list[dict[str, object]]:
    latest_by_role: dict[str, str] = {}
    inbox_counts: dict[str, int] = {}
    outbox_counts: dict[str, int] = {}
    for message in messages:
        from_role = str(message.get("from_role") or "")
        to_role = str(message.get("to_role") or "")
        content = str(message.get("content") or "")
        if to_role:
            inbox_counts[to_role] = inbox_counts.get(to_role, 0) + 1
            latest_by_role.setdefault(to_role, content)
        if from_role:
            outbox_counts[from_role] = outbox_counts.get(from_role, 0) + 1
            latest_by_role.setdefault(from_role, content)
    enriched = []
    for card in cards:
        role = str(card.get("role") or "")
        updated = dict(card)
        updated["inbox_count"] = inbox_counts.get(role, 0)
        updated["outbox_count"] = outbox_counts.get(role, 0)
        updated["latest_message_summary"] = latest_by_role.get(role, "")
        enriched.append(updated)
    return enriched


def _build_graph_agent_cards(payload: dict[str, object], graph: WorkUnitGraph | None) -> list[dict[str, object]]:
    cards_by_role: dict[str, dict[str, object]] = {}
    if graph:
        for node in graph.nodes:
            role = get_agent_role(node.owner_role)
            current = cards_by_role.get(role.id)
            related_ids = [*node.linked_job_ids]
            if node.linked_run_id:
                related_ids.append(node.linked_run_id)
            if current is None:
                cards_by_role[role.id] = {
                    "id": f"{payload.get('id')}-{role.id}",
                    "provider": role.default_provider,
                    "kind": node.kind,
                    "status": node.status,
                    "phase": node.status,
                    "summary": node.summary or node.title,
                    "error": None,
                    "role": role.id,
                    "role_label": role.label,
                    "layer": role.layer,
                    "layer_label": role.layer_label,
                    "current_action": node.title,
                    "related_work_unit_ids": [node.id],
                    "related_agent_ids": related_ids,
                    "terminal_ref": None,
                    "attach_available": False,
                }
            else:
                current["related_work_unit_ids"] = [*list(current.get("related_work_unit_ids", [])), node.id]
                current["related_agent_ids"] = [*list(current.get("related_agent_ids", [])), *related_ids]
                current["status"] = _dominant_status(str(current.get("status") or ""), node.status)
                current["phase"] = current["status"]
                current["current_action"] = node.title

    for job_card in _build_agent_cards(payload):
        role_id = str(job_card.get("role") or role_for_job_kind(str(job_card.get("kind") or "")).id)
        role = get_agent_role(role_id)
        current = cards_by_role.get(role.id)
        if current is None:
            cards_by_role[role.id] = dict(job_card)
        else:
            current["id"] = job_card.get("id") or current.get("id")
            current["provider"] = job_card.get("provider") or current.get("provider")
            current["kind"] = job_card.get("kind") or current.get("kind")
            current["status"] = _dominant_status(str(current.get("status") or ""), str(job_card.get("status") or ""))
            current["phase"] = job_card.get("phase") or current.get("phase")
            current["summary"] = job_card.get("summary") or current.get("summary")
            current["current_action"] = job_card.get("current_action") or current.get("current_action")
            current["terminal_ref"] = job_card.get("terminal_ref")
            current["attach_available"] = bool(job_card.get("attach_available", False))

    for role in DEFAULT_AGENT_ROLES.values():
        if role.id in cards_by_role:
            continue
        cards_by_role[role.id] = {
            "id": f"{payload.get('id')}-{role.id}",
            "provider": role.default_provider,
            "kind": "role",
            "status": "idle",
            "phase": "idle",
            "summary": "暂无分配的工作单元",
            "error": None,
            "role": role.id,
            "role_label": role.label,
            "layer": role.layer,
            "layer_label": role.layer_label,
            "current_action": "等待任务",
            "related_work_unit_ids": [],
            "related_agent_ids": [],
            "terminal_ref": None,
            "attach_available": False,
        }

    order = list(DEFAULT_AGENT_ROLES)
    return sorted(cards_by_role.values(), key=lambda card: order.index(str(card.get("role"))) if str(card.get("role")) in order else len(order))


def _dominant_status(current: str, incoming: str) -> str:
    rank = {
        "failed": 6,
        "blocked": 6,
        "needs_revision": 5,
        "executing": 4,
        "running": 4,
        "working": 4,
        "in_review": 3,
        "approved_for_execution": 2,
        "accepted": 1,
        "completed": 1,
        "idle": 0,
        "planned": 0,
    }
    return incoming if rank.get(incoming, 0) >= rank.get(current, 0) else current


def _build_governance_summary(payload: dict[str, object]) -> dict[str, object]:
    summary = get_governance_status(payload)
    verdict = payload.get("decision_verdict", {}) if isinstance(payload.get("decision_verdict"), dict) else {}
    compliance = payload.get("compliance", {}) if isinstance(payload.get("compliance"), dict) else {}
    provider_runtime = (
        verdict.get("selected_provider_runtime", {})
        if isinstance(verdict.get("selected_provider_runtime"), dict)
        else {}
    )
    recovery_actions = summary.get("recovery_actions", []) if isinstance(summary.get("recovery_actions"), list) else []
    blocking_reasons = summary.get("blocking_reasons", []) if isinstance(summary.get("blocking_reasons"), list) else []
    recommended_commands = summary.get("recommended_commands", []) if isinstance(summary.get("recommended_commands"), list) else []
    warnings = summary.get("warnings", []) if isinstance(summary.get("warnings"), list) else []
    recovery_timeline = summary.get("recovery_timeline", {}) if isinstance(summary.get("recovery_timeline"), dict) else {}
    blocking_summary = (
        recovery_timeline.get("blocking_summary", {})
        if isinstance(recovery_timeline.get("blocking_summary"), dict)
        else {}
    )
    return {
        "selected_topology": summary.get("selected_topology") or verdict.get("selected_topology"),
        "topology_reason": summary.get("topology_reason"),
        "selected_provider_runtime": provider_runtime,
        "primary_action": summary.get("primary_action"),
        "primary_reason": summary.get("primary_reason") or summary.get("next_action_message", ""),
        "review_intensity": _review_intensity(payload),
        "gate_status": _gate_status(payload, blocking_reasons),
        "compliance_status": compliance.get("status", "unknown"),
        "blocking": bool(blocking_reasons),
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "recovery_actions": recovery_actions,
        "recovery_action_count": len(recovery_actions),
        "recommended_commands": recommended_commands,
        "recommended_command_count": len(recommended_commands),
        "recovery_provider": summary.get("recovery_provider"),
        "recovery_round_type": summary.get("recovery_round_type"),
        "recovery_provider_mode": summary.get("recovery_provider_mode"),
        "recovery_provider_fallback_from": summary.get("recovery_provider_fallback_from"),
        "recovery_provider_fallback_reason": summary.get("recovery_provider_fallback_reason"),
        "recovery_provider_fallback_detail": summary.get("recovery_provider_fallback_detail"),
        "recovery_timeline": recovery_timeline,
        "recovery_dashboard": {
            "current_status": recovery_timeline.get("current_status"),
            "resume_hint": recovery_timeline.get("resume_hint"),
            "last_checkpoint": recovery_timeline.get("last_checkpoint"),
            "blocking_summary": blocking_summary,
            "read_only": True,
        },
    }


def _build_evidence_summary(
    payload: dict[str, object],
    linked_run: dict[str, object] | None,
    memory_records: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    rounds = payload.get("review_rounds", []) if isinstance(payload.get("review_rounds"), list) else []
    gaps = payload.get("gaps", []) if isinstance(payload.get("gaps"), list) else []
    summary = get_governance_status(payload)
    jobs = summary.get("delegated_jobs", []) if isinstance(summary.get("delegated_jobs"), list) else []
    providers = sorted({str(job.get("provider")) for job in jobs if isinstance(job, dict) and job.get("provider")})
    findings = [
        finding
        for round_ in rounds
        if isinstance(round_, dict) and isinstance(round_.get("review_result"), dict)
        for finding in round_.get("review_result", {}).get("findings", [])
        if isinstance(finding, dict)
    ]
    memory_records = memory_records or []
    postmortems = [record for record in memory_records if record.get("record_type") == "postmortem"]
    native_learning_records = [
        record for record in memory_records
        if record.get("namespace") in {"native_trajectory", "native_learning"}
    ]
    execution_summary = _linked_execution_summary(linked_run)
    return {
        "review_round_count": len(rounds),
        "gap_count": len(gaps),
        "finding_count": len(findings),
        "delegated_job_count": len(jobs),
        "providers": providers,
        "linked_run_id": linked_run.get("run_id") if linked_run else None,
        "linked_run_status": linked_run.get("status") if linked_run else None,
        "memory_namespaces": ["plan_session", "run_artifact", "job_log"],
        "tool_surfaces": ["team_orchestrator", "run_store", "job_runtime"],
        "memory_record_count": len(memory_records),
        "postmortem_count": len(postmortems),
        "learning_record_count": len(native_learning_records),
        "learning_consumption_ready": bool(native_learning_records),
        "execution_runtime": execution_summary.get("runtime_name"),
        "verification_status": execution_summary.get("verification_status"),
        "repair_attempt_count": execution_summary.get("repair_attempt_count", 0),
        "recovery_action": execution_summary.get("recovery_action"),
        "recent_memory": [
            {
                "namespace": record.get("namespace"),
                "record_type": record.get("record_type"),
                "summary": record.get("summary"),
            }
            for record in memory_records[:5]
        ],
        "retrieved_memory": memory_records[:3],
    }


def _build_operator_summary(
    payload: dict[str, object],
    linked_run: dict[str, object] | None,
    graph: WorkUnitGraph | None,
    messages: list[dict[str, object]],
    workspace_index: dict[str, object] | None = None,
    product_ux: dict[str, object] | None = None,
) -> dict[str, object]:
    summary = get_governance_status(payload)
    verdict = payload.get("decision_verdict", {}) if isinstance(payload.get("decision_verdict"), dict) else {}
    compliance = payload.get("compliance", {}) if isinstance(payload.get("compliance"), dict) else {}
    approved_plan = payload.get("approved_plan", {}) if isinstance(payload.get("approved_plan"), dict) else {}
    execution_contract = (
        approved_plan.get("execution_contract", {}) if isinstance(approved_plan.get("execution_contract"), dict) else {}
    )
    linked_metadata = linked_run.get("metadata", {}) if isinstance(linked_run, dict) and isinstance(linked_run.get("metadata"), dict) else {}
    provenance = linked_metadata.get("provenance", {}) if isinstance(linked_metadata.get("provenance"), dict) else {}
    provider_runtime = verdict.get("selected_provider_runtime", {}) if isinstance(verdict.get("selected_provider_runtime"), dict) else {}
    fallback_policy = execution_contract.get("fallback_policy", {}) if isinstance(execution_contract.get("fallback_policy"), dict) else {}
    review_policy = execution_contract.get("review_policy", {}) if isinstance(execution_contract.get("review_policy"), dict) else {}
    events = payload.get("events", []) if isinstance(payload.get("events"), list) else []
    execution_summary = _linked_execution_summary(linked_run)
    workspace_benchmark = (
        workspace_index.get("comparative_benchmark", {})
        if isinstance(workspace_index, dict) and isinstance(workspace_index.get("comparative_benchmark"), dict)
        else {}
    )
    execution_fact_chain = (
        workspace_index.get("execution_fact_chain", {})
        if isinstance(workspace_index, dict) and isinstance(workspace_index.get("execution_fact_chain"), dict)
        else {}
    )
    comparative_digest = _comparative_benchmark_digest(workspace_benchmark)
    proof_strength = (
        workspace_benchmark.get("comparison_proof_strength", {})
        if isinstance(workspace_benchmark.get("comparison_proof_strength"), dict)
        else {}
    )
    operator_planner_digest = derive_operator_planner_digest(
        planner_decision=(
            execution_summary.get("session_planner_decision", {})
            if isinstance(execution_summary.get("session_planner_decision"), dict)
            else {}
        ),
        planner_closure_posture=(
            execution_summary.get("planner_closure_posture", {})
            if isinstance(execution_summary.get("planner_closure_posture"), dict)
            else {}
        ),
        continuity_outline=(
            execution_summary.get("continuity_outline", {})
            if isinstance(execution_summary.get("continuity_outline"), dict)
            else {}
        ),
    )
    clarify_boundary_digest = (
        workspace_index.get("clarify_boundary_digest", {})
        if isinstance(workspace_index, dict) and isinstance(workspace_index.get("clarify_boundary_digest"), dict)
        else derive_clarify_boundary_digest(
            operator_planner_digest=operator_planner_digest,
            comparative_session_posture_summary=workspace_benchmark.get("comparative_session_posture_summary", {})
            if isinstance(workspace_benchmark.get("comparative_session_posture_summary"), dict)
            else {},
            execution_fact_chain=execution_fact_chain,
        )
    )
    approval_boundary_digest = (
        workspace_index.get("approval_boundary_digest", {})
        if isinstance(workspace_index, dict) and isinstance(workspace_index.get("approval_boundary_digest"), dict)
        else derive_approval_boundary_digest(
            operator_planner_digest=operator_planner_digest,
            comparative_session_posture_summary=workspace_benchmark.get("comparative_session_posture_summary", {})
            if isinstance(workspace_benchmark.get("comparative_session_posture_summary"), dict)
            else {},
            execution_fact_chain=execution_fact_chain,
        )
    )
    return {
        "session": {
            "id": payload.get("id"),
            "status": payload.get("status"),
            "phase": summary.get("phase") or payload.get("resume", {}).get("current_phase")
            if isinstance(payload.get("resume"), dict)
            else None,
            "primary_action": summary.get("primary_action"),
            "linked_execution_run_id": provenance.get("linked_execution_run_id")
            or (linked_run.get("run_id") if isinstance(linked_run, dict) else None),
        },
        "execution_provenance": {
            "plan_session_id": provenance.get("plan_session_id"),
            "approved_plan_goal": provenance.get("approved_plan_goal"),
            "source_requirement": provenance.get("source_requirement"),
            "selected_topology": provenance.get("selected_topology") or verdict.get("selected_topology"),
            "selected_provider_runtime": provenance.get("selected_provider_runtime") or provider_runtime,
            "linked_run_status": linked_run.get("status") if isinstance(linked_run, dict) else None,
        },
        "execution_runtime_summary": execution_summary,
        "execution_fact_chain": execution_fact_chain,
        "clarify_boundary_digest": clarify_boundary_digest,
        "approval_boundary_digest": approval_boundary_digest,
        "comparative_benchmark_summary": workspace_benchmark,
        "comparative_benchmark_digest": comparative_digest,
        "native_product_ux": product_ux if isinstance(product_ux, dict) else {},
        "native_release_candidate": (product_ux.get("release_candidate", {}) if isinstance(product_ux, dict) else {}),
        "native_release_bundle": (product_ux.get("release_bundle", {}) if isinstance(product_ux, dict) else {}),
        "comparative_planner_closure_summary": _comparative_planner_closure_summary(comparative_digest),
        "comparative_planner_autonomy_summary": build_comparative_planner_autonomy_summary(
            planner_shared_contract=(
                execution_summary.get("planner_shared_contract", {})
                if isinstance(execution_summary.get("planner_shared_contract"), dict)
                else {}
            ),
            operator_planner_digest=operator_planner_digest,
            comparative_shared_evidence_surface=(
                comparative_digest.get("shared_evidence_surface", [])
                if isinstance(comparative_digest.get("shared_evidence_surface"), list)
                else []
            ),
        ),
        "comparative_planner_candidate_summary": build_comparative_planner_candidate_summary(
            planner_shared_contract=(
                execution_summary.get("planner_shared_contract", {})
                if isinstance(execution_summary.get("planner_shared_contract"), dict)
                else {}
            ),
            operator_planner_digest=operator_planner_digest,
            comparative_shared_evidence_surface=(
                comparative_digest.get("shared_evidence_surface", [])
                if isinstance(comparative_digest.get("shared_evidence_surface"), list)
                else []
            ),
        ),
        "comparative_native_tool_summary": build_comparative_native_tool_summary(
            native_tool_productization_surface=(
                execution_summary.get("native_tool_productization_surface", {})
                if isinstance(execution_summary.get("native_tool_productization_surface"), dict)
                else {}
            ),
            native_tool_workflow_surface=(
                execution_summary.get("native_tool_workflow_surface", {})
                if isinstance(execution_summary.get("native_tool_workflow_surface"), dict)
                else {}
            ),
        ),
        "operator_tool_digest": derive_operator_tool_digest(
            native_tool_productization_surface=(
                execution_summary.get("native_tool_productization_surface", {})
                if isinstance(execution_summary.get("native_tool_productization_surface"), dict)
                else {}
            ),
            native_tool_workflow_surface=(
                execution_summary.get("native_tool_workflow_surface", {})
                if isinstance(execution_summary.get("native_tool_workflow_surface"), dict)
                else {}
            ),
        ),
        "operator_planner_digest": operator_planner_digest,
        "comparative_adapter_summary": build_comparative_adapter_summary(
            adapter_productization_surface=(
                execution_summary.get("adapter_productization_surface", {})
                if isinstance(execution_summary.get("adapter_productization_surface"), dict)
                else {}
            ),
            adapter_shared_contract=(
                execution_summary.get("adapter_shared_contract", {})
                if isinstance(execution_summary.get("adapter_shared_contract"), dict)
                else {}
            ),
            adapter_capability_surface=(
                execution_summary.get("adapter_capability_surface", {})
                if isinstance(execution_summary.get("adapter_capability_surface"), dict)
                else execution_summary.get("adapter_capability", {})
                if isinstance(execution_summary.get("adapter_capability"), dict)
                else {}
            ),
        ),
        "comparative_session_continuity_summary": (
            workspace_benchmark.get("comparative_session_continuity_summary", {})
            if isinstance(workspace_benchmark.get("comparative_session_continuity_summary"), dict)
            and workspace_benchmark.get("comparative_session_continuity_summary")
            else build_comparative_session_continuity_summary(
                session_productization_surface=(
                    execution_summary.get("session_productization_surface", {})
                    if isinstance(execution_summary.get("session_productization_surface"), dict)
                    else {}
                ),
                continuity_outline=(
                    execution_summary.get("session_continuity_outline", {})
                    if isinstance(execution_summary.get("session_continuity_outline"), dict)
                    else {}
                ),
                comparative_shared_evidence_surface=(
                    comparative_digest.get("shared_evidence_surface", [])
                    if isinstance(comparative_digest.get("shared_evidence_surface"), list)
                    else []
                ),
            )
        ),
        "comparative_native_closure_summary": (
            workspace_benchmark.get("comparative_native_closure_summary", {})
            if isinstance(workspace_benchmark.get("comparative_native_closure_summary"), dict)
            and workspace_benchmark.get("comparative_native_closure_summary")
            else build_comparative_native_closure_summary(
                native_task_proof=(
                    execution_summary.get("native_task_proof", {})
                    if isinstance(execution_summary.get("native_task_proof"), dict)
                    else {}
                ),
                verification=(
                    execution_summary.get("milestone_verification", {})
                    if isinstance(execution_summary.get("milestone_verification"), dict)
                    else {}
                ),
                recovery_summary=(
                    execution_summary.get("repair_summary", {})
                    if isinstance(execution_summary.get("repair_summary"), dict)
                    else {}
                ),
                comparative_shared_evidence_surface=(
                    comparative_digest.get("shared_evidence_surface", [])
                    if isinstance(comparative_digest.get("shared_evidence_surface"), list)
                    else []
                ),
            )
        ),
        "comparative_session_posture_summary": build_comparative_session_posture_summary(
            session_productization_surface=(
                execution_summary.get("session_productization_surface", {})
                if isinstance(execution_summary.get("session_productization_surface"), dict)
                else {}
            ),
            planner_decision=(
                execution_summary.get("session_planner_decision", {})
                if isinstance(execution_summary.get("session_planner_decision"), dict)
                else {}
            ),
            continuity_outline=(
                execution_summary.get("session_continuity_outline", {})
                if isinstance(execution_summary.get("session_continuity_outline"), dict)
                else {}
            ),
        ),
        "operator_posture_digest": (
            execution_summary.get("session_productization_surface", {}).get("operator_posture_digest", {})
            if isinstance(execution_summary.get("session_productization_surface"), dict)
            and isinstance(execution_summary.get("session_productization_surface", {}).get("operator_posture_digest"), dict)
            else {}
        ),
        "comparative_daily_driver_summary": build_comparative_daily_driver_summary(
            proof_strength=proof_strength,
            benchmark_digest=comparative_digest,
            comparative_benchmark=workspace_benchmark,
        ),
        "comparative_daily_driver_runner_artifact": (
            workspace_benchmark.get("daily_driver_runner_artifact", {})
            if isinstance(workspace_benchmark.get("daily_driver_runner_artifact"), dict)
            else {}
        ),
        "comparative_completion_summary": build_comparative_completion_summary(
            benchmark_digest=comparative_digest,
            comparative_benchmark=workspace_benchmark,
        ),
        "comparative_daily_driver_benchmark": build_comparative_daily_driver_benchmark(proof_strength),
        "review_policy": review_policy or payload.get("structured_brief", {}).get("review_policy", {})
        if isinstance(payload.get("structured_brief"), dict)
        else {},
        "fallback_snapshot": {
            "provider_runtime": provider_runtime,
            "fallback_policy": fallback_policy,
            "recovery_provider": summary.get("recovery_provider"),
            "recovery_provider_fallback_from": summary.get("recovery_provider_fallback_from"),
            "recovery_provider_fallback_reason": summary.get("recovery_provider_fallback_reason"),
            "recovery_provider_fallback_detail": summary.get("recovery_provider_fallback_detail"),
        },
        "approval_observability": {
            "approval_state": summary.get("approval_state"),
            "human_intervention_reason": summary.get("human_intervention_reason"),
            "runtime_health": summary.get("runtime_health"),
            "usage_cost": summary.get("usage_cost"),
            "recovery_timeline": summary.get("recovery_timeline"),
        },
        "compliance_snapshot": {
            "status": compliance.get("status", "unknown"),
            "blocking": bool(compliance.get("blocking", False)),
            "blocking_reasons": list(compliance.get("blocking_reasons", []))
            if isinstance(compliance.get("blocking_reasons"), list)
            else [],
            "warnings": list(compliance.get("warnings", [])) if isinstance(compliance.get("warnings"), list) else [],
            "required_actions": list(compliance.get("required_actions", []))
            if isinstance(compliance.get("required_actions"), list)
            else [],
        },
        "event_timeline": events[:10],
        "message_timeline": [
            {
                "from_role": message.get("from_role"),
                "to_role": message.get("to_role"),
                "message_type": message.get("message_type"),
                "thread": message.get("thread"),
                "content": message.get("content"),
            }
            for message in messages[:10]
        ],
        "work_graph_summary": {
            "node_count": len(graph.nodes) if graph else 0,
            "edge_count": len(graph.edges) if graph else 0,
            "schedulable_nodes": schedulable_nodes(graph) if graph else [],
        },
    }


def _comparative_benchmark_digest(benchmark: dict[str, object]) -> dict[str, object]:
    return build_runtime_comparative_benchmark_digest(benchmark if isinstance(benchmark, dict) else {})


def _comparative_planner_closure_summary(benchmark_digest: dict[str, object]) -> dict[str, object]:
    benchmark_digest = benchmark_digest if isinstance(benchmark_digest, dict) else {}
    if not benchmark_digest.get("planner_closure_mode") and not benchmark_digest.get("planner_next_recommended_action"):
        return {}
    return {
        "format": "agent_orchestrator.comparative_planner_closure_summary.v1",
        "closure_mode": benchmark_digest.get("planner_closure_mode"),
        "next_recommended_action": benchmark_digest.get("planner_next_recommended_action"),
        "resume_posture": benchmark_digest.get("planner_resume_posture"),
        "verify_selected": benchmark_digest.get("planner_verify_selected"),
        "verification_status": benchmark_digest.get("planner_verification_status"),
        "summary": (
            f"mode={benchmark_digest.get('planner_closure_mode')} "
            f"next_action={benchmark_digest.get('planner_next_recommended_action')} "
            f"resume_posture={benchmark_digest.get('planner_resume_posture')}"
        ),
    }


def _review_intensity(payload: dict[str, object]) -> str:
    verdict = payload.get("decision_verdict", {}) if isinstance(payload.get("decision_verdict"), dict) else {}
    selected = verdict.get("selected_provider_runtime", {}) if isinstance(verdict.get("selected_provider_runtime"), dict) else {}
    if payload.get("status") in {"blocked", "needs_revision", "awaiting_human"}:
        return "strict"
    if selected.get("reviewer") or selected.get("review_provider"):
        return "reviewed"
    return "standard"


def _gate_status(payload: dict[str, object], blocking_reasons: list[object]) -> str:
    status = str(payload.get("status") or "")
    if blocking_reasons or status in {"blocked", "awaiting_human"}:
        return "blocked"
    if status == "needs_revision":
        return "needs_revision"
    if status == "approved_for_execution":
        return "approved"
    if status in {"accepted", "needs_followup"}:
        return "completed"
    return "open"


def _role_for_round(round_type: str) -> tuple[str, str, str, str]:
    normalized = round_type.replace("-", "_")
    if normalized in {"review", "review_retry"}:
        return "reviewer", "质量审查", "review", "质量门禁层"
    if normalized in {"adversarial_review", "adversarial_review_retry"}:
        return "adversarial_reviewer", "风险挑战", "review", "质量门禁层"
    if normalized == "rescue":
        return "rescue", "恢复处理", "rescue", "恢复层"
    if normalized in {"implementation", "build"}:
        return "builder", "执行任务", "execution", "执行层"
    if normalized == "validation":
        return "validator", "执行验证", "execution", "执行层"
    return "planner", "规划记录", "decision", "治理层"


def _format_provider_runtime(provider_runtime: dict[str, object]) -> str:
    if not provider_runtime:
        return ""
    parts = [f"{key}:{value}" for key, value in provider_runtime.items() if value not in {None, ""}]
    return " · ".join(parts)


def _linked_execution_summary(linked_run: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(linked_run, dict):
        return {}
    payload = linked_run.get("payload", {}) if isinstance(linked_run.get("payload"), dict) else {}
    verification = payload.get("verification", {}) if isinstance(payload.get("verification"), dict) else {}
    repair_summary = payload.get("repair_summary", {}) if isinstance(payload.get("repair_summary"), dict) else {}
    recovery_summary = payload.get("recovery_summary", {}) if isinstance(payload.get("recovery_summary"), dict) else {}
    attempt_memory = payload.get("attempt_memory", []) if isinstance(payload.get("attempt_memory"), list) else []
    kernel_contract = payload.get("kernel_contract", {}) if isinstance(payload.get("kernel_contract"), dict) else {}
    step_loop_contract = payload.get("step_loop_contract", {}) if isinstance(payload.get("step_loop_contract"), dict) else {}
    context_engineering_contract = (
        payload.get("context_engineering_contract", {})
        if isinstance(payload.get("context_engineering_contract"), dict)
        else {}
    )
    context_engineering_refs = (
        step_loop_contract.get("context_engineering_refs", {})
        if isinstance(step_loop_contract.get("context_engineering_refs"), dict)
        else {}
    )
    strategy_summary = payload.get("strategy_summary", {}) if isinstance(payload.get("strategy_summary"), dict) else {}
    native_task_proof = payload.get("native_task_proof", {}) if isinstance(payload.get("native_task_proof"), dict) else {}
    native_repo_task_acceptance = (
        payload.get("native_repo_task_acceptance", {})
        if isinstance(payload.get("native_repo_task_acceptance"), dict)
        else {}
    )
    native_complex_repo_task_acceptance = (
        payload.get("native_complex_repo_task_acceptance", {})
        if isinstance(payload.get("native_complex_repo_task_acceptance"), dict)
        else {}
    )
    repo_report = payload.get("repo_report", {}) if isinstance(payload.get("repo_report"), dict) else {}
    continuity_contract = (
        payload.get("session_continuity_contract", {})
        if isinstance(payload.get("session_continuity_contract"), dict)
        else {}
    )
    productization_surface = _session_productization_surface(continuity_contract)
    program_continuity = (
        continuity_contract.get("program_continuity", {})
        if isinstance(continuity_contract.get("program_continuity"), dict)
        else {}
    )
    daily_driver_readiness = (
        continuity_contract.get("daily_driver_readiness", {})
        if isinstance(continuity_contract.get("daily_driver_readiness"), dict)
        else {}
    )
    tool_productization_surface = _native_tool_productization_surface(payload)
    adapter_productization_surface = _adapter_productization_surface(payload)
    path_selection = payload.get("path_selection", {}) if isinstance(payload.get("path_selection"), dict) else {}
    adapter_contract = payload.get("adapter_contract", {}) if isinstance(payload.get("adapter_contract"), dict) else {}
    adapter_capability_surface = (
        payload.get("adapter_capability_surface", {})
        if isinstance(payload.get("adapter_capability_surface"), dict)
        else {}
    )
    adapter_shared_contract = (
        payload.get("adapter_shared_contract", {})
        if isinstance(payload.get("adapter_shared_contract"), dict)
        else {}
    )
    if not adapter_shared_contract:
        adapter_shared_contract = {
            "adapter_family": adapter_contract.get("adapter_family"),
            "agent_kind": adapter_contract.get("agent_kind"),
            "default_path": path_selection.get("default_path"),
            "operating_boundary": path_selection.get("operating_boundary"),
            "selection_reason": path_selection.get("selection_reason"),
            "handoff_reason_code": path_selection.get("handoff_reason_code"),
            "fallback_reason_code": path_selection.get("fallback_reason_code"),
            "native_coverage_class": path_selection.get("native_coverage_class"),
            "learning_consumed": path_selection.get("learning_consumed"),
            "learning_source_count": path_selection.get("learning_source_count"),
            "comparison_mode": (
                adapter_contract.get("capability_surface", {}).get("comparability", {}).get("comparison_mode")
                if isinstance(adapter_contract.get("capability_surface"), dict)
                and isinstance(adapter_contract.get("capability_surface", {}).get("comparability"), dict)
                else None
            ),
            "hot_plug_supported": (
                adapter_contract.get("capability_surface", {}).get("governance", {}).get("hot_plug_supported")
                if isinstance(adapter_contract.get("capability_surface"), dict)
                and isinstance(adapter_contract.get("capability_surface", {}).get("governance"), dict)
                else None
            ),
            "fallback_governed": (
                adapter_contract.get("capability_surface", {}).get("governance", {}).get("fallback_governed")
                if isinstance(adapter_contract.get("capability_surface"), dict)
                and isinstance(adapter_contract.get("capability_surface", {}).get("governance"), dict)
                else None
            ),
            "approval_required": adapter_contract.get("approval_semantics", {}).get("approval_required")
            if isinstance(adapter_contract.get("approval_semantics"), dict)
            else None,
            "approval_pause_supported": adapter_contract.get("approval_semantics", {}).get("approval_pause_supported")
            if isinstance(adapter_contract.get("approval_semantics"), dict)
            else None,
            "evidence_outputs": list(adapter_contract.get("evidence_outputs", []))
            if isinstance(adapter_contract.get("evidence_outputs"), list)
            else [],
            "recovery_surfaces": list(adapter_contract.get("recovery_surfaces", []))
            if isinstance(adapter_contract.get("recovery_surfaces"), list)
            else [],
            "shared_contract_format": (
                adapter_contract.get("capability_surface", {}).get("shared_contract", {}).get("format")
                if isinstance(adapter_contract.get("capability_surface"), dict)
                and isinstance(adapter_contract.get("capability_surface", {}).get("shared_contract"), dict)
                else None
            ),
            "shared_contract_resume_supported": (
                adapter_contract.get("capability_surface", {}).get("shared_contract", {}).get("continuity_support", {}).get("resume_contract")
                if isinstance(adapter_contract.get("capability_surface"), dict)
                and isinstance(adapter_contract.get("capability_surface", {}).get("shared_contract"), dict)
                and isinstance(adapter_contract.get("capability_surface", {}).get("shared_contract", {}).get("continuity_support"), dict)
                else None
            ),
            "recovery_contract": (
                dict(adapter_contract.get("capability_surface", {}).get("shared_contract", {}).get("recovery_contract", {}))
                if isinstance(adapter_contract.get("capability_surface"), dict)
                and isinstance(adapter_contract.get("capability_surface", {}).get("shared_contract"), dict)
                and isinstance(adapter_contract.get("capability_surface", {}).get("shared_contract", {}).get("recovery_contract"), dict)
                else {}
            ),
        }
    comparative_benchmark = (
        payload.get("comparative_benchmark", {})
        if isinstance(payload.get("comparative_benchmark"), dict)
        else {}
    )
    comparative_benchmark_digest = (
        payload.get("comparative_benchmark_digest", {})
        if isinstance(payload.get("comparative_benchmark_digest"), dict)
        else {}
    )
    capability_surface = (
        adapter_capability_surface
        if adapter_capability_surface
        else adapter_contract.get("capability_surface", {})
        if isinstance(adapter_contract.get("capability_surface"), dict)
        else {}
    )
    runtime_name = payload.get("runtime_name")
    if runtime_name is None and linked_run.get("attempts"):
        runtime_name = "legacy"
    step_kind = step_loop_contract.get("current_step_kind")
    if not step_kind and step_loop_contract.get("current_stage") == "verify":
        step_kind = "verification"
    elif not step_kind and step_loop_contract.get("current_stage") == "edit":
        step_kind = "edit_execution"
    elif not step_kind and step_loop_contract.get("current_stage") == "explore":
        step_kind = "repo_exploration"
    required_surfaces = (
        list(context_engineering_refs.get("required_surfaces", []))
        if isinstance(context_engineering_refs.get("required_surfaces"), list)
        else _default_context_surfaces_for_step_kind(str(step_kind) if step_kind else None)
    )
    repo_task_acceptance_ready = native_repo_task_acceptance.get("real_repo_task_acceptance_ready")
    planner_decision = (
        strategy_summary.get("decision_evidence", {})
        if isinstance(strategy_summary.get("decision_evidence"), dict)
        else {}
    )
    session_planner_decision = (
        payload.get("planner_decision", {})
        if isinstance(payload.get("planner_decision"), dict)
        else {}
    )
    session_continuity_outline = (
        payload.get("continuity_outline", {})
        if isinstance(payload.get("continuity_outline"), dict)
        else {}
    )
    shared_productization_surface = build_shared_productization_surface(
        session_productization_surface=productization_surface,
        native_tool_productization_surface=tool_productization_surface,
        native_tool_workflow_surface=(
            payload.get("native_tool_workflow_surface", {})
            if isinstance(payload.get("native_tool_workflow_surface"), dict)
            else (
                payload.get("native_tool_surface", {}).get("workflow_surface", {})
                if isinstance(payload.get("native_tool_surface"), dict)
                and isinstance(payload.get("native_tool_surface", {}).get("workflow_surface"), dict)
                else {}
            )
        ),
        adapter_productization_surface=adapter_productization_surface,
        planner_decision=session_planner_decision
        or derive_session_planner_decision_summary(
            planner_shared={
                "format": planner_decision.get("format"),
                "planner_family": payload.get("planner_family") or strategy_summary.get("planner_family"),
                "selected_strategy": planner_decision.get("selected_strategy"),
                "selected_actions": planner_decision.get("selected_actions", []),
                "selected_owner": planner_decision.get("selected_owner"),
                "decision_boundary": planner_decision.get("decision_boundary", {}),
                "posture": planner_decision.get("posture", {}),
                "autonomy_surface": planner_decision.get("autonomy_surface", {}),
                "delegation_contract": planner_decision.get("delegation_contract", {}),
                "operator_control": planner_decision.get("operator_control", {}),
                "route_planner_intent": planner_decision.get("route_planner_intent", {}),
                "tool_workflow_plan": planner_decision.get("tool_workflow_plan", {}),
            },
            adapter_shared={
                "operating_boundary": path_selection.get("operating_boundary"),
                "selection_reason": path_selection.get("selection_reason"),
                "path_selection": {"planner_intent": path_selection.get("planner_intent", {})},
            },
        ),
        continuity_outline=session_continuity_outline
        or derive_session_continuity_outline_summary(
            continuity=continuity_contract,
            planner_family=payload.get("planner_family") or strategy_summary.get("planner_family"),
        ),
        planner_closure_posture=(
            payload.get("planner_closure_posture", {})
            if isinstance(payload.get("planner_closure_posture"), dict)
            else derive_planner_closure_posture_summary(
                planner_decision=session_planner_decision
                or derive_session_planner_decision_summary(
                    planner_shared={
                        "format": planner_decision.get("format"),
                        "planner_family": payload.get("planner_family") or strategy_summary.get("planner_family"),
                        "selected_strategy": planner_decision.get("selected_strategy"),
                        "selected_actions": planner_decision.get("selected_actions", []),
                        "selected_owner": planner_decision.get("selected_owner"),
                        "decision_boundary": planner_decision.get("decision_boundary", {}),
                        "posture": planner_decision.get("posture", {}),
                        "autonomy_surface": planner_decision.get("autonomy_surface", {}),
                        "delegation_contract": planner_decision.get("delegation_contract", {}),
                        "operator_control": planner_decision.get("operator_control", {}),
                        "route_planner_intent": planner_decision.get("route_planner_intent", {}),
                        "tool_workflow_plan": planner_decision.get("tool_workflow_plan", {}),
                    },
                    adapter_shared={
                        "operating_boundary": path_selection.get("operating_boundary"),
                        "selection_reason": path_selection.get("selection_reason"),
                        "path_selection": {"planner_intent": path_selection.get("planner_intent", {})},
                    },
                ),
                continuity=session_continuity_outline
                or derive_session_continuity_outline_summary(
                    continuity=continuity_contract,
                    planner_family=payload.get("planner_family") or strategy_summary.get("planner_family"),
                ),
            )
        ),
        runtime_cost=(
            continuity_contract.get("runtime_cost", {})
            if isinstance(continuity_contract.get("runtime_cost"), dict)
            else {}
        ),
        native_tool_usage=(
            payload.get("native_tool_usage", {})
            if isinstance(payload.get("native_tool_usage"), dict)
            else {}
        ),
        adapter_capability_surface=(
            payload.get("adapter_capability_surface", {})
            if isinstance(payload.get("adapter_capability_surface"), dict)
            else {}
        ),
        comparative_shared_evidence_surface=(
            payload.get("shared_productization_surface", {}).get("shared_evidence_surface", [])
            if isinstance(payload.get("shared_productization_surface"), dict)
            else []
        ),
    )
    compacted_context_summary = _compacted_context_summary(payload.get("compressed_context", {}))
    derived_session_planner_decision = (
        session_planner_decision
        or derive_session_planner_decision_summary(
            planner_shared={
                "format": planner_decision.get("format"),
                "planner_family": payload.get("planner_family") or strategy_summary.get("planner_family"),
                "selected_strategy": planner_decision.get("selected_strategy"),
                "selected_actions": planner_decision.get("selected_actions", []),
                "selected_owner": planner_decision.get("selected_owner"),
                "decision_boundary": planner_decision.get("decision_boundary", {}),
                "posture": planner_decision.get("posture", {}),
                "autonomy_surface": planner_decision.get("autonomy_surface", {}),
                "delegation_contract": planner_decision.get("delegation_contract", {}),
                "operator_control": planner_decision.get("operator_control", {}),
                "route_planner_intent": planner_decision.get("route_planner_intent", {}),
                "tool_workflow_plan": planner_decision.get("tool_workflow_plan", {}),
            },
            adapter_shared={
                "operating_boundary": path_selection.get("operating_boundary"),
                "selection_reason": path_selection.get("selection_reason"),
                "path_selection": {"planner_intent": path_selection.get("planner_intent", {})},
            },
        )
    )
    derived_continuity_outline = (
        session_continuity_outline
        or derive_session_continuity_outline_summary(
            continuity=continuity_contract,
            planner_family=payload.get("planner_family") or strategy_summary.get("planner_family"),
        )
    )
    planner_closure_posture = derive_planner_closure_posture_summary(
        planner_decision=derived_session_planner_decision,
        continuity=continuity_contract,
    )
    return {
        "runtime_name": runtime_name,
        "execution_mode": payload.get("execution_mode"),
        "planner_family": payload.get("planner_family") or strategy_summary.get("planner_family"),
        "planner_decision_format": planner_decision.get("format"),
        "planner_selected_strategy": planner_decision.get("selected_strategy") or strategy_summary.get("selected_execution_strategy"),
        "planner_native_work_units": planner_decision.get("native_work_units"),
        "session_planner_decision": derived_session_planner_decision,
        "planner_control_surface": (
            session_planner_decision.get("control_surface", {})
            if isinstance(session_planner_decision.get("control_surface"), dict)
            else derive_session_planner_decision_summary(
                planner_shared={
                    "format": planner_decision.get("format"),
                    "planner_family": payload.get("planner_family") or strategy_summary.get("planner_family"),
                    "selected_strategy": planner_decision.get("selected_strategy"),
                    "selected_actions": planner_decision.get("selected_actions", []),
                    "selected_owner": planner_decision.get("selected_owner"),
                    "decision_boundary": planner_decision.get("decision_boundary", {}),
                    "posture": planner_decision.get("posture", {}),
                    "autonomy_surface": planner_decision.get("autonomy_surface", {}),
                    "control_surface": planner_decision.get("control_surface", {}),
                    "delegation_contract": planner_decision.get("delegation_contract", {}),
                    "operator_control": planner_decision.get("operator_control", {}),
                    "route_planner_intent": planner_decision.get("route_planner_intent", {}),
                    "tool_workflow_plan": planner_decision.get("tool_workflow_plan", {}),
                },
                adapter_shared={
                    "operating_boundary": path_selection.get("operating_boundary"),
                    "selection_reason": path_selection.get("selection_reason"),
                    "path_selection": {"planner_intent": path_selection.get("planner_intent", {})},
                },
            ).get("control_surface", {})
        ) or None,
        "session_continuity_outline": derived_continuity_outline,
        "planner_closure_posture": planner_closure_posture,
        "planner_shared_contract": {
            "format": planner_decision.get("format"),
            "planner_family": payload.get("planner_family") or strategy_summary.get("planner_family"),
            "selected_strategy": planner_decision.get("selected_strategy") or strategy_summary.get("selected_execution_strategy"),
            "decision_candidates": list(planner_decision.get("decision_candidates", []))
            if isinstance(planner_decision.get("decision_candidates"), list)
            else [],
            "selected_owner": planner_decision.get("selected_owner"),
            "decision_boundary": dict(planner_decision.get("decision_boundary", {}))
            if isinstance(planner_decision.get("decision_boundary"), dict)
            else {},
            "posture": dict(planner_decision.get("posture", {}))
            if isinstance(planner_decision.get("posture"), dict)
            else {},
            "autonomy_surface": dict(planner_decision.get("autonomy_surface", {}))
            if isinstance(planner_decision.get("autonomy_surface"), dict)
            else {},
            "autonomy_boundary": dict(planner_decision.get("autonomy_boundary", {}))
            if isinstance(planner_decision.get("autonomy_boundary"), dict)
            else {},
            "planner_reasoning": dict(planner_decision.get("planner_reasoning", {}))
            if isinstance(planner_decision.get("planner_reasoning"), dict)
            else {},
            "delegation_contract": dict(planner_decision.get("delegation_contract", {}))
            if isinstance(planner_decision.get("delegation_contract"), dict)
            else {},
            "operator_control": dict(planner_decision.get("operator_control", {}))
            if isinstance(planner_decision.get("operator_control"), dict)
            else {},
            "tool_workflow_plan": dict(planner_decision.get("tool_workflow_plan", {}))
            if isinstance(planner_decision.get("tool_workflow_plan"), dict)
            else {},
            "route_planner_intent": dict(path_selection.get("planner_intent", {}))
            if isinstance(path_selection.get("planner_intent"), dict)
            else {},
        },
        "default_path": path_selection.get("default_path"),
        "operating_boundary": path_selection.get("operating_boundary"),
        "selection_reason": path_selection.get("selection_reason"),
        "handoff_reason_code": path_selection.get("handoff_reason_code"),
        "fallback_reason_code": path_selection.get("fallback_reason_code"),
        "native_coverage_class": path_selection.get("native_coverage_class"),
        "learning_consumed": path_selection.get("learning_consumed"),
        "learning_source_count": path_selection.get("learning_source_count"),
        "route_planner_intent": dict(path_selection.get("planner_intent", {}))
        if isinstance(path_selection.get("planner_intent"), dict)
        else {},
        "adapter_family": adapter_contract.get("adapter_family"),
        "adapter_agent_kind": adapter_contract.get("agent_kind"),
        "adapter_capability_surface_format": capability_surface.get("format"),
        "adapter_capability_surface": adapter_capability_surface,
        "adapter_capability": _adapter_capability_summary(
            adapter_contract,
            adapter_capability_surface=adapter_capability_surface,
        ),
        "adapter_governance_shared": capability_surface.get("governance", {}).get("fallback_governed")
        if isinstance(capability_surface.get("governance"), dict)
        else None,
        "adapter_hot_plug_supported": capability_surface.get("governance", {}).get("hot_plug_supported")
        if isinstance(capability_surface.get("governance"), dict)
        else None,
        "adapter_comparison_mode": capability_surface.get("comparability", {}).get("comparison_mode")
        if isinstance(capability_surface.get("comparability"), dict)
        else None,
        "adapter_evidence_outputs": capability_surface.get("evidence_outputs", [])
        if isinstance(capability_surface.get("evidence_outputs"), list)
        else [],
        "adapter_recovery_surfaces": capability_surface.get("recovery_surfaces", [])
        if isinstance(capability_surface.get("recovery_surfaces"), list)
        else [],
        "adapter_shared_contract": {
            "adapter_family": adapter_contract.get("adapter_family"),
            "agent_kind": adapter_contract.get("agent_kind"),
            "comparison_mode": capability_surface.get("comparability", {}).get("comparison_mode")
            if isinstance(capability_surface.get("comparability"), dict)
            else None,
            "default_path": path_selection.get("default_path"),
            "operating_boundary": path_selection.get("operating_boundary"),
            "approval_required": capability_surface.get("approval_semantics", {}).get("approval_required")
            if isinstance(capability_surface.get("approval_semantics"), dict)
            else None,
            "approval_pause_supported": capability_surface.get("approval_semantics", {}).get("approval_pause_supported")
            if isinstance(capability_surface.get("approval_semantics"), dict)
            else None,
            "hot_plug_supported": capability_surface.get("governance", {}).get("hot_plug_supported")
            if isinstance(capability_surface.get("governance"), dict)
            else None,
            "fallback_governed": capability_surface.get("governance", {}).get("fallback_governed")
            if isinstance(capability_surface.get("governance"), dict)
            else None,
            "evidence_outputs": list(adapter_contract.get("evidence_outputs", [])),
            "recovery_surfaces": list(adapter_contract.get("recovery_surfaces", [])),
            "recovery_contract": dict(capability_surface.get("shared_contract", {}).get("recovery_contract", {}))
            if isinstance(capability_surface.get("shared_contract"), dict)
            else {},
            "shared_contract_format": capability_surface.get("shared_contract", {}).get("format")
            if isinstance(capability_surface.get("shared_contract"), dict)
            else None,
            "shared_contract_resume_supported": capability_surface.get("shared_contract", {}).get("continuity_support", {}).get("resume_contract")
            if isinstance(capability_surface.get("shared_contract"), dict)
            and isinstance(capability_surface.get("shared_contract", {}).get("continuity_support"), dict)
            else None,
        },
        "kernel_role": kernel_contract.get("kernel_role"),
        "kernel_state_authority": kernel_contract.get("state_authority"),
        "kernel_output_surfaces": list(kernel_contract.get("output_surfaces", []))
        if isinstance(kernel_contract.get("output_surfaces"), list)
        else [],
        "step_loop_model": step_loop_contract.get("loop_model"),
        "step_loop_status": step_loop_contract.get("status"),
        "step_loop_stage": step_loop_contract.get("current_stage"),
        "step_loop_disposition": step_loop_contract.get("current_disposition"),
        "step_loop_resume_supported": step_loop_contract.get("resume_supported"),
        "step_loop_context_surfaces": required_surfaces,
        "session_resume_kind": continuity_contract.get("resume_kind"),
        "session_compaction_stage": continuity_contract.get("compaction_stage"),
        "session_masked_observation_count": continuity_contract.get("masked_observation_count"),
        "session_long_horizon_posture": continuity_contract.get("long_horizon_posture", {}),
        "session_continuity_snapshot": continuity_contract.get("continuity_snapshot", {}),
        "resume_contract": payload.get("resume_contract", {})
        if isinstance(payload.get("resume_contract"), dict)
        else {},
        "session_productization_surface": productization_surface,
        "session_comparative_digest": (
            comparative_benchmark_digest
            if isinstance(comparative_benchmark_digest, dict) and comparative_benchmark_digest
            else productization_surface.get("comparative_benchmark_digest", {})
            if isinstance(productization_surface.get("comparative_benchmark_digest"), dict)
            else continuity_contract.get("comparative_benchmark_digest", {})
            if isinstance(continuity_contract.get("comparative_benchmark_digest"), dict)
            else {}
        ),
        "shared_productization_surface": shared_productization_surface,
        "comparative_benchmark": comparative_benchmark,
        "comparative_benchmark_digest": comparative_benchmark_digest
        or _comparative_benchmark_digest(comparative_benchmark),
        "compacted_context_summary": compacted_context_summary,
        "program_posture": continuity_contract.get("program_posture", {}),
        "delegation_contract": continuity_contract.get("delegation_contract", {}),
        "program_continuity": continuity_contract.get("program_continuity", {}),
        "daily_driver_readiness": daily_driver_readiness,
        "daily_driver_main_path_ready": daily_driver_readiness.get("daily_driver_main_path_ready"),
        "milestone_verification": continuity_contract.get("milestone_verification", {}),
        "operator_control": continuity_contract.get("operator_control", {}),
        "runtime_duration_seconds": _runtime_duration_seconds(payload),
        "runtime_cost_measurement_status": _runtime_cost_measurement_status(payload),
        "step_loop_context_refs": context_engineering_refs.get("trace_refs", {})
        if isinstance(context_engineering_refs.get("trace_refs"), dict)
        else {},
        "context_engineering_contract_format": context_engineering_contract.get("format"),
        "context_engineering_main_path_required": context_engineering_contract.get("main_path_required"),
        "context_select_strategy": context_engineering_contract.get("select", {}).get("deterministic_strategy")
        if isinstance(context_engineering_contract.get("select"), dict)
        else None,
        "context_compaction_stage": context_engineering_contract.get("compact", {}).get("stage")
        if isinstance(context_engineering_contract.get("compact"), dict)
        else None,
        "context_isolation_strategy": context_engineering_contract.get("isolate", {}).get("strategy")
        if isinstance(context_engineering_contract.get("isolate"), dict)
        else None,
        "context_isolation_reinjection_mode": context_engineering_contract.get("isolate", {}).get("reinjection_mode")
        if isinstance(context_engineering_contract.get("isolate"), dict)
        else None,
        "native_runtime_only": native_task_proof.get("native_runtime_only"),
        "external_coding_agent_required": native_task_proof.get("external_coding_agent_required"),
        "task_class": native_task_proof.get("task_class"),
        "proof_scenario": native_task_proof.get("proof_scenario"),
        "closure_status": native_task_proof.get("closure_status"),
        "proof_artifact_count": native_task_proof.get("artifact_count"),
        "proof_event_count": native_task_proof.get("event_count"),
        "repo_task_acceptance_ready": repo_task_acceptance_ready,
        "repo_task_acceptance_passed_checks": native_repo_task_acceptance.get("passed_check_count"),
        "repo_task_acceptance_total_checks": native_repo_task_acceptance.get("total_check_count"),
        "closure_strength": (
            program_continuity.get("closure_strength")
            if program_continuity.get("closure_strength") in {
                "runtime_closure_only",
                "repo_task_acceptance_ready",
                "long_chain_native_first_ready",
            }
            else "long_chain_native_first_ready"
            if repo_task_acceptance_ready is True
            and native_complex_repo_task_acceptance.get("complex_repo_task_ready") is True
            else "repo_task_acceptance_ready"
            if repo_task_acceptance_ready is True
            else "runtime_closure_only"
        ),
        "complex_repo_task_acceptance_ready": native_complex_repo_task_acceptance.get("complex_repo_task_ready"),
        "complex_repo_task_acceptance_passed_checks": native_complex_repo_task_acceptance.get("passed_check_count"),
        "complex_repo_task_acceptance_total_checks": native_complex_repo_task_acceptance.get("total_check_count"),
        "long_chain_native_first_ready": (
            program_continuity.get("long_chain_native_first_ready")
            if isinstance(program_continuity.get("long_chain_native_first_ready"), bool)
            else bool(
                repo_task_acceptance_ready is True
                and native_complex_repo_task_acceptance.get("complex_repo_task_ready") is True
            )
        ),
        "verification_status": verification.get("status"),
        "verification_failure_kind": verification.get("failure_kind"),
        "repair_attempt_count": repair_summary.get("attempt_count", len(attempt_memory)),
        "repair_outcome": repair_summary.get("outcome"),
        "recovery_action": recovery_summary.get("action"),
        "recovery_reason": recovery_summary.get("reason"),
        "human_review_recommended": recovery_summary.get("human_review_recommended"),
        "native_tool_surface": payload.get("native_tool_surface", {}),
        "native_tool_workflow_surface": (
            payload.get("native_tool_workflow_surface", {})
            if isinstance(payload.get("native_tool_workflow_surface"), dict)
            else (
                payload.get("native_tool_surface", {}).get("workflow_surface", {})
                if isinstance(payload.get("native_tool_surface"), dict)
                and isinstance(payload.get("native_tool_surface", {}).get("workflow_surface"), dict)
                else {}
            )
        ),
        "native_tool_productization_surface": tool_productization_surface,
        "adapter_execution_fact": payload.get("adapter_execution_fact", {})
        if isinstance(payload.get("adapter_execution_fact"), dict)
        else {},
        "native_tool_evidence": payload.get("native_tool_evidence", {})
        if isinstance(payload.get("native_tool_evidence"), dict)
        else {},
        "native_tool_trace": payload.get("native_tool_trace", {}),
        "native_tool_trace_count": len(payload.get("native_tool_trace", {}).get("trace", []))
        if isinstance(payload.get("native_tool_trace"), dict) and isinstance(payload.get("native_tool_trace", {}).get("trace"), list)
        else 0,
        "native_exploration": {
            "existing_path_count": len(repo_report.get("existing_paths", [])) if isinstance(repo_report.get("existing_paths"), list) else 0,
            "candidate_path_count": len(repo_report.get("candidate_paths", [])) if isinstance(repo_report.get("candidate_paths"), list) else 0,
            "file_count": repo_report.get("file_count"),
            "candidate_reason": (
                repo_report.get("artifact", {}).get("exploration_profile", {}).get("candidate_reason")
                if isinstance(repo_report.get("artifact"), dict)
                and isinstance(repo_report.get("artifact", {}).get("exploration_profile"), dict)
                else None
            ),
            "selected_candidates": (
                list(repo_report.get("artifact", {}).get("exploration_profile", {}).get("selected_candidates", []))
                if isinstance(repo_report.get("artifact"), dict)
                and isinstance(repo_report.get("artifact", {}).get("exploration_profile"), dict)
                and isinstance(repo_report.get("artifact", {}).get("exploration_profile", {}).get("selected_candidates"), list)
                else []
            ),
            "repo_map_directory_count": (
                repo_report.get("artifact", {}).get("repo_map", {}).get("directory_count")
                if isinstance(repo_report.get("artifact"), dict) and isinstance(repo_report.get("artifact", {}).get("repo_map"), dict)
                else None
            ),
            "exploration_evidence": (
                dict(repo_report.get("artifact", {}).get("exploration_evidence", {}))
                if isinstance(repo_report.get("artifact"), dict)
                and isinstance(repo_report.get("artifact", {}).get("exploration_evidence"), dict)
                else {}
            ),
            "repository_understanding": (
                dict(repo_report.get("artifact", {}).get("repository_understanding", {}))
                if isinstance(repo_report.get("artifact"), dict)
                and isinstance(repo_report.get("artifact", {}).get("repository_understanding"), dict)
                else {}
            ),
        },
        "repository_understanding": (
            dict(payload.get("repository_understanding", {}))
            if isinstance(payload.get("repository_understanding"), dict)
            else dict(repo_report.get("artifact", {}).get("repository_understanding", {}))
            if isinstance(repo_report.get("artifact"), dict)
            and isinstance(repo_report.get("artifact", {}).get("repository_understanding"), dict)
            else {}
        ),
        "adapter_shared_contract": adapter_shared_contract,
        "adapter_productization_surface": adapter_productization_surface,
    }


def _default_context_surfaces_for_step_kind(step_kind: str | None) -> list[str]:
    if step_kind == "repo_exploration":
        return ["write", "select", "structured_observation"]
    if step_kind == "edit_execution":
        return ["write", "select", "structured_observation", "isolate"]
    if step_kind == "verification":
        return ["select", "structured_observation", "compact", "resume_continuity"]
    return []


def _runtime_duration_seconds(payload: dict[str, object]) -> float | None:
    continuity_contract = (
        payload.get("session_continuity_contract", {})
        if isinstance(payload.get("session_continuity_contract"), dict)
        else {}
    )
    if continuity_contract.get("runtime_duration_seconds") is not None:
        value = continuity_contract.get("runtime_duration_seconds")
        return float(value) if isinstance(value, (int, float)) else None
    artifact_summary = payload.get("native_tool_trace", {}) if isinstance(payload.get("native_tool_trace"), dict) else {}
    trace = artifact_summary.get("trace", []) if isinstance(artifact_summary.get("trace"), list) else []
    timestamps = [
        entry.get("timestamp")
        for entry in trace
        if isinstance(entry, dict)
    ]
    valid: list[datetime] = []
    for value in timestamps:
        if not isinstance(value, str):
            continue
        try:
            valid.append(datetime.fromisoformat(value))
        except ValueError:
            continue
    if len(valid) < 2:
        return None
    return round((max(valid) - min(valid)).total_seconds(), 6)


def _runtime_cost_measurement_status(payload: dict[str, object]) -> str:
    continuity_contract = (
        payload.get("session_continuity_contract", {})
        if isinstance(payload.get("session_continuity_contract"), dict)
        else {}
    )
    status = continuity_contract.get("usage_cost_measurement_status")
    return str(status) if isinstance(status, str) and status else "placeholder"


def _session_productization_surface(continuity_contract: dict[str, object]) -> dict[str, object]:
    return derive_session_productization_surface(continuity_contract)


def _native_tool_productization_surface(payload: dict[str, object]) -> dict[str, object]:
    return derive_native_tool_productization_surface(
        native_tool_surface=payload.get("native_tool_surface", {})
        if isinstance(payload.get("native_tool_surface"), dict)
        else {},
        native_tool_trace=payload.get("native_tool_trace", {})
        if isinstance(payload.get("native_tool_trace"), dict)
        else {},
        native_tool_productization_surface=payload.get("native_tool_productization_surface", {})
        if isinstance(payload.get("native_tool_productization_surface"), dict)
        else {},
    )


def _adapter_productization_surface(payload: dict[str, object]) -> dict[str, object]:
    surface = (
        payload.get("adapter_productization_surface", {})
        if isinstance(payload.get("adapter_productization_surface"), dict)
        else {}
    )
    if surface:
        return surface
    adapter_shared_contract = (
        payload.get("adapter_shared_contract", {})
        if isinstance(payload.get("adapter_shared_contract"), dict)
        else {}
    )
    if not adapter_shared_contract:
        adapter_contract = payload.get("adapter_contract", {}) if isinstance(payload.get("adapter_contract"), dict) else {}
        capability_surface = (
            adapter_contract.get("capability_surface", {})
            if isinstance(adapter_contract.get("capability_surface"), dict)
            else {}
        )
        shared_contract = (
            capability_surface.get("shared_contract", {})
            if isinstance(capability_surface.get("shared_contract"), dict)
            else {}
        )
        path_selection = payload.get("path_selection", {}) if isinstance(payload.get("path_selection"), dict) else {}
        adapter_shared_contract = {
            "adapter_family": adapter_contract.get("adapter_family"),
            "agent_kind": adapter_contract.get("agent_kind"),
            "comparison_mode": capability_surface.get("comparability", {}).get("comparison_mode")
            if isinstance(capability_surface.get("comparability"), dict)
            else None,
            "default_path": path_selection.get("default_path"),
            "operating_boundary": path_selection.get("operating_boundary"),
            "approval_required": adapter_contract.get("approval_semantics", {}).get("approval_required")
            if isinstance(adapter_contract.get("approval_semantics"), dict)
            else None,
            "approval_pause_supported": adapter_contract.get("approval_semantics", {}).get("approval_pause_supported")
            if isinstance(adapter_contract.get("approval_semantics"), dict)
            else None,
            "hot_plug_supported": capability_surface.get("governance", {}).get("hot_plug_supported")
            if isinstance(capability_surface.get("governance"), dict)
            else None,
            "fallback_governed": capability_surface.get("governance", {}).get("fallback_governed")
            if isinstance(capability_surface.get("governance"), dict)
            else None,
            "evidence_outputs": list(adapter_contract.get("evidence_outputs", []))
            if isinstance(adapter_contract.get("evidence_outputs"), list)
            else [],
            "recovery_surfaces": list(adapter_contract.get("recovery_surfaces", []))
            if isinstance(adapter_contract.get("recovery_surfaces"), list)
            else [],
            "recovery_contract": dict(shared_contract.get("recovery_contract", {}))
            if isinstance(shared_contract.get("recovery_contract"), dict)
            else {},
            "shared_contract_format": shared_contract.get("format"),
            "shared_contract_resume_supported": shared_contract.get("continuity_support", {}).get("resume_contract")
            if isinstance(shared_contract.get("continuity_support"), dict)
            else None,
        }
    return derive_adapter_productization_surface(adapter_shared_contract=adapter_shared_contract)


def _compacted_context_summary(compressed_context: dict[str, object]) -> dict[str, object]:
    if not isinstance(compressed_context, dict) or not compressed_context:
        return {}
    summarized_history = (
        compressed_context.get("summarized_history", {})
        if isinstance(compressed_context.get("summarized_history"), dict)
        else {}
    )
    completed_steps = (
        list(summarized_history.get("completed_steps", []))
        if isinstance(summarized_history.get("completed_steps"), list)
        else []
    )
    pending_steps = (
        list(summarized_history.get("pending_steps", []))
        if isinstance(summarized_history.get("pending_steps"), list)
        else []
    )
    blocked_steps = (
        list(summarized_history.get("blocked_steps", []))
        if isinstance(summarized_history.get("blocked_steps"), list)
        else []
    )
    return {
        "objective": compressed_context.get("objective"),
        "current_status": compressed_context.get("current_status"),
        "latest_recovery_hint": compressed_context.get("latest_recovery_hint"),
        "compaction_stage": summarized_history.get("compaction_stage"),
        "masked_observation_count": summarized_history.get("masked_observation_count"),
        "summarization_triggered": summarized_history.get("summarization_triggered"),
        "observation_count": summarized_history.get("observation_count"),
        "selected_memory_count": summarized_history.get("selected_memory_count"),
        "artifact_count": summarized_history.get("artifact_count"),
        "completed_step_count": len(completed_steps),
        "pending_step_count": len(pending_steps),
        "blocked_step_count": len(blocked_steps),
    }


def _adapter_capability_summary(
    adapter_contract: dict[str, object],
    *,
    adapter_capability_surface: dict[str, object] | None = None,
) -> dict[str, object]:
    if not isinstance(adapter_capability_surface, dict) or not adapter_capability_surface:
        adapter_capability_surface = (
            adapter_contract.get("capability_surface", {})
            if isinstance(adapter_contract.get("capability_surface"), dict)
            else {}
        )
    return derive_adapter_capability_summary(
        adapter_contract=adapter_contract,
        adapter_capability_surface=adapter_capability_surface,
    )


def _job_card(job: dict[str, object], jobs_root: Path | None = None) -> dict[str, object]:
    metadata = job.get("metadata", {}) if isinstance(job.get("metadata"), dict) else {}
    job_id = str(job.get("id") or "")
    stdout = str(job.get("stdout") or "")
    stderr = str(job.get("stderr") or "")
    error = str(job.get("error") or "")
    log_text = ""
    if job_id and jobs_root and (jobs_root / f"{job_id}.log").exists():
        log_text = (jobs_root / f"{job_id}.log").read_text(encoding="utf-8")
    return {
        "id": job_id,
        "task_id": job.get("task_id"),
        "provider": job.get("provider"),
        "model": job.get("model"),
        "kind": job.get("kind"),
        "status": job.get("status"),
        "phase": job.get("phase"),
        "summary": job.get("summary"),
        "error": job.get("error"),
        "pid": job.get("pid"),
        "exit_code": job.get("exit_code"),
        "session_id": job.get("session_id"),
        "thread_id": job.get("thread_id"),
        "command": job.get("command", []),
        "stdout": job.get("stdout"),
        "stderr": job.get("stderr"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "updated_at": job.get("updated_at"),
        "log_available": bool(log_text),
        "output_preview": _output_preview(stdout=stdout, stderr=stderr, error=error),
        "terminal_ref": metadata.get("terminal_ref"),
        "attach_available": bool(metadata.get("attach_available", False)),
        "last_log_excerpt": _log_excerpt(log_text),
        "last_seen_at": job.get("updated_at") or job.get("completed_at") or job.get("started_at"),
        "operation": _job_operation(job),
        "runtime_fidelity": {
            "format": "agent_orchestrator.provider_session_snapshot.v1",
            "liveness": {
                "state": "terminal" if job.get("status") in {"completed", "failed", "cancelled"} else "running" if job.get("pid") else "unknown",
                "terminal": job.get("status") in {"completed", "failed", "cancelled"},
                "last_seen_at": job.get("updated_at") or job.get("completed_at") or job.get("started_at"),
            },
            "operation_support": {
                "send": "already_terminal" if job.get("status") in {"completed", "failed", "cancelled"} else "available",
                "cancel": "already_terminal" if job.get("status") in {"completed", "failed", "cancelled"} else "available",
                "attach": "available" if metadata.get("attach_available") else "unavailable",
                "continue": "unavailable" if job.get("status") in {"completed", "failed", "cancelled"} else "available",
            },
            "last_operation_receipt": _job_operation(job),
            "read_only": True,
        },
    }


def _job_operation(job: dict[str, object]) -> dict[str, object] | None:
    parsed = job.get("parsed_payload", {}) if isinstance(job.get("parsed_payload"), dict) else {}
    operation = parsed.get("operation") if isinstance(parsed, dict) else None
    return operation if isinstance(operation, dict) else None


def _missing_job_operation(job_id: str, action: str) -> dict[str, object]:
    return {
        "id": job_id,
        "status": "missing",
        "operation": {
            "action": action,
            "status": "session_missing",
            "reason": "session_missing",
            "detail": f"Job {job_id} is not available.",
        },
    }


def _output_preview(*, stdout: str, stderr: str, error: str) -> str:
    text = error or stderr or stdout
    return text.strip().replace("\n", " ")[:180]


def _log_excerpt(text: str) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " ".join(lines[-3:])[:240]


def build_dashboard_service(
    *,
    plans_root: str = ".agent_orchestrator/plans",
    runs_root: str = ".agent_orchestrator/runs",
    jobs_root: str = ".agent_orchestrator/jobs",
    runtime: str = "mock",
    provider: str | None = None,
) -> DashboardService:
    from agent_orchestrator.cli import _build_team_orchestrator

    team_runtime = "mock" if runtime == "tmux" else runtime
    team = _build_team_orchestrator(team_runtime, provider, plans_root, runs_root)
    job_runtime = TmuxJobRuntime(root=jobs_root) if runtime == "tmux" else FileJobRuntime(root=jobs_root)
    return DashboardService(team=team, plans_root=plans_root, runs_root=runs_root, jobs_root=jobs_root, job_runtime=job_runtime)
