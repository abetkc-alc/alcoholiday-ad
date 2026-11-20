# ALCOHOLIDAY editing部：指示 2026-11-01-02（ワイン・ビール・スパークリング／23歳それぞれの部屋）Higgsfield 生成 v1
# 2026-11-01-01（日本酒）の generate-kling-v1.ps1 をコピー。ポスターの説明と雰囲気を種類ごとに持たせた
# 写真：Codex が作った <種類>-angle-01〜03-a2-420x592-v4.png を 9:16 に左右だけ切ったもの（src/）
# 順：引き(angle1) → 中くらい(angle2) → アップ(angle3)。ポスターは絶対に動かさない・湯気なし。動かすものは1本に1つ。
# 1本 5秒、見積もりが $0.25 を超えたら止める。同名ファイルがあれば生成しない。
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
$designDir = Join-Path $root 'src'
$model = 'kling-video/v2.5-turbo/standard/image-to-video'
$negCommon = 'poster warping, poster bending, poster resizing, poster shifting position, poster tilting, poster swaying, poster vibration, poster micro-movement, poster jitter, perspective change, illustration reshaping, hand redrawing in the poster, glass redrawing, mug redrawing, cropped poster, warped text, changing letters, misspelled words, garbled text, nonsense text, fake text, distorted logo, animated poster illustration, morphing artwork, new shapes appearing inside the poster, cursive text, script text, handwriting, signature, watermark, ghost text, any text not in the original image, camera orbit, zoom, zooming in, zooming out, camera push-in, dolly, pan, tilt, parallax, fast movement, shaking, flicker, people, person, silhouette, hands, arm, face, new objects, added captions, bird, birds, flying animal, insect, cat, dog, falling leaves, flying leaves, floating debris, spark, ember, lens flare, sudden appearing object, glowing particle, steam, smoke, vapor, mist, haze, fog, light bloom, light rays, poster shrinking, poster growing, artwork scaling inside the frame, food moving, leaf shadows, moving shadows, shadow patterns, sudden shadows'
$lock = "The camera itself is completely locked off and motionless like a tripod photograph, with absolutely no zoom, no push-in, no drift, no pan and no camera movement of any kind for the entire clip."
function PosterText($label, $art) {
  "The framed '$label' pop-art poster on the wall ($art) stays perfectly rigid, flat and exactly the same size for the entire clip: its illustration, hand, glass, lettering, ALCOHOLIDAY logo, white border and proportions never warp, stretch, resize, shift position or change perspective, as if it truly is a static print and not a generated image."
}
$pWine = PosterText 'NO WINE, NO LIFE.' 'a hand holding a glass of red wine on a bright yellow background'
$pBeer = PosterText 'NO BEER, NO LIFE.' 'a hand holding a beer mug on a light blue background'
$pSpk = PosterText 'NO SPARKLING WINE, NO LIFE.' 'a hand holding a champagne flute on a red background'
$mWine = "A quiet night in the small tidy one-room apartment of a 23-year-old office worker, warm desk lamp light inside and city lights outside. No steam, no smoke, no haze. No people. All motion is small, slow and calm."
$mBeer = "A bright, sunny afternoon in the small one-room apartment of a 23-year-old university student, warm sunlight coming through the window. No steam, no smoke, no haze. No people. All motion is small, slow and calm."
$mSpk = "A golden sunset in the small one-room apartment of a 23-year-old apprentice designer, warm orange evening light through the window. No steam, no smoke, no haze. No people. All motion is small, slow and calm."
$still = "Everything else in the room, including the furniture, the desk and everything on it, the shelves, the books, the bags, the clothes, the bed and especially the framed poster, is completely still and motionless."

$items = @(
  @{ name='wine-room-hiki-kling-v1'; image='wine-room-angle1-916.png'; neg=$negCommon; cfg=0.9;
     prompt="$lock $pWine The only motion anywhere in this shot is the sheer curtain beside the window: it sways very gently as if touched by a soft breeze, and stays hanging in place. The window and the city outside do not move. $still $mWine" },
  @{ name='wine-room-naka-kling-v1'; image='wine-room-angle2-916.png'; neg=$negCommon; cfg=0.9;
     prompt="$lock $pWine The only motion anywhere in this shot is the leaves of the small potted plant on the desk: they sway very gently as if touched by a soft breeze; every leaf stays firmly attached. $still $mWine" },
  @{ name='wine-room-up-kling-v1'; image='wine-room-angle3-916.png'; neg=$negCommon; cfg=0.9;
     prompt="$lock $pWine The only motion anywhere in this shot is the curtain at the left edge of the frame: it sways very gently as if touched by a soft breeze; it never covers the poster. $still $mWine" },
  @{ name='beer-room-hiki-kling-v1'; image='beer-room-angle1-916.png'; neg=$negCommon; cfg=0.9;
     prompt="$lock $pBeer The only motion anywhere in this shot is the light curtain at the window: it sways gently in a soft breeze, and the sunlight on the floor shifts very slightly with it. The window and the view outside do not move. $still $mBeer" },
  @{ name='beer-room-naka-kling-v1'; image='beer-room-angle2-916.png'; neg=$negCommon; cfg=0.9;
     prompt="$lock $pBeer The only motion anywhere in this shot is the trailing green ivy hanging at the upper right: its leaves sway gently as if touched by a soft breeze; every leaf stays firmly attached. $still $mBeer" },
  @{ name='beer-room-up-kling-v1'; image='beer-room-angle3-916.png'; neg=$negCommon; cfg=0.9;
     prompt="$lock $pBeer The only motion anywhere in this shot is the trailing green ivy at the upper right edge: its leaves sway gently as if touched by a soft breeze; every leaf stays firmly attached and never covers the poster. $still $mBeer" },
  @{ name='sparkling-room-hiki-kling-v1'; image='sparkling-room-angle1-916.png'; neg=$negCommon; cfg=0.9;
     prompt="$lock $pSpk The only motion anywhere in this shot is outside the window: the soft sunset clouds drift slowly and smoothly to the side in the orange sky. The window frame, the buildings and the skyline themselves never move. $still $mSpk" },
  @{ name='sparkling-room-naka-kling-v1'; image='sparkling-room-angle2-916.png'; neg=$negCommon; cfg=0.9;
     prompt="$lock $pSpk The only motion anywhere in this shot is the green ivy growing around the window: its leaves sway gently as if touched by a soft evening breeze; every leaf stays firmly attached. $still $mSpk" },
  @{ name='sparkling-room-up-kling-v1'; image='sparkling-room-angle3-916.png'; neg=$negCommon; cfg=0.9;
     prompt="$lock $pSpk The only motion anywhere in this shot is the green ivy at the right edge of the frame: its leaves sway gently as if touched by a soft evening breeze; every leaf stays firmly attached and never covers the poster. $still $mSpk" }
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
    Write-Host ('FAILED [' + $item.name + '] line ' + $_.InvocationInfo.ScriptLineNumber + ': ' + $_.Exception.Message + ' ' + $_.ErrorDetails.Message)
  }
}
Write-Host '=== all items processed ==='
