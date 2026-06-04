from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_FILE = Path("data/history.jsonl")
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def log_event(entry: dict) -> None:
    """
    Append a structured event to history.jsonl
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **entry
    }

    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_last_event(event_type: str):
    """
    Returns last matching event from history
    """
    if not HISTORY_FILE.exists():
        return None

    last = None

    with open(HISTORY_FILE, "r") as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get("type") == event_type:
                    last = data
            except Exception:
                continue

    return last


def days_since(event_type: str) -> int:
    """
    How many days since last event type occurred
    """
    last = get_last_event(event_type)
    if not last:
        return 999

    last_time = datetime.fromisoformat(last["timestamp"])
    now = datetime.now(timezone.utc)

    return (now - last_time).days