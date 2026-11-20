# ALCOHOLIDAY editing部：指示 2026-11-01-01（日本酒・飲食店で働く23歳の部屋）Higgsfield 生成 v1
# 写真：Codex が 2026-10-31〜11-01 に作った sake-angle-01〜03-a2-420x592-v4.png を 9:16 に左右だけ切ったもの（src/）
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
$negCommon = 'poster warping, poster bending, poster resizing, poster shifting position, poster tilting, poster swaying, poster vibration, poster micro-movement, poster jitter, perspective change, illustration reshaping, hand redrawing in the poster, masu cup redrawing, cropped poster, warped text, changing letters, misspelled words, garbled text, nonsense text, fake text, distorted logo, animated poster illustration, morphing artwork, new shapes appearing inside the poster, cursive text, script text, handwriting, signature, watermark, ghost text, any text not in the original image, camera orbit, zoom, zooming in, zooming out, camera push-in, dolly, pan, tilt, parallax, fast movement, shaking, flicker, people, person, silhouette, hands, arm, face, new objects, added captions, bird, birds, flying animal, insect, cat, dog, falling leaves, flying leaves, floating debris, spark, ember, lens flare, sudden appearing object, glowing particle, steam, smoke, vapor, mist, haze, fog, light bloom, light rays, poster shrinking, poster growing, artwork scaling inside the frame, food moving, leaf shadows, moving shadows, shadow patterns, sudden shadows'
$lock = "The camera itself is completely locked off and motionless like a tripod photograph, with absolutely no zoom, no push-in, no drift, no pan and no camera movement of any kind for the entire clip."
$poster = "The framed 'NO JAPANESE SAKE, NO LIFE.' pop-art poster on the wall (a hand holding a wooden masu cup on a pale grey background) stays perfectly rigid, flat and exactly the same size for the entire clip: its illustration, hand, masu cup, lettering, ALCOHOLIDAY logo, white border and proportions never warp, stretch, resize, shift position or change perspective, as if it truly is a static print and not a generated image."
$mood = "A quiet, calm early evening at dusk in the small tidy one-room apartment of a 23-year-old who works at a Japanese restaurant, warm lamp light inside and a deep blue city sky outside. No steam, no smoke, no haze. No people. All motion is small, slow and calm."

$items = @(
  @{ name='sake-room-hiki-kling-v1'; image='sake-room-angle1-916.png'; neg=$negCommon; cfg=0.9;
     prompt="$lock $poster The only motion anywhere in this shot is outside the window at the left: the soft dusk clouds in the blue evening sky drift slowly and smoothly to the side, and a few distant city windows twinkle very faintly. The window frame, the buildings and the skyline themselves never move. Everything else, including the window plants, the folded futon, the shelf, the black bags, the boxes, the towel, the kitchen, the low table with the notebook and food container, the shoes and the poster, is completely still and motionless. $mood" },
  @{ name='sake-room-naka-kling-v1'; image='sake-room-angle2-916.png'; neg=$negCommon; cfg=0.9;
     prompt="$lock $poster The only motion anywhere in this shot is the white hand towel with blue stripes hanging on the kitchen cabinet handle: it sways very gently back and forth as if touched by a soft breeze, and stays hanging on the handle. Everything else, including the window and the city outside, the chef jacket and the black apron on the hooks, the shelf, the boxes, the black bag, the low table with the notebook, pen, food container and cup, the cushion, the shoes and the poster, is completely still and motionless. $mood" },
  @{ name='sake-room-up-kling-v1'; image='sake-room-angle3-916.png'; neg=$negCommon; cfg=0.9;
     prompt="$lock $poster The only motion anywhere in this shot is the long black apron hanging on the hook at the left of the poster: its lower half sways very gently as if touched by a soft breeze; the apron never touches or covers the poster and stays on its hook. Everything else, including the white chef jacket, the black cap, the wall, the shelf with the black bag and boxes, the kitchen counter, the utensils, the towel and especially the framed poster, is completely still and motionless. $mood" }
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
