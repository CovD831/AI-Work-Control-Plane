"""Explicit native tool surface for the first-party coding agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
import fnmatch
import re

from agent_orchestrator.command import SubprocessCommandRunner
from agent_orchestrator.execution.artifact_store import ExecutionArtifactStore
from agent_orchestrator.execution.models import ActionRequest, ActionResult


@dataclass(frozen=True, slots=True)
class NativeToolInvocation:
    tool: str
    summary: str
    timestamp: str
    arguments: dict[str, object] = field(default_factory=dict)
    result: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "tool": self.tool,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "arguments": dict(self.arguments),
            "result": dict(self.result),
        }


@dataclass(slots=True)
class NativeToolbox:
    """Governed tool surface used by the native coding-agent main path."""

    workspace_root: Path = field(default_factory=Path.cwd)
    runner: SubprocessCommandRunner = field(default_factory=SubprocessCommandRunner)
    artifact_store: ExecutionArtifactStore = field(default_factory=ExecutionArtifactStore)
    _trace: list[NativeToolInvocation] = field(default_factory=list, init=False, repr=False)

    def surface_summary(self) -> dict[str, object]:
        return {
            "format": "agent_orchestrator.native_tool_surface.v1",
            "tools": [
                "read",
                "search",
                "glob",
                "structured_patch",
                "verify",
                "repo_map",
                "tool_trace",
            ],
            "workspace_root": str(self.workspace_root.resolve()),
            "governance": {
                "boundary_policy": "workspace_root_only",
                "approval_aware": True,
                "artifact_backed": True,
            },
        }

    def snapshot_trace(self) -> list[dict[str, object]]:
        return [item.to_dict() for item in self._trace]

    def read(self, paths: list[str], *, max_chars: int = 4000) -> dict[str, object]:
        records: list[dict[str, object]] = []
        total_chars = 0
        skipped_binary_paths: list[str] = []
        for raw_path in paths:
            candidate = self.workspace_root / raw_path
            if not _is_within_workspace(self.workspace_root, candidate) or not candidate.exists() or not candidate.is_file():
                continue
            try:
                content = candidate.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                skipped_binary_paths.append(str(raw_path))
                continue
            remaining = max(max_chars - total_chars, 0)
            if remaining <= 0:
                break
            snippet = content[:remaining]
            total_chars += len(snippet)
            records.append(
                {
                    "path": raw_path,
                    "chars": len(content),
                    "snippet": snippet,
                }
            )
        payload = {
            "records": records,
            "record_count": len(records),
            "skipped_binary_paths": skipped_binary_paths,
        }
        self._trace.append(
            NativeToolInvocation(
                tool="read",
                summary="Read bounded repository content for explicit candidate paths.",
                timestamp=_utcnow(),
                arguments={"paths": list(paths), "max_chars": max_chars},
                result={"record_count": len(records), "skipped_binary_count": len(skipped_binary_paths)},
            )
        )
        return payload

    def glob(self, patterns: list[str]) -> dict[str, object]:
        seen: set[str] = set()
        matches: list[str] = []
        all_files = [
            str(path.relative_to(self.workspace_root))
            for path in self.workspace_root.rglob("*")
            if path.is_file() and ".git" not in path.parts and ".agent_orchestrator" not in path.parts
        ]
        for pattern in patterns:
            normalized = pattern.strip() or "**/*"
            alt_pattern = normalized[3:] if normalized.startswith("**/") else normalized
            for path in all_files:
                if fnmatch.fnmatch(path, normalized) or fnmatch.fnmatch(path, alt_pattern):
                    if path not in seen:
                        seen.add(path)
                        matches.append(path)
        payload = {"patterns": list(patterns), "matches": matches, "match_count": len(matches)}
        self._trace.append(
            NativeToolInvocation(
                tool="glob",
                summary="Enumerated repository files through bounded glob patterns.",
                timestamp=_utcnow(),
                arguments={"patterns": list(patterns)},
                result={"match_count": len(matches)},
            )
        )
        return payload

    def repo_map(self, patterns: list[str] | None = None, *, depth: int = 2) -> dict[str, object]:
        selected_patterns = list(patterns or ["**/*"])
        matched = self.glob(selected_patterns).get("matches", [])
        directories: list[str] = []
        files: list[str] = []
        for raw_path in matched:
            candidate = self.workspace_root / str(raw_path)
            if not _is_within_workspace(self.workspace_root, candidate):
                continue
            try:
                relative = str(candidate.relative_to(self.workspace_root))
            except ValueError:
                continue
            if candidate.is_dir():
                if relative not in directories:
                    directories.append(relative)
                continue
            files.append(relative)
            parent = candidate.parent
            for _ in range(max(depth - 1, 0)):
                if parent == self.workspace_root or not _is_within_workspace(self.workspace_root, parent):
                    break
                rel_parent = str(parent.relative_to(self.workspace_root))
                if rel_parent not in directories:
                    directories.append(rel_parent)
                parent = parent.parent
        payload = {
            "patterns": selected_patterns,
            "depth": depth,
            "directories": sorted(directories),
            "files": files[:50],
            "directory_count": len(directories),
            "file_count": len(files),
        }
        self._trace.append(
            NativeToolInvocation(
                tool="repo_map",
                summary="Built a bounded repository map for exploration and task scoping.",
                timestamp=_utcnow(),
                arguments={"patterns": selected_patterns, "depth": depth},
                result={"directory_count": len(directories), "file_count": len(files)},
            )
        )
        return payload

    def tool_trace(self) -> dict[str, object]:
        payload = {"trace": self.snapshot_trace(), "trace_count": len(self._trace)}
        self._trace.append(
            NativeToolInvocation(
                tool="tool_trace",
                summary="Returned the governed native tool trace for operator-visible continuity.",
                timestamp=_utcnow(),
                arguments={},
                result={"trace_count": len(self._trace)},
            )
        )
        return payload

    def search(self, query: str, *, paths: list[str] | None = None, max_matches: int = 20) -> dict[str, object]:
        lowered_terms = [term for term in re.split(r"[^a-zA-Z0-9_./-]+", query.lower()) if len(term) >= 3]
        candidate_paths = paths or self.glob(["**/*"]).get("matches", [])
        matches: list[dict[str, object]] = []
        skipped_binary_paths: list[str] = []
        for raw_path in candidate_paths:
            candidate = self.workspace_root / str(raw_path)
            if not _is_within_workspace(self.workspace_root, candidate) or not candidate.exists() or not candidate.is_file():
                continue
            try:
                haystack = candidate.read_text(encoding="utf-8").lower()
            except UnicodeDecodeError:
                skipped_binary_paths.append(str(raw_path))
                continue
            if lowered_terms and not any(term in haystack or term in str(raw_path).lower() for term in lowered_terms):
                continue
            preview = haystack[:200]
            matches.append({"path": str(raw_path), "preview": preview})
            if len(matches) >= max_matches:
                break
        payload = {
            "query": query,
            "matches": matches,
            "match_count": len(matches),
            "skipped_binary_paths": skipped_binary_paths,
        }
        self._trace.append(
            NativeToolInvocation(
                tool="search",
                summary="Searched bounded repository content and path names for requirement-aligned candidates.",
                timestamp=_utcnow(),
                arguments={"query": query, "path_count": len(candidate_paths), "max_matches": max_matches},
                result={"match_count": len(matches), "skipped_binary_count": len(skipped_binary_paths)},
            )
        )
        return payload

    def structured_patch(self, operations: list[dict[str, object]]) -> ActionResult:
        executor = _action_executor(
            workspace_root=self.workspace_root,
            runner=self.runner,
            artifact_store=self.artifact_store,
        )
        result = executor.execute(
            ActionRequest(
                action_id="native-structured-patch",
                action_type="file_mutation",
                description="Apply bounded structured patch operations through the native tool surface.",
                parameters={"operations": list(operations)},
                risk_level="medium",
                requires_approval=True,
            )
        )
        applied_changes = result.payload.get("applied_changes", [])
        self._trace.append(
            NativeToolInvocation(
                tool="structured_patch",
                summary="Applied bounded structured patch operations under governance controls.",
                timestamp=_utcnow(),
                arguments={"operation_count": len(operations)},
                result={
                    "status": result.status,
                    "applied_change_count": len(applied_changes) if isinstance(applied_changes, list) else 0,
                },
            )
        )
        return result

    def verify(self, *, run_id: str, command: list[str]) -> ActionResult:
        executor = _action_executor(
            workspace_root=self.workspace_root,
            runner=self.runner,
            artifact_store=self.artifact_store,
        )
        result = executor.execute(
            ActionRequest(
                action_id="native-verify",
                action_type="run_command",
                description="Run bounded verification through the native tool surface.",
                parameters={"command": list(command), "run_id": run_id},
                risk_level="medium",
                requires_approval=True,
            )
        )
        payload = result.payload if isinstance(result.payload, dict) else {}
        self._trace.append(
            NativeToolInvocation(
                tool="verify",
                summary="Executed bounded verification command under governance controls.",
                timestamp=_utcnow(),
                arguments={"command": list(command)},
                result={
                    "status": result.status,
                    "exit_code": payload.get("exit_code"),
                    "artifact": payload.get("artifact"),
                },
            )
        )
        return result


def _action_executor(
    *,
    workspace_root: Path,
    runner: SubprocessCommandRunner,
    artifact_store: ExecutionArtifactStore,
):
    from agent_orchestrator.execution.coding_components import ActionExecutor

    return ActionExecutor(
        runner=runner,
        artifact_store=artifact_store,
        workspace_root=workspace_root,
    )


def _is_within_workspace(workspace_root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(workspace_root.resolve())
        return True
    except ValueError:
        return False


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()
