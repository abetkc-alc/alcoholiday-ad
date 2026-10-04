# ALCOHOLIDAY editing部：指示 2026-09-27-01（ワイン 3枚セット）の Higgsfield 動画生成 v2
# 社長が選んだ順：中ぐらいのアップ → 引き → アップ。ポスターは絶対に動かさない・湯気なし（社長指示）。1本 5秒、見積もりが $0.25 を超えたら止める。同名ファイルがあれば生成しない。
# コツ（過去の失敗から）：カメラは完全固定、動かすものは1つだけ、ほかは完全に静止と明言。cfg_scale 0.9。
$ErrorActionPreference = 'Stop'
$maxUsd = [decimal]0.25
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$key = [Environment]::GetEnvironmentVariable('HF_KEY','User')
if ([string]::IsNullOrWhiteSpace($key)) { $key = $env:HF_KEY }
if ([string]::IsNullOrWhiteSpace($key)) { throw 'HF_KEY is not available.' }
$headers = @{ Authorization = "Key $($key.Trim())" }

$root = $PSScriptRoot
$designDir = Join-Path $root '..\..\..\design\成果物\2026-09-27-01'
$model = 'kling-video/v2.5-turbo/standard/image-to-video'
$negBase = 'poster warping, poster bending, poster resizing, poster shifting position, poster tilting, poster swaying, poster vibration, poster micro-movement, poster jitter, perspective change, illustration reshaping, hand redrawing, glass redrawing, cropped poster, warped text, changing letters, misspelled words, garbled text, nonsense text, fake text, distorted logo, animated poster illustration, morphing artwork, new shapes appearing inside the poster, cursive text, script text, handwriting, signature, watermark, ghost text, any text not in the original image, camera orbit, zoom, zooming in, zooming out, camera push-in, dolly, pan, tilt, parallax, fast movement, shaking, flicker, hands entering, new objects, added captions, bird, birds, flying animal, falling leaves, flying leaves, floating leaves, leaves detaching from branch, leaf storm, petals flying, floating debris, spark, ember, lens flare, sudden appearing object, glowing particle, steam, smoke, vapor, mist, haze, fog, light bloom, light rays, poster shrinking, poster growing, artwork scaling inside the frame'
$lock = "The camera itself is completely locked off and motionless like a tripod photograph, with absolutely no zoom, no push-in, no drift, no pan and no camera movement of any kind for the entire clip."
$poster = "The framed yellow 'NO WINE, NO LIFE.' poster stays perfectly rigid, flat and exactly the same size for the entire clip: its illustration, hand, glass, lettering, logo, white border and proportions never warp, stretch, resize, shift position or change perspective, as if it truly is a static print and not a generated image."

$items = @(
  @{ name='wine-3shot-naka-kling-v1'; image='wine-3shot-naka-v2.png'; neg="$negBase, people";
     prompt="$lock $poster The only motion anywhere in this shot is the small candle flame in the glass holder on the side table, which flickers gently and clearly, its warm glow softly dancing on the wine glass and the plates. Everything else, including the wine, the food, the sofa, the lamp, the plants and the poster, is completely still and motionless. Bright, warm, cozy early-autumn Friday evening, interior magazine photography quality." },
  @{ name='wine-3shot-hiki-kling-v1'; image='wine-3shot-hiki-v3.png'; neg="$negBase, face, turning head, looking at camera, extra arms, extra hands, deformed hands, spilling wine";
     prompt="$lock $poster The only motion anywhere in this shot is the woman in the oatmeal knit sweater sitting on the loveseat with her back to the camera: she slowly and naturally raises her glass of red wine and takes a small relaxed sip, then lowers it again. She never turns her head toward the camera and her face is never visible. Everything else, including the furniture, the dining table, the plants, the lamps and the poster, is completely still and motionless. Bright, warm, cozy early-autumn Friday evening, interior magazine photography quality." },
  @{ name='wine-3shot-up-kling-v1'; image='wine-3shot-up-v2.png'; neg="$negBase, people";
     prompt="$lock $poster The only motion anywhere in this shot is the red-orange autumn branch in the lower right foreground, which sways very gently as if touched by a soft breeze; every leaf stays firmly attached. Everything else, including the wall, the sofa, the plant on the left and especially the framed poster, is completely still and motionless. Bright, warm, cozy early-autumn Friday evening, interior magazine photography quality." }
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
