"""Session-scoped scratchpad storage for transient runtime working state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent_orchestrator.jobs import now_iso


@dataclass(frozen=True, slots=True)
class ScratchpadEntry:
    entry_id: str
    session_id: str
    turn_id: str
    kind: str
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, object]:
        return {
            "entry_id": self.entry_id,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "kind": self.kind,
            "summary": self.summary,
            "payload": dict(self.payload),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ScratchpadEntry":
        return cls(
            entry_id=str(data.get("entry_id") or f"scratchpad-{uuid4().hex[:10]}"),
            session_id=str(data.get("session_id") or ""),
            turn_id=str(data.get("turn_id") or ""),
            kind=str(data.get("kind") or "note"),
            summary=str(data.get("summary") or ""),
            payload=dict(data.get("payload", {})) if isinstance(data.get("payload"), dict) else {},
            created_at=str(data.get("created_at") or now_iso()),
        )


@dataclass(slots=True)
class ScratchpadStore:
    root: Path | str = ".agent_orchestrator/scratchpads"

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        *,
        session_id: str,
        turn_id: str,
        kind: str,
        summary: str,
        payload: dict[str, Any] | None = None,
    ) -> ScratchpadEntry:
        entry = ScratchpadEntry(
            entry_id=f"scratchpad-{uuid4().hex[:10]}",
            session_id=session_id,
            turn_id=turn_id,
            kind=kind,
            summary=summary,
            payload=payload or {},
        )
        with self._scratchpad_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        return entry

    def query(
        self,
        *,
        session_id: str,
        turn_id: str | None = None,
        kind: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        entries = self._read_all()
        entries = [entry for entry in entries if entry.session_id == session_id]
        if turn_id is not None:
            entries = [entry for entry in entries if entry.turn_id == turn_id]
        if kind is not None:
            entries = [entry for entry in entries if entry.kind == kind]
        return [entry.to_dict() for entry in entries[-limit:]][::-1]

    @property
    def _scratchpad_path(self) -> Path:
        return self.root / "scratchpad.jsonl"

    def _read_all(self) -> list[ScratchpadEntry]:
        if not self._scratchpad_path.exists():
            return []
        entries: list[ScratchpadEntry] = []
        for line in self._scratchpad_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                entries.append(ScratchpadEntry.from_dict(payload))
        return entries
