"""Lightweight task router for the coding-agent entry skeleton."""

from __future__ import annotations

import re

from agent_orchestrator.intake.models import ClarifyPolicy, ExecutionMode, TaskKind, TaskRouterResult
from agent_orchestrator.memory import MemoryStore


QUESTION_PATTERNS = [
    r"^what\b",
    r"^why\b",
    r"^how\b",
    r"^explain\b",
    r"^分析\b",
    r"^解释\b",
    r"^为什么\b",
    r"^怎么\b",
]

DOCS_KEYWORDS = ["docs", "documentation", "readme", "document", "文档", "说明"]
INVESTIGATION_KEYWORDS = ["investigate", "analyze", "diagnose", "root cause", "summarize", "分析", "排查", "定位"]
MIGRATION_KEYWORDS = ["migrate", "migration", "rollback", "schema", "数据库迁移", "迁移"]
FIX_KEYWORDS = ["fix", "bug", "broken", "issue", "repair", "修", "修复", "报错"]
RISK_KEYWORDS = ["auth", "payment", "security", "permission", "database", "migration", "隐私", "权限"]
AMBIGUITY_PATTERNS = [
    r"帮我做一下",
    r"优化一下",
    r"看一下",
    r"处理一下",
    r"尽量",
    r"应该",
    r"可能",
]
PATH_HINT_PATTERN = r"\b[\w./-]+\.(?:py|ts|tsx|js|jsx|json|md|yml|yaml)\b"
SYMBOL_HINT_PATTERN = r"\b[A-Za-z_][\w]*\.[A-Za-z_][\w]*\b"


class TaskRouter:
    """Cheap request classifier that decides entry policy before heavy clarify."""

    native_learning_store: MemoryStore | None = None

    def route(self, requirement: str) -> TaskRouterResult:
        normalized = " ".join(requirement.strip().split())
        lowered = normalized.lower()
        reasons: list[str] = []

        task_kind = self._task_kind(normalized, lowered, reasons)
        ambiguity_level = self._ambiguity_level(normalized, lowered, task_kind, reasons)
        risk_level = self._risk_level(lowered, task_kind, reasons)
        scope_confidence = self._scope_confidence(normalized, task_kind, reasons)

        requires_human_confirmation = task_kind == TaskKind.MIGRATION and risk_level == "high"
        if requires_human_confirmation:
            reasons.append("Migration-style work is treated as confirmation-sensitive in Phase 1.")

        learning_assets = self._learning_assets(normalized, lowered)
        clarify_policy = self._clarify_policy(task_kind, ambiguity_level, risk_level, scope_confidence, learning_assets)
        execution_mode = self._execution_mode(task_kind)
        default_path, operating_boundary, selection_reason, handoff_reason_code, fallback_reason_code = self._execution_boundary(
            task_kind=task_kind,
            execution_mode=execution_mode,
            risk_level=risk_level,
            requires_human_confirmation=requires_human_confirmation,
            learning_assets=learning_assets,
            reasons=reasons,
        )
        needs_repo_context = task_kind in {
            TaskKind.DIRECT_FIX,
            TaskKind.GENERAL_CODING,
            TaskKind.INVESTIGATION,
            TaskKind.MIGRATION,
            TaskKind.DOCS,
        }

        return TaskRouterResult(
            task_kind=task_kind,
            clarify_policy=clarify_policy,
            execution_mode=execution_mode,
            ambiguity_level=ambiguity_level,
            risk_level=risk_level,
            scope_confidence=scope_confidence,
            needs_repo_context=needs_repo_context,
            requires_human_confirmation=requires_human_confirmation,
            default_path=default_path,
            operating_boundary=operating_boundary,
            selection_reason=selection_reason,
            handoff_reason_code=handoff_reason_code,
            fallback_reason_code=fallback_reason_code,
            reasons=reasons,
        )

    def _learning_assets(self, normalized: str, lowered: str) -> dict[str, object]:
        store = self.native_learning_store
        if store is None:
            return {"trajectory_hits": [], "memory_hits": [], "skill_hits": []}
        trajectory_hits = store.search(normalized, limit=5)
        memory_hits = store.search(lowered, limit=5)
        skill_hits = [record for record in store.query(record_type="memory", limit=5) if "skill" in str(record.get("summary", "")).lower()]
        return {
            "trajectory_hits": trajectory_hits,
            "memory_hits": memory_hits,
            "skill_hits": skill_hits,
        }

    def _task_kind(self, normalized: str, lowered: str, reasons: list[str]) -> TaskKind:
        if any(re.search(pattern, lowered) for pattern in QUESTION_PATTERNS):
            reasons.append("Request begins like a question or explanation task.")
            return TaskKind.QUESTION_ONLY
        if any(keyword in lowered for keyword in MIGRATION_KEYWORDS):
            reasons.append("Request includes migration or rollback language.")
            return TaskKind.MIGRATION
        if any(keyword in lowered for keyword in INVESTIGATION_KEYWORDS):
            reasons.append("Request includes investigation language and now defaults to native when scope can be bounded.")
            return TaskKind.INVESTIGATION
        if any(keyword in lowered for keyword in DOCS_KEYWORDS):
            reasons.append("Request includes documentation language.")
            return TaskKind.DOCS
        if any(keyword in lowered for keyword in FIX_KEYWORDS):
            reasons.append("Request includes fix or bug language.")
            return TaskKind.DIRECT_FIX
        if re.search(PATH_HINT_PATTERN, normalized) or re.search(SYMBOL_HINT_PATTERN, normalized):
            reasons.append("Request names concrete files or symbols, suggesting a coding task.")
            return TaskKind.GENERAL_CODING
        reasons.append("Defaulting to a general coding task.")
        return TaskKind.GENERAL_CODING

    def _ambiguity_level(
        self,
        normalized: str,
        lowered: str,
        task_kind: TaskKind,
        reasons: list[str],
    ) -> str:
        if len(normalized) < 18:
            reasons.append("Short requirement suggests ambiguity.")
            return "high"
        if any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in AMBIGUITY_PATTERNS):
            reasons.append("Requirement includes vague phrasing.")
            return "high"
        if task_kind == TaskKind.QUESTION_ONLY:
            return "low"
        if not re.search(PATH_HINT_PATTERN, normalized) and task_kind in {TaskKind.DIRECT_FIX, TaskKind.GENERAL_CODING}:
            reasons.append("Coding request does not identify any concrete file or symbol.")
            return "medium"
        return "low"

    def _risk_level(self, lowered: str, task_kind: TaskKind, reasons: list[str]) -> str:
        if any(keyword in lowered for keyword in RISK_KEYWORDS):
            reasons.append("Requirement includes risk-sensitive domain language.")
            return "high"
        if task_kind == TaskKind.MIGRATION:
            reasons.append("Migration tasks are treated as high risk.")
            return "high"
        if task_kind in {TaskKind.INVESTIGATION, TaskKind.DOCS}:
            return "low"
        return "medium"

    def _scope_confidence(self, normalized: str, task_kind: TaskKind, reasons: list[str]) -> str:
        if re.search(PATH_HINT_PATTERN, normalized) or re.search(SYMBOL_HINT_PATTERN, normalized):
            return "high"
        if task_kind == TaskKind.QUESTION_ONLY:
            return "high"
        if task_kind in {TaskKind.MIGRATION, TaskKind.GENERAL_CODING, TaskKind.DIRECT_FIX}:
            reasons.append("Execution scope must be inferred from repository context.")
            return "medium"
        return "low"

    def _clarify_policy(
        self,
        task_kind: TaskKind,
        ambiguity_level: str,
        risk_level: str,
        scope_confidence: str,
        learning_assets: dict[str, object],
    ) -> ClarifyPolicy:
        if task_kind == TaskKind.QUESTION_ONLY:
            return ClarifyPolicy.SKIP
        if risk_level == "high" or task_kind == TaskKind.MIGRATION:
            return ClarifyPolicy.DEEP
        if ambiguity_level == "high" or scope_confidence == "low":
            return ClarifyPolicy.DEEP
        if task_kind == TaskKind.INVESTIGATION and self._learning_hint_supports_native(learning_assets):
            return ClarifyPolicy.SKIP
        if ambiguity_level == "medium" or scope_confidence == "medium":
            return ClarifyPolicy.LIGHT
        return ClarifyPolicy.SKIP

    def _execution_mode(self, task_kind: TaskKind) -> ExecutionMode:
        if task_kind == TaskKind.QUESTION_ONLY:
            return ExecutionMode.NO_EXECUTION
        if task_kind in {TaskKind.DIRECT_FIX, TaskKind.GENERAL_CODING, TaskKind.DOCS}:
            return ExecutionMode.CODING_AGENT
        return ExecutionMode.LEGACY

    def _execution_boundary(
        self,
        *,
        task_kind: TaskKind,
        execution_mode: ExecutionMode,
        risk_level: str,
        requires_human_confirmation: bool,
        learning_assets: dict[str, object],
        reasons: list[str],
    ) -> tuple[str, str, str, str | None, str | None]:
        if execution_mode == ExecutionMode.NO_EXECUTION:
            return (
                "none",
                "no_execution",
                "Question-only work stays outside execution runtimes.",
                None,
                None,
            )
        if task_kind in {TaskKind.DIRECT_FIX, TaskKind.GENERAL_CODING, TaskKind.DOCS, TaskKind.INVESTIGATION}:
            if task_kind == TaskKind.INVESTIGATION and self._learning_hint_supports_native(learning_assets):
                reasons.append("Native learning assets point to an established investigation -> edit -> verify path.")
            elif task_kind == TaskKind.INVESTIGATION:
                reasons.append("Investigation-style work is now covered by the native main path when evidence supports a bounded edit follow-through.")
            return (
                "native",
                "native_preferred",
                "Bounded repository edits, docs-linked updates, and bounded investigation/rewrite tasks default to the native governed path.",
                None,
                "native_runtime_unavailable",
            )
        if task_kind == TaskKind.MIGRATION or requires_human_confirmation or risk_level == "high":
            return (
                "external",
                "external_preferred",
                "High-risk or confirmation-sensitive work stays on the governed external/handoff path.",
                "risk_exceeds_native_bounded_path",
                "external_runtime_unavailable",
            )
        return (
            "external",
            "fallback_governed",
            "Investigation-style work remains on the legacy/external path until native coverage expands.",
            "task_class_not_yet_native_default" if task_kind != TaskKind.INVESTIGATION else "native_learning_unavailable",
            "external_runtime_unavailable",
        )

    def _learning_hint_supports_native(self, learning_assets: dict[str, object]) -> bool:
        trajectory_hits = learning_assets.get("trajectory_hits", []) if isinstance(learning_assets.get("trajectory_hits"), list) else []
        memory_hits = learning_assets.get("memory_hits", []) if isinstance(learning_assets.get("memory_hits"), list) else []
        skill_hits = learning_assets.get("skill_hits", []) if isinstance(learning_assets.get("skill_hits"), list) else []
        return bool(trajectory_hits or memory_hits or skill_hits)
