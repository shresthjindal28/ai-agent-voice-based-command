#!/usr/bin/env python3
import os
import time
import sys

from vani.config import BLOCK_DURATION
from vani.audio import record_audio_block, save_wav_temp, speak
from vani.commands import handle_text_command
from vani.wake import wait_for_wake
from vani.stt import transcribe_audio

active_until_ts = 0.0


def wake_word_loop():
    global active_until_ts
    active_until_ts = wait_for_wake()
    return


def active_session_loop() -> None:
    print("Listening for commands. Say your git or terminal instructions.")
    speak("I'm listening for your commands.")
    while time.time() < active_until_ts:
        try:
            audio = record_audio_block(duration_sec=BLOCK_DURATION)
        except KeyboardInterrupt:
            print("Interrupted. Stopping session.")
            speak("Stopping.")
            return
        tmp = "./cmd.wav"
        save_wav_temp(audio, tmp)
        try:
            text = transcribe_audio(tmp)
            if text:
                print(f"Heard: {text}")
                # If user requests to end the session, stop listening immediately
                exit_words = ("exit", "quit", "bye", "goodbye", "stop", "sleep", "cancel", "go to sleep", "rest", "bye bye")
                if any(w in text for w in exit_words):
                    print("Exit command detected. Ending session now.")
                    speak("Okay, going to sleep. Say the wake word when you need me.")
                    return
                handle_text_command(text)
            else:
                print("No speech detected in this block.")
        except Exception as e:
            print(f"Transcription/handling error: {e}")
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set in environment.")
        sys.exit(1)
    try:
        while True:
            wake_word_loop()
            active_session_loop()
            print("Session ended. Say wake word again to reactivate.")
            speak("Session ended. Say the wake word again when you're ready.")
    except KeyboardInterrupt:
        print("Exiting.")
        speak("Goodbye.")


if __name__ == "__main__":
    main()