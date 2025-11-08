import sounddevice as sd
import soundfile as sf
import numpy as np
import os
import base64
import tempfile
from typing import Optional

from .config import SAMPLE_RATE, CHANNELS, BLOCK_DURATION, TTS_VOICE, sarvam_client, SARVAM_TTS_MODEL

# Track last detected language code for TTS responses (default English India)
CURRENT_LANGUAGE_CODE: Optional[str] = None

# Allowed Sarvam TTS language codes
_ALLOWED_TTS_LANGS = {"bn-IN","en-IN","gu-IN","hi-IN","kn-IN","ml-IN","mr-IN","od-IN","pa-IN","ta-IN","te-IN"}

def _normalize_tts_lang(code: Optional[str]) -> str:
    """Map various language codes to Sarvam TTS-allowed codes; fallback to en-IN."""
    c = (code or "").strip()
    if not c:
        return "en-IN"
    c_low = c.lower()
    # Handle common values
    if c_low in {"auto", "en", "en-us", "en-gb", "en-in"}:
        return "en-IN"
    # ISO to Sarvam mapping
    mapping = {
        "hi": "hi-IN",
        "bn": "bn-IN",
        "gu": "gu-IN",
        "kn": "kn-IN",
        "ml": "ml-IN",
        "mr": "mr-IN",
        "or": "od-IN",  
        "od": "od-IN",
        "pa": "pa-IN",
        "ta": "ta-IN",
        "te": "te-IN",
    }
    if c_low in mapping:
        return mapping[c_low]
    # If already in allowed set but different case
    if c in _ALLOWED_TTS_LANGS:
        return c
    # Try upper/lower variants
    if c.upper() in _ALLOWED_TTS_LANGS:
        return c.upper()
    if c.title() in _ALLOWED_TTS_LANGS:
        return c.title()
    # Default
    return "en-IN"

def set_language_code(lang_code: Optional[str]) -> None:
    global CURRENT_LANGUAGE_CODE
    CURRENT_LANGUAGE_CODE = lang_code

def get_language_code() -> Optional[str]:
    return CURRENT_LANGUAGE_CODE


def record_audio_block(duration_sec: float = BLOCK_DURATION) -> np.ndarray:
    """Record a single block of audio and return numpy array."""
    audio = sd.rec(int(duration_sec * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='float32')
    sd.wait()
    # Normalize to improve STT robustness
    peak = np.max(np.abs(audio)) or 1.0
    if peak > 0:
        audio = audio / peak
    return audio


def save_wav_temp(audio: np.ndarray, path: str) -> None:
    sf.write(path, audio, SAMPLE_RATE)


def speak(text: str) -> None:
    """Speak text using Sarvam TTS in the current detected language when possible.
    Falls back to macOS 'say'.
    """
    lang_raw = (CURRENT_LANGUAGE_CODE or "en-IN")
    lang = _normalize_tts_lang(lang_raw)
    # Prefer Sarvam TTS
    if sarvam_client is not None:
        try:
            final_text = text
            # If target language is non-English, translate to that language first for more natural TTS
            if not lang.lower().startswith("en"):
                try:
                    resp_tr = sarvam_client.text.translate(
                        input=text,
                        source_language_code="auto",
                        target_language_code=lang,
                    )
                    if isinstance(resp_tr, dict):
                        final_text = resp_tr.get("text") or resp_tr.get("output") or text
                    else:
                        final_text = getattr(resp_tr, "text", None) or getattr(resp_tr, "output", None) or text
                except Exception:
                    final_text = text

            resp_tts = sarvam_client.text_to_speech.convert(
                text=final_text,
                target_language_code=lang,
                model=SARVAM_TTS_MODEL,
            )
            # Try sarvamai.play if available on object
            try:
                from sarvamai.play import play as sarvam_play
                sarvam_play(resp_tts)
                return
            except Exception:
                pass
            # Fallback: decode base64 audio and write temp wav, play via afplay
            audio_b64 = None
            if isinstance(resp_tts, dict):
                audio_b64 = resp_tts.get("audio") or resp_tts.get("audio_base64") or resp_tts.get("audioBytes")
            else:
                audio_b64 = getattr(resp_tts, "audio", None) or getattr(resp_tts, "audio_base64", None) or getattr(resp_tts, "audioBytes", None)
            if audio_b64:
                try:
                    audio_bytes = base64.b64decode(audio_b64)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                        f.write(audio_bytes)
                        tmp_path = f.name
                    os.system(f"afplay '{tmp_path}'")
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                    return
                except Exception:
                    pass
        except Exception as e:
            print(f"Sarvam TTS error: {e}")
    # Final fallback: macOS say
    safe = text.replace("\"", "'")
    os.system(f"say -v {TTS_VOICE} \"{safe}\"")