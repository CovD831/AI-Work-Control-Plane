"""Execution-runtime abstractions for the coding-agent skeleton."""

from __future__ import annotations

from typing import Protocol

from agent_orchestrator.execution.models import ExecutionRequest, ExecutionResult


class ExecutionRuntime(Protocol):
    """Abstract execution backend for a coding-agent request."""

    name: str

    def run(self, request: ExecutionRequest) -> ExecutionResult:
        """Run the request synchronously and return a structured execution result."""

    def start(self, request: ExecutionRequest) -> ExecutionResult:
        """Start the request asynchronously and return a structured handle payload."""

    def resume_from_state(self, request: ExecutionRequest) -> ExecutionResult:
        """Resume a previously persisted execution request using the runtime's state contract."""
