"""Explicit native tool surface for the first-party coding agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from difflib import unified_diff
from pathlib import Path
import fnmatch
import re
import textwrap

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
        workflow = {
            "explore": ["repo_map", "find_files", "search", "outline", "read"],
            "edit": ["patch_preview", "structured_patch", "diff_preview"],
            "verify": ["verify", "tool_trace"],
            "daily_driver_path": ["repo_map", "find_files", "search", "outline", "read", "patch_preview", "structured_patch", "diff_preview", "verify"],
        }
        return {
            "format": "agent_orchestrator.native_tool_surface.v1",
            "tools": [
                "read",
                "search",
                "glob",
                "find_files",
                "outline",
                "patch_preview",
                "structured_patch",
                "diff_preview",
                "verify",
                "repo_map",
                "tool_trace",
            ],
            "workspace_root": str(self.workspace_root.resolve()),
            "capability_profile": {
                "read": {
                    "purpose": "bounded file inspection",
                    "governance": "workspace_root_only",
                    "output_shape": "records_with_snippets",
                },
                "search": {
                    "purpose": "content and path matching for repo exploration",
                    "governance": "workspace_root_only",
                    "output_shape": "match_previews",
                },
                "glob": {
                    "purpose": "bounded file enumeration",
                    "governance": "workspace_root_only",
                    "output_shape": "path_list",
                },
                "find_files": {
                    "purpose": "filename and path-fragment candidate discovery for repo tasks",
                    "governance": "workspace_root_only",
                    "output_shape": "ranked_path_candidates",
                },
                "outline": {
                    "purpose": "low-cost structural file understanding before full reads",
                    "governance": "workspace_root_only",
                    "output_shape": "line_anchored_structure_outline",
                },
                "patch_preview": {
                    "purpose": "pre-apply bounded mutation preview for operator-visible review",
                    "governance": "artifact_backed_preview_only",
                    "output_shape": "planned_change_preview_records",
                },
                "structured_patch": {
                    "purpose": "auditable bounded mutations with preview evidence",
                    "governance": "artifact_backed_and_approval_aware",
                    "output_shape": "applied_change_records_with_previews",
                },
                "diff_preview": {
                    "purpose": "governed bounded change preview for operator-visible review",
                    "governance": "artifact_backed_preview_only",
                    "output_shape": "change_preview_records",
                },
                "verify": {
                    "purpose": "governed command verification",
                    "governance": "artifact_backed_and_failure_classified",
                    "output_shape": "command_result_artifact",
                },
                "repo_map": {
                    "purpose": "directory-level exploration and scoping",
                    "governance": "workspace_root_only",
                    "output_shape": "directory_and_file_summary",
                },
            },
            "daily_driver_readiness": {
                "repo_exploration_ready": True,
                "bounded_read_search_ready": True,
                "structural_outline_ready": True,
                "glob_ready": True,
                "structured_patch_ready": True,
                "patch_preview_ready": True,
                "diff_preview_ready": True,
                "verification_ready": True,
                "artifact_backed": True,
            },
            "workflow_surface": {
                "explore": {
                    "tools": workflow["explore"],
                    "purpose": "bounded repository discovery and candidate scoping",
                },
                "edit": {
                    "tools": workflow["edit"],
                    "purpose": "preview-first bounded mutation and diff review",
                },
                "verify": {
                    "tools": workflow["verify"],
                    "purpose": "governed verification and trace-backed recovery",
                },
                "daily_driver_path": {
                    "tools": workflow["daily_driver_path"],
                    "purpose": "native-first repo task loop from exploration through verification",
                },
            },
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

    def find_files(self, query: str, *, max_matches: int = 20) -> dict[str, object]:
        fragments = [
            fragment
            for fragment in re.split(r"[^a-zA-Z0-9_./-]+", query.lower())
            if len(fragment) >= 2 and any(char.isalpha() for char in fragment)
        ]
        all_files = [
            str(path.relative_to(self.workspace_root))
            for path in self.workspace_root.rglob("*")
            if path.is_file() and ".git" not in path.parts and ".agent_orchestrator" not in path.parts
        ]
        ranked: list[tuple[int, str, dict[str, object]]] = []
        for raw_path in all_files:
            lowered_path = raw_path.lower()
            matched_fragments = [fragment for fragment in fragments if fragment in lowered_path]
            if fragments and not matched_fragments:
                continue
            basename = Path(raw_path).name.lower()
            score = len(matched_fragments) * 10
            score += sum(5 for fragment in matched_fragments if basename.startswith(fragment))
            score += sum(3 for fragment in matched_fragments if basename == fragment or basename == f"{fragment}.py")
            ranked.append(
                (
                    -score,
                    raw_path,
                    {
                        "path": raw_path,
                        "score": score,
                        "matched_fragments": matched_fragments,
                    },
                )
            )
        ranked.sort(key=lambda item: (item[0], item[1]))
        matches = [item[2] for item in ranked[:max_matches]]
        payload = {
            "query": query,
            "matches": matches,
            "match_count": len(matches),
        }
        self._trace.append(
            NativeToolInvocation(
                tool="find_files",
                summary="Ranked repository paths by filename and path-fragment relevance.",
                timestamp=_utcnow(),
                arguments={"query": query, "max_matches": max_matches},
                result={"match_count": len(matches)},
            )
        )
        return payload

    def outline(self, paths: list[str], *, max_entries: int = 8, max_files: int = 6) -> dict[str, object]:
        records: list[dict[str, object]] = []
        skipped_binary_paths: list[str] = []
        selected_paths = list(paths)[:max_files]
        for raw_path in selected_paths:
            candidate = self.workspace_root / raw_path
            if not _is_within_workspace(self.workspace_root, candidate) or not candidate.exists() or not candidate.is_file():
                continue
            try:
                content = candidate.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                skipped_binary_paths.append(str(raw_path))
                continue
            records.append(
                {
                    "path": str(raw_path),
                    "language_hint": _language_hint(candidate),
                    "entry_count": max_entries,
                    "outline": _structure_outline(content=content, max_entries=max_entries),
                }
            )
        payload = {
            "records": records,
            "record_count": len(records),
            "skipped_binary_paths": skipped_binary_paths,
        }
        self._trace.append(
            NativeToolInvocation(
                tool="outline",
                summary="Captured low-cost structural file outlines before bounded deep reads.",
                timestamp=_utcnow(),
                arguments={"paths": list(paths), "max_entries": max_entries, "max_files": max_files},
                result={"record_count": len(records), "skipped_binary_count": len(skipped_binary_paths)},
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
        ranked_matches: list[tuple[int, str, dict[str, object]]] = []
        skipped_binary_paths: list[str] = []
        for raw_path in candidate_paths:
            candidate = self.workspace_root / str(raw_path)
            if not _is_within_workspace(self.workspace_root, candidate) or not candidate.exists() or not candidate.is_file():
                continue
            try:
                content = candidate.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                skipped_binary_paths.append(str(raw_path))
                continue
            haystack = content.lower()
            lowered_path = str(raw_path).lower()
            matched_terms = [
                term
                for term in lowered_terms
                if term in haystack or term in lowered_path
            ]
            if lowered_terms and not matched_terms:
                continue
            score = _search_match_score(
                query=query,
                matched_terms=matched_terms,
                lowered_path=lowered_path,
                haystack=haystack,
            )
            preview = _search_preview(content=content, haystack=haystack, matched_terms=matched_terms)
            ranked_matches.append(
                (
                    -score,
                    str(raw_path),
                    {
                        "path": str(raw_path),
                        "preview": preview,
                        "score": score,
                        "matched_terms": matched_terms,
                    },
                )
            )
        ranked_matches.sort(key=lambda item: (item[0], item[1]))
        matches = [item[2] for item in ranked_matches[:max_matches]]
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
        if isinstance(applied_changes, list) and applied_changes:
            self.diff_preview(applied_changes=applied_changes)
        return result

    def patch_preview(
        self,
        operations: list[dict[str, object]],
        *,
        max_preview_chars: int = 600,
    ) -> ActionResult:
        preview_records: list[dict[str, object]] = []
        for operation in operations:
            if not isinstance(operation, dict):
                continue
            path_value = str(operation.get("path", "")).strip()
            candidate = self.workspace_root / path_value if path_value else self.workspace_root
            kind = str(operation.get("kind", "unknown"))
            if not path_value or not _is_within_workspace(self.workspace_root, candidate) or not candidate.exists() or not candidate.is_file():
                preview_records.append(
                    {
                        "path": path_value,
                        "operation": kind,
                        "status": "failed",
                        "summary": "Target path does not exist or is outside the workspace boundary.",
                        "changed": False,
                        "before_preview": "",
                        "after_preview": "",
                        "diff_preview": "",
                    }
                )
                continue
            try:
                original = candidate.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                preview_records.append(
                    {
                        "path": path_value,
                        "operation": kind,
                        "status": "failed",
                        "summary": "Target path could not be previewed as UTF-8 text.",
                        "changed": False,
                        "before_preview": "",
                        "after_preview": "",
                        "diff_preview": "",
                    }
                )
                continue
            preview_change = _preview_operation_change(
                original=original,
                operation=operation,
            )
            before_text = str(preview_change.get("before_preview") or "")
            after_text = str(preview_change.get("after_preview") or "")
            diff_text = "".join(
                unified_diff(
                    before_text.splitlines(keepends=True),
                    after_text.splitlines(keepends=True),
                    fromfile=f"{path_value}:before" if path_value else "before",
                    tofile=f"{path_value}:after" if path_value else "after",
                    n=2,
                )
            )
            preview_records.append(
                {
                    "path": path_value,
                    "operation": kind,
                    "status": preview_change.get("status"),
                    "summary": preview_change.get("summary"),
                    "changed": bool(preview_change.get("changed")),
                    "before_preview": before_text,
                    "after_preview": after_text,
                    "diff_preview": diff_text[:max_preview_chars],
                }
            )
        payload = {
            "preview_records": preview_records,
            "preview_count": len(preview_records),
            "changed_count": sum(1 for item in preview_records if item.get("changed")),
        }
        self._trace.append(
            NativeToolInvocation(
                tool="patch_preview",
                summary="Produced governed bounded mutation previews before file changes were applied.",
                timestamp=_utcnow(),
                arguments={"operation_count": len(operations), "max_preview_chars": max_preview_chars},
                result={
                    "preview_count": len(preview_records),
                    "changed_count": payload["changed_count"],
                },
            )
        )
        return ActionResult(
            action_id="native-patch-preview",
            action_type="patch_preview",
            status="passed",
            summary="Generated governed pre-apply previews for bounded file mutations.",
            payload=payload,
        )

    def diff_preview(
        self,
        *,
        applied_changes: list[dict[str, object]],
        max_preview_chars: int = 600,
    ) -> ActionResult:
        preview_records: list[dict[str, object]] = []
        for item in applied_changes:
            if not isinstance(item, dict):
                continue
            preview = item.get("preview", {}) if isinstance(item.get("preview"), dict) else {}
            before_text = str(preview.get("before_preview") or "")
            after_text = str(preview.get("after_preview") or "")
            path = str(item.get("path") or "")
            diff_text = "".join(
                unified_diff(
                    before_text.splitlines(keepends=True),
                    after_text.splitlines(keepends=True),
                    fromfile=f"{path}:before" if path else "before",
                    tofile=f"{path}:after" if path else "after",
                    n=2,
                )
            )
            preview_records.append(
                {
                    "path": path,
                    "operation": item.get("operation"),
                    "status": item.get("status"),
                    "changed": bool(preview.get("changed")),
                    "before_preview": before_text,
                    "after_preview": after_text,
                    "diff_preview": diff_text[:max_preview_chars],
                }
            )
        payload = {
            "preview_records": preview_records,
            "preview_count": len(preview_records),
            "changed_count": sum(1 for item in preview_records if item.get("changed")),
        }
        self._trace.append(
            NativeToolInvocation(
                tool="diff_preview",
                summary="Produced governed bounded diff previews for applied changes.",
                timestamp=_utcnow(),
                arguments={"applied_change_count": len(applied_changes), "max_preview_chars": max_preview_chars},
                result={
                    "preview_count": len(preview_records),
                    "changed_count": payload["changed_count"],
                },
            )
        )
        return ActionResult(
            action_id="native-diff-preview",
            action_type="diff_preview",
            status="passed",
            summary="Generated governed diff previews for bounded file mutations.",
            payload=payload,
        )

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


def _search_match_score(
    *,
    query: str,
    matched_terms: list[str],
    lowered_path: str,
    haystack: str,
) -> int:
    score = len(set(matched_terms)) * 10
    for term in matched_terms:
        if term in lowered_path:
            score += 8
        if f"/{term}" in lowered_path or lowered_path.endswith(term):
            score += 3
        if haystack.count(term) > 1:
            score += 1
    normalized_query = query.strip().lower()
    if normalized_query and normalized_query in haystack:
        score += 6
    if normalized_query and normalized_query in lowered_path:
        score += 6
    return score


def _search_preview(
    *,
    content: str,
    haystack: str,
    matched_terms: list[str],
    radius: int = 100,
) -> str:
    if not content:
        return ""
    for term in matched_terms:
        index = haystack.find(term)
        if index < 0:
            continue
        start = max(index - radius, 0)
        end = min(index + len(term) + radius, len(content))
        snippet = content[start:end].strip()
        if start > 0:
            snippet = f"...{snippet}"
        if end < len(content):
            snippet = f"{snippet}..."
        return snippet
    return content[:200]


def _language_hint(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".py": "python",
        ".md": "markdown",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".jsx": "jsx",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".toml": "toml",
        ".sh": "shell",
    }.get(suffix, suffix.lstrip(".") or "text")


def _structure_outline(*, content: str, max_entries: int) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        if len(entries) >= max_entries:
            break
        stripped = line.strip()
        if not stripped:
            continue
        kind = _outline_kind(stripped)
        if kind is None:
            continue
        entries.append(
            {
                "line": line_no,
                "kind": kind,
                "text": textwrap.shorten(stripped, width=100, placeholder="..."),
            }
        )
    return entries


def _outline_kind(stripped: str) -> str | None:
    if stripped.startswith(("# ", "## ", "### ", "#### ")):
        return "heading"
    if re.match(r"^(class|def|async def)\s+[A-Za-z_][A-Za-z0-9_]*", stripped):
        return "symbol"
    if re.match(r"^(export\s+)?(async\s+)?function\s+[A-Za-z_][A-Za-z0-9_]*", stripped):
        return "symbol"
    if re.match(r"^(export\s+)?(const|let|var)\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*(async\s*)?(\(|function)", stripped):
        return "symbol"
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:\s*$", stripped):
        return "section"
    if stripped.startswith(("[", "{")):
        return "structure"
    return None


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _preview_operation_change(
    *,
    original: str,
    operation: dict[str, object],
) -> dict[str, object]:
    updated = original
    kind = str(operation.get("kind", "unknown"))
    if kind == "append":
        addition = str(operation.get("content", ""))
        updated = original + ("" if original.endswith("\n") or not original else "\n") + addition
    elif kind == "insert_before":
        anchor = str(operation.get("anchor", ""))
        content = str(operation.get("content", ""))
        if anchor and anchor in original:
            updated = original.replace(anchor, f"{content}\n{anchor}", 1)
        else:
            return _failed_preview_change(original=original, kind=kind, summary="Insert-before anchor text was not found.")
    elif kind == "insert_after":
        anchor = str(operation.get("anchor", ""))
        content = str(operation.get("content", ""))
        if anchor and anchor in original:
            updated = original.replace(anchor, f"{anchor}\n{content}", 1)
        else:
            return _failed_preview_change(original=original, kind=kind, summary="Insert-after anchor text was not found.")
    elif kind == "delete":
        old = str(operation.get("old", ""))
        if old and old in original:
            updated = original.replace(old, "", 1)
        else:
            return _failed_preview_change(original=original, kind=kind, summary="Delete target text was not found.")
    elif kind == "replace":
        old = str(operation.get("old", ""))
        new = str(operation.get("new", ""))
        if old and old in original:
            updated = original.replace(old, new, 1)
        else:
            return _failed_preview_change(original=original, kind=kind, summary="Replace target text was not found.")
    else:
        return _failed_preview_change(original=original, kind=kind, summary="Unsupported edit operation.")
    summary = "Previewed bounded edit operation."
    status = "previewed"
    changed = updated != original
    if not changed:
        status = "skipped"
        summary = "Previewed edit would not change the file."
    return {
        "status": status,
        "summary": summary,
        "changed": changed,
        "before_preview": original,
        "after_preview": updated,
    }


def _failed_preview_change(*, original: str, kind: str, summary: str) -> dict[str, object]:
    return {
        "status": "failed",
        "summary": summary,
        "changed": False,
        "before_preview": original,
        "after_preview": original,
        "operation": kind,
    }
