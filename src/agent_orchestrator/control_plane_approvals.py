"""Approval item models and persistence for the control plane."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, dataclasses, json, pathlib, typing
# RESPONSIBILITY: Model approval records and persist approval queue decisions.
# MODULE: decision_core
# ---

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Literal

from agent_orchestrator.control_plane_artifacts import stable_id as _stable_id
from agent_orchestrator.control_plane_constants import CONTROL_PLANE_FORMATS
from agent_orchestrator.jobs import now_iso

ApprovalStatus = Literal["pending", "approved", "rejected", "resolved"]
ApprovalReasonCode = Literal[
    "blocked_session",
    "awaiting_human_decision",
    "compliance_blocking",
    "provider_fallback",
    "rescue_reroute",
    "dirty_state_overlap",
    "external_cache_unavailable",
]


@dataclass(frozen=True, slots=True)
class ApprovalItem:
    id: str
    status: ApprovalStatus
    reason_code: ApprovalReasonCode
    reason: str
    scope: str
    scope_id: str
    recommended_action: str
    session_id: str | None = None
    run_id: str | None = None
    job_id: str | None = None
    work_unit_id: str | None = None
    plan_ref: str | None = None
    topology_ref: str | None = None
    run_ref: str | None = None
    job_ref: str | None = None
    evidence_ref: str | None = None
    memory_candidate_ref: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    resolved_at: str | None = None
    resolution_reason: str | None = None
    actor: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "format": CONTROL_PLANE_FORMATS["approval_item"],
            "id": self.id,
            "status": self.status,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "scope": self.scope,
            "scope_id": self.scope_id,
            "recommended_action": self.recommended_action,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "job_id": self.job_id,
            "work_unit_id": self.work_unit_id,
            "plan_ref": self.plan_ref,
            "topology_ref": self.topology_ref,
            "run_ref": self.run_ref,
            "job_ref": self.job_ref,
            "evidence_ref": self.evidence_ref,
            "memory_candidate_ref": self.memory_candidate_ref,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolution_reason": self.resolution_reason,
            "actor": self.actor,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ApprovalItem":
        return cls(
            id=str(data.get("id") or _stable_id("approval", str(data))),
            status=str(data.get("status") or "pending"),  # type: ignore[arg-type]
            reason_code=_approval_reason_code_from_payload(data),
            reason=str(data.get("reason") or ""),
            scope=str(data.get("scope") or "unknown"),
            scope_id=str(data.get("scope_id") or ""),
            recommended_action=str(data.get("recommended_action") or "inspect"),
            session_id=data.get("session_id") if isinstance(data.get("session_id"), str) else None,
            run_id=data.get("run_id") if isinstance(data.get("run_id"), str) else None,
            job_id=data.get("job_id") if isinstance(data.get("job_id"), str) else None,
            work_unit_id=data.get("work_unit_id") if isinstance(data.get("work_unit_id"), str) else None,
            plan_ref=data.get("plan_ref") if isinstance(data.get("plan_ref"), str) else None,
            topology_ref=data.get("topology_ref") if isinstance(data.get("topology_ref"), str) else None,
            run_ref=data.get("run_ref") if isinstance(data.get("run_ref"), str) else None,
            job_ref=data.get("job_ref") if isinstance(data.get("job_ref"), str) else None,
            evidence_ref=data.get("evidence_ref") if isinstance(data.get("evidence_ref"), str) else None,
            memory_candidate_ref=data.get("memory_candidate_ref") if isinstance(data.get("memory_candidate_ref"), str) else None,
            evidence_refs=[str(item) for item in data.get("evidence_refs", [])],
            created_at=str(data.get("created_at") or now_iso()),
            resolved_at=data.get("resolved_at") if isinstance(data.get("resolved_at"), str) else None,
            resolution_reason=data.get("resolution_reason") if isinstance(data.get("resolution_reason"), str) else None,
            actor=data.get("actor") if isinstance(data.get("actor"), str) else None,
        )

    def resolved(self, *, status: ApprovalStatus, reason: str, actor: str = "human") -> "ApprovalItem":
        return ApprovalItem(
            id=self.id,
            status=status,
            reason_code=self.reason_code,
            reason=self.reason,
            scope=self.scope,
            scope_id=self.scope_id,
            recommended_action=self.recommended_action,
            session_id=self.session_id,
            run_id=self.run_id,
            job_id=self.job_id,
            work_unit_id=self.work_unit_id,
            plan_ref=self.plan_ref,
            topology_ref=self.topology_ref,
            run_ref=self.run_ref,
            job_ref=self.job_ref,
            evidence_ref=self.evidence_ref,
            memory_candidate_ref=self.memory_candidate_ref,
            evidence_refs=list(self.evidence_refs),
            created_at=self.created_at,
            resolved_at=now_iso(),
            resolution_reason=reason,
            actor=actor,
        )


@dataclass(slots=True)
class ApprovalStore:
    root: Path | str = ".agent_orchestrator/approvals"

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self.root / "approvals.jsonl"

    def append(self, item: ApprovalItem) -> ApprovalItem:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")
        return item

    def list_all(self) -> list[ApprovalItem]:
        if not self.path.exists():
            return []
        items: list[ApprovalItem] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                items.append(ApprovalItem.from_dict(payload))
        return items

    def latest_by_id(self) -> dict[str, ApprovalItem]:
        latest: dict[str, ApprovalItem] = {}
        for item in self.list_all():
            latest[item.id] = item
        return latest


def _approval_reason_code_from_payload(data: dict[str, object]) -> ApprovalReasonCode:
    value = data.get("reason_code")
    allowed = {
        "blocked_session",
        "awaiting_human_decision",
        "compliance_blocking",
        "provider_fallback",
        "rescue_reroute",
        "dirty_state_overlap",
        "external_cache_unavailable",
    }
    if isinstance(value, str) and value in allowed:
        return value  # type: ignore[return-value]
    reason = str(data.get("reason") or "").lower()
    if "compliance" in reason:
        return "compliance_blocking"
    if "provider" in reason or "fallback" in reason:
        return "provider_fallback"
    if "rescue" in reason or "reroute" in reason:
        return "rescue_reroute"
    if "dirty" in reason:
        return "dirty_state_overlap"
    if "cache" in reason:
        return "external_cache_unavailable"
    if "human" in reason or "awaiting" in reason:
        return "awaiting_human_decision"
    return "blocked_session"
