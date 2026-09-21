from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Event:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "timestamp": self.timestamp, "data": self.data}


class EventBus:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def emit(self, event_type: str, **data: Any) -> Event:
        event = Event(event_type, data)
        self.events.append(event)
        return event

    def snapshot(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.events]
