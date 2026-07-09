#!/usr/bin/env python3
"""Check GitHub for a newer Security Simulator release and prompt the player."""

from __future__ import annotations

import json
import os
import re
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

GAME_TITLE = "Security Simulator"
REPO = "TroublingRock/TerminalHacker"
REMOTE_VERSION_URL = f"https://raw.githubusercontent.com/{REPO}/main/VERSION"
DOWNLOAD_ZIP_URL = f"https://github.com/{REPO}/archive/refs/heads/main.zip"
RELEASES_URL = f"https://github.com/{REPO}/releases"
CHECK_INTERVAL = timedelta(hours=24)
STATE_PATH = Path.home() / ".terminalhacker" / "update_check.json"
VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_version(text: str) -> tuple[int, int, int] | None:
    match = VERSION_RE.search((text or "").strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def read_local_version() -> tuple[int, int, int] | None:
    version_file = _root_dir() / "VERSION"
    if not version_file.is_file():
        return None
    return parse_version(version_file.read_text(encoding="utf-8"))


def fetch_remote_version(timeout: float = 5.0) -> tuple[int, int, int] | None:
    request = Request(
        REMOTE_VERSION_URL,
        headers={"User-Agent": "SecuritySimulator-Updater/1.0"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return parse_version(response.read().decode("utf-8", errors="replace"))
    except (URLError, OSError, TimeoutError, ValueError):
        return None


def _load_state() -> dict:
    if not STATE_PATH.is_file():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _format_version(version: tuple[int, int, int]) -> str:
    return f"{version[0]}.{version[1]}.{version[2]}"


def _should_check(state: dict) -> bool:
    last_check = state.get("last_check")
    if not last_check:
        return True
    try:
        checked_at = datetime.fromisoformat(last_check)
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return datetime.now(timezone.utc) - checked_at >= CHECK_INTERVAL


def _ask_download(local: tuple[int, int, int], remote: tuple[int, int, int]) -> bool:
    message = (
        f"Update available: v{_format_version(remote)} "
        f"(you have v{_format_version(local)}).\n\n"
        "Open the download page in your browser?\n"
        "Unzip the new folder over your copy to update.\n"
        "Your save stays in ~/.terminalhacker/save.json"
    )

    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        choice = messagebox.askyesno(GAME_TITLE, message)
        root.destroy()
        return bool(choice)
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import ctypes

            # MB_YESNO | MB_ICONINFORMATION
            result = ctypes.windll.user32.MessageBoxW(0, message, GAME_TITLE, 0x40 | 0x4)
            return result == 6
        except Exception:
            pass

    answer = input(f"{message}\nDownload now? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def check_for_update(*, force: bool = False) -> bool:
    """Return True if the player chose to open the download page."""
    if os.environ.get("TERMINALHACKER_SKIP_UPDATE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return False

    local = read_local_version()
    if local is None:
        return False

    state = _load_state()
    now = datetime.now(timezone.utc).isoformat()

    if not force and not _should_check(state):
        return False

    remote = fetch_remote_version()
    state["last_check"] = now

    if remote is None:
        _save_state(state)
        return False

    state["last_remote"] = _format_version(remote)

    if remote <= local:
        _save_state(state)
        return False

    dismissed = state.get("dismissed_remote")
    if not force and dismissed == _format_version(remote):
        _save_state(state)
        return False

    if _ask_download(local, remote):
        webbrowser.open(DOWNLOAD_ZIP_URL)
        _save_state(state)
        return True

    state["dismissed_remote"] = _format_version(remote)
    _save_state(state)
    return False


if __name__ == "__main__":
    opened = check_for_update(force="--force" in sys.argv)
    print("opened download" if opened else "no update action")
