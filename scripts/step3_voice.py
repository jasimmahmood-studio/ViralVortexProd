"""
Step 3: Generate Voice Audio
Using gTTS (free) — ElevenLabs disabled until valid key is provided
"""

import os
import json
from datetime import datetime


def generate_voice(script, **kwargs):
    """Generate audio from script text using gTTS."""
    print(f"\n🎙️  Generating voice audio...")

    if not script or not isinstance(script, str):
        raise ValueError(f"Script must be a non-empty string, got: {type(script)}")

    text = script[:4000]
    print(f"📝 Script: {len(text)} chars")

    os.makedirs("output", exist_ok=True)
    audio_path = "output/audio.mp3"

    # ── gTTS (free, no API key needed) ───────────────────────
    result = _try_gtts(text, audio_path)
    if result:
        return result

    # ── pyttsx3 last resort ──────────────────────────────────
    result = _try_pyttsx3(text, audio_path)
    if result:
        return result

    raise RuntimeError("All voice generation methods failed")


def _try_gtts(text, audio_path):
    try:
        from gtts import gTTS
        print("🎤 Generating with gTTS (free)...")
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(audio_path)
        size = os.path.getsize(audio_path)
        print(f"✅ gTTS audio: {audio_path} ({size:,} bytes)")
        return _build_result(audio_path, "gtts")
    except ImportError:
        print("⚠️  gTTS not found, installing...")
        os.system("pip install gtts -q")
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(audio_path)
            return _build_result(audio_path, "gtts")
        except Exception as e:
            print(f"⚠️  gTTS failed after install: {e}")
            return None
    except Exception as e:
        print(f"⚠️  gTTS error: {e}")
        return None


def _try_pyttsx3(text, audio_path):
    try:
        import pyttsx3
        print("🎤 Generating with pyttsx3 (offline)...")
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        wav_path = audio_path.replace(".mp3", ".wav")
        engine.save_to_file(text, wav_path)
        engine.runAndWait()
        if os.path.exists(wav_path):
            ret = os.system(f"ffmpeg -y -i {wav_path} {audio_path} -loglevel quiet")
            if ret == 0 and os.path.exists(audio_path):
                os.remove(wav_path)
            else:
                os.rename(wav_path, audio_path)
        size = os.path.getsize(audio_path)
        print(f"✅ pyttsx3 audio: {audio_path} ({size:,} bytes)")
        return _build_result(audio_path, "pyttsx3")
    except Exception as e:
        print(f"⚠️  pyttsx3 error: {e}")
        return None


def _build_result(audio_path, source):
    result = {
        "audio_path": audio_path,
        "source":     source,
        "file_size":  os.path.getsize(audio_path),
        "timestamp":  datetime.now().isoformat(),
    }
    with open("output/step3_voice.json", "w") as f:
        json.dump(result, f, indent=2)
    return result


# Aliases
def generate_audio(script, **kwargs):  return generate_voice(script, **kwargs)
def create_voice(script, **kwargs):    return generate_voice(script, **kwargs)
def text_to_speech(script, **kwargs):  return generate_voice(script, **kwargs)


if __name__ == "__main__":
    test = "Welcome to ViralVortex! Today we cover the hottest trending topics. Stay tuned!"
    result = generate_voice(test)
    print(f"\n✅ Done: {result}")
