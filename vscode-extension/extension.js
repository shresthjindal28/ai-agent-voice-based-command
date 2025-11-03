const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

let childProc = null;
let outputChannel = null;
const agents = new Map(); // key: cwd, value: { proc, channel }

function getFolderChannelName(cwd) {
  const name = path.basename(cwd) || cwd;
  return `Vani Agent: ${name}`;
}

// Helper: pick a workspace folder (handles multi-root) and hints where agent is found
async function pickWorkspaceFolder(agentRel) {
  const folders = vscode.workspace.workspaceFolders || [];
  if (folders.length === 0) {
    return undefined;
  }
  if (folders.length === 1) {
    return folders[0].uri.fsPath;
  }
  const items = folders.map(f => {
    const fsPath = f.uri.fsPath;
    const agentFull = path.isAbsolute(agentRel) ? agentRel : path.join(fsPath, agentRel);
    const exists = fs.existsSync(agentFull);
    return {
      label: f.name || fsPath,
      description: exists ? '✓ agent found' : 'agent missing',
      fsPath,
      exists
    };
  });
  const selected = await vscode.window.showQuickPick(items, {
    placeHolder: 'Select workspace folder to run Vani agent'
  });
  return selected ? selected.fsPath : undefined;
}

// Helper: resolve Python path, prefer workspace venvs when available
function resolvePythonPath(cwd, configured) {
  const cfg = (configured || '').trim();
  // Treat generic names as "unset" so we can prefer venv
  const isGeneric = cfg && !path.isAbsolute(cfg) && (cfg === 'python' || cfg === 'python3');
  if (!cfg || isGeneric) {
    const candidates = [
      path.join(cwd, '.venv', 'bin', 'python'),
      path.join(cwd, 'venv', 'bin', 'python'),
      path.join(cwd, '.venv', 'bin', 'python3'),
      path.join(cwd, 'venv', 'bin', 'python3'),
      '/usr/local/bin/python3',
      '/usr/bin/python3',
      'python3'
    ];
    for (const p of candidates) {
      if (p === 'python3' || fs.existsSync(p)) return p;
    }
    // If we had a generic configured value, use it as final fallback
    if (isGeneric) return cfg;
    return 'python3';
  }
  // If a specific path is configured, prefer it when it exists
  if (path.isAbsolute(cfg) && fs.existsSync(cfg)) return cfg;
  // Otherwise, return configured as-is (user intent)
  return cfg;
}

// Helper: read OPENAI_API_KEY from .env in cwd
function readOpenAIKeyFromDotEnv(cwd) {
  try {
    const envPath = path.join(cwd, '.env');
    if (!fs.existsSync(envPath)) return '';
    const dot = fs.readFileSync(envPath, 'utf8');
    const match = dot.match(/^\s*OPENAI_API_KEY\s*=\s*(.+)\s*$/m);
    if (match) return match[1].trim().replace(/^"|"$/g, '');
  } catch (_) {}
  return '';
}

// Helper: ensure Python dependencies (soundfile, sounddevice, numpy) are available; install via pip if needed
function ensureDependencies(pythonPath, cwd, channel, runInTerminal, autoInstall) {
  return new Promise(resolve => {
    const check = spawn(pythonPath, ['-c', 'import soundfile, sounddevice, numpy; print("ok")'], { cwd });
    let failed = false;
    check.on('error', () => { failed = true; });
    check.on('close', code => {
      failed = failed || code !== 0;
      const reqPath = path.join(cwd, 'requirements.txt');
      const shouldInstall = failed || !!autoInstall;
      if (!shouldInstall) return resolve(true);
      if (!fs.existsSync(reqPath)) {
        channel.appendLine('requirements.txt not found; proceeding without auto-install.');
        return resolve(!failed);
      }
      if (runInTerminal) {
        const term = vscode.window.createTerminal({ name: getFolderChannelName(cwd), cwd });
        term.show(true);
        term.sendText(`${pythonPath} -m pip install -r "${reqPath}"`);
        // Assume success and continue (terminal will show errors if any)
        return resolve(true);
      }
      channel.appendLine(`Installing Python dependencies: ${pythonPath} -m pip install -r ${reqPath}`);
      const pip = spawn(pythonPath, ['-m', 'pip', 'install', '-r', reqPath], { cwd });
      pip.stdout.on('data', d => channel.append(d.toString()));
      pip.stderr.on('data', d => channel.append(d.toString()));
      pip.on('close', code2 => {
        if (code2 === 0) channel.appendLine('Dependencies installed successfully.');
        else channel.appendLine(`Dependency installation failed with code ${code2}.`);
        resolve(code2 === 0);
      });
      pip.on('error', err => {
        channel.appendLine(`Failed to run pip: ${err && err.message}`);
        resolve(false);
      });
    });
  });
}

/**
 * Activate the extension.
 * Registers commands to run/stop the agent, and streams output to a VS Code Output Channel.
 */
function activate(context) {
  console.log('Vani extension: activate() called');
  try {
    vscode.window.showInformationMessage('Vani extension activated');
  } catch (e) {
    console.log('Vani extension: showInformationMessage failed', e && e.message);
  }

  outputChannel = vscode.window.createOutputChannel('Vani Agent');

  // Run Agent command
  const runDisposable = vscode.commands.registerCommand('vani.runAgent', async function () {
    const config = vscode.workspace.getConfiguration('vaniAgent');
    const configuredPython = config.get('pythonPath') || '';
    const agentRel = config.get('agentPath') || 'agent.py';
    const runInTerminal = config.get('runInTerminal') || false;
    const openaiKeySetting = config.get('openaiKey') || '';
    const autoInstallDeps = config.get('autoInstallDeps') ?? true;

    // Choose correct workspace folder
    let cwd = await pickWorkspaceFolder(agentRel);
    if (!cwd) {
      vscode.window.showErrorMessage('Open a workspace folder first, or select one when prompted.');
      return;
    }

    const pythonPath = resolvePythonPath(cwd, configuredPython);
    const agentFull = path.isAbsolute(agentRel) ? agentRel : path.join(cwd, agentRel);
    if (!fs.existsSync(agentFull)) {
      vscode.window.showErrorMessage(`Agent script not found in selected folder: ${agentFull}`);
      return;
    }

    const effectiveKey = openaiKeySetting || readOpenAIKeyFromDotEnv(cwd);

    if (runInTerminal) {
      const term = vscode.window.createTerminal({ name: 'Vani Agent', cwd });
      term.show(true);
      if (effectiveKey) {
        term.sendText(`export OPENAI_API_KEY="${effectiveKey}"`);
      } else {
        vscode.window.showWarningMessage('OPENAI_API_KEY is not set. Set vaniAgent.openaiKey, use a .env file, or configure your OS environment.');
      }
      const reqPath = path.join(cwd, 'requirements.txt');
      if (autoInstallDeps && fs.existsSync(reqPath)) {
        term.sendText(`${pythonPath} -m pip install -r "${reqPath}"`);
      }
      term.sendText(`${pythonPath} "${agentFull}"`);
      vscode.window.showInformationMessage('Started Vani agent in terminal. Check the Terminal panel for logs.');
      return;
    }

    // Start single agent in Output Channel for selected folder
    const channel = vscode.window.createOutputChannel(getFolderChannelName(cwd));
    channel.clear();
    channel.show(true);
    channel.appendLine(`Starting Vani agent: ${pythonPath} ${agentFull}`);

    const env = { ...process.env };
    if (effectiveKey) env.OPENAI_API_KEY = effectiveKey;
    if (!env.OPENAI_API_KEY) {
      vscode.window.showWarningMessage('OPENAI_API_KEY is not set. The agent may exit. Set vaniAgent.openaiKey, use a .env file, or configure your shell environment.');
    }

    const depsOk = await ensureDependencies(pythonPath, cwd, channel, false, autoInstallDeps);
    if (!depsOk) {
      vscode.window.showErrorMessage('Failed to verify or install Python dependencies. Check the Output panel for details.');
      channel.appendLine('Aborting start due to dependency issues.');
      return;
    }
    try {
      const proc = spawn(pythonPath, ['-u', agentFull], { cwd, env, stdio: ['ignore', 'pipe', 'pipe'] });
      agents.set(cwd, { proc, channel });
      proc.stdout.on('data', data => channel.append(data.toString()));
      proc.stderr.on('data', data => channel.append(data.toString()));
      proc.on('close', (code, signal) => {
        channel.appendLine(`\nAgent exited (code=${code}${signal ? `, signal=${signal}` : ''}).`);
        agents.delete(cwd);
      });
      proc.on('error', err => channel.appendLine(`Agent process error: ${err && err.message}`));
      vscode.window.showInformationMessage('Started Vani agent. Check the Output panel for logs.');
    } catch (err) {
      vscode.window.showErrorMessage(`Failed to start agent: ${err && err.message}`);
    }
  });

  // Run Agent in all workspace folders
  const runAllDisposable = vscode.commands.registerCommand('vani.runAgentAll', async function () {
    const config = vscode.workspace.getConfiguration('vaniAgent');
    const configuredPython = config.get('pythonPath') || '';
    const agentRel = config.get('agentPath') || 'agent.py';
    const runInTerminal = config.get('runInTerminal') || false;
    const openaiKeySetting = config.get('openaiKey') || '';
    const autoInstallDeps = config.get('autoInstallDeps') ?? true;

    const folders = vscode.workspace.workspaceFolders || [];
    if (folders.length === 0) {
      vscode.window.showErrorMessage('Open a workspace folder first.');
      return;
    }

    for (const f of folders) {
      const cwd = f.uri.fsPath;
      const pythonPath = resolvePythonPath(cwd, configuredPython);
      const agentFull = path.isAbsolute(agentRel) ? agentRel : path.join(cwd, agentRel);
      if (!fs.existsSync(agentFull)) {
        continue; // skip folders without agent
      }
      const effectiveKey = openaiKeySetting || readOpenAIKeyFromDotEnv(cwd);
      if (runInTerminal) {
        const term = vscode.window.createTerminal({ name: getFolderChannelName(cwd), cwd });
        term.show(true);
        if (effectiveKey) term.sendText(`export OPENAI_API_KEY="${effectiveKey}"`);
        const reqPath = path.join(cwd, 'requirements.txt');
        if (autoInstallDeps && fs.existsSync(reqPath)) {
          term.sendText(`${pythonPath} -m pip install -r "${reqPath}"`);
        }
        term.sendText(`${pythonPath} "${agentFull}"`);
        continue;
      }
      const channel = vscode.window.createOutputChannel(getFolderChannelName(cwd));
      channel.clear();
      channel.show(true);
      channel.appendLine(`Starting Vani agent: ${pythonPath} ${agentFull}`);
      const env = { ...process.env };
      if (effectiveKey) env.OPENAI_API_KEY = effectiveKey;
      const depsOk = await ensureDependencies(pythonPath, cwd, channel, false, autoInstallDeps);
      if (!depsOk) {
        channel.appendLine('Aborting start due to dependency issues.');
        continue;
      }
      try {
        const proc = spawn(pythonPath, ['-u', agentFull], { cwd, env, stdio: ['ignore', 'pipe', 'pipe'] });
        agents.set(cwd, { proc, channel });
        proc.stdout.on('data', data => channel.append(data.toString()));
        proc.stderr.on('data', data => channel.append(data.toString()));
        proc.on('close', (code, signal) => {
          channel.appendLine(`\nAgent exited (code=${code}${signal ? `, signal=${signal}` : ''}).`);
          agents.delete(cwd);
        });
        proc.on('error', err => channel.appendLine(`Agent process error: ${err && err.message}`));
      } catch (err) {
        vscode.window.showErrorMessage(`Failed to start agent in ${cwd}: ${err && err.message}`);
      }
    }
    vscode.window.showInformationMessage('Started Vani agent in all workspace folders that contain the agent script.');
  });

  // Stop Agent command
  const stopDisposable = vscode.commands.registerCommand('vani.stopAgent', async function () {
    if (agents.size === 0) {
      vscode.window.showInformationMessage('No running Vani agent processes.');
      return;
    }
    const items = Array.from(agents.keys()).map(cwd => ({ label: getFolderChannelName(cwd), description: cwd, cwd }));
    const choice = await vscode.window.showQuickPick(items.concat([{ label: 'Stop All', description: 'Stop agents in all folders', stopAll: true }]), { placeHolder: 'Select agent to stop' });
    if (!choice) return;
    if (choice.stopAll) {
      for (const [cwd, { proc, channel }] of agents.entries()) {
        try { proc.kill(); } catch (_) {}
        channel.appendLine('Sent stop signal.');
        agents.delete(cwd);
      }
      vscode.window.showInformationMessage('Stopped all Vani agents.');
      return;
    }
    const entry = agents.get(choice.cwd);
    if (entry) {
      try { entry.proc.kill(); } catch (_) {}
      entry.channel.appendLine('Sent stop signal.');
      agents.delete(choice.cwd);
      vscode.window.showInformationMessage(`Stopped Vani agent in ${choice.cwd}.`);
    }
  });

  context.subscriptions.push(runDisposable, runAllDisposable, stopDisposable);
}

function deactivate() {
  try {
    if (childProc) {
      childProc.kill();
      childProc = null;
    }
    if (outputChannel) {
      outputChannel.dispose();
      outputChannel = null;
    }
  } catch (_) {}
}

module.exports = { activate, deactivate };
