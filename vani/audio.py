import sounddevice as sd
import soundfile as sf
import numpy as np
import os

from .config import SAMPLE_RATE, CHANNELS, BLOCK_DURATION, TTS_VOICE


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
    """Speak text using macOS built-in TTS 'say' with configured voice."""
    safe = text.replace("\"", "'")
    os.system(f"say -v {TTS_VOICE} \"{safe}\"")