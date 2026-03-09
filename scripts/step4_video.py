"""
STEP 4: Render Video using FFmpeg + Pexels stock footage
Creates a full video: B-roll clips + captions + music + voiceover
"""

import os
import re
import json
import time
import random
import requests
import subprocess
import textwrap
from pathlib import Path


PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
TEMP_DIR = Path("output/temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def search_pexels_videos(query: str, per_page: int = 5) -> list:
    """Fetch relevant stock video clips from Pexels"""
    if not PEXELS_API_KEY:
        return []

    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": per_page, "orientation": "landscape", "size": "medium"}

    try:
        res = requests.get(url, headers=headers, params=params, timeout=15)
        res.raise_for_status()
        data = res.json()
        clips = []
        for video in data.get("videos", []):
            # Prefer HD files
            files = sorted(video["video_files"], key=lambda x: x.get("width", 0), reverse=True)
            hd = next((f for f in files if f.get("width", 0) >= 1280), files[0] if files else None)
            if hd:
                clips.append({
                    "url": hd["link"],
                    "width": hd.get("width", 1920),
                    "height": hd.get("height", 1080),
                    "duration": video.get("duration", 10)
                })
        return clips
    except Exception as e:
        print(f"   Pexels search failed: {e}")
        return []


def download_clip(url: str, path: str) -> bool:
    """Download a video clip"""
    try:
        res = requests.get(url, stream=True, timeout=60)
        res.raise_for_status()
        with open(path, "wb") as f:
            for chunk in res.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"   Download failed: {e}")
        return False


def create_fallback_background(output_path: str, duration: int, topic: str):
    """Create animated gradient background when no stock footage available"""
    # Dark animated background with text overlay using FFmpeg
    title_safe = topic[:50].replace("'", "").replace('"', "")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x00040f:size=1920x1080:rate=30:duration={duration}",
        "-vf", (
            f"drawtext=text='ViralVortex':fontsize=80:fontcolor=0x00f5ff:"
            f"x=(w-text_w)/2:y=(h-text_h)/2-60:alpha=0.6,"
            f"drawtext=text='{title_safe}':fontsize=40:fontcolor=white:"
            f"x=(w-text_w)/2:y=(h-text_h)/2+60:alpha=0.8"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def get_audio_duration(audio_path: str) -> float:
    """Get duration of audio file in seconds"""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", audio_path],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "audio":
            return float(stream.get("duration", 60))
    return 60.0


def assemble_video(clips: list, audio_path: str, output_path: str, topic: str):
    """Combine clips, add audio, captions and branding with FFmpeg"""

    audio_duration = get_audio_duration(audio_path)
    print(f"   Audio duration: {audio_duration:.1f}s")

    if not clips:
        # No clips — use animated background
        print("   No stock footage, generating background...")
        bg_path = str(TEMP_DIR / "background.mp4")
        create_fallback_background(bg_path, int(audio_duration) + 2, topic)
        clips_to_use = [bg_path]
    else:
        clips_to_use = clips

    # Build concat list — loop clips to fill audio duration
    concat_file = str(TEMP_DIR / "concat.txt")
    total = 0
    concat_entries = []
    while total < audio_duration:
        for clip in clips_to_use:
            concat_entries.append(f"file '{os.path.abspath(clip)}'\n")
            total += 10  # approximate
            if total >= audio_duration + 10:
                break

    with open(concat_file, "w") as f:
        f.writelines(concat_entries)

    # Temp combined video
    combined_path = str(TEMP_DIR / "combined.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-t", str(audio_duration + 1),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-r", "30",
        "-an", combined_path
    ], check=True, capture_output=True)

    # Add branding overlay + audio
    title_safe = topic[:45].replace("'", "").replace('"', "").replace(":", "")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", combined_path,
        "-i", audio_path,
        "-vf", (
            # Dark overlay at bottom
            "drawbox=x=0:y=ih-120:w=iw:h=120:color=black@0.7:t=fill,"
            # Channel name top-left
            "drawtext=text='🌀 ViralVortex':fontsize=36:fontcolor=0x00f5ff:"
            "x=30:y=30:alpha=0.9,"
            # Topic title at bottom
            f"drawtext=text='{title_safe}':fontsize=38:fontcolor=white:"
            "x=30:y=ih-80:alpha=0.95,"
            # Subscribe reminder
            "drawtext=text='🔔 Subscribe for Daily Trends':fontsize=28:fontcolor=0xffaa00:"
            "x=30:y=ih-38:alpha=0.85"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path
    ], check=True, capture_output=True)

    print(f"   ✅ Video rendered: {output_path}")


def render_video(audio_path: str, script: dict, topic: str, output_path: str):
    """Main entry: fetch footage, download, assemble"""

    print(f"   Searching Pexels for: '{topic}'...")
    raw_clips = search_pexels_videos(topic, per_page=6)

    # Also search generic "viral trending" for filler
    filler_clips = search_pexels_videos("news viral trending", per_page=3)
    all_clips_info = raw_clips + filler_clips

    # Download clips
    local_clips = []
    for i, clip_info in enumerate(all_clips_info[:6]):
        clip_path = str(TEMP_DIR / f"clip_{i}.mp4")
        print(f"   Downloading clip {i+1}/{min(len(all_clips_info), 6)}...")
        if download_clip(clip_info["url"], clip_path):
            local_clips.append(clip_path)
        time.sleep(0.5)  # be nice to Pexels

    assemble_video(local_clips, audio_path, output_path, topic)
