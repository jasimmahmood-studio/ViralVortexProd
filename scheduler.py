"""
ViralVortex Scheduler
Always uses venv Python to run pipeline
"""

import os
import time
import subprocess
import sys
from datetime import datetime, timedelta

UPLOAD_TIME  = os.environ.get("UPLOAD_TIME", "07:30")
RUN_ON_START = os.environ.get("RUN_ON_START", "true").lower() == "true"

# ── Always use venv Python if available ─────────────────────
VENV_PYTHON = "/app/venv/bin/python"
PYTHON      = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

print(f"🐍 Scheduler Python : {sys.executable}")
print(f"🐍 Pipeline Python  : {PYTHON}")


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
    print(f"🐍 Using Python: {PYTHON}")
    print("=" * 55)
    try:
        result = subprocess.run(
            [PYTHON, "main.py"],
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
    print(f"🐍 Scheduler Python  : {sys.executable}")
    print(f"🐍 Pipeline Python   : {PYTHON}")
    print("=" * 55)

    # Verify venv exists and has packages
    if not os.path.exists(VENV_PYTHON):
        print(f"❌ Venv not found at {VENV_PYTHON}")
        print("   Check nixpacks.toml install phase")
    else:
        print(f"✅ Venv found at {VENV_PYTHON}")
        # Quick package check
        try:
            check = subprocess.run(
                [PYTHON, "-c", "import anthropic, gtts, requests; print('✅ Core packages OK')"],
                capture_output=True, text=True, timeout=10
            )
            print(check.stdout.strip() or check.stderr.strip())
        except Exception as e:
            print(f"⚠️  Package check failed: {e}")

    if RUN_ON_START:
        print("\n▶️  Starting pipeline now...")
        run_pipeline()
    else:
        print("\n⏸️  Waiting for scheduled time...")

    while True:
        next_run = get_next_run(UPLOAD_TIME)
        wait_secs = (next_run - datetime.now()).total_seconds()
        print(f"\n⏳ Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')} "
              f"(in {wait_secs/3600:.1f}h)")

        while True:
            remaining = (get_next_run(UPLOAD_TIME) - datetime.now()).total_seconds()
            if remaining <= 0:
                break
            if int(remaining) % 3600 < 60:
                print(f"💓 {datetime.now().strftime('%H:%M')} — {remaining/3600:.1f}h remaining")
            time.sleep(min(60, remaining))

        run_pipeline()


if __name__ == "__main__":
    main()
