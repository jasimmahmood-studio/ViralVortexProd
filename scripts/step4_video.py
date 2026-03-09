"""
Step 4: Create Video
- Re-encodes background to ensure compatibility
- Adds branding overlay
- Falls back to animated background if Pexels fails
"""

import os
import json
import shutil
import subprocess
import requests
import glob
from datetime import datetime

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "").strip()


def _find_binary(name):
    path = shutil.which(name)
    if path:
        return path
    candidates = [
        f"/usr/bin/{name}", f"/usr/local/bin/{name}", f"/bin/{name}",
    ]
    try:
        nix_results = glob.glob(f"/nix/store/*/bin/{name}")
        candidates = nix_results + candidates
    except Exception:
        pass
    try:
        result = subprocess.run(["find", "/nix", "-name", name, "-type", "f"],
                                capture_output=True, text=True, timeout=15)
        found = [p.strip() for p in result.stdout.splitlines() if p.strip()]
        candidates = found + candidates
    except Exception:
        pass
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    try:
        subprocess.run([name, "-version"], capture_output=True, timeout=5)
        return name
    except Exception:
        pass
    return None


FFMPEG  = _find_binary("ffmpeg")
FFPROBE = _find_binary("ffprobe")
print(f"🔧 ffmpeg  = {FFMPEG}")
print(f"🔧 ffprobe = {FFPROBE}")


def create_video(topic, script, audio_path, **kwargs):
    print(f"\n🎬 Creating video for: {topic}")

    if not FFMPEG:
        raise RuntimeError("ffmpeg not found — check nixpacks.toml")

    os.makedirs("output", exist_ok=True)
    video_path = "output/video.mp4"

    duration = _get_audio_duration(audio_path)
    print(f"⏱️  Duration: {duration:.1f}s")

    # Get background
    raw_background = None
    if PEXELS_API_KEY:
        raw_background = _fetch_pexels_video(topic, duration)

    # Re-encode background to safe format
    background_path = None
    if raw_background and os.path.exists(raw_background):
        print("🔄 Re-encoding background to compatible format...")
        background_path = _reencode_video(raw_background, duration)

    # Fall back to generated background
    if not background_path or not os.path.exists(background_path):
        print("🎨 Generating animated background...")
        background_path = _create_animated_background(duration)

    if not background_path or not os.path.exists(background_path):
        raise RuntimeError("Could not create any background video")

    # Render final video
    success = _render_final_video(
        background_path=background_path,
        audio_path=audio_path,
        output_path=video_path,
        topic=topic,
    )

    if not success or not os.path.exists(video_path):
        raise RuntimeError(f"Video rendering failed")

    size = os.path.getsize(video_path)
    print(f"✅ Video: {video_path} ({size:,} bytes)")

    result = {
        "video_path": video_path,
        "duration":   duration,
        "file_size":  size,
        "timestamp":  datetime.now().isoformat(),
    }
    with open("output/step4_video.json", "w") as f:
        json.dump(result, f, indent=2)
    return result


def _reencode_video(input_path, duration):
    """Re-encode any video to a safe h264/yuv420p format FFmpeg can always merge."""
    output_path = "output/background_reencoded.mp4"
    try:
        cmd = [
            FFMPEG, "-y",
            "-i", input_path,
            "-t", str(duration),          # trim to audio length
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
                   "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-an",                         # remove audio from background
            "-r", "25",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode == 0 and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"✅ Re-encoded background: {size:,} bytes")
            return output_path
        else:
            print(f"⚠️  Re-encode failed: {result.stderr[-300:]}")
            return None
    except Exception as e:
        print(f"⚠️  Re-encode error: {e}")
        return None


def _create_animated_background(duration):
    """Create animated gradient background."""
    path = "output/background.mp4"
    cmds = [
        [
            FFMPEG, "-y", "-f", "lavfi",
            "-i", f"color=c=0x00040f:size=1280x720:duration={duration}:rate=25",
            "-vf", "hue=h=t*20:s=2",
            "-c:v", "libx264", "-preset", "fast",
            "-t", str(duration), "-pix_fmt", "yuv420p", path
        ],
        [
            FFMPEG, "-y", "-f", "lavfi",
            "-i", f"color=c=navy:size=1280x720:duration={duration}:rate=25",
            "-c:v", "libx264", "-preset", "fast",
            "-t", str(duration), "-pix_fmt", "yuv420p", path
        ],
    ]
    for cmd in cmds:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and os.path.exists(path):
                print(f"✅ Animated background created")
                return path
        except Exception as e:
            print(f"⚠️  Background attempt error: {e}")
    return None


def _render_final_video(background_path, audio_path, output_path, topic):
    """Combine background + audio with text overlay."""
    safe = (topic.replace("'", "").replace('"', '')
                 .replace(":", "").replace("\\", ""))[:60]

    if len(safe) > 35:
        words = safe.split()
        mid = len(words) // 2
        l1, l2 = " ".join(words[:mid]), " ".join(words[mid:])
        title_vf = (
            f"drawtext=text='{l1}':fontcolor=white:fontsize=46:"
            f"x=(w-text_w)/2:y=(h/2)-55:box=1:boxcolor=black@0.5:boxborderw=8,"
            f"drawtext=text='{l2}':fontcolor=white:fontsize=46:"
            f"x=(w-text_w)/2:y=(h/2)+10:box=1:boxcolor=black@0.5:boxborderw=8,"
        )
    else:
        title_vf = (
            f"drawtext=text='{safe}':fontcolor=white:fontsize=52:"
            f"x=(w-text_w)/2:y=(h/2)-25:box=1:boxcolor=black@0.5:boxborderw=10,"
        )

    vf = (
        title_vf +
        "drawtext=text='VIRALVORTEX':fontcolor=00f5ff:fontsize=28:"
        "x=20:y=20:box=1:boxcolor=black@0.4:boxborderw=5,"
        "drawtext=text='LIKE  SUBSCRIBE  NOTIFY':fontcolor=yellow:fontsize=22:"
        "x=(w-text_w)/2:y=h-50:box=1:boxcolor=black@0.5:boxborderw=5"
    )

    # Attempt 1: with text overlay
    cmd1 = [
        FFMPEG, "-y",
        "-i", background_path,
        "-i", audio_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-pix_fmt", "yuv420p",
        output_path
    ]
    result = subprocess.run(cmd1, capture_output=True, text=True, timeout=300)
    if result.returncode == 0 and os.path.exists(output_path):
        print(f"✅ Video rendered with branding")
        return True

    print(f"⚠️  Overlay failed: {result.stderr[-200:]}")

    # Attempt 2: plain merge, no overlay
    cmd2 = [
        FFMPEG, "-y",
        "-i", background_path,
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-pix_fmt", "yuv420p",
        output_path
    ]
    result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=300)
    if result2.returncode == 0 and os.path.exists(output_path):
        print(f"✅ Video rendered (no overlay)")
        return True

    # Attempt 3: use filter_complex instead
    cmd3 = [
        FFMPEG, "-y",
        "-i", background_path,
        "-i", audio_path,
        "-filter_complex", "[0:v][1:a]",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        "-shortest", "-pix_fmt", "yuv420p",
        output_path
    ]
    result3 = subprocess.run(cmd3, capture_output=True, text=True, timeout=300)
    if result3.returncode == 0 and os.path.exists(output_path):
        print(f"✅ Video rendered (filter_complex)")
        return True

    print(f"❌ All render attempts failed")
    print(f"   stderr: {result2.stderr[-400:]}")
    return False


def _get_audio_duration(audio_path):
    if FFPROBE:
        try:
            cmd = [FFPROBE, "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return float(result.stdout.strip())
        except Exception:
            pass
    try:
        from mutagen.mp3 import MP3
        return MP3(audio_path).info.length
    except Exception:
        pass
    if FFMPEG:
        try:
            result = subprocess.run([FFMPEG, "-i", audio_path, "-f", "null", "-"],
                                    capture_output=True, text=True, timeout=30)
            for line in result.stderr.splitlines():
                if "Duration:" in line:
                    t = line.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = t.split(":")
                    return int(h)*3600 + int(m)*60 + float(s)
        except Exception:
            pass
    print("⚠️  Using default duration: 60s")
    return 60.0


def _fetch_pexels_video(topic, duration):
    try:
        query = " ".join(topic.split()[:4])
        headers = {"Authorization": PEXELS_API_KEY}
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params={"query": query, "per_page": 5, "orientation": "landscape"},
            timeout=15,
        )
        r.raise_for_status()
        for video in r.json().get("videos", []):
            files = sorted(video.get("video_files", []),
                           key=lambda x: x.get("width", 0), reverse=True)
            for f in files:
                if f.get("width", 0) >= 1280:
                    url = f.get("link")
                    if url:
                        path = _download_file(url, "output/background_raw.mp4")
                        if path:
                            print(f"✅ Pexels video downloaded")
                            return path
    except Exception as e:
        print(f"⚠️  Pexels error: {e}")
    return None


def _download_file(url, path):
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return path
    except Exception as e:
        print(f"⚠️  Download failed: {e}")
        return None


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
