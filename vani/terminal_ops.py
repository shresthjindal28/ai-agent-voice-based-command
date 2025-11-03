import os
import time

from .audio import record_audio_block, save_wav_temp, speak
from .stt import transcribe_audio
from .config import TERMINAL_AUTO_APPROVE

# Simple debounce to prevent multiple Terminal openings in quick succession
_LAST_RUN_AT = 0.0
_DEBOUNCE_SECONDS = 5.0


def request_terminal_permission() -> bool:
    if TERMINAL_AUTO_APPROVE:
        # Auto-approve without speaking
        return True
    # Ask for permission without verbose errors
    print("Permission required: Do you allow me to open a new terminal and run commands? Say 'yes' or 'no'.")
    tmp = "./permission.wav"
    try:
        audio = record_audio_block(duration_sec=3.5)
        save_wav_temp(audio, tmp)
        try:
            text = transcribe_audio(tmp)
        except Exception:
            text = ""
    except Exception as e:
        # If audio/STT fails, default to allowing to avoid crashes
        print(f"Permission capture failed, proceeding by default: {e}")
        text = "yes"
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    allow = ("no" not in text)
    return allow


def _ask_and_listen(prompt: str, duration: float = 4.0) -> str:
    # Speak prompt to collect user choice
    speak(prompt)
    audio = record_audio_block(duration_sec=duration)
    tmp = "./clarify.wav"
    save_wav_temp(audio, tmp)
    try:
        text = transcribe_audio(tmp)
    except Exception:
        text = ""
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    print(f"User said: {text}")
    return text


def _resolve_vite_template(args: dict) -> tuple[str, str]:
    """Return (template, project_name). Ask user if missing.
    Maps framework+variant to Vite templates: react, react-ts, vue, vue-ts, svelte, svelte-ts, vanilla, vanilla-ts.
    """
    framework = (args.get("framework") or "").lower().strip()
    language = (args.get("language") or "").lower().strip()
    project_name = (args.get("project_name") or "").strip() or "voice-project"

    # Determine framework
    if framework not in {"react", "vue", "svelte", "vanilla"}:
        said = _ask_and_listen(
            "Which framework should I use: React, Vue, Svelte, or Vanilla?"
        )
        if "react" in said:
            framework = "react"
        elif "vue" in said:
            framework = "vue"
        elif "svelte" in said:
            framework = "svelte"
        elif "vanilla" in said or "plain" in said or "basic" in said:
            framework = "vanilla"
        else:
            # Default to react if unclear
            framework = "react"

    # Determine variant JS or TS
    variant = "js"
    said2 = None
    if not ("ts" in language or "typescript" in language or "js" in language or "javascript" in language):
        said2 = _ask_and_listen("JavaScript or TypeScript?")
    else:
        said2 = language
    if "ts" in said2 or "typescript" in said2:
        variant = "ts"
    else:
        variant = "js"

    # Confirm/ask project name if not set explicitly
    if not args.get("project_name"):
        said3 = _ask_and_listen("What should be the project name?")
        if said3 and len(said3) >= 2:
            # Sanitize simple name (remove spaces)
            project_name = "-".join(
                [p for p in said3.strip().split() if p]
            ).lower()

    template = framework if variant == "js" else f"{framework}-ts"
    return template, project_name


def _build_vite_cmds(template: str, project_name: str) -> list[str]:
    return [
        "cd ~/Desktop",
        f"npm create vite@latest {project_name} -- --template {template}",
        f"cd {project_name} && npm install",
        f"cd {project_name} && npm run dev",
    ]


def _build_next_cmds(project_name: str) -> list[str]:
    return [
        "cd ~/Desktop",
        f"npm create next-app@latest {project_name}",
        f"cd {project_name} && npm run dev",
    ]


def _create_program_file(language: str, file_base_name: str, description: str = "") -> None:
    """Create a single-source program file on the Desktop based on language and a short voice description."""
    # Determine language and file extension
    lang = (language or "").lower().strip()
    ext_map = {
        "javascript": "js",
        "js": "js",
        "typescript": "ts",
        "ts": "ts",
        "python": "py",
        "py": "py",
    }
    ext = ext_map.get(lang)
    if not ext:
        # Ask for language if unknown
        said = _ask_and_listen("Which language should I use: JavaScript or Python?", duration=4.5).lower()
        if "py" in said or "python" in said:
            ext = "py"
            lang = "python"
        else:
            ext = "js"
            lang = "javascript"
    # Use provided description if available; otherwise ask
    desc = (description or "").lower().strip()
    if not desc:
        desc = _ask_and_listen(
            "Briefly describe the program. For example: 'print numbers 1 to 10'.",
            duration=5.5,
        ).lower()

    # Generate code content
    code = ""
    if lang in {"javascript", "js", "typescript", "ts"}:
        if ("1 to 10" in desc) or ("one to ten" in desc) or ("1-10" in desc) or ("print" in desc and "10" in desc):
            code = "for (let i = 1; i <= 10; i++) {\n  console.log(i);\n}\n"
        else:
            code = "console.log('Hello World');\n"
    elif lang in {"python", "py"}:
        if ("1 to 10" in desc) or ("one to ten" in desc) or ("1-10" in desc) or ("print" in desc and "10" in desc):
            code = "for i in range(1, 11):\n    print(i)\n"
        else:
            code = "print('Hello World')\n"
    else:
        code = "// Language not supported yet\n"

    # Ensure code is not empty
    if not code.strip():
        if ext in {"js", "ts"}:
            code = "console.log('Hello World');\n"
        elif ext == "py":
            code = "print('Hello World')\n"
        else:
            code = "Hello World\n"

    # Sanitize file base name
    base = file_base_name.strip() or "program"
    safe_base = "-".join([p for p in base.split() if p])
    desktop = os.path.expanduser("~/Desktop")
    ext = ext or "txt"
    path = os.path.join(desktop, f"{safe_base}.{ext}")

    # Write file
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"Created program file: {path}")
        speak(f"Created the program file on your desktop: {safe_base}.{ext}")
    except Exception as e:
        print(f"Failed to create file: {e}")
        speak("Sorry, I could not create the file.")


def run_terminal_task(args: dict) -> None:
    global _LAST_RUN_AT
    # Debounce: skip if called again within a short interval
    now = time.time()
    if (now - _LAST_RUN_AT) < _DEBOUNCE_SECONDS:
        print("Skipping duplicate terminal task (debounced).")
        return

    if not request_terminal_permission():
        print("Terminal permission denied.")
        return

    project_name = args.get("project_name", "voice-project")
    language = args.get("language", "python")
    framework = args.get("framework")
    command = args.get("command")

    cmds = []
    if command:
        raw = (command or "").lower().strip()
        handled = False
        builder_keywords = {"vite", "next", "create-next-app", "next-app"}
        # If user says "run", run the created single file instead of prompting for frameworks
        if ("run" in raw) and not any(k in raw for k in builder_keywords):
            # Determine target file on Desktop
            lang = (language or "").lower().strip()
            ext_map = {"javascript": "js", "js": "js", "typescript": "ts", "ts": "ts", "python": "py", "py": "py"}
            ext = ext_map.get(lang) or "js"
            base = project_name.strip() or "program"
            safe_base = "-".join([p for p in base.split() if p])
            desktop = os.path.expanduser("~/Desktop")
            file = f"{safe_base}.{ext}"
            path = os.path.join(desktop, file)
            # If the file doesn't exist yet, create it with a simple default
            if not os.path.exists(path):
                desc_arg = (args.get("description") or args.get("text") or args.get("problem") or args.get("prompt") or args.get("utterance") or "").strip()
                _create_program_file(language, project_name, desc_arg)
            # Build run commands
            cmds += ["cd ~/Desktop"]
            if lang in {"javascript", "js", "typescript", "ts"}:
                # For TS, assume a simple Node run; advanced TS execution would need ts-node/tsx
                cmds += [f"node {file}"]
            elif lang in {"python", "py"}:
                cmds += [f"python3 {file}"]
            else:
                cmds += [f"echo 'Cannot run {file}: unsupported language'"]
            handled = True
        # Create single-file program on Desktop when user indicates simple code generation
        simple_keywords = {"create", "write", "generate", "make", "program", "script", "code", "print"}
        if any(k in raw for k in simple_keywords) and not any(k in raw for k in builder_keywords):
            desc_arg = args.get("description") or args.get("text") or args.get("problem") or args.get("prompt") or args.get("utterance") or raw
            _create_program_file(language, project_name, desc_arg)
            return
        # Normalize common requests only if not already handled
        if not handled:
            if "vite" in raw:
                # Try to infer framework & variant from raw
                fw = None
                if "react" in raw:
                    fw = "react"
                elif "vue" in raw:
                    fw = "vue"
                elif "svelte" in raw:
                    fw = "svelte"
                elif "vanilla" in raw or "plain" in raw:
                    fw = "vanilla"
                var = "ts" if ("ts" in raw or "typescript" in raw) else "js"
                template, final_name = _resolve_vite_template({
                    "framework": fw,
                    "language": var,
                    "project_name": project_name,
                })
                cmds += _build_vite_cmds(template, final_name)
            elif "next" in raw or "create-next-app" in raw:
                name = project_name
                # If user stated a name after next keywords, try to pick it up (best-effort)
                tokens = raw.split()
                for i, t in enumerate(tokens):
                    if t in {"next", "create-next-app"} and i + 1 < len(tokens):
                        cand = tokens[i + 1]
                        if cand.isalnum() or "-" in cand:
                            name = cand
                            break
                cmds += _build_next_cmds(name)
            else:
                # Ask whether they want Vite or Next
                choice = _ask_and_listen("Do you want a Vite app or a Next.js app? Say Vite or Next.")
                if "next" in choice:
                    cmds += _build_next_cmds(project_name)
                else:
                    template, final_name = _resolve_vite_template({
                        "framework": framework,
                        "language": language,
                        "project_name": project_name,
                    })
                    cmds += _build_vite_cmds(template, final_name)
    else:
        # Vite app creation flow for JS frameworks with interactive clarification
        if language in {"javascript", "js"} or (framework in {"react", "vue", "svelte", "vanilla"}):
            template, final_name = _resolve_vite_template({
                "framework": framework,
                "language": language,
                "project_name": project_name,
            })
            cmds += _build_vite_cmds(template, final_name)
        elif language == "python" and framework == "fastapi":
            cmds += [
                f"mkdir -p {project_name}",
                f"cd {project_name} && python3 -m venv venv && source venv/bin/activate && pip install fastapi uvicorn",
                (f"cd {project_name} && " +
                 "cat > main.py << 'PY'\nfrom fastapi import FastAPI\napp = FastAPI()\n@app.get('/')\ndef read_root():\n    return {'hello': 'world'}\nPY"),
                f"cd {project_name} && uvicorn main:app --reload"
            ]
        else:
            cmds.append(f"echo 'No predefined flow for {language} {framework}. Provide command.'")

    script = " ; ".join(cmds)
    # Escape for AppleScript string
    script_escaped = script.replace("\\", "\\\\").replace("\"", "\\\"")
    # Reuse existing window if Terminal is open; otherwise create one
    osa = (
        "osascript "
        "-e 'tell application \"Terminal\"' "
        f"-e 'set cmd to \"{script_escaped}\"' "
        "-e 'if (count of windows) is 0 then' "
        "-e 'do script cmd' "
        "-e 'else' "
        "-e 'do script cmd in front window' "
        "-e 'end if' "
        "-e 'activate' "
        "-e 'end tell'"
    )
    ret = os.system(osa)
    if ret != 0:
        print(f"AppleScript failed with status {ret}.")
        return
    print("Opened Terminal with commands:")
    for c in cmds:
        print("- ", c)
    # Update debounce timestamp
    _LAST_RUN_AT = now
    # Do not speak here to avoid unnecessary chatter