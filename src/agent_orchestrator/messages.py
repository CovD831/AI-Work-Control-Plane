"""Structured agent-to-agent messages for team orchestration."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, dataclasses, json, pathlib, typing, uuid
# RESPONSIBILITY: Persist and route structured communication between agent roles.
# MODULE: interface
# ---

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent_orchestrator.jobs import now_iso


@dataclass(frozen=True, slots=True)
class TeamMessage:
    id: str
    session_id: str
    work_unit_id: str | None
    from_role: str
    to_role: str
    message_type: str
    content: str
    payload: dict[str, Any] = field(default_factory=dict)
    thread: str = "main"
    requires_response: bool = False
    status: str = "sent"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "work_unit_id": self.work_unit_id,
            "from_role": self.from_role,
            "to_role": self.to_role,
            "message_type": self.message_type,
            "content": self.content,
            "payload": self.payload,
            "thread": self.thread,
            "requires_response": self.requires_response,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "TeamMessage":
        return cls(
            id=str(data.get("id") or f"msg-{uuid4().hex[:8]}"),
            session_id=str(data.get("session_id") or ""),
            work_unit_id=data.get("work_unit_id") if isinstance(data.get("work_unit_id"), str) else None,
            from_role=str(data.get("from_role") or "unknown"),
            to_role=str(data.get("to_role") or "unknown"),
            message_type=str(data.get("message_type") or "note"),
            content=str(data.get("content") or ""),
            payload=dict(data.get("payload", {})) if isinstance(data.get("payload"), dict) else {},
            thread=str(data.get("thread") or _thread_from_payload(dict(data.get("payload", {})) if isinstance(data.get("payload"), dict) else {})),
            requires_response=bool(data.get("requires_response", False)),
            status=str(data.get("status") or "sent"),
            created_at=str(data.get("created_at") or now_iso()),
        )


@dataclass(slots=True)
class MessageStore:
    root: Path | str = ".agent_orchestrator/messages"

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def append(self, message: TeamMessage) -> TeamMessage:
        with self._messages_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")
        return message

    def create(
        self,
        *,
        session_id: str,
        from_role: str,
        to_role: str,
        message_type: str,
        content: str,
        work_unit_id: str | None = None,
        payload: dict[str, Any] | None = None,
        thread: str = "main",
        requires_response: bool = False,
        status: str = "sent",
    ) -> TeamMessage:
        return self.append(
            TeamMessage(
                id=f"msg-{uuid4().hex[:10]}",
                session_id=session_id,
                work_unit_id=work_unit_id,
                from_role=from_role,
                to_role=to_role,
                message_type=message_type,
                content=content,
                payload=payload or {},
                thread=thread,
                requires_response=requires_response,
                status=status,
            )
        )

    def query(
        self,
        *,
        session_id: str | None = None,
        from_role: str | None = None,
        to_role: str | None = None,
        message_type: str | None = None,
        work_unit_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        messages = self._read_all()
        if session_id is not None:
            messages = [message for message in messages if message.session_id == session_id]
        if from_role is not None:
            messages = [message for message in messages if message.from_role == from_role]
        if to_role is not None:
            messages = [message for message in messages if message.to_role == to_role]
        if message_type is not None:
            messages = [message for message in messages if message.message_type == message_type]
        if work_unit_id is not None:
            messages = [message for message in messages if message.work_unit_id == work_unit_id]
        return [message.to_dict() for message in messages[-limit:]][::-1]

    def list_for_session(self, session_id: str, *, limit: int = 100) -> list[dict[str, object]]:
        return self.query(session_id=session_id, limit=limit)

    def list_threads_for_session(self, session_id: str, *, limit: int = 200) -> dict[str, list[dict[str, object]]]:
        threads: dict[str, list[dict[str, object]]] = {}
        for message in self.query(session_id=session_id, limit=limit):
            threads.setdefault(str(message.get("thread") or "main"), []).append(message)
        return threads

    def list_for_role(self, session_id: str, role: str, *, direction: str = "both", limit: int = 100) -> list[dict[str, object]]:
        if direction == "inbox":
            return self.query(session_id=session_id, to_role=role, limit=limit)
        if direction == "outbox":
            return self.query(session_id=session_id, from_role=role, limit=limit)
        messages = [
            message
            for message in self._read_all()
            if message.session_id == session_id and role in {message.from_role, message.to_role}
        ]
        return [message.to_dict() for message in messages[-limit:]][::-1]

    @property
    def _messages_path(self) -> Path:
        return self.root / "messages.jsonl"

    def _read_all(self) -> list[TeamMessage]:
        path = self._messages_path
        if not path.exists():
            return []
        messages: list[TeamMessage] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                messages.append(TeamMessage.from_dict(payload))
        return messages


@dataclass(slots=True)
class MessageRouter:
    store: MessageStore

    def build_review_request(
        self,
        *,
        session_id: str,
        to_role: str,
        content: str,
        work_unit_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> TeamMessage:
        message_payload = _with_collaboration_payload(
            dict(payload or {}),
            object_type="proposal",
            session_id=session_id,
            from_role="lead",
            to_role=to_role,
            summary=content,
        )
        return self.store.create(
            session_id=session_id,
            work_unit_id=work_unit_id,
            from_role="lead",
            to_role=to_role,
            message_type="review_request",
            content=content,
            payload=message_payload,
            thread="review",
            requires_response=True,
        )

    def build_review_result(
        self,
        *,
        session_id: str,
        from_role: str,
        content: str,
        work_unit_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> TeamMessage:
        message_payload = _with_collaboration_payload(
            dict(payload or {}),
            object_type="critique",
            session_id=session_id,
            from_role=from_role,
            to_role="lead",
            summary=content,
        )
        return self.store.create(
            session_id=session_id,
            work_unit_id=work_unit_id,
            from_role=from_role,
            to_role="lead",
            message_type="review_result",
            content=content,
            payload=message_payload,
            thread="review",
            requires_response=False,
        )

    def build_handoff(
        self,
        *,
        session_id: str,
        from_role: str,
        to_role: str,
        content: str,
        work_unit_id: str | None = None,
        payload: dict[str, Any] | None = None,
        handoff_packet: dict[str, Any] | None = None,
        requires_response: bool = False,
    ) -> TeamMessage:
        message_payload = dict(payload or {})
        message_payload["handoff_packet"] = _normalize_handoff_packet(
            handoff_packet or message_payload.get("handoff_packet"),
            session_id=session_id,
            from_role=from_role,
            to_role=to_role,
            content=content,
            payload=message_payload,
        )
        message_payload = _with_collaboration_payload(
            message_payload,
            object_type="proposal",
            session_id=session_id,
            from_role=from_role,
            to_role=to_role,
            summary=content,
        )
        return self.store.create(
            session_id=session_id,
            work_unit_id=work_unit_id,
            from_role=from_role,
            to_role=to_role,
            message_type="handoff",
            content=content,
            payload=message_payload,
            thread=_thread_from_payload(message_payload),
            requires_response=requires_response,
        )

    def build_collaboration_object(
        self,
        *,
        session_id: str,
        from_role: str,
        to_role: str,
        object_type: str,
        content: str,
        work_unit_id: str | None = None,
        payload: dict[str, Any] | None = None,
        thread: str = "main",
        requires_response: bool = False,
    ) -> TeamMessage:
        message_payload = _with_collaboration_payload(
            dict(payload or {}),
            object_type=object_type,
            session_id=session_id,
            from_role=from_role,
            to_role=to_role,
            summary=content,
        )
        return self.store.create(
            session_id=session_id,
            work_unit_id=work_unit_id,
            from_role=from_role,
            to_role=to_role,
            message_type=object_type,
            content=content,
            payload=message_payload,
            thread=thread,
            requires_response=requires_response,
        )

    def build_direct_api_tool_trace(
        self,
        *,
        session_id: str,
        provider: str,
        tool_name: str,
        intent: str,
        result: str | None = None,
        fallback: dict[str, Any] | None = None,
        usage_cost: dict[str, Any] | None = None,
        work_unit_id: str | None = None,
    ) -> TeamMessage:
        payload = build_direct_api_tool_trace_payload(
            provider=provider,
            tool_name=tool_name,
            intent=intent,
            result=result,
            fallback=fallback,
            usage_cost=usage_cost,
        )
        return self.store.create(
            session_id=session_id,
            work_unit_id=work_unit_id,
            from_role=provider,
            to_role="control_plane",
            message_type="direct_api_tool_trace",
            content=intent,
            payload=payload,
            thread="governance",
            requires_response=False,
        )


def build_handoff_packet(
    *,
    session_id: str,
    from_role: str,
    to_role: str,
    summary: str,
    changes: list[str] | None = None,
    evidence: list[str] | None = None,
    risks: list[str] | None = None,
    blockers: list[str] | None = None,
    docs_context_snapshot_id: str | None = None,
    recommended_commands: list[str] | None = None,
    created_at: str | None = None,
) -> dict[str, object]:
    return {
        "format": "agent_orchestrator.handoff_packet.v1",
        "session_id": session_id,
        "from_role": from_role,
        "to_role": to_role,
        "summary": summary,
        "changes": list(changes or []),
        "evidence": list(evidence or []),
        "risks": list(risks or []),
        "blockers": list(blockers or []),
        "docs_context_snapshot_id": docs_context_snapshot_id,
        "recommended_commands": list(recommended_commands or []),
        "created_at": created_at or now_iso(),
    }


def build_direct_api_tool_trace_payload(
    *,
    provider: str,
    tool_name: str,
    intent: str,
    result: str | None = None,
    fallback: dict[str, Any] | None = None,
    usage_cost: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, object]:
    return {
        "format": "agent_orchestrator.direct_api_tool_trace.v1",
        "provider": provider,
        "runtime_mode": "direct_api",
        "tool_name": tool_name,
        "intent": intent,
        "result": result,
        "fallback": dict(fallback or {}),
        "usage_cost": {
            "available": False,
            "input_tokens": None,
            "output_tokens": None,
            "estimated_cost_usd": None,
            "source": "placeholder",
            **dict(usage_cost or {}),
        },
        "execution_policy": "record intent and result only; local file edits stay behind approved-plan runtime gates",
        "created_at": created_at or now_iso(),
    }


def build_collaboration_payload(
    *,
    object_type: str,
    session_id: str,
    from_role: str,
    to_role: str,
    summary: str,
    evidence: list[str] | None = None,
    blockers: list[str] | None = None,
    verdict: str | None = None,
    severity: str | None = None,
    next_steps: list[str] | None = None,
    refs: dict[str, object] | None = None,
    created_at: str | None = None,
) -> dict[str, object]:
    return {
        "format": "agent_orchestrator.collaboration_object.v1",
        "object_type": object_type,
        "session_id": session_id,
        "from_role": from_role,
        "to_role": to_role,
        "summary": summary,
        "evidence": list(evidence or []),
        "blockers": list(blockers or []),
        "verdict": verdict,
        "severity": severity,
        "next_steps": list(next_steps or []),
        "refs": dict(refs or {}),
        "created_at": created_at or now_iso(),
    }


def _normalize_handoff_packet(
    packet: object,
    *,
    session_id: str,
    from_role: str,
    to_role: str,
    content: str,
    payload: dict[str, Any],
) -> dict[str, object]:
    if isinstance(packet, dict):
        normalized = dict(packet)
        normalized.setdefault("format", "agent_orchestrator.handoff_packet.v1")
        normalized.setdefault("session_id", session_id)
        normalized.setdefault("from_role", from_role)
        normalized.setdefault("to_role", to_role)
        normalized.setdefault("summary", content)
        normalized.setdefault("changes", [])
        normalized.setdefault("evidence", [])
        normalized.setdefault("risks", [])
        normalized.setdefault("blockers", [])
        normalized.setdefault("docs_context_snapshot_id", payload.get("docs_context_snapshot_id"))
        normalized.setdefault("recommended_commands", payload.get("recommended_commands", []))
        normalized.setdefault("created_at", now_iso())
        return normalized
    return build_handoff_packet(
        session_id=session_id,
        from_role=from_role,
        to_role=to_role,
        summary=content,
        changes=_list_payload(payload, "changes"),
        evidence=_list_payload(payload, "evidence"),
        risks=_list_payload(payload, "risks"),
        blockers=_list_payload(payload, "blockers"),
        docs_context_snapshot_id=_string_payload(payload, "docs_context_snapshot_id"),
        recommended_commands=_list_payload(payload, "recommended_commands"),
    )


def _with_collaboration_payload(
    payload: dict[str, Any],
    *,
    object_type: str,
    session_id: str,
    from_role: str,
    to_role: str,
    summary: str,
) -> dict[str, Any]:
    collaboration = payload.get("collaboration")
    refs = {}
    for key in ("review_round_id", "reply_to_message_id", "job_id", "artifact_kind", "run_id"):
        value = payload.get(key)
        if value is not None:
            refs[key] = value
    if isinstance(collaboration, dict):
        normalized = dict(collaboration)
        normalized.setdefault("format", "agent_orchestrator.collaboration_object.v1")
        normalized.setdefault("object_type", object_type)
        normalized.setdefault("session_id", session_id)
        normalized.setdefault("from_role", from_role)
        normalized.setdefault("to_role", to_role)
        normalized.setdefault("summary", summary)
        normalized.setdefault("evidence", _list_payload(payload, "evidence"))
        normalized.setdefault("blockers", _list_payload(payload, "blockers"))
        normalized.setdefault("next_steps", _list_payload(payload, "next_steps"))
        merged_refs = dict(normalized.get("refs", {})) if isinstance(normalized.get("refs"), dict) else {}
        merged_refs.update(refs)
        normalized["refs"] = merged_refs
        payload["collaboration"] = normalized
        return payload
    verdict = None
    severity = None
    review_result = payload.get("review_result")
    if isinstance(review_result, dict):
        verdict = review_result.get("verdict") if isinstance(review_result.get("verdict"), str) else None
        findings = review_result.get("findings")
        if isinstance(findings, list):
            severities = [item.get("severity") for item in findings if isinstance(item, dict) and isinstance(item.get("severity"), str)]
            severity = severities[0] if severities else None
    payload["collaboration"] = build_collaboration_payload(
        object_type=object_type,
        session_id=session_id,
        from_role=from_role,
        to_role=to_role,
        summary=summary,
        evidence=_list_payload(payload, "evidence"),
        blockers=_list_payload(payload, "blockers"),
        verdict=verdict,
        severity=severity,
        next_steps=_list_payload(payload, "next_steps"),
        refs=refs,
    )
    return payload


def _list_payload(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value:
        return [value]
    return []


def _string_payload(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def _thread_from_payload(payload: dict[str, Any]) -> str:
    explicit = payload.get("thread")
    if isinstance(explicit, str) and explicit:
        return explicit
    round_type = str(payload.get("round_type") or "")
    artifact_kind = str(payload.get("artifact_kind") or "")
    if "review" in round_type or artifact_kind == "review_findings":
        return "review"
    if artifact_kind in {"execution_result", "runtime_handoff"} or payload.get("run_id"):
        return "rescue" if payload.get("status") == "blocked" else "main"
    return "main"
