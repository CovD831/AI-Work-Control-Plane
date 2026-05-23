"""Execution topology helpers for agent-enabled orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ProviderStep = Literal["claude", "codex"]
ModeName = Literal["success_first", "speed_first", "cost_first"]
TopologyName = Literal["solo", "team", "team_with_adversarial_review"]


@dataclass(frozen=True, slots=True)
class ExecutionTopology:
    mode: ModeName
    agent_enabled: bool
    depth: int
    provider_flow: tuple[ProviderStep, ...]
    topology_name: TopologyName = "team"

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "agent_enabled": self.agent_enabled,
            "depth": self.depth,
            "provider_flow": list(self.provider_flow),
            "topology_name": self.topology_name,
        }


def build_execution_topology(
    mode: ModeName,
    *,
    agent_enabled: bool | None = None,
    depth: int | None = None,
) -> ExecutionTopology:
    defaults: dict[ModeName, tuple[bool, tuple[ProviderStep, ...]]] = {
        "success_first": (True, ("claude", "codex", "claude")),
        "speed_first": (True, ("claude", "codex")),
        "cost_first": (False, ("codex",)),
    }

    default_enabled, base_flow = defaults[mode]
    enabled = default_enabled if agent_enabled is None else agent_enabled
    if not enabled:
        return ExecutionTopology(mode=mode, agent_enabled=False, depth=0, provider_flow=(), topology_name="solo")

    effective_depth = len(base_flow) if depth is None else max(0, min(depth, len(base_flow)))
    topology_name: TopologyName = "team_with_adversarial_review"
    if effective_depth <= 1:
        topology_name = "team"
    return ExecutionTopology(
        mode=mode,
        agent_enabled=True,
        depth=effective_depth,
        provider_flow=base_flow[:effective_depth],
        topology_name=topology_name,
    )


def build_execution_topology_from_decision(
    *,
    selected_topology: TopologyName,
    mode: ModeName,
    provider_flow: tuple[ProviderStep, ...],
) -> ExecutionTopology:
    if selected_topology == "solo":
        return ExecutionTopology(
            mode=mode,
            agent_enabled=False,
            depth=0,
            provider_flow=(),
            topology_name="solo",
        )
    depth = 3 if selected_topology == "team_with_adversarial_review" else max(1, min(len(provider_flow), 2))
    return ExecutionTopology(
        mode=mode,
        agent_enabled=True,
        depth=depth,
        provider_flow=provider_flow[:depth],
        topology_name=selected_topology,
    )
