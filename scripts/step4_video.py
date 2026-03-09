"""
Step 4: Create Video
- Downloads stock footage from Pexels (if API key set)
- Falls back to animated gradient background (no API key needed)
- Combines with audio using FFmpeg
- Adds ViralVortex branding overlay
"""

import os
import json
import subprocess
import requests
from datetime import datetime


PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "").strip()


def create_video(topic, script, audio_path, **kwargs):
    """Main function — create video from topic + audio."""
    print(f"\n🎬 Creating video for: {topic}")

    os.makedirs("output", exist_ok=True)
    video_path = "output/video.mp4"

    # Get audio duration
    duration = _get_audio_duration(audio_path)
    print(f"⏱️  Audio duration: {duration:.1f}s")

    # Try Pexels footage first
    background_path = None
    if PEXELS_API_KEY:
        background_path = _fetch_pexels_video(topic, duration)

    # Fall back to generated background
    if not background_path or not os.path.exists(background_path):
        print("🎨 Generating animated background...")
        background_path = _create_animated_background(duration)

    # Combine background + audio + branding
    success = _render_final_video(
        background_path=background_path,
        audio_path=audio_path,
        output_path=video_path,
        topic=topic,
        duration=duration,
    )

    if not success or not os.path.exists(video_path):
        raise RuntimeError(f"Video rendering failed — file not found: {video_path}")

    size = os.path.getsize(video_path)
    print(f"✅ Video created: {video_path} ({size:,} bytes)")

    result = {
        "video_path": video_path,
        "duration":   duration,
        "file_size":  size,
        "timestamp":  datetime.now().isoformat(),
    }

    with open("output/step4_video.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def _get_audio_duration(audio_path):
    """Get audio duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"⚠️  Could not get duration: {e} — using 60s default")
        return 60.0


def _fetch_pexels_video(topic, duration):
    """Download a relevant stock video from Pexels."""
    try:
        # Clean topic for search
        query = " ".join(topic.split()[:4])
        headers = {"Authorization": PEXELS_API_KEY}
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params={"query": query, "per_page": 5, "orientation": "landscape"},
            timeout=15,
        )
        response.raise_for_status()
        videos = response.json().get("videos", [])

        for video in videos:
            # Get best quality file
            files = sorted(
                video.get("video_files", []),
                key=lambda x: x.get("width", 0),
                reverse=True,
            )
            for f in files:
                if f.get("width", 0) >= 1280:
                    url = f.get("link")
                    if url:
                        path = _download_file(url, "output/background.mp4")
                        if path:
                            print(f"✅ Pexels video downloaded")
                            return path

        print("⚠️  No suitable Pexels video found")
        return None

    except Exception as e:
        print(f"⚠️  Pexels error: {e}")
        return None


def _download_file(url, path):
    """Download a file from URL."""
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return path
    except Exception as e:
        print(f"⚠️  Download failed: {e}")
        return None


def _create_animated_background(duration):
    """Create animated gradient background using FFmpeg."""
    path = "output/background.mp4"
    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", (
                f"color=c=0x00040f:size=1280x720:duration={duration}:rate=30,"
                "hue=s=1"
            ),
            "-vf", (
                "hue=h=t*20:s=2,"
                "drawtext=text='':x=0:y=0"
            ),
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0 or not os.path.exists(path):
            # Simpler fallback
            cmd2 = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=navy:size=1280x720:duration={duration}:rate=30",
                "-c:v", "libx264",
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                path
            ]
            subprocess.run(cmd2, capture_output=True, timeout=120)

        print(f"✅ Animated background created")
        return path

    except Exception as e:
        print(f"⚠️  Background creation error: {e}")
        return None


def _render_final_video(background_path, audio_path, output_path, topic, duration):
    """Combine background + audio + text overlay into final video."""
    try:
        # Clean topic text for FFmpeg drawtext
        safe_topic = topic.replace("'", "").replace(":", "").replace('"', '')
        safe_topic = safe_topic[:60]  # Limit length

        # Wrap long text
        if len(safe_topic) > 35:
            words = safe_topic.split()
            mid = len(words) // 2
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:])
            title_filter = (
                f"drawtext=text='{line1}':fontcolor=white:fontsize=48:"
                f"x=(w-text_w)/2:y=(h/2)-60:box=1:boxcolor=black@0.5:boxborderw=10,"
                f"drawtext=text='{line2}':fontcolor=white:fontsize=48:"
                f"x=(w-text_w)/2:y=(h/2)+10:box=1:boxcolor=black@0.5:boxborderw=10,"
            )
        else:
            title_filter = (
                f"drawtext=text='{safe_topic}':fontcolor=white:fontsize=52:"
                f"x=(w-text_w)/2:y=(h/2)-30:box=1:boxcolor=black@0.5:boxborderw=10,"
            )

        vf = (
            title_filter +
            "drawtext=text='VIRALVORTEX':fontcolor=cyan:fontsize=28:"
            "x=20:y=20:box=1:boxcolor=black@0.4:boxborderw=6,"
            "drawtext=text='LIKE  SUBSCRIBE  NOTIFY':fontcolor=yellow:fontsize=22:"
            "x=(w-text_w)/2:y=h-50:box=1:boxcolor=black@0.5:boxborderw=5"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", background_path,
            "-i", audio_path,
            "-vf", vf,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            "-pix_fmt", "yuv420p",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            print(f"⚠️  FFmpeg error: {result.stderr[-500:]}")
            # Try without text overlay
            cmd_simple = [
                "ffmpeg", "-y",
                "-i", background_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-shortest",
                "-pix_fmt", "yuv420p",
                output_path
            ]
            result2 = subprocess.run(cmd_simple, capture_output=True, text=True, timeout=300)
            if result2.returncode != 0:
                print(f"⚠️  Simple FFmpeg also failed: {result2.stderr[-300:]}")
                return False

        print(f"✅ Video rendered: {output_path}")
        return True

    except Exception as e:
        print(f"⚠️  Render error: {e}")
        return False


# ── Aliases — all possible names main.py might call ──────────
def make_video(topic, script, audio_path, **kwargs):
    return create_video(topic, script, audio_path, **kwargs)

def generate_video(topic, script, audio_path, **kwargs):
    return create_video(topic, script, audio_path, **kwargs)

def produce_video(topic, script, audio_path, **kwargs):
    return create_video(topic, script, audio_path, **kwargs)

def render_video(topic, script, audio_path, **kwargs):
    return create_video(topic, script, audio_path, **kwargs)


if __name__ == "__main__":
    result = create_video(
        topic="AI tools taking over the internet",
        script="Welcome to ViralVortex!",
        audio_path="output/audio.mp3"
    )
    print(f"\n✅ Done: {result}")
