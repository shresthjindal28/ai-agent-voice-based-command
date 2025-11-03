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


def parse_intent(text: str) -> ParsedIntent:
    """Use GPT to parse text into an intent and args."""
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