"""
Tools Jarvis can call. Start small and safe, add more as you trust the system.

Each tool needs:
  1. A definition in TOOL_DEFINITIONS (tells the model what it does and what
     arguments it takes) - follows Ollama's function-calling schema
  2. A branch in execute_tool() that actually performs the action

SAFETY NOTE: anything destructive (deleting files, closing unsaved work,
submitting forms) should ask for confirmation before running. This starter
only includes safe, reversible actions to begin with.
"""

import subprocess
import webbrowser

# Map of common app names -> how to launch them on Windows.
# Add your own frequently used apps here.
APP_LAUNCHERS = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "notepad": "notepad",
    "explorer": "explorer",
    "calculator": "calc",
    "spotify": "spotify",
    "vscode": "code",
    "terminal": "wt",  # Windows Terminal
    "task manager": "taskmgr",
    "taskmgr": "taskmgr",
    "epic games launcher": "EpicGamesLauncher",
    "epic games": "EpicGamesLauncher",
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an application on the user's PC by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the app to open, e.g. 'chrome', 'notepad', 'spotify'",
                    }
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a URL in the default web browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to open"}
                },
                "required": ["url"],
            },
        },
    },
]


def execute_tool(name: str, tool_input: dict) -> str:
    if name == "open_app":
        app_name = str(tool_input.get("app_name", "")).lower().strip()
        command = APP_LAUNCHERS.get(app_name, app_name)  # fall back to a best-effort attempt
        try:
            subprocess.Popen(f'start "" {command}', shell=True)
            if app_name not in APP_LAUNCHERS:
                return f"Tried opening {app_name} — it's not in my known app list, so this was a best-effort guess. Add it to APP_LAUNCHERS in tools.py if it didn't work."
            return f"Opened {app_name}."
        except Exception as e:
            return f"Failed to open {app_name}: {e}"

    if name == "open_url":
        url = tool_input.get("url", "")
        try:
            webbrowser.open(url)
            return f"Opened {url}."
        except Exception as e:
            return f"Failed to open URL: {e}"

    return f"Unknown tool: {name}"
