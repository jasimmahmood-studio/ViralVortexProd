"""
Step 4: Create Video — Section-by-section with relevant visuals
- Each script section gets its own relevant video/image from Pexels
- Sections are concatenated into one 2-3 minute video
- Text overlay matches section content
- Falls back to animated background if no Pexels key
"""

import os
import json
import shutil
import subprocess
import requests
import glob
import tempfile
from datetime import datetime

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "").strip()
PEXELS_HEADERS = {"Authorization": PEXELS_API_KEY} if PEXELS_API_KEY else {}


def _find_binary(name):
    path = shutil.which(name)
    if path: return path
    candidates = [f"/usr/bin/{name}", f"/usr/local/bin/{name}", f"/bin/{name}"]
    try:
        nix = glob.glob(f"/nix/store/*/bin/{name}")
        candidates = nix + candidates
    except Exception:
        pass
    try:
        r = subprocess.run(["find", "/nix", "-name", name, "-type", "f"],
                           capture_output=True, text=True, timeout=15)
        candidates = [p.strip() for p in r.stdout.splitlines() if p.strip()] + candidates
    except Exception:
        pass
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    try:
        subprocess.run([name, "-version"], capture_output=True, timeout=5)
        return name
    except Exception:
        return None


FFMPEG  = _find_binary("ffmpeg")
FFPROBE = _find_binary("ffprobe")
print(f"🔧 ffmpeg  = {FFMPEG}")
print(f"🔧 ffprobe = {FFPROBE}")


def create_video(topic, script, audio_path, output_path=None, script_data=None, **kwargs):
    print(f"\n🎬 Creating video for: {topic}")
    if not FFMPEG:
        raise RuntimeError("ffmpeg not found — check nixpacks.toml")

    os.makedirs("output", exist_ok=True)
    video_path = output_path or "output/video.mp4"

    duration = _get_audio_duration(audio_path)
    print(f"⏱️  Audio duration: {duration:.1f}s")

    # Get sections from script_data if available
    sections = []
    if isinstance(script_data, dict):
        sections = script_data.get("sections", [])

    # If no sections, create one section for whole video
    if not sections:
        search_query = _topic_to_search(topic)
        sections = [{"section": "main", "duration_seconds": duration,
                     "visual_search": search_query, "script": script}]

    print(f"📑 Sections: {len(sections)}")

    # Build each section clip
    section_clips = []
    total_assigned = sum(s.get("duration_seconds", 30) for s in sections)
    scale_factor   = duration / max(total_assigned, 1)

    for i, section in enumerate(sections):
        sec_duration = section.get("duration_seconds", 30) * scale_factor
        visual_query = section.get("visual_search", topic)
        sec_label    = section.get("section", f"section_{i}")

        print(f"\n  📽️  Section {i+1}/{len(sections)}: {sec_label} ({sec_duration:.1f}s)")
        print(f"       Visual: {visual_query}")

        clip_path = f"output/clip_{i:02d}.mp4"
        bg = None

        # Try Pexels video
        if PEXELS_API_KEY:
            bg = _fetch_pexels_video(visual_query, sec_duration, clip_path)

        # Try Pexels image as video
        if not bg and PEXELS_API_KEY:
            bg = _fetch_pexels_image_as_video(visual_query, sec_duration, clip_path)

        # Fall back to animated background
        if not bg:
            bg = _create_section_background(visual_query, sec_duration, clip_path, i)

        if bg and os.path.exists(bg):
            section_clips.append({"path": bg, "duration": sec_duration, "label": sec_label})
        else:
            print(f"  ⚠️  Skipping section {i+1} — no background created")

    if not section_clips:
        raise RuntimeError("No section clips created")

    # Concatenate all clips
    print(f"\n🔗 Concatenating {len(section_clips)} clips...")
    concat_path = _concatenate_clips(section_clips, duration)

    if not concat_path or not os.path.exists(concat_path):
        raise RuntimeError("Clip concatenation failed")

    # Merge with audio + add branding
    print(f"🎵 Merging with audio + branding...")
    success = _render_final(concat_path, audio_path, video_path, topic)

    # Cleanup clip files
    for clip in section_clips:
        try:
            if os.path.exists(clip["path"]):
                os.remove(clip["path"])
        except Exception:
            pass
    if concat_path and os.path.exists(concat_path):
        try: os.remove(concat_path)
        except Exception: pass

    if not success or not os.path.exists(video_path):
        raise RuntimeError("Final video render failed")

    size = os.path.getsize(video_path)
    print(f"✅ Video: {video_path} ({size/1024/1024:.1f} MB)")

    result = {
        "video_path": video_path,
        "duration":   duration,
        "sections":   len(section_clips),
        "file_size":  size,
        "timestamp":  datetime.now().isoformat(),
    }
    with open("output/step4_video.json", "w") as f:
        json.dump(result, f, indent=2)
    return result


def _topic_to_search(topic):
    """Convert topic to a good visual search query."""
    # Remove filler words
    stopwords = {"the","a","an","is","are","was","were","be","been",
                 "has","have","had","will","would","could","should",
                 "why","how","what","who","when","where","this","that"}
    words = [w for w in topic.lower().split() if w not in stopwords]
    return " ".join(words[:5])


def _fetch_pexels_video(query, duration, output_path):
    """Fetch relevant video from Pexels."""
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers=PEXELS_HEADERS,
            params={"query": query, "per_page": 5,
                    "orientation": "landscape", "size": "medium"},
            timeout=15
        )
        r.raise_for_status()
        videos = r.json().get("videos", [])

        for video in videos:
            files = sorted(video.get("video_files", []),
                           key=lambda x: x.get("width", 0), reverse=True)
            for f in files:
                if 1280 <= f.get("width", 0) <= 3840:
                    url = f.get("link")
                    if url:
                        raw = _download_file(url, output_path + "_raw.mp4")
                        if raw:
                            encoded = _reencode_clip(raw, duration, output_path)
                            try: os.remove(raw)
                            except Exception: pass
                            if encoded:
                                print(f"  ✅ Pexels video: {query[:40]}")
                                return encoded
    except Exception as e:
        print(f"  ⚠️  Pexels video error: {e}")
    return None


def _fetch_pexels_image_as_video(query, duration, output_path):
    """Fetch image from Pexels and convert to video clip."""
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers=PEXELS_HEADERS,
            params={"query": query, "per_page": 3,
                    "orientation": "landscape"},
            timeout=15
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])

        for photo in photos:
            url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large")
            if url:
                img_path = output_path + "_img.jpg"
                img = _download_file(url, img_path)
                if img:
                    # Convert image to video
                    cmd = [
                        FFMPEG, "-y",
                        "-loop", "1",
                        "-i", img_path,
                        "-vf", f"scale=1280:720:force_original_aspect_ratio=decrease,"
                               f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,"
                               f"zoompan=z='min(zoom+0.0005,1.3)':d={int(duration*25)}:s=1280x720",
                        "-c:v", "libx264", "-preset", "fast",
                        "-t", str(duration),
                        "-pix_fmt", "yuv420p",
                        "-r", "25",
                        "-an",
                        output_path
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    try: os.remove(img_path)
                    except Exception: pass
                    if result.returncode == 0 and os.path.exists(output_path):
                        print(f"  ✅ Pexels image→video: {query[:40]}")
                        return output_path
    except Exception as e:
        print(f"  ⚠️  Pexels image error: {e}")
    return None


def _create_section_background(query, duration, output_path, index):
    """Create unique colored animated background per section."""
    colors = [
        "0x00040f", "0x0a0020", "0x001a0a", "0x1a0000",
        "0x00101a", "0x100010", "0x0a1000", "0x001010"
    ]
    color = colors[index % len(colors)]
    hue   = index * 45  # different hue per section

    cmds = [
        [
            FFMPEG, "-y", "-f", "lavfi",
            "-i", f"color=c={color}:size=1280x720:duration={duration}:rate=25",
            "-vf", f"hue=h={hue}:s=2",
            "-c:v", "libx264", "-preset", "fast",
            "-t", str(duration), "-pix_fmt", "yuv420p", "-an",
            output_path
        ],
        [
            FFMPEG, "-y", "-f", "lavfi",
            "-i", f"color=c=navy:size=1280x720:duration={duration}:rate=25",
            "-c:v", "libx264", "-preset", "fast",
            "-t", str(duration), "-pix_fmt", "yuv420p", "-an",
            output_path
        ],
    ]
    for cmd in cmds:
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=60)
            if r.returncode == 0 and os.path.exists(output_path):
                return output_path
        except Exception:
            pass
    return None


def _reencode_clip(input_path, duration, output_path):
    """Re-encode to safe format."""
    try:
        cmd = [
            FFMPEG, "-y", "-i", input_path,
            "-t", str(duration),
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
                   "pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,setsar=1",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-r", "25", "-an",
            output_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0 and os.path.exists(output_path):
            return output_path
    except Exception as e:
        print(f"  ⚠️  Re-encode error: {e}")
    return None


def _concatenate_clips(section_clips, total_duration):
    """Concatenate all section clips into one video."""
    if len(section_clips) == 1:
        return section_clips[0]["path"]

    concat_list = "output/concat_list.txt"
    concat_out  = "output/concat.mp4"

    try:
        with open(concat_list, "w") as f:
            for clip in section_clips:
                f.write(f"file '{os.path.abspath(clip['path'])}'\n")

        cmd = [
            FFMPEG, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-t", str(total_duration),
            concat_out
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode == 0 and os.path.exists(concat_out):
            return concat_out
        print(f"⚠️  Concat error: {r.stderr[-300:]}")
    except Exception as e:
        print(f"⚠️  Concat exception: {e}")

    # Fallback: use first clip
    return section_clips[0]["path"]


def _render_final(bg_path, audio_path, output_path, topic):
    """Merge background video with audio + add branding overlay."""
    safe = (topic.replace("'","").replace('"',"")
                 .replace(":","").replace("\\",""))[:50]

    vf = (
        "drawtext=text='🌀 VIRALVORTEX':fontcolor=00f5ff:fontsize=24:"
        "x=20:y=15:box=1:boxcolor=black@0.5:boxborderw=5,"
        "drawtext=text='LIKE  •  SUBSCRIBE  •  NOTIFY':"
        "fontcolor=yellow:fontsize=18:"
        "x=(w-text_w)/2:y=h-40:box=1:boxcolor=black@0.6:boxborderw=4"
    )

    # With overlay
    cmd1 = [
        FFMPEG, "-y",
        "-i", bg_path, "-i", audio_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-pix_fmt", "yuv420p",
        output_path
    ]
    r = subprocess.run(cmd1, capture_output=True, text=True, timeout=600)
    if r.returncode == 0 and os.path.exists(output_path):
        print("✅ Final video rendered with branding")
        return True

    # Without overlay
    cmd2 = [
        FFMPEG, "-y",
        "-i", bg_path, "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-pix_fmt", "yuv420p",
        output_path
    ]
    r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=600)
    if r2.returncode == 0 and os.path.exists(output_path):
        print("✅ Final video rendered (no overlay)")
        return True

    print(f"❌ Render failed: {r2.stderr[-400:]}")
    return False


def _get_audio_duration(audio_path):
    if FFPROBE:
        try:
            cmd = [FFPROBE, "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return float(r.stdout.strip())
        except Exception: pass
    try:
        from mutagen.mp3 import MP3
        return MP3(audio_path).info.length
    except Exception: pass
    if FFMPEG:
        try:
            r = subprocess.run([FFMPEG, "-i", audio_path, "-f", "null", "-"],
                               capture_output=True, text=True, timeout=30)
            for line in r.stderr.splitlines():
                if "Duration:" in line:
                    t = line.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = t.split(":")
                    return int(h)*3600 + int(m)*60 + float(s)
        except Exception: pass
    return 150.0  # default 2.5 mins


def _download_file(url, path):
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return path
    except Exception as e:
        print(f"  ⚠️  Download failed: {e}")
        return None


# Aliases
def make_video(topic, script, audio_path, **kwargs):     return create_video(topic, script, audio_path, **kwargs)
def generate_video(topic, script, audio_path, **kwargs): return create_video(topic, script, audio_path, **kwargs)
def produce_video(topic, script, audio_path, **kwargs):  return create_video(topic, script, audio_path, **kwargs)
def render_video(topic, script, audio_path, **kwargs):   return create_video(topic, script, audio_path, **kwargs)


if __name__ == "__main__":
    result = create_video(
        topic="AI robots replacing jobs",
        script="Welcome to ViralVortex!",
        audio_path="output/audio.mp3"
    )
    print(f"✅ Done: {result}")
