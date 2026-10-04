# ALCOHOLIDAY editing部：Tシャツ「1966 ISLAY WAS FRUIT」宣伝動画（2026-10-03-02）の Higgsfield 動画生成 v1
# 社長承認済み（2026-10-03）：声は後から付けるので、すべて音なしで生成。同名ファイルがあれば生成しない（二重課金防止）。
# ①話す（Kling 3.0 std・音なし・5秒・上限 $0.40）②Tシャツのアップ（Kling 2.5・5秒・上限 $0.25）③笑顔（Kling 2.5・5秒・上限 $0.25）
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$key = [Environment]::GetEnvironmentVariable('HF_KEY','User')
if ([string]::IsNullOrWhiteSpace($key)) { $key = $env:HF_KEY }
if ([string]::IsNullOrWhiteSpace($key)) { throw 'HF_KEY is not available.' }
$headers = @{ Authorization = "Key $($key.Trim())" }

$root = $PSScriptRoot
$designDir = Join-Path $root '..\..\..\design\成果物\2026-10-03-02'
$lock = "The camera is completely locked off like a tripod shot: no zoom, no push-in, no drift, no pan, no camera movement at all."
$print = "The yellow print on her black T-shirt (the words '1966', 'ISLAY', 'WAS', 'FRUIT' and the seagull line drawing) stays exactly the same: same letters, same spelling, same shapes, never redrawn, never morphing, it only moves naturally with the fabric."
$negBase = 'zoom, zooming in, zooming out, camera push-in, dolly, pan, tilt, camera shake, garbled text, changing letters, misspelled words, nonsense text, extra text, new text, morphing print, print redrawing, warped logo, extra fingers, deformed hands, distorted face, face morphing, identity change, different person, teeth distortion, flicker, watermark, captions, subtitles'

$items = @(
  @{ name='b-talk-kling3-v1'; image='tshirt1966-womanB-v2-blend.png'; model='kling-video/v3.0/std/image-to-video'; max=[decimal]0.40;
     extra=@{ sound='off' };
     prompt="$lock $print A cool young Japanese woman stands still at a dim whisky bar counter, staring straight into the camera with a completely deadpan, expressionless face, slightly surreal. She speaks one short sentence quietly and slowly in Japanese directly to the viewer, her lips moving naturally as if saying 'Single malt wo shiranai to... kono imi wa, wakaranai.', with a tiny pause before the last words. Her eyes never leave the camera, she does not smile, her head and shoulders stay almost still. Only her lips, a slow blink and a few strands of hair move. The warm bokeh lights of the bar softly glimmer in the background. Avoid: $negBase" },
  @{ name='closeup-kling25-v1'; image='tshirt1966-B-closeup-v1.png'; model='kling-video/v2.5-turbo/standard/image-to-video'; max=[decimal]0.25;
     extra=@{ cfg_scale=0.9; negative_prompt="$negBase, face, head" };
     prompt="$lock $print Close-up of a woman's chest wearing a black T-shirt with a yellow print. The only motion is her fingers gently tugging the hem of the T-shirt once and releasing it, so the cotton fabric softly ripples and the print follows the fabric naturally. Her body otherwise stays still with a slow breath. The warm bar lights in the background stay softly blurred. Realistic cinematic product shot." },
  @{ name='smile-kling25-v1'; image='tshirt1966-B-smile-start-v1.png'; model='kling-video/v2.5-turbo/standard/image-to-video'; max=[decimal]0.25;
     extra=@{ cfg_scale=0.9; negative_prompt="$negBase, laughing loudly, open mouth, exaggerated expression" };
     prompt="$lock $print A young Japanese woman at a warm whisky bar looks into the camera with a calm neutral face, then her eyes gradually soften and she breaks into a gentle, warm, genuine smile, tilting her head very slightly, as if sharing a secret with a friend. Natural subtle movement, same face and identity throughout, no exaggeration. Warm bokeh lights glimmer softly in the background." }
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

    $req = [ordered]@{ prompt=$item.prompt; duration=5; image_url=$upload.public_url }
    foreach ($k in $item.extra.Keys) { $req[$k] = $item.extra[$k] }
    $body = $req | ConvertTo-Json -Depth 8
    $estimate = Invoke-RestMethod -Method Post -Uri ("https://api.higgsfield.ai/estimate/" + $item.model) -Headers $headers -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body))
    $usd = [decimal]::Parse([string]$estimate.usd, [Globalization.CultureInfo]::InvariantCulture)
    Write-Host ('Estimate USD: ' + $usd)
    if ($usd -gt $item.max) { throw ('Estimate exceeds safety limit of $' + $item.max) }

    $submit = Invoke-RestMethod -Method Post -Uri ("https://api.higgsfield.ai/" + $item.model) -Headers $headers -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body))
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
    [ordered]@{ generated_at=(Get-Date).ToString('o'); model=$item.model; request_id=$requestId; estimate_usd=[string]$estimate.usd; source=$item.image; input=$req } |
      ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $root ($item.name + '-result.json')) -Encoding UTF8
    Write-Host "DONE $($item.name).mp4"
  } catch {
    Write-Host ('FAILED [' + $item.name + ']: ' + $_.Exception.Message)
  }
}
Write-Host '=== all items processed ==='
