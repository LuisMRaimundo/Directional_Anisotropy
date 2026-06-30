# Directional_Anisotropy - Windows installation

**Repository:** https://github.com/LuisMRaimundo/Directional_Anisotropy

## Standard installation (no Python required)

1. Download a **fresh** ZIP from GitHub (**Code -> Download ZIP**) or clone the repo.
2. Open **`installers\windows`**.
3. Double-click **`INSTALL.bat`** or **`START-HERE.bat`**.
4. Wait for **SUCCESS** or **Done** (first run: **5-15 minutes**).
5. The app opens in your browser (Streamlit).

You can also run **`INSTALL-WINDOWS.bat`** at the repository root (same installer).

## Install log

`install.log` in the project root (next to `Anisotropia.py`).

## Run again later

Double-click **`START-Directional-Anisotropy.bat`** in the project root (created by the installer).

## Troubleshooting

| Issue | Action |
|-------|--------|
| No window / closes instantly | Re-download from GitHub; run **`INSTALL.bat`**. Never use `>>>` in batch echo lines. |
| PowerShell parse error | Old copy with Unicode characters; download fresh from GitHub. |
| Python error | Install Python 3.10+ from https://www.python.org/downloads/ with **Add to PATH**, then run **`INSTALL.bat`** again. |
| Setup failed | Open `install.log`, check Internet/firewall, delete `.venv` and retry. |
