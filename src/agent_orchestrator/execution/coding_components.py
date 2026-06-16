"""Building blocks for the coding-agent execution runtime MVP."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from agent_orchestrator.adapters import EnvSlotFillConfig, _default_openai_compatible_transport, _extract_openai_message_content
from agent_orchestrator.command import CommandResult, SubprocessCommandRunner
from agent_orchestrator.execution.artifact_store import ExecutionArtifactStore
from agent_orchestrator.execution.models import ActionRequest, ActionResult, ExecutionRequest
from agent_orchestrator.execution.native_tools import NativeToolbox
from agent_orchestrator.strategy.models import ExecutionPlan


@dataclass(frozen=True, slots=True)
class RepoExplorationReport:
    workspace_root: str
    explicit_paths: list[str]
    existing_paths: list[str]
    candidate_paths: list[str]
    file_count: int
    artifact: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "workspace_root": self.workspace_root,
            "explicit_paths": list(self.explicit_paths),
            "existing_paths": list(self.existing_paths),
            "candidate_paths": list(self.candidate_paths),
            "file_count": self.file_count,
            "artifact": dict(self.artifact) if isinstance(self.artifact, dict) else None,
        }


@dataclass(frozen=True, slots=True)
class ExecutionContextPackage:
    requirement: str
    route: dict[str, object]
    strategy_summary: dict[str, object]
    session_context: dict[str, object]
    repo_report: dict[str, object]
    task_contract: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement": self.requirement,
            "route": dict(self.route),
            "strategy_summary": dict(self.strategy_summary),
            "session_context": dict(self.session_context),
            "repo_report": dict(self.repo_report),
            "task_contract": dict(self.task_contract),
        }


@dataclass(frozen=True, slots=True)
class EditIntent:
    mode: str
    target_paths: list[str]
    summary: str
    patch_plan: list[str] = field(default_factory=list)
    operations: list[dict[str, object]] = field(default_factory=list)
    patch_preview: dict[str, object] | None = None
    refinement: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "target_paths": list(self.target_paths),
            "summary": self.summary,
            "patch_plan": list(self.patch_plan),
            "operations": [dict(item) for item in self.operations],
            "patch_preview": dict(self.patch_preview) if isinstance(self.patch_preview, dict) else None,
            "refinement": dict(self.refinement) if isinstance(self.refinement, dict) else None,
        }


@dataclass(frozen=True, slots=True)
class AppliedChange:
    path: str
    status: str
    operation: str
    summary: str
    before_sha256: str | None = None
    after_sha256: str | None = None
    preview: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "status": self.status,
            "operation": self.operation,
            "summary": self.summary,
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
            "preview": dict(self.preview) if isinstance(self.preview, dict) else None,
        }


@dataclass(frozen=True, slots=True)
class VerificationReport:
    status: str
    command: list[str]
    exit_code: int | None
    stdout: str
    stderr: str
    skipped_reason: str | None = None
    failure_kind: str | None = None
    artifact: dict[str, object] | None = None
    attempt_index: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "command": list(self.command),
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "skipped_reason": self.skipped_reason,
            "failure_kind": self.failure_kind,
            "artifact": dict(self.artifact) if isinstance(self.artifact, dict) else None,
            "attempt_index": self.attempt_index,
        }


@dataclass(frozen=True, slots=True)
class RepairAttempt:
    attempt_index: int
    action: str
    target_paths: list[str]
    verification: dict[str, object]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "attempt_index": self.attempt_index,
            "action": self.action,
            "target_paths": list(self.target_paths),
            "verification": dict(self.verification),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class RepairLoopSummary:
    outcome: str
    attempt_count: int
    retry_budget: int
    attempts: list[dict[str, object]]
    recovery_recommendation: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "outcome": self.outcome,
            "attempt_count": self.attempt_count,
            "retry_budget": self.retry_budget,
            "attempts": [dict(item) for item in self.attempts],
            "recovery_recommendation": dict(self.recovery_recommendation),
        }


@dataclass(slots=True)
class ActionExecutor:
    runner: SubprocessCommandRunner = field(default_factory=SubprocessCommandRunner)
    artifact_store: ExecutionArtifactStore = field(default_factory=ExecutionArtifactStore)
    workspace_root: Path = field(default_factory=Path.cwd)

    def execute(self, action: ActionRequest) -> ActionResult:
        governance = self._governance_metadata(action)
        boundary_error = self._boundary_error(action)
        if boundary_error is not None:
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status="blocked",
                summary="Action blocked by workspace boundary policy.",
                error=boundary_error,
                payload={
                    "governance": governance,
                    "parameters": dict(action.parameters),
                },
            )
        if action.action_type == "file_mutation":
            result = self._execute_file_mutation(action)
            return _action_result_with_governance(result, governance)
        if action.action_type == "run_command":
            result = self._execute_command(action)
            return _action_result_with_governance(result, governance)
        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status="failed",
            summary="Unsupported action type.",
            error=f"unsupported_action_type:{action.action_type}",
            payload={
                "governance": governance,
                "parameters": dict(action.parameters),
            },
        )

    def _governance_metadata(self, action: ActionRequest) -> dict[str, object]:
        return {
            "workspace_root": str(self.workspace_root.resolve()),
            "risk_level": _classify_action_risk(action),
            "requires_approval": action.requires_approval,
            "boundary_policy": "workspace_root_only",
        }

    def _boundary_error(self, action: ActionRequest) -> str | None:
        if action.action_type == "file_mutation":
            operations = action.parameters.get("operations", [])
            if not isinstance(operations, list):
                return None
            for operation in operations:
                if not isinstance(operation, dict):
                    continue
                raw_path = str(operation.get("path", "")).strip()
                if not raw_path:
                    continue
                candidate = self.workspace_root / raw_path
                if not _is_within_workspace(self.workspace_root, candidate):
                    return f"workspace_boundary_violation:{raw_path}"
            return None
        if action.action_type == "run_command":
            command = action.parameters.get("command", [])
            if not isinstance(command, list):
                return None
            for item in command:
                if not isinstance(item, str):
                    continue
                normalized = item.strip()
                if "/" not in normalized and normalized not in {".", ".."}:
                    continue
                if normalized.startswith("-"):
                    continue
                candidate = self.workspace_root / normalized
                if not _is_within_workspace(self.workspace_root, candidate):
                    return f"workspace_boundary_violation:{normalized}"
            return None
        return None

    def _execute_file_mutation(self, action: ActionRequest) -> ActionResult:
        operations = action.parameters.get("operations", [])
        if not isinstance(operations, list):
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status="failed",
                summary="File mutation operations were not provided as a list.",
                error="invalid_operations",
                payload={"parameters": dict(action.parameters)},
            )
        changes: list[dict[str, object]] = []
        for operation in operations:
            if not isinstance(operation, dict):
                continue
            path = self.workspace_root / str(operation.get("path", ""))
            if not path.exists():
                changes.append(
                    AppliedChange(
                        path=str(operation.get("path", "")),
                        status="failed",
                        operation=str(operation.get("kind", "unknown")),
                        summary="Target path does not exist.",
                    ).to_dict()
                )
                continue
            original = path.read_text(encoding="utf-8")
            updated = original
            kind = str(operation.get("kind", "unknown"))
            if kind == "append":
                addition = str(operation.get("content", ""))
                updated = original + ("" if original.endswith("\n") or not original else "\n") + addition
            elif kind == "insert_before":
                anchor = str(operation.get("anchor", ""))
                content = str(operation.get("content", ""))
                matched_anchor = next((candidate for candidate in _operation_text_candidates(anchor) if candidate in original), "")
                if matched_anchor:
                    updated = original.replace(matched_anchor, f"{content}\n{matched_anchor}", 1)
                else:
                    changes.append(
                        AppliedChange(
                            path=str(operation.get("path", "")),
                            status="failed",
                            operation=kind,
                            summary="Insert-before anchor text was not found.",
                            before_sha256=_sha256_text(original),
                            after_sha256=_sha256_text(original),
                            preview=_mutation_preview(original, original),
                        ).to_dict()
                    )
                    continue
            elif kind == "insert_after":
                anchor = str(operation.get("anchor", ""))
                content = str(operation.get("content", ""))
                matched_anchor = next((candidate for candidate in _operation_text_candidates(anchor) if candidate in original), "")
                if matched_anchor:
                    updated = original.replace(matched_anchor, f"{matched_anchor}\n{content}", 1)
                else:
                    changes.append(
                        AppliedChange(
                            path=str(operation.get("path", "")),
                            status="failed",
                            operation=kind,
                            summary="Insert-after anchor text was not found.",
                            before_sha256=_sha256_text(original),
                            after_sha256=_sha256_text(original),
                            preview=_mutation_preview(original, original),
                        ).to_dict()
                    )
                    continue
            elif kind == "delete":
                old = str(operation.get("old", ""))
                matched_old = next((candidate for candidate in _operation_text_candidates(old) if candidate in original), "")
                if matched_old:
                    updated = original.replace(matched_old, "", 1)
                else:
                    changes.append(
                        AppliedChange(
                            path=str(operation.get("path", "")),
                            status="failed",
                            operation=kind,
                            summary="Delete target text was not found.",
                            before_sha256=_sha256_text(original),
                            after_sha256=_sha256_text(original),
                            preview=_mutation_preview(original, original),
                        ).to_dict()
                    )
                    continue
            elif kind == "replace":
                old = str(operation.get("old", ""))
                new = str(operation.get("new", ""))
                matched_old = next((candidate for candidate in _operation_text_candidates(old) if candidate in original), "")
                if matched_old:
                    updated = original.replace(matched_old, _decode_operation_text(new), 1)
                else:
                    changes.append(
                        AppliedChange(
                            path=str(operation.get("path", "")),
                            status="failed",
                            operation=kind,
                            summary="Replace target text was not found.",
                            before_sha256=_sha256_text(original),
                            after_sha256=_sha256_text(original),
                            preview=_mutation_preview(original, original),
                        ).to_dict()
                    )
                    continue
            else:
                changes.append(
                    AppliedChange(
                        path=str(operation.get("path", "")),
                        status="failed",
                        operation=kind,
                        summary="Unsupported edit operation.",
                        before_sha256=_sha256_text(original),
                        after_sha256=_sha256_text(original),
                        preview=_mutation_preview(original, original),
                    ).to_dict()
                )
                continue
            if updated == original:
                changes.append(
                    AppliedChange(
                        path=str(operation.get("path", "")),
                        status="skipped",
                        operation=kind,
                        summary="Edit produced no file change.",
                        before_sha256=_sha256_text(original),
                        after_sha256=_sha256_text(updated),
                        preview=_mutation_preview(original, updated),
                    ).to_dict()
                )
                continue
            path.write_text(updated, encoding="utf-8")
            changes.append(
                AppliedChange(
                    path=str(operation.get("path", "")),
                    status="applied",
                    operation=kind,
                    summary="Applied bounded edit operation.",
                    before_sha256=_sha256_text(original),
                    after_sha256=_sha256_text(updated),
                    preview=_mutation_preview(original, updated),
                ).to_dict()
            )
        status = "completed" if any(item.get("status") == "applied" for item in changes) else "blocked" if changes else "skipped"
        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=status,
            summary="Bounded file mutation actions executed.",
            payload={"applied_changes": changes},
        )

    def _execute_command(self, action: ActionRequest) -> ActionResult:
        command = action.parameters.get("command", [])
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status="failed",
                summary="Command action requires a string command list.",
                error="invalid_command",
                payload={"parameters": dict(action.parameters)},
            )
        result = self.runner.run(command, cwd=str(self.workspace_root))
        status = "passed" if result.exit_code == 0 else "failed"
        run_id = str(action.parameters.get("run_id") or "inline")
        artifact = self.artifact_store.write_command_result(
            run_id=run_id,
            action_id=action.action_id,
            command=command,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            failure_kind=_failure_kind(result),
        )
        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=status,
            summary="Command action executed.",
            error=result.error,
            payload={
                "command": command,
                "exit_code": result.exit_code,
                "stdout_preview": _preview_text(result.stdout),
                "stderr_preview": _preview_text(result.stderr),
                "failure_kind": _failure_kind(result),
                "artifact": artifact,
            },
        )


@dataclass(slots=True)
class RepoExplorer:
    artifact_store: ExecutionArtifactStore = field(default_factory=ExecutionArtifactStore)
    workspace_root: Path = field(default_factory=Path.cwd)
    toolbox: NativeToolbox | None = None
    max_candidates: int = 8

    def explore(self, request: ExecutionRequest) -> RepoExplorationReport:
        toolbox = self.toolbox or NativeToolbox(workspace_root=self.workspace_root, artifact_store=self.artifact_store)
        toolbox.workspace_root = self.workspace_root
        toolbox.artifact_store = self.artifact_store
        explicit_paths = _extract_paths(request.requirement)
        exploration_patterns = _exploration_patterns(request.requirement, explicit_paths)
        repo_map_result = toolbox.repo_map(exploration_patterns, depth=3)
        mapped_files = list(repo_map_result.get("files", [])) if isinstance(repo_map_result.get("files"), list) else []
        glob_result = toolbox.glob(exploration_patterns)
        glob_matches = list(glob_result.get("matches", [])) if isinstance(glob_result.get("matches"), list) else []
        find_files_result = toolbox.find_files(request.requirement, max_matches=self.max_candidates)
        filename_matches = (
            [dict(item) for item in find_files_result.get("matches", []) if isinstance(item, dict)]
            if isinstance(find_files_result.get("matches"), list)
            else []
        )
        filename_match_paths = [str(item.get("path")) for item in filename_matches if item.get("path")]
        search_paths = list(dict.fromkeys([*filename_match_paths, *mapped_files, *glob_matches]))
        search_result = toolbox.search(request.requirement, paths=search_paths, max_matches=self.max_candidates)
        all_files = list(dict.fromkeys([*filename_match_paths, *mapped_files, *glob_matches]))
        existing_paths = [path for path in explicit_paths if (self.workspace_root / path).exists()]
        candidate_paths = existing_paths[:]
        if not candidate_paths:
            candidate_paths = filename_match_paths[: self.max_candidates]
        if not candidate_paths:
            candidate_paths = [str(item.get("path")) for item in search_result.get("matches", []) if isinstance(item, dict) and item.get("path")]
        if not candidate_paths:
            candidate_paths = all_files[: self.max_candidates]
        candidate_paths = list(dict.fromkeys(path for path in candidate_paths if isinstance(path, str) and path.strip()))
        outline_result = toolbox.outline(candidate_paths[: self.max_candidates], max_entries=6, max_files=self.max_candidates)
        outline_records = (
            [dict(item) for item in outline_result.get("records", []) if isinstance(item, dict)]
            if isinstance(outline_result.get("records"), list)
            else []
        )
        outlined_paths = [
            str(item.get("path"))
            for item in sorted(
                outline_records,
                key=lambda item: (
                    -(len(item.get("outline", [])) if isinstance(item.get("outline"), list) else 0),
                    str(item.get("path", "")),
                ),
            )
            if item.get("path")
        ]
        read_targets = outlined_paths[: self.max_candidates] if outlined_paths else candidate_paths[: self.max_candidates]
        read_result = toolbox.read(read_targets, max_chars=8000)
        search_matches = (
            [dict(item) for item in search_result.get("matches", []) if isinstance(item, dict)]
            if isinstance(search_result.get("matches"), list)
            else []
        )
        read_records = (
            [dict(item) for item in read_result.get("records", []) if isinstance(item, dict)]
            if isinstance(read_result.get("records"), list)
            else []
        )
        artifact = self.artifact_store.write_repo_exploration(
            run_id=_execution_run_id(request),
            workspace_root=str(self.workspace_root),
            explicit_paths=explicit_paths,
            existing_paths=existing_paths,
            candidate_paths=candidate_paths[: self.max_candidates],
            file_listing=all_files,
        )
        return RepoExplorationReport(
            workspace_root=str(self.workspace_root),
            explicit_paths=explicit_paths,
            existing_paths=existing_paths,
            candidate_paths=candidate_paths[: self.max_candidates],
            file_count=len(all_files),
            artifact={
                **artifact,
                "tool_surface": toolbox.surface_summary(),
                "repo_map": repo_map_result,
                "glob": glob_result,
                "find_files": find_files_result,
                "search": search_result,
                "outline": outline_result,
                "read": read_result,
                "exploration_profile": {
                    "patterns": exploration_patterns,
                    "search_path_count": len(search_paths),
                    "mapped_directory_count": repo_map_result.get("directory_count"),
                    "filename_match_count": len(filename_matches),
                    "outline_record_count": len(outline_records),
                    "candidate_reason": (
                        "explicit_existing_paths"
                        if existing_paths
                        else "filename_matches"
                        if filename_matches
                        else "search_matches"
                        if search_result.get("match_count")
                        else "repo_map_fallback"
                    ),
                    "selected_candidates": candidate_paths[: self.max_candidates],
                },
                "exploration_evidence": {
                    "format": "agent_orchestrator.native_exploration_evidence.v1",
                    "candidate_reason": (
                        "explicit_existing_paths"
                        if existing_paths
                        else "filename_matches"
                        if filename_matches
                        else "search_matches"
                        if search_result.get("match_count")
                        else "repo_map_fallback"
                    ),
                    "explicit_path_hits": existing_paths,
                    "filename_match_count": len(filename_matches),
                    "filename_match_paths": filename_match_paths[: self.max_candidates],
                    "search_match_count": len(search_matches),
                    "search_match_paths": [
                        str(item.get("path"))
                        for item in search_matches[: self.max_candidates]
                        if item.get("path")
                    ],
                    "outline_paths": [
                        str(item.get("path"))
                        for item in outline_records[: self.max_candidates]
                        if item.get("path")
                    ],
                    "read_record_count": len(read_records),
                    "read_paths": [
                        str(item.get("path"))
                        for item in read_records[: self.max_candidates]
                        if item.get("path")
                    ],
                    "selected_candidates": candidate_paths[: self.max_candidates],
                    "shared_evidence_surface": [
                        "runtime_payload",
                        "workspace_index",
                        "ui_execution_summary",
                        "cli_execution_summary",
                        "outline_projection",
                    ],
                },
            },
        )


@dataclass(slots=True)
class ContextBuilder:
    def build(
        self,
        *,
        request: ExecutionRequest,
        strategy_plan: ExecutionPlan | None,
        repo_report: RepoExplorationReport,
    ) -> ExecutionContextPackage:
        return ExecutionContextPackage(
            requirement=request.requirement,
            route=request.route.to_dict(),
            strategy_summary=strategy_plan.summary() if strategy_plan is not None else {},
            session_context={
                "session_id": request.session_id,
                "turn_id": request.turn_id,
                "resume_kind": request.resume_kind,
            },
            repo_report=repo_report.to_dict(),
            task_contract=dict(request.task_contract or {}),
        )


@dataclass(slots=True)
class EditExecutor:
    action_executor: ActionExecutor = field(default_factory=ActionExecutor)
    workspace_root: Path = field(default_factory=Path.cwd)
    toolbox: NativeToolbox | None = None
    intent_refiner_transport: Callable[[str, dict[str, object], dict[str, str], int], dict[str, object]] | None = None

    def build_intent(
        self,
        *,
        request: ExecutionRequest,
        repo_report: RepoExplorationReport,
        context: ExecutionContextPackage,
        context_selection: dict[str, object] | None = None,
    ) -> EditIntent:
        toolbox = self.toolbox or NativeToolbox(workspace_root=self.workspace_root, artifact_store=self.action_executor.artifact_store)
        toolbox.workspace_root = self.workspace_root
        toolbox.artifact_store = self.action_executor.artifact_store
        self.toolbox = toolbox
        target_paths = repo_report.existing_paths or repo_report.candidate_paths[:3]
        operations = _extract_operations(request.requirement)
        operation_paths = [
            str(item.get("path", "")).strip()
            for item in operations
            if isinstance(item, dict) and str(item.get("path", "")).strip()
        ]
        if operation_paths:
            merged_target_paths = [*operation_paths]
            for path in target_paths:
                if path not in merged_target_paths:
                    merged_target_paths.append(path)
            target_paths = merged_target_paths
        explicit_paths = _extract_paths(request.requirement)
        if explicit_paths:
            merged_target_paths = [*target_paths]
            for path in explicit_paths:
                if path not in merged_target_paths:
                    merged_target_paths.append(path)
            target_paths = merged_target_paths
        patch_plan = [f"Inspect {path} and update the implementation if needed." for path in target_paths]
        mode = "report_first"
        if operations:
            mode = "direct_apply"
            patch_plan.extend(f"Apply {operation['kind']} to {operation['path']}." for operation in operations)
        elif target_paths:
            read_result = toolbox.read(target_paths[:3], max_chars=6000)
            matched = read_result.get("records", []) if isinstance(read_result, dict) else []
            if matched:
                patch_plan.append(f"Review {len(matched)} target files before editing.")
        refinement = _refine_edit_intent(
            request=request,
            repo_report=repo_report,
            context=context,
            context_selection=context_selection,
            mode=mode,
            target_paths=target_paths,
            patch_plan=patch_plan,
            transport=self.intent_refiner_transport,
        )
        refined_target_paths = target_paths
        refined_summary = (
            "Prepare a bounded implementation intent from repository context."
            if not operations
            else "Apply a bounded explicit edit operation and verify the result."
        )
        refined_patch_plan = patch_plan
        patch_preview = None
        if isinstance(refinement.get("refined_target_paths"), list):
            refined_target_paths = [str(item) for item in refinement["refined_target_paths"] if str(item).strip()]
        if isinstance(refinement.get("refined_summary"), str) and refinement["refined_summary"].strip():
            refined_summary = refinement["refined_summary"].strip()
        if isinstance(refinement.get("refined_patch_plan"), list):
            refined_patch_plan = [str(item) for item in refinement["refined_patch_plan"] if str(item).strip()]
        if operations:
            preview_result = toolbox.patch_preview(list(operations))
            patch_preview = dict(preview_result.payload) if isinstance(preview_result.payload, dict) else None
        return EditIntent(
            mode=mode,
            target_paths=refined_target_paths,
            summary=refined_summary,
            patch_plan=refined_patch_plan,
            operations=operations,
            patch_preview=patch_preview,
            refinement=refinement,
        )

    def apply(self, edit_intent: EditIntent) -> list[AppliedChange]:
        if edit_intent.mode != "direct_apply":
            return []
        toolbox = self.toolbox or NativeToolbox(workspace_root=self.workspace_root, artifact_store=self.action_executor.artifact_store)
        toolbox.workspace_root = self.workspace_root
        toolbox.artifact_store = self.action_executor.artifact_store
        toolbox.runner = self.action_executor.runner
        self.toolbox = toolbox
        result = toolbox.structured_patch(list(edit_intent.operations))
        changes = result.payload.get("applied_changes", [])
        if not isinstance(changes, list):
            return []
        applied: list[AppliedChange] = []
        for item in changes:
            if not isinstance(item, dict):
                continue
            applied.append(
                AppliedChange(
                    path=str(item.get("path", "")),
                    status=str(item.get("status", "")),
                    operation=str(item.get("operation", "")),
                    summary=str(item.get("summary", "")),
                    before_sha256=str(item.get("before_sha256")) if item.get("before_sha256") else None,
                    after_sha256=str(item.get("after_sha256")) if item.get("after_sha256") else None,
                    preview=dict(item.get("preview", {})) if isinstance(item.get("preview"), dict) else None,
                )
            )
        return applied


@dataclass(slots=True)
class VerificationRunner:
    action_executor: ActionExecutor = field(default_factory=ActionExecutor)
    runner: SubprocessCommandRunner = field(default_factory=SubprocessCommandRunner)
    workspace_root: Path = field(default_factory=Path.cwd)
    toolbox: NativeToolbox | None = None

    def run(
        self,
        request: ExecutionRequest,
        edit_intent: EditIntent,
        *,
        command_override: list[str] | None = None,
    ) -> VerificationReport:
        toolbox = self.toolbox or NativeToolbox(workspace_root=self.workspace_root, runner=self.runner, artifact_store=self.action_executor.artifact_store)
        toolbox.workspace_root = self.workspace_root
        toolbox.runner = self.runner
        toolbox.artifact_store = self.action_executor.artifact_store
        command = list(command_override) if isinstance(command_override, list) else []
        verification_targets = _verification_target_paths(edit_intent.target_paths)
        if not command and not verification_targets:
            return VerificationReport(
                status="skipped",
                command=[],
                exit_code=None,
                stdout="",
                stderr="",
                skipped_reason="no_target_paths",
                failure_kind=None,
            )
        if not command:
            command = ["python3", "-m", "compileall", *verification_targets]
        action_result = toolbox.verify(run_id=_execution_run_id(request), command=command)
        payload = action_result.payload
        return VerificationReport(
            status="passed" if action_result.status == "passed" else "failed",
            command=command,
            exit_code=int(payload["exit_code"]) if isinstance(payload.get("exit_code"), int) else None,
            stdout=str(payload.get("stdout_preview", "")),
            stderr=str(payload.get("stderr_preview", "")),
            skipped_reason=action_result.error,
            failure_kind=str(payload.get("failure_kind")) if payload.get("failure_kind") else None,
            artifact=dict(payload.get("artifact", {})) if isinstance(payload.get("artifact"), dict) else None,
        )


@dataclass(slots=True)
class VerifyLoop:
    verifier: VerificationRunner = field(default_factory=VerificationRunner)
    retry_budget: int = 1

    def verify(
        self,
        request: ExecutionRequest,
        edit_intent: EditIntent,
        *,
        command_override: list[str] | None = None,
        continuation_notes: list[str] | None = None,
        retry_budget_override: int | None = None,
    ) -> RepairLoopSummary:
        attempts: list[RepairAttempt] = []
        effective_retry_budget = self.retry_budget if retry_budget_override is None else max(retry_budget_override, 0)
        verification = _run_verifier_with_optional_override(
            self.verifier,
            request,
            edit_intent,
            command_override=command_override,
        )
        verification = VerificationReport(
            status=verification.status,
            command=verification.command,
            exit_code=verification.exit_code,
            stdout=verification.stdout,
            stderr=verification.stderr,
            skipped_reason=verification.skipped_reason,
            failure_kind=verification.failure_kind,
            artifact=verification.artifact,
            attempt_index=0,
        )
        attempts.append(
            RepairAttempt(
                attempt_index=0,
                action="initial_verify",
                target_paths=list(edit_intent.target_paths),
                verification=verification.to_dict(),
                notes=[
                    "Initial verification attempt.",
                    *[str(item) for item in continuation_notes or []],
                ],
            )
        )
        if verification.status != "failed":
            return RepairLoopSummary(
                outcome=verification.status,
                attempt_count=len(attempts),
                retry_budget=effective_retry_budget,
                attempts=[attempt.to_dict() for attempt in attempts],
                recovery_recommendation=_recovery_recommendation(verification, exhausted=False),
            )

        for retry_index in range(1, effective_retry_budget + 1):
            repaired_intent = EditIntent(
                mode=edit_intent.mode,
                target_paths=list(edit_intent.target_paths),
                summary=edit_intent.summary,
                patch_plan=[*edit_intent.patch_plan, "Retry with narrowed verification scope and re-check syntax."],
            )
            retried = _run_verifier_with_optional_override(
                self.verifier,
                request,
                repaired_intent,
                command_override=command_override,
            )
            retried = VerificationReport(
                status=retried.status,
                command=retried.command,
                exit_code=retried.exit_code,
                stdout=retried.stdout,
                stderr=retried.stderr,
                skipped_reason=retried.skipped_reason,
                failure_kind=retried.failure_kind,
                artifact=retried.artifact,
                attempt_index=retry_index,
            )
            attempts.append(
                RepairAttempt(
                    attempt_index=retry_index,
                    action="retry_verify",
                    target_paths=list(repaired_intent.target_paths),
                    verification=retried.to_dict(),
                    notes=["Retry after bounded repair policy."],
                )
            )
            if retried.status != "failed":
                return RepairLoopSummary(
                    outcome=retried.status,
                    attempt_count=len(attempts),
                    retry_budget=effective_retry_budget,
                    attempts=[attempt.to_dict() for attempt in attempts],
                    recovery_recommendation=_recovery_recommendation(retried, exhausted=False),
                )

        return RepairLoopSummary(
            outcome="failed",
            attempt_count=len(attempts),
            retry_budget=effective_retry_budget,
            attempts=[attempt.to_dict() for attempt in attempts],
            recovery_recommendation=_recovery_recommendation(verification, exhausted=True),
        )


def _extract_paths(requirement: str) -> list[str]:
    tokens = shlex.split(requirement.replace("\n", " "), posix=False)
    paths: list[str] = []
    for token in tokens:
        normalized = token.strip("`'\".,:;()[]{}")
        if "." not in normalized:
            continue
        if "/" not in normalized and not re.fullmatch(r"[\w.-]+\.[A-Za-z0-9]+", normalized):
            continue
        paths.append(normalized)
    deduped: list[str] = []
    for path in paths:
        if path not in deduped:
            deduped.append(path)
    return deduped


def _exploration_patterns(requirement: str, explicit_paths: list[str]) -> list[str]:
    patterns: list[str] = []
    for raw_path in explicit_paths:
        normalized = raw_path.strip().lstrip("./")
        if not normalized:
            continue
        patterns.append(normalized)
        parent = str(Path(normalized).parent)
        if parent not in {"", "."}:
            patterns.append(f"{parent}/**/*")
    lowered = requirement.lower()
    if any(token in lowered for token in {"test", "verify", "pytest"}):
        patterns.append("tests/**/*.py")
    if any(token in lowered for token in {"doc", "readme", "guide"}):
        patterns.extend(["docs/**/*.md", "README.md"])
    patterns.extend(["src/**/*.py", "**/*.py", "**/*.md", "**/*.json", "**/*.ts", "**/*.tsx"])
    ordered: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        if pattern and pattern not in seen:
            seen.add(pattern)
            ordered.append(pattern)
    return ordered


def _refine_edit_intent(
    *,
    request: ExecutionRequest,
    repo_report: RepoExplorationReport,
    context: ExecutionContextPackage,
    context_selection: dict[str, object] | None,
    mode: str,
    target_paths: list[str],
    patch_plan: list[str],
    transport: Callable[[str, dict[str, object], dict[str, str], int], dict[str, object]] | None,
) -> dict[str, object]:
    base_summary = (
        "Prepare a bounded implementation intent from repository context."
        if mode != "direct_apply"
        else "Apply a bounded explicit edit operation and verify the result."
    )
    if mode != "report_first":
        return {
            "used_model": False,
            "applied": False,
            "source": "deterministic_only",
            "reason": "Intent refinement is only enabled for report_first mode.",
            "refined_summary": base_summary,
            "refined_target_paths": list(target_paths),
            "refined_patch_plan": list(patch_plan),
        }
    config = EnvSlotFillConfig.from_env()
    if config is None:
        return {
            "used_model": False,
            "applied": False,
            "source": "deterministic_only",
            "reason": "Intent refinement config was unavailable.",
            "refined_summary": base_summary,
            "refined_target_paths": list(target_paths),
            "refined_patch_plan": list(patch_plan),
        }
    candidates = list(dict.fromkeys([*target_paths, *repo_report.candidate_paths[:5]]))
    payload = {
        "model": config.model,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Refine a bounded coding-agent implementation intent for a report-first execution step. "
                    "Return only JSON with keys summary, target_paths, patch_plan, rationale. "
                    "Keep the plan bounded, conservative, and aligned to the provided candidate files. "
                    "Do not invent file paths outside the provided candidates."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "requirement": request.requirement,
                        "mode": mode,
                        "initial_target_paths": target_paths,
                        "initial_patch_plan": patch_plan,
                        "candidate_paths": candidates,
                        "task_contract": context.task_contract,
                        "context_selection": context_selection or {},
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    request_url = f"{config.base_url}/chat/completions"
    selected_transport = transport or _default_openai_compatible_transport
    try:
        response = selected_transport(request_url, payload, headers, config.timeout_seconds)
        content = _extract_openai_message_content(response)
        parsed = json.loads(content) if content else {}
    except Exception as exc:
        return {
            "used_model": False,
            "applied": False,
            "source": "deterministic_fallback",
            "reason": f"Intent refinement request failed: {exc}",
            "refined_summary": base_summary,
            "refined_target_paths": list(target_paths),
            "refined_patch_plan": list(patch_plan),
        }
    if not isinstance(parsed, dict):
        return {
            "used_model": False,
            "applied": False,
            "source": "deterministic_fallback",
            "reason": "Intent refinement returned a non-object JSON payload.",
            "refined_summary": base_summary,
            "refined_target_paths": list(target_paths),
            "refined_patch_plan": list(patch_plan),
        }
    allowed_paths = set(candidates)
    refined_target_paths = [
        str(item).strip()
        for item in parsed.get("target_paths", [])
        if isinstance(item, str) and str(item).strip() in allowed_paths
    ]
    refined_patch_plan = [
        str(item).strip()
        for item in parsed.get("patch_plan", [])
        if isinstance(item, str) and str(item).strip()
    ]
    refined_summary = parsed.get("summary") if isinstance(parsed.get("summary"), str) else base_summary
    if not refined_target_paths:
        refined_target_paths = list(target_paths)
    if not refined_patch_plan:
        refined_patch_plan = list(patch_plan)
    return {
        "used_model": True,
        "applied": True,
        "source": "llm",
        "reason": "Intent refinement completed via configured OpenAI-compatible model.",
        "rationale": str(parsed.get("rationale", "")).strip(),
        "refined_summary": refined_summary.strip() if isinstance(refined_summary, str) and refined_summary.strip() else base_summary,
        "refined_target_paths": refined_target_paths,
        "refined_patch_plan": refined_patch_plan,
    }


def _run_verifier_with_optional_override(
    verifier: object,
    request: ExecutionRequest,
    edit_intent: EditIntent,
    *,
    command_override: list[str] | None,
) -> VerificationReport:
    run = getattr(verifier, "run")
    try:
        return run(request, edit_intent, command_override=command_override)
    except TypeError:
        return run(request, edit_intent)


def _extract_operations(requirement: str) -> list[dict[str, object]]:
    operations_with_pos: list[tuple[int, dict[str, object]]] = []
    for match in re.finditer(
        r"""append\s+["'`](?P<content>.+?)["'`]\s+to\s+(?P<path>[\w./-]+\.[A-Za-z0-9]+)""",
        requirement,
        flags=re.IGNORECASE,
    ):
        operations_with_pos.append(
            (
                match.start(),
                {
                    "kind": "append",
                    "path": match.group("path"),
                    "content": match.group("content"),
                },
            )
        )
    for match in re.finditer(
        r"""replace\s+["'`](?P<old>.+?)["'`]\s+with\s+["'`](?P<new>.+?)["'`]\s+in\s+(?P<path>[\w./-]+\.[A-Za-z0-9]+)""",
        requirement,
        flags=re.IGNORECASE,
    ):
        operations_with_pos.append(
            (
                match.start(),
                {
                    "kind": "replace",
                    "path": match.group("path"),
                    "old": match.group("old"),
                    "new": match.group("new"),
                },
            )
        )
    for match in re.finditer(
        r"""insert\s+["'`](?P<content>.+?)["'`]\s+before\s+["'`](?P<anchor>.+?)["'`]\s+in\s+(?P<path>[\w./-]+\.[A-Za-z0-9]+)""",
        requirement,
        flags=re.IGNORECASE,
    ):
        operations_with_pos.append(
            (
                match.start(),
                {
                    "kind": "insert_before",
                    "path": match.group("path"),
                    "anchor": match.group("anchor"),
                    "content": match.group("content"),
                },
            )
        )
    for match in re.finditer(
        r"""insert\s+["'`](?P<content>.+?)["'`]\s+after\s+["'`](?P<anchor>.+?)["'`]\s+in\s+(?P<path>[\w./-]+\.[A-Za-z0-9]+)""",
        requirement,
        flags=re.IGNORECASE,
    ):
        operations_with_pos.append(
            (
                match.start(),
                {
                    "kind": "insert_after",
                    "path": match.group("path"),
                    "anchor": match.group("anchor"),
                    "content": match.group("content"),
                },
            )
        )
    for match in re.finditer(
        r"""delete\s+["'`](?P<old>.+?)["'`]\s+from\s+(?P<path>[\w./-]+\.[A-Za-z0-9]+)""",
        requirement,
        flags=re.IGNORECASE,
    ):
        operations_with_pos.append(
            (
                match.start(),
                {
                    "kind": "delete",
                    "path": match.group("path"),
                    "old": match.group("old"),
                },
            )
        )
    operations_with_pos.sort(key=lambda item: item[0])
    return [item for _, item in operations_with_pos]


def _verification_target_paths(target_paths: list[str]) -> list[str]:
    verifiable_suffixes = {".py", ".pyi"}
    filtered: list[str] = []
    for item in target_paths:
        path = Path(str(item))
        if path.suffix.lower() in verifiable_suffixes:
            filtered.append(str(item))
    return filtered


def _operation_text_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for candidate in (text, _decode_operation_text(text)):
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _decode_operation_text(text: str) -> str:
    try:
        return bytes(text, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return text


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _failure_kind(result: CommandResult) -> str | None:
    if result.error:
        return "command_error"
    if result.exit_code not in {None, 0}:
        return "nonzero_exit"
    return None


def _recovery_recommendation(verification: VerificationReport, *, exhausted: bool) -> dict[str, object]:
    if verification.status in {"passed", "skipped"}:
        return {
            "action": "continue",
            "reason": "verification_satisfied",
            "human_review_recommended": False,
        }
    return {
        "action": "inspect_and_retry_later" if exhausted else "retry_completed",
        "reason": verification.failure_kind or "verification_failed",
        "human_review_recommended": exhausted,
    }


def _preview_text(text: str, *, limit: int = 500) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n...[truncated]"


def _mutation_preview(before: str, after: str, *, limit: int = 160) -> dict[str, object]:
    return {
        "before_preview": _preview_text(before, limit=limit),
        "after_preview": _preview_text(after, limit=limit),
        "changed": before != after,
    }


def _execution_run_id(request: ExecutionRequest) -> str:
    if request.turn_id:
        return f"coding-{request.turn_id}"
    if request.session_id:
        return f"coding-{request.session_id}"
    return "coding-inline"


def _action_result_with_governance(result: ActionResult, governance: dict[str, object]) -> ActionResult:
    return ActionResult(
        action_id=result.action_id,
        action_type=result.action_type,
        status=result.status,
        summary=result.summary,
        error=result.error,
        artifacts=list(result.artifacts),
        payload={
            **dict(result.payload),
            "governance": governance,
        },
    )


def _classify_action_risk(action: ActionRequest) -> str:
    if action.action_type == "run_command":
        return "high"
    if action.action_type == "file_mutation":
        operations = action.parameters.get("operations", [])
        if isinstance(operations, list) and any(
            isinstance(item, dict) and str(item.get("kind", "")).lower() == "replace"
            for item in operations
        ):
            return "high"
        return "medium"
    return action.risk_level


def _is_within_workspace(workspace_root: Path, candidate: Path) -> bool:
    try:
        workspace = workspace_root.resolve()
        target = candidate.resolve(strict=False)
    except OSError:
        return False
    try:
        target.relative_to(workspace)
    except ValueError:
        return False
    return True
