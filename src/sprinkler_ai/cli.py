from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import asdict

from .config import Config
from .history import append_entry
from .weather import fetch_weather
from .engine import run_engine   # <-- your new irrigation engine


# -----------------------------
# PRINT ENGINE OUTPUT CLEANLY
# -----------------------------
def _print_engine_output(result: dict) -> None:
    print("\n=== ENGINE OUTPUT ===")
    print(result)

    print("\nDecision:")
    print("WATER" if result["water"] else "SKIP")

    print(f"Reason: {result['reason']}")

    if "schedule" in result:
        print("\nSchedule:")
        print(result["schedule"])


# -----------------------------
# MAIN RUN
# -----------------------------
async def _run(dry_run: bool) -> int:
    config = Config.load()

    print("[1/3] Fetching weather...")
    weather = fetch_weather(
        config.location.latitude,
        config.location.longitude,
        config.location.timezone,
    )

    print("[2/3] Running irrigation engine...\n")

    # 👇 THIS is your entire decision system now
    result = run_engine(weather, config)

    _print_engine_output(result)

    print("\n[3/3] Execution stage")

    if dry_run:
        print("Dry-run mode — no hardware control executed.")

        append_entry({
            "action": "dry_run",
            "engine_result": result,
            "weather": weather.to_prompt_dict(),
        })
        return 0

    if not result["water"]:
        print("SKIP TODAY — no watering needed.")

        append_entry({
            "action": "skip",
            "engine_result": result,
            "weather": weather.to_prompt_dict(),
        })
        return 0

    # -----------------------------
    # FUTURE: hardware integration
    # (LinkTap / timers / Pi GPIO)
    # -----------------------------
    print("Would execute schedule:")
    print(result["schedule"])

    append_entry({
        "action": "watered",
        "engine_result": result,
        "weather": weather.to_prompt_dict(),
    })

    return 0


# -----------------------------
# CLI ENTRYPOINT
# -----------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Weather-based sprinkler engine (manual mode)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        return asyncio.run(_run(args.dry_run))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())