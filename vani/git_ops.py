import os
from git import Repo, GitCommandError
from .audio import speak


def perform_git_operation(args: dict) -> None:
    repo_path = args.get("repo_path", os.getcwd())
    operation = args.get("operation", "status")
    files = args.get("files")
    branch_name = args.get("branch_name")
    commit_message = args.get("commit_message", "voice commit")

    # Special case: allow init without requiring an existing repo
    if operation == "init":
        try:
            Repo.init(repo_path)
            print(f"Initialized git repository at {repo_path}")
            speak("Initialized git repository.")
        except Exception as e:
            print(f"Git init error: {e}")
            speak("Failed to initialize git repository.")
        return

    try:
        repo = Repo(repo_path)
    except Exception as e:
        msg = f"Git error: cannot open repo at {repo_path}: {e}"
        print(msg)
        speak("I could not open a git repository in this folder. Please initialize git first or tell me to link a remote.")
        return

    try:
        if operation == "status":
            print(repo.git.status())
            speak("Reported repository status.")
        elif operation == "add":
            if files:
                repo.index.add(files)
            else:
                repo.git.add(".")
            print("Staged changes.")
            speak("Staged your changes.")
        elif operation == "commit":
            repo.index.commit(commit_message)
            print(f"Committed: {commit_message}")
            speak("Committed your changes.")
        elif operation == "push":
            print(repo.git.push())
            speak("Pushed to remote.")
        elif operation == "pull":
            print(repo.git.pull())
            speak("Pulled latest changes.")
        elif operation == "checkout":
            if not branch_name:
                print("No branch_name provided.")
                speak("Please provide a branch name.")
                return
            print(repo.git.checkout(branch_name))
            speak(f"Switched to branch {branch_name}.")
        elif operation == "branch":
            if not branch_name:
                print("No branch_name provided.")
                speak("Please provide a branch name.")
                return
            print(repo.git.checkout('-b', branch_name))
            speak(f"Created and switched to branch {branch_name}.")
        else:
            print(f"Unsupported git operation: {operation}")
            speak("Unsupported git operation.")
    except GitCommandError as e:
        msg = f"Git command error: {e}"
        print(msg)
        speak("There was an error running the git command.")