"""Workspace state and index models for the control plane."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, dataclasses, pathlib
# RESPONSIBILITY: Model workspace state snapshots and persist workspace index artifact references.
# MODULE: decision_core
# ---

from dataclasses import dataclass, field
from pathlib import Path

from agent_orchestrator.control_plane_artifacts import artifact_ref as _artifact_ref
from agent_orchestrator.control_plane_artifacts import atomic_write_json as _atomic_write_json
from agent_orchestrator.control_plane_artifacts import read_json_object as _read_json_object
from agent_orchestrator.control_plane_constants import CONTROL_PLANE_FORMATS
from agent_orchestrator.jobs import now_iso


@dataclass(frozen=True, slots=True)
class WorkspaceStateSnapshot:
    project_root: str
    plans: list[dict[str, object]]
    runs: list[dict[str, object]]
    jobs: list[dict[str, object]]
    evidence: dict[str, object]
    approvals: list[dict[str, object]]
    provider_health: dict[str, object] | None
    dirty_state: dict[str, object]
    memory_digest: dict[str, object]
    external_cache: dict[str, object]
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, object]:
        return {
            "format": CONTROL_PLANE_FORMATS["workspace_state"],
            "project_root": self.project_root,
            "plans": list(self.plans),
            "runs": list(self.runs),
            "jobs": list(self.jobs),
            "evidence": dict(self.evidence),
            "approvals": list(self.approvals),
            "provider_health": self.provider_health,
            "dirty_state": dict(self.dirty_state),
            "memory_digest": dict(self.memory_digest),
            "external_cache": dict(self.external_cache),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "WorkspaceStateSnapshot":
        return cls(
            project_root=str(data.get("project_root") or ""),
            plans=[dict(item) for item in data.get("plans", []) if isinstance(item, dict)],
            runs=[dict(item) for item in data.get("runs", []) if isinstance(item, dict)],
            jobs=[dict(item) for item in data.get("jobs", []) if isinstance(item, dict)],
            evidence=dict(data.get("evidence", {})) if isinstance(data.get("evidence"), dict) else {},
            approvals=[dict(item) for item in data.get("approvals", []) if isinstance(item, dict)],
            provider_health=dict(data.get("provider_health", {})) if isinstance(data.get("provider_health"), dict) else None,
            dirty_state=dict(data.get("dirty_state", {})) if isinstance(data.get("dirty_state"), dict) else {},
            memory_digest=dict(data.get("memory_digest", {})) if isinstance(data.get("memory_digest"), dict) else {},
            external_cache=dict(data.get("external_cache", {})) if isinstance(data.get("external_cache"), dict) else {},
            created_at=str(data.get("created_at") or now_iso()),
        )


@dataclass(slots=True)
class WorkspaceIndexStore:
    root: Path | str = ".agent_orchestrator/workspace"

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self.root / "index.json"

    def write(self, snapshot: WorkspaceStateSnapshot) -> dict[str, object]:
        existing = _read_json_object(self.path)
        artifacts = existing.get("artifacts", {}) if isinstance(existing.get("artifacts"), dict) else {}
        payload = workspace_index_payload(
            snapshot,
            artifacts={
                **artifacts,
                "workspace_state": _artifact_ref(snapshot.to_dict()),
            },
        )
        return _atomic_write_json(self.path, payload)

    def write_index(self, payload: dict[str, object]) -> dict[str, object]:
        return _atomic_write_json(self.path, payload)

    def payload(self) -> dict[str, object] | None:
        payload = _read_json_object(self.path)
        return payload or None

    def record_artifact(self, name: str, payload: dict[str, object]) -> dict[str, object]:
        existing = _read_json_object(self.path)
        artifacts = existing.get("artifacts", {}) if isinstance(existing.get("artifacts"), dict) else {}
        workspace_state = existing.get("workspace_state") if isinstance(existing.get("workspace_state"), dict) else None
        if workspace_state is None and existing.get("format") == CONTROL_PLANE_FORMATS["workspace_state"]:
            workspace_state = existing
        index_payload = {
            "format": CONTROL_PLANE_FORMATS["workspace_index"],
            "workspace_state": workspace_state,
            "artifacts": {
                **artifacts,
                name: _artifact_ref(payload),
            },
            "updated_at": now_iso(),
        }
        if isinstance(workspace_state, dict):
            index_payload.update(
                workspace_index_optional_sections(
                    WorkspaceStateSnapshot.from_dict(workspace_state),
                    artifacts=index_payload["artifacts"],
                )
            )
        return _atomic_write_json(self.path, index_payload)

    def read(self) -> WorkspaceStateSnapshot | None:
        if not self.path.exists():
            return None
        payload = _read_json_object(self.path)
        if not payload:
            return None
        if payload.get("format") == CONTROL_PLANE_FORMATS["workspace_index"]:
            workspace_state = payload.get("workspace_state")
            return WorkspaceStateSnapshot.from_dict(workspace_state) if isinstance(workspace_state, dict) else None
        return WorkspaceStateSnapshot.from_dict(payload) if isinstance(payload, dict) else None


def workspace_index_payload(
    snapshot: WorkspaceStateSnapshot,
    *,
    artifacts: dict[str, object],
) -> dict[str, object]:
    payload = {
        "format": CONTROL_PLANE_FORMATS["workspace_index"],
        "workspace_state": snapshot.to_dict(),
        "artifacts": artifacts,
        "updated_at": now_iso(),
    }
    payload.update(workspace_index_optional_sections(snapshot, artifacts=artifacts))
    return payload


def workspace_index_optional_sections(
    snapshot: WorkspaceStateSnapshot,
    *,
    artifacts: dict[str, object],
) -> dict[str, object]:
    plans = list(snapshot.plans)
    active_plans = [plan for plan in plans if str(plan.get("status")) not in {"completed", "cancelled", "failed"}]
    approvals = list(snapshot.approvals)
    open_approvals = [item for item in approvals if str(item.get("status")) == "pending"]
    recent_runs = list(snapshot.runs)[:10]
    memory_recent = (
        list(snapshot.memory_digest.get("recent", []))
        if isinstance(snapshot.memory_digest.get("recent", []), list)
        else []
    )
    provider_health = snapshot.provider_health or {
        "runtime_mode": "unknown",
        "available": None,
        "status": "not_checked",
        "degraded_reason": None,
    }
    return {
        "program": {
            "kind": "workspace_program",
            "name": Path(snapshot.project_root).name or "workspace",
            "project_root": snapshot.project_root,
            "active_plan_count": len(active_plans),
            "open_approval_count": len(open_approvals),
            "recent_run_count": len(recent_runs),
        },
        "active_artifacts": {
            "workspace_state": artifacts.get("workspace_state"),
            "context_packet": artifacts.get("context_packet"),
            "strategy_decision": artifacts.get("strategy_decision"),
            "topology_snapshot": artifacts.get("topology_snapshot"),
            "approval_queue": artifacts.get("approval_queue"),
            "run_ledger": artifacts.get("run_ledger"),
            "recovery_timeline": artifacts.get("recovery_timeline"),
            "runtime_event_stream": artifacts.get("runtime_event_stream"),
            "provider_session_snapshot": artifacts.get("provider_session_snapshot"),
            "recovery_recommendation": artifacts.get("recovery_recommendation"),
            "evidence_bundle": artifacts.get("evidence_bundle"),
        },
        "recent_artifacts": [
            {"name": name, "ref": ref}
            for name, ref in sorted(artifacts.items())
            if isinstance(name, str)
        ][-10:],
        "open_approvals": open_approvals,
        "recent_runs": recent_runs,
        "memory_candidates": [
            {
                "record_type": record.get("record_type"),
                "namespace": record.get("namespace"),
                "summary": record.get("summary"),
                "provenance": record.get("provenance", {}),
                "source": "memory_digest",
            }
            for record in memory_recent
            if isinstance(record, dict)
        ],
        "provider_runtime_health": provider_health,
    }


def workspace_recovery_dashboard(
    *,
    recovery_timeline: dict[str, object],
    runtime_events: dict[str, object],
    recovery_recommendation: dict[str, object] | None,
) -> dict[str, object]:
    timeline_summary = recovery_timeline.get("summary", {}) if isinstance(recovery_timeline.get("summary"), dict) else {}
    runtime_summary = runtime_events.get("summary", {}) if isinstance(runtime_events.get("summary"), dict) else {}
    blocking_summary = (
        timeline_summary.get("blocking_summary", {})
        if isinstance(timeline_summary.get("blocking_summary"), dict)
        else {}
    )
    return {
        "recovery_timeline": {
            "format": recovery_timeline.get("format"),
            "summary": timeline_summary,
            "read_only": True,
        },
        "runtime_events": {
            "format": runtime_events.get("format"),
            "summary": runtime_summary,
            "read_only": True,
        },
        "runtime_fidelity": {
            "provider_session_snapshot_count": len(runtime_events.get("provider_session_snapshots", []))
            if isinstance(runtime_events.get("provider_session_snapshots"), list)
            else 0,
            "operation_receipt_count": len(runtime_events.get("operation_receipts", []))
            if isinstance(runtime_events.get("operation_receipts"), list)
            else 0,
            "live_session_count": runtime_summary.get("live_session_count", 0),
            "missing_session_count": runtime_summary.get("missing_session_count", 0),
            "read_only": True,
        },
        "recovery_recommendation": recovery_recommendation,
        "blocking_summary": blocking_summary,
        "resume_hint": timeline_summary.get("resume_hint"),
        "last_checkpoint": timeline_summary.get("last_checkpoint"),
    }
