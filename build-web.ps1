# Voice Assistant frontend build script (Vue3 + TS + Vite)
# Run on real machine (sandbox cannot spawn node subprocesses)
#
# Usage:
#   .\build-web.ps1              # npm install + build to dist
#   .\build-web.ps1 -Dev         # start vite dev server (HMR)
#   .\build-web.ps1 -SkipInstall # skip npm install

param(
    [switch]$Dev,
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$webapp = Join-Path $root 'webapp'

Write-Host '=============================================='
Write-Host '  Voice Assistant frontend build'
Write-Host '=============================================='

Set-Location $webapp

if (-not $SkipInstall) {
    Write-Host '[1/2] npm install ...'
    npm install --registry=https://registry.npmmirror.com
    if ($LASTEXITCODE -ne 0) { Write-Host 'npm install failed' -ForegroundColor Red; exit 1 }
}

if ($Dev) {
    Write-Host '[2/2] Starting dev server: http://127.0.0.1:5173'
    Write-Host '(Backend must be running: .\start-web.ps1)'
    if (Test-Path 'node_modules\vite\bin\vite.js') {
        # Direct node call (avoids npm wrapper issues)
        node node_modules/vite/bin/vite.js --port 5173 --host 127.0.0.1
    } else {
        npm run dev
    }
} else {
    Write-Host '[2/2] Building to dist/ ...'
    if (Test-Path 'node_modules\vite\bin\vite.js') {
        node node_modules/vite/bin/vite.js build
    } else {
        npm run build
    }
    if ($LASTEXITCODE -ne 0) { Write-Host 'build failed' -ForegroundColor Red; exit 1 }
    Write-Host ''
    Write-Host 'Build done! Start backend, then open http://127.0.0.1:8000'
    Write-Host '(Backend auto-serves webapp/dist)'
}
