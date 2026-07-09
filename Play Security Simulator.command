#!/bin/bash
# Double-click this file on macOS (Finder → Open) to play Security Simulator.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

alert() {
  osascript -e "display alert \"Security Simulator\" message \"$1\" as critical" 2>/dev/null || echo "$1"
}

info() {
  osascript -e "display alert \"Security Simulator\" message \"$1\"" 2>/dev/null || echo "$1"
}

find_python() {
  local candidates=(
    /opt/homebrew/bin/python3
    /usr/local/bin/python3
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3
    /Library/Frameworks/Python.framework/Versions/3.10/bin/python3
    python3
    python
  )
  local bin
  for bin in "${candidates[@]}"; do
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
  if command -v brew >/dev/null 2>&1; then
    choice=$(osascript -e 'button returned of (display dialog "Security Simulator needs Python 3.10+.\n\nInstall with Homebrew now?" buttons {"Cancel", "Install"} default button "Install")' 2>/dev/null || echo "Cancel")
    if [[ "$choice" == "Install" ]]; then
      brew install python@3.12
      return 0
    fi
  fi
  info "Download Python 3.10+ from python.org, then double-click this file again."
  open "https://www.python.org/downloads/macos/" 2>/dev/null || true
  return 1
}

PYTHON="$(find_python)" || {
  install_python || exit 1
  PYTHON="$(find_python)" || {
    alert "Python 3.10+ still not found after install attempt."
    exit 1
  }
}

exec "$PYTHON" "$ROOT/launch/bootstrap.py" "$@"
