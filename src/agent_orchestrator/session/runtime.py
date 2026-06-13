"""Compatibility session runtime for the coding-agent architecture."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from agent_orchestrator.session.models import (
    AgentSession,
    ContextSnapshot,
    ExecutionActivity,
    SessionTurn,
    new_activity_id,
    new_session_id,
    new_snapshot_id,
    new_turn_id,
)


class SessionRuntime:
    """Owns session and turn continuity without replacing control-plane truth."""

    def __init__(self, root: Path | str = ".agent_orchestrator/agent_sessions") -> None:
        self.root = Path(root)

    def start_session(
        self,
        *,
        origin: str,
        metadata: dict[str, object] | None = None,
        session_id: str | None = None,
    ) -> AgentSession:
        now = _utcnow()
        session = AgentSession(
            session_id=session_id or new_session_id(),
            status="active",
            created_at=now,
            updated_at=now,
            current_turn_id=None,
            turn_ids=[],
            origin=origin,
            metadata=dict(metadata or {}),
        )
        self._write_json(self._session_dir(session.session_id) / "session.json", session.to_dict())
        return session

    def get_session(self, session_id: str) -> AgentSession:
        return AgentSession.from_dict(self._read_json(self._session_dir(session_id) / "session.json"))

    def start_turn(
        self,
        *,
        session_id: str,
        requirement: str,
        route: dict[str, object],
        clarify_summary: dict[str, object],
        strategy_summary: dict[str, object],
        task_contract: dict[str, object],
        compatibility_metadata: dict[str, object],
        selected_execution_strategy: str,
        resume_kind: str = "fresh",
        resume_from_turn_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> tuple[AgentSession, SessionTurn, ContextSnapshot]:
        session = self.get_session(session_id)
        turn_id = new_turn_id()
        snapshot_id = new_snapshot_id()
        snapshot = ContextSnapshot(
            snapshot_id=snapshot_id,
            session_id=session_id,
            turn_id=turn_id,
            task_contract=dict(task_contract),
            selected_execution_strategy=selected_execution_strategy,
            compatibility_metadata=dict(compatibility_metadata),
            resume_kind=resume_kind,
            metadata=dict(metadata or {}),
        )
        turn = SessionTurn(
            turn_id=turn_id,
            session_id=session_id,
            requirement=requirement,
            status="prepared",
            route=dict(route),
            clarify_summary=dict(clarify_summary),
            strategy_summary=dict(strategy_summary),
            linked_run_id=None,
            resume_from_turn_id=resume_from_turn_id,
            context_snapshot_id=snapshot_id,
            metadata=dict(metadata or {}),
        )
        updated_session = replace(
            session,
            updated_at=_utcnow(),
            current_turn_id=turn_id,
            turn_ids=[*session.turn_ids, turn_id],
        )
        session_dir = self._session_dir(session_id)
        self._write_json(session_dir / "session.json", updated_session.to_dict())
        self._write_json(session_dir / "turns" / f"{turn_id}.json", turn.to_dict())
        self._write_json(session_dir / "snapshots" / f"{snapshot_id}.json", snapshot.to_dict())
        return updated_session, turn, snapshot

    def get_turn(self, session_id: str, turn_id: str) -> SessionTurn:
        return SessionTurn.from_dict(self._read_json(self._session_dir(session_id) / "turns" / f"{turn_id}.json"))

    def get_snapshot(self, session_id: str, snapshot_id: str) -> ContextSnapshot:
        return ContextSnapshot.from_dict(self._read_json(self._session_dir(session_id) / "snapshots" / f"{snapshot_id}.json"))

    def record_activity(
        self,
        *,
        session_id: str,
        turn_id: str,
        runtime_name: str,
        linked_run_id: str | None,
        status: str,
        accepted: bool | None,
        summary: str,
        metadata: dict[str, object] | None = None,
    ) -> ExecutionActivity:
        activity = ExecutionActivity(
            activity_id=new_activity_id(),
            session_id=session_id,
            turn_id=turn_id,
            runtime_name=runtime_name,
            linked_run_id=linked_run_id,
            status=status,
            accepted=accepted,
            summary=summary,
            metadata=dict(metadata or {}),
        )
        self._write_json(
            self._session_dir(session_id) / "activities" / f"{activity.activity_id}.json",
            activity.to_dict(),
        )
        return activity

    def attach_run_result(
        self,
        *,
        session_id: str,
        turn_id: str,
        linked_run_id: str | None,
        status: str,
        accepted: bool | None,
        runtime_name: str,
        payload: dict[str, object],
    ) -> SessionTurn:
        turn = self.get_turn(session_id, turn_id)
        updated_turn = replace(
            turn,
            status="completed" if status == "completed" else status,
            linked_run_id=linked_run_id,
            metadata={**turn.metadata, "last_result": dict(payload)},
        )
        self._write_json(self._session_dir(session_id) / "turns" / f"{turn_id}.json", updated_turn.to_dict())
        self.record_activity(
            session_id=session_id,
            turn_id=turn_id,
            runtime_name=runtime_name,
            linked_run_id=linked_run_id,
            status=status,
            accepted=accepted,
            summary=f"Runtime {runtime_name} finished with status={status}",
            metadata={"result_keys": sorted(payload.keys())},
        )
        return updated_turn

    def complete_turn(self, *, session_id: str, turn_id: str, status: str) -> SessionTurn:
        turn = self.get_turn(session_id, turn_id)
        updated_turn = replace(turn, status=status)
        self._write_json(self._session_dir(session_id) / "turns" / f"{turn_id}.json", updated_turn.to_dict())
        return updated_turn

    def latest_turn(self, session_id: str) -> SessionTurn | None:
        session = self.get_session(session_id)
        if not session.current_turn_id:
            return None
        return self.get_turn(session_id, session.current_turn_id)

    def _session_dir(self, session_id: str) -> Path:
        return self.root / session_id

    def _read_json(self, path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()
