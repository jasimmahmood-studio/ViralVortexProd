"""
ViralVortex — Main Pipeline Orchestrator
Runs all 7 steps with full error handling and detailed logging
"""

import os
import sys
import json
import traceback
from datetime import datetime

print("=" * 50)
print("🌀 ViralVortex Pipeline Starting...")
print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)

# ── Verify working directory ─────────────────────────────────
print(f"\n📁 Working directory: {os.getcwd()}")
print(f"📂 Files present: {os.listdir('.')}")

# ── Create output folder ─────────────────────────────────────
os.makedirs("output", exist_ok=True)

# ── Pipeline state ───────────────────────────────────────────
state = {
    "topic": None,
    "script": None,
    "audio_path": None,
    "video_path": None,
    "thumbnail_path": None,
    "upload_result": None,
}


def run_step(step_number, step_name, func, *args, **kwargs):
    """Run a pipeline step with full error handling."""
    print(f"\n{'─'*50}")
    print(f"▶️  Step {step_number}: {step_name}")
    print(f"{'─'*50}")
    try:
        result = func(*args, **kwargs)
        print(f"✅ Step {step_number} complete: {step_name}")
        return result
    except ImportError as e:
        print(f"❌ Step {step_number} ImportError: {e}")
        print(f"   → Check that all dependencies are installed")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"❌ Step {step_number} failed: {e}")
        traceback.print_exc()
        return None


# ════════════════════════════════════════════════════════════
# STEP 1: Fetch Trending Topics
# ════════════════════════════════════════════════════════════
def step1():
    from scripts.step1_trends import fetch_trending_topics
    result = fetch_trending_topics(limit=10)
    if not result:
        raise ValueError("No trending topics returned")
    topic = result.get("topic") if isinstance(result, dict) else (
        result[0] if isinstance(result, list) and result else None
    )
    if not topic:
        raise ValueError("Could not extract topic from result")
    print(f"📌 Topic: {topic}")
    return topic

state["topic"] = run_step(1, "Fetch Trending Topics", step1)
if not state["topic"]:
    state["topic"] = "Top trending topics this week"
    print(f"⚠️  Using fallback topic: {state['topic']}")


# ════════════════════════════════════════════════════════════
# STEP 2: Generate Script
# ════════════════════════════════════════════════════════════
def step2():
    from scripts.step2_script import generate_script
    result = generate_script(state["topic"])
    if not result:
        raise ValueError("No script generated")
    script = result.get("script") if isinstance(result, dict) else str(result)
    if not script or len(script) < 50:
        raise ValueError(f"Script too short: {len(script) if script else 0} chars")
    print(f"📝 Script length: {len(script)} characters")
    return script

state["script"] = run_step(2, "Generate Script", step2)
if not state["script"]:
    state["script"] = f"Welcome to ViralVortex! Today we're covering: {state['topic']}. Stay tuned for the latest trending content."
    print(f"⚠️  Using fallback script")


# ════════════════════════════════════════════════════════════
# STEP 3: Generate Voice/Audio
# ════════════════════════════════════════════════════════════
def step3():
    from scripts.step3_voice import generate_voice
    result = generate_voice(state["script"])
    if not result:
        raise ValueError("No audio generated")
    audio_path = result.get("audio_path") if isinstance(result, dict) else str(result)
    if not audio_path or not os.path.exists(audio_path):
        raise ValueError(f"Audio file not found at: {audio_path}")
    size = os.path.getsize(audio_path)
    print(f"🎙️  Audio: {audio_path} ({size} bytes)")
    return audio_path

state["audio_path"] = run_step(3, "Generate Voice Audio", step3)
if not state["audio_path"]:
    print("⚠️  Audio generation failed — pipeline cannot continue without audio")
    print("   Check ELEVENLABS_API_KEY or gTTS installation")


# ════════════════════════════════════════════════════════════
# STEP 4: Create Video
# ════════════════════════════════════════════════════════════
def step4():
    if not state["audio_path"]:
        raise ValueError("No audio path — skipping video creation")
    from scripts.step4_video import create_video
    result = create_video(
        topic=state["topic"],
        script=state["script"],
        audio_path=state["audio_path"]
    )
    if not result:
        raise ValueError("No video generated")
    video_path = result.get("video_path") if isinstance(result, dict) else str(result)
    if not video_path or not os.path.exists(video_path):
        raise ValueError(f"Video file not found at: {video_path}")
    size = os.path.getsize(video_path)
    print(f"🎬 Video: {video_path} ({size} bytes)")
    return video_path

state["video_path"] = run_step(4, "Create Video", step4)


# ════════════════════════════════════════════════════════════
# STEP 5: Create Thumbnail
# ════════════════════════════════════════════════════════════
def step5():
    from scripts.step5_thumbnail import create_thumbnail
    result = create_thumbnail(state["topic"])
    if not result:
        raise ValueError("No thumbnail generated")
    thumb_path = result.get("thumbnail_path") if isinstance(result, dict) else str(result)
    if not thumb_path or not os.path.exists(thumb_path):
        raise ValueError(f"Thumbnail not found at: {thumb_path}")
    print(f"🖼️  Thumbnail: {thumb_path}")
    return thumb_path

state["thumbnail_path"] = run_step(5, "Create Thumbnail", step5)


# ════════════════════════════════════════════════════════════
# STEP 6: Upload to YouTube
# ════════════════════════════════════════════════════════════
def step6():
    if not state["video_path"]:
        raise ValueError("No video to upload")
    from scripts.step6_upload import upload_video
    result = upload_video(
        video_path=state["video_path"],
        title=state["topic"],
        description=f"Today on ViralVortex: {state['topic']}\n\n#ViralVortex #Trending #Viral",
        thumbnail_path=state["thumbnail_path"],
    )
    if not result:
        raise ValueError("Upload returned no result")
    video_id = result.get("video_id") if isinstance(result, dict) else str(result)
    print(f"🚀 Uploaded! Video ID: {video_id}")
    print(f"🔗 URL: https://www.youtube.com/watch?v={video_id}")
    return result

state["upload_result"] = run_step(6, "Upload to YouTube", step6)


# ════════════════════════════════════════════════════════════
# STEP 7: Send Report
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
print(f"📌 Topic:     {state['topic']}")
print(f"📝 Script:    {'✅' if state['script'] else '❌'}")
print(f"🎙️  Audio:     {'✅ ' + state['audio_path'] if state['audio_path'] else '❌'}")
print(f"🎬 Video:     {'✅ ' + state['video_path'] if state['video_path'] else '❌'}")
print(f"🖼️  Thumbnail: {'✅ ' + state['thumbnail_path'] if state['thumbnail_path'] else '❌'}")
print(f"🚀 Uploaded:  {'✅' if state['upload_result'] else '❌'}")

# Save state to output
with open("output/pipeline_state.json", "w") as f:
    json.dump({k: str(v) if v else None for k, v in state.items()}, f, indent=2)

if state["upload_result"]:
    print("\n🎉 Pipeline completed successfully!")
else:
    print("\n⚠️  Pipeline completed with some failures — check logs above")

print("=" * 50)
