from __future__ import annotations

import json
from pathlib import Path
from datetime import date, datetime


LOG_FILE = Path("data/watering_log.json")


def load_log():
    if not LOG_FILE.exists():
        return {
            "last_watering_date": None,
            "last_rain_date": None,
            "last_moisture_date": None,
        }

    return json.loads(LOG_FILE.read_text())


def save_log(data):
    LOG_FILE.parent.mkdir(exist_ok=True)

    LOG_FILE.write_text(
        json.dumps(data, indent=2)
    )


def mark_watered():
    data = load_log()

    today = date.today().isoformat()

    data["last_watering_date"] = today
    data["last_moisture_date"] = today

    save_log(data)


def mark_rain():
    data = load_log()

    today = date.today().isoformat()

    data["last_rain_date"] = today
    data["last_moisture_date"] = today

    save_log(data)


def days_since_moisture():
    data = load_log()

    if not data["last_moisture_date"]:
        return 999

    last = datetime.fromisoformat(
        data["last_moisture_date"]
    ).date()

    return (date.today() - last).days


if __name__ == "__main__":
    print(load_log())