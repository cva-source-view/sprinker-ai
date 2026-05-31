from __future__ import annotations

from datetime import datetime
from .weather import fetch_weather


# =========================================================
# UTIL
# =========================================================

def c_to_f(c: float) -> float:
    return (c * 9 / 5) + 32


def avg(vals):
    return sum(vals) / len(vals) if vals else 0


def is_alternate_day() -> bool:
    """
    Water on odd-numbered calendar days.
    Example:
    1,3,5,7 = allowed
    2,4,6,8 = skipped
    """
    return datetime.now().day % 2 == 1


# =========================================================
# CORE ENGINE
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

    # ---------------------------
    # Temperature factor
    # ---------------------------
    if avg_high >= 95:
        temp_factor = 1.35
    elif avg_high >= 90:
        temp_factor = 1.25
    elif avg_high >= 80:
        temp_factor = 1.10
    else:
        temp_factor = 0.95

    # ---------------------------
    # Base score
    # ---------------------------
    score = (et * temp_factor) - (rain_forecast * 1.2) - (rain_past * 0.5)

    # ---------------------------
    # Soil memory clamp
    # ---------------------------
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
# DECISION LOGIC
# =========================================================

def should_water(data: dict, hour: int):
    """
    Rules:
    - morning only: before 8 AM
    - skip if rain expected
    - alternate days unless extreme heat
    """

    avg_temp = data["avg_high_f"]

    # ---------------------------
    # Morning only
    # ---------------------------
    if hour >= 8:
        return False, "Outside morning watering window"

    # ---------------------------
    # Rain skip
    # ---------------------------
    if data["rain_forecast"] >= 2.5:
        return False, "Rain expected"

    if data["rain_past"] + data["rain_forecast"] >= 5:
        return False, "Recent rain sufficient"

    # ---------------------------
    # Alternate-day drought resistance
    # Override if very hot
    # ---------------------------
    if avg_temp < 95 and not is_alternate_day():
        return False, "Alternate-day drought schedule"

    # ---------------------------
    # Low demand skip
    # ---------------------------
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
# CLI ENTRY
# =========================================================

def run_engine(weather, config):
    return build_schedule(weather, hour=6)


# =========================================================
# TEST RUN
# =========================================================

def test():
    weather = fetch_weather(
        39.74,
        -104.99,
        "America/Denver"
    )

    result = build_schedule(weather)

    print("\n=== ENGINE OUTPUT ===")
    print(result)


if __name__ == "__main__":
    test()