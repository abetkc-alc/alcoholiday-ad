# ALCOHOLIDAY editing部：指示 2026-10-06-01（ウイスキー・8畳のワンルームでサッカー観戦）の Higgsfield 動画生成 v1
# 社長が選んだ順：中ぐらいのアップ(angle2) → 引き(angle1) → アップ(angle3)。ポスターは絶対に動かさない・湯気なし。
# テレビにはサッカーの試合（文字・ロゴ・顔なし）。1本 5秒、見積もりが $0.25 を超えたら止める。同名ファイルがあれば生成しない。
# コツ：カメラは完全固定、動かすものは1つだけ、ほかは完全に静止と明言。cfg_scale 0.9。
$ErrorActionPreference = 'Stop'
$maxUsd = [decimal]0.25
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$key = [Environment]::GetEnvironmentVariable('HF_KEY','User')
if ([string]::IsNullOrWhiteSpace($key)) { $key = $env:HF_KEY }
if ([string]::IsNullOrWhiteSpace($key)) { throw 'HF_KEY is not available.' }
$headers = @{ Authorization = "Key $($key.Trim())" }

$root = $PSScriptRoot
$designDir = Join-Path $root '..\..\..\design\成果物\2026-10-06-01'
$model = 'kling-video/v2.5-turbo/standard/image-to-video'
$negCommon = 'poster warping, poster bending, poster resizing, poster shifting position, poster tilting, poster swaying, poster vibration, poster micro-movement, poster jitter, perspective change, illustration reshaping, hand redrawing, glass redrawing, cropped poster, warped text, changing letters, misspelled words, garbled text, nonsense text, fake text, distorted logo, animated poster illustration, morphing artwork, new shapes appearing inside the poster, cursive text, script text, handwriting, signature, watermark, ghost text, any text not in the original image, on-screen text, score display, scoreboard, channel logo, TV logo, subtitles on TV, camera orbit, zoom, zooming in, zooming out, camera push-in, dolly, pan, tilt, parallax, fast movement, shaking, flicker, hands entering, face, close-up face, new objects, added captions, bird, birds, flying animal, insect, cat, dog, falling leaves, flying leaves, floating debris, spark, ember, lens flare, sudden appearing object, glowing particle, steam, smoke, vapor, mist, haze, fog, light bloom, light rays, poster shrinking, poster growing, artwork scaling inside the frame, spilling, whisky level changing, food moving, ball rolling'
$negNoPeople = $negCommon + ', people, person, silhouette'
$lock = "The camera itself is completely locked off and motionless like a tripod photograph, with absolutely no zoom, no push-in, no drift, no pan and no camera movement of any kind for the entire clip."
$poster = "The framed beige 'NO WHISKY, NO LIFE.' pop-art poster on the wall stays perfectly rigid, flat and exactly the same size for the entire clip: its illustration, hand, rocks glass, lettering, logo, white border and proportions never warp, stretch, resize, shift position or change perspective, as if it truly is a static print and not a generated image."
$mood = "Bright, warm, cozy night in a small tidy Japanese 8-tatami one-room apartment, interior magazine photography quality. No steam, no smoke, no haze."

$items = @(
  @{ name='whisky-soccer8-naka-kling-v1'; image='whisky-soccer8-angle2-v2-blend.png'; neg=$negNoPeople;
     prompt="$lock $poster The only motion anywhere in this shot is inside the rocks glass of whisky on the round coffee table: the large ice cube turns and settles very slightly and the golden whisky surface ripples gently and catches the warm light. The whisky level and the glass shape never change. Everything else, including the bottle, the karaage, fries and edamame packs, the sofa, the cushions, the green-and-cream scarf, the football, the floor lamp, the shelf, the plants and the poster, is completely still and motionless. $mood" },
  @{ name='whisky-soccer8-hiki-kling-v1'; image='whisky-soccer8-angle1-v2-blend.png'; neg=$negCommon;
     prompt="$lock $poster The only motion anywhere in this shot is on the TV screen at the right: a football match continues as a distant wide broadcast view of a bright green pitch, where tiny soft-focus players run naturally across the field; the TV screen shows no text, no score, no logos and no faces, only the distant pitch and tiny players. The TV set itself does not move. Everything else, including the sofa, the scarf, the coffee table with the whisky and deli food, the rug, the football on the floor, the floor lamp, the shelf with bottles, the plants, the bed and the poster, is completely still and motionless. $mood" },
  @{ name='whisky-soccer8-up-kling-v1'; image='whisky-soccer8-angle3-v2-blend.png'; neg=$negNoPeople;
     prompt="$lock $poster The only motion anywhere in this shot is the trailing green leaves of the potted plant at the right edge, which sway very gently as if touched by a soft breeze from the air conditioner; every leaf stays firmly attached. Everything else, including the wall, the warm light on the wall, the green sofa, the cushion, the scarf and especially the framed poster, is completely still and motionless. $mood" }
)

foreach ($item in $items) {
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
