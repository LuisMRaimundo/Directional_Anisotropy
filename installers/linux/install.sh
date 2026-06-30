#!/usr/bin/env bash
# Directional_Anisotropy — Linux one-click installer

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
REQ_FILE="$PROJECT_ROOT/requirements-app.txt"
APP_FILE="$PROJECT_ROOT/Anisotropia.py"

export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
cd "$PROJECT_ROOT"

step() { echo ""; echo "==> $*"; }

find_python() {
  local candidates=(
    python3.12 python3.11 python3.10 python3
    /usr/bin/python3.12 /usr/bin/python3.11 /usr/bin/python3.10 /usr/bin/python3
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

install_python_linux() {
  step "Python 3.10+ not found. Installing via system package manager..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip python3-dev \
      || sudo apt-get install -y python3.12 python3.12-venv python3-pip 2>/dev/null \
      || sudo apt-get install -y python3.11 python3.11-venv python3-pip 2>/dev/null
    return 0
  fi
  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-pip
    return 0
  fi
  if command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm python python-pip
    return 0
  fi
  if command -v zypper >/dev/null 2>&1; then
    sudo zypper install -y python3 python3-pip python3-virtualenv
    return 0
  fi
  echo ""
  echo "  Could not detect apt, dnf, pacman, or zypper."
  echo "  Install Python 3.10+ manually, then run this script again."
  exit 1
}

echo ""
echo "  Directional_Anisotropy — Linux installer"
echo "  Project: $PROJECT_ROOT"
echo ""

step "Checking for Python 3.10+..."
PY="$(find_python)" || true
if [[ -z "${PY:-}" ]]; then
  install_python_linux
  PY="$(find_python)" || { echo "Python still not found."; exit 1; }
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

step "Writing START-Directional-Anisotropy.sh launcher..."
cat > "$PROJECT_ROOT/START-Directional-Anisotropy.sh" << 'LAUNCHER'
#!/usr/bin/env bash
cd "$(dirname "$0")"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
if [[ ! -x ".venv/bin/python" ]]; then
  echo "Run INSTALL-LINUX.sh first."
  read -r -p "Press Enter to close..."
  exit 1
fi
echo "Starting Directional_Anisotropy..."
echo "Press Ctrl+C in this terminal to stop the app."
exec .venv/bin/python -m streamlit run Anisotropia.py
LAUNCHER
chmod +x "$PROJECT_ROOT/START-Directional-Anisotropy.sh"

step "Starting Directional_Anisotropy (browser should open)..."
echo "To run again later, run: ./START-Directional-Anisotropy.sh"
echo ""
exec "$VENV_PY" -m streamlit run "$APP_FILE"
