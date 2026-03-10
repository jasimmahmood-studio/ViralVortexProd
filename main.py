"""
ViralVortex — Main Pipeline Orchestrator
Uploads 10 videos per run, each with unique trending topic
"""

import os
import sys
import json
import traceback
from datetime import datetime

print("=" * 55)
print("🌀 ViralVortex Pipeline Starting...")
print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📁 CWD: {os.getcwd()}")
print("=" * 55)

os.makedirs("output", exist_ok=True)

VIDEOS_PER_RUN = int(os.environ.get("VIDEOS_PER_RUN", "10"))
print(f"🎬 Videos to produce: {VIDEOS_PER_RUN}")


def extract_text(result, keys=("script", "text", "content", "body")):
    if result is None: return None
    if isinstance(result, str) and len(result.strip()) > 10:
        return result.strip()
    if isinstance(result, dict):
        for key in keys:
            val = result.get(key)
            if val and isinstance(val, str) and len(val.strip()) > 10:
                return val.strip()
    return None


def extract_topic(result):
    if result is None: return None
    if isinstance(result, str) and result.strip(): return result.strip()
    if isinstance(result, dict):
        for key in ("topic", "title", "trend", "query"):
            val = result.get(key)
            if val and isinstance(val, str): return val.strip()
        topics = result.get("all_topics", [])
        if topics and isinstance(topics, list): return str(topics[0])
    if isinstance(result, list) and result: return str(result[0])
    return None


def extract_all_topics(result):
    """Extract full list of trending topics."""
    if isinstance(result, dict):
        topics = result.get("all_topics", [])
        if topics and isinstance(topics, list):
            return [str(t) for t in topics if t]
    return []


def extract_path(result, keys=("audio_path","video_path","thumbnail_path","path","file")):
    if result is None: return None
    if isinstance(result, str) and os.path.exists(result): return result
    if isinstance(result, dict):
        for key in keys:
            val = result.get(key)
            if val and isinstance(val, str) and os.path.exists(val): return val
    return None


def run_step(number, name, func):
    print(f"\n{'─'*55}")
    print(f"▶️  Step {number}: {name}")
    print(f"{'─'*55}")
    try:
        result = func()
        print(f"✅ Step {number} complete: {name}")
        return result
    except Exception as e:
        print(f"\n{'!'*55}")
        print(f"❌ Step {number} FAILED: {name}")
        print(f"   Error type : {type(e).__name__}")
        print(f"   Error msg  : {e}")
        traceback.print_exc()
        print(f"{'!'*55}")
        return None


# ════════════════════════════════════════════════════════════
# STEP 1 — Fetch ALL trending topics at once
# ════════════════════════════════════════════════════════════
print(f"\n{'═'*55}")
print("▶️  STEP 1: Fetch Trending Topics")
print(f"{'═'*55}")

try:
    from scripts.step1_trends import fetch_trending_topics
    trends_result = fetch_trending_topics(limit=VIDEOS_PER_RUN + 5)
    all_topics = extract_all_topics(trends_result)

    if not all_topics:
        # fallback
        topic = extract_topic(trends_result)
        all_topics = [topic] if topic else []

    print(f"✅ Got {len(all_topics)} topics")
    for i, t in enumerate(all_topics):
        print(f"   {i+1}. {t}")

except Exception as e:
    print(f"❌ Step 1 failed: {e}")
    traceback.print_exc()
    all_topics = []

# Ensure we have enough topics
fallback_topics = [
    "AI tools taking over the internet in 2025",
    "The most viral trend nobody is talking about",
    "Top 10 shocking news stories this week",
    "Why everyone is obsessed with this right now",
    "Secret tricks that will blow your mind today",
    "The biggest viral moment on the internet this week",
    "Why this video is breaking the internet right now",
    "Unbelievable things happening in the world today",
    "The truth behind the latest social media trend",
    "What everyone is searching for on Google right now",
    "Most shocking celebrity news this week",
    "Why millions are watching this viral video",
]

while len(all_topics) < VIDEOS_PER_RUN:
    for ft in fallback_topics:
        if ft not in all_topics:
            all_topics.append(ft)
        if len(all_topics) >= VIDEOS_PER_RUN:
            break

# Use only what we need, ensure all unique
seen_topics = set()
unique_topics = []
for t in all_topics:
    if t.lower() not in seen_topics:
        seen_topics.add(t.lower())
        unique_topics.append(t)

topics_to_use = unique_topics[:VIDEOS_PER_RUN]
print(f"\n🎯 Will produce {len(topics_to_use)} videos")


# ════════════════════════════════════════════════════════════
# LOOP — Produce one video per topic
# ════════════════════════════════════════════════════════════
results_summary = []

for video_num, topic in enumerate(topics_to_use, 1):
    print(f"\n{'█'*55}")
    print(f"🎬 VIDEO {video_num}/{len(topics_to_use)}: {topic}")
    print(f"{'█'*55}")

    # Use unique output paths per video
    prefix = f"output/v{video_num:02d}"
    os.makedirs("output", exist_ok=True)

    state = {
        "topic":          topic,
        "script":         None,
        "audio_path":     None,
        "video_path":     None,
        "thumbnail_path": None,
        "upload_result":  None,
        "video_num":      video_num,
    }

    # ── Step 2: Script ───────────────────────────────────────
    def step2():
        from scripts.step2_script import generate_script
        result = generate_script(topic)
        script = extract_text(result, keys=("script","text","content","body"))
        if not script or len(script) < 50:
            raise ValueError(f"Script too short: {len(script) if script else 0} chars")
        print(f"📝 Script: {len(script)} chars")
        # Return full dict so we can pass sections to step4
        if isinstance(result, dict):
            result["script"] = script
            return result
        return {"script": script, "sections": [], "title": topic}

    step2_result = run_step(2, f"Generate Script [{video_num}]", step2)
    if isinstance(step2_result, dict):
        state["script"]      = step2_result.get("script", "")
        state["script_data"] = step2_result
        state["title"]       = step2_result.get("title", topic)
    else:
        state["script"] = step2_result or ""
        state["script_data"] = None
        state["title"] = topic

    if not state["script"] or len(state["script"]) < 50:
        state["script"] = (
            f"Welcome to ViralVortex! Today we are covering: {topic}. "
            "This is one of the hottest topics right now. "
            "Stay tuned as we break it all down. "
            "Like and subscribe to ViralVortex for daily trending content!"
        )

    # ── Step 3: Voice ────────────────────────────────────────
    def step3():
        from scripts.step3_voice import generate_voice
        audio_out = f"{prefix}_audio.mp3"
        result = generate_voice(state["script"], output_path=audio_out)
        # Also try without output_path if it fails
        if not result:
            result = generate_voice(state["script"])
        path = extract_path(result, keys=("audio_path","path","file","output"))
        if not path:
            raise ValueError(f"No audio path returned: {result}")
        # Move to unique path if needed
        if path != audio_out and os.path.exists(path):
            import shutil
            shutil.copy(path, audio_out)
            path = audio_out
        return path

    state["audio_path"] = run_step(3, f"Generate Voice [{video_num}]", step3)

    if not state["audio_path"]:
        print(f"⚠️  Skipping video {video_num} — no audio")
        results_summary.append({"video_num": video_num, "topic": topic, "status": "failed_audio"})
        continue

    # ── Step 4: Video ────────────────────────────────────────
    def step4():
        from scripts.step4_video import create_video
        video_out = f"{prefix}_video.mp4"
        result = create_video(
            topic=topic,
            script=state["script"],
            script_data=state.get("script_data"),
            audio_path=state["audio_path"],
            output_path=video_out,
        )
        path = extract_path(result, keys=("video_path","path","file","output"))
        if not path:
            raise ValueError(f"No video path returned: {result}")
        if path != video_out and os.path.exists(path):
            import shutil
            shutil.copy(path, video_out)
            path = video_out
        return path

    state["video_path"] = run_step(4, f"Create Video [{video_num}]", step4)

    if not state["video_path"]:
        print(f"⚠️  Skipping video {video_num} — no video")
        results_summary.append({"video_num": video_num, "topic": topic, "status": "failed_video"})
        continue

    # ── Step 5: Thumbnail ────────────────────────────────────
    def step5():
        from scripts.step5_thumbnail import create_thumbnail
        thumb_out = f"{prefix}_thumb.jpg"
        result = create_thumbnail(topic, output_path=thumb_out)
        path = extract_path(result, keys=("thumbnail_path","path","file","output"))
        if not path:
            raise ValueError(f"No thumbnail path: {result}")
        if path != thumb_out and os.path.exists(path):
            import shutil
            shutil.copy(path, thumb_out)
            path = thumb_out
        return path

    state["thumbnail_path"] = run_step(5, f"Create Thumbnail [{video_num}]", step5)

    # ── Step 6: Upload ───────────────────────────────────────
    def step6():
        from scripts.step6_upload import upload_video
        result = upload_video(
            video_path=state["video_path"],
            title=state.get("title", topic)[:100],
            description=(
                f"Today on ViralVortex: {topic}\n\n"
                "Subscribe for daily trending videos!\n\n"
                "#ViralVortex #Trending #Viral"
            ),
            thumbnail_path=state["thumbnail_path"],
        )
        if not result:
            raise ValueError("Upload returned no result")
        video_id = result.get("video_id") if isinstance(result, dict) else str(result)
        print(f"🚀 https://www.youtube.com/watch?v={video_id}")
        return result

    state["upload_result"] = run_step(6, f"Upload to YouTube [{video_num}]", step6)

    # ── Summary for this video ───────────────────────────────
    status = "success" if state["upload_result"] else "uploaded_failed"
    video_id = None
    if isinstance(state["upload_result"], dict):
        video_id = state["upload_result"].get("video_id")

    results_summary.append({
        "video_num":  video_num,
        "topic":      topic,
        "status":     status,
        "video_id":   video_id,
        "url":        f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
    })

    print(f"\n✅ Video {video_num} done: {status}")


# ════════════════════════════════════════════════════════════
# STEP 7 — Final Report
# ════════════════════════════════════════════════════════════
def step7():
    from scripts.step7_report import send_report
    successful = [r for r in results_summary if r["status"] == "success"]
    send_report(
        topic=f"{len(successful)}/{len(topics_to_use)} videos uploaded",
        upload_result={"videos": results_summary},
        state={"results": results_summary},
    )

run_step(7, "Send Report", step7)


# ════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("📊 FINAL PIPELINE SUMMARY")
print("=" * 55)
successful = [r for r in results_summary if r["status"] == "success"]
failed     = [r for r in results_summary if r["status"] != "success"]

print(f"  ✅ Successful uploads : {len(successful)}/{len(topics_to_use)}")
print(f"  ❌ Failed             : {len(failed)}")
print()
for r in results_summary:
    icon = "✅" if r["status"] == "success" else "❌"
    print(f"  {icon} [{r['video_num']:02d}] {r['topic'][:50]}")
    if r.get("url"):
        print(f"        {r['url']}")

with open("output/pipeline_summary.json", "w") as f:
    json.dump(results_summary, f, indent=2)

print(f"\n🎉 Pipeline complete! {len(successful)} videos uploaded.")
print("=" * 55)
