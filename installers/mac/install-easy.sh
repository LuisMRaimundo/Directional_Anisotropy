#!/usr/bin/env bash
# Easy installer entry (macOS) — same as installers/mac/install.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec bash "$SCRIPT_DIR/install.sh"
