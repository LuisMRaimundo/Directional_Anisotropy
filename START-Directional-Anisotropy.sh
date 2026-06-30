#!/bin/bash
cd "$(dirname "$0")"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
if [ ! -f ".venv/bin/activate" ]; then
  echo "Run INSTALL-LINUX.sh first."
  read -r -p "Press Enter to close..."
  exit 1
fi
# shellcheck disable=SC1091
source ".venv/bin/activate"
echo "Starting Directional_Anisotropy..."
echo "Close this window to stop the app."
python -m streamlit run Anisotropia.py
