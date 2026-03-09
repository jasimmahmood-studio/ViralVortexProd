"""
STEP 3: Generate Voiceover using ElevenLabs or fallback to gTTS
"""

import os
import requests


# ElevenLabs voice IDs — change to your preferred voice
VOICE_OPTIONS = {
    "rachel":  "21m00Tcm4TlvDq8ikWAM",  # Calm, clear female
    "adam":    "pNInz6obpgDQGcFmaJgB",  # Deep male
    "josh":    "TxGEqnHWrfWFTfGW9XjX",  # Energetic male (great for viral content)
    "elli":    "MF3mGyEYCl7XYWbV9V6O",  # Upbeat female
}

DEFAULT_VOICE = "josh"  # Best for viral YouTube content


def generate_voiceover_elevenlabs(text: str, output_path: str, voice_name: str = DEFAULT_VOICE):
    """Generate voiceover using ElevenLabs (high quality)"""
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not set")

    voice_id = VOICE_OPTIONS.get(voice_name, VOICE_OPTIONS[DEFAULT_VOICE])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "Accept": "audio/mpeg",
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    body = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.80,
            "style": 0.35,
            "use_speaker_boost": True
        }
    }

    res = requests.post(url, json=body, headers=headers, timeout=120)
    res.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(res.content)

    print(f"   ElevenLabs voiceover saved: {output_path}")


def generate_voiceover_gtts(text: str, output_path: str):
    """Fallback: free Google TTS via gTTS library"""
    from gtts import gTTS
    tts = gTTS(text=text, lang='en', slow=False)
    # gTTS saves as mp3
    mp3_path = output_path.replace(".mp3", "_gtts.mp3")
    tts.save(mp3_path)

    # Convert to proper mp3 with ffmpeg for consistent format
    import subprocess
    subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path,
        "-codec:a", "libmp3lame", "-q:a", "2",
        output_path
    ], check=True, capture_output=True)

    import os
    os.remove(mp3_path)
    print(f"   gTTS fallback voiceover saved: {output_path}")


def generate_voiceover(text: str, output_path: str):
    """Main entry: try ElevenLabs first, fallback to gTTS"""
    # Truncate if too long (ElevenLabs free tier limit ~2500 chars per request)
    if len(text) > 4000:
        text = text[:4000] + "... Smash that subscribe button for daily viral content on ViralVortex!"

    try:
        generate_voiceover_elevenlabs(text, output_path)
    except Exception as e:
        print(f"   ElevenLabs failed ({e}), falling back to gTTS...")
        generate_voiceover_gtts(text, output_path)
