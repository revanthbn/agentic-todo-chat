from dataclasses import dataclass, field


@dataclass
class State:
    history: list[dict] = field(default_factory=list)
    last_referenced_id: int | None = None
    # Set when check() asked a clarifying question: {"skill", "args", "candidate_ids"}
    pending: dict | None = None
