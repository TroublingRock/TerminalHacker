#!/bin/bash
# Linux launcher — use from file manager or Security Simulator.desktop
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

dialog() {
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="Security Simulator" --text="$1" 2>/dev/null || true
  elif command -v kdialog >/dev/null 2>&1; then
    kdialog --error "$1" 2>/dev/null || true
  else
    echo "$1" >&2
  fi
}

question() {
  if command -v zenity >/dev/null 2>&1; then
    zenity --question --title="Security Simulator" --text="$1" 2>/dev/null
    return $?
  elif command -v kdialog >/dev/null 2>&1; then
    kdialog --yesno "$1" 2>/dev/null
    return $?
  fi
  echo "$1"
  read -r -p "Install now? [y/N] " ans
  [[ "$ans" =~ ^[Yy] ]]
}

find_python() {
  local bin
  for bin in python3 python; do
    if command -v "$bin" >/dev/null 2>&1; then
      if "$bin" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        echo "$bin"
        return 0
      fi
    fi
  done
  return 1
}

install_python() {
  if command -v apt-get >/dev/null 2>&1; then
    question "Python 3.10+ is required.\n\nInstall python3 and python3-tk now? (admin password needed)" || return 1
    pkexec apt-get update -qq
    pkexec apt-get install -y python3 python3-tk
    return 0
  fi
  if command -v dnf >/dev/null 2>&1; then
    question "Python 3.10+ is required.\n\nInstall python3 and python3-tkinter now?" || return 1
    pkexec dnf install -y python3 python3-tkinter
    return 0
  fi
  if command -v pacman >/dev/null 2>&1; then
    question "Python 3.10+ is required.\n\nInstall python and tk now?" || return 1
    pkexec pacman -S --noconfirm python tk
    return 0
  fi
  dialog "Install Python 3.10+ and Tk from your package manager, then run this launcher again."
  return 1
}

ensure_tk() {
  local py="$1"
  if "$py" -c "import tkinter" 2>/dev/null; then
    return 0
  fi
  if command -v apt-get >/dev/null 2>&1; then
    question "The GUI needs python3-tk.\n\nInstall it now? (admin password needed)" || return 1
    pkexec apt-get install -y python3-tk
    return 0
  fi
  if command -v dnf >/dev/null 2>&1; then
    question "The GUI needs python3-tkinter.\n\nInstall it now?" || return 1
    pkexec dnf install -y python3-tkinter
    return 0
  fi
  if command -v pacman >/dev/null 2>&1; then
    question "The GUI needs the tk package.\n\nInstall it now?" || return 1
    pkexec pacman -S --noconfirm tk
    return 0
  fi
  dialog "Install the Tk package for Python, or run: $py main.py --cli"
  return 1
}

PYTHON="$(find_python)" || {
  install_python || exit 1
  PYTHON="$(find_python)" || {
    dialog "Python 3.10+ not found after install attempt."
    exit 1
  }
}

if [[ "${1:-}" != "--cli" ]]; then
  ensure_tk "$PYTHON" || exit 1
fi

exec "$PYTHON" "$ROOT/launch/bootstrap.py" "$@"
