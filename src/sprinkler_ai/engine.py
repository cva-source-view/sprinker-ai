from __future__ import annotations

from typing import Dict, Any
from .weather import fetch_weather


# =========================================================
# UTIL
# =========================================================

def c_to_f(c: float) -> float:
    return (c * 9 / 5) + 32


def avg(vals):
    return sum(vals) / len(vals) if vals else 0


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
    if avg_high >= 90:
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
    # Soil memory clamp (important)
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
    Simple time rule:
    - allowed: before 8am OR after 6:30pm
    """

    if not (hour < 8 or hour >= 18.5):
        return False, "Outside watering window"

    if data["rain_forecast"] >= 2.5:
        return False, "Rain expected"

    if data["rain_past"] + data["rain_forecast"] >= 5:
        return False, "Recent rain sufficient"

    if data["score"] < 8:
        return False, "Low demand"

    return True, "Water needed"


# =========================================================
# SCHEDULER
# =========================================================

def runtime_minutes(score: float) -> int:
    return max(5, min(20, int(score * 0.6)))


def build_schedule(weather, hour: int = 19):
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
                {"label": "morning", "start": "06:00", "duration": minutes},
                {"label": "evening", "start": "18:30", "duration": minutes}
            ]
        }
    }


# =========================================================
# TEST RUN
# =========================================================

def test():
    weather = fetch_weather(39.74, -104.99, "America/Denver")

    result = build_schedule(weather, hour=19)

    print("\n=== ENGINE OUTPUT ===")
    print(result)


if __name__ == "__main__":
    test()
def run_engine(weather, config):
    """
    Main entry point for CLI.
    Takes weather + config and returns irrigation decision.
    """

    result = compute_water_demand(weather)

    et = result["et"]
    rain_forecast = result["rain_forecast"]
    rain_past = result["rain_past"]
    avg_temp = result["avg_high_f"]

    # -----------------------------
    # HARD RULES (your constraints)
    # -----------------------------

    # 1. Rain-based skip logic
    if rain_forecast >= 2.5:
        return {
            "water": False,
            "reason": "DEFER: meaningful rain expected soon",
            "debug": result,
        }

    if rain_forecast + rain_past >= 5:
        return {
            "water": False,
            "reason": "DEFER: soil likely partially replenished",
            "debug": result,
        }

    # 2. Time rule (already in your system design)
    schedule_minutes = min(20, int(result["score"] // 2))  # safe cap

    # 3. Water decision threshold
    water = result["score"] > 20

    schedule = {
        "run_minutes": schedule_minutes,
        "windows": [
            {"label": "morning", "start": "06:00", "duration": schedule_minutes},
            {"label": "evening", "start": "18:30", "duration": schedule_minutes},
        ],
    }

    return {
        "water": water,
        "reason": "Water needed" if water else "Low demand",
        "debug": result,
        "schedule": schedule,
    }