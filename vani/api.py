from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from .commands import handle_text_command
from .git_ops import perform_git_operation
from .terminal_ops import run_terminal_task
from .audio import record_audio_block, save_wav_temp
from .github_ops import (
    create_repo,
    delete_repo,
    link_remote,
    list_repos,
    list_open_prs,
    create_pull_request,
    merge_pull_request,
    list_issues,
    create_issue,
    close_issue,
)

app = FastAPI(title="Vani Agent API", version="0.1.0")


class TextCommand(BaseModel):
    text: str


class GitOp(BaseModel):
    repo_path: Optional[str] = None
    operation: str
    files: Optional[List[str]] = None
    branch_name: Optional[str] = None
    commit_message: Optional[str] = "voice commit"


class TerminalTask(BaseModel):
    project_name: Optional[str] = "voice-project"
    language: Optional[str] = "python"
    framework: Optional[str] = None
    command: Optional[str] = None


class CreateRepo(BaseModel):
    name: str
    private: Optional[bool] = True
    org: Optional[str] = None
    description: Optional[str] = None
    repo_path: Optional[str] = None
    protocol: Optional[str] = "ssh"


class DeleteRepo(BaseModel):
    owner: str
    name: str
    confirm: bool


class LinkRemote(BaseModel):
    repo_path: str
    owner: str
    name: str
    protocol: Optional[str] = "ssh"


class PRCreate(BaseModel):
    owner: str
    repo: str
    title: str
    head: str
    base: str
    body: Optional[str] = None


class PRMerge(BaseModel):
    owner: str
    repo: str
    number: int
    commit_title: Optional[str] = None


class IssuesList(BaseModel):
    owner: str
    repo: str
    state: Optional[str] = "open"


class IssueCreate(BaseModel):
    owner: str
    repo: str
    title: str
    body: Optional[str] = None
    labels: Optional[List[str]] = None


class IssueClose(BaseModel):
    owner: str
    repo: str
    number: int


@app.get("/")
def root() -> Dict[str, Any]:
    return {"ok": True, "service": "vani-agent", "version": "0.1.0"}


@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    return {"status": "healthy"}


@app.post("/command")
def command(cmd: TextCommand) -> Dict[str, Any]:
    handle_text_command(cmd.text)
    return {"ok": True}


@app.post("/git")
def git(op: GitOp) -> Dict[str, Any]:
    perform_git_operation(op.dict())
    return {"ok": True}


@app.post("/terminal")
def terminal(task: TerminalTask) -> Dict[str, Any]:
    run_terminal_task(task.dict())
    return {"ok": True}


@app.post("/github/create")
def github_create(req: CreateRepo) -> Dict[str, Any]:
    result = create_repo(name=req.name, private=req.private, org=req.org, description=req.description)
    owner = result.get("owner", {}).get("login")
    if req.repo_path:
        link_remote(repo_path=req.repo_path, owner=owner, name=req.name, protocol=req.protocol)
    return {"ok": True, "repo": result}


@app.post("/github/delete")
def github_delete(req: DeleteRepo) -> Dict[str, Any]:
    if not req.confirm:
        return {"ok": False, "error": "confirm must be true"}
    delete_repo(owner=req.owner, name=req.name)
    return {"ok": True}


@app.post("/github/link")
def github_link(req: LinkRemote) -> Dict[str, Any]:
    url = link_remote(repo_path=req.repo_path, owner=req.owner, name=req.name, protocol=req.protocol)
    return {"ok": True, "remote_url": url}


@app.get("/github/repos")
def github_repos(org: Optional[str] = None, visibility: Optional[str] = None) -> Dict[str, Any]:
    repos = list_repos(org=org, visibility=visibility)
    return {"ok": True, "repos": repos}


@app.get("/github/prs")
def github_prs(owner: str, repo: str) -> Dict[str, Any]:
    prs = list_open_prs(owner, repo)
    return {"ok": True, "prs": prs}


@app.post("/github/prs")
def github_create_pr(req: PRCreate) -> Dict[str, Any]:
    pr = create_pull_request(req.owner, req.repo, req.title, req.head, req.base, req.body)
    return {"ok": True, "pr": pr}


@app.post("/github/prs/merge")
def github_merge_pr(req: PRMerge) -> Dict[str, Any]:
    result = merge_pull_request(req.owner, req.repo, req.number, req.commit_title)
    return {"ok": True, "result": result}


@app.get("/github/issues")
def github_list_issues(owner: str, repo: str, state: Optional[str] = "open") -> Dict[str, Any]:
    issues = list_issues(owner, repo, state)
    return {"ok": True, "issues": issues}


@app.post("/github/issues")
def github_create_issue(req: IssueCreate) -> Dict[str, Any]:
    issue = create_issue(req.owner, req.repo, req.title, req.body, req.labels)
    return {"ok": True, "issue": issue}


@app.post("/github/issues/close")
def github_close_issue(req: IssueClose) -> Dict[str, Any]:
    result = close_issue(req.owner, req.repo, req.number)
    return {"ok": True, "result": result}