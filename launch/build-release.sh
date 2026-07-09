#!/bin/bash
# Build a ready-to-share zip with launchers at the top level.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="Security-Simulator"
VERSION="$(date +%Y%m%d)"
OUT="$ROOT/dist/${NAME}-${VERSION}.zip"

mkdir -p "$ROOT/dist"
rm -f "$OUT"

cd "$ROOT"
zip -r "$OUT" \
  *.py \
  llm.json.example \
  README.md \
  INSTALL.md \
  "Play Security Simulator.bat" \
  "Play Security Simulator.vbs" \
  "Play Security Simulator.command" \
  play-security-simulator.sh \
  "Security Simulator.desktop" \
  launch/bootstrap.py \
  -x '*__pycache__*' -x '*.pyc' -x 'test_*.py' -x '.git/*'

chmod +x play-security-simulator.sh "Play Security Simulator.command" 2>/dev/null || true

echo "Created $OUT"
ls -lh "$OUT"
