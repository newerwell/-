# Voice Assistant Web one-click start (uv-managed)
# Usage: double-click, or in PowerShell: .\start-web.ps1
# After start, open http://127.0.0.1:8000

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# CUDA DLL env (required by bitsandbytes)
$env:PATH = "$root\.venv\Lib\site-packages\torch\lib;" + $env:PATH
$env:LD_LIBRARY_PATH = "$root\.venv\Lib\site-packages\torch\lib"
$env:PYTHONIOENCODING = 'utf-8'

# uv cache in workspace (sandbox cannot write AppData)
$env:UV_CACHE_DIR = 'D:\dsh\.uv-cache'
$env:UV_PYTHON_INSTALL_DIR = 'D:\dsh\.uv-python'

Write-Host ''
Write-Host '=============================================='
Write-Host '  Voice Assistant Web Service (uv)'
Write-Host '  Starting, please wait...'
Write-Host '  Open: http://127.0.0.1:8000'
Write-Host '  Press Ctrl+C to stop'
Write-Host '=============================================='
Write-Host ''

Set-Location $root

if (Get-Command uv -ErrorAction SilentlyContinue) {
    # uv-managed: use project venv
    uv run --python "$root\.venv\Scripts\python.exe" python -m uvicorn web.server:app --host 127.0.0.1 --port 8000
} else {
    # fallback: direct python
    & "$root\.venv\Scripts\python.exe" "$root\web\server.py"
}
