from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

HISTORY_FILE = Path("data/history.jsonl")
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def append_event(event: str):
    entry = {
        "event": event,
        "date": datetime.now().strftime("%Y-%m-%d")
    }

    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def last_event(event_name: str):
    if not HISTORY_FILE.exists():
        return None

    last = None

    with open(HISTORY_FILE, "r") as f:
        for line in f:
            try:
                obj = json.loads(line)
                if obj.get("event") == event_name:
                    last = obj["date"]
            except:
                continue

    return last