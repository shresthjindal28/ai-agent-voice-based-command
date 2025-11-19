import os
import time
from difflib import SequenceMatcher

from .config import WAKE_WORD, ACTIVE_WINDOW_SECONDS, USER_NAME, TTS_VOICE, sarvam_client
from .audio import record_audio_block, save_wav_temp, speak, set_language_code
from .stt import transcribe_audio_with_lang


def _is_wake_detected(text: str, language_code: str) -> bool:
    t = (text or "").lower().strip()
    # Simple direct check in English
    if WAKE_WORD in t:
        return True
    # Common variants for "vani" across Indic scripts
    vani_variants = [
        "vani", "vaani", "vanee",
        "वाणी", "वानी",      # Hindi, Marathi
        "வாணி",             # Tamil
        "వాణి",             # Telugu
        "ವಾಣಿ",             # Kannada
        "વાણી",             # Gujarati
        "বাণী",             # Bengali
        "ਵਾਨੀ",             # Punjabi (Gurmukhi)
        "بانی",             # Urdu
    ]

    hello_variants = [
        "hello", "helo", "hi", "hey",
        "हेलो", "हैलो", "नमस्ते",     # Hindi
        "ஹலோ", "வணக்கம்",            # Tamil
        "హలో", "నమస్తే",             # Telugu
        "ಹಲೋ", "ನಮಸ್ಕಾರ",           # Kannada
        "હેલો", "નમસ્તે",            # Gujarati
        "হ্যালো", "নমস্কার",          # Bengali
        "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "ਹੈਲੋ",       # Punjabi
        "السلام عليكم",               # Urdu/Arabic
    ]
    # hello_variants = {"hello", "helo", "हेलो", "हैलो", "हॅलो", "ஹலோ", "హలో", "ಹಲೋ", "હેલો", "হ্যালো", "ਹੈਲੋ", "ഹലോ", "ହେଲୋ", "வணக்கம்", "നമസ്കാരം"}
    if any(v in t for v in vani_variants) and any(h in t for h in hello_variants):
        return True
    # Try fuzzy match
    try:
        ratio = SequenceMatcher(None, t, WAKE_WORD).ratio()
        if ratio >= 0.6:
            return True
    except Exception:
        pass
    # If Sarvam is available, translate the wake word to the detected language and compare
    if sarvam_client is not None and language_code:
        try:
            resp = sarvam_client.text.translate(
                input=WAKE_WORD,
                source_language_code="auto",
                target_language_code=language_code,
            )
            translated = None
            if isinstance(resp, dict):
                translated = resp.get("text") or resp.get("output")
            else:
                translated = getattr(resp, "text", None) or getattr(resp, "output", None)
            if translated:
                trans = translated.lower().strip()
                if trans in t:
                    return True
                try:
                    if SequenceMatcher(None, t, trans).ratio() >= 0.6:
                        return True
                except Exception:
                    pass
        except Exception:
            pass
    return False


def wait_for_wake() -> float:
    """Block until the wake word is detected, then return active_until timestamp."""
    print(f"Say the wake word to start: '{WAKE_WORD}'")
    while True:
        audio = record_audio_block(duration_sec=3.5)
        tmp = "./wake.wav"
        save_wav_temp(audio, tmp)
        try:
            text, lang_code = transcribe_audio_with_lang(tmp)
            print(f"Heard (wake): {text} | language_code={lang_code}")
        except Exception as e:
            print(f"Transcription error: {e}")
            text, lang_code = "", "en-IN"
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        if text and _is_wake_detected(text, lang_code):
            active_until_ts = time.time() + ACTIVE_WINDOW_SECONDS
            print("Wake word detected. Agent active for 2 minutes.")
            # Set current language for speech responses
            set_language_code(lang_code)
            speak(f"Hey {USER_NAME}, how can I help you today?")
            return active_until_ts
        else:
            print("Wake not detected. Say 'hello vani' clearly near the microphone.")