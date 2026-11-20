# 営業サンプル（架空の居酒屋「ほろよい亭」）：写真3枚を Kling 2.5 で5秒の動画に（2026-11-03）
# 1本 5秒、見積もりが $0.25 を超えたら止める。同名ファイルがあれば生成しない。
param([string[]]$Only)
$ErrorActionPreference = 'Stop'
$maxUsd = [decimal]0.25
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$envFile = 'C:\Users\abetk\Desktop\AIアルコホリディ\.env'
$key = ''
if (Test-Path -LiteralPath $envFile) { $key = (Get-Content -LiteralPath $envFile -Encoding UTF8 | Where-Object { $_ -match '^HF_KEY=' }) -replace '^HF_KEY=', '' }
if ([string]::IsNullOrWhiteSpace($key)) { throw 'HF_KEY is not available.' }
$headers = @{ Authorization = "Key $($key.Trim())" }

$root = $PSScriptRoot
$model = 'kling-video/v2.5-turbo/standard/image-to-video'
$neg = 'camera orbit, zoom, zooming in, zooming out, dolly, pan, fast movement, shaking, flicker, close-up face, face, new objects, new people entering, text, letters, logo, watermark, captions, warped hands, deformed hands, extra fingers, extra hands, stretched glass, glass changing shape, food changing shape, morphing, bird, insect, cat, dog'
$lock = 'The camera is locked off on a tripod with no zoom, no push-in and no camera movement. All motion is small, slow and natural.'
$items = @(
  @{ name='video1'; image='izakaya1.png'; cfg=0.9;
     prompt="$lock A warm, lively small Japanese izakaya at night. The paper lanterns glow warmly and sway very slightly. The blurred customers in the background move a little naturally. Everything else stays still." },
  @{ name='video2'; image='izakaya2.png'; cfg=0.9;
     prompt="$lock Freshly fried Japanese karaage chicken on a plate with a cold draft beer. A thin, gentle wisp of steam rises slowly from the hot karaage, and tiny bubbles rise inside the beer. The food, plate, glass and lemon keep exactly their shape and do not move." },
  @{ name='video3'; image='izakaya3.png'; cfg=0.9;
     prompt="$lock Two hands holding beer mugs move them a few centimeters together for a gentle toast; the mugs softly touch, then stay together. Each hand keeps five natural fingers and each mug keeps its exact shape. The warm blurred izakaya background stays still." }
)
foreach ($item in $items) {
  if ($Only -and ($Only -notcontains $item.name)) { continue }
  Write-Host "=== $($item.name) ==="
  try {
    $image = Join-Path $root $item.image
    if (!(Test-Path -LiteralPath $image)) { throw "Input image not found: $($item.image)" }
    $outputPath = Join-Path $root ($item.name + '.mp4')
    if (Test-Path -LiteralPath $outputPath) { Write-Host "Already exists, skipping"; continue }
    $upload = Invoke-RestMethod -Method Post -Uri 'https://api.higgsfield.ai/files/generate-upload-url' -Headers $headers -ContentType 'application/json' -Body '{"content_type":"image/png"}'
    $uploadHeaders = @{}
    if ($upload.upload_headers) { foreach ($h in $upload.upload_headers.PSObject.Properties) { $uploadHeaders[$h.Name] = [string]$h.Value } }
    Invoke-WebRequest -UseBasicParsing -Method Put -Uri $upload.upload_url -Headers $uploadHeaders -InFile $image | Out-Null
    $req = [ordered]@{ prompt=$item.prompt; duration=5; cfg_scale=$item.cfg; image_url=$upload.public_url; negative_prompt=$neg }
    $body = $req | ConvertTo-Json -Depth 8
    $estimate = Invoke-RestMethod -Method Post -Uri ("https://api.higgsfield.ai/estimate/" + $model) -Headers $headers -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body))
    $usd = [decimal]::Parse([string]$estimate.usd, [Globalization.CultureInfo]::InvariantCulture)
    Write-Host ('Estimate USD: ' + $usd)
    if ($usd -gt $maxUsd) { throw ('Estimate exceeds safety limit of $' + $maxUsd) }
    $submit = Invoke-RestMethod -Method Post -Uri ("https://api.higgsfield.ai/" + $model) -Headers $headers -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body))
    if (!$submit.request_id) { throw 'No request_id returned.' }
    $requestId = [string]$submit.request_id
    $statusUrl = if ($submit.status_url) { [string]$submit.status_url } else { "https://api.higgsfield.ai/requests/$requestId/status" }
    Write-Host ('Submitted: ' + $requestId)
    $deadline = (Get-Date).AddMinutes(10)
    do {
      if ((Get-Date) -gt $deadline) { throw "Timed out. request_id=$requestId (do not resubmit blindly)" }
      Start-Sleep -Seconds 10
      $status = Invoke-RestMethod -Method Get -Uri $statusUrl -Headers $headers
      if ($status.status -in @('failed','nsfw','canceled')) { throw ('Generation ended: ' + $status.status + ' ' + $status.error) }
    } while ($status.status -ne 'completed')
    Invoke-WebRequest -UseBasicParsing -Uri $status.video.url -OutFile $outputPath
    if ((Get-Item -LiteralPath $outputPath).Length -lt 1024) { throw 'Downloaded video is too small.' }
    [ordered]@{ generated_at=(Get-Date).ToString('o'); model=$model; request_id=$requestId; estimate_usd=[string]$estimate.usd; source=$item.image; input=$req } |
      ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $root ($item.name + '-result.json')) -Encoding UTF8
    Write-Host "DONE $($item.name).mp4"
  } catch {
    Write-Host ('FAILED [' + $item.name + ']: ' + $_.Exception.Message)
  }
}
Write-Host '=== all items processed ==='
