from __future__ import annotations

from datetime import datetime
from .history import get_last_event, days_since, log_event


# =========================================================
# UTIL
# =========================================================

def c_to_f(c: float) -> float:
    return (c * 9 / 5) + 32


def avg(vals):
    return sum(vals) / len(vals) if vals else 0


# =========================================================
# HISTORY-BASED LOGIC
# =========================================================

def is_alternate_day() -> bool:
    """
    Uses actual watering history instead of calendar day.
    Prevents drift from rain skips or missed cycles.
    """

    last = get_last_event("watered")

    if not last:
        return True  # first run always allowed

    last_date = datetime.strptime(last, "%Y-%m-%d")
    today = datetime.now()

    return (today - last_date).days >= 2


# =========================================================
# CORE MODEL
# =========================================================

def compute_water_demand(weather):
    past = weather.past
    forecast = weather.forecast

    et = sum(d.et0_mm for d in forecast)
    rain_forecast = sum(d.precipitation_mm for d in forecast)
    rain_past = sum(d.precipitation_mm for d in past)

    highs = [c_to_f(d.temp_max_c) for d in forecast]
    lows = [c_to_f(d.temp_min_c) for d in forecast]

    avg_high = avg(highs)
    avg_low = avg(lows)

    # temperature boost
    if avg_high >= 95:
        temp_factor = 1.35
    elif avg_high >= 90:
        temp_factor = 1.25
    elif avg_high >= 80:
        temp_factor = 1.10
    else:
        temp_factor = 0.95

    score = (et * temp_factor) - (rain_forecast * 1.2) - (rain_past * 0.5)

    # soil memory clamp
    if rain_past < 2 and score > 25:
        score *= 0.75

    return {
        "score": round(score, 2),
        "et": round(et, 2),
        "rain_forecast": round(rain_forecast, 2),
        "rain_past": round(rain_past, 2),
        "avg_high_f": round(avg_high, 1),
        "avg_low_f": round(avg_low, 1),
        "temp_factor": temp_factor,
    }


# =========================================================
# DECISION RULES
# =========================================================

def should_water(data: dict, hour: int):
    avg_temp = data["avg_high_f"]

    # Morning only rule
    if hour >= 8:
        return False, "Outside morning window"

    # Rain rules
    if data["rain_forecast"] >= 2.5:
        return False, "Rain expected"

    if data["rain_past"] + data["rain_forecast"] >= 5:
        return False, "Recent rain sufficient"

    # Alternate day logic (FIXED)
    if avg_temp < 95 and not is_alternate_day():
        return False, "Alternate-day schedule"

    # demand floor
    if data["score"] < 8:
        return False, "Low demand"

    return True, "Water needed"


# =========================================================
# SCHEDULER
# =========================================================

def runtime_minutes(score: float) -> int:
    return max(5, min(20, int(score * 0.6)))


def build_schedule(weather, hour: int = 6):
    data = compute_water_demand(weather)

    decision, reason = should_water(data, hour)

    if not decision:
        return {
            "water": False,
            "reason": reason,
            "debug": data,
            "schedule": None
        }

    minutes = runtime_minutes(data["score"])

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
# ENTRY POINT FOR CLI
# =========================================================

from .history import log_event


def run_engine(weather, config):
    result = build_schedule(weather, hour=6)

    # ---------------- LOG EVERYTHING ----------------
    log_event({
        "type": "water" if result["water"] else "skip",
        "decision": result["water"],
        "reason": result["reason"],
        "weather": result["debug"],
        "schedule": result["schedule"],
    })

    return result


# =========================================================
# LOCAL TEST
# =========================================================

def test():
    from .weather import fetch_weather

    weather = fetch_weather(
        39.74,
        -104.99,
        "America/Denver"
    )

    print(build_schedule(weather))


if __name__ == "__main__":
    test()