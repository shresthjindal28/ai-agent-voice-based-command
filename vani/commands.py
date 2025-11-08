from .intent import parse_intent
from .git_ops import perform_git_operation
from .terminal_ops import run_terminal_task
from .github_ops import handle_github_operation
from .audio import speak, get_language_code
from .config import sarvam_client


def handle_text_command(text: str) -> None:
    # Translate to English for intent parsing if input language is non-English
    english_text = text
    lang = (get_language_code() or "en-IN").lower()
    if sarvam_client is not None and not lang.startswith("en"):
        try:
            resp = sarvam_client.text.translate(
                input=text,
                source_language_code="auto",
                target_language_code="en-IN",
            )
            if isinstance(resp, dict):
                english_text = resp.get("text") or resp.get("output") or text
            else:
                english_text = getattr(resp, "text", None) or getattr(resp, "output", None) or text
        except Exception:
            english_text = text

    intent = parse_intent(english_text)
    # Debug log for parsed intent
    try:
        print(f"Parsed intent: {intent.intent}, args: {intent.args}")
    except Exception:
        pass
    if intent.intent == "git_operation":
        perform_git_operation(intent.args)
    elif intent.intent == "terminal_task":
        run_terminal_task(intent.args)
    elif intent.intent == "github_operation":
        handle_github_operation(intent.args)
    else:
        print(f"Unrecognized or miscellaneous command: {intent.args}")
        speak("Sorry, I did not understand. Please rephrase your request.")