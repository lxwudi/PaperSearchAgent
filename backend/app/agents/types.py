from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AgentEvent:
    event_type: str
    from_agent: str | None = None
    to_agent: str | None = None
    reason: str | None = None
    payload: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
