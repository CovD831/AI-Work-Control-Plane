"""Lightweight event recording for orchestration runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class Event:
    name: str
    details: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(slots=True)
class EventLog:
    events: list[Event] = field(default_factory=list)

    def record(self, name: str, **details: Any) -> None:
        self.events.append(Event(name=name, details=details))

    def to_list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": event.name,
                "timestamp": event.timestamp,
                "details": event.details,
            }
            for event in self.events
        ]
