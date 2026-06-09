"""Deterministic policy routing for automatic orchestration mode selection."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from agent_orchestrator.policies import OrchestrationMode, PolicyProfile, get_policy


@dataclass(frozen=True, slots=True)
class TaskProfile:
    ambiguity: str
    risk: str
    complexity: str
    parallelism: str
    cost_pressure: str
    latency_pressure: str
    recommended_mode: OrchestrationMode
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "ambiguity": self.ambiguity,
            "risk": self.risk,
            "complexity": self.complexity,
            "parallelism": self.parallelism,
            "cost_pressure": self.cost_pressure,
            "latency_pressure": self.latency_pressure,
            "recommended_mode": self.recommended_mode.value,
            "reasons": self.reasons,
        }


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    mode: OrchestrationMode
    profile: TaskProfile
    policy: PolicyProfile
    reasons: list[str] = field(default_factory=list)
    candidates: list[dict[str, object]] = field(default_factory=list)
    rejected_alternatives: list[dict[str, object]] = field(default_factory=list)
    consensus: dict[str, object] = field(default_factory=dict)
    confidence: float = 0.5

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "profile": self.profile.to_dict(),
            "policy": self.policy.to_dict(),
            "reasons": self.reasons,
            "candidates": self.candidates,
            "rejected_alternatives": self.rejected_alternatives,
            "consensus": self.consensus,
            "confidence": self.confidence,
        }


AMBIGUITY_PATTERNS = [
    r"帮我做一下",
    r"优化",
    r"改进",
    r"重构一下",
    r"看看",
    r"弄一下",
    r"尽量",
    r"应该",
]

RISK_KEYWORDS = [
    "auth",
    "payment",
    "security",
    "migration",
    "database",
    "delete",
    "permission",
    "privacy",
    "data loss",
]

COMPLEXITY_KEYWORDS = [
    "multi-service",
    "architecture",
    "integration",
    "refactor",
    "distributed",
    "concurrent",
    "workflow",
    "orchestration",
]

PARALLELISM_KEYWORDS = [
    "multiple",
    "batch",
    "modules",
    "components",
    "parallel",
    "independent",
    "many files",
    "test suite",
]

COST_PRESSURE_KEYWORDS = [
    "便宜",
    "低成本",
    "少 token",
    "少token",
    "快点简单做",
]

LATENCY_PRESSURE_KEYWORDS = [
    "asap",
    "马上",
    "快速",
    "urgent",
    "今天内",
    "先做最小版本",
]


@dataclass(slots=True)
class PolicyRouter:
    def profile(self, requirement: str) -> TaskProfile:
        text = requirement.strip().lower()
        reasons: list[str] = []

        ambiguity = _score_text(requirement, AMBIGUITY_PATTERNS, threshold_short_text=8)
        risk = _score_keywords(text, RISK_KEYWORDS)
        complexity = _score_keywords(text, COMPLEXITY_KEYWORDS)
        parallelism = _score_keywords(text, PARALLELISM_KEYWORDS)
        cost_pressure = _score_keywords(text, COST_PRESSURE_KEYWORDS)
        latency_pressure = _score_keywords(text, LATENCY_PRESSURE_KEYWORDS)

        if ambiguity == "high":
            reasons.append("Requirement language is vague or too short.")
        if risk == "high":
            reasons.append("Requirement contains high-risk keywords.")
        if complexity == "high":
            reasons.append("Requirement suggests broader architecture or integration work.")
        if parallelism == "high":
            reasons.append("Requirement suggests independent work can run in parallel.")
        if cost_pressure == "high":
            reasons.append("User expressed cost sensitivity.")
        if latency_pressure == "high":
            reasons.append("User expressed urgency or speed pressure.")

        mode, decision_reasons, confidence = self._select_mode_from_signals(
            ambiguity=ambiguity,
            risk=risk,
            complexity=complexity,
            parallelism=parallelism,
            cost_pressure=cost_pressure,
            latency_pressure=latency_pressure,
        )
        reasons.extend(decision_reasons)

        return TaskProfile(
            ambiguity=ambiguity,
            risk=risk,
            complexity=complexity,
            parallelism=parallelism,
            cost_pressure=cost_pressure,
            latency_pressure=latency_pressure,
            recommended_mode=mode,
            reasons=reasons,
        )

    def select_mode(self, profile: TaskProfile) -> OrchestrationMode:
        return profile.recommended_mode

    def route(self, requirement: str) -> RoutingDecision:
        profile = self.profile(requirement)
        mode = self.select_mode(profile)
        policy = get_policy(mode)
        confidence = _confidence_for_profile(profile)
        candidates = _build_mode_candidates(profile, selected_mode=mode)
        return RoutingDecision(
            mode=mode,
            profile=profile,
            policy=policy,
            reasons=profile.reasons,
            candidates=candidates,
            rejected_alternatives=[candidate for candidate in candidates if candidate.get("mode") != mode.value],
            consensus=_build_route_consensus(candidates, selected_mode=mode),
            confidence=confidence,
        )

    def _select_mode_from_signals(
        self,
        *,
        ambiguity: str,
        risk: str,
        complexity: str,
        parallelism: str,
        cost_pressure: str,
        latency_pressure: str,
    ) -> tuple[OrchestrationMode, list[str], float]:
        reasons: list[str] = []

        if risk == "high":
            reasons.append("High risk forces success_first.")
            return OrchestrationMode.SUCCESS_FIRST, reasons, 0.95

        if ambiguity == "high":
            reasons.append("High ambiguity forces success_first.")
            return OrchestrationMode.SUCCESS_FIRST, reasons, 0.9

        if parallelism == "high" and ambiguity == "low" and risk != "high":
            reasons.append("High parallelism with low ambiguity favors speed_first.")
            return OrchestrationMode.SPEED_FIRST, reasons, 0.8

        if complexity == "low" and risk == "low" and ambiguity == "low":
            reasons.append("Low complexity, low risk, and low ambiguity favor cost_first.")
            return OrchestrationMode.COST_FIRST, reasons, 0.75

        if latency_pressure == "high" and risk != "high":
            reasons.append("Urgent work without high risk leans speed_first.")
            return OrchestrationMode.SPEED_FIRST, reasons, 0.7

        if cost_pressure == "high" and complexity == "low" and risk == "low":
            reasons.append("Cost pressure with simple work favors cost_first.")
            return OrchestrationMode.COST_FIRST, reasons, 0.7

        reasons.append("Defaulting to success_first for ambiguous or mixed signals.")
        return OrchestrationMode.SUCCESS_FIRST, reasons, 0.6


def _score_text(requirement: str, patterns: list[str], *, threshold_short_text: int = 0) -> str:
    if len(requirement.strip()) <= threshold_short_text:
        return "high"
    for pattern in patterns:
        if re.search(pattern, requirement, flags=re.IGNORECASE):
            return "high"
    return "low"


def _score_keywords(text: str, keywords: list[str]) -> str:
    return "high" if any(keyword in text for keyword in keywords) else "low"


def _confidence_for_profile(profile: TaskProfile) -> float:
    if profile.risk == "high" or profile.ambiguity == "high":
        return 0.95
    if profile.parallelism == "high" and profile.ambiguity == "low":
        return 0.8
    if profile.cost_pressure == "high" or profile.latency_pressure == "high":
        return 0.7
    return 0.6


def _build_mode_candidates(profile: TaskProfile, *, selected_mode: OrchestrationMode) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for mode in (
        OrchestrationMode.SUCCESS_FIRST,
        OrchestrationMode.SPEED_FIRST,
        OrchestrationMode.COST_FIRST,
    ):
        score = _candidate_score(profile, mode)
        candidates.append(
            {
                "mode": mode.value,
                "selected": mode == selected_mode,
                "score": score,
                "rationale": _candidate_rationale(profile, mode),
            }
        )
    return candidates


def _candidate_rationale(profile: TaskProfile, mode: OrchestrationMode) -> list[str]:
    reasons: list[str] = []
    if mode == OrchestrationMode.SUCCESS_FIRST:
        if profile.risk == "high":
            reasons.append("High risk favors stronger review and safer escalation.")
        if profile.ambiguity == "high":
            reasons.append("High ambiguity favors more cautious orchestration.")
        if not reasons:
            reasons.append("Success-first remains the conservative default for mixed signals.")
        return reasons
    if mode == OrchestrationMode.SPEED_FIRST:
        if profile.parallelism == "high":
            reasons.append("Independent work can be accelerated through parallel execution.")
        if profile.latency_pressure == "high":
            reasons.append("Urgency favors faster execution with lighter decision overhead.")
        if not reasons:
            reasons.append("Speed-first is viable when risk stays below the strictest threshold.")
        return reasons

    if profile.cost_pressure == "high":
        reasons.append("Cost sensitivity favors lower-depth execution.")
    if profile.complexity == "low" and profile.risk == "low" and profile.ambiguity == "low":
        reasons.append("Simple low-risk work can justify the smallest execution shape.")
    if not reasons:
        reasons.append("Cost-first is only attractive when scope and risk stay small.")
    return reasons


def _candidate_score(profile: TaskProfile, mode: OrchestrationMode) -> int:
    score = 0
    if mode == OrchestrationMode.SUCCESS_FIRST:
        if profile.risk == "high":
            score += 4
        if profile.ambiguity == "high":
            score += 4
        if profile.complexity == "high":
            score += 1
        if score == 0:
            score = 2
        return score
    if mode == OrchestrationMode.SPEED_FIRST:
        if profile.parallelism == "high":
            score += 4
        if profile.latency_pressure == "high":
            score += 3
        if profile.risk == "low":
            score += 1
        return score

    if profile.cost_pressure == "high":
        score += 3
    if profile.complexity == "low":
        score += 2
    if profile.risk == "low":
        score += 2
    if profile.ambiguity == "low":
        score += 1
    return score


def _build_route_consensus(candidates: list[dict[str, object]], *, selected_mode: OrchestrationMode) -> dict[str, object]:
    ranked = sorted(candidates, key=lambda item: int(item.get("score", 0)), reverse=True)
    selected = next((item for item in ranked if item.get("mode") == selected_mode.value), ranked[0] if ranked else {})
    runner_up = next((item for item in ranked if item.get("mode") != selected_mode.value), None)
    selected_score = int(selected.get("score", 0)) if isinstance(selected, dict) else 0
    runner_up_score = int(runner_up.get("score", 0)) if isinstance(runner_up, dict) else 0
    delta = selected_score - runner_up_score
    disagreement = "high" if delta <= 1 else "medium" if delta <= 3 else "low"
    return {
        "selected_mode": selected_mode.value,
        "selected_score": selected_score,
        "runner_up_mode": runner_up.get("mode") if isinstance(runner_up, dict) else None,
        "runner_up_score": runner_up_score if runner_up else None,
        "disagreement_level": disagreement,
        "candidate_count": len(candidates),
    }
