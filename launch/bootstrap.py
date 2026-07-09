#!/usr/bin/env python3
"""Bootstrap launcher — checks environment and starts Security Simulator."""

from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_VERSION = (3, 10)
GAME_TITLE = "Security Simulator"


def show_message(title: str, message: str, *, error: bool = False) -> None:
    """Best-effort GUI dialog; falls back to stderr."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        if error:
            messagebox.showerror(title, message)
        else:
            messagebox.showinfo(title, message)
        root.destroy()
        return
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import ctypes

            flags = 0x10 if error else 0x40
            ctypes.windll.user32.MessageBoxW(0, message, title, flags)
            return
        except Exception:
            pass

    stream = sys.stderr if error else sys.stdout
    print(f"{title}\n{message}", file=stream)


def ensure_tkinter() -> bool:
    try:
        import tkinter  # noqa: F401

        return True
    except ImportError:
        if sys.platform.startswith("linux"):
            show_message(
                GAME_TITLE,
                "The desktop GUI needs the Tk package for Python.\n\n"
                "Debian/Ubuntu: sudo apt install python3-tk\n"
                "Fedora: sudo dnf install python3-tkinter\n"
                "Arch: sudo pacman -S tk\n\n"
                "Or run CLI-only mode: python3 main.py --cli",
                error=True,
            )
        elif sys.platform == "darwin":
            show_message(
                GAME_TITLE,
                "Python on this Mac is missing Tkinter.\n\n"
                "Reinstall Python from https://www.python.org/downloads/macos/\n"
                "and include Tcl/Tk in the installer.\n\n"
                "Or run CLI-only: python3 main.py --cli",
                error=True,
            )
        else:
            show_message(
                GAME_TITLE,
                "Python Tkinter is not available for the GUI.\n\n"
                "Reinstall Python with Tcl/Tk enabled, or run:\n"
                "python main.py --cli",
                error=True,
            )
        return False


def main() -> int:
    os.chdir(ROOT)
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

    if sys.version_info < MIN_VERSION:
        show_message(
            GAME_TITLE,
            f"Python {MIN_VERSION[0]}.{MIN_VERSION[1]}+ is required.\n"
            f"This interpreter is {sys.version_info.major}.{sys.version_info.minor}.",
            error=True,
        )
        return 1

    if "--cli" in sys.argv:
        os.execv(sys.executable, [sys.executable, os.path.join(ROOT, "main.py"), "--cli"])

    if not ensure_tkinter():
        return 1

    # Prefer pythonw on Windows to avoid a console flash.
    if sys.platform == "win32" and os.path.basename(sys.executable).lower() == "python.exe":
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if os.path.isfile(pythonw):
            os.execv(pythonw, [pythonw, os.path.join(ROOT, "main.py")])

    os.execv(sys.executable, [sys.executable, os.path.join(ROOT, "main.py")])


if __name__ == "__main__":
    raise SystemExit(main())
