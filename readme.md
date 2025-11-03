# Vani Agent – About README

![VS Code](https://img.shields.io/badge/VS%20Code-Extension-007ACC.svg) ![Python](https://img.shields.io/badge/Python-3.x-3776AB.svg) ![Voice](https://img.shields.io/badge/Voice-Assistant-ff69b4.svg) ![GitHub API](https://img.shields.io/badge/GitHub-API-181717.svg) ![OpenAI](https://img.shields.io/badge/OpenAI-Whisper%20%2B%20Chat-00a67d.svg)

A voice-driven developer assistant packaged as a VS Code extension plus a Python agent. It listens for a wake word, transcribes your speech, classifies the intent, and executes developer tasks (Git operations, GitHub actions, and Terminal scaffolding).

> Tip: Say “hello vani” to wake the agent, then speak natural commands like “create a React TypeScript app” or “push my repo”.

---

## Overview & Architecture

```
[Mic] → record_audio_block → [WAV] → Whisper STT → text
                         → Intent (LLM) → {intent,args}
                         → Ops: git | github | terminal
VS Code extension → spawn agent (per folder) → Output/Terminal logs
```

- VS Code Extension (JavaScript): commands + sidebar to start/stop agent per workspace; multi-root support; auto pip install when missing.
- Python Agent: audio I/O + STT (Whisper) + intent parsing (Chat) + ops runners (git, GitHub REST, macOS Terminal).
- Optional FastAPI service: HTTP endpoints for programmatic control.

---

## Languages & Runtime

| Component          | Language/Runtime                           |
|--------------------|--------------------------------------------|
| VS Code Extension  | JavaScript/Node.js (extension.js)          |
| Python Agent/API   | Python 3 (agent.py, vani/*, api.py)        |
| TTS & Terminal     | macOS say + AppleScript (osascript)        |

## Tools & Libraries

| Area            | Tech                                   | Purpose                                  |
|-----------------|----------------------------------------|------------------------------------------|
| STT/LLM         | openai (Whisper + Chat)                | Speech-to-text, intent parsing           |
| Config          | python-dotenv                          | .env loading                             |
| Audio           | sounddevice, soundfile, numpy          | Mic capture, WAV write, normalization    |
| Git local       | gitpython                              | Git status/add/commit/push/etc.          |
| GitHub remote   | requests (REST API)                    | Repos, PRs, issues                       |
| API             | fastapi, pydantic                      | Optional HTTP control layer              |
| VS Code         | Extension API                          | Commands, Output, Terminal, Tree View    |

## Extension Features

| Command                           | What it does                                                        |
|-----------------------------------|---------------------------------------------------------------------|
| Vani: Run Agent                   | Starts agent for selected workspace; logs to Output or Terminal     |
| Vani: Stop Agent                  | Stops agent process for selected folder                             |
| Vani: Run Agent in All Folders    | Starts an agent in each workspace root                              |

| Setting (vaniAgent.*) | Default     | Description                                                                 |
|-----------------------|-------------|-----------------------------------------------------------------------------|
| pythonPath            | python3     | Interpreter to run agent                                                    |
| agentPath             | agent.py    | Script path relative to workspace root                                      |
| openaiKey             | (empty)     | Inject OPENAI_API_KEY (recommended: set via OS/.env for security)          |
| runInTerminal         | false       | true → run in Terminal; false → stream logs in Output panel                |
| autoInstallDeps       | true        | Auto install soundfile/sounddevice/numpy via pip if missing                |

## Agent Intents & Actions

| Intent            | Examples                                     | Actions Performed                                                      |
|-------------------|----------------------------------------------|------------------------------------------------------------------------|
| git_operation     | “status”, “commit ‘msg’”, “push”              | Local git via gitpython: status/add/commit/push/branch/checkout/init   |
| github_operation  | “create private repo demo and link/push”      | GitHub API: create/delete, link remote (ssh/https), push, PRs, issues  |
| terminal_task     | “create React TS app”, “write python program” | AppleScript: run Vite/Next scaffolding; create/run simple JS/Py files  |
| misc              | Unclear or unsupported                        | Friendly guidance; asks clarifying questions                           |

---

## Core Algorithms (Detailed)

1) Wake Word Detection (vani/wake.py)
- Exact substring match for WAKE_WORD.
- Variant list to catch common pronunciations (e.g., “vani”, “vaani”, “wani”, …).
- Fuzzy match using difflib.SequenceMatcher; considers wake if ratio ≥ 0.6.

Pseudo:
```
t = text.lower()
if WAKE_WORD in t: wake
elif any(v in t for v in variants): wake
elif SequenceMatcher(None, t, WAKE_WORD).ratio() >= 0.6: wake
else: no wake
```

2) Audio Normalization (vani/audio.py)
- Record float32 samples; compute peak amplitude; divide by peak to normalize to unit range for robust STT.

3) Intent Parsing & JSON Extraction (vani/intent.py)
- System prompt constrains intents/args; temperature=0.
- Removes optional ```json fences; finds outermost {…}; loads JSON; falls back to misc on failure.

4) Dependency Assurance (extension.js)
- Tries import soundfile/sounddevice/numpy via a Python -c check.
- If missing and requirements.txt exists → pip install (Terminal or non-interactive) before spawning agent.

5) Python Path Resolution (extension.js)
- If pythonPath is unset/generic, prefers workspace venvs (.venv/venv) → /usr/local/bin/python3 → python3.
- If absolute path configured and exists, uses it; else uses configured value as-is.

6) Terminal Task Debounce & Permission (vani/terminal_ops.py)
- Debounce window 5s to avoid repeated openings.
- Permission flow: asks “yes/no” via TTS+STT unless TERMINAL_AUTO_APPROVE=true; defaults to allow if audio fails.

7) Git Push & Remote Handling (vani/git_ops.py, vani/github_ops.py)
- Detect current branch or create “main” if detached; push with upstream.
- For https remotes with token: temporarily set origin to tokened URL, push, restore original.

---

## Configuration

| Environment Variable         | Default         | Purpose                                                    |
|------------------------------|-----------------|------------------------------------------------------------|
| OPENAI_API_KEY               | —               | Required for Whisper/GPT                                  |
| GITHUB_TOKEN                 | —               | Required for GitHub API                                   |
| GITHUB_DEFAULT_VISIBILITY    | private         | Default repo visibility                                   |
| GITHUB_DEFAULT_ORG           | —               | Default org for repo creation                             |
| GITHUB_DEFAULT_PROTOCOL      | ssh             | ssh or https for linking remotes                          |
| WHISPER_MODEL                | whisper-1       | STT model                                                 |
| GPT_MODEL                    | gpt-4o-mini     | Intent parsing model                                      |
| USER_NAME                    | Sir             | Greeting name                                             |
| TTS_VOICE                    | Samantha        | macOS ‘say’ voice                                         |
| WAKE_WORD                    | hello vani      | Wake phrase                                               |
| ACTIVE_WINDOW_SECONDS        | 120             | Active session duration                                   |
| TERMINAL_AUTO_APPROVE        | true            | Auto-approve terminal opening                             |
| STT_LANGUAGE                 | en              | Whisper language                                          |
| BLOCK_DURATION               | 7.0             | Seconds per recorded clip                                 |

---

## Usage

- In VS Code, run “Vani: Run Agent”. Say “hello vani”, then:
  - “status of git repo”
  - “create a React TypeScript app”
  - “create a private repo named demo and push my local code”
  - “print numbers 1 to 10 in python and run it”

Optional API: run `uvicorn vani.api:app --reload` and call /command, /git, /terminal, /github/* endpoints.

## Security

- Keep secrets out of source control (.env preferred). Use OS env or secret managers.
- The extension can inject OPENAI_API_KEY, but OS-level env is recommended.
- GitHub token used only for REST and optional one-time https push; original remote restored afterward.

## Limitations

- macOS-specific (say, osascript). For other OSes, swap TTS/terminal automation.
- Requires OpenAI credentials for STT/LLM.
- Simple program generation is heuristic; extend for complex tasks.