# ALCOHOLIDAY one-shot (2026-10-12): outside window -> entrance -> inside -> poster close-up
# Order (approved): 2 -> 1 -> 3 -> 4. Kling O3 first-last-frame, std, 5s each (~0.42 USD each).
# Stops if an estimate exceeds the limit. Skips clips that already exist (no double billing).
$ErrorActionPreference = 'Stop'
$maxUsd = [decimal]0.45
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$envFile = Join-Path $PSScriptRoot '..\..\.env'
$key = ''
if (Test-Path -LiteralPath $envFile) { $key = ((Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^HF_KEY=' }) -replace '^HF_KEY=', '') }
if ([string]::IsNullOrWhiteSpace($key)) { $key = [Environment]::GetEnvironmentVariable('HF_KEY','User') }
if ([string]::IsNullOrWhiteSpace($key)) { throw 'HF_KEY is not available.' }
$headers = @{ Authorization = "Key $($key.Trim())" }

$root = $PSScriptRoot
$src = Join-Path $root 'sozai'
$model = 'kling-video/o3/first-last-frame'

$style = "One single continuous cinematic shot with no cuts, filmed on a smooth steady gimbal at a slow, constant walking pace, like a scene from a film. Warm golden evening light, cozy European bistro."
$poster = "The framed red pop-art poster of a hand holding a sparkling wine glass with the caption 'NO SPARKLING WINE, NO LIFE.' is a real flat printed poster: its illustration, lettering, white border and gold frame stay perfectly rigid and never warp, morph, redraw or change."
$avoid = "Avoid: cuts, scene changes, morphing objects, warped poster, changing letters, garbled text, new text, extra posters, people, hands, birds, steam, smoke, shaking camera, fast movement, zoom jumps."

$items = @(
  @{ name='oneshot-a-2to1'; first='2.png'; last='1.png';
     prompt="$style The shot starts outside on the street, looking through the restaurant's wooden-framed window at the poster on the wall inside. The camera glides smoothly to the left along the facade, reaches the open entrance door and moves forward through the doorway into the restaurant, ending just inside the door with the brass door handle in the left foreground and the dining room and poster ahead. $poster $avoid" },
  @{ name='oneshot-b-1to3'; first='1.png'; last='3.png';
     prompt="$style The camera continues walking slowly forward from the entrance into the dining room, gliding between the set tables with candles and wine glasses, the poster on the wall growing gradually closer, ending at a wider view of the corner with the window on the left and the poster in the center. $poster $avoid" },
  @{ name='oneshot-c-3to4'; first='3.png'; last='4.png';
     prompt="$style The camera keeps moving slowly and steadily forward toward the wall, rising gently past the table in the foreground, until the framed poster fills most of the frame in a close-up, with warm sunlight falling across the textured wall. $poster $avoid" }
)

function Upload-Image($path) {
  $upload = Invoke-RestMethod -Method Post -Uri 'https://api.higgsfield.ai/files/generate-upload-url' -Headers $headers -ContentType 'application/json' -Body '{"content_type":"image/png"}'
  $uploadHeaders = @{}
  if ($upload.upload_headers) { foreach ($h in $upload.upload_headers.PSObject.Properties) { $uploadHeaders[$h.Name] = [string]$h.Value } }
  Invoke-WebRequest -UseBasicParsing -Method Put -Uri $upload.upload_url -Headers $uploadHeaders -InFile $path | Out-Null
  return $upload.public_url
}

$urls = @{}
foreach ($item in $items) {
  Write-Host "=== $($item.name) ==="
  try {
    $outputPath = Join-Path $root ($item.name + '.mp4')
    if (Test-Path -LiteralPath $outputPath) { Write-Host "Already exists, skipping"; continue }
    foreach ($f in @($item.first, $item.last)) {
      if (-not $urls.ContainsKey($f)) {
        $p = Join-Path $src $f
        if (!(Test-Path -LiteralPath $p)) { throw "Input image not found: $f" }
        $urls[$f] = Upload-Image $p
      }
    }
    $req = [ordered]@{ prompt=$item.prompt; duration=5; mode='std'; sound='off'; aspect_ratio='9:16'; first_frame_url=$urls[$item.first]; last_frame_url=$urls[$item.last] }
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
    $deadline = (Get-Date).AddMinutes(15)
    do {
      if ((Get-Date) -gt $deadline) { throw "Timed out. request_id=$requestId (do not resubmit blindly)" }
      Start-Sleep -Seconds 10
      $status = Invoke-RestMethod -Method Get -Uri $statusUrl -Headers $headers
      if ($status.status -in @('failed','nsfw','canceled')) { throw ('Generation ended: ' + $status.status + ' ' + $status.error) }
    } while ($status.status -ne 'completed')
    Invoke-WebRequest -UseBasicParsing -Uri $status.video.url -OutFile $outputPath
    if ((Get-Item -LiteralPath $outputPath).Length -lt 1024) { throw 'Downloaded video is too small.' }
    [ordered]@{ generated_at=(Get-Date).ToString('o'); model=$model; request_id=$requestId; estimate_usd=[string]$estimate.usd; input=$req } |
      ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $root ($item.name + '-result.json')) -Encoding UTF8
    Write-Host "DONE $($item.name).mp4"
  } catch {
    Write-Host ('FAILED [' + $item.name + ']: ' + $_.Exception.Message)
  }
}
Write-Host '=== all items processed ==='
