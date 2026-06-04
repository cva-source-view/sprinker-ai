from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime

from .config import Config
from .weather import fetch_weather
from .core import run_engine


# -----------------------------
# HELPERS
# -----------------------------
def _is_alternate_day() -> bool:
    return datetime.now().day % 2 == 1


# -----------------------------
# CLEAN PRETTY PRINT
# -----------------------------
def _print_engine(result: dict) -> None:
    debug = result.get("debug", {})
    schedule = result.get("schedule")

    print("\n=== FULL IRRIGATION DECISION ===\n")

    # ---------------- WEATHER SUMMARY ----------------
    print("🌡 WEATHER MODEL")
    print(f"Avg High: {debug.get('avg_high_f', 'N/A')}°F")
    print(f"Avg Low:  {debug.get('avg_low_f', 'N/A')}°F\n")

    # ---------------- RAIN ----------------
    print("🌧 RAIN")
    print(f"Past Rain:      {debug.get('rain_past', 0):.1f} mm")
    print(f"Forecast Rain:  {debug.get('rain_forecast', 0):.1f} mm\n")

    # ---------------- ET ----------------
    print("🌿 EVAPOTRANSPIRATION")
    print(f"ET Total: {debug.get('et', 0):.1f} mm\n")

    # ---------------- MODEL ----------------
    print("⚙ MODEL")
    print(f"Score:        {debug.get('score', 0):.2f}")
    print(f"Temp Factor:  {debug.get('temp_factor', 1.0)}\n")

    # ---------------- RULES ----------------
    print("🕒 RULES")
    print("Allowed watering window: 06:00–08:00")
    print(
        f"Alternate-day schedule: "
        f"{'YES (watering day)' if _is_alternate_day() else 'NO (skip day)'}"
    )
    print("Extreme heat override: 95°F+\n")

    # ---------------- DECISION ----------------
    print("🚿 DECISION")
    print("WATER\n" if result["water"] else "SKIP\n")
    print(f"Reason: {result['reason']}\n")

    # ---------------- SCHEDULE ----------------
    print("📅 SCHEDULE")

    if schedule:
        print(f"Run Minutes: {schedule.get('run_minutes', 0)}\n")

        for w in schedule.get("windows", []):
            print(f"• {w['label'].upper()}")
            print(f"  Start: {w['start']}")
            print(f"  Duration: {w['duration']} min\n")
    else:
        print("No watering scheduled.\n")


# -----------------------------
# MAIN
# -----------------------------
async def _run(dry_run: bool) -> int:
    config = Config.load()

    print("[1/3] Fetching weather...")
    weather = fetch_weather(
        config.location.latitude,
        config.location.longitude,
        config.location.timezone,
    )

    print("[2/3] Running irrigation engine...")
    result = run_engine(weather, config)

    _print_engine(result)

    print("[3/3] Execution stage")

    if dry_run:
        print("Dry-run mode — no hardware executed.")
        return 0

    if not result["water"]:
        print("SKIP — no watering needed.")
        return 0

    print("Would execute schedule:")
    print(result["schedule"])
    return 0


# -----------------------------
# ENTRYPOINT
# -----------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Sprinkler Engine (rule-based)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        return asyncio.run(_run(args.dry_run))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())