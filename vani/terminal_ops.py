import os

from .audio import record_audio_block, save_wav_temp, speak
from .stt import transcribe_audio
from .config import TERMINAL_AUTO_APPROVE


def request_terminal_permission() -> bool:
    if TERMINAL_AUTO_APPROVE:
        speak("Permission granted. Opening terminal.")
        return True
    speak("Permission required. Do you allow me to open a new terminal and run commands? Say yes or no.")
    print("Permission required: Do you allow me to open a new terminal and run commands? Say 'yes' or 'no'.")
    audio = record_audio_block(duration_sec=3.5)
    tmp = "./permission.wav"
    save_wav_temp(audio, tmp)
    text = transcribe_audio(tmp)
    if os.path.exists(tmp):
        os.remove(tmp)
    # Default to granting permission unless an explicit 'no' is detected
    allow = ("no" not in text)
    speak("Permission granted." if allow else "Permission denied.")
    return allow


def run_terminal_task(args: dict) -> None:
    if not request_terminal_permission():
        print("Terminal permission denied.")
        speak("Terminal permission denied.")
        return

    project_name = args.get("project_name", "voice-project")
    language = args.get("language", "python")
    framework = args.get("framework")
    command = args.get("command")

    cmds = []
    if command:
        cmds.append(command)
    else:
        if language == "python" and framework == "fastapi":
            cmds += [
                f"mkdir -p {project_name}",
                f"cd {project_name} && python3 -m venv venv && source venv/bin/activate && pip install fastapi uvicorn",
                (f"cd {project_name} && " +
                 "cat > main.py << 'PY'\nfrom fastapi import FastAPI\napp = FastAPI()\n@app.get('/')\ndef read_root():\n    return {'hello': 'world'}\nPY"),
                f"cd {project_name} && uvicorn main:app --reload"
            ]
        elif language == "javascript" and framework == "react":
            cmds += [
                f"npm create vite@latest {project_name} -- --template react",
                f"cd {project_name} && npm install && npm run dev"
            ]
        else:
            cmds.append(f"echo 'No predefined flow for {language} {framework}. Provide command.'")

    script = " ; ".join(cmds)
    # Escape for AppleScript string
    script_escaped = script.replace("\\", "\\\\").replace("\"", "\\\"")
    osa = f"osascript -e 'tell application \"Terminal\" to activate' -e 'tell application \"Terminal\" to do script \"{script_escaped}\"'"
    ret = os.system(osa)
    if ret != 0:
        print(f"AppleScript failed with status {ret}. Trying fallback.")
        os.system("open -a Terminal")
        ret2 = os.system(f"osascript -e 'tell application \"Terminal\" to do script \"{script_escaped}\"'")
        if ret2 != 0:
            print(f"Fallback AppleScript failed with status {ret2}.")
            speak("I couldn't open Terminal to run your commands. Please grant automation permissions and try again.")
            return
    print("Opened Terminal with commands:")
    for c in cmds:
        print("- ", c)
    speak("Opening Terminal and running your commands.")