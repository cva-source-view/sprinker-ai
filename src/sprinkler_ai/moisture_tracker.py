from __future__ import annotations

import json
from pathlib import Path
from datetime import date, datetime

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

TRACKER_FILE = DATA_DIR / "watering_log.json"


def load_tracker() -> dict:
    if not TRACKER_FILE.exists():
        return {
            "last_watering_date": None,
            "last_rain_date": None,
            "last_moisture_date": None,
        }

    try:
        with open(TRACKER_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {
            "last_watering_date": None,
            "last_rain_date": None,
            "last_moisture_date": None,
        }


def save_tracker(data: dict):
    with open(TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=2)


def record_watering():
    data = load_tracker()

    today = date.today().isoformat()

    data["last_watering_date"] = today
    data["last_moisture_date"] = today

    save_tracker(data)


def record_rain():
    data = load_tracker()

    today = date.today().isoformat()

    data["last_rain_date"] = today
    data["last_moisture_date"] = today

    save_tracker(data)


def days_since_moisture() -> int:
    data = load_tracker()

    last = data.get("last_moisture_date")

    if not last:
        return 999

    last_date = datetime.strptime(last, "%Y-%m-%d").date()

    return (date.today() - last_date).days