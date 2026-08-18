# Push voice-assistant to GitHub
# Run on your real machine (sandbox git TLS is blocked).
#
# Usage:
#   .\push-github.ps1                        # use default repo below
#   .\push-github.ps1 -Token "ghp_xxx"       # with PAT token
#
# Or set env GITHUB_TOKEN before running.

param(
    [string]$Repo = "https://github.com/newerwell/-.git",
    [string]$Token
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not $Token) { $Token = $env:GITHUB_TOKEN }
if (-not $Token) { $Token = $env:GH_TOKEN }

# Build push URL with token if provided
$pushUrl = $Repo
if ($Token) {
    # https://TOKEN@github.com/USER/REPO.git
    $pushUrl = $Repo -replace '^https://', "https://$Token@"
}

Write-Host "Pushing to: $Repo"
if (-not (Test-Path '.git')) {
    Write-Host 'No git repo, initializing...'
    git init
}

# Ensure main branch name
git branch -M main 2>$null

# Commit any pending changes
$status = git status --porcelain
if ($status) {
    Write-Host 'Committing pending changes...'
    git add -A
    git commit -m "chore: update"
}

# Add remote if missing
$hasRemote = git remote | Select-String 'origin'
if (-not $hasRemote) {
    git remote add origin $Repo
} else {
    git remote set-url origin $pushUrl
}

Write-Host 'Pushing...'
git push -u origin main

Write-Host ''
Write-Host 'Done! Visit: https://github.com/'
