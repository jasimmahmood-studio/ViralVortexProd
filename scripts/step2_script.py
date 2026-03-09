"""
Step 2: Generate Video Script using Claude API
Returns plain string script directly — no dict wrapping issues
"""

import os
import json
import anthropic
from datetime import datetime


def generate_script(topic, **kwargs):
    print(f"\n📝 Generating script for: {topic}")

    # ── Read API key ─────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    if not api_key.startswith("sk-ant-"):
        raise ValueError(f"ANTHROPIC_API_KEY invalid — must start with sk-ant-, got: {api_key[:10]}")

    print(f"🔑 API key: {api_key[:12]}...{api_key[-4:]}")

    # ── Call Claude ──────────────────────────────────────────
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are a viral YouTube scriptwriter for ViralVortex channel.

Write an energetic spoken script (300-400 words) about this trending topic: {topic}

Rules:
- Start with a strong hook in the first sentence
- Keep it conversational and exciting  
- Include surprising facts or insights
- End with a call to action (like + subscribe)
- Write ONLY the spoken words, no stage directions, no headers, no labels
- Just plain text the narrator will speak

Begin the script now:"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    # ── Extract text safely ──────────────────────────────────
    script = ""

    # Try content blocks
    if hasattr(message, "content") and message.content:
        for block in message.content:
            if hasattr(block, "text") and block.text:
                script = block.text.strip()
                break

    # Fallback: convert to dict
    if not script:
        try:
            msg_dict = message.model_dump() if hasattr(message, "model_dump") else message.dict()
            content = msg_dict.get("content", [])
            if content and isinstance(content, list):
                script = content[0].get("text", "").strip()
        except Exception as e:
            print(f"⚠️  Dict extraction failed: {e}")

    print(f"✅ Raw script length: {len(script)} chars")
    print(f"✅ Preview: {script[:100]}...")

    if not script or len(script) < 50:
        raise ValueError(f"Claude returned empty or short response. Full response: {message}")

    # ── Save to file ─────────────────────────────────────────
    os.makedirs("output", exist_ok=True)

    result = {
        "topic":      topic,
        "script":     script,
        "word_count": len(script.split()),
        "timestamp":  datetime.now().isoformat(),
    }

    with open("output/step2_script.json", "w") as f:
        json.dump(result, f, indent=2)

    # Also save plain text file for easy debugging
    with open("output/script.txt", "w") as f:
        f.write(script)

    print(f"✅ Script saved: {len(script)} chars, {result['word_count']} words")
    return result


# ── Aliases ───────────────────────────────────────────────────
def create_script(topic, **kwargs):
    return generate_script(topic, **kwargs)

def write_script(topic, **kwargs):
    return generate_script(topic, **kwargs)


if __name__ == "__main__":
    result = generate_script("AI tools taking over the internet in 2025")
    print(f"\n--- SCRIPT PREVIEW ---\n{result['script'][:400]}\n...")
