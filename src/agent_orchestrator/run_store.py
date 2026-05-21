"""Local persistence for orchestration runs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


@dataclass(slots=True)
class RunStore:
    root: Path | str = ".agent_orchestrator/runs"
    stale_after_seconds: float = 5.0

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._run_path(run_id)
        data = json.dumps(payload, ensure_ascii=False, indent=2)
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.root, delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)
        return payload

    def read(self, run_id: str) -> dict[str, Any]:
        path = self._run_path(run_id)
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return {}
        return json.loads(text)

    def exists(self, run_id: str) -> bool:
        return self._run_path(run_id).exists()

    def acquire_run_lock(
        self,
        run_id: str,
        *,
        owner: str | None = None,
        reason: str | None = None,
        steal_stale: bool = True,
    ) -> bool:
        path = self._lock_path(run_id)
        payload = {
            "run_id": run_id,
            "pid": os.getpid(),
            "owner": owner,
            "reason": reason,
            "started_at": self._now_iso(),
            "heartbeat_at": self._now_iso(),
        }
        data = json.dumps(payload, ensure_ascii=False, indent=2)

        while True:
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                if steal_stale and self._is_stale_lock(path):
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                return False
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                file.write(data)
            return True

    def refresh_run_lock(
        self,
        run_id: str,
        *,
        owner: str | None = None,
        reason: str | None = None,
    ) -> bool:
        path = self._lock_path(run_id)
        if not path.exists():
            return False
        lock = self.read_run_lock(run_id)
        if not lock or lock.get("stale"):
            return False
        if owner is not None and lock.get("owner") != owner:
            return False
        if lock.get("pid") != os.getpid():
            return False
        lock["reason"] = reason if reason is not None else lock.get("reason")
        lock["heartbeat_at"] = self._now_iso()
        path.write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")
        return True

    def release_run_lock(self, run_id: str) -> None:
        path = self._lock_path(run_id)
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    def is_run_locked(self, run_id: str) -> bool:
        lock = self.read_run_lock(run_id)
        return bool(lock and not lock.get("stale"))

    def read_run_lock(self, run_id: str) -> dict[str, Any] | None:
        path = self._lock_path(run_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {
                "run_id": run_id,
                "state": "corrupt",
                "stale": True,
                "path": str(path),
            }
        stale = self._is_stale_lock_payload(payload)
        payload["stale"] = stale
        payload["state"] = "stale" if stale else "active"
        payload["path"] = str(path)
        return payload

    def _run_path(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"

    def _lock_path(self, run_id: str) -> Path:
        return self.root / f"{run_id}.lock"

    def _is_stale_lock(self, path: Path) -> bool:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return True
        return self._is_stale_lock_payload(payload)

    def _is_stale_lock_payload(self, payload: dict[str, Any]) -> bool:
        pid = payload.get("pid")
        if not isinstance(pid, int):
            return True
        if not self._pid_alive(pid):
            return True
        heartbeat_at = payload.get("heartbeat_at")
        if not isinstance(heartbeat_at, str):
            return True
        try:
            heartbeat = datetime.fromisoformat(heartbeat_at)
        except ValueError:
            return True
        delta = datetime.now(UTC) - heartbeat
        return delta.total_seconds() > self.stale_after_seconds

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()
