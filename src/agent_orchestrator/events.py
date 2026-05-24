"""Append-only event store for orchestration state changes."""
from __future__ import annotations

# DEPS: __future__, agent_orchestrator, dataclasses, json, pathlib, typing, uuid
# RESPONSIBILITY: Persist lightweight backend events for dashboard and recovery flows.
# MODULE: interface
# ---

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent_orchestrator.jobs import now_iso


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    id: str
    type: str
    scope: str
    scope_id: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "type": self.type,
            "scope": self.scope,
            "scope_id": self.scope_id,
            "message": self.message,
            "payload": self.payload,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ExecutionEvent":
        return cls(
            id=str(data.get("id") or f"event-{uuid4().hex[:8]}"),
            type=str(data.get("type") or "unknown"),
            scope=str(data.get("scope") or "unknown"),
            scope_id=str(data.get("scope_id") or ""),
            message=str(data.get("message") or ""),
            payload=dict(data.get("payload", {})) if isinstance(data.get("payload"), dict) else {},
            created_at=str(data.get("created_at") or now_iso()),
        )


@dataclass(slots=True)
class EventStore:
    root: Path | str = ".agent_orchestrator/events"

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        *,
        type: str,
        scope: str,
        scope_id: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> ExecutionEvent:
        event = ExecutionEvent(
            id=f"event-{uuid4().hex[:10]}",
            type=type,
            scope=scope,
            scope_id=scope_id,
            message=message,
            payload=payload or {},
        )
        with self._events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        return event

    def list_recent(self, *, limit: int = 100) -> list[dict[str, object]]:
        events = self._read_all()
        return [event.to_dict() for event in events[-limit:]][::-1]

    def list_for_session(self, session_id: str, *, limit: int = 100) -> list[dict[str, object]]:
        events = [
            event
            for event in self._read_all()
            if event.scope_id == session_id
            or event.payload.get("session_id") == session_id
            or event.payload.get("plan_session_id") == session_id
        ]
        return [event.to_dict() for event in events[-limit:]][::-1]

    @property
    def _events_path(self) -> Path:
        return self.root / "events.jsonl"

    def _read_all(self) -> list[ExecutionEvent]:
        path = self._events_path
        if not path.exists():
            return []
        events: list[ExecutionEvent] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(ExecutionEvent.from_dict(payload))
        return events
