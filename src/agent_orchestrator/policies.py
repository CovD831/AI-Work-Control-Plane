"""Policy profiles for deriving modes from the success-first parent architecture."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

Parallelism = Literal["limited", "controlled", "aggressive"]
ReviewPolicy = bool | Literal["risk_based"]


class OrchestrationMode(str, Enum):
    SUCCESS_FIRST = "success_first"
    SPEED_FIRST = "speed_first"
    COST_FIRST = "cost_first"


@dataclass(frozen=True, slots=True)
class PolicyProfile:
    mode: OrchestrationMode
    max_depth: int
    planner_agents: int
    review_required: ReviewPolicy
    rescue_enabled: bool
    rescue_policy: Literal["always_available", "on_failure_only", "disabled"]
    parallelism: Parallelism

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "max_depth": self.max_depth,
            "planner_agents": self.planner_agents,
            "review_required": self.review_required,
            "rescue_enabled": self.rescue_enabled,
            "rescue_policy": self.rescue_policy,
            "parallelism": self.parallelism,
        }


def get_policy(mode: OrchestrationMode) -> PolicyProfile:
    profiles = {
        OrchestrationMode.SUCCESS_FIRST: PolicyProfile(
            mode=OrchestrationMode.SUCCESS_FIRST,
            max_depth=3,
            planner_agents=4,
            review_required=True,
            rescue_enabled=True,
            rescue_policy="always_available",
            parallelism="controlled",
        ),
        OrchestrationMode.SPEED_FIRST: PolicyProfile(
            mode=OrchestrationMode.SPEED_FIRST,
            max_depth=2,
            planner_agents=1,
            review_required="risk_based",
            rescue_enabled=True,
            rescue_policy="on_failure_only",
            parallelism="aggressive",
        ),
        OrchestrationMode.COST_FIRST: PolicyProfile(
            mode=OrchestrationMode.COST_FIRST,
            max_depth=1,
            planner_agents=1,
            review_required=False,
            rescue_enabled=True,
            rescue_policy="on_failure_only",
            parallelism="limited",
        ),
    }
    return profiles[mode]
