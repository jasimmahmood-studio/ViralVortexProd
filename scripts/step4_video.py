"""
Step 4: Create Video
Auto-finds ffmpeg in Railway Nix store, PATH, or any common location
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
    """Find ffmpeg/ffprobe binary anywhere on the system."""
    # 1. shutil.which checks PATH
    path = shutil.which(name)
    if path:
        print(f"✅ {name} found in PATH: {path}")
        return path

    # 2. Common fixed locations
    candidates = [
        f"/usr/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/bin/{name}",
        f"/opt/homebrew/bin/{name}",
    ]

    # 3. Search entire /nix store (Railway nixpacks installs here)
    try:
        nix_results = glob.glob(f"/nix/store/*/{name}", recursive=False)
        nix_results += glob.glob(f"/nix/store/*/bin/{name}", recursive=False)
        candidates = nix_results + candidates
    except Exception:
        pass

    # 4. Also try find command
    try:
        result = subprocess.run(
            ["find", "/nix", "-name", name, "-type", "f"],
            capture_output=True, text=True, timeout=15
        )
        found = [p.strip() for p in result.stdout.splitlines() if p.strip()]
        candidates = found + candidates
    except Exception:
        pass

    # 5. Try find in /usr too
    try:
        result = subprocess.run(
            ["find", "/usr", "-name", name, "-type", "f"],
            capture_output=True, text=True, timeout=10
        )
        found = [p.strip() for p in result.stdout.splitlines() if p.strip()]
        candidates = found + candidates
    except Exception:
        pass

    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            print(f"✅ {name} found at: {candidate}")
            return candidate

    # 6. Last resort — try running it directly and hope it's in PATH
    try:
        subprocess.run([name, "-version"], capture_output=True, timeout=5)
        print(f"✅ {name} works directly (in PATH but not found by which)")
        return name
    except Exception:
        pass

    print(f"❌ {name} NOT found anywhere")
    return None


# Find at module load time
FFMPEG  = _find_binary("ffmpeg")
FFPROBE = _find_binary("ffprobe")

print(f"🔧 ffmpeg  = {FFMPEG}")
print(f"🔧 ffprobe = {FFPROBE}")


def create_video(topic, script, audio_path, **kwargs):
    print(f"\n🎬 Creating video for: {topic}")

    if not FFMPEG:
        # Try one more time at runtime
        ffmpeg = _find_binary("ffmpeg")
        if not ffmpeg:
            raise RuntimeError(
                "ffmpeg not found on this system.\n"
                "Make sure nixpacks.toml contains:\n"
                "  [phases.setup]\n"
                "  nixPkgs = [\"python311\", \"ffmpeg-full\", \"gcc\"]"
            )

    os.makedirs("output", exist_ok=True)
    video_path = "output/video.mp4"

    duration = _get_audio_duration(audio_path)
    print(f"⏱️  Duration: {duration:.1f}s")

    background_path = None
    if PEXELS_API_KEY:
        background_path = _fetch_pexels_video(topic, duration)

    if not background_path or not os.path.exists(background_path):
        print("🎨 Generating background...")
        background_path = _create_animated_background(duration)

    success = _render_final_video(
        background_path=background_path,
        audio_path=audio_path,
        output_path=video_path,
        topic=topic,
    )

    if not success or not os.path.exists(video_path):
        raise RuntimeError(f"Video rendering failed — {video_path} not created")

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


def _get_audio_duration(audio_path):
    if FFPROBE:
        try:
            cmd = [
                FFPROBE, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"⚠️  ffprobe duration error: {e}")

    # mutagen fallback
    try:
        from mutagen.mp3 import MP3
        return MP3(audio_path).info.length
    except Exception:
        pass

    # ffmpeg stderr parse
    if FFMPEG:
        try:
            result = subprocess.run(
                [FFMPEG, "-i", audio_path, "-f", "null", "-"],
                capture_output=True, text=True, timeout=30
            )
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
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params={"query": query, "per_page": 5, "orientation": "landscape"},
            timeout=15,
        )
        response.raise_for_status()
        for video in response.json().get("videos", []):
            files = sorted(video.get("video_files", []), key=lambda x: x.get("width", 0), reverse=True)
            for f in files:
                if f.get("width", 0) >= 1280:
                    url = f.get("link")
                    if url:
                        path = _download_file(url, "output/background.mp4")
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


def _create_animated_background(duration):
    path = "output/background.mp4"
    cmds = [
        # Animated color cycle
        [
            FFMPEG, "-y", "-f", "lavfi",
            "-i", f"color=c=0x00040f:size=1280x720:duration={duration}:rate=25",
            "-vf", "hue=h=t*20:s=2",
            "-c:v", "libx264", "-t", str(duration), "-pix_fmt", "yuv420p", path
        ],
        # Simple solid color fallback
        [
            FFMPEG, "-y", "-f", "lavfi",
            "-i", f"color=c=navy:size=1280x720:duration={duration}:rate=25",
            "-c:v", "libx264", "-t", str(duration), "-pix_fmt", "yuv420p", path
        ],
    ]
    for cmd in cmds:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and os.path.exists(path):
                print(f"✅ Background created")
                return path
            print(f"⚠️  Background attempt failed: {result.stderr[-200:]}")
        except Exception as e:
            print(f"⚠️  Background error: {e}")
    return None


def _render_final_video(background_path, audio_path, output_path, topic):
    safe = (topic.replace("'","").replace('"',"").replace(":","").replace("\\",""))[:60]

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

    # Try with branding overlay
    cmd = [
        FFMPEG, "-y",
        "-i", background_path,
        "-i", audio_path,
        "-vf", vf,
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest", "-pix_fmt", "yuv420p",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode == 0 and os.path.exists(output_path):
        print(f"✅ Video rendered with branding")
        return True

    print(f"⚠️  Overlay failed, trying plain merge...")

    # Fallback — no text overlay
    cmd2 = [
        FFMPEG, "-y",
        "-i", background_path,
        "-i", audio_path,
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest", "-pix_fmt", "yuv420p",
        output_path
    ]
    result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=300)
    if result2.returncode == 0 and os.path.exists(output_path):
        print(f"✅ Video rendered (no overlay)")
        return True

    print(f"❌ FFmpeg stderr: {result2.stderr[-500:]}")
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
