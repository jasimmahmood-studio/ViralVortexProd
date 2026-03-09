"""
Step 3: Generate Voice Audio
- Primary: ElevenLabs API
- Fallback: gTTS (Google Text-to-Speech, free, no API key)
"""

import os
import json
from datetime import datetime


def generate_voice(script, **kwargs):
    """Generate audio from script text. Tries ElevenLabs first, then gTTS."""
    print(f"\n🎙️  Generating voice audio...")

    # Truncate script if too long (ElevenLabs free tier limit)
    text = script[:4000] if len(script) > 4000 else script
    print(f"📝 Script length: {len(text)} chars")

    os.makedirs("output", exist_ok=True)
    audio_path = "output/audio.mp3"

    # ── Try ElevenLabs first ─────────────────────────────────
    elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if elevenlabs_key:
        result = _try_elevenlabs(text, audio_path, elevenlabs_key)
        if result:
            return result

    # ── Fallback: gTTS ───────────────────────────────────────
    print("⚠️  Falling back to gTTS (free)...")
    result = _try_gtts(text, audio_path)
    if result:
        return result

    # ── Fallback: pyttsx3 (offline) ──────────────────────────
    print("⚠️  Falling back to pyttsx3 (offline)...")
    result = _try_pyttsx3(text, audio_path)
    if result:
        return result

    raise RuntimeError("All voice generation methods failed")


def _try_elevenlabs(text, audio_path, api_key):
    """Try ElevenLabs API."""
    try:
        import requests

        # Voice ID: Josh (energetic male voice)
        voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "TxGEqnHWrfWFTfGW9XjX")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.3,
                "use_speaker_boost": True,
            },
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()

        with open(audio_path, "wb") as f:
            f.write(response.content)

        size = os.path.getsize(audio_path)
        print(f"✅ ElevenLabs audio: {audio_path} ({size} bytes)")

        return _build_result(audio_path, "elevenlabs")

    except Exception as e:
        print(f"⚠️  ElevenLabs error: {e}")
        return None


def _try_gtts(text, audio_path):
    """Try Google Text-to-Speech (free, no API key)."""
    try:
        from gtts import gTTS

        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(audio_path)

        size = os.path.getsize(audio_path)
        print(f"✅ gTTS audio: {audio_path} ({size} bytes)")

        return _build_result(audio_path, "gtts")

    except ImportError:
        print("⚠️  gTTS not installed — run: pip install gtts")
        return None
    except Exception as e:
        print(f"⚠️  gTTS error: {e}")
        return None


def _try_pyttsx3(text, audio_path):
    """Try pyttsx3 offline TTS."""
    try:
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        engine.setProperty('volume', 1.0)

        # Save to wav first then convert
        wav_path = audio_path.replace(".mp3", ".wav")
        engine.save_to_file(text, wav_path)
        engine.runAndWait()

        # Try to convert wav to mp3 with ffmpeg
        if os.path.exists(wav_path):
            os.system(f"ffmpeg -y -i {wav_path} {audio_path} -loglevel quiet")
            if os.path.exists(audio_path):
                os.remove(wav_path)
            else:
                # Use wav as-is
                os.rename(wav_path, audio_path)

        size = os.path.getsize(audio_path)
        print(f"✅ pyttsx3 audio: {audio_path} ({size} bytes)")

        return _build_result(audio_path, "pyttsx3")

    except ImportError:
        print("⚠️  pyttsx3 not installed")
        return None
    except Exception as e:
        print(f"⚠️  pyttsx3 error: {e}")
        return None


def _build_result(audio_path, source):
    """Build standardised result dict."""
    result = {
        "audio_path": audio_path,
        "source": source,
        "file_size": os.path.getsize(audio_path),
        "timestamp": datetime.now().isoformat(),
    }
    with open("output/step3_voice.json", "w") as f:
        json.dump(result, f, indent=2)
    return result


# ── Backward-compatible aliases ───────────────────────────────
def generate_audio(script, **kwargs):
    return generate_voice(script, **kwargs)

def create_voice(script, **kwargs):
    return generate_voice(script, **kwargs)

def text_to_speech(script, **kwargs):
    return generate_voice(script, **kwargs)


if __name__ == "__main__":
    test_script = "Welcome to ViralVortex! Today we are covering the hottest trending topics on the internet. Stay tuned!"
    result = generate_voice(test_script)
    print(f"\n✅ Result: {result}")
