"""
STEP 5: Generate YouTube Thumbnail
Uses Pillow to create a professional thumbnail with text overlays.
Optional: DALL-E 3 for AI background image.
"""

import os
import io
import textwrap
import requests
from pathlib import Path


def generate_thumbnail_pillow(topic: str, hook: str, output_path: str):
    """Generate thumbnail using Pillow (no API key required)"""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import math

    W, H = 1280, 720
    img = Image.new("RGB", (W, H), color=(0, 4, 15))
    draw = ImageDraw.Draw(img)

    # ── Gradient background ──────────────────────────────────
    for y in range(H):
        t = y / H
        r = int(0 + 8 * t)
        g = int(4 + 4 * t)
        b = int(15 + 25 * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ── Vortex circles (decorative) ──────────────────────────
    for radius in [320, 240, 160, 90]:
        cx, cy = 220, 360
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     outline=(0, 245, 255), width=2)

    # ── Neon glow rectangles ─────────────────────────────────
    # Bottom banner
    draw.rectangle([0, H - 100, W, H], fill=(0, 0, 0, 180))

    # Left accent bar
    for x in range(6):
        alpha = 255 - x * 40
        draw.line([(x, 0), (x, H)], fill=(0, 245, 255, alpha), width=1)

    # ── Load fonts (fallback to default) ─────────────────────
    try:
        from PIL import ImageFont
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        font_tag = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except Exception:
        font_big = ImageFont.load_default()
        font_med = font_big
        font_sm = font_big
        font_tag = font_big

    # ── Channel badge ─────────────────────────────────────────
    draw.rounded_rectangle([W - 260, 20, W - 20, 70], radius=8,
                            fill=(0, 245, 255, 40), outline=(0, 245, 255), width=2)
    draw.text((W - 240, 28), "🌀 ViralVortex", font=font_tag, fill=(0, 245, 255))

    # ── TRENDING badge ────────────────────────────────────────
    draw.rounded_rectangle([20, 20, 180, 65], radius=8,
                            fill=(255, 50, 50, 200), outline=(255, 100, 100), width=1)
    draw.text((35, 28), "🔥 TRENDING", font=font_tag, fill=(255, 255, 255))

    # ── Main topic title (wrapped) ────────────────────────────
    title_text = topic[:55].upper()
    words = title_text.split()
    lines = []
    current = ""
    for word in words:
        if len(current + " " + word) <= 22:
            current = (current + " " + word).strip()
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    lines = lines[:3]  # max 3 lines

    y_start = 130
    for i, line in enumerate(lines):
        # Shadow
        draw.text((42, y_start + i * 85 + 3), line, font=font_big, fill=(0, 0, 0, 180))
        # Gradient effect (cyan to white)
        if i == 0:
            draw.text((40, y_start + i * 85), line, font=font_big, fill=(0, 245, 255))
        else:
            draw.text((40, y_start + i * 85), line, font=font_big, fill=(255, 255, 255))

    # ── Hook text at bottom ───────────────────────────────────
    hook_short = hook[:80] + ("..." if len(hook) > 80 else "")
    hook_wrapped = textwrap.fill(hook_short, width=55)
    hook_lines = hook_wrapped.split('\n')[:2]
    for j, hline in enumerate(hook_lines):
        draw.text((20, H - 90 + j * 38), hline, font=font_sm, fill=(255, 200, 50))

    # ── Glow effect on main text (blur overlay) ───────────────
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for i, line in enumerate(lines):
        glow_draw.text((40, y_start + i * 85), line, font=font_big, fill=(0, 100, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=8))
    img = Image.blend(img, glow, alpha=0.4)

    img.save(output_path, "JPEG", quality=95)
    print(f"   ✅ Thumbnail saved (Pillow): {output_path}")


def generate_thumbnail_dalle(topic: str, hook: str, output_path: str):
    """Generate AI background using DALL-E 3, then add text overlay"""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    import openai
    client = openai.OpenAI(api_key=api_key)

    prompt = (
        f"YouTube thumbnail background for a video about '{topic}'. "
        "Dark, dramatic, cinematic style. Deep navy and cyan color palette. "
        "Glowing neon effects. NO text. High contrast. Photorealistic."
    )

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1792x1024",
        quality="standard",
        n=1
    )

    img_url = response.data[0].url
    img_data = requests.get(img_url, timeout=30).content

    from PIL import Image, ImageDraw, ImageFont
    import io

    bg = Image.open(io.BytesIO(img_data)).convert("RGB")
    bg = bg.resize((1280, 720))

    # Add text overlay
    draw = ImageDraw.Draw(bg)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
        font_sm = font

    # Dark overlay for text readability
    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([0, 580, 1280, 720], fill=(0, 0, 0, 180))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)

    # Title
    title = topic[:55].upper()
    draw.text((40, 40), title, font=font, fill=(0, 245, 255))
    draw.text((40, 600), hook[:80], font=font_sm, fill=(255, 200, 50))
    draw.text((1050, 20), "ViralVortex", font=font_sm, fill=(0, 245, 255))

    bg.save(output_path, "JPEG", quality=95)
    print(f"   ✅ Thumbnail saved (DALL-E): {output_path}")


def generate_thumbnail(topic: str, hook: str, output_path: str):
    """Main entry: try DALL-E first, fallback to Pillow"""
    try:
        generate_thumbnail_dalle(topic, hook, output_path)
    except Exception as e:
        print(f"   DALL-E failed ({e}), using Pillow fallback...")
        generate_thumbnail_pillow(topic, hook, output_path)
