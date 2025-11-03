from .config import client, WHISPER_MODEL, STT_LANGUAGE


def transcribe_audio(file_path: str) -> str:
    with open(file_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=f,
            language=STT_LANGUAGE,
            temperature=0,
            prompt="Commands for git, GitHub, and terminal tasks"
        )
    text = transcript.text.strip().lower()
    return text