#!/usr/bin/env python3
import os
import time

from vani.audio import record_audio_block, save_wav_temp, speak, set_language_code
from vani.commands import handle_text_command
from vani.wake import wait_for_wake
from vani.stt import transcribe_audio_with_lang


def wake_word_loop():
    try:
        while True:
            active_until = wait_for_wake()
            active_session_loop(active_until)
    except KeyboardInterrupt:
        print("Exiting.")


def active_session_loop(active_until_ts: float):
    while time.time() < active_until_ts:
        speak("I'm listening.")
        audio = record_audio_block(duration_sec=5.0)
        tmp = "./active.wav"
        save_wav_temp(audio, tmp)
        try:
            text, lang_code = transcribe_audio_with_lang(tmp)
            print(f"Heard: {text} | language_code={lang_code}")
        except Exception as e:
            print(f"Transcription error: {e}")
            text, lang_code = "", None
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        if not text:
            speak("Sorry, I didn't catch that.")
            continue
        # Update current language for responses
        if lang_code:
            set_language_code(lang_code)
        handle_text_command(text)


if __name__ == "__main__":
    wake_word_loop()