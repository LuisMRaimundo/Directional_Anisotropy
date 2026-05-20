# Installers — Anisotropia Direcional

One-click setup for users **without Python**. Scripts install Python 3.10+ when needed, create `.venv/`, install `requirements-app.txt`, and launch the Streamlit UI.

**Repository:** https://github.com/LuisMRaimundo/Music_xml_anisotropy

## Quick start

| Platform | Recommended entry |
|----------|-------------------|
| **Windows 10/11** | Double-click **`instalers/windows/INSTALL.bat`** (or root **`INSTALL-WINDOWS.bat`**) |
| **macOS** | Double-click root **`INSTALL-MAC.command`** (runs `instalers/mac/install.sh`) |
| **Linux** | **`bash instalers/linux/install-easy.sh`** or root **`INSTALL-LINUX.sh`** |

After install, use **`START-Anisotropia.bat`** (Windows), **`START-Anisotropia.command`** (macOS), or **`START-Anisotropia.sh`** (Linux).

## Layout

| Folder | Standard install | Portable build (PyInstaller) |
|--------|------------------|------------------------------|
| [`windows/`](windows/) | **`INSTALL.bat`**, `Install-Anisotropia.ps1` | *Not included in git* — see [GitHub Releases](https://github.com/LuisMRaimundo/Music_xml_anisotropy/releases) if distributed |
| [`mac/`](mac/) | `install.sh`, `install-easy.sh` | *Not included in git* |
| [`linux/`](linux/) | `install.sh`, `install-easy.sh` | *Not included in git* |

Built `.exe` / `.app` / `.dmg` / `.tar.gz` files are **not** stored in this repository. Publish frozen builds via **GitHub Releases** if you distribute them.

## Requirements

- Internet connection (first run downloads Python and Python packages).
- **Windows:** [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/) (Windows 10/11).
- **macOS:** Terminal; Homebrew optional; otherwise install Python from [python.org](https://www.python.org/downloads/macos/).
- **Linux:** `sudo` for system Python via apt/dnf/pacman when Python is missing.

First install typically takes **5–15 minutes**.
