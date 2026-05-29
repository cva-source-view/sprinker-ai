from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from src.sprinkler_ai.weather import fetch_weather


# =========================================================
# Helpers
# =========================================================

def c_to_f(c: float) -> float:
    return (c * 9 / 5) + 32


def avg(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0


# =========================================================
# Weather scoring model
# =========================================================

def compute_water_demand(weather):
    past = weather.past
    forecast = weather.forecast

    et = sum(d.et0_mm for d in forecast)
    rain_forecast = sum(d.precipitation_mm for d in forecast)
    rain_past = sum(d.precipitation_mm for d in past)

    highs_f = [c_to_f(d.temp_max_c) for d in forecast]
    lows_f = [c_to_f(d.temp_min_c) for d in forecast]

    avg_high = avg(highs_f)
    avg_low = avg(lows_f)

    # Temperature factor
    if avg_high >= 90:
        temp_factor = 1.25
    elif avg_high >= 80:
        temp_factor = 1.10
    else:
        temp_factor = 0.95

    score = (et * temp_factor) - (rain_forecast * 1.2) - (rain_past * 0.5)

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
# Time rules (your constraints)
# =========================================================

def is_safe_time(hour: int, minute: int):
    minutes = hour * 60 + minute

    morning_end = 8 * 60
    evening_start = 18 * 60 + 30

    if 0 <= minutes < morning_end:
        return True, "morning window"
    if minutes >= evening_start:
        return True, "evening window"

    return False, "unsafe window (family time / evaporation risk)"


# =========================================================
# Decision layer
# =========================================================

def should_water(weather, hour: int, minute: int):
    data = compute_water_demand(weather)

    safe, reason_time = is_safe_time(hour, minute)

    # Hard blocks
    if not safe:
        return False, f"BLOCKED: {reason_time}", data

    if data["rain_forecast"] >= 2.5:
        return False, "DEFER: rain expected soon", data

    if data["rain_forecast"] + data["rain_past"] >= 5:
        return False, "DEFER: rain cycle sufficient", data

    # Demand thresholds
    if data["score"] < 8:
        return False, "LOW DEMAND", data

    if data["score"] < 18:
        return True, "MODERATE DEMAND", data

    return True, "HIGH DEMAND", data


# =========================================================
# Scheduling engine
# =========================================================

def compute_runtime_minutes(score: float) -> int:
    """
    Converts demand score → irrigation runtime
    capped at 20 min (your requirement)
    """
    return max(5, min(20, int(score * 0.6)))


def build_schedule(weather, hour: int = 19, minute: int = 0):
    """
    Main scheduler output
    """

    decision, reason, data = should_water(weather, hour, minute)

    if not decision:
        return {
            "water": False,
            "reason": reason,
            "schedule": None,
            "debug": data
        }

    runtime = compute_runtime_minutes(data["score"])

    schedule = {
        "water": True,
        "reason": reason,
        "run_minutes": runtime,
        "windows": [
            {
                "label": "morning",
                "start": "05:30",
                "duration": runtime
            },
            {
                "label": "evening",
                "start": "18:30",
                "duration": runtime
            }
        ]
    }

    return {
        "water": True,
        "reason": reason,
        "schedule": schedule,
        "debug": data
    }


# =========================================================
# FULL DEBUG RUN
# =========================================================

def test():
    weather = fetch_weather(39.74, -104.99, "America/Denver")

    result = build_schedule(weather, hour=19, minute=0)

    print("\n=== FULL WEATHER DEBUG ===")

    d = result["debug"]

    print("\n🌡 Temperature")
    print(f"High Avg: {d['avg_high_f']}°F")
    print(f"Low Avg:  {d['avg_low_f']}°F")

    print("\n🌧 Rain")
    print(f"Past: {d['rain_past']} mm")
    print(f"Forecast: {d['rain_forecast']} mm")

    print("\n🌿 ET")
    print(f"Total ET: {d['et']} mm")

    print("\n⚙ Model")
    print(f"Temp factor: {d['temp_factor']}")
    print(f"Score: {d['score']}")

    print("\n=== FINAL DECISION ===")

    if not result["water"]:
        print(result["reason"])
        print("SKIP TODAY")
        return

    print(result["reason"])
    print(f"Run time: {result['schedule']['run_minutes']} min per session")

    print("\n🕒 Schedule")
    for w in result["schedule"]["windows"]:
        print(f"- {w['label']} @ {w['start']} → {w['duration']} min")


if __name__ == "__main__":
    test()