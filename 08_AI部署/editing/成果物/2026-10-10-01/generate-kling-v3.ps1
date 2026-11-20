# ALCOHOLIDAY editing部：指示 2026-10-10-01（日本酒）動画づくり2回目 Higgsfield 生成 v3
# 社長が作り直した写真（4回目）：引き(angle1-v7-blend) → 乾杯の直前(angle2-v2-blend) → アップ(angle3-v1-blend)
# 1回目への社長の直し「乾杯の動きがとても不自然。おちょこが長くなったり、突然、葉の影が出たり」を受けて：
#   - 乾杯は手を寄せた写真から、お猪口どうしがそっとふれ合うだけ（数mm〜1cm）。腕・体は動かさない
#   - 葉の影・木もれ日・影の模様は出さない（negative に leaf shadows 等）
#   - 1本に動かすもの1つ、小さく落ち着いた動き。cfg 0.9〜0.92
# 1本 5秒、見積もりが $0.25 を超えたら止める。同名ファイルがあれば生成しない。
# 使い方: generate-kling-v3.ps1 [-Only 名前...]（省略時は全部）
param([string[]]$Only)
$ErrorActionPreference = 'Stop'
$maxUsd = [decimal]0.25
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$envFile = 'C:\Users\abetk\Desktop\AIアルコホリディ\.env'
$key = ''
if (Test-Path -LiteralPath $envFile) { $key = (Get-Content -LiteralPath $envFile -Encoding UTF8 | Where-Object { $_ -match '^HF_KEY=' }) -replace '^HF_KEY=', '' }
if ([string]::IsNullOrWhiteSpace($key)) { $key = [Environment]::GetEnvironmentVariable('HF_KEY','User') }
if ([string]::IsNullOrWhiteSpace($key)) { throw 'HF_KEY is not available.' }
$headers = @{ Authorization = "Key $($key.Trim())" }

$root = $PSScriptRoot
$designDir = Join-Path $root '..\..\..\design\成果物\2026-10-10-01'
$model = 'kling-video/v2.5-turbo/standard/image-to-video'
$negCommon = 'poster warping, poster bending, poster resizing, poster shifting position, poster tilting, poster swaying, poster vibration, poster micro-movement, poster jitter, perspective change, illustration reshaping, hand redrawing in the poster, masu cup redrawing, cropped poster, warped text, changing letters, misspelled words, garbled text, nonsense text, fake text, distorted logo, animated poster illustration, morphing artwork, new shapes appearing inside the poster, cursive text, script text, handwriting, signature, watermark, ghost text, any text not in the original image, bottle label text changing, camera orbit, zoom, zooming in, zooming out, camera push-in, dolly, pan, tilt, parallax, fast movement, shaking, flicker, face, close-up face, head, new objects, added captions, bird, birds, flying animal, insect, cat, dog, falling leaves, flying leaves, floating debris, spark, ember, lens flare, sudden appearing object, glowing particle, steam, smoke, vapor, mist, haze, fog, light bloom, light rays, poster shrinking, poster growing, artwork scaling inside the frame, spilling, pouring, sake level changing, food moving, fish moving, leaf shadows, dappled light, tree shadows, moving shadows, shadow patterns, sudden shadows, sunbeams, window light patterns'
$negHands = $negCommon + ', elongated cup, stretched cup, deformed cup, cup changing size, cup changing shape, tall cup, warped hands, deformed hands, extra fingers, missing fingers, extra hands, extra arms, new hands entering, new person entering, arm raising, lifting arms high, big gesture, upper body, shoulders turning, body moving'
$negNoPeople = $negCommon + ', people, person, silhouette, hands, arm, red berries moving, branch moving'
$lock = "The camera itself is completely locked off and motionless like a tripod photograph, with absolutely no zoom, no push-in, no drift, no pan and no camera movement of any kind for the entire clip."
$poster = "The framed 'NO JAPANESE SAKE, NO LIFE.' pop-art poster on the wall (a hand holding a wooden masu cup) stays perfectly rigid, flat and exactly the same size for the entire clip: its illustration, hand, masu cup, lettering, ALCOHOLIDAY logo, white border and proportions never warp, stretch, resize, shift position or change perspective, as if it truly is a static print and not a generated image."
$mood = "A calm, quiet, relaxed holiday afternoon in a Japanese tatami room with soft even natural light. The sake is cold: no steam, no smoke, no haze. No faces are ever shown. No shadows of leaves or trees, no moving shadow patterns anywhere. All motion is very small, slow and calm."

$items = @(
  @{ name='sake-holiday4-hiki-kling-v3'; image='sake-holiday4-angle1-v7-blend.png'; neg=$negHands; cfg=0.9;
     prompt="$lock $poster The only motion anywhere in this shot is the hand of the person in the navy plaid shirt at the right edge of the table: his resting hand slowly and slightly slides a few centimeters toward the small white sake cup in front of him and his fingertips lightly touch the cup; the cup stays on the table and is not lifted high. His arm, shoulder and body do not rise or move otherwise, and his face never appears. His hand keeps exactly five natural fingers and every sake cup keeps exactly its original small round shape and size. Everything else, including the person in the grey knit sweater in the foreground, the bottles, the tokkuri, all sake cups, all food and dishes, the red berry branch, the cabinet, the shoji screen and the poster, is completely still and motionless. $mood" },
  @{ name='sake-holiday4-kanpai-kling-v3'; image='sake-holiday4-angle2-v2-blend.png'; neg=$negHands; cfg=0.92;
     prompt="$lock $poster The only motion anywhere in this shot is a tiny, gentle toast: the two small white sake cups held by the two hands, already almost touching, move together by just a few millimeters until their rims softly touch with a quiet clink, then stay touching. Only the fingers and wrists move very slightly; the arms, the grey knit sleeve, the navy plaid sleeve and the bodies do not move at all. Both small sake cups keep exactly their original short, round shape and size for the entire clip and are never stretched, elongated or deformed. Each hand keeps exactly five natural fingers. Everything else, including the plain wall, the cabinet, the wrapped cloth, the bottles, the red berries and the poster above, is completely still and motionless. $mood" },
  @{ name='sake-holiday4-up-kling-v3'; image='sake-holiday4-angle3-v1-blend.png'; neg=$negNoPeople; cfg=0.92;
     prompt="$lock $poster This is a calm still shot of a plain beige wall with the framed poster. The only change in this shot is an extremely subtle, slow and even variation in the soft natural daylight brightness on the plain wall, as if a thin cloud passes far away; the light changes uniformly and smoothly with no shapes, no patterns, no shadows of leaves or trees and no moving shadows. The small red berry tip at the lower left corner stays still. Everything, especially the framed poster, is completely still and motionless. $mood" }
)

foreach ($item in $items) {
  if ($Only -and ($Only -notcontains $item.name)) { continue }
  Write-Host "=== $($item.name) ==="
  try {
    $image = Join-Path $designDir $item.image
    if (!(Test-Path -LiteralPath $image)) { throw "Input image not found: $($item.image)" }
    $outputPath = Join-Path $root ($item.name + '.mp4')
    if (Test-Path -LiteralPath $outputPath) { Write-Host "Already exists, skipping"; continue }

    $upload = Invoke-RestMethod -Method Post -Uri 'https://api.higgsfield.ai/files/generate-upload-url' -Headers $headers -ContentType 'application/json' -Body '{"content_type":"image/png"}'
    $uploadHeaders = @{}
    if ($upload.upload_headers) { foreach ($h in $upload.upload_headers.PSObject.Properties) { $uploadHeaders[$h.Name] = [string]$h.Value } }
    Invoke-WebRequest -UseBasicParsing -Method Put -Uri $upload.upload_url -Headers $uploadHeaders -InFile $image | Out-Null

    $req = [ordered]@{ prompt=$item.prompt; duration=5; cfg_scale=$item.cfg; image_url=$upload.public_url; negative_prompt=$item.neg }
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
