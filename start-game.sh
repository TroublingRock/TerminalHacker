#!/usr/bin/env bash
# Launch TerminalHacker GUI on the cloud desktop (VNC display :1).
set -euo pipefail
cd "$(dirname "$0")"
export DISPLAY="${DISPLAY:-:1}"
if pgrep -f 'python3 main.py' >/dev/null 2>&1; then
  WIN=$(xdotool search --name 'TerminalHacker' 2>/dev/null | head -1 || true)
  if [[ -n "${WIN:-}" ]]; then
    xdotool windowactivate "$WIN" 2>/dev/null || true
    xdotool windowraise "$WIN" 2>/dev/null || true
    echo "TerminalHacker already running — brought window to front."
    exit 0
  fi
fi
exec python3 main.py
