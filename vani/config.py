import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Load environment
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_DEFAULT_VISIBILITY = os.getenv("GITHUB_DEFAULT_VISIBILITY", "private").lower()
GITHUB_DEFAULT_ORG = os.getenv("GITHUB_DEFAULT_ORG")
GITHUB_DEFAULT_PROTOCOL = os.getenv("GITHUB_DEFAULT_PROTOCOL", "ssh").lower()
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini")
USER_NAME = os.getenv("USER_NAME", "Sir")
TTS_VOICE = os.getenv("TTS_VOICE", "Samantha")
WAKE_WORD = os.getenv("WAKE_WORD", "hello vani").lower().strip()
ACTIVE_WINDOW_SECONDS = int(os.getenv("ACTIVE_WINDOW_SECONDS", "120"))
# Add terminal permission auto-approve and STT language
TERMINAL_AUTO_APPROVE = os.getenv("TERMINAL_AUTO_APPROVE", "true").lower() in {"1", "true", "yes", "y"}
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "en")

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_DURATION = float(os.getenv("BLOCK_DURATION", "7.0"))  # seconds per recorded clip for STT

if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY is not set in environment.")
    sys.exit(1)

# OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)