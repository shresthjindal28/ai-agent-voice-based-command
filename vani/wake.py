import os
import time
from difflib import SequenceMatcher

from .config import WAKE_WORD, ACTIVE_WINDOW_SECONDS, USER_NAME, TTS_VOICE
from .audio import record_audio_block, save_wav_temp
from .stt import transcribe_audio


def _is_wake_detected(text: str) -> bool:
    t = text.lower()
    if WAKE_WORD in t:
        return True
    variants = ["vani", "vaani", "vanni", "wani", "bani", "bunny", "vanee"]
    if "hello" in t and any(v in t for v in variants):
        return True
    try:
        ratio = SequenceMatcher(None, t, WAKE_WORD).ratio()
        if ratio >= 0.6:
            return True
    except Exception:
        pass
    return False


def _say(text: str) -> None:
    """Speak a short response using macOS built-in TTS 'say'."""
    # Use macOS 'say' with selected voice; escape quotes
    safe = text.replace("\"", "'")
    os.system(f"say -v {TTS_VOICE} \"{safe}\"")


def wait_for_wake() -> float:
    """Block until the wake word is detected, then return active_until timestamp."""
    print(f"Say the wake word to start: '{WAKE_WORD}'")
    while True:
        audio = record_audio_block(duration_sec=3.5)
        tmp = "./wake.wav"
        save_wav_temp(audio, tmp)
        try:
            text = transcribe_audio(tmp)
            print(f"Heard (wake): {text}")
        except Exception as e:
            print(f"Transcription error: {e}")
            text = ""
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        if text and _is_wake_detected(text):
            active_until_ts = time.time() + ACTIVE_WINDOW_SECONDS
            print("Wake word detected. Agent active for 2 minutes.")
            _say(f"Hey {USER_NAME}, how can I help you today?")
            return active_until_ts
        else:
            print("Wake not detected. Say 'hello vani' clearly near the microphone.")