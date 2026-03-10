"""
Step 3: Generate Voice Audio — gTTS (free, no API key)
Accepts output_path to save each video's audio separately
"""

import os
import json
from datetime import datetime


def generate_voice(script, output_path=None, **kwargs):
    print(f"\n🎙️  Generating voice audio...")

    if not script or not isinstance(script, str):
        raise ValueError(f"Script must be non-empty string, got: {type(script)}")

    text = script[:4000]
    audio_path = output_path or "output/audio.mp3"
    os.makedirs(os.path.dirname(audio_path) if os.path.dirname(audio_path) else "output", exist_ok=True)

    print(f"📝 Script: {len(text)} chars → {audio_path}")

    result = _try_gtts(text, audio_path)
    if result:
        return result

    result = _try_pyttsx3(text, audio_path)
    if result:
        return result

    raise RuntimeError("All voice generation methods failed")


def _try_gtts(text, audio_path):
    try:
        from gtts import gTTS
        print("🎤 Generating with gTTS...")
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(audio_path)
        size = os.path.getsize(audio_path)
        print(f"✅ gTTS: {audio_path} ({size:,} bytes)")
        return _build_result(audio_path, "gtts")
    except ImportError:
        os.system("pip install gtts -q")
        try:
            from gtts import gTTS
            gTTS(text=text, lang='en').save(audio_path)
            return _build_result(audio_path, "gtts")
        except Exception as e:
            print(f"⚠️  gTTS failed: {e}")
            return None
    except Exception as e:
        print(f"⚠️  gTTS error: {e}")
        return None


def _try_pyttsx3(text, audio_path):
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        wav_path = audio_path.replace(".mp3", ".wav")
        engine.save_to_file(text, wav_path)
        engine.runAndWait()
        if os.path.exists(wav_path):
            os.system(f"ffmpeg -y -i {wav_path} {audio_path} -loglevel quiet")
            if os.path.exists(audio_path):
                os.remove(wav_path)
            else:
                os.rename(wav_path, audio_path)
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


def generate_audio(script, **kwargs):  return generate_voice(script, **kwargs)
def create_voice(script, **kwargs):    return generate_voice(script, **kwargs)
def text_to_speech(script, **kwargs):  return generate_voice(script, **kwargs)


if __name__ == "__main__":
    result = generate_voice("Welcome to ViralVortex! Testing audio generation.")
    print(f"✅ Done: {result}")
