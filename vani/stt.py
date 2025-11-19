import os
import json
from typing import Tuple, Optional

from .config import sarvam_client, SARVAM_MODEL, SARVAM_LANGUAGE_CODE, OPENAI_API_KEY, WHISPER_MODEL, STT_LANGUAGE


def _ascii_ratio(s: str) -> float:
    if not s:
        return 0.0
    total = len(s)
    ascii_count = sum(1 for ch in s if ord(ch) < 128 and ch.isprintable())
    return ascii_count / max(total, 1)


def _extract_text_and_lang(resp) -> Tuple[str, Optional[str]]:
    # Try multiple possible shapes from Sarvam / Whisper
    text = None
    lang = None
    if isinstance(resp, dict):
        text = resp.get("text") or resp.get("transcript") or resp.get("output") or resp.get("data", {}).get("text")
        lang = resp.get("language_code") or resp.get("language") or resp.get("detected_language_code")
    else:
        text = getattr(resp, "text", None) or getattr(resp, "transcript", None) or getattr(resp, "output", None)
        lang = getattr(resp, "language_code", None) or getattr(resp, "language", None) or getattr(resp, "detected_language_code", None)
    text = (text or "").strip()
    # Avoid propagating invalid values like 'auto' to TTS consumers
    fallback_lang = STT_LANGUAGE if (STT_LANGUAGE and STT_LANGUAGE.lower() != "auto") else "en-IN"
    lang = (lang or fallback_lang or "en-IN")
    return text, lang


def transcribe_audio_with_lang(file_path: str) -> Tuple[str, Optional[str]]:
    """Transcribe audio and return text + detected language code.
    Prioritize Sarvam; fall back to OpenAI Whisper.
    """
    # Prefer Sarvam AI
    if sarvam_client is not None:
        try:
            with open(file_path, "rb") as audio_file:
                kwargs = {"file": audio_file, "model": SARVAM_MODEL}
                if SARVAM_LANGUAGE_CODE and SARVAM_LANGUAGE_CODE.lower() != "auto":
                    kwargs["language_code"] = SARVAM_LANGUAGE_CODE
                resp = sarvam_client.speech_to_text.transcribe(**kwargs)
            text, lang = _extract_text_and_lang(resp)
            if text:
                if (
                    STT_LANGUAGE and STT_LANGUAGE.lower() == "auto" and
                    lang and isinstance(lang, str) and not lang.lower().startswith("en")
                ):
                    try:
                        with open(file_path, "rb") as audio_file2:
                            resp_en = sarvam_client.speech_to_text.transcribe(
                                file=audio_file2,
                                model=SARVAM_MODEL,
                                language_code="en-IN",
                            )
                        t_en, l_en = _extract_text_and_lang(resp_en)
                        if t_en and _ascii_ratio(t_en) >= 0.65:
                            return t_en, "en-IN"
                    except Exception:
                        pass
                return text, lang
        except Exception as e:
            print(f"Sarvam STT failed: {e}")
    # Fallback: Whisper via local or OpenAI SDK
    try:
        import whisper
        model_name = WHISPER_MODEL or "base"
        model = whisper.load_model(model_name)
        result = model.transcribe(file_path, language=STT_LANGUAGE or None)
        text = result.get("text", "").strip()
        # Whisper language detection is separate; we may not have a code, so keep previous
        lang = result.get("language") or (STT_LANGUAGE if (STT_LANGUAGE and STT_LANGUAGE.lower() != "auto") else "en-IN")
        return text, lang
    except Exception as e:
        print(f"Local Whisper failed: {e}")
    # As last resort, try OpenAI if key exists
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI()
            with open(file_path, "rb") as f:
                resp = client.audio.transcriptions.create(model="whisper-1", file=f)
            if isinstance(resp, dict):
                text = resp.get("text", "").strip()
            else:
                text = getattr(resp, "text", "")
            return text, (STT_LANGUAGE if (STT_LANGUAGE and STT_LANGUAGE.lower() != "auto") else "en-IN")
        except Exception as e:
            print(f"OpenAI Whisper API failed: {e}")
    return "", (STT_LANGUAGE if (STT_LANGUAGE and STT_LANGUAGE.lower() != "auto") else "en-IN")


# Preserve original API

def transcribe_audio(file_path: str) -> str:
    text, _ = transcribe_audio_with_lang(file_path)
    return text