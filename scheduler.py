"""
ViralVortex Scheduler
Runs pipeline immediately on start, then daily at UPLOAD_TIME
"""

import os
import time
import subprocess
import sys
from datetime import datetime, timedelta

UPLOAD_TIME  = os.environ.get("UPLOAD_TIME", "07:30")
RUN_ON_START = os.environ.get("RUN_ON_START", "true").lower() == "true"  # DEFAULT TRUE


def get_next_run(time_str):
    now = datetime.now()
    h, m = map(int, time_str.split(":"))
    run_today = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if run_today <= now:
        run_today += timedelta(days=1)
    return run_today


def run_pipeline():
    print("\n" + "=" * 55)
    print(f"🚀 Running pipeline at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    try:
        result = subprocess.run(
            [sys.executable, "main.py"],
            timeout=3600
        )
        if result.returncode == 0:
            print("✅ Pipeline completed successfully")
        else:
            print(f"⚠️  Pipeline exited with code {result.returncode}")
    except subprocess.TimeoutExpired:
        print("❌ Pipeline timed out after 1 hour")
    except Exception as e:
        print(f"❌ Pipeline error: {e}")


def main():
    print("=" * 55)
    print("🌀 ViralVortex Scheduler Started")
    print(f"⏰ Daily upload time : {UPLOAD_TIME}")
    print(f"▶️  RUN_ON_START      : {RUN_ON_START}")
    print(f"🐍 Python            : {sys.executable}")
    print("=" * 55)

    # ── Run immediately ──────────────────────────────────────
    if RUN_ON_START:
        print("\n▶️  Starting pipeline now (RUN_ON_START=true)...")
        run_pipeline()
    else:
        print("\n⏸️  RUN_ON_START=false — waiting for scheduled time")

    # ── Daily loop ───────────────────────────────────────────
    while True:
        next_run = get_next_run(UPLOAD_TIME)
        wait_seconds = (next_run - datetime.now()).total_seconds()
        print(f"\n⏳ Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')} "
              f"(in {wait_seconds/3600:.1f} hours)")

        while True:
            remaining = (get_next_run(UPLOAD_TIME) - datetime.now()).total_seconds()
            if remaining <= 0:
                break
            if int(remaining) % 3600 < 60:
                print(f"💓 {datetime.now().strftime('%H:%M')} — "
                      f"{remaining/3600:.1f}h until next run")
            time.sleep(min(60, remaining))

        run_pipeline()


if __name__ == "__main__":
    main()
