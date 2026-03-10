"""
Step 2: Generate Video Script using Claude API
- Generates structured script with scene descriptions
- 2-3 minute duration (300-450 words)
- Each section has a visual cue for relevant footage/images
"""

import os
import json
import anthropic
from datetime import datetime


def generate_script(topic, **kwargs):
    print(f"\n📝 Generating script for: {topic}")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    if not api_key.startswith("sk-ant-"):
        raise ValueError(f"Invalid ANTHROPIC_API_KEY format")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are a viral YouTube video scriptwriter for ViralVortex channel.

Write a 2-3 minute script (350-450 words) about this trending topic: {topic}

Return your response as valid JSON in this exact format:
{{
  "title": "Catchy YouTube title under 100 chars",
  "description": "YouTube description 2-3 sentences",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "search_keywords": ["keyword1", "keyword2", "keyword3"],
  "sections": [
    {{
      "section": "intro",
      "duration_seconds": 20,
      "visual_search": "search query to find relevant video/image for this section",
      "script": "Spoken words for this section (hook to grab attention in first 5 seconds)"
    }},
    {{
      "section": "main_point_1", 
      "duration_seconds": 35,
      "visual_search": "specific search query for relevant footage",
      "script": "Spoken words explaining first key point with facts"
    }},
    {{
      "section": "main_point_2",
      "duration_seconds": 35,
      "visual_search": "specific search query for relevant footage",
      "script": "Spoken words explaining second key point"
    }},
    {{
      "section": "main_point_3",
      "duration_seconds": 35,
      "visual_search": "specific search query for relevant footage", 
      "script": "Spoken words explaining third key point"
    }},
    {{
      "section": "shocking_fact",
      "duration_seconds": 30,
      "visual_search": "specific search query for shocking/surprising visual",
      "script": "Spoken words revealing surprising fact or insight"
    }},
    {{
      "section": "conclusion",
      "duration_seconds": 25,
      "visual_search": "specific search query for conclusion visual",
      "script": "Spoken words wrapping up with strong call to action to like and subscribe"
    }}
  ]
}}

Rules:
- visual_search must be specific to the topic (e.g. "artificial intelligence robot 2025" not just "technology")
- script text must flow naturally when spoken aloud
- total spoken words across all sections: 350-450 words
- make it engaging, surprising, and shareable
- Return ONLY valid JSON, no other text"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = ""
    for block in message.content:
        if hasattr(block, "text"):
            raw = block.text.strip()
            break

    # Clean JSON
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned invalid JSON: {e}\nRaw: {raw[:500]}")

    # Build full script from sections
    sections = data.get("sections", [])
    full_script = " ".join(s.get("script", "") for s in sections).strip()

    if not full_script or len(full_script) < 100:
        raise ValueError(f"Script too short: {len(full_script)} chars")

    total_duration = sum(s.get("duration_seconds", 30) for s in sections)

    result = {
        "topic":          topic,
        "title":          data.get("title", topic),
        "description":    data.get("description", ""),
        "tags":           data.get("tags", ["ViralVortex", "Trending", "Viral"]),
        "search_keywords": data.get("search_keywords", [topic]),
        "sections":       sections,
        "script":         full_script,
        "word_count":     len(full_script.split()),
        "total_duration": total_duration,
        "timestamp":      datetime.now().isoformat(),
    }

    os.makedirs("output", exist_ok=True)
    with open("output/step2_script.json", "w") as f:
        json.dump(result, f, indent=2)
    with open("output/script.txt", "w") as f:
        f.write(full_script)

    print(f"✅ Script: {result['word_count']} words, ~{total_duration}s")
    print(f"   Title: {result['title']}")
    print(f"   Sections: {len(sections)}")
    return result


def create_script(topic, **kwargs): return generate_script(topic, **kwargs)
def write_script(topic, **kwargs):  return generate_script(topic, **kwargs)


if __name__ == "__main__":
    result = generate_script("AI robots replacing human jobs in 2025")
    print(json.dumps(result, indent=2))
