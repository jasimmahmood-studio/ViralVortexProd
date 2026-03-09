#!/usr/bin/env python3
"""
ViralVortex Scheduler
Runs the pipeline daily at the configured time.
Usage:
  python scheduler.py            # runs forever (for VPS)
  python scheduler.py --now      # run pipeline immediately (for testing)
"""

import sys
import schedule
import time
import os
from dotenv import load_dotenv

load_dotenv()

from main import run_pipeline

UPLOAD_TIME = os.environ.get("UPLOAD_TIME", "07:30")


def job():
    print(f"\n{'='*50}")
    print(f"⏰ Scheduled run triggered at {UPLOAD_TIME}")
    print(f"{'='*50}\n")
    run_pipeline()


if __name__ == "__main__":
    if "--now" in sys.argv:
        print("▶ Running pipeline immediately...")
        run_pipeline()
    else:
        print(f"🌀 ViralVortex Scheduler started")
        print(f"📅 Pipeline will run daily at {UPLOAD_TIME}")
        print(f"   Press Ctrl+C to stop\n")

        schedule.every().day.at(UPLOAD_TIME).do(job)

        while True:
            schedule.run_pending()
            time.sleep(30)
