# ALCOHOLIDAY editing部：指示 2026-10-10-01（日本酒・連休に同級生と昼飲み）の Higgsfield 動画生成 v1
# 社長が選んだ順：中ぐらい(angle2-v2) → 引き(angle1-v1) → アップ(angle3-v3)。ポスターは絶対に動かさない・湯気なし（冷酒）。
# 人は顔を出さない（negative_prompt に face）。1本 5秒、見積もりが $0.25 を超えたら止める。同名ファイルがあれば生成しない。
# コツ：カメラは完全固定、動かすものは1つだけ、ほかは完全に静止と明言。cfg_scale 0.9。
# 使い方: generate-kling-v1.ps1 [-Only 名前...]（省略時は全部）
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
$negCommon = 'poster warping, poster bending, poster resizing, poster shifting position, poster tilting, poster swaying, poster vibration, poster micro-movement, poster jitter, perspective change, illustration reshaping, hand redrawing in the poster, masu cup redrawing, cropped poster, warped text, changing letters, misspelled words, garbled text, nonsense text, fake text, distorted logo, animated poster illustration, morphing artwork, new shapes appearing inside the poster, cursive text, script text, handwriting, signature, watermark, ghost text, any text not in the original image, bottle label text changing, camera orbit, zoom, zooming in, zooming out, camera push-in, dolly, pan, tilt, parallax, fast movement, shaking, flicker, face, close-up face, head, new objects, added captions, bird, birds, flying animal, insect, cat, dog, falling leaves, flying leaves, floating debris, spark, ember, lens flare, sudden appearing object, glowing particle, steam, smoke, vapor, mist, haze, fog, light bloom, light rays, poster shrinking, poster growing, artwork scaling inside the frame, spilling, pouring, sake level changing, food moving, fish moving'
$negHands = $negCommon + ', extra fingers, missing fingers, deformed hands, extra hands, extra arms, new hands entering, new person entering, upper body, shoulders turning'
$negNoPeople = $negCommon + ', people, person, silhouette, hands, arm'
$lock = "The camera itself is completely locked off and motionless like a tripod photograph, with absolutely no zoom, no push-in, no drift, no pan and no camera movement of any kind for the entire clip."
$poster = "The framed 'NO JAPANESE SAKE, NO LIFE.' pop-art poster on the wall (a hand holding a wooden masu cup) stays perfectly rigid, flat and exactly the same size for the entire clip: its illustration, hand, masu cup, lettering, ALCOHOLIDAY logo, white border and proportions never warp, stretch, resize, shift position or change perspective, as if it truly is a static print and not a generated image."
$mood = "A sunny, relaxed holiday afternoon in a Japanese tatami living room, warm natural sunlight, two old school friends enjoying chilled sake together. The sake is cold: no steam, no smoke, no haze. No faces are ever shown."

$items = @(
  @{ name='sake-holiday-naka-kling-v1'; image='sake-holiday-angle2-v2-blend.png'; neg=$negHands;
     prompt="$lock $poster The only motion anywhere in this shot is the hand in the grey knit sleeve in the lower left foreground: it slowly and gently lifts the small white sake cup a little higher and tilts it slightly toward the left edge of the frame, as if about to take a happy sip; the person's face and head stay completely outside the frame and never appear. The hand keeps exactly five natural fingers and the cup keeps its shape. Everything else, including the sake bottles, the tokkuri, the sashimi, the grilled fish, the edamame and all dishes, the person in the navy plaid shirt at the right edge, the cabinet, the plants, the window and the poster, is completely still and motionless. $mood" },
  @{ name='sake-holiday-hiki-kling-v1'; image='sake-holiday-angle1-v1-blend.png'; neg=$negHands;
     prompt="$lock $poster The only motion anywhere in this shot is the hand of the man in the navy plaid shirt at the right: holding his small white sake cup, he raises it gently forward toward his friend in a small, cheerful kanpai toast gesture and then holds it there; his face stays completely outside the frame and never appears. His hand keeps exactly five natural fingers and the cup keeps its shape. Everything else, including the man in the grey knit sweater in the foreground and his hand on the cup, the low table with the sake bottles, tokkuri and food, the TV, the shelf, the plants, the shoji screen, the window and the poster, is completely still and motionless. $mood" },
  @{ name='sake-holiday-up-kling-v1'; image='sake-holiday-angle3-v3-blend.png'; neg=$negNoPeople;
     prompt="$lock $poster The only motion anywhere in this shot is the soft dappled sunlight and leaf shadows on the beige wall at the right side and on the wooden table: the shadows of tree leaves outside sway slowly and gently, as if a light breeze moves the branches, and the sunlight on the white tokkuri and sake cups shimmers softly. The leaf shadows stay on the wall beside the poster and on the table and never move the poster. Everything else, including the blurred tokkuri and sake cups in the foreground, the table, the wall and especially the framed poster, is completely still and motionless. $mood" }
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

    $req = [ordered]@{ prompt=$item.prompt; duration=5; cfg_scale=0.9; image_url=$upload.public_url; negative_prompt=$item.neg }
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
