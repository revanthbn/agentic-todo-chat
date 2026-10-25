EVENTS = {"catalog_shown", "skill_loaded", "proposed", "validated", "clarified", "executed", "failed"}


class Trace:
    def __init__(self):
        self.events: list[dict] = []

    def emit(self, event: str, **data) -> None:
        assert event in EVENTS, f"unknown trace event {event}"
        self.events.append({"event": event, **data})

    def names(self) -> list[str]:
        return [e["event"] for e in self.events]


def format_event(e: dict) -> str:
    data = ", ".join(f"{k}={v}" for k, v in e.items() if k != "event")
    return f"[{e['event']}] {data}"
