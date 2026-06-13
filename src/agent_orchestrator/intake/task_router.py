"""Lightweight task router for the coding-agent entry skeleton."""

from __future__ import annotations

import re

from agent_orchestrator.intake.models import ClarifyPolicy, ExecutionMode, TaskKind, TaskRouterResult


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

        clarify_policy = self._clarify_policy(task_kind, ambiguity_level, risk_level, scope_confidence)
        execution_mode = self._execution_mode(task_kind)
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
            reasons=reasons,
        )

    def _task_kind(self, normalized: str, lowered: str, reasons: list[str]) -> TaskKind:
        if any(re.search(pattern, lowered) for pattern in QUESTION_PATTERNS):
            reasons.append("Request begins like a question or explanation task.")
            return TaskKind.QUESTION_ONLY
        if any(keyword in lowered for keyword in MIGRATION_KEYWORDS):
            reasons.append("Request includes migration or rollback language.")
            return TaskKind.MIGRATION
        if any(keyword in lowered for keyword in INVESTIGATION_KEYWORDS):
            reasons.append("Request includes investigation language.")
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
    ) -> ClarifyPolicy:
        if task_kind == TaskKind.QUESTION_ONLY:
            return ClarifyPolicy.SKIP
        if risk_level == "high" or task_kind == TaskKind.MIGRATION:
            return ClarifyPolicy.DEEP
        if ambiguity_level == "high" or scope_confidence == "low":
            return ClarifyPolicy.DEEP
        if ambiguity_level == "medium" or scope_confidence == "medium":
            return ClarifyPolicy.LIGHT
        return ClarifyPolicy.SKIP

    def _execution_mode(self, task_kind: TaskKind) -> ExecutionMode:
        if task_kind == TaskKind.QUESTION_ONLY:
            return ExecutionMode.NO_EXECUTION
        if task_kind in {TaskKind.DIRECT_FIX, TaskKind.GENERAL_CODING, TaskKind.DOCS}:
            return ExecutionMode.CODING_AGENT
        return ExecutionMode.LEGACY
