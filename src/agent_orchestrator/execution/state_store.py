"""Lightweight persistence for step-level execution runtime state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_orchestrator.control_plane_artifacts import atomic_write_json, read_json_object
from agent_orchestrator.jobs import now_iso


@dataclass(slots=True)
class ExecutionStateStore:
    root: Path | str = ".agent_orchestrator/execution_state"

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, run_id: str, payload: dict[str, object]) -> dict[str, object]:
        state = {
            **payload,
            "run_id": run_id,
            "updated_at": now_iso(),
        }
        atomic_write_json(self._path(run_id), state)
        return state

    def read(self, run_id: str) -> dict[str, object]:
        return read_json_object(self._path(run_id))

    def exists(self, run_id: str) -> bool:
        return self._path(run_id).exists()

    def _path(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"
