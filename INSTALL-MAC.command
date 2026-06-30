#!/bin/bash
# Double-click this file in Finder to install and run Directional_Anisotropy on macOS.

cd "$(dirname "$0")"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

clear
echo ""
echo "  ========================================"
echo "   Directional_Anisotropy"
echo "   One-click install for macOS"
echo "  ========================================"
echo ""
echo "  This will install Python (if needed), set up the app,"
echo "  and open it in your web browser."
echo ""
read -r -p "Press Enter to continue... " _

bash "installers/mac/install.sh" || {
  echo ""
  echo "  Installation failed. See messages above."
  read -r -p "Press Enter to close... " _
  exit 1
}
