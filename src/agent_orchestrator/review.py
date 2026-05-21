"""Structured review result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["low", "medium", "high", "critical"]
ReviewVerdict = Literal["approve", "needs_attention"]


@dataclass(frozen=True, slots=True)
class Finding:
    severity: Severity
    title: str
    body: str
    file: str
    line_start: int
    line_end: int
    confidence: float
    recommendation: str

    def __post_init__(self) -> None:
        if self.line_start < 1 or self.line_end < 1:
            raise ValueError("Finding line numbers are 1-based.")
        if self.line_end < self.line_start:
            raise ValueError("Finding line_end must be >= line_start.")
        if not 0 <= self.confidence <= 1:
            raise ValueError("Finding confidence must be between 0 and 1.")

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "title": self.title,
            "body": self.body,
            "file": self.file,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True, slots=True)
class ReviewResult:
    verdict: ReviewVerdict
    summary: str
    findings: list[Finding] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.verdict == "approve" and self.findings:
            raise ValueError("Approved reviews cannot contain findings.")
        if self.verdict == "needs_attention" and not self.findings:
            raise ValueError("needs_attention reviews must include findings.")

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "summary": self.summary,
            "findings": [finding.to_dict() for finding in self.findings],
            "next_steps": self.next_steps,
        }
