from __future__ import annotations

from dataclasses import dataclass

from .engine import run_engine


# =========================================================
# FAKE WEATHER OBJECTS
# =========================================================

@dataclass
class FakeDay:
    precipitation_mm: float
    et0_mm: float
    temp_max_c: float
    temp_min_c: float


@dataclass
class FakeWeather:
    past: list[FakeDay]
    forecast: list[FakeDay]


# =========================================================
# INPUT HELPERS
# =========================================================

def ask_float(prompt: str, default: float) -> float:
    value = input(f"{prompt} [{default}]: ").strip()

    if not value:
        return default

    return float(value)


# =========================================================
# MAIN
# =========================================================

def main():

    print("\n=== MANUAL SPRINKLER TEST ===\n")
    print("Leave blank to use defaults.\n")

    avg_high_f = ask_float("Average forecast high (°F)", 90)
    avg_low_f = ask_float("Average forecast low (°F)", 65)

    rain_forecast = ask_float("Forecast rain total (mm)", 0)
    rain_past = ask_float("Past rain total (mm)", 0)

    et = ask_float("Forecast ET total (mm)", 30)

    high_c = (avg_high_f - 32) * 5 / 9
    low_c = (avg_low_f - 32) * 5 / 9

    # Split totals across days so engine works normally

    past = [
        FakeDay(
            precipitation_mm=rain_past / 3,
            et0_mm=0,
            temp_max_c=high_c,
            temp_min_c=low_c,
        )
        for _ in range(3)
    ]

    forecast = [
        FakeDay(
            precipitation_mm=rain_forecast / 5,
            et0_mm=et / 5,
            temp_max_c=high_c,
            temp_min_c=low_c,
        )
        for _ in range(5)
    ]

    weather = FakeWeather(
        past=past,
        forecast=forecast,
    )

    result = run_engine(weather, None)

    print("\n==============================")
    print("ENGINE RESULT")
    print("==============================\n")

    print(f"Decision : {'WATER' if result['water'] else 'SKIP'}")
    print(f"Reason   : {result['reason']}")

    print("\nDebug:")

    for k, v in result["debug"].items():
        print(f"  {k}: {v}")

    if result["schedule"]:
        print("\nSchedule:")
        print(result["schedule"])

    print()


if __name__ == "__main__":
    main()