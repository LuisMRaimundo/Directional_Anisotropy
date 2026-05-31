#!/usr/bin/env bash
# Anisotropia Direcional — macOS one-click installer

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
REQ_FILE="$PROJECT_ROOT/requirements-app.txt"
APP_FILE="$PROJECT_ROOT/Anisotropia.py"
MIN_PY=310

export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
cd "$PROJECT_ROOT"

step() { echo ""; echo "==> $*"; }

find_python() {
  local candidates=(
    python3.12 python3.11 python3.10
    /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.10
    /usr/local/bin/python3.12 /usr/local/bin/python3.11 /usr/local/bin/python3.10
    python3 /usr/bin/python3
  )
  for c in "${candidates[@]}"; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
        echo "$c"
        return 0
      fi
    fi
  done
  return 1
}

install_python_macos() {
  step "Python 3.10+ not found."
  if command -v brew >/dev/null 2>&1; then
    step "Installing Python via Homebrew (may take several minutes)..."
    brew install python@3.12 || brew install python@3.11 || brew install python
    hash -r 2>/dev/null || true
    return 0
  fi
  echo ""
  echo "  Please install Python 3.10 or newer:"
  echo "    https://www.python.org/downloads/macos/"
  echo "  Or install Homebrew (https://brew.sh) and run this installer again."
  echo ""
  open "https://www.python.org/downloads/macos/" 2>/dev/null || true
  exit 1
}

echo ""
echo "  Anisotropia Direcional — macOS installer"
echo "  Project: $PROJECT_ROOT"
echo ""

step "Checking for Python 3.10+..."
PY="$(find_python)" || true
if [[ -z "${PY:-}" ]]; then
  install_python_macos
  PY="$(find_python)" || { echo "Python still not found after install attempt."; exit 1; }
fi
echo "Using: $("$PY" --version)"

step "Creating virtual environment (.venv)..."
if [[ ! -d "$VENV_DIR" ]]; then
  "$PY" -m venv "$VENV_DIR"
fi
VENV_PY="$VENV_DIR/bin/python"
[[ -x "$VENV_PY" ]] || { echo "venv failed at $VENV_DIR"; exit 1; }

step "Installing dependencies (first time may take 5–15 minutes)..."
"$VENV_PY" -m pip install --upgrade pip wheel setuptools
"$VENV_PY" -m pip install -r "$REQ_FILE"

step "Writing START-Anisotropia.command launcher..."
cat > "$PROJECT_ROOT/START-Anisotropia.command" << 'LAUNCHER'
#!/bin/bash
cd "$(dirname "$0")"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
if [[ ! -x ".venv/bin/python" ]]; then
  echo "Run INSTALL-MAC.command first."
  read -r -p "Press Enter to close..."
  exit 1
fi
echo "Starting Anisotropia Direcional..."
echo "Close this Terminal window to stop the app."
exec .venv/bin/python -m streamlit run Anisotropia.py
LAUNCHER
chmod +x "$PROJECT_ROOT/START-Anisotropia.command"

step "Starting Anisotropia (browser should open)..."
echo "To run again later, double-click START-Anisotropia.command"
echo ""
exec "$VENV_PY" -m streamlit run "$APP_FILE"
