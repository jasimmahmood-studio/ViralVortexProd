"""
Step 4: Create Video
- Auto-finds ffmpeg/ffprobe regardless of install path
- Downloads stock footage from Pexels (if API key set)
- Falls back to animated gradient background (no API key needed)
- Combines with audio using FFmpeg
- Adds ViralVortex branding overlay
"""

import os
import json
import shutil
import subprocess
import requests
from datetime import datetime

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "").strip()


def _find_binary(name):
    """Find ffmpeg/ffprobe binary path anywhere on the system."""
    # 1. Check PATH first
    path = shutil.which(name)
    if path:
        return path

    # 2. Common locations on Railway / Linux / Nixpacks
    candidates = [
        f"/usr/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/nix/var/nix/profiles/default/bin/{name}",
        f"/run/current-system/sw/bin/{name}",
        f"/home/user/.nix-profile/bin/{name}",
        f"/opt/homebrew/bin/{name}",  # Mac
    ]

    # 3. Search nix store (Railway uses nixpacks)
    try:
        result = subprocess.run(
            ["find", "/nix", "-name", name, "-type", "f"],
            capture_output=True, text=True, timeout=10
        )
        nix_paths = [p.strip() for p in result.stdout.splitlines() if p.strip()]
        candidates = nix_paths + candidates
    except Exception:
        pass

    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            print(f"✅ Found {name} at: {candidate}")
            return candidate

    print(f"⚠️  {name} not found anywhere on system")
    return None


# Find binaries once at module load
FFMPEG  = _find_binary("ffmpeg")
FFPROBE = _find_binary("ffprobe")

print(f"🔧 ffmpeg:  {FFMPEG}")
print(f"🔧 ffprobe: {FFPROBE}")


def create_video(topic, script, audio_path, **kwargs):
    """Main function — create video from topic + audio."""
    print(f"\n🎬 Creating video for: {topic}")

    if not FFMPEG:
        raise RuntimeError(
            "ffmpeg not found. Add this to nixpacks.toml:\n"
            "[phases.setup]\nnixPkgs = ['ffmpeg']"
        )

    os.makedirs("output", exist_ok=True)
    video_path = "output/video.mp4"

    duration = _get_audio_duration(audio_path)
    print(f"⏱️  Audio duration: {duration:.1f}s")

    # Get background
    background_path = None
    if PEXELS_API_KEY:
        background_path = _fetch_pexels_video(topic, duration)

    if not background_path or not os.path.exists(background_path):
        print("🎨 Generating animated background...")
        background_path = _create_animated_background(duration)

    # Render final video
    success = _render_final_video(
        background_path=background_path,
        audio_path=audio_path,
        output_path=video_path,
        topic=topic,
        duration=duration,
    )

    if not success or not os.path.exists(video_path):
        raise RuntimeError(f"Video rendering failed — {video_path} not created")

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
    """Get audio duration using ffprobe, with mutagen fallback."""
    # Try ffprobe
    if FFPROBE:
        try:
            cmd = [
                FFPROBE, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            duration = float(result.stdout.strip())
            print(f"✅ Duration via ffprobe: {duration:.1f}s")
            return duration
        except Exception as e:
            print(f"⚠️  ffprobe duration failed: {e}")

    # Try mutagen (pure Python, no binary needed)
    try:
        from mutagen.mp3 import MP3
        audio = MP3(audio_path)
        duration = audio.info.length
        print(f"✅ Duration via mutagen: {duration:.1f}s")
        return duration
    except ImportError:
        pass
    except Exception as e:
        print(f"⚠️  mutagen failed: {e}")

    # Try ffmpeg directly
    if FFMPEG:
        try:
            cmd = [
                FFMPEG, "-i", audio_path,
                "-f", "null", "-"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # Parse duration from stderr
            for line in result.stderr.splitlines():
                if "Duration:" in line:
                    t = line.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = t.split(":")
                    duration = int(h)*3600 + int(m)*60 + float(s)
                    print(f"✅ Duration via ffmpeg stderr: {duration:.1f}s")
                    return duration
        except Exception as e:
            print(f"⚠️  ffmpeg duration parse failed: {e}")

    print("⚠️  Using default duration: 60s")
    return 60.0


def _fetch_pexels_video(topic, duration):
    """Download relevant stock video from Pexels."""
    try:
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
            files = sorted(
                video.get("video_files", []),
                key=lambda x: x.get("width", 0), reverse=True
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
    """Create animated background using FFmpeg."""
    path = "output/background.mp4"
    try:
        cmd = [
            FFMPEG, "-y",
            "-f", "lavfi",
            "-i", f"color=c=0x00040f:size=1280x720:duration={duration}:rate=30",
            "-vf", "hue=h=t*15:s=2",
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            # Simpler fallback — solid color
            cmd2 = [
                FFMPEG, "-y",
                "-f", "lavfi",
                "-i", f"color=c=navy:size=1280x720:duration={duration}:rate=30",
                "-c:v", "libx264",
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                path
            ]
            subprocess.run(cmd2, capture_output=True, timeout=120)
        print(f"✅ Background created")
        return path
    except Exception as e:
        print(f"⚠️  Background error: {e}")
        return None


def _render_final_video(background_path, audio_path, output_path, topic, duration):
    """Combine background + audio + text branding."""
    try:
        safe_topic = (topic
            .replace("'", "")
            .replace('"', '')
            .replace(":", "")
            .replace("\\", ""))[:60]

        # Split long titles into 2 lines
        if len(safe_topic) > 35:
            words = safe_topic.split()
            mid = len(words) // 2
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:])
            title_vf = (
                f"drawtext=text='{line1}':fontcolor=white:fontsize=46:"
                f"x=(w-text_w)/2:y=(h/2)-55:box=1:boxcolor=black@0.5:boxborderw=8,"
                f"drawtext=text='{line2}':fontcolor=white:fontsize=46:"
                f"x=(w-text_w)/2:y=(h/2)+10:box=1:boxcolor=black@0.5:boxborderw=8,"
            )
        else:
            title_vf = (
                f"drawtext=text='{safe_topic}':fontcolor=white:fontsize=52:"
                f"x=(w-text_w)/2:y=(h/2)-25:box=1:boxcolor=black@0.5:boxborderw=10,"
            )

        vf = (
            title_vf +
            "drawtext=text='VIRALVORTEX':fontcolor=00f5ff:fontsize=28:"
            "x=20:y=20:box=1:boxcolor=black@0.4:boxborderw=5,"
            "drawtext=text='LIKE  SUBSCRIBE  NOTIFY':fontcolor=yellow:fontsize=22:"
            "x=(w-text_w)/2:y=h-50:box=1:boxcolor=black@0.5:boxborderw=5"
        )

        cmd = [
            FFMPEG, "-y",
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
            print(f"⚠️  FFmpeg with overlay failed, trying without text...")
            cmd_simple = [
                FFMPEG, "-y",
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
                print(f"⚠️  FFmpeg stderr: {result2.stderr[-400:]}")
                return False

        print(f"✅ Video rendered successfully")
        return True

    except Exception as e:
        print(f"⚠️  Render error: {e}")
        return False


# Aliases
def make_video(topic, script, audio_path, **kwargs):     return create_video(topic, script, audio_path, **kwargs)
def generate_video(topic, script, audio_path, **kwargs): return create_video(topic, script, audio_path, **kwargs)
def produce_video(topic, script, audio_path, **kwargs):  return create_video(topic, script, audio_path, **kwargs)
def render_video(topic, script, audio_path, **kwargs):   return create_video(topic, script, audio_path, **kwargs)


if __name__ == "__main__":
    result = create_video(
        topic="AI tools taking over the internet",
        script="Welcome to ViralVortex!",
        audio_path="output/audio.mp3"
    )
    print(f"\n✅ Done: {result}")
