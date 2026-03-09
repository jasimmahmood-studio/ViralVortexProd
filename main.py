#!/usr/bin/env python3
"""
ViralVortex Daily Automation Engine
Runs the full pipeline: Trends → Script → Voice → Video → Upload
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path

# ── Setup logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("viralvortex.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("ViralVortex")

# ── Import pipeline modules ────────────────────────────────────
from scripts.step1_trends   import fetch_trending_topics
from scripts.step2_script   import generate_script
from scripts.step3_voice    import generate_voiceover
from scripts.step4_video    import render_video
from scripts.step5_thumbnail import generate_thumbnail
from scripts.step6_upload   import upload_to_youtube
from scripts.step7_report   import send_report

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def run_pipeline():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log.info(f"🌀 ViralVortex pipeline started — run_id={run_id}")

    results = {"run_id": run_id, "steps": {}}

    try:
        # ── STEP 1: Fetch trends ──────────────────────────────
        log.info("🔥 STEP 1: Fetching trending topics...")
        topics = fetch_trending_topics(limit=10)
        best_topic = topics[0]
        log.info(f"   ✅ Best topic: '{best_topic['title']}' ({best_topic['traffic']})")
        results["steps"]["trends"] = {"status": "ok", "topic": best_topic["title"]}

        # ── STEP 2: Generate script ───────────────────────────
        log.info("🧠 STEP 2: Generating script with Claude AI...")
        script_data = generate_script(best_topic["title"])
        script_path = OUTPUT_DIR / f"{run_id}_script.txt"
        script_path.write_text(script_data["full_script"])
        log.info(f"   ✅ Script saved: {script_path} ({len(script_data['full_script'])} chars)")
        results["steps"]["script"] = {"status": "ok", "path": str(script_path)}

        # ── STEP 3: Voiceover ─────────────────────────────────
        log.info("🎙️  STEP 3: Generating voiceover...")
        audio_path = OUTPUT_DIR / f"{run_id}_voice.mp3"
        generate_voiceover(script_data["narration"], str(audio_path))
        log.info(f"   ✅ Audio saved: {audio_path}")
        results["steps"]["voice"] = {"status": "ok", "path": str(audio_path)}

        # ── STEP 4: Render video ──────────────────────────────
        log.info("🎬 STEP 4: Rendering video with FFmpeg...")
        video_path = OUTPUT_DIR / f"{run_id}_video.mp4"
        render_video(
            audio_path=str(audio_path),
            script=script_data,
            topic=best_topic["title"],
            output_path=str(video_path)
        )
        log.info(f"   ✅ Video saved: {video_path}")
        results["steps"]["video"] = {"status": "ok", "path": str(video_path)}

        # ── STEP 5: Thumbnail ─────────────────────────────────
        log.info("🖼️  STEP 5: Generating thumbnail...")
        thumb_path = OUTPUT_DIR / f"{run_id}_thumb.jpg"
        generate_thumbnail(best_topic["title"], script_data["hook"], str(thumb_path))
        log.info(f"   ✅ Thumbnail: {thumb_path}")
        results["steps"]["thumbnail"] = {"status": "ok", "path": str(thumb_path)}

        # ── STEP 6: Upload to YouTube ─────────────────────────
        log.info("📤 STEP 6: Uploading to YouTube...")
        video_id = upload_to_youtube(
            video_path=str(video_path),
            thumbnail_path=str(thumb_path),
            title=script_data["title"],
            description=script_data["description"],
            tags=script_data["tags"]
        )
        yt_url = f"https://youtube.com/watch?v={video_id}"
        log.info(f"   ✅ Uploaded: {yt_url}")
        results["steps"]["upload"] = {"status": "ok", "video_id": video_id, "url": yt_url}

        # ── STEP 7: Report ────────────────────────────────────
        log.info("📊 STEP 7: Sending report...")
        send_report(results)
        log.info("   ✅ Report sent!")

        log.info(f"🎉 Pipeline complete! Video live at: {yt_url}")

    except Exception as e:
        log.error(f"❌ Pipeline failed at step: {e}", exc_info=True)
        results["error"] = str(e)

    # Save run results
    result_path = OUTPUT_DIR / f"{run_id}_result.json"
    result_path.write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    run_pipeline()
