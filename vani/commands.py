from .intent import parse_intent
from .git_ops import perform_git_operation
from .terminal_ops import run_terminal_task
from .github_ops import handle_github_operation
from .audio import speak


def handle_text_command(text: str) -> None:
    intent = parse_intent(text)
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