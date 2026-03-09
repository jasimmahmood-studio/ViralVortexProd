"""
ViralVortex — Main Pipeline Orchestrator
"""

import os
import sys
import json
import traceback
from datetime import datetime

print("=" * 50)
print("🌀 ViralVortex Pipeline Starting...")
print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)

os.makedirs("output", exist_ok=True)

# ── Pipeline state ───────────────────────────────────────────
state = {
    "topic":          None,
    "script":         None,
    "audio_path":     None,
    "video_path":     None,
    "thumbnail_path": None,
    "upload_result":  None,
}


def extract_text(result, keys=("script", "text", "content", "body")):
    """Safely extract a string from a dict or return the string itself."""
    if result is None:
        return None
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict):
        for key in keys:
            val = result.get(key)
            if val and isinstance(val, str) and len(val.strip()) > 10:
                return val.strip()
    return None


def extract_topic(result):
    """Safely extract topic string."""
    if result is None:
        return None
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict):
        for key in ("topic", "title", "trend", "query"):
            val = result.get(key)
            if val and isinstance(val, str):
                return val.strip()
        # Try all_topics list
        topics = result.get("all_topics", [])
        if topics and isinstance(topics, list):
            return topics[0]
    if isinstance(result, list) and result:
        return str(result[0])
    return None


def extract_path(result, keys=("audio_path", "video_path", "thumbnail_path", "path", "file")):
    """Safely extract a file path from result."""
    if result is None:
        return None
    if isinstance(result, str) and os.path.exists(result):
        return result
    if isinstance(result, dict):
        for key in keys:
            val = result.get(key)
            if val and isinstance(val, str) and os.path.exists(val):
                return val
    return None


def run_step(number, name, func):
    print(f"\n{'─'*50}")
    print(f"▶️  Step {number}: {name}")
    print(f"{'─'*50}")
    try:
        result = func()
        print(f"✅ Step {number} complete")
        return result
    except Exception as e:
        print(f"❌ Step {number} failed: {e}")
        traceback.print_exc()
        return None


# ════════════════════════════════════════════════════════════
# STEP 1 — Trending Topics
# ════════════════════════════════════════════════════════════
def step1():
    from scripts.step1_trends import fetch_trending_topics
    result = fetch_trending_topics(limit=10)
    topic = extract_topic(result)
    if not topic:
        raise ValueError(f"Could not extract topic from: {type(result)} → {str(result)[:100]}")
    print(f"📌 Topic: {topic}")
    return topic

state["topic"] = run_step(1, "Fetch Trending Topics", step1)
if not state["topic"]:
    state["topic"] = "Top trending topics everyone is talking about right now"
    print(f"⚠️  Using fallback topic")


# ════════════════════════════════════════════════════════════
# STEP 2 — Generate Script
# ════════════════════════════════════════════════════════════
def step2():
    from scripts.step2_script import generate_script
    result = generate_script(state["topic"])
    script = extract_text(result, keys=("script", "text", "content", "body"))
    if not script or len(script) < 50:
        raise ValueError(f"Script too short or missing. Got type={type(result)}, preview={str(result)[:200]}")
    print(f"📝 Script: {len(script)} chars, {len(script.split())} words")
    return script

state["script"] = run_step(2, "Generate Script", step2)
if not state["script"]:
    state["script"] = (
        f"Welcome to ViralVortex! Today we're diving into: {state['topic']}. "
        "This is one of the most talked-about topics right now and you won't believe what's happening. "
        "Stay with us as we break it all down. Don't forget to like and subscribe to ViralVortex "
        "so you never miss a trending story!"
    )
    print("⚠️  Using fallback script")


# ════════════════════════════════════════════════════════════
# STEP 3 — Generate Voice
# ════════════════════════════════════════════════════════════
def step3():
    from scripts.step3_voice import generate_voice
    # Always pass plain string — never the dict
    script_text = state["script"]
    if not isinstance(script_text, str):
        raise ValueError(f"Script is not a string: {type(script_text)}")
    print(f"🎙️  Sending {len(script_text)} chars to voice engine")
    result = generate_voice(script_text)
    path = extract_path(result, keys=("audio_path", "path", "file", "output"))
    if not path:
        raise ValueError(f"No valid audio path in result: {result}")
    print(f"🎙️  Audio saved: {path}")
    return path

state["audio_path"] = run_step(3, "Generate Voice Audio", step3)


# ════════════════════════════════════════════════════════════
# STEP 4 — Create Video
# ════════════════════════════════════════════════════════════
def step4():
    if not state["audio_path"]:
        raise ValueError("No audio file — cannot create video")
    from scripts.step4_video import create_video
    result = create_video(
        topic=state["topic"],
        script=state["script"],
        audio_path=state["audio_path"],
    )
    path = extract_path(result, keys=("video_path", "path", "file", "output"))
    if not path:
        raise ValueError(f"No valid video path in result: {result}")
    size = os.path.getsize(path)
    print(f"🎬 Video saved: {path} ({size:,} bytes)")
    return path

state["video_path"] = run_step(4, "Create Video", step4)


# ════════════════════════════════════════════════════════════
# STEP 5 — Create Thumbnail
# ════════════════════════════════════════════════════════════
def step5():
    from scripts.step5_thumbnail import create_thumbnail
    result = create_thumbnail(state["topic"])
    path = extract_path(result, keys=("thumbnail_path", "path", "file", "output"))
    if not path:
        raise ValueError(f"No valid thumbnail path in result: {result}")
    print(f"🖼️  Thumbnail saved: {path}")
    return path

state["thumbnail_path"] = run_step(5, "Create Thumbnail", step5)


# ════════════════════════════════════════════════════════════
# STEP 6 — Upload to YouTube
# ════════════════════════════════════════════════════════════
def step6():
    if not state["video_path"]:
        raise ValueError("No video file to upload")
    from scripts.step6_upload import upload_video
    result = upload_video(
        video_path=state["video_path"],
        title=state["topic"],
        description=(
            f"Today on ViralVortex: {state['topic']}\n\n"
            "Subscribe for daily trending videos!\n\n"
            "#ViralVortex #Trending #Viral"
        ),
        thumbnail_path=state["thumbnail_path"],
    )
    if not result:
        raise ValueError("Upload returned no result")
    video_id = result.get("video_id") if isinstance(result, dict) else str(result)
    print(f"🚀 Uploaded! https://www.youtube.com/watch?v={video_id}")
    return result

state["upload_result"] = run_step(6, "Upload to YouTube", step6)


# ════════════════════════════════════════════════════════════
# STEP 7 — Send Report
# ════════════════════════════════════════════════════════════
def step7():
    from scripts.step7_report import send_report
    send_report(
        topic=state["topic"],
        upload_result=state["upload_result"],
        state=state,
    )

run_step(7, "Send Report", step7)


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 50)
print("📊 PIPELINE SUMMARY")
print("=" * 50)
print(f"  Topic:     {state['topic']}")
print(f"  Script:    {'✅' if state['script'] else '❌'}")
print(f"  Audio:     {'✅ ' + str(state['audio_path']) if state['audio_path'] else '❌'}")
print(f"  Video:     {'✅ ' + str(state['video_path']) if state['video_path'] else '❌'}")
print(f"  Thumbnail: {'✅ ' + str(state['thumbnail_path']) if state['thumbnail_path'] else '❌'}")
print(f"  Uploaded:  {'✅' if state['upload_result'] else '❌'}")

with open("output/pipeline_state.json", "w") as f:
    json.dump({k: str(v) if v else None for k, v in state.items()}, f, indent=2)

if state["upload_result"]:
    print("\n🎉 Pipeline completed successfully!")
else:
    print("\n⚠️  Pipeline completed with some issues — check logs above")
print("=" * 50)
