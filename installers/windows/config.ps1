# Directional_Anisotropy - Windows installer constants
$script:AnisotropiaConfig = @{
    GitHubRepoUrl        = 'https://github.com/LuisMRaimundo/Directional_Anisotropy'
    AppName              = 'Directional_Anisotropy'
    PythonVersion        = '3.11'
    PythonMinMinor       = 10
    PythonMaxMinor       = 12
    PythonInstallerUrl   = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
    RequirementsFile     = 'requirements-app.txt'
    AppScript            = 'Anisotropia.py'
    VenvFolder           = '.venv'
    StartBatName         = 'START-Directional-Anisotropy.bat'
}
