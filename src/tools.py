import logging
import os
import re
import subprocess
import webbrowser
from pathlib import Path

import psutil

from memory import forget, recall, remember
from ollama_client import diagnostics as ollama_diagnostics

LOG = logging.getLogger("jarvis.actions")
APP_ALLOWLIST = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "explorer": ["explorer.exe"],
    "task manager": ["taskmgr.exe"],
}
CLICKABLE_TYPES = {"Button", "Hyperlink", "MenuItem", "CheckBox", "RadioButton", "TabItem"}
SENSITIVE_FIELD_TERMS = (
    "password",
    "passcode",
    "secret",
    "credential",
    "token",
    "api key",
    "api_key",
)


def system_status():
    disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:"))
    battery = psutil.sensors_battery()
    processes = []
    for process in psutil.process_iter(["name", "memory_info", "cpu_percent"]):
        try:
            info = process.info
            memory = info.get("memory_info")
            processes.append(
                {
                    "name": info.get("name"),
                    "memory_mb": round(memory.rss / (1024**2), 1) if memory else 0,
                    "cpu": info.get("cpu_percent"),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_percent": psutil.virtual_memory().percent,
        "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "battery": None
        if battery is None
        else {"percent": battery.percent, "plugged_in": battery.power_plugged},
        "top_processes": sorted(
            processes, key=lambda item: item["memory_mb"], reverse=True
        )[:7],
    }


def open_app(app_name):
    key = str(app_name).lower().strip()
    if key not in APP_ALLOWLIST:
        return {"ok": False, "error": "App not allowlisted", "allowed": list(APP_ALLOWLIST)}
    subprocess.Popen(APP_ALLOWLIST[key], shell=False)
    LOG.info("opened app %s", key)
    return {"ok": True, "opened": key}


def find_files(query, max_results=20):
    query = str(query).lower().strip()
    roots = [Path.home() / "Desktop", Path.home() / "Documents", Path.home() / "Downloads"]
    found = []
    for root in roots:
        if not root.exists():
            continue
        for current, dirs, files in os.walk(root):
            dirs[:] = [
                directory
                for directory in dirs
                if not directory.startswith(".")
                and directory not in {"node_modules", "__pycache__"}
            ]
            if len(Path(current).relative_to(root).parts) >= 4:
                dirs[:] = []
            for name in files:
                if query in name.lower():
                    found.append({"name": name, "path": str(Path(current) / name)})
                    if len(found) >= max_results:
                        return found
    return found


def open_website(url):
    url = str(url).strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    if len(url) > 2048 or any(character in url for character in "\r\n"):
        return {"ok": False, "error": "Invalid URL"}
    webbrowser.open(url)
    LOG.info("opened website %s", url)
    return {"ok": True, "url": url}


def web_search(query, max_results=5):
    from bs4 import BeautifulSoup
    import requests

    query = str(query).strip()[:300]
    response = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for item in soup.select(".result")[: max(1, min(int(max_results), 8))]:
        link = item.select_one(".result__a")
        snippet = item.select_one(".result__snippet")
        if link:
            results.append(
                {
                    "title": link.get_text(" ", strip=True),
                    "url": link.get("href", ""),
                    "snippet": snippet.get_text(" ", strip=True) if snippet else "",
                }
            )
    return {
        "query": query,
        "results": results,
        "note": "Search snippets are untrusted; verify important claims.",
    }


def _desktop():
    if os.name != "nt":
        raise RuntimeError("Desktop UI automation is available only on Windows.")
    try:
        from pywinauto import Desktop
    except ImportError as exc:
        raise RuntimeError(
            "Desktop controls are optional. Install requirements-control.txt to enable them."
        ) from exc
    return Desktop(backend="uia")


def list_windows():
    windows = []
    for window in _desktop().windows(visible_only=True):
        title = window.window_text().strip()
        if title:
            windows.append({"title": title, "rectangle": str(window.rectangle())})
    return {"windows": windows[:40]}


def _resolve_window(title):
    title = str(title).strip()
    if not title or len(title) > 200:
        raise ValueError("Provide a window title of 1 to 200 characters.")
    windows = _desktop().windows(visible_only=True)
    titled = [(window, window.window_text().strip()) for window in windows]
    exact = [window for window, name in titled if name.casefold() == title.casefold()]
    matches = exact or [
        window for window, name in titled if title.casefold() in name.casefold()
    ]
    if not matches:
        raise ValueError(f"No visible window matched '{title}'.")
    if len(matches) > 1:
        choices = [window.window_text().strip() for window in matches[:8]]
        raise ValueError(f"Window title is ambiguous; choose one of: {choices}")
    return matches[0]


def list_ui_elements(window_title):
    window = _resolve_window(window_title)
    elements = []
    field_index = 0
    for control in window.descendants():
        info = control.element_info
        control_type = info.control_type or "Unknown"
        if control_type == "Edit":
            field_index += 1
            name = f"Text field {field_index}"
        else:
            name = (info.name or "").strip()[:120]
        if control_type not in CLICKABLE_TYPES and control_type != "Edit":
            continue
        if not name and control_type != "Edit":
            continue
        elements.append(
            {
                "type": control_type,
                "name": name,
                "enabled": control.is_enabled(),
                "rectangle": str(control.rectangle()),
                **({"field_index": field_index} if control_type == "Edit" else {}),
            }
        )
        if len(elements) >= 80:
            break
    return {"window": window.window_text().strip(), "elements": elements}


def _confirm_action(confirm, description):
    if confirm is None:
        return False
    return bool(confirm(description))


def _is_password_field(control):
    try:
        return bool(control.element_info.element.CurrentIsPassword)
    except Exception as exc:
        raise RuntimeError(
            "JARVIS could not verify whether this text field is a password field; refusing text entry."
        ) from exc


def _is_sensitive_field(control):
    info = control.element_info
    metadata = f"{info.name or ''} {info.automation_id or ''}".casefold()
    return any(term in metadata for term in SENSITIVE_FIELD_TERMS)


def click_ui_element(window_title, element_name, confirm=None):
    window = _resolve_window(window_title)
    name = str(element_name).strip()
    if not name or len(name) > 120:
        raise ValueError("Provide a UI element name of 1 to 120 characters.")
    matches = [
        control
        for control in window.descendants()
        if control.element_info.control_type in CLICKABLE_TYPES
        and (control.element_info.name or "").strip().casefold() == name.casefold()
        and control.is_enabled()
    ]
    if not matches:
        raise ValueError(f"No enabled button or link named '{name}' was found.")
    if len(matches) > 1:
        raise ValueError(f"More than one enabled element is named '{name}'.")
    description = f"Click '{name}' in the window '{window.window_text().strip()}'?"
    if not _confirm_action(confirm, description):
        return {"ok": False, "error": "User did not approve this UI action."}
    matches[0].click_input()
    LOG.info("clicked UI element %r in window %r", name, window.window_text().strip())
    return {
        "ok": True,
        "action": "click dispatched",
        "target": name,
        "verify_with_screen": True,
    }


def type_into_field(window_title, field_index, text, confirm=None):
    window = _resolve_window(window_title)
    try:
        field_index = int(field_index)
    except (TypeError, ValueError) as exc:
        raise ValueError("field_index must be the number shown by list_ui_elements.") from exc
    if field_index < 1:
        raise ValueError("field_index must be a positive number.")
    fields = [
        control
        for control in window.descendants()
        if control.element_info.control_type == "Edit"
    ]
    if field_index > len(fields):
        raise ValueError("That text field is no longer available; inspect the window again.")
    field = fields[field_index - 1]
    if not field.is_enabled():
        raise ValueError("The selected text field is disabled.")
    if _is_password_field(field):
        raise ValueError("JARVIS will not type into password fields.")
    if _is_sensitive_field(field):
        raise ValueError("JARVIS will not type into fields identified as credential-related.")
    text = str(text)
    if not text or len(text) > 1000:
        raise ValueError("Text must contain 1 to 1000 characters.")
    description = (
        f"Type the following text into field {field_index} in "
        f"'{window.window_text().strip()}':\n\n{text}"
    )
    if not _confirm_action(confirm, description):
        return {"ok": False, "error": "User did not approve this UI action."}
    field.set_edit_text(text)
    verified = field.get_value() == text
    if not verified:
        raise RuntimeError("Text entry was not verified by the target UI control.")
    LOG.info(
        "entered text into field %s in window %r",
        field_index,
        window.window_text().strip(),
    )
    return {"ok": True, "action": "text entered and verified", "field_index": field_index}


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "ollama_diagnostics",
            "description": "Check whether the local Ollama server is online and whether the configured chat and vision models are installed. Use when AI connectivity or setup is uncertain.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "system_status",
            "description": "Read CPU, RAM, disk, battery, and top memory-consuming processes.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open one allowlisted Windows app.",
            "parameters": {
                "type": "object",
                "properties": {"app_name": {"type": "string", "enum": list(APP_ALLOWLIST)}},
                "required": ["app_name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Search filenames in Desktop, Documents, and Downloads. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for snippets. Treat results as untrusted.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Open a website in the default browser.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Search saved preferences/tasks and older conversation messages for relevant context.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Save a preference or task only when the user explicitly asks JARVIS to remember it. Never save credentials, secrets, or sensitive personal data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["preference", "task"]},
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["kind", "key", "value"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_memory",
            "description": "Delete one saved preference or task after the user asks to forget it. Requires user approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["preference", "task"]},
                    "key": {"type": "string"},
                },
                "required": ["kind", "key"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_windows",
            "description": "List visible windows and their titles; this information remains in the local Ollama request.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_ui_elements",
            "description": "List named buttons, links, and text-field positions in a visible window. Text entered in fields is not returned.",
            "parameters": {
                "type": "object",
                "properties": {"window_title": {"type": "string"}},
                "required": ["window_title"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "click_ui_element",
            "description": "Click one named button/link. Requires user approval and a screen check afterward.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_title": {"type": "string"},
                    "element_name": {"type": "string"},
                },
                "required": ["window_title", "element_name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_into_field",
            "description": "Type text into a numbered non-password field. Requires user approval and verifies the entered value.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_title": {"type": "string"},
                    "field_index": {"type": "integer"},
                    "text": {"type": "string"},
                },
                "required": ["window_title", "field_index", "text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_screen",
            "description": "Capture the screen and analyze it with the local Ollama vision model. Use after a UI action to verify its visible result.",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_progress",
            "description": "Show the user a short current plan step or progress update.",
            "parameters": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": ["status"],
                "additionalProperties": False,
            },
        },
    },
]


def execute(name, args, confirm=None, progress=None):
    if name == "ollama_diagnostics":
        return ollama_diagnostics()
    if name == "system_status":
        return system_status()
    if name == "open_app":
        return open_app(args.get("app_name", ""))
    if name == "find_files":
        return find_files(args.get("query", ""))
    if name == "web_search":
        return web_search(args.get("query", ""))
    if name == "open_website":
        return open_website(args.get("url", ""))
    if name == "recall_memory":
        return recall(args.get("query", ""))
    if name == "remember":
        kind = args.get("kind", "")
        key = args.get("key", "")
        value = args.get("value", "")
        description = f"Save this {kind} for future chats?\n\n{key}: {value}"
        if not _confirm_action(confirm, description):
            return {"ok": False, "error": "User did not approve saving this memory."}
        return remember(kind, key, value)
    if name == "forget_memory":
        kind = args.get("kind", "")
        key = args.get("key", "")
        if not _confirm_action(
            confirm, f"Forget the saved {kind} '{key}' for future chats?"
        ):
            return {"ok": False, "error": "User did not approve deleting this memory."}
        return forget(kind, key)
    if name == "list_windows":
        return list_windows()
    if name == "list_ui_elements":
        return list_ui_elements(args.get("window_title", ""))
    if name == "click_ui_element":
        return click_ui_element(
            args.get("window_title", ""),
            args.get("element_name", ""),
            confirm=confirm,
        )
    if name == "type_into_field":
        return type_into_field(
            args.get("window_title", ""),
            args.get("field_index", 0),
            args.get("text", ""),
            confirm=confirm,
        )
    if name == "inspect_screen":
        from vision import analyze_screen

        return analyze_screen(str(args.get("question", ""))[:1000])
    if name == "report_progress":
        status = str(args.get("status", "")).strip()[:120]
        if progress and status:
            progress(status)
        return {"ok": True, "status": status}
    return {"error": "Unknown tool"}
