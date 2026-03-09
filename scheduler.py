"""
ViralVortex Scheduler
Runs main.py once daily at UPLOAD_TIME (default 07:30)
No external 'schedule' module needed — uses simple sleep loop
"""

import os
import time
import subprocess
import sys
from datetime import datetime, timedelta

UPLOAD_TIME = os.environ.get("UPLOAD_TIME", "07:30")


def get_next_run(time_str):
    """Get next datetime for the given HH:MM time string."""
    now = datetime.now()
    h, m = map(int, time_str.split(":"))
    run_today = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if run_today <= now:
        run_today += timedelta(days=1)
    return run_today


def run_pipeline():
    """Run main.py using the same Python interpreter."""
    print("\n" + "=" * 55)
    print(f"🚀 Running pipeline at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    try:
        result = subprocess.run(
            [sys.executable, "main.py"],
            timeout=3600  # 1 hour max
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
    print(f"⏰ Daily upload time: {UPLOAD_TIME}")
    print(f"🐍 Python: {sys.executable}")
    print("=" * 55)

    # Run immediately on first start (optional)
    run_now = os.environ.get("RUN_ON_START", "false").lower() == "true"
    if run_now:
        print("▶️  RUN_ON_START=true — running pipeline now...")
        run_pipeline()

    # Main loop
    while True:
        next_run = get_next_run(UPLOAD_TIME)
        wait_seconds = (next_run - datetime.now()).total_seconds()
        print(f"\n⏳ Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')} "
              f"(in {wait_seconds/3600:.1f} hours)")

        # Sleep in chunks so we can log heartbeat
        while True:
            remaining = (get_next_run(UPLOAD_TIME) - datetime.now()).total_seconds()
            if remaining <= 0:
                break
            # Log heartbeat every hour
            if int(remaining) % 3600 < 60:
                print(f"💓 Heartbeat — {remaining/3600:.1f}h until next run "
                      f"[{datetime.now().strftime('%H:%M')}]")
            time.sleep(min(60, remaining))

        run_pipeline()


if __name__ == "__main__":
    main()
