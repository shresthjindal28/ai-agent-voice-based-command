import os
import json
import requests
from typing import Optional, List
from git import Repo

from .config import GITHUB_TOKEN, GITHUB_DEFAULT_VISIBILITY, GITHUB_DEFAULT_ORG, GITHUB_DEFAULT_PROTOCOL
from .audio import speak

GITHUB_API = "https://api.github.com"

class GitHubError(Exception):
    pass

# Re-export helpers for use in commands handler
__all__ = [
    "create_repo",
    "delete_repo",
    "link_remote",
    "list_repos",
    "list_open_prs",
    "create_pull_request",
    "merge_pull_request",
    "list_issues",
    "create_issue",
    "close_issue",
    "push_local_repo",
]


def _headers():
    if not GITHUB_TOKEN:
        raise GitHubError("GITHUB_TOKEN not configured")
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def create_repo(name: str, private: bool = True, org: Optional[str] = None, description: Optional[str] = None) -> dict:
    """Create a GitHub repository under user or org."""
    path = f"/orgs/{org}/repos" if org else "/user/repos"
    url = f"{GITHUB_API}{path}"
    payload = {"name": name, "private": private}
    if description:
        payload["description"] = description
    r = requests.post(url, headers=_headers(), json=payload, timeout=20)
    if r.status_code >= 300:
        raise GitHubError(f"GitHub create_repo failed: {r.status_code} {r.text}")
    return r.json()


def delete_repo(owner: str, name: str) -> None:
    """Delete a GitHub repository. Requires delete_repo scope."""
    url = f"{GITHUB_API}/repos/{owner}/{name}"
    r = requests.delete(url, headers=_headers(), timeout=20)
    if r.status_code == 404:
        raise GitHubError("Repository not found")
    if r.status_code >= 300:
        raise GitHubError(f"GitHub delete_repo failed: {r.status_code} {r.text}")


def link_remote(repo_path: str, owner: str, name: str, protocol: str = "ssh") -> str:
    """Set git remote 'origin' to the GitHub repo using ssh or https."""
    repo = Repo(repo_path)
    remote_url = (
        f"git@github.com:{owner}/{name}.git" if protocol == "ssh" else f"https://github.com/{owner}/{name}.git"
    )
    try:
        if "origin" in [r.name for r in repo.remotes]:
            repo.delete_remote("origin")
        repo.create_remote("origin", remote_url)
    except Exception:
        # If origin exists but delete_remote failed in this environment, set_url
        repo.git.remote("set-url", "origin", remote_url)
    return remote_url


def push_local_repo(repo_path: str, commit_message: str = "voice commit") -> None:
    """Stage, commit (if needed), and push local repo to origin."""
    repo = Repo(repo_path)
    # Stage all files
    try:
        repo.git.add(".")
        print("Staged changes.")
    except Exception as e:
        print(f"Add error: {e}")
    # Try to commit; ignore if nothing to commit
    try:
        repo.index.commit(commit_message)
        print(f"Committed: {commit_message}")
    except Exception as e:
        print(f"Commit skipped or failed: {e}")
    # Ensure we are on a branch
    try:
        branch_name = repo.active_branch.name
    except Exception:
        branch_name = "main"
        try:
            repo.git.checkout("-b", branch_name)
            print(f"Created and switched to branch {branch_name}.")
        except Exception as e:
            print(f"Branch setup error: {e}")
    # Push with upstream
    try:
        print(repo.git.push("--set-upstream", "origin", branch_name))
        speak("Pushed your local repository to GitHub.")
    except Exception as e:
        print(f"Push error: {e}")
        speak("Failed to push; please check your SSH keys or HTTPS credentials.")


def list_repos(org: Optional[str] = None, visibility: Optional[str] = None) -> list:
    """List repositories for the authenticated user or a given org.
    visibility: one of None, 'all', 'public', 'private'.
    """
    params = {}
    if visibility in {"all", "public", "private"}:
        params["visibility"] = visibility
    if org:
        url = f"{GITHUB_API}/orgs/{org}/repos"
    else:
        url = f"{GITHUB_API}/user/repos"
    r = requests.get(url, headers=_headers(), params=params, timeout=20)
    if r.status_code >= 300:
        raise GitHubError(f"GitHub list_repos failed: {r.status_code} {r.text}")
    return r.json()


def list_open_prs(owner: str, repo: str) -> List[dict]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
    r = requests.get(url, headers=_headers(), timeout=20)
    if r.status_code >= 300:
        raise GitHubError(f"GitHub list_open_prs failed: {r.status_code} {r.text}")
    return r.json()


def create_pull_request(owner: str, repo: str, title: str, head: str, base: str, body: Optional[str] = None) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
    payload = {"title": title, "head": head, "base": base}
    if body:
        payload["body"] = body
    r = requests.post(url, headers=_headers(), json=payload, timeout=20)
    if r.status_code >= 300:
        raise GitHubError(f"GitHub create_pull_request failed: {r.status_code} {r.text}")
    return r.json()


def merge_pull_request(owner: str, repo: str, number: int, commit_title: Optional[str] = None) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{number}/merge"
    payload = {"merge_method": "squash"}
    if commit_title:
        payload["commit_title"] = commit_title
    r = requests.put(url, headers=_headers(), json=payload, timeout=20)
    if r.status_code >= 300:
        raise GitHubError(f"GitHub merge_pull_request failed: {r.status_code} {r.text}")
    return r.json()


def list_issues(owner: str, repo: str, state: str = "open") -> List[dict]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"
    params = {"state": state}
    r = requests.get(url, headers=_headers(), params=params, timeout=20)
    if r.status_code >= 300:
        raise GitHubError(f"GitHub list_issues failed: {r.status_code} {r.text}")
    return r.json()


def create_issue(owner: str, repo: str, title: str, body: Optional[str] = None, labels: Optional[List[str]] = None) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"
    payload = {"title": title}
    if body:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    r = requests.post(url, headers=_headers(), json=payload, timeout=20)
    if r.status_code >= 300:
        raise GitHubError(f"GitHub create_issue failed: {r.status_code} {r.text}")
    return r.json()


def close_issue(owner: str, repo: str, number: int) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{number}"
    payload = {"state": "closed"}
    r = requests.patch(url, headers=_headers(), json=payload, timeout=20)
    if r.status_code >= 300:
        raise GitHubError(f"GitHub close_issue failed: {r.status_code} {r.text}")
    return r.json()


def handle_github_operation(args: dict) -> None:
    op = args.get("operation")
    try:
        if op == "create_repo":
            name = args.get("name")
            # Default visibility from env
            visibility = args.get("private")
            if visibility is None:
                visibility = True if GITHUB_DEFAULT_VISIBILITY == "private" else False
            private = bool(visibility)
            # Default org from env
            org = args.get("org", GITHUB_DEFAULT_ORG)
            description = args.get("description")
            result = create_repo(name=name, private=private, org=org, description=description)
            owner = result.get("owner", {}).get("login")
            full_name = result.get("full_name")
            speak(f"Created repo {full_name}.")
            # Optionally link local repo (defaults to current directory) and push
            repo_path = args.get("repo_path", os.getcwd())
            protocol = args.get("protocol", GITHUB_DEFAULT_PROTOCOL)
            push_local = bool(args.get("push_local", False))
            commit_message = args.get("commit_message", "voice commit")
            try:
                url = link_remote(repo_path=repo_path, owner=owner, name=name, protocol=protocol)
                speak("Linked origin to GitHub.")
                if push_local:
                    try:
                        push_local_repo(repo_path=repo_path, commit_message=commit_message)
                    except Exception:
                        speak("Link done, but push failed.")
            except Exception:
                speak("Repo created; link skipped because no local git repo found here.")
        elif op == "delete_repo":
            owner = args.get("owner")
            name = args.get("name")
            # Add explicit confirmation flag to reduce risk
            if not bool(args.get("confirm", False)):
                speak("Deletion requires confirm=true.")
                return
            delete_repo(owner=owner, name=name)
            speak(f"Deleted {owner}/{name}.")
        elif op == "link_remote":
            repo_path = args.get("repo_path", os.getcwd())
            owner = args.get("owner")
            name = args.get("name")
            protocol = args.get("protocol", GITHUB_DEFAULT_PROTOCOL)
            try:
                url = link_remote(repo_path=repo_path, owner=owner, name=name, protocol=protocol)
                speak("Linked origin to GitHub.")
            except Exception:
                speak("Link skipped; no local git repo found here.")
        elif op == "list_repos":
            org = args.get("org")
            visibility = args.get("visibility")
            repos = list_repos(org=org, visibility=visibility)
            top = [r.get("full_name") or r.get("name") for r in repos[:5]]
            summary = ", ".join(top) if top else "none"
            speak(f"Found {len(repos)} repos: {summary}.")
        elif op == "list_prs":
            owner = args.get("owner")
            repo = args.get("repo")
            prs = list_open_prs(owner, repo)
            titles = [p.get("title") for p in prs[:5]]
            speak(f"Open PRs: {', '.join(titles) if titles else 'none'}.")
        elif op == "create_pr":
            owner = args.get("owner")
            repo = args.get("repo")
            title = args.get("title")
            head = args.get("head")
            base = args.get("base")
            body = args.get("body")
            pr = create_pull_request(owner, repo, title, head, base, body)
            speak(f"PR #{pr.get('number')} created.")
        elif op == "merge_pr":
            owner = args.get("owner")
            repo = args.get("repo")
            number = int(args.get("number"))
            result = merge_pull_request(owner, repo, number)
            speak(f"PR #{number} merged.")
        elif op == "list_issues":
            owner = args.get("owner")
            repo = args.get("repo")
            state = args.get("state", "open")
            issues = list_issues(owner, repo, state)
            titles = [i.get("title") for i in issues[:5]]
            speak(f"{state.capitalize()} issues: {', '.join(titles) if titles else 'none'}.")
        elif op == "create_issue":
            owner = args.get("owner")
            repo = args.get("repo")
            title = args.get("title")
            body = args.get("body")
            labels = args.get("labels")
            issue = create_issue(owner, repo, title, body, labels)
            speak(f"Issue #{issue.get('number')} created.")
        elif op == "close_issue":
            owner = args.get("owner")
            repo = args.get("repo")
            number = int(args.get("number"))
            close_issue(owner, repo, number)
            speak(f"Issue #{number} closed.")
        else:
            speak(f"Unsupported GitHub op: {op}.")
    except GitHubError as e:
        msg = str(e)
        if "Resource not accessible by personal access token" in msg:
            speak("GitHub token lacks repo create permission; use a classic PAT with repo/public_repo scope or adjust org settings.")
        else:
            speak(f"GitHub error: {msg}")
    except Exception as e:
        speak("Unexpected GitHub error.")
        print(f"Unexpected error: {e}")