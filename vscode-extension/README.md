Vani Agent - VS Code extension

This minimal extension adds a "Vani: Run Agent" command to VS Code that opens a terminal and runs your project's `agent.py` script.

Installation & testing

1. Open the project in VS Code (the workspace root should contain `agent.py`).
2. Open the `vscode-extension` folder in the same VS Code window or use the Extension Development Host:
   - Press F5 to start an Extension Development Host with the extension loaded.
3. Run the command palette (Cmd+Shift+P) and execute `Vani: Run Agent`.

Configuration

- vscode setting `vaniAgent.pythonPath` (default: `python3`) - change to the Python interpreter you want to use.
- vscode setting `vaniAgent.agentPath` (default: `agent.py`) - path to the agent script relative to the workspace root.

Notes

- This extension is intentionally minimal: it runs the agent script in an integrated terminal. You can enhance it to use the Python extension API, virtual environments, or pass arguments.
