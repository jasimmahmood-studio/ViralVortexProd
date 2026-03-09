"""
ViralVortex — Main Pipeline Orchestrator
Full error logging on every step
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
print(f"🐍 Python: {sys.version.split()[0]}")
print("=" * 55)

os.makedirs("output", exist_ok=True)

state = {
    "topic":          None,
    "script":         None,
    "audio_path":     None,
    "video_path":     None,
    "thumbnail_path": None,
    "upload_result":  None,
}


def extract_text(result, keys=("script", "text", "content", "body")):
    if result is None:
        return None
    if isinstance(result, str) and len(result.strip()) > 10:
        return result.strip()
    if isinstance(result, dict):
        for key in keys:
            val = result.get(key)
            if val and isinstance(val, str) and len(val.strip()) > 10:
                return val.strip()
    return None


def extract_topic(result):
    if result is None:
        return None
    if isinstance(result, str) and result.strip():
        return result.strip()
    if isinstance(result, dict):
        for key in ("topic", "title", "trend", "query"):
            val = result.get(key)
            if val and isinstance(val, str):
                return val.strip()
        topics = result.get("all_topics", [])
        if topics and isinstance(topics, list):
            return str(topics[0])
    if isinstance(result, list) and result:
        return str(result[0])
    return None


def extract_path(result, keys=("audio_path", "video_path", "thumbnail_path", "path", "file")):
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
    print(f"\n{'─' * 55}")
    print(f"▶️  STEP {number}: {name}")
    print(f"{'─' * 55}")
    try:
        result = func()
        print(f"✅ STEP {number} COMPLETE: {name}")
        return result
    except Exception as e:
        print(f"\n{'!' * 55}")
        print(f"❌ STEP {number} FAILED: {name}")
        print(f"   Error type : {type(e).__name__}")
        print(f"   Error msg  : {str(e)}")
        print(f"   Full trace :")
        traceback.print_exc()
        print(f"{'!' * 55}")
        return None


# ════════════════════════════════════════════════════════════
# STEP 1 — Trending Topics
# ════════════════════════════════════════════════════════════
def step1():
    print("📦 Importing step1_trends...")
    from scripts.step1_trends import fetch_trending_topics
    print("✅ Import OK")
    result = fetch_trending_topics(limit=10)
    print(f"📦 Raw result type: {type(result)}")
    print(f"📦 Raw result preview: {str(result)[:200]}")
    topic = extract_topic(result)
    if not topic:
        raise ValueError(f"Could not extract topic. Got: {type(result)} = {str(result)[:200]}")
    print(f"📌 Topic: {topic}")
    return topic

state["topic"] = run_step(1, "Fetch Trending Topics", step1)
if not state["topic"]:
    state["topic"] = "Top trending topics everyone is talking about right now"
    print(f"⚠️  Using fallback topic: {state['topic']}")


# ════════════════════════════════════════════════════════════
# STEP 2 — Generate Script
# ════════════════════════════════════════════════════════════
def step2():
    print("📦 Importing step2_script...")
    from scripts.step2_script import generate_script
    print("✅ Import OK")
    result = generate_script(state["topic"])
    print(f"📦 Raw result type: {type(result)}")
    print(f"📦 Raw result preview: {str(result)[:200]}")
    script = extract_text(result, keys=("script", "text", "content", "body"))
    if not script or len(script) < 50:
        raise ValueError(
            f"Script too short or missing.\n"
            f"  Result type: {type(result)}\n"
            f"  Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}\n"
            f"  Preview: {str(result)[:300]}"
        )
    print(f"📝 Script OK: {len(script)} chars, {len(script.split())} words")
    return script

state["script"] = run_step(2, "Generate Script", step2)
if not state["script"]:
    state["script"] = (
        f"Welcome to ViralVortex! Today we are covering: {state['topic']}. "
        "This is one of the most talked about topics right now and you won't believe what is happening. "
        "Stay with us as we break it all down. Don't forget to like and subscribe to ViralVortex "
        "so you never miss a trending story. Hit that notification bell right now!"
    )
    print(f"⚠️  Using fallback script ({len(state['script'])} chars)")


# ════════════════════════════════════════════════════════════
# STEP 3 — Generate Voice
# ════════════════════════════════════════════════════════════
def step3():
    print("📦 Importing step3_voice...")
    from scripts.step3_voice import generate_voice
    print("✅ Import OK")
    script_text = state["script"]
    if not isinstance(script_text, str) or len(script_text) < 10:
        raise ValueError(f"Script is not valid string: type={type(script_text)}, len={len(str(script_text))}")
    print(f"🎙️  Sending {len(script_text)} chars to voice engine")
    result = generate_voice(script_text)
    print(f"📦 Raw result type: {type(result)}")
    print(f"📦 Raw result preview: {str(result)[:200]}")
    path = extract_path(result, keys=("audio_path", "path", "file", "output"))
    if not path:
        raise ValueError(f"No valid audio path in result: {result}")
    print(f"🎙️  Audio: {path} ({os.path.getsize(path):,} bytes)")
    return path

state["audio_path"] = run_step(3, "Generate Voice Audio", step3)


# ════════════════════════════════════════════════════════════
# STEP 4 — Create Video
# ════════════════════════════════════════════════════════════
def step4():
    if not state["audio_path"]:
        raise ValueError("No audio_path in state — Step 3 must have failed")
    print("📦 Importing step4_video...")
    from scripts.step4_video import create_video
    print("✅ Import OK")
    result = create_video(
        topic=state["topic"],
        script=state["script"],
        audio_path=state["audio_path"],
    )
    print(f"📦 Raw result type: {type(result)}")
    print(f"📦 Raw result preview: {str(result)[:200]}")
    path = extract_path(result, keys=("video_path", "path", "file", "output"))
    if not path:
        raise ValueError(f"No valid video path in result: {result}")
    print(f"🎬 Video: {path} ({os.path.getsize(path):,} bytes)")
    return path

state["video_path"] = run_step(4, "Create Video", step4)


# ════════════════════════════════════════════════════════════
# STEP 5 — Create Thumbnail
# ════════════════════════════════════════════════════════════
def step5():
    print("📦 Importing step5_thumbnail...")
    from scripts.step5_thumbnail import create_thumbnail
    print("✅ Import OK")
    result = create_thumbnail(state["topic"])
    print(f"📦 Raw result type: {type(result)}")
    print(f"📦 Raw result preview: {str(result)[:200]}")
    path = extract_path(result, keys=("thumbnail_path", "path", "file", "output"))
    if not path:
        raise ValueError(f"No valid thumbnail path in result: {result}")
    print(f"🖼️  Thumbnail: {path}")
    return path

state["thumbnail_path"] = run_step(5, "Create Thumbnail", step5)


# ════════════════════════════════════════════════════════════
# STEP 6 — Upload to YouTube
# ════════════════════════════════════════════════════════════
def step6():
    if not state["video_path"]:
        raise ValueError("No video_path in state — Step 4 must have failed")
    print("📦 Importing step6_upload...")
    from scripts.step6_upload import upload_video
    print("✅ Import OK")
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
    print("📦 Importing step7_report...")
    from scripts.step7_report import send_report
    print("✅ Import OK")
    send_report(
        topic=state["topic"],
        upload_result=state["upload_result"],
        state=state,
    )

run_step(7, "Send Report", step7)


# ════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("📊 PIPELINE SUMMARY")
print("=" * 55)
print(f"  Topic      : {state['topic']}")
print(f"  Script     : {'✅' if state['script'] else '❌'}")
print(f"  Audio      : {'✅  ' + str(state['audio_path']) if state['audio_path'] else '❌ failed'}")
print(f"  Video      : {'✅  ' + str(state['video_path']) if state['video_path'] else '❌ failed'}")
print(f"  Thumbnail  : {'✅  ' + str(state['thumbnail_path']) if state['thumbnail_path'] else '❌ failed'}")
print(f"  Uploaded   : {'✅' if state['upload_result'] else '❌ failed'}")

with open("output/pipeline_state.json", "w") as f:
    json.dump({k: str(v) if v else None for k, v in state.items()}, f, indent=2)

if state["upload_result"]:
    print("\n🎉 Pipeline completed successfully!")
elif state["video_path"]:
    print("\n⚠️  Video created but upload failed — check YouTube credentials")
else:
    print("\n⚠️  Pipeline incomplete — check errors above")
print("=" * 55)
