#!/bin/bash
# Double-click launcher for a non-technical Mac user. Sets up a local Python
# virtualenv (once), starts the local UI server on 127.0.0.1 only, and opens
# it in the default browser. Closing this Terminal window stops the server.
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display dialog "Python 3 was not found on this Mac.\n\nInstall it from python.org (the macOS installer under Downloads), then double-click Screener.command again." with title "Screener" buttons {"OK"} default button "OK"'
  exit 1
fi

VENV=".venv"
STAMP="$VENV/.installed"
REQ_HASH="$(shasum -a 256 requirements.txt | awk '{print $1}')"

if [ ! -d "$VENV" ]; then
  echo "First run — setting up (about a minute)..."
  python3 -m venv "$VENV"
fi

if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP" 2>/dev/null)" != "$REQ_HASH" ]; then
  echo "Installing dependencies..."
  "$VENV/bin/pip" install -q -r requirements.txt
  echo "$REQ_HASH" > "$STAMP"
fi

cleanup() {
  if [ -n "$SERVER_PID" ]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

"$VENV/bin/python3" ui/server.py &
SERVER_PID=$!

sleep 1
open "http://127.0.0.1:8765"

echo ""
echo "Screener UI running — leave this window open; close it to stop."
echo ""

wait "$SERVER_PID"
