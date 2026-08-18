# Download CosyVoice2-0.5B model files via curl with https->http downgrade
$files = @(
    @{ Name = 'llm.pt'; Url = 'http://www.modelscope.cn/models/iic/CosyVoice2-0.5B/resolve/master/llm.pt' },
    @{ Name = 'flow.pt'; Url = 'http://www.modelscope.cn/models/iic/CosyVoice2-0.5B/resolve/master/flow.pt' },
    @{ Name = 'hift.pt'; Url = 'http://www.modelscope.cn/models/iic/CosyVoice2-0.5B/resolve/master/hift.pt' },
    @{ Name = 'speech_tokenizer_v2.onnx'; Url = 'http://www.modelscope.cn/models/iic/CosyVoice2-0.5B/resolve/master/speech_tokenizer_v2.onnx' },
    @{ Name = 'campplus.onnx'; Url = 'http://www.modelscope.cn/models/iic/CosyVoice2-0.5B/resolve/master/campplus.onnx' },
    @{ Name = 'cosyvoice2.yaml'; Url = 'http://www.modelscope.cn/models/iic/CosyVoice2-0.5B/resolve/master/cosyvoice2.yaml' }
)
$outDir = 'D:\dsh\voice-assistant\models\CosyVoice2-0.5B'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

foreach ($f in $files) {
    $dest = Join-Path $outDir $f.Name
    if (Test-Path $dest) { Write-Host "skip (exists): $($f.Name)"; continue }
    # get 302 Location, downgrade https->http
    $headers = curl.exe -s -o NUL -D - --max-time 30 "$($f.Url)" -r 0-0
    $loc = $headers | Where-Object { $_ -match '^[Ll]ocation:' } | Select-Object -First 1
    if (-not $loc) { Write-Host "FAIL $($f.Name): no redirect"; continue }
    $http = ($loc -replace '^[Ll]ocation: ', '') -replace '^https://', 'http://'
    Write-Host "downloading $($f.Name) ..."
    curl.exe -s -o $dest -w "  %{size_download} bytes in %{time_total}s`n" --max-time 3600 $http
}
Write-Host '=== done ==='
Get-ChildItem $outDir | Select-Object Name, @{N='GB';E={[math]::Round($_.Length/1e9,2)}} | Format-Table -AutoSize
