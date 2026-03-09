"""
STEP 2: Generate Video Script using Claude AI
"""

import os
import json
import anthropic


def generate_script(topic: str) -> dict:
    """Generate a full YouTube script using Claude"""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""You are a viral YouTube content writer for the channel "ViralVortex".
Write a complete YouTube video script about this trending topic: "{topic}"

The video should be 7-9 minutes when read aloud (approx 1000-1300 words of narration).

Return ONLY a valid JSON object with these exact fields:
{{
  "title": "YouTube video title (under 70 chars, clickbait but honest)",
  "hook": "First 15 seconds - shocking opening statement to grab attention",
  "narration": "Full narration script (everything the voiceover will read - no stage directions)",
  "description": "YouTube description (200 words, include timestamps, end with subscribe CTA)",
  "tags": ["tag1", "tag2", ...10 tags max],
  "full_script": "Complete script with section labels like [HOOK], [BODY], [CTA]"
}}

Rules for the script:
- Hook must be a jaw-dropping fact or question
- Body covers 3-5 key points about the topic
- Use conversational, energetic language
- End with: "Smash that subscribe button and hit the bell for daily viral content on ViralVortex!"
- Tags should mix broad and specific keywords"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text

    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    try:
        script_data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: extract JSON object
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            script_data = json.loads(match.group())
        else:
            raise ValueError("Claude did not return valid JSON")

    # Ensure all required fields exist
    required = ["title", "hook", "narration", "description", "tags", "full_script"]
    for field in required:
        if field not in script_data:
            raise ValueError(f"Missing field in script: {field}")

    return script_data
