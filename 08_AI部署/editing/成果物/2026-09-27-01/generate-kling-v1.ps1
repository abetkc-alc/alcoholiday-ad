# ALCOHOLIDAY editing部：指示 2026-09-27-01（ワイン 金曜の夜）の Higgsfield 動画生成 v1
# 社長が選んだ順：角度4 → 角度5 → 角度2。1本 5秒、見積もりが $0.25 を超えたら止める。同名ファイルがあれば生成しない。
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
$negBase = 'poster warping, poster bending, poster resizing, poster shifting position, poster tilting, poster swaying, poster vibration, poster micro-movement, poster jitter, perspective change, illustration reshaping, hand redrawing, glass redrawing, cropped poster, warped text, changing letters, misspelled words, garbled text, nonsense text, fake text, distorted logo, animated poster illustration, morphing artwork, new shapes appearing inside the poster, cursive text, script text, handwriting, signature, watermark, ghost text, any text not in the original image, camera orbit, zoom, zooming in, zooming out, camera push-in, dolly, pan, tilt, parallax, fast movement, shaking, flicker, hands entering, new objects, added captions, bird, birds, flying animal, falling leaves, flying leaves, floating leaves, leaves detaching from branch, leaf storm, petals flying, floating debris, spark, ember, lens flare, sudden appearing object, glowing particle'
$lock = "The camera itself is completely locked off and motionless like a tripod photograph, with absolutely no zoom, no push-in, no drift, no pan and no camera movement of any kind for the entire clip."
$poster = "The framed yellow 'NO WINE, NO LIFE.' poster stays perfectly rigid, flat and exactly the same size for the entire clip: its illustration, hand, glass, lettering, logo, white border and proportions never warp, stretch, resize, shift position or change perspective, as if it truly is a static print and not a generated image."

$items = @(
  @{ name='wine-friday-angle4-kling-v1'; image='wine-friday-angle4-v1.png'; neg="$negBase, people";
     prompt="$lock $poster The only motion anywhere in this shot is the small candle flame in the glass holder on the coffee table, which flickers gently and clearly, its warm light softly dancing on the wine glass and the plates. Everything else, including the wine in the glass, the food, the sofa, the plants and the poster, is completely still and motionless. Bright, warm, cozy Friday evening living room, interior magazine photography quality." },
  @{ name='wine-friday-angle5-kling-v1'; image='wine-friday-angle5-v1.png'; neg="$negBase, extra legs, extra feet, deformed feet, face, upper body";
     prompt="$lock $poster The only motion anywhere in this shot is the woman's relaxed feet in cozy gray knit socks resting on the pouf in the foreground: she slowly and naturally stretches her feet and wiggles her toes once, then relaxes, as if enjoying the moment after a bath. Her legs stay in the same place with natural anatomy. Everything else, including the coffee table, food, wine, sofa, plants and the poster, is completely still and motionless. Bright, warm, cozy Friday evening living room, interior magazine photography quality." },
  @{ name='wine-friday-angle2-kling-v1'; image='wine-friday-angle2-v1.png'; neg="$negBase, people";
     prompt="$lock $poster The only motion anywhere in this shot is the mustard knit throw draped over the sofa arm, whose soft fringe sways gently and clearly as if touched by a light breeze. Every autumn leaf on the branches in the vase stays firmly attached and frozen in place. Everything else, including the sofa, cushions, lamp, vase and the poster, is completely still and motionless. Bright, warm, cozy Friday evening living room, interior magazine photography quality." }
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
