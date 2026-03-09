"""
Step 5: Create Thumbnail
- Primary: DALL-E 3 (if OPENAI_API_KEY set)
- Fallback: Pillow generated thumbnail (no API key needed)
"""

import os
import json
import requests
import textwrap
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()


def create_thumbnail(topic, **kwargs):
    """Main function — create thumbnail for the video."""
    print(f"\n🖼️  Creating thumbnail for: {topic}")
    os.makedirs("output", exist_ok=True)
    thumb_path = "output/thumbnail.jpg"

    # Try DALL-E first
    if OPENAI_API_KEY:
        result = _try_dalle(topic, thumb_path)
        if result:
            return result

    # Fallback: Pillow generated
    result = _try_pillow(topic, thumb_path)
    if result:
        return result

    raise RuntimeError("All thumbnail generation methods failed")


def _try_dalle(topic, thumb_path):
    """Generate thumbnail using DALL-E 3."""
    try:
        prompt = (
            f"YouTube thumbnail for a viral video about: {topic}. "
            "Bold text, bright colors, shocked expression, "
            "professional YouTube thumbnail style, eye-catching, 16:9"
        )
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1792x1024",
            "quality": "standard",
        }
        r = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers, json=payload, timeout=60
        )
        r.raise_for_status()
        image_url = r.json()["data"][0]["url"]

        # Download image
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()
        with open(thumb_path, "wb") as f:
            f.write(img_response.content)

        size = os.path.getsize(thumb_path)
        print(f"✅ DALL-E thumbnail: {thumb_path} ({size:,} bytes)")
        return _build_result(thumb_path, "dalle")

    except Exception as e:
        print(f"⚠️  DALL-E error: {e}")
        return None


def _try_pillow(topic, thumb_path):
    """Generate thumbnail using Pillow (no API key needed)."""
    if not PIL_AVAILABLE:
        print("⚠️  Pillow not installed — trying to install...")
        os.system("pip install Pillow -q")
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception:
            print("⚠️  Pillow install failed")
            return None

    try:
        from PIL import Image, ImageDraw, ImageFont

        # Canvas: 1280x720
        W, H = 1280, 720
        img = Image.new("RGB", (W, H), color=(0, 4, 15))
        draw = ImageDraw.Draw(img)

        # Background gradient effect (simple rectangles)
        for i in range(H):
            ratio = i / H
            r = int(0   + ratio * 20)
            g = int(4   + ratio * 10)
            b = int(15  + ratio * 40)
            draw.line([(0, i), (W, i)], fill=(r, g, b))

        # Cyan glow bar top
        draw.rectangle([(0, 0), (W, 8)], fill=(0, 245, 255))
        # Cyan glow bar bottom
        draw.rectangle([(0, H-8), (W, H)], fill=(0, 245, 255))

        # Channel name top-left
        try:
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            font_med   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        except Exception:
            font_small = ImageFont.load_default()
            font_large = ImageFont.load_default()
            font_med   = ImageFont.load_default()

        # VIRALVORTEX branding
        draw.text((20, 20), "🌀 VIRALVORTEX", font=font_small, fill=(0, 245, 255))

        # Main title — wrap at 28 chars per line
        safe_topic = topic[:120]
        lines = textwrap.wrap(safe_topic, width=28)[:3]

        total_height = len(lines) * 90
        start_y = (H - total_height) // 2 - 20

        for i, line in enumerate(lines):
            y = start_y + i * 90
            # Shadow
            draw.text((W//2 - 1 + 3, y + 3), line,
                      font=font_large, fill=(0, 0, 0), anchor="mm")
            # Main text
            draw.text((W//2 - 1, y), line,
                      font=font_large, fill=(255, 255, 255), anchor="mm")

        # Bottom bar
        draw.rectangle([(0, H-60), (W, H-8)], fill=(123, 47, 255, 180))
        draw.text((W//2, H-34), "LIKE  •  SUBSCRIBE  •  NOTIFY",
                  font=font_small, fill=(255, 255, 0), anchor="mm")

        # Save
        img.save(thumb_path, "JPEG", quality=95)
        size = os.path.getsize(thumb_path)
        print(f"✅ Pillow thumbnail: {thumb_path} ({size:,} bytes)")
        return _build_result(thumb_path, "pillow")

    except Exception as e:
        print(f"⚠️  Pillow error: {e}")
        return None


def _build_result(thumb_path, source):
    result = {
        "thumbnail_path": thumb_path,
        "source":         source,
        "file_size":      os.path.getsize(thumb_path),
        "timestamp":      datetime.now().isoformat(),
    }
    with open("output/step5_thumbnail.json", "w") as f:
        json.dump(result, f, indent=2)
    return result


# ── Aliases — all possible names main.py might call ──────────
def generate_thumbnail(topic, **kwargs): return create_thumbnail(topic, **kwargs)
def make_thumbnail(topic, **kwargs):     return create_thumbnail(topic, **kwargs)
def get_thumbnail(topic, **kwargs):      return create_thumbnail(topic, **kwargs)
def build_thumbnail(topic, **kwargs):    return create_thumbnail(topic, **kwargs)


if __name__ == "__main__":
    result = create_thumbnail("AI tools taking over the internet in 2025")
    print(f"\n✅ Done: {result}")
