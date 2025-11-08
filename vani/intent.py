from dataclasses import dataclass
import json
import re

from .config import client, GPT_MODEL


@dataclass
class ParsedIntent:
    intent: str
    args: dict


def _extract_json(content: str) -> str:
    """Extract JSON object from content, removing code fences if present."""
    s = content.strip()
    # Remove triple backtick fences like ```json ... ```
    if s.startswith("```"):
        # Strip leading fence
        s = re.sub(r"^```[a-zA-Z]*\n", "", s)
        # Strip trailing fence
        s = re.sub(r"\n```$", "", s)
    # Find first { and last }
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start:end+1]
    return s


def _heuristic_intent(text: str) -> ParsedIntent:
    """Best-effort local parser when LLM is unavailable."""
    t = (text or "").lower()
    # Git operations
    if any(k in t for k in ["git status", "status"]):
        return ParsedIntent(intent="git_operation", args={"operation": "status"})
    if "git add" in t or "stage" in t:
        return ParsedIntent(intent="git_operation", args={"operation": "add"})
    if "commit" in t:
        # Extract message in quotes
        m = re.search(r"commit( with)?( message)?\s+\"([^\"]+)\"", text, re.IGNORECASE)
        msg = m.group(3) if m else "voice commit"
        return ParsedIntent(intent="git_operation", args={"operation": "commit", "commit_message": msg})
    if "push" in t:
        return ParsedIntent(intent="git_operation", args={"operation": "push"})
    if "pull" in t:
        return ParsedIntent(intent="git_operation", args={"operation": "pull"})
    if "checkout" in t or "switch" in t:
        m = re.search(r"(checkout|switch)\s+(to\s+)?([\w\-/]+)", t)
        branch = m.group(3) if m else None
        return ParsedIntent(intent="git_operation", args={"operation": "checkout", "branch_name": branch})
    if "create branch" in t or "new branch" in t or "branch" in t:
        m = re.search(r"branch\s+(named\s+)?([\w\-/]+)", t)
        branch = m.group(2) if m else None
        return ParsedIntent(intent="git_operation", args={"operation": "branch", "branch_name": branch})
    if "init" in t and "git" in t:
        return ParsedIntent(intent="git_operation", args={"operation": "init"})

    # Terminal tasks / project scaffolding
    if any(k in t for k in ["vite", "next", "create-next-app"]):
        # Infer framework and language
        framework = "react" if "react" in t else ("vue" if "vue" in t else ("svelte" if "svelte" in t else "vanilla"))
        lang = "ts" if ("typescript" in t or "ts" in t) else "js"
        return ParsedIntent(intent="terminal_task", args={"framework": framework, "language": lang, "project_name": "voice-app"})
    if any(k in t for k in ["create", "write", "generate", "make", "program", "script", "code"]):
        # Simple single-file code creation
        language = "python" if ("python" in t or "py" in t) else ("typescript" if ("typescript" in t or "ts" in t) else "javascript")
        return ParsedIntent(intent="terminal_task", args={"language": language, "project_name": "program", "description": text})

    # GitHub operations (limited heuristics)
    if "create repo" in t or "new repo" in t:
        return ParsedIntent(intent="github_operation", args={"operation": "create_repo", "name": "voice-repo"})
    if "delete repo" in t:
        return ParsedIntent(intent="github_operation", args={"operation": "delete_repo", "name": "voice-repo"})
    if "link remote" in t or "add remote" in t:
        return ParsedIntent(intent="github_operation", args={"operation": "link_remote", "repo_path": "."})

    return ParsedIntent(intent="misc", args={"raw": text})


def parse_intent(text: str) -> ParsedIntent:
    """Use GPT to parse text into an intent and args; fallback to heuristics when unavailable."""
    SYSTEM_PROMPT = (
        "You are a voice agent that turns user speech into structured intents. "
        "Supported intents: 'git_operation', 'terminal_task', 'github_operation', 'misc'. "
        "For git_operation, args may include: operation (status, add, commit, push, pull, checkout, branch, init), "
        "branch_name, commit_message, files (list). For terminal_task, args may include: language, framework, command, project_name. "
        "For github_operation, args may include: operation (create_repo, delete_repo, link_remote, list_repos, list_prs, create_pr, merge_pr, list_issues, create_issue, close_issue), "
        "name, owner, private (bool), org (string), description, repo_path, protocol (ssh or https), confirm (bool), visibility (public/private/all), "
        "repo (string), title (string), head (branch), base (branch), body (string), labels (list of strings), number (int), state (open/closed/all), "
        "push_local (bool), commit_message (string). "
        "If user asks to create code or project, set intent=terminal_task and provide suggested commands."
    )
    user_prompt = f"Command: {text}\nReturn JSON only."
    if client is None:
        return _heuristic_intent(text)
    try:
        resp = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
            temperature=0
        )
        content = resp.choices[0].message.content
        try:
            payload = _extract_json(content)
            data = json.loads(payload)
            intent = data.get("intent", "misc")
            args = data.get("args", {})
            return ParsedIntent(intent=intent, args=args)
        except Exception:
            return ParsedIntent(intent="misc", args={"raw": content})
    except Exception:
        # Fallback to heuristics on any error
        return _heuristic_intent(text)