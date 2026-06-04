from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

from .weather import fetch_weather


# =========================================================
# PATHS (STATE + LOGS)
# =========================================================

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

WATER_LOG = DATA_DIR / "watering_log.json"
EVENT_LOG = DATA_DIR / "sprinkler.log"


# =========================================================
# LOGGING (replaces logger.py)
# =========================================================

def log_event(msg: str):
    EVENT_LOG.parent.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(EVENT_LOG, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")


# =========================================================
# STATE MEMORY (replaces watering_log.py)
# =========================================================

def load_state() -> dict:
    if not WATER_LOG.exists():
        return {
            "last_watering_date": None
        }
    return json.loads(WATER_LOG.read_text())


def save_state(state: dict):
    WATER_LOG.write_text(json.dumps(state, indent=2))


def today():
    return datetime.now().strftime("%Y-%m-%d")


def days_since(date_str: str | None) -> int:
    if not date_str:
        return 999
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return (datetime.now() - d).days
    except:
        return 999


# =========================================================
# UTIL
# =========================================================

def c_to_f(c: float) -> float:
    return (c * 9 / 5) + 32


def avg(vals):
    return sum(vals) / len(vals) if vals else 0


# =========================================================
# CORE WEATHER SCORING
# =========================================================

def compute_score(weather):
    past = weather.past
    forecast = weather.forecast

    et = sum(d.et0_mm for d in forecast)
    rain_forecast = sum(d.precipitation_mm for d in forecast)
    rain_past = sum(d.precipitation_mm for d in past)

    highs = [c_to_f(d.temp_max_c) for d in forecast]
    avg_high = avg(highs)

    if avg_high >= 95:
        temp_factor = 1.35
    elif avg_high >= 90:
        temp_factor = 1.25
    elif avg_high >= 80:
        temp_factor = 1.10
    else:
        temp_factor = 0.95

    score = (et * temp_factor) - (rain_forecast * 1.2) - (rain_past * 0.5)

    if rain_past < 2 and score > 25:
        score *= 0.75

    return {
        "score": round(score, 2),
        "et": round(et, 2),
        "rain_forecast": round(rain_forecast, 2),
        "rain_past": round(rain_past, 2),
        "avg_high_f": round(avg_high, 1),
        "temp_factor": temp_factor,
    }


# =========================================================
# DECISION ENGINE
# =========================================================

def decide(data: dict, hour: int, state: dict):
    avg_temp = data["avg_high_f"]

    # ---------------- MORNING ONLY ----------------
    if hour >= 8:
        return False, "Outside morning window"

    # ---------------- RAIN SAFETY ----------------
    if data["rain_forecast"] >= 2.5:
        return False, "Rain expected soon"

    if data["rain_forecast"] + data["rain_past"] >= 5:
        return False, "Recent rain sufficient"

    # ---------------- ALTERNATE DAY MEMORY ----------------
    last_watered = days_since(state.get("last_watering_date"))

    extreme_heat = avg_temp >= 95

    if not extreme_heat and last_watered <= 1:
        return False, f"Alternate-day rule ({last_watered} day gap)"

    # ---------------- LOW DEMAND ----------------
    if data["score"] < 8:
        return False, "Low demand"

    return True, "Water needed"


# =========================================================
# SCHEDULER
# =========================================================

def runtime_minutes(score: float) -> int:
    return max(5, min(20, int(score * 0.6)))


def build_engine(weather, hour: int = 6):
    state = load_state()
    data = compute_score(weather)

    ok, reason = decide(data, hour, state)

    if not ok:
        log_event(f"SKIP: {reason}")
        return {
            "water": False,
            "reason": reason,
            "debug": data,
            "schedule": None
        }

    minutes = runtime_minutes(data["score"])

    log_event(f"WATER: {minutes} min (score {data['score']})")

    # update memory
    state["last_watering_date"] = today()
    save_state(state)

    return {
        "water": True,
        "reason": reason,
        "debug": data,
        "schedule": {
            "run_minutes": minutes,
            "windows": [
                {
                    "label": "morning",
                    "start": "06:00",
                    "duration": minutes
                }
            ]
        }
    }


# =========================================================
# ENTRY POINT (CLI USE)
# =========================================================

def run_engine(weather, config=None):
    return build_engine(weather, hour=6)


# =========================================================
# TEST
# =========================================================

def test():
    weather = fetch_weather(
        39.74,
        -104.99,
        "America/Denver"
    )

    result = build_engine(weather)

    print("\n=== ENGINE OUTPUT ===")
    print(result)


if __name__ == "__main__":
    test()