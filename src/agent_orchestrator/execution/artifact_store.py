"""Execution-side artifact persistence for large runtime payloads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_orchestrator.control_plane_artifacts import artifact_ref, atomic_write_json, stable_id
from agent_orchestrator.jobs import now_iso


@dataclass(slots=True)
class ExecutionArtifactStore:
    root: Path | str = ".agent_orchestrator/execution_artifacts"

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write_command_result(
        self,
        *,
        run_id: str,
        action_id: str,
        command: list[str],
        exit_code: int | None,
        stdout: str,
        stderr: str,
        failure_kind: str | None,
    ) -> dict[str, object]:
        payload = {
            "format": "agent_orchestrator.execution_command_artifact.v1",
            "id": stable_id("exec-artifact", run_id, action_id, tuple(command)),
            "run_id": run_id,
            "action_id": action_id,
            "command": list(command),
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "failure_kind": failure_kind,
            "created_at": now_iso(),
        }
        atomic_write_json(self._path(str(payload["id"])), payload)
        return {
            "artifact_id": payload["id"],
            "path": str(self._path(str(payload["id"]))),
            "ref": artifact_ref(payload),
        }

    def write_repo_exploration(
        self,
        *,
        run_id: str,
        workspace_root: str,
        explicit_paths: list[str],
        existing_paths: list[str],
        candidate_paths: list[str],
        file_listing: list[str],
    ) -> dict[str, object]:
        payload = {
            "format": "agent_orchestrator.execution_repo_exploration_artifact.v1",
            "id": stable_id("exec-artifact", run_id, "repo-exploration", workspace_root),
            "run_id": run_id,
            "workspace_root": workspace_root,
            "explicit_paths": explicit_paths,
            "existing_paths": existing_paths,
            "candidate_paths": candidate_paths,
            "file_count": len(file_listing),
            "file_listing": file_listing,
            "created_at": now_iso(),
        }
        atomic_write_json(self._path(str(payload["id"])), payload)
        return {
            "artifact_id": payload["id"],
            "path": str(self._path(str(payload["id"]))),
            "ref": artifact_ref(payload),
        }

    def _path(self, artifact_id: str) -> Path:
        return self.root / f"{artifact_id}.json"
