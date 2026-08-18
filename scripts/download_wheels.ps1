# Batch download pip wheels from Aliyun HTTP mirror (v2, fixed URL + version parsing)
$ErrorActionPreference = 'Continue'
$mirror = 'http://mirrors.aliyun.com/pypi'
$simple = "$mirror/simple"
$outDir = 'D:\dsh\voice-assistant\wheels\deps'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$pkgs = @('filelock','typing_extensions','sympy','networkx','jinja2','fsspec','setuptools','mpmath','markupsafe','certifi')

function Get-WheelUrl([string]$pkg) {
    $html = curl.exe -s --max-time 20 "$simple/$pkg/"
    if (-not $html) { throw "no index for $pkg" }
    $rows = @()
    foreach ($line in $html) {
        if ($line -match 'href="([^"]+\.whl)(?:[#"]|$)') {
            $url = $Matches[1]
            $file = $url -split '/' | Select-Object -Last 1
            if ($file -match '^[^\-]+-([0-9][^\-]*)-(\S+)\.whl$') {
                $ver = $Matches[1]; $tag = $Matches[2]
                # skip pre-releases (alpha/beta/rc/dev) and non-windows/non-pure wheels
                if ($ver -match '[a-zA-Z]') { continue }
                if ($tag -notmatch 'py3-none-any|cp312.*win_amd64|cp312.*win32') { continue }
                $rows += [PSCustomObject]@{ File=$file; Url=$url; Ver=$ver; Tag=$tag }
            }
        }
    }
    if (-not $rows) { throw "no usable wheel for $pkg" }
    # newest version via numeric sort
    $best = $rows | Sort-Object { [long](([regex]::Match($_.Ver,'^(\d+)')).Groups[1].Value) } -Descending |
            Sort-Object { [long](([regex]::Match($_.Ver,'\.(\d+)')).Groups[1].Value) } -Descending |
            Select-Object -First 1
    return $best
}

foreach ($pkg in $pkgs) {
    try {
        $w = Get-WheelUrl $pkg
        $dest = Join-Path $outDir $w.File
        if (Test-Path $dest) { Write-Host "skip (exists): $($w.File)"; continue }
        # href is like ../../packages/xx/yy/.../file.whl -> strip leading ../../
        $rel = ($w.Url -replace '^\.\./\.\./', '')
        $fullUrl = "$mirror/$rel"
        Write-Host "downloading $($w.File)"
        curl.exe -s -o $dest --max-time 180 -w "  %{size_download} bytes, %{time_total}s, %{speed_download} B/s`n" $fullUrl
        $fi = Get-Item $dest -ErrorAction SilentlyContinue
        if (-not $fi -or $fi.Length -lt 5000) { Write-Host "  !! bad download ($($fi.Length) bytes), removing"; Remove-Item $dest -Force -ErrorAction SilentlyContinue }
    } catch {
        Write-Host "FAILED $pkg : $($_.Exception.Message)"
    }
}
Write-Host '=== done ==='
Get-ChildItem $outDir | Select-Object Name, @{N='KB';E={[math]::Round($_.Length/1KB,1)}} | Format-Table -AutoSize
