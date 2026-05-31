#!/usr/bin/env bash
# Easy installer entry (Linux) — same as installers/linux/install.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec bash "$SCRIPT_DIR/install.sh"
